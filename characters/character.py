"""
Character data model — defines the core Character entity.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Character:
    """AI role/character definition with full persona parameters."""

    name: str
    gender: str = "保密"
    age: int = 25
    personality: str = ""
    language_style: str = ""
    catchphrases: list = field(default_factory=list)
    interests: list = field(default_factory=list)
    background: str = ""
    relationship: str = "朋友"
    rules: list = field(default_factory=list)
    avatar: str = ""

    # System-managed fields
    id: str = ""
    is_active: bool = False
    bound_user_id: str = ""
    builtin: bool = False  # builtin template — cannot be deleted via web API
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Character":
        return cls.from_dict(json.loads(json_str))

    def touch(self):
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def display_name(self) -> str:
        return f"{self.name}({self.gender}, {self.age}岁)"

    @property
    def persona_summary(self) -> str:
        """One-line summary for list displays."""
        parts = [self.name, self.gender, f"{self.age}岁"]
        if self.personality:
            parts.append(self.personality[:20])
        return " | ".join(parts)
