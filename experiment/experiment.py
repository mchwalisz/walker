#!/usr/bin/env python

import click
import wifi

from fabric import Connection
from fabric import SerialGroup
from pprint import pprint


@click.group(
    context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-v', '--verbose', count=True)
@click.version_option('v0.1.0')
def cli(verbose):
    # click.echo('Verbosity: %s' % verbose)
    pass


@cli.command(short_help="Run experiment")
def run():
    hosts = ['nuc4', 'nuc10', 'nuc12']
    grp = SerialGroup(*hosts)
    ap = Connection(hosts[0])
    stations = SerialGroup(*hosts[1:])
    grp.run('uname -s -n -r')
    wifi.info(grp)

    wifi.create_ap(ap, phy='03:00', ssid='exp1', channel=1)
    for sta in stations:
        # wifi.connect(sta, phy='03:00', ssid='exp1')
        pprint(wifi.scan(sta, phy='03:00'))


if __name__ == '__main__':
    cli()
