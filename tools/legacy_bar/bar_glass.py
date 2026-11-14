"""Optional native backend, using the existing same-user Noctalia IPC socket.

The P6 backdrop is static. No screenshots, secondary renderer, config file or polling
service is created. Short readiness polling occurs only when applying an effect.
"""
import json
import time
from pathlib import Path
import noctalia_config


def command(action='status', bar='default', **parameters):
    raw = noctalia_config.invoke(['macdock-glass', json.dumps(dict(action=action, bar=bar, **parameters), ensure_ascii=False)])
    try: result = json.loads(raw)
    except ValueError as error: raise RuntimeError('Experimental Bar backend returned invalid JSON: '+raw[:200]) from error
    if result.get('backend') != 1: raise RuntimeError('Compatible experimental Noctalia backend is not running')
    return result


def parameters(config):
    path = config.get('barGlassBackdrop', '')
    if not isinstance(path, str) or not Path(path).is_absolute() or not Path(path).is_file():
        raise ValueError('Bar Liquid Glass requires an absolute static P6 backdrop path')
    result = {'backdrop': path}
    for key, native, default, maximum in [
        ('barGlassRefraction','refraction',12,80), ('barGlassBlur','blur',3,24),
        ('barGlassDispersion','dispersion',.25,2), ('barGlassHighlight','highlight',.09,.3),
        ('barGlassTint','tint',.15,1), ('barGlassOpacity','opacity',.85,1)]:
        value = config.get(key,default)
        if type(value) not in (int,float) or not 0 <= value <= maximum: raise ValueError('Invalid '+key)
        result[native] = value
    result['quality'] = config.get('barGlassQuality','balanced')
    if result['quality'] not in ('low','balanced','high'): raise ValueError('Invalid Bar shader quality')
    return result


def activate(bar, config):
    return activate_parameters(bar,parameters(config))


def activate_parameters(bar,params):
    reply = command('apply', bar, **params)
    for _ in range(30):
        if reply['state'] == 'ready': return reply
        if reply['state'] == 'failed': raise RuntimeError('Bar shader failed: '+reply.get('error','unknown error'))
        time.sleep(.1)
        reply = command('status',bar)
    raise RuntimeError('Bar shader not rendered within 3s (hidden Bar, unsupported geometry or renderer); previous appearance restored')


def disable_owned(journal):
    path = journal.with_name('bar-glass-owned.json')
    if not path.exists(): return
    for name in json.loads(path.read_text())['bars']:
        try: command('disable',name)
        except RuntimeError as error:
            # A stock fallback shell cannot own this material. Confirm it is live before
            # removing ownership; missing IPC must preserve the journal for a later retry.
            if 'unknown command' not in str(error): raise
            noctalia_config.get(['bar'])
    path.unlink()
