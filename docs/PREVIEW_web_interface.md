# 📘 **UI-GUIDE.md — Lignes directrices pour l’interface Jupiter**

Ce document définit toutes les règles, attentes, conventions et comportements de l’interface utilisateur du projet Jupiter.
Il concerne :

* l’**interface web** (mode serveur),
* l’**interface locale** (mode `jupiter gui`),
* la **cohérence UI globale**,
* l’expérience utilisateur,
* les composants,
* les pages principales,
* les comportements dynamiques,
* les règles de traduction et de thèmes.

L’objectif : avoir une interface **cohérente**, **fonctionnelle**, **moderne**, **minimaliste**, **thématisée**, et **intégralement traduisible**.

---

# 1. Objectifs UX principaux

L’interface Jupiter doit être :

### ✔ **Intuitive**

Un utilisateur doit comprendre les informations immédiatement.

### ✔ **Lisible**

Priorité absolue à la lisibilité des informations techniques (scans, dépendances, heatmaps…).

### ✔ **Minimaliste**

Pas de menus inutiles, pas de boutons superflus, pas de animations parasites.

### ✔ **Sobre & moderne**

Design sombre par défaut, angles doux, interface respirante.

### ✔ **Extensible**

Chaque panneau doit pouvoir évoluer (plugins, vues techniques additionnelles…).

### ✔ **Accessible**

Interface claire même sur petits écrans (responsive minimal).

### ✔ **Polyglotte**

Toute la surface UI doit passer par le système de traduction.

---

# 2. Identité visuelle / Design system

## 2.1. Thème général

### 🎨 **Thème par défaut : Dark**

