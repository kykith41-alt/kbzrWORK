---
тип: ModuleScript
где: ReplicatedStorage
система: "[[Система шахты]]"
tags: [скрипт, ModuleScript]
---
# MiningShared

**Тип:** ModuleScript · **Где:** `ReplicatedStorage` · **Система:** [[Система шахты]]

Общие настройки игры: вместимость рюкзака, урон, дальность удара, кап уровня, все ID звуков и картинок, список блоков (HP, цена, опыт, глубина), формула опыта, `PlaySound` и `WorldStatic` для надписей над головой.

## Заметки
- Скорость звуков по группам: `Shared.SoundSpeed` (шаги на 0.8).
- `PlaySound` принимает и один ID, и список (берёт случайный).
- `WorldStatic` — надписи над головой одного размера в мире при отдалении камеры.
- У Stone `spots = false` — без мешей руды.

## Связано
- [[MineServer]]
- [[MiningFX]]
- [[MiningEffects]]
- [[MiningHUD]]
- [[LevelBar]]
- [[CapacityOrb]]
- [[PickaxeClient]]
- [[PickaxeSheath]]
- [[Nameplates]]
- [[MineRangeRing]]
- [[FootstepSounds]]
- [[WeatherClient]]

## Код
```lua
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = {}

Shared.MAX_CAPACITY = 50
Shared.SWING_TIME = 0.5
Shared.BASE_DAMAGE = 10
Shared.CRIT_CHANCE = 0.12
Shared.MINE_RANGE = 16
Shared.MAX_LEVEL = 35

Shared.Sounds = {
	Swing = "rbxassetid://9120972321",
	Hit = { "rbxassetid://132928849005488", "rbxassetid://93983700233677", "rbxassetid://132875216872180" },
	Break = { "rbxassetid://77663289183610", "rbxassetid://116019985061436" },
	Collect = { "rbxassetid://76663463555301", "rbxassetid://82696495986588", "rbxassetid://125592843777396" },
	Footsteps = {
		"rbxassetid://93803555891980", "rbxassetid://85682518019906",
		"rbxassetid://80346333847986", "rbxassetid://140594308250996", "rbxassetid://82615619091463",
	},
	Jump = "rbxassetid://117660523052559",
	Land = "rbxassetid://76529964789209",
	Draw = "rbxassetid://9116651688",
}

Shared.SoundSpeed = {
	Footsteps = 0.8,
}


local soundTemplates = {}
local soundGroup = {}
for group, v in pairs(Shared.Sounds) do
	if type(v) == "table" then
		for _, id in ipairs(v) do soundGroup[id] = group end
	else
		soundGroup[v] = group
	end
end

function Shared.PreloadSounds()
	local SoundService = game:GetService("SoundService")
	local folder = SoundService:FindFirstChild("MiningSounds") or Instance.new("Folder")
	folder.Name = "MiningSounds"
	folder.Parent = SoundService
	local list = {}
	local function add(id)
		if soundTemplates[id] then return end
		local s = Instance.new("Sound")
		s.SoundId = id
		s.Parent = folder
		soundTemplates[id] = s
		table.insert(list, s)
	end
	for _, v in pairs(Shared.Sounds) do
		if type(v) == "table" then
			for _, id in ipairs(v) do add(id) end
		else
			add(v)
		end
	end
	task.spawn(function()
		game:GetService("ContentProvider"):PreloadAsync(list)
	end)
end


function Shared.PlaySound(id, parent, volume, speed)
	if type(id) == "table" then
		id = Shared.RandomSound(id)
	end
	local group = soundGroup[id]
	local groupSpeed = group and Shared.SoundSpeed[group] or 1
	local template = soundTemplates[id]
	local s = template and template:Clone() or Instance.new("Sound")
	s.SoundId = id
	s.Volume = volume or 0.6
	s.PlaybackSpeed = (speed or 1) * groupSpeed
	s.RollOffMaxDistance = 90
	s.Parent = parent or game:GetService("SoundService")
	s:Play()
	s.Ended:Once(function() s:Destroy() end)
	task.delay(4, function() if s.Parent then s:Destroy() end end)
	return s
end

function Shared.RandomSound(list)
	return list[math.random(1, #list)]
end

Shared.Images = {
	OrbFrame = "rbxassetid://78645527217551",
	PickaxeHead = "rbxassetid://80132345738980",
	PickaxeSocket = "rbxassetid://125058433361760",
	PickaxeWood = "rbxassetid://88334422170769",
	FxSpark = "rbxassetid://88844888475075",
	FxDust = "rbxassetid://110677299514517",
	FxStar = "rbxassetid://135735857044237",
	FxRing = "rbxassetid://122093438565331",
}


Shared.Mine = {
	CELL = 4,
	W = 14,
	D = 14,
	L = 25,
	ORIGIN = Vector3.new(-28, 0, 22),
	RESET_AT = 0.35,
}

function Shared.CellPosition(i, j, k)
	local m = Shared.Mine
	return m.ORIGIN + Vector3.new(i * m.CELL + m.CELL / 2, -k * m.CELL - m.CELL / 2, j * m.CELL + m.CELL / 2)
end


Shared.Blocks = {
	{ name = "Stone",    display = "Stone",   hp = 20,  value = 1,  xp = 2,  weight = 60, minDepth = 0, spots = false,
		color = Color3.fromRGB(143, 76, 42),  ore = Color3.fromRGB(44, 58, 88),    glow = false },
	{ name = "Coal",     display = "Coal",    hp = 30,  value = 3,  xp = 5,  weight = 30, minDepth = 1,
		color = Color3.fromRGB(143, 76, 42), ore = Color3.fromRGB(30, 30, 36),    glow = false },
	{ name = "Copper",   display = "Copper",     hp = 45,  value = 6,  xp = 9,  weight = 22, minDepth = 4,
		color = Color3.fromRGB(143, 76, 42),  ore = Color3.fromRGB(228, 126, 64),  glow = false },
	{ name = "Iron",     display = "Iron",   hp = 65,  value = 10, xp = 15, weight = 16, minDepth = 8,
		color = Color3.fromRGB(143, 76, 42), ore = Color3.fromRGB(226, 212, 196), glow = false },
	{ name = "Gold",     display = "Gold",   hp = 90,  value = 20, xp = 28, weight = 10, minDepth = 12,
		color = Color3.fromRGB(143, 76, 42),    ore = Color3.fromRGB(255, 196, 40),  glow = true },
	{ name = "Crystal",  display = "Crystal", hp = 120, value = 35, xp = 45, weight = 7,  minDepth = 16,
		color = Color3.fromRGB(143, 76, 42),    ore = Color3.fromRGB(176, 190, 236), glow = false },
	{ name = "Amethyst", display = "Amethyst",  hp = 140, value = 45, xp = 60, weight = 6,  minDepth = 19,
		color = Color3.fromRGB(143, 76, 42),    ore = Color3.fromRGB(190, 96, 255),  glow = true },
	{ name = "Diamond",  display = "Diamond",    hp = 170, value = 60, xp = 80, weight = 5,  minDepth = 21,
		color = Color3.fromRGB(143, 76, 42),    ore = Color3.fromRGB(100, 236, 255), glow = true },
}
Shared.BlockByName = {}
for _, def in ipairs(Shared.Blocks) do
	Shared.BlockByName[def.name] = def
end


function Shared.XpToNext(level: number): number
	return math.floor(50 * level ^ 1.6)
end


function Shared.AddXP(player: Player, amount: number)
	if not amount or amount <= 0 then return end
	local level = player:GetAttribute("Level") or 1
	local xp = (player:GetAttribute("XP") or 0) + amount
	while level < Shared.MAX_LEVEL and xp >= Shared.XpToNext(level) do
		xp -= Shared.XpToNext(level)
		level += 1
	end
	if level >= Shared.MAX_LEVEL then xp = math.min(xp, Shared.XpToNext(level)) end
	player:SetAttribute("Level", level)
	player:SetAttribute("XP", xp)
end


function Shared.RollBlock(rng: Random, depth: number)
	local pool, total = {}, 0
	for _, def in ipairs(Shared.Blocks) do
		if depth >= def.minDepth then
			local w = def.weight
			if def.name == "Stone" then w = math.max(12, w - depth * 2) end
			table.insert(pool, { def = def, w = w })
			total += w
		end
	end
	local roll = rng:NextNumber(0, total)
	for _, e in ipairs(pool) do
		roll -= e.w
		if roll <= 0 then return e.def end
	end
	return pool[1].def
end


function Shared.SwingTime(player: Player): number
	return Shared.SWING_TIME / (player:GetAttribute("SwingSpeed") or 1)
end

local function spotTemplates()
	local assets = ReplicatedStorage:FindFirstChild("MineAssets")
	local list = {}
	if assets then
		for _, name in ipairs({ "Spots_A", "Spots_B", "Spots_C" }) do
			local m = assets:FindFirstChild(name)
			if m then table.insert(list, m) end
		end
	end
	return list
end


function Shared.MakeBlockModel(def, size: number, seed: number?)
	local rng = Random.new(seed or 1)
	local model = Instance.new("Model")
	model.Name = def.name
	local main = Instance.new("Part")
	main.Name = "Main"
	main.Size = Vector3.new(size, size, size)
	main.Material = Enum.Material.SmoothPlastic
	main.Color = def.color
	main.Anchored = true
	main.TopSurface = Enum.SurfaceType.Smooth
	main.BottomSurface = Enum.SurfaceType.Smooth
	main.Parent = model
	model.PrimaryPart = main

	local templates = def.spots == false and {} or spotTemplates()
	if #templates > 0 then
		local spots = templates[rng:NextInteger(1, #templates)]:Clone()
		spots.Name = "Ore"
		spots.Anchored = true
		spots.CanCollide = false
		spots.CanQuery = false
		spots.CanTouch = false
		spots.CastShadow = false
		spots.Material = def.glow and Enum.Material.Neon or Enum.Material.SmoothPlastic
		spots.Color = def.ore
		local ext = spots.Size
		spots.Size = ext * (size * 1.006 / math.max(ext.X, ext.Y, ext.Z))
		spots.CFrame = CFrame.Angles(0, math.rad(90 * rng:NextInteger(0, 3)), 0)
		spots.Parent = model
	end
	return model
end


local REF_PX_PER_STUD = 58
local worldGuis = {}
local worldConn

local function scaleUDim2(u, f)
	return UDim2.new(u.X.Scale, u.X.Offset * f, u.Y.Scale, u.Y.Offset * f)
end

local function updateWorldGuis()
	local camera = workspace.CurrentCamera
	if not camera then return end
	local camPos = camera.CFrame.Position
	local k = camera.ViewportSize.Y / (2 * math.tan(math.rad(camera.FieldOfView) / 2))
	for gui, e in pairs(worldGuis) do
		local adornee = gui.Adornee
		if not gui.Parent or not adornee or not adornee.Parent then
			worldGuis[gui] = nil
		else
			local pos = adornee.Position + gui.StudsOffsetWorldSpace
			local dist = math.max((camPos - pos).Magnitude, 0.5)
			local f = math.clamp(k / dist / REF_PX_PER_STUD, 0.05, 3.8)
			gui.Size = scaleUDim2(e.size, f)
			for _, it in ipairs(e.items) do
				local obj, prop, base = it[1], it[2], it[3]
				if typeof(base) == "UDim2" then
					obj[prop] = scaleUDim2(base, f)
				elseif typeof(base) == "UDim" then
					obj[prop] = UDim.new(base.Scale, base.Offset * f)
				else
					obj[prop] = math.max(base * f, prop == "TextSize" and 1 or 0)
				end
			end
		end
	end
end


function Shared.WorldStatic(gui: BillboardGui)
	local items = {}
	local function track(obj, prop)
		local v = obj[prop]
		if typeof(v) == "UDim2" and v.X.Offset == 0 and v.Y.Offset == 0 then return end
		if typeof(v) == "UDim" and v.Offset == 0 then return end
		table.insert(items, { obj, prop, v })
	end
	for _, d in ipairs(gui:GetDescendants()) do
		if d:IsA("GuiObject") then
			track(d, "Size")
			track(d, "Position")
			if d:IsA("TextLabel") or d:IsA("TextButton") then track(d, "TextSize") end
		elseif d:IsA("UIStroke") then
			track(d, "Thickness")
		elseif d:IsA("UIListLayout") then
			track(d, "Padding")
		end
	end
	worldGuis[gui] = { size = gui.Size, items = items }
	if not worldConn then
		worldConn = game:GetService("RunService").RenderStepped:Connect(updateWorldGuis)
	end
	updateWorldGuis()
end

return Shared
```
