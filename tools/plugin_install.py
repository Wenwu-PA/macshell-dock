#!/usr/bin/env python3
import hashlib
import json
import datetime
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]

def refuse_symlink(path):
    for part in (path,*path.parents):
        if part.is_symlink():raise RuntimeError('Refusing to overwrite symlink: '+str(part))

def main():
    mode=sys.argv[1]
    version=subprocess.check_output(['noctalia','--version'],text=True)
    if 'v5.4.1' not in version:raise RuntimeError('This integration targets Noctalia 5.4.1')
    # Fail before any mutation when the supported registration API is unavailable.
    live=subprocess.run(['noctalia','msg','plugins','list'],capture_output=True,text=True)
    if live.returncode:raise RuntimeError('Noctalia IPC unavailable; no files changed: '+live.stderr.strip())
    status=subprocess.run(['systemctl','--user','is-active','macdock.service'],capture_output=True,text=True)
    dock_live=subprocess.run(['qs','-c','MacDock','ipc','call','health','ready'],capture_output=True,text=True)
    if status.returncode and dock_live.returncode==0:raise RuntimeError('Independent Dock running; refusing service takeover')
    data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    app=config/'quickshell/MacDock'
    if not (app/'shell.qml').exists():raise RuntimeError('Existing MacDock installation required')
    target=data/'noctalia/plugins/macdock'
    state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))
    for path in (target,app,state/'macdock/plugin-backups'):
        refuse_symlink(path)
    if target.exists():
        for path in target.rglob('*'):
            if path.is_symlink():raise RuntimeError('Plugin contains a symlink: '+str(path))
    for name in ('MacDock.qml','shell.qml','config_store.py','runtime.py','integration_cleanup.py','integration_bar_style.py','noctalia_config.py'):
        refuse_symlink(app/name)
    backup=state/'macdock/plugin-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    if target.exists():shutil.copytree(target,backup/'plugin')
    shutil.copytree(app,backup/'complete-dock',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(app/'MacDock.qml',backup/'MacDock.qml')
    settings=config/'macdock/settings.json'
    if settings.exists():shutil.copy2(settings,backup/'settings.json')
    if mode=='--plugin-remove':
        subprocess.run([sys.executable,str(ROOT/'tools/restore_legacy_bar.py')],check=True)
        subprocess.run(['noctalia','msg','plugins','disable','wenwu/macdock'],check=True)
        if target.exists():shutil.rmtree(target)
        print('Plugin removed; MacDock and user settings retained. Backup:',backup)
        return
    subprocess.run(['noctalia','plugins','lint',str(ROOT/'noctalia/plugin')],check=True)
    # Update only recognized previous files; refuse to overwrite unrelated local edits.
    bases=json.loads((ROOT/'tools/glass-update-bases.json').read_text())
    replacements={}
    for name in ('MacDock.qml','shell.qml'):
        old=(app/name).read_bytes()
        comparison=old
        if name=='shell.qml':comparison=re.sub(rb'^//@ pragma IconTheme .+$',b'//@ pragma IconTheme MacOS-Like-Dark',old,flags=re.M)
        new=(ROOT/'app/MacDock'/name).read_bytes()
        if hashlib.sha256(comparison).hexdigest() not in (bases[name] if isinstance(bases[name],list) else [bases[name]]) and comparison != new:
            raise RuntimeError('Local changes in '+name+'; merge before updating')
        if name=='shell.qml':
            theme=re.search(rb'^//@ pragma IconTheme .+$',old,re.M)
            if theme:new=re.sub(rb'^//@ pragma IconTheme .+$',lambda _:theme.group(),new,flags=re.M)
        replacements[name]=new
        shutil.copy2(app/name,backup/name)
    helper=app/'config_store.py'
    if helper.exists():shutil.copy2(helper,backup/'config_store.py')
    replacements['config_store.py']=(ROOT/'app/MacDock/config_store.py').read_bytes()
    runtime=(ROOT/'tools/runtime.py').read_bytes()
    installed_runtime=app/'runtime.py'
    if installed_runtime.exists():
        old=installed_runtime.read_bytes()
        legacy=runtime.replace(b"[qs, '-n', '-c', 'MacDock']",b"[qs, '-c', 'MacDock']")
        if old not in (runtime,legacy):raise RuntimeError('Local changes in runtime.py; merge before updating')
        shutil.copy2(installed_runtime,backup/'runtime.py')
        replacements['runtime.py']=runtime
    for name,source in (('integration_cleanup.py',ROOT/'bridge/integration_cleanup.py'),('noctalia_config.py',ROOT/'bridge/noctalia_config.py'),('wayland_probe.py',ROOT/'bridge/wayland_probe.py')):
        refuse_symlink(app/name)
        if (app/name).exists():shutil.copy2(app/name,backup/name)
        replacements[name]=source.read_bytes()
    replacements['DockGlassPanel.qml']=(ROOT/'app/MacDock/DockGlassPanel.qml').read_bytes()
    if (app/'DockGlassPanel.qml').exists():shutil.copy2(app/'DockGlassPanel.qml',backup/'DockGlassPanel.qml')
    stage=Path(tempfile.mkdtemp(prefix='macdock-release-'))
    staged_plugin=stage/'plugin'
    shutil.copytree(ROOT/'noctalia/plugin',staged_plugin)
    for name in ('bridge.py','dock_process.py','settings_store.py','monitors.py','native_blur.py','options.py','wayland_probe.py','noctalia_config.py','icon_theme.py','applications.py'):
        shutil.copy2(ROOT/'bridge'/name,staged_plugin/name)
    shutil.copy2(ROOT/'app/MacDock/config_store.py',staged_plugin/'config_store.py')
    for file in staged_plugin.glob('*.py'):compile(file.read_text(),str(file),'exec')
    subprocess.run(['noctalia','plugins','lint',str(staged_plugin)],check=True)
    staged_app=stage/'dock'
    shutil.copytree(app,staged_app)
    for name,content in replacements.items():(staged_app/name).write_bytes(content)
    formatter=shutil.which('qmlformat') or '/usr/lib/qt6/bin/qmlformat'
    for file in staged_app.glob('*.qml'):
        subprocess.run([formatter,'-n',str(file)],stdout=subprocess.DEVNULL,check=True)
    qml=app/'MacDock.qml'   
    log=Path.home()/'.cache/noctalia/noctalia.log'
    log_offset=log.stat().st_size if log.exists() else 0
    try:
        subprocess.run(['noctalia','msg','plugins','disable','wenwu/macdock'],check=True)
        subprocess.run(['systemctl','--user','stop','macdock.service'],check=True)
        # Restore only journal-owned old Bar changes before retiring their helpers.
        subprocess.run([sys.executable,str(ROOT/'tools/restore_legacy_bar.py')],check=True)
        sys.path.insert(0,str(ROOT/'tools'))
        sys.path.insert(0,str(ROOT/'bridge'))
        import migrate_native
        migrate_native.migrate(settings)
        import noctalia_config,settings_store
        existing=json.loads(settings.read_text()) if settings.exists() else {}
        legacy={} if existing.get('settingsStorageVersion')==1 else noctalia_config.get(['plugin_settings']).get('wenwu/macdock',{})
        if legacy:
            (backup/"plugin-settings.json").write_text(json.dumps(legacy,ensure_ascii=False,indent=2)+"\n")
            from bridge import atomic_merge
            retained={('dockEnabled' if k=='enabled' else k):v for k,v in legacy.items() if k in settings_store.DEFAULTS}
            atomic_merge(settings,dict(retained,settingsStorageVersion=1))
        elif existing.get('settingsStorageVersion')!=1:
            from bridge import atomic_merge
            atomic_merge(settings,{'settingsStorageVersion':1})
        holding=app.with_name(app.name+'.update-previous')
        if holding.exists():raise RuntimeError('Previous update holding directory exists: '+str(holding))
        app.rename(holding)
        try:shutil.copytree(staged_app,app)
        except BaseException:
            if app.exists():shutil.rmtree(app)
            holding.rename(app)
            raise
        shutil.rmtree(holding)
        if target.exists():shutil.rmtree(target)
        shutil.copytree(staged_plugin,target)
        subprocess.run(['noctalia','msg','plugins','enable','wenwu/macdock'],check=True)
        # Reconcile live hosts after source replacement; enable alone can be a no-op.
        subprocess.run(['noctalia','msg','config-reload'],check=True)
        subprocess.run(['systemctl','--user','restart','macdock.service'],check=True)
        import deployment_probe
        deployment_probe.verify(log_offset=log_offset)
        # Verify disk contents rather than treating lint/enable as installation proof.
        for name,content in replacements.items():
            if (app/name).read_bytes()!=content:raise RuntimeError('Installed Dock verification failed: '+name)
        for source in (ROOT/'noctalia/plugin').rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts:
                installed=target/source.relative_to(ROOT/'noctalia/plugin')
                if not installed.is_file() or installed.read_bytes()!=source.read_bytes():raise RuntimeError('Installed plugin verification failed: '+str(installed))
        if not (target/'widget.luau').is_file():raise RuntimeError('Installed widget entry missing')
        for name in ('integration_bar_style.py','bar_glass.py','native_rules.py','MenuBorder.qml','GlassCapture.qml','LiveWall.qml','DockPreferences.qml','GlassShape.js','dockglass.frag','liquidglass.frag','dockglass.frag.qsb','liquidglass.frag.qsb'):
            old=app/name
            if old.exists():shutil.copy2(old,backup/name);old.unlink()
    except BaseException:
        if (backup/'settings.json').exists():shutil.copy2(backup/'settings.json',settings)
        elif settings.exists():settings.unlink()
        if app.exists():shutil.rmtree(app)
        shutil.copytree(backup/'complete-dock',app)
        if target.exists():shutil.rmtree(target)
        if (backup/'plugin').exists():shutil.copytree(backup/'plugin',target)
        for command in (['noctalia','msg','plugins','enable','wenwu/macdock'],['noctalia','msg','config-reload'],['systemctl','--user','restart','macdock.service']):
            result=subprocess.run(command,capture_output=True,text=True)
            if result.returncode:print('Rollback restart failed: '+(result.stderr or result.stdout),file=sys.stderr)
        shutil.rmtree(stage,ignore_errors=True)
        raise
    shutil.rmtree(stage,ignore_errors=True)
    print('Installed Dock:',app)
    print('Installed plugin:',target)
    print('Verified widget: wenwu/macdock:widget (manifest and widget.luau match source)')
    print('Installed. Backup:',backup)
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,subprocess.SubprocessError) as e:sys.exit(str(e))
