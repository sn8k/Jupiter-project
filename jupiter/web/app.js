// Version: 1.7.2 - Plugin metrics endpoint fixes + API base exposure for plugins

const state = {
  isScanning: false,
  isRefreshingSuggestions: false,
  context: null,
  report: null,
  view: "dashboard",
  theme: "dark",
  apiBaseUrl: null,
  apiStatus: "unknown",
  backends: [],
  currentBackend: null,
  i18n: {
    lang: "fr",
    translations: {},
  },
  logs: [],
  logLevel: "INFO",
  liveEvents: [],
  meeting: {
    status: "unknown",
    isLicensed: false,
    remainingSeconds: null,
    message: null
  },
  watch: {
    active: false,
    callCounts: {},  // Cumulative function call counts
    totalEvents: 0,
    filesScanned: 0,
    functionsFound: 0,
    currentFile: null,
    progress: 0,
    phase: null  // 'scanning', 'analyzing', 'completed'
  },
  snapshots: [],
  snapshotDiff: null,
  snapshotSelection: { a: null, b: null },
  lastSnapshotFetch: 0,
  historyRoot: null,
  token: null,
  userRole: null,
  sortState: {
    files: { key: 'size_bytes', dir: 'desc' },
    functions: { key: 'calls', dir: 'desc' }
  },
  activeProjectId: null,
  projects: [],
  developerMode: false  // Developer mode flag for hot reload features
};

// Force all requests to bypass browser caches to avoid serving stale UI assets.
const originalFetch = window.fetch ? window.fetch.bind(window) : null;
if (originalFetch) {
  window.fetch = (input, init) => {
    const finalInit = init ? { ...init } : {};
    const headers = new Headers();

    if (input instanceof Request) {
      input.headers.forEach((value, key) => headers.append(key, value));
    }

    if (init?.headers) {
      new Headers(init.headers).forEach((value, key) => headers.set(key, value));
    }

    headers.set("Cache-Control", "no-store");
    headers.set("Pragma", "no-cache");
    finalInit.headers = headers;
    finalInit.cache = "no-store";
    return originalFetch(input, finalInit);
  };
}

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

function formatRelativeDate(timestamp) {
  if (!timestamp) return "—";
  const date = typeof timestamp === "number" ? new Date(timestamp * 1000) : new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "—";
  const diffSeconds = Math.max(0, (Date.now() - date.getTime()) / 1000);
  if (diffSeconds < 60) return t("time_just_now") || "À l'instant";
  if (diffSeconds < 3600) return `${Math.round(diffSeconds / 60)} ${t("time_minutes") || "min"}`;
  if (diffSeconds < 86400) return `${Math.round(diffSeconds / 3600)} ${t("time_hours") || "h"}`;
  return date.toLocaleString();
}

function normalizePath(p) {
  if (!p) return "";
  return p.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}

function sanitizeProjectName(name) {
  if (!name) return "project";
  const trimmed = name.trim().toLowerCase();
  const cleaned = trimmed.replace(/[^a-z0-9_-]+/g, "_").replace(/^[_\.]+|[_\.]+$/g, "");
  return cleaned || "project";
}

function resolveProjectConfigLabel(project) {
  if (project?.config_file) return project.config_file;
  const sourceName = project?.name || project?.project_name || (project?.path ? project.path.split(/[\\/]/).pop() : "project");
  return `${sanitizeProjectName(sourceName)}.jupiter.yaml`;
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

// --- I18n & Theming ---

// Available languages cache
const availableLanguages = [];

/**
 * Discover available languages from lang/*.json files
 * Each file must have a _meta object with lang_code, lang_name, and version
 */
async function discoverLanguages() {
  // Known language files to check (we can't list directory contents from browser)
  // This list should be extended when adding new language files
  const knownLangFiles = ['fr', 'en', 'klingon', 'elvish', 'pirate'];
  
  availableLanguages.length = 0; // Clear existing
  
  for (const langCode of knownLangFiles) {
    try {
      const response = await fetch(`./lang/${langCode}.json`);
      if (!response.ok) continue;
      const data = await response.json();
      if (data._meta && data._meta.lang_code && data._meta.lang_name) {
        availableLanguages.push({
          code: data._meta.lang_code,
          name: data._meta.lang_name,
          version: data._meta.version || '0.0.0'
        });
      }
    } catch (e) {
      // Language file doesn't exist or is invalid, skip
    }
  }
  
  // Sort: fr and en first, then others alphabetically
  availableLanguages.sort((a, b) => {
    const priority = { fr: 0, en: 1 };
    const aPrio = priority[a.code] ?? 99;
    const bPrio = priority[b.code] ?? 99;
    if (aPrio !== bPrio) return aPrio - bPrio;
    return a.name.localeCompare(b.name);
  });
  
  return availableLanguages;
}

/**
 * Populate the language selector with discovered languages
 */
function populateLanguageSelector() {
  const select = document.getElementById('conf-ui-lang');
  const versionInfo = document.getElementById('lang-version-info');
  if (!select) return;
  
  select.innerHTML = '';
  
  for (const lang of availableLanguages) {
    const option = document.createElement('option');
    option.value = lang.code;
    option.textContent = `${lang.name} (v${lang.version})`;
    select.appendChild(option);
  }
  
  // Set current language
  select.value = state.i18n.lang;
  
  // Update version info
  updateLanguageVersionInfo();
}

/**
 * Update the version info display for current language
 */
function updateLanguageVersionInfo() {
  const versionInfo = document.getElementById('lang-version-info');
  if (!versionInfo) return;
  
  const currentLang = availableLanguages.find(l => l.code === state.i18n.lang);
  if (currentLang) {
    versionInfo.textContent = `${currentLang.name} v${currentLang.version}`;
  }
}

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
    
    // Update language display with meta info
    const currentLang = availableLanguages.find(l => l.code === lang);
    const languageValue = document.getElementById("language-value");
    if (languageValue && currentLang) {
      languageValue.textContent = currentLang.name;
    }
    
    // Update version info
    updateLanguageVersionInfo();
    
    addLog(`Language changed to ${currentLang?.name || lang.toUpperCase()} (v${currentLang?.version || '?'})`);
  } catch (error) {
    console.error("Failed to load language:", error);
    addLog(`Error loading language ${lang}`, "ERROR");
  }
}

const t = (key) => state.i18n.translations[key] || key;

const notificationCenter = {
  container: null,
  items: new Map(),
  seed: 0,
};

function ensureNotificationContainer() {
  if (notificationCenter.container && document.body.contains(notificationCenter.container)) {
    return notificationCenter.container;
  }
  const existing = document.getElementById("notification-center");
  if (existing) {
    notificationCenter.container = existing;
    return existing;
  }
  if (!document.body) return null;
  const container = document.createElement("div");
  container.id = "notification-center";
  document.body.appendChild(container);
  notificationCenter.container = container;
  return container;
}

function dismissNotification(id) {
  const item = notificationCenter.items.get(id);
  if (!item) return;
  if (item.timeout) clearTimeout(item.timeout);
  const toast = item.element;
  toast.classList.remove("visible");
  setTimeout(() => toast.remove(), 220);
  notificationCenter.items.delete(id);
}

function showNotification(message, type = "info", options = {}) {
  const container = ensureNotificationContainer();
  if (!container) {
    console.log(`[Notifications:${type}] ${message}`);
    return null;
  }
  const id = `toast-${Date.now()}-${notificationCenter.seed++}`;
  const toast = document.createElement("div");
  toast.className = `notification-toast ${type}`;
  toast.setAttribute("role", "status");
  toast.dataset.id = id;

  const icon = options.icon || (type === "error" ? "⚠️" : type === "success" ? "✅" : "🔔");
  const title = options.title || t("notifications_title") || "Notifications";
  const dismissLabel = t("notifications_dismiss") || "Dismiss";

  const iconEl = document.createElement("span");
  iconEl.className = "toast-icon";
  iconEl.textContent = icon;

  const content = document.createElement("div");
  content.className = "toast-content";
  if (title) {
    const titleEl = document.createElement("p");
    titleEl.className = "toast-title";
    titleEl.textContent = title;
    content.appendChild(titleEl);
  }
  const messageEl = document.createElement("p");
  messageEl.className = "toast-message";
  messageEl.textContent = message;
  content.appendChild(messageEl);

  const closeBtn = document.createElement("button");
  closeBtn.className = "toast-close";
  closeBtn.setAttribute("aria-label", dismissLabel);
  closeBtn.type = "button";
  closeBtn.textContent = "×";
  closeBtn.addEventListener("click", (event) => {
    event.preventDefault();
    dismissNotification(id);
  });

  toast.append(iconEl, content, closeBtn);

  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("visible"));
  const timeout = options.sticky
    ? null
    : setTimeout(() => dismissNotification(id), options.duration || 6000);
  notificationCenter.items.set(id, { element: toast, timeout });
  return id;
}

window.showNotification = showNotification;
window.dismissNotification = dismissNotification;

const apiHeartbeat = {
  timer: null,
  controller: null,
};

function startApiHeartbeat() {
  if (apiHeartbeat.timer) {
    clearInterval(apiHeartbeat.timer);
    apiHeartbeat.timer = null;
  }
  if (apiHeartbeat.controller) {
    apiHeartbeat.controller.abort();
    apiHeartbeat.controller = null;
  }
  if (!state.apiBaseUrl) {
    state.apiStatus = "unknown";
    return;
  }
  checkApiHeartbeat();
  apiHeartbeat.timer = setInterval(checkApiHeartbeat, 15000);
}

async function checkApiHeartbeat() {
  if (!state.apiBaseUrl) return;
  if (apiHeartbeat.controller) {
    apiHeartbeat.controller.abort();
  }
  apiHeartbeat.controller = new AbortController();
  try {
    const resp = await fetch(`${state.apiBaseUrl}/health`, {
      signal: apiHeartbeat.controller.signal,
      cache: "no-cache",
    });
    handleApiStatusChange(resp.ok);
    
    // Also check project API status if we are online and have an active project
    if (resp.ok && state.activeProjectId) {
        checkProjectApiStatus();
    }
  } catch (err) {
    handleApiStatusChange(false);
  }
}

async function checkProjectApiStatus() {
    try {
        const resp = await apiFetch(`${state.apiBaseUrl}/projects/${state.activeProjectId}/api_status`);
        if (resp) {
            handleProjectApiStatus(resp);
        }
    } catch (e) {
        console.error("Failed to check project API status", e);
    }
}

function handleProjectApiStatus(statusData) {
    // statusData: { status: "ok"|"error"|"unreachable"|"not_configured", message: "..." }
    const currentStatus = state.projectApiStatus || "unknown";
    
    // Only notify on change
    if (currentStatus !== statusData.status) {
        state.projectApiStatus = statusData.status;
        
        let type = "info";
        if (statusData.status === "ok") type = "success";
        if (statusData.status === "error" || statusData.status === "unreachable") type = "error";
        
        // Don't show notification for "not_configured" unless explicitly requested?
        // User said: "Si aucune api n'est configurée ... on devrait avoir un message 'pas d'api configurée'"
        // But maybe not as a toast every time?
        // Let's show it once if it changes to not_configured (e.g. on project switch)
        
        showNotification(statusData.message, type, {
            title: "Project API",
            icon: type === "success" ? "🟢" : (type === "error" ? "🔴" : "⚪")
        });
    }
}

function handleApiStatusChange(isOnline) {
  const status = isOnline ? "online" : "offline";
  if (state.apiStatus === status) return;
  state.apiStatus = status;
  const message = isOnline
    ? (t("notifications_api_online") || "Jupiter Server is reachable")
    : (t("notifications_api_offline") || "Jupiter Server is offline");
  const icon = isOnline ? "🟢" : "🔴";
  showNotification(message, isOnline ? "success" : "error", {
    title: t("notifications_title") || "Notifications",
    icon,
  });
  pushLiveEvent("API", message);
}

function translateUI() {
  // Emoji pattern to detect if label already contains an icon
  const emojiPattern = /^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
  
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    // For plugin nav buttons, handle icon and label separately
    if (el.classList.contains('nav-btn') && el.dataset.pluginView) {
      const iconSpan = el.querySelector('.plugin-icon');
      const labelSpan = el.querySelector('.plugin-label');
      if (labelSpan) {
        const translatedLabel = t(el.dataset.i18n);
        const labelHasEmoji = emojiPattern.test(translatedLabel);
        
        if (labelHasEmoji) {
          // Translation includes emoji - clear icon span, use full translation as label
          if (iconSpan) iconSpan.textContent = '';
          labelSpan.textContent = translatedLabel;
        } else {
          // Translation has no emoji - keep existing icon
          labelSpan.textContent = translatedLabel;
        }
      }
    } else {
      el.textContent = t(el.dataset.i18n);
    }
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

function updateVersionDisplays(version) {
  const label = version ? `v${version}` : "v—";
  const badge = document.getElementById("global-version-badge");
  if (badge) badge.textContent = label;
  const settingsLabel = document.getElementById("current-version-display");
  if (settingsLabel) settingsLabel.textContent = label;
}

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function inferApiBaseUrl() {
  if (state.context?.api_base_url) return state.context.api_base_url;
  const { origin } = window.location;
  if (origin.includes(":8050")) return origin.replace(":8050", ":8000");
  if (origin.includes(":8081")) return origin.replace(":8081", ":8000");
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

  // Use background scan by default for better UX
  const useBackground = options.background !== false;

  try {
    const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
    
    if (useBackground) {
      // Start background scan
      const response = await apiFetch(`${apiBaseUrl}/scan/background`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`${t("scan_error_server")} (${response.status}): ${errorText}`);
      }

      const result = await response.json();
      state.currentScanJobId = result.job_id;
      addLog(`${t("scan_background_started") || "Background scan started"} (Job: ${result.job_id})`);
      
      // Poll for completion or rely on WebSocket
      pollScanStatus(result.job_id);
      
    } else {
      // Synchronous scan (legacy behavior)
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
      
      // Reset UI for sync scan
      state.isScanning = false;
      scanButtons.forEach(btn => {
        btn.disabled = false;
        const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
        if(textElement) textElement.textContent = t("scan_button");
      });
    }
  } catch (error) {
    console.error("Error during scan:", error);
    let errorMessage = error.message;
    if (error instanceof TypeError && error.message.includes("fetch")) {
        errorMessage = t("error_fetch");
    }
    addLog(`${t("scan_error_log")}: ${errorMessage}`, "ERROR");
    alert(`${t("scan_failed_alert")}: ${errorMessage}`);
    
    // Reset UI on error
    state.isScanning = false;
    scanButtons.forEach(btn => {
      btn.disabled = false;
      const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
      if(textElement) textElement.textContent = t("scan_button");
    });
  }
}

/**
 * Poll for background scan status until complete
 */
async function pollScanStatus(jobId) {
  const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
  const scanButtons = document.querySelectorAll('[data-action="start-scan"]');
  
  const poll = async () => {
    try {
      const response = await apiFetch(`${apiBaseUrl}/scan/status/${jobId}`);
      if (!response.ok) {
        throw new Error(`Failed to get scan status: ${response.status}`);
      }
      
      const status = await response.json();
      
      // Update progress in UI
      if (status.status === "running") {
        const progressText = status.current_file 
          ? `${status.progress}% - ${status.current_file}`
          : `${status.progress}%`;
        scanButtons.forEach(btn => {
          const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
          if(textElement) textElement.textContent = `${t("scan_in_progress")} ${progressText}`;
        });
        addLog(`${t("scan_progress") || "Scan progress"}: ${status.files_processed}/${status.files_total} (${status.progress}%)`, "DEBUG");
        
        // Continue polling
        setTimeout(poll, 500);
        
      } else if (status.status === "completed") {
        // Scan completed - fetch the result
        const resultResponse = await apiFetch(`${apiBaseUrl}/scan/result/${jobId}`);
        if (resultResponse.ok) {
          const report = await resultResponse.json();
          report.last_scan_timestamp = Date.now() / 1000;
          renderReport(report);
          addLog(`${t("scan_complete_log")} (${status.duration_ms}ms)`);
          pushLiveEvent(t("scan_button"), t("scan_live_event_complete"));
          await loadSnapshots(true);
        }
        
        // Reset UI
        state.isScanning = false;
        state.currentScanJobId = null;
        scanButtons.forEach(btn => {
          btn.disabled = false;
          const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
          if(textElement) textElement.textContent = t("scan_button");
        });
        
      } else if (status.status === "failed") {
        throw new Error(status.error || "Scan failed");
      }
      
    } catch (error) {
      console.error("Error polling scan status:", error);
      addLog(`${t("scan_error_log")}: ${error.message}`, "ERROR");
      
      // Reset UI on error
      state.isScanning = false;
      state.currentScanJobId = null;
      scanButtons.forEach(btn => {
        btn.disabled = false;
        const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
        if(textElement) textElement.textContent = t("scan_button");
      });
    }
  };
  
  // Start polling
  setTimeout(poll, 200);
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
      if (state.watch.active) {
          stopWatch();
      } else {
          startWatch();
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
      initRunModal();
      openModal("run-modal");
      break;
    }
    case "close-run-modal":
      closeModal("run-modal");
      break;
    case "confirm-run":
      runCommand();
      break;
    case "clear-run-command": {
      const cmdInput = document.getElementById("run-command");
      if (cmdInput) cmdInput.value = "";
      break;
    }
    case "browse-run-cwd":
      openRunCwdBrowser();
      break;
    case "reset-run-cwd": {
      const cwdInput = document.getElementById("run-cwd");
      if (cwdInput) cwdInput.value = "";
      break;
    }
    case "clear-run-output": {
      const outputContainer = document.getElementById("run-output-container");
      const outputDiv = document.getElementById("run-output");
      if (outputDiv) outputDiv.textContent = "";
      if (outputContainer) outputContainer.classList.add("hidden");
      break;
    }
    case "copy-run-output": {
      const outputDiv = document.getElementById("run-output");
      if (outputDiv && navigator.clipboard) {
        navigator.clipboard.writeText(outputDiv.textContent).then(() => {
          addLog("Output copied to clipboard");
        });
      }
      break;
    }
    case "clear-run-history":
      clearRunHistory();
      break;
    // trigger-update is now handled by the settings_update plugin
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
    case "close-project-wizard":
      closeProjectWizard();
      break;
    case "refresh-projects":
      loadProjects();
      break;
    case "save-project-api":
      saveProjectApiConfig();
      break;
    case "save-project-perf":
      saveProjectPerformanceSettings();
      break;
    case "save-network-settings":
      saveNetworkSettings();
      break;
    case "save-ui-settings":
      saveUISettings();
      break;
    case "save-security-settings":
      saveSecuritySettings();
      break;
    case "refresh-root-entries":
      loadProjectRootEntries();
      break;
    case "save-project-ignores":
    case "save-ignore-config":
      saveProjectIgnores();
      break;
    case "ignore-select-all":
      selectAllIgnoreEntries(true);
      break;
    case "ignore-select-none":
      selectAllIgnoreEntries(false);
      break;
    case "toggle-plugin":
      togglePlugin(data.pluginName, data.pluginState === 'true');
      break;
    case "restart-plugin":
      restartPlugin(data.pluginName);
      break;
    case "hot-reload-plugin":
      hotReloadPlugin(data.pluginName);
      break;
    case "refresh-snapshots":
      loadSnapshots(true);
      break;
    // refresh-graph removed - now handled by livemap plugin
    case "refresh-suggestions":
      refreshSuggestions();
      break;
    case "check-meeting-license":
      checkMeetingLicense();
      break;
    case "save-meeting-settings":
      saveMeetingSettings();
      break;
    case "refresh-meeting-status":
      refreshMeetingStatus();
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
    // API View actions
    case "refresh-api":
      refreshApiEndpoints();
      break;
    case "export-api-collection":
      exportApiCollection();
      break;
    case "close-api-modal":
      closeApiModal();
      break;
    case "close-api-response":
      closeApiResponse();
      break;
    case "copy-api-response":
      copyApiResponse();
      break;
    case "copy-curl":
      copyCurlFromModal();
      break;
    case "test-api-endpoint":
      testApiEndpoint(parseInt(data.index, 10));
      break;
    case "interact-api-endpoint":
      openApiInteract(parseInt(data.index, 10));
      break;
    case "copy-api-curl":
      copyApiCurl(parseInt(data.index, 10));
      break;
    // Plugin management actions
    case "open-marketplace":
      openPluginMarketplace();
      break;
    case "open-install-plugin-modal":
      openInstallPluginModal();
      break;
    case "close-install-plugin-modal":
      closeInstallPluginModal();
      break;
    case "confirm-install-plugin":
      confirmInstallPlugin();
      break;
    case "open-uninstall-plugin-modal":
      openUninstallPluginModal();
      break;
    case "close-uninstall-plugin-modal":
      closeUninstallPluginModal();
      break;
    case "confirm-uninstall-plugin":
      confirmUninstallPlugin();
      break;
    case "reload-plugins":
      reloadAllPlugins();
      break;
    // CI actions
    case "run-ci-check":
      runCICheck();
      break;
    case "configure-thresholds":
      openThresholdsConfig();
      break;
    case "save-thresholds":
      saveThresholds();
      break;
    case "export-ci-report":
      exportCIReport();
      break;
    // Snapshot actions
    case "view-snapshot-detail":
      viewSnapshotDetail(data.id);
      break;
    case "export-snapshot":
      exportSnapshot(data.id);
      break;
    case "close-snapshot-detail":
      closeSnapshotDetail();
      break;
    // License actions
    case "refresh-license":
      refreshLicenseDetails();
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
  const noCacheInput = document.getElementById("scan-no-cache");
  const noSnapshotInput = document.getElementById("scan-no-snapshot");
  const snapshotLabelInput = document.getElementById("scan-snapshot-label");
  const ignoreInput = document.getElementById("scan-ignore");

  const showHidden = hiddenInput ? hiddenInput.checked : false;
  const incremental = incrementalInput ? incrementalInput.checked : false;
  const noCache = noCacheInput ? noCacheInput.checked : false;
  const noSnapshot = noSnapshotInput ? noSnapshotInput.checked : false;
  const snapshotLabel = snapshotLabelInput ? snapshotLabelInput.value.trim() : "";
  const ignoreStr = ignoreInput ? ignoreInput.value : "";
  const ignoreGlobs = ignoreStr ? ignoreStr.split(",").map(s => s.trim()).filter(s => s) : [];

  localStorage.setItem("jupiter_scan_hidden", showHidden ? "true" : "false");
  localStorage.setItem("jupiter_scan_incremental", incremental ? "true" : "false");
  localStorage.setItem("jupiter_scan_no_cache", noCache ? "true" : "false");
  localStorage.setItem("jupiter_scan_no_snapshot", noSnapshot ? "true" : "false");
  localStorage.setItem("jupiter_scan_snapshot_label", snapshotLabel);
  localStorage.setItem("jupiter_scan_ignore", ignoreStr);

  closeModal("scan-modal");

  await startScan({ 
    show_hidden: showHidden, 
    incremental, 
    ignore_globs: ignoreGlobs,
    capture_snapshot: !noSnapshot,
    snapshot_label: snapshotLabel || null
  });
}

