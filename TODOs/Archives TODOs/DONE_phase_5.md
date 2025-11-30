# Jupiter – Phase 5 : Simulation, Historique & Intégrations avancées

Ce document récapitule les livrables de la Phase 5.

## 1. Historique de scans & diff
- Modèle de snapshots persistés dans `.jupiter/snapshots/`.
- CLI `snapshots list|show|diff` et endpoints `/snapshots`, `/snapshots/{id}`, `/snapshots/diff`.
- Vue **Historique** dans la WebUI avec sélection de deux snapshots et diff détaillé.

## 2. Simulation d’impact (`simulate remove`)
- Moteur de simulation dans le core (impact de suppression de fichier/fonction).
- Endpoint `/simulate/remove` et commande CLI `simulate remove <cible>`.
- Intégration UI (icône Corbeille dans les vues Fichiers/Fonctions + panneau de résultats).

## 3. Intégration APIs de projet
- Système de connecteurs (`jupiter.core.connectors`) avec `ProjectApiConfig`.
- Connecteur OpenAPI v1 : récupération du schéma, extraction des endpoints.
- Vue **API** dans la WebUI listant les endpoints du projet.

## 4. Live Map
- Génération d’un graphe de dépendances via `GraphBuilder`.
- Endpoint `/graph`.
- Vue **Live Map** avec graph interactif (fichiers, fonctions, JS/TS, hotspots).

## 5. Vérification intermédiaire
- Tests manuels et automatisés de l’historique, de la simulation, des connecteurs API et de la Live Map.
- Synchronisation de la doc avec les fonctionnalités 1–4.

## 6. Support polyglotte (JS/TS)
- Analyseur `js_ts.py` pour fichiers JS/TS.
- Intégration des métriques JS/TS à l’analyse et à la Live Map.
- Indication claire des langages dans l’UI.

## 7. Notifications & Webhooks
- Plugin `notifications_webhook` envoyant des POST JSON configurables.
- Configuration dans `jupiter.yaml` + UI pour l’URL et les événements.

## 8. Sécurité / Sandboxing
- Paramétrage de `run` via `security.allow_run` et `security.allowed_commands`.
- Politique de plugins (niveau de confiance, logs explicites).
- Durcissement des connecteurs distants (timeouts, gestion d’erreurs, pas de fuite de secrets).

## 9. Documentation & stabilisation
- Mise à jour de `README.md`, `Manual.md`, `docs/api.md`, `docs/user_guide.md`, `docs/architecture.md`, `docs/dev_guide.md`, `docs/plugins.md`, `docs/index.md` et référence FR.
- Présence d’un changelog par fichier et d’un récap global de phase.

La Phase 5 est considérée comme **clôturée**. La prochaine étape naturelle est une Phase 6 orientée IA, sécurité avancée et intégrations profondes supplémentaires.


## 🧾 Roadmap Jupiter – Phase 5 : Simulation, Historique & Intégrations avancées

---

### **Section 1 – Historique de scans & diff entre états du projet**

Objectif : permettre à Jupiter de **garder une mémoire** de l’état du projet et de comparer deux scans (ou analyses) dans le temps.

* [x] **1.1 – Modèle d’“instantané” (snapshot)**

  * [x] Introduire une notion de snapshot de scan/analysis (ex : `snapshots/scan-<timestamp>.json` ou stockage indexé).
  * [x] Ajouter des métadonnées : nom lisible, timestamp, version de Jupiter, projet et backend cible.

* [x] **1.2 – Commandes & API**

  * [x] Ajouter une API/commande pour lister les snapshots disponibles d’un projet.
  * [x] Ajouter un endpoint `/snapshots/{id}` pour récupérer un snapshot donné.
  * [x] Ajouter un endpoint `/snapshots/diff?id_a=...&id_b=...` pour produire un **diff structuré** (fichiers ajoutés/supprimés/modifiés, fonctions apparues/disparues, variations de complexité, etc.).

