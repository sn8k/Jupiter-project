const state = {
  isScanning: false,
  isRefreshingSuggestions: false,
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
  },
  snapshots: [],
  snapshotDiff: null,
  snapshotSelection: { a: null, b: null },
  lastSnapshotFetch: 0,
  token: null,
  userRole: null,
  sortState: {
    files: { key: 'size_bytes', dir: 'desc' },
    functions: { key: 'calls', dir: 'desc' }
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

function formatBytes(value) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
}

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
    const response = await apiFetch(`${apiBaseUrl}/scan`, {
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
    await loadSnapshots(true);
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
    case "open-scan-modal": {
      const hiddenInput = document.getElementById("scan-show-hidden");
      const incrementalInput = document.getElementById("scan-incremental");
      const ignoreInput = document.getElementById("scan-ignore");

      const savedHidden = localStorage.getItem("jupiter_scan_hidden");
      const savedIncremental = localStorage.getItem("jupiter_scan_incremental");
      const savedIgnore = localStorage.getItem("jupiter_scan_ignore");

      if (hiddenInput && savedHidden !== null) hiddenInput.checked = savedHidden === "true";
      if (incrementalInput && savedIncremental !== null) incrementalInput.checked = savedIncremental === "true";
      if (ignoreInput && savedIgnore !== null) ignoreInput.value = savedIgnore;

      openModal("scan-modal");
      break;
    }
    case "close-scan-modal":
      closeModal("scan-modal");
      break;
    case "confirm-scan":
      startScanWithOptions();
      break;
    case "open-run-modal": {
      const runCommandInput = document.getElementById("run-command");
      const runDynamicInput = document.getElementById("run-dynamic");
      const savedRunCommand = localStorage.getItem("jupiter_run_command");
      const savedRunDynamic = localStorage.getItem("jupiter_run_dynamic");

      if (runCommandInput && savedRunCommand !== null) runCommandInput.value = savedRunCommand;
      if (runDynamicInput && savedRunDynamic !== null) runDynamicInput.checked = savedRunDynamic === "true";

      openModal("run-modal");
      break;
    }
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
    case "open-project-wizard":
      openProjectWizard();
      break;
    case "toggle-plugin":
      togglePlugin(data.pluginName, data.pluginState === 'true');
      break;
    case "refresh-snapshots":
      loadSnapshots(true);
      break;
    case "refresh-graph":
      renderGraph();
      break;
    case "refresh-suggestions":
      refreshSuggestions();
      break;
    case "copy-snapshot-id":
      if (navigator.clipboard) {
        navigator.clipboard.writeText(data.snapshotId).then(() => addLog(`Snapshot ${data.snapshotId} copied.`));
      } else {
        alert(data.snapshotId);
      }
      break;
    case "open-raw-config":
      openRawConfigEditor();
      break;
    case "close-raw-config":
      closeModal("raw-config-modal");
      break;
    case "save-raw-config":
      saveRawConfig();
      break;
    case "add-user":
      addUser();
      break;
    case "delete-user":
      deleteUser(data.name);
      break;
    case "export-quality":
      if (state.report && state.report.quality) {
        const exportPayload = {
            context: {
                project_root: state.report.root,
                scan_timestamp: state.report.last_scan_timestamp,
                type: "quality_report"
            },
            data: state.report.quality
        };
        exportData(exportPayload, "jupiter-quality-report.json");
      } else {
        alert(t("no_data_to_export") || "No data to export. Please run a scan first.");
      }
      break;
    case "export-suggestions":
      if (state.report && state.report.refactoring) {
        const exportPayload = {
            context: {
                project_root: state.report.root,
                scan_timestamp: state.report.last_scan_timestamp,
                type: "suggestions_report"
            },
            data: state.report.refactoring
        };
        exportData(exportPayload, "jupiter-suggestions-report.json");
      } else {
        alert(t("no_data_to_export") || "No data to export. Please run a scan first.");
      }
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
  const hiddenInput = document.getElementById("scan-show-hidden");
  const incrementalInput = document.getElementById("scan-incremental");
  const ignoreInput = document.getElementById("scan-ignore");

  const showHidden = hiddenInput ? hiddenInput.checked : false;
  const incremental = incrementalInput ? incrementalInput.checked : false;
  const ignoreStr = ignoreInput ? ignoreInput.value : "";
  const ignoreGlobs = ignoreStr ? ignoreStr.split(",").map(s => s.trim()).filter(s => s) : [];

  localStorage.setItem("jupiter_scan_hidden", showHidden ? "true" : "false");
  localStorage.setItem("jupiter_scan_incremental", incremental ? "true" : "false");
  localStorage.setItem("jupiter_scan_ignore", ignoreStr);

  closeModal("scan-modal");

  await startScan({ show_hidden: showHidden, incremental, ignore_globs: ignoreGlobs });
}

async function runCommand() {
  const commandInput = document.getElementById("run-command");
  const dynamicInput = document.getElementById("run-dynamic");
  const outputDiv = document.getElementById("run-output");

  if (!commandInput || !dynamicInput || !outputDiv) return;

  const commandStr = commandInput.value;
  const withDynamic = dynamicInput.checked;
    
  if (!commandStr) return;

  // Save settings
  localStorage.setItem("jupiter_run_command", commandStr);
  localStorage.setItem("jupiter_run_dynamic", withDynamic ? "true" : "false");
    
  outputDiv.textContent = "Running...";
  outputDiv.classList.remove("hidden");
    
    try {
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        // Split command string simply by space (naive)
        // Ideally the backend should handle string parsing or we use a library
        // But for now we send the string and let backend handle it or split here
        // The API expects a list of strings.
        const command = commandStr.split(" "); 
        
        const response = await apiFetch(`${apiBaseUrl}/run`, {
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
        const response = await apiFetch(`${state.apiBaseUrl}/config`);
        if (response.ok) {
            const config = await response.json();
            console.log("Loaded config:", config);
            if (document.getElementById("conf-server-host")) document.getElementById("conf-server-host").value = config.server_host || "127.0.0.1";
            if (document.getElementById("conf-server-port")) document.getElementById("conf-server-port").value = config.server_port || 8000;
            if (document.getElementById("conf-gui-host")) document.getElementById("conf-gui-host").value = config.gui_host || "127.0.0.1";
            if (document.getElementById("conf-gui-port")) document.getElementById("conf-gui-port").value = config.gui_port || 8050;
            
            // Meeting
            if (document.getElementById("conf-meeting-enabled")) {
                document.getElementById("conf-meeting-enabled").checked = !!config.meeting_enabled;
            }
            if (document.getElementById("conf-meeting-key")) {
                document.getElementById("conf-meeting-key").value = config.meeting_device_key || "";
            }

            if (document.getElementById("conf-ui-theme")) document.getElementById("conf-ui-theme").value = config.ui_theme || "dark";
            if (document.getElementById("conf-ui-lang")) document.getElementById("conf-ui-lang").value = config.ui_language || "fr";
            
            // Performance
            if (document.getElementById("conf-perf-parallel")) document.getElementById("conf-perf-parallel").checked = config.perf_parallel_scan !== false;
            if (document.getElementById("conf-perf-workers")) document.getElementById("conf-perf-workers").value = config.perf_max_workers || 0;
            if (document.getElementById("conf-perf-timeout")) document.getElementById("conf-perf-timeout").value = config.perf_scan_timeout || 300;
            if (document.getElementById("conf-perf-graph-simple")) document.getElementById("conf-perf-graph-simple").checked = config.perf_graph_simplification || false;
            if (document.getElementById("conf-perf-graph-nodes")) document.getElementById("conf-perf-graph-nodes").value = config.perf_max_graph_nodes || 1000;
            
            // Security
            if (document.getElementById("conf-sec-allow-run")) document.getElementById("conf-sec-allow-run").checked = config.sec_allow_run !== false;

            // API Inspection
            if (document.getElementById("conf-api-connector")) {
                document.getElementById("conf-api-connector").value = config.api_connector || "";
                // Trigger change event to update UI state
                document.getElementById("conf-api-connector").dispatchEvent(new Event('change'));
            }
            if (document.getElementById("conf-api-app-var")) document.getElementById("conf-api-app-var").value = config.api_app_var || "";
            if (document.getElementById("conf-api-path")) document.getElementById("conf-api-path").value = config.api_path || "";

            // Load Users
            loadUsers();

        } else {
            console.error("Failed to load settings:", response.status);
            addLog(`Failed to load settings: ${response.status}`, "ERROR");
        }
    } catch (e) {
        console.error("Failed to load settings", e);
        addLog(`Failed to load settings: ${e.message}`, "ERROR");
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
        plugins_disabled: [],
        
        // Performance
        perf_parallel_scan: formData.get("perf_parallel_scan") === "on",
        perf_max_workers: parseInt(formData.get("perf_max_workers")) || null,
        perf_scan_timeout: parseInt(formData.get("perf_scan_timeout")) || 300,
        perf_graph_simplification: formData.get("perf_graph_simplification") === "on",
        perf_max_graph_nodes: parseInt(formData.get("perf_max_graph_nodes")) || 1000,
        
        // Security
        sec_allow_run: formData.get("sec_allow_run") === "on",

        // API Inspection
        api_connector: formData.get("api_connector") || null,
        api_app_var: formData.get("api_app_var") || null,
        api_path: formData.get("api_path") || null
    };
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config`, {
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
    const response = await apiFetch(`${state.apiBaseUrl}/config/root`, {
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
  renderApi(report);
  renderAnalysis(report);
  renderHotspots(report);
  renderAlerts(report);
  renderPluginList(report);
  renderStatusBadges(report);
  renderQuality(report);
  renderDiagnostics(report);
  
  if (state.view === 'suggestions') {
      renderSuggestions();
  }

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

function handleSort(view, key) {
  const current = state.sortState[view];
  if (current.key === key) {
    current.dir = current.dir === 'asc' ? 'desc' : 'asc';
  } else {
    current.key = key;
    current.dir = 'desc'; // Default to desc for numbers usually
  }
  
  if (view === 'files') renderFiles(state.report);
  if (view === 'functions') renderFunctions(state.report);
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

    const { key, dir } = state.sortState.files;
    files.sort((a, b) => {
        let valA, valB;
        if (key === 'func_count') {
            valA = a.language_analysis?.defined_functions?.length || 0;
            valB = b.language_analysis?.defined_functions?.length || 0;
        } else {
            valA = a[key] || 0;
            valB = b[key] || 0;
        }
        
        if (typeof valA === 'string') {
            return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return dir === 'asc' ? valA - valB : valB - valA;
    });

    files
        .slice(0, 200)
        .forEach((file) => {
            const funcCount = file.language_analysis?.defined_functions?.length || 0;
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${file.path}</td>
                <td class="numeric">${bytesToHuman(file.size_bytes || 0)}</td>
                <td class="numeric">${formatDate(file.modified_timestamp)}</td>
                <td class="numeric">${funcCount}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="triggerSimulation('file', '${file.path.replace(/\\/g, '\\\\')}')" title="Simulate Removal">🗑️</button>
                </td>
            `;
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

    const { key, dir } = state.sortState.functions;
    allFunctions.sort((a, b) => {
        const valA = a[key];
        const valB = b[key];
        if (typeof valA === 'string') {
            return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return dir === 'asc' ? valA - valB : valB - valA;
    });

    allFunctions.forEach(func => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${func.name}</td>
            <td>${func.file}</td>
            <td class="numeric">${func.calls}</td>
            <td>${func.status}</td>
            <td class="actions">
                <button class="btn-icon" onclick="triggerSimulation('function', '${func.file.replace(/\\/g, '\\\\')}', '${func.name}')" title="Simulate Removal">🗑️</button>
            </td>
        `;
        body.appendChild(row);
    });
}

function renderApi(report) {
    const body = document.getElementById("api-endpoints-body");
    const empty = document.getElementById("api-empty");
    const badge = document.getElementById("api-status-badge");
    if (!body || !empty) return;
    
    body.innerHTML = "";
    
    const apiData = report?.api;
    
    if (!apiData || !apiData.endpoints || !apiData.endpoints.length) {
        // If we have a config but no endpoints, it might be a connection error or empty API
        if (apiData && apiData.config && apiData.config.base_url) {
             empty.style.display = "block";
             empty.textContent = "Aucun endpoint détecté ou erreur de connexion.";
             if (badge) badge.innerHTML = `<span class="badge active">Connecté: ${apiData.config.base_url}</span>`;
             return;
        }

        empty.style.display = "block";
        empty.textContent = "Aucune API configurée ou détectée.";
        if (badge) badge.innerHTML = `<span class="badge">Non configuré</span>`;
        return;
    }
    
    empty.style.display = "none";
    if (badge) {
        const url = apiData.config?.base_url || "Configuré";
        badge.innerHTML = `<span class="badge active">Connecté: ${url}</span>`;
    }
    
    apiData.endpoints.forEach(ep => {
        const row = document.createElement("tr");
        const tags = ep.tags ? ep.tags.map(t => `<span class="tag">${t}</span>`).join(" ") : "";
        row.innerHTML = `
            <td><span class="method method-${ep.method.toLowerCase()}">${ep.method}</span></td>
            <td><code>${ep.path}</code></td>
            <td>${ep.summary || "-"}</td>
            <td>${tags}</td>
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

    // Add JS/TS stats if available
    const jsFiles = files.filter(f => ["js", "ts", "jsx", "tsx"].includes(f.file_type));
    if (jsFiles.length > 0) {
        const jsFuncCount = jsFiles.reduce((acc, f) => acc + (f.language_analysis?.defined_functions?.length || 0), 0);
        stats.push({ label: "Fichiers JS/TS", value: jsFiles.length });
        stats.push({ label: "Fonctions JS/TS", value: jsFuncCount });
    }

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
    
    let configHtml = "";
    if (plugin.name === "notifications_webhook" && plugin.enabled) {
        const url = plugin.config && plugin.config.url ? plugin.config.url : "";
        configHtml = `
            <div class="plugin-config" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-color);">
                <label class="small muted" style="display:block; margin-bottom: 5px;">Webhook URL</label>
                <div style="display:flex; gap: 5px;">
                    <input type="text" class="webhook-url-input" value="${url}" placeholder="http://..." style="flex:1; padding: 4px; background: var(--bg-input); border: 1px solid var(--border-color); color: var(--text-main);">
                    <button class="small primary save-webhook-btn" data-plugin="${plugin.name}">Save</button>
                </div>
            </div>
        `;
    }

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
      ${configHtml}
    `;
    
    const saveBtn = card.querySelector(".save-webhook-btn");
    if (saveBtn) {
        saveBtn.addEventListener("click", (e) => {
            const input = card.querySelector(".webhook-url-input");
            savePluginConfig(plugin.name, { url: input.value });
        });
    }

    container.appendChild(card);
  });
}

async function savePluginConfig(name, config) {
    if (!state.apiBaseUrl) return;
    try {
        const response = await fetch(`${state.apiBaseUrl}/plugins/${name}/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config)
        });
        if (response.ok) {
            // alert("Configuration saved!"); // Optional: show feedback
            fetchPlugins(); 
        } else {
            console.error("Failed to save configuration.");
        }
    } catch (e) {
        console.error("Failed to save plugin config", e);
    }
}

async function fetchPlugins() {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/plugins`);
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
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/${name}/toggle?enable=${enable}`, { method: "POST" });
        if (response.ok) {
            fetchPlugins(); // Refresh list
            addLog(`Plugin ${name} ${enable ? "enabled" : "disabled"}`);
        }
    } catch (e) {
        console.error("Failed to toggle plugin", e);
    }
}

