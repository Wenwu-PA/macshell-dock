#!/usr/bin/env python3
"""Launch only MacDock, without replacing or stopping any other shell."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    qs = shutil.which('qs')
    if not qs:
        sys.exit('Quickshell missing. Install: sudo pacman -S quickshell qt6-shadertools qt6-multimedia')
    action = sys.argv[1] if len(sys.argv) > 1 else 'start'
    if action == 'settings':
        return subprocess.call([qs, '-c', 'MacDock', 'ipc', 'call', 'settings', 'open'])
    if action == 'status':
        return subprocess.call([qs, '-c', 'MacDock', 'ipc', 'call', 'health', 'ready'])
    if action == 'stop':
        return subprocess.call([qs, '-c', 'MacDock', 'ipc', 'call', 'lifecycle', 'stop'])
    if action != 'start':
        sys.exit('Usage: macdock [start|stop|settings|status]')
    if not os.environ.get('WAYLAND_DISPLAY'):
        sys.exit('Start MacDock from your Wayland session.')
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime:
        sys.exit('XDG_RUNTIME_DIR is missing.')
    lock = open(Path(runtime) / 'macdock-launch.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('MacDock launcher is already running.')
    check = subprocess.run([qs, '-c', 'MacDock', 'ipc', 'call', 'health', 'ready'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if check.returncode == 0:
        return 0
    os.set_inheritable(lock.fileno(), True)
    os.execv(qs, [qs, '-n', '-c', 'MacDock'])


if __name__ == '__main__':
    sys.exit(main())
