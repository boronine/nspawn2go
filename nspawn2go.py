#!/usr/bin/env python3
"""
Sample usage: VMNAME=vm1 VMGRAPHICS=1 VMDISPLAY=5 VMDESKTOP=icewm python3 nspawn2go.py
"""

import os
import shutil
import crypt
import subprocess
import sys
from pathlib import Path


def print_blue(s: str):
    print(f'\033[94m{s}\033[0m')


def print_green(s: str):
    print(f'\033[92m{s}\033[0m')


def print_red(s: str):
    print(f'\033[91m{s}\033[0m')


def parse_boolean(s: str):
    s = s.lower()
    if s in ('y', 'yes', 't', 'true', '1'):
        return True
    elif s in ('n', 'no', 'f', 'false', '0'):
        return False


def parse_integer(s: str):
    try:
        return int(s)
    except ValueError:
        return None


def param(env: str, prompt: str, default, boolean=False, integer=False, choices=None):
    t = os.environ.get(env, '').strip()
    if t != '':
        return t
    if boolean:
        s = 'Yn' if default else 'yN'
        print_blue(f'{prompt} [{s}]')
    elif choices:
        c = ', '.join(choices)
        print_blue(f'{prompt} (choices: {c}, default: {default})')
    else:
        print_blue(f'{prompt} (default: {default})')
    while True:
        t = input(f'{env}=').strip()
        if boolean:
            b = default if t == '' else parse_boolean(t)
            if b is None:
                print_red("Invalid boolean")
                continue
            print_green(f'{env}={int(b)}')
            return b
        elif integer:
            i = default if t == '' else parse_integer(t)
            if t is None:
                print_red("Invalid integer")
                continue
            print_green(f'{env}={i}')
            return i
        elif choices:
            t = t or default
            if t not in choices:
                print_red("Invalid choice")
                continue
            print_green(f'{env}={t}')
            return t
        else:
            t = t or default
        print_green(f'{env}={t}')
        return t


# Check dependencies

if shutil.which('machinectl') is None:
    print_red('dependency not found: systemd-container')
    print('install: apt-get install systemd-container')
    sys.exit(1)

if shutil.which('debootstrap') is None:
    print_red('dependency not found: debootstrap')
    print('install: apt-get install debootstrap')
    sys.exit(1)

# Configuration

ROOT_PASS = 'debian'
USER_NAME = 'debian'
USER_PASS = 'debian'

VMNAME = param('VMNAME',
               prompt="Give your VM a name.",
               default='vm1')

VMRELEASE: str = param('VMRELEASE',
                       prompt="Debian release",
                       default='stable',
                       choices=['stable', 'testing'])

VMSSHD: bool = param('VMSSHD',
                     prompt='Install SSH server?',
                     default=False,
                     boolean=True)

VMSSHDPORT: int = 2022
if VMSSHD:
    VMSSHDPORT = param('VMSSHDPORT',
                       prompt='SSH server port',
                       default=VMSSHDPORT,
                       integer=True)
    # VMSSHKEY = param('VMSSHDKEY',
    #                  prompt=f'SSH public key for {USER_NAME}',
    #                  default='')

VMGRAPHICS: bool = param('VMGRAPHICS',
                         prompt='Should we install a graphical environment?',
                         default=False,
                         boolean=True)

VMDISPLAY: int = 1
VMDESKTOP: str = 'icewm'
if VMGRAPHICS:
    VMDISPLAY = param('VMDISPLAY',
                      prompt="VNC display, corresponds to TCP port: 1 -> 5901, 2 -> 5902",
                      default=VMDISPLAY,
                      integer=True)
    VMDESKTOP = param('VMDESKTOP',
                      prompt="Desktop environment",
                      default=VMDESKTOP,
                      choices=['icewm', 'lxqt', 'xfce4'])

VNC_PORT = 5900 + VMDISPLAY

# This is a security feature of systemd-nspawn that is a pain in the ass to work with
PRIVATE_USERS = 'no'

USER_PASS_VNC = 'debian'
USER_PASS_ENC = crypt.crypt(USER_PASS)

DHOST_HOME = Path.home()
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
D_CACHE = os.environ.get('XDG_CACHE_HOME', DHOST_HOME / '.cache')
D_CACHE_DEB = D_CACHE / 'b9_provision_nspawn_deb'
D_MACHINES = Path('/var/lib/machines')
D_NSPAWN = Path('/etc/systemd/nspawn')
F_NSPAWN = D_NSPAWN / f'{VMNAME}.nspawn'
D_MACHINE = D_MACHINES / VMNAME
F_HOSTNAME = D_MACHINE / 'etc/hostname'
F_HOSTS = D_MACHINE / 'etc/hosts'
F_SUDOER = D_MACHINE / f'etc/sudoers.d/{USER_NAME}'
F_SSHD_CONFDIR = D_MACHINE / 'etc/ssh/sshd_config.d'
F_SSHD_CONF = F_SSHD_CONFDIR / 'custom_port.conf'

