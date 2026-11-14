# Configuration

settings.json is the only Dock preference store. pinned.json is the existing ordered list of desktop-entry IDs.
Use the running Dock's context menu to pin/unpin apps. The resolver uses desktop IDs, StartupWMClass and
application identity; Telegram's canonical desktop ID is supported without a separate Telegram icon store.

Control exposes enable, autostart, monitor, iconSize, spacing and glassOpacity (the historical key now means
native-background opacity). Numeric edits persist on release. A save error is shown instead of reporting success.
Other retained keys include cornerRadius, magnificationEnabled, magnification, animationSpeed, hideMode
(never/always/smart), showRunning, showThumbs, iconTheme and iconOverrides. Custom icon overrides map app IDs to
absolute existing SVG/PNG paths; these are personal settings, not repository files.

monitor="" means All Monitors, "@auto" selects an available output, and a connector name expresses a preference.
Missing preferred outputs receive a temporary fallback; the preference is retained for hotplug.
runtimeMonitor is derived runtime state, not a second user configuration.

Back up JSON before manual edits. Atomic external replacement is supported by the QML FileView watcher.
No plugin.toml settings duplicate these preferences; internal panel placement is owned by Noctalia itself.
