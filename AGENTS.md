## Directives pour GPT-5 / Codex – Projet Jupiter

Ce document définit les **lignes directrices**, **règles de codage** et **attentes de normalisation** pour un agent GPT-5 / Codex travaillant sur le projet **Jupiter** (et, plus largement, sur des outils proches).

L’objectif est que l’agent produise un code **cohérent**, **maintenable**, **prévisible** et **aligné avec la vision du projet**.

---

## 1. Rôle de l’agent

L’agent est :

* un **assistant de développement** pour Jupiter ;
* spécialisé sur :

  * le **backend** (surtout Python),
  * la **CLI**,
  * l’API serveur,
  * les scripts de scan / analyse,
  * frontend web (JS/TS).


L’agent doit toujours :

1. Respecter l’architecture définie dans le document de référence de Jupiter.
2. Privilégier Python (langage prioritaire).
3. Garder le projet simple, léger et extensible.
4. Documenter suffisamment pour qu’un humain reprenne facilement la main.
5. Si une TODO list cochable est fournie, prendre en charge les taches via la TODO, et mettre a jour la TODO UNIQUEMENT en cochant les cases des taches effectivement terminées.
6. chaque fichier doit avoir son changelog dedié.
7. mise à jour systematique des fichiers README.md, requirements.txt, changelogs.
8. Une documentation globale (root/Manual.md) doit etre rédigée et mise à jour systematiquement.

---

## 2. Langages & Priorités

1. **Python** : langage principal.

   * Utilisé pour : `core/`, `server/`, `cli/`, plugins, outils internes.
2. **JavaScript / TypeScript** :

   * Utilisé pour : frontend web (`web/`), interactions API.
3. **Autres langages** :

   * Potentiellement supportés plus tard via plugins.
   * L’agent ne doit pas introduire d’autres langages dans le cœur du projet sans raison forte.

---

## 3. Style de code Python

### 3.1. Conventions générales

* Respecter **PEP 8** (avec pragmatisme).
* Utiliser des **noms explicites** :

  * fonctions/méthodes : `snake_case`
  * variables : `snake_case`
  * classes : `CamelCase`
  * constantes : `UPPER_SNAKE_CASE`
* Éviter les abréviations obscures.

### 3.2. Types & signatures

* Utiliser les **annotations de types** partout (Python 3.10+).
* Exemple :

```python
from pathlib import Path
from typing import Iterable, List

def scan_project(root: Path) -> List[Path]:
    ...
```

* Préférer `list[str]`, `dict[str, Any]` si la version Python cible le permet.

### 3.3. Docstrings & commentaires

* Docstrings **pour toutes les fonctions publiques** :

  * Format simple, inspiré Google ou NumPy, sans être rigide.
* Commentaires :

  * Explication **du “pourquoi”**, pas seulement du “comment”.
  * Commenter les heuristiques, choix non évidents, limites.

Exemple :

```python
def detect_unused_functions(file_ast: ast.AST) -> list[str]:
    """
    Analyse l'AST d'un fichier et renvoie la liste des fonctions
    qui semblent ne jamais être appelées.

    Limites :
    - Ne détecte pas les usages via reflection ou import dynamique.
    """
```

### 3.4. Gestion des erreurs

* **Ne pas** masquer les erreurs silencieusement.
* Utiliser des exceptions claires, idéalement spécifiques au projet (ex. `JupiterError`, `ScanError`).
* Loguer les erreurs dans les couches appropriées (`runner`, `server`, etc.).

### 3.5. Logging

* Utiliser le module standard `logging`.
* Pas de `print()` dans le code de prod, sauf :

  * code CLI,
  * mode debug très explicite.
* Prévoir des niveaux : `DEBUG`, `INFO`, `WARNING`, `ERROR`.

---

## 4. Structure originelles des modules Jupiter (soumi a modifications)

L’agent doit respecter et renforcer la structure suivante :