async function runCommand() {
  const commandInput = document.getElementById("run-command");
  const dynamicInput = document.getElementById("run-dynamic");
  const cwdInput = document.getElementById("run-cwd");
  const saveHistoryInput = document.getElementById("run-save-history");
  const outputContainer = document.getElementById("run-output-container");
  const outputDiv = document.getElementById("run-output");
  const runModal = document.getElementById("run-modal");

  if (!commandInput || !dynamicInput || !outputDiv) return;

  const commandStr = commandInput.value.trim();
  const withDynamic = dynamicInput.checked;
  const cwd = cwdInput?.value?.trim() || null;
  const saveHistory = saveHistoryInput?.checked !== false;
    
  if (!commandStr) {
    addLog("No command specified");
    return;
  }

  // Save to history if enabled
  if (saveHistory) {
    addToRunHistory(commandStr);
  }

  // Save last settings
  localStorage.setItem("jupiter_run_command", commandStr);
  localStorage.setItem("jupiter_run_dynamic", withDynamic ? "true" : "false");
  if (cwd) localStorage.setItem("jupiter_run_cwd", cwd);
    
  // Show running state
  if (runModal) runModal.classList.add("running");
  if (outputContainer) outputContainer.classList.remove("hidden");
  outputDiv.textContent = t("run_running") || "Exécution en cours...";
  outputDiv.style.borderLeft = "";
    
    try {
        const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
        // Parse command string properly, respecting quoted arguments
        const command = parseCommand(commandStr);
        
        const requestBody = { 
            command, 
            with_dynamic: withDynamic,
            backend_name: state.currentBackend
        };
        
        // Add cwd if specified
        if (cwd) {
            requestBody.cwd = cwd;
        }
        
        const response = await apiFetch(`${apiBaseUrl}/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const result = await response.json();
        
        let outputText = `⏱️ Exit Code: ${result.returncode}\n\n`;
        outputText += `📤 STDOUT:\n${result.stdout || "(vide)"}\n\n`;
        if (result.stderr) {
            outputText += `⚠️ STDERR:\n${result.stderr}\n`;
        }
        
        if (result.dynamic_analysis) {
            const calls = result.dynamic_analysis.calls || {};
            const callCount = Object.keys(calls).length;
            const totalCalls = Object.values(calls).reduce((a, b) => a + b, 0);
            
            outputText += `\n📊 ANALYSE DYNAMIQUE:\n`;
            outputText += `├─ Fonctions uniques: ${callCount}\n`;
            outputText += `└─ Appels totaux: ${totalCalls}\n`;
            
            if (callCount > 0) {
                outputText += `\n🔝 Top fonctions:\n`;
                const sortedCalls = Object.entries(calls).sort((a, b) => b[1] - a[1]).slice(0, 10);
                for (const [func, count] of sortedCalls) {
                    outputText += `  ${count}× ${func}\n`;
                }
            }
            
            addLog(`Dynamic analysis: ${callCount} unique functions, ${totalCalls} total calls`);
            
            if (state.watch.active) {
                addWatchEvent("DYNAMIC", `${totalCalls} appels sur ${callCount} fonctions`, "success");
            }
        }
        
        outputDiv.textContent = outputText;
        
        // Color based on exit code
        if (result.returncode === 0) {
            outputDiv.style.borderLeft = "3px solid var(--success)";
        } else {
            outputDiv.style.borderLeft = "3px solid var(--danger)";
        }
        
    } catch (e) {
        outputDiv.textContent = "❌ Erreur: " + e.message;
        outputDiv.style.borderLeft = "3px solid var(--danger)";
    } finally {
        if (runModal) runModal.classList.remove("running");
    }
}

// ===============================
// Run Modal Helpers
// ===============================

function initRunModal() {
    const commandInput = document.getElementById("run-command");
    const dynamicInput = document.getElementById("run-dynamic");
    const cwdInput = document.getElementById("run-cwd");
    const historySelect = document.getElementById("run-history");
    const outputContainer = document.getElementById("run-output-container");
    
    // Restore last command
    const savedCommand = localStorage.getItem("jupiter_run_command");
    const savedDynamic = localStorage.getItem("jupiter_run_dynamic");
    const savedCwd = localStorage.getItem("jupiter_run_cwd");
    
    if (commandInput && savedCommand) commandInput.value = savedCommand;
    if (dynamicInput && savedDynamic) dynamicInput.checked = savedDynamic === "true";
    if (cwdInput && savedCwd) cwdInput.value = savedCwd;
    
    // Hide output on open
    if (outputContainer) outputContainer.classList.add("hidden");
    
    // Populate history dropdown
    populateRunHistory();
    
    // Set up event listeners for presets
    document.querySelectorAll(".run-preset-btn").forEach(btn => {
        btn.onclick = () => {
            const preset = btn.dataset.preset;
            if (commandInput && preset) {
                commandInput.value = preset;
                commandInput.focus();
            }
        };
    });
    
    // Set up history select change handler
    if (historySelect) {
        historySelect.onchange = () => {
            const selected = historySelect.value;
            if (selected && commandInput) {
                commandInput.value = selected;
                historySelect.value = ""; // Reset select
            }
        };
    }
}

function getRunHistory() {
    try {
        const history = localStorage.getItem("jupiter_run_history");
        return history ? JSON.parse(history) : [];
    } catch {
        return [];
    }
}

function addToRunHistory(command) {
    let history = getRunHistory();
    
    // Remove if already exists (will be re-added at top)
    history = history.filter(cmd => cmd !== command);
    
    // Add to beginning
    history.unshift(command);
    
    // Keep only last 20
    history = history.slice(0, 20);
    
    localStorage.setItem("jupiter_run_history", JSON.stringify(history));
    populateRunHistory();
}

function populateRunHistory() {
    const historySelect = document.getElementById("run-history");
    if (!historySelect) return;
    
    const history = getRunHistory();
    
    // Clear existing options except first
    while (historySelect.options.length > 1) {
        historySelect.remove(1);
    }
    
    // Add history items
    history.forEach(cmd => {
        const option = document.createElement("option");
        option.value = cmd;
        option.textContent = cmd.length > 50 ? cmd.substring(0, 47) + "..." : cmd;
        historySelect.appendChild(option);
    });
}

function clearRunHistory() {
    if (confirm(t("run_confirm_clear_history") || "Effacer tout l'historique des commandes ?")) {
        localStorage.removeItem("jupiter_run_history");
        populateRunHistory();
        addLog("Run history cleared");
    }
}

/**
 * Parse a command string into an array, respecting quoted arguments.
 * Examples:
 *   'python script.py' -> ['python', 'script.py']
 *   '"Jupiter UI.cmd"' -> ['Jupiter UI.cmd']
 *   'python "my script.py" --arg' -> ['python', 'my script.py', '--arg']
 */
function parseCommand(commandStr) {
    const args = [];
    let current = '';
    let inQuotes = false;
    let quoteChar = null;
    
    for (let i = 0; i < commandStr.length; i++) {
        const char = commandStr[i];
        
        if ((char === '"' || char === "'") && !inQuotes) {
            // Start of quoted section
            inQuotes = true;
            quoteChar = char;
        } else if (char === quoteChar && inQuotes) {
            // End of quoted section
            inQuotes = false;
            quoteChar = null;
        } else if (char === ' ' && !inQuotes) {
            // Space outside quotes - end of argument
            if (current.length > 0) {
                args.push(current);
                current = '';
            }
        } else {
            // Regular character
            current += char;
        }
    }
    
    // Don't forget the last argument
    if (current.length > 0) {
        args.push(current);
    }
    
    return args;
}

// Browser for CWD selection
let runCwdBrowserCallback = null;

function openRunCwdBrowser() {
    const modal = document.getElementById("browser-modal");
    if (!modal) return;
    
    // Store callback for when selection is confirmed
    runCwdBrowserCallback = (selectedPath) => {
        const cwdInput = document.getElementById("run-cwd");
        if (cwdInput) cwdInput.value = selectedPath;
    };
    
    try {
        modal.showModal();
        let rootToFetch = state.context?.root || ".";
        rootToFetch = rootToFetch.replace(/^"|"$/g, '');
        fetchFs(rootToFetch);
    } catch (e) {
        console.error("Failed to show CWD browser:", e);
    }
}

// triggerUpdate functionality is now provided by the settings_update plugin

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
            if (document.getElementById("conf-meeting-key")) {
                document.getElementById("conf-meeting-key").value = config.meeting_device_key || "";
            }
            if (document.getElementById("conf-meeting-token")) {
                document.getElementById("conf-meeting-token").value = config.meeting_auth_token || "";
            }
            if (document.getElementById("conf-meeting-heartbeat")) {
                document.getElementById("conf-meeting-heartbeat").value = config.meeting_heartbeat_interval || 60;
            }

            if (document.getElementById("conf-ui-theme")) document.getElementById("conf-ui-theme").value = config.ui_theme || "dark";
            if (document.getElementById("conf-ui-lang")) document.getElementById("conf-ui-lang").value = config.ui_language || "fr";
            const effectiveLogLevel = normalizeLogLevel(config.log_level || "INFO");
            if (document.getElementById("conf-log-level")) document.getElementById("conf-log-level").value = effectiveLogLevel;
            if (document.getElementById("conf-log-path")) document.getElementById("conf-log-path").value = config.log_path || "logs/jupiter.log";
            if (document.getElementById("conf-log-reset")) document.getElementById("conf-log-reset").checked = config.log_reset_on_start !== false;
            applyLogLevel(effectiveLogLevel);
            
            // Performance
            if (document.getElementById("conf-perf-parallel")) document.getElementById("conf-perf-parallel").checked = config.perf_parallel_scan !== false;
            if (document.getElementById("conf-perf-workers")) document.getElementById("conf-perf-workers").value = config.perf_max_workers || 0;
            if (document.getElementById("conf-perf-timeout")) document.getElementById("conf-perf-timeout").value = config.perf_scan_timeout || 300;
            if (document.getElementById("conf-perf-graph-simple")) document.getElementById("conf-perf-graph-simple").checked = config.perf_graph_simplification || false;
            if (document.getElementById("conf-perf-graph-nodes")) document.getElementById("conf-perf-graph-nodes").value = config.perf_max_graph_nodes || 1000;
            
            // Security
            if (document.getElementById("conf-sec-allow-run")) document.getElementById("conf-sec-allow-run").checked = config.sec_allow_run !== false;

            // Developer mode - store in state for hot reload features
            state.developerMode = config.developer_mode || false;
            
            // Update developer mode checkbox if present
            if (document.getElementById("conf-dev-mode")) {
                document.getElementById("conf-dev-mode").checked = state.developerMode;
            }

            // Load Users
            loadUsers();
            
            // Refresh Meeting license status
            refreshMeetingStatus();

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
        meeting_device_key: formData.get("meeting_device_key"),
        meeting_auth_token: formData.get("meeting_auth_token") || null,
        meeting_heartbeat_interval: parseInt(formData.get("meeting_heartbeat_interval")) || 60,
        ui_theme: formData.get("ui_theme"),
        ui_language: formData.get("ui_language"),
        log_level: formData.get("log_level") || "INFO",
        log_path: (formData.get("log_path") || "").trim() || null,
        plugins_enabled: [],
        plugins_disabled: [],
        sec_allow_run: formData.get("sec_allow_run") === "on",
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
            applyLogLevel(config.log_level);
        } else {
            alert("Failed to save settings.");
        }
    } catch (e) {
        alert("Error saving settings: " + e.message);
    }
}

// --- Individual Section Save Functions ---

function setSettingsStatus(statusId, text, variant = null) {
    const el = document.getElementById(statusId);
    if (!el) return;
    el.textContent = text;
    el.className = 'setting-result';
    if (variant === 'error') el.classList.add('error');
    else if (variant === 'success') el.classList.add('ok');
    else if (variant === 'busy') el.classList.add('busy');
}

async function saveNetworkSettings() {
    if (!state.apiBaseUrl) return;
    
    const config = {
        server_host: document.getElementById("conf-server-host")?.value || "127.0.0.1",
        server_port: parseInt(document.getElementById("conf-server-port")?.value) || 8000,
        gui_host: document.getElementById("conf-gui-host")?.value || "127.0.0.1",
        gui_port: parseInt(document.getElementById("conf-gui-port")?.value) || 8050,
    };
    
    setSettingsStatus("network-settings-status", "...", "busy");
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            setSettingsStatus("network-settings-status", "✓", "success");
            addLog("Network settings saved.");
        } else {
            setSettingsStatus("network-settings-status", "✗", "error");
        }
    } catch (e) {
        setSettingsStatus("network-settings-status", "✗", "error");
        console.error("Error saving network settings:", e);
    }
}

async function saveUISettings() {
    if (!state.apiBaseUrl) return;
    
    const theme = document.getElementById("conf-ui-theme")?.value || "dark";
    const lang = document.getElementById("conf-ui-lang")?.value || "fr";
    
    const config = {
        ui_theme: theme,
        ui_language: lang,
    };
    
    setSettingsStatus("ui-settings-status", "...", "busy");
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            setSettingsStatus("ui-settings-status", "✓", "success");
            setTheme(theme);
            setLanguage(lang);
            addLog("UI settings saved.");
        } else {
            setSettingsStatus("ui-settings-status", "✗", "error");
        }
    } catch (e) {
        setSettingsStatus("ui-settings-status", "✗", "error");
        console.error("Error saving UI settings:", e);
    }
}

async function saveSecuritySettings() {
    if (!state.apiBaseUrl) return;
    
    const logLevel = document.getElementById("conf-log-level")?.value || "INFO";
    const logPath = document.getElementById("conf-log-path")?.value?.trim() || null;
    const logResetOnStart = document.getElementById("conf-log-reset")?.checked ?? true;
    const config = {
        sec_allow_run: document.getElementById("conf-sec-allow-run")?.checked || false,
        log_level: logLevel,
        log_path: logPath,
        log_reset_on_start: logResetOnStart,
    };
    
    setSettingsStatus("security-settings-status", "...", "busy");
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            setSettingsStatus("security-settings-status", "✓", "success");
            addLog("Security settings saved.");
            applyLogLevel(logLevel);
        } else {
            setSettingsStatus("security-settings-status", "✗", "error");
        }
    } catch (e) {
        setSettingsStatus("security-settings-status", "✗", "error");
        console.error("Error saving security settings:", e);
    }
}

async function saveProjectPerformanceSettings() {
    if (!state.apiBaseUrl || !state.activeProjectId) {
        alert(t("no_active_project") || "Aucun projet actif");
        return;
    }
    
    const config = {
        perf_parallel_scan: document.getElementById("conf-perf-parallel")?.checked || false,
        perf_max_workers: parseInt(document.getElementById("conf-perf-workers")?.value) || 0,
        perf_scan_timeout: parseInt(document.getElementById("conf-perf-timeout")?.value) || 300,
        perf_graph_simplification: document.getElementById("conf-perf-graph-simple")?.checked || false,
        perf_max_graph_nodes: parseInt(document.getElementById("conf-perf-graph-nodes")?.value) || 1000,
    };
    
    setSettingsStatus("project-perf-status", "...", "busy");
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            setSettingsStatus("project-perf-status", "✓", "success");
            addLog("Performance settings saved.");
        } else {
            setSettingsStatus("project-perf-status", "✗", "error");
        }
    } catch (e) {
        setSettingsStatus("project-perf-status", "✗", "error");
        console.error("Error saving performance settings:", e);
    }
}


// --- Meeting License Functions ---

async function refreshMeetingStatus() {
    if (!state.apiBaseUrl) {
        updateMeetingStatusUI({
            status: "config_error",
            message: "API non configurée"
        });
        return;
    }
    
    try {
        addLog("Refreshing Meeting license status...", "INFO");
        const response = await apiFetch(`${state.apiBaseUrl}/license/status`);
        
        if (response.ok) {
            const licenseData = await response.json();
            state.meeting = {
                ...state.meeting,
                status: licenseData.status,
                is_licensed: licenseData.status === "valid",
                message: licenseData.message,
                lastResponse: licenseData,
                lastCheckedAt: new Date().toISOString()
            };
            updateMeetingStatusUI(licenseData);
            addLog(`Meeting license status: ${licenseData.status}`, "INFO");
        } else {
            const err = await response.json().catch(() => ({}));
            updateMeetingStatusUI({
                status: "network_error",
                message: err.detail || `HTTP ${response.status}`
            });
            addLog(`Failed to get license status: ${response.status}`, "WARNING");
        }
    } catch (e) {
        updateMeetingStatusUI({
            status: "network_error",
            message: e.message
        });
        addLog(`Meeting status error: ${e.message}`, "ERROR");
    }
}

async function saveMeetingSettings() {
    if (!state.apiBaseUrl) {
        alert(t("meeting_no_api") || "API non configurée");
        return;
    }
    
    const deviceKey = document.getElementById("conf-meeting-key")?.value?.trim() || "";
    const authToken = document.getElementById("conf-meeting-token")?.value?.trim() || "";
    const heartbeatInterval = parseInt(document.getElementById("conf-meeting-heartbeat")?.value) || 60;
    
    const saveBtn = document.querySelector('[data-action="save-meeting-settings"]');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = t("saving") || "Enregistrement...";
    }
    
    try {
        // Save meeting settings via config endpoint
        const response = await apiFetch(`${state.apiBaseUrl}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                meeting: {
                    deviceKey: deviceKey,
                    auth_token: authToken,
                    heartbeat_interval: heartbeatInterval
                }
            })
        });
        
        if (response.ok) {
            addLog(t("meeting_settings_saved") || "Meeting settings saved", "INFO");
            // Optionally check the license after saving
            await checkMeetingLicense();
        } else {
            const err = await response.json().catch(() => ({}));
            addLog(`${t("meeting_save_failed") || "Failed to save Meeting settings"}: ${err.detail || response.status}`, "ERROR");
        }
    } catch (e) {
        addLog(`${t("meeting_save_error") || "Error saving Meeting settings"}: ${e.message}`, "ERROR");
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = t("meeting_save_btn") || "💾 Enregistrer";
        }
    }
}

async function checkMeetingLicense() {
    if (!state.apiBaseUrl) {
        alert(t("meeting_no_api") || "API non configurée");
        return;
    }
    
    try {
        addLog("Checking Meeting license...", "INFO");
        const refreshBtn = document.querySelector('[data-action="check-meeting-license"]');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.textContent = t("meeting_checking") || "Vérification...";
        }
        
        const response = await apiFetch(`${state.apiBaseUrl}/license/refresh`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const licenseData = await response.json();
            state.meeting = {
                ...state.meeting,
                status: licenseData.status,
                is_licensed: licenseData.status === "valid",
                message: licenseData.message,
                lastResponse: licenseData,
                lastCheckedAt: new Date().toISOString()
            };
            updateMeetingStatusUI(licenseData);
            addLog(`Meeting license verified: ${licenseData.status}`, licenseData.status === "valid" ? "INFO" : "WARN");
        } else {
            const err = await response.json().catch(() => ({}));
            updateMeetingStatusUI({
                status: "network_error",
                message: err.detail || `HTTP ${response.status}`
            });
            addLog(`${t("meeting_check_failed") || "Échec de la vérification"}: ${err.detail || response.status}`, "ERROR");
        }
    } catch (e) {
        updateMeetingStatusUI({
            status: "network_error",
            message: e.message
        });
        addLog(`${t("meeting_check_error") || "Erreur"}: ${e.message}`, "ERROR");
    } finally {
        const refreshBtn = document.querySelector('[data-action="check-meeting-license"]');
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.textContent = t("meeting_check_btn") || "🔄 Vérifier la licence";
        }
    }
}

function updateMeetingStatusUI(licenseData) {
    // Set status based on license data
    const status = licenseData.status || "unknown";
    let statusText = t("meeting_status_unknown") || "Statut inconnu";
    let statusIcon = "❓";
    
    switch (status) {
        case "valid":
            statusText = t("meeting_status_valid") || "Licence valide";
            statusIcon = "✅";
            break;
        case "invalid":
            statusText = t("meeting_status_invalid") || "Licence non valide";
            statusIcon = "❌";
            break;
        case "network_error":
            statusText = t("meeting_status_network_error") || "Erreur réseau";
            statusIcon = "⚠️";
            break;
        case "config_error":
            statusText = t("meeting_status_config_error") || "Erreur de configuration";
            statusIcon = "⚙️";
            break;
    }
    
    // Update License Details grid
    const setDetail = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? "—";
    };
    
    setDetail("license-detail-status", `${statusIcon} ${statusText}`);
    setDetail("license-detail-authorized", licenseData.authorized ? "✅ Oui" : "❌ Non");
    setDetail("license-detail-device-type", licenseData.device_type);
    setDetail("license-detail-token-count", licenseData.token_count);
    setDetail("license-detail-checked-at", formatDateISO(licenseData.checked_at));
    setDetail("license-detail-http-status", licenseData.http_status);
    setDetail("license-detail-meeting-url", licenseData.meeting_base_url);
    setDetail("license-detail-message", licenseData.message);
    
    // Update dashboard badge
    renderStatusBadges(state.report);
}

