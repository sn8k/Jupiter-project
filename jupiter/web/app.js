const state = {
  isScanning: false,
  context: null,
  report: null,
  view: "dashboard",
  theme: "dark",
  apiBaseUrl: null,
  backends: [],
  currentBackend: null,
  i18n: {
    lang: "fr",
    translations: {},
  },
  logs: [],
  logLevel: "ALL",
  liveEvents: [],
  meeting: {
    status: "unknown",
    isLicensed: false,
    remainingSeconds: null,
    message: null
  }
};

const sampleReport = {
  root: "~/projets/jupiter-demo",
  report_schema_version: "1.0",
  last_scan_timestamp: Math.floor(Date.now() / 1000) - 7200,
  files: [
    {
      path: "jupiter/core/scanner.py",
      size_bytes: 18456,
      modified_timestamp: Math.floor(Date.now() / 1000) - 86400,
      file_type: "py",
    },
    {
      path: "jupiter/web/app.js",
      size_bytes: 9645,
      modified_timestamp: Math.floor(Date.now() / 1000) - 43200,
      file_type: "js",
    },
    {
      path: "README.md",
      size_bytes: 4096,
      modified_timestamp: Math.floor(Date.now() / 1000) - 3600,
      file_type: "md",
    },
    {
      path: "requirements.txt",
      size_bytes: 512,
      modified_timestamp: Math.floor(Date.now() / 1000) - 10800,
      file_type: "txt",
    },
  ],
  hotspots: {
    most_functions: [
      { path: "jupiter/core/scanner.py", details: "27 fonctions recensées" },
      { path: "jupiter/core/analyzer.py", details: "18 fonctions recensées" },
    ],
  },
  python_summary: {
    total_potentially_unused_functions: 3,
  },
  plugins: [
    { name: "code_quality", status: "ok", description: "Analyse des imports et fonctions orphelines" },
    { name: "meeting", status: "pending", description: "Synchronisation licence Meeting" },
    { name: "notify_webhook", status: "disabled", description: "Notification webhook (placeholder)" },
  ],
};

// --- I18n & Theming ---

async function setLanguage(lang) {
  if (state.i18n.lang === lang && Object.keys(state.i18n.translations).length) return;
  
  try {
    const response = await fetch(`./lang/${lang}.json`);
    if (!response.ok) throw new Error("Language file not found");
    state.i18n.translations = await response.json();
    state.i18n.lang = lang;
    localStorage.setItem("jupiter-lang", lang);
    document.documentElement.lang = lang;
    translateUI();
    const languageValue = document.getElementById("language-value");
    if (languageValue) {
      languageValue.textContent = lang === "fr" ? "Français" : "English";
    }
    addLog(`Language changed to ${lang.toUpperCase()}`);
  } catch (error) {
    console.error("Failed to load language:", error);
    addLog(`Error loading language ${lang}`, "ERROR");
  }
}

const t = (key) => state.i18n.translations[key] || key;

function translateUI() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  renderReport(state.report);
}

function setTheme(theme) {
  state.theme = theme;
  document.body.classList.remove("theme-light", "theme-dark");
  document.body.classList.add(`theme-${theme}`);
  localStorage.setItem("jupiter-theme", theme);
  addLog(`Theme changed to ${theme} mode`);
  const themeValue = document.getElementById("theme-value");
  if (themeValue) {
    themeValue.textContent = theme === "dark" ? t("s_theme_value_dark") : t("s_theme_value_light");
  }
}

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function inferApiBaseUrl() {
  if (state.context?.api_base_url) return state.context.api_base_url;
  const { origin } = window.location;
  if (origin.includes(":8050")) {
    return origin.replace(":8050", ":8000");
  }
  return DEFAULT_API_BASE;
}

// --- Core App Logic ---

async function startScan(options = {}) {
  const scanButtons = document.querySelectorAll('[data-action="start-scan"]');
  if (state.isScanning) return;

  state.isScanning = true;
  scanButtons.forEach(btn => {
    btn.disabled = true;
    const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
    if(textElement) textElement.textContent = t("scan_in_progress");
  });
  addLog(t("scan_start_log"));
  pushLiveEvent(t("scan_button"), t("scan_live_event_start"));

  const payload = {
    show_hidden: false,
    incremental: false,
    ignore_globs: [],
    backend_name: state.currentBackend,
    ...options,
  };

  try {
    const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`${t("scan_error_server")} (${response.status}): ${errorText}`);
    }

    const report = await response.json();
    console.log("Scan report received:", report);
    report.last_scan_timestamp = Date.now() / 1000;
    renderReport(report);
    addLog(t("scan_complete_log"));
    pushLiveEvent(t("scan_button"), t("scan_live_event_complete"));
  } catch (error) {
    console.error("Error during scan:", error);
    let errorMessage = error.message;
    if (error instanceof TypeError && error.message.includes("fetch")) {
        errorMessage = t("error_fetch");
    }
    addLog(`${t("scan_error_log")}: ${errorMessage}`, "ERROR");
    alert(`${t("scan_failed_alert")}: ${errorMessage}`);
  } finally {
    state.isScanning = false;
    scanButtons.forEach(btn => {
      btn.disabled = false;
      const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
      if(textElement) textElement.textContent = t("scan_button");
    });
  }
}

