local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")

local SwingAnimation = require(script.Parent:WaitForChild("SwingAnimation"))

local CharacterAnimator = {}

local R = math.rad
local TAU = math.pi * 2
local V0 = Vector3.zero
local WALK_SPEED = 16
local RUN_START = 10 -- с этой скорости походка начинает переходить в бег
local RUN_FULL = 20 -- с этой скорости полностью бег
local POSE_SMOOTH = 16

-- приземление: присед -> короткая пауза -> плавный подъём
local LAND_ATTACK = 0.07
local LAND_HOLD = 0.08
local LAND_RECOVER = 0.45

local active = {}

local function v(x, y, z) return Vector3.new(x or 0, y or 0, z or 0) end
local function arr(t) return Vector3.new(t[1], t[2], t[3]) end



local function getJoints(character)
	local function j(part, name)
		local p = character:FindFirstChild(part)
		return p and p:FindFirstChild(name)
	end
	if character:FindFirstChild("UpperTorso") then
		return {
			root = j("LowerTorso", "Root"), waist = j("UpperTorso", "Waist"), neck = j("Head", "Neck"),
			rArm = j("RightUpperArm", "RightShoulder"), lArm = j("LeftUpperArm", "LeftShoulder"),
			rElbow = j("RightLowerArm", "RightElbow"), lElbow = j("LeftLowerArm", "LeftElbow"),
			rWrist = j("RightHand", "RightWrist"), lWrist = j("LeftHand", "LeftWrist"),
			rHip = j("RightUpperLeg", "RightHip"), lHip = j("LeftUpperLeg", "LeftHip"),
			rKnee = j("RightLowerLeg", "RightKnee"), lKnee = j("LeftLowerLeg", "LeftKnee"),
			rAnkle = j("RightFoot", "RightAnkle"), lAnkle = j("LeftFoot", "LeftAnkle"),
		}, true
	end
	return {
		root = j("HumanoidRootPart", "RootJoint"), neck = j("Torso", "Neck"),
		rArm = j("Torso", "Right Shoulder"), lArm = j("Torso", "Left Shoulder"),
		rHip = j("Torso", "Right Hip"), lHip = j("Torso", "Left Hip"),
	}, false
end

local function read(joint)
	if joint:IsA("AnimationConstraint") then
		return joint.Attachment0 and joint.Attachment0.CFrame
	end
	return joint.C0
end

local function write(joint, cf)
	if joint:IsA("AnimationConstraint") then
		if joint.Attachment0 then joint.Attachment0.CFrame = cf end
	else
		joint.C0 = cf
	end
end



local NAMES = { "root", "waist", "neck", "rArm", "lArm", "rElbow", "lElbow", "rWrist", "lWrist",
	"rHip", "lHip", "rKnee", "lKnee", "rAnkle", "lAnkle" }

local function emptyPose()
	local p = { lift = V0 }
	for _, n in ipairs(NAMES) do p[n] = V0 end
	return p
end

local function addPose(dst, src, w)
	for _, n in ipairs(NAMES) do dst[n] += src[n] * w end
	dst.lift += src.lift * w
end

local function lookAround(t, seed)
	return v(math.noise(t * 0.25, seed) * R(8), math.noise(t * 0.18, seed + 3) * R(22), 0)
end



local R15 = {}
R15.STRIDE = 7.5

function R15.idle(t, seed)
	local p = emptyPose()
	local breathe = math.sin(t * 1.9)
	local sway = math.sin(t * 0.55 + seed)
	p.lift = v(sway * 0.05, breathe * 0.025, 0)
	p.root = v(0, sway * R(2), sway * R(1.5))
	p.waist = v(breathe * R(1.6), -sway * R(2), 0)
	p.neck = lookAround(t, seed) + v(-breathe * R(1))
	p.rArm = v(R(3) + breathe * R(1.5), 0, R(5) + breathe * R(1))
	p.lArm = v(R(3) + breathe * R(1.5), 0, -R(5) - breathe * R(1))
	p.rElbow = v(R(9)); p.lElbow = v(R(9))
	p.rHip = v(0, 0, sway * R(1.5)); p.lHip = v(0, 0, sway * R(1.5))
	return p