// --- Projects Management ---

async function loadProjects() {
    if (!state.apiBaseUrl) state.apiBaseUrl = inferApiBaseUrl();
    if (!state.apiBaseUrl) return;

    try {
        const response = await apiFetch(`${state.apiBaseUrl}/system/projects`);
        if (response.ok) {
            const projects = await response.json();
            renderProjects(projects);
        } else {
            console.error("Failed to load projects");
            addLog("Erreur lors du chargement des projets", "ERROR");
        }
    } catch (e) {
        console.error("Error loading projects", e);
        addLog("Erreur réseau (projets)", "ERROR");
    }
}

function renderProjects(projects) {
    const tbody = document.querySelector("#projects-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    projects.forEach(p => {
        const tr = document.createElement("tr");
        
        const nameTd = document.createElement("td");
        nameTd.innerHTML = `<strong>${p.project_name}</strong>`;
        tr.appendChild(nameTd);

        const pathTd = document.createElement("td");
        pathTd.textContent = p.project_path;
        pathTd.classList.add("muted", "small", "mono");
        tr.appendChild(pathTd);

        const statusTd = document.createElement("td");
        if (p.is_active) {
            const badge = document.createElement("span");
            badge.className = "badge active";
            badge.textContent = t("active") || "Actif";
            statusTd.appendChild(badge);
        } else {
            const badge = document.createElement("span");
            badge.className = "badge";
            badge.textContent = t("inactive") || "Inactif";
            statusTd.appendChild(badge);
        }
        tr.appendChild(statusTd);

        const actionsTd = document.createElement("td");
        actionsTd.style.display = "flex";
        actionsTd.style.gap = "0.5rem";

        if (!p.is_active) {
            const activateBtn = document.createElement("button");
            activateBtn.className = "small primary";
            activateBtn.textContent = t("activate") || "Activer";
            activateBtn.onclick = () => activateProject(p.project_id);
            actionsTd.appendChild(activateBtn);
        }

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "small secondary";
        deleteBtn.textContent = t("delete") || "Supprimer";
        deleteBtn.onclick = () => deleteProject(p.project_id, p.project_name);
        actionsTd.appendChild(deleteBtn);

        tr.appendChild(actionsTd);
        tbody.appendChild(tr);
    });
}

