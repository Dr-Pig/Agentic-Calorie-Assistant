from __future__ import annotations

import json
from pathlib import Path


def test_calibration_benchmark_fixture_has_expected_shape() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "calibration_benchmark_cases.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert len(cases) >= 20
    categories = {case["category"] for case in cases}
    assert categories == {
        "simple_anchored_foods",
        "exact_branded_items",
        "composite_cooked_dishes",
        "customizable_drinks",
        "quantity_missing_home_meals",
    }
    assert all({"id", "category", "query", "expected_mode"} <= set(case) for case in cases)
