"""Tests for install_engine.py — TDD: these fail before implementation exists."""

import os
import sys
import tempfile
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scripts.installer.install_engine import InstallEngine


def test_engine_has_run_method():
    """InstallEngine should expose a run() method."""
    engine = InstallEngine("/tmp/test", None)
    assert hasattr(engine, "run")
    assert callable(engine.run)


def test_engine_stores_install_dir():
    """InstallEngine should store the install directory."""
    engine = InstallEngine("/some/path", None)
    assert engine.install_dir == "/some/path"


def test_engine_stores_callback_queue():
    """InstallEngine should accept a callback queue."""
    import queue
    q = queue.Queue()
    engine = InstallEngine("/tmp/test", q)
    assert engine.callback_queue is q


def test_discover_payload_path():
    """_discover_payload_path should return a directory that exists."""
    import queue
    engine = InstallEngine("/tmp/test", queue.Queue())
    path = engine._discover_payload_path()
    # Falls back to scripts/installer/payload in dev mode
    assert os.path.isdir(path)
    assert os.path.basename(path) in ("payload", "installer")


def test_default_install_dir_windows():
    """On Windows, default path should be under C:\\Program Files or user-chosen."""
    import queue
    engine = InstallEngine("/tmp/test", queue.Queue())
    default = engine.get_default_install_dir()
    assert isinstance(default, str)
    assert len(default) > 2


def test_step_emit():
    """_step should emit a (percent, text) tuple to the queue."""
    import queue
    q = queue.Queue()
    engine = InstallEngine("/tmp/test", q)
    engine._step("testing", 42)
    item = q.get(timeout=1)
    assert item == (42, "testing")


def test_validate_path_creatable():
    """_validate_path should return True for a writable path."""
    import queue
    engine = InstallEngine("/tmp/test", queue.Queue())
    valid, msg = engine.validate_path(tempfile.mkdtemp())
    assert valid
    assert msg == ""


def test_validate_path_empty():
    """_validate_path should reject empty path."""
    import queue
    engine = InstallEngine("/tmp/test", queue.Queue())
    valid, msg = engine.validate_path("")
    assert not valid
    assert len(msg) > 0


def test_validate_path_invalid_chars_windows():
    """_validate_path should reject paths with invalid characters on Windows."""
    import queue
    engine = InstallEngine("/tmp/test", queue.Queue())
    if sys.platform == "win32":
        valid, msg = engine.validate_path('C:\\test\\bad?name')
        assert not valid
