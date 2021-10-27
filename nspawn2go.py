#!/usr/bin/env python3
"""
Copyright 2021 Alexei Boronine

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Interactive mode:         python3 nspawn2go.py
Sample automated usage:   VMNAME=vm1 VMGRAPHICS=1 VMDISPLAY=5 VMDESKTOP=icewm python3 nspawn2go.py
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def print_blue(s: str):
    print(f'\033[94m{s}\033[0m')


def print_cyan(s: str):
    print(f'\033[96m{s}\033[0m')


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
            if i is None:
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
VMGEOMETRY: str = '1280x720'
if VMGRAPHICS:
    VMDISPLAY = param('VMDISPLAY',
                      prompt="VNC display, corresponds to TCP port: 1 -> 5901, 2 -> 5902",
                      default=VMDISPLAY,
                      integer=True)
    VMDESKTOP = param('VMDESKTOP',
                      prompt="Desktop environment",
                      default=VMDESKTOP,
                      choices=['icewm', 'xfce4'])
    VMGEOMETRY = param('VMGEOMETRY',
                       prompt="VNC display resolution",
                       default=VMGEOMETRY)

VMPASS = param('VMPASS',
               prompt="User password",
               default='debian')

USER_NAME = 'debian'
VNC_PORT = 5900 + VMDISPLAY

# This is a security feature of systemd-nspawn that is a pain in the ass to work with
PRIVATE_USERS = 'no'

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
    # needed for 'machinectl start' (not needed for basic 'system-nspawn' usage)
    'systemd',
    # We are including sudo by default
    'sudo'
]
if VMGRAPHICS:
    INCLUDE.extend([
        'tigervnc-standalone-server',
        # This package is necessary for lxqt settings, pcmanfm-qt, thunar settings and many other programs
        'dbus-x11',
    ])
    if VMDESKTOP == 'icewm':
        INCLUDE.extend([
            'icewm',
            # no terminal emulator is included by default
            'xterm'
        ])
    elif VMDESKTOP == 'xfce4':
        INCLUDE.extend([
            'xfce4',
            # no terminal emulator is included by default
            'xfce4-terminal'
        ])

DEBOOTSTRAP_OPTS = ['--variant=minbase']
if len(INCLUDE) > 0:
    pgks = ','.join(INCLUDE)
    DEBOOTSTRAP_OPTS.append(f'--include={pgks}')


def run_local(command: str):
    print_cyan(command)
    subprocess.run(command, check=True, shell=True)


def run_nspawn(command: str, user='root'):
    command_spawn = f"systemd-nspawn --private-users={PRIVATE_USERS} --user={user} --machine={VMNAME} /bin/sh -c '{command}'"
    run_local(command_spawn)


try:

    D_CACHE_DEB.mkdir(parents=True, exist_ok=True)
    os.chdir(D_MACHINES)
    p = subprocess.run('debootstrap --version', stdout=subprocess.PIPE, shell=True, encoding='utf-8')
    debootstrap_version_m = re.search('(\\d+\\.)+\\d+', p.stdout)
    if debootstrap_version_m is None:
        print_red("Could not detect debootstrap version")
        sys.exit(2)

    debootstrap_version = debootstrap_version_m.group(0)
    print('debootstrap version detected:', debootstrap_version)

    [v1, v2, v3] = [int(i) for i in debootstrap_version.split('.')]
    # Minimum version that supports --cache-dir is 1.0.97
    # https://metadata.ftp-master.debian.org/changelogs//main/d/debootstrap/debootstrap_1.0.123_changelog
    if not (v1 < 1 or v2 < 0 or v3 < 97):
        DEBOOTSTRAP_OPTS.append('--cache-dir={D_CACHE_DEB}')

    opts = ' '.join(DEBOOTSTRAP_OPTS)
    run_local(f'debootstrap --arch=armel {opts} {VMRELEASE} {VMNAME} http://deb.debian.org/debian/')

    print('injecting hostname', F_HOSTNAME)
    F_HOSTNAME.write_text(f'{VMNAME}\n')

    print('injecting sudoer', F_SUDOER)
    F_SUDOER.write_text(f'{USER_NAME} ALL=(ALL:ALL) ALL')

    if VMSSHD:
        print('injecting sshd port', F_SSHD_CONF)
        F_SSHD_CONFDIR.mkdir(parents=True)
        F_SSHD_CONF.write_text(f'Port {VMSSHDPORT}')
        # We have to install openssh-server after everything else, so it picks up port config
        run_nspawn('apt-get install -y openssh-server')

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

    # NOTE: This command accepts --password "{VMPASS}", but this doesn't work for some reason
    run_nspawn(f'useradd --create-home --shell /bin/bash {USER_NAME}')
    run_nspawn(f'echo {USER_NAME}:{VMPASS} | chpasswd')
    run_nspawn(f'echo root:{VMPASS} | chpasswd')

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
        VNC_CONFIG = f'session={session}\\ngeometry={VMGEOMETRY}\\nlocalhost=no\\nalwaysshared'
        run_nspawn(f'echo ":{VMDISPLAY}={USER_NAME}" >> /etc/tigervnc/vncserver.users')
        run_nspawn(f'mkdir /home/{USER_NAME}/.vnc', user=USER_NAME)
        run_nspawn(f'echo {VMPASS} | vncpasswd -f > /home/{USER_NAME}/.vnc/passwd', user=USER_NAME)
        run_nspawn(f'chmod 600 /home/{USER_NAME}/.vnc/passwd')
        run_nspawn(f'echo "{VNC_CONFIG}" > /home/{USER_NAME}/.vnc/config', user=USER_NAME)
        run_nspawn(f'systemctl enable tigervncserver@:{VMDISPLAY}')

    print("Setup finished")
    print_blue(f'root password: {VMPASS}')
    print_blue(f'{USER_NAME} password: {VMPASS}')
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
        print_blue(f"VNC password: {VMPASS}")
    print("You can delete your new VM with:")
    print_green(f"    machinectl stop {VMNAME}")
    print_green(f"    rm -rf {D_MACHINE}")
    print_green(f"    rm {F_NSPAWN}")

except BaseException as e:
    print_red("Something went wrong with the installation, run this to clean up your system:")
    print_red(f"    rm -rf {D_MACHINE}")
    print_red(f"    rm {F_NSPAWN}")
    raise e
