"""
server/events.py – Hooks pub/sub et schémas de payload pour le plugin.
Version: 0.1.0
"""

# Topics auxquels ce plugin s'abonne ou émet
TOPICS = {
    "example.action_completed": {
        "description": "Émis quand une action exemple est terminée.",
        "payload_schema": {
            "action_id": "string",
            "result": "any",
            "timestamp": "iso8601"
        }
    }
}


def on_action_completed(bridge, payload: dict):
    """
    Handler appelé lorsque le topic 'example.action_completed' est émis.
    
    Args:
        bridge: Instance Bridge (pour émettre d'autres events ou accéder aux services).
        payload: Données de l'événement.
    """
    # Exemple : journaliser ou déclencher une action secondaire
    pass


def register_events(bridge):
    """
    Enregistre les abonnements aux événements via le Bridge.
    
    Args:
        bridge: Instance Bridge.
    """
    bridge.events.subscribe("example.action_completed", on_action_completed)
