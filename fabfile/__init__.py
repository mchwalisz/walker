import time
# from itertools import permutations
from fabric.api import *
import pandas as pd
from io import StringIO
import fabfile.config as config # noqa
import fabfile.wifi as wifi # noqa
from fabfile.config import set_hosts  # noqa

env.shell = '/bin/sh -c'
env.pool_size = 5


@task
@parallel
def node_info():
    with settings(warn_only=True):
        run('cat /etc/twistprotected')
        run('ip a')
        run('iw dev')


@task
@serial
def iperf(duration=20, server=False, dest=None, clean=False):
    with settings(warn_only=True), hide('warnings', 'stdout', 'stderr'):
        run('pkill iperf')
    if clean:
        return
    if server:
        run('iperf -s -i 1 -D', pty=False)
        time.sleep(1)
        return
    raw = run('iperf -i 1 -t {} --reportstyle C -c {}'.format(
        duration, dest))
    columns = (
        'timestamp',
        'source_address',
        'source_port',
        'destination_address',
        'destination_port',
        'transfer_id',
        'interval',
        'transferred_bytes',
        'bits_per_second',
    )
    result = pd.read_csv(
        StringIO(raw),
        header=0,
        names=columns)
    return result


@task
def check_reg():
    for reg in ['00', 'DE', 'US', 'EU']:
        sudo(f'iw reg set {reg}')
        run('iw phy'
            + ' | grep -e " MHz " -e "Wiphy"'
            + ' | grep -v -e "IR" -e "disabled"')
