import time
from datetime import datetime
# from itertools import permutations
from itertools import product
from fabric.api import *
from fabric.exceptions import CommandTimeout
from fabric.decorators import runs_once
import pandas as pd
import fabfile.config as config # noqa
import fabfile.wifi as wifi # noqa
from fabfile.config import set_hosts  # noqa
import tqdm


@task()
def node_info():
    with settings(warn_only=True):
        run('cat /etc/twistprotected')
        run('ip a')
        run('iw dev')


@task()
def iperf(server=False, dest=None):
    if server:
        with settings(warn_only=True), hide('warnings', 'stdout', 'stderr'):
            run('pkill iperf')
        run('nohup iperf -s -i 1 &', pty=False)
        return
    return run('iperf -i 1 -t 20 -c {}'.format(dest))


@task()
@runs_once
def full_scan():
    execute(wifi.ifaces_clean)
    phys = execute(wifi.phys_get)
    execute(wifi.ifaces_create, types_=('managed',))
    data = pd.DataFrame()
    ssid = 'twist-test'
    t_ap = tqdm.tqdm_gui(desc='AP',
        total=sum(map(lambda h: len(phys[h]), phys)) * 2)
    for server in env.hosts:
        for phy, (channel, mode) in product(
                phys[server],
                zip([1, 48], ['g', 'a'])):
            t_ap.set_description('AP {}'.format(server))
            t_ap.set_postfix(phy=phy, channel=channel)
            t_ap.update(1)
            # Setup
            try:
                execute(wifi.create_ap,
                    channel=channel,
                    hw_mode=mode,
                    ssid=ssid,
                    phy=phy,
                    hosts=[server])
            except wifi.FabricRunException:
                print("Cannot setup AP")
                continue
            # Experiment
            with settings(parallel=True, pool_size=10):
                scan = execute(wifi.scan,
                    hosts=[x for x in env.hosts if x != server])
            for scanner in scan:
                s = pd.DataFrame.from_dict(scan[scanner], orient='columns')
                if s.empty:
                    continue
                s.ix[s.ssid == ssid, 'ap'] = server
                s.ix[s.ssid == ssid, 'ap_dev'] = phy
                data = data.append(s, ignore_index=True)
            # Tear down
            execute(wifi.ifaces_clean, hosts=[server])
            execute(wifi.ifaces_create, types_=('managed',), hosts=[server])
    data.to_csv('data/scan_{}.csv'.format(datetime.now().isoformat()))
    print(data)


@task()
def check_reg():
    for reg in ['00', 'DE', 'US', 'EU']:
        sudo(f'iw reg set {reg}')
        run('iw phy'
            + ' | grep -e " MHz " -e "Wiphy"'
            + ' | grep -v -e "IR" -e "disabled"')
