---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Таблички]]"
tags: [скрипт, LocalScript]
---
# NameplateFX

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Таблички]]

Анимация табличек: в шахте плавно уменьшаются до `SHRINK 0.8` и тают, при выходе так же проявляются. Без ухода вверх.



## Связано
- [[Nameplates]]

## Код
```lua
-- Анимация табличек над головой: в шахте плавно уменьшаются к центру и тают,
-- при выходе так же плавно проявляются. Атрибут Hidden ставит сервер (Nameplates).
local TweenService = game:GetService("TweenService")

local SHRINK = 0.8     -- до какого размера уменьшается (от центра, на месте)
local FADE_TIME = 0.25 -- длительность исчезания и появления

local plates = setmetatable({}, { __mode = "k" }) -- [gui] = { size, labels, strokes, version }

local function scaled(size, k)
	return UDim2.new(size.X.Scale * k, size.X.Offset * k, size.Y.Scale * k, size.Y.Offset * k)
end

local function setFade(data, alpha)
	for _, l in ipairs(data.labels) do l.TextTransparency = alpha end
	for _, s in ipairs(data.strokes) do s.Transparency = alpha end
end

local function tweenFade(data, info, alpha)
	for _, l in ipairs(data.labels) do TweenService:Create(l, info, { TextTransparency = alpha }):Play() end
	for _, s in ipairs(data.strokes) do TweenService:Create(s, info, { Transparency = alpha }):Play() end
end

local function apply(gui, instant)
	local data = plates[gui]
	if not data then return end
	data.version += 1
	local version = data.version
	local hidden = gui:GetAttribute("Hidden") == true
	local small = scaled(data.size, SHRINK)

	if instant then
		gui.Enabled = not hidden
		gui.Size = hidden and small or data.size
		setFade(data, hidden and 1 or 0)
		return
	end

	if hidden then
		-- немного уменьшается к центру и тает, потом выключается
		local info = TweenInfo.new(FADE_TIME, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
		TweenService:Create(gui, info, { Size = small }):Play()
		tweenFade(data, info, 1)
		task.delay(FADE_TIME, function()
			if data.version == version then gui.Enabled = false end
		end)
	else
		-- из чуть уменьшенной и прозрачной — плавно до обычной
		gui.Enabled = true
		local info = TweenInfo.new(FADE_TIME, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
		TweenService:Create(gui, info, { Size = data.size }):Play()
		tweenFade(data, info, 0)
	end
end

local function track(gui)
	if plates[gui] or not gui:IsA("BillboardGui") or gui.Name ~= "Nameplate" then return end
	local data = { size = gui.Size, labels = {}, strokes = {}, version = 0 }
	for _, d in ipairs(gui:GetDescendants()) do
		if d:IsA("TextLabel") then table.insert(data.labels, d)
		elseif d:IsA("UIStroke") then table.insert(data.strokes, d) end
	end
	plates[gui] = data
	apply(gui, true) -- при появлении персонажа — сразу в нужном состоянии, без анимации
	gui:GetAttributeChangedSignal("Hidden"):Connect(function() apply(gui, false) end)
end

workspace.DescendantAdded:Connect(track)
for _, d in ipairs(workspace:GetDescendants()) do track(d) end
```
