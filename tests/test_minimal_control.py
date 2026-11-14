from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MinimalControl(unittest.TestCase):
 def test_no_secondary_pages_or_scroll(self):
  source=(ROOT/'noctalia/plugin/panel.luau').read_text()
  for token in ('ui.scroll','openApplications','renderApps','reset-settings','icon-themes','noctalia.getConfig'):
   self.assertNotIn(token,source)
  for label in ('Icon Size','Icon Spacing','Background Opacity'):
   self.assertIn('slider("'+label+'"',source)
  for label in ('Corner Radius','Magnification Scale','Animation Speed'):
   self.assertNotIn('slider("'+label+'"',source)
 def test_native_blur_lifecycle_does_not_toggle_with_hide(self):
  source=(ROOT/'app/MacDock/MacDock.qml').read_text()
  self.assertIn('BackgroundEffect.blurRegion: nativeBlurRegion',source)
  self.assertIn('opacity: revealProgress',source)
  self.assertIn('Behavior on revealProgress',source)
  self.assertNotIn('Behavior on y { NumberAnimation { duration: 240',source)
  self.assertIn('Math.min(dock.height, ui.height - dock.y)',source)
