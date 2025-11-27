## 🧾 Roadmap Jupiter – Checklist séquentielle pour Codex

> Usage prévu :
> 👉 “Codex, développe la **section 1**”, puis **2**, puis **3**, etc.

---

### **1. Base environnement & squelette projet**

* [ ] Vérifier que la structure actuelle du projet est propre et cohérente avec les docs (core, cli, server, web, config).
* [ ] Vérifier l’environnement Python :

  * [ ] `.venv` fonctionnel
  * [ ] `requirements.txt` minimal
* [ ] Ajouter un `requirements-dev.txt` si besoin (pytest, outils de dev).
* [ ] S’assurer que `python -m jupiter.cli.main --help` fonctionne.

---

### **2. Scanner & format de rapport v1 (fondations)**

* [ ] Stabiliser l’implémentation de `scan` dans `jupiter/core/`.
* [ ] Définir et documenter le **schéma JSON** de rapport v1 :

  * [ ] ajouter un champ `version`
  * [ ] décrire les champs obligatoires (chemin, taille, dates, type de fichier, etc.).
* [ ] S’assurer que le rapport est :

  * [ ] stable,
  * [ ] lisible,
  * [ ] prêt à être enrichi (analyse Python, dynamique, etc.).
* [ ] Mettre à jour `analyze` pour reposer proprement sur ce format.

---

### **3. CLI – Cohérence & UX de base**

* [ ] Repasser sur `jupiter/cli/main.py` :

  * [ ] aligner toutes les commandes avec le manuel utilisateur actuel.
* [ ] Vérifier les options :

  * [ ] `scan <racine> [...]`
  * [ ] `analyze <racine> [...]`
  * [ ] `server <racine> [...]`
  * [ ] `gui <racine> [...]`
* [ ] S’assurer que :

  * [ ] `--ignore`, `--show-hidden` et `.jupiterignore` se combinent correctement.
  * [ ] les messages d’aide (`--help`) sont clairs.
* [ ] Remplacer les `print()` de debug par du **logging** quand c’est pertinent.

---

### **4. Système de configuration (config/)**

* [ ] Introduire une gestion de config centralisée dans `jupiter/config/` :

  * [ ] support YAML/JSON (choisir un format principal).
  * [ ] structurer les clés : `project_root`, `server`, `meeting`, `ui`, etc.
* [ ] Chargement de la config :

  * [ ] au lancement de la CLI,
  * [ ] par défaut + override via arguments CLI.
* [ ] Préparer les champs pour Meeting :

  * [ ] `meeting.enabled`
  * [ ] `meeting.deviceKey`
* [ ] Prévoir un champ pour **thème UI** et **langue** (même si GUI ne l’utilise pas encore).

---

### **5. Serveur / API – Fondations**

* [ ] Brancher un framework ASGI léger (ex : FastAPI) dans `jupiter/server/api.py`.
* [ ] Définir les premiers endpoints REST :

  * [ ] `GET /health` → état du serveur
  * [ ] `POST /scan` → lance un scan sur `<racine>` et renvoie un rapport
  * [ ] `GET /analyze` → renvoie un résumé à partir du rapport
* [ ] Intégrer le système de config :

  * [ ] host/port
  * [ ] racine projet par défaut
* [ ] Mettre en place un **logging serveur** propre (requêtes, erreurs).

---

### **6. GUI – Connexion au backend**

* [ ] Adapter `gui` pour qu’il serve la web UI et parle à l’API :

  * [ ] remplacer progressivement le fonctionnement “importer un JSON local” par un mode connecté à `/scan`.
* [ ] Dashboard :

  * [ ] afficher les KPI à partir du rapport reçu de l’API
  * [ ] montrer la date du dernier scan
* [ ] Bouton “Scan” :

  * [ ] envoyer une requête à l’API `/scan`
  * [ ] afficher un état “scan en cours”
  * [ ] rafraîchir les vues dès que le rapport est dispo.
* [ ] Garder la possibilité de charger un rapport JSON local en mode fallback/offline si utile.

---

### **7. Analyse Python – Langage prioritaire**

* [ ] Créer `jupiter/core/language/python.py`.
* [ ] Ajouter :

  * [ ] extraction des fonctions définies par fichier,
  * [ ] extraction des fonctions appelées,
  * [ ] extraction des imports de modules.
* [ ] Enrichir le rapport JSON :

  * [ ] ajouter une section `language.python` avec détails par fichier.
* [ ] Commencer une **première heuristique** :

  * [ ] liste de fonctions potentiellement inutilisées (pure statique pour commencer).

---

### **8. Analyse avancée & agrégation**

