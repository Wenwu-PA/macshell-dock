# MacDock

A standalone macOS-style Dock for Hyprland, with native compositor blur and a small Noctalia control widget.
Built with Quickshell/QML, a Python bridge and Noctalia Luau plugins. Derived from MacShell; see [NOTICE](NOTICE).

## Screenshot

A verified desktop screenshot is not available yet. No mockup is presented as a running application.

## Features

- Native Hyprland blur confined to the rounded Dock body.
- Hover magnification, neighboring-icon falloff, launch and hide/show animations.
- Never / Always / Smart auto-hide, pinned applications and optional window previews.
- XDG icon themes, custom app icons and canonical desktop-entry resolution.
- Automatic display selection, explicit monitor selection and All Monitors.
- MacDock Control Bar widget for restart, enable, autostart, display, icon size/spacing and background opacity.
- Atomic settings writes, staged updates, backups and rollback.

## Requirements

- Linux with Hyprland/Wayland; Quickshell 0.3.2 and Python 3.11+.
- Qt 6 Quick, Quick Effects and Multimedia (provided through your distribution's Quickshell dependencies).
- Noctalia 5.4.1 / Plugin API 42 for the optional control integration.
- `inotify-tools`, `xdg-utils`, user systemd; an installed XDG icon theme.
- Native blur requires compositor support for `ext-background-effect-v1` and enabled compositor blur.

MacOS-Like is supported if already installed. No icon theme, font or wallpaper is bundled.
The Dock falls back to its translucent body when compositor blur is unavailable.

## Installation

```sh
git clone https://github.com/Wenwu-PA/macshell-dock.git
cd macshell-dock
./install.sh --deps # Arch/CachyOS: review the pacman packages before running
./install.sh
qs -c MacDock
```

The first install checks dependencies and chooses an installed icon theme. Run it as your regular user.
For an explicit theme, use `./install.sh --theme THEME_DIRECTORY_NAME`.
Stop a running Dock before a standalone installation; `~/.local/bin/macdock stop` targets this configuration only.
Noctalia and Hyprland are not replaced. No global blur strength is changed.

## Configuration

User preferences live in `$XDG_CONFIG_HOME/macdock/settings.json` (default `~/.config/macdock/settings.json`).
Pins live in `pinned.json`. Unknown keys are retained. These personal files are not part of the repository.
See [configuration](docs/CONFIGURATION.md) for advanced preferences and pin/icon behavior.

## Noctalia Integration

With Noctalia running in the actual Wayland session:

```sh
./install.sh --plugin
```

Open Noctalia's Bar widget editor, search **MacDock Control** and add it to Start, Center or End.
Capsule groups use the host's normal presentation. Clicking `wenwu/macdock:widget` toggles the existing
`wenwu/macdock:control` panel. The installer never places widgets in your Bar automatically.
The compact panel is the only custom settings UI; plugin Settings has no duplicate Dock parameters.

## Updating

```sh
git pull --ff-only
./install.sh --plugin-update
```

Integration updates require live Noctalia IPC. The installer validates known versions/local changes, stages
all scripts and QML, migrates preferences once, restarts the existing service, checks readiness and rolls back
failed acceptance. Unknown local edits are refused. Backups live under `$XDG_STATE_HOME/macdock/plugin-backups`.
Do not copy only plugin.toml: manifest, Luau, bridge and QML must be updated together.
Standalone installs can be repeated using `./install.sh` after stopping the Dock; preferences and pins are retained.

## Uninstallation

```sh
./install.sh --plugin-remove # with Noctalia running; remove your placed widget through its editor too
~/.local/bin/macdock stop
./uninstall.sh
```

User settings/pins and recovery backups are retained. Bar layouts are not rewritten.
Autostart is opt-in: `python3 tools/manage.py autostart on --backend systemd`; consult `--help` before changing it.

## Troubleshooting

```sh
~/.local/bin/macdock status
systemctl --user status macdock.service
journalctl --user -u macdock.service -n 50
noctalia plugins lint noctalia/plugin
```

`noctalia msg plugins list` requires the running shell. The command is `plugins`, not `plugin`.
See [troubleshooting and recovery](docs/TROUBLESHOOTING.md).

## Known Limitations

- Experimental v0.1.0 source preparation: live Hyprland/NVIDIA visual acceptance is outstanding. Automated/offscreen
  checks do not establish flicker-free reveal, working compositor blur or capsule input behavior.
- Native blur intensity follows compositor settings; MacDock does not change global blur settings.
- Some advanced preferences are JSON-only; Control deliberately has no scrolling or secondary editor pages.
- No screenshot, live wallpaper capture or custom optical shader is used.
- A matching Noctalia 5.4.1 API is required; later versions are not declared supported without testing.

## Development

```sh
python3 tools/check.py
noctalia plugins lint noctalia/plugin
python3 tools/check_reveal_geometry.py # optional offscreen Qt animation probe
```

The tests include isolated installation, update, persistence and rollback scenarios. Hardware/display acceptance
must be performed separately. MIT license and original copyright notices are retained.
