---
тип: Script
где: ServerScriptService
система: "[[Персонаж]]"
tags: [скрипт, Script]
---
# CollisionSetup

**Тип:** Script · **Где:** `ServerScriptService` · **Система:** [[Персонаж]]

Группы столкновений: `Players`, `PlayerUpper`, `MiningChips`. Верх тела и кирка ни с чем не сталкиваются (удар не отталкивает назад), ноги стоят на блоках, осколки не толкают игрока.

## Заметки
- Если отключить коллизию у всего тела — проваливаешься сквозь блоки.

## Связано
- [[MiningFX]]
- [[SwingAnimation]]

## Код
```lua
-- Столкновения персонажа и эффектов:
--   • верх тела (голова, UpperTorso, руки, аксессуары, кирка) не сталкивается с миром — анимация удара
--     наклоняет его вперёд в блок, и это больше не отталкивает персонажа назад;
--   • низ тела (HumanoidRootPart, LowerTorso / Torso у R6, ноги) сталкивается как обычно — стоим на блоках;
--   • осколки от ударов падают на землю, но игроков не толкают.
local PhysicsService = game:GetService("PhysicsService")
local Players = game:GetService("Players")

local PLAYERS_GROUP = "Players"      -- низ тела: пол, стены, блоки — как обычно
local UPPER_GROUP = "PlayerUpper"    -- верх тела: с миром не сталкивается
local CHIPS_GROUP = "MiningChips"    -- осколки от ударов

-- части, которые анимация удара двигает вперёд
local UPPER_PARTS = {
	Head = true,
	UpperTorso = true,
	RightUpperArm = true, RightLowerArm = true, RightHand = true,
	LeftUpperArm = true, LeftLowerArm = true, LeftHand = true,
	["Right Arm"] = true, ["Left Arm"] = true, -- R6
}

for _, name in ipairs({ PLAYERS_GROUP, UPPER_GROUP, CHIPS_GROUP }) do
	if not PhysicsService:IsCollisionGroupRegistered(name) then
		PhysicsService:RegisterCollisionGroup(name)
	end
end
for _, other in ipairs({ "Default", PLAYERS_GROUP, UPPER_GROUP, CHIPS_GROUP }) do
	PhysicsService:CollisionGroupSetCollidable(UPPER_GROUP, other, false)
end
PhysicsService:CollisionGroupSetCollidable(CHIPS_GROUP, PLAYERS_GROUP, false)
PhysicsService:CollisionGroupSetCollidable(CHIPS_GROUP, CHIPS_GROUP, false)

local function setupPart(part)
	if not part:IsA("BasePart") then return end
	local inTool = part:FindFirstAncestorOfClass("Tool") ~= nil
	local inAccessory = part:FindFirstAncestorOfClass("Accessory") ~= nil
	if UPPER_PARTS[part.Name] or inTool or inAccessory then
		part.CollisionGroup = UPPER_GROUP
	else
		part.CollisionGroup = PLAYERS_GROUP
	end
	-- кирка и любые инструменты в руках: без столкновений и без веса
	if inTool then
		part.CanCollide = false
		part.Massless = true
	end
end

local function setupCharacter(character)
	for _, d in ipairs(character:GetDescendants()) do setupPart(d) end
	character.DescendantAdded:Connect(setupPart)
end

local function setupPlayer(player)
	player.CharacterAdded:Connect(setupCharacter)
	if player.Character then setupCharacter(player.Character) end
end

Players.PlayerAdded:Connect(setupPlayer)
for _, p in ipairs(Players:GetPlayers()) do setupPlayer(p) end
```
