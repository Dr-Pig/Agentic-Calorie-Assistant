from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_context_engineering_golden_set.yaml"
)


def load_context_engineering_golden_set() -> dict[str, Any]:
    data = yaml.safe_load(GOLDEN_SET_PATH.read_text(encoding="utf-8-sig"))
    return dict(data)


def golden_set_case_ids() -> list[str]:
    return [str(item["case_id"]) for item in load_context_engineering_golden_set()["cases"]]


__all__ = ["GOLDEN_SET_PATH", "golden_set_case_ids", "load_context_engineering_golden_set"]
