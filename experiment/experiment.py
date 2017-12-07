#!/usr/bin/env python

import click
import measurement
import time
import wifi

from fabric import SerialGroup
from pathlib import Path
from pprint import pprint
from tqdm import tqdm


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
def run():
    hosts = ['nuc4', 'nuc10', 'nuc12']
    grp = SerialGroup(*hosts)
    grp.run('uname -s -n -r')
    wifi.info(grp)
    data_folder = Path.cwd() / 'data' / time.strftime("%Y-%m-%d-%H%M%S")
    data_folder.mkdir()

    pbar_ap = tqdm(select_one(grp), total=len(grp))
    for ap, stations in pbar_ap:
        pbar_ap.set_description(f'AP {ap.host}')
        wifi.create_ap(ap, phy='03:00', ssid='exp1', channel=1)
        measurement.iperf_server(ap)
        pbar_sta = tqdm(stations)
        for sta in pbar_sta:
            pbar_sta.set_description(f'STA {sta.host}')
            try:
                wifi.connect(sta, phy='03:00', ssid='exp1')
            except EnvironmentError as e:
                continue
            result = measurement.iperf_client(sta, duration=5)

            result_path = data_folder / f'{ap.host}-{sta.host}.json'
            with result_path.open('w') as f:
                f.write(result.stdout)


if __name__ == '__main__':
    cli()
