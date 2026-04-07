from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.benchmark_loader import parse_benchmark_text


ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_fixture_parses_external_source() -> None:
    source = Path(r"C:\Users\User\Desktop\benchmark_test_set_v1.txt")
    if not source.exists():
        pytest.skip("external benchmark source is not available in this environment")
    cases = parse_benchmark_text(source.read_text(encoding="utf-8"))

    assert len(cases) == 18
    assert all("id" in case and "input" in case for case in cases)
    assert all("expected_behavior" in case for case in cases)
    assert all("expected_evidence_outcome" in case for case in cases)
    assert all("source_of_truth" in case for case in cases)


def test_repo_benchmark_fixture_has_expected_shape() -> None:
    fixture = ROOT / "tests" / "fixtures" / "benchmark_test_set_v1.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))

    assert len(cases) == 18
    for case in cases:
        assert "id" in case
        assert "input" in case
        assert "expected_behavior" in case
        assert "expected_evidence_outcome" in case
        assert "source_of_truth" in case
        assert "parsed_truth" in case


def test_benchmark_fixture_extracts_known_truth_hints() -> None:
    fixture = ROOT / "tests" / "fixtures" / "benchmark_test_set_v1.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in cases}

    assert by_id["case_001"]["parsed_truth"]["exact_kcal"] == 189.0
    assert by_id["case_003"]["parsed_truth"]["exact_kcal"] == 503.17
    assert by_id["case_006"]["parsed_truth"]["macro_truth"] == {
        "protein_g": 31.0,
        "fat_g": 56.3,
        "carb_g": 145.1,
    }
