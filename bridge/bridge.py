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
NOCTALIA_IMPORT_KEYS=('iconSize','spacing','glassOpacity','cornerRadius','magnificationEnabled','magnification','showRunning','hideMode')


def active_import_backups(state):
    return sorted((state/'import-backups').glob('*.json'))


def noctalia_dock_patch(source):
    """Copy compatible global Dock values; never copy pins, enable state or monitors."""
    if not isinstance(source,dict):raise ValueError('Expected Noctalia Dock settings')
    mappings={
        'icon_size':('iconSize',24,128,int),
        'item_spacing':('spacing',0,40,int),
        'background_opacity':('glassOpacity',0,1,float),
        'radius':('cornerRadius',0,80,int),
        'magnification_scale':('magnification',1,3,float),
    }
    patch={}
    for name,(key,minimum,maximum,kind) in mappings.items():
        if name not in source:continue
        value=source[name]
        if type(value) not in (float,int) or not math.isfinite(value):raise ValueError('Invalid Noctalia '+name)
        patch[key]=kind(max(minimum,min(maximum,value)))
    for name,key in [('magnification','magnificationEnabled'),('show_running','showRunning')]:
        if name in source:
            if type(source[name]) is not bool:raise ValueError('Invalid Noctalia '+name)
            patch[key]=source[name]
    if 'auto_hide' in source or 'smart_auto_hide' in source:
        smart=source.get('smart_auto_hide',False)
        automatic=source.get('auto_hide',False)
        if type(smart) is not bool or type(automatic) is not bool:raise ValueError('Invalid Noctalia hide mode')
        patch['hideMode']='smart' if smart else 'always' if automatic else 'never'
    if not patch:raise ValueError('No compatible Noctalia Dock settings found')
    return patch


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
    if c.get('noctaliaDockColorSync',True) and 'iconColorize' in request:
        enabled=request['iconColorize'];color=request.get('iconColor')
        if type(enabled) is not bool:raise ValueError('Invalid icon colorization flag')
        overrides=request.get('iconColorizeByMonitor',{})
        if not isinstance(overrides,dict) or any(not isinstance(k,str) or type(v) is not bool for k,v in overrides.items()):
            raise ValueError('Invalid monitor icon colorization settings')
        selected=out['monitor']
        if selected=='@auto':selected=out.get('runtimeMonitor','')
        if selected in overrides:enabled=overrides[selected]
        if not isinstance(color,str) or not re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})',color):
            raise ValueError('Invalid icon color')
        out['iconTint']=enabled
        out['iconTintColor']=color
        out['iconTintStrength']=1.0
    if 'iconOverrides' in c:
        import options
        out.update(options.optional({'iconOverrides':c['iconOverrides']},{}))
    return out


def atomic_merge(path, patch, backup=None, respect_color_sync=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    with (path.parent/'.integration.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(old,dict): raise ValueError('settings.json must be an object')
        # A sync request can be calculated before Undo and commit after it.
        # Check the current flag under the same lock as the write.
        if respect_color_sync and old.get('noctaliaDockColorSync',True) is False:
            patch={k:v for k,v in patch.items() if k not in ('iconTint','iconTintColor','iconTintStrength')}
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
        keys=('iconSize','spacing','glassOpacity','cornerRadius','magnificationEnabled','magnification','animationSpeed','hideMode','monitor','noctaliaDockColorSync')
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
    elif action=='apply-noctalia-dock':
        patch=noctalia_dock_patch(json.loads(sys.argv[2]))
        target=config/'macdock/settings.json'
        # Repeated Apply must not overwrite the pre-import state. One Undo
        # always returns to the settings from before the first active Apply.
        backup=None
        if not active_import_backups(state):
            backup=state/'import-backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
        atomic_merge(target,dict(patch,noctaliaDockColorSync=True),backup=backup)
        import settings_store
        applied=settings_store.read(target)
        if any(applied[key]!=value for key,value in patch.items()):raise RuntimeError('Imported settings did not match disk')
        applied['undoNoctaliaAvailable']=True
        print(json.dumps({'saved':True,'settings':applied,'changed':patch,'backup':str(backup)}))
    elif action=='undo-noctalia-dock':
        backups=active_import_backups(state)
        if not backups:raise ValueError('No Noctalia Dock import to undo')
        previous=json.loads(backups[0].read_text())
        if not isinstance(previous,dict):raise ValueError('Import backup must contain a settings object')
        import settings_store
        # Explicit defaults also update a running QML model whose FileView
        # cannot clear an old value when a key disappears from settings.json.
        restore={key:previous.get(key,settings_store.DEFAULTS[key]) for key in NOCTALIA_IMPORT_KEYS}
        # Stop the independent 1.5 s palette sync from immediately undoing
        # the user's Undo. Normal full-color icons are restored as well.
        restore.update(noctaliaDockColorSync=False,iconTint=False)
        target=config/'macdock/settings.json'
        undo_backup=state/'import-undo-backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
        atomic_merge(target,restore,backup=undo_backup)
        current=json.loads(target.read_text())
        if any(current.get(key)!=value for key,value in restore.items()):
            raise RuntimeError('Undo settings did not match disk')
        # Archive the full import session, including snapshots from older
        # versions. Never revert one import on top of another imported state.
        for snapshot in backups:
            snapshot.rename(snapshot.with_suffix('.undone'))
        restored=settings_store.read(target);restored['undoNoctaliaAvailable']=False
        print(json.dumps({'saved':True,'settings':restored,'backup':str(undo_backup)}))
    elif action=='settings':
        import settings_store
        settings=settings_store.read(config/'macdock/settings.json')
        settings['undoNoctaliaAvailable']=bool(active_import_backups(state))
        print(json.dumps(settings))
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
            atomic_merge(config/'macdock/settings.json',{k:v for k,v in patch.items() if k in ('runtimeMonitor','darkMode','appearanceMode','tintMode','backgroundTint','dockStyle','outputSettings','iconTint','iconTintColor','iconTintStrength')},respect_color_sync=True)
            import icon_theme
            icon_theme.apply(request['config'].get('iconTheme',''),config/'quickshell/MacDock/shell.qml',state/'theme-backups')
            # The ownership marker survives logout. It must not suppress a new
            # start when systemd stopped the service in the previous session.
            if request['config'].get('enabled') and request['config'].get('automatic'):
                live=command(['qs','-c','MacDock','ipc','call','health','ready'])
                if live.returncode:
                    active=command(['systemctl','--user','is-active','macdock.service'])
                    if active.returncode:
                        result=command(['systemctl','--user','start','macdock.service'])
                        if result.returncode:raise RuntimeError(result.stderr or result.stdout)
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
