-- Native content-sized panel. JSON is transport only, never presentation.
local process = "Stopped"
local detail = ""
local busy = false
local polling = false
local values = {}
local drafts = {}
local nativeDetail = "Native Blur · Not checked"





noctalia.setUpdateInterval(2000)
local loaded = false
local readError = ""
local config
local revision = 0
local readTicket = 0
local reading = false
local pendingWrites = {}
local function same(a,b)
    if type(a)~=type(b) then return false end
    if type(a)~="table" then return a==b end
    for k,v in pairs(a) do if not same(v,b[k]) then return false end end
    for k,_ in pairs(b) do if a[k]==nil then return false end end
    return true
end
local function current(key)
    if drafts[key] ~= nil then return drafts[key] end
    return values[key]
end
local function run(action, payload, callback)
    return noctalia.runAsync({"python3", noctalia.pluginDir() .. "/bridge.py", action, noctalia.json.encode(payload or {})}, callback)
end
config = function(force)
    if busy or next(drafts) ~= nil or (reading and not force) then return end
    readTicket=readTicket+1
    local ticket,epoch=readTicket,revision
    reading=true
    local accepted=run("settings",{},function(result)
        if ticket ~= readTicket then return end
        reading=false
        if epoch ~= revision or busy or next(drafts) ~= nil then return end
        local ok,data=pcall(noctalia.json.decode,result.stdout or "")
        if ok and result.exitCode==0 and not result.timedOut and type(data)=="table" then
            local changed=not loaded or readError ~= "" or not same(values,data)
            values=data;loaded=true;readError=""
            if changed then render() end
        else
            readError="Could not load settings: " .. tostring(result.stderr);detail=readError;noctalia.log(readError);render()
        end
    end)
    if not accepted then reading=false;readError="Could not start settings reader";detail=readError;noctalia.log(readError);render() end
end
local save
local saveState = ""
local saveDetail = ""
save = function(key, value)
    revision=revision+1
    drafts[key]=value
    if busy then pendingWrites[key]=value;render();return end
    busy=true;saveState="Saving";saveDetail=key;render()
    local function finished(result)
        busy=false
        local ok,response=pcall(noctalia.json.decode,result.stdout or "")
        local confirmed=not result.timedOut and result.exitCode==0 and ok and type(response)=="table"
            and response.saved==true and response.key==key
            and same(response.value,value)
        if confirmed then
            values[key]=response.value;saveState="Saved";saveDetail=key .. " · saved"
        else
            saveState="Error"
            saveDetail=key .. ": " .. (result.timedOut and "Save timed out; checking disk" or tostring(result.stderr ~= "" and result.stderr or result.stdout))
            noctalia.log(saveDetail)
        end
        if pendingWrites[key]==nil then drafts[key]=nil end
        local nextKey,nextValue=next(pendingWrites)
        if nextKey then pendingWrites[nextKey]=nil;save(nextKey,nextValue)
        else config(true);render() end
    end
    if not run("set",{[key]=value},finished) then
        finished({exitCode=-1,stdout="",stderr="Could not start settings writer",timedOut=false})
    end
end
local displayMetadata = {}
local function refreshDisplays()
    run("monitors",{},function(result)
        local ok,data=pcall(noctalia.json.decode,result.stdout or "")
        if ok and result.exitCode==0 then displayMetadata=data end
        render()
    end)
end
local function displays()
    local names, labels = {"@auto"}, {"Auto"}
    local selected = 0
    local selectedPreference = current("monitor") or "@auto"
    for _, output in ipairs(noctalia.outputs()) do
        table.insert(names, output.name)
        local info=output
        for _, candidate in ipairs(displayMetadata) do if candidate.name==output.name then info=candidate;break end end
        local label = output.name
        if info.description and info.description ~= "" then label=label .. " · " .. info.description end
        if info.width and info.height then label = label .. " · " .. tostring(info.width) .. "×" .. tostring(info.height) end
        if info.refreshRate then label=label .. " · " .. string.format("%.2f",info.refreshRate):gsub("0+$", ""):gsub("%.$", "") .. " Hz" end
        table.insert(labels,label)
        if output.name == selectedPreference then selected = #names - 1 end
    end
    table.insert(names, "");table.insert(labels,"All Monitors")
    if selectedPreference == "" then selected=#names-1 end
    if selectedPreference ~= "" and selectedPreference ~= "@auto" and selected == 0 then
        table.insert(names,selectedPreference); table.insert(labels,selectedPreference .. " · Disconnected · temporarily using an available display"); selected=#names-1
    end
    return names, labels, selected
end
local function toggle(label,key)
    return ui.row({key=key .. "-group",justify="space_between"},{ui.label({text=label}),ui.toggle({checked=current(key),enabled=not busy,onChange=function(v) save(key,v==true or v=="true") end})})
end
local function slider(label,key,minimum,maximum,step)
    local value=current(key)
    return ui.column({key=key .. "-group",gap=9},{
        ui.row({justify="space_between"},{ui.label({text=label}),ui.label({text=string.format(step>=1 and "%.0f" or "%.2f",value)})}),
        ui.slider({key=key,min=minimum,max=maximum,step=step,value=value,enabled=not busy,
            onChange=function(v) revision=revision+1;drafts[key]=tonumber(v) or value;render() end,
            onDragEnd=function() save(key,drafts[key] or value) end})
    })
