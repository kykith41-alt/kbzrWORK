local TweenService = game:GetService("TweenService")
local RunService = game:GetService("RunService")

local SwingAnimation = {}
SwingAnimation.IMPACT = 0.42
SwingAnimation.DRAW_TIME = 0.26
SwingAnimation.WINDUP = 0.3
SwingAnimation.SHEATHE_TIME = 0.55
SwingAnimation.IDLE_SHEATHE = 3
SwingAnimation.TURN_SMOOTH = 13 -- чем больше, тем резче разворот к блоку
SwingAnimation.TURN_MAX_SPEED = math.rad(900) -- максимум градусов в секунду
SwingAnimation.TURN_HOLD = 0.5 -- сколько секунд держать лицо к блоку после клика
SwingAnimation.Transition = Instance.new("BindableEvent")

local R = math.rad
local ZERO = { 0, 0, 0 }


local HOLD = {
	rArm = { R(52), 0, R(-4) }, rElbow = { R(36), 0, 0 }, rWrist = { R(-12), 0, 0 },
	lArm = ZERO, lElbow = ZERO,
	waist = ZERO, neck = ZERO, dip = 0,
}
SwingAnimation.HOLD = HOLD

local function key(t, style, dir, pose) return { t = t, style = style, dir = dir, pose = pose } end
local Quad, Cubic, Sine, Back = Enum.EasingStyle.Quad, Enum.EasingStyle.Cubic, Enum.EasingStyle.Sine, Enum.EasingStyle.Back
local In, Out, InOut = Enum.EasingDirection.In, Enum.EasingDirection.Out, Enum.EasingDirection.InOut


local REACH = {
	rArm = { R(188), 0, R(-18) }, rElbow = { R(70), 0, 0 }, rWrist = { R(18), 0, 0 },
	lArm = { R(12), 0, -R(10) }, lElbow = { R(10), 0, 0 },
	waist = { R(6), R(16), 0 }, neck = { R(4), R(14), 0 }, dip = 0,
}


local WINDUP = {
	rArm = { R(158), 0, R(-10) }, rElbow = { R(34), 0, 0 }, rWrist = { R(0), 0, 0 },
	lArm = { R(38), 0, -R(14) }, lElbow = { R(26), 0, 0 },
	waist = { R(14), R(14), 0 }, neck = { R(10), 0, 0 }, dip = 0.06,
}

local SWING = {
	key(0, nil, nil, HOLD),
	key(0.3, Quad, Out, WINDUP),
	key(0.42, Cubic, In, {
		rArm = { R(18), 0, R(-4) }, rElbow = { R(6), 0, 0 }, rWrist = { R(-42), 0, 0 },
		lArm = { -R(30), 0, -R(16) }, lElbow = { R(18), 0, 0 },
		waist = { R(-32), R(-10), 0 }, neck = { R(-18), 0, 0 }, dip = -0.55 }),
	key(0.56, Quad, Out, {
		rArm = { R(30), 0, R(-4) }, rElbow = { R(12), 0, 0 }, rWrist = { R(-30), 0, 0 },
		lArm = { -R(18), 0, -R(12) }, lElbow = { R(14), 0, 0 },
		waist = { R(-26), R(-6), 0 }, neck = { R(-12), 0, 0 }, dip = -0.42 }),
	key(1, Sine, InOut, HOLD),
}

local DRAW = {
	key(0, nil, nil, HOLD),
	key(1, Quad, Out, WINDUP),
}

local SHEATHE = {
	key(0, nil, nil, HOLD),
	key(0.45, Quad, InOut, REACH),
	key(1, Sine, Out, {
		rArm = { R(120), 0, R(-10) }, rElbow = { R(40), 0, 0 }, rWrist = ZERO,
		lArm = ZERO, lElbow = ZERO, waist = { R(3), R(6), 0 }, neck = ZERO, dip = 0 }),
}

