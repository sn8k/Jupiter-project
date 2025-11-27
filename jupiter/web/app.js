const state = {
  context: null,
  report: null,
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
  const date = new Date(timestamp * 1000);
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const sampleReport = {
  root: "~/mon/projet",
  files: [
    { path: "src/main.py", size_bytes: 2400, modified_timestamp: 1700000000 },
    { path: "docs/readme.md", size_bytes: 1800, modified_timestamp: 1699900000 },
    { path: "tests/test_core.py", size_bytes: 4600, modified_timestamp: 1699000000 },
  ],
};

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
    console.error("Impossible de charger le contexte", error);
    document.getElementById("root-path").textContent = "Non disponible";
  }
}

function bindUpload() {
  const input = document.getElementById("report-input");
  const dropzone = document.getElementById("dropzone");
  const sampleButton = document.getElementById("load-sample");

  input.addEventListener("change", async (event) => {
    const [file] = event.target.files;
    if (!file) return;
    const text = await file.text();
    try {
      const payload = JSON.parse(text);
      renderReport(payload);
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
    } catch (error) {
      alert("Le fichier n'est pas un JSON valide.");
      console.error(error);
    }
  });

  sampleButton.addEventListener("click", () => renderReport(sampleReport));
}

function renderReport(report) {
  state.report = report;
  document.getElementById("summary-hint").textContent = report.root
    ? `Racine déclarée : ${report.root}`
    : "Racine inconnue";

  const files = Array.isArray(report.files) ? [...report.files] : [];
  const totalSize = files.reduce((acc, file) => acc + (file.size_bytes || 0), 0);
  const largest = [...files].sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))[0];
  const lastUpdated = [...files].sort((a, b) => (b.modified_timestamp || 0) - (a.modified_timestamp || 0))[0];

  const statGrid = document.getElementById("stats-grid");
  statGrid.innerHTML = "";

  const stats = [
    { label: "Fichiers", value: files.length.toLocaleString("fr-FR") },
    { label: "Taille totale", value: bytesToHuman(totalSize) },
    {
      label: "Dernière mise à jour",
      value: lastUpdated ? formatDate(lastUpdated.modified_timestamp) : "-",
    },
    {
      label: "Plus gros fichier",
      value: largest ? `${largest.path} (${bytesToHuman(largest.size_bytes)})` : "-",
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

  const body = document.getElementById("files-body");
  body.innerHTML = "";
  const empty = document.getElementById("files-empty");

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
      timeCell.textContent = file.modified_timestamp
        ? formatDate(file.modified_timestamp)
        : "-";
      row.appendChild(pathCell);
      row.appendChild(sizeCell);
      row.appendChild(timeCell);
      body.appendChild(row);
    });
}

window.addEventListener("DOMContentLoaded", () => {
  loadContext();
  bindUpload();
});
