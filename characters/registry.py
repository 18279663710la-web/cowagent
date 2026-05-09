"""
Character System Registry — holds singleton references to the CharacterManager
and ProactiveService, avoiding __main__ vs app module confusion.

All modules (app.py, web_channel.py, agent_bridge.py) import from this
single shared module so there is only one copy of the global state.
"""

_character_manager = None
_proactive_service = None


def set_character_manager(cm):
    global _character_manager
    _character_manager = cm


def get_character_manager():
    return _character_manager


def set_proactive_service(svc):
    global _proactive_service
    _proactive_service = svc


def get_proactive_service():
    return _proactive_service
