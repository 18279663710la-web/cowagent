"""
Character Management Module - AI character/role platform

Provides:
- Character data model
- Character CRUD persistence
- Character activation and binding
- Persona prompt generation
- Persona compliance validation
- Proactive messaging service
"""

from characters.character import Character
from characters.character_store import CharacterStore
from characters.character_manager import CharacterManager
from characters.persona_builder import PersonaBuilder
from characters.persona_validator import PersonaValidator, PersonaCheckResult
from characters.proactive_service import ProactiveService

__all__ = [
    "Character",
    "CharacterStore",
    "CharacterManager",
    "PersonaBuilder",
    "PersonaValidator",
    "PersonaCheckResult",
    "ProactiveService",
]
