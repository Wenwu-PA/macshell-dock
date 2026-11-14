import importlib.util
from pathlib import Path
import tempfile,json,unittest
spec=importlib.util.spec_from_file_location('migration',Path(__file__).resolve().parents[1]/'tools/migrate_native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MigrationTests(unittest.TestCase):
 def test_preserves_user_data_and_opacity(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'settings.json';old={'iconSize':64,'magnification':2,'glassOpacity':.75,'unifiedOpacity':0,'glassBlur':12,'dockStyle':'liquid','custom':'keep'};p.write_text(json.dumps(old));pins=p.with_name('pinned.json');pins.write_text('["org.telegram.desktop"]')
   backup=m.migrate(p);self.assertEqual(json.loads(backup.read_text()),old);new=json.loads(p.read_text());self.assertEqual(new['dockStyle'],'native');self.assertEqual(new['glassOpacity'],.75);self.assertEqual(new['custom'],'keep');self.assertNotIn('unifiedOpacity',new);self.assertEqual(pins.read_text(),'["org.telegram.desktop"]');self.assertIsNone(m.migrate(p))

 def test_native_contract(self):
  import sys
  root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'bridge'))
  import bridge,tomllib
  manifest=tomllib.loads((root/'noctalia/plugin/plugin.toml').read_text())
  config={x['key']:x['default'] for x in manifest.get('setting',[])}
  self.assertFalse(any(k.startswith('bar') or k in ('unified','liquid','effectMode','shaderQuality') for k in config))
  out=bridge.adapt({'config':config,'dark':False,'background':'#ffffff'})
  self.assertEqual(out['dockStyle'],'native');self.assertEqual(out['backgroundTint'],'#ffffff')
  self.assertFalse(any('ShaderEffect' in p.read_text() for p in (root/'app/MacDock').glob('*.qml')))
