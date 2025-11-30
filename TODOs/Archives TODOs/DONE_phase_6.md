## 🧾 Roadmap Jupiter – Phase 6 (agent de codage ready)

**IMPERATIF** : ce fichier doit etre mis a jour à chaque action effectivement terminée en cochant les cases. Ceci est la seule modification autorisée et obligatoire de ce document.
---

### **Section 1 – Performance & gros projets (scalabilité)**

Objectif : faire en sorte que Jupiter reste fluide sur des **gros monorepos** (des dizaines / centaines de milliers de fichiers), en optimisant les scans, l’analyse et la Live Map.

* [x] **1.1 – Profiling des performances actuelles**

  * [x] Ajouter un mode debug/perf (flag config ou CLI) qui :

    * [x] mesure le temps de scan,
    * [x] mesure le temps d’analyse,
    * [x] mesure le temps de génération de graph / Live Map.
  * [x] Tester sur un projet volontairement volumineux et noter les points lents (I/O, parsing Python/JS, génération du graphe, etc.).

* [x] **1.2 – Optimisation du scan / analyse**

  * [x] Introduire de la **parallélisation contrôlée** (threadpool ou process pool) dans le scanner pour les fichiers indépendants.
  * [x] Limiter la profondeur d’analyse pour certains fichiers (ex : très gros assets, vendor, node_modules) via config (glob / taille max).
  * [x] Améliorer l’incrémental : éviter de toucher aux structures qui n’ont pas changé, même si le projet est énorme (cible `.jupiter/cache/`).

* [x] **1.3 – Optimisation Live Map**

  * [x] Ajouter une option pour **simplifier le graphe** sur les gros projets :

    * [x] regrouper certains nœuds (ex : par dossier),
    * [x] filtrer les nœuds peu utilisés (based on `dynamic.calls` / complexité).
  * [x] Pagination ou lazy‑load côté UI si le graphe dépasse un certain nombre de nœuds.

* [x] **1.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **Manual**, **User Guide** et **Dev Guide** pour :

    * expliquer les limites recommandées,
    * détailler les options de perf (parallélisation, filtres, options d’incrémental).

---

### **Section 2 – Intégration CI/CD & quality gates**

Objectif : permettre d’utiliser Jupiter facilement dans un pipeline CI/CD pour **bloquer ou noter** une build en fonction de la qualité et de l’analyse. (Aligné avec la partie “CI/CD integration” dans les extensions futures. )

* [x] **2.1 – Mode CI en ligne de commande**

  * [x] Ajouter un mode dédié (ex : `jupiter ci` / flag `--ci`) qui :

    * [x] exécute un scan + analyse,
    * [x] sort un résumé machine‑friendly (JSON, éventuellement SARIF ou JUnit‑like),
    * [x] retourne un code de sortie non‑nul si des seuils sont dépassés.

* [x] **2.2 – Quality gates configurables**

  * [x] Dans `jupiter.yaml`, ajouter une section, ex. :

    ```yaml
    ci:
      fail_on:
        max_complexity: 20
        max_duplication_clusters: 50
        max_unused_functions: 100
    ```
  * [x] Appliquer ces règles dans le mode CI :

    * [x] si les seuils sont franchis → code retour `1` + détails dans la sortie.

* [x] **2.3 – Docs & exemples de pipeline**

  * [x] Ajouter dans le repo :

    * [x] un exemple GitHub Actions (ou mettre à jour celui existant) pour utiliser le mode CI Jupiter,
    * [x] éventuellement un exemple GitLab / generic CI yml.
  * [x] S’assurer que les tests et l’analyse Jupiter peuvent tourner dans un environnement Docker minimal.

* [x] **2.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **README**, **Manual** et **Dev Guide** avec une section “Intégration CI/CD” :

    * exemples de commandes,
    * exemples de config,
    * exemples de pipeline.

---

### **Section 3 – Mode “équipe” : préférences & multi-utilisateur léger**

Objectif : sans faire un full “SaaS multi‑tenant”, offrir un **mode équipe** simple : préférences par utilisateur, plusieurs tokens, et séparation propre des responsabilités.

* [x] **3.1 – Tokens multiples & rôles simples**

  * [x] Étendre la section `security` de `jupiter.yaml` (déjà utilisée pour le token global).

    * [x] Autoriser une liste de tokens avec rôles, par ex. :

      ```yaml
      security:
        tokens:
          - token: "admin-token"
            role: "admin"
          - token: "viewer-token"
            role: "viewer"
      ```
  * [x] Définir des règles minimales :

    * `admin` : accès complet (run, update, config, plugins).
    * `viewer` : lecture seule (scan/analyze, Live Map, historique).

* [x] **3.2 – Préférences UI par utilisateur**

  * [x] Supporter le stockage de préférences côté client (thème, langue, vues préférées) déjà en place, mais :

    * [x] relier ces préférences à une “identité” utilisateur (ex : token ou pseudo simple).
  * [x] Permettre à l’UI d’afficher “profil” : rôle + réglages.

* [x] **3.3 – Journalisation des actions**

  * [x] Ajouter un log structuré des actions sensibles (run, update, change config, toggle plugin) avec :

    * [x] timestamp,
    * [x] token/role utilisé,
    * [x] action détaillée.

* [x] **3.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **API Reference**, **Architecture** et **Dev Guide** pour :

    * décrire le modèle `role/token`,
    * documenter les endpoints protégés et leur comportement selon le rôle.

---

### **Section 4 – Observabilité & métriques exportables**

Objectif : exposer l’état de Jupiter et de ses analyses à des outils externes (Prometheus, dashboards, etc.).

