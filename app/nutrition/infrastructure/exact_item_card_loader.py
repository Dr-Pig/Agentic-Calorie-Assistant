from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .knowledge_paths import repo_local_knowledge_path


@lru_cache(maxsize=1)
def load_exact_item_card_seed_records() -> list[dict[str, Any]]:
    path = repo_local_knowledge_path("exact_item_cards_tw.json")
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("cards", []))


__all__ = ["load_exact_item_card_seed_records"]
