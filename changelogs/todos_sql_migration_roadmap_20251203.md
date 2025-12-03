# Changelog – TODOs/sql_migration_roadmap.md

## v0.1.0
- Création de la roadmap SQL décrivant les phases 0 à 7 pour migrer Jupiter vers un stockage SQL automatisé (init/migrations/backup).
- Définition du schéma cible (projects, snapshots, scan_files, analysis, plugins, jobs, events, settings, migrations) et des principes (mode hybride, SQLite par défaut, PostgreSQL optionnel).
- Planification des impacts sur History/cache, Bridge/plugins/jobs, API/CLI/WebUI, sécurité/sauvegardes et décommission du stockage fichier.