function handleAction(action, data) {
  console.log("Action triggered:", action, data);
  switch (action) {
    case "load-sample":
      renderReport(sampleReport);
      addLog("Sample report loaded.");
      break;
    case "start-scan":
      startScan();
      break;
    case "start-watch":
      if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.close();
      } else {
          connectWebSocket();
      }
      break;
    case "open-scan-modal":
      openModal("scan-modal");
      break;
    case "close-scan-modal":
      closeModal("scan-modal");
      break;
    case "confirm-scan":
      startScanWithOptions();
      break;
    case "open-run-modal":
      openModal("run-modal");
      break;
    case "close-run-modal":
      closeModal("run-modal");
      break;
    case "confirm-run":
      runCommand();
      break;
    case "trigger-update":
      triggerUpdate();
      break;
    case "open-settings":
      setView("settings");
      loadSettings();
      break;
    case "toggle-theme":
      setTheme(state.theme === "dark" ? "light" : "dark");
      break;
    case "change-language":
      setLanguage(data.lang);
      break;
    case "open-license":
      alert(`Device Key: ${state.context?.meeting?.deviceKey || "N/A"}`);
      break;
    case "browse-root":
      console.log("Action: browse-root triggered");
      openBrowser();
      break;
    case "close-modal":
      closeBrowser();
      break;
    case "confirm-path":
      confirmBrowserSelection();
      break;
    case "create-config":
      createConfig();
      break;
    case "close-onboarding":
      const onboardingModal = document.getElementById('onboarding-modal');
      if (onboardingModal) onboardingModal.remove();
      break;
    case "toggle-plugin":
      togglePlugin(data.pluginName, data.pluginState === 'true');
      break;
    default:
      console.warn(`Unknown action: ${action}`);
      break;
  }
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("hidden");
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add("hidden");
}

async function startScanWithOptions() {
    const showHidden = document.getElementById("scan-show-hidden").checked;
    const incremental = document.getElementById("scan-incremental").checked;
    const ignoreStr = document.getElementById("scan-ignore").value;
    const ignoreGlobs = ignoreStr ? ignoreStr.split(",").map(s => s.trim()).filter(s => s) : [];

    closeModal("scan-modal");

    await startScan({ show_hidden: showHidden, incremental, ignore_globs: ignoreGlobs });
}

async function runCommand() {
    const commandStr = document.getElementById("run-command").value;
    const withDynamic = document.getElementById("run-dynamic").checked;
    const outputDiv = document.getElementById("run-output");
    
    if (!commandStr) return;
    
    outputDiv.textContent = "Running...";
    outputDiv.classList.remove("hidden");
    
    try {
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        // Split command string simply by space (naive)
        // Ideally the backend should handle string parsing or we use a library
        // But for now we send the string and let backend handle it or split here
        // The API expects a list of strings.
        const command = commandStr.split(" "); 
        
        const response = await fetch(`${apiBaseUrl}/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                command, 
                with_dynamic: withDynamic,
                backend_name: state.currentBackend
            })
        });
        
        const result = await response.json();
        outputDiv.textContent = `Exit Code: ${result.returncode}\n\nSTDOUT:\n${result.stdout}\n\nSTDERR:\n${result.stderr}`;
        
        if (result.dynamic_analysis) {
            addLog("Dynamic analysis data received.");
        }
    } catch (e) {
        outputDiv.textContent = "Error: " + e.message;
    }
}

async function triggerUpdate() {
    const source = document.getElementById("update-source").value;
    const force = document.getElementById("update-force").checked;
    
    if (!source) {
        alert("Please provide a source (ZIP path or Git URL)");
        return;
    }
    
    if (!confirm("Are you sure you want to update Jupiter? The server will need to be restarted.")) return;
    
    try {
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        const response = await fetch(`${apiBaseUrl}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, force })
        });
        
        if (response.ok) {
            alert("Update successful. Please restart Jupiter.");
        } else {
            const err = await response.json();
            alert("Update failed: " + err.detail);
        }
    } catch (e) {
        alert("Update failed: " + e.message);
    }
}

async function loadSettings() {
    if (!state.apiBaseUrl) return;
    try {
        const response = await fetch(`${state.apiBaseUrl}/config`);
        if (response.ok) {
            const config = await response.json();
            document.getElementById("conf-server-host").value = config.server_host;
            document.getElementById("conf-server-port").value = config.server_port;
            document.getElementById("conf-gui-host").value = config.gui_host;
            document.getElementById("conf-gui-port").value = config.gui_port;
            document.getElementById("conf-meeting-enabled").checked = config.meeting_enabled;
            document.getElementById("conf-meeting-key").value = config.meeting_device_key || "";
            document.getElementById("conf-ui-theme").value = config.ui_theme;
            document.getElementById("conf-ui-lang").value = config.ui_language;
        }
    } catch (e) {
        console.error("Failed to load settings", e);
    }
}

