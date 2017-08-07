#!/usr/bin/env python

from datetime import datetime
from itertools import product
import click
import pandas as pd
import tqdm
from fabric.api import *
import fabfile as tasks

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True)
@click.version_option('v0.1.0')
def cli(verbose):
    # click.echo('Verbosity: %s' % verbose)
    pass


@cli.command('speed_test', short_help='iperf between two Wi-Fi nodes')
@click.option('--ap', '-a',
    default='tplink01', show_default=True,
    help='Hostname for AP')
@click.option('--sta', '-s',
    default='nuc5', show_default=True,
    help='Hostname for STA')
@click.option('--ssid',
    default='TSCH', show_default=True,
    help='Network name')
@click.option('--channel',
    default=11, type=int, show_default=True,
    help='Network name')
@click.option('--duration', '-t',
    default=20, type=int, show_default=True,
    help='Iperf duration')
@click.option('--setup/--no-setup',
    default=True, show_default=True,
    help='Setup networks')
@click.option('--teardown/--no-teardown',
    default=False, show_default=True,
    help='Tear down networks')
def speed_test(ap, sta, ssid, channel, duration, setup, teardown):
    """Measures throughput between AP and STA with iperf"""
    apip = '10.100.1.1'

    if setup:
        execute(tasks.wifi.ifaces_clean, hosts=[ap, sta])
        # phys = execute(wifi.phys_get, hosts=[ap, sta])
        execute(tasks.wifi.create_ap,
            channel=channel,
            hw_mode='g' if channel < 13 else 'n',
            ssid=ssid,
            phy='phy0',
            ip=apip,
            hosts=[ap])
        execute(tasks.wifi.connect,
            phy='phy0',
            ssid=ssid,
            hosts=[sta])

    execute(tasks.iperf, server=True, hosts=[ap])
    result = execute(
        tasks.iperf,
        duration=duration,
        dest=apip, hosts=[sta])

    result[sta]['ap'] = ap
    result[sta]['sta'] = sta
    result[sta].to_csv(
        'data/speed_test_{}.csv'.format(
            datetime.now().isoformat()))
    print(result)

    if teardown:
        execute(tasks.iperf, clean=True, hosts=[ap, sta])
        execute(tasks.wifi.ifaces_clean, hosts=[ap, sta])


@cli.command('network_scan', short_help='Perform network scan between nodes')
@click.option('hosts', '--hosts', '-H',
    help='Node used for scanning, comma separated list')
@click.option('--show-all', '-a',
    default=False, is_flag=True,
    help='Output all scan results. False returns only own ssid')
def network_scan(hosts, show_all):
    hosts = hosts.split(',')
    # Make sure everything is cleaned up
    execute(tasks.wifi.ifaces_clean, hosts=hosts)
    phys = execute(tasks.wifi.phys_get, hosts=hosts)
    execute(tasks.wifi.ifaces_create, types_=('managed',), hosts=hosts)

    data = pd.DataFrame()
    ssid = 'twist-test'
    t_ap = tqdm.tqdm(desc='AP',
        total=sum(map(lambda h: len(phys[h]), phys)) * 2)

    for server in hosts:
        for phy, (channel, mode) in product(
                phys[server],
                zip([1, 48], ['g', 'a'])):
            t_ap.set_postfix(ap=server, phy=phy, channel=channel)
            t_ap.update(1)
            # Setup
            try:
                execute(tasks.wifi.create_ap,
                    channel=channel,
                    hw_mode=mode,
                    ssid=ssid,
                    phy=phy,
                    hosts=[server])
            except tasks.wifi.FabricRunException:
                print("Cannot setup AP")
                continue
            # Experiment
            scan = execute(tasks.wifi.scan,
                hosts=[x for x in hosts if x != server])
            for scanner in scan:
                s = pd.DataFrame.from_dict(scan[scanner], orient='columns')
                if s.empty:
                    continue
                s.ix[s.ssid == ssid, 'ap'] = server
                s.ix[s.ssid == ssid, 'ap_dev'] = phy
                if show_all:
                    data = data.append(s, ignore_index=True)
                else:
                    data = data.append(s[s.ssid == ssid], ignore_index=True)
            # Tear down
            execute(tasks.wifi.ifaces_clean, hosts=[server])
            execute(tasks.wifi.ifaces_create,
                types_=('managed',), hosts=[server])
    data.to_csv('data/scan_{}.csv'.format(datetime.now().isoformat()))


if __name__ == '__main__':
    cli()
