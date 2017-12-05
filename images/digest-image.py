#!/usr/bin/env python

import os
import boto3
import requests
import jinja2
import yaml
import sys

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def upload_aws(filename):

    s3 = boto3.client('s3')

    bucket = "twistimages"
    key = "image.tgz"

    s3.upload_file(filename, bucket, key, ExtraArgs={'ACL': 'public-read'})

    return(f"https://s3.eu-central-1.amazonaws.com/{bucket}/{key}")


def render_rspec(image_url):

    with open(os.path.join(BASE_PATH, 'rspecs', 'nodes.yml'), 'r') as stream:
        node_spec = yaml.load(stream)

    nodes = list()
    for node_type in node_spec:
        for node_name in node_spec[node_type]:
            node = {'name': node_name, 'type': node_type}
            if(node_type == 'nuc'):
                node['disk_image'] = image_url
            nodes.append(node)

    rspec = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                os.path.join(BASE_PATH, 'rspecs'))).get_template('rspec.jn2')

    output = rspec.render({'nodes': nodes})

    with open(os.path.join(BASE_PATH, 'rspecs', 'rendered.rspec'), 'w') as f:
        f.write(output)


if __name__ == "__main__":
    if(len(sys.argv) == 1):
        filename = "image.tgz"
    else:
        filename = sys.argv[1]

    image_url = upload_aws(filename)
    render_rspec(image_url)
