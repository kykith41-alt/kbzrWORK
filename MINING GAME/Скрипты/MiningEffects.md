---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Эффекты]]"
tags: [скрипт, LocalScript]
---
# MiningEffects

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Эффекты]]

Эффекты шахты на клиенте: удары других игроков, цифры урона (в том числе на добивающем ударе), разрушение блоков, звуки. При разрушении играют `Slash` (0.37 с) и `Break` (0.40 с) из ReplicatedStorage.

## Заметки
- Название в Studio может быть другим — это «скрипт эффектов шахты».
- `playEffect(template, cframe, lifetime)` — общий запуск шаблона частиц.

## Связано
- [[MiningFX]]
- [[MiningShared]]
- [[SwingAnimation]]
- [[MineServer]]
- [[Эффекты частиц]]

## Код
```lua
-- Эффекты шахты: удары других игроков, цифры урона, разрушение блоков, звуки
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local SwingAnimation = require(ReplicatedStorage:WaitForChild("SwingAnimation"))
local MiningFX = require(ReplicatedStorage:WaitForChild("MiningFX"))
local Remotes = ReplicatedStorage:WaitForChild("Remotes")
local SlashTemplate = ReplicatedStorage:WaitForChild("Slash")
local BreakTemplate = ReplicatedStorage:WaitForChild("Break")
local player = Players.LocalPlayer

Shared.PreloadSounds()

local fxFolder = workspace:WaitForChild("LocalMiningFX")

-- полоски HP блоков: следим за HP, который выставляет сервер
-- заодно запоминаем последний живой HP и позицию: на добивающем ударе блок уже удалён,
-- и цифру урона показываем по этим данным
local blockFolder = workspace:WaitForChild("Mine"):WaitForChild("Blocks")
local blockInfo = {} -- [model] = { hp, top, shownAt, brokenAt }

local function blockTop(model)
	return MiningFX.BasePivot(model).Position + Vector3.new(0, Shared.Mine.CELL / 2, 0)
end

local function watchBlock(model)
	local info = { hp = model:GetAttribute("HP"), shownAt = -10, brokenAt = -10 }
	pcall(function() info.top = blockTop(model) end)
	blockInfo[model] = info
	model:GetAttributeChangedSignal("HP"):Connect(function()
		local hp = model:GetAttribute("HP")
		if hp and hp > 0 then info.hp = hp end -- 0 не записываем: нужен остаток перед добиванием
		MiningFX.ServerHealth(model)
	end)
end
blockFolder.ChildAdded:Connect(watchBlock)
blockFolder.ChildRemoved:Connect(function(model)
	task.delay(1, function() blockInfo[model] = nil end)
end)
for _, model in ipairs(blockFolder:GetChildren()) do watchBlock(model) end

-- блок, который стоял в этой точке (сам блок к этому моменту может быть уже удалён)
local function findBlockAt(position)
	local best, bestDist = nil, Shared.Mine.CELL * 0.75
	for model, info in pairs(blockInfo) do
		if info.top then
			local d = (info.top - Vector3.new(0, Shared.Mine.CELL / 2, 0) - position).Magnitude
			if d < bestDist then best, bestDist = model, d end
		end
	end
	return best, best and blockInfo[best]
end

------------------------------------------------------------------ поза и удары других игроков (старые Motor6D-риги)

local function watchCharacter(other, character)
	if other == player then return end
	local function update()
		if SwingAnimation.UsesPhysicsJoints(character) then return end
		local tool = character:FindFirstChildOfClass("Tool")
		if tool and tool.Name == "Pickaxe" then
			SwingAnimation.StartHold(character)
		else
			SwingAnimation.StopHold(character)
		end
	end
	character.ChildAdded:Connect(update)
	character.ChildRemoved:Connect(update)
	update()
end
local function watchPlayer(other)
	other.CharacterAdded:Connect(function(c) watchCharacter(other, c) end)
	if other.Character then watchCharacter(other, other.Character) end
end
Players.PlayerAdded:Connect(watchPlayer)
for _, p in ipairs(Players:GetPlayers()) do watchPlayer(p) end

Remotes.Swing.OnClientEvent:Connect(function(other, duration, fromWindup)
	local character = other.Character
	if character and not SwingAnimation.UsesPhysicsJoints(character) then
		SwingAnimation.Play(character, duration, nil, fromWindup)
	end
end)

------------------------------------------------------------------ разрушение: эффекты Slash и Break

local EFFECT_DEFAULT_EMIT = 12 -- сколько частиц выпустить, если у эмиттера нет атрибута EmitCount
local SLASH_LIFETIME = 0.37    -- сколько живёт каждая частица Slash, секунд
local BREAK_LIFETIME = 0.40    -- сколько живёт каждая частица Break, секунд

-- копия шаблона из ReplicatedStorage на месте блока: выпускает свои частицы и удаляется
local function playEffect(template, cframe, lifetime)
	local fx = template:Clone()
	-- случайный поворот вокруг вертикали, чтобы разрушения не выглядели одинаково
	local cf = CFrame.new(cframe.Position) * CFrame.Angles(0, math.rad(math.random(0, 359)), 0)

	-- всё внутри — без физики и столкновений; частицы живут lifetime
	local longestDelay = 0
	for _, d in ipairs(fx:GetDescendants()) do
		if d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.CastShadow = false
		elseif d:IsA("ParticleEmitter") then
			d.Enabled = false
			d.Lifetime = NumberRange.new(lifetime)
			longestDelay = math.max(longestDelay, d:GetAttribute("EmitDelay") or 0)
		end
	end
	if fx:IsA("BasePart") then
		fx.Anchored = true
		fx.CanCollide = false
		fx.CanQuery = false
		fx.CanTouch = false
		fx.CastShadow = false
	end

	if fx:IsA("Model") then
		fx:PivotTo(cf)
	elseif fx:IsA("BasePart") then
		fx.CFrame = cf
	end
	fx.Parent = fxFolder

	-- видимые детали меша (если есть) тают так же быстро, как частицы
	local parts = fx:GetDescendants()
	if fx:IsA("BasePart") then table.insert(parts, fx) end
	for _, d in ipairs(parts) do
		if d:IsA("BasePart") and d.Transparency < 1 then
			TweenService:Create(d, TweenInfo.new(lifetime, Enum.EasingStyle.Quad, Enum.EasingDirection.In), { Transparency = 1 }):Play()
		end
	end

	-- выпускаем частицы (EmitCount / EmitDelay — атрибуты эмиттеров, если они заданы)
	for _, d in ipairs(fx:GetDescendants()) do
		if d:IsA("ParticleEmitter") then
			local count = d:GetAttribute("EmitCount") or EFFECT_DEFAULT_EMIT
			local delay = d:GetAttribute("EmitDelay") or 0
			if delay > 0 then
				task.delay(delay, function() if d.Parent then d:Emit(count) end end)
			else
				d:Emit(count)
			end
		end
	end
	Debris:AddItem(fx, longestDelay + lifetime + 0.3)
end

------------------------------------------------------------------ попадание (подтверждение сервера)

-- жирный шрифт с тонкой чёрной обводкой, как в симуляторах
local DAMAGE_FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.ExtraBold)
local DAMAGE_COLOR = Color3.fromRGB(240, 240, 245)
local CRIT_COLOR = Color3.fromRGB(175, 33, 33)

-- 5358 -> "5,358", 1234567.5 -> "1,234,567.5"
local function formatNumber(n)
	local int, frac = tostring(n):match("^(%d+)(%.?%d*)$")
	if not int then return tostring(n) end
	int = int:reverse():gsub("(%d%d%d)", "%1,"):reverse():gsub("^,", "")
	return int .. frac
end

local function damageNumber(position, damage, crit)
	local anchor = Instance.new("Part")
	anchor.Anchored = true; anchor.CanCollide = false; anchor.CanQuery = false; anchor.CanTouch = false
	anchor.Transparency = 1
	anchor.Size = Vector3.one * 0.1
	anchor.Position = position + Vector3.new(math.random() * 1.4 - 0.7, 0, math.random() * 1.4 - 0.7)
	anchor.Parent = fxFolder
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromScale(crit and 3.2 or 2.1, crit and 1.3 or 0.95)
	gui.AlwaysOnTop = true
	gui.LightInfluence = 0
	gui.Parent = anchor
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.AnchorPoint = Vector2.new(0.5, 0.5) -- сжимается к центру
	label.Position = UDim2.fromScale(0.5, 0.5)
	label.Size = UDim2.fromScale(1, 1)
	label.FontFace = DAMAGE_FONT
	label.TextScaled = true
	local amount = "-" .. formatNumber(damage)
	label.Text = crit and ("Critical " .. amount) or amount
	label.TextColor3 = crit and CRIT_COLOR or DAMAGE_COLOR
	local stroke = Instance.new("UIStroke")
	stroke.Thickness = 1.6
	stroke.Color = Color3.new(0, 0, 0)
	stroke.LineJoinMode = Enum.LineJoinMode.Round
	stroke.Parent = label
	label.Parent = gui
	local scale = Instance.new("UIScale"); scale.Scale = 0.2; scale.Parent = label
	-- выпрыгивает с пружинкой
	TweenService:Create(scale, TweenInfo.new(0.2, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = crit and 1.2 or 1.05 }):Play()
	-- плавно поднимается
	TweenService:Create(anchor, TweenInfo.new(0.8, Enum.EasingStyle.Quart, Enum.EasingDirection.Out), { Position = anchor.Position + Vector3.new(0, 1.4, 0) }):Play()
	-- потом уменьшается и тает
	task.delay(0.42, function()
		local info = TweenInfo.new(0.33, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
		TweenService:Create(scale, info, { Scale = 0 }):Play()
		TweenService:Create(label, info, { TextTransparency = 0.6 }):Play()
		TweenService:Create(stroke, info, { Transparency = 0.6 }):Play()
	end)
	Debris:AddItem(anchor, 0.8)
end

-- удар, пришедший без блока (сервер уже удалил его): покажем при BlockBroken
local orphanHit = nil -- { damage, crit, t }

Remotes.BlockHit.OnClientEvent:Connect(function(model, damage, crit, hitter)
	if not model or not model.Parent then
		orphanHit = { damage = damage, crit = crit, t = os.clock() }
		return
	end
	local info = blockInfo[model]
	if info and os.clock() - info.brokenAt < 0.5 then return end -- цифра уже показана при разрушении
	local top = blockTop(model)
	if hitter ~= player then
		-- свои удары уже показаны мгновенно в момент попадания кирки
		MiningFX.Impact(model, top, crit)
		Shared.PlaySound(Shared.RandomSound(Shared.Sounds.Hit), model.PrimaryPart, 0.8, 0.9 + math.random() * 0.25)
	elseif crit then
		MiningFX.Impact(model, top, true)
	end
	if info then info.shownAt = os.clock() end
	damageNumber(top + Vector3.new(0, 0.6, 0), damage, crit)
end)

Remotes.BlockBroken.OnClientEvent:Connect(function(who, typeName, cframe)
	-- пыль и блёстки разрушения (кубиков в MiningFX.Break больше нет) + эффекты Slash и Break
	local def = Shared.BlockByName[typeName]
	if def then MiningFX.Break(cframe, def) end
	playEffect(SlashTemplate, cframe, SLASH_LIFETIME)
	playEffect(BreakTemplate, cframe, BREAK_LIFETIME)

	-- цифра добивающего удара, если BlockHit её не показал
	local _, info = findBlockAt(cframe.Position)
	if not info or os.clock() - info.shownAt > 0.3 then
		local damage, crit
		if orphanHit and os.clock() - orphanHit.t < 0.5 then
			damage, crit = orphanHit.damage, orphanHit.crit
		elseif info and info.hp then
			damage, crit = info.hp, false -- сколько HP оставалось перед добиванием
		end
		orphanHit = nil
		if damage then
			local top = info and info.top or cframe.Position + Vector3.new(0, Shared.Mine.CELL / 2, 0)
			damageNumber(top + Vector3.new(0, 0.6, 0), damage, crit)
		end
	end
	if info then info.brokenAt = os.clock() end

	local parent = nil
	if who ~= player then
		parent = Instance.new("Part")
		parent.Anchored = true; parent.CanCollide = false; parent.CanQuery = false; parent.Transparency = 1
		parent.Position = cframe.Position
		parent.Parent = fxFolder
		Debris:AddItem(parent, 3)
	end
	Shared.PlaySound(Shared.RandomSound(Shared.Sounds.Break), parent, who == player and 0.7 or 0.9, 0.95 + math.random() * 0.15)
end)
```
