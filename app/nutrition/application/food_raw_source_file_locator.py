from __future__ import annotations

import hashlib
from pathlib import Path


def find_source_file(filename: str, scan_roots: list[Path]) -> tuple[Path, Path] | None:
    for root in scan_roots:
        if not root.exists():
            continue
        if root.is_file() and root.name == filename:
            return root, root.parent
        if root.is_dir():
            direct = root / filename
            if direct.exists():
                return direct, root
            for candidate in root.rglob(filename):
                if candidate.is_file():
                    return candidate, root
    return None


def path_hash(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


__all__ = [
    "find_source_file",
    "path_hash",
    "relative_to_root",
]
