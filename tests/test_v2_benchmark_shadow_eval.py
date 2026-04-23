from __future__ import annotations

from scripts.run_v2_benchmark_shadow_eval import (
    _parse_replay_cases,
    _parse_v1_cases,
    _parse_v2_cases,
    build_normalized_registry,
    build_shadow_report,
    select_blocking_cases,
)


def test_parse_v1_cases_reads_archive_text_cases() -> None:
    cases = _parse_v1_cases()
    assert cases
    assert any(case["source_case_id"] == "case_001" for case in cases)
    assert any(case["source_case_id"] == "case_003" for case in cases)
    assert all(case["source_suite"] == "benchmark_test_set_v1" for case in cases)


def test_parse_v2_cases_reads_archive_text_cases() -> None:
    cases = _parse_v2_cases()
    assert cases
    assert any(str(case["source_case_id"]).startswith("case_001") for case in cases)
    assert all(case["source_suite"] == "benchmark_test_set_v2" for case in cases)


def test_parse_replay_cases_reads_all_turn2_hybrid_cases() -> None:
    cases = _parse_replay_cases()
    assert len(cases) == 9
    assert all(case["source_suite"] == "turn2_hybrid_replay_pack_v1" for case in cases)
    assert all(case["blocking_candidate"] is False for case in cases)


def test_build_shadow_report_marks_promotion_candidates_and_dedupe_status() -> None:
    registry = build_normalized_registry()
    report = build_shadow_report(registry)
    assert report["summary"]["dedupe_status"] == "complete"
    assert report["summary"]["shadow_case_status"] == "normalized"
    assert report["summary"]["quality_gap_status"] == "not_run"
    assert report["summary"]["promotion_candidate_status"] in {"identified", "none"}
    assert "blocking_registry" in report


def test_select_blocking_cases_promotes_replay_and_one_exact_case_per_domain() -> None:
    registry = build_normalized_registry()
    selected = select_blocking_cases(registry)
    replay_cases = [case for case in selected if str(case.get("evidence_topology", "")).startswith("replay_")]
    assert len(replay_cases) == 9
    starbucks_cases = [case for case in selected if case.get("source_domain") == "starbucks"]
    assert len(starbucks_cases) == 1
    assert any(case.get("evidence_topology") == "multi_item_exact_combo" for case in selected)