* [x] **1.3 – UI pour l’historique**

  * [x] Ajouter une vue “Historique” dans la WebUI listant les snapshots d’un projet (table triable).
  * [x] Permettre de sélectionner deux snapshots et d’afficher un **diff lisible** (fichiers, fonctions, métriques qualité/dynamique).

* 📚 **Documentation** :
  À la fin de cette section, mettre à jour User Guide, Manual, API Reference et Dev Guide pour expliquer :

  * comment les snapshots sont créés/utilisés,
  * comment utiliser le diff d’historique (CLI + UI).

---

### **Section 2 – Simulation d’impact (`simulate remove`)**

Objectif : permettre à Jupiter de **simuler l’impact de la suppression** d’une fonction ou d’un fichier, sans modifier le code.

* [x] **2.1 – API interne de simulation**

  * [x] Ajouter dans le core une fonction de simulation prenant en entrée :

    * [x] un identifiant de fonction (fichier + nom) ou de fichier,
    * [x] le graphe de dépendances (imports, appels de fonctions, usages).
  * [x] Calculer :

    * [x] quelles fonctions/fichiers deviendraient orphelins,
    * [x] quelles erreurs de lien d’appel apparaîtraient,
    * [x] quelles zones de code deviendraient clairement inutiles.

* [x] **2.2 – Endpoint & CLI**

  * [x] Ajouter un endpoint `/simulate/remove` qui :

    * [x] accepte une cible (`function` ou `file`) et renvoie un rapport d’impact.
  * [x] Ajouter une commande CLI `simulate remove <cible>` comme interface avancée (SSH / power users), en s’alignant avec le design du document de référence.

* [x] **2.3 – UI pour la simulation**

  * [x] Dans la WebUI, depuis :

    * [x] la vue Fichier,
    * [x] la vue Fonction,
    * ajouter un bouton “Simuler suppression”.
  * [x] Afficher un panneau de résultats :

    * [x] liste des impacts potentiels,
    * [x] évaluation “risque” (faible/moyen/fort),
    * [x] possibilité d’exporter le rapport.

* 📚 **Documentation** :
  À la fin de cette section, mettre à jour la référence (FR/EN) pour documenter la commande `simulate remove`, les endpoints associés et l’usage depuis l’UI (avec exemples).

---

### **Section 3 – Intégration avec APIs de projet génériques (au-delà des APIs Jupiter)**

Objectif : commencer à répondre au “à terme” → que Jupiter puisse **se greffer sur l’URL de l’API d’un projet** (pas nécessairement Jupiter) pour enrichir ses analyses.

* [x] **3.1 – Architecture de connecteurs d’API projet**

  * [x] Créer un module `jupiter/core/connectors/` avec une interface générique, par ex. `ProjectApiConnector` :

    * [x] méthodes possibles : `describe()`, `get_endpoints()`, `get_metrics()`, etc.
  * [x] Permettre de déclarer dans `jupiter.yaml` un ou plusieurs connecteurs pour un projet :

    ```yaml
    project_api:
      type: "openapi"
      base_url: "https://mon-projet/api"
      openapi_url: "/openapi.json"
    ```

* [x] **3.2 – Connecteur OpenAPI v1**

  * [x] Implémenter un connecteur de base pour une API exposant un schéma OpenAPI :

    * [x] récupération du schema,
    * [x] extraction des endpoints, méthodes, tags.
  * [x] Stocker ces infos dans le rapport d’analyse sous une section `api.endpoints`.

* [x] **3.3 – UI d’inspection d’API**

  * [x] Ajouter une vue “API du projet” qui :

    * [x] affiche les endpoints (table),
    * [x] croise éventuellement endpoints & fichiers (si on peut inférer les handlers, même de façon heuristique).
  * [x] Indiquer clairement quand l’API d’un projet est configurée ou non.

* 📚 **Documentation** :
  À la fin de cette section, documenter :

  * le concept de connecteur d’API de projet,
  * la configuration `project_api` dans `jupiter.yaml`,
  * et la vue correspondante dans la WebUI (FR + EN, + Dev Guide côté intégration).

