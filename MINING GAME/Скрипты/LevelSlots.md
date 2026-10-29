---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Уровни и опыт]]"
tags: [скрипт, LocalScript]
---
# LevelSlots

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Уровни и опыт]]

6 слотов над полоской уровня с номерами снизу. Закрытый слот светлее, на нём замок (нарисован рамками) и «Lvl 12». Открывается, когда у игрока есть нужный уровень, с анимацией.

## Заметки
- Уровни открытия: `SLOT_LEVELS = { 1, 1, 1, 12, 12, 16 }`.
- У каждого слота (`Slot1`…`Slot6`) атрибут `Unlocked`.
- Высота над низом экрана: `BOTTOM_OFFSET` (под полоску из [[LevelBar]]).

## Связано
- [[LevelBar]]
- [[MiningShared]]

## Код
```lua
-- Слоты над полоской уровня: 6 квадратов с номерами снизу.
-- Закрытый слот светлее, на нём замок и «Lvl 12»; открывается, когда у игрока есть нужный уровень.
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")

local player = Players.LocalPlayer

local SLOT_LEVELS = { 1, 1, 1, 12, 12, 16 } -- с какого уровня открывается каждый слот
local SLOT_SIZE = 52
local SLOT_GAP = 8
local BOTTOM_OFFSET = 45 -- от низа экрана до низа слотов: над полоской уровня (6 + 19) с местом под номера

local FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.ExtraBold)
local OUTLINE = Color3.fromRGB(18, 18, 18)
local OPEN_COLOR = Color3.fromRGB(48, 48, 48)
local LOCKED_COLOR = Color3.fromRGB(88, 88, 88)

local screen = Instance.new("ScreenGui")
screen.Name = "LevelSlots"
screen.ResetOnSpawn = false
screen.IgnoreGuiInset = true
screen.Parent = player:WaitForChild("PlayerGui")

local row = Instance.new("Frame")
row.Name = "Slots"
row.AnchorPoint = Vector2.new(0.5, 1)
row.Position = UDim2.new(0.5, 0, 1, -BOTTOM_OFFSET)
row.Size = UDim2.fromOffset(#SLOT_LEVELS * SLOT_SIZE + (#SLOT_LEVELS - 1) * SLOT_GAP, SLOT_SIZE)
row.BackgroundTransparency = 1
row.Parent = screen
local layout = Instance.new("UIListLayout")
layout.FillDirection = Enum.FillDirection.Horizontal
layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
layout.SortOrder = Enum.SortOrder.LayoutOrder
layout.Padding = UDim.new(0, SLOT_GAP)
layout.Parent = row

local function corner(parent, radius)
	local c = Instance.new("UICorner")
	c.CornerRadius = radius
	c.Parent = parent
end

local function stroke(parent, thickness, color)
	local s = Instance.new("UIStroke")
	s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	s.Thickness = thickness
	s.Color = color or OUTLINE
	s.Parent = parent
	return s
end

-- верх ровный, к низу чуть темнее
local function shade(parent, bottom)
	local g = Instance.new("UIGradient")
	g.Rotation = 90
	g.Color = ColorSequence.new({
		ColorSequenceKeypoint.new(0, Color3.new(1, 1, 1)),
		ColorSequenceKeypoint.new(0.5, Color3.new(1, 1, 1)),
		ColorSequenceKeypoint.new(1, Color3.new(bottom, bottom, bottom)),
	})
	g.Parent = parent
end

local function label(parent, text, size)
	local l = Instance.new("TextLabel")
	l.BackgroundTransparency = 1
	l.FontFace = FONT
	l.Text = text
	l.TextSize = size
	l.TextColor3 = Color3.new(1, 1, 1)
	l.Parent = parent
	stroke(l, 1.2).ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual
	return l
end

-- замок из рамок: дужка (белая с чёрной обводкой) + корпус с замочной скважиной
local function makeLock(parent)
	local lock = Instance.new("Frame")
	lock.Name = "Lock"
	lock.AnchorPoint = Vector2.new(0.5, 0)
	lock.Position = UDim2.new(0.5, 0, 0, 5)
	lock.Size = UDim2.fromOffset(20, 25)
	lock.BackgroundTransparency = 1
	lock.Parent = parent

	for i, look in ipairs({ { 5.5, OUTLINE }, { 3, Color3.new(1, 1, 1) } }) do
		local shackle = Instance.new("Frame")
		shackle.AnchorPoint = Vector2.new(0.5, 0)
		shackle.Position = UDim2.new(0.5, 0, 0, 2)
		shackle.Size = UDim2.fromOffset(11, 15)
		shackle.BackgroundTransparency = 1
		shackle.ZIndex = i
		shackle.Parent = lock
		corner(shackle, UDim.new(0.5, 0))
		stroke(shackle, look[1], look[2])
	end

	local body = Instance.new("Frame")
	body.AnchorPoint = Vector2.new(0.5, 1)
	body.Position = UDim2.new(0.5, 0, 1, 0)
	body.Size = UDim2.fromOffset(20, 14)
	body.BackgroundColor3 = Color3.new(1, 1, 1)
	body.BorderSizePixel = 0
	body.ZIndex = 3
	body.Parent = lock
	corner(body, UDim.new(0, 3))
	stroke(body, 1.5)

	local hole = Instance.new("Frame")
	hole.AnchorPoint = Vector2.new(0.5, 0.5)
	hole.Position = UDim2.fromScale(0.5, 0.5)
	hole.Size = UDim2.fromOffset(4, 6)
	hole.BackgroundColor3 = Color3.fromRGB(60, 60, 60)
	hole.BorderSizePixel = 0
	hole.ZIndex = 4
	hole.Parent = body
	corner(hole, UDim.new(0.5, 0))

	return lock
end

local slots = {}
for i, need in ipairs(SLOT_LEVELS) do
	local slot = Instance.new("Frame")
	slot.Name = "Slot" .. i
	slot.LayoutOrder = i
	slot.Size = UDim2.fromOffset(SLOT_SIZE, SLOT_SIZE)
	slot.BackgroundColor3 = OPEN_COLOR
	slot.BorderSizePixel = 0
	slot.Parent = row
	corner(slot, UDim.new(0, 6))
	stroke(slot, 1.5)
	shade(slot, 0.82)
	local pop = Instance.new("UIScale")
	pop.Parent = slot

	-- номер слота на нижнем краю
	local badge = Instance.new("Frame")
	badge.Name = "Number"
	badge.AnchorPoint = Vector2.new(0.5, 0.5)
	badge.Position = UDim2.new(0.5, 0, 1, 1)
	badge.Size = UDim2.fromOffset(18, 15)
	badge.BackgroundColor3 = Color3.fromRGB(130, 130, 130)
	badge.BorderSizePixel = 0
	badge.ZIndex = 5
	badge.Parent = slot
	corner(badge, UDim.new(0, 4))
	stroke(badge, 1.5)
	shade(badge, 0.7)
	local num = label(badge, tostring(i), 12)
	num.Size = UDim2.fromScale(1, 1)
	num.ZIndex = 6

	-- замок и «Lvl 12»
	local lockGroup = Instance.new("Frame")
	lockGroup.Name = "Locked"
	lockGroup.Size = UDim2.fromScale(1, 1)
	lockGroup.BackgroundTransparency = 1
	lockGroup.Parent = slot
	local lockScale = Instance.new("UIScale")
	lockScale.Parent = lockGroup
	makeLock(lockGroup)
	local req = label(lockGroup, "Lvl " .. need, 13)
	req.AnchorPoint = Vector2.new(0.5, 0)
	req.Position = UDim2.new(0.5, 0, 0, 31)
	req.Size = UDim2.new(1, 0, 0, 13)
	req.ZIndex = 4

	slots[i] = { frame = slot, need = need, lock = lockGroup, lockScale = lockScale, pop = pop, unlocked = nil }
end

local function setUnlocked(s, unlocked, animate)
	if s.unlocked == unlocked then return end
	s.unlocked = unlocked
	s.frame:SetAttribute("Unlocked", unlocked)
	local color = unlocked and OPEN_COLOR or LOCKED_COLOR
	if not animate then
		s.frame.BackgroundColor3 = color
		s.lock.Visible = not unlocked
		s.lockScale.Scale = 1
		return
	end
	if unlocked then
		-- замок сжимается и пропадает, слот темнеет и подпрыгивает
		local shrink = TweenService:Create(s.lockScale, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.In), { Scale = 0 })
		shrink.Completed:Once(function()
			if s.unlocked then s.lock.Visible = false end
		end)
		shrink:Play()
		TweenService:Create(s.frame, TweenInfo.new(0.35), { BackgroundColor3 = color }):Play()
		s.pop.Scale = 1.15
		TweenService:Create(s.pop, TweenInfo.new(0.45, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	else
		s.lock.Visible = true
		s.lockScale.Scale = 1
		s.frame.BackgroundColor3 = color
	end
end

local function refresh(animate)
	local level = player:GetAttribute("Level") or 1
	for _, s in ipairs(slots) do
		setUnlocked(s, level >= s.need, animate)
	end
end

refresh(false)
local hadLevel = player:GetAttribute("Level") ~= nil
player:GetAttributeChangedSignal("Level"):Connect(function()
	-- первая загрузка уровня при входе — без анимации
	refresh(hadLevel)
	hadLevel = true
end)
```