```text
jupiter/
 ├── core/
 │    ├── scanner.py          # scan statique
 │    ├── incremental.py      # mise à jour ciblée
 │    ├── analyzer.py         # analyse et heuristiques
 │    ├── language/
 │    │       ├── python.py   # analyseur Python (prioritaire)
 │    │       └── ...         # autres langages via modules séparés
 │    ├── docs.py             # analyse de documentation
 │    ├── runner.py           # exécution + logs
 │    └── report.py           # génération de rapports
 ├── server/
 │    ├── api.py              # API HTTP
 │    ├── manager.py          # gestion des projets
 │    ├── ws.py               # WebSocket pour temps réel
 │    └── meeting_adapter.py  # intégration Meeting (licence + présence)
 ├── web/
 │    ├── index.html
 │    ├── app.js              # ou app.ts
 │    ├── lang/               # fichiers de traduction
 │    └── components/
 ├── cli/
 │    └── main.py             # interface CLI
 └── config/
      ├── default.yml         # config par défaut
      └── languages.yml       # infos langues / i18n
```

Règles :

* Ne pas inventer une structure radicalement différente.
* Si un nouveau module est nécessaire, le placer dans l’espace logique le plus pertinent (ex : nouvelle analyse → `core/analyzer_*.py` ou sous-module).
* Respecter la séparation :

  * **core** : logique métier,
  * **server** : exposition réseau,
  * **web** : UI,
  * **cli** : interface ligne de commande,
  * **config** : configuration.

---

## 5. CLI & UX en ligne de commande

### 5.1. Commandes clés

L’agent doit garder en tête les commandes prévues :

* `jupiter scan`
* `jupiter update`
* `jupiter watch`
* `jupiter check <fonction>`
* `jupiter run "<commande>"`
* `jupiter server start`

### 5.2. Implémentation CLI

* Utiliser un framework léger :

  * `argparse` acceptable pour MVP,
  * `typer` ou `click` possible si validé, mais ne pas ajouter de dépendance lourde sans justification.
* Messages :

  * clairs, concis, cohérents,
  * respectant la logique multi-langue (pas de textes en dur quand c’est critique pour l’UI).

---

## 6. API & serveur

### 6.1. Style API

* REST simple, JSON.
* Endpoints prévisibles, versionnés si besoin (ex. `/api/v1/projects`).
* Réponses structurées : ne pas renvoyer des objets Python bruts, mais des dicts JSON.

### 6.2. Framework serveur

* Utiliser un framework Python léger (FastAPI ou équivalent) si nécessaire.
* L’agent doit être cohérent : ne pas mélanger plusieurs frameworks backend pour des tâches similaires.

---

## 7. Frontend (web)

### 7.1. Objectifs

Le frontend :

* affiche les résultats Jupiter,
* permet de lancer des scans, updates, watch,
* gère le multi-langue,
* respecte le **thème dark par défaut**, avec possibilité de passer en light.
* doit etre en developpement synchrone avec le reste du projet. Si c'est dans la CLI, ca doit etre sur le frontend, et inversement.

### 7.2. Style

* Code JS/TS clair, modulaire.
* Éviter les frameworks lourds par défaut (React/Vue/etc.) tant que non validé.
* Utiliser des composants simples, découplés, faciles à maintenir.

### 7.3. i18n

* Tous les textes affichés doivent provenir des fichiers de traduction (`web/lang/*.json`).
* Ne pas “hardcoder” les phrases dans le code, sauf cas très spécifique / technique.

---

## 8. Plugins & extensibilité

### 8.1. Système de plugins

L’agent peut proposer un système de plugins, mais doit :

* le rendre **simple à comprendre**,
* clairement séparer le cœur de Jupiter des extensions,
* éviter de coupler fortement un plugin au noyau.

Exemple de structure :

```text
jupiter/
 └── plugins/
       ├── code_quality/
       ├── security/
       └── notify_webhook/
```

**A TERME, LA PLUPART DES FONCTIONS DE JUPITER DEVRONT MIGRER VERS DES PLUGINS**

### 8.2. IA en option

* Toute fonctionnalité IA doit être **optionnelle**.
* L’agent ne doit pas supposer que l’IA est disponible ou activée.
* Les modules IA doivent être isolés (ex. `plugins/ai_*.py`).

