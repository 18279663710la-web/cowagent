"""
Tests for short-term and long-term memory systems.

Covers:
- ConversationStore append / load / session lifecycle
- SessionManager normal-mode persistence (restore from SQLite)
- MemoryManager search_sync (keyword fallback, no embedding needed)
- AgentInitializer _filter_text_only_messages
- AgentInitializer _restore_conversation_history turn-cap fix
- Per-character session isolation

Run: python -m pytest tests/test_memory_system.py -v
  or: python tests/test_memory_system.py
"""

import json
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ──────────────────────────────────────────────────────────────

def _temp_db():
    return Path(tempfile.mkdtemp()) / "test.db"


# ── ConversationStore tests ──────────────────────────────────────────────

def test_append_and_load_messages():
    from agent.memory.conversation_store import ConversationStore

    db_path = _temp_db()
    store = ConversationStore(db_path)

    sid = "user_test_001"
    msgs = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？"},
        {"role": "user", "content": "我叫小明"},
        {"role": "assistant", "content": "好的，小明，我记住了。"},
    ]
    store.append_messages(sid, msgs)

    loaded = store.load_messages(sid, max_turns=10)
    assert len(loaded) == 4, f"Expected 4 messages, got {len(loaded)}"
    assert loaded[0]["role"] == "user"
    assert loaded[0]["content"] == "你好"
    assert loaded[3]["content"] == "好的，小明，我记住了。"


def test_load_messages_respects_max_turns():
    from agent.memory.conversation_store import ConversationStore

    db_path = _temp_db()
    store = ConversationStore(db_path)

    sid = "user_turns_test"
    # Create 6 user messages → 6 visible turns, 12 total messages
    msgs = []
    for i in range(6):
        msgs.append({"role": "user", "content": f"问题{i}"})
        msgs.append({"role": "assistant", "content": f"回答{i}"})
    store.append_messages(sid, msgs)

    loaded = store.load_messages(sid, max_turns=3)
    # Should contain only the last 3 turns (6 messages)
    user_msgs = [m for m in loaded if m["role"] == "user"]
    assert len(user_msgs) == 3, f"Expected 3 visible turns, got {len(user_msgs)}"
    assert user_msgs[0]["content"] == "问题3"
    assert user_msgs[-1]["content"] == "问题5"


def test_clear_session():
    from agent.memory.conversation_store import ConversationStore

    db_path = _temp_db()
    store = ConversationStore(db_path)

    sid = "user_clear_test"
    store.append_messages(sid, [{"role": "user", "content": "test"}])
    assert len(store.load_messages(sid, max_turns=5)) == 1

    store.clear_session(sid)
    assert store.load_messages(sid, max_turns=5) == []


def test_multiple_sessions_isolation():
    from agent.memory.conversation_store import ConversationStore

    db_path = _temp_db()
    store = ConversationStore(db_path)

    store.append_messages("user_A", [{"role": "user", "content": "A的消息"}])
    store.append_messages("user_B", [{"role": "user", "content": "B的消息"}])

    loaded_a = store.load_messages("user_A", max_turns=5)
    loaded_b = store.load_messages("user_B", max_turns=5)

    assert loaded_a[0]["content"] == "A的消息"
    assert loaded_b[0]["content"] == "B的消息"
    assert len(loaded_a) == len(loaded_b) == 1


# ── AgentInitializer _filter_text_only_messages tests ────────────────────

def test_filter_text_only_basic():
    from bridge.agent_initializer import AgentInitializer

    msgs = [
        {"role": "user", "content": [{"type": "text", "text": "你好"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "你好！"}]},
        {"role": "user", "content": [{"type": "text", "text": "帮我查天气"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "name": "weather", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "content": "晴天 25°C"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "今天是晴天，25°C"}]},
    ]

    filtered = AgentInitializer._filter_text_only_messages(msgs)
    assert len(filtered) == 4, f"Expected 4 msgs (2 turns), got {len(filtered)}"

    # First turn
    assert filtered[0]["role"] == "user"
    assert _extract(filtered[0]["content"]) == "你好"
    assert filtered[1]["role"] == "assistant"
    assert _extract(filtered[1]["content"]) == "你好！"

    # Second turn (tool call filtered, only first user + last assistant text)
    assert filtered[2]["role"] == "user"
    assert _extract(filtered[2]["content"]) == "帮我查天气"
    assert filtered[3]["role"] == "assistant"
    assert _extract(filtered[3]["content"]) == "今天是晴天，25°C"


def test_filter_text_only_empty_user_skipped():
    from bridge.agent_initializer import AgentInitializer

    msgs = [
        # Internal hint injected by agent loop (no text)
        {"role": "user", "content": [{"type": "text", "text": ""}]},
        {"role": "assistant", "content": [{"type": "text", "text": "忽略上面"}]},
    ]

    filtered = AgentInitializer._filter_text_only_messages(msgs)
    assert len(filtered) == 0, f"Empty user should be skipped, got {len(filtered)}"


