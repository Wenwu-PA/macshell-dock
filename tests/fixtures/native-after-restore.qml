// Extracted from MacShell 51db0bab6997da310d2aacfaa7084740ec44ad4a (MIT).
import QtQuick
import QtQuick.Effects
import QtQuick.Controls
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Wayland
import "I18n.js" as I18n
import "Fonts.js" as Fonts

Scope {
    id: root
    readonly property string dockStyle: "native"
    property bool windowCapture: true

    // shared helpers from shell.qml (window geometry poller, wallpaper lookup)
    readonly property var screens: Quickshell.screens
    property var hub: null
    property bool dockEnabled: true      // false = no Dock at all (settings window stays available)
    property bool settingsEnabled: true  // false = keep the System Settings window closed
    property bool desktopIcons: true     // show files, folders and .desktop shortcuts from the XDG Desktop directory
    property int desktopIconSize: 48     // Desktop icon size in logical pixels
    property var bar: hub ? hub.bar : null
    Connections {
        target: root.bar
        function onDarkModeChanged() {
            if (root.darkMode !== root.bar.darkMode) root.darkMode = root.bar.darkMode;
        }
        function onAppearanceModeChanged() {
            if (root.appearanceMode !== root.bar.appearanceMode) root.appearanceMode = root.bar.appearanceMode;
        }
    }
    property string userName: Quickshell.env("USER") || ""

    readonly property bool captureCut: hub ? hub.captureCut : false
    readonly property bool glassHold: hub ? hub.glassHold : false          // windows opening / closing: the glass's live captures pause, source stays attached
    readonly property bool previewHold: hub ? hub.previewHold : false
    readonly property bool captureHold: hub ? hub.captureHold : false     // windows opening / closing: the dock PREVIEW capture stops (source released 0.5 s later); the glass is not affected
    // appearance values shared by Dock and Menu Bar
    function setLook(k, v) { root[k] = v; if (bar) bar[k] = v; }
    // Appearance: the Menu Bar resolves "auto" (light by day, dark by night) and keeps both windows in step
    function setAppearance(mode) {
        if (["light", "dark", "auto"].indexOf(mode) < 0) return;
        appearanceMode = mode;
        if (mode === "auto") {
            var h = new Date().getHours();
            darkMode = bar && bar.autoIsDark ? bar.autoIsDark() : (h < 7 || h >= 19);
        } else darkMode = mode === "dark";
        // Update this window first so its palette reacts immediately, then keep the Menu Bar in sync.
        if (bar && bar.setAppearance) {
            bar.setAppearance(mode);
            appearanceMode = mode;
            darkMode = bar.darkMode;
        }
    }

    // ───────────── CONFIG ───────────── Lachowski
    property string tintMode: "theme"
    property color backgroundTint: "#202023"
    readonly property color effectiveBackgroundTint: tintMode === "custom" ? backgroundTint : (dockDark ? "#202023" : "#ffffff")
    property real borderWidth: 0.25
    property real borderOpacity: 0.12
    property real shadowStrength: 0
    property real magnificationRadius: 2.6
    property real animationSpeed: 1
    property bool showRunning: true
    property bool reserveSpace: true
    property string layerMode: "top"
    property bool groupWindows: false
    property var iconOverrides: ({})
    property var outputSettings: ({})
    property string monitor: ""          // "" = every monitor, or e.g. "DP-1"
    property int iconSize: 52
    property real magnification: 1.7     // peak icon scale
    property int spacing: 6
    property int hPad: 10
    property int topPad: 8
    property int bottomPad: 9            // room under icons (running dots live here)
    property int cornerRadius: 18
    readonly property real uiS: bar ? bar.uiScale : 1      // UI scale (Settings → Menu Bar): Settings / About windows follow it
    property int margin: 6
    property bool darkMode: true
    // the dock keeps one fixed look (dark): switching the system between Light and Dark does not change its colours
    readonly property bool dockDark: darkMode
    property string appearanceMode: "dark"      // light | dark | auto (kept in step with the Menu Bar, see setAppearance)
    // The Dock's own real-time switch (Dock Preferences -> Appearance). It used to follow the Menu Bar's "Real-time glass" toggle, which is OFF by
    // default, so the Dock glass was a 15 fps, pause-while-windows-open snapshot unless that was found and switched on.
    property real glassOpacity: 0.42     // 0 = fully clear; below the layerrule's ignore_alpha (0.2) the blur turns off
    // "smart"  = hide while a non-floating window is open on that monitor's workspace
    // "always" = always auto-hide, "never" = always visible and reserves space
    property string hideMode: "smart"
    property bool showTrash: true
    property string fontFamily: "Sans Serif"  // bundled in assets/fonts (shell.qml loads it); falls back to the system font if missing
    readonly property string boldFontFamily: hub && hub.boldFontFamily ? hub.boldFontFamily : "Open Runde Semibold"
    // Open Runde: bold text uses its Semibold face; another selected font keeps its own family (and real bold weight)
    function fontForWeight(weight, regularFamily) { return (Number(weight) >= Font.DemiBold && regularFamily === "Open Runde") ? boldFontFamily : regularFamily; }
    onFontFamilyChanged: if (fontFamily.indexOf("Inter") === 0) fontFamily = "Open Runde"
    property bool magnificationEnabled: true
    property bool showLabels: true       // hover tooltips
    property bool showIndicators: true   // dots under running apps
    property bool bounceOnLaunch: true
    property bool showThumbs: true       // open windows get a live preview cell next to the Trash
    property int hideDelay: 450          // ms before the dock hides after the pointer leaves
    readonly property var accentChoices: [
        { name: "Blue",     c: "#0a84ff" }, { name: "Purple", c: "#bf5af2" },
        { name: "Pink",     c: "#ff375f" }, { name: "Red",    c: "#ff453a" },
        { name: "Orange",   c: "#ff9f0a" }, { name: "Yellow", c: "#ffd60a" },
        { name: "Green",    c: "#30d158" }, { name: "Graphite", c: "#8e8e93" }
    ]
    property color accent: "#0A84FF"     // menu highlight (macOS blue)
    // Dock icon tint: every icon is re-coloured with one colour (works with any icon pack)
    property bool iconTint: false
    property string iconTintColor: "#0a84ff"
    property real iconTintStrength: 1.0
    readonly property var tintChoices: [
        { name: "Blue",     c: "#0a84ff" }, { name: "Purple", c: "#bf5af2" }, { name: "Pink",  c: "#ff375f" },
        { name: "Red",      c: "#ff453a" }, { name: "Orange", c: "#ff9f0a" }, { name: "Yellow", c: "#ffd60a" },
        { name: "Green",    c: "#30d158" }, { name: "Teal",   c: "#40c8e0" }, { name: "Graphite", c: "#8e8e93" },
        { name: "White",    c: "#ffffff" }, { name: "Black",  c: "#1c1c1e" }
    ]
    readonly property var defaultPinned: [
        "org.gnome.Nautilus", "org.kde.dolphin", "thunar",
        "firefox", "zen", "chromium", "google-chrome",
        "kitty", "com.mitchellh.ghostty", "Alacritty", "foot",
        "code", "discord", "spotify", "steam", "obsidian"
    ]   // used until you change pins from the dock; unknown ids are skipped
    property var pinned: defaultPinned
    // ──────────────────────────────────

    QtObject { id: prefsWindow; property bool visible: false; function requestActivate() {} }

    readonly property real effMag: magnificationEnabled ? magnification : 1
    // hover labels and the right-click menu scale with the Dock (52 px icons = the reference size)
    readonly property real labelK: Math.max(0.7, Math.min(2.2, iconSize / 52))
    readonly property int bgHeight: iconSize + topPad + bottomPad
    readonly property int sepWidth: 9
    readonly property real magRadius: (iconSize + spacing) * magnificationRadius
    readonly property int menuRoom: 300
    readonly property int windowHeight: Math.ceil(margin + bgHeight + iconSize * (effMag - 1) + 72 + menuRoom)
    readonly property string configDir: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/macdock"

    property var items: []
    property int appCount: 0
    property int sepCount: 0
    readonly property real totalW0: Math.max(0, appCount * (iconSize + spacing) + sepCount * (sepWidth + spacing) - spacing)
    property var launching: ({})
    property var knownKeys: ({})
    // the Dock's cells live in a keyed ListModel updated in place: a cell is only created when its item appears and
    // only destroyed after it has animated out — every other cell (and its live window preview) keeps running
    property var itemMap: ({})
    ListModel { id: dockModel }
    function syncModel(list) {
        var m = dockModel;
        for (var i = 0; i < list.length; i++) {
            var k = list[i].key;
            if (i < m.count && m.get(i).key === k) continue;
            var j = -1;
            for (var x = i + 1; x < m.count; x++) if (m.get(x).key === k) { j = x; break; }
            if (j >= 0) m.move(j, i, 1); else m.insert(i, { key: k });
        }
        while (m.count > list.length) m.remove(m.count - 1);
    }
    property var leaving: ({})          // key → time it started leaving
    readonly property int leaveMs: 340
    Timer { id: leaveTimer; interval: root.leaveMs + 30; onTriggered: root.rebuild() }
    property string lastSig: ""

    // ───────────── LOGIC ─────────────
    Process { id: openSettingsProcess; command: ["noctalia", "msg", "panel-toggle", "wenwu/macdock:control"] }

    function openPrefs(pane) {
        if (!settingsEnabled) return;
        if (bar) {
            darkMode = bar.darkMode;
            appearanceMode = bar.appearanceMode;
        }
        if (!openSettingsProcess.running) openSettingsProcess.running = true;
    }

    function togglePrefs(pane) {
        if (prefsWindow.visible) prefsWindow.visible = false;
        else openPrefs(pane);
    }

    property var pinBaseline: []
    function persistPins(value) {
        queueWrite(configDir + "/pinned.json", value, pinBaseline);
        pinBaseline = value.slice();
    }

    function resetPins() {
        pinned = defaultPinned;
        persistPins(defaultPinned.slice());
        rebuild();
    }

    function resetSettings() {
        dockEnabled = true;
        settingsEnabled = true;
        if (bar) {
            bar.resetSettings();
            bar.uiSounds = true; bar.gamingMode = false; bar.gamingAuto = true; bar.lockArtBackground = true;
            bar.applyLockClockPreset("glass");
            bar.wallpaperAppearance = "auto"; bar.notifDnd = false; bar.nightOn = false; bar.keepAwake = false;
            bar.kbRepeatRate = 35; bar.kbRepeatDelay = 250; bar.mouseSens = 0; bar.mouseNatural = false;
            bar.tpNatural = true; bar.tpTap = true; bar.tpDwt = true; bar.tpScroll = 0.7;
        }
        if (hub && hub.widgets) { hub.widgets.tempUnit = "C"; hub.widgets.locMode = "auto"; hub.widgets.cityName = ""; hub.widgets.widgetScale = 1.0; }
        desktopIcons = true; desktopIconSize = 48;
        iconSize = 52; magnification = 1.7; magnificationEnabled = true;
        spacing = 6; margin = 6; cornerRadius = 18;
        darkMode = true; appearanceMode = "dark"; glassOpacity = 0.42; accent = "#0a84ff"; fontFamily = "Open Runde";
        iconTint = false; iconTintColor = "#0a84ff"; iconTintStrength = 1.0;
        hideMode = "smart"; hideDelay = 450; monitor = "";
        showTrash = true; showLabels = true; showIndicators = true; bounceOnLaunch = true; showThumbs = true; windowCapture = true; }

    // ── settings persistence (~/.config/macdock/settings.json) ──
    readonly property string settingsSig: [tintMode, String(backgroundTint), JSON.stringify(iconOverrides), borderWidth, borderOpacity, shadowStrength, magnificationRadius, animationSpeed, showRunning, reserveSpace, layerMode, groupWindows, outputSettings, dockEnabled, settingsEnabled, desktopIcons, desktopIconSize, iconSize, magnification, magnificationEnabled, spacing, margin,
        cornerRadius, darkMode, appearanceMode, glassOpacity, dockStyle, String(accent), fontFamily, hideMode, hideDelay, monitor,
        showTrash, showLabels, showIndicators, bounceOnLaunch, showThumbs, windowCapture, iconTint, iconTintColor, iconTintStrength].join("|")
    property bool settingsReady: false
    property bool settingsLoading: false
    onSettingsSigChanged: if (settingsReady && !settingsLoading) saveTimer.restart()
    onShowTrashChanged: { rebuild(); if (showTrash) trashCheck(); }
    onShowThumbsChanged: rebuild()
    onShowRunningChanged: rebuild()
    onGroupWindowsChanged: rebuild()
    onWindowCaptureChanged: rebuild()

    function flushSettings() { if (saveTimer.running) { saveTimer.stop(); saveSettings(); } }
    Component.onDestruction: flushSettings()
    property bool stopping: false
    function requestStop() { flushSettings(); stopping = true; runWriter(); }
    property var writeQueue: []
    function queueWrite(path, value, expected) {
        var args = ["python3", decodeURIComponent(Qt.resolvedUrl("config_store.py").toString().replace("file://", "")), path, JSON.stringify(value)];
        if (expected !== undefined) args.push(JSON.stringify(expected));
        writeQueue = writeQueue.concat([args]);
        runWriter();
    }
    function runWriter() {
        if (configWriter.running) return;
        if (writeQueue.length === 0) { if (stopping) Qt.quit(); return; }
        configWriter.command = writeQueue[0];
        writeQueue = writeQueue.slice(1);
        configWriter.running = true;
    }
    Process {
        id: configWriter
        stderr: StdioCollector { onStreamFinished: if (text.trim()) console.warn("MacDock persistence:", text.trim()) }
        onExited: (code, status) => {
            if (code !== 0) { root.writeQueue = []; settingsStore.reload(); store.reload(); }
            Qt.callLater(root.runWriter);
        }
    }
    property var originalSettings: ({})
    function saveSettings() {
        var o = {
            dockEnabled: dockEnabled, settingsEnabled: settingsEnabled, desktopIcons: desktopIcons, desktopIconSize: desktopIconSize, iconSize: iconSize, magnification: magnification, magnificationEnabled: magnificationEnabled,
            spacing: spacing, margin: margin, cornerRadius: cornerRadius,
            darkMode: darkMode, appearanceMode: appearanceMode, glassOpacity: glassOpacity, dockStyle: dockStyle, accent: String(accent), fontFamily: fontFamily,
            hideMode: hideMode, hideDelay: hideDelay, monitor: monitor,
            showTrash: showTrash, showLabels: showLabels, showIndicators: showIndicators,
            bounceOnLaunch: bounceOnLaunch, showThumbs: showThumbs, windowCapture: windowCapture, iconTint: iconTint, iconTintColor: iconTintColor, iconTintStrength: iconTintStrength
        };
        var merged = Object.assign({}, originalSettings, o);
        merged.tintMode = tintMode; merged.backgroundTint = String(backgroundTint); merged.iconOverrides = iconOverrides; merged.borderWidth = borderWidth; merged.borderOpacity = borderOpacity; merged.shadowStrength = shadowStrength; merged.magnificationRadius = magnificationRadius; merged.animationSpeed = animationSpeed; merged.showRunning = showRunning; merged.reserveSpace = reserveSpace; merged.layerMode = layerMode; merged.groupWindows = groupWindows; merged.outputSettings = outputSettings; 
        var patch = {};
        for (var key in merged) if (JSON.stringify(merged[key]) !== JSON.stringify(originalSettings[key])) patch[key] = merged[key];
        if (Object.keys(patch).length) queueWrite(configDir + "/settings.json", patch);
        originalSettings = merged;
    }

    function applySettings(o) {
        if (!o || typeof o !== "object") return;
        originalSettings = o;
        var keys = ["tintMode", "backgroundTint", "iconOverrides", "borderWidth", "borderOpacity", "shadowStrength", "magnificationRadius", "animationSpeed", "showRunning", "reserveSpace", "layerMode", "groupWindows", "outputSettings", "dockEnabled", "settingsEnabled", "desktopIcons", "desktopIconSize", "iconSize", "magnification", "magnificationEnabled", "spacing", "margin", "cornerRadius",
                    "darkMode", "appearanceMode", "glassOpacity", "accent", "fontFamily", "hideMode", "hideDelay", "monitor",
                    "showTrash", "showLabels", "showIndicators", "bounceOnLaunch", "showThumbs", "windowCapture", "iconTint", "iconTintColor", "iconTintStrength"];
        for (var i = 0; i < keys.length; i++) {
            if (o[keys[i]] === undefined) continue;
            try { root[keys[i]] = o[keys[i]]; } catch (err) { }
        }
    }

    FileView {
        id: settingsStore
        watchChanges: true
        onFileChanged: reload()
        path: root.configDir + "/settings.json"
        printErrors: false
        onLoaded: {
            root.settingsLoading = true;
            saveTimer.stop();
            try { root.applySettings(JSON.parse(text())); } catch (err) { console.warn("MacDock settings:", err); }
            root.settingsLoading = false;
            root.settingsReady = true;
            root.outputSettings = {};
        }
        onLoadFailed: root.settingsReady = true
    }
    Timer { id: saveTimer; interval: 400; onTriggered: root.saveSettings() }

    // MacShell's own windows (About This Linux, Settings, Finder, Photos ...) all have the app id "org.quickshell":
    // they show the MacShell logo and name instead of a generic icon
    readonly property string appsIconPath: "view-app-grid"
    readonly property string logoPath: "preferences-system"
    function isShellApp(appId) { return appId === "org.macshell.MacDock"; }

    function lookup(appId) {
        if (!appId) return null;
        var e = DesktopEntries.byId(String(appId));
        if (!e && String(appId).endsWith(".desktop")) e = DesktopEntries.byId(String(appId).slice(0, -8));
        if (!e && DesktopEntries.applications) {
            var entries = DesktopEntries.applications.values;
            for (var n = 0; n < entries.length; n++) {
                if (String(entries[n].startupClass || "").toLowerCase() === String(appId).toLowerCase()) { e = entries[n]; break; }
            }
        }
        if (!e && DesktopEntries.heuristicLookup) e = DesktopEntries.heuristicLookup(appId);
        return e;
    }

    function keyOf(appId) {
        var e = lookup(appId);
        return (e ? e.id : appId).toLowerCase();
    }

    // stable ids so a window's preview cell isn't rebuilt on every refresh
    property var winIdList: []
    property int winIdNext: 1
    function winIdFor(tl) {
        for (var i = 0; i < winIdList.length; i++) if (winIdList[i].tl === tl) return winIdList[i].id;
        var id = winIdNext++;
        winIdList.push({ tl: tl, id: id, born: Date.now() });
        return id;
    }
    function winAge(tl) {
        for (var i = 0; i < winIdList.length; i++) if (winIdList[i].tl === tl) return Date.now() - winIdList[i].born;
        return 0;
    }
    Timer { id: youngWin; interval: 250; onTriggered: root.rebuild() }

    function iconSrc(icon) {
        if (!icon) return Quickshell.iconPath("application-x-executable");
        if (icon.charAt(0) === "/") return "file://" + icon;
        return Quickshell.iconPath(icon, "application-x-executable");
    }
    // icon of a dock cell; the Trash switches to the "full" icon while there is something in it
    function cellIconSrc(it) {
        if (it && !it.special && iconOverrides[it.appId || it.key]) return iconSrc(iconOverrides[it.appId || it.key]);
        if (it && it.special === "trash" && trashFull) {
            var p = Quickshell.iconPath("user-trash-full", true);
            if (p !== "") return p;
        }
        return iconSrc(it ? it.icon : "");
    }

    // ── Trash state: the standard XDG trash (~/.local/share/Trash/files) is what Dolphin's trash:/ shows ──
    // inotifywait (inotify-tools) reports changes at once; without it the folder is checked every 3 s.
    property bool trashFull: false
    property bool trashReady: false           // first check done (it also creates the folder, which inotifywait needs)
    property bool trashPoll: false            // no inotifywait: poll instead
    readonly property string trashDir: {
        var x = Quickshell.env("XDG_DATA_HOME");
        return ((x && x !== "") ? x : Quickshell.env("HOME") + "/.local/share") + "/Trash/files";
    }
    function trashCheck() { if (!trashCheckProc.running) trashCheckProc.running = true; }
    Process {
        id: trashCheckProc
        command: ["sh", "-c", "mkdir -p \"$1\"; if [ -n \"$(ls -A \"$1\" 2>/dev/null | head -n 1)\" ]; then s=1; else s=0; fi; "
                              + "if command -v inotifywait >/dev/null 2>&1; then w=w; else w=p; fi; echo \"$s $w\"", "sh", root.trashDir]
        stdout: StdioCollector {
            onStreamFinished: {
                var t = text.trim().split(" ");
                root.trashFull = t[0] === "1";
                root.trashPoll = t[1] === "p";
                root.trashReady = true;
            }
        }
    }
    Process {
        id: trashWatch
        running: root.showTrash && root.trashReady && !root.trashPoll
        command: ["inotifywait", "-m", "-q", "-e", "create", "-e", "delete", "-e", "moved_to", "-e", "moved_from", root.trashDir]
        stdout: SplitParser { onRead: data => trashDebounce.restart() }
    }
    // Empty Trash: KDE's ktrash when it exists (it also cleans trashes on other drives and keeps Dolphin's trash icon in sync),
    // otherwise the standard XDG trash folder is cleared directly. (gio is not used: without gvfs it "succeeds" without doing anything.)
    function emptyTrash() {
        Quickshell.execDetached(["sh", "-c",
            "command -v ktrash6 >/dev/null 2>&1 && ktrash6 --empty && exit 0; "
            + "command -v ktrash5 >/dev/null 2>&1 && ktrash5 --empty && exit 0; "
            + "d=\"${XDG_DATA_HOME:-$HOME/.local/share}/Trash\"; "
            + "chmod -R u+w \"$d/files\" 2>/dev/null; "
            + "find \"$d/files\" \"$d/info\" -mindepth 1 -delete 2>/dev/null; "
            + "rm -f \"$d/directorysizes\""]);
        trashAfterEmpty.restart();
        if (bar) bar.playSound("trash", 0.8);
    }
    Timer { id: trashAfterEmpty; interval: 900; onTriggered: root.trashCheck() }
    Timer { id: trashDebounce; interval: 150; onTriggered: root.trashCheck() }
    Timer { interval: 3000; repeat: true; running: root.showTrash && root.trashPoll; onTriggered: root.trashCheck() }

    // bumped (debounced) whenever windows open, close or change focus; thumbnails re-pick their window from it
    property int windowTick: 0
    Timer { id: tickDebounce; interval: 120; onTriggered: root.windowTick++ }

    // the window an unpinned app is represented by: the focused one, else the first
    function thumbWindow(key) {
        var w = windowsFor(key);
        for (var i = 0; i < w.length; i++) if (w[i].activated) return w[i];
        return w.length > 0 ? w[0] : null;
    }

    // MacShell's own windows all have the app id "org.quickshell": the Clock window counts as the Clock app
    function appOf(tl) { return (tl.appId === "org.macshell.MacDock" && tl.title === "Clock") ? "macshell-clock" : tl.appId; }
    function windowsFor(key) {
        var out = [];
        var tls = ToplevelManager.toplevels.values;
        for (var i = 0; i < tls.length; i++) {
            if (tls[i].appId && keyOf(appOf(tls[i])) === key) out.push(tls[i]);
        }
        return out;
    }

    function activate(item, forceNew) {
        if (item.kind === "win") { if (item.tl) item.tl.activate(); return; }
        if (item.special === "apps") return;
        if (item.special === "trash") {
            // the file manager first (Dolphin understands trash:/ natively); xdg-open only as the last resort
            Quickshell.execDetached(["sh", "-c",
                "if command -v dolphin >/dev/null 2>&1; then exec dolphin trash:/; fi; "
                + "for fm in nautilus thunar nemo pcmanfm-qt; do if command -v $fm >/dev/null 2>&1; then exec $fm trash:///; fi; done; "
                + "exec xdg-open trash:///"]);
            return;
        }
        var wins = windowsFor(item.key);
        if (wins.length > 0 && !forceNew) {
            var idx = -1;
            for (var i = 0; i < wins.length; i++) if (wins[i].activated) idx = i;
            wins[(idx + 1) % wins.length].activate();
            return;
        }
        if (item.entry || item.key) {
            var L = {};
            for (var k in launching) L[k] = launching[k];
            L[item.key] = Date.now();
            launching = L;
            // resolve the desktop entry again at click time: the one stored in the dock model can be a stale object
            // (after the app database reloads it turned into "TypeError ... execute is not a function", and Files never opened)
            var ent = null;
            var rid = item.appId || item.key;
            try { ent = DesktopEntries.byId(rid); } catch (err) { ent = null; }
            if (!ent) { try { ent = DesktopEntries.heuristicLookup ? DesktopEntries.heuristicLookup(item.key) : null; } catch (err2) { ent = null; } }
            var ok = false;
            if (ent && typeof ent.execute === "function") { try { ent.execute(); ok = true; } catch (err3) { ok = false; } }
            if (!ok) {
                var id = rid;
                console.log("[macdock] launching", id, "via gtk-launch (desktop entry unavailable)");
                Quickshell.execDetached(["sh", "-c", 'gtk-launch "$1" 2>/dev/null || gtk-launch "$1.desktop" 2>/dev/null || exec "$1"', "sh", id]);
            }
            pruneTimer.restart();
        }
    }

    function togglePin(item) {
        var out = [], found = false;
        for (var i = 0; i < pinned.length; i++) {
            var id = keyOf(String(pinned[i]));
            if (id.toLowerCase() === item.key) { found = true; continue; }
            out.push(pinned[i]);
        }
        if (!found && item.entry) out.push(item.entry.id);
        pinned = out;
        persistPins(out);
        rebuild();
    }

    function reorderPinned(from, to) {
        var vis = [];
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            if (it.kind === "app" && it.pinned && (!it.special || it.special === "apps")) vis.push(it);
            else break;
        }
        if (from < 0) return;
        if (from >= vis.length) {
            // "Apps" dragged out of its default spot (after the separators / windows) into the pinned block
            var ai = items[from];
            if (!ai || ai.special !== "apps") return;
            vis.splice(Math.max(0, Math.min(to, vis.length)), 0, ai);
        } else {
            var moved = vis.splice(from, 1)[0];
            vis.splice(Math.max(0, Math.min(to, vis.length)), 0, moved);
        }

        var out = [], have = {};
        for (var v = 0; v < vis.length; v++) { out.push(vis[v].special === "apps" ? "__apps" : vis[v].entry.id); have[vis[v].key] = true; }
        for (var p = 0; p < pinned.length; p++) {
            var id = keyOf(String(pinned[p]));
            if (!have[id.toLowerCase()]) out.push(pinned[p]);
        }
        pinned = out;
        persistPins(out);
        rebuild();
    }

    function resetAppsSlot() {
        var out = [];
        for (var i = 0; i < pinned.length; i++) if (String(pinned[i]) !== "__apps") out.push(pinned[i]);
        pinned = out;
        persistPins(out);
        rebuild();
    }

    function menuFor(item) {
        var m = [];
        if (item.kind === "win") {
            m.push({ kind: "item", label: I18n.tr("Show"), run: function () { activate(item, false); } });
            m.push({ kind: "item", label: I18n.tr("Close"), run: function () { var t = item.tl; if (!t) return; if (root.hub) root.hub.closeQuietly(function () { if (t) t.close(); }); else t.close(); } });
            m.push({ kind: "sep" });
            m.push({ kind: "item", label: I18n.tr("Settings\u2026"), run: function() { root.openPrefs(); } });
            return m;
        }
        if (item.special === "apps") {
            m.push({ kind: "item", label: I18n.tr("Open"), run: function () { activate(item, false); } });
            if (item.pinned) m.push({ kind: "item", label: I18n.tr("Reset Position"), run: function () { resetAppsSlot(); } });
            m.push({ kind: "sep" });
            m.push({ kind: "item", label: I18n.tr("Settings\u2026"), run: function() { root.openPrefs(); } });
            return m;
        }
        if (item.special === "trash") {
            m.push({ kind: "item", label: I18n.tr("Open"), run: function () { activate(item, false); } });
            m.push({ kind: "item", label: I18n.tr("Empty Trash"), confirm: true, disabled: !trashFull, run: function () { root.emptyTrash(); } });
            m.push({ kind: "sep" });
            m.push({ kind: "item", label: I18n.tr("Settings\u2026"), run: function() { root.openPrefs(); } });
            return m;
        }
        var wins = windowsFor(item.key);
        if (wins.length > 0) {
            for (var i = 0; i < wins.length && i < 8; i++) {
                (function (w) {
                    var t = w.title && w.title.length > 0 ? w.title : item.name;
                    m.push({ kind: "item", label: (w.activated ? "\u2713  " : "") + t,
                             run: function () { w.activate(); } });
                })(wins[i]);
            }
            m.push({ kind: "sep" });
        }
        if (item.entry) {
            m.push({ kind: "item", label: item.pinned ? I18n.tr("Remove from Dock") : I18n.tr("Keep in Dock"),
                     run: function () { togglePin(item); } });
            m.push({ kind: "item", label: wins.length > 0 ? I18n.tr("New Window") : I18n.tr("Open"),
                     run: function () { activate(item, true); } });
        }
        if (wins.length > 0) {
            m.push({ kind: "sep" });
            m.push({ kind: "item", label: I18n.tr("Quit"), run: function () {
                var ws = windowsFor(item.key);
                var closeAll = function () { for (var j = 0; j < ws.length; j++) { try { if (ws[j]) ws[j].close(); } catch (err) { } } };
                if (root.hub) root.hub.closeQuietly(closeAll); else closeAll();
            } });
        }
        
        m.push({ kind: "sep" });
        m.push({ kind: "item", label: I18n.tr("Settings\u2026"), run: function() { root.openPrefs(); } });

        return m;
    }

    function rebuild() {
        var tls = ToplevelManager.toplevels.values;
        var running = {};
        var runOrder = [];
        for (var i = 0; i < tls.length; i++) {
            var id = appOf(tls[i]);
            if (!id) continue;
            var k = keyOf(id);
            if (!running[k]) { running[k] = true; runOrder.push({ key: k, appId: id }); }
        }

        var L = {}, now = Date.now(), changed = false;
        for (var lk in launching) {
            if (!running[lk] && now - launching[lk] < 8000) L[lk] = launching[lk];
            else changed = true;
        }
        if (changed) launching = L;

        var list = [], seen = {};
        for (var p = 0; p < pinned.length; p++) {
            if (String(pinned[p]) === "__apps") continue;
            var e = lookup(String(pinned[p]));
            if (!e) continue;
            var ek = e.id.toLowerCase();
            if (seen[ek]) continue;
            seen[ek] = true;
            list.push({ kind: "app", key: ek, appId: e.id, name: e.name, icon: e.icon, entry: e,
                        running: !!running[ek], pinned: true });
        }

        var extras = [];
        for (var r = 0; r < runOrder.length; r++) if (root.showRunning && !seen[runOrder[r].key]) extras.push(runOrder[r]);
        if (extras.length > 0 && list.length > 0) list.push({ kind: "sep", key: "sep:run" });
        for (var x = 0; x < extras.length; x++) {
            var e2 = lookup(extras[x].appId);
            var own = isShellApp(extras[x].appId);
            list.push({ kind: "app", key: extras[x].key, appId: e2 ? e2.id : extras[x].appId,
                        name: own ? "MacDock" : (e2 ? e2.name : extras[x].appId),
                        icon: own ? logoPath : (e2 ? e2.icon : extras[x].appId.toLowerCase()),
                        entry: e2, running: true, pinned: false });
        }

        // window previews: one cell per open window, in their own section next to the Trash
        var winItems = [], liveWins = [], previewApps = {};
        if (showThumbs) {
            for (var w = 0; w < tls.length; w++) {
                var tl = tls[w];
                if (!tl.appId || tl.title === "MacDock Settings") continue;
                // live capture off: a preview cell is only an app icon, so a pinned app (its icon is already in the Dock) gets none; unpinned apps keep theirs
                if (!windowCapture && seen[keyOf(appOf(tl))]) continue;
                var appKey = keyOf(appOf(tl));
                if (root.groupWindows && previewApps[appKey]) continue;
                previewApps[appKey] = true;
                var e3 = lookup(appOf(tl));
                var wid = winIdFor(tl);
                liveWins.push(tl);
                if (winAge(tl) < 200) { if (!youngWin.running) youngWin.start(); continue; }     // no preview (= no capture) for brand-new windows
                var own3 = isShellApp(tl.appId);
                winItems.push({ kind: "win", key: "win:" + wid, tl: tl,
                                name: own3 ? (tl.title || "MacShell") : (e3 ? e3.name : tl.appId),
                                icon: own3 ? logoPath : (e3 ? e3.icon : tl.appId.toLowerCase()),
                                entry: null, running: false, pinned: false });
            }
        }
        var keep = [];
        for (var wi = 0; wi < winIdList.length; wi++) if (liveWins.indexOf(winIdList[wi].tl) >= 0) keep.push(winIdList[wi]);
        winIdList = keep;

        // [apps…] | [windows…] | Apps (Spotlight's application list) | Trash
        list.push({ kind: "sep", key: "sep:win" });
        for (var wj = 0; wj < winItems.length; wj++) list.push(winItems[wj]);
        if (winItems.length > 0) list.push({ kind: "sep", key: "sep:trash" });
        if (showTrash) {
            list.push({ kind: "app", key: "__trash", name: "Trash", icon: "user-trash",
                        entry: null, running: false, pinned: true, special: "trash" });
        }

        var firstBuild = (lastSig === "");
        // closed apps / windows don't vanish: they stay for a moment as "leaving" cells that shrink and fade out —
        // the opening animation played backwards — then are dropped by leaveTimer's rebuild
        var liveKeys = {};
        for (var lq = 0; lq < list.length; lq++) if (list[lq].key) liveKeys[list[lq].key] = true;
        var LV = {};
        for (var lk2 in leaving) if (!liveKeys[lk2] && now - leaving[lk2] < leaveMs) LV[lk2] = leaving[lk2];
        if (!firstBuild) {
            var prev = items || [];
            for (var pv = 0; pv < prev.length; pv++) {
                var po = prev[pv];
                if (!po.key || liveKeys[po.key]) continue;
                if (LV[po.key] === undefined) { if (po.leaving) continue; LV[po.key] = now; }
                // put it back after the item that preceded it last time
                var at = 0;
                for (var pb = pv - 1; pb >= 0; pb--) {
                    var ix = -1;
                    for (var q = 0; q < list.length; q++) if (list[q].key === prev[pb].key) { ix = q; break; }
                    if (ix >= 0) { at = ix + 1; break; }
                }
                var cp = {};
                for (var f in po) cp[f] = po[f];
                cp.leaving = true; cp.leaveAt = LV[po.key]; cp.fresh = false;
                cp.tl = null;          // the window is gone: never capture a destroyed toplevel (that crashed the shell)
                list.splice(at, 0, cp);
            }
        }
        leaving = LV;
        var anyLeaving = false;
        for (var lk3 in LV) { anyLeaving = true; break; }
        if (anyLeaving) leaveTimer.restart();

        var nowKeys = {}, nA = 0, nS = 0, sig = [];
        for (var n = 0; n < list.length; n++) {
            var it = list[n];
            it.nA = nA; it.nS = nS;
            if (it.kind === "sep") nS++; else nA++;
            if (it.key && !it.leaving) {
                it.fresh = !firstBuild && !knownKeys[it.key];
                nowKeys[it.key] = true;
            }
            sig.push(it.kind + ":" + (it.key || "") + ":" + it.running + ":" + (it.icon || "") + (it.leaving ? ":L" : ""));
        }
        appCount = nA;
        sepCount = nS;
        knownKeys = nowKeys;

        var s = sig.join("|");
        if (s !== lastSig) {
            lastSig = s;
            var map = {};
            for (var mi = 0; mi < list.length; mi++) map[list[mi].key] = list[mi];
            itemMap = map;
            items = list;
            syncModel(list);
        }
    }

    // ═════════════ LIQUID GLASS BACKEND ═════════════
    readonly property bool liquidActive: false
    readonly property bool settingsGlass: false
    readonly property string glassState: "disabled"
    readonly property string glassError: ""

    // ── smart hide: which monitors have a non-floating window on their active workspace ──
    property var busyMonitors: ({})
    property var monData: []
    property bool refreshPending: false

    function refreshBusy() {
        if (monProc.running || clientProc.running) { refreshPending = true; return; }
        monProc.running = true;
    }

    // Match the 0.3.0 method: recompute directly from hyprctl's monitor/client snapshot after each compositor event.
    function computeBusy(clients) {
        if (!Array.isArray(clients)) clients = [];
        var busy = {};
        for (var m = 0; m < monData.length; m++) {
            var mon = monData[m];
            if (!mon || mon.id === undefined || !mon.name) continue;
            var ids = [mon.activeWorkspace && mon.activeWorkspace.id !== undefined ? mon.activeWorkspace.id : -999];
            if (mon.specialWorkspace && mon.specialWorkspace.id !== undefined && mon.specialWorkspace.id !== 0) ids.push(mon.specialWorkspace.id);
            for (var c = 0; c < clients.length; c++) {
                var cl = clients[c];
                if (!cl || cl.floating || !cl.mapped || cl.hidden) continue;
                if (cl.monitor !== mon.id) continue;
                if (!cl.workspace || cl.workspace.id === undefined) continue;
                if (ids.indexOf(cl.workspace.id) >= 0) { busy[mon.name] = true; break; }
            }
        }
        busyMonitors = busy;
    }

    Process {
        id: monProc
        command: ["hyprctl", "-j", "monitors"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.monData = JSON.parse(text); } catch (err) { root.monData = []; }
                clientProc.running = true;
            }
        }
    }
    Process {
        id: clientProc
        command: ["hyprctl", "-j", "clients"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.computeBusy(JSON.parse(text)); } catch (err) { root.computeBusy([]); }
                if (root.refreshPending) { root.refreshPending = false; monProc.running = true; }
            }
        }
    }
    Connections {
        target: Hyprland
        function onRawEvent(event) { busyDebounce.restart(); tickDebounce.restart(); }
    }
    Timer { id: busyDebounce; interval: 120; onTriggered: root.refreshBusy() }

    Component.onCompleted: {
        Quickshell.execDetached(["mkdir", "-p", configDir]);
        rebuild();
        refreshBusy();
        trashCheck();
        }

    FileView {
        id: store
        watchChanges: true
        onFileChanged: reload()
        path: root.configDir + "/pinned.json"
        printErrors: false
        onLoaded: {
            try {
                var a = JSON.parse(text());
                if (Array.isArray(a)) { root.pinBaseline = a.slice(); root.pinned = a; root.rebuild(); }
            } catch (err) { }
        }
    }

    Connections {
        target: ToplevelManager.toplevels
        function onValuesChanged() { root.rebuild(); settle.restart(); tickDebounce.restart(); }
    }
    Connections {
        target: DesktopEntries.applications
        function onValuesChanged() { root.rebuild(); }
    }
    Timer { id: settle; interval: 350; onTriggered: root.rebuild() }
    Timer { id: pruneTimer; interval: 8200; onTriggered: root.rebuild() }

    // ───────────── UI ─────────────
    Variants {
        model: (root.settingsReady && root.dockEnabled) ? Quickshell.screens : []

        PanelWindow {
            id: win
            required property var modelData
            screen: modelData
            readonly property var output: root.outputSettings[modelData.name] || ({})
            readonly property int iconSize: output.iconSize === undefined ? root.iconSize : output.iconSize
            readonly property real magnification: output.magnification === undefined ? root.magnification : output.magnification
            readonly property int margin: output.margin === undefined ? root.margin : output.margin
            readonly property string hideMode: output.hideMode === undefined ? root.hideMode : output.hideMode
            readonly property real effMag: root.magnificationEnabled ? magnification : 1
            readonly property real magRadius: (iconSize + root.spacing) * root.magnificationRadius
            readonly property real labelK: Math.max(0.7, Math.min(2.2, iconSize / 52))
            readonly property int bgHeight: iconSize + root.topPad + root.bottomPad
            readonly property int windowHeight: Math.ceil(margin + bgHeight + iconSize * (effMag - 1) + 72 + root.menuRoom)
            readonly property real totalW0: Math.max(0, root.appCount * (iconSize + root.spacing) + root.sepCount * (root.sepWidth + root.spacing) - root.spacing)
            readonly property bool liquidActive: false

            readonly property bool glassVisible: visible && win.liquidActive && !ui.tucked
            visible: output.enabled !== false && (root.monitor === "" || modelData.name === root.monitor || (!Quickshell.screens.some(s => s.name === root.monitor) && modelData === Quickshell.screens[0]))

            anchors { left: true; right: true; bottom: true }
            implicitHeight: win.windowHeight
            color: "transparent"

            exclusionMode: ExclusionMode.Normal
            exclusiveZone: root.reserveSpace && win.hideMode === "never" ? win.bgHeight + win.margin : 0

            WlrLayershell.namespace: "macdock"
            // Native protocol region tracks only the rounded body, not the full-width window.
            BackgroundEffect.blurRegion: root.dockStyle === "native" && !win.liquidActive && !ui.tucked && win.visible ? nativeBlurRegion : null
            Region {
                id: nativeBlurRegion
                item: dock
                radius: Math.round(Math.min(root.cornerRadius, dock.height / 2))
            }
            WlrLayershell.layer: root.layerMode === "overlay" ? WlrLayer.Overlay : WlrLayer.Top

            mask: Region { item: maskItem }

            // the lifted item lives in its own full-screen, click-through overlay so it can go anywhere on the screen
            // (the Dock's own surface only covers the bottom of the screen — it used to be cut off half way up)
            PanelWindow {
                id: tearWin
                screen: win.modelData
                visible: ui.tearing || tearLaunch.running || tearHome.running || ghostFade.running || oldOut.running
                anchors { left: true; right: true; top: true; bottom: true }
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                mask: Region {}
                WlrLayershell.namespace: "macdock-drag"
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
                // the window where it WAS: a still copy that takes its place the instant the real window jumps to the
                // pointer, then fades and sinks away — so the old spot never just blinks empty
                Item {
                    id: oldSnap
                    property bool shown: false
                    visible: shown && opacity > 0.01
                    opacity: 0
                    transformOrigin: Item.Center
                    RectangularShadow { anchors.fill: parent; radius: 10; blur: 30; offset.y: 8; color: Qt.rgba(0, 0, 0, 0.30) }
                    Rectangle { anchors.fill: parent; radius: 10; color: Qt.rgba(0.09, 0.08, 0.09, 0.88) }
                    ScreencopyView {
                        id: oldSv
                        anchors.fill: parent
                        live: false
                        layer.enabled: true
                        layer.effect: MultiEffect { maskEnabled: true; maskSource: oldMask; maskThresholdMin: 0.5; maskSpreadAtMin: 1.0 }
                    }
                    Item { id: oldMask; anchors.fill: parent; visible: false; layer.enabled: true; Rectangle { anchors.fill: parent; radius: 10; color: "black" } }
                    ParallelAnimation {
                        id: oldOut
                        NumberAnimation { target: oldSnap; property: "opacity"; from: 1; to: 0; duration: 340 * root.animationSpeed; easing.type: Easing.OutCubic }
                        NumberAnimation { target: oldSnap; property: "scale"; from: 1; to: 0.94; duration: 420 * root.animationSpeed; easing.type: Easing.OutQuint }
                        onFinished: { oldSnap.shown = false; oldSv.captureSource = null; }
                    }
                }
                Item {
                    id: tearGhost
                    property real zoom: 1
                    property real wob: 0
                    readonly property bool isWin: ui.tearItem !== null && ui.tearItem.kind === "win"
                    // a window preview is picked up like the window itself: the higher it's pulled out of the Dock the
                    // closer it gets to the window's real size, held near its title bar (no wiggle — it's a window)
                    readonly property real liftRaw: isWin ? Math.max(0, Math.min(1, (ui.activeTop - ui.tearY) / 240)) : 0
                    property real lift: 1 - Math.pow(1 - liftRaw, 3)
                    Behavior on lift { NumberAnimation { duration: 140 * root.animationSpeed; easing.type: Easing.OutCubic } }
                    readonly property real thumbW: 170
                    readonly property real liftW: thumbW + (ui.tearW - thumbW) * lift
                    readonly property real grabFy: 0.5 + (0.035 - 0.5) * lift
                    readonly property real offY: tearWin.height - win.height   // Dock surface → screen coordinates
                    visible: opacity > 0.01
                    width: isWin ? liftW : win.iconSize * 1.12
                    height: isWin ? liftW * ui.tearH / ui.tearW : width
                    x: ui.tearX - width / 2
                    y: offY + ui.tearY - height * (isWin ? grabFy : 0.5)
                    scale: zoom
                    rotation: isWin ? 0 : wob
                    Image {
                        visible: !tearGhost.isWin
                        anchors.fill: parent
                        source: ui.tearSrc
                        sourceSize: Qt.size(256, 256)
                        smooth: true; mipmap: true
                    }
                    RectangularShadow {
                        visible: tearGhost.isWin
                        anchors.fill: parent; radius: 10
                        offset.y: 6 + 14 * tearGhost.lift; blur: 18 + 32 * tearGhost.lift; spread: 0
                        color: Qt.rgba(0, 0, 0, 0.30 + 0.15 * tearGhost.lift)
                    }
                    // translucent windows (terminals) get Hyprland's blur behind them; the lifted copy can't, so it gets a
                    // dark backing instead — otherwise it reads as a faint see-through ghost, not the window
                    Rectangle {
                        visible: tearGhost.isWin
                        anchors.fill: parent; radius: 10
                        color: Qt.rgba(0.09, 0.08, 0.09, 0.88)
                    }
                    SafeCapture {
                        id: gsv
                        visible: tearGhost.isWin
                        anchors.fill: parent
                        want: (tearGhost.isWin && tearWin.visible && ui.tearItem && ui.tearItem.tl) ? ui.tearItem.tl : null
                        wantLive: tearGhost.isWin && tearWin.visible && tearGhost.visible
                        layer.enabled: true
                        layer.effect: MultiEffect { maskEnabled: true; maskSource: gsvMask; maskThresholdMin: 0.5; maskSpreadAtMin: 1.0 }
                    }
                    Item { id: gsvMask; anchors.fill: parent; visible: false; layer.enabled: true; Rectangle { anchors.fill: parent; radius: 10; color: "black" } }
                    Rectangle {
                        visible: tearGhost.isWin
                        anchors.fill: parent; radius: 10; color: "transparent"
                        border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.25)
                    }
                    // light wiggle while held
                    SequentialAnimation on wob {
                        running: ui.tearing
                        loops: Animation.Infinite
                        NumberAnimation { to: 2.5; duration: 90 * root.animationSpeed; easing.type: Easing.InOutSine }
                        NumberAnimation { to: -2.5; duration: 180 * root.animationSpeed; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 0; duration: 90 * root.animationSpeed; easing.type: Easing.InOutSine }
                    }
                }
            }

            Item {
                id: ui
                anchors.fill: parent

                // pointer x, followed EXACTLY (no animation). This used to ease over 55 ms, restarted on every pointer event: moving
                // the mouse quickly left the magnification a few frames behind the pointer, worse with many icons
                property real mx: 0
                // raw pointer x as the events arrive; ui.mx (which every cell's scale is bound to) takes it once per FRAME. A 1000 Hz mouse
                // used to re-evaluate every cell's bindings + the Row layout hundreds of times a second, more with more pinned apps.
                property real rawMx: 0
                FrameAnimation {
                    running: hh.hovered && !ui.dragging
                    onTriggered: if (ui.mx !== ui.rawMx && (!ui.menuOpen || hh.point.position.y > ui.activeTop)) ui.mx = ui.rawMx
                }
                property bool revealed: false
                property var menuItem: null
                property var menuModel: []
                property string armed: ""            // label of a confirm-type entry that was clicked once (e.g. Empty Trash)
                property real menuTailX: -1
                function updateMenuTail() {
                    if (!menuOpen) return;
                    var w = menuW;
                    var idealX = menuCx - w / 2;
                    var clampedX = Math.max(8, Math.min(ui.width - w - 8, idealX));
                    menuTailX = Math.round(menuCx - clampedX);
                }
                onMenuItemChanged: {
                    armed = "";
                    if (menuItem === null) {
                        menuCell = null;
                        menuIconTop = -1;
                        menuTailX = -1;
                    } else {
                        updateMenuTail();
                    }
                }
                // the cell the right-click menu belongs to: while the menu is open it follows that icon (its centre and its top edge), the
                // way the hover label does, as the icons magnify and the Dock widens / narrows
                property Item menuCell: null
                property real menuIconTop: -1
                function syncMenu() {
                    var c = menuCell;
                    if (!c || !c.iconImg) return;
                    var p = c.mapToItem(ui, c.width / 2, 0);
                    if (Math.abs(p.x - menuCx) > 0.05) menuCx = p.x;
                    var t = c.iconImg.mapToItem(ui, 0, 0).y;
                    if (Math.abs(t - menuIconTop) > 0.05) menuIconTop = t;
                    if (menuTailX < 0) updateMenuTail();
                }
                FrameAnimation { running: ui.menuOpen && ui.menuCell !== null; onTriggered: ui.syncMenu() }
                property real menuCx: 0
                // the menu is as wide as its longest entry (measured here whenever a menu is built)
                property real menuTextW: 0
                readonly property real menuW: Math.max(Math.round(168 * win.labelK), Math.min(Math.round(360 * win.labelK), Math.ceil(menuTextW) + Math.round(38 * win.labelK)))
                TextMetrics {
                    id: menuTm
                    font.pixelSize: Math.max(9, Math.round(13 * win.labelK))
                    font.family: root.fontForWeight(Font.Normal, root.fontFamily)
                }
                function measureMenu() {
                    var w = 0;
                    for (var i = 0; i < menuModel.length; i++) {
                        var e = menuModel[i];
                        if (e.kind === "sep") continue;
                        menuTm.text = I18n.tr(e.label);
                        w = Math.max(w, menuTm.advanceWidth);
                        if (e.confirm === true) { menuTm.text = I18n.tr("Click again to confirm"); w = Math.max(w, menuTm.advanceWidth); }
                    }
                    menuTextW = w;
                }
                onMenuModelChanged: {
                    measureMenu();
                    updateMenuTail();
                }
                readonly property bool menuOpen: menuItem !== null
                readonly property bool wantsHide: win.hideMode === "always"
                    || (win.hideMode === "smart" && root.busyMonitors[win.modelData.name] === true)
                property bool dragging: false
                property int dragIndex: -1
                property int dragTarget: -1
                property string dragKey: ""
                property bool dragTail: false          // "Apps" is being dragged out of its default spot (everything between shifts, separators included)
                property real dragPressX: 0
                property real dragDelta: 0
                property real dragShiftW: 0
                property bool justDragged: false
                // tear-off: an icon dragged up out of the Dock follows the pointer (wiggling); dropped over the desktop it
                // zooms up and fades while the app opens / comes to the front, dropped back on the Dock it flies home
                property bool tearing: false
                property var tearItem: null
                property string tearSrc: ""
                property real tearX: 0
                property real tearY: 0
                property real tearHomeX: 0
                property real tearHomeY: 0
                // window being dragged: its real size (capped) and Hyprland address
                property real tearW: 900
                property real tearH: 600
                property string tearAddr: ""
                // the real window: once its preview (pulled out of the Dock) has grown to the window's size, the real window
                // takes over under the pointer and follows it (like Super + drag) until the button is let go; a still copy
                // fades away where it used to be
                property bool following: false
                property bool oldVisible: false
                NumberAnimation { id: ghostFade; target: tearGhost; property: "opacity"; to: 0; duration: 180 * root.animationSpeed; easing.type: Easing.OutCubic }
                onTearXChanged: if (following) Qt.callLater(moveReal)
                onTearYChanged: {
                    if (following) Qt.callLater(moveReal);
                    else if (tearing && tearAddr && tearGhost.liftRaw >= 1) handoff();
                }
                function wsel() { return 'window = "address:' + tearAddr + '"'; }
                function realPos() {
                    return { x: Math.round(win.modelData.x + tearX - tearW / 2),
                             y: Math.round(win.modelData.y + tearGhost.offY + tearY - tearH * 0.035) };
                }
                function moveReal() {
                    if (!following || !tearAddr) return;
                    var p = realPos();
                    Hyprland.dispatch('hl.dsp.window.move({ x = ' + p.x + ', y = ' + p.y + ', "exact", ' + wsel() + ' })');
                }
                function handoff() {
                    if (following || !tearAddr) return;
                    following = true;
                    var mon = Hyprland.monitorFor(win.modelData);
                    var ws = (mon && mon.activeWorkspace) ? String(mon.activeWorkspace.name) : "";
                    var p = realPos(), sel = wsel();
                    if (ws) Hyprland.dispatch('hl.dsp.window.move({ workspace = "' + ws + '", follow = false, ' + sel + ' })');
                    Hyprland.dispatch('hl.dsp.window.fullscreen_state({ internal = 0, client = 0, ' + sel + ' })');
                    Hyprland.dispatch('hl.dsp.window.float({ action = "enable", ' + sel + ' })');
                    Hyprland.dispatch('hl.dsp.window.set_prop({ prop = "no_anim", value = "1", ' + sel + ' })');
                    Hyprland.dispatch('hl.dsp.window.resize({ x = ' + Math.round(tearW) + ', y = ' + Math.round(tearH) + ', "exact", ' + sel + ' })');
                    Hyprland.dispatch('hl.dsp.window.move({ x = ' + p.x + ', y = ' + p.y + ', "exact", ' + sel + ' })');
                    if (tearItem && tearItem.tl) tearItem.tl.activate();
                    if (oldVisible) { oldSnap.scale = 1; oldSnap.opacity = 1; oldSnap.shown = true; oldOut.restart(); }
                    // the real window appears exactly where its preview is, the preview fades off it
                    ghostFade.restart();
                }
                function finishFollow() {
                    following = false;
                    tearing = false;
                    if (tearAddr) Hyprland.dispatch('hl.dsp.window.set_prop({ prop = "no_anim", value = "0", ' + wsel() + ' })');
                    tearAddr = "";
                    if (!ghostFade.running) tearItem = null;
                    else ghostFade.finished.connect(function () { if (!ui.tearing) ui.tearItem = null; });
                }
                function hyprOf(tl) {
                    var v = Hyprland.toplevels.values;
                    for (var i = 0; i < v.length; i++) if (v[i].wayland === tl) return v[i];
                    return null;
                }
                function beginTear(item, src, homeX, homeY) {
                    if (dragging) { dragTarget = dragIndex; endDrag(); }
                    menuItem = null;
                    tearItem = item; tearSrc = src; tearHomeX = homeX; tearHomeY = homeY;
                    tearGhost.opacity = 1; tearGhost.zoom = 1;
                    following = false; ghostFade.stop();
                    tearAddr = "";
                    if (item.kind === "win") {
                        var h = hyprOf(item.tl), o = h ? h.lastIpcObject : null;
                        tearAddr = h ? ("0x" + h.address.replace(/^0x/, "")) : "";
                        var sw = win.modelData.width, sh = win.modelData.height;
                        var w = (o && o.size) ? o.size[0] : (gsv.implicitWidth || 900);
                        var hh = (o && o.size) ? o.size[1] : (gsv.implicitHeight || 600);
                        // a fullscreen / huge window comes off as a comfortable floating size, like macOS restoring it
                        var k = Math.min(1, (sw * 0.78) / w, (sh * 0.78) / hh);
                        tearW = Math.round(w * k); tearH = Math.round(hh * k);
                        // where it is now: if that's on screen here, a still copy will stand in for it at the hand-off
                        var mon0 = Hyprland.monitorFor(win.modelData);
                        oldSnap.shown = false; oldOut.stop();
                        oldVisible = !!(o && o.at && o.workspace && mon0 && mon0.activeWorkspace && o.workspace.id === mon0.activeWorkspace.id);
                        if (oldVisible) {
                            oldSnap.x = o.at[0] - win.modelData.x; oldSnap.y = o.at[1] - win.modelData.y;
                            oldSnap.width = o.size[0]; oldSnap.height = o.size[1];
                            oldSv.captureSource = item.tl;          // one still frame (live: false)
                        }
                    }
                    tearing = true;
                }
                function endTear() {
                    if (!tearing) return;
                    // a window: let go wherever the pointer is — it simply stays there
                    if (tearAddr && (following || tearY < activeTop - 30)) {
                        if (!following) handoff();
                        finishFollow();
                        justDragged = true;
                        Qt.callLater(function () { ui.justDragged = false; });
                        return;
                    }
                    tearing = false;
                    justDragged = true;
                    Qt.callLater(function () { ui.justDragged = false; });
                    if (tearY < activeTop - 30) {
                        tearLaunch.item = tearItem;
                        tearLaunch.restart();               // enlarge + fade, then open / focus
                    } else {
                        // back on the Dock: the preview flies home and the window fades back in where it was
                        tearHome.restart();                 // back to its place
                    }
                }

                function pinnedCount() {
                    var n = 0;
                    for (var i = 0; i < root.items.length; i++) {
                        var it = root.items[i];
                        if (it.kind === "app" && it.pinned && (!it.special || it.special === "apps")) n++;
                        else break;
                    }
                    return n;
                }
                function naturalCenter(i) {
                    var c = rep.itemAt(i);
                    return c ? row.mapToItem(ui, c.x + c.width / 2, 0).x : 0;
                }
                function beginDrag(index, key, pressX, shiftW) {
                    menuItem = null;
                    dragIndex = index;
                    dragTarget = index;
                    dragKey = key;
                    dragTail = index >= pinnedCount();
                    dragPressX = pressX;
                    dragDelta = 0;
                    dragShiftW = shiftW;
                    dragging = true;
                }
                function dragUpdate(absX) {
                    dragDelta = absX - dragPressX;
                    var center = naturalCenter(dragIndex) + dragDelta;
                    var P = pinnedCount(), t = 0;
                    for (var j = 0; j < P; j++) {
                        if (j === dragIndex) continue;
                        if (naturalCenter(j) < center) t++;
                    }
                    // from its default spot "Apps" only moves once it is dropped among the pinned icons
                    if (dragTail) { dragTarget = (t >= P) ? dragIndex : t; return; }
                    dragTarget = t;
                }
                function shiftFor(i) {
                    if (dragIndex < i && i <= dragTarget) return -dragShiftW;
                    if (dragTarget <= i && i < dragIndex) return dragShiftW;
                    return 0;
                }
                function endDrag() {
                    var from = dragIndex, to = dragTarget;
                    dragging = false;
                    dragKey = "";
                    dragIndex = -1;
                    dragTarget = -1;
                    dragTail = false;
                    dragDelta = 0;
                    justDragged = true;
                    Qt.callLater(function () { ui.justDragged = false; });
                    if (to !== from) root.reorderPinned(from, to);
                }

                SequentialAnimation {
                    id: tearLaunch
                    property var item: null
                    ParallelAnimation {
                        NumberAnimation { target: tearGhost; property: "zoom"; to: tearGhost.isWin ? 2.0 : 2.6; duration: 460 * root.animationSpeed; easing.type: Easing.OutQuint }
                        NumberAnimation { target: tearGhost; property: "opacity"; to: 0; duration: 460 * root.animationSpeed; easing.type: Easing.OutCubic }
                        NumberAnimation { target: tearGhost; property: "wob"; to: 0; duration: 200 * root.animationSpeed }
                    }
                    ScriptAction { script: { if (tearLaunch.item) root.activate(tearLaunch.item, false); ui.tearItem = null; } }
                }
                ParallelAnimation {
                    id: tearHome
                    NumberAnimation { target: ui; property: "tearX"; to: ui.tearHomeX; duration: 420 * root.animationSpeed; easing.type: Easing.OutQuint }
                    NumberAnimation { target: ui; property: "tearY"; to: ui.tearHomeY; duration: 420 * root.animationSpeed; easing.type: Easing.OutQuint }
                    NumberAnimation { target: tearGhost; property: "wob"; to: 0; duration: 200 * root.animationSpeed }
                    onFinished: { ui.tearItem = null; ui.tearAddr = ""; }
                }

                readonly property bool tucked: wantsHide && !revealed && !menuOpen && !dragging && !tearing
                readonly property real refLeft: (width - win.totalW0) / 2
                readonly property real activeTop: height - win.margin - win.bgHeight
                                                  - win.iconSize * (win.effMag - 1) - 12
                readonly property bool active: dragging || (hh.hovered && !tucked && (hh.point.position.y > activeTop || (menuOpen && hh.point.position.y > menu.y)))
                property real strength: active ? 1 : 0
                Behavior on strength { NumberAnimation { duration: 140 * root.animationSpeed; easing.type: Easing.OutCubic } }

                HoverHandler {
                    id: hh
                    onPointChanged: {
                        if (!hovered || ui.dragging) return;
                        ui.rawMx = point.position.x;
                        if (ui.strength < 0.02) ui.mx = ui.rawMx;     // coming in from outside: start under the pointer
                    }
                    onHoveredChanged: {
                        if (hovered) { hideTimer.stop(); ui.revealed = true; }
                        else hideTimer.restart();
                    }
                }
                Timer { id: hideTimer; interval: root.hideDelay; onTriggered: if (!ui.dragging) ui.revealed = false }

                // Built from per-window captures (not a screen capture) so the Dock never ends up refracting itself.
                

                Item {
                    id: maskItem
                    // The input region only changes in 64 px steps while the Dock breathes under magnification (it used to follow dock.width
                    // exactly: a new Wayland input region every frame of every pointer move). Always a superset of the Dock.
                    readonly property real maskW: hh.hovered ? Math.min(ui.width, Math.ceil((dock.width + 8) / 64) * 64) : dock.width
                    x: ui.menuOpen ? 0 : (ui.width - maskW) / 2
                    width: ui.menuOpen ? ui.width : maskW
                    y: ui.menuOpen ? 0 : (ui.tucked ? ui.height - 3 : (hh.hovered ? ui.activeTop : dock.y))
                    height: ui.height - y
                }

                Item {
                    id: dock
                    width: row.width + root.hPad * 2
                    height: win.bgHeight
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: ui.height - win.margin - height + (ui.tucked ? height + win.margin + 6 : 0)
                    Behavior on y { NumberAnimation { duration: 240 * root.animationSpeed; easing.type: Easing.OutCubic } }

                    

                    Rectangle {
                        visible: !win.liquidActive
                        anchors.fill: parent
                        radius: root.cornerRadius
                        color: root.dockStyle === "transparent" ? "transparent" : Qt.rgba(root.effectiveBackgroundTint.r, root.effectiveBackgroundTint.g, root.effectiveBackgroundTint.b, root.dockStyle === "solid" ? 1 : root.glassOpacity)
                        layer.enabled: root.shadowStrength > 0 && root.dockStyle !== "transparent"
                        layer.effect: MultiEffect { shadowEnabled: true; shadowOpacity: root.shadowStrength; shadowBlur: 0.7; shadowVerticalOffset: 3; autoPaddingEnabled: true }
                        border.width: 0      // dark outer border removed

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 0
                            radius: parent.radius - 0.35
                            color: "transparent"
                            border.width: root.borderWidth
                            border.color: Qt.rgba(1, 1, 1, root.borderOpacity)
                        }
                    }

                    // same extra edge detail as the top-bar menus: faint dominant-colour edge (no dark hairline)
                    MenuBorder {
                        visible: win.liquidActive
                        anchors.fill: parent      // no z: stays below the icon row, so magnified icons are drawn over the border
                        cornerR: root.cornerRadius
                        dark: root.dockDark
                        tint: root.bar ? root.bar.menuBorderColor : root.effectiveBackgroundTint
                        outline: false      // no dark hairline / shade around the dock
                    }

                    // The dark hairline of the real macOS Dock: ~1.5 px wide, centred ON the edge of the glass (half outside, half inside),
                    // about 12% dark along the straight left and right sides, easing out around the corners until it is gone where the
                    // top and bottom edges start (those carry the bright line from the glass shader instead). Plain black with alpha, so it
                    // darkens whatever is behind it and follows the wallpaper. The canvas is 3 px larger than the Dock on every side so
                    // the outer half of the line can be drawn; it only repaints when the Dock's size, corner radius or mode changes.
                    // Drawn as two small end caps (left, right = mirrored) instead of one Canvas over the whole Dock. The hairline fades out
                    // within one corner radius of each end and the Dock's HEIGHT never changes, so a cap looks the same whatever the width. The old
                    // full-width Canvas repainted (a CPU raster + texture upload) on every pointer move while the Dock widened under magnification,
                    // and the wider the Dock (more pinned apps) the slower that got. The caps are painted once (again on size / radius change).
                    Repeater {
                        model: win.liquidActive ? 2 : 0
                        delegate: Canvas {
                            id: cap
                            required property int index
                            readonly property real fadeW: Math.min(root.cornerRadius, win.bgHeight / 2) * 1.05
                            anchors.top: parent.top;       anchors.topMargin: -3
                            anchors.bottom: parent.bottom; anchors.bottomMargin: -3
                            width: Math.ceil(3 + fadeW) + 3
                            antialiasing: true
                            // index 0 hugs the left edge; index 1 is the same picture mirrored on the right edge
                            x: index === 0 ? -3 : parent.width + 3 - width
                            transform: Scale { origin.x: cap.width / 2; xScale: cap.index === 0 ? 1 : -1 }
                            readonly property real strength: root.dockDark ? 0.14 : 0.12
                            onStrengthChanged: requestPaint()
                            onWidthChanged: requestPaint()
                            onHeightChanged: requestPaint()
                            Connections { target: root; function onCornerRadiusChanged() { cap.requestPaint(); } }
                            onPaint: {
                                var ctx = getContext("2d");
                                ctx.reset();
                                var m = 3, H = height;
                                var h = H - 2 * m;                         // the Dock's height
                                if (h < 4) return;
                                var r = Math.max(2, Math.min(root.cornerRadius, h / 2));
                                var fade = r * 1.05;
                                // paint as if the Dock were wide: only its near end shows inside this narrow canvas
                                var w = 2 * (fade + r) + 8;
                                var g = ctx.createLinearGradient(m, 0, m + w, 0);
                                var N = 24;
                                for (var k = 0; k <= N; k++) {
                                    var u = k / N, sm = u * u * u * (u * (u * 6 - 15) + 10), al = (strength * (1 - sm)).toFixed(4);
                                    g.addColorStop(u * fade / w, "rgba(0,0,0," + al + ")");
                                    g.addColorStop(1 - u * fade / w, "rgba(0,0,0," + al + ")");
                                }
                                ctx.strokeStyle = g;
                                ctx.lineWidth = 1.6;
                                ctx.beginPath();
                                ctx.moveTo(m + r, m);
                                ctx.lineTo(m + w - r, m);
                                ctx.arc(m + w - r, m + r, r, 1.5 * Math.PI, 2 * Math.PI, false);
                                ctx.lineTo(m + w, m + h - r);
                                ctx.arc(m + w - r, m + h - r, r, 0, 0.5 * Math.PI, false);
                                ctx.lineTo(m + r, m + h);
                                ctx.arc(m + r, m + h - r, r, 0.5 * Math.PI, Math.PI, false);
                                ctx.lineTo(m, m + r);
                                ctx.arc(m + r, m + r, r, Math.PI, 1.5 * Math.PI, false);
                                ctx.closePath();
                                ctx.stroke();
                            }
                        }
                    }

                    Loader {
                        anchors.fill: parent
                        active: true
                        sourceComponent: CornerBorder {
                            anchors.fill: parent
                            cornerR: root.cornerRadius
                            dark: root.dockDark
                            tint: root.bar ? root.bar.menuBorderColor : root.effectiveBackgroundTint
                            amount: 0.12
                            lineW: 0.35
                            fade: false
                        }
                    }

                    Row {
                        id: row
                        spacing: root.spacing
                        height: win.iconSize
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: root.bottomPad

                        Repeater {
                            id: rep
                            model: dockModel

                            delegate: Item {
                                id: cell
                                required property string key
                                required property int index
                                readonly property var modelData: root.itemMap[key] || ({ kind: "sep", key: key, nA: 0, nS: 0 })
                                readonly property bool isSep: modelData.kind === "sep"
                                readonly property bool canDrag: !isSep && ((modelData.pinned === true && !modelData.special) || modelData.special === "apps")
                                readonly property bool torn: ui.tearing && ui.tearItem && !isSep && ui.tearItem.key === modelData.key
                                opacity: (torn ? 0.3 : (isDragged ? 0.92 : 1)) * (leavingCell ? appear : 1)
                                Behavior on opacity { NumberAnimation { duration: 220 * root.animationSpeed; easing.type: Easing.OutCubic } }
                                readonly property bool isDragged: ui.dragging && modelData.key === ui.dragKey

                                // app cells always show their plain icon; only window cells show a live preview
                                // (with the app's icon as a badge), grouped next to the Trash
                                readonly property var thumbWin: (!isSep && modelData.kind === "win") ? modelData.tl : null
                                // the capture only restarts when the window itself changes — refreshed Dock data hands the cell
                                // the same window again, and re-binding it used to blank the live preview for ~2 s
                                property var heldTl: null
                                readonly property string winAddr: { if (!thumbWin) return ""; var h = ui.hyprOf(thumbWin); return h ? String(h.address).replace(/^0x/, "") : ""; }
                                readonly property bool closingWin: winAddr !== "" && root.hub && root.hub.closingWins[winAddr] === true
                                onThumbWinChanged: if (thumbWin !== heldTl) heldTl = thumbWin
                                readonly property bool useThumb: thumbWin !== null
                                readonly property bool thumbReady: useThumb && (sv.hasContent === undefined || sv.hasContent === true)

                                property real dx: {
                                    if (!ui.dragging) return 0;
                                    if (isSep && !ui.dragTail) return 0;
                                    if (isDragged) return ui.dragDelta;
                                    return ui.shiftFor(index);
                                }
                                Behavior on dx {
                                    enabled: !cell.isDragged
                                    NumberAnimation { duration: 160 * root.animationSpeed; easing.type: Easing.OutCubic }
                                }
                                transform: Translate { x: cell.dx }
                                z: isDragged ? 100 : 0

                                readonly property Item iconImg: img
                                readonly property bool leavingCell: modelData.leaving === true
                                property real appear: modelData.fresh ? 0 : 1
                                Behavior on appear { NumberAnimation { duration: cell.leavingCell ? root.leaveMs : 320; easing.type: cell.leavingCell ? Easing.InOutCubic : Easing.OutCubic } }
                                Component.onCompleted: { heldTl = thumbWin; Qt.callLater(function () { cell.appear = cell.leavingCell ? 0 : 1; cell.bounceStep(); }); }
                                onLeavingCellChanged: appear = leavingCell ? 0 : 1
                                enabled: !leavingCell

                                readonly property real c0: modelData.nA * (win.iconSize + root.spacing)
                                                           + modelData.nS * (root.sepWidth + root.spacing)
                                                           + (isSep ? root.sepWidth : win.iconSize) / 2
                                readonly property real s: {
                                    if (isSep) return 1;
                                    var dist = Math.abs(ui.mx - ui.refLeft - cell.c0);
                                    var R = win.magRadius;
                                    var f = dist < R ? 0.5 * (1 + Math.cos(Math.PI * dist / R)) : 0;
                                    return 1 + (win.effMag - 1) * f * ui.strength;
                                }

                                width: isSep ? root.sepWidth * appear : win.iconSize * s * appear
                                height: win.iconSize

                                Rectangle {
                                    visible: cell.isSep
                                    width: 1
                                    height: win.iconSize * 0.85
                                    anchors.centerIn: parent
                                    color: root.dockDark ? Qt.rgba(1, 1, 1, 0.28) : Qt.rgba(0, 0, 0, 0.22)
                                }

                                Image {
                                    id: img
                                    visible: false
                                    property real lift: 0
                                    // icon art drawn at ~99%: the dock and the cells keep their size. Whole pixels only: at rest this was
                                    // 51.48 px wide and centred on a fractional x, so the GPU re-sampled the icon texture (blurry) until the
                                    // magnification made it big enough that the blur was no longer noticeable
                                    width: Math.max(1, Math.round(win.iconSize * 0.99 * cell.s * cell.appear))
                                    height: width
                                    x: Math.round((parent.width - width) / 2)
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: Math.round(lift)
                                    source: cell.isSep ? "" : root.cellIconSrc(cell.modelData)
                                    sourceSize: Qt.size(Math.ceil(win.iconSize * win.magnification * 1.25),
                                                        Math.ceil(win.iconSize * win.magnification * 1.25))
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    mipmap: true
                                    asynchronous: true
                                }
                                MultiEffect {
                                    visible: !cell.isSep && !cell.thumbReady
                                    source: img
                                    anchors.fill: img
                                    shadowEnabled: true
                                    shadowColor: "black"
                                    shadowOpacity: 0.32
                                    shadowBlur: 0.55
                                    shadowVerticalOffset: 3
                                    // icon tint: desaturate, then colourise (no shader build needed)
                                    saturation: root.iconTint ? -0.75 * root.iconTintStrength : 0.0
                                    colorization: root.iconTint ? 1.0 * root.iconTintStrength : 0.0
                                    brightness: (ma.pressed ? -0.3 : 0.0) + (root.iconTint ? 0.14 * root.iconTintStrength : 0.0)
                                    contrast: root.iconTint ? 0.04 * root.iconTintStrength : 0.0
                                    colorizationColor: root.iconTintColor
                                }

                                // ── window thumbnail (same box as the icon, so magnification just works) ──
                                Item {
                                    id: th
                                    anchors.fill: img
                                    // kept (almost) opaque while loading so the capture isn't paused by the renderer
                                    visible: cell.useThumb
                                    opacity: cell.thumbReady ? 1 : 0.01

                                    Rectangle {      // soft drop shadow
                                        x: sv.x
                                        y: sv.y + 3
                                        width: sv.width
                                        height: sv.height
                                        radius: 5
                                        color: Qt.rgba(0, 0, 0, 0.32)
                                    }
                                    SafeCapture {
                                        id: sv
                                        anchors.centerIn: parent
                                        want: (root.hub && !root.hub.windowCapture) ? null : cell.heldTl
                                        graceMs: 400        // longer than the cell's leave animation: the preview stays until the cell is gone, and nothing is in flight by then
                                        // live only while the pointer is on the Dock (where you look at them); otherwise one fresh
                                        // frame every 2 s — live previews of every window were ~8% CPU at idle
                                        wantLive: !ui.tucked && !root.previewHold && !cell.closingWin && hh.hovered
                                        Timer {
                                            interval: 2000; repeat: true; triggeredOnStart: true
                                            running: !sv.wantLive && !ui.tucked && !root.previewHold && !cell.closingWin && sv.armed
                                            onTriggered: sv.snap()
                                        }
                                        readonly property real ar: (implicitWidth > 0 && implicitHeight > 0)
                                                                   ? implicitWidth / implicitHeight : 4 / 3
                                        width: Math.min(th.width, th.height * ar)
                                        height: width / ar
                                    }
                                    Rectangle {      // thin frame + pressed dimming
                                        anchors.fill: sv
                                        radius: 3
                                        color: ma.pressed ? Qt.rgba(0, 0, 0, 0.3) : "transparent"
                                        border.width: 1
                                        border.color: root.dockDark ? Qt.rgba(1, 1, 1, 0.28) : Qt.rgba(0, 0, 0, 0.28)
                                    }
                                }
                                // small app icon in the corner, so you can tell which app the window belongs to
                                Image {
                                    id: badge
                                    visible: cell.thumbReady
                                    width: img.width * 0.46
                                    height: width
                                    x: img.x + img.width - width + 3
                                    y: img.y + img.height - height + 3
                                    source: img.source
                                    sourceSize: Qt.size(Math.ceil(win.iconSize * win.magnification * 0.6),
                                                        Math.ceil(win.iconSize * win.magnification * 0.6))
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    mipmap: true
                                }

                                Rectangle {
                                    visible: !cell.isSep && cell.modelData.running && root.showIndicators
                                    width: 4; height: 4; radius: 2
                                    color: root.dockDark ? Qt.rgba(1, 1, 1, 0.85) : Qt.rgba(0, 0, 0, 0.6)
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    y: cell.height + 3
                                }

                                // ── launch bounce ──
                                // Bounces while the app launches. When the app opens, the bounce in progress finishes its landing, then a
                                // couple of smaller bounces settle it back onto the Dock. Nothing plays while the Dock is tucked away.
                                readonly property bool wantBounce: !cell.isSep && root.bounceOnLaunch && root.launching[cell.modelData.key] !== undefined
                                property bool bounceShown: false          // a bounce was actually visible, so it deserves a settle
                                function bounceStep() {
                                    if (ui.tucked) return;
                                    if (cell.wantBounce) { cell.bounceShown = true; if (!bounceAnim.running && !settleAnim.running) bounceAnim.start(); }
                                    else if (cell.bounceShown && !bounceAnim.running && !settleAnim.running) { cell.bounceShown = false; settleAnim.start(); }
                                }
                                onWantBounceChanged: bounceStep()
                                Connections {
                                    target: ui
                                    function onTuckedChanged() {
                                        if (ui.tucked) {                       // dock slid away: drop the bounce, it must not poke out
                                            bounceAnim.stop(); settleAnim.stop(); img.lift = 0; cell.bounceShown = false;
                                        } else cell.bounceStep();
                                    }
                                }
                                SequentialAnimation {
                                    id: bounceAnim
                                    NumberAnimation { target: img; property: "lift"; to: win.iconSize * 0.42
                                                      duration: 280 * root.animationSpeed; easing.type: Easing.OutCubic }
                                    NumberAnimation { target: img; property: "lift"; to: 0
                                                      duration: 280 * root.animationSpeed; easing.type: Easing.InCubic }
                                    onFinished: cell.bounceStep()              // goes again while still launching, otherwise settles
                                }
                                SequentialAnimation {
                                    id: settleAnim
                                    NumberAnimation { target: img; property: "lift"; to: win.iconSize * 0.16
                                                      duration: 170 * root.animationSpeed; easing.type: Easing.OutQuad }
                                    NumberAnimation { target: img; property: "lift"; to: 0
                                                      duration: 170 * root.animationSpeed; easing.type: Easing.InQuad }
                                    NumberAnimation { target: img; property: "lift"; to: win.iconSize * 0.06
                                                      duration: 120 * root.animationSpeed; easing.type: Easing.OutQuad }
                                    NumberAnimation { target: img; property: "lift"; to: 0
                                                      duration: 120 * root.animationSpeed; easing.type: Easing.InQuad }
                                    onFinished: cell.bounceStep()              // relaunched while settling: bounce again
                                }

                                // ── hover label ──
                                // appearance, sized from the Dock (see DockGlassPanel.qml). It is only built while it is shown.
                                // The label is a whole glass bubble (3 canvases, a masked blur capture, a shadow). It used to be built for EVERY icon the
                                // pointer crossed, so a fast sweep over many pinned apps built and tore down a bubble per icon (a hitch each): that was the
                                // "laggy when the mouse moves a bit fast, worse with many apps". It now appears once the pointer rests on an icon for a moment.
                                property bool hoverSettled: false
                                Timer { id: tipDwell; interval: 90; running: ma.containsMouse && !cell.isSep; onTriggered: cell.hoverSettled = true }
                                Connections { target: ma; function onContainsMouseChanged() { if (!ma.containsMouse) cell.hoverSettled = false; } }
                                readonly property bool tipOn: root.showLabels && !cell.isSep && cell.hoverSettled && ma.containsMouse && !ma.pressed && !ui.menuOpen && !ui.dragging
                                Loader {
                                    id: tip
                                    z: 10
                                    opacity: cell.tipOn ? 1 : 0
                                    Behavior on opacity { NumberAnimation { duration: 120 * root.animationSpeed } }
                                    active: cell.tipOn || opacity > 0
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    // (no explicit width / height: the Loader takes the bubble's size from it)
                                    // the tail's tip sits just above the icon (above the magnified / bouncing icon, too)
                                    y: cell.height - img.height - img.lift - height - Math.round(9 * win.labelK)
                                    sourceComponent: DockGlassPanel {
                                        id: lp
                                        readonly property string title: cell.isSep ? "" : ((cell.modelData.kind === "win" && cell.modelData.tl && cell.modelData.tl.title) ? cell.modelData.tl.title : cell.modelData.name)
                                        // a window cell names its window and, underneath, the app it belongs to
                                        readonly property string sub: (!cell.isSep && cell.modelData.kind === "win" && cell.modelData.name && cell.modelData.name !== title) ? cell.modelData.name : ""
                                        readonly property real fs: Math.max(9, Math.round(13 * k))
                                        backdrop: null
                                        live: false
                                        dark: root.darkMode
                                        k: win.labelK
                                        radius: Math.min(11.7 * k, bodyH / 2)
                                        tailW: 21 * k
                                        tailH: 5.8 * k
                                        tailTipR: 2.4 * k
                                        bodyH: sub !== "" ? 32 * k : 26 * k
                                        width: Math.ceil(Math.max(tt.width, st.visible ? st.width : 0)) + 2 * Math.round(12 * k)

                                        Text {
                                            id: tt
                                            text: lp.title
                                            width: Math.min(implicitWidth, Math.round(320 * lp.k))
                                            elide: Text.ElideRight
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            anchors.verticalCenter: parent.top
                                            anchors.verticalCenterOffset: lp.sub !== "" ? 9.2 * lp.k : lp.bodyH / 2 + 0.5 * lp.k
                                            color: lp.dark ? Qt.rgba(1, 1, 1, 0.92) : Qt.rgba(0, 0, 0, 0.86)
                                            font.pixelSize: lp.fs
                                            font.family: root.fontForWeight(Font.Normal, root.fontFamily)
                                        }
                                        Text {
                                            id: st
                                            visible: lp.sub !== ""
                                            text: lp.sub
                                            width: Math.min(implicitWidth, Math.round(320 * lp.k))
                                            elide: Text.ElideRight
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            anchors.verticalCenter: parent.top
                                            anchors.verticalCenterOffset: 22.4 * lp.k
                                            color: lp.dark ? Qt.rgba(1, 1, 1, 0.60) : Qt.rgba(0, 0, 0, 0.58)
                                            font.pixelSize: Math.max(8, Math.round(10.2 * lp.k))
                                            font.family: root.fontForWeight(Font.Normal, root.fontFamily)
                                        }
                                    }
                                }

                                MouseArea {
                                    id: ma
                                    visible: !cell.isSep
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: -root.bottomPad
                                    width: cell.width
                                    height: img.height + root.bottomPad
                                    hoverEnabled: true
                                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                                    property real pressX: 0

                                    property real pressY: 0
                                    onPressed: mouse => {
                                        if (mouse.button === Qt.LeftButton) {
                                            var pp = ma.mapToItem(ui, mouse.x, mouse.y);
                                            pressX = pp.x; pressY = pp.y;
                                        }
                                    }
                                    onPositionChanged: mouse => {
                                        if (!(pressedButtons & Qt.LeftButton) || cell.isSep) return;
                                        var ap = ma.mapToItem(ui, mouse.x, mouse.y);
                                        // pulled up out of the Dock → tear the icon off (any app icon, pinned or running)
                                        if (ui.tearing) { ui.tearX = ap.x; ui.tearY = ap.y; return; }
                                        if (pressY - ap.y > 56 && (cell.modelData.kind === "app" || cell.modelData.kind === "win") && !cell.modelData.special) {
                                            var home = img.mapToItem(ui, img.width / 2, img.height / 2);
                                            ui.tearX = ap.x; ui.tearY = ap.y;
                                            ui.beginTear(cell.modelData, root.cellIconSrc(cell.modelData), home.x, home.y);
                                            return;
                                        }
                                        if (!cell.canDrag) return;
                                        var ax = ap.x;
                                        if (!ui.dragging) {
                                            if (Math.abs(ax - pressX) < 8) return;
                                            ui.beginDrag(cell.index, cell.modelData.key, pressX, cell.width + root.spacing);
                                        }
                                        if (cell.isDragged) ui.dragUpdate(ax);
                                    }
                                    onReleased: mouse => {
                                        if (ui.tearing) { ui.endTear(); return; }
                                        if (ui.dragging && cell.isDragged) ui.endDrag();
                                    }
                                    onClicked: mouse => {
                                        if (ui.justDragged) return;
                                        if (mouse.button === Qt.RightButton) {
                                            ui.menuCx = cell.mapToItem(ui, cell.width / 2, 0).x;
                                            ui.menuModel = root.menuFor(cell.modelData);
                                            ui.menuCell = cell;
                                            ui.menuItem = cell.modelData;
                                            ui.syncMenu();
                                        } else {
                                            root.activate(cell.modelData, mouse.button === Qt.MiddleButton);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    z: 50
                    visible: ui.menuOpen
                    enabled: ui.menuOpen
                    acceptedButtons: Qt.AllButtons
                    onPressed: ui.menuItem = null
                }

                // ── right-click menu ──
                // Dock. Rows are 22 pt with capsule highlights, as in macOS 26.
                DockGlassPanel {
                    id: menu
                    z: 60
                    visible: opacity > 0
                    opacity: ui.menuOpen ? 1 : 0
                    scale: ui.menuOpen ? 1 : 0.96
                    transformOrigin: Item.Bottom
                    Behavior on opacity { NumberAnimation { duration: 110 * root.animationSpeed } }
                    Behavior on scale { NumberAnimation { duration: 110 * root.animationSpeed; easing.type: Easing.OutCubic } }

                    backdrop: null
                    live: false
                    frozen: ui.menuOpen      // the menu's glass stops updating while it is open
                    dark: root.darkMode
                    k: win.labelK
                    radius: 16 * k
                    tailW: 24 * k
                    tailH: 9 * k
                    tailTipR: 3.6 * k
                    readonly property real pad: Math.round(5 * k)

                    width: ui.menuW
                    bodyH: menuCol.height + 2 * pad
                    x: Math.max(8, Math.min(ui.width - width - 8, ui.menuCx - width / 2))
                    y: ui.menuIconTop >= 0 ? ui.menuIconTop - Math.round(10 * k) - height
                                           : ui.height - win.margin - win.bgHeight - win.iconSize * (win.effMag - 1) - Math.round(10 * k) - height
                    // The tail points at the icon the menu belongs to. Its position along the bubble is locked when the menu opens:
                    // re-evaluating tailX while the menu follows its icon during magnification changed shapeKey on every frame,
                    // repainting all of the bubble's canvases (blurred shadow included) on the CPU and causing severe magnification lag.
                    tailX: ui.menuTailX >= 0 ? ui.menuTailX : width / 2

                    Column {
                        id: menuCol
                        x: menu.pad
                        y: menu.pad
                        width: menu.width - 2 * menu.pad

                        Repeater {
                            model: ui.menuModel

                            delegate: Item {
                                id: mi
                                required property var modelData
                                readonly property bool isSep: modelData.kind === "sep"
                                readonly property bool off: !isSep && modelData.disabled === true
                                readonly property bool armedNow: !isSep && modelData.confirm === true && ui.armed === modelData.label
                                width: menuCol.width
                                height: isSep ? Math.round(11 * menu.k) : Math.round(22 * menu.k)

                                Rectangle {
                                    visible: mi.isSep
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width
                                    height: 1
                                    color: menu.dark ? Qt.rgba(1, 1, 1, 0.14) : Qt.rgba(0, 0, 0, 0.12)
                                }
                                Rectangle {
                                    visible: !mi.isSep && !mi.off && mia.containsMouse
                                    anchors.fill: parent
                                    radius: Math.round(8 * menu.k)          // softly rounded selection
                                    color: mi.armedNow ? "#FF453A" : root.accent
                                }
                                Text {
                                    visible: !mi.isSep
                                    x: Math.round(11 * menu.k)
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 2 * Math.round(11 * menu.k)
                                    elide: Text.ElideRight
                                    text: mi.isSep ? "" : (mi.armedNow ? I18n.tr("Click again to confirm") : I18n.tr(mi.modelData.label))
                                    color: (!mi.isSep && !mi.off && mia.containsMouse) ? "white"
                                         : (mi.off ? (menu.dark ? Qt.rgba(1, 1, 1, 0.30) : Qt.rgba(0, 0, 0, 0.28))
                                                   : (menu.dark ? Qt.rgba(1, 1, 1, 0.92) : Qt.rgba(0, 0, 0, 0.86)))
                                    font.pixelSize: Math.max(9, Math.round(13 * menu.k))
                                    font.family: root.fontForWeight(Font.Normal, root.fontFamily)
                                }
                                MouseArea {
                                    id: mia
                                    anchors.fill: parent
                                    enabled: !mi.isSep && !mi.off
                                    hoverEnabled: true
                                    onContainsMouseChanged: if (!containsMouse && ui.armed === mi.modelData.label) ui.armed = ""
                                    onClicked: {
                                        if (mi.modelData.confirm === true && ui.armed !== mi.modelData.label) { ui.armed = mi.modelData.label; return; }
                                        var run = mi.modelData.run;
                                        ui.menuItem = null;
                                        if (run) run();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

