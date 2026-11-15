"""The existing settings.json is the sole authority for editable Dock settings."""
import json
DEFAULTS={'enabled':True,'automatic':True,'monitor':'@auto','iconTheme':'','iconSize':52,'spacing':6,'glassOpacity':.42,'cornerRadius':18,'magnificationEnabled':True,'magnification':1.7,'animationSpeed':1,'hideMode':'smart','showRunning':True,'showThumbs':False,'iconOverrides':{},'noctaliaDockColorSync':True}
def read(path):
    raw=json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(raw,dict):raise ValueError('settings.json must be an object')
    result={k:raw.get('dockEnabled' if k=='enabled' else k,v) for k,v in DEFAULTS.items()}
    return result
