"""
Persona Validator — post-generation compliance check.

Runs a lightweight validation to detect whether the LLM output
has deviated from the character's defined persona. If a deviation
is detected, signals the caller to re-generate.
"""

from dataclasses import dataclass, field

from characters.character import Character


@dataclass
class PersonaCheckResult:
    passed: bool
    score: float  # 0.0 ~ 1.0, higher = more compliant
    issues: list = field(default_factory=list)


VALIDATION_PROMPT = """你是一个角色扮演合规性检查器。请判断以下AI回复是否符合角色设定。

## 角色设定
姓名：{name}
性别：{gender}
年龄：{age}
性格：{personality}
语言风格：{language_style}
口头禅：{catchphrases}
与用户的关系：{relationship}

## AI 的回复
{reply}

## 检查标准
1. AI是否声称自己是AI/语言模型/机器人？（如果声称，则严重违规）
2. AI的用词和语气是否符合角色的语言风格？
3. AI是否做出了不符合角色身份的表述？
4. AI是否跳出角色说了一些"打破第四面墙"的话？

请以JSON格式回复（只输出JSON，不要有其他文字）：
{{
  "passed": true/false,
  "score": 0.0~1.0,
  "issues": ["问题描述1", "问题描述2"]
}}
"""

# Keywords that indicate the model is breaking character
_OOC_PATTERNS = [
    "作为一个AI",
    "作为一个人工智能",
    "作为AI助手",
    "我是AI",
    "我是人工智能",
    "根据我的训练",
    "我不能…因为我是",
    "我的知识截止",
    "作为语言模型",
    "作为一个语言模型",
    "我是语言模型",
    "作为大模型",
    "我无法",
    "我无法执行",
]


class PersonaValidator:
    """Validates that LLM output stays within the character persona."""

    def __init__(self, llm_model=None):
        self._model = llm_model

    def set_model(self, model):
        self._model = model

    def validate(self, reply_text: str, character: Character) -> PersonaCheckResult:
        """
        Check whether reply_text is compliant with character persona.

        Returns PersonaCheckResult with passed=True if compliant.
        """
        # Fast path: rule-based keyword check (no LLM call needed)
        keyword_issues = self._keyword_check(reply_text)
        if keyword_issues:
            return PersonaCheckResult(
                passed=False,
                score=0.0,
                issues=keyword_issues,
            )

        # If we have a model, do LLM-based deep validation
        if self._model:
            return self._llm_validate(reply_text, character)

        # Without a model, keyword check is sufficient
        return PersonaCheckResult(passed=True, score=1.0)

    def _keyword_check(self, reply_text: str) -> list[str]:
        """Fast rule-based check for obvious out-of-character language."""
        issues = []
        for pattern in _OOC_PATTERNS:
            if pattern in reply_text:
                issues.append(f"检测到暴露AI身份的表述: '{pattern}'")
        return issues

    def _llm_validate(self, reply_text: str, character: Character) -> PersonaCheckResult:
        """Use a lightweight LLM call to deeply validate persona compliance."""
        prompt = VALIDATION_PROMPT.format(
            name=character.name,
            gender=character.gender,
            age=str(character.age),
            personality=character.personality or "无特殊设定",
            language_style=character.language_style or "自然对话",
            catchphrases="、".join(character.catchphrases) if character.catchphrases else "无",
            relationship=character.relationship,
            reply=reply_text[:1500],  # cap to keep validation cheap
        )

        try:
            from agent.protocol import LLMModel, LLMRequest

            request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
            )

            response = self._model.call(request)
            result_text = self._extract_text(response)

            import json
            data = json.loads(result_text)
            return PersonaCheckResult(
                passed=data.get("passed", True),
                score=data.get("score", 1.0),
                issues=data.get("issues", []),
            )
        except Exception:
            # On any validation error, default to pass (don't block replies)
            return PersonaCheckResult(passed=True, score=1.0)

    @staticmethod
    def _extract_text(response) -> str:
        """Extract text content from LLM response (handles various formats)."""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            content = response.get("content") or response.get("text") or ""
            if isinstance(content, list):
                parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                return "\n".join(parts)
            return content
        return str(response)