async function saveSettings(e) {
    e.preventDefault();
    if (!state.apiBaseUrl) return;
    
    const formData = new FormData(e.target);
    const config = {
        server_host: formData.get("server_host"),
        server_port: parseInt(formData.get("server_port")),
        gui_host: formData.get("gui_host"),
        gui_port: parseInt(formData.get("gui_port")),
        meeting_enabled: formData.get("meeting_enabled") === "on",
        meeting_device_key: formData.get("meeting_device_key"),
        ui_theme: formData.get("ui_theme"),
        ui_language: formData.get("ui_language"),
        plugins_enabled: [], // TODO: Handle plugins list
        plugins_disabled: []
    };
    
    try {
        const response = await fetch(`${state.apiBaseUrl}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            addLog("Settings saved.");
            alert("Settings saved. Some changes may require a restart.");
            setTheme(config.ui_theme);
            setLanguage(config.ui_language);
        } else {
            alert("Failed to save settings.");
        }
    } catch (e) {
        alert("Error saving settings: " + e.message);
    }
}

async function changeRoot(path) {
  if (!state.apiBaseUrl) return;
  try {
    const response = await fetch(`${state.apiBaseUrl}/config/root`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
    });
    if (response.ok) {
        const data = await response.json();
        addLog(`Root changed to ${data.root}`);
        
        const rootLabel = document.getElementById("root-path");
        if (rootLabel) rootLabel.textContent = data.root;
        
        // Update context locally
        if (state.context) state.context.root = data.root;
        
        // Trigger a new scan on the new root
      await loadCachedReport();
      startScan(); 
    } else {
        alert("Erreur: Dossier invalide ou inaccessible.");
    }
  } catch (e) {
      console.error(e);
      alert("Erreur de communication avec le serveur.");
  }
}

// --- UI Rendering ---

function renderReport(report) {
  console.log("Rendering report with", report?.files?.length, "files");
  state.report = report;
  renderStats(report);
  renderUploadMeta(report);
  renderFiles(report);
  renderFunctions(report);
  renderAnalysis(report);
  renderHotspots(report);
  renderAlerts(report);
  renderPluginList(report);
  renderStatusBadges(report);
  renderQuality(report);
  renderDiagnostics(report);
  if (report) {
    addLog("UI updated with new report.");
  }
}

function renderStats(report) {
    const statGrid = document.getElementById("stats-grid");
    if (!statGrid) return;
    statGrid.innerHTML = "";
    if (!report || !report.files) {
        statGrid.innerHTML = `<p class="muted">${t('analysis_empty')}</p>`;
        return;
    }
    const files = report.files;
    const totalSize = files.reduce((acc, file) => acc + (file.size_bytes || 0), 0);
    const lastUpdated = files.length > 0 ? [...files].sort((a, b) => (b.modified_timestamp || 0) - (a.modified_timestamp || 0))[0] : null;
    const hasDynamic = report?.dynamic?.calls && Object.keys(report.dynamic.calls).length > 0;

    const stats = [
        { label: t("files_view"), value: files.length.toLocaleString(state.i18n.lang) },
        { label: t("analysis_avg_size"), value: bytesToHuman(totalSize) },
        { label: t("analysis_freshest"), value: lastUpdated ? formatDate(lastUpdated.modified_timestamp) : "-" },
        { label: "Dernier scan", value: report?.last_scan_timestamp ? formatDate(report.last_scan_timestamp) : "N/A" },
        { label: "Données dynamiques", value: hasDynamic ? "Oui" : "Non" },
    ];
    stats.forEach(stat => {
        const card = document.createElement("div");
        card.className = "stat-card";
        card.innerHTML = `<p class="label">${stat.label}</p><p class="value">${stat.value}</p>`;
        statGrid.appendChild(card);
    });
}

function renderUploadMeta(report) {
    const container = document.getElementById("upload-meta");
    if(!container) return;
    if (!report) {
        container.textContent = t("alert_no_report_detail");
        return;
    }
    const fileCount = Array.isArray(report.files) ? report.files.length : 0;
    container.innerHTML = `<p class="small muted">${fileCount} ${t('files_view')} importés — racine : ${report.root || "?"}</p>`;
}

function renderFiles(report) {
    const files = Array.isArray(report?.files) ? [...report.files] : [];
    const body = document.getElementById("files-body");
    const empty = document.getElementById("files-empty");
    if(!body || !empty) return;
    body.innerHTML = "";

    if (!files.length) {
        empty.style.display = "block";
        empty.textContent = t("alert_no_report_detail");
        return;
    }
    empty.style.display = "none";
    files
        .sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))
        .slice(0, 200)
        .forEach((file) => {
            const funcCount = file.language_analysis?.defined_functions?.length || 0;
            const row = document.createElement("tr");
            row.innerHTML = `<td>${file.path}</td><td class="numeric">${bytesToHuman(file.size_bytes || 0)}</td><td class="numeric">${formatDate(file.modified_timestamp)}</td><td class="numeric">${funcCount}</td>`;
            body.appendChild(row);
        });
}

function renderFunctions(report) {
    const body = document.getElementById("functions-body");
    const empty = document.getElementById("functions-empty");
    if (!body || !empty) return;
    body.innerHTML = "";

    const files = Array.isArray(report?.files) ? report.files : [];
    const dynamicCalls = report?.dynamic?.calls || {};
    
    let allFunctions = [];
    files.forEach(file => {
        if (file.language_analysis && file.language_analysis.defined_functions) {
            file.language_analysis.defined_functions.forEach(funcName => {
                let callCount = 0;
                // Simple heuristic matching
                const fileName = file.path.split(/[/\\]/).pop();
                const keySuffix = `${fileName}::${funcName}`;
                
                for (const [key, count] of Object.entries(dynamicCalls)) {
                    if (key.endsWith(keySuffix)) {
                        callCount = count;
                        break;
                    }
                }
                
                let status = "unknown";
                const unusedFuncs = file.language_analysis.potentially_unused_functions || [];
                if (unusedFuncs.includes(funcName)) {
                    if (callCount > 0) {
                        status = "used (dynamic)";
                    } else {
                        status = "unused";
                    }
                } else {
                    status = "used";
                }

                allFunctions.push({
                    name: funcName,
                    file: file.path,
                    calls: callCount,
                    status: status
                });
            });
        }
    });

    if (!allFunctions.length) {
        empty.style.display = "block";
        empty.textContent = "Aucune fonction détectée.";
        return;
    }
    empty.style.display = "none";

    allFunctions.sort((a, b) => b.calls - a.calls);

    allFunctions.forEach(func => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${func.name}</td>
            <td>${func.file}</td>
            <td class="numeric">${func.calls}</td>
            <td>${func.status}</td>
        `;
        body.appendChild(row);
    });
}

