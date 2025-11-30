Chaque section est indépendante et dans un ordre logique de dev.
ce fichier **doit** etre mis a jour a chaque action effectivement terminées. C'est la seule modification autorisée de ce document.

---

## **Section 1 – Stabilisation de l’API & schémas**

* [x] **1.1 – Introduire des modèles de données (Pydantic)**

  * [x] Créer des modèles pour les payloads de requête :

    * [x] `ScanRequest` (`show_hidden`, `ignore_globs`, etc.)
    * [x] `RunRequest` (`command: List[str]`)
  * [x] Créer des modèles pour les réponses :

    * [x] `ScanReport`
    * [x] `AnalyzeResponse`
    * [x] `RunResponse`
    * [x] `MeetingStatus`

* [x] **1.2 – Brancher les modèles dans les endpoints FastAPI**

  * [x] Utiliser `ScanRequest` dans `POST /scan`
  * [x] Utiliser les modèles de réponse pour tous les `return` d’API
  * [x] Vérifier que la doc OpenAPI reflète bien ces schémas

* [x] **1.3 – Harmoniser le format du rapport côté core & API**

  * [x] S’assurer que `ScanReport` correspond au JSON produit par le core
  * [x] Ajouter un champ `schema_version` si ce n’est pas déjà fait
  * [x] Prévoir un champ pour `dynamic` (même vide au début)

---

## **Section 2 – Gestion des erreurs & statuts HTTP**

* [x] **2.1 – Créer une hiérarchie d’exceptions Jupiter**

  * [x] `JupiterError` (base)
  * [x] `ScanError`
  * [x] `AnalyzeError`
  * [x] `RunError`
  * [x] `MeetingError`

* [x] **2.2 – Mapper les erreurs vers des réponses HTTP**

  * [x] Utiliser des handlers FastAPI pour :

    * [x] 400 → erreurs d’entrée utilisateur
    * [x] 404 → ressources introuvables (si applicable)
    * [x] 500 → erreurs internes
    * [x] 503 → Meeting indisponible

* [x] **2.3 – Messages d’erreur cohérents**

  * [x] Définir une structure standard :

    ```json
    { "error": { "code": "SCAN_FAILED", "message": "...", "details": {...} } }
    ```
  * [x] S’assurer que tous les endpoints suivent ce format en cas d’erreur

---

## **Section 3 – Incremental scan & cache**

* [x] **3.1 – Définir l’emplacement du cache**

  * [x] Dossier `.jupiter/cache/` à la racine du projet
  * [x] Fichier `last_scan.json` + éventuellement `meta.json`

* [x] **3.2 – Implémenter la logique de scan incrémental**

  * [x] Ajouter un flag `incremental` côté core (scan)
  * [x] Comparer timestamps / tailles / hash légers pour détecter les fichiers modifiés
  * [x] Ne rescanner que les fichiers modifiés + nouveaux + supprimés

* [x] **3.3 – Raccorder CLI & API**

  * [x] Ajouter `--incremental` à la CLI `scan` et `analyze`
  * [x] Ajouter un champ `incremental` dans la requête `POST /scan`
  * [x] Documenter le comportement dans l’API et le user guide

---

## **Section 4 – Analyse dynamique v1 (exécution réelle)**

* [x] **4.1 – Instrumentation minimale Python**

  * [x] Introduire un mécanisme léger pour compter les appels de fonctions (ex. wrapper ou table globale)
  * [x] Associer les compteurs aux fonctions identifiées par `language.python` (nom + fichier)

* [x] **4.2 – Intégration avec `runner`**

  * [x] Lors d’un `run`, activer la collecte dynamique si demandé (`--with-dynamic` ou param API)
  * [x] Après exécution, récupérer les compteurs et les fusionner dans le rapport (`report["dynamic"]["calls"]`)

* [x] **4.3 – Mise à jour de l’analyse statique**

  * [x] Adapter l’heuristique des fonctions inutilisées :

    * [x] “vraiment suspecte” = non appelée statiquement **et** `dynamic.calls == 0`
  * [x] Exposer cette info dans le JSON d’analyse

---

## **Section 5 – GUI v2 (données live & vues détaillées)**

* [x] **5.1 – Dashboard enrichi**

  * [x] Ajouter un widget “activité récente” (fonctions / fichiers touchés)
  * [x] Afficher la dernière exécution `run` et son statut
  * [x] Indiquer si des données dynamiques sont disponibles (badge)

* [x] **5.2 – Vue “Fichier” avancée**

  * [x] Afficher :

    * [x] métriques de taille, lignes, complexité simple (si dispo)
    * [x] nombre de fonctions
    * [x] nombre d’appels dynamiques par fonction (si dispo)
  * [x] Ajouter un petit graphique ou barre visuelle d’activité

* [x] **5.3 – Vue “Fonction” avancée**

  * [x] Détail :

    * [x] chemin fichier
    * [x] ligne
    * [x] appels statiques
    * [x] appels dynamiques
  * [x] Indicateurs :

    * [x] `status: "unused" | "used" | "observed_once" | ...`
  * [x] Ajouter une timeline ou historique des appels (agrégé si simple)

---

## **Section 6 – Meeting v2 (système de licence concret)**

