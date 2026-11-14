# Troubleshooting

Run installation in the actual Wayland session. Missing Noctalia IPC aborts before installation changes.
Use `noctalia plugins lint noctalia/plugin` offline and `noctalia msg plugins list` for a running shell.
The plugin normally installs to ~/.local/share/noctalia/plugins/macdock, honoring XDG_DATA_HOME.

A local-change error protects files not recognized as a previous release. Compare with a backup; do not remove
that guard or overwrite a lone manifest. Updates require the full matching QML/Luau/Python bundle.
If update acceptance fails, the installer restores the full prior Dock/plugin/JSON and reports restart errors.
That prior version may itself be broken. tools/restore_known_release.py can recover a supplied compatible local
backup; read its help and inspect that backup first. It is not a download of another release.

Do not kill Quickshell by process name. MacDock has its own configuration-specific IPC and macdock.service.
Restart in Control verifies a nonempty ready model; check journalctl if it reports failure.
A Supported blur capability report does not prove a rendered effect. Check compositor protocol availability,
opacity below 1, and your existing Hyprland blur configuration. MacDock does not modify global blur strength.

Report minimal reproduction steps and sanitized logs. Do not attach settings.json/pinned.json without reviewing
personal paths and application IDs. Include Quickshell, Noctalia and compositor versions.
