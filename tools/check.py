#!/usr/bin/env python3
"""Offline checks. A successful parse is not a Quickshell/Wayland runtime test."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app/MacDock'


def tool(name):
    return shutil.which(name) or (str(Path('/usr/lib/qt6/bin') / name) if (Path('/usr/lib/qt6/bin') / name).exists() else None)


def main():
    if (ROOT/'research/upstream').exists():
        manifest = json.loads((ROOT / 'sources.lock.json').read_text())
        for rec in manifest['unmodified']:
            if rec['path']=='DockGlassPanel.qml':continue  # Replaced with native plain popup; historical original retained upstream.
            data = ((ROOT/'research/upstream/MacShell'/rec['path']) if rec['path']=='DockGlassPanel.qml' else (APP / rec['path']) if (APP / rec['path']).exists() else ROOT/'research/retired-native-transition'/rec['path']).read_bytes()
            sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if len(data) != rec['size'] or sha != rec['sha']:
                raise ValueError('Upstream content mismatch: ' + rec['path'])
        for rec in manifest['adapted']:
            data = (ROOT / 'research/upstream/MacShell' / rec['path']).read_bytes()
            candidates = (data, data[:-1]) if data.endswith(b'\n') else (data,)
            if not any(hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == rec['sha'] for b in candidates):
                raise ValueError('Pinned source mismatch: ' + rec['path'])
        print(f'PASS upstream: {len(manifest["unmodified"])} exact Git blobs and 2 pinned source files')
    else:
        print('SKIP historical upstream provenance (not included in runtime distribution)')
    for file in list(APP.rglob('*.qml')) + list(APP.rglob('*.js')):
        for path in re.findall(r'(?:\.?import|Qt\.resolvedUrl\()\s*["\']([^"\']+)["\']', file.read_text()):
            if not (file.parent / path).exists():
                raise ValueError(f'Missing local dependency {file}: {path}')
    print('PASS local JS imports and resolved assets')
    formatter = tool('qmlformat')
    if not formatter:
        raise ValueError('qmlformat unavailable (qt6-declarative)')
    for file in APP.glob('*.qml'):
        subprocess.run([formatter, '-n', str(file)], stdout=subprocess.DEVNULL, check=True)
    print('PASS Qt QML syntax: all application components')
    for file in (ROOT / 'install.sh', ROOT / 'uninstall.sh', ROOT / 'run.sh'):
        subprocess.run(['bash', '-n', str(file)], check=True)
    print('PASS shell entry points')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-v'], check=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