INCLUDE = [
    # needed for 'machinectl login'
    'dbus',
    # needed for 'machinectl start' (not needed for simple 'system-nspawn')
    'systemd',
    # We are including sudo by default
    'sudo'
]
if VMGRAPHICS:
    INCLUDE.extend([
        'tigervnc-standalone-server',
        # 'mate-desktop-environment-core',
        'dbus-x11',  # This package is necessary for lxqt settings, pcmanfm-qt, thunar settings and many other programs
    ])
    if VMDESKTOP == 'icewm':
        INCLUDE.extend([
            'icewm',
        ])
    elif VMDESKTOP == 'lxqt':
        INCLUDE.extend([
            'lxqt-core',
        ])
    elif VMDESKTOP == 'xfce4':
        INCLUDE.extend([
            'xfce4',
        ])

INCLUDE_OPT = '' if len(INCLUDE) == 0 else '--include=' + ','.join(INCLUDE)

D_CACHE_DEB.mkdir(parents=True, exist_ok=True)
os.chdir(D_MACHINES)
subprocess.run(
    f'debootstrap --variant minbase {INCLUDE_OPT} --cache-dir {D_CACHE_DEB} {VMRELEASE} {VMNAME} http://deb.debian.org/debian/',
    check=True,
    shell=True)

print('injecting hostname', F_HOSTNAME)
F_HOSTNAME.write_text(f'{VMNAME}\n')

print('injecting sudoer', F_SUDOER)
F_SUDOER.write_text(f'{USER_NAME} ALL=(ALL:ALL) ALL')


def run(command: str, user='root'):
    command_spawn = f"systemd-nspawn --private-users={PRIVATE_USERS} --user={user} --machine={VMNAME} /bin/sh -c '{command}'"
    print('#', command_spawn)
    subprocess.run(command_spawn, check=True, shell=True)


if VMSSHD:
    print('injecting sshd port', F_SSHD_CONF)
    F_SSHD_CONFDIR.mkdir(parents=True)
    F_SSHD_CONF.write_text(f'Port {VMSSHDPORT}')
    # We have to install openssh-server after everything else, so it picks up port config
    run('apt-get install -y openssh-server')

print('injecting hostname', F_HOSTS)
with F_HOSTS.open('a') as f:
    f.write(f'127.0.1.1	{VMNAME}')

print('writing', F_NSPAWN)
D_NSPAWN.mkdir(exist_ok=True)
F_NSPAWN.write_text(f'''
[Exec]
PrivateUsers={PRIVATE_USERS}

[Network]
VirtualEthernet=no
''')

# NOTE: This command accepts --password "{USER_PASS_ENC}", but this doesn't work for some reason
run(f'useradd --create-home --shell /bin/bash {USER_NAME}')
run(f'echo {USER_NAME}:{USER_PASS} | chpasswd')
run(f'echo root:{ROOT_PASS} | chpasswd')

if VMGRAPHICS:
    # NOTE: session corresponds to files like /usr/share/xsessions/XYZ.desktop
    if VMDESKTOP == 'icewm':
        session = 'icewm-session'
    elif VMDESKTOP == 'lxqt':
        session = 'lxqt'
    elif VMDESKTOP == 'xfce4':
        session = 'xfce'
    else:
        raise Exception()
    VNC_CONFIG = f'session={session}\\ngeometry=1600x1000\\nlocalhost=no\\nalwaysshared'
    run(f'echo ":{VMDISPLAY}={USER_NAME}" >> /etc/tigervnc/vncserver.users')
    run(f'mkdir /home/{USER_NAME}/.vnc', user=USER_NAME)
    run(f'echo {USER_PASS_VNC} | vncpasswd -f > /home/{USER_NAME}/.vnc/passwd', user=USER_NAME)
    run(f'chmod 600 /home/{USER_NAME}/.vnc/passwd')
    run(f'echo "{VNC_CONFIG}" > /home/{USER_NAME}/.vnc/config', user=USER_NAME)
    run(f'systemctl enable tigervncserver@:{VMDISPLAY}')

print("Setup finished")
print_blue(f'root password: {ROOT_PASS}')
print_blue(f'{USER_NAME} password: {USER_PASS}')
print(f"Start your new VM:")
print_green(f"    machinectl start {VMNAME}")
print(f"Enable your new VM on boot:")
print_green(f"    machinectl enable {VMNAME}")
print(f"Log into your new VM:")
print_green(f"    machinectl login {VMNAME}")
if VMSSHD:
    print(f"You can connect to your VM using:")
    print_green(f"    ssh debian@HOSTNAME -p {VMSSHDPORT}")
if VMGRAPHICS:
    print(f"You can expect the VNC server to be running on {VNC_PORT}")
    print_blue(f"VNC password: {USER_PASS}")
print("You can delete your new VM with:")
print_green(f"    machinectl stop {VMNAME}")
print_green(f"    rm -rf {D_MACHINE}")
print_green(f"    rm {F_NSPAWN}")
