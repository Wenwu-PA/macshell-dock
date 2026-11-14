#!/usr/bin/env python3
"""Back up and migrate only existing MacDock JSON; pins and Noctalia are untouched."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/MacDock'))

REMOVED={'barMode','barNames','barOpacity','barRadius','outputIconSize','outputMagnification','outputMargin','outputEnabled','outputLiquid','outputHideMode','effectMode','unified','unifiedOpacity','glassBlur','glassLiquid','glassRim','glassGrain','glassDispersion','glassTint','glassDebug','glassLive','shaderQuality','wallpaperPath'}

def migrate(path):
    if not path.exists():return None
    import fcntl
    with (path.parent/'.integration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        raw=path.read_bytes();old=json.loads(raw);new={k:v for k,v in old.items() if k not in REMOVED and not k.startswith('barGlass')}
        new['dockStyle']='native'
        if new==old:return None
        backup=path.with_name(path.name+'.before-native-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        with backup.open('xb') as out:out.write(raw)
        import tempfile
        fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.native-migration-')
        try:
            with os.fdopen(fd,'w') as out:json.dump(new,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        return backup

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('settings',type=Path);args=parser.parse_args();print(migrate(args.settings) or 'No migration needed')