---

### **Section 4 – Live Map UI & visualisation avancée**

Objectif : matérialiser la **“carte vivante” du projet** évoquée dans la référence : graphe des modules, des fonctions, des appels, enrichi par la dynamique et la qualité.

* [x] **4.1 – Génération du graphe**

  * [x] Construire un graphe orienté des dépendances internes :

    * [x] nœuds : fichiers, modules, éventuellement fonctions,
    * [x] arêtes : imports, appels de fonctions principaux.
  * [x] Enrichir les nœuds avec :

    * [x] métriques statiques (taille, complexité),
    * [x] info dynamique (nombre d’appels),
    * [x] état qualité (hotspots).

* [x] **4.2 – Endpoint “graph”**

  * [x] Ajouter un endpoint `/graph` renvoyant une structure JSON (compatible avec librairie JS de graph/force layout).

* [x] **4.3 – Vue “Live Map” dans la WebUI**

  * [x] Ajouter un onglet “Carte” ou “Live Map” :

    * [x] afficher le graphe sous forme interactive (zoom, pan, click).
    * [x] colorer les nœuds selon la complexité / usage dynamique.
    * [x] réagir aux événements temps réel (`watch` / `run`) pour mettre en surbrillance les parties actives.

* 📚 **Documentation** :
  À la fin de cette section, mettre à jour la référence et le User Guide pour expliquer la Live Map, comment l’interpréter et comment elle combine statique/dynamique/qualité.

---

### **Section 5 – Étape de vérification intermédiaire (agent de codage)**

Objectif : faire un **checkpoint à mi‑parcours** sur les fonctionnalités avancées introduites en Sections 1–4.

* [x] **5.1 – Revue fonctionnelle**

  * [x] tu dois :

    * [x] tester l’historique et le diff de scans (création, liste, comparaison),
    * [x] tester la simulation de suppression via CLI + UI,
    * [x] configurer au moins une API de projet (OpenAPI) et vérifier la remontée des endpoints,
    * [x] vérifier que la Live Map fonctionne sur un projet de taille significative.

* [x] **5.2 – Revue technique**

  * [x] Vérifier que :

    * [x] les nouveaux endpoints (snapshots, simulate, graph, project_api) sont documentés et correctement typés,
    * [x] aucune régression n’a été introduite sur les fonctionnalités précédentes (scan, analyze, quality, dynamic, Meeting, plugins).

* 📚 **Documentation** :
  À la fin de cette section, tu dois t’assurer que la doc existante est **synchronisée** avec les implémentations des Sections 1–4 (pas de fonctionnalité cachée, pas de doc obsolète).

---

### **Section 6 – Support polyglotte (JS/TS en priorité) & extension langage**

Objectif : étendre Jupiter au-delà de Python, comme prévu dans la vision “projets polyglottes”.

* [x] **6.1 – Analyseur JavaScript/TypeScript**

  * [x] Créer `jupiter/core/language/js_ts.py` ou équivalent :

    * [x] détecter les fichiers JS/TS,
    * [x] extraire fonctions, classes, imports,
    * [x] calculer des métriques basiques (nombre de fonctions, taille, complexité approximative).

* [x] **6.2 – Intégration à l’analyse et à la qualité**

  * [x] Intégrer JS/TS au pipeline `analyzer` :

    * [x] inclure leurs stats dans les agrégats,
    * [x] intégrer à la section `quality` si possible (complexité, duplication).
  * [x] Représenter les modules JS/TS dans la Live Map (avec un code couleur distinct).

* [x] **6.3 – UI & configuration**

  * [x] Permettre d’activer/désactiver l’analyse JS/TS via config/Plugins/langages.
  * [x] Afficher clairement dans l’UI les langages détectés dans le projet.

* 📚 **Documentation** :
  À la fin de cette section, mettre à jour les docs pour indiquer :

  * que Jupiter supporte désormais JS/TS (et comment),
  * comment étendre à d’autres langages (guide rapide dans Dev Guide / plugins).

---

