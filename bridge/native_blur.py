"""Conservative live capability check; never labels a requested setting as rendered."""
import json
import shutil
import subprocess


def probe(opacity=None,target="dock"):
    if opacity is not None and opacity >= 1:
        return {'state':'Unavailable','reason':'Background opacity is 1.0; the opaque Dock hides compositor blur.'}
    try:
        option=subprocess.run(['hyprctl','-j','getoption','decoration:blur:enabled'],capture_output=True,text=True,timeout=3)
        if option.returncode:return {'state':'Unavailable','reason':'Hyprland IPC unavailable: '+(option.stderr or option.stdout).strip()}
        value=json.loads(option.stdout)
        if not value.get('int',value.get('bool',False)):return {'state':'Unavailable','reason':'Hyprland decoration.blur.enabled is disabled.'}
        layers=subprocess.run(['hyprctl','-j','layers'],capture_output=True,text=True,timeout=3)
        if layers.returncode:return {'state':'Unavailable','reason':'Cannot inspect live layer namespaces.'}
        data=json.loads(layers.stdout);names=[]
        def walk(v):
            if isinstance(v,dict):
                namespace=str(v.get('namespace',''))
                if (target=='dock' and namespace=='macdock'):names.append(namespace)
                for item in v.values():walk(item)
            elif isinstance(v,list):
                for item in v:walk(item)
        walk(data)
        if not names:return {'state':'Unavailable','reason':'No live '+target+' layer found.'}
        from wayland_probe import globals_available
        if 'ext_background_effect_manager_v1' not in globals_available():return {'state':'Unavailable','reason':'ext-background-effect-v1 is not advertised by the compositor.','namespaces':names}
        return {'state':'Supported','reason':'Native blur protocol available; layer-rule alpha thresholds and visual result still require verification.','namespaces':names}
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as e:
        return {'state':'Unavailable','reason':str(e)}
