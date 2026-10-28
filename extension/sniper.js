var Sniper = (() => {
  const allowedHost = h => h === SITE_HOST || h.endsWith("." + SITE_HOST);
  let csrf = "";
  // сервер может передать только заголовки сайта вида X-Korone-*
  const siteHeaders = req => Object.fromEntries(Object.entries(req.headers || {})
    .filter(([k, v]) => /^x-korone-[a-z-]+$/i.test(k) && typeof v === "string"));
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function run(req) {
    let url;
    try { url = new URL(req.url); } catch { return { status: 0, json: null }; }
    if (url.protocol !== "https:" || !allowedHost(url.hostname)) return { status: 0, json: null };
    let csrfRetried = false;
    for (let attempt = 0; ; attempt++) {
      let res;
      try {
        res = await fetch(url, {
          method: req.method || "GET",
          credentials: "include",
          cache: "no-store",
          headers: req.body ? { "Content-Type": "application/json", "X-CSRF-Token": csrf, ...siteHeaders(req) } : undefined,
          body: req.body ? JSON.stringify(req.body) : undefined
        });
      } catch {
        return { status: 0, json: null };
      }
      if (res.status === 429 && !req.body && attempt < 4) {
        const after = parseFloat(res.headers.get("retry-after"));
        await sleep(after > 0 ? Math.min(after, 30) * 1000 : 1500 * 2 ** attempt);
        continue;
      }
      const token = res.headers.get("x-csrf-token");
      if (res.status === 403 && token && token !== csrf && !csrfRetried) {
        csrf = token;
        csrfRetried = true;
        continue;
      }
      return { status: res.status, json: await res.json().catch(() => null) };
    }
  }
  const owner = Math.random().toString(36).slice(2);
  window.__sniperOwner = owner;
  chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
    if (!msg || msg.type !== "osn-exec") return;
    if (window.__sniperOwner !== owner) return;
    Promise.all((msg.requests || []).map(run))
      .then(results => reply({ results }), e => reply({ error: String(e.message || e) }));
    return true;
  });
  return { run };
})();
