# Jupiter Documentation (v1.8.5)

Bienvenue dans la documentation Jupiter. Le code fait foi ; cette page référence les guides à jour et leur rôle.

## Sommaire
- `user_guide.md` – Parcours utilisateur complet (GUI + CLI, snapshots, simulation, Live Map, multi-backends).
- `api.md` – Endpoints REST (scan/analyze/ci, snapshots, simulate, projects/config, plugins, Meeting, watch, WS) avec exemples de payloads.
- `architecture.md` – Modules core/server/web/cli/plugins, responsabilités et flux scan → analyse → historique.
- `dev_guide.md` – Points d’extension (nouveau langage, plugins, API, connecteurs) et internals.
- `plugins.md` – Développement et configuration des plugins intégrés (webhook, livemap, watchdog, bridge, settings update).
- `reference_fr.md` – Vision et concepts d’origine.
- `autodiag.md` – Notes d’autodiagnostic, couverture des faux positifs et plan d’amélioration.
- `meeting Encyclopedie.md` – Spécificités Meeting (licence, présence).
- `orphan_functions.md`, `missing_in_UI.md` – Analyses ciblées (fonctions orphelines, écarts UI/API).

La Web UI propose un **Projects Control Center** pour enregistrer/activer des projets sans redémarrage, et une **History** pour visualiser/différencier les snapshots créés par l’API, la CLI ou l’UI.
