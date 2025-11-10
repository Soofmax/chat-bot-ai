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
    if (cfg.requestId) {
      const ri = document.getElementById("requestId");
      if (ri) ri.value = cfg.requestId;
    }
    const dbg = document.getElementById("debug");
    if (dbg && typeof cfg.debug === "boolean") dbg.checked = !!cfg.debug;

    // theme + brand
    applyTheme(cfg.theme || {});
    const brand = cfg.brandName || defaults.brandName;
    els.brandTitle.textContent = brand;

    // persist merged config to localStorage
    localStorage.setItem("rag_dashboard_cfg", JSON.stringify(cfg));
  }

  els.saveCfg.addEventListener("click", () => {
    const riEl = document.getElementById("requestId");
    const dbgEl = document.getElementById("debug");
    const newCfg = {
      apiUrl: els.apiUrl.value.trim(),
      apiKey: els.apiKey.value.trim(),
      clientId: els.clientId.value.trim(),
      mode: els.mode.value,
      requestId: riEl ? riEl.value.trim() : "",
      debug: dbgEl ? !!dbgEl.checked : false,
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

  function addHistory(entry) {
    const list = JSON.parse(localStorage.getItem("rag_dashboard_history") || "[]");
    list.unshift(entry);
    // Limit to last 20
    localStorage.setItem("rag_dashboard_history", JSON.stringify(list.slice(0, 20)));
    renderHistory();
  }

  function renderHistory() {
    const ul = document.getElementById("history");
    if (!ul) return;
    const list = JSON.parse(localStorage.getItem("rag_dashboard_history") || "[]");
    ul.innerHTML = "";
    for (const it of list) {
      const li = document.createElement("li");
      const info = document.createElement("div");
      info.className = "info";
      const rid = it.rid ? ` • rid=${it.rid}` : "";
      info.textContent = `${new Date(it.ts).toLocaleString()} • ${it.ms}ms • status=${it.status}${rid} • q="${it.question}"`;
      const actions = document.createElement("div");
      actions.className = "actions";
      const copyBtn = document.createElement("button");
      copyBtn.textContent = "Copier CURL";
      copyBtn.addEventListener("click", () => {
        copyCurl(it.url, it.headers, it.body);
      });
      actions.appendChild(copyBtn);
      li.appendChild(info);
      li.appendChild(actions);
      ul.appendChild(li);
    }
  }

  document.getElementById("clearHistory").addEventListener("click", () => {
    localStorage.removeItem("rag_dashboard_history");
    renderHistory();
    toast("Historique effacé.");
  });

  document.getElementById("exportHistory").addEventListener("click", () => {
    const list = localStorage.getItem("rag_dashboard_history") || "[]";
    const blob = new Blob([list], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "history.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  renderHistory();

  els.sendBtn.addEventListener("click", async () => {
    const apiUrl = (els.apiUrl.value || "").trim();
    const apiKey = (els.apiKey.value || "").trim();
    const clientId = (els.clientId.value || "").trim();
    const mode = els.mode.value;
    const question = (els.question.value || "").trim();
    const refresh = !!els.refresh.checked;
    const requestIdEl = document.getElementById("requestId");
    const debugEl = document.getElementById("debug");
    const requestId = requestIdEl ? requestIdEl.value.trim() : "";
    const debug = debugEl ? !!debugEl.checked : false;

    if (!apiUrl) return toast("Veuillez renseigner l'API Base URL.");
    if (!clientId) return toast("Veuillez renseigner le Client ID.");
    if (!question) return toast("Veuillez saisir une question.");

    const body = { question, client_id: clientId, mode, refresh };
    const headers = { "Content-Type": "application/json" };
    if (apiKey) headers["Authorization"] = "Bearer " + apiKey;
    if (requestId) headers["X-Request-ID"] = requestId;

    const url = apiUrl.replace(/\/+$/, "") + "/v1/chat";

    try {
      const t0 = performance.now();
      const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
      const t1 = performance.now();
      const ms = Math.round(t1 - t0);
      const txt = await res.text();

      let json;
      try { json = JSON.parse(txt); } catch (_) { json = { raw: txt }; }

      const rid = res.headers.get("X-Request-ID") || "";

      els.meta.innerHTML = `Status: <span class="code">${res.status}</span> — ${ms}ms — rid=${rid || "n/a"}`;

      if (res.ok && !debug) {
        els.result.textContent = json.response || txt;
      } else {
        els.result.textContent = JSON.stringify(json, null, 2);
      }

      addHistory({
        ts: Date.now(),
        ms,
        status: res.status,
        rid,
        question,
        url,
        headers,
        body,
        ok: res.ok,
      });
    } catch (e) {
      els.result.textContent = "Erreur réseau: " + (e && e.message ? e.message : String(e));
    }
  });

  function copyCurl(url, headers, body) {
    function sq(s) { return `'${String(s).replace(/'/g, `'\\''`)}'`; }
    const parts = [
      "curl -X POST",
      sq(url),
      "-H 'Content-Type: application/json'",
    ];
    if (headers["Authorization"]) {
      parts.push("-H " + sq(headers["Authorization"]));
    }
    if (headers["X-Request-ID"]) {
      parts.push("-H " + sq(`X-Request-ID: ${headers["X-Request-ID"]}`));
    }
    parts.push("-d " + sq(JSON.stringify(body)));
    const cmd = parts.join(" ");
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(cmd).then(() => toast("CURL copié dans le presse-papiers."));
    } else {
      const ta = document.createElement("textarea");
      ta.value = cmd;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch {}
      ta.remove();
      toast("CURL copié.");
    }
  }

  // Copy CURL button
  document.getElementById("copyCurl").addEventListener("click", () => {
    const apiUrl = (els.apiUrl.value || "").trim();
    const apiKey = (els.apiKey.value || "").trim();
    const clientId = (els.clientId.value || "").trim();
    const mode = els.mode.value;
    const question = (els.question.value || "").trim();
    const refresh = !!els.refresh.checked;

    if (!apiUrl) return toast("Veuillez renseigner l'API Base URL.");
    if (!clientId) return toast("Veuillez renseigner le Client ID.");
    if (!question) return toast("Veuillez saisir une question.");

    const url = apiUrl.replace(/\/+$/, "") + "/v1/chat";
    const body = { question, client_id: clientId, mode, refresh };

    function sq(s) {
      return `'${String(s).replace(/'/g, `'\\''`)}'`;
    }

    const parts = [
      "curl -X POST",
      sq(url),
      "-H 'Content-Type: application/json'",
    ];
    if (apiKey) {
      parts.push(sq(`Authorization: Bearer ${apiKey}`));
      parts[parts.length - 1] = "-H " + parts[parts.length - 1];
    }
    parts.push("-d " + sq(JSON.stringify(body)));

    const cmd = parts.join(" ");

    // Copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(cmd).then(() => toast("CURL copié dans le presse-papiers."));
    } else {
      const ta = document.createElement("textarea");
      ta.value = cmd;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch {}
      ta.remove();
      toast("CURL copié.");
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