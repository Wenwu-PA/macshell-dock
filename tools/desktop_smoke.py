#!/usr/bin/env python3
"""Read-only offscreen test of production lookup against installed DesktopEntries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'app/MacDock/MacDock.qml').read_text()
start=source.index('    function lookup(');end=source.index('\n    }',start)+6
lookup=source[start:end]
ids=sys.argv[1:] or ['org.telegram.desktop','org.telegram.desktop.desktop','TelegramDesktop','kitty']
with tempfile.TemporaryDirectory(prefix='macdock-desktop-') as d:
 p=Path(d)/'shell.qml'
 p.write_text('''//@ pragma IconTheme MacOS-Like-Dark
import QtQuick
import Quickshell
ShellRoot {
 id: root
 property var entries: DesktopEntries.applications.values
'''+lookup+'''
 Timer { interval: 1000; running: true; onTriggered: {
 var ids='''+json.dumps(ids)+''';
 for (var i=0;i<ids.length;i++) {
  var e=root.lookup(ids[i]);
  console.log("RESOLVE="+JSON.stringify({requested:ids[i],id:e?e.id:null,startupClass:e?e.startupClass:null,icon:e?e.icon:null,path:e?Quickshell.iconPath(e.icon):null}));
 }
 Qt.quit();
 } }
}
''')
 r=subprocess.run(['qs','-p',str(p)],env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME='',QT_QUICK_CONTROLS_STYLE='Basic',XDG_RUNTIME_DIR=d),capture_output=True,text=True,timeout=10)
 print(r.stdout+r.stderr)
 sys.exit(r.returncode)
