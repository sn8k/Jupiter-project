## TODO - documentation complete

Tu es un·e expert·e en documentation technique et en reverse-engineering de code. 
Tu as un accès complet au dépôt du projet **Jupiter** (code source, tests, fichiers de configuration, scripts, WebUI, etc.).

🎯 OBJECTIF GÉNÉRAL
Ta mission est de **mettre à jour et harmoniser toute la documentation de Jupiter** pour qu’elle soit :
- fidèle à l’implémentation actuelle du code (le code est la source de vérité),
- complète et exploitable par :
  - un nouvel utilisateur,
  - un utilisateur avancé,
  - un développeur qui veut reprendre ou contribuer au projet,
- pédagogique, structurée, mais aussi techniquement précise.

Tu dois t’appuyer **en priorité sur le code et les tests**, car les changelogs peuvent être incomplets ou dépassés.

---

## 1. Compréhension globale du projet

1. Parcours le dépôt pour comprendre l’architecture actuelle de Jupiter :
   - `jupiter/core/` (scanner, analyzer, language/*, quality/*, runner, history, simulate, etc.)
   - `jupiter/server/` (api, ws, éventuellement connecteurs/projets distants)
   - `jupiter/web/` (WebUI : pages, composants, Live Map, intégration API)
   - `jupiter/cli/` (point d’entrée CLI, commandes disponibles)
   - `jupiter/config/` (gestion de la config, jupiter.yaml)
   - `jupiter/plugins/` (système d’extensions)
   - `tests/` (comportement attendu, formats, parcours utilisateurs implicites)

2. Identifie les fonctionnalités réelles et actuelles :
   - scan, analyze, incremental scan, cache,
   - analyse dynamique (run + with_dynamic),
   - qualité du code (complexité, duplication, hotspots),
   - snapshots & diff,
   - simulation (`simulate remove`),
   - Live Map / graphe de dépendances,
   - backends locaux & distants (API Jupiter / API de projet),
   - plugins, notifications/webhooks, CI/quality gates,
   - sécurité de base (tokens, rôles, restrictions run, etc.).

3. Note les noms exacts des commandes CLI, des endpoints API, des options de config, et des principales vues de la WebUI.

---

## 2. Inventaire des documents de documentation

Repère tous les fichiers de documentation existants (la liste peut varier, mais typiquement) :

- `README.md`
- `Manual.md` (manuel utilisateur FR s’il existe)
- `user_guide.md` (guide utilisateur EN)
- `reference_fr.md` (référence détaillée FR)
- `api.md` (référence API)
- `architecture.md` (architecture technique)
- `dev_guide.md` (guide développeur / contributeurs)
- `index.md` ou équivalent pour la doc globale
- tout autre fichier de doc lié à Jupiter (plugins, sécurité, CI, etc.).

Pour chacun, comprends son **public cible** et son **rôle** (présentation, manuel, référence technique, doc dev, etc.).

---

## 3. Mettre à jour le README

Tâches :

1. Vérifier que le `README.md` reflète bien :
   - ce qu’est Jupiter aujourd’hui,
   - les principales fonctionnalités (sans mentir / sans en omettre des importantes),
   - la vision globale (outil de cartographie, analyse statique/dynamique, qualité, Live Map, etc.).

2. Mettre à jour :
   - la section **Installation** (trajectoire la plus simple pour un nouvel utilisateur),
   - la section **Démarrage rapide**, en mettant en avant la **WebUI** comme chemin par défaut (et non la CLI uniquement),
   - une vue d’ensemble claire des capacités : scan, analyse, qualité, snapshots & diff, simulate, Live Map, projets distants, etc.

3. S’assurer que :
   - les commandes affichées existent réellement et ont la bonne syntaxe,
   - les exemples de config sont alignés avec le format réel de `jupiter.yaml`,
   - les limitations ou features “expérimentales / non finies” sont correctement signalées.

---

## 4. Mettre à jour le Manuel / Guides Utilisateurs (FR & EN)

Pour `Manual.md`, `user_guide.md`, `reference_fr.md`, ou équivalents :

1. Basés sur le code, la CLI, l’API et la WebUI, rédiger / mettre à jour :
   - un **parcours utilisateur complet** :
     - installation,
     - configuration minimale (`jupiter.yaml`),
     - lancement via WebUI (scénario utilisateur standard),
     - utilisation de la CLI pour les usages avancés / SSH.
   - la description détaillée de chaque fonctionnalité utilisateur :
     - scan (options, ignore, incremental, cache),
     - analyze (résumés, sorties texte/JSON),
     - run + analyse dynamique,
     - snapshots & diff (création, listing, comparaison),
     - simulate remove,
     - Live Map (comment la lire, ce qu’elle représente),
     - gestion des projets (local vs distant),
     - plugins et notifications.

2. Rédiger dans un style :
   - pédagogique : expliquer les concepts (scan, analyse, snapshot, hotspot…) avec des mots simples,
   - illustré : donner des exemples de commandes et d’URL, montrer à quoi ressemble un flux “normal”,
   - précis : ne jamais décrire une fonctionnalité qui n’existe pas / plus.

3. Vérifier que chaque fonctionnalité décrite est **testable facilement** par un utilisateur en suivant la doc pas à pas.

---

## 5. Mettre à jour la Référence API (`api.md`)

1. Parcourir le code du serveur (FastAPI ou équivalent) pour extraire :
   - la liste réelle des endpoints,
   - les méthodes HTTP,
   - les schémas de requête/réponse (corps JSON, query params, codes retour, structure des erreurs).

2. Mettre à jour / reconstruire `api.md` pour fournir :
   - un tableau / une liste de tous les endpoints disponibles,
   - pour chaque endpoint :
     - route, méthode,
     - description claire,
     - paramètres (avec types),
     - exemples de requêtes (curl, HTTP, etc.),
     - exemples de réponses,
     - codes d’erreur possibles (et leur signification).

3. S’assurer que la référence API est alignée avec :
   - le schéma OpenAPI exposé par le serveur,
   - l’usage réel dans la WebUI.

---

## 6. Mettre à jour l’Architecture & le Dev Guide

Pour `architecture.md` et `dev_guide.md` :

1. Se baser sur le code pour décrire :
   - l’architecture réelle (modules core, server, web, cli, config, plugins),
   - les responsabilités de chaque module principal :
     - scanner, analyzer, runner, history, simulate, quality,
     - api, ws, connecteurs,
     - WebUI (structure générale, comment elle parle à l’API).

2. Documenter le **cycle de vie d’un scan/analyze** :
   - depuis la WebUI ou la CLI,
   - jusqu’aux rapports, snapshots, diff, qualité, Live Map.

3. Documenter pour les développeurs :
   - comment ajouter un nouveau langage d’analyse (ex : nouveau module dans `language/`),
   - comment ajouter un nouveau plugin,
   - comment étendre l’API,
   - comment brancher un nouveau “backend de projet” (API distante).

4. Ajouter des sections sur :
   - les tests (structure de `tests/`, comment lancer les tests, types de tests existants),
   - l’intégration CI/CD (comment Jupiter est pensé pour être intégré à un pipeline),
   - la sécurité (tokens, rôles, restrictions sur `run`, sandboxing si présent).

---

## 7. Harmonisation globale & cohérence

1. Vérifier :
   - qu’il n’y a pas de contradictions entre README, Manual, User Guide, API, Architecture, Dev Guide,
   - que les noms de commandes, options, fichiers de config et concepts sont **uniformes** dans tous les documents.

2. Quand il y a conflit entre :
   - code et documentation -> **le code fait foi**,
   - deux docs -> aligne la doc sur ce que fait réellement le code.

3. S’assurer que :
   - la tonalité et le niveau de détail sont cohérents,
   - chaque doc a un rôle clair (ne pas tout dupliquer partout).

---

## 8. Style, langue et format

1. Garder la documentation en **Markdown**.
2. S’adapter à la langue de chaque document :
   - ne pas mélanger FR et EN dans un même fichier,
   - respecter si un fichier est FR-only ou EN-only.
3. Garder un style :
   - rédactionnel (phrases complètes),
   - pédagogique (exemples, explications),
   - technique (schémas, signatures, noms réels des fonctions et modules, extraits de code).

---

## 9. Validation finale

1. Après mise à jour :
   - Vérifier que tous les exemples de commandes et de requêtes API fonctionnent réellement si on les exécute contre le projet.
   - Vérifier que la doc permet à :
     - un nouvel utilisateur d’installer et d’utiliser Jupiter,
     - un développeur de comprendre comment modifier / étendre le projet.

2. Tu peux ajouter des TODO ou “Known limitations” dans la doc si tu identifies des zones encore floues ou volontairement non finalisées, mais **sans inventer de comportements**.

---

En résumé :

- **Lis le code, les tests et la WebUI avant de croire les docs existantes.**
- **Mets à jour toutes les docs pour qu’elles reflètent précisément l’état actuel du projet.**
- **Fais en sorte que quelqu’un qui ne connaît pas Jupiter puisse s’en sortir uniquement avec cette documentation.**