end

function R15.walk(phase, w, run)
	local p = emptyPose()
	local s, c = math.sin(phase), math.cos(phase)
	local thigh = R(30 + 24 * run) * w
	local kneeLift = R(48 + 62 * run) * w
	local lean = R(7) * run * w
	local function leg(ph)
		local ls, lc = math.sin(ph), math.cos(ph)
		local swingK = math.max(0, lc) ^ 1.3
		-- при беге задняя нога сильнее отталкивается стопой
		local push = math.max(0, -ls) * math.max(0, -lc) * R(25) * run * w
		return v(ls * thigh + lean),
			v(-(R(6) * w + swingK * kneeLift)),
			v(-ls * thigh * 0.35 + swingK * kneeLift * 0.35 - push)
	end
	p.rHip, p.rKnee, p.rAnkle = leg(phase)
	p.lHip, p.lKnee, p.lAnkle = leg(phase + math.pi)
	local arm = R(26 + 30 * run) * w
	p.rArm = v(-s * arm, s * R(8) * run * w, R(5)); p.lArm = v(s * arm, s * R(8) * run * w, -R(5))
	p.rElbow = v(R(14 + 72 * run) * w + math.max(0, -s) * R(14) * w)
	p.lElbow = v(R(14 + 72 * run) * w + math.max(0, s) * R(14) * w)
	-- ходьба: выше всего, когда ноги проходят друг мимо друга; бег: наоборот, пик в фазе полёта
	local walkLift = (math.abs(c) - 0.64) * 0.2
	local runLift = (math.abs(s) - 0.55) * 0.34
	p.lift = v(0, (walkLift + (runLift - walkLift) * run) * w, 0)
	p.root = v(-lean, -s * R(7) * w, -c * R(2.5) * w)
	p.waist = v(-R(5 + 12 * run) * w, s * R(10 + 5 * run) * w, 0)
	p.neck = v(R(4 + 10 * run) * w, -s * R(6) * w, 0)
	return p
end

function R15.air(rising, t)
	local p = emptyPose()
	local flail = math.sin(t * 9)
	local up = emptyPose()
	up.rArm = v(R(145), 0, R(18)); up.lArm = v(R(132), 0, -R(22))
	up.rElbow = v(R(22)); up.lElbow = v(R(30))
	up.rHip = v(R(58)); up.rKnee = v(-R(92)); up.rAnkle = v(R(20))
	up.lHip = v(-R(8)); up.lKnee = v(-R(38)); up.lAnkle = v(R(12))
	up.waist = v(-R(6)); up.neck = v(R(10))
	local fall = emptyPose()
	fall.rArm = v(R(30) + flail * R(8), 0, R(72) + flail * R(6))
	fall.lArm = v(R(30) - flail * R(8), 0, -R(72) + flail * R(6))
	fall.rElbow = v(R(20)); fall.lElbow = v(R(20))
	fall.rHip = v(R(22) + flail * R(5)); fall.rKnee = v(-R(38)); fall.rAnkle = v(R(10))
	fall.lHip = v(-R(4) - flail * R(5)); fall.lKnee = v(-R(22)); fall.lAnkle = v(R(8))
	fall.waist = v(R(4)); fall.neck = v(-R(10))
	addPose(p, up, rising)
	addPose(p, fall, 1 - rising)
	return p
end


local R6 = {}
R6.STRIDE = 9
local R6_LEG = 2

function R6.idle(t, seed)
	local p = emptyPose()
	local breathe = math.sin(t * 1.9)
	local sway = math.sin(t * 0.55 + seed)
	p.waist = v(breathe * R(1.8), -sway * R(3), sway * R(1.5))
	p.neck = lookAround(t, seed) + v(-breathe * R(1.2))
	p.rArm = v(R(2) + breathe * R(2.5), math.sin(t * 0.8) * R(3), R(4) + breathe * R(1.5) + sway * R(1))
	p.lArm = v(R(2) + breathe * R(2.5), -math.sin(t * 0.8 + 1) * R(3), -R(4) - breathe * R(1.5) + sway * R(1))
	p.rHip = v(0, R(3), -sway * R(1.2)); p.lHip = v(0, -R(3), -sway * R(1.2))
	return p