async function activateProject(projectId) {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/system/projects/${projectId}/activate`, { method: "POST" });
        if (response.ok) {
            addLog(t("project_activated") || "Projet activé", "INFO");
            window.location.reload(); 
        } else {
            const err = await response.json();
            alert("Erreur: " + (err.detail || "Impossible d'activer le projet"));
        }
    } catch (e) {
        console.error(e);
        alert("Erreur réseau");
    }
}

async function deleteProject(projectId, projectName) {
    const msg = (t("delete_confirm") || "Voulez-vous vraiment supprimer le projet \"{name}\" ?").replace("{name}", projectName);
    if (!confirm(msg)) {
        return;
    }

    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/system/projects/${projectId}`, { method: "DELETE" });
        if (response.ok) {
            addLog(t("project_deleted") || "Projet supprimé", "INFO");
            loadProjects(); 
            // If we deleted the active project, the backend might have switched.
            // We should check if we need to reload.
            // But for now, loadProjects updates the list.
            // If the active project was deleted, the backend sets another one as active.
            // We might want to reload to reflect that in the UI context.
            // Let's check if the deleted project was the active one.
            // Actually, simpler to just reload if we deleted the active one, but we don't know easily here.
            // Let's just reload context.
            loadContext();
        } else {
            const err = await response.json();
            alert("Erreur: " + (err.detail || "Impossible de supprimer le projet"));
        }
    } catch (e) {
        console.error(e);
        alert("Erreur réseau");
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
    if (rootLabel) {
        const name = payload.project_name || "Projet";
        const root = payload.root || "(undefined)";
        rootLabel.textContent = `${name} (${root})`;
        rootLabel.title = root;
    }
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
    const response = await apiFetch(`${state.apiBaseUrl}/reports/last`);
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

async function loadSnapshots(force = false) {
  if (!state.apiBaseUrl) return;
  const now = Date.now();
  if (!force && state.lastSnapshotFetch && now - state.lastSnapshotFetch < 5000) {
    return;
  }

  try {
    const response = await apiFetch(`${state.apiBaseUrl}/snapshots`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.snapshots = payload.snapshots || [];
    state.lastSnapshotFetch = now;
    renderSnapshots();
  } catch (error) {
    console.error("Failed to load snapshots", error);
    addLog(`Snapshot fetch failed: ${error.message}`, "ERROR");
  }
}

async function fetchSnapshotDiff() {
  if (!state.apiBaseUrl) return;
  const { a, b } = state.snapshotSelection;
  if (!a || !b) {
    alert(t("history_diff_missing"));
    return;
  }

  try {
    const params = new URLSearchParams({ id_a: a, id_b: b });
    const response = await apiFetch(`${state.apiBaseUrl}/snapshots/diff?${params.toString()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.snapshotDiff = payload;
    renderSnapshotDiff();
    addLog(`Loaded diff ${a} → ${b}`);
  } catch (error) {
    console.error("Failed to diff snapshots", error);
    addLog(`Snapshot diff failed: ${error.message}`, "ERROR");
  }
}

function renderSnapshots() {
  updateSnapshotSelectors();
  renderSnapshotSelectionMeta();

  const body = document.getElementById("snapshot-table-body");
  const empty = document.getElementById("snapshots-empty");
  if (!body || !empty) return;

  body.innerHTML = "";
  if (!state.snapshots.length) {
    empty.textContent = t("history_empty");
    empty.classList.remove("hidden");
    return;
  }

  empty.classList.add("hidden");
  state.snapshots.forEach((snap) => {
    const row = document.createElement("tr");
    const ts = new Date(snap.timestamp * 1000);
    row.innerHTML = `
      <td>${snap.label}</td>
      <td>${ts.toLocaleString()}</td>
      <td class="numeric">${snap.file_count}</td>
      <td class="numeric">${formatBytes(snap.total_size_bytes)}</td>
      <td>
        <button class="ghost small" data-action="copy-snapshot-id" data-snapshot-id="${snap.id}">${t("history_copy_id")}</button>
      </td>
    `;
    body.appendChild(row);
  });
}

function updateSnapshotSelectors() {
  const selectA = document.getElementById("snapshot-select-a");
  const selectB = document.getElementById("snapshot-select-b");
  if (!selectA || !selectB) return;

  const buildOptions = (selected) => {
    const fragment = document.createDocumentFragment();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = t("history_select_placeholder");
    fragment.appendChild(placeholder);
    state.snapshots.forEach((snap) => {
      const option = document.createElement("option");
      option.value = snap.id;
      option.textContent = `${snap.label} (${new Date(snap.timestamp * 1000).toLocaleString()})`;
      if (snap.id === selected) option.selected = true;
      fragment.appendChild(option);
    });
    return fragment;
  };

  selectA.innerHTML = "";
  selectA.appendChild(buildOptions(state.snapshotSelection.a));
  selectB.innerHTML = "";
  selectB.appendChild(buildOptions(state.snapshotSelection.b));
}

function renderSnapshotSelectionMeta() {
  const metaA = document.getElementById("snapshot-meta-a");
  const metaB = document.getElementById("snapshot-meta-b");
  if (!metaA || !metaB) return;

  const render = (snap) => {
    if (!snap) return `<p class="muted">${t("history_slot_empty")}</p>`;
    const ts = new Date(snap.timestamp * 1000).toLocaleString();
    return `
      <p class="strong">${snap.label}</p>
      <p class="muted">${ts}</p>
      <p>${t("history_files")}: ${snap.file_count} · ${t("history_functions")}: ${snap.function_count}</p>
    `;
  };

  const currentA = state.snapshots.find((s) => s.id === state.snapshotSelection.a);
  const currentB = state.snapshots.find((s) => s.id === state.snapshotSelection.b);
  metaA.innerHTML = render(currentA);
  metaB.innerHTML = render(currentB);
}

function renderSnapshotDiff() {
  const container = document.getElementById("snapshot-diff-output");
  if (!container) return;

  if (!state.snapshotDiff) {
    container.innerHTML = `<p class="muted">${t("history_diff_placeholder")}</p>`;
    return;
  }

  const diff = state.snapshotDiff;
  const metrics = diff.diff.metrics_delta;
  const files = diff.diff;
  container.innerHTML = `
    <div class="stats-grid">
      <div><strong>${t("history_metric_files")}</strong><p>${metrics.file_count}</p></div>
      <div><strong>${t("history_metric_size")}</strong><p>${formatBytes(metrics.total_size_bytes)}</p></div>
      <div><strong>${t("history_metric_funcs")}</strong><p>${metrics.function_count}</p></div>
      <div><strong>${t("history_metric_unused")}</strong><p>${metrics.unused_function_count}</p></div>
    </div>
    <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:0.5rem;">
      <p>${t("history_added")}: ${files.files_added.length}</p>
      <p>${t("history_removed")}: ${files.files_removed.length}</p>
      <p>${t("history_modified")}: ${files.files_modified.length}</p>
    </div>
  `;
}

function bindHistoryControls() {
  const selectA = document.getElementById("snapshot-select-a");
  const selectB = document.getElementById("snapshot-select-b");
  const diffBtn = document.getElementById("snapshot-diff-btn");

  if (selectA) {
    selectA.addEventListener("change", (event) => {
      state.snapshotSelection.a = event.target.value || null;
      renderSnapshotSelectionMeta();
    });
  }

  if (selectB) {
    selectB.addEventListener("change", (event) => {
      state.snapshotSelection.b = event.target.value || null;
      renderSnapshotSelectionMeta();
    });
  }

  if (diffBtn) {
    diffBtn.addEventListener("click", fetchSnapshotDiff);
  }

  updateSnapshotSelectors();
  renderSnapshotSelectionMeta();
  renderSnapshotDiff();
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
  } else if (view === "history") {
    loadSnapshots();
  } else if (view === "graph") {
    renderGraph();
  } else if (view === "suggestions") {
    renderSuggestions();
  } else if (view === "projects") {
    loadProjects();
  }
}

async function refreshSuggestions() {
  if (!state.report) {
    const message = t("suggestions_no_report") || "No report available. Please run a scan first.";
    addLog(message, "WARN");
    alert(message);
    return;
  }

  if (state.isRefreshingSuggestions) {
    return;
  }

  const apiBase = state.apiBaseUrl || inferApiBaseUrl();
  if (!apiBase) {
    const err = t("error_fetch") || "Missing API base URL.";
    addLog(err, "ERROR");
    alert(err);
    return;
  }

  state.apiBaseUrl = apiBase;
  state.isRefreshingSuggestions = true;
  const button = document.querySelector('[data-action="refresh-suggestions"]');
  const originalLabel = button ? button.textContent : null;
  if (button) {
    button.disabled = true;
    button.dataset.originalLabel = originalLabel || "";
    button.textContent = t("suggestions_refreshing") || "Refreshing…";
  }

  try {
    const params = new URLSearchParams({ top: "5" });
    if (state.currentBackend) {
      params.set("backend_name", state.currentBackend);
    }
    const response = await apiFetch(`${apiBase}/analyze?${params.toString()}`);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status} – ${errorText}`);
    }

    const summary = await response.json();
    state.report = state.report || {};
    state.report.refactoring = summary.refactoring || [];
    renderSuggestions();
    addLog(t("suggestions_refresh_success") || "AI suggestions updated.");
  } catch (error) {
    console.error("Failed to refresh suggestions", error);
    const message = t("suggestions_refresh_error") || "Unable to refresh suggestions";
    addLog(`${message}: ${error.message}`, "ERROR");
    alert(`${message}: ${error.message}`);
  } finally {
    state.isRefreshingSuggestions = false;
    if (button) {
      button.disabled = false;
      button.textContent = button.dataset.originalLabel || t("history_refresh") || "Refresh";
      delete button.dataset.originalLabel;
    }
  }
}

function renderSuggestions() {
  const list = document.getElementById("suggestions-list");
  if (!list) return;
  list.innerHTML = "";

  if (!state.report) {
    list.innerHTML = '<p class="muted">Aucun rapport disponible. Lancez une analyse.</p>';
    return;
  }

  if (!state.report.refactoring || state.report.refactoring.length === 0) {
    list.innerHTML = '<p class="muted">Aucune suggestion de refactoring trouvée pour ce scan.</p>';
    return;
  }

  state.report.refactoring.forEach(s => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong>${s.path}</strong>
        <span class="badge ${s.severity === 'critical' ? 'error' : s.severity === 'warning' ? 'warning' : 'info'}">${s.severity}</span>
      </div>
      <p><em>${s.type}</em>: ${s.details}</p>
    `;
    list.appendChild(item);
  });
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
      let parsed = null;
      if (typeof event.data === "string") {
        try {
          parsed = JSON.parse(event.data);
        } catch (err) {
          parsed = null;
        }
      }

      if (parsed && parsed.type === "PLUGIN_NOTIFICATION") {
        const payload = parsed.payload || {};
        const source = payload.source || "Plugin";
        const detail = payload.message || JSON.stringify(payload.details || {});
        pushLiveEvent(source, detail);
        addLog(`${source}: ${detail}`);
        return;
      }

      if (parsed) {
        const detail = parsed.payload && Object.keys(parsed.payload).length ? JSON.stringify(parsed.payload) : "";
        pushLiveEvent(parsed.type || "Server", detail || "(empty payload)");
        addLog(`WS: ${parsed.type}`);
      } else {
        pushLiveEvent("Server", event.data);
        addLog(`WS: ${event.data}`);
      }

      if (!parsed && typeof event.data === "string" && event.data.startsWith("Snapshot stored")) {
        loadSnapshots(true);
        if (state.view === "graph") renderGraph();
      }
      
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
      if (state.browserMode === 'wizard') {
          // In wizard mode, start from current directory if possible, or root
          rootToFetch = ".";
      }
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
  const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
  try {
    // Ensure path is clean before sending
    const cleanPath = path.replace(/^"|"$/g, '');
    console.log(`Fetching ${apiBaseUrl}/fs/list?path=${encodeURIComponent(cleanPath)}`);
    
    // Use fetch directly if no token (setup mode) or apiFetch if logged in
    const headers = state.token ? { 'Authorization': `Bearer ${state.token}` } : {};
    
    const response = await fetch(`${apiBaseUrl}/fs/list?path=${encodeURIComponent(cleanPath)}`, {
        headers: headers
    });
    
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
    if (state.browserMode === 'wizard') {
        const input = document.getElementById("project-path");
        if (input) input.value = currentBrowserPath;
        closeBrowser();
        // Reset mode
        state.browserMode = null;
    } else {
        changeRoot(currentBrowserPath);
        closeBrowser();
    }
  }
}

function openBrowserForWizard() {
    state.browserMode = 'wizard';
    openBrowser();
}

// --- Backend Management ---

async function fetchBackends() {
  if (!state.apiBaseUrl) return;
  try {
    const response = await apiFetch(`${state.apiBaseUrl}/backends`);
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
  addLog("App initialized v1.0.1", "INFO");
  const savedLang = localStorage.getItem("jupiter-lang") || "fr";
  await setLanguage(savedLang);
  
  const savedTheme = localStorage.getItem("jupiter-theme") || "dark";
  setTheme(savedTheme);

  state.apiBaseUrl = inferApiBaseUrl();

  // Load Token
  const savedToken = localStorage.getItem("jupiter-token");
  if (savedToken) {
      state.token = savedToken;
      // Verify silently
      try {
          const response = await fetch(`${state.apiBaseUrl}/me`, {
              headers: { 'Authorization': `Bearer ${savedToken}` }
          });
          if (response.ok) {
              const data = await response.json();
              state.userRole = data.role;
          } else {
              state.token = null;
              localStorage.removeItem("jupiter-token");
          }
      } catch (e) {
          console.warn("Could not verify token on init");
      }
  }
  updateProfileUI();

  renderDiagnostics(state.report);
  renderStatusBadges(state.report);
  
  await loadContext();
  await loadCachedReport();
  await fetchBackends(); // Fetch backends early
  fetchMeetingStatus();
  connectWebSocket();
  bindUpload();
  bindActions();
  bindHistoryControls();
  // renderReport(null); // Do not reset report if loaded from cache
  pushLiveEvent("Startup", "UI ready. Load a report or use the sample.");
}

window.addEventListener("DOMContentLoaded", init);

// --- Simulation ---

async function triggerSimulation(type, path, funcName = null) {
    const modal = document.getElementById("simulation-modal");
    const content = document.getElementById("simulation-content");
    if (!modal || !content) return;
    
    content.innerHTML = `<p>${t("loading")}</p>`;
    modal.classList.remove("hidden");
    
    try {
        const response = await fetch(`${state.apiBaseUrl}/simulate/remove`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target_type: type,
                path: path,
                function_name: funcName
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Simulation failed");
        }
        
        const result = await response.json();
        renderSimulationResult(result);
    } catch (e) {
        content.innerHTML = `<div class="error">Error: ${e.message}</div>`;
    }
}

window.triggerSimulation = triggerSimulation;

// --- Authentication ---

async function apiFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (state.token) {
        options.headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    const response = await fetch(url, options);
    
    if (response.status === 401) {
        addLog("Authentication required", "WARNING");
        state.token = null;
        state.userRole = null;
        localStorage.removeItem("jupiter-token");
        updateProfileUI();
        openLoginModal();
        throw new Error("Unauthorized");
    }
    
    return response;
}

function openLoginModal() {
    const modal = document.getElementById("login-modal");
    if (modal) {
        modal.showModal();
        // Prevent closing by escape key if not logged in
        modal.addEventListener('cancel', (event) => {
            if (!state.token) {
                event.preventDefault();
            }
        });
    }
}

async function handleLogin() {
    const usernameInput = document.getElementById("login-username");
    const passwordInput = document.getElementById("login-password");
    const rememberInput = document.getElementById("login-remember");
    const errorDiv = document.getElementById("login-error");
    
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    
    if (!username || !password) return;
    
    try {
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        const response = await fetch(`${apiBaseUrl}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            state.token = data.token;
            state.userRole = data.role;
            
            if (rememberInput.checked) {
                localStorage.setItem("jupiter-token", data.token);
                localStorage.setItem("jupiter-username", data.name);
            } else {
                sessionStorage.setItem("jupiter-token", data.token);
            }
            
            updateProfileUI();
            document.getElementById("login-modal").close();
            addLog(`Logged in as ${data.name} (${data.role})`, "SUCCESS");
            
            // Refresh data
            if (state.view === "dashboard") startScan();
        } else {
            errorDiv.textContent = "Identifiants invalides";
            errorDiv.classList.remove("hidden");
        }
    } catch (e) {
        console.error(e);
        errorDiv.textContent = "Erreur de connexion";
        errorDiv.classList.remove("hidden");
    }
}

