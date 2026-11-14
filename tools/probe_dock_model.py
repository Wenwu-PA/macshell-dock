from pathlib import Path
import tempfile,shutil,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
with tempfile.TemporaryDirectory() as d:
 p=Path(d);shutil.copytree('app/MacDock',p/'app');shutil.copytree(Path.home()/'.config/macdock',p/'config/macdock');(p/'runtime').mkdir()
 dock=p/'app/MacDock.qml';text=dock.read_text();text=text[:text.index('    // ───────────── UI')]+ '}\n';dock.write_text(text)
 shell=p/'app/shell.qml';s=shell.read_text();i=s.rfind('}');s=s[:i]+'Timer { interval: 1800; running: true; onTriggered: { console.log("MODEL_PROBE",macDock.appCount,JSON.stringify(macDock.items.map(i=>i.key)));Qt.quit(); } }\n'+s[i:];shell.write_text(s)
 r=subprocess.run(['qs','-p',str(shell)],env=dict(os.environ,QT_QPA_PLATFORM='offscreen',XDG_RUNTIME_DIR=str(p/'runtime'),XDG_CONFIG_HOME=str(p/'config')),capture_output=True,text=True,timeout=8);print(r.stdout+r.stderr)
