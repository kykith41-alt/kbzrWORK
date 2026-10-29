---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Уровни и опыт]]"
tags: [скрипт, LocalScript]
---
# LevelUpFX

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Уровни и опыт]]

При повышении уровня (атрибут `Level`) включает на 1.5 с частицы из `ReplicatedStorage.Lvlup` на персонаже и сразу играет звук level up. Работает для всех игроков.

## Заметки
- Звук предзагружается при входе и клонируется — играет мгновенно.
- Если в начале самого аудио есть тишина, поставь `SOUND_START` (секунды), например `0.1`.
- Старый серверный `LevelUpFX` в ServerScriptService нужно удалить.

## Связано
- [[LevelBar]]
- [[CapacityOrb]]
- [[MiningShared]]
- [[Эффекты частиц]]
- [[Звуки]]

## Код
```lua
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local SoundService = game:GetService("SoundService")
local ContentProvider = game:GetService("ContentProvider")
local Debris = game:GetService("Debris")

local TEMPLATE = ReplicatedStorage:WaitForChild("Lvlup")
local SOUND_ID = "rbxassetid://99608180022223"
local SOUND_START = 0
local DURATION = 1.5
local VOLUME = 0.7

local soundTemplate = Instance.new("Sound")
soundTemplate.Name = "LevelUpSound"
soundTemplate.SoundId = SOUND_ID
soundTemplate.Volume = VOLUME
soundTemplate.RollOffMaxDistance = 90
soundTemplate.Parent = SoundService

local fxTemplate = TEMPLATE:Clone()

task.spawn(function()
	local list = { soundTemplate }
	for _, d in ipairs(fxTemplate:GetDescendants()) do
		if d:IsA("ParticleEmitter") then table.insert(list, d) end
	end
	ContentProvider:PreloadAsync(list)
end)

local function makeHolder(root)
	if fxTemplate:IsA("BasePart") then
		local part = fxTemplate:Clone()
		part.Anchored = false
		part.CanCollide = false
		part.CanQuery = false
		part.CanTouch = false
		part.Massless = true
		part.Transparency = 1
		part.CFrame = root.CFrame
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = root
		weld.Part1 = part
		weld.Parent = part
		part.Parent = root.Parent
		return part
	end

	local att = Instance.new("Attachment")
	att.Name = "Lvlup"
	for _, d in ipairs(fxTemplate:GetDescendants()) do
		if d:IsA("ParticleEmitter") then
			d:Clone().Parent = att
		end
	end
	att.Parent = root
	return att
end

local function playSound(root)
	local s = soundTemplate:Clone()
	s.Parent = root
	s.TimePosition = SOUND_START
	s:Play()
	s.Ended:Once(function() s:Destroy() end)
	Debris:AddItem(s, 10)
end

local function playLevelUp(character)
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root then return end

	playSound(root)

	local holder = makeHolder(root)
	local emitters = {}
	local maxLife = 0
	for _, d in ipairs(holder:GetDescendants()) do
		if d:IsA("ParticleEmitter") then
			table.insert(emitters, d)
			maxLife = math.max(maxLife, d.Lifetime.Max)
			d.Enabled = true
			local burst = d:GetAttribute("EmitCount")
			if burst then d:Emit(burst) end
		end
	end

	task.delay(DURATION, function()
		for _, e in ipairs(emitters) do
			if e.Parent then e.Enabled = false end
		end
	end)
	Debris:AddItem(holder, DURATION + maxLife + 0.5)
end

local function watch(player)
	local last = player:GetAttribute("Level")
	player:GetAttributeChangedSignal("Level"):Connect(function()
		local level = player:GetAttribute("Level")
		if last and level and level > last then
			playLevelUp(player.Character)
		end
		last = level
	end)
end

Players.PlayerAdded:Connect(watch)
for _, p in ipairs(Players:GetPlayers()) do
	watch(p)
end
```
