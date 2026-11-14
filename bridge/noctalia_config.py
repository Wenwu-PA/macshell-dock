"""Noctalia 5.4.1 IPC: keep quoted keys in the VALUE, not its broken path splitter."""
import json
import math
import re
import subprocess
import time
import tomllib


def literal(value):
    if type(value) is bool:return 'true' if value else 'false'
    if type(value) is int:return str(value)
    if type(value) is float:
        if not math.isfinite(value):raise ValueError('Non-finite TOML number')
        return repr(value)
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,list):return '['+', '.join(literal(v) for v in value)+']'
    if isinstance(value,dict):return '{ '+', '.join(literal(str(k))+' = '+literal(v) for k,v in value.items())+' }'
    raise ValueError('Unsupported TOML value')


def invoke(args):
    try:r=subprocess.run(['noctalia','msg',*args],capture_output=True,text=True,timeout=12)
    except subprocess.TimeoutExpired as e:raise RuntimeError(args[0]+': timed out after 12s') from e
    if r.returncode or r.stdout.lstrip().startswith('error:'):
        raise RuntimeError(f'{args[0]} exit={r.returncode}: stdout={r.stdout.strip()!r}; stderr={r.stderr.strip()!r}')
    return r.stdout.strip()


def get(parts):
    # A table-valued config-get prints TOML table contents. Only pass a bare root.
    raw=invoke(['config-get',parts[0]])
    try:table=tomllib.loads(raw)
    except tomllib.TOMLDecodeError as e:raise RuntimeError('config-get returned invalid TOML: '+raw[:500]) from e
    value=table
    for part in parts[1:]:
        if not isinstance(value,dict) or part not in value:raise RuntimeError('config-get: missing '+'.'.join(parts))
        value=value[part]
    return value


def equivalent(actual,expected):
    if type(actual) in (int,float) and type(expected) in (int,float):
        return math.isclose(actual,expected,rel_tol=1e-6,abs_tol=1e-7)
    return type(actual) is type(expected) and actual==expected


def set_value(parts,value):
    if len(parts)<2 or not re.fullmatch('[A-Za-z_][A-Za-z0-9_-]*',parts[0]):raise ValueError('Expected bare root and nested key')
    nested=value
    for part in reversed(parts[1:]):nested={part:nested}
    reply=invoke(['config-set',parts[0],literal(nested)])
    if reply!='ok':raise RuntimeError('config-set: unexpected acknowledgement '+repr(reply))
    actual=None
    read_error=None
    for attempt in range(6):
        try:
            actual=get(parts)
            read_error=None
        except RuntimeError as error:
            read_error=error
            time.sleep(.1)
            continue
        if equivalent(actual,value):return actual
        time.sleep(.1)
    if read_error:raise RuntimeError("Write acknowledged but readback failed: "+str(read_error))
    raise RuntimeError(f'config-get mismatch for {".".join(parts)}: requested={value!r}, effective={actual!r}')
