local busy = false
local previous = ""
local retryAt = 0
local failures = 0
noctalia.setUpdateInterval(1500)
local function invoke(action, payload, callback)
    return noctalia.runAsync({"python3", noctalia.pluginDir() .. "/bridge.py", action, payload or "{}"}, callback)
end
function update()
    if busy or noctalia.nowMs() < retryAt then return end
    local request = {dark=noctalia.isDarkMode(), accent=noctalia.getColor("primary"), background=noctalia.getColor("surface"), outputs=noctalia.outputs()}
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
