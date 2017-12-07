#!/usr/bin/env python

import click
import measurement
import wifi

from fabric import SerialGroup
from pprint import pprint


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

    for ap, stations in select_one(grp):
        wifi.create_ap(ap, phy='03:00', ssid='exp1', channel=1)
        measurement.iperf_server(ap)
        for sta in stations:
            print(f'AP: {ap.host} STA: {sta.host}')
            try:
                wifi.connect(sta, phy='03:00', ssid='exp1')
            except EnvironmentError as e:
                continue
            print(measurement.iperf_client(sta, duration=5))


if __name__ == '__main__':
    cli()
