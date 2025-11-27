const state = {
  isScanning: false,
  context: null,
  report: null,
  view: "dashboard",
  theme: "dark",
  apiBaseUrl: null,
  i18n: {
    lang: "fr",
    translations: {},
  },
  logs: [],
  liveEvents: [],
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
    addLog(`Error loading language ${lang}`);
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

async function startScan() {
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

  try {
    const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ show_hidden: false, ignore_globs: [] }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`${t("scan_error_server")} (${response.status}): ${errorText}`);
    }

    const report = await response.json();
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
    addLog(`${t("scan_error_log")}: ${errorMessage}`);
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
  switch (action) {
    case "load-sample":
      renderReport(sampleReport);
      addLog("Sample report loaded.");
      break;
    case "start-scan":
      startScan();
      break;
    case "start-watch":
      showPlaceholder("Watch");
      break;
    case "open-settings":
      setView("settings");
      break;
    case "toggle-theme":
      setTheme(state.theme === "dark" ? "light" : "dark");
      break;
    case "change-language":
      setLanguage(data.lang);
      break;
    default:
      showPlaceholder(action);
      break;
  }
}

// --- UI Rendering ---

function renderReport(report) {
  state.report = report;
  renderStats(report);
  renderUploadMeta(report);
  renderFiles(report);
  renderAnalysis(report);
  renderHotspots(report);
  renderAlerts(report);
  renderPluginList(report);
  renderStatusBadges(report);
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

    const stats = [
        { label: t("files_view"), value: files.length.toLocaleString(state.i18n.lang) },
        { label: t("analysis_avg_size"), value: bytesToHuman(totalSize) },
        { label: t("analysis_freshest"), value: lastUpdated ? formatDate(lastUpdated.modified_timestamp) : "-" },
        { label: "Dernier scan", value: report?.last_scan_timestamp ? formatDate(report.last_scan_timestamp) : "N/A" },
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
            const row = document.createElement("tr");
            row.innerHTML = `<td>${file.path}</td><td class="numeric">${bytesToHuman(file.size_bytes || 0)}</td><td class="numeric">${formatDate(file.modified_timestamp)}</td>`;
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
        { label: t("analysis_dynamic"), value: t("placeholder_dynamic") },
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

    if (!report || !report.hotspots || !report.hotspots.most_functions) {
        empty.style.display = "block";
        empty.textContent = t('hotspots_empty');
        return;
    }

    empty.style.display = "none";
    const candidates = report.hotspots.most_functions.slice(0, 5);

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

  badges.forEach((badge) => {
    const pill = document.createElement("span");
    pill.className = "badge";
    pill.textContent = `${badge.icon} ${badge.label}: ${badge.value}`;
    container.appendChild(pill);
  });
}

function renderPluginList(report) {
  const container = document.getElementById("plugin-list");
  if (!container) return;
  container.innerHTML = "";

  const plugins = Array.isArray(report?.plugins) && report.plugins.length
    ? report.plugins
    : sampleReport.plugins;

  if (!plugins.length) {
    container.innerHTML = `<p class="empty">${t("plugins_empty")}</p>`;
    return;
  }

  plugins.forEach((plugin) => {
    const card = document.createElement("div");
    card.className = "plugin-card";

    const statusText = t(`plugin_status_${plugin.status}`) || plugin.status;
    card.innerHTML = `
      <p class="label">${t("plugin_name_label")}</p>
      <p class="value">${plugin.name}</p>
      <p class="muted">${plugin.description || t("plugins_empty")}</p>
      <p class="small">${t("plugin_status_label")}: ${statusText}</p>
    `;
    container.appendChild(card);
  });
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

function addLog(message) {
  const entry = { message, timestamp: new Date() };
  state.logs.unshift(entry);
  state.logs = state.logs.slice(0, 8);
  const container = document.getElementById("log-stream");
  if (!container) return;
  container.innerHTML = "";
  state.logs.forEach((log) => {
    const item = document.createElement("div");
    item.className = "log-entry";
    item.textContent = `[${log.timestamp.toLocaleTimeString()}] ${log.message}`;
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
  } catch (error) {
    console.warn("Could not load context", error);
    const rootLabel = document.getElementById("root-path");
    if (rootLabel) rootLabel.textContent = "N/A";
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
}

function showPlaceholder(action) {
  const detail = `${action}: This action is a placeholder for future functionality.`;
  addLog(detail);
  pushLiveEvent("Placeholder", detail);
}

function bindActions() {
  document.body.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    const { action, lang } = target.dataset;
    handleAction(action, { lang });
  });

  document.querySelectorAll(".nav-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      const { view } = event.currentTarget.dataset;
      setView(view);
    });
  });
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

// --- Initialization ---
async function init() {
  const savedLang = localStorage.getItem("jupiter-lang") || "fr";
  await setLanguage(savedLang);
  
  const savedTheme = localStorage.getItem("jupiter-theme") || "dark";
  setTheme(savedTheme);

  state.apiBaseUrl = inferApiBaseUrl();
  renderDiagnostics(state.report);
  renderStatusBadges(state.report);

  loadContext();
  bindUpload();
  bindActions();
  renderReport(null);
  pushLiveEvent("Startup", "UI ready. Load a report or use the sample.");
}

window.addEventListener("DOMContentLoaded", init);