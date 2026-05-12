from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .knowledge_paths import repo_local_knowledge_dir, repo_local_knowledge_path


@lru_cache(maxsize=1)
def load_exact_item_card_seed_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _exact_item_card_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        for card in payload.get("cards", []):
            record = dict(card)
            record.setdefault("_fooddb_source_file", f"app/knowledge/{path.name}")
            records.append(record)
    return records


def _exact_item_card_paths() -> list[Path]:
    main_path = repo_local_knowledge_path("exact_item_cards_tw.json")
    paths = [main_path] if main_path.exists() else []
    batch_paths = sorted(repo_local_knowledge_dir().glob("exact_item_cards_tw_batch_*.json"))
    return [*paths, *batch_paths]


__all__ = ["load_exact_item_card_seed_records"]