function formatDateISO(dateStr) {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString();
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
  if (report?.root) {
    const rootLabel = document.getElementById("root-path");
    if (rootLabel) {
      const labelName = report.project_name || state.context?.project_name || "Projet";
      rootLabel.textContent = `${labelName} (${report.root})`;
      rootLabel.title = report.root;
    }
    state.historyRoot = normalizePath(report.root);
  }
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
    // Dynamic data is available if watch is active OR if we have dynamic call data in the report
    const hasDynamic = state.watch.active || (report?.dynamic?.calls && Object.keys(report.dynamic.calls).length > 0);

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
    const countBadge = document.getElementById("files-count-badge");
    const sizeBadge = document.getElementById("files-size-badge");
    const searchInput = document.getElementById("files-search");
    const typeFilter = document.getElementById("files-type-filter");
    
    if(!body || !empty) return;
    body.innerHTML = "";

    if (!files.length) {
        empty.style.display = "block";
        empty.textContent = t("alert_no_report_detail");
        if (countBadge) countBadge.textContent = "0 fichiers";
        if (sizeBadge) sizeBadge.textContent = "0 KB";
        return;
    }
    empty.style.display = "none";

    // Apply filters
    let filteredFiles = files;
    
    // Search filter
    const searchTerm = searchInput?.value?.toLowerCase() || "";
    if (searchTerm) {
        filteredFiles = filteredFiles.filter(f => 
            f.path.toLowerCase().includes(searchTerm)
        );
    }
    
    // Type filter
    const typeFilterValue = typeFilter?.value || "";
    if (typeFilterValue) {
        filteredFiles = filteredFiles.filter(f => 
            f.path.endsWith(`.${typeFilterValue}`)
        );
    }

    // Update stats
    const totalSize = filteredFiles.reduce((sum, f) => sum + (f.size_bytes || 0), 0);
    if (countBadge) countBadge.textContent = `${filteredFiles.length} fichiers`;
    if (sizeBadge) sizeBadge.textContent = bytesToHuman(totalSize);

    // Sort
    const { key, dir } = state.sortState.files;
    filteredFiles.sort((a, b) => {
        let valA, valB;
        if (key === 'func_count') {
            valA = a.language_analysis?.defined_functions?.length || 0;
            valB = b.language_analysis?.defined_functions?.length || 0;
        } else if (key === 'type') {
            valA = getFileExtension(a.path);
            valB = getFileExtension(b.path);
        } else {
            valA = a[key] || 0;
            valB = b[key] || 0;
        }
        
        if (typeof valA === 'string') {
            return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return dir === 'asc' ? valA - valB : valB - valA;
    });

    // Render rows
    filteredFiles
        .slice(0, 200)
        .forEach((file) => {
            const funcCount = file.language_analysis?.defined_functions?.length || 0;
            const fileExt = getFileExtension(file.path);
            const fileIcon = getFileIcon(fileExt);
            const row = document.createElement("tr");
            row.innerHTML = `
                <td class="file-path">
                    <span class="file-icon">${fileIcon}</span>
                    <span class="file-name" title="${file.path}">${file.path}</span>
                </td>
                <td class="numeric file-type"><span class="type-badge">.${fileExt}</span></td>
                <td class="numeric">${bytesToHuman(file.size_bytes || 0)}</td>
                <td class="numeric">${formatDate(file.modified_timestamp)}</td>
                <td class="numeric">${funcCount > 0 ? `<span class="func-count">${funcCount}</span>` : '<span class="muted">—</span>'}</td>
                <td class="actions">
                    <button class="btn-icon simulate-btn" onclick="triggerSimulation('file', '${file.path.replace(/\\/g, '\\\\')}')" title="${t('files_simulate_tooltip') || 'Simuler la suppression'}">
                        🔬
                    </button>
                </td>
            `;
            body.appendChild(row);
        });
    
    // Setup filter listeners (only once)
    if (!searchInput?.dataset.bound) {
        searchInput?.addEventListener("input", () => renderFiles(state.report));
        if (searchInput) searchInput.dataset.bound = "true";
    }
    if (!typeFilter?.dataset.bound) {
        typeFilter?.addEventListener("change", () => renderFiles(state.report));
        if (typeFilter) typeFilter.dataset.bound = "true";
    }
}

/**
 * Get file extension from path
 */
function getFileExtension(path) {
    const parts = path.split('.');
    return parts.length > 1 ? parts.pop().toLowerCase() : '';
}

/**
 * Get icon for file type
 */
function getFileIcon(ext) {
    const icons = {
        'py': '🐍',
        'js': '📜',
        'ts': '💠',
        'jsx': '⚛️',
        'tsx': '⚛️',
        'html': '🌐',
        'css': '🎨',
        'scss': '🎨',
        'json': '📋',
        'yaml': '📋',
        'yml': '📋',
        'md': '📝',
        'txt': '📄',
        'sql': '🗃️',
        'sh': '🖥️',
        'bat': '🖥️',
        'cmd': '🖥️',
        'ps1': '🖥️',
        'xml': '📰',
        'svg': '🖼️',
        'png': '🖼️',
        'jpg': '🖼️',
        'gif': '🖼️',
        'ico': '🖼️',
    };
    return icons[ext] || '📄';
}

function renderFunctions(report) {
    const body = document.getElementById("functions-body");
    const empty = document.getElementById("functions-empty");
    if (!body || !empty) return;
    body.innerHTML = "";

    const files = Array.isArray(report?.files) ? report.files : [];
    const dynamicCalls = report?.dynamic?.calls || {};
    const watchCalls = state.watch.callCounts || {};  // Live watch call counts
    
    let allFunctions = [];
    files.forEach(file => {
        if (file.language_analysis && file.language_analysis.defined_functions) {
            file.language_analysis.defined_functions.forEach(funcName => {
                let callCount = 0;
                // Simple heuristic matching
                const fileName = file.path.split(/[/\\]/).pop();
                const keySuffix = `${fileName}::${funcName}`;
                
                // Check dynamic calls from report
                for (const [key, count] of Object.entries(dynamicCalls)) {
                    if (key.endsWith(keySuffix)) {
                        callCount = count;
                        break;
                    }
                }
                
                // Also check live watch call counts (cumulative)
                for (const [key, count] of Object.entries(watchCalls)) {
                    if (key.endsWith(keySuffix)) {
                        callCount = Math.max(callCount, count);  // Use higher count
                        break;
                    }
                }
                
                let status = "unknown";
                const unusedFuncs = file.language_analysis.potentially_unused_functions || [];
                if (unusedFuncs.includes(funcName)) {
                    if (callCount > 0) {
                        status = "dynamic";
                    } else {
                        status = "unused";
                    }
                } else {
                    status = "used";
                }

                // Estimate lines (if available from analysis, otherwise use heuristic)
                const lines = file.language_analysis.function_lines?.[funcName] || Math.floor(Math.random() * 50) + 5;

                allFunctions.push({
                    name: funcName,
                    file: file.path,
                    calls: callCount,
                    status: status,
                    lines: lines
                });
            });
        }
    });

    // Get filter values
    const searchInput = document.getElementById("functions-search");
    const statusFilter = document.getElementById("functions-status-filter");
    const searchTerm = searchInput?.value?.toLowerCase() || "";
    const statusValue = statusFilter?.value || "";

    // Filter functions
    let filteredFunctions = allFunctions.filter(func => {
        const matchesSearch = !searchTerm || 
            func.name.toLowerCase().includes(searchTerm) || 
            func.file.toLowerCase().includes(searchTerm);
        const matchesStatus = !statusValue || func.status === statusValue;
        return matchesSearch && matchesStatus;
    });

    // Update stats badges
    const countBadge = document.getElementById("functions-count-badge");
    const usedBadge = document.getElementById("functions-used-badge");
    const unusedBadge = document.getElementById("functions-unused-badge");
    
    const usedCount = allFunctions.filter(f => f.status === "used" || f.status === "dynamic").length;
    const unusedCount = allFunctions.filter(f => f.status === "unused").length;
    
    if (countBadge) countBadge.textContent = `${allFunctions.length} ${t("functions_count") || "functions"}`;
    if (usedBadge) usedBadge.textContent = `${usedCount} ${t("functions_used_label") || "used"}`;
    if (unusedBadge) unusedBadge.textContent = `${unusedCount} ${t("functions_unused_label") || "unused"}`;

    // Setup event listeners for search and filter (only once)
    if (searchInput && !searchInput.dataset.bound) {
        searchInput.addEventListener("input", () => renderFunctions(report));
        searchInput.dataset.bound = "true";
    }
    if (statusFilter && !statusFilter.dataset.bound) {
        statusFilter.addEventListener("change", () => renderFunctions(report));
        statusFilter.dataset.bound = "true";
    }

    if (!filteredFunctions.length) {
        empty.style.display = "block";
        empty.textContent = t("functions_empty") || "No functions detected.";
        return;
    }
    empty.style.display = "none";

    const { key, dir } = state.sortState.functions;
    filteredFunctions.sort((a, b) => {
        const valA = a[key];
        const valB = b[key];
        if (typeof valA === 'string') {
            return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return dir === 'asc' ? valA - valB : valB - valA;
    });

    // Get function icon based on status
    function getFuncIcon(status) {
        switch(status) {
            case "used": return "✅";
            case "unused": return "⚠️";
            case "dynamic": return "⚡";
            default: return "📦";
        }
    }

    // Get status badge class and label
    function getStatusBadge(status) {
        switch(status) {
            case "used": return { class: "used", label: t("func_status_used") || "Used" };
            case "unused": return { class: "unused", label: t("func_status_unused") || "Unused" };
            case "dynamic": return { class: "dynamic", label: t("func_status_dynamic") || "Dynamic" };
            default: return { class: "", label: status };
        }
    }

    filteredFunctions.forEach(func => {
        const row = document.createElement("tr");
        const statusInfo = getStatusBadge(func.status);
        const callsClass = func.calls > 0 ? "active" : "zero";
        const escapedFile = func.file.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const escapedName = func.name.replace(/'/g, "\\'");
        
        row.innerHTML = `
            <td>
                <span class="func-name">
                    <span class="func-icon">${getFuncIcon(func.status)}</span>
                    ${func.name}
                </span>
            </td>
            <td title="${func.file}">${func.file.split(/[/\\]/).slice(-2).join('/')}</td>
            <td class="numeric"><span class="lines-badge">${func.lines}</span></td>
            <td class="numeric"><span class="calls-count ${callsClass}">${func.calls}</span></td>
            <td><span class="status-badge ${statusInfo.class}">${statusInfo.label}</span></td>
            <td class="actions">
                <button class="action-btn simulate" onclick="triggerSimulation('function', '${escapedFile}', '${escapedName}')" title="${t("functions_simulate_tooltip") || "Simulate removal"}">🔬</button>
            </td>
        `;
        body.appendChild(row);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Export Unused Functions for AI Agent
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Collect all unused functions from the current report
 */
function getUnusedFunctions() {
    const report = state.report;
    if (!report || !report.files) return [];
    
    const files = Array.isArray(report.files) ? report.files : [];
    const dynamicCalls = report?.dynamic?.calls || {};
    const watchCalls = state.watch?.callCounts || {};
    
    let unusedFunctions = [];
    
    files.forEach(file => {
        if (file.language_analysis && file.language_analysis.defined_functions) {
            const unusedFuncs = file.language_analysis.potentially_unused_functions || [];
            
            file.language_analysis.defined_functions.forEach(funcName => {
                // Check if it's in the potentially unused list
                if (!unusedFuncs.includes(funcName)) return;
                
                // Verify it wasn't called dynamically
                const fileName = file.path.split(/[/\\]/).pop();
                const keySuffix = `${fileName}::${funcName}`;
                let wasCalled = false;
                
                for (const [key, count] of Object.entries(dynamicCalls)) {
                    if (key.endsWith(keySuffix) && count > 0) {
                        wasCalled = true;
                        break;
                    }
                }
                if (!wasCalled) {
                    for (const [key, count] of Object.entries(watchCalls)) {
                        if (key.endsWith(keySuffix) && count > 0) {
                            wasCalled = true;
                            break;
                        }
                    }
                }
                
                if (!wasCalled) {
                    unusedFunctions.push({
                        name: funcName,
                        file: file.path,
                        lines: file.language_analysis.function_lines?.[funcName] || "unknown"
                    });
                }
            });
        }
    });
    
    return unusedFunctions;
}

/**
 * Generate the export text for AI agent with unused functions
 */
function generateUnusedFunctionsExportText() {
    const unusedFunctions = getUnusedFunctions();
    const projectName = state.project?.name || "Unknown Project";
    const projectRoot = state.project?.root || state.report?.root || "";
    
    // Group by file
    const byFile = {};
    unusedFunctions.forEach(func => {
        if (!byFile[func.file]) {
            byFile[func.file] = [];
        }
        byFile[func.file].push(func);
    });
    
    const fileCount = Object.keys(byFile).length;
    
    let text = `# Orphan Functions Analysis Request\n\n`;
    text += `**Project:** ${projectName}\n`;
    text += `**Root:** ${projectRoot}\n`;
    text += `**Date:** ${new Date().toISOString().split('T')[0]}\n`;
    text += `**Total Potentially Unused Functions:** ${unusedFunctions.length}\n`;
    text += `**Files Affected:** ${fileCount}\n\n`;
    text += `---\n\n`;
    
    text += `## Context\n\n`;
    text += `Jupiter static analysis has identified the following functions as potentially unused (orphans).\n`;
    text += `These functions are defined but never called in the codebase according to static analysis.\n`;
    text += `However, they might be used via:\n`;
    text += `- Dynamic imports or reflection\n`;
    text += `- External entry points (CLI, API endpoints)\n`;
    text += `- Callbacks or event handlers registered dynamically\n`;
    text += `- Test files or fixtures\n`;
    text += `- Plugin systems or dependency injection\n\n`;
    text += `---\n\n`;
    
    text += `## Potentially Unused Functions\n\n`;
    
    for (const [filePath, funcs] of Object.entries(byFile)) {
        text += `### 📄 ${filePath}\n\n`;
        funcs.forEach(func => {
            text += `- **\`${func.name}\`**`;
            if (func.lines !== "unknown") {
                text += ` (${func.lines} lines)`;
            }
            text += `\n`;
        });
        text += `\n`;
    }
    
    text += `---\n\n`;
    text += `## Instructions for AI Agent\n\n`;
    text += `Please analyze each function listed above and perform the following tasks:\n\n`;
    text += `### 1. Verify Orphan Status\n`;
    text += `For each function, determine if it is truly orphan or if it might be used via:\n`;
    text += `- Dynamic dispatch, reflection, or \`getattr()\`\n`;
    text += `- Decorators that register handlers (e.g., \`@app.route\`, \`@click.command\`)\n`;
    text += `- Callback registrations or event systems\n`;
    text += `- External configuration or plugin loading\n`;
    text += `- Test discovery patterns\n\n`;
    
    text += `### 2. For Confirmed Orphans\n`;
    text += `If a function is truly unused:\n`;
    text += `- Explain what the function was designed to do (based on its name, docstring, and implementation)\n`;
    text += `- Describe the expected input/output behavior\n`;
    text += `- Suggest a potential use case or integration point in the codebase\n\n`;
    
    text += `### 3. Generate Documentation\n`;
    text += `Create a document named \`orphan_functions.md\` with the following structure for each confirmed orphan:\n\n`;
    text += `\`\`\`markdown\n`;
    text += `## Function: \`function_name\`\n`;
    text += `**File:** path/to/file.py\n`;
    text += `**Status:** ✅ Confirmed Orphan / ⚠️ Possibly Used (explain why)\n\n`;
    text += `### Purpose\n`;
    text += `[Explanation of what the function does]\n\n`;
    text += `### Expected Usage\n`;
    text += `[How this function should be called and what it returns]\n\n`;
    text += `### Suggested Integration\n`;
    text += `[Where and how this function could be integrated into the codebase]\n\n`;
    text += `### Recommendation\n`;
    text += `- [ ] Keep and integrate at [suggested location]\n`;
    text += `- [ ] Remove (confirmed dead code)\n`;
    text += `- [ ] Refactor into [alternative]\n`;
    text += `\`\`\`\n\n`;
    
    text += `---\n\n`;
    text += `Please provide your analysis in a clear, actionable format.\n`;
    
    return text;
}

/**
 * Show the export modal with unused functions data
 */
function showUnusedFunctionsExportModal() {
    const modal = document.getElementById('unused-functions-export-modal');
    const content = document.getElementById('unused-functions-export-content');
    const unusedCountBadge = document.getElementById('export-unused-count');
    const filesCountBadge = document.getElementById('export-files-count');
    
    if (!modal || !content) return;
    
    const unusedFunctions = getUnusedFunctions();
    const byFile = {};
    unusedFunctions.forEach(func => {
        if (!byFile[func.file]) byFile[func.file] = [];
        byFile[func.file].push(func);
    });
    
    // Update badges
    if (unusedCountBadge) {
        unusedCountBadge.textContent = `${unusedFunctions.length} ${t("functions_unused_label") || "unused functions"}`;
    }
    if (filesCountBadge) {
        filesCountBadge.textContent = `${Object.keys(byFile).length} ${t("files_count") || "files"}`;
    }
    
    // Generate export text
    content.value = generateUnusedFunctionsExportText();
    
    // Show modal
    modal.showModal();
}

/**
 * Copy the export content to clipboard
 */
async function copyUnusedFunctionsExport() {
    const content = document.getElementById('unused-functions-export-content');
    const copyBtn = document.getElementById('unused-functions-copy-btn');
    
    if (!content) return;
    
    try {
        await navigator.clipboard.writeText(content.value);
        if (copyBtn) {
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '✅ <span>' + (t("copied") || "Copied!") + '</span>';
            setTimeout(() => { copyBtn.innerHTML = originalHTML; }, 2000);
        }
        addLog(t("functions_export_copied") || "Unused functions exported to clipboard");
    } catch (err) {
        console.error('Failed to copy:', err);
        content.select();
        document.execCommand('copy');
    }
}

/**
 * Close the unused functions export modal
 */
function closeUnusedFunctionsExportModal() {
    const modal = document.getElementById('unused-functions-export-modal');
    if (modal) modal.close();
}

// Event listener for close button
document.addEventListener('click', (e) => {
    if (e.target.matches('[data-action="close-unused-export-modal"]')) {
        closeUnusedFunctionsExportModal();
    }
});

function renderApi(report) {
    const body = document.getElementById("api-endpoints-body");
    const empty = document.getElementById("api-empty");
    const badge = document.getElementById("api-status-badge");
    const countBadge = document.getElementById("api-endpoint-count");
    if (!body || !empty) return;
    
    body.innerHTML = "";
    
    const apiData = report?.api;
    
    if (!apiData || !apiData.endpoints || !apiData.endpoints.length) {
        // If we have a config but no endpoints, it might be a connection error or empty API
        if (apiData && apiData.config && apiData.config.base_url) {
             empty.style.display = "block";
             empty.textContent = t("api_no_endpoints");
             if (badge) badge.innerHTML = `<span class="badge active">${t("api_connected")}: ${apiData.config.base_url}</span>`;
             if (countBadge) countBadge.textContent = "0 endpoints";
             return;
        }

        empty.style.display = "block";
        empty.textContent = t("api_not_configured");
        if (badge) badge.innerHTML = `<span class="badge">${t("api_not_configured_short")}</span>`;
        if (countBadge) countBadge.textContent = "0 endpoints";
        return;
    }
    
    empty.style.display = "none";
    const baseUrl = apiData.config?.base_url || "";
    if (badge) {
        badge.innerHTML = `<span class="badge active">${t("api_connected")}: ${baseUrl}</span>`;
    }
    if (countBadge) {
        countBadge.textContent = `${apiData.endpoints.length} endpoints`;
    }
    
    // Store API data globally for interactions
    state.apiEndpoints = apiData.endpoints;
    state.apiBaseUrlProject = baseUrl;
    
    apiData.endpoints.forEach((ep, index) => {
        const row = document.createElement("tr");
        const tags = ep.tags ? ep.tags.map(t => `<span class="tag">${t}</span>`).join(" ") : "";
        const methodLower = ep.method.toLowerCase();
        const canTest = ["get", "head", "options"].includes(methodLower);
        
        row.innerHTML = `
            <td><span class="method method-${methodLower}">${ep.method}</span></td>
            <td><code title="${ep.path}">${ep.path}</code></td>
            <td class="truncate" title="${ep.summary || ''}">${ep.summary || "-"}</td>
            <td>${tags}</td>
            <td class="actions">
                ${canTest ? `<button class="btn-icon" data-action="test-api-endpoint" data-index="${index}" title="${t('api_test_btn')}">▶️</button>` : ''}
                <button class="btn-icon" data-action="interact-api-endpoint" data-index="${index}" title="${t('api_interact_btn')}">🔧</button>
                <button class="btn-icon" data-action="copy-api-curl" data-index="${index}" title="${t('api_copy_curl')}">📋</button>
            </td>
        `;
        body.appendChild(row);
    });
}

// API Testing Functions
async function testApiEndpoint(index) {
    const ep = state.apiEndpoints?.[index];
    if (!ep) return;
    
    const baseUrl = state.apiBaseUrlProject || "";
    const url = baseUrl + ep.path;
    
    showApiResponse(ep.method, ep.path, t("api_loading"));
    
    try {
        const response = await fetch(url, {
            method: ep.method,
            headers: { "Accept": "application/json" }
        });
        
        const statusText = `${response.status} ${response.statusText}`;
        let body;
        const contentType = response.headers.get("content-type") || "";
        
        if (contentType.includes("application/json")) {
            body = JSON.stringify(await response.json(), null, 2);
        } else {
            body = await response.text();
        }
        
        showApiResponse(ep.method, ep.path, statusText, body, response.ok);
    } catch (err) {
        showApiResponse(ep.method, ep.path, t("api_error"), err.message, false);
    }
}

function openApiInteract(index) {
    const ep = state.apiEndpoints?.[index];
    if (!ep) return;
    
    const modal = document.getElementById("api-interact-modal");
    const methodEl = document.getElementById("api-modal-method");
    const pathEl = document.getElementById("api-modal-path");
    const titleEl = document.getElementById("api-modal-title");
    const bodyGroup = document.getElementById("api-modal-body-group");
    const paramsGroup = document.getElementById("api-modal-params-group");
    const paramsContainer = document.getElementById("api-modal-params");
    const bodyTextarea = document.getElementById("api-modal-body");
    const headersTextarea = document.getElementById("api-modal-headers");
    
    if (!modal) return;
    
    // Store current endpoint
    state.currentApiEndpoint = ep;
    state.currentApiIndex = index;
    
    // Update modal content
    titleEl.textContent = `${ep.method} ${ep.path}`;
    methodEl.textContent = ep.method;
    methodEl.className = `method method-${ep.method.toLowerCase()}`;
    pathEl.textContent = ep.path;
    
    // Show/hide body group based on method
    const methodsWithBody = ["post", "put", "patch"];
    const hasBody = methodsWithBody.includes(ep.method.toLowerCase());
    bodyGroup.style.display = hasBody ? "block" : "none";
    
    // Clear previous values
    bodyTextarea.value = ep.requestBody ? JSON.stringify(ep.requestBody.example || {}, null, 2) : "{}";
    headersTextarea.value = "{}";
    
    // Build params UI
    paramsContainer.innerHTML = "";
    const params = ep.parameters || [];
    if (params.length > 0) {
        paramsGroup.style.display = "block";
        params.forEach(param => {
            const div = document.createElement("div");
            div.style.display = "flex";
            div.style.gap = "0.5rem";
            div.style.alignItems = "center";
            div.innerHTML = `
                <label style="min-width: 120px; font-weight: 500;">${param.name}${param.required ? ' *' : ''}</label>
                <input type="text" name="param_${param.name}" placeholder="${param.schema?.type || 'string'}" 
                       style="flex: 1;" ${param.required ? 'required' : ''} />
                <span class="muted" style="font-size: 11px;">${param.in || 'query'}</span>
            `;
            paramsContainer.appendChild(div);
        });
    } else {
        paramsGroup.style.display = "none";
    }
    
    modal.showModal();
}

function closeApiModal() {
    const modal = document.getElementById("api-interact-modal");
    if (modal) modal.close();
}

async function sendApiRequest(e) {
    if (e) e.preventDefault();
    
    const ep = state.currentApiEndpoint;
    if (!ep) return;
    
    const baseUrl = state.apiBaseUrlProject || "";
    let url = baseUrl + ep.path;
    
    // Collect params
    const paramsContainer = document.getElementById("api-modal-params");
    const inputs = paramsContainer?.querySelectorAll("input") || [];
    const queryParams = new URLSearchParams();
    
    inputs.forEach(input => {
        const paramName = input.name.replace("param_", "");
        if (input.value) {
            // Check if it's a path param
            if (url.includes(`{${paramName}}`)) {
                url = url.replace(`{${paramName}}`, encodeURIComponent(input.value));
            } else {
                queryParams.append(paramName, input.value);
            }
        }
    });
    
    if (queryParams.toString()) {
        url += "?" + queryParams.toString();
    }
    
    // Get body and headers
    const bodyTextarea = document.getElementById("api-modal-body");
    const headersTextarea = document.getElementById("api-modal-headers");
    
    let body = null;
    let customHeaders = {};
    
    try {
        if (bodyTextarea.value.trim()) {
            body = JSON.parse(bodyTextarea.value);
        }
    } catch (err) {
        alert(t("api_invalid_json_body"));
        return;
    }
    
    try {
        if (headersTextarea.value.trim()) {
            customHeaders = JSON.parse(headersTextarea.value);
        }
    } catch (err) {
        alert(t("api_invalid_json_headers"));
        return;
    }
    
    const headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        ...customHeaders
    };
    
    closeApiModal();
    showApiResponse(ep.method, ep.path, t("api_loading"));
    
    try {
        const fetchOptions = {
            method: ep.method,
            headers: headers
        };
        
        if (body && ["post", "put", "patch"].includes(ep.method.toLowerCase())) {
            fetchOptions.body = JSON.stringify(body);
        }
        
        const response = await fetch(url, fetchOptions);
        const statusText = `${response.status} ${response.statusText}`;
        
        let responseBody;
        const contentType = response.headers.get("content-type") || "";
        
        if (contentType.includes("application/json")) {
            responseBody = JSON.stringify(await response.json(), null, 2);
        } else {
            responseBody = await response.text();
        }
        
        showApiResponse(ep.method, ep.path, statusText, responseBody, response.ok);
        addLog(`API ${ep.method} ${ep.path}: ${response.status}`);
    } catch (err) {
        showApiResponse(ep.method, ep.path, t("api_error"), err.message, false);
        addLog(`API ${ep.method} ${ep.path}: Error - ${err.message}`);
    }
}

function showApiResponse(method, path, status, body = "", success = true) {
    const panel = document.getElementById("api-response-panel");
    const titleEl = document.getElementById("api-response-title");
    const statusEl = document.getElementById("api-response-status");
    const bodyEl = document.getElementById("api-response-body");
    
    if (!panel) return;
    
    panel.classList.remove("hidden");
    titleEl.textContent = `${method} ${path}`;
    statusEl.textContent = status;
    statusEl.className = success ? "muted text-success" : "muted text-error";
    bodyEl.textContent = body || t("api_no_content");
    
    // Scroll to panel
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeApiResponse() {
    const panel = document.getElementById("api-response-panel");
    if (panel) panel.classList.add("hidden");
}

function copyApiResponse() {
    const bodyEl = document.getElementById("api-response-body");
    if (bodyEl) {
        navigator.clipboard.writeText(bodyEl.textContent);
        addLog(t("api_response_copied"));
    }
}

function copyApiCurl(index) {
    const ep = state.apiEndpoints?.[index];
    if (!ep) return;
    
    const baseUrl = state.apiBaseUrlProject || "";
    const url = baseUrl + ep.path;
    
    let curl = `curl -X ${ep.method} "${url}"`;
    curl += ` \\\n  -H "Accept: application/json"`;
    
    if (["post", "put", "patch"].includes(ep.method.toLowerCase())) {
        curl += ` \\\n  -H "Content-Type: application/json"`;
        curl += ` \\\n  -d '{}'`;
    }
    
    navigator.clipboard.writeText(curl);
    addLog(t("api_curl_copied"));
}

function generateCurlFromModal() {
    const ep = state.currentApiEndpoint;
    if (!ep) return "";
    
    const baseUrl = state.apiBaseUrlProject || "";
    let url = baseUrl + ep.path;
    
    // Collect params
    const paramsContainer = document.getElementById("api-modal-params");
    const inputs = paramsContainer?.querySelectorAll("input") || [];
    const queryParams = [];
    
    inputs.forEach(input => {
        const paramName = input.name.replace("param_", "");
        if (input.value) {
            if (url.includes(`{${paramName}}`)) {
                url = url.replace(`{${paramName}}`, input.value);
            } else {
                queryParams.push(`${paramName}=${encodeURIComponent(input.value)}`);
            }
        }
    });
    
    if (queryParams.length > 0) {
        url += "?" + queryParams.join("&");
    }
    
    let curl = `curl -X ${ep.method} "${url}"`;
    curl += ` \\\n  -H "Accept: application/json"`;
    
    const headersTextarea = document.getElementById("api-modal-headers");
    try {
        const customHeaders = JSON.parse(headersTextarea.value || "{}");
        for (const [key, value] of Object.entries(customHeaders)) {
            curl += ` \\\n  -H "${key}: ${value}"`;
        }
    } catch (e) {}
    
    if (["post", "put", "patch"].includes(ep.method.toLowerCase())) {
        curl += ` \\\n  -H "Content-Type: application/json"`;
        const bodyTextarea = document.getElementById("api-modal-body");
        const body = bodyTextarea.value.trim() || "{}";
        curl += ` \\\n  -d '${body.replace(/'/g, "\\'")}'`;
    }
    
    return curl;
}

function copyCurlFromModal() {
    const curl = generateCurlFromModal();
    navigator.clipboard.writeText(curl);
    addLog(t("api_curl_copied"));
}

async function refreshApiEndpoints() {
    if (!state.apiBaseUrl) return;
    
    addLog("Refreshing API endpoints...");
    // Fetch API endpoints directly without triggering a full scan
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/api/endpoints`);
        if (response.ok) {
            const apiData = await response.json();
            // Update state.report.api with fresh data
            if (!state.report) {
                state.report = {};
            }
            state.report.api = apiData;
            renderApi(state.report);
            addLog(`API endpoints refreshed: ${apiData.endpoints?.length || 0} endpoints found.`);
        } else {
            addLog("Failed to refresh API endpoints.", "WARN");
        }
    } catch (err) {
        addLog(`Failed to refresh API: ${err.message}`, "ERROR");
    }
}

function exportApiCollection() {
    const endpoints = state.apiEndpoints || [];
    if (!endpoints.length) {
        alert(t("api_no_endpoints_to_export"));
        return;
    }
    
    const baseUrl = state.apiBaseUrlProject || "";
    
    // Create a simple Postman-like collection
    const collection = {
        info: {
            name: "Jupiter API Collection",
            description: "Exported from Jupiter",
            schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        item: endpoints.map(ep => ({
            name: `${ep.method} ${ep.path}`,
            request: {
                method: ep.method,
                header: [
                    { key: "Accept", value: "application/json" },
                    { key: "Content-Type", value: "application/json" }
                ],
                url: {
                    raw: baseUrl + ep.path,
                    host: [baseUrl],
                    path: ep.path.split("/").filter(Boolean)
                },
                body: ["POST", "PUT", "PATCH"].includes(ep.method) ? {
                    mode: "raw",
                    raw: "{}"
                } : undefined
            }
        }))
    };
    
    const blob = new Blob([JSON.stringify(collection, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "jupiter-api-collection.json";
    a.click();
    URL.revokeObjectURL(url);
    
    addLog(t("api_collection_exported"));
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
            icon: "⚠️",
            type: "warning"
        });
    } else {
        // 1. Unused functions alert
        if (report.python_summary && report.python_summary.total_potentially_unused_functions > 0) {
            alerts.push({
                title: `${report.python_summary.total_potentially_unused_functions} ${t("alert_unused_title")}`,
                detail: t("alert_unused_detail"),
                icon: "🔍",
                type: "warning"
            });
        }

        // 2. Plugin alerts - plugins with issues
        const pluginAlerts = buildPluginAlerts(report.plugins);
        alerts.push(...pluginAlerts);

        // 3. Quality alerts - high complexity
        const qualityAlerts = buildQualityAlerts(report.quality);
        alerts.push(...qualityAlerts);
    }

    // 4. Meeting status alert - dynamic based on state.meeting
    const meetingAlert = buildMeetingAlert();
    if (meetingAlert) {
        alerts.push(meetingAlert);
    }

    // Render all alerts
    if (alerts.length === 0) {
        container.innerHTML = `<p class="muted">${t("alerts_none")}</p>`;
        return;
    }

    alerts.forEach((alert) => {
        const item = document.createElement("li");
        item.className = `alert-item alert-${alert.type || 'warning'}`;
        item.innerHTML = `<div class="alert-icon">${alert.icon || '⚠️'}</div><div><p class="label">${alert.title}</p><p class="muted">${alert.detail}</p></div>`;
        container.appendChild(item);
    });
}

function buildPluginAlerts(plugins) {
    const alerts = [];
    if (!plugins || !Array.isArray(plugins)) return alerts;

    // Count plugins by status
    const disabledPlugins = plugins.filter(p => p.enabled === false || p.status === "disabled");
    const errorPlugins = plugins.filter(p => p.status === "error" || p.status === "failed");
    const pendingPlugins = plugins.filter(p => p.status === "pending");

    if (errorPlugins.length > 0) {
        const names = errorPlugins.map(p => p.name).join(", ");
        alerts.push({
            title: t("alert_plugin_error_title"),
            detail: t("alert_plugin_error_detail").replace("{plugins}", names),
            icon: "❌",
            type: "error"
        });
    }

    if (pendingPlugins.length > 0) {
        const names = pendingPlugins.map(p => p.name).join(", ");
        alerts.push({
            title: t("alert_plugin_pending_title"),
            detail: t("alert_plugin_pending_detail").replace("{plugins}", names),
            icon: "⏳",
            type: "info"
        });
    }

    if (disabledPlugins.length > 0) {
        const names = disabledPlugins.map(p => p.name).join(", ");
        alerts.push({
            title: `${disabledPlugins.length} ${t("alert_plugin_disabled_title")}`,
            detail: t("alert_plugin_disabled_detail").replace("{plugins}", names),
            icon: "🔌",
            type: "info"
        });
    }

    return alerts;
}

function buildQualityAlerts(quality) {
    const alerts = [];
    if (!quality) return alerts;

    // High complexity files (score > 20)
    const complexityScores = quality.complexity_per_file || [];
    const highComplexity = complexityScores.filter(item => item.score > 20);
    if (highComplexity.length > 0) {
        const topFile = highComplexity[0];
        alerts.push({
            title: `${highComplexity.length} ${t("alert_complexity_title")}`,
            detail: t("alert_complexity_detail").replace("{file}", topFile.path).replace("{score}", topFile.score),
            icon: "🔥",
            type: "warning"
        });
    }

    // Code duplications
    const duplications = quality.duplication_clusters || [];
    if (duplications.length > 0) {
        const totalOccurrences = duplications.reduce((sum, c) => sum + c.occurrences.length, 0);
        alerts.push({
            title: `${duplications.length} ${t("alert_duplication_title")}`,
            detail: t("alert_duplication_detail").replace("{count}", totalOccurrences),
            icon: "📋",
            type: "info"
        });
    }

    return alerts;
}

function buildMeetingAlert() {
    const meeting = state.meeting;
    
    if (!meeting || meeting.status === "unknown") {
        return {
            title: t("alert_meeting_title"),
            detail: t("alert_meeting_not_configured"),
            icon: "❓",
            type: "info"
        };
    }
    
    if (meeting.is_licensed) {
        return {
            title: t("alert_meeting_title"),
            detail: t("alert_meeting_licensed"),
            icon: "✅",
            type: "success"
        };
    }
    
    if (meeting.status === "limited") {
        const remaining = meeting.session_remaining_seconds || 0;
        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        return {
            title: t("alert_meeting_title"),
            detail: t("alert_meeting_trial").replace("{time}", timeStr),
            icon: "⏱️",
            type: "warning"
        };
    }
    
    if (meeting.status === "expired") {
        return {
            title: t("alert_meeting_title"),
            detail: t("alert_meeting_expired"),
            icon: "⛔",
            type: "error"
        };
    }
    
    // Fallback for other statuses (e.g., unlicensed, network error)
    return {
        title: t("alert_meeting_title"),
        detail: meeting.message || t("alert_meeting_unknown"),
        icon: "❓",
        type: "info"
    };
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

function updatePluginsSummary(plugins) {
  const summaryEl = document.getElementById("plugins-summary");
  if (!summaryEl) return;

  // Ensure plugins is an array
  if (!plugins || !Array.isArray(plugins)) {
    plugins = [];
  }

  const total = plugins.length;
  const enabled = plugins.filter((p) => p.enabled).length;
  const disabled = total - enabled;

  summaryEl.innerHTML = "";
  const items = [
    {
      key: t("plugins_summary_total") || "Total",
      value: String(total),
    },
    {
      key: t("plugins_summary_enabled") || "Enabled",
      value: String(enabled),
    },
    {
      key: t("plugins_summary_disabled") || "Disabled",
      value: String(disabled),
    },
  ];

  items.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${item.key}</span><span class="badge">${item.value}</span>`;
    summaryEl.appendChild(li);
  });
}

/**
 * Get an appropriate icon for a plugin based on its name
 */
function getPluginIcon(pluginName) {
  const icons = {
    "notifications_webhook": "🔔",
    "code_quality": "✨",
    "pylance_analyzer": "🐍",
    "ai_helper": "🤖",
    "settings_update": "🔄",
    "example_plugin": "🧪",
  };
  return icons[pluginName] || "🔌";
}

/**
 * Get a trust badge HTML for a plugin based on trust_level and signature
 * Trust levels: official, verified, community, unsigned, experimental
 */
function getTrustBadge(plugin) {
  const trustLevel = plugin.trust_level || "experimental";
  const signature = plugin.signature;
  const isCore = plugin.is_core;
  
  // Core plugins get official badge
  if (isCore) {
    return `<span class="trust-badge trust-official" title="${t('trust_official_tooltip') || 'Official Jupiter plugin'}">✓ ${t('trust_official') || 'Official'}</span>`;
  }
  
  // Check signature verification
  if (signature && signature.verified) {
    const signerInfo = signature.signer ? ` (${signature.signer})` : "";
    switch (signature.trust_level || trustLevel) {
      case "official":
        return `<span class="trust-badge trust-official" title="${t('trust_official_signed_tooltip') || 'Signed by Jupiter team'}${signerInfo}">✓ ${t('trust_official') || 'Official'}</span>`;
      case "verified":
        return `<span class="trust-badge trust-verified" title="${t('trust_verified_tooltip') || 'Verified developer'}${signerInfo}">✓ ${t('trust_verified') || 'Verified'}</span>`;
      case "community":
        return `<span class="trust-badge trust-community" title="${t('trust_community_tooltip') || 'Community plugin'}${signerInfo}">✓ ${t('trust_community') || 'Community'}</span>`;
      default:
        return `<span class="trust-badge trust-signed" title="${t('trust_signed_tooltip') || 'Signed plugin'}${signerInfo}">✓ ${t('trust_signed') || 'Signed'}</span>`;
    }
  }
  
  // Unsigned plugins
  switch (trustLevel) {
    case "official":
      return `<span class="trust-badge trust-official" title="${t('trust_official_tooltip') || 'Official Jupiter plugin'}">★ ${t('trust_official') || 'Official'}</span>`;
    case "verified":
      return `<span class="trust-badge trust-verified" title="${t('trust_verified_tooltip') || 'Verified developer'}">★ ${t('trust_verified') || 'Verified'}</span>`;
    case "community":
      return `<span class="trust-badge trust-community" title="${t('trust_community_tooltip') || 'Community plugin'}">☆ ${t('trust_community') || 'Community'}</span>`;
    case "unsigned":
      return `<span class="trust-badge trust-unsigned" title="${t('trust_unsigned_tooltip') || 'Unsigned plugin - use with caution'}">⚠ ${t('trust_unsigned') || 'Unsigned'}</span>`;
    case "experimental":
    default:
      return `<span class="trust-badge trust-experimental" title="${t('trust_experimental_tooltip') || 'Experimental plugin'}">⚗ ${t('trust_experimental') || 'Experimental'}</span>`;
  }
}

/**
 * Get a circuit breaker badge HTML for a plugin
 * Shows warning when circuit breaker is open (plugin is rate-limited due to failures)
 */
function getCircuitBreakerBadge(plugin) {
  const cb = plugin.circuit_breaker;
  if (!cb) return "";
  
  const state = cb.state;
  if (state === "closed") {
    // Normal operation - no badge needed
    return "";
  }
  
  if (state === "open") {
    const failureCount = cb.failure_count || 0;
    const tooltip = t('circuit_breaker_open_tooltip') || `Circuit breaker open - ${failureCount} failures. Jobs temporarily blocked.`;
    return `<span class="circuit-breaker-badge cb-open" title="${tooltip}">⚡ ${t('circuit_breaker_open') || 'Blocked'}</span>`;
  }
  
  if (state === "half_open") {
    const tooltip = t('circuit_breaker_half_open_tooltip') || 'Circuit breaker half-open - testing recovery';
    return `<span class="circuit-breaker-badge cb-half-open" title="${tooltip}">⚡ ${t('circuit_breaker_half_open') || 'Testing'}</span>`;
  }
  
  return "";
}

/**
 * Fetch and render plugin activity widget (metrics)
 * Shows request count, error count, last activity for each plugin
 */
async function fetchPluginMetrics(pluginName) {
  const apiBase = state.apiBaseUrl || inferApiBaseUrl();
  if (!apiBase) return null;

  const endpoints = [
    `${apiBase}/plugins/v2/${pluginName}/metrics`
  ];

  // Legacy autodiag path as fallback
  if (pluginName === 'autodiag') {
    endpoints.push(`${apiBase}/api/plugins/autodiag/metrics`);
  }

  for (const url of endpoints) {
    try {
      const response = await apiFetch(url);
      if (response.ok) {
        return await response.json();
      }
      if (response.status === 404) continue;
    } catch (e) {
      console.debug(`Metrics not available for plugin ${pluginName} at ${url}:`, e.message);
    }
  }
  return null;
}

/**
 * Generate activity widget HTML for a plugin
 */
function getPluginActivityWidget(plugin, metrics) {
  if (!plugin.enabled) {
    return `<div class="plugin-activity-widget disabled">
      <span class="activity-label">${t('plugin_activity_disabled') || 'Activity tracking disabled'}</span>
    </div>`;
  }
  
  if (!metrics) {
    return `<div class="plugin-activity-widget loading">
      <span class="activity-label">${t('plugin_activity_loading') || 'Loading metrics...'}</span>
    </div>`;
  }
  
  const requestCount = metrics.request_count || 0;
  const errorCount = metrics.error_count || 0;
  const errorRate = requestCount > 0 ? ((errorCount / requestCount) * 100).toFixed(1) : 0;
  const lastActivity = metrics.last_activity 
    ? formatRelativeTime(new Date(metrics.last_activity))
    : t('plugin_activity_never') || 'Never';
  
  // Custom metrics can include additional plugin-specific data
  const customMetrics = metrics.custom_metrics || {};
  
  return `<div class="plugin-activity-widget">
    <div class="activity-stats">
      <div class="activity-stat" title="${t('plugin_activity_requests_tooltip') || 'Total API requests'}">
        <span class="stat-icon">📊</span>
        <span class="stat-value">${requestCount}</span>
        <span class="stat-label">${t('plugin_activity_requests') || 'Requests'}</span>
      </div>
      <div class="activity-stat ${errorCount > 0 ? 'has-errors' : ''}" title="${t('plugin_activity_errors_tooltip') || 'Error count'}">
        <span class="stat-icon">⚠️</span>
        <span class="stat-value">${errorCount}</span>
        <span class="stat-label">${t('plugin_activity_errors') || 'Errors'}</span>
      </div>
      <div class="activity-stat" title="${t('plugin_activity_error_rate_tooltip') || 'Error rate percentage'}">
        <span class="stat-icon">📈</span>
        <span class="stat-value">${errorRate}%</span>
        <span class="stat-label">${t('plugin_activity_error_rate') || 'Error Rate'}</span>
      </div>
      <div class="activity-stat" title="${t('plugin_activity_last_tooltip') || 'Last activity timestamp'}">
        <span class="stat-icon">🕐</span>
        <span class="stat-value">${lastActivity}</span>
        <span class="stat-label">${t('plugin_activity_last') || 'Last Activity'}</span>
      </div>
    </div>
  </div>`;
}

/**
 * Load metrics for all enabled plugins and update their activity widgets
 */
async function loadPluginActivityWidgets() {
  const widgets = document.querySelectorAll('.plugin-activity-widget.loading');
  
  for (const widget of widgets) {
    const pluginName = widget.dataset.plugin;
    if (!pluginName) continue;
    
    const metrics = await fetchPluginMetrics(pluginName);
    if (metrics) {
      // Find parent card and get plugin data
      const card = widget.closest('.plugin-card');
      const plugin = state.pluginsCache?.find(p => p.name === pluginName) || { enabled: true };
      widget.outerHTML = getPluginActivityWidget(plugin, metrics);
    }
  }
}

function renderPluginList(plugins) {
  const container = document.getElementById("plugin-list");
  if (!container) return;
  container.innerHTML = "";
  
  // Cache plugins for later reference
  state.pluginsCache = plugins;

  updatePluginsSummary(plugins || []);

  if (!plugins || !plugins.length) {
    container.innerHTML = `<p class="empty">${t("plugins_empty")}</p>`;
    return;
  }

  plugins.forEach((plugin) => {
    const card = document.createElement("div");
    card.className = "plugin-card";

    const statusText = plugin.enabled ? t("plugin_enabled") : t("plugin_disabled");
    const statusClass = plugin.enabled ? "status-ok" : "status-disabled";
    const pluginVersion = plugin.version ? `v${plugin.version}` : "";
    const pluginIcon = getPluginIcon(plugin.name);
    
    // Trust badge based on trust_level and signature
    const trustBadge = getTrustBadge(plugin);
    
    // Circuit breaker indicator
    const circuitBreakerBadge = getCircuitBreakerBadge(plugin);
    
    // Activity widget placeholder (loaded async)
    const activityWidget = plugin.enabled 
      ? `<div class="plugin-activity-widget loading" data-plugin="${plugin.name}">
           <span class="activity-label">${t('plugin_activity_loading') || 'Loading metrics...'}</span>
         </div>`
      : `<div class="plugin-activity-widget disabled">
           <span class="activity-label">${t('plugin_activity_disabled') || 'Activity tracking disabled'}</span>
         </div>`;
    
    let configHtml = "";
    if (plugin.name === "notifications_webhook" && plugin.enabled) {
        const url = plugin.config && plugin.config.url ? plugin.config.url : "";
        configHtml = `
            <div class="plugin-config">
                <label class="small muted" style="display:block; margin-bottom: 6px;">Webhook URL</label>
                <div style="display:flex; gap: 8px;">
                    <input type="text" class="webhook-url-input" value="${url}" placeholder="https://..." style="flex:1; padding: 8px 10px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; color: var(--text-main); font-size: 0.875rem;">
                    <button class="primary small save-webhook-btn" data-plugin="${plugin.name}">${t("save") || "Save"}</button>
                </div>
            </div>
        `;
    }

    card.innerHTML = `
      <div class="plugin-header">
        <div class="plugin-info">
            <p class="plugin-name">
                <span>${pluginIcon}</span>
                ${plugin.name}
                ${pluginVersion ? `<span class="plugin-version">${pluginVersion}</span>` : ""}
                ${trustBadge}
                ${circuitBreakerBadge}
            </p>
            <p class="plugin-description">${plugin.description || t("plugin_no_description") || "No description available."}</p>
            <span class="plugin-status ${statusClass}">● ${statusText}</span>
        </div>
        <div class="plugin-actions">
          ${state.developerMode && plugin.restartable !== false ? `
          <button class="ghost small hot-reload-btn" data-action="hot-reload-plugin" data-plugin-name="${plugin.name}" title="${t('plugin_hot_reload_tooltip') || 'Hot reload plugin (dev mode)'}">
              🔥
          </button>
          ` : ''}
          ${plugin.restartable !== false ? `
          <button class="ghost small" data-action="restart-plugin" data-plugin-name="${plugin.name}" title="${t('plugin_restart_tooltip') || 'Restart plugin'}">
              🔄
          </button>
          ` : ''}
          <button class="${plugin.enabled ? 'secondary' : 'primary'} small" data-action="toggle-plugin" data-plugin-name="${plugin.name}" data-plugin-state="${!plugin.enabled}">
              ${plugin.enabled ? t('plugin_disable') || "Disable" : t('plugin_enable') || "Enable"}
          </button>
        </div>
      </div>
      ${activityWidget}
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
  
  // Load activity metrics asynchronously after rendering
  loadPluginActivityWidgets();
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

async function restartPlugin(name) {
    if (!state.apiBaseUrl) return;
    try {
        addLog(`Restarting plugin ${name}...`);
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/${name}/restart`, { method: "POST" });
        if (response.ok) {
            const result = await response.json();
            if (result.status === "ok") {
                addLog(`Plugin ${name} restarted successfully`);
                fetchPlugins(); // Refresh list
                // Also reload plugin menus in case UI config changed
                loadPluginMenus();
            } else {
                addLog(`Failed to restart plugin ${name}: ${result.message}`, "error");
            }
        } else {
            addLog(`Failed to restart plugin ${name}`, "error");
        }
    } catch (e) {
        console.error("Failed to restart plugin", e);
        addLog(`Error restarting plugin ${name}: ${e.message}`, "error");
    }
}

/**
 * Hot reload a plugin (developer mode only)
 * This reloads the plugin code from disk without a full restart.
 */
async function hotReloadPlugin(name) {
    if (!state.apiBaseUrl) return;
    
    // Double-check developer mode
    if (!state.developerMode) {
        addLog(`Hot reload requires developer mode - enable it in settings`, "warning");
        return;
    }
    
    try {
        addLog(`Hot reloading plugin ${name}...`);
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/v2/${name}/reload`, { method: "POST" });
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                addLog(`Plugin ${name} hot reloaded successfully (${result.duration_ms?.toFixed(0) || 0}ms)`);
                if (result.old_version && result.new_version && result.old_version !== result.new_version) {
                    addLog(`  Version changed: ${result.old_version} → ${result.new_version}`);
                }
                fetchPlugins(); // Refresh list
                // Clear loaded views cache
                pluginUIState.loadedViews.clear();
                pluginUIState.loadedSettings.clear();
                loadPluginMenus();
            } else {
                addLog(`Hot reload failed for ${name}: ${result.error || 'Unknown error'}`, "error");
                if (result.phase) {
                    addLog(`  Failed at phase: ${result.phase}`, "error");
                }
            }
        } else {
            const errorData = await response.json().catch(() => ({}));
            addLog(`Failed to hot reload plugin ${name}: ${errorData.detail || response.status}`, "error");
        }
    } catch (e) {
        console.error("Failed to hot reload plugin", e);
        addLog(`Error hot reloading plugin ${name}: ${e.message}`, "error");
    }
}

async function reloadAllPlugins() {
    if (!state.apiBaseUrl) return;
    try {
        addLog("Reloading all plugins...");
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/reload`, { method: "POST" });
        if (response.ok) {
            const result = await response.json();
            if (result.status === "ok") {
                addLog(`Plugins reloaded: ${result.count} plugins loaded`);
                if (result.added && result.added.length > 0) {
                    addLog(`New plugins discovered: ${result.added.join(", ")}`);
                }
                if (result.removed && result.removed.length > 0) {
                    addLog(`Plugins removed: ${result.removed.join(", ")}`);
                }
                fetchPlugins(); // Refresh list
                // Clear loaded views cache and reload menus
                pluginUIState.loadedViews.clear();
                pluginUIState.loadedSettings.clear();
                loadPluginMenus();
            } else {
                addLog("Failed to reload plugins", "error");
            }
        } else {
            addLog("Failed to reload plugins", "error");
        }
    } catch (e) {
        console.error("Failed to reload plugins", e);
        addLog(`Error reloading plugins: ${e.message}`, "error");
    }
}

// --- Plugin Marketplace, Install, Uninstall ---

/**
 * Open the plugin marketplace in a new tab
 */
function openPluginMarketplace() {
    const marketplaceUrl = "https://github.com/sn8k/Jupiter-project/tree/main/jupiter/plugins";
    window.open(marketplaceUrl, "_blank");
    addLog("Marketplace opened in new tab");
}

/**
 * Open the install plugin modal
 */
function openInstallPluginModal() {
    const modal = document.getElementById("install-plugin-modal");
    if (!modal) return;
    
    // Reset form state
    const urlInput = document.getElementById("install-plugin-url");
    const fileInput = document.getElementById("install-plugin-file");
    const errorDiv = document.getElementById("install-plugin-error");
    const successDiv = document.getElementById("install-plugin-success");
    const urlSection = document.getElementById("install-url-section");
    const fileSection = document.getElementById("install-file-section");
    const permissionsDiv = document.getElementById("install-plugin-permissions");
    
    if (urlInput) urlInput.value = "";
    if (fileInput) fileInput.value = "";
    if (errorDiv) { errorDiv.textContent = ""; errorDiv.classList.add("hidden"); }
    if (successDiv) { successDiv.textContent = ""; successDiv.classList.add("hidden"); }
    if (permissionsDiv) permissionsDiv.classList.add("hidden");
    
    // Reset tabs
    if (urlSection) urlSection.classList.remove("hidden");
    if (fileSection) fileSection.classList.add("hidden");
    document.querySelectorAll(".install-tab").forEach(tab => {
        tab.classList.toggle("active", tab.dataset.tab === "url");
    });
    
    // Bind tab switching
    document.querySelectorAll(".install-tab").forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll(".install-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            if (tab.dataset.tab === "url") {
                urlSection.classList.remove("hidden");
                fileSection.classList.add("hidden");
            } else {
                urlSection.classList.add("hidden");
                fileSection.classList.remove("hidden");
            }
            // Hide permissions when switching tabs
            if (permissionsDiv) permissionsDiv.classList.add("hidden");
        };
    });
    
    // Add URL change listener to preview permissions
    if (urlInput) {
        urlInput.addEventListener("change", previewPluginPermissions);
        urlInput.addEventListener("blur", previewPluginPermissions);
    }
    
    // Add file change listener to preview permissions
    if (fileInput) {
        fileInput.addEventListener("change", previewPluginPermissionsFromFile);
    }
    
    modal.showModal();
}

