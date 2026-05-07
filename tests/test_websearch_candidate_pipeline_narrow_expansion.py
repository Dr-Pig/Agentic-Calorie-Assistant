from __future__ import annotations

from app.nutrition.application.websearch_candidate_pipeline import (
    build_websearch_candidate_pipeline_diagnostic,
)
from app.nutrition.application.websearch_grokfast_live_diagnostic_case_matrix import (
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from app.nutrition.application.websearch_candidate_pipeline_narrow_expansion import (
    build_websearch_candidate_pipeline_narrow_expansion_artifact,
)


def test_websearch_candidate_pipeline_narrow_expansion_proves_later_live_cases_are_covered() -> None:
    artifact = build_websearch_candidate_pipeline_narrow_expansion_artifact(
        candidate_pipeline_artifact=build_websearch_candidate_pipeline_diagnostic(),
        live_case_matrix_artifact=build_websearch_grokfast_live_diagnostic_case_matrix_artifact(),
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_candidate_pipeline_narrow_expansion_v1"
    )
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["required_expansion_case_count"] == 7
    assert artifact["summary"]["covered_expansion_case_count"] == 7
    assert artifact["summary"]["pipeline_case_count"] == 23
    assert artifact["summary"]["live_case_matrix_case_count"] == 11
    assert artifact["next_required_slice"] == "inspect_websearch_status_packet"

    checkpoints = {case["checkpoint_id"]: case for case in artifact["coverage_checkpoints"]}
    assert checkpoints["official_brand_positive.large_size_preferred"]["pipeline_case_id"] == (
        "pipeline_large_size_preferred"
    )
    assert checkpoints["official_brand_positive.modifier_same_candidate"]["pipeline_case_id"] == (
        "pipeline_modifier_match_preferred"
    )
    assert checkpoints["negative_mismatch.serving_size_not_listed"]["pipeline_case_id"] == (
        "pipeline_serving_size_not_listed"
    )
    assert checkpoints["negative_mismatch.size_unknown_requires_followup"]["pipeline_case_id"] == (
        "pipeline_size_unknown_requires_followup"
    )
    assert checkpoints["source_quality.brand_page_without_nutrition"]["pipeline_case_id"] == (
        "pipeline_missing_kcal"
    )
    assert checkpoints["source_quality.third_party_blog_snippet"]["pipeline_case_id"] == (
        "pipeline_third_party_weak"
    )
    assert checkpoints["source_quality.all_candidates_blocked_source_policy"]["pipeline_case_id"] == (
        "pipeline_all_candidates_blocked"
    )


def test_websearch_candidate_pipeline_narrow_expansion_blocks_missing_checkpoint() -> None:
    pipeline = build_websearch_candidate_pipeline_diagnostic()
    pipeline["cases"] = [
        case for case in pipeline["cases"] if case["case_id"] != "pipeline_all_candidates_blocked"
    ]
    pipeline["summary"]["case_count"] = len(pipeline["cases"])

    artifact = build_websearch_candidate_pipeline_narrow_expansion_artifact(
        candidate_pipeline_artifact=pipeline,
        live_case_matrix_artifact=build_websearch_grokfast_live_diagnostic_case_matrix_artifact(),
    )

    assert artifact["status"] == "blocked"
    assert "missing_pipeline_case.pipeline_all_candidates_blocked" in artifact["blockers"]
    assert artifact["next_required_slice"] == "websearch_candidate_pipeline_narrow_expansion"
