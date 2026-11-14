#!/usr/bin/env python3
"""Execute production reveal animation/Region geometry offscreen; not a Hyprland visual test."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
src=(ROOT/'app/MacDock/MacDock.qml').read_text()
a=src.index('                    property real revealProgress:');b=src.index('                    opacity: revealProgress',a)+len('                    opacity: revealProgress')
animation=src[a:b]
a=src.index('                Item {\n                    id: blurBody');b=src.index('\n                Item {\n                    id: dock',a)
body=src[a:b]
for width in (2560,1920):
 with tempfile.TemporaryDirectory(prefix='macdock-reveal-') as directory:
  root=Path(directory);runtime=root/'runtime';runtime.mkdir()
  code='''import QtQuick
import Quickshell
ShellRoot {
 id: root
 property real animationSpeed: .04
 Window {
  visible: true
  width: '''+str(width)+'''; height: 400
  Item {
   id: win; anchors.fill: parent
   property real margin: 7
   Item {
    id: ui; anchors.fill: parent
    property bool tucked: true
'''+body+'''
    Item { id: dock; width: 500; height: 70
'''+animation+'''
    }
   }
  }
 }
 property int steps: 0
 Timer { interval: 80; running: true; repeat: true
  onTriggered: {
   if (root.steps>0) {
    var shown=root.steps%2===1;
    if (Math.abs(dock.revealProgress-(shown?1:0))>.001 || (shown ? blurBody.height!==70 : blurBody.height!==0 || blurBody.width!==0)) {
     console.error("REVEAL_FAILED",root.steps,dock.revealProgress,blurBody.height);Qt.quit();return;
    }
   }
   if (root.steps===40) {console.log("REVEAL_CYCLES_OK=20");Qt.quit();return;}
   ui.tucked=root.steps%2===1;root.steps++;
  }
 }
}
'''
  path=root/'shell.qml';path.write_text(code)
  result=subprocess.run(['qs','-p',str(path)],env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_QPA_PLATFORMTHEME='generic',QT_QUICK_CONTROLS_STYLE='Basic',XDG_RUNTIME_DIR=str(runtime)),capture_output=True,text=True,timeout=10)
  output=result.stdout+result.stderr
  if 'REVEAL_CYCLES_OK=20' not in output:raise SystemExit(output)
  print(f'PASS {width}px: 20 real Qt show/hide animation cycles; hidden blur region empty')
print('NOT VERIFIED: compositor blur, cursor routing, magnification or flicker in Hyprland.')
