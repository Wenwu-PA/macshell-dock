"""Reversible native Noctalia Bar styling. This is compositor blur, not refraction."""
from noctalia_config import equivalent
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib


def run(argv):
    r=subprocess.run(argv,capture_output=True,text=True,timeout=15)
    if r.returncode:raise RuntimeError(r.stderr.strip() or 'Noctalia IPC failed')
    return r.stdout


def atomic(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.bar-')
    try:
        with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def effective():
    from noctalia_config import get
    return {'bar': get(['bar'])}


def read(config, segments):
    value=config
    for part in segments:value=value[part]
    return value


def set_value(segments,value):
    import noctalia_config
    noctalia_config.set_value(segments,value)


def _restore(journal):
    import bar_glass
    bar_glass.disable_owned(journal)
    import native_rules
    native_rules.clear(journal.with_name('bar-native-rules.json'))
    if not journal.exists():return
    record=json.loads(journal.read_text());current=effective();conflicts=[]
    for item in reversed(record['changes']):
        try:value=read(current,item['path'])
        except KeyError:conflicts.append(item);continue
        if equivalent(value,item['before']):continue
        if not equivalent(value,item['after']) and not equivalent(value,item.get('pending_before',item['after'])):
            conflicts.append(item);continue
        set_value(item['path'],item['before'])
    if conflicts:
        record['changes']=list(reversed(conflicts));atomic(journal,record)
        raise RuntimeError('Bar restoration conflict: settings changed externally; original values retained in '+str(journal))
    journal.unlink()


def _apply(config,journal):
    if config.get('barMode','unchanged')=='unchanged':_restore(journal);return
    mode=config.get('barMode')
    if mode not in ('compositor','solid','transparent','liquid'):raise ValueError('Unsupported Bar effect')
    opacity=config.get('unifiedOpacity',.42) if config.get('unified') else config.get('barOpacity',.42)
    if mode=='solid':opacity=1.0
    elif mode=='transparent':opacity=0.0
    radius=config.get('cornerRadius',18) if config.get('unified') else config.get('barRadius',12)
    if type(opacity) not in (int,float) or not 0<=opacity<=1:raise ValueError('Invalid Bar opacity')
    if type(radius) not in (int,float) or not 0<=radius<=80:raise ValueError('Invalid Bar radius')
    from bar_capability import probe
    if mode=='compositor':
        capability=probe(opacity)
        if capability['state']!='Supported':raise RuntimeError('Bar Blur '+capability['state']+': '+capability['reason'])
    bars=effective().get('bar',{})
    names=config.get('barNames',[])
    # Noctalia 5.4.1 luaToJson emits {} for an empty Luau table, including string_list [].
    if names == {}: names = []
    if not isinstance(names,list) or not all(isinstance(n,str) for n in names):raise ValueError('Invalid Bar names')
    selected=names or [name for name,b in bars.items() if isinstance(b,dict) and b.get('position')=='top' and b.get('enabled',True)]
    if mode == 'liquid':
        import bar_glass
        # Current renderer owns one texture: allow multiple outputs of one Bar, not competing Bars.
        if len(selected) != 1: raise ValueError('Experimental Liquid Glass requires exactly one selected Bar')
        bar_glass.parameters(config)
        previous_glass = bar_glass.command('status', selected[0])  # Fail before any settings/rules writes on stock Noctalia.
    desired=[]
    for name in selected:
        bar=bars.get(name)
        if not isinstance(bar,dict) or bar.get('position')!='top':raise ValueError('Selected Bar is not a top Bar: '+name)
        patches={'background_opacity':opacity,'compositor_blur':mode=='compositor','radius':radius}
        if mode == 'liquid':
            # Glass alpha is an independent uniform. Retain the user's background alpha for fallback.
            patches['background_opacity'] = bar['background_opacity']
            if bar.get('concave_edge_corners') or any(o.get('concave_edge_corners') for o in bar.get('monitor',{}).values() if isinstance(o,dict)):
                if not config.get('barGlassConvex',False):
                    raise ValueError('Bar has concave corners: enable experimental convex-corner compatibility first')
            if config.get('barGlassConvex',False) and 'concave_edge_corners' in bar:
                patches['concave_edge_corners'] = False
        if config.get('unified'):
            patches.update(border_width=config.get('borderWidth',.25),border='#ffffff'+format(round(config.get('borderOpacity',.12)*255),'02x'))
            # Noctalia 5.4.1 Bar uses ColorRole::Surface; no per-Bar color key exists.
            # Keep the native palette instead of aborting all writes on a fabricated key.
            if config.get('tintMode')=='custom' and 'color' in bar:patches['color']=config['backgroundTint']
        # Explicit corners override radius. Touch only corners actually exposed by this version.
        patches.update({k:radius for k in ('radius_top_left','radius_top_right','radius_bottom_left','radius_bottom_right') if k in bar})
        for field,value in patches.items():
            if field not in bar:raise ValueError('Unsupported Bar property '+field)
            desired.append((['bar',name,field],bar[field],value))
        for match,override in bar.get('monitor',{}).items():
            if not isinstance(override,dict) or not override.get('enabled',True) or override.get('position',bar['position'])!='top':continue
            # Only touch existing keys; omitted properties already inherit the base.
            for field,value in patches.items():
                if field in override:desired.append((['bar',name,'monitor',match,field],override[field],override[field] if mode == 'liquid' and field == 'background_opacity' else value))
    if not selected:raise RuntimeError('Bar Blur Unavailable: no enabled top Bar selected')
    if mode == 'compositor' and 'namespaces' in capability:
        missing = ['noctalia-bar-' + n for n in selected if 'noctalia-bar-' + n not in capability['namespaces']]
        if missing: raise RuntimeError('Selected Bar layer missing: ' + ', '.join(missing))
    record=json.loads(journal.read_text()) if journal.exists() else {'changes':[]}
    # Restore previous selection before switching bars, never silently leave an old bar styled.
    targets={tuple(p) for p,_,_ in desired}
    if any(tuple(i['path']) not in targets for i in record['changes']):
        _restore(journal);return _apply(config,journal)
    previous_record = json.loads(json.dumps(record))
    try:
        import bar_glass
        if mode != 'liquid': bar_glass.disable_owned(journal)
        import native_rules
        native_rules.apply(['noctalia-bar-'+name for name in selected],mode=='compositor',journal.with_name('bar-native-rules.json'))
        for path,before,after in desired:
            item=next((i for i in record['changes'] if i['path']==path),None)
            if item and not any(equivalent(before,v) for v in (item['after'],item['before'])):raise RuntimeError('Bar setting modified externally: '+'.'.join(path))
            if equivalent(before,after):continue
            if item is None:item={'path':path,'before':before,'after':after};record['changes'].append(item)
            else:item['pending_before']=before;item['after']=after
            atomic(journal,record) # write-ahead rollback record
            set_value(path,after)
            item.pop('pending_before',None)
            atomic(journal,record)
        if mode == 'liquid':
            atomic(journal.with_name('bar-glass-owned.json'), {'bars':selected})
            bar_glass.activate(selected[0],config)
    except BaseException as error:
        try:
            _restore(journal)
            if mode == 'liquid':
                # Return to the actual previously working native appearance, not an unrelated
                # old pre-integration baseline. Retain that baseline journal for later removal.
                for path,before,_ in desired:
                    set_value(path,before)
                if previous_record['changes']: atomic(journal,previous_record)
                native_rules.apply(['noctalia-bar-'+name for name in selected],
                    all(bars[name].get('compositor_blur',False) for name in selected),
                    journal.with_name('bar-native-rules.json'))
                if previous_glass.get('enabled') and previous_glass.get('state') == 'ready' and previous_glass.get('backdrop'):
                    old_parameters = {key:previous_glass[key] for key in ('backdrop','refraction','blur','dispersion','highlight','tint','opacity','quality')}
                    atomic(journal.with_name('bar-glass-owned.json'), {'bars':selected})
                    bar_glass.activate_parameters(selected[0],old_parameters)
        except Exception as rollback_error:
            raise RuntimeError(str(error)+'; rollback failed: '+str(rollback_error)) from error
        raise


def locked(journal, callback):
    journal.parent.mkdir(parents=True, exist_ok=True)
    with (journal.parent / '.bar.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return callback()


def restore(journal):
    return locked(journal, lambda: _restore(journal))


def apply(config, journal):
    def operation():
        receipt = journal.with_name('bar-apply-status.json')
        try:
            _apply(config, journal)
        except Exception as error:
            atomic(receipt, {'requested': config.get('barMode', 'unchanged'), 'error': str(error)})
            raise
        atomic(receipt, {'requested': config.get('barMode', 'unchanged'), 'error': ''})
    return locked(journal, operation)


def status(config, journal):
    """Read live IPC, not file export or requested mode, to report configured appearance.

    Even matching values prove configuration, not visually rendered blur.
    """
    requested = config.get('barMode', 'unchanged')
    result = {'requested': requested, 'applied': 'unknown', 'state': 'Unavailable',
              'reason': '', 'bars': [], 'availableBars': []}
    try:
        bars = effective().get('bar', {})
        result['availableBars'] = [name for name, bar in bars.items()
                                   if isinstance(bar, dict) and bar.get('position') == 'top']
        selected = config.get('barNames') or [name for name in result['availableBars']
                                             if bars[name].get('enabled', True)]
        rows = []
        for name in selected:
            if name not in result['availableBars']: raise RuntimeError('Selected top Bar not found: ' + name)
            bar = bars[name]
            if not bar.get('enabled', True): raise RuntimeError('Selected Bar is disabled: ' + name)
            variants = [('base', bar)] + [(monitor, dict(bar, **override))
                for monitor, override in bar.get('monitor', {}).items()
                if isinstance(override, dict) and override.get('enabled', bar.get('enabled', True))]
            for monitor, value in variants:
                opacity = value.get('background_opacity')
                blur = value.get('compositor_blur')
                if type(opacity) not in (int, float): raise RuntimeError('Missing background_opacity: ' + name)
                # Zero tint is not proof that an explicit compositor blur region is disabled.
                mode = 'solid' if opacity >= 1 else ('compositor' if blur else ('transparent' if opacity <= 0 else 'translucent'))
                rows.append({'name': name, 'monitor': monitor, 'mode': mode,
                             'opacity': opacity, 'compositor_blur': blur})
        if not rows: raise RuntimeError('No enabled top Bar selected')
        result['bars'] = rows
        modes = {row['mode'] for row in rows}
        result['applied'] = next(iter(modes)) if len(modes) == 1 else 'mixed'
        result['state'] = 'Configured'
        result['reason'] = 'Live Noctalia settings read back; visual rendering not verified.'
        if any(row['opacity'] == 0 and row['compositor_blur'] for row in rows):
            result['reason'] += ' Tint is transparent; blur is still requested and depends on the compositor region/rules.'
        if requested != 'unchanged' and result['applied'] != requested:
            result['state'] = 'Mismatch'
            result['reason'] = 'Selected mode differs from live Bar settings (including monitor overrides).'
        if requested == 'liquid':
            import bar_glass
            native = [bar_glass.command('status',name) for name in selected]
            ready = all(n.get('enabled') and n.get('state') == 'ready' for n in native)
            result['applied'] = 'liquid' if ready else result['applied']
            result['state'] = 'Ready' if ready else 'Unavailable'
            result['reason'] = 'Experimental · Static Backdrop; rendered GLES material, not live Waywallen.' if ready else '; '.join(n.get('error') or n.get('state','unknown') for n in native)
        if requested == 'compositor':
            from bar_capability import probe
            opacity = config.get('unifiedOpacity', .42) if config.get('unified') else config.get('barOpacity', .42)
            capability = probe(opacity)
            if capability['state'] != 'Supported':
                result['state'] = 'Unavailable'; result['reason'] = capability['reason']
            elif not all('noctalia-bar-' + name in capability.get('namespaces', []) for name in selected):
                result['state'] = 'Unavailable'; result['reason'] = 'Selected Bar namespace absent from live Hyprland layers.'
        receipt = journal.with_name('bar-apply-status.json')
        if receipt.exists():
            last = json.loads(receipt.read_text())
            if last.get('requested') == requested and last.get('error'):
                result['state'] = 'Error'; result['reason'] = last['error']
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        result['state'] = 'Unavailable'; result['reason'] = str(error)
    return result
