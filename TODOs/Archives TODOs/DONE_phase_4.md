## 🧾 Roadmap Jupiter – Phase 4 (agent de codage ready)

### **Section 1 – Expérience WebUI‑first & démarrage simplifié**

Objectif : un·e utilisateur·rice standard doit pouvoir utiliser Jupiter **uniquement via la WebUI**, sans avoir à taper de commande, y compris pour le démarrer.

* [x] **1.1 – Entry point “mode utilisateur”**

  * [x] Introduire un entry point haut niveau (ex : `jupiter.app` ou équivalent) qui :

    * [x] charge la config (`jupiter.yaml`),
    * [x] démarre le serveur API,
    * [x] sert le frontend,
    * [x] ouvre le navigateur par défaut sur la WebUI.
  * [x] Raccorder l’entrée console `jupiter` de manière à ce que :

    * [x] si appelée **sans arguments**, elle lance ce mode “full UI” directement (pas besoin de se souvenir de `gui` ou `server`).

* [x] **1.2 – Réduire la dépendance visible à la CLI**

  * [x] Mettre à jour la logique CLI pour que les commandes avancées (`scan`, `analyze`, `watch`, `update`, etc.) restent disponibles **pour usage SSH / avancé**, mais ne soient plus présentées comme chemin principal dans la doc “grand public”.
  * [x] Vérifier que tout ce que fait la CLI a un équivalent UI (au moins conceptuel) avant d’aller plus loin.

* [x] **1.3 – Tableau de bord “premier lancement”**

  * [x] Ajouter un mode “first run” dans la WebUI :

    * [x] si aucun projet n’est configuré, afficher un onboarding simple (“Choisir un dossier de projet” / “Configurer un backend distant”, cf. Section 3).
    * [x] guider l’utilisateur pour créer un `jupiter.yaml` minimal si besoin.

* [x] **1.4 – Mise à jour de la documentation**

  * [x] Mettre à jour le **Manuel utilisateur** FR et le **User Guide** EN pour mettre en avant le démarrage via WebUI et reléguer la CLI au rang d’outil avancé.
  * [x] Mettre à jour le **README** pour que la séquence “Quick Start” commence par l’UI et non plus par la CLI.

---

### **Section 2 – WebUI : tout faire depuis l’interface (parité CLI/UI)**

Objectif : l’UI doit exposer **toutes les actions importantes** qui existent déjà côté CLI/API.

**note importante concernant "meeting"** : cette fonction utilisera a terme ce que nous appelons une deviceKey, du type (exemple) 7F334701F08E904D796A83C6C26ADAF3. Tant que l'implementation de meeting est à l'etat de mock, considerer "7F334701F08E904D796A83C6C26ADAF3" comme etant la deviceKey, et que celle-ci est valide.


* [x] **2.1 – Parité fonctionnalités WebUI / CLI**

  * [x] Vérifier la couverture UI pour :

    * [x] `scan` (avec options `ignore`, `show_hidden`, `incremental`),
    * [x] `analyze` (`top`, `json`),
    * [x] `watch` (mode continu),
    * [x] `run` (commande arbitraire + `with_dynamic`),
    * [x] `update` (self‑update depuis ZIP ou Git),
    * [x] gestion des plugins (activer/désactiver),
    * [x] intégration Meeting (statut licence / deviceKey).
  * [x] Créer/compléter les écrans UI manquants :

    * [x] formulaire pour lancer un scan avec options,
    * [x] formulaire pour `run` + options dynamiques,
    * [x] panneau pour `watch`,
    * [x] panneau pour déclencher un `update` graphique.

* [x] **2.2 – Édition et gestion de configuration via UI**

  * [x] Ajouter une UI pour éditer `jupiter.yaml` :

    * [x] sections `server`, `ui`, `meeting`, `plugins`,
    * [x] validation basique des valeurs (port, URL, deviceKey, etc.).
  * [x] Permettre de :

    * [x] basculer thème et langue depuis Paramètres (données déjà supportées côté config/UX),
    * [x] gérer les plugins activés/désactivés depuis l’UI (en phase avec la config).

