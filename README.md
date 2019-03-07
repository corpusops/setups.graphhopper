# Initialise your development environment

- Idea is to have a pair of two graphhoppers (ying/yang) running the same configuration balanced using a loadbalancer.
- Every once and then, a colocated daemon will detach one of the daemons and refresh the routing from the OSM last extract and then refresh the first (ying) instance upon termination.


## First clone
```sh
git clone --recursive https://github.com/corpusops/setups.graphhopper.git
```

## Install docker and docker compose
if you are under debian/ubuntu/mint/centos you can do the following:

```sh
.ansible/scripts/download_corpusops.sh
.ansible/scripts/setup_corpusops.sh
local/*/bin/cops_apply_role --become \
    local/*/*/corpusops.roles/services_virt_docker/role.yml
```

... or follow official procedures for
  [docker](https://docs.docker.com/install/#releases) and
  [docker-compose](https://docs.docker.com/compose/install/).


## Update corpusops
You may have to update corpusops time to time with
￼
```
./control.sh up_corpusops
```

## Doc for deployment on environments
- [See here](./docs/deploy.md)

## update cron pseudo code

- GRAPHHOPPER_CACHE_BACKEND_EXPIRY=604800 # world (weekly)
- GRAPHHOPPER_CACHE_BACKEND_EXPIRY=86400  # europe (daily)
- GRAPHHOPPER_CACHE_BACKEND_EXPIRY=43200  # france (halfdaily)
- On garde un fichier json minimaliste pour garder un etat des executions
ancers from loadbalancers themselves
```
.ansible/scripts/call_ansible.sh -vvvvv .ansible/playbooks/lb.yml -e "{lb_servers: prod_loc-lb, graphhopper_servers: prod_loc-graphhopper}"
```

## Switcher docs
. [docs](./switcher/controller/README.md)


