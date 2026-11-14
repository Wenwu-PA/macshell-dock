#!/usr/bin/env python3
"""Shared atomic writer for Dock edits and integration. No shell interpolation."""
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile

def write(path,patch,expected=None):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with (path.parent/'.integration.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  old=json.loads(path.read_text()) if path.exists() else ([] if isinstance(patch,list) else {})
  if expected is not None and old!=expected:raise ValueError('Configuration changed externally; reload before retrying')
  if isinstance(patch,dict):
   if not isinstance(old,dict):raise ValueError('Expected object')
   new=dict(old,**patch)
  else:
   if not isinstance(patch,list) or not all(isinstance(x,str) for x in patch):raise ValueError('Expected desktop IDs')
   new=patch
  if old==new:return False
  fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.macdock-')
  try:
   with os.fdopen(fd,'w') as f:json.dump(new,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
   os.replace(tmp,path)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  return True
if __name__=='__main__':
 try:write(sys.argv[1],json.loads(sys.argv[2]),json.loads(sys.argv[3]) if len(sys.argv)>3 else None)
 except (ValueError,OSError) as e:sys.exit(str(e))