end

function R6.walk(phase, w, run)
	local p = emptyPose()
	local s, c = math.sin(phase), math.cos(phase)
	local amp = R(30 + 22 * run) * w
	local theta = s * amp

	p.rHip = v(theta, R(5) * w, R(2.5) * w * math.max(0, c))
	p.lHip = v(-theta, -R(5) * w, -R(2.5) * w * math.max(0, -c))

	local sa = math.sin(phase - 0.45)
	local armAmp = R(30 + 30 * run) * w
	p.rArm = v(-sa * armAmp + R(10) * run * w, -sa * R(9) * w, R(5 + 6 * run) * w + math.max(0, sa) * R(9) * w)
	p.lArm = v(sa * armAmp + R(10) * run * w, -sa * R(9) * w, -R(5 + 6 * run) * w - math.max(0, -sa) * R(9) * w)

	local plant = math.max(0, math.sin(phase * 2 - 0.5))
	local runBounce = (math.abs(s) - 0.55) * 0.3 * run
	p.lift = v(0, -R6_LEG * (1 - math.cos(theta)) * 0.92 - plant * 0.05 * w + runBounce * w, 0)

	p.waist = v(-R(4 + 14 * run) * w + plant * R(2.5) * w, s * R(12) * w, -c * R(4) * w)

	p.neck = v(R(3 + 11 * run) * w - plant * R(4) * w, -s * R(9) * w, c * R(3) * w)
	return p
end

function R6.air(rising, t)
	local p = emptyPose()
	local flail = math.sin(t * 9)
	local up = emptyPose()
	up.rArm = v(R(165), 0, R(12)); up.lArm = v(R(150), 0, -R(16))
	up.rHip = v(R(32)); up.lHip = v(-R(14))
	up.waist = v(-R(5)); up.neck = v(R(10))
	local fall = emptyPose()
	fall.rArm = v(R(25) + flail * R(10), 0, R(80) + flail * R(8))
	fall.lArm = v(R(25) - flail * R(10), 0, -R(80) + flail * R(8))
	fall.rHip = v(R(14) + flail * R(7), 0, R(8)); fall.lHip = v(-R(8) - flail * R(7), 0, -R(8))
	fall.waist = v(R(5)); fall.neck = v(-R(10))
	addPose(p, up, rising)
	addPose(p, fall, 1 - rising)
	return p
end



local function legAngle(drop, legLength)

	return math.acos(math.clamp(1 - drop / legLength, -1, 1))
end

-- 0..1: насколько глубоко сидим после приземления
local function landCurve(t, recover)
	if t < LAND_ATTACK then
		return math.sin(t / LAND_ATTACK * math.pi / 2)
	end
	t -= LAND_ATTACK + LAND_HOLD
	if t < 0 then return 1 end
	local u = math.min(t / recover, 1)
	return 1 - u * u * (3 - 2 * u)
end

local function writePose(state, pose)
	for _, n in ipairs(NAMES) do
		local joint = state.joints[n]
		if joint then
			local base = state.base[joint]
			local rot = pose[n]
			local p = base.Position
			local offset = (n == "root") and CFrame.new(pose.lift) or CFrame.identity
			write(joint, offset * CFrame.new(p) * CFrame.Angles(rot.X, rot.Y, rot.Z) * CFrame.new(-p) * base)
		end
	end
end