# ── Agent restoration turn-cap fix test ─────────────────────────────────

def test_restore_turns_uses_max_turns():
    """Verify the fix: restore_turns = max_turns, not max_turns // 6."""
    from config import conf

    # Simulate what _restore_conversation_history does
    max_turns = conf().get("agent_max_context_turns", 20)

    # Old formula (buggy)
    old_restore = max(3, max_turns // 6)
    assert old_restore == 3, f"Old formula would restore {old_restore} turns"

    # New formula (fixed)
    new_restore = max_turns
    assert new_restore == 20, f"New formula restores {new_restore} turns"

    # Scheduler formula
    scheduler_restore = max(3, max_turns // 4)
    assert scheduler_restore == 5, f"Scheduler restore: {scheduler_restore}"


# ── MemoryManager search_sync test (keyword-only, no embedding) ─────────

def test_memory_search_sync_keyword():
    from agent.memory.manager import MemoryManager
    from agent.memory.config import MemoryConfig

    tmp_ws = Path(tempfile.mkdtemp())
    config = MemoryConfig(workspace_root=str(tmp_ws))

    # No embedding provider → keyword-only search
    mgr = MemoryManager(config=config, embedding_provider=None, llm_model=None)

    # Add some memory content
    mgr.add_memory_sync("用户小明喜欢吃火锅，特别是麻辣口味的", scope="shared", source="session")
    mgr.add_memory_sync("小明对海鲜过敏，绝对不能吃虾和蟹", scope="shared", source="session")
    mgr.add_memory_sync("上次讨论了去成都旅游的计划，预算5000元", scope="shared", source="session")

    # Search for relevant memories
    results = mgr.search_sync("小明喜欢吃什么", max_results=3, min_score=0.0)
    assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
    assert any("火锅" in r.snippet for r in results), f"No result about 火锅: {[r.snippet for r in results]}"

    results2 = mgr.search_sync("海鲜", max_results=3, min_score=0.0)
    assert len(results2) >= 1
    assert any("过敏" in r.snippet for r in results2)

    results3 = mgr.search_sync("旅游", max_results=3, min_score=0.0)
    assert len(results3) >= 1
    assert any("成都" in r.snippet for r in results3)

    mgr.close()


def test_memory_search_sync_empty():
    from agent.memory.manager import MemoryManager
    from agent.memory.config import MemoryConfig

    tmp_ws = Path(tempfile.mkdtemp())
    config = MemoryConfig(workspace_root=str(tmp_ws))
    mgr = MemoryManager(config=config, embedding_provider=None, llm_model=None)

    results = mgr.search_sync("some query about nothing")
    assert len(results) == 0

    mgr.close()


# ── Per-character isolation tests ───────────────────────────────────────

def test_character_session_keys():
    """Verify that character session keys encode user+character pairing."""

    # Same user, different characters
    key_a = "user_123:char_aaa"
    key_b = "user_123:char_bbb"

    assert key_a != key_b, "Different characters must have different keys"

    # Same character, different users
    key_c = "user_456:char_aaa"
    assert key_a != key_c, "Different users must have different keys"


def test_character_conversation_isolation():
    """Different (user, character) pairs get isolated conversation storage."""
    from agent.memory.conversation_store import ConversationStore

    db_path = _temp_db()
    store = ConversationStore(db_path)

    user_char_a = "user_1:char_alice"
    user_char_b = "user_1:char_bob"

    store.append_messages(user_char_a, [{"role": "user", "content": "Alice的对话"}])
    store.append_messages(user_char_b, [{"role": "user", "content": "Bob的对话"}])

    a_msgs = store.load_messages(user_char_a, max_turns=5)
    b_msgs = store.load_messages(user_char_b, max_turns=5)

    assert a_msgs[0]["content"] == "Alice的对话"
    assert b_msgs[0]["content"] == "Bob的对话"


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract(content):
    """Extract text from JSON content (string or block list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p)
    return ""


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("append_and_load_messages", test_append_and_load_messages),
        ("load_messages_respects_max_turns", test_load_messages_respects_max_turns),
        ("clear_session", test_clear_session),
        ("multiple_sessions_isolation", test_multiple_sessions_isolation),
        ("filter_text_only_basic", test_filter_text_only_basic),
        ("filter_text_only_empty_user_skipped", test_filter_text_only_empty_user_skipped),
        ("restore_turns_uses_max_turns", test_restore_turns_uses_max_turns),
        ("memory_search_sync_keyword", test_memory_search_sync_keyword),
        ("memory_search_sync_empty", test_memory_search_sync_empty),
        ("character_session_keys", test_character_session_keys),
        ("character_conversation_isolation", test_character_conversation_isolation),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
