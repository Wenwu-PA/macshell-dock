import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app/MacDock'))
spec=importlib.util.spec_from_file_location('applications',ROOT/'bridge/applications.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Applications(unittest.TestCase):
 def test_xdg_precedence_hidden_and_nested_id(self):
  with tempfile.TemporaryDirectory() as d:
   user=Path(d)/'user';system=Path(d)/'system'
   for r in (user,system):(r/'applications/sub').mkdir(parents=True)
   (system/'applications/foo.desktop').write_text('[Desktop Entry]\nType=Application\nName=System\n')
   (user/'applications/foo.desktop').write_text('[Desktop Entry]\nType=Application\nHidden=true\n')
   (system/'applications/sub/bar.desktop').write_text('[Desktop Entry]\nType=Application\nName=Тест\nIcon=bar\nStartupWMClass=BarClass\n')
   with patch.dict(os.environ,{'XDG_DATA_HOME':str(user),'XDG_DATA_DIRS':str(system)}):
    self.assertEqual(a.catalog(),[{'id':'sub-bar','name':'Тест','icon':'bar','startupClass':'BarClass'}])
 def test_pin_edit_rejects_stale_gui_snapshot(self):
  with tempfile.TemporaryDirectory() as d,patch.object(a,'catalog',return_value=[{'id':'kitty'},{'id':'firefox'}]):
   path=Path(d)/'pinned.json'
   a.edit(path,{'action':'add','id':'kitty','expected':'[]'})
   with self.assertRaises(ValueError):a.edit(path,{'action':'add','id':'firefox','expected':'[]'})
   self.assertEqual(a.read_pins(path),['kitty'])
   a.edit(path,{'action':'add','id':'firefox','expected':['kitty']})
   a.edit(path,{'action':'up','index':1,'expected':['kitty','firefox']})
   self.assertEqual(a.read_pins(path),['firefox','kitty'])
 def test_unknown_app_and_invalid_index(self):
  with tempfile.TemporaryDirectory() as d,patch.object(a,'catalog',return_value=[]):
   path=Path(d)/'pins.json'
   for request in ({'action':'add','id':'not-installed','expected':[]},{'action':'remove','index':True,'expected':['kitty']}):
    with self.assertRaises(ValueError):a.edit(path,request)
   self.assertFalse(path.exists())

 def test_desktop_suffix_is_part_of_canonical_id(self):
  entries=[{'id':'org.telegram.desktop','startupClass':'TelegramDesktop'},{'id':'kitty','startupClass':'kitty'}]
  self.assertEqual(a.canonical('org.telegram.desktop',entries),'org.telegram.desktop')
  self.assertEqual(a.canonical('org.telegram.desktop.desktop',entries),'org.telegram.desktop')
  self.assertEqual(a.canonical('telegramdesktop',entries),'org.telegram.desktop')
  self.assertEqual(a.canonical('kitty.desktop',entries),'kitty')
  with tempfile.TemporaryDirectory() as d,patch.object(a,'catalog',return_value=entries):
   path=Path(d)/'pins.json';old=['org.telegram.desktop']*3+['kitty'];path.write_text(json.dumps(old))
   a.edit(path,{'action':'add','id':'org.telegram.desktop','expected':old})
   self.assertEqual(a.read_pins(path),['org.telegram.desktop','kitty'])

 def test_remove_all_legacy_duplicate_aliases(self):
  entries=[{'id':'org.sample.desktop','startupClass':'Sample'}]
  with tempfile.TemporaryDirectory() as d,patch.object(a,'catalog',return_value=entries):
   path=Path(d)/'pins.json';old=['org.sample.desktop','org.sample.desktop.desktop','other'];path.write_text(json.dumps(old))
   a.edit(path,{'action':'remove','index':0,'expected':old})
   self.assertEqual(a.read_pins(path),['other'])
