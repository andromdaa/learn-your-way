"""Tests for lyw_core.settings.

Covers: typed defaults, LYW_-prefix env overrides, .env discovery,
and Literal validation for log_format.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from lyw_core.settings import Settings

_ALL_LYW_KEYS = [
    "LYW_DATA_DIR",
    "LYW_DB_PATH",
    "LYW_QDRANT_URL",
    "LYW_REDIS_URL",
    "LYW_OLLAMA_BASE_URL",
    "LYW_MODEL_NAME",
    "LYW_LOG_FORMAT",
]


def _clear_lyw(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ALL_LYW_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_lyw(monkeypatch)
    s = Settings(_env_file=tmp_path / "missing.env")  # type: ignore[call-arg]
    assert isinstance(s.data_dir, Path)
    assert isinstance(s.db_path, Path)
    assert s.qdrant_url == "http://localhost:6333"
    assert s.redis_url == "redis://localhost:6379/0"
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.model_name == "gemma3:4b"
    assert s.log_format == "console"


def test_env_prefix_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_lyw(monkeypatch)
    monkeypatch.setenv("LYW_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("LYW_REDIS_URL", "redis://redis:6379/1")
    monkeypatch.setenv("LYW_MODEL_NAME", "gemma3:12b")
    monkeypatch.setenv("LYW_LOG_FORMAT", "json")
    monkeypatch.setenv("LYW_DATA_DIR", str(tmp_path / "mydata"))
    s = Settings(_env_file=tmp_path / "missing.env")  # type: ignore[call-arg]
    assert s.qdrant_url == "http://qdrant:6333"
    assert s.redis_url == "redis://redis:6379/1"
    assert s.model_name == "gemma3:12b"
    assert s.log_format == "json"
    assert s.data_dir == tmp_path / "mydata"


def test_log_format_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_lyw(monkeypatch)
    monkeypatch.setenv("LYW_LOG_FORMAT", "xml")
    with pytest.raises(ValidationError):
        Settings(_env_file=tmp_path / "missing.env")  # type: ignore[call-arg]


def test_dotenv_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_lyw(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LYW_QDRANT_URL=http://qdrant-from-dotenv:6333\n"
        "LYW_MODEL_NAME=gemma3:27b\n"
    )
    s = Settings(_env_file=env_file)  # type: ignore[call-arg]
    assert s.qdrant_url == "http://qdrant-from-dotenv:6333"
    assert s.model_name == "gemma3:27b"
