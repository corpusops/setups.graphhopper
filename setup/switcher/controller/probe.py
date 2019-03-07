#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import os
import sys
import traceback
import argparse

from controller import main as _c

re_flags = _c.re_flags


class Check(object):
    def __init__(self, *a, **kw):
        self._program = "graphhopper_lag_checks"
        self._author = "Mathieu Le Marec - Pasquet (kiorky)"
        self._nick = self._program.replace("check_", "")
        self._ok = 0
        self._warning = 1
        self._critical = 2
        self._unknown = 3
        self.parser = None
        self.args = None
        self.options = None
        self.c = _c.GraphHopperController(*a, **kw)
        self.states = self.c.states
        self.docker = self.c.gdocker

    def compute_perfdata(self, force=True):
        if force or not self._perfdata:
            self._perfdata += "test=1"
        return self._perfdata

    def exit(self, code, msg="", perfdata=None):
        if perfdata:
            msg += "|{0}".format(perfdata.strip())
        if msg:
            print(msg)
        sys.exit(code)

    def critical(self, msg="", perfdata=None):
        msg = "{0} CRITICAL - {1}".format(self._nick, msg)
        self.exit(self._critical, msg=msg, perfdata=perfdata)

    def warning(self, msg="", perfdata=None):
        msg = "{0} WARNING - {1}".format(self._nick, msg)
        self.exit(self._warning, msg=msg, perfdata=perfdata)

    def unknown(self, msg="", perfdata=None):
        msg = "{0} UNKNOWN - {1}".format(self._nick, msg)
        self.exit(self._unknown, msg=msg, perfdata=perfdata)

    def ok(self, msg="", perfdata=None):
        msg = "{0} OK - {1}".format(self._nick, msg)
        self.exit(self._ok, msg=msg, perfdata=perfdata)

    def opt_parser(self):
        dlag = int(os.environ.get('GRAPHHOPPER_CACHE_BACKEND_EXPIRY',
                                  60 * 60 * 7))
        parser = self.parser = argparse.ArgumentParser(
            prog=self._program, description=("Check Graphhopper lag state")
        )
        parser.add_argument(
            "--lag-max",
            default=dlag,
            const=dlag,
            type=str,
            nargs="?",
            dest="lag",
            help="lag trigger",
        )
        parser.add_argument(
            "--warning",
            default=1.8 * dlag,
            const=1.8 * dlag,
            type=str,
            nargs="?",
            dest="wlag",
            help="warning lag trigger",
        )
        parser.add_argument(
            "--critical",
            default=2.2 * dlag,
            const=2.2 * dlag,
            type=float,
            nargs="?",
            dest="clag",
            help="critical lag trigger",
        )
        self.args = vars(parser.parse_args())

    def run(self):
        method = self.unknown
        counters = {}
        lag = 0
        self.opt_parser()
        lo = self.states.last_ok
        counters['last_ok'] = int(lo.timestamp())
        msg = 'no last_ok status found'
        if lo:
            lag = int(datetime.now().timestamp() - lo.timestamp())
            nolag = not lag
            if lag:
                if lag >= self.args['wlag']:
                    method = self.warning
                    msg = 'graphhopper data is a bit stale'
                elif lag >= self.args['clag']:
                    method = self.critical
                    msg = 'graphhopper data is very stale'
                else:
                    nolag = True
            if nolag:
                method = self.ok
                msg = 'graphhopper data is fresh'
        counters['lag'] = lag
        perfdata = ""
        for i, val in counters.items():
            perfdata += " {0}={1}".format(i, val)
        method(msg, perfdata=perfdata)


def main():
    try:
        check = Check()
        check.run()
    except (Exception,) as e:
        trace = traceback.format_exc()
        print("Unknown error UNKNOW - {0}".format(e))
        print(trace)
        sys.exit(3)


if __name__ == "__main__":
    main()
