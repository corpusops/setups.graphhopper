#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import traceback
import json
import requests
import docker
from datetime import datetime, timedelta
import logging
import re
import subprocess
import re
import time

from raven import Client


re_flags = re.U | re.M
PBFS = os.environ.get("GRAPHHOPPER_PBFS", "")
TRAEFIK_ROUTING_CONF = os.environ.get(
    "TRAEFIK_ROUTING_CONF", "/traefik/00_routing.toml"
)
TRAEFIK_ADDRESS = os.environ.get("TRAEFIK_ADDRESS", "http://traefik:8080")
TRAEFIK_PROVIDER = os.environ.get("TRAEFIK_PROVIDER", "file")
TRAEFIK_BACKEND = os.environ.get("TRAEFIK_BACKEND", "graphhopper")
TRAEFIK_FRONTEND = os.environ.get("TRAEFIK_FRONTEND", "graphhopper")
COMPOSE_PROJECT_NAME = os.environ.get("COMPOSE_PROJECT_NAME", "graphhopper")
SENTRY_URL = os.environ.get("SENTRY_URL", None)
CHECK_INTERVAL = int(os.environ.get("GRAPHHOPPER_CHECK_INTERVAL", 10))
CACHE_BACKEND_TIMEOUT = int(
    os.environ.get("GRAPHHOPPER_CACHE_BACKEND_TIMEOUT", 60 * 60 * 4)
)
CACHE_BACKEND_EXPIRY = int(
    os.environ.get("GRAPHHOPPER_CACHE_BACKEND_EXPIRY", 432000)
)

STATESFILE = "/switcher-data/cops_graphhopper.json"
LOG_FORMAT = "%(asctime)s  [%(levelname)-5.5s]  %(message)s"
log = logging.getLogger("graphprctlr")
"""
Json has the following spec, and is multilined to make
monitoring probes easier to write with simple (bash) scripts.

The upgraded backend is always the "yang" backend.
Upon final sync, we sync it's data back to the ying one.

{
    "last_ok": TS,
    "status": Bool
}
"""

compose_container = re.compile(
    "/{0}_".format(COMPOSE_PROJECT_NAME), flags=re.M | re.U
)


def traefik_backend_conf(backend):
    return {
        backend: {
            "url": "http://graphhopper-{0}:8989".foramt(backend),
            "weight": 0,
        }
    }


class FinishedUpdateError(Exception):
    """."""


class UpdateError(Exception):
    """."""


class UpdateTimeoutError(Exception):
    """."""


class TraefikAttachError(Exception):
    """."""


class TraefikDetachError(Exception):
    """."""


def report_err(sentry_url=SENTRY_URL, trace=None):
    if sentry_url:
        client = Client(sentry_url)
        client.captureException()
    elif trace:
        log.error(trace)


class States(object):
    def __init__(self, statesfile=STATESFILE, *a, **kw):
        self.states = {}
        self.statesfile = STATESFILE
        self.now = datetime.now()

    def write(self):
        with open(self.statesfile, "w") as f:
            f.write(json.dumps(self.states))

    @classmethod
    def load(kls, *a, **kw):
        self = kls(*a, **kw)
        if not os.path.exists(self.statesfile):
            self.states = {}
        else:
            with open(self.statesfile) as f:
                self.states.update(json.loads(f.read()))
        self.states.setdefault("last_ok", None)
        self.states.setdefault("status", "STALE")
        return self

    def _ts(self, k):
        try:
            ts = datetime.fromtimestamp(self.states[k])
        except KeyError:
            ts = None
        return ts

    @property
    def last_ok(self):
        return self._ts("last_ok")

    @property
    def status(self):
        return self.states.get("status", None)

    def write_switch(self, state):
        self.states["status"] = state
        log.info("Marking state as {0}".format(state))
        if state == "OK":
            last_ok = datetime.now()
            self.states["last_ok"] = last_ok.timestamp()
        self.write()

    def stale(self):
        lo = self.last_ok()
        stale = True
        if lo:
            td = self.now() - lo
            sd = td.total_seconds()
            stale = sd >= CACHE_BACKEND_EXPIRY
        stale = stale or self.status == "STALE"
        if stale and self.status != "STALE":
            self.write_switch("STALE")
        return stale


