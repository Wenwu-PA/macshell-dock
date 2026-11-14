"""Read XDG desktop entries and edit the existing pin list with compare-and-swap."""
import configparser
import json
import os
from pathlib import Path


def catalog():
    roots = [Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))]
    roots += [Path(p) for p in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':') if p]
    entries, seen = [], set()
    for root in roots:
        directory = root/'applications'
        for path in sorted(directory.rglob('*.desktop')):
            desktop_id = str(path.relative_to(directory)).replace(os.sep, '-')[:-8]
            if desktop_id in seen: continue
            seen.add(desktop_id)  # Hidden user entries mask system entries.
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                cp.read(path, encoding='utf-8')
                e = cp['Desktop Entry']
                if e.get('Type') != 'Application' or e.getboolean('Hidden',False) or e.getboolean('NoDisplay',False): continue
                entries.append({'id': desktop_id, 'name': e.get('Name',desktop_id), 'icon': e.get('Icon',''), 'startupClass': e.get('StartupWMClass','')})
            except (OSError, UnicodeError, ValueError, KeyError, configparser.Error): continue
    return sorted(entries, key=lambda e:(e['name'].casefold(),e['id']))


def canonical(value, entries):
    # Exact IDs win: org.telegram.desktop is an ID, not a filename suffix.
    for field in ('id','startupClass'):
        matches=[e['id'] for e in entries if e.get(field) and e[field].casefold()==value.casefold()]
        if len(matches)==1:return matches[0]
    if value.endswith('.desktop'):
        matches=[e['id'] for e in entries if e['id'].casefold()==value[:-8].casefold()]
        if len(matches)==1:return matches[0]
    return value


def normalized(pins, entries):
    result=[];seen=set()
    for pin in pins:
        value=canonical(pin,entries)
        if value.casefold() not in seen:result.append(value);seen.add(value.casefold())
    return result


def read_pins(path):
    pins = json.loads(path.read_text()) if path.exists() else []
    if not isinstance(pins,list) or not all(isinstance(p,str) for p in pins): raise ValueError('Invalid pinned.json')
    return pins


def edit(path, request):
    from config_store import write
    expected = request.get('expected')
    if isinstance(expected,str): expected=json.loads(expected)
    if not isinstance(expected,list) or not all(isinstance(p,str) for p in expected): raise ValueError('Missing pin snapshot; refresh the list')
    result = list(expected)
    entries=catalog()
    action = request.get('action')
    if action == 'add':
        app = request.get('id')
        if app not in {e['id'] for e in entries}: raise ValueError('Desktop entry is no longer installed')
        if app not in normalized(result,entries): result.append(app)
    elif action in ('remove','up','down'):
        index = request.get('index')
        if type(index) is not int or not 0 <= index < len(result): raise ValueError('Invalid pin index')
        if action == 'remove':
            selected=canonical(result[index],entries)
            result=[p for p in result if canonical(p,entries).casefold()!=selected.casefold()]
        else:
            target = index + (-1 if action == 'up' else 1)
            if not 0 <= target < len(result): raise ValueError('Pin is already at the edge')
            result[index],result[target] = result[target],result[index]
    else: raise ValueError('Invalid pin action')
    result=normalized(result,entries)
    write(path,result,expected)
    return result
