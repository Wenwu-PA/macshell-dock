"""Read-only display metadata and effective target selection; never persists preferences."""
import json
import subprocess

def connected():
    try:
        result=subprocess.run(['hyprctl','-j','monitors'],capture_output=True,text=True,timeout=3)
        value=json.loads(result.stdout) if result.returncode==0 else []
        return [m for m in value if isinstance(m,dict) and isinstance(m.get('name'),str)] if isinstance(value,list) else []
    except (OSError,ValueError,subprocess.SubprocessError):return []

def resolve(preferred, outputs):
    if preferred=='':return '' # Explicit all-monitors selection, including existing installs.
    names=[o['name'] for o in outputs if isinstance(o,dict) and isinstance(o.get('name'),str)]
    if preferred!='@auto' and preferred in names:return preferred
    if not names:return ''
    metadata=[m for m in connected() if m['name'] in names]
    primary=[m['name'] for m in metadata if m.get('primary') is True]
    if len(primary)==1:return primary[0]
    focused=[m['name'] for m in metadata if m.get('focused') is True]
    return focused[0] if len(focused)==1 else names[0]
