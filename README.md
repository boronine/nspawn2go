# nspawn2go

## What is it?

An interactive script to provision lightweight Debian VMs on your Linux host.

```
wget 
```

## How does it work?

Modern systemd-based Linux hosts come equipped with a lightweight container system called
[nspawn](https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html). For most practical
purposes, these containers are lightweight, portable VMs. They boot using their own instance
of systemd and are able to run a SSH server, graphical environment via VNC and just about anything
you want.
