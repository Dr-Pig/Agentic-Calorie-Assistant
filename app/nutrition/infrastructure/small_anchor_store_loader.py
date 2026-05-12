from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .knowledge_paths import repo_local_knowledge_dir, repo_local_knowledge_path


@lru_cache(maxsize=1)
def load_small_anchor_seed_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _small_anchor_store_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(list(payload.get("anchors", [])))
    return records


def _small_anchor_store_paths() -> list[Path]:
    main_path = repo_local_knowledge_path("small_anchor_store_tw.json")
    paths = [main_path] if main_path.exists() else []
    batch_paths = sorted(repo_local_knowledge_dir().glob("small_anchor_store_tw_batch_*.json"))
    return [*paths, *batch_paths]


__all__ = ["load_small_anchor_seed_records"]
