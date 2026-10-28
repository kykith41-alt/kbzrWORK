# Memora Sniper

Снайпер лимиток для memora.zip: расширение (`extension/`) + сервер лицензий и логики (`server/server.py`).

## Как работает
1. Расширение раз в N секунд просит сервер `/api/job` с `op: "snipe"`.
2. Сервер отвечает списком запросов к API сайта; расширение выполняет их во вкладке memora.zip
   (с вашими куками и CSRF-токеном) и отправляет ответы обратно.
3. Сервер выбирает лимитки по цене/валюте/ключевым словам и отдаёт команду на покупку.

## API сайта
Все адреса в одном месте: блок `MEMORA` в `server/server.py`
(`SITE_BASE`, `API_BASE`, `URL_LIMITEDS`, `URL_DETAILS`, `URL_PURCHASE`).
По умолчанию это Roblox-совместимые пути под `/apisite` — **их нужно проверить**:
откройте memora.zip, F12 → Console, вставьте `tools/probe.js`. Скрипт покажет,
какие пути отвечают JSON-ом. Путь покупки удобнее подсмотреть во вкладке Network,
купив любой бесплатный предмет вручную.

Базу можно сменить без правки кода: `API_BASE=https://memora.zip/api python3 server.py`.

## Смена сайта
- `extension/defaults.js` → `SITE_HOST`
- `extension/manifest.json` → `host_permissions` и `content_scripts.matches`
- `server/server.py` → `SITE_BASE` / `API_BASE`

## Ключи
`python3 server/server.py new 30` — ключ на 30 дней (`new` без числа — навсегда),
`list`, `revoke KEY`, `reset KEY`, `delete KEY`.
