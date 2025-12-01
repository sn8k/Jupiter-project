# Changelog – Run Modal Enhanced

## 2025-12-01 – Amélioration majeure de la modale Run

### Résumé
Refonte complète de la modale "Exécuter une commande" pour la rendre plus pratique, intuitive et professionnelle.

### Nouvelles fonctionnalités

#### 1. Commandes prédéfinies (Presets)
- Grille de boutons pour les commandes les plus courantes :
  - `pytest` : Lancer les tests Python
  - `coverage` : Tests avec couverture de code
  - `main.py` : Lancer le script principal
  - `npm dev` : Serveur de développement NPM
  - `mypy` : Vérification de types
  - `flake8` : Linter Python

#### 2. Historique des commandes
- Dropdown listant les 20 dernières commandes exécutées
- Sélection rapide depuis l'historique
- Bouton pour effacer l'historique
- Option pour désactiver la sauvegarde dans l'historique

#### 3. Dossier de travail (CWD)
- Champ pour spécifier un répertoire de travail personnalisé
- Bouton **Parcourir** pour sélectionner visuellement
- Bouton de réinitialisation rapide
- Par défaut : racine du projet

#### 4. Interface améliorée
- Zone de sortie avec header et actions (copier, effacer)
- Indicateur visuel de l'état d'exécution (animation)
- Coloration selon le code de retour (vert = succès, rouge = erreur)
- Emojis pour une meilleure lisibilité de la sortie

### Fichiers modifiés

#### Frontend
- `jupiter/web/index.html` : Nouvelle structure HTML de la modale
- `jupiter/web/styles.css` : ~150 lignes de styles pour la modale améliorée
- `jupiter/web/app.js` :
  - `initRunModal()` : Initialisation de la modale
  - `runCommand()` : Refactorisation avec support CWD
  - `getRunHistory()`, `addToRunHistory()`, `populateRunHistory()` : Gestion de l'historique
  - `clearRunHistory()` : Effacement de l'historique
  - `openRunCwdBrowser()` : Ouverture du navigateur pour CWD
  - Nouvelles actions : `browse-run-cwd`, `reset-run-cwd`, `clear-run-output`, `copy-run-output`, `clear-run-history`

#### Backend
- `jupiter/server/models.py` : Ajout du champ `cwd` dans `RunRequest`
- `jupiter/server/routers/system.py` : Passage du CWD au connector
- `jupiter/core/connectors/base.py` : Signature mise à jour avec `cwd: Optional[str]`
- `jupiter/core/connectors/local.py` : Implémentation du support CWD
- `jupiter/core/connectors/remote.py` : Support CWD pour appels distants
- `jupiter/core/connectors/generic_api.py` : Signature compatible

#### Traductions (i18n)
- `jupiter/web/lang/fr.json` : 15 nouvelles clés pour la modale
- `jupiter/web/lang/en.json` : 15 nouvelles clés traduites

### Stockage localStorage
- `jupiter_run_command` : Dernière commande
- `jupiter_run_dynamic` : État de l'analyse dynamique
- `jupiter_run_cwd` : Dernier CWD utilisé
- `jupiter_run_history` : Tableau JSON des commandes récentes

### Notes techniques
- L'historique est limité à 20 entrées
- Les doublons sont automatiquement dédupliqués (la commande remonte en tête)
- Le CWD peut être relatif (résolu par rapport à la racine projet) ou absolu
- Le navigateur de dossiers réutilise le composant existant (`browser-modal`)
