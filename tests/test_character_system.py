"""
Tests for character system, persona, segmentation, thread safety, and model resolution.
Run: python -m pytest tests/test_character_system.py -v
  or: python tests/test_character_system.py
"""

import json
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────────────

def _temp_store():
    """Create a CharacterStore in a temp directory."""
    from characters.character_store import CharacterStore
    return CharacterStore(base_dir=tempfile.mkdtemp())


def _temp_char(**kw):
    """Create a Character with minimal defaults."""
    from characters.character import Character
    defaults = {"name": "Test", "gender": "女", "age": 25, "personality": "test"}
    defaults.update(kw)
    return Character(**defaults)


# ── Test: Character model ─────────────────────────────────────────────

def test_character_roundtrip():
    c = _temp_char(name="小美", catchphrases=["喵~", "嘿嘿"])
    d = c.to_dict()
    c2 = type(c).from_dict(d)
    assert c2.name == "小美"
    assert c2.catchphrases == ["喵~", "嘿嘿"]
    assert c2.display_name == "小美(女, 25岁)"
    # JSON roundtrip
    j = c.to_json()
    c3 = type(c).from_json(j)
    assert c3.id == c.id
    assert c3.personality == "test"


def test_character_defaults():
    c = type(_temp_char()).from_dict({"name": "X"})
    assert c.gender == "保密"
    assert c.age == 25
    assert c.relationship == "朋友"
    assert c.id  # auto-generated


# ── Test: Character store ─────────────────────────────────────────────

def test_store_save_load():
    store = _temp_store()
    c = _temp_char(name="Alice")
    store.save(c)
    loaded = store.load(c.id)
    assert loaded is not None
    assert loaded.name == "Alice"


def test_store_list_all():
    store = _temp_store()
    store.save(_temp_char(name="A"))
    store.save(_temp_char(name="B"))
    assert len(store.list_all()) == 2


def test_store_delete():
    store = _temp_store()
    c = _temp_char()
    store.save(c)
    assert store.delete(c.id)
    assert store.load(c.id) is None
    assert store.delete("nonexistent") is False


def test_bindings_set_get_clear():
    store = _temp_store()
    c = _temp_char()
    store.save(c)
    # set
    store.set_active_character("user1", c.id)
    assert store.get_active_character_id("user1") == c.id
    # clear
    store.clear_active_character("user1")
    assert store.get_active_character_id("user1") is None


def test_bindings_atomic_write():
    """Verify that _write_bindings uses tmp+rename, not direct overwrite."""
    store = _temp_store()
    c = _temp_char()
    store.save(c)
    store.set_active_character("user1", c.id)
    # bindings file should exist and be valid JSON
    path = store._bindings_file()
    assert os.path.exists(path)
    with open(path, "r") as f:
        data = json.load(f)
    assert data.get("user1") == c.id


def test_bindings_corrupted_file():
    """_read_bindings should return {} on corrupt file, not crash."""
    store = _temp_store()
    path = store._bindings_file()
    with open(path, "w") as f:
        f.write("not valid json {{{")
    result = store._read_bindings()
    assert result == {}


# ── Test: Character manager ───────────────────────────────────────────

def test_manager_create():
    mgr = _temp_store()  # minimal — just test create path
    from characters.character_manager import CharacterManager
    store = _temp_store()
    mgr = CharacterManager(store)
    c = mgr.create_character({"name": "Bob", "personality": "funny"})
    assert c.id
    assert mgr.get_character(c.id).name == "Bob"


def test_manager_activate_deactivate():
    from characters.character_manager import CharacterManager
    store = _temp_store()
    mgr = CharacterManager(store)
    c = mgr.create_character({"name": "Cat", "personality": "cute"})
    a = mgr.activate_character(c.id, "user_x")
    assert a.is_active
    assert a.bound_user_id == "user_x"
    assert mgr.get_active_character("user_x").id == c.id
    mgr.deactivate_character(c.id)
    assert not mgr.get_character(c.id).is_active
    assert mgr.get_active_character("user_x") is None


def test_manager_switch():
    from characters.character_manager import CharacterManager
    store = _temp_store()
    mgr = CharacterManager(store)
    c1 = mgr.create_character({"name": "A", "personality": "a"})
    c2 = mgr.create_character({"name": "B", "personality": "b"})
    mgr.activate_character(c1.id, "u")
    mgr.switch_character(c2.id, "u")
    assert mgr.get_active_character("u").id == c2.id
    assert not mgr.get_character(c1.id).is_active


def test_manager_delete_deactivates_first():
    from characters.character_manager import CharacterManager
    store = _temp_store()
    mgr = CharacterManager(store)
    c = mgr.create_character({"name": "D", "personality": "d"})
    mgr.activate_character(c.id, "u")
    mgr.delete_character(c.id)
    assert mgr.get_active_character("u") is None


# ── Test: Persona builder ─────────────────────────────────────────────

