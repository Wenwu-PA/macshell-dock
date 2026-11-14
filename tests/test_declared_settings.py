import re,tomllib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DeclaredSettings(unittest.TestCase):
 def test_every_literal_config_read_is_declared(self):
  plugin=ROOT/'noctalia/plugin';schema=tomllib.loads((plugin/'plugin.toml').read_text());declared={s['key'] for s in schema.get('setting',[])}
  for path in plugin.glob('*.luau'):
   keys=set(re.findall(r'noctalia\.getConfig\(["\']([^"\']+)["\']\)',path.read_text()))
   self.assertFalse(keys-declared,(path.name,keys-declared))
 def test_service_reads_exact_current_schema(self):
  plugin=ROOT/'noctalia/plugin';declared={s['key'] for s in tomllib.loads((plugin/'plugin.toml').read_text()).get('setting',[])}
  reads=set(re.findall(r'noctalia\.getConfig\("([^"]+)"\)',(plugin/'service.luau').read_text()))
  self.assertEqual(reads,declared)
 def test_widget_uses_host_global(self):
  text=(ROOT/'noctalia/plugin/widget.luau').read_text()
  self.assertNotRegex(text,r'(?<![A-Za-z])widget\.')
  self.assertIn('barWidget.setGlyph',text)
