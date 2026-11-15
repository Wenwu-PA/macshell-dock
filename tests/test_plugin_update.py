import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('plugin_install',ROOT/'tools/plugin_install.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(ROOT/'bridge'))
sys.path.insert(0,str(ROOT/'tools'))
class PluginUpdate(unittest.TestCase):
 def run_update(self, fail=False, previous=False, runtime_failure=False, restored=False, unknown=False, noctalia_version='noctalia v5.4.1', leaked_runtime=False, reset_unloaded=False):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);config=base/'config';data=base/'data';state=base/'state';app=config/'quickshell/MacDock';app.mkdir(parents=True)
   for name in ('MacDock.qml','shell.qml','DockGlassPanel.qml'):shutil.copy2(ROOT/'app/MacDock'/name,app/name)
   if previous:
    shutil.copy2(ROOT/'tests/fixtures/native-before-control.qml',app/'MacDock.qml')
   if restored:
    restored_bytes=(ROOT/'tests/fixtures/native-after-restore.qml').read_bytes()
    import hashlib
    self.assertEqual(hashlib.sha256(restored_bytes).hexdigest(),'9c1c13683d8346d2969ce25c2f6e1a2e7e6907281cb5f6633c58948d2501d351')
    if unknown:restored_bytes+=b'\n// Unreviewed local modification\n'
    (app/'MacDock.qml').write_bytes(restored_bytes)
   oldruntime=(ROOT/'tools/runtime.py').read_text().replace("[qs, '-n', '-c', 'MacDock']","[qs, '-c', 'MacDock']")
   if leaked_runtime:oldruntime=(ROOT/'tests/fixtures/runtime-lock-legacy.py').read_text()
   (app/'runtime.py').write_text(oldruntime)
   settings=config/'macdock/settings.json';settings.parent.mkdir(parents=True)
   original_settings='{"iconSize":52,"custom":"keep"}'
   settings.write_text(original_settings)
   pins=settings.with_name('pinned.json');pins.write_text('["org.telegram.desktop"]')
   target=data/'noctalia/plugins/macdock';target.mkdir(parents=True);(target/'sentinel').write_text('existing')
   calls=[]
   def run(argv,**kw):
    calls.append(tuple(argv))
    if reset_unloaded and argv[-2:]==['reset-failed','macdock.service']:
     return subprocess.CompletedProcess(argv,1,stdout='',stderr='Unit macdock.service not loaded.')
    if fail and argv[-2:]==['enable','wenwu/macdock']:raise subprocess.CalledProcessError(1,argv)
    return subprocess.CompletedProcess(argv,0,stdout='',stderr='')
   with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(config),'XDG_DATA_HOME':str(data),'XDG_STATE_HOME':str(state)}),patch.object(sys,'argv',['plugin_install.py','--plugin-update']),patch.object(m.subprocess,'check_output',return_value=noctalia_version),patch.object(m.subprocess,'run',side_effect=run),patch('deployment_probe.verify',return_value={'ready':True,'items':7},side_effect=RuntimeError('empty application model') if runtime_failure else None),patch('noctalia_config.get',return_value={'wenwu/macdock':{'iconSize':64,'automatic':False,'monitor':'DP-1','unifiedOpacity':0}}):
    if fail or runtime_failure or unknown:
     expected=self.assertRaisesRegex(RuntimeError,'Local changes in MacDock.qml') if unknown else self.assertRaises((subprocess.CalledProcessError,RuntimeError))
     with expected:m.main()
     if restored:self.assertEqual((app/'MacDock.qml').read_bytes(),restored_bytes)
     self.assertEqual(settings.read_text(),original_settings)
     self.assertEqual(pins.read_text(),'["org.telegram.desktop"]')
     self.assertFalse((app/'config_store.py').exists());self.assertEqual((app/'runtime.py').read_text(),oldruntime)
     self.assertEqual(list(p.name for p in target.iterdir()),['sentinel'])
     if not unknown:self.assertIn(('systemctl','--user','reset-failed','macdock.service'),calls)
    else:
     m.main()
     migrated=json.loads(settings.read_text());self.assertEqual(migrated['iconSize'],64);self.assertFalse(migrated['automatic']);self.assertEqual(migrated['monitor'],'DP-1');self.assertEqual(migrated['custom'],'keep');self.assertNotIn('unifiedOpacity',migrated)
     self.assertEqual(pins.read_text(),'["org.telegram.desktop"]')
     self.assertTrue((app/'config_store.py').exists());self.assertTrue((target/'applications.py').exists());self.assertTrue((target/'config_store.py').exists())
     self.assertIn("'-n'",(app/'runtime.py').read_text())
     self.assertNotIn('macdock-launch.lock',(app/'runtime.py').read_text())
     self.assertIn(('systemctl','--user','reset-failed','macdock.service'),calls)
     self.assertEqual((app/'MacDock.qml').read_bytes(),(ROOT/'app/MacDock/MacDock.qml').read_bytes())
     self.assertTrue((target/'widget.luau').exists())
 def test_update_includes_helpers(self):self.run_update()
 def test_update_replaces_leaking_runtime(self):self.run_update(leaked_runtime=True)
 def test_unloaded_unit_does_not_abort_update(self):self.run_update(reset_unloaded=True)
 def test_unloaded_unit_does_not_abort_rollback(self):self.run_update(reset_unloaded=True,runtime_failure=True)
 def test_5_5_0_plugin_update(self):self.run_update(noctalia_version='Noctalia 5.5.0')
 def test_5_4_1_without_prefix(self):self.run_update(noctalia_version='Noctalia 5.4.1')
 def test_unrecognized_version_fails_before_mutation(self):
  with self.assertRaisesRegex(RuntimeError,'Unsupported Noctalia version: .*5.6.0'):
   m.validate_noctalia_version('noctalia v5.6.0')
 def test_failed_enable_restores_previous_installation(self):self.run_update(fail=True)

 def test_reviewed_previous_native_version_updates(self):self.run_update(previous=True)

 def test_failed_runtime_acceptance_restores_entire_release(self):self.run_update(runtime_failure=True)

 def test_restored_release_updates(self):self.run_update(restored=True)
 def test_restored_release_with_any_extra_edit_is_rejected(self):self.run_update(restored=True,unknown=True)
 def test_restored_release_is_retained_after_runtime_failure(self):self.run_update(restored=True,runtime_failure=True)