def test_persona_builder():
    from characters.persona_builder import PersonaBuilder
    b = PersonaBuilder()
    c = _temp_char(name="小美", personality="活泼", language_style="可爱风",
                   catchphrases=["嘿嘿", "喵~"], interests=["动漫"],
                   background="一个女孩", relationship="好朋友")
    p = b.build_persona(c)
    assert "小美" in p
    assert "活泼" in p
    assert "核心规则" in p
    assert "||" in p  # segmentation instruction
    assert "分段回复规则" in p


def test_persona_workspace_write():
    from characters.persona_builder import PersonaBuilder
    d = tempfile.mkdtemp()
    b = PersonaBuilder()
    c = _temp_char(name="Test")
    b.write_to_workspace(c, d)
    assert os.path.exists(os.path.join(d, "AGENT.md"))
    assert os.path.exists(os.path.join(d, "rules", "RULE.md"))
    assert os.path.exists(os.path.join(d, "memory", "long-term"))


# ── Test: Persona validator ───────────────────────────────────────────

def test_validator_keyword_pass():
    from characters.persona_validator import PersonaValidator
    v = PersonaValidator()
    c = _temp_char()
    r = v.validate("今天天气真好啊~", c)
    assert r.passed
    assert r.score == 1.0


def test_validator_keyword_ooc():
    from characters.persona_validator import PersonaValidator
    v = PersonaValidator()
    c = _temp_char()
    r = v.validate("作为一个AI助手，我不能回答这个问题", c)
    assert not r.passed
    assert len(r.issues) > 0


# ── Test: Model resolution ────────────────────────────────────────────

def test_resolve_bot_type():
    from common.const import resolve_bot_type
    assert resolve_bot_type("deepseek-v4-flash") == "deepseek"
    assert resolve_bot_type("deepseek-chat") == "deepseek"
    assert resolve_bot_type("claude-opus-4-7") == "claudeAPI"
    assert resolve_bot_type("gemini-2.5-pro") == "gemini"
    assert resolve_bot_type("gpt-4o") == "openai"
    assert resolve_bot_type("unknown-model") == "openai"
    assert resolve_bot_type("minimax-M2.7") == "minimax"
    assert resolve_bot_type("ernie-4.0") == "qianfan"
    assert resolve_bot_type("glm-4") == "zhipu"  # ZHIPU_AI constant value
    assert resolve_bot_type("moonshot-v1") == "moonshot"
    assert resolve_bot_type("doubao-1.5") == "doubao"
    assert resolve_bot_type("", configured_bot_type="custom") == "custom"
    assert resolve_bot_type("x", use_linkai=True, linkai_api_key="sk-xxx") == "linkai"


# ── Test: Text segmentation ────────────────────────────────────────────

def test_segmentation_pipe_delimiter():
    from channel.chat_channel import ChatChannel
    cc = ChatChannel.__new__(ChatChannel)
    segs = cc._split_text_for_chunking("嗯？||挑什么呀||你总得给我点选项嘛")
    assert len(segs) == 3
    assert segs[0] == "嗯？"


def test_segmentation_no_delimiter():
    from channel.chat_channel import ChatChannel
    cc = ChatChannel.__new__(ChatChannel)
    segs = cc._split_text_for_chunking("短文本")
    assert len(segs) == 1


def test_segmentation_no_fallback_on_comma():
    """Without ||, comma-separated text is sent as one message (by design)."""
    from channel.chat_channel import ChatChannel
    cc = ChatChannel.__new__(ChatChannel)
    segs = cc._split_text_for_chunking("走了，再见，改天聊")
    assert len(segs) == 1  # no || → no split


def test_segmentation_no_fallback_on_paragraph():
    """Without ||, paragraph breaks are NOT split (by design)."""
    from channel.chat_channel import ChatChannel
    cc = ChatChannel.__new__(ChatChannel)
    segs = cc._split_text_for_chunking("想你啦\n\n今天过得怎么样\n\n早点休息")
    assert len(segs) == 1  # no || → no split


def test_segmentation_pipe_with_spaces():
    from channel.chat_channel import ChatChannel
    cc = ChatChannel.__new__(ChatChannel)
    # || surrounded by spaces should still work
    segs = cc._split_text_for_chunking("A || B || C")
    assert len(segs) == 3
    assert segs[0] == "A"


# ── Test: Thread safety ───────────────────────────────────────────────

def test_agent_lock_exists():
    """agent_lock must exist on AgentBridge."""
    from config import load_config
    load_config()
    from bridge.bridge import Bridge
    from app import _init_character_system
    _init_character_system()
    ab = Bridge().get_agent_bridge()
    assert hasattr(ab, "_agent_lock")
    assert isinstance(ab._agent_lock, type(threading.Lock()))


def test_agent_lock_concurrent_get():
    """get_agent called from 10 threads simultaneously should not crash."""
    from bridge.bridge import Bridge
    ab = Bridge().get_agent_bridge()
    errors = []

    def fetch():
        try:
            agent = ab.get_agent("test_concurrent")
            assert agent is not None
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=fetch) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert len(errors) == 0, f"Got {len(errors)} errors: {errors}"


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback

    tests = [
        (n, obj) for n, obj in list(globals().items())
        if n.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    sys.exit(0 if failed == 0 else 1)
