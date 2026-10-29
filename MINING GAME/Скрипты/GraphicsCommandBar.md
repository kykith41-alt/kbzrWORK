---
тип: Command Bar
где: View → Command Bar (один раз)
система: "[[Графика]]"
tags: [скрипт, CommandBar]
---
# GraphicsCommandBar

**Тип:** Command Bar · **Где:** `View → Command Bar (один раз)` · **Система:** [[Графика]]

Настройка графики через Command Bar: эффекты Lighting (Bloom, ColorCorrection, SunRays и т.д.). Не трогает небо, атмосферу, время суток и `Technology`.

## Заметки
- `Technology` из Command Bar менять нельзя — ставь вручную в свойствах Lighting.

## Связано
- [[WeatherClient]]

## Код
```lua
local L = game:GetService("Lighting")
local function get(className)
	local obj = L:FindFirstChildOfClass(className)
	if not obj then
		obj = Instance.new(className)
		obj.Parent = L
	end
	return obj
end

-- мягкие тени и чуть ярче картинка
L.GlobalShadows = true
L.ShadowSoftness = 0.3
L.ExposureCompensation = 0.3
L.EnvironmentDiffuseScale = 0.5
L.EnvironmentSpecularScale = 0.3

-- сочные мультяшные цвета
local cc = get("ColorCorrectionEffect")
cc.Brightness = 0.03
cc.Contrast = 0.15
cc.Saturation = 0.35

-- свечение вокруг неона и ламп
local bloom = get("BloomEffect")
bloom.Intensity = 0.8
bloom.Size = 30
bloom.Threshold = 1.2
```
