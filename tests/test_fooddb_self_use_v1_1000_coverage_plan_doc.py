from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/quality/FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md")
DOC_INDEX_PATH = Path("docs/DOC_INDEX.md")


def _content() -> str:
    return DOC_PATH.read_text(encoding="utf-8-sig")


def test_fooddb_self_use_v1_plan_freezes_1000_packet_ready_target() -> None:
    content = _content()

    assert "total_packet_ready_records: 1000" in content
    assert "exact_brand_item: 250" in content
    assert "generic_common_serving_anchor: 400" in content
    assert "listed_component_anchor: 350" in content
    assert "exact_macro_complete_minimum: 200" in content
    assert "broad_raw_source_rows_not_counted_as_packet_ready: true" in content


def test_fooddb_self_use_v1_plan_preserves_owner_boundaries_and_macro_policy() -> None:
    content = _content()

    assert "Owner: FoodDB" in content
    assert "user_intent: ManagerRuntime" in content
    assert "food_source_truth: FoodDB approved packet-ready artifact" in content
    assert "kcal_logging_blocked_by_missing_macro: false" in content
    assert "LLM_invented_protein_carbs_fat" in content
    assert "frontend_macro_sum_from_text" in content
    assert "raw_source_rows" in content
    assert "WebSearch_snippets" in content


def test_fooddb_self_use_v1_plan_defines_live_llm_and_edge_matrix_acceptance() -> None:
    content = _content()

    assert "fixed_18_case_live_llm_required: true" in content
    assert "manifest: docs/quality/accurate_intake_mvp_live_diagnostic_case_manifest.json" in content
    assert "provider_calls_required: true" in content
    assert "edge_live_matrix_min_cases: 36" in content
    assert "all_blocking_trace_layers_green: true" in content
    assert "no_websearch_snippet_as_truth: true" in content


def test_fooddb_self_use_v1_plan_is_discoverable_from_doc_index() -> None:
    index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md" in index
