# Changelog – jupiter/web i18n Dynamic System

## 2025-01 – v1.3.0 – Système i18n dynamique & Fun Language Packs

### Ajouté

#### Métadonnées de version (`_meta`)
- Chaque fichier `lang/*.json` contient désormais un bloc `_meta` :
  ```json
  "_meta": {
    "lang_code": "fr",
    "lang_name": "Français",
    "version": "1.0.0"
  }
  ```
- Permet le suivi de version par langue et l'affichage dans le sélecteur

#### Découverte dynamique des langues (`app.js`)
- `discoverLanguages()` : Parcourt la liste des fichiers connus et extrait les métadonnées
- `populateLanguageSelector()` : Remplit le sélecteur avec "Nom (vX.X.X)"
- `updateLanguageVersionInfo()` : Affiche la version de la langue active sous le sélecteur
- Cache `availableLanguages` pour éviter les requêtes répétées

#### Nouveaux packs de langue (fun)
- 🖖 **Klingon** (`klingon.json`) – Traduction tlhIngan Hol pour les fans de Star Trek
- 🧝 **Sindarin** (`elvish.json`) – Traduction elfique inspirée de Tolkien
- 🏴‍☠️ **Pirate français** (`pirate.json`) – Parler pirate avec "arrr", "mille sabords!"

#### Audit complet des traductions
- `en.json` et `fr.json` : 729 clés chacun en parfaite parité
- Clés ajoutées pour CI, snapshots, options de scan, détails de licence, etc.

### Modifié

#### `index.html`
- Le sélecteur `#conf-ui-lang` est maintenant vide par défaut (peuplé dynamiquement)
- Ajout de `<p id="lang-version-info">` pour afficher la version de la langue

#### `app.js`
- `setLanguage()` utilise désormais les métadonnées pour l'affichage
- `init()` appelle `discoverLanguages()` puis `populateLanguageSelector()` au démarrage
- Tableau `knownLangFiles`: `['fr', 'en', 'klingon', 'elvish', 'pirate']`

### Technique
- Tri des langues : `fr` et `en` en priorité, puis ordre alphabétique
- Le navigateur ne pouvant lister les fichiers d'un dossier, la liste des langues connues est maintenue manuellement dans `knownLangFiles`
- Compatible avec l'ajout futur de nouvelles langues : il suffit d'ajouter le code au tableau

### Fichiers impactés
- `jupiter/web/lang/fr.json` – Ajout `_meta`
- `jupiter/web/lang/en.json` – Ajout `_meta`
- `jupiter/web/lang/klingon.json` – Nouveau fichier
- `jupiter/web/lang/elvish.json` – Nouveau fichier
- `jupiter/web/lang/pirate.json` – Nouveau fichier
- `jupiter/web/app.js` – Logique de découverte et population
- `jupiter/web/index.html` – Sélecteur dynamique + info version
