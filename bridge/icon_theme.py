"""Validate an installed XDG icon theme and update only MacDock's Qt pragma."""
import configparser
import datetime
import os
from pathlib import Path
import re
import shutil
import tempfile


def themes():
    roots=[Path.home()/'.icons',Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'icons']
    roots += [Path(p)/'icons' for p in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':') if p]
    result={}
    for root in roots:
        for path in sorted(root.glob('*/index.theme')):
            name=path.parent.name
            if name in result or not re.fullmatch(r'[\w.-]+',name):continue
            cp=configparser.ConfigParser(interpolation=None,strict=False)
            try:
                cp.read(path,encoding='utf-8')
                result[name]={'id':name,'name':cp['Icon Theme']['Name'],'path':str(path)}
            except (OSError,UnicodeError,KeyError,configparser.Error):continue
    return sorted(result.values(),key=lambda t:(not t['id'].startswith('MacOS-Like'),t['id']))


def apply(name, shell, backup_dir):
    if not name:return False
    if name not in {t['id'] for t in themes()}:raise ValueError('Icon theme is not installed: '+str(name))
    if shell.is_symlink():raise ValueError('Refusing to modify a symlinked shell.qml')
    text=shell.read_text()
    if not re.search(r'^//@ pragma IconTheme .+$',text,re.M):raise ValueError('Missing MacDock IconTheme pragma')
    updated=re.sub(r'^//@ pragma IconTheme .+$','//@ pragma IconTheme '+name,text,flags=re.M)
    if updated==text:return False
    backup_dir.mkdir(parents=True,exist_ok=True)
    shutil.copy2(shell,backup_dir/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-shell.qml'))
    fd,tmp=tempfile.mkstemp(dir=shell.parent,prefix='.theme-')
    try:
        with os.fdopen(fd,'w') as f:f.write(updated);f.flush();os.fsync(f.fileno())
        os.replace(tmp,shell)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return True
