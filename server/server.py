import base64
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "keys.db")
SECRET_PATH = os.path.join(HERE, "secret.key")
PORT = int(os.environ.get("SERVER_PORT") or os.environ.get("PORT") or 8080)

TOKEN_TTL = 10 * 60
BAN_DEVICES = 2
MAX_BODY = 2_000_000

db_lock = threading.Lock()

def load_secret():
    if not os.path.exists(SECRET_PATH):
        with open(SECRET_PATH, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_PATH) as f:
        return bytes.fromhex(f.read().strip())

SECRET = load_secret()

def open_db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY, created INTEGER NOT NULL, expires INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active', device TEXT, bound_at INTEGER, last_seen INTEGER, last_ip TEXT
        );
        CREATE TABLE IF NOT EXISTS foreign_tries (
            key TEXT NOT NULL, device TEXT NOT NULL, at INTEGER NOT NULL, ip TEXT
        );
    """)
    return con

db = open_db()

def q(sql, args=(), one=False):
    with db_lock:
        cur = db.execute(sql, args)
        db.commit()
        rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows

def now(): return int(time.time())
def device_hash(device): return hashlib.sha256(("osn-device:" + device).encode()).hexdigest()
def new_key():
    raw = secrets.token_hex(8).upper()
    return "ECHO-" + "-".join(raw[i:i + 4] for i in range(0, 16, 4))

def key_problem(row):
    if row is None: return "Key not found"
    if row["status"] == "revoked": return "Key disabled"
    if row["status"] == "banned": return "Key banned"
    if row["expires"] and row["expires"] < now(): return "Key expired"
    return None

def note_foreign(key, dev, ip):
    t = now()
    q("INSERT INTO foreign_tries (key, device, at, ip) VALUES (?, ?, ?, ?)", (key, dev, t, ip))
    n = q("SELECT COUNT(DISTINCT device) AS n FROM foreign_tries WHERE key = ? AND at > ?", (key, t - 86400), one=True)["n"]
    if n >= BAN_DEVICES:
        q("UPDATE keys SET status = 'banned' WHERE key = ?", (key,))

def b64(data): return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
def unb64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def make_token(key, dev):
    exp = now() + TOKEN_TTL
    body = b64(json.dumps({"k": key, "d": dev, "e": exp}, separators=(",", ":")).encode())
    sig = b64(hmac.new(SECRET, body.encode(), hashlib.sha256).digest())
    return body + "." + sig, exp

def check_token(token, device):
    try:
        body, sig = token.split(".")
        good = b64(hmac.new(SECRET, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good): return None, "bad token"
        data = json.loads(unb64(body))
    except Exception: return None, "bad token"
    if data["e"] < now(): return None, "token expired"
    if data["d"] != device_hash(device or ""): return None, "bad token"
    row = q("SELECT * FROM keys WHERE key = ?", (data["k"],), one=True)
    problem = key_problem(row)
    if problem: return None, problem
    if row["device"] != data["d"]: return None, "Key is bound to another device"
    return data["k"], None

class JobError(Exception): pass
def is_num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return math.nan

def get(url): return {"url": url}
def post(url, body): return {"url": url, "method": "POST", "body": body}

def need_json(r, url):
    if not isinstance(r, dict) or not (200 <= (r.get("status") or 0) < 300):
        raise JobError(f"HTTP Error {r.get('status') if isinstance(r, dict) else 'unknown'} on {url}")
    if r.get("json") is None: raise JobError("No JSON in response")
    return r["json"]

def fetch_json(url):
    (r,) = yield [get(url)]
    return need_json(r, url)

# ---------- MEMORA ----------
# Все адреса сайта здесь. Пути — Roblox-совместимый API, как у большинства ревайвов.
# Проверьте их скриптом tools/probe.js на memora.zip и поправьте, если отличаются.
SITE_BASE = os.environ.get("SITE_BASE", "https://memora.zip")
API_BASE = os.environ.get("API_BASE", SITE_BASE + "/apisite")

URL_LIMITEDS = f"{API_BASE}/catalog/v1/search/items?category=Collectibles&limit=120&sortType=3"
URL_DETAILS = f"{API_BASE}/catalog/v1/catalog/items/details"
URL_PURCHASE = API_BASE + "/economy/v1/purchases/products/{pid}"
URL_HANDSHAKE = URL_PURCHASE + "/handshake"

ROBUX, TICKETS = 1, 2
SNIPE_CHECK = 30
KNOWN_SIZE = 500

def is_limited(d):
    r = d.get("itemRestrictions") or []
    return bool(d.get("isLimited") or d.get("isLimitedUnique") or "Limited" in r or "LimitedUnique" in r)

def for_sale(d):
    if "isForSale" in d: return bool(d["isForSale"])
    return is_num(d.get("price")) and d.get("priceStatus") != "Off Sale"

def details(ids):
    payload = {"items": [{"itemType": "Asset", "id": int(i)} for i in ids]}
    (r,) = yield [post(URL_DETAILS, payload)]
    j = need_json(r, URL_DETAILS)
    return [d for d in (j.get("data") or []) if isinstance(d, dict)]

def error_text(r):
    status = r.get("status") if isinstance(r, dict) else 0
    j = r.get("json") if isinstance(r, dict) else None
    return (isinstance(j, dict) and (j.get("reason") or j.get("errorMsg") or
            ((j.get("errors") or [{}])[0].get("message")))) or f"response {status}"

def purchase(product_id, asset_id, price, seller_id, currency):
    # Как на сайте: handshake выдаёт одноразовый билет, покупка идёт с X-Korone-Ticket.
    # tToken — токен Cloudflare Turnstile; если сайт его требует, handshake вернёт ошибку.
    pid = int(product_id)
    (r,) = yield [post(URL_HANDSHAKE.format(pid=pid), {"tToken": None})]
    j = r.get("json") if isinstance(r, dict) else None
    ticket = isinstance(j, dict) and j.get("token")
    if not (200 <= (r.get("status") or 0) < 300) or not ticket:
        return {"ok": False, "handshake": True, "reason": "handshake: " + error_text(r)}
    payload = {"assetId": int(asset_id), "expectedPrice": int(price), "expectedSellerId": int(seller_id),
               "userAssetId": None, "expectedCurrency": currency}
    (r,) = yield [{**post(URL_PURCHASE.format(pid=pid), payload), "headers": {"X-Korone-Ticket": ticket}}]
    j = r.get("json") if isinstance(r, dict) else None
    ok = 200 <= (r.get("status") or 0) < 300 and isinstance(j, dict) and j.get("purchased") is True
    return {"ok": ok, "reason": "ok" if ok else error_text(r)}

def to_int(v, default):
    n = num(v)
    return int(n) if math.isfinite(n) else default

def keywords(cfg):
    return [w.lower() for w in re.split(r"[,\n]+", str(cfg.get("sniperKeywords") or "")) if w.strip()]

def pick_price(d, cfg):
    """Возвращает (цена, валюта) по настройкам или None, если дорого."""
    r, t = d.get("price"), d.get("priceTickets")
    if d.get("isOnSale"):
        if is_num(d.get("salePriceRobux")): r = d["salePriceRobux"]
        if is_num(d.get("salePriceTix")): t = d["salePriceTix"]
    cur = cfg.get("sniperCurrency") or "robux"
    max_r, max_t = num(cfg.get("sniperMaxRobux", 50)), num(cfg.get("sniperMaxTickets", 500))
    if cur in ("robux", "any") and is_num(r) and r <= max_r: return r, ROBUX
    if cur in ("tickets", "any") and is_num(t) and t <= max_t: return t, TICKETS
    return None

def job_snipe(a, key):
    cfg = a.get("cfg") or {}
    st = a.get("st") or {}
    count = to_int(st.get("sniperBought"), 0)
    max_buys = to_int(cfg.get("sniperMaxBuys"), 5)
    known = [str(x) for x in (st.get("sniperKnown") or [])]
    words = keywords(cfg)
    log, bought = [], []
    ok, text = True, ""

    def done():
        return {"state": {"sniperStatus": {"at": int(time.time() * 1000), "ok": ok, "text": text},
                          "sniperBought": count, "sniperKnown": known[-KNOWN_SIZE:]},
                "bought": bought, "log": log}

    if count >= max_buys:
        text = f"Buy limit reached ({count}/{max_buys})"
        return done()
    try:
        lst = yield from fetch_json(URL_LIMITEDS)
        ids = [str(x.get("id")) for x in (lst.get("data") or []) if x.get("id")]
        ids = [i for i in ids if i not in known][:SNIPE_CHECK]
        items = (yield from details(ids)) if ids else []
        for d in items:
            if count >= max_buys: break
            name = d.get("name") or "#" + str(d.get("id"))
            if not is_limited(d) or not for_sale(d) or d.get("unitsAvailableForConsumption") == 0: continue
            if words and not any(w in name.lower() for w in words): continue
            choice = pick_price(d, cfg)
            seller = d.get("creatorTargetId") or d.get("expectedSellerId")
            # memora не отдаёт productId — покупка идёт по id ассета
            product = d.get("productId") or d.get("id")
            if not choice or not seller or not product: continue
            price, cur = choice
            res = yield from purchase(product, d["id"], price, seller, cur)
            if res.get("handshake"):
                # покупка сейчас невозможна ни для одного предмета — не помечаем, повторим позже
                log.append({"kind": "fail", "name": name, "text": res["reason"]})
                raise JobError(res["reason"])
            known.append(str(d.get("id")))
            sign = "R$" if cur == ROBUX else "Tx"
            if res["ok"]:
                count += 1
                bought.append(name)
                log.append({"kind": "buy", "name": name, "text": f"bought for {price} {sign}"})
            else:
                log.append({"kind": "fail", "name": name, "text": res["reason"]})
        text = f"Checked {len(items)}, bought {len(bought)}"
    except JobError as e:
        ok, text = False, str(e)
    return done()

# ---------- РОУТИНГ ЗАДАЧ ----------
JOBS = {"snipe": job_snipe}
running = {}
running_lock = threading.Lock()

def run_job(key, body):
    if body.get("job"):
        with running_lock: job = running.pop(str(body["job"]), None)
        if not job or job["key"] != key or job["until"] < time.time(): raise JobError("Task expired")
        results = body.get("results")
        gen = job["gen"]
    else:
        fn = JOBS.get(body.get("op"))
        if not fn: raise JobError("Unknown task")
        args = body.get("args")
        gen = fn(args if isinstance(args, dict) else {}, key)
        results = None
    try: reqs = gen.send(results)
    except StopIteration as stop: return {"done": stop.value}
    
    job_id = secrets.token_hex(12)
    t = time.time()
    with running_lock:
        for k in [k for k, v in running.items() if v["until"] < t]: del running[k]
        running[job_id] = {"gen": gen, "key": key, "until": t + 120, "n": len(reqs)}
    return {"job": job_id, "requests": reqs}

class Handler(BaseHTTPRequestHandler):
    server_version = "osn"
    sys_version = ""

    def log_message(self, *a): pass
    def ip(self): return self.client_address[0]
    def send(self, code, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Device")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        if self.path == "/": return self.send(200, {"ok": True})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY: return self.send(413, {"error": "too big"})
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self.send(400, {"error": "bad json"})

        if self.path == "/api/auth":
            return self.auth(body)

        key, err = check_token((self.headers.get("Authorization") or "").replace("Bearer ", ""), self.headers.get("X-Device"))
        if not key: return self.send(401, {"error": err})
        q("UPDATE keys SET last_seen = ?, last_ip = ? WHERE key = ?", (now(), self.ip(), key))

        if self.path == "/api/job":
            try: return self.send(200, run_job(key, body))
            except JobError as e: return self.send(422, {"error": str(e)})
            except Exception as e:
                log(f"Ошибка: {e!r}")
                return self.send(500, {"error": str(e)})
        self.send(404, {"error": "not found"})

    def auth(self, body):
        key = str(body.get("key") or "").strip().upper()
        device = str(body.get("device") or "")
        if len(device) < 16: return self.send(400, {"error": "bad device"})
        dev = device_hash(device)

        row = q("SELECT * FROM keys WHERE key = ?", (key,), one=True)
        problem = key_problem(row)
        if problem: return self.send(403, {"error": problem})
        
        if row["device"] is None:
            q("UPDATE keys SET device = ?, bound_at = ? WHERE key = ?", (dev, now(), key))
        elif row["device"] != dev:
            note_foreign(key, dev, self.ip())
            return self.send(403, {"error": "Key bound to another device"})

        q("UPDATE keys SET last_seen = ?, last_ip = ? WHERE key = ?", (now(), self.ip(), key))
        
        token, exp = make_token(key, dev)
        self.send(200, {"token": token, "exp": exp, "keyExpires": row["expires"] or None})

def log(text): print(time.strftime("[%H:%M:%S] ") + text, flush=True)
def fmt_time(t): return time.strftime("%d.%m.%Y %H:%M", time.localtime(t)) if t else "—"
def describe(r):
    exp = "навсегда" if not r["expires"] else "до " + fmt_time(r["expires"])
    bound = "привязан " + fmt_time(r["bound_at"]) if r["device"] else "не активирован"
    return f"{r['key']}  {r['status']}, {exp}, {bound}"

def run_command(line):
    parts = line.split()
    if not parts: return
    cmd, args = parts[0].lower(), parts[1:]
    key = args[0].upper() if args else ""

    if cmd == "new":
        days = int(args[0]) if args and args[0].isdigit() else 0
        k = new_key()
        q("INSERT INTO keys (key, created, expires) VALUES (?, ?, ?)", (k, now(), now() + days * 86400 if days else 0))
        log(f"Новый ключ: {k}")
    elif cmd == "list":
        rows = q("SELECT * FROM keys ORDER BY created")
        for r in rows: print(describe(r), flush=True)
    elif cmd == "revoke":
        q("UPDATE keys SET status = 'revoked' WHERE key = ?", (key,)); log("Отключен")
    elif cmd == "reset":
        q("UPDATE keys SET device = NULL, bound_at = NULL, status = 'active' WHERE key = ?", (key,)); log("Сброшен")
    elif cmd == "delete":
        q("DELETE FROM keys WHERE key = ?", (key,)); log("Удален")

def console():
    for line in sys.stdin:
        try: run_command(line.strip())
        except Exception as e: log("Ошибка: " + str(e))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_command(" ".join(sys.argv[1:]))
        sys.exit(0)
    threading.Thread(target=console, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log(f"Сервер запущен на порту {PORT}")
    server.serve_forever()
