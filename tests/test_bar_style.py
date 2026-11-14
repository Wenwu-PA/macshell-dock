import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/"bridge"))
spec=importlib.util.spec_from_file_location('bar_style',ROOT/'tools/legacy_bar/bar_style.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sys.path.insert(0,str(ROOT/'tools/legacy_bar'))
class BarStyle(unittest.TestCase):
 def setUp(self):
  import sys
  sys.path.insert(0,str(ROOT/'bridge'))
  self.probe=patch('bar_capability.probe',return_value={'state':'Supported','reason':'test'})
  self.probe.start();self.addCleanup(self.probe.stop)
  for name in ("native_rules.apply","native_rules.clear"):
   mock=patch(name);mock.start();self.addCleanup(mock.stop)

 def test_apply_restore_only_style(self):
  data={'bar':{'default':{'position':'top','enabled':True,'background_opacity':.8,'compositor_blur':False,'radius':10,'reserve_space':True,'start':['clock'],'layer':'top'}}}
  def write(path,value):data['bar'][path[1]][path[2]]=value
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',side_effect=lambda:data),patch.object(b,'set_value',side_effect=write):
   journal=Path(d)/'restore.json';b.apply({'barMode':'compositor','barOpacity':.4},journal)
   self.assertEqual(data['bar']['default']['background_opacity'],.4)
   self.assertEqual(data['bar']['default']['start'],['clock']);self.assertEqual(data['bar']['default']['layer'],'top')
   b.restore(journal);self.assertEqual(data['bar']['default']['background_opacity'],.8);self.assertFalse(journal.exists())
 def test_external_edit_is_not_overwritten(self):
  data={'bar':{'default':{'position':'top','background_opacity':.8,'compositor_blur':False,'radius':10}}}
  def write(path,value):data['bar'][path[1]][path[2]]=value
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',side_effect=lambda:data),patch.object(b,'set_value',side_effect=write):
   journal=Path(d)/'restore.json';b.apply({'barMode':'compositor'},journal)
   data['bar']['default']['background_opacity']=.95
   with self.assertRaises(RuntimeError):b.restore(journal)
   self.assertEqual(data['bar']['default']['background_opacity'],.95);self.assertTrue(journal.exists())
 def test_failed_reapply_restores_original(self):
  data={'bar':{'default':{'position':'top','background_opacity':.8,'compositor_blur':False,'radius':10}}}
  fail=False
  def write(path,value):
   if fail and path[-1]=='background_opacity' and value==.2:raise RuntimeError('IPC rejected update')
   data['bar'][path[1]][path[2]]=value
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',side_effect=lambda:data),patch.object(b,'set_value',side_effect=write):
   journal=Path(d)/'restore.json';b.apply({'barMode':'compositor','barOpacity':.4},journal)
   fail=True
   with self.assertRaises(RuntimeError):b.apply({'barMode':'compositor','barOpacity':.2},journal)
   self.assertEqual(data['bar']['default']['background_opacity'],.8)
   self.assertFalse(data['bar']['default']['compositor_blur']);self.assertFalse(journal.exists())

 def test_monitor_override_and_restore(self):
  data={'bar':{'default':{'position':'top','background_opacity':.8,'compositor_blur':False,'radius':10,'monitor':{'DP-1':{'background_opacity':.9,'compositor_blur':False,'radius':8},'HDMI-A-1':{'enabled':False,'background_opacity':.9}}}}}
  def write(path,value):
   node=data
   for k in path[:-1]:node=node[k]
   node[path[-1]]=value
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',side_effect=lambda:data),patch.object(b,'set_value',side_effect=write):
   journal=Path(d)/'restore.json';b.apply({'barMode':'compositor','barOpacity':.6},journal)
   self.assertEqual(data['bar']['default']['monitor']['DP-1']['background_opacity'],.6)
   self.assertEqual(data['bar']['default']['monitor']['HDMI-A-1']['background_opacity'],.9)
   b.restore(journal)
   self.assertEqual(data['bar']['default']['monitor']['DP-1']['background_opacity'],.9)
 def test_unavailable_never_modifies_bar(self):
  with tempfile.TemporaryDirectory() as d,patch('bar_capability.probe',return_value={'state':'Unavailable','reason':'blur disabled'}),patch.object(b,'set_value') as setter:
   with self.assertRaisesRegex(RuntimeError,'blur disabled'):b.apply({'barMode':'compositor'},Path(d)/'restore.json')
   setter.assert_not_called()
 def test_status_reports_selected_and_actual_overrides(self):
  data={'bar':{'default':{'position':'top','background_opacity':.5,'compositor_blur':True,'monitor':{'DP-1':{'background_opacity':0,'compositor_blur':False},'HDMI-A-1':{'enabled':False,'background_opacity':1}}}}}
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',return_value=data),patch('bar_capability.probe',return_value={'state':'Supported','namespaces':['noctalia-bar-default']}):
   result=b.status({'barMode':'compositor','barOpacity':.5},Path(d)/'restore.json')
   self.assertEqual(result['requested'],'compositor');self.assertEqual(result['applied'],'mixed')
   self.assertEqual(result['state'],'Mismatch');self.assertEqual(len(result['bars']),2)
 def test_status_ipc_failure_never_claims_applied(self):
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',side_effect=RuntimeError('Noctalia not running')):
   result=b.status({'barMode':'compositor'},Path(d)/'restore.json')
   self.assertEqual(result['applied'],'unknown');self.assertIn('not running',result['reason'])
 def test_failure_receipt_explains_unapplied_mode(self):
  data={'bar':{'default':{'position':'top','background_opacity':0,'compositor_blur':False}}}
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',return_value=data),patch('bar_capability.probe',return_value={'state':'Unavailable','reason':'blur disabled'}):
   journal=Path(d)/'restore.json'
   with self.assertRaisesRegex(RuntimeError,'blur disabled'):b.apply({'barMode':'compositor'},journal)
   result=b.status({'barMode':'compositor'},journal)
   self.assertEqual(result['applied'],'transparent');self.assertEqual(result['state'],'Error');self.assertIn('blur disabled',result['reason'])
 def test_unified_palette_does_not_write_unsupported_color(self):
  data={'bar':{'default':{'position':'top','background_opacity':.8,'compositor_blur':False,'radius':10,'border_width':0,'border':'outline_variant'}}}
  def write(path,value):data['bar'][path[1]][path[2]]=value
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',return_value=data),patch.object(b,'set_value',side_effect=write):
   b.apply({'barMode':'compositor','unified':True,'tintMode':'custom','backgroundTint':'#eeeeee'},Path(d)/'restore.json')
   self.assertTrue(data['bar']['default']['compositor_blur']);self.assertNotIn('color',data['bar']['default'])
 def test_empty_luau_list_transport_applies_all_bars(self):
  data={'bar':{'default':{'position':'top','background_opacity':.8,'compositor_blur':False,'radius':10}}}
  def write(path,value):data['bar'][path[1]][path[2]]=value
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',return_value=data),patch.object(b,'set_value',side_effect=write):
   # Exact JSON representation emitted by Noctalia 5.4.1 luaToJson for getConfig("barNames") == {}.
   b.apply({'barMode':'compositor','barNames':{},'barOpacity':.4},Path(d)/'restore.json')
   self.assertEqual(data['bar']['default']['background_opacity'],.4)
   self.assertTrue(data['bar']['default']['compositor_blur'])
 def test_nonempty_bar_map_is_not_silently_coerced(self):
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',return_value={'bar':{}}):
   with self.assertRaisesRegex(ValueError,'Invalid Bar names'):
    b.apply({'barMode':'solid','barNames':{'default':True}},Path(d)/'restore.json')
 def test_zero_tint_with_blur_is_not_mislabelled_transparent(self):
  data={'bar':{'default':{'position':'top','background_opacity':0,'compositor_blur':True}}}
  with tempfile.TemporaryDirectory() as d,patch.object(b,'effective',return_value=data),patch('bar_capability.probe',return_value={'state':'Supported','namespaces':['noctalia-bar-default']}):
   result=b.status({'barMode':'compositor','barOpacity':0},Path(d)/'restore.json')
   self.assertEqual(result['applied'],'compositor');self.assertEqual(result['state'],'Configured')
   self.assertIn('Tint is transparent',result['reason'])