local function step(state, dt)
	local character, hum, hrp = state.character, state.hum, state.hrp
	local poses = state.r6 and R6 or R15
	local t = os.clock()
	local vel = hrp.AssemblyLinearVelocity
	local flat = Vector3.new(vel.X, 0, vel.Z)
	local speed = flat.Magnitude


	local down = hum.HipHeight + hrp.Size.Y / 2 + (state.r6 and 2.7 or 0.7)
	local grounded = hum.Sit or Workspace:Raycast(hrp.Position, Vector3.new(0, -down, 0), state.rayParams) ~= nil


	local function approach(cur, target, rate) return cur + (target - cur) * (1 - math.exp(-dt * rate)) end
	state.moveW = approach(state.moveW, grounded and math.clamp(speed / 5, 0, 1) or 0, 10)
	state.speedW = approach(state.speedW, math.clamp(speed / WALK_SPEED, 0, 1.15), 8)
	state.runW = approach(state.runW, math.clamp((speed - RUN_START) / (RUN_FULL - RUN_START), 0, 1), 6)
	state.airW = approach(state.airW, grounded and 0 or 1, grounded and 18 or 14)
	state.rising = approach(state.rising, math.clamp((vel.Y + 5) / 30, 0, 1), 12)

	-- при беге шаг длиннее, чтобы ноги не мельтешили на большой скорости
	local stride = poses.STRIDE * (1 + 0.6 * state.runW)
	local forward = speed > 0.1 and flat.Unit:Dot(hrp.CFrame.LookVector) or 1
	if grounded then
		state.phase = (state.phase + dt * speed / stride * TAU * (forward < -0.3 and -1 or 1)) % TAU
	end


	if grounded and not state.wasGrounded and state.airTime > 0.18 then
		local strength = math.clamp(-state.lastVY / 50, 0.3, 1) * (1 - 0.45 * state.runW)
		state.landAmt = strength
		state.landT = 0
		state.landRecover = LAND_RECOVER * (0.65 + 0.35 * strength) * (1 - 0.35 * state.moveW)
	end
	if grounded then
		state.airTime = 0
	else
		state.airTime += dt
		state.landAmt = approach(state.landAmt, 0, 12)
	end
	state.wasGrounded = grounded
	state.lastVY = vel.Y
	state.landT += dt
	local land = -state.landAmt * landCurve(state.landT, state.landRecover)


	state.turnLean = approach(state.turnLean, math.clamp(hrp.AssemblyAngularVelocity.Y * speed * 0.004, -0.2, 0.2), 6)
	local accel = (speed - state.lastSpeed) / math.max(dt, 1e-3)
	state.lastSpeed = speed
	state.accelLean = approach(state.accelLean, math.clamp(accel * 0.006, -0.12, 0.18), 5)


	local target = emptyPose()
	addPose(target, poses.idle(t, state.seed), 1 - state.moveW)
	addPose(target, poses.walk(state.phase, state.speedW, state.runW), state.moveW)
	if state.airW > 0.01 then
		local blended = emptyPose()
		addPose(blended, target, 1 - state.airW)
		addPose(blended, poses.air(state.rising, t), state.airW)
		target = blended
	end
	target.root += v(0, 0, state.turnLean)
	target.waist += v(-state.accelLean + land * R(22))
	target.neck += v(-land * R(12))
	target.rArm += v(land * R(12), 0, -land * R(16))
	target.lArm += v(land * R(12), 0, land * R(16))


	local cur = state.pose
	local a = 1 - math.exp(-dt * POSE_SMOOTH)
	for _, n in ipairs(NAMES) do cur[n] = cur[n]:Lerp(target[n], a) end
	cur.lift = cur.lift:Lerp(target.lift, math.min(1, a * 1.6))


	local final = emptyPose()
	addPose(final, cur, 1)
	local toolDip = 0
	local tool, shake, _, weight = SwingAnimation.Sample(character)
	if tool and weight > 0.001 then
		local hold = SwingAnimation.HOLD
		local breathe = math.sin(t * 2.2) * R(2)

		-- насколько сейчас кирка просто в руке (а не в замахе): во время удара покачивание убираем
		local swingDiff = 0
		if hold.rArm then swingDiff += (arr(tool.rArm) - arr(hold.rArm)).Magnitude end
		if hold.rElbow then swingDiff += (arr(tool.rElbow) - arr(hold.rElbow)).Magnitude end
		state.holdW = approach(state.holdW, 1 - math.clamp(swingDiff / R(25), 0, 1), 12)

		-- кирка в руке качается в такт шагам/бегу
		local carry = state.moveW * state.speedW * state.holdW
		local s = math.sin(state.phase)
		local s2 = math.sin(state.phase * 2)
		local run = state.runW
		local carryArm = v(-s * R(14 + 18 * run) * carry - R(8) * run * carry, 0, math.max(0, s) * R(5) * carry)
		local carryElbow = v(math.max(0, -s) * R(16) * carry + R(18) * run * carry)
		local carryWrist = v(s2 * R(7 + 5 * run) * carry)

		local rArm = arr(tool.rArm) + carryArm
		local lDelta = arr(tool.lArm) - arr(hold.lArm)
		if state.r6 then

			rArm += v(tool.rElbow[1] * 0.5 + tool.rWrist[1] * 0.3) + carryElbow * 0.5 + carryWrist * 0.3
			lDelta += v((tool.lElbow[1] - hold.lElbow[1]) * 0.5)
		end
		final.rArm = final.rArm:Lerp(rArm + v(breathe + shake + land * R(12)), weight)
		final.rElbow = final.rElbow:Lerp(arr(tool.rElbow) + carryElbow, weight)
		final.rWrist = final.rWrist:Lerp(arr(tool.rWrist) + carryWrist + v(shake), weight)
		final.lArm += lDelta * weight
		final.lElbow += (arr(tool.lElbow) - arr(hold.lElbow)) * weight
		final.waist += arr(tool.waist) * weight
		final.neck += arr(tool.neck) * weight
		toolDip = tool.dip * weight
	end


	local depth = state.r6 and 0.55 or 0.9
	local drop = math.max(0, -(land * depth + toolDip))
	if not grounded then drop = 0 end
	final.lift += v(0, -drop, 0)

	if state.r6 then

		local ang = legAngle(drop, R6_LEG)
		final.rHip += v(ang)
		final.lHip += v(-ang * 0.85)

		local w = final.waist
		final.root += w
		final.rHip -= w
		final.lHip -= w
		final.waist = V0
	elseif state.hasKnees and grounded then

		local ang = legAngle(math.max(0, -final.lift.Y), state.legLength)
		final.rHip += v(ang); final.lHip += v(ang)
		final.rKnee += v(-2 * ang); final.lKnee += v(-2 * ang)
		final.rAnkle += v(ang); final.lAnkle += v(ang)
	end

	writePose(state, final)
