(() => {
  async function search(q) {
    const res = await fetch(`/api/items/search?q=${encodeURIComponent(q)}`);
    if (!res.ok) return [];
    return await res.json();
  }

  async function save(posId, itemId) {
    const res = await fetch(`/api/lv/positions/${posId}/match`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ item_id: itemId || null })
    });
    return res.ok ? await res.json() : null;
  }

  document.querySelectorAll("tr").forEach(tr => {
    const inp = tr.querySelector("input.search");
    const sel = tr.querySelector("select.pick");
    const btn = tr.querySelector("button.save");
    if (!inp || !sel || !btn) return;
    const posId = inp.dataset.pos;

    let tmr = null;
    inp.addEventListener("input", () => {
      clearTimeout(tmr);
      const q = inp.value.trim();
      if (q.length < 2) return;
      tmr = setTimeout(async () => {
        const items = await search(q);
        sel.innerHTML = '<option value="">—</option>';
        for (const it of items) {
          const opt = document.createElement("option");
          opt.value = it.id;
          opt.textContent = `${it.article_no} – ${it.name}${it.manufacturer ? " ("+it.manufacturer+")" : ""}`;
          sel.appendChild(opt);
        }
      }, 250);
    });

    btn.addEventListener("click", async () => {
      const itemId = sel.value ? parseInt(sel.value, 10) : null;
      const out = await save(posId, itemId);
      if (!out) { alert("Speichern fehlgeschlagen"); return; }
      const cur = document.getElementById(`current-${posId}`);
      cur.textContent = out.current || "aktuell: —";
      inp.value = "";
      sel.innerHTML = '<option value="">—</option>';
    });
  });
})();
