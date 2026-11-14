"""Execute extracted production JS functions with Qt's JS engine (no compositor)."""
from pathlib import Path
import unittest
try:
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtQml import QJSEngine
except ImportError:
    QJSEngine = None


@unittest.skipIf(QJSEngine is None, 'Optional PySide6 unavailable')
class DockLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])
        cls.source = (Path(__file__).resolve().parents[1] / 'app/MacDock/MacDock.qml').read_text()

    def setUp(self):
        self.engine = QJSEngine()
        self.runjs('''var activated=[], launched=[], saved=null;
          var entries={kitty:{id:'kitty',name:'Kitty',execute:function(){launched.push('kitty')}}};
          var DesktopEntries={byId:function(id){return entries[id]||null},heuristicLookup:function(id){return entries[id.toLowerCase()]||null}};
          var ToplevelManager={toplevels:{values:[]}};
          var Quickshell={execDetached:function(args){launched.push(args)}};
          var launching={},pruneTimer={restart:function(){}},pinned=['kitty'];
          var pinBaseline=["kitty"]; var queueWrite=function(path,value){saved=value};
          var configDir="/tmp/macdock";
          var store={setText:function(s){saved=JSON.parse(s)}}, rebuild=function(){};
          var root={};
        ''')
        for name in ['persistPins','lookup','keyOf','appOf','windowsFor','activate','togglePin']:
            start = self.source.index('    function '+name+'(')
            end = self.source.index('\n    }', start) + len('\n    }')
            self.runjs(self.source[start:end])

    def runjs(self, source):
        result = self.engine.evaluate(source)
        self.assertFalse(result.isError(), result.toString())
        return result

    def test_cycles_windows_without_launching(self):
        self.runjs('ToplevelManager.toplevels.values=[{appId:"kitty",activated:true,activate:function(){activated.push(1)}},{appId:"kitty",activated:false,activate:function(){activated.push(2)}}]; activate({key:"kitty",appId:"kitty"},false)')
        self.assertEqual(self.runjs('JSON.stringify(activated)').toString(),'[2]')
        self.assertEqual(self.runjs('launched.length').toInt(),0)

    def test_new_window_launches_desktop_entry(self):
        self.runjs('activate({key:"kitty",appId:"kitty",entry:entries.kitty},true)')
        self.assertEqual(self.runjs('JSON.stringify(launched)').toString(),'["kitty"]')

    def test_preview_activates_its_window(self):
        self.runjs('activate({kind:"win",tl:{activate:function(){activated.push(7)}}},false)')
        self.assertEqual(self.runjs('JSON.stringify(activated)').toString(),'[7]')

    def test_pin_roundtrip_original_format(self):
        self.runjs('togglePin({key:"kitty",entry:entries.kitty})')
        self.assertEqual(self.runjs('JSON.stringify(saved)').toString(),'[]')
        self.runjs('togglePin({key:"kitty",entry:entries.kitty})')
        self.assertEqual(self.runjs('JSON.stringify(saved)').toString(),'["kitty"]')

    def test_startup_wmclass_is_case_insensitive(self):
        self.runjs("DesktopEntries.applications={values:[{id:'org.example.App',startupClass:'ExampleWM'}]}")
        self.assertEqual(self.runjs("keyOf('examplewm')").toString(),'org.example.app')

    def test_canonical_id_ending_in_desktop(self):
        self.runjs("entries['org.telegram.desktop']={id:'org.telegram.desktop',startupClass:'TelegramDesktop'}; DesktopEntries.applications={values:[entries['org.telegram.desktop']]}")
        for value in ('org.telegram.desktop','org.telegram.desktop.desktop','telegramdesktop'):
            self.assertEqual(self.runjs('keyOf('+repr(value)+')').toString(),'org.telegram.desktop')
        self.runjs("pinned=['org.telegram.desktop','org.telegram.desktop']; togglePin({key:'org.telegram.desktop',entry:entries['org.telegram.desktop']})")
        self.assertEqual(self.runjs('JSON.stringify(saved)').toString(),'[]')

    def test_unknown_app_falls_back_to_app_id(self):
        self.assertEqual(self.runjs('keyOf("Some.Unknown.App")').toString(),'some.unknown.app')


if __name__ == '__main__':
    unittest.main()
