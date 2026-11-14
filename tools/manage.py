#!/usr/bin/env python3
"""User installation and reversible lifecycle; never edits Hyprland."""
import argparse
import configparser
import copy
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def xdg(name, fallback):
    p = Path(os.environ.get(name, str(Path.home() / fallback)))
    if not p.is_absolute():
        raise ValueError(f'{name} must be absolute')
    return p


def paths():
    config = xdg('XDG_CONFIG_HOME', '.config')
    data = xdg('XDG_DATA_HOME', '.local/share')
    state = xdg('XDG_STATE_HOME', '.local/state')
    return {
        'app': config / 'quickshell/MacDock',
        'launcher': Path.home() / '.local/bin/macdock',
        'desktop': data / 'applications/macdock.desktop',
        'autostart': config / 'autostart/macdock.desktop',
        'settings': config / 'macdock',
        'service': config / 'systemd/user/macdock.service',
        'service_link': config / 'systemd/user/graphical-session.target.wants/macdock.service',
        'noctalia': Path(os.environ.get('NOCTALIA_STATE_HOME', str(state / 'noctalia'))) / 'settings.toml',
    }


def safe(p):
    # Do not overwrite a symlink to some other application or dotfiles repository.
    for part in (p, *p.parents):
        if part.is_symlink():
            if part == p and p == paths()['service_link'] and p.resolve() == paths()['service'].resolve():
                continue
            raise ValueError(f'Refusing to modify symlink: {part}')


def remove(p):
    safe(p)
    if p.is_symlink():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()


def atomic_write(p, text, mode=0o600):
    safe(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.macdock-', dir=p.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def copy_path(src, dst):
    if src.is_symlink():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(os.readlink(src))
    elif src.is_dir():
        shutil.copytree(src, dst, symlinks=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def backup(keys=None):
    targets = paths()
    keys = list(keys) if keys is not None else list(targets)
    base = xdg('XDG_STATE_HOME', '.local/state') / 'macdock/backups'
    safe(base)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=base))
    entries = {}
    for key in keys:
        p = targets[key]
        safe(p)
        entries[key] = {'path': str(p), 'present': p.exists() or p.is_symlink()}
        if p.exists() or p.is_symlink():
            copy_path(p, dest / key)
    atomic_write(dest / 'manifest.json', json.dumps({'version': 1, 'entries': entries}, indent=2))
    return dest


def restore_snapshot(snapshot):
    snapshot = Path(snapshot).resolve()
    manifest = json.loads((snapshot / 'manifest.json').read_text())
    targets = paths()
    if manifest.get('version') != 1:
        raise ValueError('Unsupported backup format')
    # Validate the entire manifest before making changes.
    for key, entry in manifest['entries'].items():
        if key not in targets or entry['path'] != str(targets[key]):
            raise ValueError('Backup belongs to another HOME / XDG configuration')
        safe(targets[key])
        if entry['present'] and not ((snapshot / key).exists() or (snapshot / key).is_symlink()):
            raise ValueError(f'Incomplete backup: {key}')
    for key, entry in manifest['entries'].items():
        p = targets[key]
        remove(p)
        if entry['present']:
            p.parent.mkdir(parents=True, exist_ok=True)
            copy_path(snapshot / key, p)


