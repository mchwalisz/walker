#!/usr/bin/env python

import click
import measurement
import time
import wifi
import yaml

from fabric import SerialGroup
from fabric import Connection
from pathlib import Path
from pprint import pprint
from tqdm import tqdm

BASE_PATH = Path(__file__).parent / '..'


def select_one(param):
    for i in range(len(param)):
        cut = param[:]
        sel = cut.pop(i)
        yield sel, cut


@click.group(
    context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-v', '--verbose', count=True)
@click.version_option('v0.1.0')
def cli(verbose):
    # click.echo('Verbosity: %s' % verbose)
    pass


@cli.command(short_help="Scan for networks")
def scan():
    hosts = ['nuc4', 'nuc10', 'nuc12']
    grp = SerialGroup(*hosts)

    for sta in grp:
        pprint(wifi.scan(sta, phy='03:00'))


@cli.command(short_help="Run experiment")
@click.option('--duration', '-d',
    default=60,
    help='Iperf3 measurement duration')
def run(duration):
    with (BASE_PATH / 'node_selection' / 'hosts').open('r') as stream:
        config = yaml.load(stream)
    hosts = list(config['nuc']['hosts'].keys())
    phy = '03:00'
    grp = SerialGroup(*hosts)
    grp.run('uname -s -n -r')
    wifi.info(grp)
    data_folder = Path.cwd() / 'data' / time.strftime("%Y-%m-%d-%H%M%S")
    data_folder.mkdir()
    for host in grp:
        wifi.phy_clean(host)

    pbar_ap = tqdm(select_one(grp), total=len(grp))
    for ap, stations in pbar_ap:
        pbar_ap.set_description(f'AP {ap.host}')

        # Create AP
        wifi.create_ap(ap, phy=phy, ssid='exp1', channel=11)
        measurement.iperf_server(ap)

        pbar_sta = tqdm(stations)
        for sta in pbar_sta:
            pbar_sta.set_description(f'STA {sta.host}')
            # Connect and measure
            try:
                wifi.connect(sta, phy=phy, ssid='exp1')
            except EnvironmentError as e:
                continue
            result = measurement.iperf_client(sta, duration=duration)

            # Collect measurement
            result_path = data_folder / f'{ap.host}-{sta.host}.json'
            with result_path.open('w') as f:
                f.write(result.stdout)

            wifi.phy_clean(sta, phy=phy)


if __name__ == '__main__':
    cli()
