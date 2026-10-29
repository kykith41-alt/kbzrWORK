---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Кирка]]"
tags: [скрипт, LocalScript]
---
# PickaxeClient

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Кирка]]

Копание: зажми ЛКМ / тап по блоку. Удар только по блоку под курсором в радиусе `MINE_RANGE`. Клик мимо — кирка остаётся за спиной. Через 3 с без ударов кирка убирается и состояние уходит на сервер (`Remotes.Sheath`).



## Связано
- [[SwingAnimation]]
- [[PickaxeSheath]]
- [[MiningFX]]
- [[MiningShared]]
- [[MineServer]]

## Код
```lua
-- Кирка: зажми ЛКМ / тап по блоку, чтобы копать (только блок под курсором в радиусе досягаемости).
-- Клик мимо блока ничего не делает — кирка остаётся за спиной.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local Shared = require(ReplicatedStorage:WaitForChild("MiningShared"))
local SwingAnimation = require(ReplicatedStorage:WaitForChild("SwingAnimation"))
local MiningFX = require(ReplicatedStorage:WaitForChild("MiningFX"))
local Remotes = ReplicatedStorage:WaitForChild("Remotes")

local tool = script.Parent
local handle = tool:WaitForChild("Handle")
local trail = handle:WaitForChild("SwingTrail")
local player = Players.LocalPlayer
local mouse = player:GetMouse()
local blockFolder = workspace:WaitForChild("Mine"):WaitForChild("Blocks")
local fxFolder = workspace:WaitForChild("LocalMiningFX")
mouse.TargetFilter = fxFolder

Shared.PreloadSounds()

local holding = false
local swinging = false     -- цикл ударов запущен (кнопка зажата)
local striking = false     -- идёт сам удар
local equipped = false
local sheathed = false     -- кирка на спине
local lastAction = 0       -- последний удар
local IDLE_SHEATHE = 3     -- через сколько секунд без ударов кирка уходит за спину (стоит или ходит — неважно)

local function blockFrom(inst)
	while inst and inst.Parent ~= blockFolder do
		inst = inst.Parent
		if inst == workspace or inst == game then return nil end
	end
	return inst
end

local function inRange(model, root)
	return (model:GetPivot().Position - root.Position).Magnitude <= Shared.MINE_RANGE - 1
end

-- блок под курсором, если до него можно дотянуться
local function hoveredBlock(root)
	local target = blockFrom(mouse.Target)
	if target and inRange(target, root) then return target end
	return nil
end

-- точка удара: где курсор на блоке, иначе центр грани со стороны игрока
local function hitPoint(target, root)
	if blockFrom(mouse.Target) == target then
		return mouse.Hit.Position
	end
	local pivot = MiningFX.BasePivot(target)
	local half = Shared.Mine.CELL / 2
	local toPlayer = root.Position - pivot.Position
	if toPlayer.Y > half then
		return pivot.Position + Vector3.new(0, half, 0)
	end
	local flat = Vector3.new(toPlayer.X, 0, toPlayer.Z)
	return pivot.Position + (flat.Magnitude > 0.1 and flat.Unit * half or Vector3.new(0, half, 0))
end

local function cameraShake(strength)
	local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	if not hum then return end
	local start = os.clock()
	local conn
	conn = RunService.RenderStepped:Connect(function()
		local t = os.clock() - start
		if t > 0.16 then
			hum.CameraOffset = Vector3.zero
			conn:Disconnect()
			return
		end
		local a = strength * (1 - t / 0.16)
		hum.CameraOffset = Vector3.new(math.random() - 0.5, (math.random() - 0.5) - 0.3, 0) * a
	end)
end

local function swing(target)
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root then return end
	striking = true
	local duration = Shared.SwingTime(player)

	-- кирка на спине: выхватывание сразу переходит в замах — удар продолжается с верхней точки
	local fromWindup = false
	if sheathed then
		sheathed = false
		fromWindup = true
		lastAction = os.clock()
		Remotes.Sheath:FireServer(false)
		task.wait(SwingAnimation.Draw(character))
	end
	lastAction = os.clock()
	local skip = fromWindup and SwingAnimation.WINDUP or 0

	-- поворачиваемся к блоку
	local p = target:GetPivot().Position
	local look = Vector3.new(p.X, root.Position.Y, p.Z)
	if (look - root.Position).Magnitude > 1 then
		root.CFrame = CFrame.lookAt(root.Position, look)
	end

	Remotes.Swing:FireServer(duration, fromWindup)
	task.delay(math.max(0, 0.28 - skip) * duration, function()
		trail.Enabled = true
		Shared.PlaySound(Shared.Sounds.Swing, nil, 0.35, 1.1 + math.random() * 0.15)
	end)
	task.delay((0.55 - skip) * duration, function() trail.Enabled = false end)
	SwingAnimation.Play(character, duration, function()
		if target and target.Parent == blockFolder then
			-- всё мгновенно на клиенте, сервер только засчитывает урон
			Remotes.MineHit:FireServer(target)
			Shared.PlaySound(Shared.RandomSound(Shared.Sounds.Hit), nil, 0.9, 0.92 + math.random() * 0.2)
			MiningFX.Impact(target, hitPoint(target, root), false)
			MiningFX.PredictDamage(target, Shared.BASE_DAMAGE)
			cameraShake(0.35)
		end
	end, fromWindup)
	task.wait(duration * (1 - skip))
	lastAction = os.clock()
	striking = false
end

-- пока кнопка зажата: бьём, только когда курсор на блоке; мимо блока — просто ждём
local function loop()
	if swinging then return end
	swinging = true
	while holding and tool.Parent == player.Character do
		local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
		local target = root and hoveredBlock(root)
		if target then
			swing(target)
		else
			RunService.Heartbeat:Wait()
		end
	end
	swinging = false
end

------------------------------------------------------------------ чёрная наводка на блок под курсором

local proxy = Instance.new("Part")
proxy.Name = "HoverProxy"
proxy.Anchored = true
proxy.CanCollide = false
proxy.CanQuery = false
proxy.CanTouch = false
proxy.Transparency = 1
proxy.Size = Vector3.one * Shared.Mine.CELL
proxy.Parent = fxFolder
local hoverBox = Instance.new("SelectionBox")
hoverBox.Adornee = proxy
hoverBox.Color3 = Color3.fromRGB(60, 164, 255)
hoverBox.SurfaceTransparency = 1
hoverBox.LineThickness = 0.05
hoverBox.Visible = false
hoverBox.Parent = fxFolder

local hovered, hoverStart = nil, 0
RunService.RenderStepped:Connect(function()
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	local target = (equipped and root) and hoveredBlock(root) or nil
	if target ~= hovered then
		hovered = target
		hoverStart = os.clock()
	end
	if not hovered or not hovered.PrimaryPart then
		hoverBox.Visible = false
		return
	end
	local t = os.clock()
	local k = math.clamp((t - hoverStart) / 0.22, 0, 1)
	local snap = 1 - TweenService:GetValue(k, Enum.EasingStyle.Back, Enum.EasingDirection.Out) -- 1 -> 0 с перелётом
	local breathe = math.sin(t * 6) * 0.5 + 0.5
	proxy.CFrame = hovered.PrimaryPart.CFrame -- рамка трясётся вместе с блоком
	proxy.Size = Vector3.one * (Shared.Mine.CELL + 0.06 + breathe * 0.08 + snap * 0.9)
	hoverBox.LineThickness = 0.04 + breathe * 0.025
	hoverBox.Transparency = 0.05 + (1 - k) * 0.6
	hoverBox.Visible = true
end)

tool.Equipped:Connect(function()
	equipped = true
	-- при появлении кирка висит на спине
	sheathed = true
	SwingAnimation.SetSheathed(player.Character, true)
	Remotes.Sheath:FireServer(true)
end)

-- давно не копал — убираем кирку за спину (и стоя, и на ходу)
RunService.Heartbeat:Connect(function()
	if not equipped then return end
	local character = player.Character
	if not character then return end
	-- SwingAnimation мог убрать кирку сам — сообщаем серверу, чтобы другие игроки тоже видели
	if not sheathed and SwingAnimation.IsSheathed(character) then
		sheathed = true
		Remotes.Sheath:FireServer(true)
		return
	end
	if sheathed or striking then return end
	if os.clock() - lastAction > IDLE_SHEATHE then
		sheathed = true
		SwingAnimation.Sheathe(character)
		Remotes.Sheath:FireServer(true)
	end
end)

tool.Activated:Connect(function()
	holding = true
	task.spawn(loop)
end)
tool.Deactivated:Connect(function()
	holding = false
end)
tool.Unequipped:Connect(function()
	equipped = false
	holding = false
	trail.Enabled = false
	SwingAnimation.StopHold(player.Character)
end)
```
