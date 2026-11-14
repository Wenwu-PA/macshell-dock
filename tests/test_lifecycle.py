import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('manage', Path(__file__).resolve().parents[1] / 'tools/manage.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='macdock test ')
        self.home = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'HOME': str(self.home), 'XDG_CONFIG_HOME': str(self.home / 'config'), 'XDG_DATA_HOME': str(self.home / 'data'), 'XDG_STATE_HOME': str(self.home / 'state'), 'NOCTALIA_STATE_HOME': str(self.home / 'noctalia')})
        self.env.start()
        theme = self.home / 'data/icons/MacOS-Like-Dark/index.theme'
        theme.parent.mkdir(parents=True)
        theme.write_text('[Icon Theme]\nName=MacOS-Like-Dark\n')
        self.quiet = contextlib.redirect_stdout(io.StringIO()); self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.env.stop(); self.temp.cleanup()

    def install(self, **kw):
        with patch.object(m, 'check_dependencies', return_value=[]):
            m.install(**kw)

    def test_install_preserves_settings_and_noctalia(self):
        paths = m.paths()
        paths['settings'].mkdir(parents=True)
        (paths['settings'] / 'settings.json').write_text('{"iconSize":64,"future":true}')
        (paths['settings'] / 'pinned.json').write_text('["kitty"]')
        paths['noctalia'].parent.mkdir(parents=True)
        paths['noctalia'].write_text('[dock]\nenabled=true\n')
        self.install(autostart=True)
        self.assertEqual((paths['settings'] / 'settings.json').read_text(), '{"iconSize":64,"future":true}')
        self.assertEqual((paths['settings'] / 'pinned.json').read_text(), '["kitty"]')
        self.assertEqual(paths['noctalia'].read_text(), '[dock]\nenabled=true\n')
        self.assertTrue(paths['autostart'].exists())
        self.assertIn('pragma IconTheme MacOS-Like-Dark', (paths['app'] / 'shell.qml').read_text())
        compile(paths['launcher'].read_text(), str(paths['launcher']), 'exec')

    def test_backup_and_restore_existing_and_absent(self):
        snap = m.backup()
        self.install(autostart=True)
        m.restore_snapshot(snap)
        self.assertFalse(m.paths()['app'].exists())
        self.assertFalse(m.paths()['launcher'].exists())
        self.assertFalse(m.paths()['settings'].exists())
        self.install()
        (m.paths()['settings'] / 'pinned.json').write_text('["kitty"]')
        snap2 = m.backup()
        (m.paths()['settings'] / 'pinned.json').write_text('[]')
        m.restore_snapshot(snap2)
        self.assertEqual((m.paths()['settings'] / 'pinned.json').read_text(), '["kitty"]')

    def test_failed_install_rolls_back(self):
        self.install()
        before = (m.paths()['app'] / 'shell.qml').read_bytes()
        real_write = m.atomic_write
        def fail_launcher(path, *args, **kw):
            if path == m.paths()['launcher']:
                raise OSError('injected disk failure')
            return real_write(path, *args, **kw)
        with patch.object(m, 'atomic_write', side_effect=fail_launcher):
            with self.assertRaises(OSError):
                self.install(autostart=True)
        self.assertEqual((m.paths()['app'] / 'shell.qml').read_bytes(), before)
        self.assertTrue(m.paths()['launcher'].exists())
        self.assertFalse(m.paths()['autostart'].exists())

    def test_symlink_not_overwritten(self):
        victim = self.home / 'keep'; victim.write_text('keep')
        p = m.paths()['launcher']; p.parent.mkdir(parents=True); p.symlink_to(victim)
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(victim.read_text(), 'keep')

    def test_bad_backup_rejected_before_changes(self):
        self.install()
        snap = m.backup()
        doc = json.loads((snap / 'manifest.json').read_text())
        doc['entries']['launcher']['path'] = '/tmp/wrong-target'
        (snap / 'manifest.json').write_text(json.dumps(doc))
        with self.assertRaises(ValueError):
            m.restore_snapshot(snap)
        self.assertTrue(m.paths()['app'].is_dir())

    def test_cli_uninstall_retains_pins_and_restores(self):
        self.install(autostart=True)
        (m.paths()['settings'] / 'pinned.json').write_text('["kitty"]')
        with patch.object(m, 'require_stopped'), patch('sys.argv', ['manage.py', 'uninstall']):
            m.main()
        self.assertFalse(m.paths()['app'].exists())
        self.assertEqual((m.paths()['settings'] / 'pinned.json').read_text(), '["kitty"]')
        backups = list((self.home / 'state/macdock/backups').iterdir())
        uninstall_backup = next(p for p in backups if set(json.loads((p / 'manifest.json').read_text())['entries']) == {'app','launcher','desktop','autostart','service','service_link'})
        m.restore_snapshot(uninstall_backup)
        self.assertTrue((m.paths()['app'] / 'shell.qml').exists())

    def test_noctalia_requires_successful_dock(self):
        with patch.object(m, 'health', side_effect=ValueError('not ready')), patch('sys.argv', ['manage.py', 'noctalia-disable']):
            with self.assertRaises(ValueError):
                m.main()
        self.assertFalse(m.paths()['noctalia'].exists())

    def test_noctalia_gui_state_and_restore(self):
        p = m.paths()['noctalia']; p.parent.mkdir(parents=True)
        original = '# keep\n[dock]\nenabled = true # comment\nicon_size = 65\n[wallpaper]\nenabled = false\n'
        p.write_text(original)
        snap = m.backup(['noctalia'])
        with patch.object(m, 'health', return_value={'ready': True}), patch('sys.argv', ['manage.py', 'noctalia-disable']):
            m.main()
        self.assertFalse(tomllib.loads(p.read_text())['dock']['enabled'])
        self.assertIn('# comment', p.read_text())
        m.restore_snapshot(snap)
        self.assertEqual(p.read_text(), original)

    def test_systemd_autostart_backup_restore(self):
        self.install(autostart='systemd')
        paths = m.paths()
        self.assertTrue(paths['service_link'].is_symlink())
        self.assertEqual(paths['service_link'].resolve(), paths['service'])
        self.assertFalse(paths['autostart'].exists())
        snap = m.backup()
        m.set_autostart('off', 'systemd')
        self.assertFalse(paths['service_link'].exists())
        m.restore_snapshot(snap)
        self.assertTrue(paths['service_link'].is_symlink())

    def test_toml_layouts(self):
        for s in ('', '[dock]\nicon_size=65\n', 'dock.enabled = true\n', '[dock]\nenabled=false\n'):
            out = m.disable_dock_toml(s)
            self.assertFalse(tomllib.loads(out)['dock']['enabled'])
        with self.assertRaises(ValueError):
            m.disable_dock_toml('dock = { enabled = true, size = 10 }\n')

    def test_missing_dependencies_no_install(self):
        with patch.object(m, 'check_dependencies', return_value=['qs']):
            with self.assertRaises(ValueError):
                m.install()
        self.assertFalse(m.paths()['app'].exists())


if __name__ == '__main__':
    unittest.main()