* [x] **2.3 – Feedback et UX**

  * [x] Vérifier que chaque action déclenchée depuis UI :

    * [x] montre un état “en cours” clair,
    * [x] affiche un résultat ou message d’erreur structuré (reprenant le format d’erreur JSON standard de l’API).

* [x] **2.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **User Guide** et **Manual** avec des captures / descriptions de chaque action réalisable depuis la WebUI.
  * [x] Mettre à jour le **Dev Guide** pour décrire la parité CLI/UI et où ajouter de nouvelles actions UI.

---

### **Section 3 – Projets distants & “greffe” sur une API de projet**

Objectif : permettre à Jupiter de **se connecter à une API distante** (autre instance Jupiter ou API de projet) pour réaliser des analyses, sans être forcément collé au filesystem local.

> On part pragmatiquement :
> d’abord support “backend Jupiter distant” (API Jupiter existante),
> puis on prépare le terrain pour des backends plus génériques à terme.

* [x] **3.1 – Concept de “backend de projet”**

  * [x] Introduire dans la config et l’architecture (ex : `ProjectBackend`) :

    * [x] type `local_fs`,
    * [x] type `remote_jupiter_api`,
    * [x] (prévoir une extension future pour `remote_custom_api`).
  * [x] Adapter `jupiter.server.manager` pour supporter plusieurs backends (multi‑projets), avec pour chacun :

    * [x] un identifiant,
    * [x] un type,
    * [x] un chemin local *ou* une `base_url` d’API distante.

* [x] **3.2 – Support d’un backend “Jupiter distant”**

  * [x] Permettre à la WebUI de configurer une `JUPITER_API_BASE` pour un projet donné (plus besoin d’édition manuelle d’ENV).
  * [x] En UI, permettre de :

    * [x] sélectionner un backend (local ou distant) dans un menu déroulant,
    * [x] interroger l’API distante (`/health`, `/scan`, `/analyze`, `/meeting/status`) comme si c’était le Jupiter local.
  * [x] Gérer les erreurs réseau et CORS proprement (afficher un statut clair “API distante inaccessible”).

* [x] **3.3 – Préparer les connecteurs d’API de projet**

  * [x] Définir un endroit dans le code (ex : `jupiter/core/connectors/`) pour :

    * [x] déclarer des “adapters” vers des API de projets externes (ex : un backend qui expose déjà ses propres métriques).
  * [x] Documenter un premier protocole minimal pour ces connecteurs (même si pas encore implémentés en profondeur).

* [x] **3.4 – Mise à jour de la documentation**

  * [x] Mettre à jour **Architecture** et **Dev Guide** pour inclure la notion de “backend de projet” (local/distant).
  * [x] Mettre à jour **User Guide / Manuel** pour expliquer comment ajouter un projet distant par URL d’API.

---

### **Section 4 – Checkpoint intermédiaire**

Objectif : faire une pause à mi‑parcours pour s’assurer que tout ce qui a été implémenté dans les Sections 1 à 3 est cohérent, testé et bien documenté.

* [x] **4.1 – Revue technique intermédiaire**

  * [x] effectuer les taches suivantes :

    * [x] vérifier la parité réelle CLI / WebUI pour les actions principales,
    * [x] valider le comportement du mode WebUI‑first (lancement simple, pas besoin de CLI pour un utilisateur normal),
    * [x] vérifier que la notion de backend local/distant fonctionne bien dans le code et dans l’UI.

* [x] **4.2 – Vérification tests & stabilité**

  * [x] S’assurer que :

    * [x] les tests existants sont toujours verts (scan, analyze, run, watch, Meeting, plugins, etc.),
    * [x] de nouveaux tests couvrent les fonctionnalités introduites (backend distant, parité UI/CLI, etc.).

* [x] **4.3 – Mise à jour de la documentation**

  * [x] Vérifier que les docs déjà modifiées dans les Sections 1–3 sont bien commitées, lisibles et alignées.
  * [x] Compléter ou corriger si besoin avant d’attaquer les sections suivantes.

---

### **Section 5 – Sécurité, permissions & durcissement de l’API**

Avec les projets distants et la WebUI plus puissante, il devient important de poser des bases de sécurité.

