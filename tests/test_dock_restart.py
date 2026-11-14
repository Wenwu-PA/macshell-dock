import sys,json,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
import dock_process as d
class DockRestart(unittest.TestCase):
 def result(self,code=0,text='',err=''):return subprocess.CompletedProcess([],code,text,err)
 def test_managed_service_needs_no_integration_marker(self):
  calls=[]
  def run(args):
   calls.append(args)
   return self.result(text=json.dumps({'app':'MacDock','ready':True,'items':7})) if args==d.HEALTH else self.result()
  self.assertEqual(d.restart(run)['items'],7)
  self.assertIn(['systemctl','--user','restart','macdock.service'],calls)
 def test_independent_config_stops_before_service_start(self):
  calls=[];state={'stopped':False,'started':False}
  def run(args):
   calls.append(args)
   if args[-1]=='is-active' or 'is-active' in args:return self.result(3)
   if args==d.HEALTH:
    return self.result(1) if state['stopped'] and not state['started'] else self.result(text=json.dumps({'app':'MacDock','ready':True,'items':7}))
   if args[-2:]==['lifecycle','stop']:state['stopped']=True
   if args==['systemctl','--user','start','macdock.service']:self.assertTrue(state['stopped']);state['started']=True
   return self.result()
  d.restart(run);self.assertTrue(state['started'])
 def test_stuck_old_instance_prevents_duplicate(self):
  calls=[]
  def run(args):
   calls.append(args)
   return self.result(3) if 'is-active' in args else self.result(text='{}')
  with patch.object(d.time,'sleep'),self.assertRaisesRegex(RuntimeError,'refusing to start a duplicate'):d.restart(run)
  self.assertNotIn(['systemctl','--user','start','macdock.service'],calls)
 def test_zero_exit_is_not_readiness(self):
  calls=[]
  def run(args):calls.append(args);return self.result(text='{"app":"MacDock","ready":true,"items":0}')
  with patch.object(d.time,'sleep'),self.assertRaisesRegex(RuntimeError,'model is empty'):d.restart(run)
  self.assertIn(['systemctl','--user','stop','macdock.service'],calls)
