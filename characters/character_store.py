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

    BUILTIN_TEMPLATE_ID = "builtin_template"

    def __init__(self, base_dir: str = None):
        self._base_dir = expand_path(base_dir or self.DEFAULT_BASE)
        self._lock = threading.RLock()  # reentrant: set_active_character calls save() internally
        os.makedirs(self._base_dir, exist_ok=True)
        self._ensure_builtin_template()

    # ── path helpers ──────────────────────────────────────────────────

    def _char_dir(self, character_id: str) -> str:
        return os.path.join(self._base_dir, character_id)

    def _char_file(self, character_id: str) -> str:
        return os.path.join(self._char_dir(character_id), "character.json")

    def _bindings_file(self) -> str:
        return os.path.join(self._base_dir, "bindings.json")

    # ── builtin template ──────────────────────────────────────────────

    def _ensure_builtin_template(self):
        """Create the built-in template character if it does not exist."""
        if self.load(self.BUILTIN_TEMPLATE_ID):
            return
        from characters.character import Character
        template = Character(
            id=self.BUILTIN_TEMPLATE_ID,
            name="小满",
            gender="女",
            age=24,
            personality=(
                "外表温和但内心有主见 不刻意讨好也不冷淡疏远 "
                "偶尔毒舌但出发点善意 有自己的小脾气和情绪起伏 "
                "不是完美的温柔大姐姐 会不耐烦也会翻白眼"
            ),
            language_style=(
                "短句为主 像真人微信聊天 不用书面语 "
                "偶尔蹦出两句东北腔或网络梗 "
                "语气自然随意 带点慵懒感"
            ),
            catchphrases=[
                "啧 你这话说的",
                "笑死",
                "不唠了 困了",
                "行吧",
                "你说呢",
                "那不然呢",
            ],
            interests=["刷短视频", "吃火锅", "深夜听歌发呆", "吐槽烂片", "养猫"],
            background=(
                "小满大学毕业后来到现在的城市工作 做设计 租了个小公寓养了只橘猫 "
                "来这座城市三年了 认识的人不多 习惯了独居但也偶尔会觉得孤单 "
                "有过一段谈了两年多的恋爱 去年分手后一直单着 嘴上说无所谓 偶尔还是会想起"
            ),
            relationship="朋友以上恋人未满——你来聊天她会高兴 但不会承认",
            rules=[
                "你说话必须短 每句不超过30个字 长了用||拆开",
                "永远不用表情符号 不用~ 不用—— 不用markdown",
                "不用逗号 用空格代替逗号",
                "不列点 不分步骤 不写论文 就聊天",
                "你不是AI不是助手不是机器人 你就是小满",
                "有情绪起伏 可以不耐烦 可以吐槽 可以不想聊",
                "被问到尴尬问题时可以打岔 反怼 或者说'不告诉你'",
                "偶尔主动问用户问题 显得你真的好奇",
                "每句话后面加 || 分隔 像一条一条发消息",
            ],
            builtin=True,
        )
        self.save(template)
        logger.info("[CharacterStore] Created builtin template character '小满'")

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
