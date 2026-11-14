"""Explicit restart of the MacDock configuration only; no process-name termination."""
import json,time
HEALTH=['qs','-c','MacDock','ipc','call','health','ready']
def restart(run):
    active=run(['systemctl','--user','is-active','macdock.service']).returncode==0
    if active:
        result=run(['systemctl','--user','restart','macdock.service'])
    else:
        if run(HEALTH).returncode==0:
            stopped=run(['qs','-c','MacDock','ipc','call','lifecycle','stop'])
            if stopped.returncode:raise RuntimeError('Cannot stop current MacDock: '+(stopped.stderr or stopped.stdout))
            for _ in range(20):
                if run(HEALTH).returncode!=0:break
                time.sleep(.25)
            else:raise RuntimeError('Old MacDock still responds; refusing to start a duplicate')
        result=run(['systemctl','--user','start','macdock.service'])
    if result.returncode:raise RuntimeError('macdock.service: '+(result.stderr or result.stdout))
    reason='MacDock did not become ready'
    for _ in range(24):
        result=run(HEALTH)
        try:
            health=json.loads(result.stdout)
            if result.returncode==0 and health.get('app')=='MacDock' and health.get('ready') and health.get('items',0)>0:return health
            reason='MacDock is not ready or its application model is empty'
        except ValueError:reason=result.stderr or result.stdout or reason
        time.sleep(.25)
    cleanup=run(['systemctl','--user','stop','macdock.service'])
    raise RuntimeError('Restart failed: '+reason+('; stop failed: '+cleanup.stderr if cleanup.returncode else ''))
