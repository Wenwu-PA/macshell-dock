import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'app/MacDock/config_store.py'
spec=importlib.util.spec_from_file_location('config_store',HELPER)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ConfigStore(unittest.TestCase):
 def test_parallel_merges_and_unicode(self):
  with tempfile.TemporaryDirectory(prefix='dock тест ') as d:
   p=Path(d)/'settings.json';p.write_text('{"unknown":"keep"}')
   jobs=[subprocess.Popen([sys.executable,str(HELPER),str(p),json.dumps({str(i):i})]) for i in range(12)]
   self.assertEqual([j.wait() for j in jobs],[0]*12)
   self.assertEqual(json.loads(p.read_text()),dict({'unknown':'keep'},**{str(i):i for i in range(12)}))
 def test_idempotent_and_compare_swap(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'pinned.json';m.write(p,['kitty']);stamp=p.stat().st_mtime_ns
   self.assertFalse(m.write(p,['kitty']));self.assertEqual(p.stat().st_mtime_ns,stamp)
   with self.assertRaises(ValueError):m.write(p,['firefox'],['stale'])
   self.assertEqual(json.loads(p.read_text()),['kitty'])
   m.write(p,['firefox'],['kitty']);self.assertEqual(json.loads(p.read_text()),['firefox'])
