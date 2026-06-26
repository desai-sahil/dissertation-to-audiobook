"""Real FileCache: a filesystem content-addressed byte store for rendered chunks.

Keyed by the renderer's sha256 chunk key, sharded one level by the key prefix to keep
directories small. Persisting across runs is the whole point: an unchanged chunk is
served from disk instead of re-rendered (and re-billed). No network, no cost, so the
cost guard does not touch it; tests use MemoryCache instead.
"""

from __future__ import annotations

from pathlib import Path


class FileCache:
    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def _path(self, key: str) -> Path:
        return self._root / key[:2] / key

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def put(self, key: str, value: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
