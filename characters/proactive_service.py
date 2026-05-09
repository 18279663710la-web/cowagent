"""
Proactive Messaging Service — enables AI characters to initiate conversations.

Trigger types:
- emotion_trigger: analyzes recent chat sentiment, initiates comfort/distraction
- inactivity_trigger: checks if user hasn't messaged in N hours
- cron_trigger: time-based scheduled messages (good morning, good night, etc.)
- event_trigger: reacts to specific keywords or patterns in recent messages
"""

import datetime
import random
import threading
from typing import Optional

from common.log import logger
from characters.character import Character


class ProactiveService:
    """
    Manages proactive message triggers for AI characters.

    Integrates with the existing SchedulerService for cron-based triggers
    and adds emotion/inactivity detection on top.
    """

    # Default thresholds
    INACTIVITY_THRESHOLD_HOURS = 6
    EMOTION_CHECK_WINDOW_HOURS = 2
    EMOTION_LOW_THRESHOLD = -0.3  # sentiment score below this = "low mood"

    def __init__(self, character_manager=None, agent_bridge=None):
        self._character_manager = character_manager
        self._agent_bridge = agent_bridge
        self._last_activity: dict[str, datetime.datetime] = {}  # user_id -> timestamp
        self._lock = threading.Lock()

    def set_character_manager(self, cm):
        self._character_manager = cm

    def set_agent_bridge(self, ab):
        self._agent_bridge = ab

    # ── activity tracking ────────────────────────────────────────────

    def record_activity(self, user_id: str):
        """Call this every time a user sends a message."""
        with self._lock:
            self._last_activity[user_id] = datetime.datetime.now()

    def get_last_activity(self, user_id: str) -> Optional[datetime.datetime]:
        with self._lock:
            return self._last_activity.get(user_id)

    # ── trigger checks ────────────────────────────────────────────────

    def should_send_inactivity_message(self, user_id: str) -> bool:
        """
        Check if user has been inactive long enough to warrant a proactive message.
        """
        last = self.get_last_activity(user_id)
        if not last:
            return False
        elapsed = (datetime.datetime.now() - last).total_seconds() / 3600
        return elapsed >= self.INACTIVITY_THRESHOLD_HOURS

    def check_emotion_trigger(
        self, user_id: str, recent_messages: list = None
    ) -> tuple[bool, str]:
        """
        Analyze recent conversation for emotional triggers.

        Returns (should_trigger, emotion_label).
        emotion_label is one of: "positive", "neutral", "low", "unknown"
        """
        if not recent_messages:
            return False, "unknown"

        # Simple keyword-based sentiment analysis (no LLM call)
        negative_words = [
            "难过", "伤心", "不开心", "郁闷", "烦躁", "焦虑", "害怕",
            "孤独", "失落", "生气", "愤怒", "累", "疲惫", "压力",
            "无聊", "不知道", "迷茫", "想哭", "崩溃", "受不了",
            "sad", "depressed", "angry", "tired", "lonely", "upset",
        ]
        positive_words = [
            "开心", "高兴", "快乐", "太好了", "棒", "喜欢", "爱",
            "兴奋", "期待", "感谢", "幸福", "满足", "轻松", "美好",
            "happy", "great", "exciting", "love", "wonderful", "amazing",
        ]

        neg_count = 0
        pos_count = 0
        for msg in recent_messages:
            text = msg if isinstance(msg, str) else msg.get("content", "")
            if isinstance(text, list):
                text = " ".join(
                    b.get("text", "")
                    for b in text
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            for word in negative_words:
                if word in text:
                    neg_count += 1
            for word in positive_words:
                if word in text:
                    pos_count += 1

        if neg_count > pos_count and neg_count >= 2:
            return True, "low"
        elif pos_count > neg_count:
            return False, "positive"
        return False, "neutral"

    # ── message generation ────────────────────────────────────────────

    def generate_proactive_message(
        self, character: Character, trigger_type: str, context: dict = None
    ) -> Optional[str]:
        """
        Generate a proactive message in the character's voice.

        trigger_type: "inactivity", "emotion_low", "morning", "night", "event"
        context: optional dict with additional info (emotion, topic, etc.)
        """
        if not self._agent_bridge or not character.bound_user_id:
            return None

        context = context or {}
        emotion = context.get("emotion", "")

        prompts = {
            "inactivity": f"你已经有一段时间没和用户说话了。作为{character.name}，请自然地发起一句问候或关心的话。不要太正式，像朋友之间的随意关心。",
            "emotion_low": f"用户最近似乎情绪不太好（{emotion}）。作为{character.name}，你和用户是{character.relationship}的关系，请用你的方式表达关心、安慰或者转移话题逗用户开心。保持自然，不要像做任务一样生硬。",
            "morning": f"现在是早上，作为{character.name}，用你的方式和用户说早安。根据你的性格和你们的关系，自然地开始新的一天。",
            "night": f"现在是晚上，作为{character.name}，用你的方式向用户道晚安。根据你的性格和你们的关系自然地表达。",
            "event": f"你注意到了一些事情，作为{character.name}，请自然地向用户提起这个话题。用你的语言风格和性格来表达。",
        }

        prompt = prompts.get(trigger_type, prompts["inactivity"])

        try:
            user_id = character.bound_user_id
            reply = self._agent_bridge.agent_reply(
                query=f"[系统指令 - 主动消息触发 - {trigger_type}]\n{prompt}",
                context=self._make_context(user_id),
            )
            return reply.content if reply else None
        except Exception as e:
            logger.error(f"[ProactiveService] Failed to generate message: {e}")
            return None

    def _make_context(self, user_id: str):
        """Create a minimal context for the agent bridge."""
        from bridge.context import Context, ContextType
        return Context(
            type=ContextType.TEXT,
            content="",
            session_id=user_id,
            receiver=user_id,
            isgroup=False,
            channel_type="weixin",
        )

    # ── scheduled task integration ────────────────────────────────────

    def setup_proactive_tasks(self, character: Character):
        """
        Create default proactive tasks in the scheduler for a character.
        Call after a character is activated.
        """
        if not self._agent_bridge:
            return

        user_id = character.bound_user_id
        if not user_id:
            return

        try:
            from agent.tools.scheduler.scheduler_service import SchedulerService
            from agent.tools.scheduler.task_store import TaskStore
            from config import conf

            task_store = TaskStore()
            workspace = conf().get("character_workspace_base", "~/cow/characters")
            os_module = __import__("os")
            task_store_path = os_module.path.join(
                os_module.path.expanduser(workspace.replace("~/", "~/")),
                character.id,
                "scheduler",
                "tasks.json",
            )
        except Exception as e:
            logger.warning(f"[ProactiveService] Could not set up scheduler: {e}")
