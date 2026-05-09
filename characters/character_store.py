"""
Character persistence layer — JSON file storage for character definitions
and user↔character binding mappings.
"""

import json
import os
import threading
from typing import Optional

from common.log import logger
from common.utils import expand_path
from characters.character import Character


class CharacterStore:
    """
    Persists Character objects as JSON files.

    Directory layout:
        ~/cow/characters/
            {character_id}/
                character.json       # serialized Character
            bindings.json            # user_id -> active_character_id mapping
    """

    DEFAULT_BASE = "~/cow/characters"

    def __init__(self, base_dir: str = None):
        self._base_dir = expand_path(base_dir or self.DEFAULT_BASE)
        self._lock = threading.RLock()  # reentrant: set_active_character calls save() internally
        os.makedirs(self._base_dir, exist_ok=True)

    # ── path helpers ──────────────────────────────────────────────────

    def _char_dir(self, character_id: str) -> str:
        return os.path.join(self._base_dir, character_id)

    def _char_file(self, character_id: str) -> str:
        return os.path.join(self._char_dir(character_id), "character.json")

    def _bindings_file(self) -> str:
        return os.path.join(self._base_dir, "bindings.json")

    # ── CRUD ──────────────────────────────────────────────────────────

    def save(self, character: Character) -> bool:
        """Persist a character. Returns True on success."""
        character.touch()
        char_dir = self._char_dir(character.id)
        os.makedirs(char_dir, exist_ok=True)
        try:
            with self._lock:
                with open(self._char_file(character.id), "w", encoding="utf-8") as f:
                    f.write(character.to_json())
            logger.info(f"[CharacterStore] Saved character: {character.display_name} ({character.id})")
            return True
        except Exception as e:
            logger.error(f"[CharacterStore] Failed to save character {character.id}: {e}")
            return False

    def load(self, character_id: str) -> Optional[Character]:
        """Load a single character by ID."""
        path = self._char_file(character_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return Character.from_json(f.read())
        except Exception as e:
            logger.error(f"[CharacterStore] Failed to load character {character_id}: {e}")
            return None

    def delete(self, character_id: str) -> bool:
        """Delete a character (removes the JSON file, keeps the directory for memory data)."""
        path = self._char_file(character_id)
        if not os.path.exists(path):
            return False
        try:
            with self._lock:
                os.remove(path)
            logger.info(f"[CharacterStore] Deleted character: {character_id}")
            return True
        except Exception as e:
            logger.error(f"[CharacterStore] Failed to delete character {character_id}: {e}")
            return False

    def list_all(self) -> list[Character]:
        """Return all stored characters."""
        characters = []
        if not os.path.isdir(self._base_dir):
            return characters
        for name in os.listdir(self._base_dir):
            char_file = self._char_file(name)
            if os.path.isfile(char_file):
                ch = self.load(name)
                if ch:
                    characters.append(ch)
        characters.sort(key=lambda c: c.updated_at, reverse=True)
        return characters

    # ── bindings (user ↔ active character) ───────────────────────────

    def _read_bindings(self) -> dict:
        path = self._bindings_file()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[CharacterStore] Failed to read bindings file, returning empty: {e}")
            return {}

    def _write_bindings(self, bindings: dict):
        path = self._bindings_file()
        # Atomic write: tmp file + rename, prevents corruption on crash
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(bindings, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # atomic on POSIX and Windows

    def get_active_character_id(self, user_id: str) -> Optional[str]:
        with self._lock:
            bindings = self._read_bindings()
            return bindings.get(user_id)

    def set_active_character(self, user_id: str, character_id: str):
        with self._lock:
            bindings = self._read_bindings()
            # deactivate previous character for this user
            old_id = bindings.get(user_id)
            if old_id and old_id != character_id:
                old_char = self.load(old_id)
                if old_char:
                    old_char.is_active = False
                    self.save(old_char)
            bindings[user_id] = character_id
            self._write_bindings(bindings)
            # mark new character active
            new_char = self.load(character_id)
            if new_char:
                new_char.is_active = True
                new_char.bound_user_id = user_id
                self.save(new_char)

    def clear_active_character(self, user_id: str):
        with self._lock:
            bindings = self._read_bindings()
            old_id = bindings.pop(user_id, None)
            if old_id:
                old_char = self.load(old_id)
                if old_char:
                    old_char.is_active = False
                    old_char.bound_user_id = ""
                    self.save(old_char)
                self._write_bindings(bindings)
                logger.info(f"[CharacterStore] Cleared binding: user={user_id} -> char={old_id}")

    def get_character_workspace(self, character_id: str) -> str:
        """Return the workspace directory for a character."""
        return self._char_dir(character_id)
