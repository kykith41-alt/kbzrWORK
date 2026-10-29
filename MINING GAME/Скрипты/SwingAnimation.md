---
тип: ModuleScript
где: ReplicatedStorage
система: "[[Кирка]]"
tags: [скрипт, ModuleScript]
---
# SwingAnimation

**Тип:** ModuleScript · **Где:** `ReplicatedStorage` · **Система:** [[Кирка]]

Анимация замаха и удара киркой (IMPACT, DRAW_TIME и т.д.), авто-убирание за спину через `IDLE_SHEATHE = 3` с.



## Связано
- [[PickaxeClient]]
- [[PickaxeSheath]]
- [[CharacterAnimator]]
- [[MiningEffects]]

## Код
```lua
local TweenService = game:GetService("TweenService")

local SwingAnimation = {}
SwingAnimation.IMPACT = 0.42
SwingAnimation.DRAW_TIME = 0.26
SwingAnimation.WINDUP = 0.3 -- доля удара, где кирка в верхней точке замаха
SwingAnimation.SHEATHE_TIME = 0.55
SwingAnimation.IDLE_SHEATHE = 3 -- через сколько секунд без ударов кирка сама уходит за спину (стоит или ходит — неважно)
-- сигнал о начале «достать»/«убрать» (для звуков и эффектов)
SwingAnimation.Transition = Instance.new("BindableEvent")

local R = math.rad
local ZERO = { 0, 0, 0 }

-- углы {rx, ry, rz} в пространстве родительской детали; dip — присед корпуса.
-- Кирка в правой руке, левая рука свободная: её значения — добавка к обычной анимации.
local HOLD = {
	rArm = { R(52), 0, R(-4) }, rElbow = { R(36), 0, 0 }, rWrist = { R(-12), 0, 0 },
	lArm = ZERO, lElbow = ZERO,
	waist = ZERO, neck = ZERO, dip = 0,
}
SwingAnimation.HOLD = HOLD

local function key(t, style, dir, pose) return { t = t, style = style, dir = dir, pose = pose } end
local Quad, Cubic, Sine, Back = Enum.EasingStyle.Quad, Enum.EasingStyle.Cubic, Enum.EasingStyle.Sine, Enum.EasingStyle.Back
local In, Out, InOut = Enum.EasingDirection.In, Enum.EasingDirection.Out, Enum.EasingDirection.InOut

-- рука за плечом — схватить/отпустить кирку
local REACH = {
	rArm = { R(188), 0, R(-18) }, rElbow = { R(70), 0, 0 }, rWrist = { R(18), 0, 0 },
	lArm = { R(12), 0, -R(10) }, lElbow = { R(10), 0, 0 },
	waist = { R(6), R(16), 0 }, neck = { R(4), R(14), 0 }, dip = 0,
}

-- замах из-за головы, левая рука вперёд для баланса
local WINDUP = {
	rArm = { R(158), 0, R(-10) }, rElbow = { R(34), 0, 0 }, rWrist = { R(0), 0, 0 },
	lArm = { R(38), 0, -R(14) }, lElbow = { R(26), 0, 0 },
	waist = { R(14), R(14), 0 }, neck = { R(10), 0, 0 }, dip = 0.06,
}

local SWING = {
	key(0, nil, nil, HOLD),
	key(0.3, Quad, Out, WINDUP),
	key(0.42, Cubic, In, { -- удар вниз, левая рука уходит назад
		rArm = { R(18), 0, R(-4) }, rElbow = { R(6), 0, 0 }, rWrist = { R(-42), 0, 0 },
		lArm = { -R(30), 0, -R(16) }, lElbow = { R(18), 0, 0 },
		waist = { R(-32), R(-10), 0 }, neck = { R(-18), 0, 0 }, dip = -0.55 }),
	key(0.56, Quad, Out, { -- отдача
		rArm = { R(30), 0, R(-4) }, rElbow = { R(12), 0, 0 }, rWrist = { R(-30), 0, 0 },
		lArm = { -R(18), 0, -R(12) }, lElbow = { R(14), 0, 0 },
		waist = { R(-26), R(-6), 0 }, neck = { R(-12), 0, 0 }, dip = -0.42 }),
	key(1, Sine, InOut, HOLD),
}

local DRAW = {
	key(0, nil, nil, HOLD),
	key(1, Quad, Out, WINDUP), -- хватает кирку со спины — и она уже над головой
}

local SHEATHE = {
	key(0, nil, nil, HOLD),
	key(0.45, Quad, InOut, REACH), -- заводит кирку за спину
	key(1, Sine, Out, {
		rArm = { R(120), 0, R(-10) }, rElbow = { R(40), 0, 0 }, rWrist = ZERO,
		lArm = ZERO, lElbow = ZERO, waist = { R(3), R(6), 0 }, neck = ZERO, dip = 0 }),
}

local POSE_JOINTS = { "rArm", "rElbow", "rWrist", "lArm", "lElbow", "waist", "neck" }
local states = setmetatable({}, { __mode = "k" })

local function lerp3(a, b, k)
	return { a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k, a[3] + (b[3] - a[3]) * k }
end

local function sample(keys, t)
	for i = 1, #keys - 1 do
		local a, b = keys[i], keys[i + 1]
		if t <= b.t then
			local k = TweenService:GetValue((t - a.t) / (b.t - a.t), b.style, b.dir)
			local out = { dip = a.pose.dip + (b.pose.dip - a.pose.dip) * k }
			for _, name in ipairs(POSE_JOINTS) do out[name] = lerp3(a.pose[name], b.pose[name], k) end
			return out
		end
	end
	return keys[#keys].pose
end

local function smooth01(e0, e1, x)
	local t = math.clamp((x - e0) / (e1 - e0), 0, 1)
	return t * t * (3 - 2 * t)
end

function SwingAnimation.StartHold(character)
	if character and not states[character] then
		states[character] = { sheathed = false, lastActive = os.clock() }
	end
end

function SwingAnimation.StopHold(character)
	if character then states[character] = nil end
end

function SwingAnimation.IsHolding(character)
	return states[character] ~= nil
end

-- мгновенно (без анимации), например при появлении персонажа
function SwingAnimation.SetSheathed(character, sheathed)
	SwingAnimation.StartHold(character)
	local state = states[character]
	state.sheathed = sheathed
	state.transition = nil
	state.lastActive = os.clock()
end

function SwingAnimation.IsSheathed(character)
	local state = states[character]
	return state ~= nil and state.sheathed and not state.transition
end

local function startTransition(character, kind, duration)
	SwingAnimation.StartHold(character)
	local state = states[character]
	state.swing = nil
	state.transition = { kind = kind, start = os.clock(), duration = duration }
	state.sheathed = kind == "sheathe"
	state.lastActive = os.clock()
	SwingAnimation.Transition:Fire(character, kind)
	return duration
end

-- достать кирку из-за спины; возвращает длительность
function SwingAnimation.Draw(character)
	return startTransition(character, "draw", SwingAnimation.DRAW_TIME)
end

-- убрать кирку за спину (если уже за спиной или убирается — ничего не делает)
function SwingAnimation.Sheathe(character)
	local state = states[character]
	if state and state.sheathed then return 0 end
	return startTransition(character, "sheathe", SwingAnimation.SHEATHE_TIME)
end

-- где кирка: 0 — на спине, 1 — в руке (для PickaxeSheath)
function SwingAnimation.HandleBlend(character)
	local state = states[character]
	if not state then return 1 end
	local tr = state.transition
	if tr then
		local p = math.clamp((os.clock() - tr.start) / tr.duration, 0, 1)
		if tr.kind == "draw" then return smooth01(0.15, 0.85, p) end
		return 1 - smooth01(0.32, 0.56, p)
	end
	return state.sheathed and 0 or 1
end

function SwingAnimation.UsesPhysicsJoints(character)
	local lower = character and character:FindFirstChild("LowerTorso")
	local root = lower and lower:FindFirstChild("Root")
	if not root then
		local hrp = character and character:FindFirstChild("HumanoidRootPart")
		root = hrp and hrp:FindFirstChild("RootJoint")
	end
	return root ~= nil and root:IsA("AnimationConstraint")
end

-- удар; onImpact вызывается в момент попадания (по таймеру, не зависит от отрисовки)
-- fromWindup: начать с верхней точки замаха (сразу после выхватывания со спины)
function SwingAnimation.Play(character, duration: number, onImpact: (() -> ())?, fromWindup: boolean?)
	if not character then return end
	SwingAnimation.StartHold(character)
	local state = states[character]
	local startP = fromWindup and SwingAnimation.WINDUP or 0
	local swing = { start = os.clock(), duration = duration, startP = startP }
	state.swing = swing
	state.sheathed = false
	state.transition = nil
	state.lastActive = os.clock()
	task.delay(duration * (SwingAnimation.IMPACT - startP), function()
		if state.swing == swing then swing.shakeUntil = os.clock() + 0.12 end
		if onImpact then onImpact() end
	end)
end

-- поза кирки: pose, shake, swinging, weight (0 — руки свободны, 1 — поза кирки целиком)
function SwingAnimation.Sample(character)
	local state = states[character]
	if not state then return nil end
	local now = os.clock()

	local tr = state.transition
	if tr then
		local p = math.clamp((now - tr.start) / tr.duration, 0, 1)
		if p >= 1 then
			state.transition = nil
			state.lastActive = now
			if tr.kind == "draw" then state.drawEnded = now end
		elseif tr.kind == "draw" then
			return sample(DRAW, p), 0, false, smooth01(0, 0.35, p)
		else
			return sample(SHEATHE, p), 0, false, 1 - smooth01(0.6, 1, p)
		end
	end
	if state.sheathed then return nil end

	local swing = state.swing
	if swing then
		local p = math.clamp(swing.startP + (now - swing.start) / swing.duration, 0, 1)
		local shake = (swing.shakeUntil and now < swing.shakeUntil) and (math.random() - 0.5) * R(6) or 0
		state.lastActive = now -- отсчёт простоя начинается после конца удара
		if p >= 1 then state.swing = nil end
		return sample(SWING, p), shake, true, 1
	end
	-- только что достали, удар вот-вот начнётся — держим замах, без рывка в позу держания
	if state.drawEnded and now - state.drawEnded < 0.15 then
		return WINDUP, 0, false, 1
	end
	-- долго не копал — убираем кирку за спину (и когда стоит, и когда ходит)
	if now - (state.lastActive or now) >= SwingAnimation.IDLE_SHEATHE then
		SwingAnimation.Sheathe(character)
		return HOLD, 0, false, 1 -- первый кадр анимации убирания
	end
	return HOLD, 0, false, 1
end

return SwingAnimation
```
