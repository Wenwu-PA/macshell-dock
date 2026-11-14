"""Owned, runtime-only Hyprland Lua rules. Never edits or disables user rules."""
import json
from pathlib import Path
import re
import subprocess


def lua_string(text):
    return 'string.char('+','.join(str(n) for n in text.encode('utf-8'))+')'


def script(names, enabled):
    for name in names:
        if not name.startswith('noctalia-bar-'):raise ValueError('Only Noctalia Bar namespaces are allowed')
    desired='{'+','.join('['+lua_string(name)+']={pattern='+lua_string('^'+re.escape(name)+'$')+'}' for name in names)+'}'
    blur='true' if enabled else 'false'
    return '''local key="__wenwu_macdock_bar_rules_v1"
local owned=rawget(_G,key) or {}; rawset(_G,key,owned)
local desired='''+desired+'''
local enabled='''+blur+'''
for name,entry in pairs(owned) do
 if entry.on then entry.on:set_enabled(false) end
 if entry.off then entry.off:set_enabled(false) end
end
for name,spec in pairs(desired) do
 local entry=owned[name] or {}; owned[name]=entry
 local mode=enabled and "on" or "off"
 if not entry[mode] then
  entry[mode]=hl.layer_rule({name="wenwu-macdock-integration-"..name.."-"..mode,match={namespace=spec.pattern},blur=enabled,ignore_alpha=0.0})
 else entry[mode]:set_enabled(true) end
end'''



def apply(names,enabled,journal):
    from bar_style import atomic
    atomic(journal,{'names':names}) # rollback receipt; no user configuration here
    r=subprocess.run(['hyprctl','eval',script(names,enabled)],capture_output=True,text=True,timeout=5)
    if r.returncode or 'error' in (r.stdout+r.stderr).lower():raise RuntimeError('Hyprland layer-rule update failed: '+r.stdout+r.stderr)


def clear(journal):
    if not journal.exists():return
    r=subprocess.run(['hyprctl','eval',script([],False)],capture_output=True,text=True,timeout=5)
    if r.returncode or 'error' in (r.stdout+r.stderr).lower():raise RuntimeError('Could not disable owned Bar rules: '+r.stdout+r.stderr)
    journal.unlink()
