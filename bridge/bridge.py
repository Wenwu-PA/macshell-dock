#!/usr/bin/env python3
"""Validated, atomic Noctalia -> existing MacDock settings adapter."""
import datetime
import shutil
import fcntl
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

RANGES={'iconSize':(24,128),'magnification':(1,3),'glassOpacity':(0,1)}


def adapt(request):
    c=request['config'];out={'dockStyle':'native','outputSettings':{},'tintMode':'custom'}
    defaults={'iconSize':52,'spacing':6,'cornerRadius':18,'glassOpacity':.42,'magnification':1.7,'animationSpeed':1}
    limits={'iconSize':(24,128),'spacing':(0,40),'cornerRadius':(0,80),'glassOpacity':(0,1),'magnification':(1,3),'animationSpeed':(.25,3)}
    for key,default in defaults.items():
        v=c.get(key,default);lo,hi=limits[key]
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid '+key)
        out[key]=v
    for key,default in [('magnificationEnabled',True),('showRunning',True),('showThumbs',True)]:
        value=c.get(key,default)
        if type(value) is not bool:raise ValueError('Invalid '+key)
        out[key]=value
    out['dockEnabled']=c.get('enabled',True)
    out['hideMode']=c.get('hideMode','smart');out['monitor']=c.get('monitor','')
    if out['hideMode'] not in ('never','always','smart') or not isinstance(out['monitor'],str):raise ValueError('Invalid behavior')
    if 'outputs' in request:
        import monitors
        out['runtimeMonitor']=monitors.resolve(out['monitor'],request['outputs'])
    out['darkMode']=bool(request.get('dark',True));out['appearanceMode']='dark' if out['darkMode'] else 'light'
    tint=request.get('background','#202023' if out['darkMode'] else '#ffffff')
    if not isinstance(tint,str) or not re.fullmatch('#[0-9a-fA-F]{6}',tint):raise ValueError('Invalid theme color')
    out['backgroundTint']=tint
    if 'iconOverrides' in c:
        import options
        out.update(options.optional({'iconOverrides':c['iconOverrides']},{}))
    return out


