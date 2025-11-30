## 🧾 Roadmap Jupiter – Checklist séquentielle pour Codex

> Usage prévu :
> 👉 “Codex, développe la **section 1**”, puis **2**, puis **3**, etc.

---

### **1. Base environnement & squelette projet**

* [x] Vérifier que la structure actuelle du projet est propre et cohérente avec les docs (core, cli, server, web, config).
* [x] Vérifier l’environnement Python :

  * [x] `.venv` fonctionnel
  * [x] `requirements.txt` minimal
* [x] Ajouter un `requirements-dev.txt` si besoin (pytest, outils de dev).
* [x] S’assurer que `python -m jupiter.cli.main --help` fonctionne.

---

### **2. Scanner & format de rapport v1 (fondations)**

* [x] Stabiliser l’implémentation de `scan` dans `jupiter/core/`.
* [x] Définir et documenter le **schéma JSON** de rapport v1 :

  * [x] ajouter un champ `version`
  * [x] décrire les champs obligatoires (chemin, taille, dates, type de fichier, etc.).
* [x] S’assurer que le rapport est :

  * [x] stable,
  * [x] lisible,
  * [x] prêt à être enrichi (analyse Python, dynamique, etc.).
* [x] Mettre à jour `analyze` pour reposer proprement sur ce format.

---

### **3. CLI – Cohérence & UX de base**

* [x] Repasser sur `jupiter/cli/main.py` :

  * [x] aligner toutes les commandes avec le manuel utilisateur actuel.
* [x] Vérifier les options :

  * [x] `scan <racine> [...]`
  * [x] `analyze <racine> [...]`
  * [x] `server <racine> [...]`
  * [x] `gui <racine> [...]`
* [x] S’assurer que :

  * [x] `--ignore`, `--show-hidden` et `.jupiterignore` se combinent correctement.
  * [x] les messages d’aide (`--help`) sont clairs.
* [x] Remplacer les `print()` de debug par du **logging** quand c’est pertinent.

---

### **4. Système de configuration (config/)**

* [x] Introduire une gestion de config centralisée dans `jupiter/config/` :

  * [x] support YAML/JSON (choisir un format principal).
  * [x] structurer les clés : `project_root`, `server`, `meeting`, `ui`, etc.
* [x] Chargement de la config :

  * [x] au lancement de la CLI,
  * [x] par défaut + override via arguments CLI.
* [x] Préparer les champs pour Meeting :

  * [x] `meeting.enabled`
  * [x] `meeting.deviceKey`
* [x] Prévoir un champ pour **thème UI** et **langue** (même si GUI ne l’utilise pas encore).

---

### **5. Serveur / API – Fondations**

* [x] Brancher un framework ASGI léger (ex : FastAPI) dans `jupiter/server/api.py`.
* [x] Définir les premiers endpoints REST :

  * [x] `GET /health` → état du serveur
  * [x] `POST /scan` → lance un scan sur `<racine>` et renvoie un rapport
  * [x] `GET /analyze` → renvoie un résumé à partir du rapport
* [x] Intégrer le système de config :

  * [x] host/port
  * [x] racine projet par défaut
* [x] Mettre en place un **logging serveur** propre (requêtes, erreurs).

---

### **6. GUI – Connexion au backend**

* [x] Adapter `gui` pour qu’il serve la web UI et parle à l’API :

  * [x] remplacer progressivement le fonctionnement “importer un JSON local” par un mode connecté à `/scan`.
* [x] Dashboard :

  * [x] afficher les KPI à partir du rapport reçu de l’API
  * [x] montrer la date du dernier scan
* [x] Bouton “Scan” :

  * [x] envoyer une requête à l’API `/scan`
  * [x] afficher un état “scan en cours”
  * [x] rafraîchir les vues dès que le rapport est dispo.
* [x] Garder la possibilité de charger un rapport JSON local en mode fallback/offline si utile.

---

### **7. Analyse Python – Langage prioritaire**

* [x] Créer `jupiter/core/language/python.py`.
* [x] Ajouter :

  * [x] extraction des fonctions définies par fichier,
  * [x] extraction des fonctions appelées,
  * [x] extraction des imports de modules.
* [x] Enrichir le rapport JSON :

  * [x] ajouter une section `language.python` avec détails par fichier.
* [x] Commencer une **première heuristique** :

  * [x] liste de fonctions potentiellement inutilisées (pure statique pour commencer).

---

### **8. Analyse avancée & agrégation**