class TraefikController(object):
    def __init__(
        self,
        traefik_address=TRAEFIK_ADDRESS,
        traefik_timeout=10,
        traefik_provider=TRAEFIK_PROVIDER,
        traefik_backend=TRAEFIK_BACKEND,
        traefik_frontend=TRAEFIK_FRONTEND,
        *a,
        **kw
    ):
        self.address = traefik_address
        self.timeout = traefik_timeout
        self.provider = traefik_provider
        self.backend = traefik_backend
        self.frontend = traefik_frontend

    def request(self, path="/", method="get", timeout=None, *args, **kwargs):
        if timeout is None:
            timeout = self.timeout
        kwargs.setdefault("timeout", timeout)
        return getattr(requests, method)(
            "{0}{1}".format(self.address, path), *args, **kwargs
        )

    def get(self, *args, **kw):
        return self.request(method="get", *args, **kw)

    def post(self, *args, **kw):
        return self.request(method="post", *args, **kw)

    def put(self, *args, **kw):
        return self.request(method="put", *args, **kw)

    def write_conf(self, content):
        with open(TRAEFIK_ROUTING_CONF, "w") as wfic:
            wfic.write(u"\n".join(content))

    def get_conf(self):
        with open(TRAEFIK_ROUTING_CONF, "r") as fic:
            content = fic.read().splitlines()
        return content

    def get_attached_backends(self):
        ret = {"ying": None, "yang": None}
        content = self.get_conf()
        for i, l in enumerate(content):
            for backend in ret:
                if backend in l and ret[backend] is None:
                    if l.strip().startswith("#"):
                        ret[backend] = False
                    else:
                        ret[backend] = True
        return ret

    def toggle(self, backend, activate=True):
        content = self.get_conf()
        ncontent = []
        if activate:
            state = "Attaching {0} to traefik".format(backend)
        else:
            state = "Detaching {0} from traefik".format(backend)
        log.info(state)
        for i, l in enumerate(content):
            nl = l
            if backend in l:
                ls = l.strip()
                if ls.startswith("#") and activate:
                    nl = ls[1:]
                elif not ls.startswith("#") and not activate:
                    nl = "#{0}".format(l)
            ncontent.append(nl)
        changed = content != ncontent
        if changed:
            self.write_conf(ncontent)
        return content, ncontent, changed

    def attach(self, backend):
        content, ncontent, changed = self.toggle(backend, activate=True)
        return content, ncontent, changed

    def detach(self, backend):
        content, ncontent, changed = self.toggle(backend, activate=False)
        return content, ncontent, changed


class GDocker(object):
    def __init__(self, *a, **kw):
        self.api = docker.from_env()
        # ensure docker connection is working
        self.api.ping()

    def get_containers(self, filter=True, all=True):
        ret = {}
        for a in self.api.containers(all=all):
            k = a["Names"][0]
            if filter and not compose_container.search(k):
                continue
            ret[k] = a
        return ret

    def get_ct(self, pat):
        ct = self.get_containers()
        for c in ct:
            if pat in c:
                return ct[c]

    def get_yang(self):
        return self.get_ct("yang")

    def get_ying(self):
        return self.get_ct("ying")

    def logs(self, backend):
        return self.api.logs(self.get_ct(backend)["Id"])

    def start(self, backend):
        return self.api.start(self.get_ct(backend)["Id"])

    def stop(self, backend, timeout=0):
        return self.api.stop(self.get_ct(backend)["Id"], timeout=timeout)

    def sync_data(self, orig="yang", dest="ying"):
        ret = None
        if (
            orig != dest
            and orig in ["yang", "ying"]
            and dest in ["yang", "ying"]
        ):
            log.info("Syncing {0} -> {1}".format(orig, dest))
            cmd = "rsync -av /{0}/ /{1}/".format(orig, dest)
            ret = subprocess.check_output(cmd, shell=True)
        return ret

    def list_data(self, backend):
        ps = u""
        for fpbf in PBFS.split():
            pbf = os.path.basename(fpbf)
            name = ".pbf".join(pbf.split(".pbf")[:-1])
            cmd = "ls -1 /{0}/{1}* 2>/dev/null || /bin/true".format(
                backend, name
            )
            ret = subprocess.check_output(cmd, shell=True)
            ps += ret.decode("utf-8")
        return ps

    def cleanup_data(self, backend):
        log.info("Cleaning {0}".format(backend))
        ps = u""
        for fpbf in PBFS.split():
            pbf = os.path.basename(fpbf)
            ps = [os.path.join("/ying", pbf), os.path.join("/yang", pbf)]
            assert True in [os.path.exists(p) for p in ps]
            name = ".pbf".join(pbf.split(".pbf")[:-1])
            cmd = "rm -rvf /{0}/{1}*".format(backend, name)
            ret = subprocess.check_output(cmd, shell=True)
            ps += ret.decode("utf-8")
        log.info("Cleaned {0}".format(backend))
        return ps

    def wipe(self, backend):
        log.info("Wiping {0}".format(backend))
        self.stop(backend)
        self.cleanup_data(backend)
        self.start(backend)
        log.info("Wiped {0}".format(backend))


