"""Installed beside MacDock; survives removal of the Noctalia plugin directory."""
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))


def main():
    state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'macdock'
    owner=state/'integration-owned'
    if owner.exists():
        subprocess.run(['systemctl','--user','stop','macdock.service'],check=True,timeout=15)
        owner.unlink(missing_ok=True)
if __name__=='__main__':main()
