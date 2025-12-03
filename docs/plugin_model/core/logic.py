"""
core/logic.py – Logique métier du plugin.
Version: 0.3.0

Ce module contient les fonctions métier appelées par CLI, API ou UI.
Il ne doit pas dépendre directement de FastAPI ou argparse.

Conforme à plugins_architecture.md v0.4.0
"""

from typing import Any, Dict, Optional
from datetime import datetime


def perform_example_action(params: Dict[str, Any], bridge=None) -> Dict[str, Any]:
    """
    Exécute l'action principale du plugin.
    
    Args:
        params: Paramètres de l'action.
        bridge: Instance du Bridge (optionnel) pour accès aux services.
    
    Returns:
        Résultat de l'action.
    """
    start_time = datetime.now()
    
    # Logique exemple
    result = {
        "input": params,
        "output": "Example result",
        "success": True,
        "timestamp": start_time.isoformat()
    }
    
    # Utiliser le runner via Bridge si nécessaire (§3.6)
    if bridge and params.get("use_runner"):
        runner = bridge.services.get_runner()
        # runner.execute() est médié par le Bridge avec contrôle des permissions
        # result["runner_output"] = runner.execute(params.get("command"))
        pass
    
    return result


def get_status(bridge=None) -> Dict[str, Any]:
    """
    Retourne le statut interne du plugin.
    
    Args:
        bridge: Instance du Bridge (optionnel).
    
    Returns:
        Dictionnaire avec clés `healthy`, `details`.
    """
    return {"healthy": True, "details": "All systems nominal"}


def process_item(item: Any) -> Dict[str, Any]:
    """
    Traite un élément individuel (utilisé dans les jobs async).
    
    Args:
        item: Élément à traiter.
    
    Returns:
        Résultat du traitement.
    """
    return {
        "item": item,
        "processed": True,
        "timestamp": datetime.now().isoformat()
    }


def validate_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valide la configuration du plugin avant sauvegarde.
    
    Args:
        config: Configuration à valider.
    
    Returns:
        Tuple (is_valid, error_message).
    """
    # Validation exemple
    if "api_endpoint" in config and config["api_endpoint"]:
        if not config["api_endpoint"].startswith(("http://", "https://")):
            return False, "api_endpoint must be a valid URL"
    
    return True, None
