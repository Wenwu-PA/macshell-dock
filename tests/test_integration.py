import sys
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bridge'))
spec=importlib.util.spec_from_file_location('bridge',ROOT/'bridge/bridge.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Integration(unittest.TestCase):
 def config(self):return dict(__import__('settings_store').DEFAULTS)
 def test_invalid_values(self):
  c=self.config();c['iconSize']=-5
  with self.assertRaises(ValueError):b.adapt({'config':c})
 def test_atomic_idempotent_preserves_pins_and_unknown(self):
  with tempfile.TemporaryDirectory(prefix='dock unicode тест ') as d:
   p=Path(d)/'settings.json';p.write_text('{"unknown":true}')
   pins=Path(d)/'pinned.json';pins.write_text('["kitty"]')
   self.assertTrue(b.atomic_merge(p,{'iconSize':64}));stamp=p.stat().st_mtime_ns
   self.assertFalse(b.atomic_merge(p,{'iconSize':64}));self.assertEqual(p.stat().st_mtime_ns,stamp)
   self.assertTrue(json.loads(p.read_text())['unknown']);self.assertEqual(pins.read_text(),'["kitty"]')

 def test_panel_manifest_content_height(self):
  m=tomllib.loads((ROOT/'noctalia/plugin/plugin.toml').read_text())
  self.assertEqual(m['plugin_api'],42)
  self.assertEqual(m['panel'][0]['height'],'content')
  self.assertLessEqual(m['panel'][0]['max_height'],650)

 def test_icon_override_validation(self):
  c=self.config();c['iconOverrides']={'firefox':'relative.png'}
  with self.assertRaises(ValueError):b.adapt({'config':c})
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'icon тест.svg';p.write_text('<svg/>');c['iconOverrides']['firefox']=str(p)
   self.assertEqual(b.adapt({'config':c})['iconOverrides']['firefox'],str(p))
