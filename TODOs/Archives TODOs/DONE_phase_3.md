### 🎯 **Roadmap Jupiter – Phase 3 : Fonctionnalités avancées & optimisation**

Voici la TODO pour **Phase 3** qui inclut les étapes suivantes :

---

### **1. Optimisation de la performance & gestion du cache**

Avec le système d’analyse incrémental en place, il est crucial d’optimiser davantage le processus de scan et d’analyse. L’objectif de cette section est de rendre le système plus réactif et d'éviter les recalculs inutiles.

* [x] **1.1. Optimisation du cache de scan**

  * [x] Finaliser l’utilisation du cache pour accélérer les scans incrémentaux : comparer les timestamps et les tailles de fichiers pour détecter les changements.
  * [x] Améliorer la gestion des **fichiers volatils** (temporaire) dans le cache.

* [x] **1.2. Mettre en place un mécanisme de cache intelligent pour `analyze`**

  * [x] Réduire les recalculs inutiles dans `analyze` avec un système de **cache basé sur les résultats** précédents.
  * [x] Exclure les fichiers déjà analysés et qui n’ont pas changé depuis le dernier scan (en utilisant un hash de fichier ou une date de dernière modification).

* [x] **1.3. Ajouter une option `--no-cache` dans la CLI**

  * [x] Permettre à l’utilisateur de forcer une analyse sans cache (utile en cas de doute sur les résultats précédents).

* **Documentation** :

  * Mettre à jour la documentation pour inclure les optimisations liées au cache et à l'incrémentalité, en expliquant le comportement attendu lors de l'utilisation de l'option `--incremental` et `--no-cache`.

---

### **2. Amélioration de l’analyse dynamique**

Avec le mécanisme de base en place pour l’analyse dynamique, il est maintenant temps de lui donner plus de profondeur et d’intégrer davantage de métriques et de suivi en temps réel.

* [x] **2.1. Extension de l’instrumentation dynamique**

  * [x] Ajouter des **comptages d’appels** pour les fonctions appelant d'autres fonctions, et pas seulement les appels directs.
  * [x] Améliorer le suivi dynamique pour qu’il capture plus de détails : exemple, les retours de fonctions ou les exceptions déclenchées.

* [x] **2.2. Collecte des métriques de performance pendant l’exécution**

  * [x] Ajouter des mesures de **temps d’exécution** pour chaque fonction (par exemple, calculer le temps total passé dans chaque fonction appelée).
  * [x] Regrouper ces métriques dans le rapport dynamique, sous un champ `performance` par fonction.

* [x] **2.3. Visualisation dynamique**

  * [x] Créer une vue graphique interactive qui montre les **appels de fonctions** en temps réel (comme un graphe de dépendances dynamique), intégrée dans l’UI.
  * [x] Utiliser des couleurs pour indiquer les **zones d’inactivité** et les **fonctions les plus sollicitées** en temps réel.

* **Documentation** :

  * Mettre à jour le **Guide Utilisateur** et la **documentation API** pour inclure les nouvelles métriques disponibles dans l’analyse dynamique.

---

### **3. Ajout de la fonctionnalité de refactorisation et d’optimisation du code**

La prochaine étape est de rendre Jupiter capable de **suggérer des améliorations** sur le code, en utilisant des heuristiques de **qualité de code**, de **duplication** et de **complexité cyclomatique**.

* [x] **3.1. Détection des zones de code à refactorer**

  * [x] Intégrer un **analyseur de complexité cyclomatique** (module `complexity.py`).
  * [x] Détecter les **blocs de code dupliqués** (module `duplication.py`).
  * [x] Ajouter ces informations dans le rapport JSON sous la section `quality`.

* [x] **3.2. Améliorer le système de **hotspots** de qualité de code**

  * [x] Définir des critères pour un **“top 10 des fichiers à refactorer”** selon la complexité et la duplication.
  * [x] Visualiser ces **hotspots** dans la **GUI** sous forme de graphes ou de listes.

* [x] **3.3. Proposer des actions de refactorisation**

  * [x] Générer des recommandations basiques pour refactoriser les fichiers ou fonctions trop complexes (ex. : “fonction X trop complexe”).
  * [x] Ajouter une fonctionnalité où l’utilisateur peut **ignorer** certaines recommandations de refactorisation.

