const state = {
  context: null,
  report: null,
  view: "dashboard",
  logs: [],
  liveEvents: [],
  plugins: [
    {
      name: "Analyse statique",
      description: "Inspecte la structure des projets et calcule des métriques de base.",
      status: "placeholder",
    },
    {
      name: "Watch temps réel",
      description: "Diffuse les changements de fichiers via WebSocket.",
      status: "placeholder",
    },
    {
      name: "Meeting",
      description: "Synchronise la licence et la présence de l'agent Jupiter.",
      status: "placeholder",
    },
    {
      name: "Plugins IA",
      description: "Analyse optionnelle par IA, désactivée par défaut.",
      status: "inactive",
    },
  ],
};

const sampleReport = {
  root: "~/mon/projet",
  last_scan_timestamp: 1700000000,
  files: [
    { path: "src/main.py", size_bytes: 2400, modified_timestamp: 1700000000 },
    { path: "docs/readme.md", size_bytes: 1800, modified_timestamp: 1699900000 },
    { path: "tests/test_core.py", size_bytes: 4600, modified_timestamp: 1699000000 },
    { path: "jupiter/web/index.html", size_bytes: 8200, modified_timestamp: 1698800000 },
    { path: "jupiter/web/app.js", size_bytes: 16400, modified_timestamp: 1698700000 },
    { path: "jupiter/web/styles.css", size_bytes: 9200, modified_timestamp: 1698600000 },
  ],
};

const bytesToHuman = (value) => {
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
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

function addLog(message) {
  const entry = { message, timestamp: new Date() };
  state.logs.unshift(entry);
  state.logs = state.logs.slice(0, 8);
  const container = document.getElementById("log-stream");
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
  stream.innerHTML = "";
  state.liveEvents.forEach((event) => {
    const card = document.createElement("div");
    card.className = "live-card";
    const header = document.createElement("div");
    header.className = "live-title";
    header.textContent = `${event.title} · ${event.timestamp.toLocaleTimeString()}`;
    const body = document.createElement("p");
    body.className = "muted";
    body.textContent = event.detail;
    card.appendChild(header);
    card.appendChild(body);
    stream.appendChild(card);
  });
}

async function loadContext() {
  try {
    const response = await fetch("/context.json");
    if (!response.ok) {
      throw new Error("Réponse réseau inattendue");
    }
    const payload = await response.json();
    state.context = payload;
    document.getElementById("root-path").textContent = payload.root || "(non défini)";
  } catch (error) {
    console.warn("Impossible de charger le contexte", error);
    document.getElementById("root-path").textContent = "Non disponible";
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
  const detail = `${action} : action non câblée – un appel API sera ajouté ultérieurement.`;
  addLog(detail);
  pushLiveEvent("Placeholder", detail);
}

function handleAction(action) {
  switch (action) {
    case "load-sample":
      renderReport(sampleReport);
      addLog("Rapport exemple chargé.");
      break;
    case "start-scan":
      showPlaceholder("Scan");
      break;
    case "start-watch":
      showPlaceholder("Watch temps réel");
      break;
    case "start-run":
      showPlaceholder("Run commande");
      break;
    case "open-settings":
      setView("settings");
      pushLiveEvent("Navigation", "Ouverture des paramètres (placeholder)");
      break;
    case "open-license":
      showPlaceholder("Gestion licence Meeting");
      break;
    case "toggle-theme":
      showPlaceholder("Bascule de thème");
      break;
    case "change-language":
      showPlaceholder("Sélecteur de langue");
      break;
    default:
      break;
  }
}

function bindActions() {
  document.querySelectorAll("[data-action]").forEach((element) => {
    element.addEventListener("click", (event) => {
      const { action } = event.currentTarget.dataset;
      handleAction(action);
    });
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

  input.addEventListener("change", async (event) => {
    const [file] = event.target.files;
    if (!file) return;
    const text = await file.text();
    try {
      const payload = JSON.parse(text);
      renderReport(payload);
      addLog(`Rapport chargé depuis ${file.name}.`);
    } catch (error) {
      alert("Le fichier n'est pas un JSON valide.");
      console.error("Erreur de parsing", error);
    }
  });

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragging");
  });

  dropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
    const [file] = event.dataTransfer.files;
    if (!file) return;
    const text = await file.text();
    try {
      renderReport(JSON.parse(text));
      addLog(`Rapport chargé depuis ${file.name}.`);
    } catch (error) {
      alert("Le fichier n'est pas un JSON valide.");
      console.error(error);
    }
  });
}