* [x] **4.1 – Endpoint de métriques**

  * [x] Ajouter un endpoint (ex. `/metrics` ou `/observability`) qui expose :

    * [x] nombre de scans,
    * [x] temps moyen de scan/analyse,
    * [x] nombre de plugins actifs,
    * [x] taille moyenne des projets, etc.
  * [x] Réfléchir à un format :

    * [x] soit compatible Prometheus text,
    * [x] soit un JSON simple, en laissant l’export spécialisé pour plus tard.

* [x] **4.2 – Événements structurés**

  * [x] Normaliser les messages envoyés via WebSocket (`/ws`) :

    * [x] typer les événements (SCAN_STARTED, SCAN_FINISHED, RUN_STARTED, RUN_FINISHED, SNAPSHOT_CREATED, etc.),
    * [x] documenter le format de chaque payload.

* [x] **4.3 – Intégration avec le plugin de notifications**

  * [x] Adapter le plugin notifications/webhook déjà en place (phase précédente) pour se brancher sur ces événements typés, si ce n’est pas déjà fait,
  * [x] offrir un mapping clair “événement interne → notification externe”.

* [x] **4.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **Dev Guide** (événements / hooks), **API Reference** (endpoint métriques / structure WS) et la section Plugins pour refléter ce modèle d’observabilité.

---

### **Section 5 – Checkpoint intermédiaire (revue par l’agent de codage)**

Objectif : faire une pause à mi‑parcours de la phase 6 et s’assurer que tout est propre, cohérent et testé.
**Note : en cas de besoin de tests sur un gros projet, utiliser "C:\Dev_VSCode\Brain2025-main\" comme root served !**

* [x] **5.1 – Revue fonctionnelle**

  * [x] L’agent de codage vérifie :

    * [x] la performance sur un gros projet (avec et sans incrémental),
    * [x] le fonctionnement du mode CI (`--ci` ou équivalent) avec quality gates,
    * [x] le modèle multi‑tokens/roles (admin vs viewer),
    * [x] la bonne exposition des métriques et la cohérence des événements WS.

* [x] **5.2 – Revue tests & CI**

  * [x] Vérifier que :

    * [x] de nouveaux tests couvrent les fonctionnalités de cette phase (perf, CI, rôles, métriques),
    * [x] la CI existante (GitHub Actions) reste verte et inclut ces nouveaux tests.

* [x] **5.3 – Mise à jour de la documentation**

  * [x] L’agent de codage doit s’assurer que toutes les docs déjà touchées en Sections 1–4 sont bien à jour et cohérentes, sinon les compléter avant de continuer.

---

### **Section 6 – Socle IA optionnel (sans la logique lourde)**

Objectif : préparer **proprement** le terrain pour l’IA optionnelle (refactor assistant, détection legacy, etc.), sans rendre Jupiter dépendant d’un modèle externe. (Ça rejoint les “extensions futures ML/assistant de refactoring” du document de référence. )

* [x] **6.1 – Clarifier l’interface du plugin IA**

  * [x] Finaliser le contrat de `plugins/ai_helper` déjà esquissé :

    * [x] quelles données il reçoit (rapport, diff, hotspots, quality, dynamic),
    * [x] ce qu’il est censé renvoyer (suggestions structurées, tags, annotations).
  * [x] Documenter cette interface de manière stable pour permettre des implémentations variées (OpenAI, autre LLM, offline, etc.).

* [x] **6.2 – Intégration dans l’UI**

  * [x] Ajouter un onglet ou une section “Suggestions IA” (désactivé si plugin IA non actif),
  * [x] pré‑voir l’affichage :

    * [x] liste de suggestions par fichier/fonction,
    * [x] possibilité de marquer “utile / pas utile / ignoré”.

* [x] **6.3 – Pilotage via config**

  * [x] Dans `jupiter.yaml`, clarifier :

    * [x] plugin IA activable/désactivable,
    * [x] éventuels paramètres (clé API, endpoint, etc.) laissés à la discrétion de l’implémentation.

* [x] **6.4 – Mise à jour de la documentation**

  * [x] Mettre à jour la section Plugins (FR/EN) et le Dev Guide pour :

    * décrire l’architecture du plugin IA,
    * rappeler que l’IA est **optionnelle** et isolée.

---

### **Section 7 – Préparation version “v1.0” (release & stabilité)**

Objectif : se rapprocher de la version “finale” stable en structurant la livraison, le support et le canal de mise à jour.

* [x] **7.1 – Politique de version**

  * [x] Clarifier dans le code et la doc :

    * [x] schéma de versioning (semver ou autre),
    * [x] ce que signifie “v1.0” pour Jupiter (stabilité des APIs, compat des rapports, etc.).
  * [x] Mettre à jour le fichier `VERSION` et la logique `jupiter --version` en conséquence.

* [x] **7.2 – Canal de release**

  * [x] Définir une branche ou tag “release”,
  * [x] mettre à jour la CI pour :

    * [x] créer un build (wheel / zip) sur tag,
    * [x] éventuellement publier automatiquement sur un artefact local ou un dépôt privé.

* [x] **7.3 – Scénario d’installation “utilisateur final”**

  * [x] Valider l’installation sur :

    * [x] Linux,
    * [x] Windows (via exécutable généré, comme prévu dans DONE_phase_4),
    * [x] éventuellement macOS.
  * [x] Vérifier que :

    * [x] le double‑click ou l’entrée “Jupiter UI” ouvre bien l’interface web,
    * [x] aucun prérequis CLI n’est nécessaire pour un utilisateur qui suit la doc.

* [x] **7.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **README**, **Manual**, **User Guide** et **index.md** pour présenter Jupiter comme proche d’une v1.0 stable, avec sections :

    * “Qu’est‑ce qu’il sait faire aujourd’hui ?”
    * “Comment l’installer ?”
    * “Comment l’utiliser sans terminal ?”

