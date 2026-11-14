import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
import monitors
class MonitorSelection(unittest.TestCase):
 def setUp(self):self.outputs=[{'name':'A'},{'name':'B'}]
 def test_auto_primary_before_focused(self):
  with patch.object(monitors,'connected',return_value=[{'name':'A','primary':True},{'name':'B','focused':True}]):self.assertEqual(monitors.resolve('@auto',self.outputs),'A')
 def test_auto_focused(self):
  with patch.object(monitors,'connected',return_value=[{'name':'B','focused':True}]):self.assertEqual(monitors.resolve('@auto',self.outputs),'B')
 def test_disconnected_preference_survives(self):
  preferred='B'
  with patch.object(monitors,'connected',return_value=[]):
   self.assertEqual(monitors.resolve(preferred,[{'name':'A'}]),'A')
   self.assertEqual(preferred,'B');self.assertEqual(monitors.resolve(preferred,self.outputs),'B')
 def test_all_and_no_outputs(self):
  self.assertEqual(monitors.resolve('',self.outputs),'');self.assertEqual(monitors.resolve('@auto',[]),'')
