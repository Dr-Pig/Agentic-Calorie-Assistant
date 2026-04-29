from __future__ import annotations

from pathlib import Path


def repo_local_knowledge_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge"


def repo_local_knowledge_path(filename: str) -> Path:
    return repo_local_knowledge_dir() / filename


__all__ = ["repo_local_knowledge_dir", "repo_local_knowledge_path"]
