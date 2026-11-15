import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
import bridge


class NoctaliaDockImport(unittest.TestCase):
    def test_theme_role_resolves_to_existing_qml_icon_tint(self):
        source = (ROOT / 'noctalia/plugin/service.luau').read_text()
        self.assertIn('noctalia.getSetting("dock")', source)
        self.assertIn('dock.colorize_icons', source)
        self.assertIn('shell.app_icon_colorize', source)
        self.assertIn('noctalia.getSetting("shell.app_icon_color")', source)
        self.assertIn('noctalia.getColor(spec)', source)
        for enabled in (True, False):
            patch = bridge.adapt({
                'config': {}, 'iconColorize': enabled,
                'iconColor': '#b7a454', 'background': '#202023'
            })
            self.assertEqual(patch['iconTint'], enabled)
            self.assertEqual(patch['iconTintColor'], '#b7a454')
            self.assertEqual(patch['iconTintStrength'], 1.0)
        self.assertIn('colorizationColor: root.iconTintColor', (ROOT / 'app/MacDock/MacDock.qml').read_text())

    def test_5_5_colorize_per_monitor_override(self):
        request = {'config': {'monitor': 'DP-1'}, 'iconColorize': False,
                   'iconColorizeByMonitor': {'DP-1': True, 'HDMI-A-1': False}, 'iconColor': '#c2a45a'}
        self.assertTrue(bridge.adapt(request)['iconTint'])
        request['config']['monitor'] = 'HDMI-A-1'
        self.assertFalse(bridge.adapt(request)['iconTint'])
        request['config']['monitor'] = ''
        self.assertFalse(bridge.adapt(request)['iconTint'])
        request['config']['monitor'] = 'DP-1'
        request['iconColorizeByMonitor'] = {'DP-1': 'true'}
        with self.assertRaisesRegex(ValueError, 'monitor icon colorization'):
            bridge.adapt(request)

    def test_icon_color_validation(self):
        for color in ('#abc', '#abcd', '#aabbcc', '#aabbccdd'):
            self.assertEqual(bridge.adapt({'config': {}, 'iconColorize': True, 'iconColor': color})['iconTintColor'], color)
        for color in ('red', '#12', '#12345', '#xyzabc', '#000000000'):
            with self.subTest(color=color), self.assertRaisesRegex(ValueError, 'Invalid icon color'):
                bridge.adapt({'config': {}, 'iconColorize': True, 'iconColor': color})
        with self.assertRaisesRegex(ValueError, 'colorization flag'):
            bridge.adapt({'config': {}, 'iconColorize': 'true', 'iconColor': '#fff'})

    def test_import_maps_supported_values_and_preserves_other_keys(self):
        source = {
            'icon_size': 66, 'item_spacing': 9, 'background_opacity': .68,
            'radius': 20, 'magnification': True, 'magnification_scale': 1.9,
            'show_running': False, 'auto_hide': True, 'smart_auto_hide': False,
            'enabled': False, 'pinned': ['org.telegram.desktop'],
            'monitor': {'DP-1': {'pinned': ['another-app']}},
        }
        patch = bridge.noctalia_dock_patch(source)
        self.assertEqual(patch, {
            'iconSize': 66, 'spacing': 9, 'glassOpacity': .68,
            'cornerRadius': 20, 'magnificationEnabled': True,
            'magnification': 1.9, 'showRunning': False, 'hideMode': 'always'
        })
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'; state = Path(tmp) / 'state'
            target = config / 'macdock/settings.json'
            target.parent.mkdir(parents=True)
            original = {'dockEnabled': True, 'automatic': False, 'iconTheme': 'custom', 'iconOverrides': {'telegram': '/icons/icon.svg'}, 'iconSize': 52}
            target.write_text(json.dumps(original))
            pins = target.parent / 'pinned.json'; pins.write_text('["telegram"]')
            env = dict(os.environ, XDG_CONFIG_HOME=str(config), XDG_STATE_HOME=str(state))
            result = subprocess.run([sys.executable, str(ROOT/'bridge/bridge.py'), 'apply-noctalia-dock', json.dumps(source)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            response = json.loads(result.stdout)
            self.assertTrue(response['saved'])
            self.assertEqual(response['changed'], patch)
            self.assertEqual(json.loads(Path(response['backup']).read_text()), original)
            saved = json.loads(target.read_text())
            self.assertEqual(saved, dict(original, **patch, noctaliaDockColorSync=True))
            self.assertEqual(pins.read_text(), '["telegram"]')

    def test_live_color_sync_updates_settings_without_touching_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'; state = Path(tmp) / 'state'
            target = config / 'macdock/settings.json'; target.parent.mkdir(parents=True)
            target.write_text(json.dumps({'dockEnabled': False, 'automatic': False, 'iconSize': 65}))
            pins = target.parent / 'pinned.json'; pins.write_text('["org.telegram.desktop"]')
            env = dict(os.environ, XDG_CONFIG_HOME=str(config), XDG_STATE_HOME=str(state))
            for enabled, color in ((True, '#aa8760'), (True, '#00ffaa'), (False, '#00ffaa')):
                request = {'dark': True, 'background': '#222222', 'iconColorize': enabled, 'iconColor': color}
                result = subprocess.run([sys.executable, str(ROOT/'bridge/bridge.py'), 'sync', json.dumps(request)], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                settings = json.loads(target.read_text())
                self.assertEqual(settings['iconTint'], enabled)
                self.assertEqual(settings['iconTintColor'], color)
                self.assertEqual(settings['iconSize'], 65)
                self.assertEqual(pins.read_text(), '["org.telegram.desktop"]')

    def test_invalid_import_cannot_modify_file(self):
        with self.assertRaisesRegex(ValueError, 'No compatible'):
            bridge.noctalia_dock_patch({'pinned': ['firefox']})
        with self.assertRaisesRegex(ValueError, 'magnification'):
            bridge.noctalia_dock_patch({'magnification': 'yes'})
        self.assertEqual(bridge.noctalia_dock_patch({'smart_auto_hide': True, 'auto_hide': True})['hideMode'], 'smart')
        self.assertEqual(bridge.noctalia_dock_patch({'auto_hide': False})['hideMode'], 'never')

    def test_undo_restores_only_imported_settings_and_keeps_pins(self):
        source = {'icon_size': 72, 'item_spacing': 14, 'background_opacity': .8,
                  'magnification_scale': 2.4, 'auto_hide': True}
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config';state=Path(tmp)/'state'
            target=config/'macdock/settings.json';target.parent.mkdir(parents=True)
            original={'iconSize': 62, 'spacing': 6, 'automatic': True,
                      'dockEnabled': True, 'iconTheme': 'MacOS-Like',
                      'iconOverrides': {'telegram': '/icons/telegram.svg'}, 'custom': 'retain'}
            target.write_text(json.dumps(original))
            pins=target.with_name('pinned.json');pins.write_text('["telegram"]')
            env=dict(os.environ,XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(state))
            def command(action, payload=None):
                args=[sys.executable,str(ROOT/'bridge/bridge.py'),action]
                if payload is not None:args.append(json.dumps(payload))
                return subprocess.run(args,env=env,capture_output=True,text=True)
            applied=command('apply-noctalia-dock',source)
            self.assertEqual(applied.returncode,0,applied.stderr)
            self.assertTrue(json.loads(command('settings').stdout)['undoNoctaliaAvailable'])
            updated=json.loads(target.read_text())
            self.assertEqual(updated['iconSize'],72)
            updated['custom']='changed after import';target.write_text(json.dumps(updated))
            undone=command('undo-noctalia-dock')
            self.assertEqual(undone.returncode,0,undone.stderr)
            response=json.loads(undone.stdout)
            self.assertFalse(response['settings']['undoNoctaliaAvailable'])
            self.assertTrue(Path(response['backup']).is_file())
            result=json.loads(target.read_text())
            self.assertEqual(result['iconSize'],62)
            self.assertEqual(result['spacing'],6)
            self.assertEqual(result['glassOpacity'],.42)
            self.assertEqual(result['magnification'],1.7)
            self.assertEqual(result['hideMode'],'smart')
            self.assertFalse(result['noctaliaDockColorSync'])
            self.assertFalse(result['iconTint'])
            self.assertEqual(result['custom'],'changed after import')
            self.assertEqual(result['automatic'],True)
            self.assertEqual(result['iconOverrides'],original['iconOverrides'])
            self.assertEqual(pins.read_text(),'["telegram"]')
            self.assertFalse(json.loads(command('settings').stdout)['undoNoctaliaAvailable'])
            self.assertNotEqual(command('undo-noctalia-dock').returncode,0)

    def test_repeated_imports_undo_to_original_settings_in_one_click(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config';config.joinpath('macdock').mkdir(parents=True)
            target=config/'macdock/settings.json'
            target.write_text('{"iconSize":52,"spacing":8,"glassOpacity":0.4,"iconTint":false,"dockEnabled":false,"automatic":false,"extra":"keep"}')
            state=Path(tmp)/'state'
            env=dict(os.environ,XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(state))
            def run(action,source=None):
                argv=[sys.executable,str(ROOT/'bridge/bridge.py'),action]
                if source is not None:argv.append(json.dumps(source))
                result=subprocess.run(argv,env=env,text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout or '{}')
            run('apply-noctalia-dock',{'icon_size':60,'item_spacing':0})
            self.assertEqual(len(list((state/'macdock/import-backups').glob('*.json'))),1)
            # A manual adjustment followed by Apply must not shift the baseline.
            updated=json.loads(target.read_text());updated['spacing']=9;target.write_text(json.dumps(updated))
            run('apply-noctalia-dock',{'icon_size':70,'item_spacing':0})
            self.assertEqual(len(list((state/'macdock/import-backups').glob('*.json'))),1)
            result=run('undo-noctalia-dock')['settings']
            self.assertEqual(result['iconSize'],52)
            self.assertEqual(result['spacing'],8)
            self.assertEqual(result['glassOpacity'],0.4)
            self.assertFalse(result['undoNoctaliaAvailable'])
            self.assertFalse(result['noctaliaDockColorSync'])
            self.assertFalse(json.loads(target.read_text())['iconTint'])
            self.assertEqual(json.loads(target.read_text())['extra'],'keep')
            self.assertEqual(len(list((state/'macdock/import-backups').glob('*.json'))),0)
            self.assertEqual(len(list((state/'macdock/import-backups').glob('*.undone'))),1)

            # Undo also disables future Noctalia tint updates, even if the
            # shell continues reporting enabled colorization each tick.
            run('sync',{'iconColorize':True,'iconColor':'#bbbbbb','background':'#202023'})
            self.assertFalse(json.loads(target.read_text())['iconTint'])
            # Apply re-enables color sync and starts a new undo session.
            run('apply-noctalia-dock',{'icon_size':65})
            self.assertTrue(json.loads(target.read_text())['noctaliaDockColorSync'])
            run('sync',{'iconColorize':True,'iconColor':'#bbbbbb','background':'#202023'})
            self.assertTrue(json.loads(target.read_text())['iconTint'])
            run('undo-noctalia-dock')
            self.assertFalse(json.loads(target.read_text())['iconTint'])

    def test_legacy_multiple_backups_undo_to_earliest_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config';(config/'macdock').mkdir(parents=True)
            target=config/'macdock/settings.json'
            target.write_text('{"iconSize":73,"spacing":0,"iconTint":true}')
            state=Path(tmp)/'state';snapshots=state/'macdock/import-backups';snapshots.mkdir(parents=True)
            (snapshots/'20261115-090000-000001.json').write_text('{"iconSize":52,"spacing":8}')
            (snapshots/'20261115-090010-000002.json').write_text('{"iconSize":67,"spacing":0}')
            env=dict(os.environ,XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(state))
            result=subprocess.run([sys.executable,str(ROOT/'bridge/bridge.py'),'undo-noctalia-dock'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            restored=json.loads(target.read_text())
            self.assertEqual((restored['iconSize'],restored['spacing']),(52,8))
            self.assertFalse(restored['iconTint'])
            self.assertEqual(len(list(snapshots.glob('*.undone'))),2)
            self.assertFalse(json.loads(result.stdout)['settings']['undoNoctaliaAvailable'])

    def test_sync_cannot_reapply_tint_after_undo_when_request_was_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'settings.json';target.write_text('{"noctaliaDockColorSync":false,"iconTint":false}')
            changed=bridge.atomic_merge(target,{'iconTint':True,'iconTintColor':'#ffffff','backgroundTint':'#202023'},respect_color_sync=True)
            self.assertTrue(changed)
            stored=json.loads(target.read_text())
            self.assertFalse(stored['iconTint'])
            self.assertNotIn('iconTintColor',stored)
            self.assertEqual(stored['backgroundTint'],'#202023')

    def test_import_button_without_extra_panel_or_scroll(self):
        panel = (ROOT / 'noctalia/plugin/panel.luau').read_text()
        self.assertIn('"applyNoctaliaDock"', panel)
        self.assertIn('"undoNoctaliaDock"', panel)
        self.assertIn('key="noctalia-apply",text="Apply Noctalia",onClick="applyNoctaliaDock"', panel)
        self.assertIn('key="noctalia-undo",text="Undo Noctalia",onClick="undoNoctaliaDock"', panel)
        self.assertIn('enabled=not busy and values.undoNoctaliaAvailable==true', panel)
        self.assertIn('drafts={}', panel)
        self.assertIn('noctalia.getSetting("dock." .. key)', panel)
        self.assertNotIn('ui.scroll', panel)


if __name__ == '__main__':
    unittest.main()
