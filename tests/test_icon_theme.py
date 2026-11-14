import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('icon_theme',ROOT/'bridge/icon_theme.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
class Theme(unittest.TestCase):
 def test_change_only_pragma_with_backup_and_no_repeat(self):
  with tempfile.TemporaryDirectory() as d,patch.object(t,'themes',return_value=[{'id':'MacOS-Like-Light'}]):
   p=Path(d)/'shell.qml';p.write_text('//@ pragma IconTheme MacOS-Like-Dark\nShellRoot {}\n');backup=Path(d)/'backups'
   self.assertTrue(t.apply('MacOS-Like-Light',p,backup));self.assertEqual(p.read_text(),'//@ pragma IconTheme MacOS-Like-Light\nShellRoot {}\n')
   stamp=p.stat().st_mtime_ns;self.assertFalse(t.apply('MacOS-Like-Light',p,backup));self.assertEqual(p.stat().st_mtime_ns,stamp)
   self.assertEqual(len(list(backup.iterdir())),1)
   with self.assertRaises(ValueError):t.apply('missing',p,backup)
