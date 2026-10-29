---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Интерфейс]]"
tags: [скрипт, LocalScript]
---
# CapacityOrb

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Интерфейс]]

3D-шар вместимости: стеклянная сфера в лианах, внутри последний добытый блок, снизу полоска заполнения. Летит за игроком, размер GUI статичный при отдалении камеры.

## Заметки
- Звук collect — список, `PlaySound` сам выбирает случайный.
- При новом уровне шар 2 с «танцует» вокруг игрока (круг, прыжки, вращение) и возвращается на место. Настройки: `DANCE_TIME`, `DANCE_TURNS`, `DANCE_RADIUS`, `DANCE_HOPS`, `DANCE_HOP_HEIGHT`.

## Связано
- [[MiningShared]]
- [[MineServer]]
- [[MiningHUD]]
- [[LevelUpFX]]
- [[Звуки]]

## Код
```lua
-- 3D-шар вместимости: стеклянная сфера в лианах, внутри последний добытый блок, снизу полоска заполнения.
-- Летит за игроком на пружине, смотрит на камеру, наклоняется по ходу, листья колышутся.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local Remotes = ReplicatedStorage:WaitForChild("Remotes")
local player = Players.LocalPlayer

local SCALE = 1.3                               -- кольцо лианы радиусом 1 стад * SCALE
local GLASS_RADIUS = 0.95
local FOLLOW_OFFSET = Vector3.new(3.6, 3.0, 2.0) -- справа-сзади над плечом
local BAR_W, BAR_H = 2.8, 0.3                   -- размер полоски в стадах (масштабируется вместе с шаром)
local DANCE_TIME = 2                            -- «танец» вокруг игрока при новом уровне, секунд
local DANCE_TURNS = 1                           -- сколько кругов вокруг игрока за танец (целое число)
local DANCE_RADIUS = 5                          -- радиус круга, стады
local DANCE_HOPS = 4                            -- сколько раз подпрыгивает за танец
local DANCE_HOP_HEIGHT = 1.4                    -- высота прыжка, стады

------------------------------------------------------------------ сборка модели

local orb = Instance.new("Model")
orb.Name = "CapacityOrb3D"

local parts = {} -- { part, relPivot, pivotToPart, baseSize, leaf, phase }
local function register(part, relPivot, pivotToPart, leaf)
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	table.insert(parts, {
		part = part, relPivot = relPivot, pivotToPart = pivotToPart or CFrame.identity,
		baseSize = part.Size, leaf = leaf, phase = math.random() * 6.28, flutter = 0,
	})
	part.Parent = orb
end

-- стекло
local glass = Instance.new("Part")
glass.Name = "Glass"
glass.Shape = Enum.PartType.Ball
glass.Size = Vector3.one * GLASS_RADIUS * 2
glass.Material = Enum.Material.SmoothPlastic
glass.Color = Color3.fromRGB(196, 232, 255)
glass.Transparency = 0.62
glass.Reflectance = 0.25
register(glass, CFrame.identity)

-- блик на стекле
local shine = Instance.new("Part")
shine.Name = "Shine"
shine.Shape = Enum.PartType.Ball
shine.Size = Vector3.new(0.22, 0.14, 0.14)
shine.Material = Enum.Material.Neon
shine.Color = Color3.new(1, 1, 1)
shine.Transparency = 0.25
register(shine, CFrame.new(-0.42, 0.5, 0.62) * CFrame.Angles(0, 0, math.rad(35)))

-- лиана и листья из Blender (MineAssets.Orb), если импортированы
local assets = ReplicatedStorage:FindFirstChild("MineAssets")
local orbAsset = assets and assets:FindFirstChild("Orb")
if orbAsset then
	local ref = orbAsset:GetPivot()
	for _, src in ipairs(orbAsset:GetChildren()) do
		if src:IsA("MeshPart") then
			local p = src:Clone()
			local pivot = src:GetPivot()
			register(p, ref:ToObjectSpace(pivot), pivot:ToObjectSpace(src.CFrame), src.Name:find("Leaf") ~= nil)
		end
	end
end

-- чёрная обводка силуэта стекла (Highlight не обводит полупрозрачные детали):
-- кольцо из тонких сегментов каждый кадр встаёт по силуэту сферы со стороны камеры
local camera = workspace.CurrentCamera
local RING_SEGMENTS = 40
local ringFolder = Instance.new("Folder")
ringFolder.Name = "CapacityOrbOutline"
ringFolder.Parent = workspace
local ringParts, ringCFrames = {}, {}
for i = 1, RING_SEGMENTS do
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Material = Enum.Material.SmoothPlastic
	p.Color = Color3.fromRGB(8, 14, 8)
	p.Size = Vector3.new(0.1, 0.05, 0.01)
	p.Parent = ringFolder
	ringParts[i] = p
	ringCFrames[i] = CFrame.identity
end
local ringVisible = true
local lastWidth, lastLen = -1, -1
local function setRingVisible(v)
	if v == ringVisible then return end
	ringVisible = v
	for _, p in ipairs(ringParts) do p.Transparency = v and 0 or 1 end
end
local function updateOutline(center, radius)
	local camPos = camera.CFrame.Position
	local toCam = camPos - center
	local dist = toCam.Magnitude
	if dist <= radius * 1.1 then setRingVisible(false) return end
	setRingVisible(true)
	-- силуэт сферы в перспективе: окружность чуть ближе к камере и чуть меньше радиуса
	local offset = radius * radius / dist
	local r = radius * math.sqrt(1 - (radius / dist) ^ 2)
	local basis = CFrame.lookAt(center + toCam / dist * offset, camPos)
	-- толщина ~3 пикселя на экране
	local pxWorld = 2 * dist * math.tan(math.rad(camera.FieldOfView) / 2) / camera.ViewportSize.Y
	local width = math.clamp(pxWorld * 3, 0.015, 0.25)
	local segLen = 2 * math.pi * (r + width / 2) / RING_SEGMENTS * 1.1
	if math.abs(width - lastWidth) > 0.004 or math.abs(segLen - lastLen) > 0.004 then
		lastWidth, lastLen = width, segLen
		for _, p in ipairs(ringParts) do p.Size = Vector3.new(segLen, width, 0.01) end
	end
	for i = 1, RING_SEGMENTS do
		local ang = (i - 0.5) / RING_SEGMENTS * math.pi * 2
		ringCFrames[i] = basis * CFrame.Angles(0, 0, ang) * CFrame.new(0, r + width / 2, 0)
	end
	workspace:BulkMoveTo(ringParts, ringCFrames, Enum.BulkMoveMode.FireCFrameChanged)
end

local outline = Instance.new("Highlight")
outline.FillTransparency = 1
outline.OutlineColor = Color3.fromRGB(10, 20, 8)
outline.OutlineTransparency = 0
outline.DepthMode = Enum.HighlightDepthMode.Occluded
outline.Adornee = orb
outline.Parent = orb

orb.Parent = workspace

-- блок внутри
local blockModel
local blockParts = {}
local blockSpinStart = 0
local function showBlock(typeName, animate)
	if blockModel then blockModel:Destroy() blockModel = nil end
	table.clear(blockParts)
	local def = Shared.BlockByName[typeName]
	if not def then return end
	blockModel = Shared.MakeBlockModel(def, 0.9, 3)
	local center = blockModel:GetPivot()
	for _, p in ipairs(blockModel:GetDescendants()) do
		if p:IsA("BasePart") then
			p.CanCollide = false; p.CanQuery = false; p.CanTouch = false; p.CastShadow = false
			table.insert(blockParts, { part = p, rel = center:ToObjectSpace(p.CFrame), size = p.Size })
		end
	end
	blockModel.Parent = orb
	if animate then blockSpinStart = os.clock() end
end

-- полоска вместимости на нижнем краю шара: полупрозрачная серая капсула, тонкая чёрная обводка,
-- тёмно-зелёная заливка, жирный белый текст с чёрной обводкой
local STROKE_COLOR = Color3.fromRGB(0, 0, 0)
local barGui = Instance.new("BillboardGui")
barGui.Name = "CapacityBar"
barGui.Adornee = glass
barGui.Size = UDim2.fromScale(BAR_W, BAR_H) -- Scale у BillboardGui = стады: полоска масштабируется вместе с шаром
barGui.StudsOffsetWorldSpace = Vector3.new(0, -SCALE * 0.98, 0)
barGui.LightInfluence = 0
barGui.AlwaysOnTop = true -- шар никогда не перекрывает полоску
barGui.ResetOnSpawn = false
barGui.Parent = player:WaitForChild("PlayerGui")
local bar = Instance.new("Frame")
bar.Size = UDim2.fromScale(1, 1)
bar.BackgroundColor3 = Color3.new(1, 1, 1)
bar.BackgroundTransparency = 0.45 -- сквозь фон видно шар и мир
bar.BorderSizePixel = 0
bar.Parent = barGui
Instance.new("UICorner", bar).CornerRadius = UDim.new(0.2, 0)
local barBg = Instance.new("UIGradient")
barBg.Rotation = 90
barBg.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(225, 225, 225)),
	ColorSequenceKeypoint.new(0.4, Color3.fromRGB(220, 220, 220)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(150, 150, 150)),
})
barBg.Parent = bar
local barStroke = Instance.new("UIStroke")
barStroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
barStroke.Thickness = 1.5
barStroke.Color = STROKE_COLOR
barStroke.Parent = bar
local fill = Instance.new("Frame")
fill.Size = UDim2.fromScale(0, 1)
fill.BackgroundColor3 = Color3.new(1, 1, 1)
fill.BorderSizePixel = 0
fill.Parent = bar
Instance.new("UICorner", fill).CornerRadius = UDim.new(0.2, 0)
local fillGrad = Instance.new("UIGradient"); fillGrad.Rotation = 90; fillGrad.Parent = fill
local barText = Instance.new("TextLabel")
barText.BackgroundTransparency = 1
barText.AnchorPoint = Vector2.new(0.5, 0.5)
barText.Position = UDim2.fromScale(0.5, 0.52)
barText.Size = UDim2.fromScale(1, 1.25) -- цифры почти во всю высоту полоски
barText.FontFace = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.ExtraBold)
barText.TextScaled = true -- размер текста следует за размером полоски
barText.TextColor3 = Color3.new(1, 1, 1)
barText.ZIndex = 3
barText.Parent = bar
local ts = Instance.new("UIStroke"); ts.Thickness = 1.5; ts.Color = STROKE_COLOR; ts.Parent = barText


------------------------------------------------------------------ состояние

-- верх ровный, к низу темнеет
local function barColors(top, bottom)
	return ColorSequence.new({
		ColorSequenceKeypoint.new(0, top),
		ColorSequenceKeypoint.new(0.45, top),
		ColorSequenceKeypoint.new(1, bottom),
	})
end
local GREEN = barColors(Color3.fromRGB(8, 125, 24), Color3.fromRGB(5, 84, 16))
local RED = barColors(Color3.fromRGB(190, 24, 24), Color3.fromRGB(125, 12, 12))
local shownCount = player:GetAttribute("Blocks") or 0
local pending = 0
local bounceStart = -10   -- упругое «раздувание» при сборе
local shakeUntil = 0
local danceStart = -10   -- «танец» вокруг игрока при новом уровне

local function refreshBar(animate)
	local max = player:GetAttribute("MaxCapacity") or Shared.MAX_CAPACITY
	local ratio = math.clamp(shownCount / max, 0, 1)
	fillGrad.Color = ratio >= 1 and RED or GREEN
	fill.Visible = ratio > 0
	local goal = UDim2.fromScale(ratio, 1)
	if animate then
		TweenService:Create(fill, TweenInfo.new(0.35, Enum.EasingStyle.Quart, Enum.EasingDirection.Out), { Size = goal }):Play()
	else
		fill.Size = goal
	end
	barText.Text = shownCount .. "/" .. max
end

-- зелёные искры-листочки при сборе
local function leafBurst(center)
	for i = 1, 10 do
		local p = Instance.new("Part")
		p.Size = Vector3.new(0.22, 0.05, 0.14)
		p.Material = Enum.Material.Neon
		p.Color = i % 2 == 0 and Color3.fromRGB(120, 230, 90) or Color3.fromRGB(200, 255, 150)
		p.CanCollide = false; p.CanQuery = false; p.CanTouch = false; p.CastShadow = false
		p.Anchored = true
		local dir = Vector3.new(math.random() - 0.5, math.random() * 0.6 + 0.2, math.random() - 0.5).Unit
		p.CFrame = CFrame.new(center + dir * 1.2) * CFrame.Angles(math.random() * 6, math.random() * 6, math.random() * 6)
		p.Parent = workspace
		TweenService:Create(p, TweenInfo.new(0.55, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
			CFrame = CFrame.new(center + dir * 3.2) * CFrame.Angles(math.random() * 6, math.random() * 6, math.random() * 6),
			Transparency = 1, Size = Vector3.new(0.05, 0.02, 0.04),
		}):Play()
		Debris:AddItem(p, 0.6)
	end
end


-- кубик летит по дуге из разбитого блока в шар
local function flyToOrb(typeName, fromCF, onArrive)
	local def = Shared.BlockByName[typeName]
	local cube = Shared.MakeBlockModel(def, 1.2, 5)
	for _, p in ipairs(cube:GetDescendants()) do
		if p:IsA("BasePart") then p.CanCollide = false; p.CanQuery = false; p.CanTouch = false; p.CastShadow = false end
	end
	local start = fromCF.Position
	cube:PivotTo(CFrame.new(start))
	cube.Parent = workspace
	local side = (math.random() - 0.5) * 6
	local t0 = os.clock()
	local conn
	conn = RunService.RenderStepped:Connect(function()
		local t = math.min((os.clock() - t0) / 0.6, 1)
		local k = TweenService:GetValue(t, Enum.EasingStyle.Sine, Enum.EasingDirection.In)
		local target = glass.Position
		local ctrl = (start + target) / 2 + Vector3.new(side, 6, side * 0.4)
		local pos = start:Lerp(ctrl, k):Lerp(ctrl:Lerp(target, k), k)
		cube:PivotTo(CFrame.new(pos) * CFrame.Angles(t * 8, t * 11, t * 4))
		cube:ScaleTo(math.max(1 - k * 0.75, 0.05))
		if t >= 1 then
			conn:Disconnect()
			cube:Destroy()
			onArrive()
		end
	end)
end

Remotes.BlockBroken.OnClientEvent:Connect(function(who, typeName, cframe, amount)
	if who ~= player then return end
	for _ = 1, amount do
		pending += 1
		flyToOrb(typeName, cframe, function()
			pending -= 1
			shownCount = math.min(shownCount + 1, player:GetAttribute("Blocks") or shownCount + 1)
			showBlock(typeName, true)
			refreshBar(true)
			bounceStart = os.clock()
			for _, e in ipairs(parts) do
				if e.leaf then e.flutter = 1 end
			end
			leafBurst(glass.Position)
			local fullness = math.clamp(shownCount / (player:GetAttribute("MaxCapacity") or Shared.MAX_CAPACITY), 0, 1)
			Shared.PlaySound(Shared.Sounds.Collect, nil, 0.45, 0.95 + fullness * 0.35)
		end)
	end
end)

player:GetAttributeChangedSignal("Blocks"):Connect(function()
	local actual = player:GetAttribute("Blocks") or 0
	if actual < shownCount then
		shownCount = actual
		refreshBar(true)
	else
		task.delay(1.4, function()
			local now = player:GetAttribute("Blocks") or 0
			if pending == 0 and shownCount ~= now then
				shownCount = now
				refreshBar(true)
			end
		end)
	end
end)
player:GetAttributeChangedSignal("MaxCapacity"):Connect(function() refreshBar(true) end)

Remotes.Full.OnClientEvent:Connect(function()
	shakeUntil = os.clock() + 0.45
	glass.Color = Color3.fromRGB(255, 90, 90)
	TweenService:Create(glass, TweenInfo.new(0.6), { Color = Color3.fromRGB(196, 232, 255) }):Play()
	barStroke.Color = Color3.fromRGB(220, 40, 40)
	task.delay(0.5, function() barStroke.Color = STROKE_COLOR end)
end)

local lastLevel = player:GetAttribute("Level")
player:GetAttributeChangedSignal("Level"):Connect(function()
	local level = player:GetAttribute("Level")
	if lastLevel and level and level > lastLevel then
		danceStart = os.clock()
		for _, e in ipairs(parts) do
			if e.leaf then e.flutter = 1 end
		end
	end
	lastLevel = level
end)

showBlock(player:GetAttribute("LastBlock"), false)
refreshBar(false)

------------------------------------------------------------------ движение

local function scaled(cf, s)
	return CFrame.new(cf.Position * s) * cf.Rotation
end

local function smoother(x)
	return x * x * x * (x * (x * 6 - 15) + 10)
end

-- танец: круги вокруг игрока с прыжками; начинается и заканчивается ровно в обычном месте шара
local FOLLOW_FLAT = Vector3.new(FOLLOW_OFFSET.X, 0, FOLLOW_OFFSET.Z)
local function danceOffset(p)
	local e = smoother(p)
	local swell = math.sin(math.pi * p)
	local radius = FOLLOW_FLAT.Magnitude + (DANCE_RADIUS - FOLLOW_FLAT.Magnitude) * swell
	local flat = CFrame.Angles(0, e * DANCE_TURNS * 2 * math.pi, 0) * FOLLOW_FLAT.Unit * radius
	local hop = math.abs(math.sin(p * math.pi * DANCE_HOPS)) * DANCE_HOP_HEIGHT * swell
	return flat + Vector3.new(0, FOLLOW_OFFSET.Y + hop, 0)
end

local pos, vel = nil, Vector3.zero
local faceDir
RunService.RenderStepped:Connect(function(dt)
	dt = math.min(dt, 1 / 20)
	local character = player.Character
	local hrp = character and character:FindFirstChild("HumanoidRootPart")
	local t = os.clock()
	if not hrp then
		barGui.Enabled = false
		setRingVisible(false)
		return
	end
	barGui.Enabled = true

	-- пружина за игроком
	local dp = (t - danceStart) / DANCE_TIME
	local dancing = dp >= 0 and dp < 1
	local offset = dancing and danceOffset(dp) or FOLLOW_OFFSET
	local target = hrp.CFrame:PointToWorldSpace(offset) + Vector3.new(0, math.sin(t * 2.1) * 0.28, 0)
	if not pos or (pos - target).Magnitude > 50 then pos, vel = target, Vector3.zero end
	if dancing then
		-- в танце шар идёт точно по кругу, без отставания пружины
		local newPos = pos:Lerp(target, math.clamp(dp / 0.1, 0.25, 1))
		vel = (newPos - pos) / dt
		pos = newPos
	else
		local stiffness = 55
		local accel = (target - pos) * stiffness - vel * (2 * math.sqrt(stiffness) * 0.85)
		vel += accel * dt
		pos += vel * dt
	end

	-- смотрит на камеру, наклон по скорости, лёгкое покачивание
	-- разворот как у персонажа (лицом назад, к камере за спиной), плавно догоняет
	local fwd = hrp.CFrame.LookVector
	fwd = Vector3.new(fwd.X, 0, fwd.Z)
	faceDir = faceDir and faceDir:Lerp(fwd, 1 - math.exp(-dt * 4)) or fwd
	if faceDir.Magnitude < 0.05 then faceDir = fwd end
	local face = CFrame.lookAt(pos, pos + faceDir.Unit)
	local localVel = face:VectorToObjectSpace(vel)
	local roll = math.clamp(localVel.X * 0.05, -0.45, 0.45)
	local pitch = math.clamp(-localVel.Z * 0.03, -0.3, 0.3)
	local wobble = CFrame.Angles(math.sin(t * 1.3) * 0.06 + pitch, math.sin(t * 0.7) * 0.28, math.sin(t * 1.1) * 0.05 + roll)
	local shake = t < shakeUntil and CFrame.new((math.random() - 0.5) * 0.25, (math.random() - 0.5) * 0.25, 0) or CFrame.identity
	local danceSpin = dancing and CFrame.Angles(0, smoother(dp) * DANCE_TURNS * 4 * math.pi, math.sin(dp * math.pi * DANCE_HOPS * 2) * 0.25 * math.sin(math.pi * dp)) or CFrame.identity
	local root = face * shake * danceSpin * wobble

	-- упругое раздувание при сборе
	local bt = t - bounceStart
	local s = SCALE * (1 + (bt < 1.2 and math.exp(-bt * 6) * math.sin(bt * 22) * 0.22 or 0)) * (1 + math.sin(t * 2.4) * 0.012)
	if dancing then
		s *= 1 + math.sin(math.pi * dp) * (0.12 + math.abs(math.sin(dp * math.pi * DANCE_HOPS)) * 0.08)
	end

	for _, e in ipairs(parts) do
		local sway = CFrame.identity
		if e.leaf then
			e.flutter = math.max(0, e.flutter - dt * 1.6)
			local amp = 0.07 + e.flutter * 0.45
			sway = CFrame.Angles(math.sin(t * 2.3 + e.phase) * amp, 0, math.sin(t * 1.7 + e.phase * 1.3) * amp * 0.8)
		end
		local pivot = root * scaled(e.relPivot, s) * sway
		e.part.Size = e.baseSize * s
		e.part.CFrame = pivot * scaled(e.pivotToPart, s)
	end

	updateOutline(glass.Position, GLASS_RADIUS * s)

	-- обводка полоски и текста в пикселях: подгоняем под текущий размер полоски на экране
	local camDist = (camera.CFrame.Position - glass.Position).Magnitude
	local pxPerStud = camera.ViewportSize.Y / (2 * camDist * math.tan(math.rad(camera.FieldOfView) / 2))
	local barPx = BAR_H * pxPerStud
	barStroke.Thickness = math.max(barPx * 0.065, 1)
	ts.Thickness = math.max(barPx * 0.06, 1)

	-- блок внутри: медленно вращается, после сбора раскручивается
	if blockModel then
		local since = t - blockSpinStart
		local spin = since < 0.8 and (1 - since / 0.8) ^ 2 * 10 or 0
		local pop = since < 0.5 and TweenService:GetValue(since / 0.5, Enum.EasingStyle.Back, Enum.EasingDirection.Out) or 1
		local bs = s * pop
		local center = root * CFrame.new(0, math.sin(t * 1.9) * 0.05 * s, 0)
			* CFrame.Angles(math.rad(-18), t * 0.9 + spin, math.rad(12))
		for _, b in ipairs(blockParts) do
			b.part.Size = b.size * bs
			b.part.CFrame = center * scaled(b.rel, bs)
		end
	end
end)
```
