# Changelog - docs/PLUGIN_MIGRATION_GUIDE.md

Ce fichier documente les modifications apportées au guide de migration des plugins.

## [0.2.0] - Exemples concrets de migration

### Ajouté
- **Section 9.1** : Exemple complet de migration d'un plugin d'analyse de complexité
  - Code v1 avant migration (fichier unique avec hooks)
  - Code v2 après migration (structure modulaire complète)
  - Manifest plugin.yaml avec permissions et UI
  - Point d'entrée __init__.py avec IPlugin, IPluginHealth, IPluginMetrics
  - Logique métier isolée dans analyzer.py
  - Routes API dans server/api.py
  - Fichiers de traduction i18n (en.json, fr.json)

- **Section 9.2** : Points clés de la migration
  - Tableau comparatif v1 vs v2
  - Couverture: structure, config, hooks, API, UI, i18n, permissions, santé, métriques

- **Section 9.3** : Checklist de migration
  - Liste complète des étapes pour migrer un plugin
  - Sections: Préparation, Fichiers requis, Migration du code, Contributions, Validation

- **Section 9.4** : Référence vers plugin settings_update comme exemple système

## [0.1.0] - Création initiale

### Ajouté
- Vue d'ensemble de la migration
- Différences v1 vs v2
- Structure d'un plugin v2
- Création du manifest
- Migration du code
- Enregistrement des contributions
- Adaptateur legacy
- Tests et validation
