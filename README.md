# Memora Sniper

Снайпер лимиток для memora.zip: расширение (`extension/`) + сервер лицензий и логики (`server/server.py`).

## Как работает
1. Расширение раз в N секунд просит сервер `/api/job` с `op: "snipe"`.
2. Сервер отвечает списком запросов к API сайта; расширение выполняет их во вкладке memora.zip
   (с вашими куками и CSRF-токеном) и отправляет ответы обратно.
3. Сервер выбирает лимитки по цене/валюте/ключевым словам и отдаёт команду на покупку.

## API сайта (проверено на memora.zip)
Все адреса — в блоке `MEMORA` в `server/server.py`, база `https://memora.zip/apisite`.
- список лимиток: `GET /catalog/v1/search/items?category=Collectibles&sortType=3`
- данные предметов: `POST /catalog/v1/catalog/items/details` — `productId` нет, покупка идёт по id ассета
- покупка в два шага, как на сайте:
  1. `POST /economy/v1/purchases/products/{id}/handshake` `{tToken}` → `{token}`
  2. `POST /economy/v1/purchases/products/{id}` с заголовком `X-Korone-Ticket: <token>`

`tToken` — токен Cloudflare Turnstile. Снайпер отправляет `null`; если сайт включит
обязательную капчу, handshake вернёт ошибку и снайпер покажет её в статусе.

`tools/probe*.js` — скрипты для консоли браузера, которыми проверялся API.

## Смена сайта
- `extension/defaults.js` → `SITE_HOST`
- `extension/manifest.json` → `host_permissions` и `content_scripts.matches`
- `server/server.py` → `SITE_BASE` / `API_BASE`

## Ключи
`python3 server/server.py new 30` — ключ на 30 дней (`new` без числа — навсегда),
`list`, `revoke KEY`, `reset KEY`, `delete KEY`.
