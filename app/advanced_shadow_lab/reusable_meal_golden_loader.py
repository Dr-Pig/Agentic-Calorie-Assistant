from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_reusable_meal_golden_set.yaml"
)


def load_reusable_meal_golden_set() -> dict[str, Any]:
    return yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8-sig"))


__all__ = ["load_reusable_meal_golden_set"]
