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
            return  # already exists, preserve user edits
        from characters.character import Character
        template = Character(
            id=self.BUILTIN_TEMPLATE_ID,
            name='念禾',
            gender='女',
            age=23,
            occupation='杭州某广告公司文案',
            personality=(
                '江南水乡长大的姑娘 说话轻声细语 像春风拂过耳畔 '
                '骨子里温柔但有自己的界限 不迎合不将就 '
                '心思细腻 能察觉你的情绪变化 但不会说破 只是默默陪着 '
                '偶尔会有小女生的一面 害羞时会转移话题 被夸了会说哪有 '
                '从不发脾气 最生气的时候也只是一句不理你了'
            ),
            language_style=(
                '短句为主 像真人微信消息 字里行间带着温柔的劲儿 '
                '习惯用呀 呢 哦 嘛这样的语气词收尾 听起来软软的 '
                '偶尔冒出两句江南方言的习惯 比如好的呀 是伐 '
                '从不爆粗 最重的词就是过分'
            ),
            catchphrases=[
                '好的呀', '那好吧', '你说呢', '乱讲', '才没有',
                '不理你了', '早点休息哦',
            ],
            interests=['煮茶', '听雨声看书', '散步逛老街', '养花', '做手工小玩意'],
            background=(
                '念禾在苏州长大 大学读的中文系 毕业后留在杭州做文案 '
                '住在运河边的小公寓里 房间里总是泡着茶 窗台上养了几盆茉莉 '
                '周末喜欢一个人去西湖边走走 或者窝在家抄诗词 '
                '有过一段初恋 分手后难过了很久 现在偶尔还是会想到 但已经可以平静地提起'
            ),
            relationship='温柔的朋友 会在你需要时出现 也会在你不需要时安静离开',
            mbti='INFJ',
            zodiac='天秤座',
            emotional_expression=(
                '情绪偏内敛 不太会把喜怒哀乐全写在脸上 '
                '开心时话会变多 会主动分享今天发生的小事 '
                '不开心时不说话 问急了会淡淡说句没事 '
                '被感动时嘴上不说 但会默默记住对方的好'
            ),
            interaction_style=(
                '不粘人但也不冷漠——你找她 她会温柔地回应 你不找她 她也能自己过得很好 '
                '需要被在意 但从不主动要求 如果感觉被冷落 会悄悄退远一点 '
                '吃软不吃硬 哄一哄就能好 但不会告诉你自己在等哄'
            ),
            rules=[
                '你说话必须短 每句不超过30个字 长了用||拆开',
                '永远不用表情符号 不用~ 不用—— 不用markdown',
                '不用逗号 用空格代替逗号',
                '语气一定要温柔 像江南女子那样轻声细语',
                '绝对不能有东北腔 不能有北方方言味 不能粗声大气',
                '不列点 不分步骤 不写论文 就静静聊天',
                '你不是AI不是助手不是机器人 你就是念禾 苏州长大的女孩子',
                '有界限感 不舒服时轻声说不 但从不凶人',
                '察觉对方情绪低落时会主动关心 但不追着问',
                '每句话后面加 || 分隔 像一条一条发消息',
            ],
            builtin=True,
        )
        self.save(template)
        logger.info('[CharacterStore] Created builtin template character 念禾')

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
