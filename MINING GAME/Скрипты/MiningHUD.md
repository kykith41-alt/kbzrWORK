---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Интерфейс]]"
tags: [скрипт, LocalScript]
---
# MiningHUD

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Интерфейс]]

HUD шахты: всплывашки «x1 Stone», «Рюкзак полон!» над головой, кнопка «Наверх», уведомления.

## Заметки
- При `amount = 0` (рюкзак полон) «x1 Stone» не показывается.
- Шрифт задаётся через `FontFace`, не `Font`.

## Связано
- [[MiningShared]]
- [[MineServer]]
- [[LevelBar]]
- [[CapacityOrb]]

## Код
```lua
-- HUD шахты: уведомления и кнопка «Наверх»
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local Remotes = ReplicatedStorage:WaitForChild("Remotes")
local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local player = Players.LocalPlayer

local FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.ExtraBold)

local screen = Instance.new("ScreenGui")
screen.Name = "MiningHUD"
screen.ResetOnSpawn = false
screen.Parent = player:WaitForChild("PlayerGui")

local function notify(text, color)
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.AnchorPoint = Vector2.new(0.5, 0.5)
	label.Position = UDim2.fromScale(0.5, 0.28)
	label.Size = UDim2.fromOffset(700, 44)
	label.FontFace = FONT
	label.TextSize = 34
	label.Text = text
	label.TextColor3 = color or Color3.new(1, 1, 1)
	local s = Instance.new("UIStroke"); s.Thickness = 3; s.Parent = label
	local scale = Instance.new("UIScale"); scale.Scale = 0.4; scale.Parent = label
	label.Parent = screen
	TweenService:Create(scale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	TweenService:Create(label, TweenInfo.new(1.8, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Position = UDim2.fromScale(0.5, 0.23) }):Play()
	TweenService:Create(label, TweenInfo.new(0.5, Enum.EasingStyle.Linear, Enum.EasingDirection.In, 0, false, 1.4), { TextTransparency = 1 }):Play()
	TweenService:Create(s, TweenInfo.new(0.5, Enum.EasingStyle.Linear, Enum.EasingDirection.In, 0, false, 1.4), { Transparency = 1 }):Play()
	Debris:AddItem(label, 2)
end

local lastNotify = {}
Remotes.Notify.OnClientEvent:Connect(function(text, color)
	if lastNotify[text] and os.clock() - lastNotify[text] < 1.5 then return end
	lastNotify[text] = os.clock()
	notify(text, color)
end)

-- кнопка «Наверх» появляется, когда игрок глубоко в шахте
local up = Instance.new("TextButton")
up.AnchorPoint = Vector2.new(1, 1)
up.Position = UDim2.new(1, -24, 1, -110)
up.Size = UDim2.fromOffset(150, 52)
up.BackgroundColor3 = Color3.fromRGB(70, 180, 80)
up.Font = Enum.Font.FredokaOne
up.TextSize = 26
up.Text = "⬆ Наверх"
up.TextColor3 = Color3.new(1, 1, 1)
up.Visible = false
up.Parent = screen
Instance.new("UICorner", up).CornerRadius = UDim.new(0.3, 0)
local upStroke = Instance.new("UIStroke"); upStroke.Thickness = 3; upStroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border; upStroke.Parent = up
local upText = Instance.new("UIStroke"); upText.Thickness = 2; upText.Parent = up
up.Activated:Connect(function()
	Remotes.GoUp:FireServer()
end)

task.spawn(function()
	while true do
		local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
		up.Visible = root ~= nil and root.Position.Y < -10
		task.wait(0.3)
	end
end)

------------------------------------------------------------------ «x1 Камень» над головой

local LIFETIME = 1.6
local ROW = 0.5 -- шаг между строками, студы
local BASE_HEIGHT = 1.35 -- над центром головы: сразу над макушкой
local popups = {} -- новые снизу

local function toHex(c)
	return string.format("#%02X%02X%02X", math.floor(c.R * 255), math.floor(c.G * 255), math.floor(c.B * 255))
end

local function layout()
	for i, p in ipairs(popups) do
		local goal = Vector3.new(0, BASE_HEIGHT + (#popups - i) * ROW, 0)
		TweenService:Create(p.gui, TweenInfo.new(0.25, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { StudsOffsetWorldSpace = goal }):Play()
	end
end

local function removePopup(p)
	for i, q in ipairs(popups) do
		if q == p then table.remove(popups, i) break end
	end
	p.dead = true
	local info = TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	TweenService:Create(p.scale, info, { Scale = 0 }):Play()
	TweenService:Create(p.label, info, { TextTransparency = 1 }):Play()
	TweenService:Create(p.stroke, info, { Transparency = 1 }):Play()
	TweenService:Create(p.icon, info, { ImageTransparency = 1 }):Play()
	TweenService:Create(p.gui, info, { StudsOffsetWorldSpace = p.gui.StudsOffsetWorldSpace + Vector3.new(0, 0.5, 0) }):Play()
	Debris:AddItem(p.gui, 0.4)
	layout()
end

-- тёмные руды (камень, уголь) осветляем, чтобы название читалось
local function readable(c)
	local h, s, v = c:ToHSV()
	return Color3.fromHSV(h, math.min(s, 0.6), math.max(v, 0.85))
end

local function setText(p)
	local def = p.def
	p.label.Text = string.format('<font color="#FFFFFF">x%d</font> <font color="%s">%s</font>',
		p.count, toHex(readable(def.ore)), def.display)
end

local function bump(p)
	p.scale.Scale = 1.3
	TweenService:Create(p.scale, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
end

local function showMined(typeName, amount)
	local head = player.Character and player.Character:FindFirstChild("Head")
	local def = Shared.BlockByName[typeName]
	if not head or not def then return end

	-- тот же тип ещё на экране — увеличиваем счётчик
	for _, p in ipairs(popups) do
		if p.def == def and not p.dead then
			p.count += amount
			p.expire = os.clock() + LIFETIME
			setText(p)
			bump(p)
			return
		end
	end

	local gui = Instance.new("BillboardGui")
	gui.Adornee = head
	gui.Size = UDim2.fromOffset(192, 29)
	gui.StudsOffsetWorldSpace = Vector3.new(0, BASE_HEIGHT - 0.4, 0)
	gui.AlwaysOnTop = true
	gui.LightInfluence = 0
	gui.ResetOnSpawn = false
	gui.Parent = player.PlayerGui
	-- контейнер по центру: иконка + текст выровнены посередине, сжатие идёт к центру
	local holder = Instance.new("Frame")
	holder.BackgroundTransparency = 1
	holder.AnchorPoint = Vector2.new(0.5, 0.5)
	holder.Position = UDim2.fromScale(0.5, 0.5)
	holder.Size = UDim2.fromScale(1, 1)
	holder.Parent = gui
	local scale = Instance.new("UIScale"); scale.Scale = 0; scale.Parent = holder
	local row = Instance.new("UIListLayout")
	row.FillDirection = Enum.FillDirection.Horizontal
	row.HorizontalAlignment = Enum.HorizontalAlignment.Center
	row.VerticalAlignment = Enum.VerticalAlignment.Center
	row.SortOrder = Enum.SortOrder.LayoutOrder
	row.Padding = UDim.new(0, 2)
	row.Parent = holder

	-- иконка блока
	local icon = Instance.new("ViewportFrame")
	icon.LayoutOrder = 1
	icon.BackgroundTransparency = 1
	icon.Size = UDim2.fromOffset(25, 25)
	icon.Ambient = Color3.fromRGB(160, 160, 170)
	icon.LightDirection = Vector3.new(-1, -1.4, -0.8)
	icon.Parent = holder
	local cam = Instance.new("Camera")
	cam.FieldOfView = 30
	cam.CFrame = CFrame.lookAt(Vector3.new(3.2, 2.6, 3.2), Vector3.zero)
	cam.Parent = icon
	icon.CurrentCamera = cam
	local model = Shared.MakeBlockModel(def, 2, 9)
	model:PivotTo(CFrame.new())
	model.Parent = icon

	local label = Instance.new("TextLabel")
	label.LayoutOrder = 2
	label.BackgroundTransparency = 1
	label.AutomaticSize = Enum.AutomaticSize.X
	label.Size = UDim2.new(0, 0, 1, 0)
	label.FontFace = FONT
	label.TextSize = 18
	label.RichText = true
	label.Parent = holder
	local stroke = Instance.new("UIStroke"); stroke.Thickness = 1.8; stroke.Color = Color3.fromRGB(10, 10, 12); stroke.Parent = label

	local p = { gui = gui, scale = scale, label = label, stroke = stroke, icon = icon, def = def, count = amount, expire = os.clock() + LIFETIME }
	setText(p)
	Shared.WorldStatic(gui) -- размер как у предмета в мире, а не постоянный на экране
	table.insert(popups, p)
	-- появление: выпрыгивает и подъезжает снизу
	TweenService:Create(scale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	layout()
end

Remotes.BlockBroken.OnClientEvent:Connect(function(who, typeName, _, amount)
	amount = amount or 1
	-- amount = 0: рюкзак полон, блок не собран — строку «x1 Stone» не показываем
	if who == player and amount > 0 then showMined(typeName, amount) end
end)

task.spawn(function()
	while true do
		local now = os.clock()
		for i = #popups, 1, -1 do
			local p = popups[i]
			if p and now >= p.expire and not p.dead then removePopup(p) end
		end
		task.wait(0.1)
	end
end)

------------------------------------------------------------------ «Рюкзак полон!» над головой

local FULL_HEIGHT = 2.6 -- выше строк «x1 Stone»
local FULL_LIFETIME = 1.6
local fullPopup = nil -- { gui, label, stroke, scale, expire }

local function showFull()
	local head = player.Character and player.Character:FindFirstChild("Head")
	if not head then return end

	-- надпись уже висит — просто «подпрыгивает» и держится дольше
	if fullPopup and not fullPopup.dead then
		fullPopup.expire = os.clock() + FULL_LIFETIME
		fullPopup.scale.Scale = 1.3
		TweenService:Create(fullPopup.scale, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
		return
	end

	local gui = Instance.new("BillboardGui")
	gui.Adornee = head
	gui.Size = UDim2.fromOffset(260, 40)
	gui.StudsOffsetWorldSpace = Vector3.new(0, FULL_HEIGHT - 0.4, 0)
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
	label.TextSize = 24
	label.Text = "Рюкзак полон!"
	label.TextColor3 = Color3.fromRGB(255, 90, 90)
	label.Parent = gui
	local stroke = Instance.new("UIStroke"); stroke.Thickness = 2.2; stroke.Color = Color3.fromRGB(10, 10, 12); stroke.Parent = label
	local scale = Instance.new("UIScale"); scale.Scale = 0; scale.Parent = label
	Shared.WorldStatic(gui) -- размер как у предмета в мире, а не постоянный на экране

	local p = { gui = gui, label = label, stroke = stroke, scale = scale, expire = os.clock() + FULL_LIFETIME }
	fullPopup = p

	-- выпрыгивает с пружинкой и подъезжает вверх
	TweenService:Create(scale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	TweenService:Create(gui, TweenInfo.new(0.4, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
		{ StudsOffsetWorldSpace = Vector3.new(0, FULL_HEIGHT, 0) }):Play()

	-- ждём, пока не перестанут бить по полному рюкзаку, потом уходит вверх и тает
	task.spawn(function()
		while os.clock() < p.expire do task.wait(0.1) end
		p.dead = true
		if fullPopup == p then fullPopup = nil end
		local info = TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
		TweenService:Create(scale, info, { Scale = 0 }):Play()
		TweenService:Create(label, info, { TextTransparency = 1 }):Play()
		TweenService:Create(stroke, info, { Transparency = 1 }):Play()
		TweenService:Create(gui, info, { StudsOffsetWorldSpace = Vector3.new(0, FULL_HEIGHT + 0.5, 0) }):Play()
		Debris:AddItem(gui, 0.4)
	end)
end

Remotes.Full.OnClientEvent:Connect(showFull)
```
