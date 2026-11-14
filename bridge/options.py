"""Validate custom application icon overrides."""
from pathlib import Path
def optional(c,out):
 if "iconOverrides" in c:
  icons=c["iconOverrides"]
  if not isinstance(icons,dict):raise ValueError("Invalid icon overrides")
  for app,path in icons.items():
   if not isinstance(app,str) or not app or not isinstance(path,str):raise ValueError("Invalid icon override")
   if not Path(path).is_absolute() or Path(path).suffix.lower() not in (".svg",".png") or not Path(path).is_file():raise ValueError("Icon must be an existing absolute SVG/PNG path")
  out["iconOverrides"]=icons
 return out
