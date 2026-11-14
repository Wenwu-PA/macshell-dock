import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bridge'))
import native_rules
import wayland_probe
import noctalia_config
class NativeBlur(unittest.TestCase):
 def test_registry_read_with_fragmented_messages(self):
  name=b'ext_background_effect_manager_v1\0';payload=struct.pack('=II',7,len(name))+name+b'\0'*((-len(name))%4)+struct.pack('=I',1)
  packet=struct.pack('=II',2,((8+len(payload))<<16))+payload+struct.pack('=III',3,12<<16,5)
  class Socket:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def settimeout(self,v):pass
   def connect(self,path):pass
   def sendall(self,data):self.sent=data
   def recv(self,n):
    part=self.data[:5];self.data=self.data[5:];return part
  sock=Socket();sock.data=packet
  with patch.object(wayland_probe.socket,'socket',return_value=sock),patch.dict(os.environ,{'WAYLAND_DISPLAY':'wayland-1','XDG_RUNTIME_DIR':'/tmp'}):
   self.assertIn('ext_background_effect_manager_v1',wayland_probe.globals_available())
  self.assertEqual(len(sock.sent),24)
 def test_float32_readback(self):
  self.assertTrue(noctalia_config.equivalent(.699999988079071,.7))
  self.assertFalse(noctalia_config.equivalent(True,1))
 @unittest.skipUnless(shutil.which('lua'),'Lua unavailable')
 def test_owned_rule_scope_reuse_and_disable(self):
  script='''local count=0;local rules={};local user={enabled=true}
hl={layer_rule=function(spec)count=count+1;local h={spec=spec,enabled=true};function h:set_enabled(v)self.enabled=v end;table.insert(rules,h);return h end}
'''
  script+=native_rules.script(['noctalia-bar-default'],True)+'\n'
  script+=native_rules.script(['noctalia-bar-default'],True)+'\nassert(count==1)\n'
  script+=native_rules.script(['noctalia-bar-default'],False)+'\nassert(count==2 and not rules[1].enabled and rules[2].enabled)\n'
  script+=native_rules.script(['noctalia-bar-default'],True)+'\nassert(count==2 and rules[1].enabled and not rules[2].enabled)\n'
  script+=native_rules.script([],False)+'\nassert(user.enabled and not rules[1].enabled and not rules[2].enabled)\nassert(rules[1].spec.match.namespace=="^noctalia\\\\-bar\\\\-default$")'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.lua';p.write_text(script);r=subprocess.run(['lua',str(p)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
 def test_rule_rejects_other_surfaces(self):
  with self.assertRaises(ValueError):native_rules.script(['.*'],True)
