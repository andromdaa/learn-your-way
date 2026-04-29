import hashlib
from pathlib import Path

import pytest

from lyw_core.settings import Settings
from lyw_core.storage import DataDir


def test_bootstrap_creates_subdirs(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    for name in ("sources", "lessons", "assets", "indexes"):
        assert (tmp_path / name).is_dir(), f"missing subdir: {name}"


def test_bootstrap_is_idempotent(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    dd.bootstrap()  # must not raise
    for name in ("sources", "lessons", "assets", "indexes"):
        assert (tmp_path / name).is_dir()


def test_write_source_roundtrip(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    payload = b"%PDF-1.4 fake pdf content"
    path = dd.write_source("sample.pdf", payload)
    assert path.read_bytes() == payload


def test_write_source_is_under_sources(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    path = dd.write_source("doc.pdf", b"data")
    assert path.parent == tmp_path / "sources"


def test_write_asset_deterministic(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    payload = b"some asset bytes"
    p1 = dd.write_asset(payload, suffix=".bin")
    p2 = dd.write_asset(payload, suffix=".bin")
    assert p1 == p2


def test_write_asset_content_hash(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    payload = b"asset content"
    path = dd.write_asset(payload)
    digest = hashlib.sha256(payload).hexdigest()
    # stem of filename must equal full digest
    assert path.stem == digest


def test_write_asset_different_content_different_path(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    p1 = dd.write_asset(b"aaa")
    p2 = dd.write_asset(b"bbb")
    assert p1 != p2


def test_path_traversal_in_write_source_raises(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    with pytest.raises(ValueError):
        dd.write_source("../../etc/passwd", b"evil")


def test_path_traversal_absolute_raises(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    dd.bootstrap()
    with pytest.raises(ValueError):
        dd.write_source("/etc/passwd", b"evil")


def test_subdir_properties(tmp_path: Path) -> None:
    dd = DataDir(tmp_path)
    assert dd.sources == tmp_path / "sources"
    assert dd.lessons == tmp_path / "lessons"
    assert dd.assets == tmp_path / "assets"
    assert dd.indexes == tmp_path / "indexes"


def test_datadir_from_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYW_DATA_DIR", str(tmp_path))
    settings = Settings()
    dd = DataDir(settings.data_dir)
    dd.bootstrap()
    assert (settings.data_dir / "sources").is_dir()
