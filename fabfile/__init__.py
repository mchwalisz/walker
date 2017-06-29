import time
from fabric.api import *
from fabric.exceptions import CommandTimeout
import config  # noqa
import wifi  # noqa
from config import set_hosts  # noqa


@task()
def node_info():
    with settings(warn_only=True):
        run('cat /etc/twistprotected')


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


def run():
    pass
    # reserve nodes
    # get the full list of nodes
    # for each pair
        # first node as AP
        # second node as client (connect)
        # check connection
        # iperf
        # remove interfaces on both
