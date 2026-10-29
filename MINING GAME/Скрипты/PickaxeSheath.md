---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Кирка]]"
tags: [скрипт, LocalScript]
---
# PickaxeSheath

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Кирка]]

Кирка на спине: двигает кирку между рукой и спиной по дуге над правым плечом у всех персонажей, звуки и эффекты «достать/убрать». Когда доставать — решает [[PickaxeClient]].

## Заметки
- Это твоя версия, без моих правок.

## Связано
- [[PickaxeClient]]
- [[SwingAnimation]]
- [[MiningFX]]
- [[MiningShared]]

## Код
```lua
-- Кирка на спине: двигает кирку между рукой и спиной (по дуге над правым плечом) для всех персонажей,
-- играет звуки и эффекты «достать/убрать». Когда убирать/доставать решает PickaxeClient у владельца.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local SwingAnimation = require(ReplicatedStorage:WaitForChild("SwingAnimation"))
local MiningFX = require(ReplicatedStorage:WaitForChild("MiningFX"))

-- кирка по диагонали за спиной: рукоять снизу-слева, голова над правым плечом
local BACK = CFrame.new(0.1, 0.2, 0.8) * CFrame.Angles(0, 0, math.rad(-38)) * CFrame.Angles(0, math.rad(90), 0)
local ARC = Vector3.new(1.4, 2.7, 0.5) -- верхняя точка дуги относительно торса

-- Настоящая кирка всегда остаётся в руке (физику и хват не трогаем — иначе сервер теряет кирку).
-- Пока она «на спине» или летит, настоящая скрыта только визуально, а рисуется её копия без физики.
local visuals = setmetatable({}, { __mode = "k" }) -- character -> { tool, model, parts, cframes, rel, hidden }
local visualFolder = Instance.new("Folder")
visualFolder.Name = "PickaxeVisuals"
visualFolder.Parent = workspace

local function torsoOf(character)
	return character:FindFirstChild("Torso") or character:FindFirstChild("UpperTorso")
end

local function buildVisual(tool)
	local handle = tool:FindFirstChild("Handle")
	if not handle then return nil end
	local model = Instance.new("Model")
	model.Name = "PickaxeVisual"
	local parts, rel = {}, {}
	for _, p in ipairs(tool:GetChildren()) do
		if p:IsA("BasePart") then
			local c = p:Clone()
			for _, d in ipairs(c:GetDescendants()) do
				if d:IsA("JointInstance") or d:IsA("WeldConstraint") or d:IsA("BaseScript") then d:Destroy() end
			end
			c.Anchored = true
			c.CanCollide = false
			c.CanQuery = false
			c.CanTouch = false
			c.Parent = model
			table.insert(parts, c)
			rel[c] = handle.CFrame:ToObjectSpace(p.CFrame)
			if p == handle then model.PrimaryPart = c end
		end
	end
	model.Parent = visualFolder
	return { tool = tool, model = model, parts = parts, rel = rel, cframes = table.create(#parts) }
end

local function setRealHidden(info, hidden)
	if info.hidden == hidden then
		if not hidden then return end
	end
	info.hidden = hidden
	for _, p in ipairs(info.tool:GetDescendants()) do
		if p:IsA("BasePart") then p.LocalTransparencyModifier = hidden and 1 or 0 end
	end
end

local function update(character)
	local tool = character:FindFirstChild("Pickaxe")
	local info = visuals[character]
	if not tool then
		if info then info.model:Destroy(); visuals[character] = nil end
		return
	end
	if not info or info.tool ~= tool or not info.model.Parent then
		if info then info.model:Destroy() end
		info = buildVisual(tool)
		if not info then return end
		visuals[character] = info
	end
	local handle = tool:FindFirstChild("Handle")
	local torso = torsoOf(character)
	local k = SwingAnimation.HandleBlend(character)
	if k >= 0.999 or not torso or not handle then
		-- кирка в руке: показываем настоящую, копию прячем
		setRealHidden(info, false)
		if info.model.Parent ~= nil then info.model.Parent = nil end
		return
	end
	setRealHidden(info, true)
	if info.model.Parent ~= visualFolder then info.model.Parent = visualFolder end
	local hand = handle.CFrame
	local back = torso.CFrame * BACK
	-- позиция по дуге (кривая Безье через точку над плечом), поворот — плавно
	local ctrl = torso.CFrame:PointToWorldSpace(ARC)
	local pos = back.Position:Lerp(ctrl, k):Lerp(ctrl:Lerp(hand.Position, k), k)
	local world = CFrame.new(pos) * back.Rotation:Lerp(hand.Rotation, k)
	for i, p in ipairs(info.parts) do
		info.cframes[i] = world * info.rel[p]
	end
	workspace:BulkMoveTo(info.parts, info.cframes, Enum.BulkMoveMode.FireCFrameChanged)
end

RunService.RenderStepped:Connect(function()
	for _, p in ipairs(Players:GetPlayers()) do
		local character = p.Character
		if character then update(character) end
	end
end)

------------------------------------------------------------------ звуки и эффекты

local function pickaxeHead(character)
	local tool = character:FindFirstChild("Pickaxe")
	return tool and tool:FindFirstChild("Head"), tool and tool:FindFirstChild("Handle")
end

SwingAnimation.Transition.Event:Connect(function(character, kind)
	local head, handle = pickaxeHead(character)
	if not handle then return end
	local info = visuals[character]
	local visualHandle = info and info.model.PrimaryPart
	local trail = visualHandle and visualHandle:FindFirstChild("SwingTrail")
	if kind == "draw" then
		Shared.PlaySound(Shared.Sounds.Swing, handle, 0.5, 1.3)
		if trail then trail.Enabled = true end
		-- кирка оказалась в руке: блик и «дзынь»
		task.delay(SwingAnimation.DRAW_TIME * 0.62, function()
			if head and head.Parent then
				MiningFX.Glint(head.Position)
				Shared.PlaySound(Shared.Sounds.Draw, handle, 0.35, 1.6)
			end
		end)
		task.delay(SwingAnimation.DRAW_TIME * 0.85, function()
			if trail then trail.Enabled = false end
		end)
	else
		Shared.PlaySound(Shared.Sounds.Swing, handle, 0.35, 0.85)
		task.delay(SwingAnimation.SHEATHE_TIME * 0.56, function()
			if handle.Parent then Shared.PlaySound(Shared.Sounds.Land, handle, 0.3, 1.3) end
		end)
	end
end)

------------------------------------------------------------------ чужие персонажи: состояние приходит атрибутом

local function watchCharacter(player, character)
	if player == Players.LocalPlayer then return end
	local function apply(initial)
		local sheathed = character:GetAttribute("PickaxeSheathed")
		if sheathed == nil then return end
		if initial then
			SwingAnimation.SetSheathed(character, sheathed)
		elseif sheathed then
			SwingAnimation.Sheathe(character)
		else
			SwingAnimation.Draw(character)
		end
	end
	character:GetAttributeChangedSignal("PickaxeSheathed"):Connect(function() apply(false) end)
	character:WaitForChild("Pickaxe", 10)
	apply(true)
end

local function watchPlayer(p)
	p.CharacterAdded:Connect(function(c) watchCharacter(p, c) end)
	if p.Character then task.spawn(watchCharacter, p, p.Character) end
end
Players.PlayerAdded:Connect(watchPlayer)
for _, p in ipairs(Players:GetPlayers()) do watchPlayer(p) end
```