function renderAnalysis(report) {
    const files = Array.isArray(report?.files) ? [...report.files] : [];
    const container = document.getElementById("analysis-stats");
    if(!container) return;
    container.innerHTML = "";

    if (!files.length) {
        container.innerHTML = `<p class='muted'>${t('analysis_empty')}</p>`;
        return;
    }

    const extensionCount = files.reduce((acc, file) => {
        const ext = file.file_type || "(sans extension)";
        acc[ext] = (acc[ext] || 0) + 1;
        return acc;
    }, {});

    const dominant = Object.entries(extensionCount).sort((a, b) => b[1] - a[1])[0];
    const avgSize = files.length ? files.reduce((acc, file) => acc + (file.size_bytes || 0), 0) / files.length : 0;
    const freshest = [...files].sort((a, b) => (b.modified_timestamp || 0) - (a.modified_timestamp || 0))[0];

    const stats = [
        { label: t("analysis_dominant_ext"), value: dominant ? `${dominant[0]} (${dominant[1]})` : "-" },
        { label: t("analysis_avg_size"), value: bytesToHuman(avgSize) },
        { label: t("analysis_freshest"), value: freshest ? freshest.path : "-" },
    ];

    stats.forEach((stat) => {
        const card = document.createElement("div");
        card.className = "stat-card";
        card.innerHTML = `<p class="label">${stat.label}</p><p class="value">${stat.value}</p>`;
        container.appendChild(card);
    });
}

function renderHotspots(report) {
    const body = document.getElementById("hotspot-body");
    const empty = document.getElementById("hotspot-empty");
    if (!body || !empty) return;
    body.innerHTML = "";

    let candidates = [];

    // Try to use pre-calculated hotspots if available
    if (report && report.hotspots && report.hotspots.most_functions) {
        candidates = report.hotspots.most_functions.slice(0, 5);
    } 
    // Otherwise calculate them from files
    else if (report && Array.isArray(report.files)) {
        const pythonFiles = report.files.filter(f => 
            f.file_type === "py" && 
            f.language_analysis && 
            Array.isArray(f.language_analysis.defined_functions)
        );
        
        pythonFiles.sort((a, b) => {
            const lenA = a.language_analysis.defined_functions.length;
            const lenB = b.language_analysis.defined_functions.length;
            return lenB - lenA;
        });

        candidates = pythonFiles.slice(0, 5).map(f => ({
            path: f.path,
            details: `${f.language_analysis.defined_functions.length} functions`
        }));
    }

    if (!candidates.length) {
        empty.style.display = "block";
        empty.textContent = t('hotspots_empty');
        return;
    }

    empty.style.display = "none";

    candidates.forEach((file, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${file.path}</td>
            <td>${file.details}</td>
            <td class="numeric">${index + 1}</td>
        `;
        body.appendChild(row);
    });
}

function renderAlerts(report) {
    const container = document.getElementById("alert-list");
    if(!container) return;
    container.innerHTML = "";
    const alerts = [];

    if (!report) {
        alerts.push({
            title: t("alert_no_report_title"),
            detail: t("alert_no_report_detail"),
        });
    } else {
        if (report.python_summary && report.python_summary.total_potentially_unused_functions > 0) {
            alerts.push({
                title: `${report.python_summary.total_potentially_unused_functions} ${t("alert_unused_title")}`,
                detail: t("alert_unused_detail"),
            });
        }
        alerts.push({ title: t("alert_meeting_title"), detail: t("alert_meeting_detail") });
    }

    alerts.forEach((alert) => {
        const item = document.createElement("li");
        item.className = "alert-item";
        item.innerHTML = `<div class="alert-icon">⚠️</div><div><p class="label">${alert.title}</p><p class="muted">${alert.detail}</p></div>`;
        container.appendChild(item);
    });
}

function renderStatusBadges(report) {
  const container = document.getElementById("status-badges");
  if (!container) return;
  container.innerHTML = "";

  const badges = [
    {
      label: t("badge_scan"),
      value: report ? t("badge_scan_ready") : t("badge_scan_missing"),
      icon: report ? "✅" : "⏳",
    },
    {
      label: t("badge_last_scan"),
      value: report?.last_scan_timestamp ? formatDate(report.last_scan_timestamp) : t("badge_last_scan_missing"),
      icon: "🕒",
    },
    {
      label: t("badge_root"),
      value: report?.root || state.context?.root || t("loading"),
      icon: "📁",
    },
  ];

  // Add Meeting Badge
  if (state.meeting) {
    let icon = "❓";
    let text = state.meeting.status;
    
    if (state.meeting.is_licensed) {
        icon = "🔑";
        text = "Licence OK";
    } else if (state.meeting.status === "limited") {
        icon = "⏱️";
        const rem = state.meeting.session_remaining_seconds;
        const min = Math.floor(rem / 60);
        text = `Essai (${min}m)`;
    } else if (state.meeting.status === "expired") {
        icon = "⛔";
        text = "Expiré";
    }

    badges.push({
        label: "Meeting",
        value: text,
        icon: icon
    });
  }

  badges.forEach((badge) => {
    const pill = document.createElement("span");
    pill.className = "badge";
    pill.textContent = `${badge.icon} ${badge.label}: ${badge.value}`;
    container.appendChild(pill);
  });
}

function renderPluginList(plugins) {
  const container = document.getElementById("plugin-list");
  if (!container) return;
  container.innerHTML = "";

  if (!plugins || !plugins.length) {
    container.innerHTML = `<p class="empty">${t("plugins_empty")}</p>`;
    return;
  }

  plugins.forEach((plugin) => {
    const card = document.createElement("div");
    card.className = "plugin-card";

    const statusText = plugin.enabled ? t("plugin_enabled") : t("plugin_disabled");
    const statusClass = plugin.enabled ? "status-ok" : "status-disabled";
    
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:start; width:100%">
        <div>
            <p class="label">${plugin.name} <span class="small muted">v${plugin.version}</span></p>
            <p class="muted">${plugin.description || ""}</p>
            <p class="small ${statusClass}">● ${statusText}</p>
        </div>
        <button class="ghost small" data-action="toggle-plugin" data-plugin-name="${plugin.name}" data-plugin-state="${!plugin.enabled}">
            ${plugin.enabled ? "Désactiver" : "Activer"}
        </button>
      </div>
    `;
    container.appendChild(card);
  });
}

