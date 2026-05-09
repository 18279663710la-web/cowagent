"""
Character business logic — CRUD, activation, switching, binding management.
"""

from typing import Optional

from common.log import logger
from characters.character import Character
from characters.character_store import CharacterStore
from characters.persona_builder import PersonaBuilder


class CharacterManager:
    """
    Central manager for AI character lifecycle.

    Responsibilities:
    - Create / update / delete characters
    - Activate / deactivate characters (one active per user at a time)
    - Switch characters — saves old state, loads new persona and workspace
    - Ensure bidirectional 1:1 binding (user ↔ character)
    """

    def __init__(self, store: CharacterStore = None, agent_bridge=None):
        self.store = store or CharacterStore()
        self._agent_bridge = agent_bridge  # injected later or at init
        self._persona_builder = PersonaBuilder()

    def set_agent_bridge(self, agent_bridge):
        self._agent_bridge = agent_bridge

    # ── CRUD ──────────────────────────────────────────────────────────

    def create_character(self, data: dict) -> Character:
        """Create a new character from a dict of field values."""
        char = Character.from_dict(data)
        self.store.save(char)
        logger.info(f"[CharacterManager] Created character: {char.display_name}")
        return char

    def get_character(self, character_id: str) -> Optional[Character]:
        return self.store.load(character_id)

    def update_character(self, character_id: str, data: dict) -> Optional[Character]:
        char = self.store.load(character_id)
        if not char:
            return None
        for key, value in data.items():
            if hasattr(char, key):
                setattr(char, key, value)
        self.store.save(char)
        # If this character is currently active, re-write persona to workspace
        if char.is_active:
            self._sync_persona_to_workspace(char)
            self._refresh_agent_prompt(char)
        return char

    def delete_character(self, character_id: str) -> bool:
        char = self.store.load(character_id)
        if char and char.is_active:
            self.deactivate_character(character_id)
        return self.store.delete(character_id)

    def list_characters(self) -> list[Character]:
        return self.store.list_all()

    # ── activation / binding ──────────────────────────────────────────

    def activate_character(self, character_id: str, user_id: str) -> Optional[Character]:
        """
        Activate a character for a user.
        - Deactivates any other active character for this user
        - Sets bidirectional binding
        - Writes persona to character workspace
        """
        char = self.store.load(character_id)
        if not char:
            logger.error(f"[CharacterManager] Character not found: {character_id}")
            return None

        # Deactivate user's previously active character
        old_active_id = self.store.get_active_character_id(user_id)
        if old_active_id and old_active_id != character_id:
            self.deactivate_character(old_active_id)

        # Bind
        self.store.set_active_character(user_id, character_id)
        char.is_active = True
        char.bound_user_id = user_id
        self.store.save(char)

        # Write persona files to character workspace
        self._sync_persona_to_workspace(char)

        logger.info(f"[CharacterManager] Activated character '{char.name}' for user {user_id}")
        return char

    def deactivate_character(self, character_id: str) -> bool:
        char = self.store.load(character_id)
        if not char:
            return False
        user_id = char.bound_user_id
        if user_id:
            self.store.clear_active_character(user_id)
        char.is_active = False
        char.bound_user_id = ""
        self.store.save(char)
        logger.info(f"[CharacterManager] Deactivated character: {char.display_name}")
        return True

    def get_active_character(self, user_id: str) -> Optional[Character]:
        """Return the currently active character for a user, or None."""
        char_id = self.store.get_active_character_id(user_id)
        if not char_id:
            return None
        return self.store.load(char_id)

    def switch_character(self, new_character_id: str, user_id: str) -> Optional[Character]:
        """Switch to a different character. Returns the newly activated character."""
        return self.activate_character(new_character_id, user_id)

    # ── persona / workspace helpers ───────────────────────────────────

    def _sync_persona_to_workspace(self, character: Character):
        """Generate persona files in the character's workspace directory."""
        workspace = self.store.get_character_workspace(character.id)
        self._persona_builder.write_to_workspace(character, workspace)

    def _refresh_agent_prompt(self, character: Character):
        """If the character is active and we have an agent_bridge, refresh the
        in-memory agent's system prompt to pick up persona changes live."""
        if not self._agent_bridge or not character.bound_user_id:
            return
        try:
            self._agent_bridge.refresh_all_skills()
            logger.debug(f"[CharacterManager] Refreshed agent prompt for char {character.id}")
        except Exception as e:
            logger.warning(f"[CharacterManager] Failed to refresh agent prompt: {e}")
