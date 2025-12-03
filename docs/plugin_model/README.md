# Plugin Modèle v2 – Documentation

Ce dossier contient un **plugin modèle** illustrant l'architecture v2 des plugins Jupiter, telle que décrite dans `docs/plugins_architecture.md` (v0.4.0).

> **Note** : Ce plugin n'est pas destiné à être exécuté dans Jupiter. Il sert uniquement de référence pour le développement de nouveaux plugins.

## Version

**0.3.0** – Conforme à plugins_architecture.md v0.4.0

## Structure

```
docs/plugin_model/
├── plugin.yaml           # Manifest : id, type, version, capabilities, permissions, i18n, signature
├── __init__.py           # Hooks init(), health(), metrics(), reset_settings(), jobs async
├── server/
│   ├── api.py            # Endpoints API (register_api_contribution) + jobs
│   └── events.py         # Pub/sub et schémas de payload
├── cli/
│   └── commands.py       # Commandes CLI (register_cli_contribution)
├── core/
│   ├── logic.py          # Logique métier isolée
│   └── runner_access.py  # Appels médiés au runner via Bridge
├── web/
│   ├── panels/
│   │   └── main.js       # Panneau principal (logs temps réel, stats, aide, export)
│   ├── settings_frame.js # Cadre de configuration (version, update, debug, changelog, reset)
│   ├── assets/
│   │   └── style.css     # Styles spécifiques
│   └── lang/
│       ├── en.json
│       └── fr.json       # Traductions i18n
├── tests/
│   └── test_basic.py     # Tests unitaires
├── changelog.md          # Changelog du plugin
└── README.md             # Ce fichier
```

## Points clés v0.4.0

### 1. Types de plugins (§3.1)

- **Plugins core** : pas de manifest, hard-codés dans `jupiter/core/` (ex: Bridge, settings_update).
- **Plugins system** : manifest requis, désactivables, healthcheck obligatoire.
- **Plugins tool** : manifest requis, optionnels, échec isolé.

Ce plugin modèle est de type `tool`.

### 2. Manifest (`plugin.yaml`) – §3.4

Le manifest inclut :
- **config_schema.schema** (JSON Schema) : génère automatiquement un formulaire dans Settings (§3.4.3).
- **entrypoints** explicites : évite l'exécution de code arbitraire pour découvrir les hooks.
- **capabilities.jobs** : timeout et concurrence pour tâches longues (§10.6).
- **permissions** granulaires : `fs_read`, `fs_write`, `run_commands`, `network_outbound`, `access_meeting`.

### 3. Bridge comme Service Locator (§3.3.1)

Les plugins utilisent `bridge.services.*` au lieu d'importer directement `jupiter.core.*` :

```python
def init(bridge):
    logger = bridge.services.get_logger("example_plugin")
    config = bridge.services.get_config("example_plugin")
    runner = bridge.services.get_runner()
    events = bridge.services.get_event_bus()
```

### 4. Scope global vs projet (§3.1.1)

- Plugins **installés** = global à l'installation Jupiter.
- Plugins **activés** = configurable par projet dans `<project>.jupiter.yaml`.
- Config = globale + overrides projet fusionnés par le Bridge.

### 5. Auto-UI (§3.4.3)

Si `config_schema.schema` est défini → formulaire auto-généré dans Settings.
Si `capabilities.metrics.enabled: true` → carte de stats auto-générée.
Composant de logs partagé injecté automatiquement.

### 6. Jobs asynchrones (§10.6)

Pour les tâches longues :

```python
async def submit_long_task(params):
    job_id = await bridge.jobs.submit(
        plugin_id="example_plugin",
        handler=my_handler,
        params=params
    )
    return job_id

async def my_handler(job, params):
    for i, item in enumerate(items):
        if job.is_cancelled():
            return {"status": "cancelled"}
        
        # Traitement
        await process_item(item)
        
        # Mise à jour progression (envoyée via WS)
        job.update_progress(progress=i*10, message=f"Step {i}")
    
    return {"status": "completed"}
```

### 7. Hot Reload (§10.5) – Dev mode

En mode développeur (`developer_mode: true`), les plugins peuvent être rechargés à chaud :

```bash
jupiter plugins reload example_plugin
```

### 8. Panneau WebUI – §9

- Zone d'aide à droite obligatoire.
- Logs temps réel avec recherche/pause/téléchargement.
- Statistiques d'utilisation.
- Exports fichier/IA.

### 9. Cadre Settings – §9

- Auto-ajouté via Bridge si `capabilities.ui.settings_frame: true`.
- Affichage de la version du plugin.
- Boutons check/update.
- Mode debug, notifications, changelog, reset.

### 10. Sécurité – §3.6, §3.9

- Permissions déclarées dans le manifest.
- Appels runner médiés par le Bridge.
- Signature optionnelle pour distribution.

## Utilisation

Pour créer un nouveau plugin v2 :

1. **Scaffold** (recommandé) :
   ```bash
   jupiter plugins scaffold my_plugin --type tool --with-ui
   ```

2. **Manuel** : Copier ce dossier sous `jupiter/plugins/<votre_plugin_id>/`.

3. Adapter `plugin.yaml` (id, type, version, dépendances, config_schema...).

4. Implémenter la logique dans `core/logic.py`.

5. Ajouter les routes API dans `server/api.py`, y compris jobs si nécessaire.

6. Créer le panneau WebUI dans `web/panels/main.js` et le cadre Settings dans `web/settings_frame.js`.

7. Fournir les traductions dans `web/lang/*.json` (clés préfixées `plugin.<id>.*`).

8. Écrire des tests dans `tests/`.

9. Documenter les changements dans `changelog.md`.

10. (Optionnel) Signer le plugin avec `jupiter plugins sign`.

## Références

- [Architecture des plugins Jupiter](../plugins_architecture.md) – v0.4.0
- [Guide développeur](../dev_guide.md)
