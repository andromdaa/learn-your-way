import hashlib
from pathlib import Path

_SUBDIRS = ("sources", "lessons", "assets", "indexes")


class DataDir:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def bootstrap(self) -> None:
        for name in _SUBDIRS:
            (self._root / name).mkdir(parents=True, exist_ok=True)

    @property
    def sources(self) -> Path:
        return self._root / "sources"

    @property
    def lessons(self) -> Path:
        return self._root / "lessons"

    @property
    def assets(self) -> Path:
        return self._root / "assets"

    @property
    def indexes(self) -> Path:
        return self._root / "indexes"

    def write_source(self, name: str, data: bytes) -> Path:
        dest = self._safe(self.sources / name)
        dest.write_bytes(data)
        return dest

    def write_asset(self, data: bytes, suffix: str = "") -> Path:
        digest = hashlib.sha256(data).hexdigest()
        shard = self.assets / digest[:2]
        shard.mkdir(parents=True, exist_ok=True)
        dest = shard / f"{digest}{suffix}"
        if not dest.exists():
            dest.write_bytes(data)
        return dest

    def _safe(self, path: Path) -> Path:
        resolved = path.resolve()
        if (
            not str(resolved).startswith(str(self._root) + "/")
            and resolved != self._root
        ):
            raise ValueError(f"path {path!r} escapes data directory {self._root!r}")
        return resolved