async function fetchPlugins() {
    if (!state.apiBaseUrl) return;
    try {
        const response = await fetch(`${state.apiBaseUrl}/plugins`);
        if (response.ok) {
            const plugins = await response.json();
            renderPluginList(plugins);
        }
    } catch (e) {
        console.error("Failed to fetch plugins", e);
    }
}

async function togglePlugin(name, enable) {
    if (!state.apiBaseUrl) return;
    try {
        const response = await fetch(`${state.apiBaseUrl}/plugins/${name}/toggle?enable=${enable}`, { method: "POST" });
        if (response.ok) {
            fetchPlugins(); // Refresh list
            addLog(`Plugin ${name} ${enable ? "enabled" : "disabled"}`);
        }
    } catch (e) {
        console.error("Failed to toggle plugin", e);
    }
}

function renderDynamicGraph(dynamicData) {
    const canvas = document.getElementById("dynamic-graph-canvas");
    if (!canvas || !dynamicData || !dynamicData.call_graph) return;
    
    const ctx = canvas.getContext("2d");
    const width = canvas.parentElement.clientWidth;
    const height = 400;
    canvas.width = width;
    canvas.height = height;
    
    ctx.clearRect(0, 0, width, height);
    
    const graph = dynamicData.call_graph;
    const nodes = new Set();
    const links = [];
    
    // Build nodes and links
    for (const [caller, callees] of Object.entries(graph)) {
        nodes.add(caller);
        for (const [callee, count] of Object.entries(callees)) {
            nodes.add(callee);
            links.push({ source: caller, target: callee, count });
        }
    }
    
    const nodeList = Array.from(nodes);
    if (nodeList.length === 0) {
        ctx.fillStyle = "#888";
        ctx.fillText("No dynamic data available", 10, 20);
        return;
    }

    // Simple circular layout
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 40;
    
    const nodePositions = {};
    nodeList.forEach((node, i) => {
        const angle = (i / nodeList.length) * 2 * Math.PI;
        nodePositions[node] = {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle)
        };
    });
    
    // Draw links
    ctx.strokeStyle = "rgba(100, 100, 255, 0.3)";
    links.forEach(link => {
        const start = nodePositions[link.source];
        const end = nodePositions[link.target];
        ctx.lineWidth = Math.min(link.count, 5);
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
    });
    
    // Draw nodes
    ctx.fillStyle = "#4CAF50";
    ctx.font = "10px sans-serif";
    nodeList.forEach(node => {
        const pos = nodePositions[node];
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.fillStyle = "#ccc";
        ctx.fillText(node.split("::").pop(), pos.x + 6, pos.y + 3);
        ctx.fillStyle = "#4CAF50";
    });
}


