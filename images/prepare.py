#!/usr/bin/env python

import os
import jinja2
import yaml
import sys
import tempfile
import invoke
import click
import awss3 as cloudstorage

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def __build(diskimage, release):

    print(f'Creating "{diskimage}"..')

    sources_tmpl = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                os.path.dirname(__file__))).get_template('sources.list.jn2')

    sources_rendered = sources_tmpl.render({'release': release})

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as outfile:
        outfile.write(sources_rendered)
        sources_filename = outfile.name

    print(f'sources.list rendered to {sources_filename}')

    cmd = (
            "sudo -E bash -c '"
            "disk-image-create ubuntu-squashfs twist"
            f" -t tgz -o {diskimage}'"
          )
    try:
        invoke.run(cmd,
                   env={
                        'DIB_APT_SOURCES': sources_filename,
                        'DIB_RELEASE': release,
                        'ELEMENTS_PATH': os.path.join(
                                os.path.dirname(__file__), 'add_elements')
                       })
    finally:
        os.unlink(sources_filename)

    print(f'Done creating "{diskimage}"')


def __upload(diskimage):
    print(f'Uploading {diskimage} to cloud storage..')
    url = cloudstorage.upload(diskimage, 'static')
    print(f'Uploaded {diskimage} to cloud storage. URL: {url}')
    return(url)


def __render_rspec(url):
    with open(os.path.join(BASE_PATH, 'rspecs', 'nodes.yml'), 'r') as stream:
        node_spec = yaml.load(stream)

    nodes = list()
    for node_type in node_spec:
        for node_name in node_spec[node_type]:
            node = {
                    'name': node_name,
                    'type': node_type,
                    'disk_image': url
                    }
            nodes.append(node)

    rspec = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                os.path.join(BASE_PATH, 'rspecs'))).get_template('rspec.jn2')

    output = rspec.render({'nodes': nodes})

    rspec_path = os.path.join(BASE_PATH, 'rspecs', 'rendered.rspec')
    with open(rspec_path, 'w') as f:
        f.write(output)

    print(f'Rspec written to {rspec_path}')


@click.group(invoke_without_command=True)
@click.option('--diskimage', default='image.tgz',
              help='Filename for diskimage')
@click.option('--release', default='artful', help='Ubuntu release codename')
@click.pass_context
def cli(ctx, diskimage, release):
    if ctx.invoked_subcommand is None:
        __build(diskimage, release)
        url = __upload(diskimage)
        __render_rspec(url)
    else:
        ctx.obj['diskimage'] = diskimage
        ctx.obj['release'] = release


@cli.command()
@click.pass_context
def build(ctx):
    __build(ctx.obj['diskimage'], ctx.obj['release'])


@cli.command()
@click.pass_context
def upload(ctx):
    __upload(ctx.obj['diskimage'])


@cli.command()
@click.option('--url',
              help='diskimage URL to bake into rspec')
def render_rspec(url):
    __render_rspec(url)


if __name__ == '__main__':
    cli(obj={})