* Fond anthracite/graphite (#111 à #151).
* Surfaces secondaires : gris foncé (#1d1d1d → #232323).
* Accents colorés discrets (bleu/gris).

### ☀️ **Thème optionnel : Light**

* Fond blanc cassé (#f8f8f8).
* Surfaces secondaires gris clair (#eaeaea).
* Accents bleus/gris légers.

## 2.2. Typographie

* Police principale : **Inter**, Roboto ou équivalent.
* Taille standard : 14–16px selon le contexte.
* Hiérarchie claire :

  * Titres : semi-bold
  * Sous-titres : medium
  * Corps : regular

## 2.3. Composants

### Boutons

* Forme : arrondie légèrement (4–6px).
* Couleurs :

  * Primaire : bleu/gris lumineux.
  * Secondaire : gris neutre.
  * Danger : rouge sombre (moins agressif en dark mode).

### Cartes / panneaux

* Fond légèrement contrasté.
* Bords arrondis.
* Ombres discrètes (ne pas exagérer).

### Menus / navbars

* Très sobres.
* Pas plus de 4–6 entrées dans la navigation principale.

### Icônes

* Style minimaliste, outline de préférence.
* Packs recommandés : lucide-icons, feather icons.

---

# 3. Architecture des pages

L'interface se décompose en plusieurs panneaux/pages :

---

## 3.1. Tableau de bord (Dashboard)

### Affiche :

* Statut du projet (ex: "scanné il y a X minutes")
* Boutons principaux :

  * **Scan**
  * **Update**
  * **Watch**
  * **Run**
* Informations rapides :

  * nombre de fichiers,
  * nombre de fonctions suspectes,
  * fichiers obsolètes détectés,
  * état Meeting (licence),
  * statut serveur / uptime.

### Objectif :

**tout voir en un coup d’œil**, sans dérouler de menus.

---

## 3.2. Explorateur de projet (File Explorer)

Arborescence du dossier projet :

* clickable
* collapsible
* fichiers colorés par catégorie :

  * code (bleu),
  * docs (vert),
  * assets (gris),
  * fichiers suspects (orange/rouge).

### Fonctionnalités :

* click → détails du fichier
* double-click → open viewer
* badges :

  * "unused"
  * "legacy"
  * "doc-outdated"
  * "new"

---

## 3.3. Analyse détaillée (Analysis View)

Page principale affichant :

* Fonctions inutilisées
* Fichiers suspects
* Docs obsolètes
* Graphe de dépendances
* Heatmap d’usage en exécution

### Onglets recommandés :

* **Static Analysis**
* **Dynamic Analysis**
* **Dependencies**
* **Code Health**
* **Docs**

Chaque onglet doit afficher :

* un résumé,
* une liste détaillée,
* filtres,
* exports.

---

## 3.4. Fiche “Fonction” (Function Detail View)

Lorsqu’on suit une fonction via `jupiter check foo`, l’UI doit montrer :

* nom
* fichier d’origine
* numéro de ligne
* nombre d’appels
* appels entrants/sortants
* historique
* statut :

  * suspecte
  * utilisée
  * disparue

### Objectif :

faciliter la prise de décision pour suppression/refactoring.

---

## 3.5. Watch / Exécution en direct (Live View)

Page temps réel affichant :

* fonctions appelées en direct (stream via WebSocket)
* fichiers chargés
* modules exécutés
* heatmap dynamique
* timeline de l’exécution

Graphiquement :

* mini “console” live
* zone “appels récents”
* zone “statistiques”

---

## 3.6. Panneau de configuration (Settings)

Le panneau doit contenir :

### 🟦 Configuration générale

* chemin du projet
* langue
* thème (dark/light)
* paramètres de scans automatiques

### 🟩 Analyse

* activer/désactiver analyse Python
* activer/désactiver plugins
* granularité des heuristiques
* seuils “suspecte / obsolète”

### 🟥 Intégration Meeting

* deviceKey
* état licence
* durée de session restante
* test de connexion

### 🟨 Serveur / API

* port
* accès API
* tokens API
* WebSocket

### 🟪 Mise à jour

* check maj
* mise à jour via ZIP
* mise à jour via repo
* historique versions

### 🟫 Avancé

* logs,
* cache,
* scan runtime,
* watchers.

---

# 4. Multi-langue (i18n)

### Règles :

* **Aucun texte en dur** dans l’UI → tout doit venir des fichiers JSON.
* Structure recommandée :

```
lang/
 ├── en.json
 ├── fr.json
 ├── es.json
 ├── de.json
 └── custom/
       └── <user>.json
```

* Toutes les clés doivent être **prefixées** selon leur domaine :

  * `ui.dashboard.title`
  * `ui.settings.language`
  * `action.scan`
  * `status.online`

---

# 5. Comportement général & UX rules

### 5.1. Fluidité

* transitions ultra légères : 100–200ms.
* suppression de toute animation lourde.

### 5.2. Feedback utilisateur

Tout doit donner un retour visuel :

* bouton cliqué,
* scan en cours,
* "mise à jour réussie",
* "watch activé".

### 5.3. Non-bloquant

Toute opération longue doit :

* être asynchrone,
* afficher une progression,
* laisser l’utilisateur naviguer dans l’UI.

### 5.4. Erreurs / alertes

* toujours afficher un message explicite,
* sections possibles :

  * erreur Meeting,
  * erreur de scan,
  * fichier inaccessible,
  * plugin en échec,
* style sobre :

  * rouge discret,
  * icône triangle.

---

# 6. Accessibilité & Responsive

### 6.1. A11y

* contrastes suffisants,
* taille de police ajustable,
* icônes accompagnées de labels.

### 6.2. Responsive

* version tablette obligatoire,
* version mobile facultative (mais possible).

---

# 7. Flux utilisateur (User Flows)

### 7.1. Flux “Scan”

1. Ouverture UI
2. Cliquer “Scan”
3. Animation courte
4. Résultats visibles page Analyse
5. Badge “scan effectué il y a X minutes”

### 7.2. Flux “Watch”

1. Cliquer “Watch”
2. Interface passe en mode “temps réel”
3. Les appels s’affichent instantanément
4. Bouton “Stop watch” visible en permanence

### 7.3. Flux “Run”

1. Choisir commande
2. Exécuter
3. Logs en temps réel s’affichent
4. Résultats intégrés dans l’analyse dynamique

### 7.4. Flux “Fonction suivie”

1. Cliquer sur une fonction
2. Page détaillée
3. Possibilité de marquer comme “à suivre”
4. L’UI se met à jour après scan/update

---

# 8. Modes & États spéciaux

### 8.1. Mode licence Meeting

* timer visible,
* badge “licence valide” ou “mode limité”.

### 8.2. Mode sans serveur

* UI locale réduite,
* certaines fonctionnalités désactivées (ex: multi-projets).

### 8.3. Mode plugins

* panneau “Extensions”
* possibilité d’activer/désactiver plugins

---

# 9. Technologies attendues et contraintes

### Front-end

* HTML/CSS/JS standard
* possibilité d’utiliser Svelte, Vue ou React **uniquement si validé**
* WebSocket pour watch / run

### Back-end

* API REST (FastAPI ou équivalent)
* WebSocket pour streaming

### i18n

* JSON pour traductions
* chargeur automatique côté JS

---

# 10. Synthèse du design attendu (en 10 points)

1. Dark mode par défaut
2. Minimaliste, lisible, moderne
3. Navigation claire (Dashboard → Analyse → Files → Settings)
4. Heatmaps et graphes sobres
5. Messages clairs et traduisibles
6. Panneau de configuration complet
7. Comportements async fluides
8. Watch en temps réel stable
9. Page détaillée pour fonctions et fichiers
10. Extensible par plugins

---

# 11. Conclusion

Ce document constitue la **référence officielle** pour la conception et la cohérence de l’interface utilisateur de Jupiter.
