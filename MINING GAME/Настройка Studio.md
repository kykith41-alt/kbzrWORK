---
tags: [гайд]
---
# Настройка Studio

## Workspace
- `Workspace → Mine → MineArea` — большой Part, весь объём шахты. Без поворота, размеры кратны 4 (например `56, 100, 56`). Прозрачность и коллизии [[MineServer]] ставит сам.

## ReplicatedStorage
- ModuleScript: [[MiningShared]], [[MiningFX]], [[SwingAnimation]], [[CharacterAnimator]].
- Шаблоны частиц: `Slash`, `Break`, `Lvlup` — см. [[Эффекты частиц]].
- `MineAssets` — меши `Spots_A/B/C` для руды.

## ServerScriptService
- [[MineServer]], [[Nameplates]], [[CollisionSetup]], [[WeatherServer]].
- Старый серверный `LevelUpFX` удалить (теперь он LocalScript).

## StarterPlayerScripts
- [[MiningEffects]], [[MiningHUD]], [[LevelBar]], [[LevelUpFX]], [[CapacityOrb]], [[PickaxeClient]], [[PickaxeSheath]], [[NameplateFX]], [[MineRangeRing]], [[FootstepSounds]], [[WeatherClient]], [[WeatherTestGui]].
- Пустой LocalScript `RbxCharacterSounds` — выключает стандартные звуки персонажа Roblox.
- Папка `Weather` с подпапками `Sunny`, `Rain`, `Rainstorm` (в каждой Effects и Properties).

## Lighting
- Настрой один раз через [[GraphicsCommandBar]]. `Technology` — вручную в свойствах.

← [[Главная]]
