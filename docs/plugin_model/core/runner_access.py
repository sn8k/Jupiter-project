"""
core/runner_access.py – Appels médiés au runner via le Bridge.
Version: 0.1.0

Ce module montre comment un plugin demande l'exécution de commandes shell
de manière sécurisée, en passant par le Bridge (qui vérifie permissions,
allowed_commands, etc.).
"""

from typing import List, Optional


def request_command_execution(
    bridge,
    command: List[str],
    cwd: Optional[str] = None,
    timeout: int = 30
) -> dict:
    """
    Demande au Bridge d'exécuter une commande via core/runner.py.
    
    Args:
        bridge: Instance Bridge.
        command: Liste des arguments de la commande.
        cwd: Répertoire de travail (optionnel).
        timeout: Timeout en secondes.
    
    Returns:
        Résultat de l'exécution (stdout, stderr, returncode).
    
    Raises:
        PermissionError: Si le plugin n'a pas la permission `runner`.
        ValueError: Si la commande n'est pas dans la liste autorisée.
    """
    # Le Bridge vérifie les permissions déclarées dans plugin.yaml
    # et la liste security.allowed_commands de la config globale.
    return bridge.runner.execute(
        plugin_id="example_plugin",
        command=command,
        cwd=cwd,
        timeout=timeout
    )
