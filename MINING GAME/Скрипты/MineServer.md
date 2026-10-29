---
тип: Script
где: ServerScriptService
система: "[[Система шахты]]"
tags: [скрипт, Script]
---
# MineServer

**Тип:** Script · **Где:** `ServerScriptService` · **Система:** [[Система шахты]]

Сервер шахты: заполняет большой невидимый Part `workspace.Mine.MineArea` блоками сеткой 4×4×4 (слоями вниз, глубже — ценнее), считает урон, вместимость, начисляет опыт, обновляет шахту.

## Заметки
- Название в Studio может быть другим — это твой серверный скрипт шахты.
- При полном рюкзаке блок ломается, опыт даётся, но `amount = 0` и `Remotes.Full`.
- Размер шахты задаёт деталь `MineArea` (без поворота, размеры кратны 4).

## Связано
- [[MiningShared]]
- [[MiningEffects]]
- [[MiningHUD]]
- [[CapacityOrb]]
- [[PickaxeClient]]

## Код
```lua
-- Сервер шахты: большой невидимый Part workspace.Mine.MineArea заполняется блоками сеткой
-- (слоями вниз, глубже — ценнее), урон, вместимость, обновление шахты.
-- Верх MineArea — поверхность шахты; размер / CELL = сколько блоков в ширину, глубину и слоёв вниз.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = require(ReplicatedStorage.MiningShared)
local Remotes = ReplicatedStorage.Remotes
local M = Shared.Mine

local mine = workspace:WaitForChild("Mine")
local blockFolder = mine:WaitForChild("Blocks")
local area = mine:WaitForChild("MineArea")

-- сама зона невидима и ни с чем не сталкивается, курсор и лучи сквозь неё проходят
area.Transparency = 1
area.CanCollide = false
area.CanQuery = false
area.CanTouch = false
area.CastShadow = false
area.Anchored = true

-- размеры шахты берём из детали (сетка по центру, если размер не кратен CELL)
M.W = math.max(1, math.floor(area.Size.X / M.CELL))
M.D = math.max(1, math.floor(area.Size.Z / M.CELL))
M.L = math.max(1, math.floor(area.Size.Y / M.CELL))
M.ORIGIN = Vector3.new(
	area.Position.X - area.Size.X / 2 + (area.Size.X - M.W * M.CELL) / 2,
	area.Position.Y + area.Size.Y / 2,
	area.Position.Z - area.Size.Z / 2 + (area.Size.Z - M.D * M.CELL) / 2
)

local rng = Random.new()
local mined = {}   -- [index] = true
local blocks = {}  -- [index] = model
local minedCount = 0
local resetting = false
local lastHit = {}
local TOTAL = M.W * M.D * M.L
-- точка у края шахты над поверхностью (кнопка «Наверх», телепорт при обновлении)
local SURFACE_CF = CFrame.new(M.ORIGIN.X + M.W * M.CELL / 2, M.ORIGIN.Y + 4, M.ORIGIN.Z - 6)

local function index(i, j, k)
	return i + j * M.W + k * M.W * M.D
end

local function inBounds(i, j, k)
	return i >= 0 and i < M.W and j >= 0 and j < M.D and k >= 0 and k < M.L
end

-- игрок внутри шахты (ниже поверхности, в пределах MineArea по X/Z)
local function insideMine(pos)
	return pos.Y < M.ORIGIN.Y + 1
		and pos.X >= M.ORIGIN.X and pos.X <= M.ORIGIN.X + M.W * M.CELL
		and pos.Z >= M.ORIGIN.Z and pos.Z <= M.ORIGIN.Z + M.D * M.CELL
end

------------------------------------------------------------------ игроки

local function setupPlayer(player: Player)
	local stats = Instance.new("Folder")
	stats.Name = "leaderstats"
	local count = Instance.new("IntValue"); count.Name = "Blocks"; count.Parent = stats
	stats.Parent = player
	player:SetAttribute("Blocks", 0)
	player:SetAttribute("MaxCapacity", Shared.MAX_CAPACITY)
	player:SetAttribute("LastBlock", "")
	-- уровень и опыт (если есть сохранение — загрузи сюда сохранённые значения)
	player:SetAttribute("Level", player:GetAttribute("Level") or 1)
	player:SetAttribute("XP", player:GetAttribute("XP") or 0)
	for _, def in ipairs(Shared.Blocks) do
		player:SetAttribute("Inv_" .. def.name, 0)
	end
	player:GetAttributeChangedSignal("Blocks"):Connect(function()
		count.Value = player:GetAttribute("Blocks")
	end)
end
Players.PlayerAdded:Connect(setupPlayer)
for _, p in ipairs(Players:GetPlayers()) do setupPlayer(p) end
Players.PlayerRemoving:Connect(function(p) lastHit[p] = nil end)

------------------------------------------------------------------ блоки

local function spawnBlock(i, j, k)
	local idx = index(i, j, k)
	if mined[idx] or blocks[idx] then return end
	local def = Shared.RollBlock(rng, k)
	local hp = math.floor(def.hp * (1 + k * 0.04))
	local model = Shared.MakeBlockModel(def, M.CELL, rng:NextInteger(1, 1e6))
	model:PivotTo(CFrame.new(Shared.CellPosition(i, j, k)) * CFrame.Angles(0, math.rad(90 * rng:NextInteger(0, 3)), 0))
	model:SetAttribute("BlockType", def.name)
	model:SetAttribute("HP", hp)
	model:SetAttribute("MaxHP", hp)
	model:SetAttribute("I", i)
	model:SetAttribute("J", j)
	model:SetAttribute("K", k)
	blocks[idx] = model
	model.Parent = blockFolder
end

-- открываем соседей выкопанной клетки (блоки создаются только когда их видно)
local NEIGHBORS = { {1,0,0}, {-1,0,0}, {0,1,0}, {0,-1,0}, {0,0,1}, {0,0,-1} }
local function reveal(i, j, k)
	for _, n in ipairs(NEIGHBORS) do
		local a, b, c = i + n[1], j + n[2], k + n[3]
		if inBounds(a, b, c) then spawnBlock(a, b, c) end
	end
end

local function fillTopLayer()
	for i = 0, M.W - 1 do
		for j = 0, M.D - 1 do
			spawnBlock(i, j, 0)
		end
		task.wait()
	end
end

local function resetMine()
	if resetting then return end
	resetting = true
	Remotes.Notify:FireAllClients("Шахта обновится через 5 секунд!", Color3.fromRGB(255, 210, 80))
	task.wait(5)
	for _, player in ipairs(Players:GetPlayers()) do
		local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
		if root and insideMine(root.Position) then
			player.Character:PivotTo(SURFACE_CF)
		end
	end
	blockFolder:ClearAllChildren()
	table.clear(mined)
	table.clear(blocks)
	minedCount = 0
	fillTopLayer()
	resetting = false
end

fillTopLayer()

------------------------------------------------------------------ добыча

local function hasPickaxe(character)
	local tool = character and character:FindFirstChildOfClass("Tool")
	return tool ~= nil and tool.Name == "Pickaxe"
end

Remotes.Swing.OnServerEvent:Connect(function(player, duration, fromWindup)
	if typeof(duration) ~= "number" or not hasPickaxe(player.Character) then return end
	duration = math.clamp(duration, 0.2, 1)
	for _, other in ipairs(Players:GetPlayers()) do
		if other ~= player then Remotes.Swing:FireClient(other, player, duration, fromWindup == true) end
	end
end)

Remotes.MineHit.OnServerEvent:Connect(function(player, model)
	if resetting or typeof(model) ~= "Instance" or model.Parent ~= blockFolder then return end
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root or not hasPickaxe(character) then return end
	if (root.Position - model:GetPivot().Position).Magnitude > Shared.MINE_RANGE then return end

	local now = os.clock()
	if lastHit[player] and now - lastHit[player] < Shared.SwingTime(player) * 0.8 then return end
	lastHit[player] = now

	local crit = rng:NextNumber() < Shared.CRIT_CHANCE
	local damage = Shared.BASE_DAMAGE * (crit and 2 or 1)
	local hp = model:GetAttribute("HP") - damage
	model:SetAttribute("HP", hp)
	Remotes.BlockHit:FireAllClients(model, damage, crit, player)

	if hp <= 0 then
		local typeName = model:GetAttribute("BlockType")
		local i, j, k = model:GetAttribute("I"), model:GetAttribute("J"), model:GetAttribute("K")
		local idx = index(i, j, k)

		-- рюкзак полон — блок всё равно ломается, но в инвентарь не идёт
		local count, max = player:GetAttribute("Blocks"), player:GetAttribute("MaxCapacity")
		local collected = count < max
		if collected then
			player:SetAttribute("Blocks", count + 1)
			player:SetAttribute("Inv_" .. typeName, player:GetAttribute("Inv_" .. typeName) + 1)
			player:SetAttribute("LastBlock", typeName)
		else
			Remotes.Full:FireClient(player) -- «Рюкзак полон!» над головой, тряска шара
		end
		-- amount = 0: клиент не запускает кубик в шар и не показывает «x1 Stone»
		Remotes.BlockBroken:FireAllClients(player, typeName, model:GetPivot(), collected and 1 or 0)

		-- опыт за блок даётся всегда, даже при полном рюкзаке
		local def = Shared.BlockByName[typeName]
		if def then Shared.AddXP(player, def.xp or 0) end

		mined[idx] = true
		blocks[idx] = nil
		minedCount += 1
		model:Destroy()
		reveal(i, j, k)
		if minedCount >= TOTAL * M.RESET_AT then
			task.spawn(resetMine)
		end
	end
end)

-- кирка на спине / в руке (видят все игроки)
Remotes.Sheath.OnServerEvent:Connect(function(player, sheathed)
	if typeof(sheathed) ~= "boolean" then return end
	local character = player.Character
	if character then character:SetAttribute("PickaxeSheathed", sheathed) end
end)

-- кнопка «Наверх»
local lastUp = {}
Remotes.GoUp.OnServerEvent:Connect(function(player)
	if lastUp[player] and os.clock() - lastUp[player] < 2 then return end
	lastUp[player] = os.clock()
	if player.Character then player.Character:PivotTo(SURFACE_CF) end
end)
```
