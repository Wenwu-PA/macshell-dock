"""Simulated Noctalia 5.4.1 IPC transport; real bridge and offscreen QML FileView.
The fake CLI deliberately reproduces v5.4.1's unquote/offset bug. This is not
an end-to-end test against the user's running Noctalia or graphical Dock.
"""
import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bridge'))
import noctalia_config as ipc
import bridge

FAKE = r'''#!/usr/bin/env python3
import json,os,shlex,sys,tomllib
from pathlib import Path
p=Path(os.environ['FAKE_SETTINGS'])
data=json.loads(p.read_text()) if p.exists() else {}
def merge(a,b):
 for k,v in b.items():
  if isinstance(v,dict):merge(a.setdefault(k,{}),v)
  else:a[k]=v
args=' '.join(sys.argv[3:])
tokens=shlex.split(args)
if sys.argv[2]=='config-set':
 path=tokens[0]
 value=args[len(path):].strip()
 try:delta=tomllib.loads(path+'='+value)
 except Exception as e:print('error: invalid TOML value: '+str(e));sys.exit(1)
 merge(data,delta);p.write_text(json.dumps(data));print('ok')
else:
 root=tokens[0]
 if root not in data:print('error: path not found');sys.exit(1)
 for plugin,values in data[root].items():
  print('['+json.dumps(plugin)+']')
  for key,v in values.items():print(key+' = '+json.dumps(v))
'''

def block(source,marker):
 start=source.index(marker);opening=source.index('{',start);level=1;i=opening+1
 # Production blocks used here contain no unmatched braces inside string literals.
 while level:
  level += (source[i]=='{')-(source[i]=='}');i+=1
 return source[start:i]

class SettingsPipeline(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='macdock pipeline тест ');self.base=Path(self.temp.name)
  bin=self.base/'bin';bin.mkdir();exe=bin/'noctalia';exe.write_text(FAKE);exe.chmod(0o755)
  self.env=patch.dict(os.environ,{'PATH':str(bin)+os.pathsep+os.environ['PATH'],'FAKE_SETTINGS':str(self.base/'effective.json'),'XDG_STATE_HOME':str(self.base/'state'),'XDG_CONFIG_HOME':str(self.base/'config')});self.env.start()
 def tearDown(self):self.env.stop();self.temp.cleanup()
 def save(self,key,value):
  r=subprocess.run([sys.executable,str(ROOT/'bridge/bridge.py'),'set',json.dumps({key:value})],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['saved'])
  return json.loads((self.base/'config/macdock/settings.json').read_text())[key]
 def test_legacy_path_fails_new_nested_value_preserves_siblings(self):
  r=subprocess.run(['noctalia','msg','config-set','plugin_settings."wenwu/macdock".iconSize','64'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('invalid TOML',r.stdout);self.assertEqual(r.stderr,'')
  self.assertEqual(self.save('iconSize',64.0),64)
  self.assertIs(type(self.save('iconSize',64.0)),int)
  for key,value in [('magnification',2.0),('glassOpacity',.75)]:self.assertEqual(self.save(key,value),value)
  self.assertFalse((self.base/'settings.json').exists())
  self.assertIs(type(self.save('magnification',2)),float)
 def test_stdout_error_and_readback_mismatch_reported(self):
  with patch.object(ipc.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'error: rejected','')):
   with self.assertRaisesRegex(RuntimeError,'rejected'):ipc.set_value(['plugin_settings','wenwu/macdock','iconSize'],64)
  with patch.object(ipc,'invoke',return_value='ok'),patch.object(ipc,'get',return_value=52),patch.object(ipc.time,'sleep'):
   with self.assertRaisesRegex(RuntimeError,'mismatch'):ipc.set_value(['plugin_settings','wenwu/macdock','iconSize'],64)
 @unittest.skipUnless(shutil.which('qs'),'Quickshell unavailable')
 def test_bridge_to_production_fileview_atomic_rename_and_restart(self):
  cfg=dict(__import__('settings_store').DEFAULTS)
  directory=self.base/'dock';directory.mkdir();path=directory/'settings.json'
  bridge.atomic_merge(path,bridge.adapt({'config':cfg}))
  source=(ROOT/'app/MacDock/MacDock.qml').read_text()
  watcher=block(source,'FileView {\n        id: settingsStore')
  apply=block(source,'function applySettings(o)')
  shell=self.base/'shell.qml'
  shell.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 id: root
 property string configDir: '''+json.dumps(str(directory))+'''
 property bool settingsReady: false
 property bool settingsLoading: false
 property var originalSettings: ({})
 property int iconSize: 52
 property real magnification: 1.7
 property real glassOpacity: .42
 property real glassBlur: 5
 property string dockStyle: "native"
 property var outputSettings: ({})
 property int readyTransitions: 0
 function startGlass() {}
 Timer { id: saveTimer }
 onSettingsReadyChanged: { readyTransitions++; console.log("READY="+readyTransitions) }
 Timer { interval: 40; running: true; repeat: true; onTriggered: console.log("VALUES="+JSON.stringify([root.iconSize,root.magnification,root.glassOpacity,root.dockStyle,root.glassBlur])) }
'''+apply+'\n'+watcher+'\n}')
  def launch():
   env=dict(os.environ,QT_QPA_PLATFORM='offscreen',XDG_RUNTIME_DIR=str(self.base))
   return subprocess.Popen(['qs','-p',str(shell),'--no-duplicate'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  def await_values(proc,expected):
   selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
   log='';end=time.monotonic()+8
   try:
    while time.monotonic()<end:
     if selector.select(.1):
      line=proc.stdout.readline();log+=line
      if 'VALUES=' in line:
       values=json.loads(line.split('VALUES=',1)[1])
       if values==expected:
        self.assertNotIn('READY=2',log);return
     if proc.poll() is not None:break
   finally:selector.close()
   self.fail('Offscreen QML did not receive values: '+log[-2500:])
  proc=launch()
  try:
   await_values(proc,[52,1.7,.42,'native',5])
   for key,value in [('iconSize',64),('magnification',2.0),('glassOpacity',.75)]:
    cfg[key]=self.save(key,value)
    out=bridge.adapt({'config':cfg});bridge.atomic_merge(path,out)
    await_values(proc,[out['iconSize'],out['magnification'],out['glassOpacity'],out['dockStyle'],5])
  finally:proc.terminate();proc.wait(timeout=5);proc.stdout.close()
  proc=launch()
  try:await_values(proc,[64,2,.75,'native',5])
  finally:proc.terminate();proc.wait(timeout=5);proc.stdout.close()
