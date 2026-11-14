#!/usr/bin/env python3
"""One-time, conflict-aware recovery of earlier MacDock-owned Bar settings/rules."""
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'legacy_bar'),str(HERE.parent/'bridge')]
import bar_style
if __name__=='__main__':
    state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'macdock'
    try:bar_style.restore(state/'bar-restore.json')
    except Exception as error:raise SystemExit('Legacy Bar recovery stopped; journal preserved: '+str(error))