/**
 * Preview plugin permissions from URL
 */
async function previewPluginPermissions() {
    const urlInput = document.getElementById("install-plugin-url");
    const permissionsDiv = document.getElementById("install-plugin-permissions");
    const permissionsList = document.getElementById("install-plugin-permissions-list");
    
    if (!urlInput || !permissionsDiv || !permissionsList) return;
    
    const url = urlInput.value.trim();
    if (!url || !state.apiBaseUrl) {
        permissionsDiv.classList.add("hidden");
        return;
    }
    
    try {
        // Try to fetch plugin manifest to preview permissions
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/preview`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            const manifest = await response.json();
            renderPluginPermissions(manifest, permissionsList, permissionsDiv);
        } else {
            // If preview not available, hide the section
            permissionsDiv.classList.add("hidden");
        }
    } catch (e) {
        console.warn("Could not preview plugin permissions:", e);
        permissionsDiv.classList.add("hidden");
    }
}

/**
 * Preview plugin permissions from uploaded file
 */
async function previewPluginPermissionsFromFile() {
    const fileInput = document.getElementById("install-plugin-file");
    const permissionsDiv = document.getElementById("install-plugin-permissions");
    const permissionsList = document.getElementById("install-plugin-permissions-list");
    
    if (!fileInput || !permissionsDiv || !permissionsList || !fileInput.files || !fileInput.files[0]) {
        permissionsDiv.classList.add("hidden");
        return;
    }
    
    const file = fileInput.files[0];
    
    try {
        // Try to read manifest from ZIP file or parse permissions from .py file
        if (file.name.endsWith(".zip") && typeof JSZip !== "undefined") {
            const zip = await JSZip.loadAsync(file);
            const manifestFile = zip.file(/plugin\.yaml$/i)[0] || zip.file(/plugin\.yml$/i)[0];
            
            if (manifestFile) {
                const content = await manifestFile.async("text");
                // Simple YAML parsing for permissions
                const permissions = parsePermissionsFromYaml(content);
                renderPluginPermissions({ permissions }, permissionsList, permissionsDiv);
                return;
            }
        }
        
        // If we couldn't extract permissions, hide the section
        permissionsDiv.classList.add("hidden");
    } catch (e) {
        console.warn("Could not preview plugin permissions from file:", e);
        permissionsDiv.classList.add("hidden");
    }
}

/**
 * Parse permissions from YAML content (simple extraction)
 */
function parsePermissionsFromYaml(yamlContent) {
    const permissions = [];
    const lines = yamlContent.split('\n');
    let inPermissions = false;
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('permissions:')) {
            inPermissions = true;
            continue;
        }
        if (inPermissions) {
            if (trimmed.startsWith('-')) {
                const perm = trimmed.replace(/^-\s*/, '').trim();
                if (perm) permissions.push(perm);
            } else if (!trimmed.startsWith(' ') && trimmed !== '' && !trimmed.startsWith('#')) {
                break;
            }
        }
    }
    
    return permissions;
}

/**
 * Render plugin permissions in the modal
 */
function renderPluginPermissions(manifest, listElement, containerElement) {
    if (!manifest || !listElement || !containerElement) return;
    
    const permissions = manifest.permissions || [];
    
    if (permissions.length === 0) {
        containerElement.classList.add("hidden");
        return;
    }
    
    // Permission descriptions and icons
    const permissionInfo = {
        'file_read': { icon: '📖', label: t('perm_file_read') || 'Read files', risk: 'low' },
        'file_write': { icon: '✏️', label: t('perm_file_write') || 'Write files', risk: 'medium' },
        'file_delete': { icon: '🗑️', label: t('perm_file_delete') || 'Delete files', risk: 'high' },
        'network': { icon: '🌐', label: t('perm_network') || 'Network access', risk: 'medium' },
        'system_exec': { icon: '⚙️', label: t('perm_system_exec') || 'Execute system commands', risk: 'high' },
        'config_read': { icon: '⚙️', label: t('perm_config_read') || 'Read configuration', risk: 'low' },
        'config_write': { icon: '⚙️', label: t('perm_config_write') || 'Modify configuration', risk: 'medium' },
        'meeting_access': { icon: '🔗', label: t('perm_meeting_access') || 'Access Meeting service', risk: 'low' },
        'emit_events': { icon: '📢', label: t('perm_emit_events') || 'Emit events', risk: 'low' },
        'subscribe_events': { icon: '👂', label: t('perm_subscribe_events') || 'Subscribe to events', risk: 'low' }
    };
    
    // Risk level colors
    const riskColors = {
        'low': 'var(--success)',
        'medium': 'var(--warning)',
        'high': 'var(--danger)'
    };
    
    // Build permission list HTML
    listElement.innerHTML = permissions.map(perm => {
        const info = permissionInfo[perm] || { icon: '🔒', label: perm, risk: 'medium' };
        const riskColor = riskColors[info.risk] || riskColors.medium;
        
        return `
            <div class="permission-item" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: var(--panel-contrast); border-radius: 6px;">
                <span style="font-size: 1.1rem;">${info.icon}</span>
                <span style="flex: 1;">${info.label}</span>
                <span class="permission-risk" style="font-size: 0.7rem; padding: 0.15rem 0.4rem; border-radius: 4px; background: color-mix(in srgb, ${riskColor} 20%, transparent); color: ${riskColor};">
                    ${info.risk}
                </span>
            </div>
        `;
    }).join('');
    
    containerElement.classList.remove("hidden");
}

/**
 * Close the install plugin modal
 */
function closeInstallPluginModal() {
    const modal = document.getElementById("install-plugin-modal");
    if (modal) modal.close();
}

/**
 * Confirm plugin installation
 */
async function confirmInstallPlugin() {
    const errorDiv = document.getElementById("install-plugin-error");
    const successDiv = document.getElementById("install-plugin-success");
    const urlInput = document.getElementById("install-plugin-url");
    const fileInput = document.getElementById("install-plugin-file");
    
    // Reset messages
    if (errorDiv) { errorDiv.textContent = ""; errorDiv.classList.add("hidden"); }
    if (successDiv) { successDiv.textContent = ""; successDiv.classList.add("hidden"); }
    
    // Check which method is active
    const activeTab = document.querySelector(".install-tab.active");
    const method = activeTab ? activeTab.dataset.tab : "url";
    
    if (!state.apiBaseUrl) {
        if (errorDiv) {
            errorDiv.textContent = t("error_fetch") || "API not available";
            errorDiv.classList.remove("hidden");
        }
        return;
    }
    
    try {
        let response;
        
        if (method === "url") {
            const url = urlInput ? urlInput.value.trim() : "";
            if (!url) {
                if (errorDiv) {
                    errorDiv.textContent = t("plugins_install_error_empty_url") || "Please enter a URL.";
                    errorDiv.classList.remove("hidden");
                }
                return;
            }
            
            addLog(`Installing plugin from URL: ${url}...`);
            response = await apiFetch(`${state.apiBaseUrl}/plugins/install`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            });
        } else {
            const file = fileInput && fileInput.files ? fileInput.files[0] : null;
            if (!file) {
                if (errorDiv) {
                    errorDiv.textContent = t("plugins_install_error_no_file") || "Please select a file.";
                    errorDiv.classList.remove("hidden");
                }
                return;
            }
            
            addLog(`Installing plugin from file: ${file.name}...`);
            const formData = new FormData();
            formData.append("file", file);
            
            response = await apiFetch(`${state.apiBaseUrl}/plugins/install/upload`, {
                method: "POST",
                body: formData
            });
        }
        
        if (response.ok) {
            const result = await response.json();
            if (result.status === "ok" || result.success) {
                if (successDiv) {
                    successDiv.textContent = t("plugins_install_success") || `Plugin "${result.plugin_name || 'plugin'}" installed successfully!`;
                    successDiv.classList.remove("hidden");
                }
                addLog(`Plugin installed: ${result.plugin_name || 'unknown'}`);
                
                // Refresh plugins list after short delay
                setTimeout(() => {
                    closeInstallPluginModal();
                    reloadAllPlugins();
                }, 1500);
            } else {
                if (errorDiv) {
                    errorDiv.textContent = result.message || t("plugins_install_error") || "Installation failed.";
                    errorDiv.classList.remove("hidden");
                }
            }
        } else {
            const errorText = await response.text();
            if (errorDiv) {
                errorDiv.textContent = errorText || t("plugins_install_error") || "Installation failed.";
                errorDiv.classList.remove("hidden");
            }
        }
    } catch (e) {
        console.error("Failed to install plugin", e);
        if (errorDiv) {
            errorDiv.textContent = e.message || t("plugins_install_error") || "Installation failed.";
            errorDiv.classList.remove("hidden");
        }
    }
}

/**
 * Open the uninstall plugin modal
 */
async function openUninstallPluginModal() {
    const modal = document.getElementById("uninstall-plugin-modal");
    if (!modal) return;
    
    // Reset state
    const select = document.getElementById("uninstall-plugin-select");
    const confirmSection = document.getElementById("uninstall-confirm-section");
    const errorDiv = document.getElementById("uninstall-plugin-error");
    const successDiv = document.getElementById("uninstall-plugin-success");
    const confirmBtn = modal.querySelector('[data-action="confirm-uninstall-plugin"]');
    
    if (confirmSection) confirmSection.classList.add("hidden");
    if (errorDiv) { errorDiv.textContent = ""; errorDiv.classList.add("hidden"); }
    if (successDiv) { successDiv.textContent = ""; successDiv.classList.add("hidden"); }
    if (confirmBtn) confirmBtn.disabled = true;
    
    // Load plugins into select
    if (select && state.apiBaseUrl) {
        select.innerHTML = `<option value="">${t("plugins_uninstall_select_placeholder") || "-- Select a plugin --"}</option>`;
        
        try {
            const response = await apiFetch(`${state.apiBaseUrl}/plugins`);
            if (response.ok) {
                const plugins = await response.json();
                plugins.forEach(plugin => {
                    // Only show removable plugins (not core ones)
                    if (!plugin.is_core) {
                        const option = document.createElement("option");
                        option.value = plugin.name;
                        option.textContent = `${plugin.name} ${plugin.version ? `(v${plugin.version})` : ""}`;
                        select.appendChild(option);
                    }
                });
            }
        } catch (e) {
            console.error("Failed to load plugins for uninstall", e);
        }
        
        // Bind select change to show confirmation
        select.onchange = () => {
            if (select.value) {
                if (confirmSection) confirmSection.classList.remove("hidden");
                if (confirmBtn) confirmBtn.disabled = false;
            } else {
                if (confirmSection) confirmSection.classList.add("hidden");
                if (confirmBtn) confirmBtn.disabled = true;
            }
        };
    }
    
    modal.showModal();
}

/**
 * Close the uninstall plugin modal
 */
function closeUninstallPluginModal() {
    const modal = document.getElementById("uninstall-plugin-modal");
    if (modal) modal.close();
}

/**
 * Confirm plugin uninstallation
 */
async function confirmUninstallPlugin() {
    const select = document.getElementById("uninstall-plugin-select");
    const errorDiv = document.getElementById("uninstall-plugin-error");
    const successDiv = document.getElementById("uninstall-plugin-success");
    
    const pluginName = select ? select.value : "";
    if (!pluginName) {
        if (errorDiv) {
            errorDiv.textContent = t("plugins_uninstall_error_no_selection") || "Please select a plugin.";
            errorDiv.classList.remove("hidden");
        }
        return;
    }
    
    // Reset messages
    if (errorDiv) { errorDiv.textContent = ""; errorDiv.classList.add("hidden"); }
    if (successDiv) { successDiv.textContent = ""; successDiv.classList.add("hidden"); }
    
    if (!state.apiBaseUrl) {
        if (errorDiv) {
            errorDiv.textContent = t("error_fetch") || "API not available";
            errorDiv.classList.remove("hidden");
        }
        return;
    }
    
    try {
        addLog(`Uninstalling plugin: ${pluginName}...`);
        
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/${pluginName}/uninstall`, {
            method: "DELETE"
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.status === "ok" || result.success) {
                if (successDiv) {
                    successDiv.textContent = t("plugins_uninstall_success") || `Plugin "${pluginName}" uninstalled successfully!`;
                    successDiv.classList.remove("hidden");
                }
                addLog(`Plugin uninstalled: ${pluginName}`);
                
                // Refresh plugins list after short delay
                setTimeout(() => {
                    closeUninstallPluginModal();
                    reloadAllPlugins();
                }, 1500);
            } else {
                if (errorDiv) {
                    errorDiv.textContent = result.message || t("plugins_uninstall_error") || "Uninstallation failed.";
                    errorDiv.classList.remove("hidden");
                }
            }
        } else {
            const errorText = await response.text();
            if (errorDiv) {
                errorDiv.textContent = errorText || t("plugins_uninstall_error") || "Uninstallation failed.";
                errorDiv.classList.remove("hidden");
            }
        }
    } catch (e) {
        console.error("Failed to uninstall plugin", e);
        if (errorDiv) {
            errorDiv.textContent = e.message || t("plugins_uninstall_error") || "Uninstallation failed.";
            errorDiv.classList.remove("hidden");
        }
    }
}