function renderQuality(report) {
    const complexityBody = document.getElementById("quality-complexity-body");
    const complexityEmpty = document.getElementById("quality-complexity-empty");
    const duplicationBody = document.getElementById("quality-duplication-body");
    const duplicationEmpty = document.getElementById("quality-duplication-empty");

    if (!complexityBody || !duplicationBody) return;

    complexityBody.innerHTML = "";
    duplicationBody.innerHTML = "";

    const quality = report?.quality || {};

    // Complexity
    const complexityScores = quality.complexity_per_file || [];
    if (complexityScores.length === 0) {
        complexityEmpty.style.display = "block";
    } else {
        complexityEmpty.style.display = "none";
        complexityScores.slice(0, 10).forEach(item => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td class="truncate" title="${item.path}">${item.path}</td>
                <td class="numeric">${item.score}</td>
            `;
            complexityBody.appendChild(row);
        });
    }

    // Duplication
    const duplications = quality.duplication_clusters || [];
    if (duplications.length === 0) {
        duplicationEmpty.style.display = "block";
    } else {
        duplicationEmpty.style.display = "none";
        duplications.slice(0, 10).forEach(cluster => {
            const row = document.createElement("tr");
            const locs = cluster.occurrences.map(o => `${o.path}:${o.line}`).join(", ");
            row.innerHTML = `
                <td class="mono small">${cluster.hash.substring(0, 8)}</td>
                <td class="numeric">${cluster.occurrences.length}</td>
                <td class="small truncate" title="${locs}">${locs}</td>
            `;
            duplicationBody.appendChild(row);
        });
    }
}

function renderDiagnostics(report) {
  const apiBaseLabel = document.getElementById("api-base-url");
  const diagRoot = document.getElementById("diag-root");
  const diagScanState = document.getElementById("diag-scan-state");

  const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
  if (apiBaseLabel) apiBaseLabel.textContent = apiBaseUrl;
  if (diagRoot) diagRoot.textContent = state.context?.root || report?.root || t("loading");
  if (diagScanState) {
    diagScanState.textContent = report ? t("diag_scan_ready") : t("diag_scan_missing");
  }
}

// --- Utility functions ---

const bytesToHuman = (value) => {
  if (typeof value !== 'number') return "-";
  const units = ["o", "Ko", "Mo", "Go"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
};

const formatDate = (timestamp) => {
  if (!timestamp) return "-";
  const date = new Date(timestamp * 1000);
  return new Intl.DateTimeFormat(state.i18n.lang, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

function addLog(message, level = "INFO") {
  const entry = { message, level, timestamp: new Date() };
  state.logs.unshift(entry);
  state.logs = state.logs.slice(0, 50);
  renderLogs();
}

function renderLogs() {
  const container = document.getElementById("log-stream");
  if (!container) return;
  container.innerHTML = "";
  
  const levels = { "ALL": 0, "INFO": 1, "WARN": 2, "ERROR": 3 };
  const currentLevel = levels[state.logLevel] || 0;

  const filteredLogs = state.logs.filter(log => {
      const logLevel = levels[log.level] || 1;
      return logLevel >= currentLevel;
  }).slice(0, 8);

  filteredLogs.forEach((log) => {
    const item = document.createElement("div");
    item.className = `log-entry log-${log.level.toLowerCase()}`;
    item.textContent = `[${log.timestamp.toLocaleTimeString()}] [${log.level}] ${log.message}`;
    container.appendChild(item);
  });
}

function pushLiveEvent(title, detail) {
  const entry = { title, detail, timestamp: new Date() };
  state.liveEvents.unshift(entry);
  state.liveEvents = state.liveEvents.slice(0, 5);
  const stream = document.getElementById("live-stream");
  if (!stream) return;
  stream.innerHTML = "";
  state.liveEvents.forEach((event) => {
    const card = document.createElement("div");
    card.className = "live-card";
    card.innerHTML = `<div class="live-title">${event.title} · ${event.timestamp.toLocaleTimeString()}</div><p class="muted">${event.detail}</p>`;
    stream.appendChild(card);
  });
}

async function loadContext() {
  try {
    const response = await fetch("/context.json");
    if (!response.ok) throw new Error("Network response was not ok");
    const payload = await response.json();
    state.context = payload;
    state.apiBaseUrl = payload.api_base_url || inferApiBaseUrl();
    const rootLabel = document.getElementById("root-path");
    if (rootLabel) rootLabel.textContent = payload.root || "(undefined)";
    const apiLabel = document.getElementById("api-base-url");
    if (apiLabel) apiLabel.textContent = state.apiBaseUrl;
    addLog(`${t("context_loaded")}: ${payload.root}`);
    
    if (payload.has_config_file === false) {
        showOnboarding();
    }
  } catch (error) {
    console.warn("Could not load context", error);
    const rootLabel = document.getElementById("root-path");
    if (rootLabel) rootLabel.textContent = "N/A";
  }
}

async function loadCachedReport() {
  if (!state.apiBaseUrl) return null;
  try {
    const response = await fetch(`${state.apiBaseUrl}/reports/last`);
    if (!response.ok) {
      if (response.status !== 404) {
        addLog(`Cached report request failed (${response.status})`, "WARN");
      }
      return null;
    }

    const report = await response.json();
    renderReport(report);
    addLog("Restored last cached report.", "INFO");
    return report;
  } catch (error) {
    console.warn("Failed to restore cached report:", error);
    return null;
  }
}

function showOnboarding() {
  const modal = document.createElement("div");
  modal.className = "modal-overlay";
  modal.id = "onboarding-modal";
  modal.innerHTML = `
    <div class="modal">
      <h2>Bienvenue sur Jupiter</h2>
      <p>Aucun projet n'est configuré dans ce dossier.</p>
      <div class="actions">
        <button class="primary" data-action="create-config">Créer une configuration par défaut</button>
        <button class="ghost" data-action="close-onboarding">Ignorer</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

async function createConfig() {
    try {
        const res = await fetch(`${state.apiBaseUrl}/init`, { method: "POST" });
        if (res.ok) {
            addLog("Configuration créée avec succès.");
            document.getElementById('onboarding-modal').remove();
            // Reload context to update state
            loadContext();
        } else {
            const err = await res.json();
            alert("Erreur: " + (err.detail || "Impossible de créer la config"));
        }
    } catch (e) {
        console.error(e);
        alert("Erreur réseau lors de la création de la config");
    }
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((section) => {
    section.classList.toggle("hidden", section.dataset.view !== view);
  });

  if (view === "plugins") {
    fetchPlugins();
  } else if (view === "functions") {
    if (state.report && state.report.dynamic) {
      renderDynamicGraph(state.report.dynamic);
    }
  }
}

function showPlaceholder(action) {
  const detail = `${action}: This action is a placeholder for future functionality.`;
  addLog(detail);
  pushLiveEvent("Placeholder", detail);
}

function bindActions() {
  console.log("Binding actions...");
  document.body.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;
    handleAction(action, target.dataset);
  });

  document.querySelectorAll(".nav-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      const { view } = event.currentTarget.dataset;
      setView(view);
      if (view === "settings") {
          loadSettings();
      }
    });
  });
  
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
      settingsForm.addEventListener("submit", saveSettings);
  }

  const logLevelFilter = document.getElementById("log-level-filter");
  if (logLevelFilter) {
      logLevelFilter.addEventListener("change", (e) => {
          state.logLevel = e.target.value;
          renderLogs();
      });
  }
}

