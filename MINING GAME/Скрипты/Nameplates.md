---
тип: Script
где: ServerScriptService
система: "[[Таблички]]"
tags: [скрипт, Script]
---
# Nameplates

**Тип:** Script · **Где:** `ServerScriptService` · **Система:** [[Таблички]]

Табличка над головой: «Level: 10» (число оранжевое), под ней ник, шрифт BuilderSans ExtraBold. В зоне копания (`MineArea`) ставит атрибут `Hidden`.



## Связано
- [[NameplateFX]]
- [[MiningShared]]
- [[MineServer]]

## Код
```lua
-- Табличка над головой: «Level: 10» (число оранжевое), под ней ник. Видят все игроки.
-- В зоне копания табличка прячется, при выходе — появляется снова.
-- Сервер ставит атрибут Hidden, саму анимацию проигрывает клиент (NameplateFX).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local M = Shared.Mine

local FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.ExtraBold)
local LEVEL_COLOR = "#FFA60B"
local OUTLINE = Color3.fromRGB(20, 20, 22)
local HEIGHT = 2.0 -- центр таблички над центром головы, студы

-- зона копания: по детали MineArea (по X/Z — её границы, по высоте — от низа до чуть выше верха)
local ZONE_MARGIN = 1   -- запас по краям шахты, студы
local ZONE_TOP = 7      -- выше поверхности шахты на столько студов — уже не в зоне
local area = workspace:WaitForChild("Mine"):WaitForChild("MineArea")
local half = area.Size / 2
local ZONE_MIN = area.Position - half - Vector3.new(ZONE_MARGIN, 10, ZONE_MARGIN)
local ZONE_MAX = area.Position + half + Vector3.new(ZONE_MARGIN, ZONE_TOP, ZONE_MARGIN)

local function inMineZone(pos: Vector3)
	return pos.X >= ZONE_MIN.X and pos.X <= ZONE_MAX.X
		and pos.Y >= ZONE_MIN.Y and pos.Y <= ZONE_MAX.Y
		and pos.Z >= ZONE_MIN.Z and pos.Z <= ZONE_MAX.Z
end

local function levelText(player)
	return string.format('Level: <font color="%s">%d</font>', LEVEL_COLOR, player:GetAttribute("Level") or 1)
end

local function makeLabel(parent, posY, sizeY)
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.Position = UDim2.fromScale(0, posY)
	label.Size = UDim2.fromScale(1, sizeY)
	label.FontFace = FONT
	label.TextScaled = true
	label.TextColor3 = Color3.new(1, 1, 1)
	label.Parent = parent
	local stroke = Instance.new("UIStroke")
	stroke.Thickness = 1.5
	stroke.Color = OUTLINE
	stroke.LineJoinMode = Enum.LineJoinMode.Round
	stroke.Parent = label
	return label
end

local plates = {} -- [player] = { gui, level }

local function attach(player, character)
	local head = character:WaitForChild("Head", 10)
	if not head then return end
	local humanoid = character:FindFirstChildOfClass("Humanoid") or character:WaitForChild("Humanoid", 10)
	if humanoid then
		humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None -- прячем стандартный ник
	end

	local gui = Instance.new("BillboardGui")
	gui.Name = "Nameplate"
	gui.Adornee = head
	gui.Size = UDim2.fromScale(6, 1.3) -- в стадах: размер как у предмета в мире
	gui.StudsOffsetWorldSpace = Vector3.new(0, HEIGHT, 0)
	gui.LightInfluence = 0
	gui.MaxDistance = 100
	gui:SetAttribute("Hidden", inMineZone(head.Position))

	local level = makeLabel(gui, 0, 0.44)
	level.RichText = true
	level.Text = levelText(player)

	local name = makeLabel(gui, 0.44, 0.56)
	name.Text = player.DisplayName

	gui.Parent = head -- в самом конце: клиент получает табличку уже целиком
	plates[player] = { gui = gui, level = level }
end

local function setup(player)
	player.CharacterAdded:Connect(function(character)
		attach(player, character)
	end)
	if player.Character then
		task.spawn(attach, player, player.Character)
	end
	player:GetAttributeChangedSignal("Level"):Connect(function()
		local plate = plates[player]
		if plate and plate.level.Parent then
			plate.level.Text = levelText(player)
		end
	end)
end

Players.PlayerAdded:Connect(setup)
Players.PlayerRemoving:Connect(function(player) plates[player] = nil end)
for _, p in ipairs(Players:GetPlayers()) do setup(p) end

-- вошёл в шахту — табличка прячется, вышел — возвращается (анимацию делает клиент)
task.spawn(function()
	while true do
		for player, plate in pairs(plates) do
			local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
			if plate.gui.Parent and root then
				local hidden = inMineZone(root.Position)
				if plate.gui:GetAttribute("Hidden") ~= hidden then plate.gui:SetAttribute("Hidden", hidden) end
			end
		end
		task.wait(0.2)
	end
end)
```
