import time
from itertools import permutations
from fabric.api import *
from fabric.exceptions import CommandTimeout
from fabric.decorators import runs_once
import fabfile.config as config # noqa
import fabfile.wifi as wifi # noqa
from fabfile.config import set_hosts  # noqa


@task()
def node_info():
    with settings(warn_only=True):
        run('cat /etc/twistprotected')
        run('ip a')
        run('iw dev')


@task()
@parallel()
def run_iperf():
    if env.hosts.index(env.host_string) == 0:
        try:
            run('iperf -s -i 1', timeout=15)
        except CommandTimeout:
            print('ending server')
    elif env.hosts.index(env.host_string) == 1:
        time.sleep(1)
        run('iperf -i 1 -t  10 -c {}'.format(env.hosts[0]))


@task()
@runs_once
def full_scan():
    with settings(parallel=True):
        execute(wifi.interfaces_create)
    for server in env.hosts:
        print("S: {}".format(server))
        # Setup
        execute(wifi.create_ap, hosts=[server])
        # Experiment
        execute(wifi.scan, hosts=[x for x in env.hosts if x != server])
        # Tear down
        execute(wifi.interfaces_create, hosts=[server])
