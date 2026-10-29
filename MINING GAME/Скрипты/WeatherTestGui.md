---
тип: LocalScript
где: StarterPlayerScripts
система: "[[Погода]]"
tags: [скрипт, LocalScript]
---
# WeatherTestGui

**Тип:** LocalScript · **Где:** `StarterPlayerScripts` · **Система:** [[Погода]]

Тестовая панель погоды: текущая погода, время до смены, кнопки Default/Sunny/Rain/Rainstorm. Видна только в Studio и владельцу.



## Связано
- [[WeatherServer]]
- [[WeatherClient]]

## Код
```lua
-- Тестовая панель погоды: текущая погода, время до смены, кнопки для переключения.
-- Видна только в Studio и владельцу игры.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
if not (RunService:IsStudio() or player.UserId == game.CreatorId) then return end

local remote = ReplicatedStorage:WaitForChild("WeatherRemote")
local weatherRoot = script.Parent:WaitForChild("Weather")
local FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Bold)

local screen = Instance.new("ScreenGui")
screen.Name = "WeatherTestGui"
screen.ResetOnSpawn = false
screen.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("Frame")
panel.AnchorPoint = Vector2.new(1, 0)
panel.Position = UDim2.new(1, -12, 0, 60)
panel.Size = UDim2.fromOffset(190, 0)
panel.AutomaticSize = Enum.AutomaticSize.Y
panel.BackgroundColor3 = Color3.fromRGB(25, 28, 34)
panel.BackgroundTransparency = 0.15
panel.Parent = screen
Instance.new("UICorner", panel).CornerRadius = UDim.new(0, 8)
local pad = Instance.new("UIPadding")
pad.PaddingTop, pad.PaddingBottom = UDim.new(0, 8), UDim.new(0, 8)
pad.PaddingLeft, pad.PaddingRight = UDim.new(0, 8), UDim.new(0, 8)
pad.Parent = panel
local list = Instance.new("UIListLayout")
list.Padding = UDim.new(0, 5)
list.SortOrder = Enum.SortOrder.LayoutOrder
list.Parent = panel

local function label(text, size, order)
	local l = Instance.new("TextLabel")
	l.BackgroundTransparency = 1
	l.Size = UDim2.new(1, 0, 0, size + 4)
	l.FontFace = FONT
	l.TextSize = size
	l.TextColor3 = Color3.new(1, 1, 1)
	l.TextXAlignment = Enum.TextXAlignment.Left
	l.Text = text
	l.LayoutOrder = order
	l.Parent = panel
	return l
end

label("Weather test", 16, 1)
local current = label("Сейчас: —", 15, 2)
local timer = label("Смена через: —", 13, 3)
timer.TextColor3 = Color3.fromRGB(180, 190, 205)

local buttons = {}
local function button(text, order, onClick)
	local b = Instance.new("TextButton")
	b.Size = UDim2.new(1, 0, 0, 26)
	b.BackgroundColor3 = Color3.fromRGB(55, 62, 75)
	b.AutoButtonColor = true
	b.FontFace = FONT
	b.TextSize = 14
	b.TextColor3 = Color3.new(1, 1, 1)
	b.Text = text
	b.LayoutOrder = order
	b.Parent = panel
	Instance.new("UICorner", b).CornerRadius = UDim.new(0, 6)
	b.Activated:Connect(onClick)
	return b
end

local names = { "Default" }
for _, f in ipairs(weatherRoot:GetChildren()) do
	if f:IsA("Folder") and f.Name ~= "Default" then table.insert(names, f.Name) end
end
table.sort(names)
for i, name in ipairs(names) do
	buttons[name] = button(name, 10 + i, function() remote:FireServer(name) end)
end
button("Следующая ▶", 100, function() remote:FireServer("__next") end)

local function refresh()
	local name = ReplicatedStorage:GetAttribute("Weather") or "—"
	current.Text = "Сейчас: " .. name
	for n, b in pairs(buttons) do
		b.BackgroundColor3 = n == name and Color3.fromRGB(70, 150, 80) or Color3.fromRGB(55, 62, 75)
	end
end
ReplicatedStorage:GetAttributeChangedSignal("Weather"):Connect(refresh)
refresh()

RunService.Heartbeat:Connect(function()
	local changedAt = ReplicatedStorage:GetAttribute("WeatherChangedAt")
	local duration = ReplicatedStorage:GetAttribute("WeatherDuration")
	if not changedAt or not duration then return end
	local left = math.max(0, duration - (workspace:GetServerTimeNow() - changedAt))
	timer.Text = string.format("Смена через: %d:%02d", math.floor(left / 60), math.floor(left % 60))
end)
```