* [x] Modifier `analyze` pour prendre en compte l’analyse Python :

  * [x] statistiques sur le nombre de fonctions, ratio utilisées/non utilisées.
* [x] Ajouter une liste de **“hotspots”** (gros fichiers, beaucoup de fonctions, etc.).
* [x] Préparer les structures pour les futures analyses (qualité, duplication, etc.) sans encore les implémenter.

---

### **9. Watch & Run – Bases de l’analyse dynamique**

* [x] Implémenter dans `jupiter/core/runner.py` :

  * [x] exécution d’une commande (`run`) avec capture des logs.
  * [x] base pour collecter événements d’exécution (même si stub au début).
* [x] Implémenter `jupiter watch` côté CLI :

  * [x] option `watch` qui, pour l’instant, se contente de surveiller les fichiers (file watcher) et logue les changements.
* [x] Sur le serveur :

  * [x] définir un endpoint `/run` (exécuter une commande côté backend)
  * [x] prévoir `ws.py` pour diffuser les logs en direct via WebSocket (même si stub).
* [x] Préparer la place dans le rapport JSON pour les métadonnées d’exécution (ex: `dynamic.calls`, même vide au début).

---

### **10. Intégration Meeting & logique de licence**

* [x] Dans `jupiter/server/meeting_adapter.py` :

  * [x] définir les fonctions internes `register_device()`, `heartbeat()`, `check_license()`.
  * [x] simuler la logique :

    * [x] si `deviceKey` inconnue → usage limité (timer 10 min).
* [x] Côté serveur :

  * [x] exposer un endpoint `/meeting/status` pour la GUI.
* [x] Côté GUI (Dashboard) :

  * [x] afficher :

    * [x] état licence,
    * [x] temps restant si mode limité,
    * [x] dernier ping Meeting.

---

### **11. i18n & Thèmes UI**

* [x] Mettre en place les fichiers de langue dans `jupiter/web/lang/` :

  * [x] `en.json`
  * [x] `fr.json`
* [x] Modifier la GUI pour utiliser les clés de traduction à la place des textes en dur.
* [x] Ajouter un sélecteur de langue dans le panneau Paramètres :

  * [x] appliquer le changement sans recharger toute l’app si possible.
* [x] Implémenter le système de thème :

  * [x] dark par défaut,
  * [x] switch vers light,
  * [x] persistance du choix (localStorage ou similaire).

---

### **12. Système de plugins & IA optionnelle (hooks)**

* [x] Créer `jupiter/plugins/__init__.py`.
* [x] Définir une interface de base pour les plugins :

  * [x] hooks type `on_scan(report)`, `on_analyze(report)`, etc.
* [x] Créer un **plugin d’exemple** :

  * [x] `plugins/code_quality_stub` qui ajoute quelques métriques triviales.
* [x] Prévoir l’emplacement pour un plugin IA (optionnel) :

  * [x] ex: `plugins/ai_helper` (non implémenté pour l’instant, mais interface définie).

---

### **13. Tests, qualité & packaging**

* [x] Installer et configurer `pytest`.
* [x] Tests pour `scan` :

  * [x] projet simple,
  * [x] `.jupiterignore`,
  * [x] combinaisons `--ignore` / fichiers cachés.
* [x] Tests pour `analyze` :

  * [x] résumés cohérents,
  * [x] pas de crash sur gros projets ou fichiers non parsables.
* [x] Tests basiques pour l’API :

  * [x] `/health`,
  * [x] `/scan`.
* [x] Préparer un début de packaging :

  * [x] `pyproject.toml` ou `setup.cfg` minimal,
  * [x] entrée console type `jupiter` (futur).

---

### **14. Documentation – Générée par Codex**

> 📝 **Spécifiquement ce que tu m’as demandé d’ajouter à la TODO.**

* [x] Préparer la structure de la doc (même minimaliste) :

  * [x] `docs/` ou équivalent.
  * [x] placeholders pour :

    * [x] manuel utilisateur complet,
    * [x] guides dev,
    * [x] docs API,
    * [x] docs architecture.
* [x] Une fois les étapes précédentes suffisamment mûres :

  * [x] demander à Codex/gpt de **générer automatiquement** :

    * [x] manuel utilisateur complet (à partir du code & des commandes),
    * [x] documentation technique (API, modules, etc.),
    * [x] README de niveau “public”.
* [x] Vérifier que la doc générée est alignée avec :

  * [x] `AGENTS.md` (style & conventions),
  * [x] le document de référence Jupiter,
  * [x] ce flux de développement.
