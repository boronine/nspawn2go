# nspawn2go

## What is it?

An interactive script to provision lightweight Debian VMs. Access your tiny VMs via
SSH or VNC.

```
sudo python3 nspawn2go.py
```

![screenshot](https://raw.githubusercontent.com/boronine/nspawn2go/master/screenshot.jpg)

## How does it work?

Modern systemd-based Linux hosts come equipped with a lightweight container system called
[nspawn](https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html). For most practical
purposes, these containers are lightweight, portable VMs.

They boot using their own instance of systemd and are able to run an SSH server, graphical environment
and just about anything you want.

You can manage these VMs using [machinectl](https://www.freedesktop.org/software/systemd/man/machinectl.html).

## Instructions

Host dependencies:

- python3
- systemd-container (provides the `machinectl` binary)
- debootstrap

Run:

```
wget https://raw.githubusercontent.com/boronine/nspawn2go/master/nspawn2go.py
sudo python3 nspawn2go.py
```

You can automate this script using environment variables. See the printed variables
as you go through the interactive mode.

## Cleanup

If you wish to delete your unused containers you can do it safely like so:

```
machinectl stop $VMNAME
rm -rf /var/lib/machines/$VMNAME
rm /etc/systemd/nspawn/$VMNAME.nspawn
```

## Caveats

This script disables the [--private-users=](https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html#--private-users=)
security feature of systemd-nspawn. This feature maps container UIDs and GIDs to a private set of UIDs and GIDs
on the host. We disable it because it makes working with container files from the host a hassle.

This script does not take advantage of systemd-nspawn's [--private-network=](https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html#--private-network) 
feature, instead containers share the host network. Pick unique ports for your services if you plan on running 
multiple instances.