local POSE_JOINTS = { "rArm", "rElbow", "rWrist", "lArm", "lElbow", "waist", "neck" }
local states = setmetatable({}, { __mode = "k" })
local turning = {}

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


function SwingAnimation.Draw(character)
	return startTransition(character, "draw", SwingAnimation.DRAW_TIME)
end


function SwingAnimation.Sheathe(character)
	local state = states[character]
	if state and state.sheathed then return 0 end
	return startTransition(character, "sheathe", SwingAnimation.SHEATHE_TIME)
end


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
		state.lastActive = now
		if p >= 1 then state.swing = nil end
		return sample(SWING, p), shake, true, 1
	end

	if state.drawEnded and now - state.drawEnded < 0.15 then
		return WINDUP, 0, false, 1
	end

	if now - (state.lastActive or now) >= SwingAnimation.IDLE_SHEATHE then
		SwingAnimation.Sheathe(character)
		return HOLD, 0, false, 1
	end
	return HOLD, 0, false, 1
end


local function yawOf(look)
	return math.atan2(-look.X, -look.Z)
end

local function stopTurning(character)
	local tr = turning[character]
	if not tr then return end
	turning[character] = nil
	tr.conn:Disconnect()
	if tr.hum.Parent then tr.hum.AutoRotate = tr.autoRotate end
end

-- Плавно поворачивает персонажа лицом к точке (вместо мгновенного hrp.CFrame = CFrame.lookAt(...)).
-- Вызывать на клиенте для своего персонажа, можно каждый клик: цель просто обновится.
function SwingAnimation.FaceTarget(character, targetPos: Vector3, holdTime: number?)
	local hrp = character and character:FindFirstChild("HumanoidRootPart")
	local hum = character and character:FindFirstChildOfClass("Humanoid")
	if not hrp or not hum then return end

	local tr = turning[character]
	if not tr then
		tr = { hrp = hrp, hum = hum, autoRotate = hum.AutoRotate }
		turning[character] = tr
		-- иначе Humanoid сам крутит персонажа по направлению движения и мешает развороту
		hum.AutoRotate = false
		tr.conn = RunService.PreSimulation:Connect(function(dt)
			if not character.Parent or not hrp.Parent or hum.Health <= 0 then
				stopTurning(character)
				return
			end
			local dir = tr.target - hrp.Position
			dir = Vector3.new(dir.X, 0, dir.Z)
			local yaw = yawOf(hrp.CFrame.LookVector)
			local diff = 0
			if dir.Magnitude > 0.05 then
				diff = (yawOf(dir.Unit) - yaw + math.pi) % (math.pi * 2) - math.pi
				local turn = diff * (1 - math.exp(-dt * SwingAnimation.TURN_SMOOTH))
				local maxStep = SwingAnimation.TURN_MAX_SPEED * dt
				turn = math.clamp(turn, -maxStep, maxStep)
				hrp.CFrame = CFrame.new(hrp.Position) * CFrame.Angles(0, yaw + turn, 0)
			end
			if os.clock() >= tr.untilTime and math.abs(diff) < R(2) then
				stopTurning(character)
			end
		end)
	end
	tr.target = targetPos
	tr.untilTime = os.clock() + (holdTime or SwingAnimation.TURN_HOLD)
end

-- true, пока персонаж ещё не повернулся к цели (можно подождать перед ударом)
function SwingAnimation.IsTurning(character)
	local tr = turning[character]
	if not tr then return false end
	local dir = tr.target - tr.hrp.Position
	dir = Vector3.new(dir.X, 0, dir.Z)
	if dir.Magnitude < 0.05 then return false end
	local diff = (yawOf(dir.Unit) - yawOf(tr.hrp.CFrame.LookVector) + math.pi) % (math.pi * 2) - math.pi
	return math.abs(diff) > R(10)
end

function SwingAnimation.StopFacing(character)
	stopTurning(character)
end

return SwingAnimation
