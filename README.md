# 📘 **DOCUMENT DE RÉFÉRENCE – PROJET JUPITER**

### Outil généraliste de cartographie, d’analyse, d’observation et de maintenance intelligente de projets de développement

*(Version consolidée mise à jour)*

---

# **1. Vision et Objectif Général**

**Jupiter** est un outil généraliste conçu pour analyser, cartographier, observer et diagnostiquer l’état d’un projet de développement.
Il éclaire :

* la structure réelle du code,
* les dépendances internes,
* les fonctions réellement utilisées,
* les zones obsolètes ou mortes,
* l’évolution du projet dans le temps,
* le comportement dynamique en exécution,
* la santé du projet dans sa globalité.

Il fonctionne :

* en **local**,
* en **mode serveur**,
* via **interface web** ou **interface locale**,
* via **SSH**,
* et peut être **intégré à d’autres systèmes** (ex : *Meeting*).

Jupiter est **totalement généraliste**, indépendant de *Brain* ou d’un contexte spécifique.

---

# **2. Problématique ciblée**

Les projets informatiques évoluent et s’alourdissent. Ils accumulent :

* fichiers inutilisés,
* couches legacy,
* code mort,
* documentation obsolète,
* modules fantômes,
* scripts oubliés,
* usages réels divergents du code prévu,
* dette technique non identifiée.

Jupiter met en lumière l’état réel du projet, avec des outils d’analyse statique, dynamique et incrémentale.

---

# **3. Philosophie**

### **3.1. Jupiter éclaire, il ne modifie jamais le code**

Aucune modification automatique du code ou des fichiers du projet.

### **3.2. Analyse statique + dynamique**

Comprendre le projet “au repos” *et* “en mouvement”.

### **3.3. Observabilité continue**

Jupiter peut suivre l’évolution d’un projet dans le temps, ses modifications et son comportement lors de l’exécution.

### **3.4. Multi-langue par design**

Toutes les interfaces sont traduisibles nativement.

### **3.5. Systèmes externes**

Jupiter peut se connecter à Meeting ou d’autres services tiers via plugins.

---

# **4. Fonctionnalités Principales**

## **4.1. Scan & Cartographie globale**

* Analyse complète du dossier
* Détection de tous fichiers (code, doc, assets)
* Graphe de dépendances internes
* Arborescence annotée
* Résultats exportables

---

## **4.2. Analyse des fonctions**

### Extraction

Pour chaque langage :

* fonctions définies
* fonctions appelées
* classes, méthodes, endpoints, handlers…

### Détection des fonctions inutilisées

Basée sur :

* absence d’usage,
* absence de référence,
* ancienneté,
* heuristiques d’usage indirect.

### Niveaux de suspicion

🔴 fort — 🟠 moyen — 🟡 faible — 🟢 sain

---

## **4.3. Détection des fichiers obsolètes**

Basée sur :

* absence d’imports,
* absence de références,
* absence d’exécution,
* ancienneté,
* vide ou quasi vide,
* non-consultation documentée.

---

## **4.4. Analyse documentaire**

Score basé sur :

* âge,
* taille,
* mots-clés “deprecated/obsolete/legacy…“,
* référencement dans README,
* importance probable.

---

## **4.5. Exécution + Logging**

```
jupiter run "ma_commande"
```

→ logs en temps réel
→ sauvegarde structurée
→ diffusion WebSocket en mode serveur

---

# **5. Architecture Logicielle**

```
jupiter/
 ├── core/
 │    ├── scanner.py
 │    ├── incremental.py
 │    ├── analyzer.py
 │    ├── language/
 │    │       ├── python.py
 │    │       ├── js_ts.py
 │    │       └── …
 │    ├── docs.py
 │    ├── runner.py
 │    └── report.py
 ├── server/
 │    ├── api.py
 │    ├── manager.py
 │    ├── ws.py
 │    └── meeting_adapter.py
 ├── web/
 │    ├── index.html
 │    ├── app.js
 │    ├── lang/
 │    └── components/
 ├── cli/
 │    └── main.py
 └── config/
      ├── default.yml
      └── languages.yml
```

---

# **6. Interfaces**

## **6.1. Interface locale**

Via :

```
jupiter gui
```

Inclut :

* tableau de bord,
* arborescence,
* résultats,
* follow-up de fonctions,
* mise à jour incrémentale.

---

## **6.2. Interface web (serveur)**

