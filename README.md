# WaLKER - Wifi Linux Kernel ExpeRiment

Perform a full mesh measurements of the interference and throughput between all WiFi nodes deployed in TWIST testbed in TKN building.

It is helpful to know the channel quality between each pair of nodes in a testbed.
There can, of course, be interference on the channel and this can change over time.
We have to keep in mind that the measurement of the channel quality is only one of the approaches.
But even this approach can be helpful to understand happenings on the channel.
It is a good idea to measure the throughput between a pair of nodes to get an indication of the channel quality.

All nodes of the testbed operate in the 2.4 GHz and in the 5 GHz band.
The goal of the experiment is to measure the channel quality between all pair of nodes by its throughput.
This measurement should be done twice: once in the 2.4GHz and in the 5GHz band.

Other experimenters can modify this script for their own experiment.
To enable them to do this a documentation of the script is needed.

## Installation

We leverage Python 3.6 tools in the whole experiment.
We use [pipenv](https://docs.pipenv.org/index.html) as a packaging tool.
Please install it first with:

```bash
$ pip install pipenv
```

To bootstrap new virtual environment enter the project directory and run:

```bash
pipenv
```

## Usage
### Node selection

The nodes that are used in the experiment are listed in one [YAML](https://www.yaml.org) file under `node_selection/hosts`. The file is a valid [ansible inventory](http://docs.ansible.com/ansible/latest/intro_inventory.html) hosts file and is used in multiple stages throughout the experiment.
In the same directory, you'll find a [Jinja2](http://jinja.pocoo.org/docs/2.10/) template for a request [RSpec](http://groups.geni.net/geni/wiki/GENIExperimenter/RSpecs), that will be used to request node reservation later on. There are also two pre-rendered RSpec files `rendered.rspec` and `rendered_small.rspec`, which can be used as-is to reserve the corresponding nodes.

### OS image preparation

This stage consists of three essential steps:

1. Building the disk image
2. Uploading the image
3. Rendering the RSpec with the corresponding link to the image

The three steps are conveniently wrapped in one script `images/preparation/prepare.py`. To display available commands and options use
```bash
./prepare.py --help
```
You can build a xenial image with additional linux kernels `v3.18.87` and `v4.14.5`, upload it to an [Amazon S3](https://aws.amazon.com/s3/?nc1=h_ls) bucket and render the corresponding RSpec with

```bash
./prepare.py
```

Note that you will need to setup an AWS bucket and provide your credentials. You will find the resulting RSpec under `node_selection/rendered.rspec`. Use this file to request reservation at the testbed (see TODO).

The following three paragraphs give a more detailed description of the process

#### Building the disk image

We use openstack's [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/) to build a ready-to-use ubuntu disk image, which can be flashed and booted on the nodes. We add two elements to customize the image according to our needs: `images/add_elements/twist` installs python3 into the image and allows to use a customized `sources.list` file, which is rendered from the template under `images/sources.list.jn2` and can be modified to include additional repositories for aptitude. The `images/add_elements/mainline-kernel` element allows to install user-defined mainline kernels into the image. The corresponding `.deb` packages are automatically downloaded and installed during image creation.

This functionality is provided by the `build` command of the `prepare.py` script:

```bash
./prepare.py --release xenial --diskimage myimage.tgz --kernel 4.14.5 --kernel 3.18.87 build
```

#### Uploading the image

In order to deploy the image to the nodes, the testbed management software of `TWIST` must be able to fetch the image from an http server. As an example, we use an [Amazon S3](https://aws.amazon.com/s3/?nc1=h_ls) bucket to upload the file and generate a publicly available URL, from which the image can be fetched. The corresponding code can be found in `images/awss3.py`. Note that you need to setup the `twistimages` bucket and provide your `AWS` credentials in order to use this script. You are encouraged to use your own cloud storage or self-hosted web server to provide the image.

Use the following command to upload your exisiting image `myimage.tgz` to the cloud. It will output the resulting URL, which you can use to render the RSpec

```bash
./prepare.py --diskimage myimage.tgz upload
```

#### Rendering the RSpec

Now that we have uploaded the image and can provide a URL, the RSpec can be rendered using the hosts file under `node_selection/hosts` and the previously mentioned request template under `node_selection/rspec.jn2`.

Use the following command to render the RSpec for the experiment, using the URL to your uploaded image:

```bash
./prepare.py render_rspec --url http://myserver/myimage.tgz
```

### OS image deployment

#### Using SFA testbed

At this point, we can request reservation of the corresponding nodes at the testbed using the previously generated RSpec file. The reservation consists of three consecutive steps:

1. Allocation - Claim exclusive access to the nodes for the time of the experiment
2. Provisioning - Prepare the nodes for the experiment by flashing the disk image and allowing remote access
3. Starting - Boot the disk image, allowing you to login to the nodes by ssh

[jFed](http://jfed.iminds.be/) is a Java-based framework for node management in federated testbeds. It offers a GUI for defining the resources used in an experiment, but also allows to use existing RSpec files to reserve nodes from a range of federated testbeds. Refer to the official instructions for [getting started](http://jfed.iminds.be/get_started/) and [creating a first experiment](http://doc.ilabt.iminds.be/jfed-documentation-5.7/firstexperiment.html).

We recommend [omni](https://github.com/GENI-NSF/geni-tools/wiki/Omni) as a python-based CLI alternative to jFed. Follow the official [instructions](https://github.com/GENI-NSF/geni-tools/wiki/Omni) for getting started and usage.

#### Using Ad-hoc setup

We also provide scripts to download and boot the image on an ad-hoc setup of hardware. The mechanism is based on the `kexec` feature of the Linux kernel.
Please refer to the scripts located in `images/deployment`. The playbook `deploy.yml` downloads the image to the target nodes and handles basic configuration. The key task is execution of the `bootos` module. This is an Ansible action plugin, provided by us. It consists of two parts. The first one `images/deployment/action_plugins/bootos.py` is executed locally on the machine, that is running ansible. The actual module (`images/deployment/library/bootos` is executed remotely on the target host and uses kexec to boot a specified kernel with user-defined parameters.

Assuming all nodes are prepared with a basic OS with kexec support and the experimenter has ssh access, the experimental OS can be downloaded and booted by executing the corresponding playbook:

```bash
ansible-playbook deployment.yml
```

### Software deployment

We use this step to deploy software, which is common to all experiments that we are going to perform. We use [ansible](https://www.ansible.com/) to concisely define the desired state of the nodes (which packets should be installed, regulatory settings, etc.). The corresponding playbook can be found under `deployment/main.yml`. To apply the configuration to each node in the experiment we call ansible:

```bash
ansible-playbook main.yml
```

### Experiment run

Now that we have an experimental OS with all the required software up and running, we can start the actual experiments. In the `experiment` directory there is a convenient script `experiment.py` that can be used to orchestrate all experiments.

The first step is to activate the kernel, for which we want to measure Wifi throughput, in a two step procedure.

```bash
experiment.py select_kernel
```

This will prompt the user to select one of the installed kernels. Note that this just sets a symlink to the specified kernel, but does not yet load it. Therefore the nodes have to be rebooted in order to activate the new kernel. This can be achieved using the testbed API (or using Ansible/Fabric in an Ad-Hoc setting).

When the nodes have rebooted, it is time to start the actual measurements. This consists of configuration, i.e. starting an Access Point on a node and connecting a Station and starting iperf to measure throughput between the pair, saving results to the local filesystem. This procedure is automatically repeated for every constellation when calling:

```bash
experiment.py run
```

After the measurements have finished, repeat the whole procedure, starting by selecting another kernel.

### Data analysis

To view results start jupyter notebook:

```
pipenv run jupyter notebook
```

and open one of the notebooks in `analysis` folder.
