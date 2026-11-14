import json,os,subprocess,sys,tempfile,tomllib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class JsonPanelStorage(unittest.TestCase):
 def test_save_without_noctalia_or_panel_reload(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);config=base/'config';dock=config/'macdock';dock.mkdir(parents=True)
   settings=dock/'settings.json';settings.write_text('{"unknown":"keep","monitor":"DP-1"}')
   pins=dock/'pinned.json';pins.write_text('["org.telegram.desktop"]')
   env=dict(os.environ,XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(base/'state'),PATH=str(base/'no-cli'))
   for key,value in [('iconSize',64),('glassOpacity',.75),('magnification',2),('enabled',False),('monitor','@auto')]:
    result=subprocess.run([sys.executable,str(ROOT/'bridge/bridge.py'),'set',json.dumps({key:value})],env=env,capture_output=True,text=True)
    self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['saved'])
   data=json.loads(settings.read_text());self.assertEqual(data['iconSize'],64);self.assertEqual(data['glassOpacity'],.75);self.assertFalse(data['dockEnabled']);self.assertEqual(data['unknown'],'keep')
   self.assertEqual(pins.read_text(),'["org.telegram.desktop"]')
   before=settings.read_bytes();result=subprocess.run([sys.executable,str(ROOT/'bridge/bridge.py'),'set','{"iconSize":999}'],env=env,capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertEqual(settings.read_bytes(),before)
 def test_no_declarative_duplicate_settings(self):
  manifest=tomllib.loads((ROOT/'noctalia/plugin/plugin.toml').read_text());self.assertFalse(manifest.get('setting'))
  self.assertEqual(manifest['panel'][0]['width'],440);self.assertEqual(manifest['panel'][0]['max_height'],650)
  for file in ('panel.luau','service.luau'):
   text=(ROOT/'noctalia/plugin'/file).read_text();self.assertNotIn('getConfig(',text);self.assertNotIn('config-set',text)
 def test_confirmed_reset_retains_identity_and_startup(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);dock=base/'config/macdock';dock.mkdir(parents=True)
   original={'iconSize':80,'automatic':False,'dockEnabled':False,'iconTheme':'MacOS-Like','iconOverrides':{'app':'/custom/icon.svg'},'unknown':'retain','monitor':'DP-1'}
   path=dock/'settings.json';path.write_text(json.dumps(original));pins=dock/'pinned.json';pins.write_text('["org.telegram.desktop"]')
   env=dict(os.environ,XDG_CONFIG_HOME=str(base/'config'),XDG_STATE_HOME=str(base/'state'))
   cmd=[sys.executable,str(ROOT/'bridge/bridge.py'),'reset-settings']
   r=subprocess.run(cmd+['{}'],env=env,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(path.read_text()),original)
   r=subprocess.run(cmd+['{"confirm":true}'],env=env,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
   data=json.loads(path.read_text());self.assertEqual(data['iconSize'],52)
   for key in ('automatic','dockEnabled','iconTheme','iconOverrides','unknown'):self.assertEqual(data[key],original[key])
   backup=Path(json.loads(r.stdout)['backup']);self.assertEqual(json.loads(backup.read_text()),original);self.assertEqual(pins.read_text(),'["org.telegram.desktop"]')
