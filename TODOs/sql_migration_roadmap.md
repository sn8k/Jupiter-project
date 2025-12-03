# Roadmap – Migration Jupiter vers stockage SQL

Version : 0.1.0  
Statut : Brouillon initial (à affiner avec l’équipe backend)

## Contexte et périmètre

- Sources analysées : `docs/architecture.md`, `docs/dev_guide.md`, `docs/user_guide.md`, `docs/plugins_architecture.md`, `docs/plugins.md`, `docs/PLUGIN_MIGRATION_GUIDE.md`.
- Stockage actuel : snapshots et rapports dans `.jupiter/snapshots/`, cache incrémental dans `.jupiter/cache/`, configs projet dans `<project>.jupiter.yaml`, configs plugins dans `jupiter/plugins/<id>/config.yaml` avec overrides projet, logs dans `logs/`, métriques/états épars en mémoire.
- Cibles SQL : centraliser l’historique, les métadonnées de scan/analyse, les configs effectives fusionnées, les états plugins, les jobs/events, et l’index des projets/backends.
- Contraintes : base gérée automatiquement par Jupiter (init/migrations/sauvegardes), option par défaut embarquée (SQLite) et option serveur (PostgreSQL) sans dépendances externes forcées.

## Principes directeurs

- Séparation nette entre couche d’accès aux données (DAL) et logique métier : tous les modules (`history`, `cache`, `plugins`, `server`, `watch`) passent par une façade SQL.
- Migration progressive et réversible : mode miroir fichier+SQL au début, bascule complète après validation.
- Portabilité : SQLite par défaut, PostgreSQL optionnel ; aucun driver exotique.
- Observabilité intégrée : métriques de pool, temps de requêtes, taille DB, migrations appliquées, surface d’alertes dans l’autodiag.
- Sécurité : contrôle des permissions pour les opérations mutantes, chiffrement optionnel au repos (au moins pour SQLite via PRAGMA), sauvegardes automatisées versionnées.

## Schéma cible (brouillon)

- `projects` : id, name, root_path, backend_type, config_json, created_at, updated_at.
- `snapshots` : id, project_id, label, backend_name, created_at, summary_json, storage_ref (chemin legacy ou blob), source_version.
- `scan_files` : snapshot_id, path, hash, size, mtime, language, flags (ignored, binary, test).
- `analysis` : snapshot_id, metrics_json (hotspots, qualité, duplication, unused functions scores).
- `dynamic_runs` : id, snapshot_id, command, exit_code, duration_ms, trace_summary_json.
- `plugins` : id, version, type (core/system/tool), state, manifest_json, config_effective_json, health, last_error.
- `plugin_events` : id, plugin_id, topic, payload_json, created_at.
- `jobs` : id, plugin_id (nullable), kind, state, progress, payload_json, created_at, updated_at, error.
- `users` / `tokens` (si RBAC activé) : role, hashed_token, created_at, last_used_at.
- `settings` : key, value_json, scope (global/project/plugin), version.
- `migrations` : id, applied_at, checksum, status, logs (pour audit et autodiag).

## Phases de migration

### Phase 0 – Préparation et cadrage
- Valider la cible SQLite par défaut + support PostgreSQL optionnel.
- Choisir l’ORM/minimal DAL : privilégier SQLModel/SQLAlchemy ou couche maison fine (pas de dépendance lourde).
- Définir la stratégie de versioning DB (table `migrations`) et le format des migrations (SQL brut + scripts Python).
- Spécifier les SLA internes : temps max init DB, temps max migration, taille maximale snapshots compressés.
- Définir la politique de sauvegarde : rotation locale (N dernières), export CLI (`jupiter db backup/restore`).

### Phase 1 – Couche d’abstraction SQL
- Créer un module `jupiter/core/storage/` :
  - `engine.py` : création/gestion des connexions, pooling, réglages SQLite/PG.
  - `migrations.py` : application des migrations embarquées, validation checksum.
  - `dal.py` : primitives CRUD typées (Projects, Snapshots, Plugins, Jobs, Settings).
- Ajouter un auto-diagnostic DB (connectivité, version, migrations en retard, espace disque, intégrité PRAGMA).
- Exposer un toggle `storage.mode = filesystem|sql|hybrid` dans la config globale/projet.