* [x] **6.1 – Formaliser le protocole interne Meeting**

  * [x] Documenter les appels prévus vers Meeting (même mockés pour l’instant)
  * [x] Définir :

    * [x] `register_device`
    * [x] `heartbeat`
    * [x] `validate_license`

* [x] **6.2 – Implémenter la logique licence côté backend**

  * [x] Timer de session si `deviceKey` inconnue (10 minutes)
  * [x] Stocker l’heure de démarrage de la session
  * [x] Bloquer ou restreindre certaines features après expiration :

    * [x] watch
    * [x] run
    * [x] scans dynamiques

* [x] **6.3 – Intégration UI**

  * [x] Dashboard :

    * [x] état licence (“active”, “limitée”, “non valide”)
    * [x] temps restant si mode limité
  * [x] Messages d’erreur clairs lorsque l’utilisateur tente une action bloquée

---

## **Section 7 – Analyse qualité (Code Quality v1)**

* [x] **7.1 – Créer `jupiter/core/quality/`**

  * [x] module `complexity.py` pour métrique simple (ex: complexité cyclomatique approximative)
  * [x] module `duplication.py` pour repérer des bloc de code dupliqués de manière naïve (hash de chunks)

* [x] **7.2 – Intégrer au pipeline d’analyse**

  * [x] Ajouter une section `quality` dans le rapport d’analyse :

    * [x] `complexity_per_file`
    * [x] `duplication_clusters`
  * [x] Ajouter quelques scores globaux (“top 10 fichiers à risque”)

* [x] **7.3 – Exposer dans l’UI**

  * [x] Nouveau tab “Code Quality”
  * [x] Liste des fichiers triés par “complexité”
  * [x] Indication des duplications les plus visibles

---

## **Section 8 – Plugins v2 (système complet)**

* [x] **8.1 – Plugin loader générique**

  * [x] Scanner `jupiter/plugins/` pour y trouver des classes `Plugin`
  * [x] Charger dynamiquement les plugins au démarrage
  * [x] Gérer les erreurs de chargement (logger proprement)

* [x] **8.2 – Contrat de plugin clair**

  * [x] Définir un protocole ou ABC `Plugin` :

    * [x] `name`, `version`, `description`
    * [x] hooks : `on_scan`, `on_analyze`, `on_run`, etc.
  * [x] Documenter ce contrat dans un doc dédié (`plugins.md` ou autre)

* [x] **8.3 – GUI Plugins**

  * [x] Page “Plugins” listant :

    * [x] nom
    * [x] description
    * [x] état (activé/désactivé)
  * [x] Permettre d’activer/désactiver un plugin (au moins en config + reload)

---

## **Section 9 – Tests avancés & CI**

* [x] **9.1 – Tests d’intégration API**

  * [x] Tests end-to-end sur :

    * [x] `/health`
    * [x] `/scan` (avec et sans options)
    * [x] `/analyze`
    * [x] `/run`
    * [x] `/meeting/status` (scénarios licence OK / KO)

* [x] **9.2 – Tests sur l’analyse dynamique**

  * [x] Projets de test simples :

    * [x] une fonction jamais appelée
    * [x] une fonction appelée dynamiquement
  * [x] Vérifier que les flags `unused/used` sont cohérents

* [x] **9.3 – Mise en place CI (GitHub Actions ou autre)**

  * [x] Workflow :

    * [x] lint (si tu en utilises un)
    * [x] tests
    * [x] build package (dry-run)

---

## **Section 10 – Packaging & Auto-update**

* [x] **10.1 – Packaging propre**

  * [x] Finaliser `pyproject.toml` ou `setup.cfg`
  * [x] Créer l’entrée console `jupiter` qui wrappe `python -m jupiter.cli.main`
  * [x] Vérifier l’install locale (`pip install -e .`)

* [x] **10.2 – Versioning**

  * [x] Fichier `VERSION` ou équivalent
  * [x] `jupiter --version` lit cette info

* [x] **10.3 – `self-update` minimal**

  * [x] Commande `jupiter self-update` :

    * [x] mode “depuis repo git” (si présent)
    * [x] mode “depuis ZIP local” (chemin fourni)
  * [x] Vérifier version avant/après
  * [x] Prévoir un mécanisme simple de rollback (ex: garder l’ancienne version tant que la nouvelle n’a pas démarré)

---

## **Section 11 – Documentation phase 2**

*(Tu as déjà une très bonne base.)*

* [x] **11.1 – Compléter la doc existante**

  * [x] Vérifier cohérence entre `user_guide.md`, `api.md`, `architecture.md`, et l’état réel du code
  * [x] Ajouter une section explicite sur :

    * [x] incremental scan
    * [x] analyse dynamique
    * [x] Meeting licence
    * [x] plugins

* [x] **11.2 – Génération assistée par Codex**

  * [x] Pour chaque module core (`scanner`, `analyzer`, `runner`, `language.python`, `quality`) :

    * [x] demander à Codex de proposer une doc détaillée (dev guide)
  * [x] Générer un `CONTRIBUTING.md` :

    * [x] workflow de dev
    * [x] conventions AGENTS.md
  * [x] Générer un `README.md` “public” à partir des docs existantes

* [x] **11.3 – Option site statique**

  * [x] (optionnel) Mettre en place un `mkdocs` ou équivalent
  * [x] Générer un site doc (local pour l’instant)

---



