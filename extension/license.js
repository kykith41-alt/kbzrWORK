var OSN_SERVER = "http://fi13.bot-hosting.cloud:25537";
var OsnLicense = (() => {
  const get = keys => new Promise(r => chrome.storage.local.get(keys, r));
  const set = v => new Promise(r => chrome.storage.local.set(v, r));
  
  async function device() {
    let { osnDevice } = await get({ osnDevice: "" });
    if (!osnDevice) {
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      osnDevice = [...bytes].map(b => b.toString(16).padStart(2, "0")).join("");
      await set({ osnDevice });
    }
    return osnDevice;
  }

  async function post(path, body, headers) {
    let r;
    try {
      r = await fetch(OSN_SERVER + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify(body)
      });
    } catch { throw new Error("License server is unreachable"); }
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const e = new Error(data.error || "Server error " + r.status);
      e.status = r.status;
      throw e;
    }
    return data;
  }

  async function token(force) {
    const { osnKey, osnToken } = await get({ osnKey: "", osnToken: null });
    if (!osnKey) throw new Error("License key required — enter it in the extension menu");
    if (!force && osnToken && osnToken.exp - Date.now() / 1000 > 120) return osnToken.token;
    try {
      const r = await post("/api/auth", { key: osnKey, device: await device() }, {});
      await set({ osnToken: { token: r.token, exp: r.exp }, osnLicense: { ok: true, keyExpires: r.keyExpires, at: Date.now() } });
      return r.token;
    } catch (e) {
      if (e.status) await set({ osnToken: null, osnLicense: { ok: false, error: e.message, at: Date.now() } });
      throw e;
    }
  }

  async function activate(key) {
    await set({ osnKey: key.trim().toUpperCase(), osnToken: null, osnLicense: null });
    await token(true);
  }

  async function call(path, body) {
    const dev = await device();
    for (let attempt = 0; ; attempt++) {
      const t = await token(attempt > 0);
      try {
        return await post(path, body, { Authorization: "Bearer " + t, "X-Device": dev });
      } catch (e) {
        if (e.status !== 401 || attempt) throw e;
      }
    }
  }
  
  return { activate, token, call };
})();