function renderStatusBadges(report) {
  const container = document.getElementById("status-badges");
  container.innerHTML = "";
  const badges = [];

  if (report) {
    badges.push({ label: "Rapport", value: "chargé" });
    badges.push({ label: "Mode", value: "Statique" });
    badges.push({ label: "Meeting", value: "À synchroniser" });
  } else {
    badges.push({ label: "Rapport", value: "aucun" });
    badges.push({ label: "Mode", value: "Attente" });
  }

  badges.forEach((badge) => {
    const span = document.createElement("span");
    span.className = "badge";
    span.textContent = `${badge.label} : ${badge.value}`;
    container.appendChild(span);
  });
}

function renderStats(report) {
  const statGrid = document.getElementById("stats-grid");
  statGrid.innerHTML = "";
  const files = Array.isArray(report?.files) ? [...report.files] : [];
  const totalSize = files.reduce((acc, file) => acc + (file.size_bytes || 0), 0);
  const largest = [...files].sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))[0];
  const lastUpdated = [...files].sort((a, b) => (b.modified_timestamp || 0) - (a.modified_timestamp || 0))[0];

  const stats = [
    { label: "Fichiers", value: files.length.toLocaleString("fr-FR") },
    { label: "Taille totale", value: bytesToHuman(totalSize) },
    {
      label: "Dernière modification",
      value: lastUpdated ? formatDate(lastUpdated.modified_timestamp) : "-",
    },
    {
      label: "Plus gros fichier",
      value: largest ? `${largest.path} (${bytesToHuman(largest.size_bytes)})` : "-",
    },
    {
      label: "Dernier scan",
      value: report?.last_scan_timestamp ? formatDate(report.last_scan_timestamp) : "Non fourni",
    },
    {
      label: "Licence Meeting",
      value: "Placeholder – en attente de l'adaptateur",
    },
  ];

  stats.forEach((stat) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    const label = document.createElement("p");
    label.className = "label";
    label.textContent = stat.label;
    const value = document.createElement("p");
    value.className = "value";
    value.textContent = stat.value;
    card.appendChild(label);
    card.appendChild(value);
    statGrid.appendChild(card);
  });
}

function renderUploadMeta(report) {
  const container = document.getElementById("upload-meta");
  if (!report) {
    container.textContent = "Aucun rapport chargé pour l'instant.";
    return;
  }
  container.innerHTML = "";
  const info = document.createElement("p");
  info.className = "small muted";
  const fileCount = Array.isArray(report.files) ? report.files.length : 0;
  info.textContent = `${fileCount} éléments importés — racine déclarée : ${report.root || "?"}`;
  container.appendChild(info);
}

function renderFiles(report) {
  const files = Array.isArray(report?.files) ? [...report.files] : [];
  const body = document.getElementById("files-body");
  const empty = document.getElementById("files-empty");
  body.innerHTML = "";

  if (!files.length) {
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  files
    .sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))
    .slice(0, 200)
    .forEach((file) => {
      const row = document.createElement("tr");
      const pathCell = document.createElement("td");
      pathCell.textContent = file.path;
      const sizeCell = document.createElement("td");
      sizeCell.className = "numeric";
      sizeCell.textContent = bytesToHuman(file.size_bytes || 0);
      const timeCell = document.createElement("td");
      timeCell.className = "numeric";
      timeCell.textContent = file.modified_timestamp ? formatDate(file.modified_timestamp) : "-";
      row.appendChild(pathCell);
      row.appendChild(sizeCell);
      row.appendChild(timeCell);
      body.appendChild(row);
    });
}