### **Section 7 – Notifications & webhooks (plugin) – Observabilité externe**

Objectif : permettre au système de **notifier** des événements à l’extérieur (Slack, HTTP webhook, etc.), de manière pluginisée comme prévu.

* [x] **7.1 – Plugin de notifications générique**

  * [x] Créer un plugin `notifications_webhook` ou similaire qui :

    * [x] envoie des POST JSON vers une URL configurable lors de certains événements :

      * [x] fin de scan,
      * [x] nouvel hotspot qualité,
      * [x] fonction marquée comme “vraiment inutilisée”,
      * [x] expiration de licence Meeting.

* [x] **7.2 – Configuration**

  * [x] Ajouter la configuration correspondante dans `jupiter.yaml` :

    ```yaml
    plugins:
      enabled: ["notifications_webhook"]
    notifications_webhook:
      url: "https://mon-service/hooks/jupiter"
      events: ["scan_complete", "unused_function", "meeting_expired"]
    ```

* [x] **7.3 – UI**

  * [x] Dans l’onglet Plugins / Paramètres, afficher une petite interface pour configurer l’URL de webhook et les événements écoutés, si le plugin est activé.

* 📚 **Documentation** :
  À la fin de cette section, documenter ce plugin dans la partie Plugins (FR/EN), en expliquant les événements disponibles et les formats de payload.

---

### **Section 8 – Sécurité / sandboxing (premier passage sérieux)**

Objectif : commencer à répondre aux questions en suspens sur la **sécurité**, notamment autour de `run`, des plugins et des projets distants.

* [x] **8.1 – Limiter/paramétrer `run`**

  * [x] Ajouter la possibilité de restreindre `run` :

    * [x] à certains utilisateurs (token/API key),
    * [x] à un set d’actions prédéfinies,
    * [x] ou de désactiver complètement `run` via config.

* [x] **8.2 – Politique de plugins**

  * [x] Documenter et implémenter une politique simple :

    * [x] plugins “de confiance” vs “expérimentaux”,
    * [x] logs explicites quand un plugin lève une exception ou fait quelque chose de suspect.

* [x] **8.3 – Projets distants & sécurité**

  * [x] Vérifier que les intégrations d’API distantes sont :

    * [x] explicitement opt-in,
    * [x] correctement isolées (timeouts, erreurs réseau gérées),
    * [x] sans exposition de secrets dans les logs/UI.

* 📚 **Documentation** :
  À la fin de cette section, ajouter une section “Sécurité” dans Dev Guide / Architecture / README, décrivant :

  * les choix actuels,
  * les limitations connues,
  * les options de durcissement recommandées.

---

### **Section 9 – Documentation & stabilisation Phase 5**

Objectif : refermer la phase 5 avec un système **cohérent, documenté, diffable et simulable**.

* [x] **9.1 – Revue doc globale**

  * [x] Mettre à jour :

    * [x] `README.md` (ajout des nouvelles features majeures : historique/diff, simulation, Live Map, support JS/TS, intégration API de projet, notifications),
    * [x] `Manual.md` & `user_guide.md` (parcours utilisateur complet avec ces nouvelles capacités),
    * [x] `api.md` (endpoints snapshots, simulate, graph, connecteurs API, plugins),
    * [x] `architecture.md` et `dev_guide.md` (connecteurs, graph, polyglotte, sandboxing, plugins avancés),
    * [x] `reference_fr.md` et `index.md` si nécessaire pour refléter l’état final.

* [x] **9.2 – Marquage de fin de phase**

  * [x] Ajouter un `DONE_chapter_3.md` (ou équivalent) récapitulant les livrables de la Phase 5.
  * [x] S’assurer que la roadmap restante (Phase 6 éventuelle : IA, sécurité avancée, etc.) est claire dans la tête et dans les notes.

* 📚 **Documentation** :
  Cette section est entièrement dédiée à la documentation : à sa fin, tout doit être **synchronisé, complet, et exploitable** comme base de travail pour l’agent de codage et pour toi.

