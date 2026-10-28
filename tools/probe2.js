// Второй шаг проверки API memora.zip. Откройте страницу любого предмета в каталоге
// memora.zip (чтобы загрузились скрипты покупки), F12 → Console, вставьте файл и Enter.
// Скрипт только читает данные, ничего не покупает.
(async () => {
  const API = location.origin + "/apisite";
  let csrf = "";
  async function call(method, url, body) {
    for (let i = 0; i < 2; i++) {
      const r = await fetch(url, {
        method, credentials: "include",
        headers: body ? { "Content-Type": "application/json", "X-CSRF-Token": csrf } : undefined,
        body: body ? JSON.stringify(body) : undefined
      });
      const t = r.headers.get("x-csrf-token");
      if (r.status === 403 && t && t !== csrf) { csrf = t; continue; }
      let json = null;
      const text = await r.text();
      try { json = JSON.parse(text); } catch {}
      return { status: r.status, json, text: json ? undefined : text.slice(0, 200) };
    }
  }
  const report = {};

  // 1. Полные details для первых лимиток (поля цены, productId, остаток)
  const list = await call("GET", API + "/catalog/v1/search/items?category=Collectibles&limit=5&sortType=3");
  const ids = ((list.json && list.json.data) || []).map(x => x.id);
  const det = await call("POST", API + "/catalog/v1/catalog/items/details",
    { items: ids.map(id => ({ itemType: "Asset", id })) });
  report.details = det.json;

  // 2. Цена/продавцы для первой лимитки — пробуем типичные адреса
  const id = ids[0];
  report.extra = {};
  for (const path of [
    `/economy/v1/assets/${id}/resellers?limit=3`,
    `/economy/v1/assets/${id}/resale-data`,
    `/marketplace/v1/items/${id}`,
    `/catalog/v1/assets/${id}/bundles`
  ]) {
    const r = await call("GET", API + path);
    report.extra[path] = { status: r.status, body: r.json ?? r.text };
  }

  // 3. Ищем адреса покупки в JS-файлах сайта
  const scripts = new Set([
    ...[...document.scripts].map(s => s.src),
    ...performance.getEntriesByType("resource").map(e => e.name)
  ].filter(u => u && u.startsWith(location.origin) && /\.js(\?|$)/.test(u)));
  const found = new Set();
  const re = /["'`][^"'`\s]{0,80}(purchase|buy|resell|economy|transaction)[^"'`\s]{0,80}["'`]/gi;
  for (const src of scripts) {
    try {
      const code = await (await fetch(src)).text();
      for (const m of code.matchAll(re)) {
        const s = m[0];
        if (/[\/{$]/.test(s)) found.add(s.slice(1, -1));
      }
    } catch {}
  }
  report.scriptsChecked = scripts.size;
  report.purchasePaths = [...found].sort();

  const out = JSON.stringify(report, null, 1);
  console.log(out);
  try { await navigator.clipboard.writeText(out); console.log("Отчёт скопирован в буфер обмена"); }
  catch { console.log("Скопируйте текст выше вручную (ПКМ → Copy object или выделить)"); }
})();