---

## 9. Gestion de l’intégration Meeting

### 9.1. Rappels fonctionnels

* Jupiter peut déclarer une `deviceKey`.
* Si Meeting ne connaît pas la `deviceKey`, Jupiter fonctionne sur une durée limitée (timer, ex. 10 minutes).
* Meeting doit pouvoir :

  * voir si Jupiter est online,
  * voir depuis quand.

### 9.2. Règles pour l’agent

* Toute logique Meeting reliée à Jupiter doit passer par `server/meeting_adapter.py`.
* Ne pas disperser la logique licence ou présence dans tout le code.
* Prévoir une **dégradation gracieuse** : Jupiter doit rester utilisable en mode restreint même sans Meeting.

---

## 10. Sécurité & prudence

Même si certaines décisions sont “à décider plus tard”, l’agent doit :

* éviter d’introduire des surfaces d’attaque évidentes (ex : exécution de commande non filtrée sans avertissement),
* isoler autant que possible :

  * exécution de commandes utilisateur (module `runner`),
  * exposition d’API sensibles,
* commenter clairement tout endroit où une future **sandbox** ou **restriction** sera nécessaire.

---

## 11. Tests & validation

L’agent doit encourager :

* l’écriture de tests unitaires pour les modules critiques (`core/`, `server/`),
* l’utilisation de tests simples, lisibles, peu magiques,
* des exemples concrets dans la documentation ou docstrings.

Il peut proposer :

* des tests pytest,
* des scénarios d’intégration minimalistes.

---

## 12. Qualité, simplicité, lisibilité

Règles d’or :

1. **Faire simple avant tout.**
2. Préférer une solution claire à une solution “clever”.
3. Un autre dev doit comprendre le code **sans** l’agent.
4. Les heuristiques doivent être :

   * isolées,
   * documentées,
   * faciles à ajuster.

---

## 13. Auto-mise à jour

L’agent peut proposer un système de mise à jour :

* via téléchargement d’un ZIP depuis un repo,
* via `git pull`,
* avec validation minimale (ex. vérifier version).

Règles :

* la mise à jour doit être **explicite** (jamais automatique sans action utilisateur),
* l’agent ne doit pas inventer de mécanisme opaque.

---

## 14. Style de réponse de l’agent (dans les discussions)

Quand l’agent produit du code ou des propositions :

1. **Toujours** fournir du code complet / exécutable ou facilement intégrable (éviter les bribes incomplètes).
2. Mentionner où placer le code dans l’arborescence (`core/scanner.py`, `cli/main.py`, etc.).
3. Expliquer brièvement les choix structurants.
4. Signaler les limitations / TODO si quelque chose est partiel.

Exemple de réponse idéale :

* Explication courte du contexte,
* Proposition de fichier ou de fonction,
* Bloc de code complet,
* Notes sur l’intégration.

---

Ce fichier `agents.md` sert de **référence opérationnelle** pour tout agent amené à travailler sur Jupiter.
L’agent doit y revenir mentalement pour vérifier :

* le style,
* les conventions,
* les attentes,
* la structure globale,

avant de générer du code ou des modifications.


Note finale du patron : 
**IMPERATIF : A CHAQUE FICHIER MODIFIé, MEME POUR UN FIX, IL FAUT :

- mettre a jour VERSION
- mettre a jour SANS METTRE DE DATES le changelog du fichier (dans le dossier changelogs)  !!
- mettre a jour SANS METTRE DE DATES les versions des fichiers modifiés. en cas d'absence, en ajouter un en docstring.
- mettre a jour SANS METTRE DE DATES les documentations du dossier docs (si necessaire) et README.MD
- requirements*.txt doivent TOUJOURS ETRE A JOUR, AJOUTER SYSTEMATIQUEMENT LES REQUIREMENTS NECESSAIRES !!!!!!!!!
- ne jamais contourner un probleme, le corriger à la source
- jupiter doit toujours etre en mesure de s'autodiagnostiquer, si besoin, utiliser l'auto-diagnostic pour etre certain que jupiter soit parfaitement propre**