end
function render()
    if not loaded then panel.render(ui.label({key="loading",text=detail ~= "" and detail or "Loading settings…"}));return end
    local names,labels,selected=displays()
    local status=readError ~= "" and readError or (saveState=="Error" and saveDetail or (detail ~= "" and detail or nativeDetail))
    panel.render(ui.column({key="settings-root",padding=18,gap=10},{
        ui.label({key="status",text="MacDock · " .. process,fontWeight="bold"}),
        ui.label({key="blur-status",text=status,height=36,maxLines=2}),
        ui.row({key="dock-actions",gap=6},{
            ui.button({key="restart",text="Restart",onClick="restartDock",enabled=not busy}),
            ui.button({key="noctalia-apply",text="Apply Noctalia",onClick="applyNoctaliaDock",enabled=not busy}),
            ui.button({key="noctalia-undo",text="Undo Noctalia",onClick="undoNoctaliaDock",
                enabled=not busy and values.undoNoctaliaAvailable==true})
        }),
        toggle("Enable Dock","enabled"),
        toggle("Autostart","automatic"),
        ui.column({key="monitor-group",gap=6},{ui.label({text="Monitor"}),
            ui.select({key="display-picker",options=labels,selectedIndex=selected,enabled=not busy,onChange=function(v)
                local i=tonumber(v);if i and names[i+1] then save("monitor",names[i+1]) end
            end})}),
        slider("Icon Size","iconSize",24,128,1),
        slider("Icon Spacing","spacing",0,40,1),
        slider("Background Opacity","glassOpacity",0,1,.01)
    }))
end

local function changeNoctaliaDock(action, source)
    if busy then return end
    -- A slider's final onChange may leave an unsaved draft even after its
    -- drag ended. Apply/Undo are explicit operations and must stay clickable.
    drafts={}
    revision=revision+1;readTicket=readTicket+1;reading=false
    busy=true;detail=action=="apply-noctalia-dock" and "Importing Noctalia Dock settings…" or "Undoing Noctalia Dock import…";render()
    local function finished(result)
        busy=false
        local ok,response=pcall(noctalia.json.decode,result.stdout or "")
        if not result.timedOut and result.exitCode==0 and ok and type(response)=="table" and response.saved==true and type(response.settings)=="table" then
            values=response.settings;drafts={};loaded=true
            detail=action=="apply-noctalia-dock" and "Noctalia Dock settings applied" or "Previous Dock settings restored"
        else
            detail="Noctalia Dock action failed: " .. tostring(result.stderr ~= "" and result.stderr or result.stdout)
            noctalia.log(detail)
        end
        render()
    end
    if not run(action,source,finished) then
        finished({exitCode=-1,stdout="",stderr="Could not start Dock action",timedOut=false})
    end
end
function applyNoctaliaDock()
    local keys = {"icon_size","item_spacing","background_opacity","radius",
        "magnification","magnification_scale","show_running","auto_hide","smart_auto_hide"}
    local source = {}
    for _, key in ipairs(keys) do source[key] = noctalia.getSetting("dock." .. key) end
    changeNoctaliaDock("apply-noctalia-dock",source)
end
function undoNoctaliaDock() changeNoctaliaDock("undo-noctalia-dock",{}) end

local function control(action)
    if busy then return end
    busy = true
    if not run(action, {}, function(result)
        busy = false
        if result.exitCode ~= 0 then
            process = "Error"; detail = result.timedOut and "Restart timed out" or tostring(result.stderr ~= "" and result.stderr or result.stdout)
            noctalia.log(result.stderr)
        else detail = ""; update() end
        render()
    end) then busy = false; process = "Error"; detail = "Process service unavailable" end
    render()
end
function startDock() control("start") end
function stopDock() control("stop") end
function restartDock() control("restart") end

function update()
    config()

    if busy or polling then return end
    polling = true
    if not run("status", {}, function(result)
        polling = false
        if result.exitCode == 0 then
            local ok, health = pcall(noctalia.json.decode, result.stdout)
            if ok and type(health) == "table" and health.app == "MacDock" then
                process = "Running"
            else process = "Error"; detail = "Invalid Dock status response" end
        else process = "Stopped" end
        render()
    end) then polling = false; process = "Error" end
end
function onOpen(_context)
    drafts={};revision=revision+1;config(true);render();update();refreshDisplays()
    run("blur-status",{},function(result)
        local ok,data=pcall(noctalia.json.decode,result.stdout or "")
        if ok and result.exitCode==0 then nativeDetail=data.state=="Supported" and "Native Blur · Available" or "Native Blur · Unavailable";noctalia.log(tostring(data.reason))
        else nativeDetail="Native Blur · Unavailable: " .. tostring(result.stderr) end
        render()
    end)
end
function onConfigChanged() end
function onOutputsChanged() displayMetadata={};render();refreshDisplays() end
config()