// Expose functions to window for inline onclick handlers
window.openLoginModal = openLoginModal;
window.handleLogin = handleLogin;
window.openBrowserForWizard = openBrowserForWizard;
window.handleCreateProject = handleCreateProject;

function logout() {
    state.token = null;
    state.userRole = null;
    localStorage.removeItem("jupiter-token");
    localStorage.removeItem("jupiter-username");
    sessionStorage.removeItem("jupiter-token");
    updateProfileUI();
    addLog("Logged out", "INFO");
    
    // Force login modal
    openLoginModal();
}

function updateProfileUI() {
    const btn = document.getElementById("user-profile-btn");
    if (!btn) return;
    
    if (state.token) {
        const username = localStorage.getItem("jupiter-username") || "User";
        btn.textContent = "👤 " + username;
        btn.title = "Click to logout";
        btn.onclick = () => {
            if (confirm("Logout?")) logout();
        };
        btn.classList.add("active");
    } else {
        btn.textContent = "👤";
        btn.title = "Not connected";
        btn.onclick = openLoginModal;
        btn.classList.remove("active");
    }
}

function checkAutoLogin() {
    const token = localStorage.getItem("jupiter-token") || sessionStorage.getItem("jupiter-token");
    if (token) {
        // Verify token validity
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        fetch(`${apiBaseUrl}/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(res => {
            if (res.ok) {
                return res.json().then(data => {
                    state.token = token;
                    state.userRole = data.role;
                    updateProfileUI();
                    addLog("Auto-login successful");
                    if (state.view === "dashboard") startScan();
                });
            } else {
                // Token invalid
                logout();
            }
        }).catch(() => {
            // Offline or error, maybe keep token but show warning?
            // For security, better to logout if we can't verify
            logout();
        });
    } else {
        openLoginModal();
    }
}

// Call checkAutoLogin on init
document.addEventListener("DOMContentLoaded", () => {
    // ... existing init code ...
    // We need to make sure this runs after other inits or is part of init
    setTimeout(checkAutoLogin, 500);
    setTimeout(checkProjectStatus, 1000);
});

async function checkProjectStatus() {
    const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
    try {
        // Try to get projects list. If empty, show wizard.
        // Note: /projects requires auth usually, but for setup we might need a way to check status publicly or handle 401
        // Actually, let's check /health or a specific status endpoint.
        // If we are logged in, we can check /projects.
        // If not logged in, we might need to login first? 
        // Assumption: Setup wizard is for local usage where we might be admin or it's open.
        // Let's try to fetch projects if we have a token, or if not, maybe we can't check?
        // Better approach: The backend should tell us if it's in "setup mode" via /health or /config
        
        const response = await fetch(`${apiBaseUrl}/projects`, {
             headers: state.token ? { 'Authorization': `Bearer ${state.token}` } : {}
        });
        
        if (response.status === 401) {
            // Not logged in, can't check projects. 
            // But if it's a fresh install, maybe there is no auth yet?
            // For now, let's assume if we can't list projects, we do nothing until login.
            return;
        }
        
        if (response.ok) {
            const projects = await response.json();
            if (projects.length === 0) {
                openProjectWizard();
            }
        }
    } catch (e) {
        console.error("Failed to check project status", e);
    }
}

function openProjectWizard() {
    const modal = document.getElementById("project-wizard-modal");
    if (modal) {
        modal.showModal();
        // Prevent closing
        modal.addEventListener('cancel', (event) => event.preventDefault());
    }
}

async function handleCreateProject() {
    const pathInput = document.getElementById("project-path");
    const nameInput = document.getElementById("project-name");
    const errorDiv = document.getElementById("project-wizard-error");
    
    const path = pathInput.value.trim();
    const name = nameInput.value.trim();
    
    if (!path || !name) return;
    
    try {
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        // We need to be admin to create project. If we are not logged in, this might fail.
        // For the wizard to work on fresh install, we might need a special "setup" token or endpoint that is open if no projects exist.
        // Or we assume the user logs in as default admin first.
        // Let's try to create.
        
        const response = await fetch(`${apiBaseUrl}/projects`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {})
            },
            body: JSON.stringify({ path, name })
        });
        
        if (response.ok) {
            const project = await response.json();
            addLog((t("project_created") || "Projet créé") + ": " + project.name);
            document.getElementById("project-wizard-modal").close();
            
            if (state.view === "projects") {
                await loadProjects();
            } else {
                window.location.reload();
            }
        } else {
            const err = await response.json();
            errorDiv.textContent = "Erreur: " + (err.detail || "Impossible de créer le projet");
            errorDiv.classList.remove("hidden");
        }
    } catch (e) {
        errorDiv.textContent = "Erreur réseau: " + e.message;
        errorDiv.classList.remove("hidden");
    }
}

function renderSimulationResult(result) {
    const content = document.getElementById("simulation-content");
    if (!content) return;
    
    let html = `<h3>Simulation: ${result.target}</h3>`;
    html += `<div class="risk-score risk-${result.risk_score}">${t("risk")}: ${result.risk_score.toUpperCase()}</div>`;
    
    if (!result.impacts || result.impacts.length === 0) {
        html += `<p>${t("no_impacts")}</p>`;
    } else {
        html += `<ul class="impact-list">`;
        result.impacts.forEach(imp => {
            html += `<li class="impact-item severity-${imp.severity}">
                <span class="severity">[${imp.severity.toUpperCase()}]</span>
                <span class="target">${imp.target}</span>
                <span class="details">${imp.details}</span>
            </li>`;
        });
        html += `</ul>`;
    }
    content.innerHTML = html;
}

async function renderGraph() {
  const container = document.getElementById("graph-container");
  if (!container) return;
  
  container.innerHTML = '<p style="padding: 1rem;">Chargement du graphe...</p>';
  
  try {
    const response = await apiFetch(`${state.apiBaseUrl}/graph`);
    if (!response.ok) throw new Error("Failed to fetch graph");
    const graphData = await response.json();
    
    container.innerHTML = ""; // Clear loading
    
    if (!graphData.nodes || graphData.nodes.length === 0) {
      container.innerHTML = '<p style="padding: 1rem;">Aucune donnée de graphe disponible.</p>';
      return;
    }
    
    // D3.js rendering
    if (typeof d3 === 'undefined') {
      container.innerHTML = '<p style="padding: 1rem;">Erreur: D3.js non chargé. Vérifiez votre connexion internet.</p>';
      return;
    }

    const width = container.clientWidth;
    const height = container.clientHeight;

    const svg = d3.select("#graph-container").append("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [0, 0, width, height])
        .attr("style", "max-width: 100%; height: auto;");

    // Add zoom capabilities
    const g = svg.append("g");
    
    svg.call(d3.zoom()
        .extent([[0, 0], [width, height]])
        .scaleExtent([0.1, 8])
        .on("zoom", ({transform}) => {
            g.attr("transform", transform);
        }));

    const simulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(60))
        .force("charge", d3.forceManyBody().strength(-100))
        .force("collide", d3.forceCollide().radius(15))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const link = g.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(graphData.links)
      .join("line")
        .attr("stroke-width", d => Math.sqrt(d.weight || 1));

    const node = g.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(graphData.nodes)
      .join("circle")
        .attr("r", 5)
        .attr("fill", d => {
            if (d.group === "js_file") return "#f1e05a"; // JS yellow
            if (d.group === "py_file") return "#3572A5"; // Python blue
            return d.type === "file" ? "#69b3a2" : "#ff7f0e";
        })
        .call(drag(simulation));

    node.append("title")
        .text(d => d.label);

    simulation.on("tick", () => {
      link
          .attr("x1", d => d.source.x)
          .attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x)
          .attr("y2", d => d.target.y);

      node
          .attr("cx", d => d.x)
          .attr("cy", d => d.y);
    });

    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      
      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      
      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
      
      return d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended);
    }

  } catch (e) {
    console.error(e);
    container.innerHTML = `<p style="padding: 1rem; color: red;">Erreur: ${e.message}</p>`;
  }
}

async function openRawConfigEditor() {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config/raw`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById("raw-config-editor").value = data.content;
            openModal("raw-config-modal");
        } else {
            alert("Failed to load raw config.");
        }
    } catch (e) {
        alert("Error loading raw config: " + e.message);
    }
}