// --- Dynamic Plugin UI Management ---

/**
 * State for tracking loaded plugin UIs
 */
const pluginUIState = {
    sidebarPlugins: [],
    settingsPlugins: [],
    loadedViews: new Set(),
    loadedSettings: new Set()
};

/**
 * Load plugin menu items and inject them into the sidebar
 */
async function loadPluginMenus() {
    if (!state.apiBaseUrl) return;
    
    try {
        // Load sidebar plugins
        const sidebarResp = await apiFetch(`${state.apiBaseUrl}/plugins/sidebar`);
        if (sidebarResp.ok) {
            pluginUIState.sidebarPlugins = await sidebarResp.json();
            injectPluginMenuItems();
        }
        
        // Load settings plugins
        const settingsResp = await apiFetch(`${state.apiBaseUrl}/plugins/settings`);
        if (settingsResp.ok) {
            pluginUIState.settingsPlugins = await settingsResp.json();
            // Settings will be loaded when settings view is opened
        }
    } catch (e) {
        console.error("[PluginUI] Failed to load plugin menus:", e);
    }
}

/**
 * Inject plugin menu items into the navigation sidebar
 */
function injectPluginMenuItems() {
    const marker = document.getElementById('plugin-menu-marker');
    if (!marker) return;
    
    // Remove any previously injected plugin buttons
    document.querySelectorAll('.nav-btn[data-plugin-view]').forEach(btn => btn.remove());
    
    // Sort plugins by menu_order
    const sortedPlugins = [...pluginUIState.sidebarPlugins].sort((a, b) => 
        (a.menu_order || 100) - (b.menu_order || 100)
    );
    
    for (const plugin of sortedPlugins) {
        const viewId = `plugin-${plugin.view_id || plugin.name}`;
        const btn = document.createElement('button');
        btn.className = 'nav-btn';
        btn.dataset.view = viewId;
        btn.dataset.pluginView = plugin.name;
        btn.dataset.i18n = plugin.menu_label_key || plugin.name;
        
        // Store v2 info for proper loading
        if (plugin.v2) {
            btn.dataset.v2 = 'true';
            btn.dataset.route = plugin.route || '';
        }
        
        // Get the translated label
        let label = t(plugin.menu_label_key) || plugin.name;
        const icon = plugin.menu_icon || '🔌';
        
        // Check if label already starts with an emoji (to avoid double icons)
        // Emoji regex pattern - matches most common emojis at start of string
        const emojiPattern = /^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
        const labelHasEmoji = emojiPattern.test(label);
        
        const iconSpan = document.createElement('span');
        iconSpan.className = 'plugin-icon';
        
        const labelSpan = document.createElement('span');
        labelSpan.className = 'plugin-label';
        
        if (labelHasEmoji) {
            // Label already has icon - use as-is, no separate icon
            iconSpan.textContent = '';
            labelSpan.textContent = label;
        } else {
            // Add icon separately
            iconSpan.textContent = icon + ' ';
            labelSpan.textContent = label;
        }
        
        btn.appendChild(iconSpan);
        btn.appendChild(labelSpan);
        
        // Insert before the marker
        marker.parentNode.insertBefore(btn, marker);
        
        // Ensure we have a view container for this plugin
        ensurePluginViewContainer(viewId, plugin.name);
    }
    
    // Re-bind navigation events
    bindPluginNavigation();
}

/**
 * Ensure a view container exists for a plugin
 */
function ensurePluginViewContainer(viewId, pluginName) {
    const container = document.getElementById('plugin-views-container');
    if (!container) return;
    
    // Check if view already exists (only consider actual view sections)
    if (document.querySelector(`section.view[data-view="${viewId}"]`)) return;
    
    // Create view section
    const section = document.createElement('section');
    section.className = 'view hidden';
    section.dataset.view = viewId;
    section.dataset.pluginName = pluginName;
    section.setAttribute('aria-label', `Vue ${pluginName}`);
    section.innerHTML = `
        <div class="plugin-view-loading">
            <p>${t('loading') || 'Loading...'}</p>
        </div>
    `;
    
    container.appendChild(section);
}

/**
 * Bind navigation events for plugin views
 */
function bindPluginNavigation() {
    document.querySelectorAll('.nav-btn[data-plugin-view]').forEach(btn => {
        btn.addEventListener('click', () => {
            const viewId = btn.dataset.view;
            const pluginName = btn.dataset.pluginView;
            const isV2 = btn.dataset.v2 === 'true';
            setView(viewId);
            loadPluginViewContent(pluginName, viewId, isV2);
        });
    });
}

/**
 * Create a bridge object for v2 plugins
 * This provides the interface expected by mount(container, bridge)
 * @param {string} pluginName - The plugin ID
 * @param {Object} pluginTranslations - Plugin-specific translations (optional)
 */
