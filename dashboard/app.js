(function () {
  const els = {
    apiUrl: document.getElementById("apiUrl"),
    apiKey: document.getElementById("apiKey"),
    clientId: document.getElementById("clientId"),
    mode: document.getElementById("mode"),
    saveCfg: document.getElementById("saveCfg"),
    question: document.getElementById("question"),
    refresh: document.getElementById("refresh"),
    sendBtn: document.getElementById("sendBtn"),
    result: document.getElementById("result"),
    meta: document.getElementById("meta"),
  };

  // Load config
  const cfg = JSON.parse(localStorage.getItem("rag_dashboard_cfg") || "{}");
  if (cfg.apiUrl) els.apiUrl.value = cfg.apiUrl;
  if (cfg.apiKey) els.apiKey.value = cfg.apiKey;
  if (cfg.clientId) els.clientId.value = cfg.clientId;
  if (cfg.mode) els.mode.value = cfg.mode;

  els.saveCfg.addEventListener("click", () => {
    const newCfg = {
      apiUrl: els.apiUrl.value.trim(),
      apiKey: els.apiKey.value.trim(),
      clientId: els.clientId.value.trim(),
      mode: els.mode.value,
    };
    localStorage.setItem("rag_dashboard_cfg", JSON.stringify(newCfg));
    toast("Configuration enregistrée.");
  });

  els.sendBtn.addEventListener("click", async () => {
    const apiUrl = (els.apiUrl.value || "").trim();
    const apiKey = (els.apiKey.value || "").trim();
    const clientId = (els.clientId.value || "").trim();
    const mode = els.mode.value;
    const question = (els.question.value || "").trim();
    const refresh = !!els.refresh.checked;

    if (!apiUrl) return toast("Veuillez renseigner l'API Base URL.");
    if (!clientId) return toast("Veuillez renseigner le Client ID.");
    if (!question) return toast("Veuillez saisir une question.");

    const body = { question, client_id: clientId, mode, refresh };
    const headers = { "Content-Type": "application/json" };
    if (apiKey) headers["Authorization"] = "Bearer " + apiKey;

    const url = apiUrl.replace(/\/+$/, "") + "/v1/chat";

    try {
      const t0 = performance.now();
      const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
      const t1 = performance.now();
      const ms = Math.round(t1 - t0);
      const txt = await res.text();

      let json;
      try { json = JSON.parse(txt); } catch (_) { json = { raw: txt }; }

      els.meta.innerHTML = `Status: <span class="code">${res.status}</span> — ${ms}ms`;

      if (res.ok) {
        els.result.textContent = json.response || txt;
      } else {
        els.result.textContent = JSON.stringify(json, null, 2);
      }
    } catch (e) {
      els.result.textContent = "Erreur réseau: " + (e && e.message ? e.message : String(e));
    }
  });

  function toast(msg) {
    // Simple toast
    const el = document.createElement("div");
    el.textContent = msg;
    el.style.position = "fixed";
    el.style.bottom = "16px";
    el.style.right = "16px";
    el.style.background = "#111827";
    el.style.border = "1px solid #374151";
    el.style.color = "#e5e7eb";
    el.style.padding = "8px 12px";
    el.style.borderRadius = "8px";
    el.style.boxShadow = "0 4px 16px rgba(0,0,0,0.25)";
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1800);
  }
})();