* **Documentation** :

  * Mettre à jour le **guide utilisateur** et **developer guide** pour expliquer comment fonctionne la détection des zones à refactorer et comment interagir avec cette fonctionnalité.

---

### **4. Amélioration du système de plugins (Phase 2)**

La gestion des plugins est essentielle pour **étendre** les fonctionnalités de Jupiter. Nous devons ajouter la possibilité de créer des plugins tiers tout en améliorant les capacités actuelles.

* [x] **4.1. Finaliser l’architecture des plugins**

  * [x] S’assurer que les plugins peuvent être activés/désactivés facilement via le fichier de configuration `jupiter.yaml`.
  * [x] Ajouter un **plugin d’exemple** : un plugin simple qui calcule des statistiques supplémentaires (ex : analyse de performance, code coverage, etc.).

* [x] **4.2. Documentation du système de plugins**

  * [x] Ajouter un fichier **`plugins.md`** qui explique comment développer, installer et activer un plugin dans Jupiter.
  * [x] Définir les **hooks disponibles** pour les plugins (`on_scan`, `on_analyze`, `on_run`).

* [x] **4.3. Ajouter un gestionnaire de plugins dans l’UI**

  * [x] Ajouter une **vue Plugins** dans la GUI qui affiche les plugins installés et leur état (activé/désactivé).
  * [x] Permettre l’activation/désactivation des plugins via l’UI et rechargement dynamique sans redémarrage.

* **Documentation** :

  * Mettre à jour la documentation **Plugin system** et ajouter une section dédiée dans le **Guide du Développeur** (`dev_guide.md`).

---

### **5. Tests et validation**

Il est essentiel d'avoir une couverture de test solide avant de passer à la phase de production. Cette étape vise à assurer la qualité et la stabilité du projet.

* [x] **5.1. Écrire des tests unitaires et d’intégration pour le code refactoré**

  * [x] Ajouter des tests sur le cache et le scan incrémental.
  * [x] Tester l’intégration de l’analyse dynamique (tests sur l’API `POST /run`, `POST /scan`).
  * [x] Ajouter des tests sur les **recommandations de refactorisation** générées par Jupiter.

* [x] **5.2. Intégration continue & tests automatisés**

  * [x] Ajouter des tests automatisés dans **GitHub Actions** pour tester les fonctionnalités essentielles (CLI, API, plugins).
  * [x] Ajouter un **rapport de couverture** pour le code testé, notamment pour les nouveaux modules de qualité et de refactorisation.

* **Documentation** :

  * Mettre à jour le **Dev Guide** pour inclure des instructions sur l’écriture des tests, l’utilisation de `pytest`, et les bonnes pratiques de CI.

---

### **6. Optimisation finale et performance**

Il reste une dernière phase pour **vérifier** et **optimiser** les performances avant la version finale de la fonctionnalité.

* [x] **6.1. Analyser les performances du système**

  * [x] Tester Jupiter sur des projets de grande taille pour détecter des **goulots d’étranglement**.
  * [x] Optimiser le traitement des fichiers volumineux dans le scan, analyse, et génération du rapport.

* [x] **6.2. Optimisation des WebSockets**

  * [x] Vérifier que les connexions WebSocket sont stables même avec un grand nombre d’événements (logs/changes).

* **Documentation** :

  * Mettre à jour la **documentation utilisateur** avec des **conseils de performance**, notamment pour les projets volumineux.

---

### **7. Documentation finale et vérification complète**

Avant de déployer en production, il est impératif que la **documentation soit vérifiée et mise à jour** à chaque étape du développement.

* [x] **7.1. Vérification finale de la documentation**

  * [x] Relire et vérifier que toutes les sections de documentation sont cohérentes et à jour :

    * **API** (`api.md`)
    * **User Guide** (`user_guide.md`)
    * **Developer Guide** (`dev_guide.md`)
    * **Architecture** (`architecture.md`)
  * [x] Vérifier que toutes les fonctionnalités documentées sont bien implémentées.

---