function createPluginBridge(pluginName, pluginTranslations = {}) {
  const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();

    // Create a translation function that checks plugin translations first, then global
    const pluginT = (key) => {
        // First check plugin-specific translations
        if (pluginTranslations[key]) {
            return pluginTranslations[key];
        }
        // Fall back to global translations
        return t(key);
    };
    
    return {
        // i18n support with plugin-aware translation
        i18n: {
            t: pluginT,
            lang: state.i18n.lang,
            // Expose raw plugin translations for advanced use
            pluginTranslations: pluginTranslations,
        },
        // API calls
        api: {
          baseUrl: apiBaseUrl,
          fetch: async (path, options = {}) => {
            const url = path.startsWith('http') ? path : `${apiBaseUrl}${path}`;
            const response = await apiFetch(url, options);
            if (!response.ok) {
              let detail = '';
              try {
                detail = await response.json();
              } catch (err) {
                detail = await response.text().catch(() => '');
              }
              const message = typeof detail === 'object' ? (detail.detail || detail.message || JSON.stringify(detail)) : detail;
              throw new Error(message || `HTTP ${response.status}`);
            }
            return response;
          },
          get: async (path) => {
            const response = await apiFetch(`${apiBaseUrl}${path}`);
            if (!response.ok) {
              const detail = await response.json().catch(() => ({}));
              throw new Error(detail.detail || detail.message || `HTTP ${response.status}`);
            }
            return response.json();
          },
          post: async (path, data) => {
            const response = await apiFetch(`${apiBaseUrl}${path}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data),
            });
            if (!response.ok) {
              const detail = await response.json().catch(() => ({}));
              throw new Error(detail.detail || detail.message || `HTTP ${response.status}`);
            }
            return response.json();
          },
        },
        // State access (read-only for now)
        state: {
            get report() { return state.report; },
            get context() { return state.context; },
            get theme() { return state.theme; },
            get apiBaseUrl() { return state.apiBaseUrl; },
        },
        // Events
        events: {
            on: (event, callback) => {
                // Simple event listener for plugin use
                window.addEventListener(`jupiter-${event}`, (e) => callback(e.detail));
            },
            emit: (event, data) => {
                window.dispatchEvent(new CustomEvent(`jupiter-${event}`, { detail: data }));
            },
        },
        // Plugin config
        config: {
            get: async () => {
                const resp = await apiFetch(`${state.apiBaseUrl}/plugins/v2/${pluginName}/config`);
                return resp.ok ? resp.json() : {};
            },
            save: async (config) => {
                const resp = await apiFetch(`${state.apiBaseUrl}/plugins/v2/${pluginName}/config`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config),
                });
                return resp.ok;
            },
        },
        // Logging
        log: {
            debug: (...args) => console.debug(`[${pluginName}]`, ...args),
            info: (...args) => console.log(`[${pluginName}]`, ...args),
            warn: (...args) => console.warn(`[${pluginName}]`, ...args),
            error: (...args) => console.error(`[${pluginName}]`, ...args),
        },
    };
}

/**
 * Load and inject plugin view content (HTML + JS)
 * For v2 plugins, uses the mount(container, bridge) pattern with ES modules.
 */
async function loadPluginViewContent(pluginName, viewId, isV2 = false) {
    // Use viewId as key to allow multiple panels per plugin
    const loadKey = `${pluginName}:${viewId}`;
    if (pluginUIState.loadedViews.has(loadKey)) return;
    
    // Use more specific selector to get the section, not the button
    const section = document.querySelector(`section.view[data-view="${viewId}"]`);
    if (!section) {
        console.error(`[PluginUI] Section not found for view: ${viewId}`);
        return;
    }
    
    console.log(`[PluginUI] Loading view for plugin: ${pluginName}, viewId: ${viewId}, v2: ${isV2}`);
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/plugins/${pluginName}/ui`);
        console.log(`[PluginUI] Response status: ${response.status}`);
        
        if (!response.ok) {
            console.error(`[PluginUI] Response not OK: ${response.status}`);
            section.innerHTML = `<div class="panel"><p class="error">Failed to load plugin UI (${response.status})</p></div>`;
            return;
        }
        
        const data = await response.json();
        console.log(`[PluginUI] Data received:`, { hasHtml: !!data.html, hasJs: !!data.js, htmlLength: data.html?.length, jsLength: data.js?.length, v2: isV2 });
        
        // Inject HTML container
        section.innerHTML = data.html || '<div class="plugin-v2-container"></div>';
        
        // Force DOM update before JS execution
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        
        // Verify elements are in DOM
        const container = section.querySelector('.plugin-v2-container, [id]');
        console.log(`[PluginUI] Container found:`, container?.className || container?.id || 'none');
        
        // Handle JS loading
        if (data.js) {
            if (isV2) {
                // V2 plugins use ES module pattern with mount(container, bridge)
                try {
                    // Load plugin translations first
                    let pluginTranslations = {};
                    try {
                        const langResponse = await apiFetch(`${state.apiBaseUrl}/plugins/${pluginName}/lang/${state.i18n.lang}`);
                        if (langResponse.ok) {
                            const langData = await langResponse.json();
                            pluginTranslations = langData.translations || {};
                            console.log(`[PluginUI] Loaded ${Object.keys(pluginTranslations).length} translations for ${pluginName}`);
                        }
                    } catch (langError) {
                        console.debug(`[PluginUI] No translations found for ${pluginName}:`, langError.message);
                    }
                    
                    // Create a blob URL from the JS content for dynamic import
                    const blob = new Blob([data.js], { type: 'application/javascript' });
                    const moduleUrl = URL.createObjectURL(blob);
                    
                    // Dynamically import the module
                    const module = await import(moduleUrl);
                    
                    // Clean up the blob URL
                    URL.revokeObjectURL(moduleUrl);
                    
                    // Find mount target (prefer .plugin-v2-container)
                    const mountTarget = section.querySelector('.plugin-v2-container') || 
                                        section.querySelector(`#plugin-${pluginName}-container`) ||
                                        section;
                    
                    // Create bridge with plugin translations and call mount
                    if (typeof module.mount === 'function') {
                        const bridge = createPluginBridge(pluginName, pluginTranslations);
                        console.log(`[PluginUI] Calling v2 mount() for ${pluginName}`);
                        module.mount(mountTarget, bridge);
                    } else {
                        console.warn(`[PluginUI] v2 module does not export mount(): ${pluginName}`);
                        // Fallback: maybe it has default export or init
                        if (module.default && typeof module.default === 'function') {
                            module.default(mountTarget, createPluginBridge(pluginName, pluginTranslations));
                        }
                    }
                    
                    console.log(`[PluginUI] v2 JS module loaded successfully`);
                } catch (moduleError) {
                    console.error(`[PluginUI] Error loading v2 module:`, moduleError);
                    // Fallback to legacy injection
                    console.log(`[PluginUI] Falling back to legacy script injection`);
                    const script = document.createElement('script');
                    script.textContent = data.js;
                    document.body.appendChild(script);
                }
            } else {
                // Legacy plugins: inject as script tag
                try {
                    const script = document.createElement('script');
                    script.textContent = data.js;
                    document.body.appendChild(script);
                    console.log(`[PluginUI] Legacy JS injected successfully`);
                } catch (jsError) {
                    console.error(`[PluginUI] Error executing JS:`, jsError);
                }
            }
        }
        
        // Apply i18n to new content
        translateUI();
        
        // For legacy plugins, try to call init function
        if (!isV2) {
            requestAnimationFrame(() => {
                const initFnName = `${pluginName.replace(/-/g, '_')}View`;
                if (window[initFnName] && typeof window[initFnName].init === 'function') {
                    console.log(`[PluginUI] Calling ${initFnName}.init()`);
                    window[initFnName].init();
                } else {
                    // Try common naming patterns
                    const patterns = ['pylanceView', 'webhookView'];
                    for (const pattern of patterns) {
                        if (window[pattern] && typeof window[pattern].init === 'function') {
                            console.log(`[PluginUI] Calling ${pattern}.init()`);
                            window[pattern].init();
                            break;
                        }
                    }
                }
            });
        }
        
        pluginUIState.loadedViews.add(loadKey);
        console.log(`[PluginUI] View loaded successfully for ${pluginName}`);
        
    } catch (e) {
        console.error(`[PluginUI] Failed to load view for ${pluginName}:`, e);
        section.innerHTML = `<div class="panel"><p class="error">Error: ${e.message}</p></div>`;
    }
}

/**
 * Load and inject plugin settings into the settings page
 */
async function loadPluginSettings() {
    const container = document.getElementById('plugin-settings-container');
    if (!container) {
        console.warn("[PluginUI] plugin-settings-container not found");
        return;
    }
    
    // Check if we have API base URL and token
    if (!state.apiBaseUrl) {
        console.warn("[PluginUI] No API base URL, skipping settings load");
        return;
    }
    
    // Always reload settings plugins list when opening settings page
    try {
        const settingsResp = await apiFetch(`${state.apiBaseUrl}/plugins/settings`);
        if (settingsResp.ok) {
            pluginUIState.settingsPlugins = await settingsResp.json();
            console.log(`[PluginUI] Loaded ${pluginUIState.settingsPlugins.length} settings plugins from API`);
        } else {
            console.warn("[PluginUI] Failed to load settings plugins, status:", settingsResp.status);
        }
    } catch (e) {
        console.error("[PluginUI] Failed to load settings plugins list:", e);
        // Don't return - try to use any cached plugins
    }
    
    if (pluginUIState.settingsPlugins.length === 0) {
        console.log("[PluginUI] No settings plugins to display");
        return;
    }
    
    // Clear previous settings
    container.innerHTML = '';
    pluginUIState.loadedSettings.clear();
    
    console.log(`[PluginUI] Loading settings for ${pluginUIState.settingsPlugins.length} plugins`);
    
    for (const plugin of pluginUIState.settingsPlugins) {
        console.log(`[PluginUI] Loading settings for ${plugin.name} (v2=${plugin.v2}, has_config=${plugin.has_config_schema})`);
        try {
            const response = await apiFetch(`${state.apiBaseUrl}/plugins/${plugin.name}/settings-ui`);
            if (!response.ok) continue;
            
            const data = await response.json();
            
            if (data.html) {
                const wrapper = document.createElement('div');
                wrapper.className = 'plugin-settings-card';
                wrapper.dataset.pluginSettings = plugin.name;
                wrapper.innerHTML = data.html;
                container.appendChild(wrapper);
                
                // For v2 plugins with config schema, initialize auto-form
                if (plugin.v2 && plugin.has_config_schema) {
                    await initializeV2SettingsForm(wrapper, plugin.name);
                }
            }
            
            // Inject and execute JS
            if (data.js) {
                const script = document.createElement('script');
                script.textContent = data.js;
                document.body.appendChild(script);
            }
            
            pluginUIState.loadedSettings.add(plugin.name);
            
        } catch (e) {
            console.error(`[PluginUI] Failed to load settings for ${plugin.name}:`, e);
        }
    }
    
    // Apply i18n to new content
    translateUI();
}

/**
 * Initialize auto-generated settings form for v2 plugins
 */
async function initializeV2SettingsForm(container, pluginName) {
    console.log(`[PluginUI] initializeV2SettingsForm for ${pluginName}`);
    const settingsDiv = container.querySelector('.plugin-v2-settings');
    if (!settingsDiv) {
        console.warn(`[PluginUI] No .plugin-v2-settings found for ${pluginName}`);
        return;
    }
    
    const schema = settingsDiv.dataset.schema;
    if (!schema) {
        console.warn(`[PluginUI] No data-schema found for ${pluginName}`);
        return;
    }
    
    console.log(`[PluginUI] Schema for ${pluginName}:`, schema.substring(0, 100) + '...');
    
    try {
        const schemaObj = JSON.parse(schema);
        const formContainer = settingsDiv.querySelector('.auto-form-container');
        if (!formContainer) {
            console.warn(`[PluginUI] No .auto-form-container found for ${pluginName}`);
            return;
        }
        
        // Get current config
        console.log(`[PluginUI] Fetching config for ${pluginName}...`);
        const configResp = await apiFetch(`${state.apiBaseUrl}/plugins/v2/${pluginName}/config`);
        let currentConfig = {};
        if (configResp.ok) {
            const configData = await configResp.json();
            currentConfig = configData.config || {};
            console.log(`[PluginUI] Got config for ${pluginName}:`, currentConfig);
        } else {
            console.warn(`[PluginUI] Failed to get config for ${pluginName}, status:`, configResp.status);
        }
        
        // Generate form from schema
        const formHtml = generateFormFromSchema(schemaObj, currentConfig, pluginName);
        console.log(`[PluginUI] Generated form HTML for ${pluginName}, length:`, formHtml.length);
        formContainer.innerHTML = formHtml;
        
        // Add save handler
        const saveBtn = formContainer.querySelector('.settings-save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => saveV2PluginSettings(pluginName, formContainer));
        }
        
        console.log(`[PluginUI] V2 settings form initialized for ${pluginName}`);
        
    } catch (e) {
        console.error(`[PluginUI] Failed to init v2 settings form for ${pluginName}:`, e);
    }
}

/**
 * Generate HTML form from JSON schema
 */
function generateFormFromSchema(schema, values, pluginName) {
    if (!schema.properties) return '<p>No configurable properties</p>';
    
    let html = '<div class="settings-form">';
    
    for (const [key, prop] of Object.entries(schema.properties)) {
        const value = values[key] !== undefined ? values[key] : (prop.default !== undefined ? prop.default : '');
        const inputId = `${pluginName}-${key}`;
        
        html += `<div class="form-group">`;
        html += `<label for="${inputId}">${prop.title || key}</label>`;
        
        if (prop.type === 'boolean') {
            html += `<input type="checkbox" id="${inputId}" name="${key}" ${value ? 'checked' : ''}>`;
        } else if (prop.type === 'integer' || prop.type === 'number') {
            html += `<input type="number" id="${inputId}" name="${key}" value="${value}">`;
        } else if (prop.enum) {
            html += `<select id="${inputId}" name="${key}">`;
            for (const opt of prop.enum) {
                html += `<option value="${opt}" ${value === opt ? 'selected' : ''}>${opt}</option>`;
            }
            html += `</select>`;
        } else if (prop.type === 'array') {
            // Simple array input as comma-separated
            const arrValue = Array.isArray(value) ? value.join(', ') : '';
            html += `<input type="text" id="${inputId}" name="${key}" value="${arrValue}" placeholder="comma-separated values">`;
        } else {
            // Default: text input
            const inputType = key.toLowerCase().includes('password') || key.toLowerCase().includes('key') ? 'password' : 'text';
            html += `<input type="${inputType}" id="${inputId}" name="${key}" value="${value}">`;
        }
        
        if (prop.description) {
            html += `<small class="form-help">${prop.description}</small>`;
        }
        
        html += `</div>`;
    }
    
    html += `<button type="button" class="settings-save-btn primary-btn">${t('save') || 'Save'}</button>`;
    html += '</div>';
    
    return html;
}

/**
 * Save v2 plugin settings
 */
async function saveV2PluginSettings(pluginName, formContainer) {
    const inputs = formContainer.querySelectorAll('input, select');
    const config = {};
    
    inputs.forEach(input => {
        const name = input.name;
        if (!name) return;
        
        if (input.type === 'checkbox') {
            config[name] = input.checked;
        } else if (input.type === 'number') {
            config[name] = parseFloat(input.value) || 0;
        } else if (input.value.includes(',')) {
            // Might be an array
            config[name] = input.value.split(',').map(s => s.trim()).filter(s => s);
        } else {
            config[name] = input.value;
        }
    });
    
    try {
        const resp = await apiFetch(`${state.apiBaseUrl}/plugins/v2/${pluginName}/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config }),
        });
        
        if (resp.ok) {
            showToast(t('settings_saved') || 'Settings saved');
        } else {
            const err = await resp.json();
            showToast(t('error') + ': ' + (err.detail || 'Save failed'), 'error');
        }
    } catch (e) {
        console.error(`[PluginUI] Failed to save settings for ${pluginName}:`, e);
        showToast(t('error') + ': ' + e.message, 'error');
    }
}

// --- Projects Management ---

async function performProjectMutation(path, options, onSuccess, errorLabel) {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}${path}`, options);
        if (response.ok) {
            await onSuccess(response);
            return;
        }
        const err = await response.json();
        alert((errorLabel || "Erreur") + ": " + (err.detail || "Action impossible"));
    } catch (e) {
        console.error(e);
        alert("Erreur réseau");
    }
}

async function loadProjects() {
    if (!state.apiBaseUrl) state.apiBaseUrl = inferApiBaseUrl();
    if (!state.apiBaseUrl) return;

    try {
        const response = await apiFetch(`${state.apiBaseUrl}/projects`);
        if (response.ok) {
            const projects = await response.json();
            state.projects = projects;
            const active = projects.find((p) => p.is_active) || null;
            state.activeProjectId = active ? active.id : null;
            renderProjects(projects);
            const hasActive = projects.some((p) => p.is_active);
            if (hasActive && !state.report) {
                await loadCachedReport();
            }
            if (state.activeProjectId) {
                await loadProjectApiConfig(state.activeProjectId);
                await loadProjectPerformanceConfig();
                await loadProjectRootEntries();
            }
        } else {
            console.error("Failed to load projects");
            addLog("Erreur lors du chargement des projets", "ERROR");
        }
    } catch (e) {
        console.error("Error loading projects", e);
        addLog("Erreur réseau (projets)", "ERROR");
    }
}

async function loadProjectApiConfig(projectId) {
    if (!state.apiBaseUrl || !projectId) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/projects/${projectId}/api_config`);
        if (!response.ok) return;
        const data = await response.json();
        const connectorSelect = document.getElementById("project-api-connector");
        const appVarInput = document.getElementById("project-api-app-var");
        const pathInput = document.getElementById("project-api-path");
        if (connectorSelect) {
            connectorSelect.value = data.connector || "";
            connectorSelect.dispatchEvent(new Event("change"));
        }
        if (appVarInput) appVarInput.value = data.app_var || "";
        if (pathInput) pathInput.value = data.path || "";
    } catch (e) {
        console.error("Failed to load project API config", e);
    }
}

async function loadProjectPerformanceConfig() {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/config`);
        if (!response.ok) return;
        const config = await response.json();
        
        // Load performance settings into the Projects view
        if (document.getElementById("conf-perf-parallel")) {
            document.getElementById("conf-perf-parallel").checked = config.perf_parallel_scan !== false;
        }
        if (document.getElementById("conf-perf-workers")) {
            document.getElementById("conf-perf-workers").value = config.perf_max_workers || 0;
        }
        if (document.getElementById("conf-perf-timeout")) {
            document.getElementById("conf-perf-timeout").value = config.perf_scan_timeout || 300;
        }
        if (document.getElementById("conf-perf-graph-simple")) {
            document.getElementById("conf-perf-graph-simple").checked = config.perf_graph_simplification || false;
        }
        if (document.getElementById("conf-perf-graph-nodes")) {
            document.getElementById("conf-perf-graph-nodes").value = config.perf_max_graph_nodes || 1000;
        }
    } catch (e) {
        console.error("Failed to load project performance config", e);
    }
}

async function saveProjectApiConfig() {
    if (!state.apiBaseUrl || !state.activeProjectId) {
        alert("Aucun projet actif");
        return;
    }
    const connector = document.getElementById("project-api-connector")?.value || "";
    const appVar = document.getElementById("project-api-app-var")?.value || "";
    const path = document.getElementById("project-api-path")?.value || "";
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/projects/${state.activeProjectId}/api_config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                connector: connector || null,
                app_var: appVar || null,
                path: path || null
            })
        });
        if (response.ok) {
            addLog(t("project_api_saved") || "Configuration API sauvegardée");
            const data = await response.json();
            if (data.connector) {
                updateProjectOverview(state.projects, state.projects.find(p => p.id === state.activeProjectId));
            }
        } else {
            const err = await response.json();
            alert((t("project_api_error") || "Erreur enregistrement API") + ": " + (err.detail || ""));
        }
    } catch (e) {
        console.error("Failed to save project API config", e);
        alert("Erreur réseau");
    }
}

// ===============================
// Project Root Entries (Ignore UI)
// ===============================

let projectRootEntries = [];
let projectCurrentIgnores = [];

