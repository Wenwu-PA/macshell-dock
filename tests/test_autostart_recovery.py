"""The Noctalia-owned service must restart after a graphical logout/login."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
import bridge


class AutostartRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        config = self.base / 'config/macdock'; config.mkdir(parents=True)
        (config / 'settings.json').write_text(json.dumps({'dockEnabled': True, 'automatic': True, 'iconSize': 64}))
        (config / 'pinned.json').write_text('["telegram"]')
        self.state = self.base / 'state/macdock'; self.state.mkdir(parents=True)
        self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.base/'config'), 'XDG_STATE_HOME': str(self.base/'state')})
        self.env.start()
        self.addCleanup(self.env.stop)

    def sync(self, behavior):
        calls = []
        def command(args):
            calls.append(args)
            return subprocess.CompletedProcess(args, behavior(args), '', '')
        with patch.object(bridge, 'command', side_effect=command), patch.object(sys, 'argv', ['bridge.py', 'sync', json.dumps({'background': '#252525'})]):
            bridge.main()
        self.assertEqual((self.base / 'config/macdock/pinned.json').read_text(), '["telegram"]')
        self.assertEqual(json.loads((self.base / 'config/macdock/settings.json').read_text())['iconSize'], 64)
        return calls

    def test_stale_ownership_marker_does_not_block_new_login(self):
        owner = self.state / 'integration-owned'; owner.touch()
        calls = self.sync(lambda args: 1 if args[0] == 'qs' or 'is-active' in args else 0)
        self.assertIn(['systemctl', '--user', 'start', 'macdock.service'], calls)
        self.assertTrue(owner.exists())

    def test_existing_independent_dock_is_not_started_or_claimed(self):
        calls = self.sync(lambda _args: 0)
        self.assertNotIn(['systemctl', '--user', 'start', 'macdock.service'], calls)
        self.assertFalse((self.state/'integration-owned').exists())

    def test_running_service_is_not_restarted_while_becoming_ready(self):
        owner = self.state / 'integration-owned'; owner.touch()
        calls = self.sync(lambda args: 1 if args[0] == 'qs' else 0)
        self.assertIn(['systemctl', '--user', 'is-active', 'macdock.service'], calls)
        self.assertNotIn(['systemctl', '--user', 'start', 'macdock.service'], calls)

    def test_start_failure_reports_error_for_service_retry(self):
        owner = self.state / 'integration-owned'; owner.touch()
        with self.assertRaisesRegex(RuntimeError, 'Dock:'):
            self.sync(lambda args: 1 if args[0] == 'qs' or 'is-active' in args or 'start' in args else 0)
        self.assertTrue(owner.exists())


if __name__ == '__main__':
    unittest.main()
