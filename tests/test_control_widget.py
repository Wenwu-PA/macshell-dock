import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"bridge"))
import json,shutil,subprocess,tempfile,tomllib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ControlWidget(unittest.TestCase):
 def test_schema_separate_widget_and_panel(self):
  manifest=tomllib.loads((ROOT/'noctalia/plugin/plugin.toml').read_text())
  self.assertEqual(manifest['widget'][0]['id'],'widget');self.assertEqual(manifest['panel'][0]['id'],'control')
  self.assertTrue(all(s.get('advanced') for s in manifest.get('setting',[])))
 @unittest.skipUnless(shutil.which('lua'),'Lua interpreter unavailable')
 def test_widget_toggle_and_panel_draft_commit(self):
  cfg=dict(__import__('settings_store').DEFAULTS)
  def literal(value):
   if isinstance(value,dict):return '{'+','.join('['+json.dumps(k)+']='+literal(v) for k,v in value.items())+'}'
   if isinstance(value,bool):return str(value).lower()
   return json.dumps(value)
  script='local cfg='+literal(cfg)+'\n'+r'''
local tree=nil
local writes=0
local toggles=0
ui=setmetatable({}, {__index=function(_,kind) return function(props,children) props.kind=kind;props.children=children;return props end end})
panel={render=function(value) tree=value end}
noctalia={getConfig=function(k)assert(cfg[k]~=nil,"undeclared setting: "..k);return cfg[k] end,setUpdateInterval=function()end,
 outputs=function()return {{name='A',width=2560,height=1440}}end,
 pluginDir=function()return '.' end,log=function()end,openSettings=function()end,
 togglePanel=function(id)assert(id=='wenwu/macdock:control');toggles=toggles+1 end,
 json={encode=function(v)return v end,decode=function(v)return v end}}
noctalia.runAsync=function(args,callback)
 local action=args[3];local payload=args[4];local response={}
 if action=='settings' then response=cfg
 elseif action=='set' then
  writes=writes+1
  for k,v in pairs(payload)do cfg[k]=v;response={saved=true,key=k,value=v}end
 elseif action=='status' then response={app='MacDock',ready=true}
 elseif action=='monitors' then response={{name='A',width=2560,height=1440,refreshRate=165}}
 elseif action=='blur-status' then response={state='Supported',reason='protocol available'} end
 if callback then callback({exitCode=0,stdout=response,stderr='',timedOut=false})end
 return true
end
assert(widget==nil)
barWidget={setGlyph=function(v)assert(v~='')end,setText=function(v)assert(v=='')end,setTooltip=function(v)assert(v=='MacDock Control')end}
'''
  script+='dofile('+json.dumps(str(ROOT/'noctalia/plugin/widget.luau'))+')\nonClick();onClick();assert(toggles==2)\n'
  script+='dofile('+json.dumps(str(ROOT/'noctalia/plugin/panel.luau'))+')\nonOpen({})\n'+r'''
local function find(node,key)
 if node.key==key then return node end
 for _,child in ipairs(node.children or {})do local result=find(child,key);if result then return result end end
end
local slider=find(tree,'iconSize');assert(slider)
slider.onChange(64);assert(writes==0)
slider=find(tree,'iconSize');assert(slider.value==64)
slider.onDragEnd();assert(writes==1 and cfg.iconSize==64)
local picker=find(tree,'display-picker');assert(picker.options[1]=='Auto')
assert(string.find(picker.options[2],'165 Hz',1,true))
picker.onChange(1);assert(cfg.monitor=='A')
onOutputsChanged();assert(find(tree,'display-picker').selectedIndex==1)
'''
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'test.lua';p.write_text(script);r=subprocess.run(['lua',str(p)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
 @unittest.skipUnless(shutil.which('noctalia'),'Noctalia unavailable')
 def test_real_noctalia_registry_accepts_all_lanes(self):
  import os
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);target=base/'data/noctalia/plugins/macdock';shutil.copytree(ROOT/'noctalia/plugin',target)
   env=dict(os.environ,XDG_DATA_HOME=str(base/'data'),NOCTALIA_DATA_HOME=str(base/'data'),XDG_CONFIG_HOME=str(base/'config'),XDG_STATE_HOME=str(base/'state'))
   for lane in ('start','center','end'):
    cfg=base/'candidate.toml';cfg.write_text('[plugins]\nenabled=["wenwu/macdock"]\n[widget.macdock_control]\ntype="wenwu/macdock:widget"\ncapsule=true\n[bar.default]\n'+lane+'=["macdock_control"]\n[[bar.default.capsule_group]]\nid="dock_controls"\nmembers=["macdock_control"]\n')
    r=subprocess.run(['noctalia','config','validate',str(cfg)],env=env,capture_output=True,text=True)
    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    self.assertNotIn('unrecognized widget',r.stdout+r.stderr)
    self.assertNotIn('WARN',r.stdout+r.stderr)
