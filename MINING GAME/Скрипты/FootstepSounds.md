---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Персонаж]]"
tags: [скрипт, LocalScript]
---
# FootstepSounds

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Персонаж]]

Звук шагов по событию `CharacterAnimator.Footstep` — всегда совпадает с анимацией. Защита от повтора `MIN_GAP = 0.15`, глушит стандартный звук `Running`.

## Заметки
- Скорость 0.8 задаётся в [[MiningShared]] (`Shared.SoundSpeed.Footsteps`).
- Нужен пустой LocalScript `RbxCharacterSounds` в StarterPlayerScripts, иначе Roblox играет свои шаги.

## Связано
- [[CharacterAnimator]]
- [[MiningShared]]
- [[Звуки]]

## Код
```lua
-- Звук шагов: играет, когда нога персонажа ставится на землю (сигнал CharacterAnimator.Footstep),
-- поэтому всегда совпадает с анимацией ходьбы и бега. Работает и для других игроков.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local CharacterAnimator = require(ReplicatedStorage:WaitForChild("CharacterAnimator"))

local WALK_VOLUME = 0.3   -- громкость при ходьбе
local RUN_VOLUME = 0.45   -- громкость при беге
local MIN_GAP = 0.15      -- не чаще одного шага за столько секунд у одного персонажа

Shared.PreloadSounds()

local lastStep = setmetatable({}, { __mode = "k" })

-- стандартный звук ходьбы Roblox, если он всё-таки есть, — глушим
local function muteDefault(character)
	local root = character:FindFirstChild("HumanoidRootPart")
	local running = root and root:FindFirstChild("Running")
	if running and running:IsA("Sound") then
		running.Volume = 0
	end
end

CharacterAnimator.Footstep.Event:Connect(function(character, speed, run)
	local root = character:FindFirstChild("HumanoidRootPart")
	if not root then return end
	local now = os.clock()
	if lastStep[character] and now - lastStep[character] < MIN_GAP then return end
	lastStep[character] = now
	muteDefault(character)
	local volume = WALK_VOLUME + (RUN_VOLUME - WALK_VOLUME) * run
	Shared.PlaySound(Shared.RandomSound(Shared.Sounds.Footsteps), root, volume, 0.95 + math.random() * 0.1)
end)
```
