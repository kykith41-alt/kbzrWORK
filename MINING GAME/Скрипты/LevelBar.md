---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Уровни и опыт]]"
tags: [скрипт, LocalScript]
---
# LevelBar

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Уровни и опыт]]

Полоска уровня внизу по центру: «Level: 10/35» слева, опыт посередине, зелёные пузырьки при получении опыта, «LEVEL UP!» над головой.

## Заметки
- Кап уровня — `Shared.MAX_LEVEL`.

## Связано
- [[MiningShared]]
- [[LevelUpFX]]
- [[MineServer]]

## Код
```lua
-- Полоска уровня внизу по центру: «Level: 10/35» слева, опыт посередине,
-- при получении опыта внутри заливки поднимаются зелёные пузырьки (вправо, куда растёт опыт),
-- при новом уровне над головой выпрыгивает «LEVEL UP!»
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local player = Players.LocalPlayer

local FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.ExtraBold)
local OUTLINE = Color3.fromRGB(18, 18, 18)
local RADIUS = UDim.new(0, 6)

local screen = Instance.new("ScreenGui")
screen.Name = "LevelBar"
screen.ResetOnSpawn = false
screen.IgnoreGuiInset = true
screen.Parent = player:WaitForChild("PlayerGui")

-- тёмная подложка с тонкой чёрной обводкой и скруглёнными углами
local bar = Instance.new("Frame")
bar.AnchorPoint = Vector2.new(0.5, 1)
bar.Position = UDim2.new(0.5, 0, 1, -6)
bar.Size = UDim2.new(0.42, 0, 0, 19)
bar.BackgroundColor3 = Color3.new(1, 1, 1)
bar.BorderSizePixel = 0
bar.Parent = screen
local sizeLimit = Instance.new("UISizeConstraint"); sizeLimit.MaxSize = Vector2.new(540, 19); sizeLimit.Parent = bar
Instance.new("UICorner", bar).CornerRadius = RADIUS
local barGrad = Instance.new("UIGradient")
barGrad.Rotation = 90
barGrad.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(50, 50, 50)),
	ColorSequenceKeypoint.new(0.85, Color3.fromRGB(42, 42, 42)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(48, 48, 48)),
})
barGrad.Parent = bar
local barStroke = Instance.new("UIStroke")
barStroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
barStroke.Thickness = 1.5
barStroke.Color = OUTLINE
barStroke.Parent = bar
local barScale = Instance.new("UIScale"); barScale.Parent = bar

-- ярко-зелёная заливка: верх ровный, к низу темнее, внизу лёгкий блик
local FILL_COLORS = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(44, 231, 51)),
	ColorSequenceKeypoint.new(0.3, Color3.fromRGB(44, 230, 51)),
	ColorSequenceKeypoint.new(0.85, Color3.fromRGB(37, 192, 42)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(42, 221, 49)),
})
local function greenGradient(parent)
	local g = Instance.new("UIGradient")
	g.Rotation = 90
	g.Color = FILL_COLORS
	g.Parent = parent
end

-- скругление слева совпадает с подложкой; пузырьки не вылезают за заливку
local fill = Instance.new("Frame")
fill.Size = UDim2.fromScale(0, 1)
fill.BackgroundColor3 = Color3.new(1, 1, 1)
fill.BorderSizePixel = 0
fill.ClipsDescendants = true
fill.Parent = bar
Instance.new("UICorner", fill).CornerRadius = RADIUS
greenGradient(fill)

-- прямой правый край заливки (пока полоска не дошла до скруглённого конца подложки)
local cap = Instance.new("Frame")
cap.AnchorPoint = Vector2.new(1, 0)
cap.Position = UDim2.fromScale(1, 0)
cap.Size = UDim2.new(0, RADIUS.Offset, 1, 0)
cap.BackgroundColor3 = Color3.new(1, 1, 1)
cap.BorderSizePixel = 0
cap.Parent = fill
greenGradient(cap)

local function updateCap()
	local w, full = fill.AbsoluteSize.X, bar.AbsoluteSize.X
	cap.Visible = w >= RADIUS.Offset * 2 and w <= full - RADIUS.Offset
end
fill:GetPropertyChangedSignal("AbsoluteSize"):Connect(updateCap)
bar:GetPropertyChangedSignal("AbsoluteSize"):Connect(updateCap)

local function makeText(xAlign)
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.Size = UDim2.new(1, -20, 1, 0)
	label.Position = UDim2.fromOffset(10, 0)
	label.FontFace = FONT
	label.TextSize = 15
	label.TextColor3 = Color3.new(1, 1, 1)
	label.TextXAlignment = xAlign
	label.ZIndex = 2
	label.Parent = bar
	local s = Instance.new("UIStroke"); s.Thickness = 1.2; s.Color = OUTLINE; s.Parent = label
	return label
end
local levelText = makeText(Enum.TextXAlignment.Left)
local xpText = makeText(Enum.TextXAlignment.Center)

------------------------------------------------------------------ пузырьки

local BUBBLE_COLOR = Color3.fromRGB(170, 255, 170)
local MAX_BUBBLES = 40
local FARM_TRAIL = 1.2      -- сколько секунд после получения опыта ещё идут пузырьки
local TRAIL_INTERVAL = 0.08 -- как часто появляются пузырьки, пока фармишь
local EDGE = 3              -- отступ от краёв заливки, пиксели: пузырьки всегда внутри
local bubbles = {}
local farmUntil = 0
local spawnTimer = 0

local function spawnBubble()
	local w, h = fill.AbsoluteSize.X, fill.AbsoluteSize.Y
	local left = RADIUS.Offset           -- не залезаем в скруглённый левый угол
	local right = w - EDGE
	if right - left < 10 or not fill.Visible or #bubbles >= MAX_BUBBLES then return end
	local size = math.random(2, 3)
	local x0 = left + math.random() * (right - left) * 0.85
	local y0 = h - EDGE - size / 2
	local frame = Instance.new("Frame")
	frame.AnchorPoint = Vector2.new(0.5, 0.5)
	frame.Size = UDim2.fromOffset(size, size)
	frame.Position = UDim2.fromOffset(x0, y0)
	frame.BackgroundColor3 = BUBBLE_COLOR
	frame.BackgroundTransparency = 1
	frame.BorderSizePixel = 0
	frame.ZIndex = 2
	frame.Parent = fill
	Instance.new("UICorner", frame).CornerRadius = UDim.new(1, 0)
	table.insert(bubbles, {
		frame = frame, size = size, x0 = x0, y0 = y0,
		dx = 14 + math.random() * 26,                          -- насколько уходит вправо
		dy = (h - EDGE * 2 - size) * (0.6 + math.random() * 0.4), -- насколько поднимается (не выше рамки)
		start = os.clock(), life = 0.6 + math.random() * 0.5,
		amp = 0.3 + math.random() * 0.5, freq = 9 + math.random() * 6, phase = math.random() * 6.28,
	})
end

local function burst(count)
	for _ = 1, count do spawnBubble() end
end

RunService.RenderStepped:Connect(function(dt)
	local now = os.clock()
	-- пока фармишь — пузырьки идут непрерывно
	if now < farmUntil then
		spawnTimer -= dt
		while spawnTimer <= 0 do
			spawnBubble()
			spawnTimer += TRAIL_INTERVAL
		end
	end
	local w, h = fill.AbsoluteSize.X, fill.AbsoluteSize.Y
	for i = #bubbles, 1, -1 do
		local b = bubbles[i]
		local t = (now - b.start) / b.life
		local x = b.x0 + b.dx * t
		local half = b.size / 2
		-- дошёл до правого края заливки или закончилась жизнь — исчезает
		if t >= 1 or x + half > w - EDGE then
			b.frame:Destroy()
			table.remove(bubbles, i)
		else
			-- поднимается вправо-вверх, слегка покачивается, но не выходит за верх и низ
			local y = b.y0 - b.dy * (t ^ 1.2) + math.sin(now * b.freq + b.phase) * b.amp
			y = math.clamp(y, EDGE + half, h - EDGE - half)
			b.frame.Position = UDim2.fromOffset(x, y)
			-- плавно появляется и плавно тает
			local fadeIn = math.clamp(t / 0.15, 0, 1)
			local fadeOut = math.clamp((t - 0.6) / 0.4, 0, 1)
			b.frame.BackgroundTransparency = 1 - 0.75 * fadeIn * (1 - fadeOut)
		end
	end
end)

------------------------------------------------------------------ «LEVEL UP!» над головой

local LEVEL_UP_HEIGHT = 2.6 -- выше строк «x1 Stone», чтобы не налезать на них

local function levelUpPopup(level)
	local head = player.Character and player.Character:FindFirstChild("Head")
	if not head then return end

	local gui = Instance.new("BillboardGui")
	gui.Adornee = head
	gui.Size = UDim2.fromOffset(260, 40)
	gui.StudsOffsetWorldSpace = Vector3.new(0, LEVEL_UP_HEIGHT - 0.4, 0)
	gui.AlwaysOnTop = true
	gui.LightInfluence = 0
	gui.ResetOnSpawn = false
	gui.Parent = player.PlayerGui

	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.AnchorPoint = Vector2.new(0.5, 0.5) -- сжимается к центру
	label.Position = UDim2.fromScale(0.5, 0.5)
	label.Size = UDim2.fromScale(1, 1)
	label.FontFace = FONT
	label.TextSize = 26
	label.RichText = true
	label.Text = string.format('<font color="#5CFF5C">LEVEL UP!</font> <font color="#FFFFFF">Lv %d</font>', level)
	label.Parent = gui
	local stroke = Instance.new("UIStroke"); stroke.Thickness = 2.2; stroke.Color = Color3.fromRGB(10, 10, 12); stroke.Parent = label
	local scale = Instance.new("UIScale"); scale.Scale = 0; scale.Parent = label
	Shared.WorldStatic(gui) -- размер как у предмета в мире, а не постоянный на экране

	-- выпрыгивает с пружинкой и подъезжает вверх
	TweenService:Create(scale, TweenInfo.new(0.4, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1.15 }):Play()
	TweenService:Create(gui, TweenInfo.new(0.5, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
		{ StudsOffsetWorldSpace = Vector3.new(0, LEVEL_UP_HEIGHT, 0) }):Play()
	task.delay(0.4, function()
		TweenService:Create(scale, TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	end)

	-- держится, потом уходит вверх, уменьшается и тает
	task.delay(1.8, function()
		local info = TweenInfo.new(0.4, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
		TweenService:Create(scale, info, { Scale = 0 }):Play()
		TweenService:Create(label, info, { TextTransparency = 1 }):Play()
		TweenService:Create(stroke, info, { Transparency = 1 }):Play()
		TweenService:Create(gui, info, { StudsOffsetWorldSpace = Vector3.new(0, LEVEL_UP_HEIGHT + 0.6, 0) }):Play()
	end)
	Debris:AddItem(gui, 2.3)
end

------------------------------------------------------------------ обновление

-- 82813.29 остаётся с копейками, 120000 — без
local function fmt(n)
	if n == math.floor(n) then return tostring(n) end
	return string.format("%.2f", n)
end

local shownLevel, shownXP = nil, nil
local function refresh()
	local level = player:GetAttribute("Level") or 1
	local xp = player:GetAttribute("XP") or 0
	local maxed = level >= Shared.MAX_LEVEL
	local need = Shared.XpToNext(level)
	local ratio = maxed and 1 or math.clamp(xp / need, 0, 1)

	levelText.Text = "Level: " .. level .. "/" .. Shared.MAX_LEVEL
	xpText.Text = maxed and "MAX" or (fmt(xp) .. "/" .. fmt(need))

	local gained = shownLevel ~= nil and (level > shownLevel or (level == shownLevel and xp > shownXP))

	local goal = UDim2.fromScale(ratio, 1)
	if shownLevel and level > shownLevel then
		-- новый уровень: полоска сбрасывается и заполняется заново, рамка «подпрыгивает»
		fill.Size = UDim2.fromScale(0, 1)
		levelUpPopup(level)
		barScale.Scale = 1.08
		TweenService:Create(barScale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	end
	if shownLevel then
		TweenService:Create(fill, TweenInfo.new(0.3, Enum.EasingStyle.Quart, Enum.EasingDirection.Out), { Size = goal }):Play()
	else
		fill.Size = goal
	end
	fill.Visible = ratio > 0

	if gained then
		-- всплеск пузырьков, чуть позже — когда заливка уже подросла
		task.delay(0.08, burst, 4)
		farmUntil = os.clock() + FARM_TRAIL
	end
	shownLevel, shownXP = level, xp
end

player:GetAttributeChangedSignal("XP"):Connect(refresh)
player:GetAttributeChangedSignal("Level"):Connect(refresh)
refresh()
updateCap()
```