class GraphHopperController(object):
    def __init__(
        self,
        states=None,
        tk=None,
        gdocker=None,
        check_interval=CHECK_INTERVAL,
        timeout=CACHE_BACKEND_TIMEOUT,
        *a,
        **kw
    ):
        if tk is None:
            tk = TraefikController(*a, **kw)
        if gdocker is None:
            gdocker = GDocker(*a, **kw)
        if states is None:
            states = States.load(*a, **kw)
        self.tk = tk
        self.states = states
        self.gdocker = gdocker
        self.timeout = timeout
        self.check_interval = check_interval
        self.start = None

    @property
    def expired(self):
        ret = None
        if self.start:
            ret = self.start + timedelta(seconds=self.timeout)
        return ret

    def is_ready(self, backend):
        gdocker = self.gdocker
        logs = gdocker.logs(backend).decode("utf-8").splitlines()
        logs.reverse()
        started_pat = "org.eclipse.jetty.server.Server - Started "
        stopped_pat = "org.eclipse.jetty.server.Server - Stopped "
        ret = False
        started = None
        for line in logs:
            if stopped_pat in line:
                started = False
                break
            if started_pat in line:
                started = True
                break
        if started:
            ghost = "graphhopper-{0}".format(backend)
            try:
                req = requests.get(
                    "http://{0}:8989/maps/".format(ghost), timeout=10
                )
                rst = req.status_code == 200
                complete = "<html>" in req.text
                if rst and complete:
                    ret = True
            except requests.exceptions.ReadTimeout:
                pass
            except requests.exceptions.ConnectionError:
                pass
        return ret

    def is_data_ok(self, backend):
        ret = False
        for fpbf in PBFS.split():
            pbf = os.path.basename(fpbf)
            name = ".pbf".join(pbf.split(".pbf")[:-1])
            rpbf = "/{0}/{1}".format(backend, pbf)
            gh_dir = "/{0}/{1}-gh/properties".format(backend, name)
            if os.path.exists(rpbf) and os.path.exists(gh_dir):
                ret = True
        return ret

    def may_trigger(self):
        if self.start is None:
            return self.reset()

    def reset(self):
        self.start = datetime.now()
        return self.start

    def check_timeout(self):
        time.sleep(3)
        now = datetime.now()
        if (
            (self.states.status not in ["OK"])
            and (self.start is not None)
            and (self.expired <= now)
        ):
            raise UpdateTimeoutError("Updating data did not finish in time")

    def wait_ready(self, backend, to_sync=False):
        while True:
            self.check_timeout()
            if self.is_ready(backend):
                log.info("Ready: {0}".format(backend))
                break
            else:
                time.sleep(self.check_interval)

    def reconstruct(self, backend):
        log.info("Reconstructing {0}".format(backend))
        self.gdocker.wipe(backend)
        self.reset()
        self.states.write_switch("UPGRADING")
        self.gdocker.start(backend)
        log.info("Restarted {0}".format(backend))

    def run_loop(self):
        gdocker = self.gdocker
        tk = self.tk
        states = self.states
        now = datetime.now()
        if states.status == "FAILED":
            self.gdocker.wipe("yang")
            self.states.write_switch("STALE")
        if states.status == "OK":
            expired = now
            if self.states.last_ok:
                expired = self.states.last_ok + timedelta(
                    seconds=CACHE_BACKEND_EXPIRY
                )
            if expired < now:
                self.states.write_switch("STALE")
            else:
                raise FinishedUpdateError("Routing data is up to date, skip")
        if states.status == "STALE":
            self.may_trigger()
            tk.detach("yang")
            self.states.write_switch("TO_UPGRADE")
        sync = False
        if states.status == "TO_UPGRADE":
            self.reconstruct("yang")
            sync = True
        self.wait_ready("yang")
        if states.status == "UPGRADING":
            sync = True
        tk.attach("yang")
        if sync:
            self.states.write_switch("TO_SYNC")
        if self.states.status == "TO_SYNC":
            tk.detach("ying")
            gdocker.stop("ying")
            gdocker.sync_data("yang", "ying")
            gdocker.start("ying")
            self.wait_ready("ying")
            tk.attach("ying")
            log.info("Ying should be up & ready")
            self.states.write_switch("OK")

    def loop(self):
        while True:
            try:
                log.info("(RE)start")
                self.run_loop()
            except KeyboardInterrupt:
                raise
            except (FinishedUpdateError,) as exc:
                log.info(exc)
                time.sleep(60)
                # reload states
                self.states = States.load()
            except:  # noqa
                self.states.write_switch("FAILED")
                trace = traceback.format_exc()
                report_err(SENTRY_URL, trace)
                time.sleep(15)


def main(*a, **kw):
    logging.basicConfig(format=LOG_FORMAT)
    log.setLevel(logging.DEBUG)
    while True:
        try:
            GraphHopperController(*a, **kw).loop()
        except KeyboardInterrupt:
            raise
        except:  # noqa
            trace = traceback.format_exc()
            report_err(SENTRY_URL, trace)


if __name__ == "__main__":
    main()
# vim:set et sts=4 ts=4 tw=80:
