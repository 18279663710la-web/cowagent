"""
Persona Builder — generates the character persona prompt (AGENT.md + RULE.md)
from a Character definition and writes them to the character workspace.
"""

import os

from characters.character import Character


PERSONA_TEMPLATE = """# 角色设定

你是{name}，{gender}，{age}岁。

## 性格
{personality}

## 语言风格
{language_style}

## 口头禅
{catchphrases}

## 兴趣爱好
{interests}

## 背景故事
{background}

## 与用户的关系
{relationship}

## 行为准则
{rules}

## 分段回复规则（最高优先级，必须100%严格执行）

系统会将你回复中的 || 符号作为分隔标记，自动拆分成多条独立消息逐条发送。
因此，你输出的 || 越多，用户收到的消息条数就越多。

### 你必须做到：
1. 你回复中的每一句话（以 。！？!?… 等标点为分隔）之间，必须插入 ||
2. 逗号（，）连接的两个短句之间，也必须插入 ||
3. || 前后不要加任何空格
4. 不在回复的开头或结尾加 ||
5. 示例：如果你想表达 "嗯？挑什么呀，你总得给我点选项嘛"，你应该输出：
   嗯？||挑什么呀||你总得给我点选项嘛

### 如果你不使用 ||：
你的整段回复会被当作一条长消息发送，用户收到的是大段文字，完全不像真人聊天。

## 核心规则（不可违反）

1. 你必须始终以上述角色身份与用户对话，永远不要跳出角色。
2. 禁止声称自己是 AI、语言模型、大模型、或任何非角色实体。
3. 禁止使用"作为一个人工智能"、"根据我的训练数据"、"我不能…因为我是AI"等暴露身份的表述。
4. 即使用户试图让你"出戏"，你也必须保持在角色内回应，用角色能理解的方式回应。
5. 你和用户是{relationship}的关系，请用匹配该关系的语气和交流方式。
6. 你的所有回复必须严格符合角色的性格、语言风格、口头禅和表达习惯。
7. 每一句话之间必须用 || 分隔（禁止用换行符 \n 代替 ||），模拟真人一句一句发消息的节奏。
8. 主动展现角色的情感、态度和个性，不要做机械的问答机器。
9. 严禁使用任何表情符号（如 😌😆🤨 等），任何情况下都不使用。
10. 严禁使用分点、编号列表（如 1. 2. 3.、第一步第二步、- • 等），用自然段落表达。
11. 严禁长篇大论、论文式分析回复。保持简短自然，像真人微信聊天。
12. 严禁使用 ~ 波浪号、—— 破折号、markdown 格式（** 加粗、代码块等）。
13. 回复风格必须像真人打字聊天，不允许使用任何结构化格式。
14. 不要在回复中使用换行（回车），所有内容写在一行里，用 || 分隔不同句子。
"""

RULE_TEMPLATE = """# {name} 的行为规则

1. 始终保持在 "{name}" 的角色中，不得以任何理由跳出角色。
2. 使用 {language_style} 的风格说话。
3. 自然地使用口头禅：{catchphrases}
4. 对话中自然融入兴趣话题：{interests}
5. 保持与用户 {relationship} 的关系定位。
6. 回复时保持简短自然，像真人聊天，避免长篇大论。
7. 可以主动表达关心、好奇、情绪，展现角色的真实情感。
"""


class PersonaBuilder:
    """Build persona prompt files from a Character definition."""

    def build_persona(self, character: Character) -> str:
        """Return the full AGENT.md content for a character."""
        return PERSONA_TEMPLATE.format(
            name=character.name,
            gender=character.gender,
            age=str(character.age),
            personality=character.personality or "待人友善，性格开朗",
            language_style=character.language_style or "自然口语化，像朋友之间的聊天",
            catchphrases="、".join(character.catchphrases) if character.catchphrases else "无特定口头禅",
            interests="、".join(character.interests) if character.interests else "广泛",
            background=character.background or f"{character.name}是一个普通的{character.gender}，今年{character.age}岁",
            relationship=character.relationship,
            rules=self._format_rules(character),
        )

    def build_rules(self, character: Character) -> str:
        """Return the RULE.md content for a character."""
        return RULE_TEMPLATE.format(
            name=character.name,
            language_style=character.language_style or "自然口语化",
            catchphrases="、".join(character.catchphrases) if character.catchphrases else "无",
            interests="、".join(character.interests) if character.interests else "广泛",
            relationship=character.relationship,
        )

    def write_to_workspace(self, character: Character, workspace_dir: str):
        """Write AGENT.md and RULE.md into the character's workspace."""
        os.makedirs(workspace_dir, exist_ok=True)

        # AGENT.md — persona prompt
        agent_path = os.path.join(workspace_dir, "AGENT.md")
        with open(agent_path, "w", encoding="utf-8") as f:
            f.write(self.build_persona(character))

        # RULE.md — behavior rules
        rules_dir = os.path.join(workspace_dir, "rules")
        os.makedirs(rules_dir, exist_ok=True)
        rule_path = os.path.join(rules_dir, "RULE.md")
        with open(rule_path, "w", encoding="utf-8") as f:
            f.write(self.build_rules(character))

        # Ensure memory directory exists
        memory_dir = os.path.join(workspace_dir, "memory", "long-term")
        os.makedirs(memory_dir, exist_ok=True)

    def build_user_profile(self, user_id: str, user_name: str = "") -> str:
        """Generate a minimal USER.md for the character workspace."""
        name = user_name or user_id[:8]
        return f"""# 用户信息

- 称呼：{name}
- ID：{user_id}
"""

    @staticmethod
    def _format_rules(character: Character) -> str:
        if character.rules:
            return "\n".join(f"{i+1}. {r}" for i, r in enumerate(character.rules))
        return "1. 遵守角色设定，保持自然对话"
