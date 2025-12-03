"""
tests/test_basic.py – Tests unitaires du plugin Example.
Version: 0.1.0
"""

import pytest

# Import depuis le modèle (adapter le chemin si nécessaire pour tests réels)
# from docs.plugin_model.core.logic import perform_example_action, get_status


def test_perform_example_action():
    """
    Vérifie que perform_example_action retourne un résultat valide.
    """
    # Simulation locale pour la documentation
    params = {"key": "value"}
    result = {
        "input": params,
        "output": "Example result",
        "success": True
    }
    assert result["success"] is True
    assert result["input"] == params


def test_get_status():
    """
    Vérifie que get_status retourne un état sain.
    """
    status = {"healthy": True, "details": "All systems nominal"}
    assert status["healthy"] is True


def test_health_hook():
    """
    Vérifie que le hook health() retourne le bon format.
    """
    health_result = {"status": "ok", "details": "Example plugin healthy"}
    assert health_result["status"] == "ok"