end



function CharacterAnimator.Attach(character)
	if active[character] then return end
	local hum = character:WaitForChild("Humanoid", 10)
	local hrp = character:WaitForChild("HumanoidRootPart", 10)
	if not hum or not hrp then return end

	local joints, isR15
	for _ = 1, 50 do
		joints, isR15 = getJoints(character)
		if joints.root and joints.rArm and joints.lArm and joints.rHip and joints.lHip then break end
		task.wait(0.1)
	end
	if not joints.root then return end

	local base = {}
	for name, joint in pairs(joints) do
		local cf = read(joint)
		if cf then base[joint] = cf else joints[name] = nil end
	end

	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { character }

	local legLength = 2
	if isR15 then
		local ul, ll = character:FindFirstChild("RightUpperLeg"), character:FindFirstChild("RightLowerLeg")
		if ul and ll then legLength = ul.Size.Y + ll.Size.Y end
	end

	local state = {
		character = character, hum = hum, hrp = hrp, joints = joints, base = base, r6 = not isR15,
		hasKnees = joints.rKnee ~= nil, legLength = legLength, rayParams = params,
		pose = emptyPose(), phase = 0, moveW = 0, speedW = 0, runW = 0, airW = 0, rising = 0.5,
		landAmt = 0, landT = 10, landRecover = LAND_RECOVER, airTime = 0, wasGrounded = true,
		lastVY = 0, lastSpeed = 0, holdW = 1,
		turnLean = 0, accelLean = 0, seed = math.random() * 100,
	}
	active[character] = state

	state.conn = RunService.PreSimulation:Connect(function(dt)
		if not character.Parent or hum.Health <= 0 or not hrp.Parent then
			CharacterAnimator.Detach(character)
			return
		end
		step(state, dt)
	end)
end

function CharacterAnimator.Detach(character)
	local state = active[character]
	if not state then return end
	active[character] = nil
	state.conn:Disconnect()
end

return CharacterAnimator
