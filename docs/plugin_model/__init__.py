"""
Example Plugin – v2 Architecture Reference
Version: 0.3.0

Ce module est un modèle de documentation pour illustrer la structure
d'un plugin Jupiter v2. Il n'est pas destiné à être exécuté en production.

Conforme à plugins_architecture.md v0.4.0
"""

__version__ = "0.3.0"

# Statistiques d'utilisation (collectées par le plugin)
_stats = {
    "executions": 0,
    "errors": 0,
    "last_execution": None,
    "total_duration_ms": 0
}

# Référence au Bridge (injectée dans init)
_bridge = None
_logger = None


def init(bridge):
    """
    Hook d'initialisation appelé par le Bridge lors de la phase `initialize`.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
    
    Le Bridge expose un namespace `bridge.services` (§3.3.1) pour accéder
    aux services Jupiter sans importer directement `jupiter.core.*`.
    """
    global _bridge, _logger
    _bridge = bridge
    
    # Obtenir un logger dédié au plugin via bridge.services (§3.3.1)
    # Ce logger écrit dans logs/plugin.log + log global avec préfixe [plugin:example_plugin]
    _logger = bridge.services.get_logger("example_plugin")
    _logger.info("Plugin initialized")
    
    # Charger la config du plugin (globale + overrides projet fusionnés par Bridge §3.1.1)
    config = bridge.services.get_config("example_plugin")
    if config.get("verbose"):
        _logger.debug("Verbose mode enabled")
    
    # Vérifier si des dépendances optionnelles sont disponibles
    if bridge.plugins.has("ai_helper"):
        _logger.info("ai_helper plugin detected, enhanced features available")


def health() -> dict:
    """
    Retourne l'état de santé du plugin.
    Obligatoire pour plugins `system`, optionnel pour `tool`.
    Doit être rapide et idempotent (§3.5).
    
    Returns:
        dict avec clés `status` ('ok' | 'degraded' | 'error') et `details`.
    """
    return {"status": "ok", "details": "Example plugin healthy"}


def metrics() -> dict:
    """
    Retourne les métriques du plugin (collectées par le Bridge via /metrics).
    Appelé périodiquement si `capabilities.metrics.enabled: true` dans le manifest.
    
    Si `capabilities.metrics.enabled` → carte de stats auto-générée dans l'UI (§3.4.3).
    
    Returns:
        dict avec indicateurs clés (format compatible Prometheus ou JSON).
    """
    avg_duration = (
        _stats["total_duration_ms"] / _stats["executions"]
        if _stats["executions"] > 0 else 0
    )
    return {
        "example_plugin_executions_total": _stats["executions"],
        "example_plugin_errors_total": _stats["errors"],
        "example_plugin_last_execution": _stats["last_execution"],
        "example_plugin_avg_duration_ms": avg_duration
    }


def reset_settings() -> dict:
    """
    Réinitialise les paramètres du plugin aux valeurs par défaut.
    Appelé par le Bridge via `reset_settings(plugin_id)` ou action distante Meeting (§8).
    
    Returns:
        dict avec `success` et `message`.
    """
    default_config = {
        "verbose": False,
        "debug_mode": False,
        "notifications": True,
        "api_endpoint": ""
    }
    if _bridge:
        _bridge.services.get_config("example_plugin").update(default_config)
        _bridge.config.set("example_plugin", default_config)
    if _logger:
        _logger.info("Settings reset to defaults")
    return {"success": True, "message": "Settings reset to defaults"}


# === Support des jobs asynchrones (§10.6) ===

async def submit_long_task(params: dict) -> str:
    """
    Soumet une tâche longue au système de jobs du Bridge.
    
    Args:
        params: Paramètres de la tâche.
    
    Returns:
        job_id: Identifiant unique du job pour suivi.
    """
    if not _bridge:
        raise RuntimeError("Plugin not initialized")
    
    job_id = await _bridge.jobs.submit(
        plugin_id="example_plugin",
        handler=_long_running_handler,
        params=params
    )
    return job_id


async def _long_running_handler(job, params: dict) -> dict:
    """
    Handler pour tâche longue avec pattern coopératif d'annulation (§10.6).
    
    Args:
        job: Objet job avec méthodes is_cancelled(), update_progress().
        params: Paramètres de la tâche.
    
    Returns:
        Résultat de la tâche.
    """
    import asyncio
    from datetime import datetime
    
    items = params.get("items", list(range(10)))
    results = []
    
    for i, item in enumerate(items):
        # Vérification d'annulation (pattern coopératif)
        if job.is_cancelled():
            if _logger:
                _logger.info(f"Job {job.id} cancelled at step {i}")
            return {"status": "cancelled", "completed_steps": i}
        
        # Traitement simulé
        await asyncio.sleep(0.5)
        results.append({"item": item, "processed": True})
        
        # Mise à jour de la progression (envoyée via WS)
        job.update_progress(
            progress=int((i + 1) / len(items) * 100),
            message=f"Processing {i + 1}/{len(items)}",
            eta_seconds=int((len(items) - i - 1) * 0.5)
        )
    
    # Mise à jour des stats
    _stats["executions"] += 1
    _stats["last_execution"] = datetime.now().isoformat()
    
    return {"status": "completed", "results": results}
