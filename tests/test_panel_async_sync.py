import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PanelAsyncSync(unittest.TestCase):
 @unittest.skipUnless(shutil.which('lua'),'Lua unavailable')
 def test_async_order_external_edits_reopen_and_all_controls(self):
  import sys
  sys.path.insert(0,str(ROOT/'bridge'))
  from settings_store import DEFAULTS
  def lua(v):
   if isinstance(v,dict):return '{'+','.join('['+json.dumps(k)+']='+lua(x) for k,x in v.items())+'}'
   if isinstance(v,bool):return str(v).lower()
   return json.dumps(v)
  source='local cfg='+lua(DEFAULTS)+'\n'+r'''
local function copy(t)local o={} for k,v in pairs(t)do o[k]=type(v)=='table' and copy(v) or v end return o end
local reads,writes={},{}
local tree
ui=setmetatable({}, {__index=function(_,kind)return function(props,children)props.kind=kind;props.children=children;return props end end})
panel={render=function(t)tree=t end}
noctalia={setUpdateInterval=function()end,pluginDir=function()return '.'end,log=function()end,
 outputs=function()return {{name='A',width=2560,height=1440}}end,json={encode=function(v)return v end,decode=function(v)return v end}}
noctalia.runAsync=function(args,callback)
 local action=args[3]
 if action=='settings' then table.insert(reads,{callback=callback,value=copy(cfg)})
 elseif action=='set' then table.insert(writes,{callback=callback,patch=args[4]})
 else
  local data=action=='status' and {app='MacDock'} or action=='blur-status' and {state='Supported'} or {}
  callback({exitCode=0,stdout=data,stderr='',timedOut=false})
 end
 return true
end
local function finishRead(index)
 local r=table.remove(reads,index or #reads);r.callback({exitCode=0,stdout=r.value,stderr='',timedOut=false})
end
local function finishWrite(error)
 local w=table.remove(writes,1);local response
 for k,v in pairs(w.patch)do if not error then cfg[k]=v end response={saved=true,key=k,value=v} end
 w.callback({exitCode=error and 1 or 0,stdout=error and '' or response,stderr=error and 'write rejected' or '',timedOut=false})
end
local function find(node,key)
 if node.key==key then return node end
 for _,child in ipairs(node.children or {})do local result=find(child,key);if result then return result end end
end
local function contains(node,text)
 if type(node.text)=='string' and string.find(node.text,text,1,true)then return true end
 for _,child in ipairs(node.children or {})do if contains(child,text)then return true end end
 return false
end
local function toggle(node,label)
 for _,child in ipairs(node.children or {})do
  if child.kind=='row' and child.children and child.children[1].text==label then return child.children[2] end
  local result=toggle(child,label);if result then return result end
 end
end
'''
  source+='dofile('+json.dumps(str(ROOT/'noctalia/plugin/panel.luau'))+')\nonOpen({})\n'+r'''
-- Opening requests must supersede an older initial-load snapshot.
cfg.iconSize=60
onOpen({});finishRead();assert(find(tree,'iconSize').value==60)
while #reads>0 do finishRead(1)end
assert(find(tree,'iconSize').value==60)
-- Last draft wins even when a previous write is still running.
local s=find(tree,'iconSize');s.onChange(64);assert(find(tree,'iconSize').value==64);s.onDragEnd()
find(tree,'iconSize').onChange(68);find(tree,'iconSize').onDragEnd();assert(#writes==1)
finishWrite();assert(find(tree,'iconSize').value==68 and #writes==1)
finishWrite();finishRead();assert(cfg.iconSize==68 and find(tree,'iconSize').value==68)
-- An in-flight old read cannot replace a new edit, even after its commit.
update();find(tree,'iconSize').onChange(72);find(tree,'iconSize').onDragEnd()
finishWrite();finishRead();finishRead(1);assert(find(tree,'iconSize').value==72)
for key,value in pairs({iconSize=64,spacing=10,glassOpacity=.75})do
 find(tree,key).onChange(value);assert(find(tree,key).value==value)
 find(tree,key).onDragEnd();finishWrite();finishRead();assert(find(tree,key).value==value)
end
-- Toggles, autostart and dropdowns use the same writer/readback.
for label,key in pairs({['Enable Dock']='enabled',['Autostart']='automatic'})do
 toggle(tree,label).onChange(false);finishWrite();finishRead();assert(cfg[key]==false and toggle(tree,label).checked==false)
end
find(tree,'display-picker').onChange(1);finishWrite();finishRead();assert(cfg.monitor=='A')

-- Errors revert the draft, show failure, and do not claim Saved.
find(tree,'iconSize').onChange(80);find(tree,'iconSize').onDragEnd();finishWrite(true);finishRead()
assert(find(tree,'iconSize').value==64 and contains(tree,'write rejected'))
-- External change (including a Dock restart's write) is picked up by the existing update cycle.
cfg.iconSize=76;cfg.glassOpacity=.6;update();finishRead()
assert(find(tree,'iconSize').value==76 and find(tree,'glassOpacity').value==.6)
assert(find(tree,'settings-root'));assert(not find(tree,'settings-scroll'))
-- Reopen loads disk again, not a cached draft.
find(tree,'iconSize').onChange(90);onOpen({});finishRead();assert(find(tree,'iconSize').value==76)
'''
  with tempfile.TemporaryDirectory() as d:
   file=Path(d)/'test.lua';file.write_text(source)
   result=subprocess.run(['lua',str(file)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