function renderAnalysis(report) {
  const files = Array.isArray(report?.files) ? [...report.files] : [];
  const statsContainer = document.getElementById("analysis-stats");
  statsContainer.innerHTML = "";

  if (!files.length) {
    statsContainer.innerHTML = "<p class='muted'>Chargez un rapport pour alimenter les indicateurs.</p>";
    return;
  }

  const extensionCount = files.reduce((acc, file) => {
    const ext = file.path.includes(".") ? file.path.split(".").pop() : "(sans extension)";
    acc[ext] = (acc[ext] || 0) + 1;
    return acc;
  }, {});

  const dominant = Object.entries(extensionCount).sort((a, b) => b[1] - a[1])[0];
  const avgSize = files.length ? files.reduce((acc, file) => acc + (file.size_bytes || 0), 0) / files.length : 0;
  const freshest = [...files].sort((a, b) => (b.modified_timestamp || 0) - (a.modified_timestamp || 0))[0];

  const stats = [
    { label: "Extension dominante", value: dominant ? `${dominant[0]} (${dominant[1]})` : "-" },
    { label: "Taille moyenne", value: bytesToHuman(avgSize) },
    { label: "Fichier le plus récent", value: freshest ? freshest.path : "-" },
    { label: "Analyse dynamique", value: "Placeholder (à brancher sur run/watch)" },
  ];

  stats.forEach((stat) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    const label = document.createElement("p");
    label.className = "label";
    label.textContent = stat.label;
    const value = document.createElement("p");
    value.className = "value";
    value.textContent = stat.value;
    card.appendChild(label);
    card.appendChild(value);
    statsContainer.appendChild(card);
  });
}

function renderHotspots(report) {
  const body = document.getElementById("hotspot-body");
  const empty = document.getElementById("hotspot-empty");
  body.innerHTML = "";

  if (!report || !Array.isArray(report.files) || !report.files.length) {
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  const candidates = [...report.files]
    .sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))
    .slice(0, 5);

  candidates.forEach((file, index) => {
    const row = document.createElement("tr");
    const nameCell = document.createElement("td");
    nameCell.textContent = file.path;
    const reasonCell = document.createElement("td");
    reasonCell.textContent = "Placeholder : surveiller la complexité et les usages réels.";
    const priorityCell = document.createElement("td");
    priorityCell.className = "numeric";
    priorityCell.textContent = index + 1;
    row.appendChild(nameCell);
    row.appendChild(reasonCell);
    row.appendChild(priorityCell);
    body.appendChild(row);
  });
}

function renderAlerts(report) {
  const container = document.getElementById("alert-list");
  container.innerHTML = "";
  const alerts = [];

  if (!report) {
    alerts.push({
      title: "Aucun rapport chargé",
      detail: "Importez un JSON produit par `jupiter scan` pour remplir les cartes et tableaux.",
    });
  } else {
    alerts.push({ title: "Meeting", detail: "Synchronisation licence non configurée (placeholder)." });
    alerts.push({ title: "Watch", detail: "Flux temps réel à activer lors du branchement WebSocket." });
  }

  alerts.forEach((alert) => {
    const item = document.createElement("li");
    item.className = "alert-item";
    item.innerHTML = `<div class="alert-icon">⚠️</div><div><p class="label">${alert.title}</p><p class="muted">${alert.detail}</p></div>`;
    container.appendChild(item);
  });
}

function renderPlugins() {
  const container = document.getElementById("plugin-list");
  container.innerHTML = "";
  state.plugins.forEach((plugin) => {
    const card = document.createElement("div");
    card.className = "plugin-card";
    const title = document.createElement("p");
    title.className = "label";
    title.textContent = plugin.name;
    const description = document.createElement("p");
    description.className = "muted";
    description.textContent = plugin.description;
    const status = document.createElement("span");
    status.className = "badge";
    status.textContent = plugin.status;
    const button = document.createElement("button");
    button.className = "ghost";
    button.textContent = "Activer (placeholder)";
    button.addEventListener("click", () => showPlaceholder(`Plugin ${plugin.name}`));

    card.appendChild(title);
    card.appendChild(description);
    card.appendChild(status);
    card.appendChild(button);
    container.appendChild(card);
  });
}

function renderReport(report) {
  state.report = report;
  renderStatusBadges(report);
  renderStats(report);
  renderUploadMeta(report);
  renderFiles(report);
  renderAnalysis(report);
  renderHotspots(report);
  renderAlerts(report);
  addLog("Interface mise à jour avec le rapport chargé.");
}

window.addEventListener("DOMContentLoaded", () => {
  loadContext();
  bindUpload();
  bindActions();
  renderStatusBadges(null);
  renderStats(null);
  renderUploadMeta(null);
  renderAlerts(null);
  renderPlugins();
  pushLiveEvent("Démarrage", "UI prête. Chargez un rapport ou utilisez l'exemple.");
});