def theme_names():
    roots = [Path.home() / '.icons', xdg('XDG_DATA_HOME', '.local/share') / 'icons']
    roots += [Path(p) / 'icons' for p in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    found = {}
    for root in roots:
        for path in root.glob('*/index.theme'):
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                cp.read(path)
                name = cp.get('Icon Theme', 'Name')
                if path.parent.name.startswith('MacOS-Like'):
                    found.setdefault(path.parent.name, {'name': name, 'path': str(path)})
            except (configparser.Error, OSError):
                pass
    return found


def choose_theme(requested=None):
    themes = theme_names()
    name = requested or ('MacOS-Like-Dark' if 'MacOS-Like-Dark' in themes else next(iter(sorted(themes)), ''))
    if name not in themes or not re.fullmatch(r'[\w.-]+', name):
        raise ValueError(f'MacOS-Like theme not found: {name!r}; found {list(themes)}')
    return name


def check_dependencies():
    missing = [cmd for cmd in ('qs', 'hyprctl', 'python3', 'xdg-open') if not shutil.which(cmd)]
    return missing


def desktop_entry(launcher):
    # Desktop Entry Exec quoting (not shell quoting). %% escapes field codes.
    arg = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    return f'[Desktop Entry]\nType=Application\nName=MacDock\nComment=Standalone MacShell Dock\nExec="{arg}"\nIcon=preferences-desktop\nTerminal=false\nCategories=Utility;\n'


def service_entry(launcher):
    arg = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$')
    return ('[Unit]\nDescription=Standalone MacDock\nPartOf=graphical-session.target\nAfter=graphical-session.target\nStartLimitIntervalSec=60\nStartLimitBurst=3\n'
            '[Service]\nType=simple\nExecStart="' + arg + '"\nRestart=on-failure\nRestartSec=5\n'
            '[Install]\nWantedBy=graphical-session.target\n')


def set_autostart(state, backend):
    p = paths()
    remove(p['autostart'])
    remove(p['service_link'])
    if state == 'on':
        if backend == 'xdg':
            atomic_write(p['autostart'], desktop_entry(p['launcher']), 0o644)
        else:
            p['service_link'].parent.mkdir(parents=True, exist_ok=True)
            p['service_link'].symlink_to(p['service'])
    # Enabling affects the next graphical login. Never start/stop the compositor.


def install(theme=None, autostart=False, allow_missing=False):
    missing = check_dependencies()
    if missing and not allow_missing:
        raise ValueError('Missing dependencies: ' + ', '.join(missing) + '; run ./install.sh --deps first')
    theme = choose_theme(theme)
    src = ROOT / 'app/MacDock'
    for f in ('shell.qml', 'MacDock.qml', 'DockGlassPanel.qml'):
        if not (src / f).is_file():
            raise ValueError(f'Incomplete application: {f}; run tools/check.py')
    targets = paths()
    keys = ['app', 'launcher', 'desktop', 'autostart', 'settings', 'service', 'service_link']
    snap = backup(keys)
    try:
        target = targets['app']
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.MacDock-stage-', dir=target.parent) as temp:
            staged = Path(temp) / 'MacDock'
            shutil.copytree(src, staged)
            shell = staged / 'shell.qml'
            shell.write_text(re.sub(r'^//@ pragma IconTheme .+$', '//@ pragma IconTheme ' + theme, shell.read_text(), flags=re.M))
            shutil.copy2(ROOT / 'tools/runtime.py', staged / 'runtime.py')
            shutil.copy2(ROOT / 'LICENSE', staged / 'LICENSE')
            atomic_write(staged / '.macdock-install.json', json.dumps({'upstream': '51db0bab6997da310d2aacfaa7084740ec44ad4a', 'theme': theme}))
            remove(target)
            os.replace(staged, target)
        # Python launcher avoids shell interpolation, including paths with spaces.
        launcher = '#!/usr/bin/env python3\nimport os, sys\nos.execv(sys.executable, [sys.executable, ' + repr(str(target / 'runtime.py')) + '] + sys.argv[1:])\n'
        atomic_write(targets['launcher'], launcher, 0o755)
        atomic_write(targets['desktop'], desktop_entry(targets['launcher']), 0o644)
        targets['settings'].mkdir(parents=True, exist_ok=True)
        if not (targets['settings'] / 'settings.json').exists():
            atomic_write(targets['settings'] / 'settings.json', '{}\n')
        atomic_write(targets['service'], service_entry(targets['launcher']), 0o644)
        if autostart:
            set_autostart('on', 'xdg' if autostart is True else autostart)
    except BaseException:
        restore_snapshot(snap)
        raise
    print(f'Installed {target}\nIcon theme: {theme}\nBackup: {snap}')
    if missing:
        print('STAGED ONLY: dependencies missing: ' + ', '.join(missing))
    print('Start: qs -c MacDock (or ~/.local/bin/macdock)')


def require_stopped():
    qs = shutil.which('qs')
    if not qs:
        return
    result = subprocess.run([qs, '-c', 'MacDock', 'ipc', 'call', 'health', 'ready'], capture_output=True, text=True, timeout=8)
    if result.returncode == 0:
        raise ValueError('MacDock is running. Stop it with macdock stop before changing installed files.')


def health():
    result = subprocess.run(['qs', '-c', 'MacDock', 'ipc', 'call', 'health', 'ready'], capture_output=True, text=True, timeout=8, check=True)
    # Ignore qs logging lines; require our complete JSON response.
    for line in result.stdout.splitlines():
        try:
            status = json.loads(line)
            if isinstance(status, dict) and status.get('app') == 'MacDock' and status.get('ready') and status.get('screens'):
                return status
        except json.JSONDecodeError:
            pass
    raise ValueError('No ready standalone MacDock on a screen; Noctalia was not changed')


def disable_dock_toml(text):
    original = tomllib.loads(text)
    expected = copy.deepcopy(original)
    if not isinstance(expected.get('dock', {}), dict):
        raise ValueError('Unsupported dock value in TOML')
    expected.setdefault('dock', {})['enabled'] = False
    if original == expected:
        return text
    # Prefer the existing explicit table, preserving every unrelated line and comment.
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if re.match(r'^\s*\[dock\]\s*(?:#.*)?$', line)), None)
    if start is not None:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r'^\s*\[', lines[i])), len(lines))
        enabled = next((i for i in range(start + 1, end) if re.match(r'^\s*enabled\s*=', lines[i])), None)
        if enabled is None:
            lines.insert(start + 1, 'enabled = false\n')
        else:
            lines[enabled] = re.sub(r'(=\s*)(true|false)', r'\g<1>false', lines[enabled], count=1)
        out = ''.join(lines)
    elif re.search(r'^dock\.enabled\s*=', text, re.M):
        out = re.sub(r'^(dock\.enabled\s*=\s*)(true|false)', r'\g<1>false', text, flags=re.M)
    else:
        out = text.rstrip() + '\n\n[dock]\nenabled = false\n'
    # Inline/quoted/dotted structures that cannot be safely preserved fail before writing.
    if tomllib.loads(out) != expected:
        raise ValueError('Unsupported TOML layout; change dock.enabled in Noctalia GUI instead')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ins = sub.add_parser('install')
    ins.add_argument('--theme')
    ins.add_argument('--autostart', nargs='?', const='xdg', choices=['xdg','systemd'])
    ins.add_argument('--allow-missing-deps', action='store_true', help='Stage files only; does not claim a runnable installation')
    sub.add_parser('doctor')
    sub.add_parser('backup')
    rs = sub.add_parser('restore'); rs.add_argument('snapshot')
    sub.add_parser('uninstall')
    au = sub.add_parser('autostart'); au.add_argument('state', choices=['on', 'off']); au.add_argument('--backend', choices=['xdg', 'systemd'], default='xdg')
    sub.add_parser('noctalia-disable')
    args = parser.parse_args()
    if args.command == 'doctor':
        missing = check_dependencies()
        print(json.dumps({'missing': missing, 'themes': theme_names(), 'wayland_display': os.environ.get('WAYLAND_DISPLAY'), 'paths': {k: str(v) for k,v in paths().items()}}, indent=2))
        return int(bool(missing))
    state = xdg('XDG_STATE_HOME', '.local/state') / 'macdock'
    safe(state)
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'manage.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.command == 'install':
            require_stopped()
            install(args.theme, args.autostart, args.allow_missing_deps)
        elif args.command == 'backup':
            require_stopped()
            print(backup())
        elif args.command == 'restore':
            require_stopped()
            # Keep an undo snapshot too, but validate source first in restore_snapshot.
            snapshot = Path(args.snapshot).resolve()
            if not (snapshot / 'manifest.json').is_file():
                raise ValueError('Backup manifest missing')
            undo = backup()
            try:
                restore_snapshot(snapshot)
            except BaseException:
                restore_snapshot(undo)
                raise
            print(f'Restored. Undo backup: {undo}')
        elif args.command == 'uninstall':
            require_stopped()
            p = paths()
            if not (p['app'] / '.macdock-install.json').exists():
                raise ValueError('No managed MacDock installation; refusing to remove unknown files')
            snap = backup(['app', 'launcher', 'desktop', 'autostart', 'service', 'service_link'])
            try:
                for key in ('autostart', 'service_link', 'service', 'desktop', 'launcher', 'app'):
                    remove(p[key])
            except BaseException:
                restore_snapshot(snap)
                raise
            print(f'Uninstalled. Settings and Noctalia preserved. Restore: {snap}')
        elif args.command == 'autostart':
            p = paths()
            if not (p['app'] / '.macdock-install.json').exists():
                raise ValueError('Install MacDock first')
            snap = backup(['autostart', 'service_link'])
            try:
                set_autostart(args.state, args.backend)
            except BaseException:
                restore_snapshot(snap)
                raise
            print(f'Autostart {args.state}. Backup: {snap}')
        elif args.command == 'noctalia-disable':
            status = health()  # A working Dock is mandatory before touching Noctalia.
            p = paths()['noctalia']
            text = p.read_text() if p.exists() else ''
            out = disable_dock_toml(text)
            snap = backup(['noctalia'])
            atomic_write(p, out)
            print(f'MacDock ready: {status}\nSet dock.enabled=false in authoritative GUI state: {p}\nBackup: {snap}\nReload Noctalia settings from its GUI if needed; no service was restarted.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f'macdock: {e}', file=sys.stderr)
        sys.exit(1)
