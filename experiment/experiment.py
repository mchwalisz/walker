#!/usr/bin/env python

import click
import measurement
import kernel
import time
import wifi
import yaml
import logging

from fabric import SerialGroup
from fabric import Connection
from pathlib import Path
from pprint import pprint
from tqdm import tqdm

BASE_PATH = Path(__file__).parent / '..'
log = logging.getLogger('exp')


def select_one(param):
    for i in range(len(param)):
        cut = param[:]
        sel = cut.pop(i)
        yield sel, cut


@click.group(
    context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-v', '--verbose', count=True,
    help='Increase log verbosity level (up to 4)')
@click.version_option('v0.2.0')
def cli(verbose):
    level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}
    if verbose < 3:
        log.setLevel(level[verbose])
        verbose = 0
    elif verbose == 3:
        log.setLevel(level[2])
        verbose = 1
    else:
        verbose = 2
    logging.basicConfig(
        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
        level=level[verbose])


@cli.command(short_help="Scan for networks")
def scan():
    hosts = ['nuc4', 'nuc10', 'nuc12']
    grp = SerialGroup(*hosts)

    for sta in grp:
        pprint(wifi.scan(sta, phy='03:00'))


@cli.command(short_help="Run short test between two nodes")
@click.option('--duration', '-d',
    default=60,
    help='Iperf3 measurement duration')
@click.option('--access-point', '-a',
    default='nuc4',
    help='Host to act as Access Point and iperf3 server')
@click.option('--client', '-c',
    default='nuc10',
    help='Host to act as Wi-Fi and iperf3 client')
@click.option('--traffic', '-t',
    type=click.Choice(['udp', 'tcp']),
    default='udp',
    help='Choose traffic type')
def short(duration, access_point, client, traffic):
    gateway = Connection(
        'api.twist.tu-berlin.de',
        user='proxyuser',
        port=2222,
    )
    ap = Connection(access_point, gateway=gateway)
    sta = Connection(client, gateway=gateway)
    phy = '02:00'
    channel = 11

    for host in [ap, sta]:
        wifi.phy_clean(host)
        measurement.iperf_kill(host)

    data_folder = Path.cwd() / 'data' / 'short'
    if not data_folder.exists():
        data_folder.mkdir(parents=True)

    log.info(f'Create AP on {ap.host}')
    wifi.create_ap(ap, phy=phy, ssid='exp1', channel=channel)
    measurement.iperf_server(ap)

    log.info(f'Connect to AP from {sta.host}')
    wifi.connect(sta, phy=phy, ssid='exp1')
    log.info(f'Measure for {duration} sec')
    result = measurement.iperf_client(sta,
        duration=duration,
        traffic=traffic,
        title=f'ap:{ap.host},sta:{sta.host},channel:{channel}')

    result_path = data_folder.joinpath(
        f'{time.strftime("%Y-%m-%d-%H%M%S")}-{ap.host}-{sta.host}.json')
    log.info(f'Collect measurements to {result_path}')
    with result_path.open('w') as f:
        f.write(result.stdout)

    for host in [ap, sta]:
        wifi.phy_clean(host)
        measurement.iperf_kill(host)


@cli.command(short_help="Run experiment")
@click.option('--duration', '-d',
    default=60,
    help='Iperf3 measurement duration')
def run(duration):
    with (BASE_PATH / 'node_selection' / 'hosts').open('r') as stream:
        config = yaml.load(stream)
    hosts = list(config['nuc']['hosts'].keys())
    phy = '03:00'
    log.info(f'Node info')
    grp = SerialGroup(*hosts)
    grp.run('uname -s -n -r')
    wifi.info(grp)
    data_folder = Path.cwd() / 'data' / time.strftime("%Y-%m-%d-%H%M%S")
    data_folder.mkdir()
    log.info(f'Storing measurements in {data_folder}')
    for host in grp:
        wifi.phy_clean(host)
        measurement.iperf_kill(host)

    pbar_ap = tqdm(select_one(grp), total=len(grp), dynamic_ncols=True)
    for ap, stations in pbar_ap:
        pbar_ap.set_description(f'AP {ap.host}')

        # Create AP
        wifi.create_ap(ap, phy=phy, ssid='exp1', channel=11)
        measurement.iperf_server(ap)

        pbar_sta = tqdm(stations, dynamic_ncols=True)
        for sta in pbar_sta:
            pbar_sta.set_description(f'STA {sta.host}')
            # Connect and measure
            try:
                wifi.connect(sta, phy=phy, ssid='exp1')
            except EnvironmentError as e:
                wifi.phy_clean(sta, phy=phy)
                log.warning(f'Could not connect {sta.host} to {ap.host}')
                continue
            result = measurement.iperf_client(sta,
                duration=duration,
                title=f'AP {ap.host} STA {sta.host} using phy {phy}')

            # Collect measurement
            result_path = data_folder / f'{ap.host}-{sta.host}.json'
            with result_path.open('w') as f:
                f.write(result.stdout)

            wifi.phy_clean(sta, phy=phy)

        wifi.phy_clean(ap, phy=phy)
        measurement.iperf_kill(ap)


@cli.command(short_help="Run full experiment with switching kernels")
@click.option('--duration', '-d',
    default=60,
    help='Iperf3 measurement duration')
def full(duration):
    nuc = Connection('nuc11')
    possible_kernels = kernel.kernels(nuc)
    print(possible_kernels)
    kernel.switch(nuc, possible_kernels[-2].release)


if __name__ == '__main__':
    cli()
