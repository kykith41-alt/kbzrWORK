const fields = document.querySelectorAll("[data-key]");
let settings = { ...SNIPER_DEFAULTS };
let saveTimer = 0;
function readField(el) {
  if (el.type === "checkbox") return el.checked;
  if (el.type === "number") return parseFloat(el.value) || 0;
  return el.value;
}
function render() {
  fields.forEach(el => {
    if (el === document.activeElement && el.type !== "checkbox") return;
    const v = settings[el.dataset.key];
    if (el.type === "checkbox") el.checked = !!v;
    else el.value = v;
  });
}
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => chrome.storage.sync.set(settings), 150);
}
fields.forEach(el => {
  el.addEventListener("input", () => {
    settings[el.dataset.key] = readField(el);
    render();
    save();
  });
});
document.getElementById("reset").addEventListener("click", () => {
  settings = { ...SNIPER_DEFAULTS };
  render();
  chrome.storage.sync.set(settings);
});
chrome.storage.sync.get(SNIPER_DEFAULTS, v => {
  settings = { ...SNIPER_DEFAULTS, ...v };
  render();
});
const SNIPER_STATE = { sniperStatus: null, sniperLog: [], sniperBought: 0 };
function timeText(ms) {
  return new Date(ms).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function renderSniper(st) {
  const status = document.getElementById("sniperStatus");
  if (!settings.sniper) {
    status.className = "status";
    status.textContent = "Off";
  } else if (st.sniperStatus) {
    status.className = "status " + (st.sniperStatus.ok ? "ok" : "err");
    status.textContent = timeText(st.sniperStatus.at) + " — " + st.sniperStatus.text;
  } else {
    status.className = "status";
    status.textContent = "Starting…";
  }
  document.getElementById("sniperCount").textContent = st.sniperBought + " / " + settings.sniperMaxBuys;
  const log = document.getElementById("sniperLog");
  log.textContent = "";
  for (const e of st.sniperLog) {
    const li = document.createElement("li");
    li.className = e.kind;
    const t = document.createElement("time");
    t.textContent = timeText(e.at);
    li.append(t, `${e.name}: ${e.text}`);
    log.appendChild(li);
  }
}
function loadSniper() {
  chrome.storage.local.get(SNIPER_STATE, renderSniper);
}
document.getElementById("sniperReset").addEventListener("click", () => {
  chrome.storage.local.set({ sniperBought: 0, sniperLog: [], sniperKnown: [], sniperStatus: null });
});
const licKey = document.getElementById("licKey");
const licSave = document.getElementById("licSave");
const licStatus = document.getElementById("licStatus");
function showLicense(text, cls) {
  licStatus.className = "status " + (cls || "");
  licStatus.textContent = text;
}
function renderLicense({ osnKey, osnLicense }) {
  const ok = !!(osnKey && osnLicense && osnLicense.ok);
  document.getElementById("app").hidden = !ok;
  if (document.activeElement !== licKey) licKey.value = osnKey;
  if (!osnKey) {
    showLicense("Enter your key to unlock the extension");
  } else if (osnLicense && osnLicense.ok) {
    const until = osnLicense.keyExpires
      ? " until " + new Date(osnLicense.keyExpires * 1000).toLocaleDateString("en-GB")
      : "";
    showLicense("Key active" + until, "ok");
  } else if (osnLicense) {
    showLicense(osnLicense.error, "err");
  } else {
    showLicense("Key not checked yet");
  }
}
function loadLicense() {
  chrome.storage.local.get({ osnKey: "", osnLicense: null }, renderLicense);
}
licSave.addEventListener("click", () => {
  const key = licKey.value.trim();
  if (!key) { showLicense("Paste your key", "err"); return; }
  licSave.disabled = true;
  showLicense("Checking…");
  chrome.runtime.sendMessage({ type: "osn-activate", key }, res => {
    licSave.disabled = false;
    if (chrome.runtime.lastError || !res) showLicense("No response from the extension", "err");
    else if (res.error) showLicense(res.error, "err");
    else loadLicense();
  });
});
loadLicense();
chrome.storage.onChanged.addListener((_, area) => {
  if (area === "local") { loadSniper(); loadLicense(); }
});
fields.forEach(el => el.addEventListener("input", loadSniper));
chrome.storage.sync.get(SNIPER_DEFAULTS, loadSniper);
