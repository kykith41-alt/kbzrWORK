---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Система шахты]]"
tags: [скрипт, LocalScript]
---
# MineRangeRing

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Система шахты]]

Радиус атаки: белый пунктирный круг на земле и светлая заливка (прозрачность 0.8), только в зоне копания. Лежит на высоте верхнего слоя блоков.

## Заметки
- Радиус = `Shared.MINE_RANGE - 1`.

## Связано
- [[MiningShared]]
- [[PickaxeClient]]

## Код
```lua
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local player = Players.LocalPlayer

local RADIUS = Shared.MINE_RANGE - 1
local DASHES = 70
local DASH_FILL = 0.5
local DASH_WIDTH = 0.35
local DASH_HEIGHT = 0.08
local SPIN = 0.15
local FADE_SPEED = 6
local DASH_ALPHA = 0.05
local FILL_ALPHA = 0.92


local ZONE_MARGIN = 1
local ZONE_TOP = 7
local zoneMin, zoneMax, surfaceY
local function updateZone()
	local area = workspace:FindFirstChild("Mine") and workspace.Mine:FindFirstChild("MineArea")
	if area then
		local half = area.Size / 2
		zoneMin = area.Position - half - Vector3.new(ZONE_MARGIN, 10, ZONE_MARGIN)
		zoneMax = area.Position + half + Vector3.new(ZONE_MARGIN, ZONE_TOP, ZONE_MARGIN)
		surfaceY = area.Position.Y + half.Y
	else
		local M = Shared.Mine
		zoneMin = Vector3.new(M.ORIGIN.X - ZONE_MARGIN, M.ORIGIN.Y - M.L * M.CELL - 10, M.ORIGIN.Z - ZONE_MARGIN)
		zoneMax = Vector3.new(M.ORIGIN.X + M.W * M.CELL + ZONE_MARGIN, M.ORIGIN.Y + ZONE_TOP, M.ORIGIN.Z + M.D * M.CELL + ZONE_MARGIN)
		surfaceY = M.ORIGIN.Y
	end
end
updateZone()
task.delay(3, updateZone)

local function inMineZone(pos)
	return pos.X >= zoneMin.X and pos.X <= zoneMax.X
		and pos.Y >= zoneMin.Y and pos.Y <= zoneMax.Y
		and pos.Z >= zoneMin.Z and pos.Z <= zoneMax.Z
end


local folder = Instance.new("Folder")
folder.Name = "MineRangeRing"
folder.Parent = workspace

local function makePart(shape)
	local p = Instance.new("Part")
	p.Shape = shape or Enum.PartType.Block
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Material = Enum.Material.Neon
	p.Color = Color3.new(1, 1, 1)
	p.Transparency = 1
	p.Parent = folder
	return p
end

local dashLength = 2 * math.pi * RADIUS / DASHES * DASH_FILL
local dashes, dashCFrames = {}, {}
for i = 1, DASHES do
	local p = makePart()
	p.Size = Vector3.new(DASH_WIDTH, DASH_HEIGHT, dashLength)
	dashes[i] = p
	dashCFrames[i] = CFrame.identity
end

local fill = makePart(Enum.PartType.Cylinder)
fill.Material = Enum.Material.SmoothPlastic
fill.Size = Vector3.new(0.04, RADIUS * 2, RADIUS * 2)

local alpha = 0
local shownAlpha = -1

RunService.RenderStepped:Connect(function(dt)
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	local target = (root and inMineZone(root.Position)) and 1 or 0
	alpha += (target - alpha) * math.min(dt * FADE_SPEED, 1)
	if math.abs(alpha - target) < 0.01 then alpha = target end

	if alpha <= 0 or not root then
		if shownAlpha ~= 0 then
			for _, p in ipairs(dashes) do p.Transparency = 1 end
			fill.Transparency = 1
			shownAlpha = 0
		end
		return
	end

	local center = Vector3.new(root.Position.X, surfaceY + 0.06, root.Position.Z)

	local r = RADIUS * (0.85 + 0.15 * alpha)
	local spin = os.clock() * SPIN
	for i = 1, DASHES do
		local ang = spin + (i - 1) / DASHES * math.pi * 2
		local pos = center + Vector3.new(math.cos(ang) * r, 0, math.sin(ang) * r)
		local tangent = Vector3.new(-math.sin(ang), 0, math.cos(ang))
		dashCFrames[i] = CFrame.lookAt(pos, pos + tangent)
	end
	workspace:BulkMoveTo(dashes, dashCFrames, Enum.BulkMoveMode.FireCFrameChanged)
	fill.CFrame = CFrame.new(center - Vector3.new(0, 0.03, 0)) * CFrame.Angles(0, 0, math.rad(90))
	fill.Size = Vector3.new(0.04, r * 2, r * 2)

	if math.abs(alpha - shownAlpha) > 0.01 then
		local dashT = 1 - (1 - DASH_ALPHA) * alpha
		for _, p in ipairs(dashes) do p.Transparency = dashT end
		fill.Transparency = 1 - (1 - FILL_ALPHA) * alpha
		shownAlpha = alpha
	end
end)
```
