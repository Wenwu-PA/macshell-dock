import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/legacy_bar'))
import bar_glass
import bar_style

class BarGlassTests(unittest.TestCase):
    def test_no_backend_no_writes(self):
        data={'bar':{'default':{'position':'top','background_opacity':.7,'compositor_blur':True,'radius':12}}}
        with tempfile.TemporaryDirectory() as temp:
            crop=Path(temp)/'crop.ppm';crop.write_bytes(b'P6\n1 1\n255\nxxx')
            with patch.object(bar_style,'effective',return_value=data),patch.object(bar_style,'set_value') as write,patch.object(bar_glass,'command',side_effect=RuntimeError('unknown command')):
                with self.assertRaisesRegex(RuntimeError,'unknown command'):bar_style.apply({'barMode':'liquid','barGlassBackdrop':str(crop)},Path(temp)/'restore.json')
                write.assert_not_called()

    def transition(self, fail=False):
        data={'bar':{'default':{'position':'top','background_opacity':0.,'compositor_blur':True,'radius':12,'concave_edge_corners':True,'monitor':{'DP-1':{'concave_edge_corners':True,'background_opacity':.7}}}}}
        original=copy.deepcopy(data)
        def write(path,value):
            node=data
            for key in path[:-1]:node=node[key]
            node[path[-1]]=value
        with tempfile.TemporaryDirectory() as temp:
            crop=Path(temp)/'crop.ppm';crop.write_bytes(b'P6\n1 1\n255\nxxx')
            config={'barMode':'liquid','barGlassBackdrop':str(crop),'barGlassConvex':True,'unified':True,'unifiedOpacity':0,'borderWidth':0,'borderOpacity':0}
            # Noctalia exposes border properties; Unified Appearance must not zero material alpha.
            data['bar']['default'].update(border_width=0,border='#ffffff00');original=copy.deepcopy(data)
            journal=Path(temp)/'restore.json'
            with patch.object(bar_style,'effective',side_effect=lambda:copy.deepcopy(data)),patch.object(bar_style,'set_value',side_effect=write),patch('native_rules.apply'),patch('native_rules.clear'),patch.object(bar_glass,'command',return_value={'backend':1,'state':'ready'}),patch.object(bar_glass,'activate',side_effect=RuntimeError('shader error') if fail else None) as activate:
                if fail:
                    with self.assertRaisesRegex(RuntimeError,'shader error'):bar_style.apply(config,journal)
                    self.assertEqual(data,original)
                else:
                    bar_style.apply(config,journal)
                    self.assertFalse(data['bar']['default']['concave_edge_corners'])
                    self.assertFalse(data['bar']['default']['monitor']['DP-1']['concave_edge_corners'])
                    self.assertEqual(data['bar']['default']['monitor']['DP-1']['background_opacity'],.7)
                    self.assertEqual(bar_glass.parameters(config)['opacity'],.85)
                    # Subsequent uniform changes must not repeatedly restore corner geometry.
                    bar_style.apply(config|{'barGlassRefraction':24},journal)
                    bar_style.restore(journal)
                    self.assertEqual(data,original)
                    self.assertEqual(activate.call_count,2)
    def test_compatibility_opacity_and_restore(self):self.transition()
    def test_shader_failure_restores_working_mode(self):self.transition(True)
    def test_invalid_uniform(self):
        with tempfile.NamedTemporaryFile() as file:
            with self.assertRaises(ValueError):bar_glass.parameters({'barGlassBackdrop':file.name,'barGlassBlur':float('nan')})
    def test_ack_is_not_readiness(self):
        with tempfile.NamedTemporaryFile() as file,patch.object(bar_glass,'command',return_value={'state':'building'}),patch.object(bar_glass.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'not rendered'):bar_glass.activate('default',{'barGlassBackdrop':file.name})
    def test_cleanup_stock_shell_requires_live_ipc(self):
        with tempfile.TemporaryDirectory() as temp:
            journal=Path(temp)/'restore.json';owned=journal.with_name('bar-glass-owned.json');owned.write_text('{"bars":["default"]}')
            with patch.object(bar_glass,'command',side_effect=RuntimeError('unknown command')),patch('noctalia_config.get',side_effect=RuntimeError('not running')):
                with self.assertRaises(RuntimeError):bar_glass.disable_owned(journal)
                self.assertTrue(owned.exists())
            with patch.object(bar_glass,'command',side_effect=RuntimeError('unknown command')),patch('noctalia_config.get',return_value={}):bar_glass.disable_owned(journal)
            self.assertFalse(owned.exists())
