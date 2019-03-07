# How to execute tests ?

- in ``.env``

    ```
    # Use a smaller zone to speed up tests, eg:
    GRAPHHOPPER_PBFS=/data/europe_france_mayotte.pbf
    ```
- Start the stack and let the graphhopper construct once them,
  and be completly running.

    ```
    docker-compose  -f docker-compose.yml -f docker-compose-prod.yml \
    -p "graphhopper-fr" run --rm -w /switcher  lbswitcher bash
    # then
    pytest [args]
    ```


 
```

def loop(states):
    start = now()
    while True:
        if status == FAILED
            writeSwitch state to STALE
        elif status == OK
            print("Routing data is up to date, skip")
            break
        elif status == STALE
            cut yang from loadbalancer
            remove PBF & data
            writeSwitch the state last_status to TO_UPGRADE
        elif status == TO_UPGRADE
            dettach yang from lb
            remove yang PBF to force refresh
            restart yang after refresh
            grep logs waiting for motif
            writeSwitch state to UPGRADING
        elif status == UPGRADING
            while not timeout:
                parse logs, and check for ready
                if timeout:
                    raise Exception(UpdateTimeoutERROR)
                if backend ready:
                    ensure is_updated:
                        -> data is ok
                        -> curl backend is ok
                if error
                    raise Exception(UpdateERROR)
                else
                    writeSwitch the state last_status to TO_SYNC
        elif status == TO_SYNC
            deattach ying
            stop ying
            sync ying data from yang
            start ying
            wait ying ready
            attach ying to lb
            self.reset (self.start = now)
            state.states["last_ok"] = self.start
            writeSwitch the state last_status to OK

while True:
    try:
        loop(states)
    except Exception as exc:
        writeSwitch state to FAILED
        report_err(trace)
```

## JVM Opts timings
see [here](https://gist.github.com/svanoort/66a766ea68781140b108f465be45ff00#file-gcsettings-sh-L12)
```
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g  -XX:MetaspaceSize=100M: 41s
JAVA_OPTS=-server -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=100M: 18s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=100M: 32s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=256M -XX:MaxMetaspaceSize=512M: 21s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=256M -XX:MaxMetaspaceSize=512M: 10s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=1024M: 9s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=1024M -XX:+UseStringDeduplication: 8.5s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=1024M -XX:+UseStringDeduplication -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=20 : 8.5s
JAVA_OPTS=-server -Xconcurrentio -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=1024M -XX:+UseStringDeduplication -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=20 -XX:+ParallelRefProcEnabled: 8.5s
JAVA_OPTS=-server -Xmx28g -Xms28g -XX:+UseG1GC -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=1024M -XX:+UseStringDeduplication -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=20  -XX:+ParallelRefProcEnabled -XX:+ExplicitGCInvokesConcurrent -XX:MaxMetaspaceExpansion=64M: 8.5

```

## Cmd in vrac
- Reconfigure loadbal

