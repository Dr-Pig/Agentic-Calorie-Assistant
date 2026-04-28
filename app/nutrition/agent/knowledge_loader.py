from __future__ import annotations

"""Raw knowledge-source loaders only.

Normalization, packet assembly, and scoring logic must stay in adjacent
modules; this file is intentionally limited to source access and cache seams.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

def _main_knowledge_dir() -> Path:
    return _repo_root().parent / "line-liff-calorie-helper-main" / "knowledge"

def _local_knowledge_dir() -> Path:
    return _repo_root() / "app" / "knowledge"

def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def _risk_profiles() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "risk_gate_packets_tw.json") or {}
    return list(payload.get("profiles", []))

@lru_cache(maxsize=1)
def _exact_item_cards() -> list[dict[str, Any]]:
    base_payload = _load_json(_local_knowledge_dir() / "exact_item_cards_tw.json") or {}
    overlay_payload = _load_json(_local_knowledge_dir() / "exact_item_cards_overlay_tw.json") or {}
    cards = list(base_payload.get("cards", []))
    cards.extend(list(overlay_payload.get("cards", [])))
    return cards

@lru_cache(maxsize=1)
def _meal_templates() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "meal_templates_tw.json") or {}
    return list(payload.get("templates", []))

@lru_cache(maxsize=1)
def _base_nutrition_records() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "base_nutrition_db.json") or {}
    return list(payload.get("records", []))

@lru_cache(maxsize=1)
def _common_dish_priors() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "common_dish_priors_tw.json") or {}
    return list(payload.get("records", []))