Fonctionnalités :

* dashboard complet,
* graphes de dépendances,
* heatmaps,
* logs en temps réel,
* multi-projets,
* incrémental,
* suivi de fonction,
* thème dark par défaut + bascule light,
* moteur multi-langue intégré.

---

# **7. Mode Serveur & SSH**

## **7.1. Serveur**

```
jupiter server start
```

Permet :

* API REST complète
* Web UI
* gestion multi-projets
* WebSocket temps réel
* compatibilité Meeting
* scans planifiés

---

## **7.2. SSH**

Commandes :

* `jupiter scan`
* `jupiter update`
* `jupiter watch`
* `jupiter check foo`
* `jupiter run "..."`

---

# **8. Fonctionnalités Avancées**

## **8.1. Mise à jour incrémentale**

```
jupiter update
```

→ ne rescane **que** ce qui a changé
→ met à jour les résultats existants

---

## **8.2. Suivi d’une fonction**

```
jupiter check foo
```

Met à jour :

* nombre d’appels,
* références,
* statut d’usage,
* disparition éventuelle.

---

## **8.3. Mode scan continu**

```
jupiter watch
```

Fonctionnalités :

* file watcher,
* analyse en direct,
* alertes (function appears/disappears),
* mise à jour du rapport.

### Mode avancé : watch + exécution

```
jupiter watch --run "python main.py"
```

→ analyse dynamique réelle du programme.

---

# **9. Multi-langue**

* JSON/YAML de traduction,
* clés unifiées,
* auto-chargement selon langue choisie,
* sélecteur de langue,
* possibilité d’ajouter des langues personnalisées.

---

# **10. Compatibilité Meeting**

## Configuration

```
meeting:
  enabled: true
  deviceKey: "xxx"
```

## Comportement

* Jupiter doit apparaître comme **device online** dans Meeting,
* Meeting doit connaître :

  * statut en ligne,
  * date/heure de dernière détection,
  * état du scan / watch,
* **Système de licence** :

  * si `deviceKey` inconnue → Jupiter fonctionne 10 minutes max.

## Module dédié

```
server/meeting_adapter.py
```

---

# **11. Sorties & Rapports**

* terminal,
* web UI,
* graphiques,
* heatmaps,
* WebSocket live,
* fichiers (reports + logs).

---

# **12. Nouvelles Idées Intégrées**

## **12.1. Analyse qualité du code (optionnelle)**

Détection :

* code dupliqué,
* fonctions trop longues,
* classes trop denses,
* complexité élevée,
* imbrications excessives.

## **12.2. Plugin System / Extensions**

```
jupiter/plugins/
```

Plugins pour :

* nouveaux langages,
* rapports personnalisés,
* connexion à outils externes,
* instrumentation avancée,
* suggestions IA (optionnelles).

## **12.3. Modes d'analyse spécialisés**

* mode sécurité (patterns dangereux),
* mode performance,
* mode dépendances externes.

## **12.4. Simulation de suppression**

```
jupiter simulate remove foo
```

Affiche :

* impact potentiel,
* fichiers cassés,
* dépendances rompues.

## **12.5. Historique et comparaison**

```
jupiter diff scan1 scan2
```

Permet :

* comparaison de scans,
* suivi historique de l’évolution.

## **12.6. Support polyglotte**

Détection automatique des langages du projet.

## **12.7. API interne Python**

```python
import jupiter
project = jupiter.Project("path")
report = project.scan()
```

## **12.8. Live Map UI**

* Carte interactive,
* mise à jour en direct,
* température d’usage du code.

## **12.9. Notifications et webhooks (plugin)**

Email **non prioritaire**, mais possible via plugin.

## **12.10. Profil par projet**

```
.jupiter.yml
```

## **12.11. Supervision multi-projets**

Dashboard global.

## **12.12. Auto-mise-à-jour**

* depuis le repo Git,
* depuis un ZIP téléchargé.

---

# **13. Questions en suspens (à décider ultérieurement)**

* niveau de sécurité / sandboxing souhaité,
* niveau exact d’instrumentation dynamique,
* degré d’accès exposé par API Meeting,
* périmètre futur de l’IA optionnelle,
* granularité du profiling dynamique.

---

# **14. Conclusion**

Ce fichier est la **référence officielle** et complète du Projet Jupiter.
Tous les ajouts sont intégrés, aucune section supprimée, tout est consolidé et extensible.
