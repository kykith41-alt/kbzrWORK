// Проверка API memora.zip. Откройте memora.zip (войдите в аккаунт),
// F12 → Console, вставьте этот файл целиком и нажмите Enter.
// Скрипт только читает данные (GET и details), ничего не покупает.
(async () => {
  const bases = ["/apisite", "/api", ""];
  const tests = [
    ["me", "GET", "/users/v1/users/authenticated"],
    ["limiteds", "GET", "/catalog/v1/search/items?category=Collectibles&limit=10&sortType=3"],
    ["catalog v3", "GET", "/catalog/v3/search/items?category=0&limit=10&sortType=0&creatorType=1&minPrice=0"],
    ["details", "POST", "/catalog/v1/catalog/items/details"]
  ];
  const csrf = { token: "" };
  async function call(method, url, body) {
    for (let i = 0; i < 2; i++) {
      const r = await fetch(url, {
        method, credentials: "include",
        headers: body ? { "Content-Type": "application/json", "X-CSRF-Token": csrf.token } : undefined,
        body: body ? JSON.stringify(body) : undefined
      });
      const t = r.headers.get("x-csrf-token");
      if (r.status === 403 && t && t !== csrf.token) { csrf.token = t; continue; }
      return { status: r.status, text: await r.text() };
    }
  }
  const out = [];
  let sampleId = null;
  for (const base of bases) {
    for (const [name, method, path] of tests) {
      const url = location.origin + base + path;
      let body;
      if (name === "details") {
        if (!sampleId) continue;
        body = { items: [{ itemType: "Asset", id: sampleId }] };
      }
      try {
        const r = await call(method, url, body);
        let json = null;
        try { json = JSON.parse(r.text); } catch {}
        if (json && !sampleId && Array.isArray(json.data) && json.data[0] && json.data[0].id) sampleId = json.data[0].id;
        out.push({ name, method, url, status: r.status, json: !!json, sample: r.text.slice(0, 300) });
      } catch (e) {
        out.push({ name, method, url, status: "ERR", json: false, sample: String(e) });
      }
    }
  }
  console.table(out.map(({ sample, ...r }) => r));
  const report = JSON.stringify(out, null, 1);
  console.log(report);
  try { await navigator.clipboard.writeText(report); console.log("Отчёт скопирован в буфер обмена"); } catch {}
})();
