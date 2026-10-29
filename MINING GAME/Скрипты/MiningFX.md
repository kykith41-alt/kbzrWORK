---
тип: ModuleScript
где: ReplicatedStorage
система: "[[Эффекты]]"
tags: [скрипт, ModuleScript]
---
# MiningFX

**Тип:** ModuleScript · **Где:** `ReplicatedStorage` · **Система:** [[Эффекты]]

Визуальные эффекты удара и разрушения: тряска визуальной копии блока, осколки (в группе `MiningChips`), пыль и блики при разрушении (без кубиков), полоска HP над блоком.

## Заметки
- HP-полоска: `BAR_SIZE 2.2×0.3`, `BAR_GAP 0.35`, прячется через 10 с без ударов.
- Осколки не сталкиваются с игроками (см. [[CollisionSetup]]).

## Связано
- [[MiningEffects]]
- [[PickaxeClient]]
- [[PickaxeSheath]]
- [[MiningShared]]
- [[CollisionSetup]]

## Код
```lua
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")
local PhysicsService = game:GetService("PhysicsService")

local Shared = require(script.Parent:WaitForChild("MiningShared"))

local MiningFX = {}

local CHIPS_GROUP = "MiningChips" -- регистрирует сервер (CollisionSetup): осколки не толкают игроков

local fxFolder = workspace:FindFirstChild("LocalMiningFX") or Instance.new("Folder")
fxFolder.Name = "LocalMiningFX"
fxFolder.Parent = workspace

local function anchorAt(position)
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Transparency = 1
	p.Size = Vector3.one * 0.1
	p.Position = position
	p.Parent = fxFolder
	Debris:AddItem(p, 2)
	return p
end

local function emitter(parent, props)
	local e = Instance.new("ParticleEmitter")
	e.Rate = 0
	e.LockedToPart = false
	for k, v in pairs(props) do e[k] = v end
	e.Parent = parent
	return e
end

local function seq(...)
	local pts = {}
	local args = { ... }
	for i = 1, #args, 2 do table.insert(pts, NumberSequenceKeypoint.new(args[i], args[i + 1])) end
	return NumberSequence.new(pts)
end


------------------------------------------------------------------ тряска блока: трясётся копия, настоящий блок стоит на месте

local basePivot = setmetatable({}, { __mode = "k" })
local shakeToken = setmetatable({}, { __mode = "k" })
local shakeVisual = setmetatable({}, { __mode = "k" }) -- [model] = копия, которая трясётся вместо него

local function setHidden(model, hidden)
	for _, d in ipairs(model:GetDescendants()) do
		if d:IsA("BasePart") then d.LocalTransparencyModifier = hidden and 1 or 0 end
	end
end

-- видимая копия блока без физики: двигаем её, а настоящий блок (по которому ходит игрок) не трогаем
local function makeVisual(model, base)
	local clone = model:Clone()
	for _, d in ipairs(clone:GetDescendants()) do
		if d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
		elseif d:IsA("BillboardGui") or d:IsA("Highlight") or d:IsA("BaseScript") then
			d:Destroy()
		end
	end
	clone:PivotTo(base)
	clone.Parent = fxFolder
	setHidden(model, true)
	return clone
end

local function endShake(model)
	local clone = shakeVisual[model]
	shakeVisual[model] = nil
	if clone then clone:Destroy() end
	if model.Parent then setHidden(model, false) end
end

function MiningFX.Shake(model, strength)
	if not model or not model.Parent then return end
	strength = strength or 1
	if not basePivot[model] then basePivot[model] = model:GetPivot() end
	local base = basePivot[model]
	local clone = shakeVisual[model]
	if not clone or not clone.Parent then
		clone = makeVisual(model, base)
		shakeVisual[model] = clone
	end
	local token = {}
	shakeToken[model] = token
	local start = os.clock()
	local conn
	conn = RunService.RenderStepped:Connect(function()
		if shakeToken[model] ~= token then conn:Disconnect() return end
		if not model.Parent then
			conn:Disconnect()
			endShake(model)
			return
		end
		local t = (os.clock() - start) / 0.22
		if t >= 1 then
			conn:Disconnect()
			endShake(model)
			return
		end
		local a = (1 - t) * 0.2 * strength
		clone:PivotTo(base * CFrame.new((math.random() - 0.5) * a, -math.sin(t * math.pi) * 0.14 * strength, (math.random() - 0.5) * a)
			* CFrame.Angles((math.random() - 0.5) * a * 0.4, (math.random() - 0.5) * a * 0.4, (math.random() - 0.5) * a * 0.4))
	end)
end

function MiningFX.BasePivot(model)
	return basePivot[model] or model:GetPivot()
end


------------------------------------------------------------------ осколки

local chipsGroupReady = false
pcall(function() chipsGroupReady = PhysicsService:IsCollisionGroupRegistered(CHIPS_GROUP) end)

function MiningFX.Chips(origin: CFrame, def, count, power, size)
	for n = 1, count do
		local p = Instance.new("Part")
		local s = size * (0.6 + math.random() * 0.8)
		p.Size = Vector3.new(s, s, s)
		p.Material = (n % 3 == 0 and def.glow) and Enum.Material.Neon or Enum.Material.SmoothPlastic
		p.Color = n % 3 == 0 and def.ore or def.color
		p.CFrame = origin * CFrame.new((math.random() - 0.5) * 1.5, (math.random() - 0.5) * 1.5, (math.random() - 0.5) * 1.5)
			* CFrame.Angles(math.random() * 6, math.random() * 6, math.random() * 6)
		p.CanQuery = false
		p.CanTouch = false
		p.CastShadow = false
		p.Massless = true
		-- осколки падают на землю, но игрока не толкают
		if chipsGroupReady then
			p.CollisionGroup = CHIPS_GROUP
		else
			p.CanCollide = false
		end
		p.Parent = fxFolder
		local dir = p.Position - origin.Position
		dir = dir.Magnitude > 0.01 and dir.Unit or Vector3.yAxis
		p.AssemblyLinearVelocity = dir * power * (0.6 + math.random() * 0.6) + Vector3.new(0, power * 0.9, 0)
		p.AssemblyAngularVelocity = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 25
		task.delay(0.55 + math.random() * 0.35, function()
			if p.Parent then
				TweenService:Create(p, TweenInfo.new(0.3), { Size = Vector3.one * 0.05, Transparency = 1 }):Play()
			end
		end)
		Debris:AddItem(p, 1.3)
	end
end


function MiningFX.Impact(model, hitPos: Vector3, crit: boolean?)
	local def = Shared.BlockByName[model:GetAttribute("BlockType")] or Shared.Blocks[1]
	local a = anchorAt(hitPos)
	local img = Shared.Images


	local sparks = emitter(a, {
		Texture = img.FxSpark,
		Color = ColorSequence.new(Color3.fromRGB(255, 250, 220), Color3.fromRGB(255, 190, 80)),
		LightEmission = 1,
		Orientation = Enum.ParticleOrientation.VelocityParallel,
		Size = seq(0, 0.35, 1, 0),
		Lifetime = NumberRange.new(0.18, 0.32),
		Speed = NumberRange.new(18, 34),
		SpreadAngle = Vector2.new(70, 70),
		Acceleration = Vector3.new(0, -60, 0),
		Drag = 4,
		EmissionDirection = Enum.NormalId.Top,
	})
	sparks:Emit(crit and 22 or 13)


	local dust = emitter(a, {
		Texture = img.FxDust,
		Color = ColorSequence.new(def.color:Lerp(Color3.new(1, 1, 1), 0.25)),
		LightInfluence = 1,
		Size = seq(0, 0.6, 1, 2.2),
		Transparency = seq(0, 0.35, 1, 1),
		Lifetime = NumberRange.new(0.45, 0.7),
		Speed = NumberRange.new(2, 6),
		SpreadAngle = Vector2.new(80, 80),
		Rotation = NumberRange.new(0, 360),
		RotSpeed = NumberRange.new(-90, 90),
		Drag = 3,
		Acceleration = Vector3.new(0, 2, 0),
		EmissionDirection = Enum.NormalId.Top,
	})
	dust:Emit(crit and 9 or 6)


	local star = emitter(a, {
		Texture = img.FxStar,
		Color = ColorSequence.new(crit and Color3.fromRGB(255, 200, 90) or Color3.new(1, 1, 1)),
		LightEmission = 1,
		Size = seq(0, crit and 2.6 or 1.8, 1, 0),
		Lifetime = NumberRange.new(0.14),
		Speed = NumberRange.new(0),
		Rotation = NumberRange.new(0, 45),
		ZOffset = 1,
	})
	star:Emit(1)


	local ring = emitter(a, {
		Texture = img.FxRing,
		Color = ColorSequence.new(Color3.new(1, 1, 1)),
		LightEmission = 0.6,
		Size = seq(0, 0.4, 1, crit and 4 or 3),
		Transparency = seq(0, 0.2, 1, 1),
		Lifetime = NumberRange.new(0.22),
		Speed = NumberRange.new(0),
	})
	ring:Emit(1)

	MiningFX.Chips(CFrame.new(hitPos), def, crit and 6 or 4, 13, 0.28)
	MiningFX.Shake(model, crit and 1.4 or 1)

	-- белая вспышка — на трясущейся копии (настоящий блок в это время спрятан)
	local hl = Instance.new("Highlight")
	hl.FillColor = Color3.new(1, 1, 1)
	hl.FillTransparency = 0.35
	hl.OutlineTransparency = 1
	hl.DepthMode = Enum.HighlightDepthMode.Occluded
	hl.Parent = shakeVisual[model] or model
	TweenService:Create(hl, TweenInfo.new(0.14), { FillTransparency = 1 }):Play()
	Debris:AddItem(hl, 0.18)
end


-- разрушение: пыль и блёстки (разлетающихся кубиков больше нет — вместо них эффекты в скрипте эффектов)
function MiningFX.Break(cframe: CFrame, def)
	local a = anchorAt(cframe.Position)
	local dust = emitter(a, {
		Texture = Shared.Images.FxDust,
		Color = ColorSequence.new(def.color:Lerp(Color3.new(1, 1, 1), 0.2)),
		Size = seq(0, 1.5, 1, 4.5),
		Transparency = seq(0, 0.3, 1, 1),
		Lifetime = NumberRange.new(0.6, 0.9),
		Speed = NumberRange.new(4, 10),
		SpreadAngle = Vector2.new(180, 180),
		Rotation = NumberRange.new(0, 360),
		RotSpeed = NumberRange.new(-60, 60),
		Drag = 4,
	})
	dust:Emit(14)
	local glint = emitter(a, {
		Texture = Shared.Images.FxStar,
		Color = ColorSequence.new(def.ore:Lerp(Color3.new(1, 1, 1), 0.4)),
		LightEmission = 1,
		Size = seq(0, 0.6, 1, 0),
		Lifetime = NumberRange.new(0.4, 0.7),
		Speed = NumberRange.new(8, 16),
		SpreadAngle = Vector2.new(180, 180),
		Acceleration = Vector3.new(0, -20, 0),
	})
	glint:Emit(def.glow and 16 or 8)
end


------------------------------------------------------------------ полоска HP над блоком

local BAR_SIZE = UDim2.fromScale(2.2, 0.3) -- ширина и высота в стадах
local BAR_GAP = 0.35                       -- насколько выше верхней грани блока, стады
local BAR_HIDE_AFTER = 10                  -- через сколько секунд без ударов полоска пропадает

local GREEN = { Color3.fromRGB(120, 245, 70), Color3.fromRGB(56, 190, 30) }
local YELLOW = { Color3.fromRGB(255, 232, 70), Color3.fromRGB(232, 180, 0) }
local RED = { Color3.fromRGB(255, 96, 80), Color3.fromRGB(205, 36, 30) }

local function healthColors(ratio)
	local a, b, k
	if ratio >= 0.5 then
		a, b, k = YELLOW, GREEN, (ratio - 0.5) / 0.5
	else
		a, b, k = RED, YELLOW, math.clamp((ratio - 0.15) / 0.35, 0, 1)
	end
	return a[1]:Lerp(b[1], k), a[2]:Lerp(b[2], k)
end
local bars = setmetatable({}, { __mode = "k" })

local function getBar(model)
	local bar = bars[model]
	if bar and bar.gui.Parent then return bar end
	local main = model:FindFirstChild("Main")
	if not main then return nil end

	local gui = Instance.new("BillboardGui")
	gui.Name = "HealthBar"
	gui.Adornee = main
	gui.Size = BAR_SIZE
	-- прямо на верхней грани блока (от центра блока — половина его высоты + небольшой зазор)
	gui.StudsOffsetWorldSpace = Vector3.new(0, main.Size.Y / 2 + BAR_GAP, 0)
	gui.AlwaysOnTop = true
	gui.LightInfluence = 0
	gui.MaxDistance = 45
	gui.Parent = model

	local holder = Instance.new("Frame")
	holder.AnchorPoint = Vector2.new(0.5, 0.5)
	holder.Position = UDim2.fromScale(0.5, 0.5)
	holder.Size = UDim2.fromScale(1, 1)
	holder.BackgroundColor3 = Color3.fromRGB(42, 42, 46)
	holder.BorderSizePixel = 0
	holder.Parent = gui
	local scale = Instance.new("UIScale"); scale.Scale = 0; scale.Parent = holder

	local trail = Instance.new("Frame")
	trail.Name = "Trail"
	trail.Size = UDim2.fromScale(1, 1)
	trail.BackgroundColor3 = Color3.new(1, 1, 1)
	trail.BorderSizePixel = 0
	trail.ZIndex = 2
	trail.Parent = holder

	local fill = Instance.new("Frame")
	fill.Name = "Fill"
	fill.Size = UDim2.fromScale(1, 1)
	fill.BackgroundColor3 = Color3.new(1, 1, 1)
	fill.BorderSizePixel = 0
	fill.ZIndex = 3
	fill.Parent = holder
	local grad = Instance.new("UIGradient")
	grad.Rotation = 90
	grad.Color = ColorSequence.new(GREEN[1], GREEN[2])
	grad.Parent = fill


	local flash = Instance.new("Frame")
	flash.Size = UDim2.fromScale(1, 1)
	flash.BackgroundColor3 = Color3.new(1, 1, 1)
	flash.BackgroundTransparency = 1
	flash.BorderSizePixel = 0
	flash.ZIndex = 4
	flash.Parent = fill

	bar = { gui = gui, holder = holder, scale = scale, trail = trail, fill = fill, grad = grad, flash = flash, ratio = 1, shown = false, hitAt = 0 }
	bars[model] = bar
	return bar
end

-- блок давно не били — полоска плавно сжимается и пропадает; новый удар снова её покажет
local function scheduleHide(bar)
	local stamp = os.clock()
	bar.hitAt = stamp
	task.delay(BAR_HIDE_AFTER, function()
		if bar.hitAt ~= stamp or not bar.shown or not bar.gui.Parent then return end
		bar.shown = false
		TweenService:Create(bar.scale, TweenInfo.new(0.25, Enum.EasingStyle.Back, Enum.EasingDirection.In), { Scale = 0 }):Play()
	end)
end

local function setHealth(model, hp, maxHp)
	local bar = getBar(model)
	if not bar or not maxHp or maxHp <= 0 then return end
	local ratio = math.clamp(hp / maxHp, 0, 1)
	bar.grad.Color = ColorSequence.new(healthColors(ratio))
	if ratio >= bar.ratio then

		bar.ratio = ratio
		bar.fill.Size = UDim2.fromScale(ratio, 1)
		if bar.trail.Size.X.Scale < ratio then bar.trail.Size = UDim2.fromScale(ratio, 1) end
		return
	end
	if not bar.shown then
		bar.shown = true
		TweenService:Create(bar.scale, TweenInfo.new(0.25, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	else
		bar.scale.Scale = 1.12
		TweenService:Create(bar.scale, TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	end
	scheduleHide(bar)
	bar.ratio = ratio

	bar.fill.Size = UDim2.fromScale(ratio, 1)
	bar.flash.BackgroundTransparency = 0.2
	TweenService:Create(bar.flash, TweenInfo.new(0.15), { BackgroundTransparency = 1 }):Play()
	TweenService:Create(bar.trail, TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out, 0, false, 0.22), { Size = UDim2.fromScale(ratio, 1) }):Play()
end


local function applyTruth(model, bar)
	local hp, maxHp = model:GetAttribute("HP"), model:GetAttribute("MaxHP")
	if hp and maxHp and model.Parent then setHealth(model, hp, maxHp) end
end

function MiningFX.PredictDamage(model, damage)
	local bar = getBar(model)
	if not bar then return end
	local maxHp = model:GetAttribute("MaxHP")
	local hp = bar.predicted or model:GetAttribute("HP")
	if not (hp and maxHp) then return end
	bar.predicted = math.max(hp - damage, 0)
	bar.pending = (bar.pending or 0) + 1
	local stamp = os.clock()
	bar.lastPredict = stamp
	setHealth(model, bar.predicted, maxHp)

	task.delay(0.8, function()
		if bar.lastPredict == stamp and (bar.pending or 0) > 0 then
			bar.pending = 0
			bar.predicted = nil
			applyTruth(model, bar)
		end
	end)
end


function MiningFX.ServerHealth(model)
	local hp, maxHp = model:GetAttribute("HP"), model:GetAttribute("MaxHP")
	if not (hp and maxHp) or hp >= maxHp then return end
	local bar = getBar(model)
	if not bar then return end
	bar.pending = math.max((bar.pending or 0) - 1, 0)
	if bar.pending > 0 and bar.predicted then

		if hp < bar.predicted then
			bar.predicted = hp
			setHealth(model, hp, maxHp)
		end
		return
	end
	bar.predicted = nil
	setHealth(model, hp, maxHp)
end


function MiningFX.Glint(position: Vector3, color: Color3?)
	local a = anchorAt(position)
	local img = Shared.Images
	local star = emitter(a, {
		Texture = img.FxStar,
		Color = ColorSequence.new(color or Color3.fromRGB(220, 240, 255)),
		LightEmission = 1,
		Size = seq(0, 0.4, 0.3, 2.4, 1, 0),
		Lifetime = NumberRange.new(0.32),
		Speed = NumberRange.new(0),
		Rotation = NumberRange.new(0, 90),
		RotSpeed = NumberRange.new(180),
		ZOffset = 1,
	})
	star:Emit(1)
	local sparks = emitter(a, {
		Texture = img.FxSpark,
		Color = ColorSequence.new(Color3.fromRGB(255, 255, 255), Color3.fromRGB(150, 220, 255)),
		LightEmission = 1,
		Orientation = Enum.ParticleOrientation.VelocityParallel,
		Size = seq(0, 0.25, 1, 0),
		Lifetime = NumberRange.new(0.2, 0.35),
		Speed = NumberRange.new(10, 18),
		SpreadAngle = Vector2.new(180, 180),
		Drag = 5,
	})
	sparks:Emit(10)
end

return MiningFX
```
