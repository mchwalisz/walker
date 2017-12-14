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

## Usage and installation

### Preparation

We leverage Python 3 tools in the whole experiment.
We use [pipenv](https://docs.pipenv.org/index.html) as a packaging tool.
Please install it first with:

```bash
$ pip install pipenv
```

To bootstrap new virtual environment enter the project directory and run:

```bash
pipenv
```

### Data analysis

To view results start jupyter notebook:

```
pipenv run jupyter notebook
```

and open one of the notebooks in `analysis` folder.

## Useful commands

```bash
fab config.reserve set_hosts config.install

fab set_hosts full_scan

fab config wifi.scan
fab -H nuc4 wifi.create_ap:iface=wlan0
fab -H nuc11 wiwifi.connect:iface=wlan1
```
