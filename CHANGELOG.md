# Changelog

## Unreleased

- Split **Apply Noctalia** and **Undo Noctalia** into separate controls.
  Repeated imports retain one original snapshot; Undo restores it in a single
  click and suspends icon-color sync until the next Apply.
- Keep Apply/Undo responsive after slider changes and verify Undo on disk.
- Prevent concurrent Noctalia palette sync from reapplying icon tint after Undo.
- Prevent the launcher lock from being inherited by Dock-launched applications
  (notably Zen Browser), which previously blocked service restarts.
- Treat `systemctl --user reset-failed` as optional if the unit is unloaded,
  including during installer rollback.
- Follow Noctalia 5.5.0's `dock.colorize_icons` and per-monitor overrides while
  preserving the 5.4.1 global-toggle fallback.
- Import compatible Noctalia Dock settings without modifying pins or unrelated
  preferences, and keep snapshots recoverable after Undo.
- Accept Noctalia 5.5.0 as well as 5.4.1 in the update preflight; avoid
  rejecting valid version output without the `v` prefix.
- Follow Noctalia's live app-icon palette and colorization toggle.
- Recover autostart after graphical login even when a previous session left
  the `integration-owned` marker; preserve independently running Dock instances.

## v0.1.0 — prepared, unreleased

- Standalone MacShell-derived Dock using native compositor blur.
- Compact Noctalia control widget and panel with JSON-backed preferences.
- Canonical desktop-entry matching, pin persistence and icon overrides.
- Reactive settings synchronization with stale-response protection.
- Coordinated reveal geometry and verified process restart handling.
- Staged installation, one-time migration, full backups and rollback.
- Removed working Liquid Glass and experimental Noctalia components.

Live Hyprland visual acceptance remains outstanding; no GitHub Release has been published.