* [x] **5.1 – Authentification / Autorisation minimalistes**

  * [x] Introduire un mécanisme simple d’auth sur l’API (ex : token dans `jupiter.yaml` + header dans l’UI).
  * [x] Protéger au minimum :

    * [x] `/run`,
    * [x] `/update`,
    * [x] endpoints Meeting,
    * [x] actions d’administration backend/projets.

* [x] **5.2 – Sécurité des WebSockets**

  * [x] Vérifier que le flux `/ws` ne divulgue pas d’informations sensibles et est lié au contexte d’un projet / backend précis.
  * [x] Optionnel : ajouter un paramètre d’auth légère sur le canal WS.

* [x] **5.3 – Durcissement plugins & Meeting**

  * [x] Vérifier que les plugins ne peuvent pas casser l’ensemble du système sans être isolés/filtrés (au moins au niveau try/except + logs).
  * [x] S’assurer que la logique Meeting (licence) ne peut pas être facilement contournée par une simple modification de config locale.

* [x] **5.4 – Mise à jour de la documentation**

  * [x] Documenter la sécurité minimale et les options d’auth dans :

    * [x] **API Reference**,
    * [x] **Dev Guide**,
    * [x] éventuellement une courte section “Sécurité” dans le **README**.

---

### **Section 6 – Packaging & distribution orientée non‑tech**

Objectif : rapprocher Jupiter d’un produit utilisable par des personnes qui n’aiment pas ou ne connaissent pas le terminal.

* [x] **6.1 – Scénarios de distribution**

  * [x] Définir au moins un scénario cible (ex : zip + script, installeur, AppImage, etc.).
  * [x] S’assurer que ce scénario permet :

    * [x] de lancer Jupiter en double‑cliquant sur un script/launcher,
    * [x] d’ouvrir directement la WebUI.

* [x] **6.2 – Intégration de l’entry point “user” dans le packaging**

  * [x] Vérifier que le packaging (`pyproject.toml` ou autre) inclut l’entrée console `jupiter` déjà définie.
  * [x] Ajouter, si nécessaire, des scripts distincts pour :

    * [x] “Jupiter UI”,
    * [x] “Jupiter Server only” (pour usage avancé / infra).
    
  * [x] Fournir un script de build pour windows afin de generer un fichier executable windows.
  
* [x] **6.3 – Documentation d’installation niveau utilisateur**

  * [x] Compléter le **Manuel** et le **README** avec une section “Installation utilisateur” qui ne mentionne pas la CLI comme prérequis.

* [x] **6.4 – Mise à jour de la documentation**

  * [x] Vérifier que toute nouvelle méthode d’installation / lancement est bien expliquée dans :

    * [x] **Manual.md**,
    * [x] **README.md**,
    * [x] éventuellement **index.md** / docs d’entrée.

---

### **Section 7 – Documentation & revue finale de la phase 4**

Comme d’habitude, on termine par un passage documentation / cohérence globale.

* [x] **7.1 – Revue complète des docs**

  * [x] Passer en revue :

    * [x] `Manual.md` (FR),
    * [x] `user_guide.md` (EN),
    * [x] `api.md`,
    * [x] `architecture.md`,
    * [x] `dev_guide.md`,
    * [x] `reference_fr.md`,
    * [x] `README.md`,
    * [x] `index.md`,
  * [x] Vérifier que toutes les nouvelles fonctionnalités de la phase 4 y sont présentes et cohérentes.

* [x] **7.2 – Cohérence avec le document de référence Jupiter**

  * [x] Vérifier que ce qui est désormais implémenté colle bien à la vision décrite dans le **Document de Référence – Projet Jupiter**, notamment :

    * [x] WebUI‑first,
    * [x] multi‑projets / supervision,
    * [x] backends distants,
    * [x] auto‑mise‑à‑jour, Meeting, plugins, etc..

* [x] **7.3 – Mise à jour finale**

  * [x] Mettre à jour les chapitres DONE / roadmap pour marquer la fin de la phase 4 (ex. `DONE_chapter_3.md`).
  * [x] Confirmer que la documentation est propre, à jour, et utilisable comme base pour une phase 5 éventuelle (sécurité avancée, observabilité, IA, etc.).
