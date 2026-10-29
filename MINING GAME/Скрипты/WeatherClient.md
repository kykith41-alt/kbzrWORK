---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Погода]]"
tags: [скрипт, LocalScript]
---
# WeatherClient

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Погода]]

Плавно переводит Lighting в то, что лежит в папке `Weather/<погода>` (Effects + Properties). Дождь и шторм у камеры и у игрока, брызги, звук дождя. Без грозы.

## Заметки
- Тип осадков по названию: «rain» — дождь, «storm» — шторм.
- ID звуков дождя: `RAIN_SOUND_ID`, `STORM_SOUND_ID` (сейчас 0 — вставь свои).
- Громкость: `RAIN_VOLUME`, `STORM_VOLUME`.

## Связано
- [[WeatherServer]]
- [[WeatherTestGui]]
- [[MiningShared]]

## Код
```lua
-- Погода на клиенте.
-- Освещение: плавно переводит Lighting в то, что лежит в папке Weather/<погода> (Effects + Properties),
-- без своих цветовых слоёв поверх. «Default» — освещение, которое было в Lighting при запуске игры.
-- Дождь (Rain/Rainy, Rainstorm): частицы-струи над камерой и над игроком, брызги и круги на земле, звук дождя. Без грозы.
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))

local weatherRoot = script.Parent:WaitForChild("Weather")
local player = Players.LocalPlayer

local TRANSITION = 10 -- секунд на плавную смену освещения

local RAIN_SOUND_ID = "rbxassetid://0"
local STORM_SOUND_ID = "rbxassetid://0"
local RAIN_VOLUME = 0.2
local STORM_VOLUME = 0.28

-- текстуры частиц: искра (сжатая — струя дождя) и кольцо (круг на воде)
local TEX_SPARK = Shared.Images.FxSpark
local TEX_RING = Shared.Images.FxRing

-- насколько сильный дождь и ветер; погода выбирается по слову в названии папки:
-- «storm» (Rainstorm) — ливень, «rain» (Rain, Rainy) — дождь, остальные — без дождя
local LOOKS = {
	none = { rain = 0, wind = 0, storm = 0 },
	rain = { rain = 0.6, wind = 0.2, storm = 0 },
	storm = { rain = 1, wind = 1, storm = 1 },
}
local function lookFor(name)
	local n = string.lower(name or "")
	if n:find("storm") then return LOOKS.storm end
	if n:find("rain") then return LOOKS.rain end
	return LOOKS.none
end

-- если камера отъехала от игрока дальше этого, над игроком идёт свой дождь (иначе хватает дождя над камерой)
local PLAYER_RAIN_FROM = 25

------------------------------------------------------------------ Default: снимок Lighting при запуске

local LIGHTING_PROPS = {
	"Ambient", "Brightness", "ClockTime", "ColorShift_Bottom", "ColorShift_Top",
	"EnvironmentDiffuseScale", "EnvironmentSpecularScale", "ExposureCompensation",
	"FogColor", "FogEnd", "FogStart", "GeographicLatitude", "GlobalShadows", "OutdoorAmbient", "ShadowSoftness",
}

local defaultFolder = Instance.new("Folder")
defaultFolder.Name = "Default"
do
	local effects = Instance.new("Folder")
	effects.Name = "Effects"
	effects.Parent = defaultFolder
	local props = Instance.new("Folder")
	props.Name = "Properties"
	props.Parent = defaultFolder
	for _, name in ipairs(LIGHTING_PROPS) do
		local value = Lighting[name]
		local holder
		if typeof(value) == "Color3" then
			holder = Instance.new("Color3Value")
		elseif typeof(value) == "boolean" then
			holder = Instance.new("BoolValue")
		else
			holder = Instance.new("NumberValue")
		end
		holder.Name = name
		holder.Value = value
		holder.Parent = props
	end
	for _, c in ipairs(Lighting:GetChildren()) do
		if c:IsA("Sky") or c:IsA("Atmosphere") or c:IsA("PostEffect") then
			c:Clone().Parent = effects
			c:Destroy() -- дальше этим управляет погода
		end
	end
end

local function weatherFolder(name)
	if name == "Default" then return defaultFolder end
	return weatherRoot:FindFirstChild(name)
end

------------------------------------------------------------------ освещение и эффекты из папки

local EFFECT_CLASSES = { "Atmosphere", "BloomEffect", "ColorCorrectionEffect", "DepthOfFieldEffect", "SunRaysEffect" }
local EFFECT_PROPS = {
	Atmosphere = { "Density", "Offset", "Color", "Decay", "Glare", "Haze" },
	BloomEffect = { "Intensity", "Size", "Threshold" },
	ColorCorrectionEffect = { "Brightness", "Contrast", "Saturation", "TintColor" },
	DepthOfFieldEffect = { "FarIntensity", "FocusDistance", "InFocusRadius", "NearIntensity" },
	SunRaysEffect = { "Intensity", "Spread" },
}
-- «выключенное» состояние: из него эффект плавно появляется и в него плавно уходит
local NEUTRAL = {
	Atmosphere = { Density = 0, Offset = 0, Glare = 0, Haze = 0 },
	BloomEffect = { Intensity = 0 },
	ColorCorrectionEffect = { Brightness = 0, Contrast = 0, Saturation = 0, TintColor = Color3.new(1, 1, 1) },
	DepthOfFieldEffect = { FarIntensity = 0, NearIntensity = 0 },
	SunRaysEffect = { Intensity = 0 },
}
local SKY_TEXTURES = { "SkyboxBk", "SkyboxDn", "SkyboxFt", "SkyboxLf", "SkyboxRt", "SkyboxUp", "SunTextureId", "MoonTextureId" }
local SKY_PROPS = { "CelestialBodiesShown", "MoonAngularSize", "StarCount", "SunAngularSize" }

local live = {}
local liveSky
local jobs, finals = {}, {}
local transStart, transDur = 0, 0
local skySwap

local function convert(value, current)
	if typeof(current) == "Color3" then
		if typeof(value) == "Color3" then return value end
		if typeof(value) == "BrickColor" then return value.Color end
		if typeof(value) == "Vector3" then
			if value.X > 1 or value.Y > 1 or value.Z > 1 then return Color3.fromRGB(value.X, value.Y, value.Z) end
			return Color3.new(value.X, value.Y, value.Z)
		end
		return nil
	end
	if typeof(current) == typeof(value) then return value end
	return nil
end

local function addJob(obj, prop, to, source)
	local ok, from = pcall(function() return obj[prop] end)
	if not ok then
		warn(string.format("Погода: у %s нет свойства «%s»", obj.ClassName, prop))
		return
	end
	local value = convert(to, from)
	if value == nil then
		warn(string.format("Погода: «%s» — %s не подходит (нужен %s)", prop, source and source.ClassName or typeof(to), typeof(from)))
		return
	end
	if typeof(value) == "number" then
		table.insert(jobs, { obj, prop, from, value, prop == "ClockTime" and "clock" or "number" })
	elseif typeof(value) == "Color3" then
		table.insert(jobs, { obj, prop, from, value, "color" })
	else
		obj[prop] = value
	end
end

local function lerp(a, b, k, kind)
	if kind == "color" then return a:Lerp(b, k) end
	if kind == "clock" then
		local d = (b - a + 12) % 24 - 12 -- через полночь — коротким путём
		return (a + d * k) % 24
	end
	return a + (b - a) * k
end

local function sameSkybox(a, b)
	for _, p in ipairs(SKY_TEXTURES) do
		if a[p] ~= b[p] then return false end
	end
	return true
end

local function applyWeather(name)
	local folder = weatherFolder(name)
	if not folder then
		warn("Погода: нет папки Weather/" .. tostring(name))
		return
	end
	table.clear(jobs)
	for _, f in ipairs(finals) do f() end
	table.clear(finals)
	if skySwap then skySwap() end
	skySwap = nil
	local effects = folder:FindFirstChild("Effects")
	local props = folder:FindFirstChild("Properties")

	if props then
		for _, v in ipairs(props:GetChildren()) do
			if v:IsA("ValueBase") then addJob(Lighting, v.Name, v.Value, v) end
		end
	end

	for _, class in ipairs(EFFECT_CLASSES) do
		local target = effects and effects:FindFirstChildWhichIsA(class)
		local cur = live[class]
		if target then
			if not cur then
				cur = target:Clone()
				for prop, value in pairs(NEUTRAL[class]) do cur[prop] = value end
				cur.Parent = Lighting
				live[class] = cur
			end
			cur.Name = target.Name
			if cur:IsA("PostEffect") then cur.Enabled = target.Enabled end
			for _, prop in ipairs(EFFECT_PROPS[class]) do addJob(cur, prop, target[prop]) end
		elseif cur then
			for prop, value in pairs(NEUTRAL[class]) do addJob(cur, prop, value) end
			table.insert(finals, function()
				if live[class] == cur then cur:Destroy(); live[class] = nil end
			end)
		end
	end

	-- небо: та же картинка — только плавно меняем размеры солнца/луны; другая картинка — подмена
	-- посередине перехода (два разных скайбокса в Roblox смешать нельзя)
	local skyTarget = effects and effects:FindFirstChildWhichIsA("Sky")
	if skyTarget and liveSky and sameSkybox(liveSky, skyTarget) then
		for _, p in ipairs(SKY_PROPS) do addJob(liveSky, p, skyTarget[p]) end
	elseif skyTarget then
		local newSky = skyTarget:Clone()
		skySwap = function()
			if liveSky then liveSky:Destroy() end
			newSky.Parent = Lighting
			liveSky = newSky
		end
	elseif liveSky then
		local old = liveSky
		skySwap = function()
			old:Destroy()
			if liveSky == old then liveSky = nil end
		end
	end

	transStart = os.clock()
	transDur = TRANSITION
	print("Погода: " .. name)
end

------------------------------------------------------------------ дождь: частицы над камерой и игроком

local function ns(...)
	local args = { ... }
	if #args == 1 then return NumberSequence.new(args[1]) end
	local keys = {}
	for i = 1, #args, 2 do
		table.insert(keys, NumberSequenceKeypoint.new(args[i], args[i + 1]))
	end
	return NumberSequence.new(keys)
end

local function emitter(parent, props)
	local e = Instance.new("ParticleEmitter")
	e.Rate = 0
	for k, v in pairs(props) do e[k] = v end
	e.Parent = parent
	return e
end

local rainFolder = Instance.new("Folder")
rainFolder.Name = "WeatherRain"
rainFolder.Parent = workspace

-- невидимая плита, из неё сыплются струи (частицы, не детали — дёшево).
-- LockedToPart: уже падающие струи двигаются вместе с плитой — дождь сразу оказывается там, где камера
local function makeCloud(name)
	local part = Instance.new("Part")
	part.Name = name
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.Transparency = 1
	part.Size = Vector3.new(80, 1, 80)
	part.Parent = rainFolder
	-- искра, сжатая в тонкую полоску, выглядит как струя; FacingCameraWorldUp держит её вертикальной
	local e = emitter(part, {
		Texture = TEX_SPARK,
		Color = ColorSequence.new(Color3.fromRGB(205, 218, 238)),
		LightEmission = 0.5,
		LightInfluence = 0.1,
		Size = ns(0.42),
		Squash = ns(3),
		Transparency = ns(0.35),
		Lifetime = NumberRange.new(0.75, 0.85),
		Speed = NumberRange.new(85, 100),
		EmissionDirection = Enum.NormalId.Bottom,
		Orientation = Enum.ParticleOrientation.FacingCameraWorldUp,
		Shape = Enum.ParticleEmitterShape.Box,
		LockedToPart = true,
		Enabled = true,
	})
	return { part = part, emitter = e, rate = 0 }
end

local camCloud = makeCloud("RainCloudCamera")
local playerCloud = makeCloud("RainCloudPlayer")

-- Rate меняем только ступеньками по 100: каждая запись сбрасывает таймер эмиттера
local function setRate(c, value)
	local rate = value > 20 and math.floor(value / 100 + 0.5) * 100 or 0
	if rate ~= c.rate then
		c.rate = rate
		c.emitter.Rate = rate
	end
end

-- брызги: капельки подпрыгивают и расходится круг там, куда упала капля рядом с игроком
local splashes = {}
for _ = 1, 8 do
	local a = Instance.new("Attachment")
	a.Parent = workspace.Terrain
	local hop = emitter(a, {
		Texture = TEX_SPARK,
		Color = ColorSequence.new(Color3.fromRGB(220, 230, 245)),
		LightEmission = 0.4,
		LightInfluence = 0.2,
		Size = ns(0, 0.22, 1, 0.08),
		Transparency = ns(0, 0.3, 1, 1),
		Lifetime = NumberRange.new(0.18, 0.32),
		Speed = NumberRange.new(4, 7),
		SpreadAngle = Vector2.new(45, 45),
		Acceleration = Vector3.new(0, -40, 0),
		EmissionDirection = Enum.NormalId.Top,
		Enabled = false,
	})
	local ripple = emitter(a, {
		Texture = TEX_RING,
		Color = ColorSequence.new(Color3.fromRGB(210, 222, 240)),
		LightEmission = 0.1,
		LightInfluence = 0.8,
		Orientation = Enum.ParticleOrientation.VelocityPerpendicular,
		EmissionDirection = Enum.NormalId.Top,
		Speed = NumberRange.new(0.01),
		Size = ns(0, 0.2, 1, 1.1),
		Transparency = ns(0, 0.45, 1, 1),
		Lifetime = NumberRange.new(0.35, 0.5),
		Enabled = false,
	})
	table.insert(splashes, { att = a, hop = hop, ripple = ripple })
end
local splashIndex = 0

local groundParams = RaycastParams.new()
groundParams.FilterType = Enum.RaycastFilterType.Exclude

local function refreshFilter()
	local list = { rainFolder }
	if player.Character then table.insert(list, player.Character) end
	for _, name in ipairs({ "LocalMiningFX", "MineRangeRing" }) do
		local f = workspace:FindFirstChild(name)
		if f then table.insert(list, f) end
	end
	groundParams.FilterDescendantsInstances = list
end

local function splashAround(center, count)
	for _ = 1, count do
		local a = math.random() * math.pi * 2
		local r = math.sqrt(math.random()) * 28
		local p = center + Vector3.new(math.cos(a) * r, 40, math.sin(a) * r)
		local hit = workspace:Raycast(p, Vector3.new(0, -90, 0), groundParams)
		if hit then
			splashIndex = splashIndex % #splashes + 1
			local s = splashes[splashIndex]
			s.att.WorldPosition = hit.Position + Vector3.new(0, 0.08, 0)
			s.hop:Emit(2)
			if math.random() < 0.6 then s.ripple:Emit(1) end
		end
	end
end

------------------------------------------------------------------ звук дождя

local function loopSound(id)
	if not id or id == "" or id == "rbxassetid://0" then return nil end
	local s = Instance.new("Sound")
	s.SoundId = id
	s.Looped = true
	s.Volume = 0
	s.Parent = SoundService
	s:Play()
	return s
end
local rainSound = loopSound(RAIN_SOUND_ID)
local stormSound = loopSound(STORM_SOUND_ID)

------------------------------------------------------------------ каждый кадр

local cur = { rain = 0, wind = 0, storm = 0 }
local filterAt = 0

RunService.RenderStepped:Connect(function(dt)
	local now = os.clock()

	-- плавный переход освещения из папки
	if transDur > 0 then
		local k = math.clamp((now - transStart) / transDur, 0, 1)
		local e = k * k * (3 - 2 * k)
		for _, j in ipairs(jobs) do
			j[1][j[2]] = lerp(j[3], j[4], e, j[5])
		end
		if skySwap and k >= 0.5 then
			skySwap()
			skySwap = nil
		end
		if k >= 1 then
			table.clear(jobs)
			for _, f in ipairs(finals) do f() end
			table.clear(finals)
			transDur = 0
		end
	end

	-- дождь и ветер плавно догоняют текущую погоду
	local look = lookFor(ReplicatedStorage:GetAttribute("Weather"))
	local k = 1 - math.exp(-dt * 0.7)
	cur.rain += (look.rain - cur.rain) * k
	cur.wind += (look.wind - cur.wind) * k
	cur.storm += (look.storm - cur.storm) * k

	local camPos = workspace.CurrentCamera.CFrame.Position
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	local rain = cur.rain
	local tilt = CFrame.Angles(0.18 * cur.wind, 0, 0.12 * cur.wind)

	-- дождь над камерой: всегда
	camCloud.part.CFrame = CFrame.new(camPos + Vector3.new(0, 55, 0)) * tilt
	setRate(camCloud, rain > 0.02 and 2600 * rain or 0)

	-- дождь над игроком: когда камера отъехала далеко (иначе над ним уже идёт дождь камеры)
	local playerShare = 0
	if root then
		local flat = Vector3.new(camPos.X - root.Position.X, 0, camPos.Z - root.Position.Z).Magnitude
		playerShare = math.clamp((flat - PLAYER_RAIN_FROM) / 25, 0, 1)
		playerCloud.part.CFrame = CFrame.new(root.Position + Vector3.new(0, 55, 0)) * tilt
	end
	setRate(playerCloud, rain > 0.02 and 2600 * rain * playerShare or 0)

	if rain > 0.05 then
		if now >= filterAt then
			refreshFilter()
			filterAt = now + 2
		end
		splashAround(root and root.Position or camPos, math.max(1, math.floor(rain * 7)))
	end

	-- обычный дождь и ливень — свои петли, громкость по силе дождя
	local wet = math.min(1, rain * 1.4)
	if rainSound then rainSound.Volume = RAIN_VOLUME * wet * (1 - cur.storm) end
	if stormSound then stormSound.Volume = STORM_VOLUME * wet * cur.storm end
end)

------------------------------------------------------------------ смена погоды

local function onWeather()
	local name = ReplicatedStorage:GetAttribute("Weather")
	if name then applyWeather(name) end
end

ReplicatedStorage:GetAttributeChangedSignal("Weather"):Connect(onWeather)
if ReplicatedStorage:GetAttribute("Weather") then onWeather() end
```
