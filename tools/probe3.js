// Третий шаг: показывает код сайта, который делает покупку и handshake.
// Откройте страницу любого предмета в каталоге memora.zip, F12 → Console, вставьте и Enter.
// Скрипт только читает JS-файлы сайта, ничего не покупает.
(async () => {
  const scripts = new Set([
    ...[...document.scripts].map(s => s.src),
    ...performance.getEntriesByType("resource").map(e => e.name)
  ].filter(u => u && u.startsWith(location.origin) && /\.js(\?|$)/.test(u)));
  const needles = ["purchases/products/", "/handshake", "getPurchaseDetails", "purchaseItem"];
  const out = [];
  const seen = new Set();
  for (const src of scripts) {
    let code;
    try { code = await (await fetch(src)).text(); } catch { continue; }
    for (const n of needles) {
      let i = code.indexOf(n);
      while (i !== -1) {
        const from = Math.max(0, i - 700), to = Math.min(code.length, i + 900);
        const key = src + ":" + Math.floor(from / 500);
        if (!seen.has(key)) {
          seen.add(key);
          out.push(`===== ${n} @ ${src.split("/").pop()}:${i}\n${code.slice(from, to)}`);
        }
        i = code.indexOf(n, i + n.length);
      }
    }
  }
  const text = out.join("\n\n") || "Ничего не найдено — откройте страницу предмета и запустите снова";
  console.log(text);
  try { await navigator.clipboard.writeText(text); console.log("Скопировано в буфер обмена (" + out.length + " фрагментов)"); }
  catch { console.log("Скопируйте текст выше вручную"); }
})();
