# nspawn2go

![screenshot](https://raw.githubusercontent.com/boronine/nspawn2go/master/screenshot.jpg)

## What is it?

An interactive script to provision lightweight Debian VMs. Access your tiny VMs via
SSH or VNC.

```
sudo python3 nspawn2go.py
```

- Username: `debian`
- Password: `debian` (default)
- SSH server port: `2022` (default)
- VNC port: `5901` (default)
- VNC geometry: `1280x720` (default)
  - Try `800x480` for a minimal desktop
- Graphical environments: `icewm` or `xfce4`
- Root directory: `/var/lib/machines/VMNAME`

## What is it for?

- Run a tiny graphical desktop:
  - on a dirt-cheap 512mb VPS
  - on a Raspberry Pi in your home network
  - access from any desktop or even from your phone via VNC
- Containerize your servers:
  - Isolate your server configuration from your host
  - All-systemd, no need for third-party tools like Docker
- Portability:
  - Transfer your VM simply by copying the root directory
  - Host can be any systemd distro
  - Host can be bare metal, KVM, VirtualBox, QEMU etc.

## How does it work?

Modern systemd-based Linux hosts come equipped with a lightweight container system called
[nspawn](https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html). For most 
practical purposes, these containers are lightweight, portable VMs.

Instead of a disk image, these containers boot into a directory on your host: 
`/var/lib/machines/VMNAME`. That's why systemd-nspawn is known as "chroot on steroids".

Like Docker, you can use these containers to run ad-hoc commands but what makes this most
interesting is when you run systemd inside the container to bring up an isolated Linux
system.

You can manage these VMs using [machinectl](https://www.freedesktop.org/software/systemd/man/machinectl.html)
(start, stop, reboot, enable, disable).

## Instructions

Host dependencies:

- python3
- systemd-container (provides `machinectl`)
- debootstrap

On Debian/Ubuntu hosts:

```
apt-get install python3 systemd-container debootstrap
```

On Arch hosts:

```
pacman -S python3 debootstrap
```

Download and run nspawn2go:

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
security feature of systemd-nspawn. This feature maps container UIDs and GIDs to a private 
set of UIDs and GIDs on the host. We disable it because it makes working with container files 
from the host a hassle.

This script does not take advantage of systemd-nspawn's [--private-network=](https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html#--private-network) 
feature, instead containers share the host network. Pick unique ports for your services if you 
plan on running multiple instances.
