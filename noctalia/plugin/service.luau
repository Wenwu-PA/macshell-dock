local busy = false
local previous = ""
local retryAt = 0
local failures = 0
noctalia.setUpdateInterval(1500)
local function invoke(action, payload, callback)
    return noctalia.runAsync({"python3", noctalia.pluginDir() .. "/bridge.py", action, payload or "{}"}, callback)
end
local function iconColor()
    local spec = noctalia.getSetting("shell.app_icon_color")
    if type(spec) ~= "string" or spec == "" then
        spec = noctalia.isDarkMode() and "on_surface_variant" or "on_surface"
    end
    if string.sub(spec, 1, 1) == "#" then return spec end
    return noctalia.getColor(spec) or noctalia.getColor("on_surface")
end
local function iconColorization()
    -- 5.5 moved the shared toggle from shell.app_icon_colorize to dock.colorize_icons.
    -- Reading the containing tables avoids warnings for missing legacy keys.
    local shell = noctalia.getSetting("shell")
    local dock = noctalia.getSetting("dock")
    local enabled = type(shell) == "table" and shell.app_icon_colorize == true or false
    local overrides = {}
    if type(dock) == "table" then
        if type(dock.colorize_icons) == "boolean" then enabled = dock.colorize_icons end
        if type(dock.monitor) == "table" then
            for name, settings in pairs(dock.monitor) do
                if type(name) == "string" and type(settings) == "table" and type(settings.colorize_icons) == "boolean" then
                    overrides[name] = settings.colorize_icons
                end
            end
        end
    end
    return enabled, overrides
end
function update()
    if busy or noctalia.nowMs() < retryAt then return end
    local colorize, byMonitor = iconColorization()
    local request = {
        dark=noctalia.isDarkMode(), accent=noctalia.getColor("primary"),
        background=noctalia.getColor("surface"), outputs=noctalia.outputs(),
        iconColorize=colorize, iconColorizeByMonitor=byMonitor,
        iconColor=iconColor()
    }
    local payload = noctalia.json.encode(request)
    -- Helper reads existing JSON on each service tick; unchanged writes are suppressed.
    busy = true
    local accepted = invoke("sync", payload, function(result)
        busy = false
        if result.exitCode == 0 and not result.timedOut then
            previous = payload; failures = 0
        else
            failures = failures + 1
            retryAt = noctalia.nowMs() + math.min(300000, 5000 * 2 ^ math.min(failures, 6))
            noctalia.log("MacDock sync exit=" .. tostring(result.exitCode) .. " timedOut=" .. tostring(result.timedOut) .. " stdout=" .. tostring(result.stdout) .. " stderr=" .. tostring(result.stderr))
        end
    end)
    if not accepted then busy = false end
end
function onConfigChanged() previous = ""; retryAt = 0; update() end
function onOutputsChanged() previous = ""; update() end
function onEnable() previous = ""; update() end
function onIpc(event, _payload)
    if event == "start" or event == "stop" or event == "restart" or event == "status" then
        invoke(event, "{}", function(result) noctalia.log(result.stdout .. result.stderr) end)
    end
end
function onExit(_signal, reason)
    if reason == "disable" or reason == "uninstall" then
        -- Fixed Python code, no shell or interpolated user paths. Helper survives plugin removal.
        noctalia.runAsync({"python3", "-c", "import os,pathlib,runpy; p=pathlib.Path(os.environ.get('XDG_CONFIG_HOME',str(pathlib.Path.home()/'.config')))/'quickshell/MacDock/integration_cleanup.py'; runpy.run_path(str(p),run_name='__main__')"})
    end
end
update()