def atomic_merge(path, patch, backup=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with (path.parent/'.integration.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(old,dict): raise ValueError('settings.json must be an object')
        if backup is not None:
            backup.parent.mkdir(parents=True,exist_ok=True)
            backup.write_text(json.dumps(old,ensure_ascii=False,indent=2)+"\n")
        new=dict(old,**patch)
        if new==old:return False
        fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.settings-')
        try:
            with os.fdopen(fd,'w') as f:json.dump(new,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        return True


def command(args):
    return subprocess.run(args,capture_output=True,text=True,timeout=12)


def main():
    action=sys.argv[1]
    config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'macdock'
    state.mkdir(parents=True,exist_ok=True)
    owner=state/'integration-owned'
    if action=='reset-settings':
        request=json.loads(sys.argv[2])
        if request.get('confirm') is not True:raise ValueError('Reset requires explicit confirmation')
        import settings_store
        keys=('iconSize','spacing','glassOpacity','cornerRadius','magnificationEnabled','magnification','animationSpeed','hideMode','monitor')
        backup=state/'reset-backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
        atomic_merge(config/'macdock/settings.json',{k:settings_store.DEFAULTS[k] for k in keys},backup=backup)
        print(json.dumps({'saved':True,'backup':str(backup),'settings':settings_store.read(config/'macdock/settings.json')}))
    elif action=='icon-themes':
        import icon_theme
        print(json.dumps(icon_theme.themes()))
    elif action=='monitors':
        import monitors
        print(json.dumps(monitors.connected()))
    elif action=='applications':
        import applications
        pins=applications.read_pins(config/'macdock/pinned.json')
        print(json.dumps({'apps':applications.catalog(),'pins':pins,'pinSnapshot':json.dumps(pins)},ensure_ascii=False))
    elif action=='pins':
        import applications
        print(json.dumps(applications.edit(config/'macdock/pinned.json',json.loads(sys.argv[2])),ensure_ascii=False))
    elif action=='set':
        patch=json.loads(sys.argv[2])
        if len(patch)!=1:raise ValueError('Expected one panel setting')
        key,value=next(iter(patch.items()))
        if key=='monitor':
            if not isinstance(value,str) or len(value)>128:raise ValueError('Invalid monitor')
        elif key=='iconOverrides':
            import options
            options.optional({key:value},{})
        elif key=='iconTheme':
            import icon_theme
            if not isinstance(value,str) or (value != '' and value not in {t['id'] for t in icon_theme.themes()}):raise ValueError('Unknown icon theme')
        elif key in ('iconSize','magnification','glassOpacity'):
            lo,hi=RANGES[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Out of range')
            if key=='iconSize':
                if int(value)!=value:raise ValueError('Expected integer')
                value=int(value)
            else:value=float(value)
        elif key in ('enabled','automatic','magnificationEnabled','showRunning','showThumbs'):
            if type(value) is not bool:raise ValueError('Expected boolean')
        elif key in ('spacing','cornerRadius','animationSpeed'):
            lo,hi={'spacing':(0,40),'cornerRadius':(0,80),'animationSpeed':(.25,3)}[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Out of range')
            if key!='animationSpeed':
                if int(value)!=value:raise ValueError('Expected integer')
                value=int(value)
        elif key=='hideMode':
            if value not in ('never','always','smart'):raise ValueError('Invalid hide mode')
        else:raise ValueError('Unsupported panel setting')
        target=config/'macdock/settings.json'
        stored_key='dockEnabled' if key=='enabled' else key
        atomic_merge(target,{stored_key:value})
        import settings_store
        actual=settings_store.read(target)[key]
        if actual!=value:raise RuntimeError('Settings changed during save: '+key+'; requested='+repr(value)+'; readback='+repr(actual))
        print(json.dumps({'key':key,'value':actual,'saved':True}))
    elif action=='settings':
        import settings_store
        print(json.dumps(settings_store.read(config/'macdock/settings.json')))
    elif action=='blur-status':
        import native_blur
        print(json.dumps(native_blur.probe(target='dock')))
    elif action=='sync':
        request=json.loads(sys.argv[2])
        import settings_store
        request['config']=settings_store.read(config/'macdock/settings.json')
        patch=adapt(request)
        errors=[]
        try:
            atomic_merge(config/'macdock/settings.json',{k:v for k,v in patch.items() if k in ('runtimeMonitor','darkMode','appearanceMode','tintMode','backgroundTint','dockStyle','outputSettings')})
            import icon_theme
            icon_theme.apply(request['config'].get('iconTheme',''),config/'quickshell/MacDock/shell.qml',state/'theme-backups')
            # Never acquire an already running, independently launched Dock.
            if request['config'].get('enabled') and request['config'].get('automatic'):
                live=command(['qs','-c','MacDock','ipc','call','health','ready'])
                if live.returncode and not owner.exists():
                    result=command(['systemctl','--user','start','macdock.service'])
                    if result.returncode:raise RuntimeError(result.stderr)
                    owner.touch()
            elif not request['config'].get('enabled') and owner.exists():
                result=command(['systemctl','--user','stop','macdock.service'])
                if result.returncode:raise RuntimeError(result.stderr)
                owner.unlink()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            errors.append('Dock: '+str(error))
        if errors: raise RuntimeError('; '.join(errors))
    elif action=='restart':
        import dock_process
        health=dock_process.restart(command)
        owner.touch()
        print(json.dumps(health))
    elif action=='start':
        live=command(['qs','-c','MacDock','ipc','call','health','ready'])
        if live.returncode==0 and not owner.exists():raise RuntimeError('Existing independent MacDock preserved; stop it before transferring ownership')
        result=command(['systemctl','--user',action,'macdock.service'])
        if result.returncode:raise RuntimeError(result.stderr)
        owner.touch()
    elif action in ('stop','stop-owned'):
        if owner.exists():
            result=command(['systemctl','--user','stop','macdock.service'])
            if result.returncode:raise RuntimeError(result.stderr)
            owner.unlink()
    elif action=='status':
        r=command(['qs','-c','MacDock','ipc','call','health','ready']);print(r.stdout or r.stderr);return r.returncode
    else:raise ValueError('Unknown action')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as e:sys.exit(str(e))
