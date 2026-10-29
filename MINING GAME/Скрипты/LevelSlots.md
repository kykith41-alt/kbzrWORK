---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Уровни и опыт]]"
tags: [скрипт, LocalScript]
---
# LevelSlots

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Уровни и опыт]]

6 слотов над полоской уровня с номерами снизу. Закрытый слот светлее, с фоновой картинкой, замком и «Lvl 12». Открывается, когда у игрока есть нужный уровень, с анимацией.

## Заметки
- Уровни открытия: `SLOT_LEVELS = { 1, 1, 1, 12, 12, 16 }`.
- У каждого слота (`Slot1`…`Slot6`) атрибут `Unlocked`.
- Высота над низом экрана: `BOTTOM_OFFSET` (под полоску из [[LevelBar]]).
- Замок: `LOCK_IMAGE` = [15117261700](https://create.roblox.com/store/asset/15117261700). Фон закрытого слота: `LOCKED_BG_IMAGE` = [79992524792581](https://create.roblox.com/store/asset/79992524792581), прозрачность 0.9, плитка `LOCKED_BG_TILE`.

## Связано
- [[LevelBar]]
- [[MiningShared]]

## Код
```lua
-- Слоты над полоской уровня: 6 квадратов с номерами снизу.
-- Закрытый слот светлее, с фоновой картинкой, замком и «Lvl 12»; открывается, когда у игрока есть нужный уровень.
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
local LOCK_IMAGE = "rbxassetid://15117261700"
-- через rbxthumb: картинка показывается, даже если это ID декали (Decal), а не самой картинки
local LOCKED_BG_IMAGE = "rbxthumb://type=Asset&id=79992524792581&w=420&h=420"
local LOCKED_BG_TRANSPARENCY = 0.9
local LOCKED_BG_TILE = 80 -- размер одной плитки фона в пикселях (фон повторяется)

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

local function makeLock(parent)
	local lock = Instance.new("ImageLabel")
	lock.Name = "Lock"
	lock.AnchorPoint = Vector2.new(0.5, 0)
	lock.Position = UDim2.new(0.5, 0, 0, 5)
	lock.Size = UDim2.fromOffset(24, 24)
	lock.BackgroundTransparency = 1
	lock.Image = LOCK_IMAGE
	lock.ScaleType = Enum.ScaleType.Fit
	lock.ZIndex = 3
	lock.Parent = parent
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

	-- фон закрытого слота: картинка поверх цвета, повторяется плиткой
	local bg = Instance.new("ImageLabel")
	bg.Name = "LockedBackground"
	bg.Size = UDim2.fromScale(1, 1)
	bg.BackgroundTransparency = 1
	bg.Image = LOCKED_BG_IMAGE
	bg.ImageTransparency = LOCKED_BG_TRANSPARENCY
	bg.ScaleType = Enum.ScaleType.Tile
	bg.TileSize = UDim2.fromOffset(LOCKED_BG_TILE, LOCKED_BG_TILE)
	bg.Parent = slot
	corner(bg, UDim.new(0, 6))

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
	lockGroup.ZIndex = 2
	lockGroup.Parent = slot
	local lockScale = Instance.new("UIScale")
	lockScale.Parent = lockGroup
	makeLock(lockGroup)
	local req = label(lockGroup, "Lvl " .. need, 13)
	req.AnchorPoint = Vector2.new(0.5, 0)
	req.Position = UDim2.new(0.5, 0, 0, 31)
	req.Size = UDim2.new(1, 0, 0, 13)
	req.ZIndex = 4

	slots[i] = { frame = slot, need = need, lock = lockGroup, lockScale = lockScale, pop = pop, bg = bg, unlocked = nil }
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
		s.bg.ImageTransparency = unlocked and 1 or LOCKED_BG_TRANSPARENCY
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
		TweenService:Create(s.bg, TweenInfo.new(0.35), { ImageTransparency = 1 }):Play()
		s.pop.Scale = 1.15
		TweenService:Create(s.pop, TweenInfo.new(0.45, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	else
		s.lock.Visible = true
		s.lockScale.Scale = 1
		s.frame.BackgroundColor3 = color
		s.bg.ImageTransparency = LOCKED_BG_TRANSPARENCY
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
