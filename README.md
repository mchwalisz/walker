# Wi-Fi channel measurement experiment

Based on work from Sascha Rösler but switched to `fabric`.


### Useful commands

```bash
fab config.reserve set_hosts config.install

fab set_hosts full_scan

fab config wifi.scan
fab -H nuc4 wifi.create_ap:iface=wlan0
fab -H nuc11 wiwifi.connect:iface=wlan1
```