### Phase 2 – Schéma initial et bootstrap automatique
- Livrer un lot de migrations v1 créant les tables du schéma cible minimal (projects, snapshots, scan_files, analysis, plugins, jobs, settings, migrations).
- Implémenter l’initialisation automatique au démarrage de la CLI/API :
  - Création du fichier SQLite dans `.jupiter/storage/jupiter.db` (ou DSN PG).
  - Application des migrations manquantes.
  - Seed des paramètres par défaut dans `settings`.
- Ajouter commandes CLI : `jupiter db info`, `db migrate`, `db backup`, `db restore`, `db vacuum` (SQLite).

### Phase 3 – Migration des historiques et caches
- Adapter `HistoryManager` pour écrire en SQL (table `snapshots` + `scan_files`) tout en conservant l’export JSON pour compat.
- Ajouter un job de migration `filesystem -> SQL` :
  - Scan des archives `.jupiter/snapshots/` et import progressif avec reprise.
  - Vérification d’intégrité (hash/compte de fichiers) et journalisation.
- Implémenter le mode hybride (double écriture) puis un flag pour couper le legacy après validation.
- Déplacer le cache incrémental (`.jupiter/cache/`) vers une table `cache_entries` (clé chemin/hash/mtime).

### Phase 4 – Plugins, jobs et événements
- Persister l’état des plugins (manifests, configs fusionnées, health) dans `plugins`.
- Router le bus d’événements du Bridge vers `plugin_events` avec TTL/rotation.
- Persister les jobs du Bridge (`jobs` table) avec reprise après crash.
- Exposer l’état via API `/plugins`, `/jobs`, `/events` alimentés par SQL.

### Phase 5 – API, CLI et WebUI
- API : ajouter endpoints `/db/status`, enrichir `/snapshots`, `/plugins`, `/jobs` pour lire/écrire en SQL.
- CLI : refondre les commandes `snapshots`, `watch`, `plugins` pour consommer SQL et afficher l’état DB.
- WebUI : connecter l’historique, la Live Map et les panneaux plugins au backend SQL (pagination côté DB).

### Phase 6 – Sécurité, sauvegarde et maintenance
- Intégrer RBAC/token store dans SQL (optionnel) et audits des actions sensibles.
- Implémenter sauvegardes locales planifiées (tâche cron interne) avec rotation et vérification de checksum.
- Exposer des hooks de maintenance : vacuum/analyze pour SQLite, `pg_stat` résumé pour PG.
- Ajouter alertes dans l’autodiag (espace disque faible, migrations en attente, erreurs de connexion).

### Phase 7 – Décommission du stockage fichier
- Basculer le mode par défaut sur `sql`.
- Ajouter une commande `jupiter db finalize-filesystem` qui marque la fin du mode hybride et archive les anciens snapshots.
- Nettoyer `.jupiter/snapshots/` et `.jupiter/cache/` après confirmation utilisateur et backup automatique.

## Risques et points d’attention

- Taille des snapshots : nécessite compression ou externalisation du blob (conserver un champ `storage_ref` pour pointer vers un fichier compressé si nécessaire).
- Concurrence : gérer les verrous SQLite (mode WAL) pour watch + API + CLI simultanés.
- Rétrocompatibilité : maintenir la lecture des snapshots JSON existants le temps de la migration.
- Performance : indexer `scan_files` (path, snapshot_id), `plugin_events` (topic, created_at), `jobs` (state).
- Testabilité : prévoir des fixtures DB épurées pour les tests unitaires, et un faux moteur en mémoire (`sqlite:///:memory:`).

## Livrables attendus par phase

- Spécifications et schéma finalisés (Phase 0).
- Module `core/storage` + migrations v1 + commandes CLI DB (Phase 2).
- Mode hybride History/cache + importeur legacy (Phase 3).
- Persistance Bridge/plugins/jobs + API/CLI ajustés (Phase 4-5).
- Playbook ops (sauvegarde, vacuum, restore) + alertes autodiag (Phase 6).
- Plan de coupure legacy et procédure de rollback (Phase 7).
