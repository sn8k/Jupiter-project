## 🧪 **TODO - Tests d'autodiagnostic pour Jupiter**

L’objectif de ces tests est de vérifier la capacité de Jupiter à se **tester lui-même** tout en validant ses fonctionnalités de manière cohérente. Ces tests doivent être effectués sur le projet Jupiter lui-même, avec comparaison des résultats pour garantir la stabilité et la performance des nouvelles fonctionnalités.

### **1. Tests Unitaires & d'Intégration**

#### **1.1. Tests du module de scan (scan.py)**

* [ ] **Test du scan incrémental** :

  * Vérifier que le scan incrémental fonctionne correctement sur des projets de tailles variées.
  * Tester la gestion du cache (`.jupiter/cache/`) avec des changements mineurs.
  * Tester les options de filtre (fichiers cachés, `--ignore`, `--no-cache`).
* [ ] **Test de gestion des exclusions** :

  * Vérifier que les fichiers et répertoires exclus par `.jupiterignore` sont correctement ignorés.
  * Tester avec des glob patterns complexes.

#### **1.2. Tests du module d’analyse (analyzer.py)**

* [ ] **Test d’analyse dynamique** :

  * Vérifier l’intégration de l’analyse dynamique (fonctionnalités appelées via `run` avec `--with-dynamic`).
  * Vérifier que les métriques de performance (temps d'exécution, appels de fonction) sont bien collectées et stockées dans le rapport dynamique.
* [ ] **Test de l’analyse de code Python et JS/TS** :

  * Vérifier que les statistiques d’analyse (complexité cyclomatique, duplication de code) sont bien générées pour les fichiers Python, JS et TS.

#### **1.3. Tests du système de simulation (simulate.py)**

* [ ] **Simulation de suppression de fichier/fonction** :

  * Tester le comportement de la commande `simulate remove` pour divers types de fichiers et fonctions.
  * Vérifier que le rapport d'impact est détaillé et que les erreurs de lien sont correctement détectées.

#### **1.4. Tests des snapshots et de l’historique (history.py)**

* [ ] **Création et récupération de snapshots** :

  * Vérifier la persistance des snapshots dans `.jupiter/snapshots/` après chaque scan.
  * Tester la fonctionnalité de `diff` entre deux snapshots pour les fichiers ajoutés, supprimés, et modifiés.
  * Vérifier que la version du schéma est correctement ajoutée dans chaque snapshot.

---

### **2. Tests d'API & WebUI**

#### **2.1. Tests des endpoints API**

* [x] **Test du endpoint `/scan`** :

  * Vérifier que la commande `POST /scan` fonctionne correctement avec des options telles que `--incremental`, `--ignore`, et `--no-snapshot`.
* [x] **Test de l'endpoint `/analyze`** :

  * Vérifier que l'analyse fonctionne correctement avec des projets de taille moyenne et grande, et que le format du rapport est cohérent.
* [x] **Test de la simulation via API (`/simulate/remove`)** :

  * Vérifier que l’endpoint `/simulate/remove` renvoie des résultats précis pour les fichiers et fonctions spécifiés.
* [x] **Test de la gestion des snapshots via API** :

  * Vérifier les endpoints `/snapshots` et `/snapshots/diff` pour la gestion des snapshots historiques et la comparaison des versions.

#### **2.2. Tests de la WebUI**

* [x] **Test de l'intégration WebUI avec l'API** :

  * Vérifier que la WebUI est bien reliée à l'API pour les commandes de scan, analyse, et simulation.
  * Vérifier l’affichage des résultats dans le tableau de bord (status badges, derniers scans, etc.).
* [x] **Test des vues de gestion de projet (Backend)** :

  * Vérifier la possibilité de sélectionner différents backends (local et distant) depuis l’UI et tester les interactions avec les API distantes.
* [x] **Test des vues Snapshot & Diff** :

  * Vérifier l'affichage des snapshots dans l'UI et tester la fonctionnalité de "diff" entre deux snapshots.
* [x] **Test du module Live Map** :

  * Vérifier que le graphe interactif (Live Map) fonctionne correctement et s'adapte bien aux projets de différentes tailles.
  * Vérifier que les nœuds sont bien colorés en fonction des métriques et du temps d'exécution.

---

### **3. Tests de Performance & Stabilité**

#### **3.1. Tests de performance sur des projets volumineux**

* [ ] **Test sur un projet de grande taille** :

  * Vérifier la stabilité et la performance de Jupiter lorsqu'il analyse un projet volumineux (plusieurs milliers de fichiers).
* [ ] **Tests de parallélisation du scan** :

  * Vérifier que la parallélisation du scan fonctionne correctement en utilisant plusieurs threads pour les fichiers indépendants.

#### **3.2. Tests de performance sur la Live Map**

* [ ] **Test de performance de la génération du graphe** :

  * Tester la génération du graphe de dépendances et l’affichage dans la WebUI pour des projets larges, et s’assurer que les performances sont correctes.

---

### **4. Tests d’Intégration CI/CD**

#### **4.1. Tests d’intégration dans un pipeline CI**

* [ ] **Tests avec GitHub Actions** :

  * Vérifier l’intégration de Jupiter dans un pipeline CI/CD via GitHub Actions, en exécutant un scan et une analyse, et en vérifiant que les **quality gates** sont bien appliqués.
* [ ] **Tests avec d’autres CI (GitLab, etc.)** :

  * Vérifier que les tests de Jupiter fonctionnent correctement dans un environnement Docker minimal pour CI.

---

### **5. Comparaison des Résultats Autodiagnostiqués**

#### **5.1. Comparaison avec des tests classiques**

* [ ] **Vérifier la cohérence des résultats** :

  * Comparer les résultats des tests effectués par Jupiter avec ceux des tests classiques, pour s’assurer qu’il est capable de se diagnostiquer correctement.

#### **5.2. Validation de l’auto-diagnostic**

* [ ] **Tester les alertes sur code obsolète** :

  * Vérifier que Jupiter détecte correctement les fonctions et fichiers inutilisés ou obsolètes dans son propre code, et qu'il génère des recommandations de refactorisation ou de nettoyage.

---

### **6. Mise à jour de la documentation**

* [ ] **Mettre à jour la documentation des tests** dans `dev_guide.md` et `user_guide.md` pour intégrer toutes les nouvelles fonctionnalités testées.
* [ ] **Mettre à jour les changelogs** avec les nouvelles étapes de tests ajoutées, les cas de tests réussis, et les résultats obtenus.

