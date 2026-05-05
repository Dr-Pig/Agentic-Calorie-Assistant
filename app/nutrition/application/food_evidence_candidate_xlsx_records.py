from __future__ import annotations

from typing import Any

from app.nutrition.application.food_evidence_candidate_record_values import text


def detect_tfda_header(rows: list[tuple[Any, ...]]) -> tuple[int, dict[str, int]]:
    for index, row in enumerate(rows[:8]):
        values = [text(value) for value in row]
        if "樣品名稱" in values and (
            "修正熱量(kcal)" in values or "熱量(kcal)" in values
        ):
            return index, {
                "category": values.index("食品分類") if "食品分類" in values else 0,
                "label": values.index("樣品名稱"),
                "aliases": values.index("俗名") if "俗名" in values else 2,
                "kcal": values.index("熱量(kcal)") if "熱量(kcal)" in values else 3,
                "corrected_kcal": values.index("修正熱量(kcal)")
                if "修正熱量(kcal)" in values
                else 4,
            }
    return 1, {
        "category": 0,
        "label": 1,
        "aliases": 2,
        "kcal": 3,
        "corrected_kcal": 4,
    }


def xlsx_row_record(row: tuple[Any, ...], columns: dict[str, int]) -> dict[str, Any]:
    return {
        field: row[index] if index < len(row) else None
        for field, index in columns.items()
    }


__all__ = [
    "detect_tfda_header",
    "xlsx_row_record",
]
