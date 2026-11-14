"""Post-install acceptance for the real session. Failure must trigger rollback."""
import json,subprocess,time,os,sys
from pathlib import Path

def verify(log_offset=None, check_settings=True):
    error='Dock IPC unavailable'
    for _ in range(20):
        result=subprocess.run(['qs','-c','MacDock','ipc','call','health','ready'],capture_output=True,text=True,timeout=5)
        try:
            health=json.loads(result.stdout)
            if result.returncode==0 and health.get('app')=='MacDock' and health.get('ready') and health.get('items',0)>0:
                data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
                if check_settings:
                    subprocess.run([sys.executable,str(data/'noctalia/plugins/macdock/bridge.py'),'settings'],capture_output=True,text=True,check=True,timeout=10)
                for _toggle in range(2):
                    subprocess.run(['noctalia','msg','panel-toggle','wenwu/macdock:control'],capture_output=True,text=True,check=True,timeout=5)
                    time.sleep(.5)
                log=Path.home()/'.cache/noctalia/noctalia.log'
                if log_offset is not None and log.exists():
                    with log.open('rb') as stream:stream.seek(min(log_offset,log.stat().st_size));recent=stream.read().decode(errors='replace')
                    errors=[line for line in recent.splitlines() if 'wenwu/macdock' in line and any(word in line for word in ('[ERR]','read undeclared','disabled after'))]
                    if errors:raise RuntimeError('MacDock runtime errors: '+'; '.join(errors[-5:]))
                return health
            error='Dock not ready or application model empty: '+result.stdout
        except ValueError:error=result.stderr or result.stdout or error
        time.sleep(.25)
    raise RuntimeError(error)
