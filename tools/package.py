#!/usr/bin/env python3
"""Build a self-contained source/application archive, without downloading anything."""
import hashlib
from pathlib import Path
import tarfile
ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'dist/macdock-0.1.0.tar.gz'
out.parent.mkdir(exist_ok=True)
def clean(info):
    if Path(info.name).name in ('experimental_backend.py','check_widget_luau.py'):
        return None
    if '__pycache__' in Path(info.name).parts or info.name.endswith('.pyc'):
        return None
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    return info
with tarfile.open(out, 'w:gz') as archive:
    for name in ('app', 'tools', 'tests', 'noctalia', 'bridge', 'README.md', 'README.ru.md', 'CHANGELOG.md', 'NOTICE', 'LICENSE', 'sources.lock.json', 'install.sh', 'uninstall.sh', 'run.sh', 'Makefile'):
        archive.add(ROOT / name, arcname='macdock-0.1.0/' + name, filter=clean)
    for name in ('CONFIGURATION.md','TROUBLESHOOTING.md','RELEASE-v0.1.0.md'):
        archive.add(ROOT/'docs'/name, arcname='macdock-0.1.0/docs/'+name, filter=clean)
checksum = hashlib.sha256(out.read_bytes()).hexdigest()
(out.parent / (out.name + '.sha256')).write_text(checksum + '  ' + out.name + '\n')
print(out)
print('SHA256 ' + checksum)
