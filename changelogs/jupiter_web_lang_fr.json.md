# Changelog – jupiter/web/lang/fr.json

## Plugin i18n Architecture Change

### Changed
- Plugin-specific translations are now loaded dynamically from each plugin's `web/lang/` directory
- Main lang files only contain menu/title keys for plugins (`plugin.*.title`, `plugin.*.suggestions_panel`)
- Removed duplicate ai_helper translations that now live in `jupiter/plugins/ai_helper/web/lang/fr.json`

### Rationale
- Follows the architecture described in `docs/plugins_architecture.md`
- Each plugin owns its translations
- No duplication between main app and plugins
- Translations loaded at plugin mount time via `/plugins/{name}/lang/{lang}` API

## Plugin Activity Widget i18n (Phase 4.2.1)

### Ajouté
- `plugin_activity_loading`: "Chargement des métriques..."
- `plugin_activity_disabled`: "Suivi d'activité désactivé"
- `plugin_activity_never`: "Jamais"
- `plugin_activity_requests`: "Requêtes"
- `plugin_activity_requests_tooltip`: Tooltip pour le compteur de requêtes
- `plugin_activity_errors`: "Erreurs"
- `plugin_activity_errors_tooltip`: Tooltip pour le compteur d'erreurs
- `plugin_activity_error_rate`: "Taux d'erreur"
- `plugin_activity_error_rate_tooltip`: Tooltip pour le taux d'erreur
- `plugin_activity_last`: "Dernière activité"
- `plugin_activity_last_tooltip`: Tooltip pour l'horodatage de dernière activité

## Badge de confiance & Circuit Breaker i18n

### Ajouté
- Traductions badge de confiance :
  - `trust_official`: "Officiel" - plugins signés Jupiter
  - `trust_verified`: "Vérifié" - plugins tiers vérifiés
  - `trust_community`: "Communauté" - plugins communautaires
  - `trust_unsigned`: "Non signé" - plugins sans signature
  - `trust_experimental`: "Expérimental" - plugins expérimentaux
  - `trust_tooltip_official`: Tooltip expliquant le statut officiel
  - `trust_tooltip_verified`: Tooltip expliquant le statut vérifié
  - `trust_tooltip_community`: Tooltip expliquant le statut communautaire
  - `trust_tooltip_unsigned`: Avertissement plugins non signés
  - `trust_tooltip_experimental`: Avertissement plugins expérimentaux
- Traductions circuit breaker :
  - `circuit_closed`: "Sain" - fonctionnement normal
  - `circuit_half_open`: "Récupération" - test de récupération
  - `circuit_open`: "Dégradé" - circuit ouvert, appels bloqués
  - `circuit_tooltip_closed`: Tooltip état sain
  - `circuit_tooltip_half_open`: Tooltip état récupération
  - `circuit_tooltip_open`: Tooltip état dégradé

---

- Ajout des chaînes pour les vues Diagnostic, Analyse, Fichiers et Plugins restaurées, badges de statut, et messages de contexte API/CORS.
- Ajout des chaînes `suggestions_refresh_*` pour l'état d'actualisation des suggestions IA.
- Ajout du vocabulaire pour le tableau de bord Projets (hero actif, métriques, actions rapides, états vides) et formats de temps relatifs.
- Ajout des libellés liés au niveau de log pour décrire la nouvelle option de verbosité.
- Ajustement des libellés de configuration pour refléter le nouveau nommage `.jupiter.yaml`.
- Ajout des libellés pour le champ de chemin de fichier log dans les paramètres.
- Ajout de la traduction `suggestions_more_locations` pour expliquer qu'une liste d'occurrences de duplication est tronquée.
- (UI) L'onglet Suggestions affiche désormais des extraits de code pour les doublons ; pas de nouvelles clés requises.
- Ajout des clés pour l'édition des globs d'ignore par projet dans la page Projets.
- Ajout des clés pour le nouveau formulaire de connecteur API par projet (titre, sous-titre, sauvegarde).
- Ajout de la clé `update_current_version` pour légender la version affichée dans le panneau Mise à jour.
- Ajout des traductions pour l'onglet Dashboard du plugin Code Quality et les hints du panneau de paramètres (chunk duplication, seuils, toggle tests).
