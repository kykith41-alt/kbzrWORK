if (typeof SNIPER_DEFAULTS === "undefined") importScripts("defaults.js", "license.js");
const SITE_TABS = ["*://" + SITE_HOST + "/*", "*://*." + SITE_HOST + "/*"];
const LOG_SIZE = 40;
let looping = false;
const getStore = (area, keys) => new Promise(r => chrome.storage[area].get(keys, r));
const sleep = ms => new Promise(r => setTimeout(r, ms));

function badge(text, color) {
  chrome.action.setBadgeText({ text });
  if (color) chrome.action.setBadgeBackgroundColor({ color });
}

async function setStatus(text) {
  await chrome.storage.local.set({ sniperStatus: { at: Date.now(), ok: false, text } });
  badge("!", "#d33");
}

function askTab(tab, msg) { return chrome.tabs.sendMessage(tab.id, msg, { frameId: 0 }); }

async function askAnyTab(msg) {
  const all = await chrome.tabs.query({ url: SITE_TABS });
  const tabs = all.filter(t => !t.discarded).sort((a, b) => b.active - a.active);
  if (!tabs.length) return { err: "Open " + SITE_HOST + " in any tab" };
  let lastErr = "";
  for (const tab of tabs) {
    try {
      const res = await askTab(tab, msg);
      if (res) return { res };
      lastErr = "the tab did not respond";
    } catch (e) {
      lastErr = e.message;
      try {
        await chrome.scripting.executeScript({ target: { tabId: tab.id, frameIds: [0] }, files: ["defaults.js", "sniper.js"] });
        const res = await askTab(tab, msg);
        if (res) return { res };
        lastErr = "the tab did not respond";
      } catch (e2) { lastErr = e2.message; }
    }
  }
  return { err: "Couldn't reach the tab: " + lastErr };
}

async function addLog(entries) {
  if (!entries || !entries.length) return;
  const { sniperLog } = await getStore("local", { sniperLog: [] });
  for (const e of entries) sniperLog.unshift({ at: Date.now(), ...e });
  sniperLog.length = Math.min(sniperLog.length, LOG_SIZE);
  await chrome.storage.local.set({ sniperLog });
}

async function runJob(op, args) {
  let r = await OsnLicense.call("/api/job", { op, args });
  while (r.requests) {
    const { res, err } = await askAnyTab({ type: "osn-exec", requests: r.requests });
    if (!res) throw new Error(err);
    if (res.error) throw new Error(res.error);
    r = await OsnLicense.call("/api/job", { job: r.job, results: res.results });
  }
  const { log, ...done } = r.done;
  await addLog(log);
  return done;
}

async function tick() {
  const cfg = await getStore("sync", SNIPER_DEFAULTS);
  const st = await getStore("local", { sniperBought: 0, sniperKnown: [] });
  let out;
  try {
    out = await runJob("snipe", { cfg, st });
  }
  catch (e) {
    await setStatus(String(e.message || e));
    return;
  }
  await chrome.storage.local.set(out.state);
  if (out.state.sniperStatus.ok) badge("ON", "#2a8"); else badge("!", "#d33");
  for (const b of out.bought) {
    chrome.notifications.create({ type: "basic", iconUrl: "icons/icon128.png", title: "Item bought!", message: `${b}` });
  }
}

async function loop() {
  if (looping) return;
  looping = true;
  try {
    for (;;) {
      const cfg = await getStore("sync", SNIPER_DEFAULTS);
      if (!cfg.sniper) break;
      const started = Date.now();
      try { await tick(); } catch (e) { await setStatus(String(e.message || e)); }
      const every = Math.max(1, Number(cfg.sniperInterval) || 3) * 1000;
      await sleep(Math.max(300, every - (Date.now() - started)));
    }
  } finally {
    looping = false;
    badge("");
  }
}

chrome.alarms.create("osn-sniper", { periodInMinutes: 0.5 });
function refreshLicense() { OsnLicense.token().catch(() => {}); }
chrome.alarms.onAlarm.addListener(a => {
  if (a.name !== "osn-sniper") return;
  refreshLicense();
  loop();
});
chrome.runtime.onStartup.addListener(loop);
chrome.runtime.onInstalled.addListener(loop);
chrome.storage.onChanged.addListener((_, area) => { if (area === "sync") loop(); });
chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (!msg || msg.type !== "osn-activate") return;
  OsnLicense.activate(String(msg.key || "")).then(() => reply({ ok: true }), e => reply({ error: String(e.message || e) }));
  return true;
});

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (!msg || msg.type !== "osn-testbuy") return;
  getStore("sync", SNIPER_DEFAULTS)
    .then(cfg => runJob("test_buy", { id: msg.id, cfg }))
    .then(({ result }) => {
      if (result.ok) chrome.notifications.create({ type: "basic", iconUrl: "icons/icon128.png", title: "Test buy OK", message: `${result.name}: ${result.text}` });
      reply(result);
    }, e => reply({ ok: false, text: String(e.message || e) }));
  return true;
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && new URL(tab.url).hostname.endsWith(SITE_HOST)) {
    OsnLicense.token(true).catch(() => {});
  }
});

refreshLicense();
loop();