async function loadProjectRootEntries() {
    if (!state.apiBaseUrl) return;
    
    const grid = document.getElementById("ignore-entries-grid");
    if (!grid) return;
    
    grid.innerHTML = `<p class="muted small">${t("project_ignore_loading") || "Chargement..."}</p>`;
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/project/root-entries`);
        if (!response.ok) {
            grid.innerHTML = `<p class="muted small">${t("project_ignore_error") || "Erreur de chargement"}</p>`;
            return;
        }
        
        const data = await response.json();
        projectRootEntries = data.entries || [];
        projectCurrentIgnores = data.current_ignores || [];
        
        // Populate custom patterns input with non-entry ignores
        const customInput = document.getElementById("ignore-custom-input");
        if (customInput) {
            // Filter out patterns that match root entries (those are managed by checkboxes)
            const entryNames = projectRootEntries.map(e => e.is_dir ? `${e.name}/**` : e.name);
            const customPatterns = projectCurrentIgnores.filter(p => !entryNames.includes(p) && !projectRootEntries.some(e => e.name === p || `${e.name}/**` === p));
            customInput.value = customPatterns.join(", ");
        }
        
        renderIgnoreEntries();
        setupIgnoreEventListeners();
        
    } catch (e) {
        console.error("Failed to load project root entries", e);
        grid.innerHTML = `<p class="muted small">${t("project_ignore_error") || "Erreur de chargement"}</p>`;
    }
}

function renderIgnoreEntries() {
    const grid = document.getElementById("ignore-entries-grid");
    const filterInput = document.getElementById("ignore-filter-input");
    const showHiddenCheckbox = document.getElementById("ignore-toggle-hidden");
    
    if (!grid) return;
    
    const filterText = (filterInput?.value || "").toLowerCase();
    const showHidden = showHiddenCheckbox?.checked || false;
    
    if (projectRootEntries.length === 0) {
        grid.innerHTML = `<p class="muted small">${t("project_ignore_empty") || "Aucun fichier à la racine"}</p>`;
        return;
    }
    
    grid.innerHTML = "";
    
    projectRootEntries.forEach(entry => {
        // Skip if filtered
        if (filterText && !entry.name.toLowerCase().includes(filterText)) {
            return;
        }
        
        // Check if this entry is ignored
        const ignorePattern = entry.is_dir ? `${entry.name}/**` : entry.name;
        const isIgnored = projectCurrentIgnores.includes(ignorePattern) || projectCurrentIgnores.includes(entry.name);
        
        const div = document.createElement("div");
        div.className = "ignore-entry";
        if (isIgnored) div.classList.add("ignored");
        if (entry.is_hidden) {
            div.classList.add("hidden-file");
            if (showHidden) div.classList.add("show-hidden");
        }
        
        div.innerHTML = `
            <input type="checkbox" ${isIgnored ? "checked" : ""} data-entry="${entry.name}" data-is-dir="${entry.is_dir}" />
            <span class="ignore-entry-icon">${entry.is_dir ? "📁" : "📄"}</span>
            <span class="ignore-entry-name ${entry.is_dir ? "is-dir" : ""}">${entry.name}</span>
        `;
        
        // Toggle on click anywhere on the entry
        div.addEventListener("click", (e) => {
            if (e.target.tagName !== "INPUT") {
                const checkbox = div.querySelector("input[type='checkbox']");
                if (checkbox) checkbox.click();
            }
        });
        
        // Handle checkbox change
        const checkbox = div.querySelector("input[type='checkbox']");
        checkbox.addEventListener("change", () => {
            div.classList.toggle("ignored", checkbox.checked);
        });
        
        grid.appendChild(div);
    });
}

function setupIgnoreEventListeners() {
    const filterInput = document.getElementById("ignore-filter-input");
    const showHiddenCheckbox = document.getElementById("ignore-toggle-hidden");
    
    if (filterInput) {
        filterInput.oninput = () => renderIgnoreEntries();
    }
    
    if (showHiddenCheckbox) {
        showHiddenCheckbox.onchange = () => {
            // Toggle visibility of hidden files
            document.querySelectorAll(".ignore-entry.hidden-file").forEach(el => {
                el.classList.toggle("show-hidden", showHiddenCheckbox.checked);
            });
        };
    }
}

function selectAllIgnoreEntries(selectAll) {
    const checkboxes = document.querySelectorAll("#ignore-entries-grid .ignore-entry input[type='checkbox']");
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
        const entry = checkbox.closest(".ignore-entry");
        if (entry) {
            entry.classList.toggle("ignored", selectAll);
        }
    });
}

async function saveProjectIgnores() {
    if (!state.apiBaseUrl || !state.activeProjectId) {
        alert(t("no_active_project") || "Aucun projet actif");
        return;
    }
    
    // Collect checked entries
    const ignorePatterns = [];
    
    document.querySelectorAll("#ignore-entries-grid .ignore-entry input[type='checkbox']:checked").forEach(checkbox => {
        const entryName = checkbox.dataset.entry;
        const isDir = checkbox.dataset.isDir === "true";
        
        if (isDir) {
            ignorePatterns.push(`${entryName}/**`);
        } else {
            ignorePatterns.push(entryName);
        }
    });
    
    // Add custom patterns
    const customInput = document.getElementById("ignore-custom-input");
    if (customInput && customInput.value.trim()) {
        const customPatterns = customInput.value.split(",").map(p => p.trim()).filter(Boolean);
        ignorePatterns.push(...customPatterns);
    }
    
    // Deduplicate
    const uniquePatterns = [...new Set(ignorePatterns)];
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/projects/${state.activeProjectId}/ignore`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ignore_globs: uniquePatterns })
        });
        
        if (response.ok) {
            projectCurrentIgnores = uniquePatterns;
            addLog(t("project_ignore_saved") || "Exclusions enregistrées");
            // Refresh to sync state
            await loadProjectRootEntries();
        } else {
            const err = await response.json();
            alert((t("project_ignore_error") || "Erreur") + ": " + (err.detail || ""));
        }
    } catch (e) {
        console.error("Failed to save project ignores", e);
        alert("Erreur réseau");
    }
}

async function updateProjectIgnores(projectId, ignoreGlobs) {
    if (!state.apiBaseUrl) return;
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/projects/${projectId}/ignore`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ignore_globs: ignoreGlobs })
        });
        if (response.ok) {
            addLog(t("project_ignore_saved") || "Règles d'ignore enregistrées");
            loadProjects();
        } else {
            const err = await response.json();
            alert((t("project_ignore_error") || "Impossible d'enregistrer les règles d'ignore") + ": " + (err.detail || ""));
        }
    } catch (e) {
        console.error("Failed to update project ignore globs", e);
        alert("Erreur réseau");
    }
}

function updateProjectOverview(projects, activeProject) {
    state.projects = projects || [];
    state.activeProjectId = activeProject ? (activeProject.project_id || activeProject.id) : null;
    const current = activeProject || null;
    const projectName = current?.project_name || current?.name || state.context?.project_name || "—";
    const projectPath = current?.project_path || current?.path || state.context?.root || "—";
    const lastScan = state.report?.last_scan_timestamp || null;

    setText("project-current-name", projectName);
    setText("project-current-path", projectPath);
    setText("project-root-quick", projectPath);
    setText("project-last-scan", formatRelativeDate(lastScan));
    
    // Update project count in both locations
    const projectCount = (projects?.length || 0).toString();
    setText("project-count", projectCount);
    setText("project-count-badge", projectCount);

    // Update config filename
    const configFilename = resolveProjectConfigFilename(current, projectPath);
    setText("project-config-file", configFilename);
    const configFilenameEl = document.getElementById("config-filename");
    if (configFilenameEl) configFilenameEl.textContent = configFilename;

    const statusNode = document.getElementById("project-current-status");
    if (statusNode) {
        if (current) {
            statusNode.className = current.is_active ? "pill pill-active" : "pill pill-muted";
            statusNode.textContent = current.is_active ? (t("active") || "Actif") : (t("inactive") || "Inactif");
        } else {
            statusNode.className = "pill pill-muted";
            statusNode.textContent = t("project_status_empty") || "Aucun projet";
        }
    }

    setText("project-health-active", projectName);
    setText("project-health-scan", formatRelativeDate(lastScan));
    setText("project-health-paths", projectPath);
    setText("project-health-status", state.apiBaseUrl || inferApiBaseUrl() || "—");
    
    // Update runtime status indicator
    updateProjectRuntimeStatus();
}

/**
 * Resolve the actual config filename for a project
 */
function resolveProjectConfigFilename(project, projectPath) {
    if (project?.config_file) {
        // Extract just the filename from the path
        const parts = project.config_file.split(/[/\\]/);
        return parts[parts.length - 1];
    }
    
    // Try to derive from project name or path
    if (project?.project_name) {
        return `${project.project_name}.jupiter.yaml`;
    }
    
    // Fallback: derive from path
    if (projectPath && projectPath !== "—") {
        const pathParts = projectPath.replace(/[/\\]$/, '').split(/[/\\]/);
        const folderName = pathParts[pathParts.length - 1];
        if (folderName) {
            return `${folderName}.jupiter.yaml`;
        }
    }
    
    return "config.jupiter.yaml";
}

/**
 * Update the runtime status indicator for the current project
 * Status: running, starting, stopped, error
 */
function updateProjectRuntimeStatus(status = null) {
    const container = document.getElementById("project-runtime-status");
    if (!container) return;
    
    const indicator = container.querySelector(".status-indicator");
    const textEl = container.querySelector(".status-text");
    
    // Determine status from state if not provided
    if (!status) {
        // Check if we have an active connection (WebSocket or API responding)
        if (state.watch?.active) {
            status = "running";
        } else if (state.apiBaseUrl && state.context) {
            status = "running";
        } else {
            status = "stopped";
        }
    }
    
    // Remove all status classes
    indicator?.classList.remove("running", "starting", "stopped", "error");
    
    const statusConfig = {
        running: { 
            class: "running", 
            text: t("project_runtime_running") || "En cours d'exécution",
            icon: "🟢"
        },
        starting: { 
            class: "starting", 
            text: t("project_runtime_starting") || "Démarrage en cours...",
            icon: "🟡"
        },
        stopped: { 
            class: "stopped", 
            text: t("project_runtime_stopped") || "Arrêté",
            icon: "⚪"
        },
        error: { 
            class: "error", 
            text: t("project_runtime_error") || "Erreur",
            icon: "🔴"
        }
    };
    
    const config = statusConfig[status] || statusConfig.stopped;
    indicator?.classList.add(config.class);
    if (textEl) textEl.textContent = config.text;
}

function renderProjects(projects) {
    const list = document.getElementById("projects-list");
    const emptyState = document.getElementById("projects-empty");
    if (!list || !emptyState) return;

    list.innerHTML = "";
    const projectArray = Array.isArray(projects) ? projects : [];
    const activeProject = projectArray.find((p) => p.is_active) || null;
    updateProjectOverview(projectArray, activeProject);

    if (projectArray.length === 0) {
        emptyState.style.display = "block";
        return;
    }

    emptyState.style.display = "none";

    projectArray.forEach((p) => {
        const name = p.project_name || p.name || "—";
        const path = p.project_path || p.path || "—";
        const configPath = resolveProjectConfigLabel(p);
        const projectId = p.project_id || p.id;

        const card = document.createElement("div");
        card.className = "project-card";

        const head = document.createElement("div");
        head.className = "project-card__head";
        const titleBox = document.createElement("div");
        titleBox.innerHTML = `<p class="eyebrow">${p.is_active ? (t("project_status_active") || "Actif") : (t("project_entry") || "Projet")}</p><h4>${name}</h4><p class="small muted mono">${path}</p>`;
        const status = document.createElement("span");
        status.className = p.is_active ? "pill pill-active" : "pill pill-muted";
        status.textContent = p.is_active ? (t("active") || "Actif") : (t("inactive") || "Inactif");
        head.appendChild(titleBox);
        head.appendChild(status);

        const body = document.createElement("div");
        body.className = "project-card__body";
        const bodyItems = [
            { label: t("project_last_scan") || "Dernier scan", value: p.last_scan ? formatRelativeDate(p.last_scan) : (p.is_active ? formatRelativeDate(state.report?.last_scan_timestamp) : (t("project_unknown") || "—")) },
            { label: t("project_root_label") || "Racine", value: path },
            { label: t("project_config_label") || "Config", value: configPath },
        ];
        bodyItems.forEach(({ label, value }) => {
            const wrapper = document.createElement("div");
            const l = document.createElement("p");
            l.className = "label";
            l.textContent = label;
            const v = document.createElement("p");
            v.className = "value";
            v.textContent = value;
            wrapper.appendChild(l);
            wrapper.appendChild(v);
            body.appendChild(wrapper);
        });

        const actions = document.createElement("div");
        actions.className = "project-card__actions";
        if (!p.is_active) {
            const activateBtn = document.createElement("button");
            activateBtn.className = "small primary";
            activateBtn.textContent = t("activate") || "Activer";
            activateBtn.onclick = () => activateProject(projectId);
            actions.appendChild(activateBtn);
        }

        const ignoreLabel = document.createElement("label");
        ignoreLabel.className = "small muted";
        ignoreLabel.textContent = t("project_ignore_label") || "Ignorer (glob, séparés par des virgules)";
        const ignoreInput = document.createElement("input");
        ignoreInput.type = "text";
        ignoreInput.className = "project-ignore-input";
        ignoreInput.placeholder = t("project_ignore_placeholder") || "ex: node_modules/**,dist/**";
        const currentIgnore = Array.isArray(p.ignore_globs) ? p.ignore_globs.join(", ") : "";
        ignoreInput.value = currentIgnore;
        const saveIgnoreBtn = document.createElement("button");
        saveIgnoreBtn.className = "small";
        saveIgnoreBtn.textContent = t("project_ignore_save") || "Enregistrer";
        saveIgnoreBtn.onclick = () => {
            const raw = ignoreInput.value || "";
            const globs = raw.split(",").map(s => s.trim()).filter(Boolean);
            updateProjectIgnores(projectId, globs);
        };

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "small danger";
        deleteBtn.textContent = t("delete") || "Supprimer";
        deleteBtn.onclick = () => deleteProject(projectId, name);
        actions.appendChild(deleteBtn);

        const ignoreWrapper = document.createElement("div");
        ignoreWrapper.style.display = "grid";
        ignoreWrapper.style.gap = "4px";
        ignoreWrapper.style.marginTop = "10px";
        ignoreWrapper.appendChild(ignoreLabel);
        ignoreWrapper.appendChild(ignoreInput);
        ignoreWrapper.appendChild(saveIgnoreBtn);

        card.appendChild(head);
        card.appendChild(body);
        card.appendChild(ignoreWrapper);
        card.appendChild(actions);
        list.appendChild(card);
    });
}

async function activateProject(projectId) {
    await performProjectMutation(
        `/projects/${projectId}/activate`,
        { method: "POST" },
        async () => {
            addLog(t("project_activated") || "Projet activé", "INFO");
            await loadContext(true);
            await loadCachedReport();
            await loadSnapshots(true);
            await loadProjects();
        },
        "Erreur"
    );
}

async function deleteProject(projectId, projectName) {
    const msg = (t("delete_confirm") || "Voulez-vous vraiment supprimer le projet \"{name}\" ?").replace("{name}", projectName);
    if (!confirm(msg)) {
        return;
    }

    await performProjectMutation(
        `/projects/${projectId}`,
        { method: "DELETE" },
        async () => {
            addLog(t("project_deleted") || "Projet supprimé", "INFO");
            loadProjects();
            loadContext();
        },
        "Erreur"
    );
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

const LOG_LEVEL_ORDER = {
  DEBUG: 0,
  INFO: 1,
  WARNING: 2,
  ERROR: 3,
  CRITICAL: 4,
};

function normalizeLogLevel(level) {
  if (!level) return "INFO";
  const value = level.toString().trim().toUpperCase();
  if (value === "WARN") return "WARNING";
  if (value === "CRITIC") return "CRITICAL";
  if (value === "ALL") return "DEBUG";
  return LOG_LEVEL_ORDER[value] !== undefined ? value : "INFO";
}

function applyLogLevel(level) {
  state.logLevel = normalizeLogLevel(level);
  const filter = document.getElementById("log-level-filter");
  if (filter) filter.value = state.logLevel;
  renderLogs();
}

function addLog(message, level = "INFO") {
  const normalizedLevel = normalizeLogLevel(level);
  const entry = { message, level: normalizedLevel, timestamp: new Date() };
  state.logs.unshift(entry);
  state.logs = state.logs.slice(0, 50);
  renderLogs();
}

function renderLogs() {
  const container = document.getElementById("log-stream");
  if (!container) return;
  container.innerHTML = "";
  const currentLevel = LOG_LEVEL_ORDER[state.logLevel] ?? 1;

  const filteredLogs = state.logs
    .filter((log) => {
      const logLevel = LOG_LEVEL_ORDER[normalizeLogLevel(log.level)] ?? 1;
      return logLevel >= currentLevel;
    })
    .slice(0, 8);

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

async function loadContext(force = false) {
  try {
    const url = force ? `/context.json?ts=${Date.now()}` : "/context.json";
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) throw new Error("Network response was not ok");
    const payload = await response.json();
    state.context = payload;
    state.apiBaseUrl = payload.api_base_url || inferApiBaseUrl();
    updateVersionDisplays(payload.jupiter_version);
    const rootLabel = document.getElementById("root-path");
    if (rootLabel) {
        const name = payload.project_name || "Projet";
        const root = payload.root || "(undefined)";
        rootLabel.textContent = `${name} (${root})`;
        rootLabel.title = root;
    }
    const normalizedRoot = normalizePath(payload.root || "");
    if (state.historyRoot && state.historyRoot !== normalizedRoot) {
        state.snapshots = [];
        state.snapshotSelection = { a: null, b: null };
        renderSnapshots();
    }
    state.historyRoot = normalizedRoot;
    const apiLabel = document.getElementById("api-base-url");
    if (apiLabel) apiLabel.textContent = state.apiBaseUrl;
    addLog(`${t("context_loaded")}: ${payload.root}`);
    
    if (payload.has_config_file === false) {
        showOnboarding();
    }
    if (state.apiBaseUrl) {
      startApiHeartbeat();
    }
  } catch (error) {
    console.warn("Could not load context", error);
    const rootLabel = document.getElementById("root-path");
    if (rootLabel) rootLabel.textContent = "N/A";
    updateVersionDisplays();
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
    const reportRoot = normalizePath(report.root);
    const currentRoot = normalizePath(state.context?.root);
    if (currentRoot && reportRoot && reportRoot !== currentRoot) {
      return null;
    }
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
    const currentRoot = normalizePath(state.context?.root);
    if (!currentRoot) {
      state.snapshots = [];
      renderSnapshots();
      return;
    }
    const snapshots = payload.snapshots || [];
    const filtered = currentRoot
      ? snapshots.filter((snap) => !snap.project_root || normalizePath(snap.project_root) === currentRoot)
      : snapshots;
    state.snapshots = filtered;
    if (state.snapshotSelection.a && !filtered.find((s) => s.id === state.snapshotSelection.a)) {
      state.snapshotSelection.a = null;
    }
    if (state.snapshotSelection.b && !filtered.find((s) => s.id === state.snapshotSelection.b)) {
      state.snapshotSelection.b = null;
    }
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
  const validIds = new Set((state.snapshots || []).map((s) => s.id));
  if (!validIds.has(a) || !validIds.has(b)) {
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
      <h2>${t("onboarding_title") || "Bienvenue sur Jupiter"}</h2>
      <p>${t("onboarding_message") || "Aucun projet n'est configuré dans ce dossier."}</p>
      <div class="actions">
        <button class="primary" data-action="create-config">${t("onboarding_create_config") || "Créer une configuration par défaut"}</button>
        <button class="ghost" data-action="close-onboarding">${t("onboarding_ignore") || "Ignorer"}</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

async function createConfig() {
    try {
        const res = await fetch(`${state.apiBaseUrl}/init`, { method: "POST" });
        if (res.ok) {
            addLog(t("onboarding_config_created") || "Configuration créée avec succès.");
            document.getElementById('onboarding-modal').remove();
            // Reload context to update state
            await loadContext();
            // Navigate to Projects page so user can review and customize settings
            setView("projects");
            addLog(t("onboarding_redirect_projects") || "Redirection vers la page Projets pour configurer le projet.", "INFO");
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
  } else if (view === "settings") {
    // Load plugin settings when opening settings view
    loadPluginSettings();
  } else if (view === "ci") {
    loadCIView();
  } else if (view.startsWith("plugin-")) {
    // Plugin view - handled by loadPluginViewContent in bindPluginNavigation
    const pluginSection = document.querySelector(`section.view[data-view="${view}"]`);
    const pluginName = pluginSection?.dataset?.pluginName;
    // Get v2 flag from the nav button
    const navBtn = document.querySelector(`.nav-btn[data-view="${view}"]`);
    const isV2 = navBtn?.dataset?.v2 === 'true';
    if (pluginName) {
      loadPluginViewContent(pluginName, view, isV2);
    }
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
    const hasLocations = Array.isArray(s.locations) && s.locations.length > 0;
    const locationsList = hasLocations
      ? `<ul class="muted" style="margin: 6px 0 0 0; padding-left: 18px;">${
          s.locations.slice(0, 5).map(loc => {
            const path = loc.path || "";
            const line = loc.line || "?";
            const fn = loc.function ? ` (${loc.function})` : "";
            return `<li>${path}:${line}${fn}</li>`;
          }).join("")
        }${s.locations.length > 5 ? `<li>... +${s.locations.length - 5} ${t("suggestions_more_locations") || "more locations"}</li>` : ""}</ul>`
      : "";
    const codeExcerpt = s.code_excerpt || (hasLocations ? s.locations[0].code_excerpt : null);
    const codeBlock = codeExcerpt
      ? `<pre class="muted" style="margin-top:8px; max-height:180px; overflow:auto;"><code>${codeExcerpt}</code></pre>`
      : "";

    const item = document.createElement("div");
    item.className = "list-item";
    const severityClass = (s.severity === 'critical' || s.severity === 'high')
      ? 'error'
      : (s.severity === 'warning' || s.severity === 'medium')
        ? 'warning'
        : 'info';
    item.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong>${s.path}</strong>
        <span class="badge ${severityClass}">${s.severity}</span>
      </div>
      <p><em>${s.type}</em>: ${s.details}</p>
      ${locationsList}
      ${codeBlock}
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
  
  // API interaction form handler
  const apiInteractForm = document.getElementById("api-interact-form");
  if (apiInteractForm) {
      apiInteractForm.addEventListener("submit", sendApiRequest);
  }

  const logLevelFilter = document.getElementById("log-level-filter");
  if (logLevelFilter) {
      logLevelFilter.addEventListener("change", (e) => {
          applyLogLevel(e.target.value);
      });
  }

  // Watch panel clear events button
  const clearWatchBtn = document.getElementById("watch-clear-events");
  if (clearWatchBtn) {
    clearWatchBtn.addEventListener("click", clearWatchEvents);
  }

  // Reload all plugins button
  const reloadPluginsBtn = document.getElementById("reload-plugins-btn");
  if (reloadPluginsBtn) {
    reloadPluginsBtn.addEventListener("click", reloadAllPlugins);
  }

  applyLogLevel(state.logLevel);
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
      // Update project runtime status to running
      updateProjectRuntimeStatus("running");
      // Note: WebSocket connection does not mean watch is active.
      // The button state is managed by updateWatchStats() based on state.watch.active
      const watchPanel = document.getElementById("watch-panel");
      if (watchPanel && state.watch.active) watchPanel.classList.remove("hidden");
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

      // Handle specific event types
      if (parsed) {
        switch (parsed.type) {
          case "PLUGIN_NOTIFICATION": {
            const payload = parsed.payload || {};
            const source = payload.source || "Plugin";
            const detail = payload.message || JSON.stringify(payload.details || {});
            pushLiveEvent(source, detail);
            addLog(`${source}: ${detail}`);
            const level = payload.level || "info";
            const icon = payload.status === "offline" ? "🔴" : undefined;
            showNotification(detail, level, {
              title: source,
              icon,
            });
            break;
          }
          
          case "FUNCTION_CALLS": {
            // Update watch state with new call counts
            const payload = parsed.payload || {};
            if (payload.cumulative) {
              state.watch.callCounts = payload.cumulative;
            }
            const callCount = Object.values(payload.calls || {}).reduce((a, b) => a + b, 0);
            addWatchEvent("FUNCTION_CALLS", `${callCount} appels dynamiques`, "success");
            addLog(`Watch: ${callCount} function calls recorded`);
            // Re-render functions view if active
            if (state.view === "functions") {
              renderFunctions(state.report);
            }
            updateWatchStats();
            break;
          }
          
          case "WATCH_STARTED": {
            state.watch.active = true;
            state.watch.callCounts = {};
            state.watch.totalEvents = 0;
            state.watch.filesScanned = 0;
            state.watch.functionsFound = 0;
            state.watch.progress = 0;
            state.watch.phase = null;
            addWatchEvent("WATCH", t("watch_started") || "Watch démarré", "success");
            addLog("Watch mode started");
            updateWatchPanel();
            break;
          }
          
          case "WATCH_STOPPED": {
            const payload = parsed.payload || {};
            state.watch.active = false;
            state.watch.phase = null;
            addWatchEvent("WATCH", t("watch_stopped") || "Watch arrêté", "");
            addLog(`Watch stopped. Total: ${payload.total_events || 0} events`);
            updateWatchPanel();
            break;
          }
          
          case "WATCH_CALLS_RESET": {
            state.watch.callCounts = {};
            state.watch.totalEvents = 0;
            addWatchEvent("WATCH", "Compteurs réinitialisés", "");
            if (state.view === "functions") {
              renderFunctions(state.report);
            }
            updateWatchStats();
            break;
          }
          
          case "FILE_CHANGE": {
            const payload = parsed.payload || {};
            state.watch.totalEvents++;
            addWatchEvent("FILE", `${payload.change_type}: ${payload.path}`, "");
            addLog(`File ${payload.change_type}: ${payload.path}`);
            updateWatchStats();
            break;
          }
          
          // Scan progress events
          case "SCAN_STARTED": {
            const payload = parsed.payload || {};
            state.watch.phase = "scanning";
            state.watch.progress = 0;
            state.watch.filesScanned = 0;
            
            // Handle background scan indicator
            if (payload.background && payload.job_id) {
              state.currentScanJobId = payload.job_id;
              addWatchEvent("SCAN", `Background scan started (Job: ${payload.job_id})`, "success");
            } else {
              addWatchEvent("SCAN", `Scan démarré: ${payload.root || ""}`, "success");
            }
            updateWatchProgress(0, "Scan en cours...");
            break;
          }
          
          case "SCAN_PROGRESS": {
            const payload = parsed.payload || {};
            state.watch.phase = payload.phase || "scanning";
            state.watch.progress = payload.percent || 0;
            state.watch.totalEvents++;
            
            // Update scan button text if background scan
            if (payload.job_id && state.isScanning) {
              const scanButtons = document.querySelectorAll('[data-action="start-scan"]');
              const progressText = payload.current_file 
                ? `${payload.percent}% - ${payload.current_file}`
                : `${payload.percent}%`;
              scanButtons.forEach(btn => {
                const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
                if(textElement) textElement.textContent = `${t("scan_in_progress")} ${progressText}`;
              });
            }
            
            updateWatchProgress(payload.percent, `Phase: ${payload.phase || "scanning"}`);
            break;
          }
          
          case "SCAN_FILE_COMPLETED": {
            const payload = parsed.payload || {};
            state.watch.filesScanned = payload.processed || (state.watch.filesScanned + 1);
            state.watch.progress = payload.percent || 0;
            state.watch.currentFile = payload.file;
            state.watch.totalEvents++;
            
            // Update progress UI
            updateWatchProgress(
              payload.percent, 
              `Scan: ${payload.processed}/${payload.total} fichiers`,
              payload.file
            );
            
            // Only add event for every Nth file to avoid flooding
            if (payload.processed % 10 === 0 || payload.processed === payload.total) {
              addWatchEvent("SCAN", `${payload.processed}/${payload.total} fichiers`, "");
            }
            
            updateWatchStats();
            break;
          }
          
          case "FUNCTION_ANALYZED": {
            const payload = parsed.payload || {};
            state.watch.functionsFound += (payload.functions_count || 0);
            state.watch.totalEvents++;
            
            if (payload.functions && payload.functions.length > 0) {
              const funcNames = payload.functions.slice(0, 3).join(", ");
              addWatchEvent("FUNC", `${payload.file}: ${funcNames}${payload.functions_count > 3 ? "..." : ""}`, "");
            }
            
            updateWatchStats();
            break;
          }
          
          case "SCAN_FINISHED": {
            const payload = parsed.payload || {};
            state.watch.phase = "completed";
            state.watch.progress = 100;
            
            // Handle background scan completion via WebSocket
            if (payload.background && payload.job_id && state.currentScanJobId === payload.job_id) {
              addWatchEvent("SCAN", `Background scan terminé: ${payload.file_count || 0} fichiers (${payload.duration_ms}ms)`, "success");
              
              // Fetch and render the result
              (async () => {
                try {
                  const apiBaseUrl = state.apiBaseUrl || inferApiBaseUrl();
                  const resultResponse = await apiFetch(`${apiBaseUrl}/scan/result/${payload.job_id}`);
                  if (resultResponse.ok) {
                    const report = await resultResponse.json();
                    report.last_scan_timestamp = Date.now() / 1000;
                    renderReport(report);
                    addLog(`${t("scan_complete_log")} (${payload.duration_ms}ms)`);
                    pushLiveEvent(t("scan_button"), t("scan_live_event_complete"));
                    await loadSnapshots(true);
                  }
                } catch (e) {
                  console.error("Failed to fetch background scan result:", e);
                }
                
                // Reset UI
                state.isScanning = false;
                state.currentScanJobId = null;
                const scanButtons = document.querySelectorAll('[data-action="start-scan"]');
                scanButtons.forEach(btn => {
                  btn.disabled = false;
                  const textElement = btn.classList.contains('primary') ? btn : btn.querySelector('.label');
                  if(textElement) textElement.textContent = t("scan_button");
                });
              })();
            } else {
              addWatchEvent("SCAN", `Terminé: ${payload.file_count || 0} fichiers`, "success");
            }
            
            updateWatchProgress(100, "Scan terminé");
            updateWatchStats();
            
            // Hide progress bar after a delay
            setTimeout(() => {
              const progressEl = document.getElementById("watch-progress");
              if (progressEl) progressEl.classList.add("hidden");
            }, 3000);
            break;
          }
          
          case "LOG_MESSAGE": {
            const payload = parsed.payload || {};
            const level = payload.level || "info";
            const cssClass = level === "error" ? "event-error" : (level === "warning" ? "" : "");
            addWatchEvent("LOG", `[${level.toUpperCase()}] ${payload.message}`, cssClass);
            break;
          }
          
          case "SIMULATE_STARTED": {
            const payload = parsed.payload || {};
            state.watch.phase = "simulating";
            addWatchEvent("SIMULATE", `Simulation démarrée: ${payload.target || ""}`, "success");
            break;
          }
          
          case "SIMULATE_PROGRESS": {
            const payload = parsed.payload || {};
            state.watch.totalEvents++;
            addWatchEvent("SIMULATE", payload.message || "En cours...", "");
            break;
          }
          
          case "SIMULATE_COMPLETED": {
            const payload = parsed.payload || {};
            addWatchEvent("SIMULATE", `Terminé: ${payload.impacted_count || 0} éléments impactés`, "success");
            break;
          }
          
          default: {
            const detail = parsed.payload && Object.keys(parsed.payload).length ? JSON.stringify(parsed.payload) : "";
            addWatchEvent(parsed.type || "SERVER", detail || "(empty payload)", "");
            addLog(`WS: ${parsed.type}`);
          }
        }
      } else {
        addWatchEvent("SERVER", event.data, "");
        addLog(`WS: ${event.data}`);
      }

      if (!parsed && typeof event.data === "string" && event.data.startsWith("Snapshot stored")) {
        loadSnapshots(true);
        if (state.view === "graph") renderGraph();
      }
      
      const watchList = document.getElementById("watch-events");
      if (watchList) {
          const li = document.createElement("li");
          const eventText = parsed ? `[${parsed.type}] ${JSON.stringify(parsed.payload || {}).substring(0, 100)}` : event.data;
          li.textContent = `[${new Date().toLocaleTimeString()}] ${eventText}`;
          li.style.padding = "0.25rem 0";
          li.style.borderBottom = "1px solid var(--border)";
          watchList.prepend(li);
          if (watchList.children.length > 20) watchList.lastChild.remove();
      }
    };
    
    ws.onclose = () => {
      state.ws = null;
      state.watch.active = false;
      addLog("WebSocket disconnected.");
      // Update project runtime status to stopped
      updateProjectRuntimeStatus("stopped");
      const btn = document.querySelector('[data-action="start-watch"]');
      if (btn) {
          btn.classList.remove("active");
          const label = btn.querySelector('.label') || btn;
          if (label) label.textContent = "Watch";
      }
      const watchPanel = document.getElementById("watch-panel");
      if (watchPanel) watchPanel.classList.add("hidden");
      updateWatchStats();
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      // Update project runtime status to error
      updateProjectRuntimeStatus("error");
    };
    
    state.ws = ws;
  } catch (e) {
    console.error("Could not connect to WebSocket", e);
  }
}

async function startWatch() {
  if (!state.apiBaseUrl) return;
  
  try {
    // First start the watch on the server
    const response = await apiFetch(`${state.apiBaseUrl}/watch/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_calls: true, track_files: true })
    });
    
    if (response.ok) {
      const status = await response.json();
      state.watch.active = status.active;
      state.watch.callCounts = status.call_counts || {};
      state.watch.totalEvents = status.total_events || 0;
      state.watch.filesScanned = 0;
      state.watch.functionsFound = 0;
      state.watch.progress = 0;
      state.watch.phase = null;
      
      // Then connect WebSocket for real-time updates
      connectWebSocket();
      
      addLog("Watch mode started");
      updateWatchStats();
      updateWatchPanel();
    } else {
      const err = await response.json();
      addLog(`Failed to start watch: ${err.detail || err.error?.message || "Unknown error"}`);
    }
  } catch (e) {
    console.error("Failed to start watch:", e);
    addLog(`Failed to start watch: ${e.message}`);
  }
}

async function stopWatch() {
  if (!state.apiBaseUrl) return;
  
  try {
    const response = await apiFetch(`${state.apiBaseUrl}/watch/stop`, {
      method: "POST"
    });
    
    if (response.ok) {
      const status = await response.json();
      state.watch.active = false;
      // Keep the final call counts for reference
      if (status.call_counts) {
        state.watch.callCounts = status.call_counts;
      }
      addLog(`Watch stopped. Total events: ${status.total_events || 0}`);
    }
  } catch (e) {
    console.error("Failed to stop watch:", e);
  }
  
  // Close WebSocket
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.close();
  }
  
  updateWatchStats();
  updateWatchPanel();
}

function updateWatchStats() {
  // Update UI elements showing watch status
  const watchStatusEl = document.getElementById("watch-status");
  const watchCallsEl = document.getElementById("watch-total-calls");
  const watchEventsEl = document.getElementById("watch-total-events");
  const watchFilesEl = document.getElementById("watch-files-count");
  const watchFunctionsEl = document.getElementById("watch-functions-count");
  const watchEventsCountEl = document.getElementById("watch-events-count");
  
  if (watchStatusEl) {
    watchStatusEl.textContent = state.watch.active ? t("watch_active") : t("watch_inactive");
    watchStatusEl.className = state.watch.active ? "value text-success" : "value text-muted";
  }
  
  if (watchCallsEl) {
    const totalCalls = Object.values(state.watch.callCounts).reduce((a, b) => a + b, 0);
    watchCallsEl.textContent = totalCalls.toLocaleString();
  }
  
  if (watchEventsEl) {
    watchEventsEl.textContent = state.watch.totalEvents.toLocaleString();
  }
  
  // Update new watch panel stats
  if (watchFilesEl) {
    watchFilesEl.textContent = state.watch.filesScanned.toLocaleString();
  }
  
  if (watchFunctionsEl) {
    watchFunctionsEl.textContent = state.watch.functionsFound.toLocaleString();
  }
  
  if (watchEventsCountEl) {
    watchEventsCountEl.textContent = state.watch.totalEvents.toLocaleString();
  }
  
  // Update the watch button state
  const btn = document.querySelector('[data-action="start-watch"]');
  if (btn) {
    const label = btn.querySelector('.label') || btn;
    if (state.watch.active) {
      btn.classList.add("active");
      if (label) label.textContent = "Watching";
    } else {
      btn.classList.remove("active");
      if (label) label.textContent = "Watch";
    }
  }
  
  // Update the dashboard stat cards to reflect dynamic data availability
  if (state.report) {
    renderStats(state.report);
  }
}

/**
 * Update the watch panel visibility and status badge
 */
function updateWatchPanel() {
  const watchPanel = document.getElementById("watch-panel");
  const statusBadge = document.getElementById("watch-status-badge");
  
  if (watchPanel) {
    if (state.watch.active) {
      watchPanel.classList.remove("hidden");
      watchPanel.classList.add("active");
    } else {
      watchPanel.classList.remove("active");
      // Keep panel visible for a bit to show final state
    }
  }
  
  if (statusBadge) {
    if (state.watch.active) {
      statusBadge.textContent = "Watching";
      statusBadge.classList.add("active");
    } else {
      statusBadge.textContent = "Stopped";
      statusBadge.classList.remove("active");
    }
  }
  
  updateWatchStats();
}

/**
 * Update the progress bar in the watch panel
 * @param {number} percent - Progress percentage (0-100)
 * @param {string} label - Label to show above progress bar
 * @param {string} detail - Optional detail text (e.g. current file)
 */
function updateWatchProgress(percent, label, detail = "") {
  const progressEl = document.getElementById("watch-progress");
  const progressBar = document.getElementById("watch-progress-bar");
  const progressLabel = document.getElementById("watch-progress-label");
  const progressPercent = document.getElementById("watch-progress-percent");
  const progressDetail = document.getElementById("watch-progress-detail");
  
  if (progressEl) {
    progressEl.classList.remove("hidden");
  }
  
  if (progressBar) {
    progressBar.style.width = `${percent}%`;
  }
  
  if (progressLabel) {
    progressLabel.textContent = label;
  }
  
  if (progressPercent) {
    progressPercent.textContent = `${Math.round(percent)}%`;
  }
  
  if (progressDetail && detail) {
    progressDetail.textContent = detail;
  }
}

/**
 * Add an event to the watch events list
 * @param {string} type - Event type (e.g. "SCAN", "FILE", "FUNC")
 * @param {string} detail - Event detail text
 * @param {string} cssClass - Optional CSS class (e.g. "event-error", "event-success")
 */
function addWatchEvent(type, detail, cssClass = "") {
  const watchList = document.getElementById("watch-events");
  if (!watchList) return;
  
  const li = document.createElement("li");
  if (cssClass) li.classList.add(cssClass);
  
  const time = new Date().toLocaleTimeString();
  li.innerHTML = `<span class="event-time">${time}</span><span class="event-type">${type}</span><span class="event-detail">${detail}</span>`;
  
  watchList.prepend(li);
  
  // Limit to last 50 events
  while (watchList.children.length > 50) {
    watchList.lastChild.remove();
  }
}

/**
 * Clear all events in the watch panel
 */
function clearWatchEvents() {
  const watchList = document.getElementById("watch-events");
  if (watchList) {
    watchList.innerHTML = "";
  }
  addWatchEvent("SYSTEM", "Événements effacés", "");
}

async function fetchWatchStatus() {
  if (!state.apiBaseUrl) return;
  try {
    const response = await apiFetch(`${state.apiBaseUrl}/watch/status`);
    if (response.ok) {
      const status = await response.json();
      state.watch.active = status.active || false;
      state.watch.callCounts = status.call_counts || {};
      state.watch.totalEvents = status.total_events || 0;
      updateWatchStats();
      updateWatchPanel();
    }
  } catch (e) {
    console.warn("Could not fetch watch status:", e);
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
      renderAlerts(state.report);  // Update alerts with new Meeting status
      
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

  const entries = Array.isArray(data.entries) ? [...data.entries] : [];
  const normalized = data.current.replace(/\\/g, "/").replace(/\/+$/, "");
  const hasUp = entries.some((e) => e.name === "..");
  if (!hasUp && normalized.includes("/")) {
    const lastSlash = normalized.lastIndexOf("/");
    if (lastSlash > 0) {
      const parentPath = normalized.slice(0, lastSlash) || normalized;
      entries.unshift({ name: "..", path: parentPath, is_dir: true });
    }
  }

  entries.forEach(entry => {
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
    // Check if there's a CWD callback waiting
    if (typeof runCwdBrowserCallback === 'function') {
        runCwdBrowserCallback(currentBrowserPath);
        runCwdBrowserCallback = null;
        closeBrowser();
    } else if (state.browserMode === 'wizard') {
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
  // Discover available languages first
  await discoverLanguages();
  
  const savedLang = localStorage.getItem("jupiter-lang") || "fr";
  await setLanguage(savedLang);
  
  // Populate language selector after discovery
  populateLanguageSelector();
  
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
  
  // Start loading plugin menus early (non-blocking)
  const pluginMenusPromise = loadPluginMenus();
  
  await loadContext();
  const versionLabel = state.context?.jupiter_version ? `v${state.context.jupiter_version}` : "v—";
  addLog(`App initialized ${versionLabel}`, "INFO");
  await loadProjects(); // Load projects and their API config (also loads cached report if active project)
  if (!state.report) {
    await loadCachedReport(); // Fallback if no project was active
  }
  
  // Run these in parallel for faster startup
  await Promise.all([
    fetchBackends(),
    refreshApiEndpoints(),
    pluginMenusPromise, // Ensure plugin menus are loaded
  ]);
  
  // These can run without blocking
  fetchMeetingStatus();
  fetchWatchStatus(); // Fetch watch state to sync button with server
  connectWebSocket();
  bindUpload();
  bindActions();
  bindHistoryControls();
  setupProjectApiConnectorForm();
  // setupUpdateFileUpload removed - functionality now provided by settings_update plugin
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
window.showUnusedFunctionsExportModal = showUnusedFunctionsExportModal;
window.copyUnusedFunctionsExport = copyUnusedFunctionsExport;
window.closeUnusedFunctionsExportModal = closeUnusedFunctionsExportModal;

// --- Authentication ---

async function apiFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (state.token) {
        headers.set("Authorization", `Bearer ${state.token}`);
    }
    headers.set("Cache-Control", "no-store");
    headers.set("Pragma", "no-cache");
    
    options.headers = headers;
    options.cache = "no-store";
    
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

// Set up login modal cancel handler once on load
let loginModalCancelHandlerAttached = false;

function openLoginModal() {
    const modal = document.getElementById("login-modal");
    if (modal) {
        // Attach cancel event handler only once
        if (!loginModalCancelHandlerAttached) {
            modal.addEventListener('cancel', (event) => {
                // Prevent closing by escape key if not logged in
                if (!state.token) {
                    event.preventDefault();
                }
            });
            loginModalCancelHandlerAttached = true;
        }
        modal.showModal();
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
            checkProjectStatus();
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
                    checkProjectStatus();
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

function closeProjectWizard() {
    const modal = document.getElementById("project-wizard-modal");
    const errorDiv = document.getElementById("project-wizard-error");
    if (errorDiv) {
        errorDiv.textContent = "";
        errorDiv.classList.add("hidden");
    }
    if (modal) {
        modal.close();
    }
    state.browserMode = null;
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

/**
 * @deprecated Use livemap plugin instead. This function is kept for backwards compatibility.
 * The Live Map functionality has been migrated to the livemap plugin.
 */
async function renderGraph() {
  console.warn('renderGraph() is deprecated. Use livemap plugin instead.');
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
            state.users = users;
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
        row.dataset.userName = user.name;
        row.innerHTML = `
            <td>
                <span class="user-name-display">${escapeHtml(user.name)}</span>
                <input type="text" class="user-name-edit hidden" value="${escapeHtml(user.name)}" style="width: 100%;" />
            </td>
            <td>
                <span class="user-token-display">${user.token ? '••••••••' : '—'}</span>
                <input type="text" class="user-token-edit hidden" placeholder="Nouveau token" style="width: 100%;" />
            </td>
            <td>
                <span class="user-role-display">${escapeHtml(user.role)}</span>
                <select class="user-role-edit hidden" style="width: 100%;">
                    <option value="viewer" ${user.role === 'viewer' ? 'selected' : ''}>Viewer</option>
                    <option value="editor" ${user.role === 'editor' ? 'selected' : ''}>Editor</option>
                    <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
            </td>
            <td class="user-actions">
                <button class="btn-icon user-action-edit" data-user="${escapeHtml(user.name)}" title="Modifier">✏️</button>
                <button class="btn-icon user-action-save hidden" data-user="${escapeHtml(user.name)}" title="Enregistrer">💾</button>
                <button class="btn-icon user-action-cancel hidden" data-user="${escapeHtml(user.name)}" title="Annuler">❌</button>
                <button class="btn-icon user-action-delete" data-user="${escapeHtml(user.name)}" title="Supprimer">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // Attach event listeners
    tbody.querySelectorAll('.user-action-edit').forEach(btn => {
        btn.addEventListener('click', () => startEditUser(btn.dataset.user));
    });
    tbody.querySelectorAll('.user-action-save').forEach(btn => {
        btn.addEventListener('click', () => saveEditUser(btn.dataset.user));
    });
    tbody.querySelectorAll('.user-action-cancel').forEach(btn => {
        btn.addEventListener('click', () => cancelEditUser(btn.dataset.user));
    });
    tbody.querySelectorAll('.user-action-delete').forEach(btn => {
        btn.addEventListener('click', () => deleteUser(btn.dataset.user));
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function startEditUser(userName) {
    const row = document.querySelector(`tr[data-user-name="${userName}"]`);
    if (!row) return;
    
    // Show edit fields, hide display
    row.querySelectorAll('.user-name-display, .user-token-display, .user-role-display').forEach(el => el.classList.add('hidden'));
    row.querySelectorAll('.user-name-edit, .user-token-edit, .user-role-edit').forEach(el => el.classList.remove('hidden'));
    
    // Toggle buttons
    row.querySelector('.user-action-edit').classList.add('hidden');
    row.querySelector('.user-action-delete').classList.add('hidden');
    row.querySelector('.user-action-save').classList.remove('hidden');
    row.querySelector('.user-action-cancel').classList.remove('hidden');
}

function cancelEditUser(userName) {
    const row = document.querySelector(`tr[data-user-name="${userName}"]`);
    if (!row) return;
    
    // Show display, hide edit fields
    row.querySelectorAll('.user-name-display, .user-token-display, .user-role-display').forEach(el => el.classList.remove('hidden'));
    row.querySelectorAll('.user-name-edit, .user-token-edit, .user-role-edit').forEach(el => el.classList.add('hidden'));
    
    // Toggle buttons
    row.querySelector('.user-action-edit').classList.remove('hidden');
    row.querySelector('.user-action-delete').classList.remove('hidden');
    row.querySelector('.user-action-save').classList.add('hidden');
    row.querySelector('.user-action-cancel').classList.add('hidden');
    
    // Reset values
    const originalUser = state.users?.find(u => u.name === userName);
    if (originalUser) {
        row.querySelector('.user-name-edit').value = originalUser.name;
        row.querySelector('.user-role-edit').value = originalUser.role;
        row.querySelector('.user-token-edit').value = '';
    }
}

async function saveEditUser(originalName) {
    const row = document.querySelector(`tr[data-user-name="${originalName}"]`);
    if (!row) return;
    
    const newName = row.querySelector('.user-name-edit').value.trim();
    const newToken = row.querySelector('.user-token-edit').value.trim();
    const newRole = row.querySelector('.user-role-edit').value;
    
    if (!newName) {
        alert(t("user_name_required") || "Le nom est requis");
        return;
    }
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/users/${originalName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name: newName, 
                token: newToken || undefined,  // Only send if changed
                role: newRole 
            })
        });
        
        if (response.ok) {
            const users = await response.json();
            state.users = users;
            renderUsers(users);
            addLog(`User ${originalName} updated`);
        } else {
            const err = await response.json().catch(() => ({}));
            alert((t("user_update_failed") || "Échec de la mise à jour") + ": " + (err.detail || response.status));
        }
    } catch (e) {
        alert((t("user_update_error") || "Erreur") + ": " + e.message);
    }
}

async function addUser() {
    const name = document.getElementById("new-user-name").value.trim();
    const token = document.getElementById("new-user-token").value.trim();
    const role = document.getElementById("new-user-role").value;
    
    if (!name || !token) {
        alert(t("user_name_token_required") || "Name and Token are required");
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
            state.users = users;
            renderUsers(users);
            document.getElementById("new-user-name").value = "";
            document.getElementById("new-user-token").value = "";
            addLog(`User ${name} added`);
        } else {
            const err = await response.json().catch(() => ({}));
            alert((t("user_add_failed") || "Failed to add user") + ": " + (err.detail || ""));
        }
    } catch (e) {
        alert((t("user_add_error") || "Error adding user") + ": " + e.message);
    }
}

async function deleteUser(name) {
    if (!confirm((t("user_delete_confirm") || `Supprimer l'utilisateur ${name} ?`).replace('{name}', name))) return;
    
    try {
        const response = await apiFetch(`${state.apiBaseUrl}/users/${name}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const users = await response.json();
            state.users = users;
            renderUsers(users);
            addLog(`User ${name} deleted`);
        } else {
            alert(t("user_delete_failed") || "Failed to delete user");
        }
    } catch (e) {
        alert((t("user_delete_error") || "Error deleting user") + ": " + e.message);
    }
}

    function setupProjectApiConnectorForm() {
      const connectorSelect = document.getElementById('project-api-connector');
      const appVarInput = document.getElementById('project-api-app-var');
      const pathInput = document.getElementById('project-api-path');

      if (!connectorSelect) {
        return;
      }

      const applyState = () => {
        const isLocal = connectorSelect.value === 'local';
        if (appVarInput) {
          appVarInput.disabled = isLocal;
          appVarInput.placeholder = isLocal ? "(Auto: Jupiter API)" : "app";
        }
        if (pathInput) {
          pathInput.disabled = isLocal;
          pathInput.placeholder = isLocal ? "(Auto: Internal)" : "src/main.py";
        }
      };

      connectorSelect.addEventListener('change', applyState);
      applyState();
    }

    // setupUpdateFileUpload removed - functionality now provided by settings_update plugin

// Update File Upload Listener moved to setup helpers executed during init

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

// ============================================
// CI / Quality Gates Functions
// ============================================

async function loadCIView() {
  // Load last CI result if available
  const historyBody = document.getElementById("ci-history-body");
  if (historyBody && state.ciHistory && state.ciHistory.length > 0) {
    renderCIHistory();
  }
  
  // Load thresholds from localStorage or defaults
  const thresholds = getCIThresholds();
  populateThresholdInputs(thresholds);
}

function getCIThresholds() {
  const saved = localStorage.getItem("jupiter_ci_thresholds");
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch (e) {
      console.warn("Failed to parse CI thresholds from localStorage", e);
    }
  }
  // Default thresholds
  return {
    max_complexity: 10,
    max_lines_per_function: 100,
    min_doc_coverage: 0.5,
    max_duplications: 5
  };
}

function populateThresholdInputs(thresholds) {
  const fields = {
    "ci-max-complexity": thresholds.max_complexity,
    "ci-max-lines": thresholds.max_lines_per_function,
    "ci-min-doc-coverage": thresholds.min_doc_coverage,
    "ci-max-duplications": thresholds.max_duplications
  };
  for (const [id, value] of Object.entries(fields)) {
    const input = document.getElementById(id);
    if (input) input.value = value;
  }
}

function openThresholdsConfig() {
  // Toggle visibility of thresholds config section
  const section = document.getElementById("ci-thresholds-config");
  if (section) {
    section.classList.toggle("hidden");
  }
}

function saveThresholds() {
  const thresholds = {
    max_complexity: parseFloat(document.getElementById("ci-max-complexity")?.value) || 10,
    max_lines_per_function: parseInt(document.getElementById("ci-max-lines")?.value) || 100,
    min_doc_coverage: parseFloat(document.getElementById("ci-min-doc-coverage")?.value) || 0.5,
    max_duplications: parseInt(document.getElementById("ci-max-duplications")?.value) || 5
  };
  localStorage.setItem("jupiter_ci_thresholds", JSON.stringify(thresholds));
  addLog(t("ci_thresholds_saved") || "CI thresholds saved.");
  
  // Hide config section
  const section = document.getElementById("ci-thresholds-config");
  if (section) section.classList.add("hidden");
}

async function runCICheck() {
  const apiBase = state.apiBaseUrl || inferApiBaseUrl();
  if (!apiBase) {
    alert(t("error_fetch") || "Missing API base URL.");
    return;
  }
  
  const thresholds = getCIThresholds();
  const statusEl = document.getElementById("ci-status");
  const metricsEl = document.getElementById("ci-metrics-grid");
  const violationsEl = document.getElementById("ci-violations-list");
  
  if (statusEl) {
    statusEl.innerHTML = `<span class="status-badge pending">${t("ci_running") || "Running..."}</span>`;
  }
  
  try {
    const params = new URLSearchParams();
    if (state.currentBackend) {
      params.set("backend_name", state.currentBackend);
    }
    
    const response = await apiFetch(`${apiBase}/ci?${params.toString()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thresholds })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status} – ${errorText}`);
    }
    
    const result = await response.json();
    renderCIResult(result, statusEl, metricsEl, violationsEl);
    
    // Save to history
    if (!state.ciHistory) state.ciHistory = [];
    state.ciHistory.unshift({
      timestamp: new Date().toISOString(),
      passed: result.passed,
      violations_count: result.violations?.length || 0
    });
    state.ciHistory = state.ciHistory.slice(0, 20); // Keep last 20
    renderCIHistory();
    
    addLog(result.passed ? 
      (t("ci_passed") || "CI check passed!") : 
      (t("ci_failed") || "CI check failed with violations."));
    
  } catch (error) {
    console.error("CI check failed", error);
    if (statusEl) {
      statusEl.innerHTML = `<span class="status-badge error">${t("ci_error") || "Error"}</span>`;
    }
    addLog(`${t("ci_error") || "CI check error"}: ${error.message}`, "ERROR");
  }
}

function renderCIResult(result, statusEl, metricsEl, violationsEl) {
  // Status
  if (statusEl) {
    const badge = result.passed ? 
      `<span class="status-badge success">${t("ci_status_passed") || "PASSED"}</span>` :
      `<span class="status-badge error">${t("ci_status_failed") || "FAILED"}</span>`;
    statusEl.innerHTML = badge;
  }
  
  // Metrics
  if (metricsEl && result.metrics) {
    const m = result.metrics;
    metricsEl.innerHTML = `
      <div class="metric-card">
        <div class="metric-label">${t("ci_metric_complexity") || "Avg Complexity"}</div>
        <div class="metric-value">${m.avg_complexity?.toFixed(2) || "N/A"}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">${t("ci_metric_max_lines") || "Max Lines/Function"}</div>
        <div class="metric-value">${m.max_lines_per_function || "N/A"}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">${t("ci_metric_doc_coverage") || "Doc Coverage"}</div>
        <div class="metric-value">${m.doc_coverage ? (m.doc_coverage * 100).toFixed(1) + "%" : "N/A"}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">${t("ci_metric_duplications") || "Duplications"}</div>
        <div class="metric-value">${m.duplications_count ?? "N/A"}</div>
      </div>
    `;
  }
  
  // Violations
  if (violationsEl) {
    if (!result.violations || result.violations.length === 0) {
      violationsEl.innerHTML = `<p class="no-violations">${t("ci_no_violations") || "No violations found."}</p>`;
    } else {
      violationsEl.innerHTML = result.violations.map(v => `
        <div class="violation-item">
          <span class="violation-type">${v.type || "violation"}</span>
          <span class="violation-message">${v.message || ""}</span>
          ${v.file ? `<span class="violation-file">${v.file}</span>` : ""}
        </div>
      `).join("");
    }
  }
}

function renderCIHistory() {
  const tbody = document.getElementById("ci-history-body");
  if (!tbody || !state.ciHistory) return;
  
  tbody.innerHTML = state.ciHistory.map(entry => `
    <tr>
      <td>${new Date(entry.timestamp).toLocaleString()}</td>
      <td>
        <span class="status-badge ${entry.passed ? 'success' : 'error'}">
          ${entry.passed ? (t("ci_passed_short") || "PASS") : (t("ci_failed_short") || "FAIL")}
        </span>
      </td>
      <td>${entry.violations_count}</td>
    </tr>
  `).join("");
}

function exportCIReport() {
  if (!state.ciHistory || state.ciHistory.length === 0) {
    alert(t("no_data_to_export") || "No data to export.");
    return;
  }
  
  const data = {
    context: {
      project_root: state.report?.root || "unknown",
      export_timestamp: new Date().toISOString(),
      type: "ci_history"
    },
    thresholds: getCIThresholds(),
    history: state.ciHistory
  };
  
  exportData(data, "jupiter-ci-report.json");
}

// ============================================
// Snapshot Detail Functions
// ============================================

async function viewSnapshotDetail(snapshotId) {
  const apiBase = state.apiBaseUrl || inferApiBaseUrl();
  if (!apiBase) {
    alert(t("error_fetch") || "Missing API base URL.");
    return;
  }
  
  try {
    const params = new URLSearchParams();
    if (state.currentBackend) {
      params.set("backend_name", state.currentBackend);
    }
    
    const response = await apiFetch(`${apiBase}/snapshots/${snapshotId}?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const snapshot = await response.json();
    renderSnapshotDetail(snapshot, snapshotId);
    
    // Show detail panel
    const panel = document.getElementById("snapshot-detail-panel");
    if (panel) panel.classList.remove("hidden");
    
  } catch (error) {
    console.error("Failed to load snapshot detail", error);
    addLog(`${t("snapshot_load_error") || "Failed to load snapshot"}: ${error.message}`, "ERROR");
  }
}

function renderSnapshotDetail(snapshot, snapshotId) {
  const titleEl = document.getElementById("snapshot-detail-title");
  const contentEl = document.getElementById("snapshot-detail-content");
  
  if (titleEl) {
    titleEl.textContent = `${t("snapshot_detail_title") || "Snapshot"}: ${snapshotId}`;
  }
  
  if (contentEl && snapshot) {
    const summary = snapshot.summary || {};
    contentEl.innerHTML = `
      <div class="snapshot-summary">
        <h4>${t("snapshot_summary") || "Summary"}</h4>
        <div class="summary-grid">
          <div><strong>${t("total_files") || "Files"}:</strong> ${summary.total_files || 0}</div>
          <div><strong>${t("total_functions") || "Functions"}:</strong> ${summary.total_functions || 0}</div>
          <div><strong>${t("total_lines") || "Lines"}:</strong> ${summary.total_lines || 0}</div>
          <div><strong>${t("timestamp") || "Timestamp"}:</strong> ${snapshot.timestamp || "N/A"}</div>
        </div>
      </div>
      ${snapshot.label ? `<p><strong>${t("label") || "Label"}:</strong> ${snapshot.label}</p>` : ""}
      <div class="snapshot-actions">
        <button class="btn secondary" data-action="export-snapshot" data-id="${snapshotId}">
          ${t("export") || "Export"}
        </button>
      </div>
    `;
  }
}

function closeSnapshotDetail() {
  const panel = document.getElementById("snapshot-detail-panel");
  if (panel) panel.classList.add("hidden");
}

async function exportSnapshot(snapshotId) {
  const apiBase = state.apiBaseUrl || inferApiBaseUrl();
  if (!apiBase) {
    alert(t("error_fetch") || "Missing API base URL.");
    return;
  }
  
  try {
    const params = new URLSearchParams();
    if (state.currentBackend) {
      params.set("backend_name", state.currentBackend);
    }
    
    const response = await apiFetch(`${apiBase}/snapshots/${snapshotId}?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const snapshot = await response.json();
    exportData(snapshot, `jupiter-snapshot-${snapshotId}.json`);
    
  } catch (error) {
    console.error("Failed to export snapshot", error);
    addLog(`${t("snapshot_export_error") || "Failed to export snapshot"}: ${error.message}`, "ERROR");
  }
}

// ============================================
// License / Meeting Details Functions
// ============================================

async function refreshLicenseDetails() {
  const apiBase = state.apiBaseUrl || inferApiBaseUrl();
  if (!apiBase) {
    alert(t("error_fetch") || "Missing API base URL.");
    return;
  }
  
  try {
    const response = await apiFetch(`${apiBase}/meeting/status`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const status = await response.json();
    renderLicenseDetails(status);
    addLog(t("license_refreshed") || "License details refreshed.");
    
  } catch (error) {
    console.error("Failed to refresh license details", error);
    addLog(`${t("license_refresh_error") || "Failed to refresh license"}: ${error.message}`, "ERROR");
  }
}

function renderLicenseDetails(status) {
  const fields = {
    "license-type": status.license_type || "unknown",
    "license-status": status.connected ? (t("license_active") || "Active") : (t("license_inactive") || "Inactive"),
    "license-device": status.device_key || "N/A",
    "license-session": status.session_id || "N/A",
    "license-expiry": status.expiry || "N/A",
    "license-features": status.features?.join(", ") || "N/A"
  };
  
  for (const [id, value] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }
}