async function saveRawConfig() {
    if (!state.apiBaseUrl) return;
    const content = document.getElementById("raw-config-editor").value;
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config/raw`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        
        if (response.ok) {
            alert("Configuration saved. Please restart the server if you changed critical settings.");
            closeModal("raw-config-modal");
        } else {
            const err = await response.json();
            alert("Failed to save config: " + (err.detail || "Unknown error"));
        }
    } catch (e) {
        alert("Error saving config: " + e.message);
    }
}

// --- User Management ---

async function loadUsers() {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/users`);
        if (response.ok) {
            const users = await response.json();
            renderUsers(users);
        }
    } catch (e) {
        console.error("Failed to load users", e);
    }
}

function renderUsers(users) {
    const tbody = document.getElementById("users-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    users.forEach(user => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${user.name}</td>
            <td>${user.role}</td>
            <td>
                <button class="btn-icon" onclick="handleAction('delete-user', {name: '${user.name}'})" title="Delete">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function addUser() {
    const name = document.getElementById("new-user-name").value;
    const token = document.getElementById("new-user-token").value;
    const role = document.getElementById("new-user-role").value;
    
    if (!name || !token) {
        alert("Name and Token are required");
        return;
    }
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, token, role })
        });
        
        if (response.ok) {
            const users = await response.json();
            renderUsers(users);
            document.getElementById("new-user-name").value = "";
            document.getElementById("new-user-token").value = "";
            addLog(`User ${name} added`);
        } else {
            alert("Failed to add user");
        }
    } catch (e) {
        alert("Error adding user: " + e.message);
    }
}