* [ ] Modifier `analyze` pour prendre en compte l’analyse Python :

  * [ ] statistiques sur le nombre de fonctions, ratio utilisées/non utilisées.
* [ ] Ajouter une liste de **“hotspots”** (gros fichiers, beaucoup de fonctions, etc.).
* [ ] Préparer les structures pour les futures analyses (qualité, duplication, etc.) sans encore les implémenter.

---

### **9. Watch & Run – Bases de l’analyse dynamique**

* [ ] Implémenter dans `jupiter/core/runner.py` :

  * [ ] exécution d’une commande (`run`) avec capture des logs.
  * [ ] base pour collecter événements d’exécution (même si stub au début).
* [ ] Implémenter `jupiter watch` côté CLI :

  * [ ] option `watch` qui, pour l’instant, se contente de surveiller les fichiers (file watcher) et logue les changements.
* [ ] Sur le serveur :

  * [ ] définir un endpoint `/run` (exécuter une commande côté backend)
  * [ ] prévoir `ws.py` pour diffuser les logs en direct via WebSocket (même si stub).
* [ ] Préparer la place dans le rapport JSON pour les métadonnées d’exécution (ex: `dynamic.calls`, même vide au début).

---

### **10. Intégration Meeting & logique de licence**

* [ ] Dans `jupiter/server/meeting_adapter.py` :

  * [ ] définir les fonctions internes `register_device()`, `heartbeat()`, `check_license()`.
  * [ ] simuler la logique :

    * [ ] si `deviceKey` inconnue → usage limité (timer 10 min).
* [ ] Côté serveur :

  * [ ] exposer un endpoint `/meeting/status` pour la GUI.
* [ ] Côté GUI (Dashboard) :

  * [ ] afficher :

    * [ ] état licence,
    * [ ] temps restant si mode limité,
    * [ ] dernier ping Meeting.

---

### **11. i18n & Thèmes UI**

* [ ] Mettre en place les fichiers de langue dans `jupiter/web/lang/` :

  * [ ] `en.json`
  * [ ] `fr.json`
* [ ] Modifier la GUI pour utiliser les clés de traduction à la place des textes en dur.
* [ ] Ajouter un sélecteur de langue dans le panneau Paramètres :

  * [ ] appliquer le changement sans recharger toute l’app si possible.
* [ ] Implémenter le système de thème :

  * [ ] dark par défaut,
  * [ ] switch vers light,
  * [ ] persistance du choix (localStorage ou similaire).

---

### **12. Système de plugins & IA optionnelle (hooks)**

* [ ] Créer `jupiter/plugins/__init__.py`.
* [ ] Définir une interface de base pour les plugins :

  * [ ] hooks type `on_scan(report)`, `on_analyze(report)`, etc.
* [ ] Créer un **plugin d’exemple** :

  * [ ] `plugins/code_quality_stub` qui ajoute quelques métriques triviales.
* [ ] Prévoir l’emplacement pour un plugin IA (optionnel) :

  * [ ] ex: `plugins/ai_helper` (non implémenté pour l’instant, mais interface définie).

---

### **13. Tests, qualité & packaging**

* [ ] Installer et configurer `pytest`.
* [ ] Tests pour `scan` :

  * [ ] projet simple,
  * [ ] `.jupiterignore`,
  * [ ] combinaisons `--ignore` / fichiers cachés.
* [ ] Tests pour `analyze` :

  * [ ] résumés cohérents,
  * [ ] pas de crash sur gros projets ou fichiers non parsables.
* [ ] Tests basiques pour l’API :

  * [ ] `/health`,
  * [ ] `/scan`.
* [ ] Préparer un début de packaging :

  * [ ] `pyproject.toml` ou `setup.cfg` minimal,
  * [ ] entrée console type `jupiter` (futur).

---

### **14. Documentation – Générée par Codex**

> 📝 **Spécifiquement ce que tu m’as demandé d’ajouter à la TODO.**

* [ ] Préparer la structure de la doc (même minimaliste) :

  * [ ] `docs/` ou équivalent.
  * [ ] placeholders pour :

    * [ ] manuel utilisateur complet,
    * [ ] guides dev,
    * [ ] docs API,
    * [ ] docs architecture.
* [ ] Une fois les étapes précédentes suffisamment mûres :

  * [ ] demander à Codex/gpt de **générer automatiquement** :

    * [ ] manuel utilisateur complet (à partir du code & des commandes),
    * [ ] documentation technique (API, modules, etc.),
    * [ ] README de niveau “public”.
* [ ] Vérifier que la doc générée est alignée avec :

  * [ ] `AGENTS.md` (style & conventions),
  * [ ] le document de référence Jupiter,
  * [ ] ce flux de développement.