function bindUpload() {
  const input = document.getElementById("report-input");
  const dropzone = document.getElementById("dropzone");
  if (!input || !dropzone) return;

  const handleFile = async (file) => {
    if (!file || !file.type.includes("json")) {
        addLog("Invalid file type. Please select a JSON file.");
        return;
    }
    const text = await file.text();
    try {
      const payload = JSON.parse(text);
      renderReport(payload);
      addLog(`Report loaded from ${file.name}.`);
    } catch (error) {
      alert("The file is not a valid JSON.");
      console.error("Parsing error", error);
    }
  };
  
  input.addEventListener("change", (e) => handleFile(e.target.files[0]));
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragging"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragging"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragging");
    handleFile(e.dataTransfer.files[0]);
  });
}

function connectWebSocket() {
  if (!state.apiBaseUrl) return;
  const wsUrl = state.apiBaseUrl.replace("http", "ws") + "/ws";
  
  try {
    const ws = new WebSocket(wsUrl);
    state.ws = ws;
    
    ws.onopen = () => {
      addLog("WebSocket connected.");
      const btn = document.querySelector('[data-action="start-watch"]');
      if (btn) {
          btn.classList.add("active");
          const label = btn.querySelector('.label') || btn;
          if (label) label.textContent = "Watching";
      }
      const watchPanel = document.getElementById("watch-panel");
      if (watchPanel) watchPanel.classList.remove("hidden");
    };
    
    ws.onmessage = (event) => {
      pushLiveEvent("Server", event.data);
      addLog(`WS: ${event.data}`);
      
      const watchList = document.getElementById("watch-events");
      if (watchList) {
          const li = document.createElement("li");
          li.textContent = `[${new Date().toLocaleTimeString()}] ${event.data}`;
          li.style.padding = "0.25rem 0";
          li.style.borderBottom = "1px solid var(--border)";
          watchList.prepend(li);
          if (watchList.children.length > 20) watchList.lastChild.remove();
      }
    };
    
    ws.onclose = () => {
      state.ws = null;
      addLog("WebSocket disconnected.");
      const btn = document.querySelector('[data-action="start-watch"]');
      if (btn) {
          btn.classList.remove("active");
          const label = btn.querySelector('.label') || btn;
          if (label) label.textContent = "Watch";
      }
      const watchPanel = document.getElementById("watch-panel");
      if (watchPanel) watchPanel.classList.add("hidden");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
    
    state.ws = ws;
  } catch (e) {
    console.error("Could not connect to WebSocket", e);
  }
}

async function fetchMeetingStatus() {
  if (!state.apiBaseUrl) return;
  try {
    const response = await fetch(`${state.apiBaseUrl}/meeting/status`);
    if (response.ok) {
      const status = await response.json();
      state.meeting = status;
      renderStatusBadges(state.report);
      
      // Update Settings Panel if visible
      const statusEl = document.getElementById("meeting-status");
      if (statusEl) {
          statusEl.textContent = status.is_licensed ? "Active" : "Limited Mode";
          statusEl.className = "value " + (status.is_licensed ? "text-success" : "text-warning");
      }
    }
  } catch (error) {
    console.error("Failed to fetch meeting status:", error);
  }
}

// --- File Browser Logic ---
let currentBrowserPath = "";
let selectedBrowserPath = "";

function openBrowser() {
  console.log("Opening browser modal...");
  const modal = document.getElementById("browser-modal");
  if (modal) {
    try {
      modal.showModal();
      // Strip quotes from root if present
      let rootToFetch = state.context?.root || ".";
      rootToFetch = rootToFetch.replace(/^"|"$/g, '');
      
      console.log("Fetching FS for:", rootToFetch);
      fetchFs(rootToFetch);
    } catch (e) {
      console.error("Failed to show modal:", e);
    }
  } else {
    console.error("Browser modal not found in DOM");
  }
}

function closeBrowser() {
  const modal = document.getElementById("browser-modal");
  if (modal) modal.close();
}

async function fetchFs(path) {
  if (!state.apiBaseUrl) {
      console.error("No API Base URL defined");
      return;
  }
  try {
    // Ensure path is clean before sending
    const cleanPath = path.replace(/^"|"$/g, '');
    console.log(`Fetching ${state.apiBaseUrl}/fs/list?path=${encodeURIComponent(cleanPath)}`);
    const response = await fetch(`${state.apiBaseUrl}/fs/list?path=${encodeURIComponent(cleanPath)}`);
    if (response.ok) {
      const data = await response.json();
      currentBrowserPath = data.current;
      renderBrowser(data);
    } else {
      addLog(`Error listing directory: ${response.statusText}`);
    }
  } catch (error) {
    console.error("FS Fetch Error", error);
    addLog("Failed to fetch directory listing.");
  }
}

function renderBrowser(data) {
  const list = document.getElementById("browser-list");
  const pathInput = document.getElementById("browser-current-path");
  if (!list || !pathInput) return;

  pathInput.value = data.current;
  list.innerHTML = "";

  data.entries.forEach(entry => {
    if (!entry.is_dir) return;

    const li = document.createElement("li");
    li.className = "browser-item folder";
    li.textContent = entry.name;
    li.onclick = () => fetchFs(entry.path);
    list.appendChild(li);
  });
}

function confirmBrowserSelection() {
  if (currentBrowserPath) {
    changeRoot(currentBrowserPath);
    closeBrowser();
  }
}

// --- Backend Management ---

async function fetchBackends() {
  if (!state.apiBaseUrl) return;
  try {
    const response = await fetch(`${state.apiBaseUrl}/backends`);
    if (response.ok) {
      state.backends = await response.json();
      // Default to first backend if not set
      if (!state.currentBackend && state.backends.length > 0) {
        state.currentBackend = state.backends[0].name;
      }
      renderBackendSelector();
    }
  } catch (error) {
    console.error("Failed to fetch backends:", error);
    addLog("Failed to fetch backends", "ERROR");
  }
}

function renderBackendSelector() {
  const header = document.querySelector("header .header-content");
  if (!header) return;

  let selector = document.getElementById("backend-selector");
  if (!selector) {
    const container = document.createElement("div");
    container.className = "backend-selector-container";
    container.style.marginLeft = "20px";
    container.style.display = "flex";
    container.style.alignItems = "center";
    
    const label = document.createElement("span");
    label.textContent = "Project: ";
    label.style.marginRight = "5px";
    label.style.fontSize = "0.9rem";
    label.style.opacity = "0.8";
    
    selector = document.createElement("select");
    selector.id = "backend-selector";
    selector.className = "backend-select";
    selector.style.padding = "4px 8px";
    selector.style.borderRadius = "4px";
    selector.style.border = "1px solid var(--border-color)";
    selector.style.background = "var(--bg-secondary)";
    selector.style.color = "var(--text-primary)";
    
    selector.onchange = (e) => {
      state.currentBackend = e.target.value;
      addLog(`Switched to backend: ${state.currentBackend}`);
      // Refresh data
      startScan(); 
    };
    
    container.appendChild(label);
    container.appendChild(selector);
    
    // Insert after title or logo
    const title = header.querySelector("h1");
    if (title) {
        title.parentNode.insertBefore(container, title.nextSibling);
    } else {
        header.appendChild(container);
    }
  }

  // Update options
  selector.innerHTML = "";
  state.backends.forEach(backend => {
    const option = document.createElement("option");
    option.value = backend.name;
    option.textContent = `${backend.name} (${backend.type})`;
    if (backend.name === state.currentBackend) {
      option.selected = true;
    }
    selector.appendChild(option);
  });
}

// --- Initialization ---
async function init() {
  addLog("App initialized v0.1.4", "INFO");
  const savedLang = localStorage.getItem("jupiter-lang") || "fr";
  await setLanguage(savedLang);
  
  const savedTheme = localStorage.getItem("jupiter-theme") || "dark";
  setTheme(savedTheme);

  state.apiBaseUrl = inferApiBaseUrl();
  renderDiagnostics(state.report);
  renderStatusBadges(state.report);
  
  await loadContext();
  await loadCachedReport();
  await fetchBackends(); // Fetch backends early
  fetchMeetingStatus();
  connectWebSocket();
  bindUpload();
  bindActions();
  renderReport(null);
  pushLiveEvent("Startup", "UI ready. Load a report or use the sample.");
}

window.addEventListener("DOMContentLoaded", init);