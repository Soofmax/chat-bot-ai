(function () {
  const els = {
    apiUrl: document.getElementById("apiUrl"),
    apiKey: document.getElementById("apiKey"),
    clientId: document.getElementById("clientId"),
    mode: document.getElementById("mode"),
    saveCfg: document.getElementById("saveCfg"),
    exportCfg: document.getElementById("exportCfg"),
    importCfg: document.getElementById("importCfg"),
    question: document.getElementById("question"),
    refresh: document.getElementById("refresh"),
    sendBtn: document.getElementById("sendBtn"),
    result: document.getElementById("result"),
    meta: document.getElementById("meta"),
    brandTitle: document.getElementById("brandTitle"),
  };

  const defaults = {
    brandName: "Dashboard Client",
    theme: {
      accent: "#3b82f6",
      bg: "#0b0f1a",
      card: "#111827",
      text: "#e5e7eb",
      muted: "#9ca3af",
    },
    apiUrl: "",
    apiKey: "",
    clientId: "",
    mode: "main",
  };

  const urlParams = new URLSearchParams(location.search);
  const paramsCfg = {
    brandName: urlParams.get("brandName") || undefined,
    apiUrl: urlParams.get("apiUrl") || undefined,
    apiKey: urlParams.get("apiKey") || undefined,
    clientId: urlParams.get("clientId") || undefined,
    mode: urlParams.get("mode") || undefined,
    theme: {
      accent: urlParams.get("accent") || undefined,
      bg: urlParams.get("bg") || undefined,
      card: urlParams.get("card") || undefined,
      text: urlParams.get("text") || undefined,
      muted: urlParams.get("muted") || undefined,
    },
  };

  const localCfg = JSON.parse(localStorage.getItem("rag_dashboard_cfg") || "{}");

  let fileCfg = {};
  // Try to load config.json if present
  fetch("config.json", { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : Promise.resolve({})))
    .catch(() => ({}))
    .then((cfg) => {
      fileCfg = cfg || {};
      const merged = deepMerge(defaults, fileCfg, localCfg, paramsCfg);
      applyConfig(merged);
    });

  function deepMerge() {
    const out = {};
    for (const src of arguments) {
      if (!src || typeof src !== "object") continue;
      for (const k of Object.keys(src)) {
        const v = src[k];
        if (v && typeof v === "object" && !Array.isArray(v)) {
          out[k] = deepMerge(out[k] || {}, v);
        } else if (v !== undefined) {
          out[k] = v;
        }
      }
    }
    return out;
  }

  function applyTheme(theme) {
    const root = document.documentElement;
    if (!theme) return;
    const entries = Object.entries(theme);
    for (const [key, val] of entries) {
      if (val) root.style.setProperty(`--${key}`, String(val));
    }
  }

  function applyConfig(cfg) {
    // form fields
    if (cfg.apiUrl) els.apiUrl.value = cfg.apiUrl;
    if (cfg.apiKey) els.apiKey.value = cfg.apiKey;
    if (cfg.clientId) els.clientId.value = cfg.clientId;
    if (cfg.mode) els.mode.value = cfg.mode;

    // theme + brand
    applyTheme(cfg.theme || {});
    const brand = cfg.brandName || defaults.brandName;
    els.brandTitle.textContent = brand;

    // persist merged config to localStorage
    localStorage.setItem("rag_dashboard_cfg", JSON.stringify(cfg));
  }

  els.saveCfg.addEventListener("click", () => {
    const newCfg = {
      apiUrl: els.apiUrl.value.trim(),
      apiKey: els.apiKey.value.trim(),
      clientId: els.clientId.value.trim(),
      mode: els.mode.value,
    };
    const prev = JSON.parse(localStorage.getItem("rag_dashboard_cfg") || "{}");
    const merged = deepMerge(prev, newCfg);
    localStorage.setItem("rag_dashboard_cfg", JSON.stringify(merged));
    toast("Configuration enregistrée.");
  });

  els.exportCfg.addEventListener("click", () => {
    const cfg = JSON.parse(localStorage.getItem("rag_dashboard_cfg") || "{}");
    const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "config.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  els.importCfg.addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      const txt = await file.text();
      const json = JSON.parse(txt);
      const merged = deepMerge(JSON.parse(localStorage.getItem("rag_dashboard_cfg") || "{}"), json);
      localStorage.setItem("rag_dashboard_cfg", JSON.stringify(merged));
      applyConfig(merged);
      toast("Configuration importée.");
    } catch (err) {
      toast("Fichier invalide.");
    } finally {
      e.target.value = "";
    }
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