async function deleteUser(name) {
    if (!confirm(`Delete user ${name}?`)) return;
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/users/${name}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const users = await response.json();
            renderUsers(users);
            addLog(`User ${name} deleted`);
        } else {
            alert("Failed to delete user");
        }
    } catch (e) {
        alert("Error deleting user: " + e.message);
    }
}

// Update File Upload Listener
document.addEventListener('DOMContentLoaded', () => {
    // API Connector UI Logic
    const connectorSelect = document.getElementById('conf-api-connector');
    const appVarInput = document.getElementById('conf-api-app-var');
    const pathInput = document.getElementById('conf-api-path');

    if (connectorSelect) {
        connectorSelect.addEventListener('change', () => {
            const isLocal = connectorSelect.value === 'local';
            if (appVarInput) {
                appVarInput.disabled = isLocal;
                if (isLocal) appVarInput.placeholder = "(Auto: Jupiter API)";
                else appVarInput.placeholder = "app";
            }
            if (pathInput) {
                pathInput.disabled = isLocal;
                if (isLocal) pathInput.placeholder = "(Auto: Internal)";
                else pathInput.placeholder = "src/main.py";
            }
        });
    }

    const fileInput = document.getElementById('update-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
                // Need token for upload if protected
                const headers = {};
                if (state.token) {
                    headers['Authorization'] = `Bearer ${state.token}`;
                }

                const response = await fetch(`${apiBaseUrl}/update/upload`, {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    document.getElementById('update-source').value = data.path;
                    addLog(`Update file uploaded: ${data.filename}`);
                } else {
                    const err = await response.json();
                    alert("Upload failed: " + (err.detail || response.statusText));
                }
            } catch (e) {
                console.error(e);
                alert("Upload error: " + e.message);
            }
        });
    }
});

function exportData(data, filename) {
  const jsonStr = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  addLog((t('export_success') || 'Export successful') + ': ' + filename);
}

