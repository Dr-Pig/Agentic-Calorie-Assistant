from __future__ import annotations

import json
from pathlib import Path

from app.application.context_assembly import normalize_user_input_for_estimation as _normalize_user_input_for_estimation


def test_real_world_regression_fixture_has_expected_shape() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "real_world_regression_cases.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert len(cases) == 10
    assert all({"id", "user_input", "expected_normalized_input", "category"} <= set(case) for case in cases)


def test_real_world_regression_fixture_matches_input_normalizer() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "real_world_regression_cases.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    for case in cases:
        normalized = _normalize_user_input_for_estimation(case["user_input"])
        assert isinstance(normalized["normalized_text"], str)
        assert normalized["normalized_text"].strip()
        assert isinstance(normalized["notes"], list)


def test_input_normalizer_marks_benchmark_tail_removal() -> None:
    result = _normalize_user_input_for_estimation(
        "統一巧克力牛乳（400ml）：測試 App 針對運動後補充品，數值是否和營養標示一致。"
    )

    assert "統一巧克力牛乳" in result["normalized_text"]
    assert result["normalizer_applied"] is False


def test_input_normalizer_extracts_example_payload() -> None:
    result = _normalize_user_input_for_estimation(
        "週末社交舞會上的零食（例如：多力多滋起司口味，隨手抓的一小把約 15 片）：測試 App 對於非標準包裝零食的份量估算。"
    )

    assert "多力多滋" in result["normalized_text"]
    assert result["normalizer_applied"] is False
