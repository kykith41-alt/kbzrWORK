---
тип: Script
где: ServerScriptService
система: "[[Погода]]"
tags: [скрипт, Script]
---
# WeatherServer

**Тип:** Script · **Где:** `ServerScriptService` · **Система:** [[Погода]]

Одна погода для всех, раз в 10 минут меняется на случайную. Названия — папки в `StarterPlayerScripts.Weather` плюс `Default`.



## Связано
- [[WeatherClient]]
- [[WeatherTestGui]]

## Код
```lua
-- Погода на сервере: одна для всех игроков, раз в 10 минут меняется на случайную другую.
-- Названия — папки в StarterPlayerScripts.Weather плюс «Default» (освещение Lighting по умолчанию).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local StarterPlayer = game:GetService("StarterPlayer")

local DURATION = 600 -- секунд на одну погоду (10 минут)
local START_WEATHER = "Default"

local folder = StarterPlayer:WaitForChild("StarterPlayerScripts"):WaitForChild("Weather")
local names = { "Default" }
for _, f in ipairs(folder:GetChildren()) do
	if f:IsA("Folder") and f.Name ~= "Default" then table.insert(names, f.Name) end
end
table.sort(names)

local remote = ReplicatedStorage:FindFirstChild("WeatherRemote") or Instance.new("RemoteEvent")
remote.Name = "WeatherRemote"
remote.Parent = ReplicatedStorage

ReplicatedStorage:SetAttribute("WeatherDuration", DURATION)

local function setWeather(name)
	ReplicatedStorage:SetAttribute("Weather", name)
	ReplicatedStorage:SetAttribute("WeatherChangedAt", workspace:GetServerTimeNow())
end

local function pickNext()
	local current = ReplicatedStorage:GetAttribute("Weather")
	local pool = {}
	for _, n in ipairs(names) do
		if n ~= current then table.insert(pool, n) end
	end
	if #pool == 0 then return current end
	return pool[math.random(1, #pool)]
end

setWeather(table.find(names, START_WEATHER) and START_WEATHER or names[1])

-- тестовая панель: менять погоду можно только в Studio или владельцу игры
remote.OnServerEvent:Connect(function(player, name)
	if not (RunService:IsStudio() or player.UserId == game.CreatorId) then return end
	if name == "__next" then
		setWeather(pickNext())
	elseif typeof(name) == "string" and table.find(names, name) then
		setWeather(name)
	end
end)

task.spawn(function()
	while true do
		task.wait(1)
		local changedAt = ReplicatedStorage:GetAttribute("WeatherChangedAt") or 0
		if workspace:GetServerTimeNow() - changedAt >= DURATION then
			setWeather(pickNext())
		end
	end
end)
```
