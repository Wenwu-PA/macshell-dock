#!/usr/bin/env python3
"""Restore a validated pre-migration plugin + its QML snapshot; never replace user JSON."""
import argparse,datetime,json,os,re,shutil,subprocess,sys,tomllib
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(args):return subprocess.run(args,check=True,capture_output=True,text=True)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('backup',type=Path);args=parser.parse_args()
    run(['noctalia','msg','plugins','list']) # Fail before writes without the real session.
    source=args.backup.resolve();manifest=tomllib.loads((source/'plugin/plugin.toml').read_text())
    declared={s['key'] for s in manifest.get('setting',[])}
    for file in (source/'plugin').glob('*.luau'):
        reads=set(re.findall(r'getConfig\("([^"]+)"\)',file.read_text()))
        if reads-declared:raise RuntimeError('Inconsistent backup schema: '+str(file))
    widget=(source/'plugin/widget.luau').read_text()
    if 'barWidget.setGlyph' not in widget or 'noctalia.togglePanel("wenwu/macdock:control")' not in widget:raise RuntimeError('Backup has an incompatible widget')
    run(['noctalia','plugins','lint',str(source/'plugin')])
    config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')));data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    app=config/'quickshell/MacDock';plugin=data/'noctalia/plugins/macdock'
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');saved=source.parent/('before-recovery-'+stamp);saved.mkdir()
    shutil.copytree(app,saved/'dock');shutil.copytree(plugin,saved/'plugin');shutil.copytree(config/'macdock',saved/'user-settings')
    try:
        run(['noctalia','msg','plugins','disable','wenwu/macdock']);run(['systemctl','--user','stop','macdock.service'])
        shutil.rmtree(plugin);shutil.copytree(source/'plugin',plugin)
        # This historical snapshot contains only the changed QML. Other installed Dock helpers remain intact.
        text=(source/'MacDock.qml').read_text().replace('    readonly property bool glassRT: glassLive\n','')
        (app/'MacDock.qml').write_text(text)
        run(['noctalia','msg','plugins','enable','wenwu/macdock']);run(['noctalia','msg','config-reload']);run(['systemctl','--user','restart','macdock.service'])
        import deployment_probe
        health=deployment_probe.verify(check_settings=False)
        print('Recovery IPC ready:',json.dumps(health));print('Before-recovery backup:',saved)
        print('Visual acceptance still required. User settings and pins were not restored from an old backup.')
    except BaseException:
        run(['systemctl','--user','stop','macdock.service'])
        shutil.rmtree(app);shutil.copytree(saved/'dock',app);shutil.rmtree(plugin);shutil.copytree(saved/'plugin',plugin)
        for command in (['noctalia','msg','plugins','enable','wenwu/macdock'],['noctalia','msg','config-reload'],['systemctl','--user','restart','macdock.service']):
            result=subprocess.run(command,capture_output=True,text=True)
            if result.returncode:print('Recovery rollback command failed: '+result.stderr,file=sys.stderr)
        raise
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,subprocess.SubprocessError) as error:raise SystemExit(str(error))
