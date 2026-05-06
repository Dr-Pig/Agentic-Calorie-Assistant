from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.nutrition.application.exact_brand_web_canary import ExactBrandWebCanaryOutcome
from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
)
from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.retrieval_intent_runtime_boundary import (
    build_retrieval_intent_runtime_boundary_artifact,
)


def _raw_hint_route_plan():
    return build_food_evidence_retriever_route_plan(
        build_retrieval_intent("星巴克冰拿鐵大杯"),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
        intent_source="raw_text_hint",
    )


def test_retrieval_intent_runtime_boundary_keeps_raw_hint_out_of_runtime_execution() -> None:
    artifact = build_retrieval_intent_runtime_boundary_artifact()

    assert artifact["artifact_type"] == "accurate_intake_retrieval_intent_runtime_boundary_v1"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["summary"]["observed_runtime_call_file_count"] == 1
    assert artifact["summary"]["unexpected_runtime_call_file_count"] == 0
    assert artifact["summary"]["raw_text_runtime_execution_blocked"] is True
    assert artifact["summary"]["exact_brand_canary_manager_guard_clear"] is True
    assert artifact["runtime_call_site_audit"]["observed_runtime_call_files"] == [
        "app/nutrition/application/exact_brand_web_canary.py"
    ]
    assert artifact["exact_brand_web_canary_probe"]["skip_reason"] == (
        "manager_owned_retrieval_intent_required"
    )
    assert artifact["exact_brand_web_canary_probe"]["retrieval_goal"] is None
    assert artifact["exact_brand_web_canary_probe"]["raw_text_retrieval_hint_goal"] == (
        "exact_brand_lookup"
    )


def test_retrieval_intent_runtime_boundary_blocks_unexpected_runtime_call_sites() -> None:
    artifact = build_retrieval_intent_runtime_boundary_artifact(
        runtime_call_files=(
            "app/nutrition/application/exact_brand_web_canary.py",
            "app/runtime/bad_runtime_path.py",
        )
    )

    assert artifact["status"] == "blocked"
    assert (
        "unexpected_raw_text_retrieval_runtime_call:app/runtime/bad_runtime_path.py"
        in artifact["blockers"]
    )


def test_retrieval_intent_runtime_boundary_blocks_raw_hint_execution_attempt() -> None:
    artifact = build_retrieval_intent_runtime_boundary_artifact(
        raw_hint_route_plan=replace(
            _raw_hint_route_plan(),
            primary_backend="sqlite_fts_index",
            backend_sequence=("sqlite_fts_index",),
            raw_text_hint_executed=True,
            read_only=False,
            mutation_allowed=True,
        )
    )

    assert artifact["status"] == "blocked"
    assert "raw_text_hint_route_not_blocked" in artifact["blockers"]
    assert "raw_text_hint_route_has_backend_sequence" in artifact["blockers"]
    assert "raw_text_hint_route_executed_runtime_lookup" in artifact["blockers"]
    assert "raw_text_hint_route_not_read_only" in artifact["blockers"]
    assert "raw_text_hint_route_allowed_mutation" in artifact["blockers"]


def test_retrieval_intent_runtime_boundary_blocks_canary_runtime_execution_without_manager() -> None:
    artifact = build_retrieval_intent_runtime_boundary_artifact(
        canary_outcome=ExactBrandWebCanaryOutcome(
            result=object(),  # type: ignore[arg-type]
            trace={
                "skip_reason": "not_blocked",
                "semantic_authority_source": "live_manager_structured_output",
                "retrieval_goal": "exact_brand_lookup",
                "raw_text_retrieval_hint_goal": "exact_brand_lookup",
                "attempted": True,
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "exact_brand_canary_raw_hint_produced_runtime_result" in artifact["blockers"]
    assert "exact_brand_canary_missing_manager_guard" in artifact["blockers"]
    assert "exact_brand_canary_wrong_authority_source" in artifact["blockers"]
    assert "exact_brand_canary_raw_hint_owned_retrieval_goal" in artifact["blockers"]
    assert "exact_brand_canary_attempted_runtime_execution" in artifact["blockers"]


def test_retrieval_intent_runtime_boundary_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_retrieval_intent_runtime_boundary import main

    output = tmp_path / "retrieval_intent_runtime_boundary.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_retrieval_intent_runtime_boundary_v1"
    assert artifact["status"] == "pass"
