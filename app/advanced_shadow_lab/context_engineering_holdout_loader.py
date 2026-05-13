from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
HOLDOUT_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_context_engineering_holdouts.yaml"
)


def load_context_engineering_holdouts() -> dict[str, Any]:
    data = yaml.safe_load(HOLDOUT_PATH.read_text(encoding="utf-8-sig"))
    return dict(data)


__all__ = ["HOLDOUT_PATH", "load_context_engineering_holdouts"]
