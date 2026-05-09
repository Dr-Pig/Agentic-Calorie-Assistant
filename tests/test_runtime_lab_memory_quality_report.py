from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _trace() -> dict:
    return {
        "request_id": "rt-lab-report-001",
        "trace_meta": {
            "request_id": "rt-lab-report-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "report-run-001",
        },
        "request": {"user_id": "user-a", "text": "structured report replay"},
        "renderer_output": {"assistant_message": "Logged lunch."},
        "tool_plan": ["estimate_nutrition"],
        "state_delta": {"meal_log_id": "meal-1"},
        "manager_final_decision": {"workflow_effect": "commit_meal_log"},
        "memory_lab_candidate_signal": {
            "candidate_type": "preference",
            "manager_decision_field": "memory_candidate_requested",
            "source_refs": ["message:dogfood-report-001"],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["explicit_user_preference"],
            "summary": "prefers lighter lunch suggestions",
        },
    }


def _fixture_artifacts(tmp_path: Path) -> dict:
    from app.memory.application.runtime_lab_candidate_extraction import (
        build_candidate_extraction_artifact_from_edd_suite,
        build_candidate_extraction_artifact_from_ingress_events,
    )
    from app.memory.application.runtime_lab_lifecycle_validator import (
        build_lifecycle_decision_artifact,
    )
    from app.memory.application.runtime_lab_manager_injection import (
        build_manager_memory_injection_comparison,
    )
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )
    from app.memory.application.runtime_lab_retrieval import (
        build_shadow_memory_context_pack,
    )
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore
    from app.memory.application.runtime_lab_trace_ingress import (
        build_memory_ingress_event_from_manager_trace,
    )

    suite = load_runtime_lab_memory_edd_suite()
    fixture_extraction = build_candidate_extraction_artifact_from_edd_suite(suite)
    event = build_memory_ingress_event_from_manager_trace(_trace())
    dogfood_extraction = build_candidate_extraction_artifact_from_ingress_events([event])
    lifecycle = build_lifecycle_decision_artifact(
        dogfood_extraction["candidates"],
        as_of="2026-05-09T00:00:00+08:00",
        runtime_connected=True,
    )
    store = RuntimeLabMemoryStore(tmp_path / "store")
    for candidate in dogfood_extraction["candidates"]:
        store.write_candidate(candidate)
    pack = build_shadow_memory_context_pack(
        store,
        event["scope_keys"],
        token_budget=120,
        runtime_connected=True,
    )
    injection = build_manager_memory_injection_comparison(
        _trace(),
        pack,
        enable_lab_injection=True,
    )
    return {
        "suite": suite,
        "fixture_extraction": fixture_extraction,
        "dogfood_extraction": dogfood_extraction,
        "lifecycle": lifecycle,
        "context_pack": pack,
        "injection": injection,
    }


def _consumer_summary_projection() -> dict:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def _review_contract(status: str = "pass") -> dict:
    return {
        "artifact_type": "runtime_lab_memory_candidate_review_contract",
        "status": status,
        "reviewed_shadow_candidates": [
            {
                "candidate_id": "reviewed-pref-1",
                "candidate_type": "preference",
                "scope_keys": {
                    "user_id": "user-a",
                    "workspace_id": "workspace-a",
                    "project_id": "advanced-memory-runtime-lab",
                    "surface": "manager_runtime_lab",
                    "run_id": "report-run-001",
                },
                "source_trace_ids": ["trace:reviewed-pref-1"],
                "source_object_refs": ["message:reviewed-pref-1"],
                "review_status": "accepted_shadow",
                "payload": {"summary": "prefers lighter lunch suggestions"},
                "promotion_allowed_now": False,
                "runtime_effect_allowed": False,
                "durable_product_memory_written": False,
                "manager_context_packet_changed": False,
            }
        ],
        "blockers": [] if status == "pass" else ["fixture_review_contract_blocker"],
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def test_quality_report_schema_claim_boundaries_and_shadow_readiness(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    report = build_runtime_lab_memory_quality_report(**_fixture_artifacts(tmp_path))

    assert report["artifact_type"] == "runtime_lab_memory_shadow_quality_report"
    assert report["status"] == "pass"
    assert report["claim_boundaries"] == {
        "product_activation_ready": False,
        "private_self_use_approval": False,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
    }
    assert set(report["downstream_shadow_readiness"]) == {
        "recommendation_read_only",
        "rescue_read_only",
        "proactive_read_only",
    }
    assert all(
        item["status"] == "ready_for_shadow_planning"
        for item in report["downstream_shadow_readiness"].values()
    )


def test_quality_report_covers_fixture_holdout_negative_and_regression(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    report = build_runtime_lab_memory_quality_report(**_fixture_artifacts(tmp_path))

    assert report["coverage"]["split_counts"] == {
        "fixture": 6,
        "holdout": 2,
        "negative": 2,
    }
    assert report["coverage"]["fixture_case_count"] == 10
    assert report["coverage"]["dogfood_replay_candidate_count"] == 1
    assert report["coverage"]["lab_injection_compared"] is True


def test_quality_report_can_include_reviewed_dogfood_replay_review(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_dogfood_replay import (
        build_memory_dogfood_replay_review_artifact,
    )
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    artifacts = _fixture_artifacts(tmp_path)
    dogfood_replay_review = build_memory_dogfood_replay_review_artifact(
        [
            {
                "trace": _trace(),
                "review": {
                    "reviewer_id": "fixture-human-reviewer",
                    "case_type": "explicit_preference",
                    "split": "holdout",
                    "expected_outcome": "candidate",
                    "expected_candidate_type": "preference",
                    "semantic_oracle_source": "product_rule_and_trace_fields",
                    "raw_keyword_route_allowed": False,
                    "source_ref_confirmation": True,
                },
            }
        ]
    )

    report = build_runtime_lab_memory_quality_report(
        **artifacts,
        dogfood_replay_review=dogfood_replay_review,
    )

    assert report["coverage"]["dogfood_reviewed_case_count"] == 1
    assert report["coverage"]["dogfood_reviewed_proposed_split_counts"] == {
        "holdout": 1
    }


def test_quality_report_marks_downstream_shadow_input_ready_with_summary_projection(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    report = build_runtime_lab_memory_quality_report(
        **_fixture_artifacts(tmp_path),
        consumer_summary_projection=_consumer_summary_projection(),
    )

    assert report["coverage"]["consumer_summary_projection_present"] is True
    assert report["downstream_shadow_readiness"] == {
        "recommendation_read_only": {
            "status": "ready_for_shadow_build",
            "allowed_input": "runtime_lab_memory_consumer_summary_projection",
        },
        "rescue_read_only": {
            "status": "ready_for_shadow_build",
            "allowed_input": "runtime_lab_memory_consumer_summary_projection",
        },
        "proactive_read_only": {
            "status": "ready_for_shadow_build",
            "allowed_input": "runtime_lab_memory_consumer_summary_projection",
        },
    }
    assert report["activation_boundaries"] == {
        "durable_memory_activation_ready": False,
        "manager_context_packet_memory_ready": False,
        "user_facing_memory_ready": False,
        "scheduler_or_proactive_send_ready": False,
        "recommendation_serving_ready": False,
        "rescue_proposal_commit_ready": False,
    }
    assert report["next_allowed_downstream_slices"] == [
        "recommendation_shadow_summary_consumer",
        "rescue_shadow_summary_consumer",
        "proactive_no_send_summary_consumer",
    ]


def test_quality_report_blocks_downstream_shadow_readiness_on_projection_claim_drift(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    projection = _consumer_summary_projection()
    projection["recommendation_served"] = True

    report = build_runtime_lab_memory_quality_report(
        **_fixture_artifacts(tmp_path),
        consumer_summary_projection=projection,
    )

    assert report["status"] == "blocked"
    assert "consumer_summary_projection.recommendation_served" in report["blockers"]
    assert all(
        item["status"] == "blocked_by_claim_boundary"
        for item in report["downstream_shadow_readiness"].values()
    )


def test_quality_report_activation_ladder_status_is_explicit(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    report = build_runtime_lab_memory_quality_report(**_fixture_artifacts(tmp_path))
    ladder = {item["stage"]: item["status"] for item in report["activation_ladder"]}

    assert ladder == {
        "contract": "complete",
        "fixture_fake": "complete",
        "live_diagnostic": "complete",
        "isolated_shadow_store": "complete",
        "lab_only_context_injection": "complete",
        "shadow_comparison": "complete",
    }


def test_quality_report_blocks_behavior_or_mutation_claim_drift(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_quality_report import (
        build_runtime_lab_memory_quality_report,
    )

    artifacts = _fixture_artifacts(tmp_path)
    artifacts["injection"] = dict(artifacts["injection"])
    artifacts["injection"]["user_facing_behavior_changed"] = True

    report = build_runtime_lab_memory_quality_report(**artifacts)

    assert report["status"] == "blocked"
    assert "user_facing_behavior_changed" in report["blockers"]
    assert all(
        item["status"] == "blocked_by_claim_boundary"
        for item in report["downstream_shadow_readiness"].values()
    )


def test_quality_report_runner_writes_non_claim_artifact(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "quality_report.json"
    store_root = tmp_path / "store"
    trace_path.write_text(json.dumps(_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_runtime_lab_memory_quality_report.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
            "--as-of",
            "2026-05-09T00:00:00+08:00",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["artifact_type"] == "runtime_lab_memory_shadow_quality_report"
    assert report["optional_live_run_invoked"] is False
    assert report["claim_boundaries"]["product_activation_ready"] is False
    assert report["live_evidence_required_for_merge"] is False


def test_quality_report_runner_threads_review_contract_into_summary_projection(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    review_contract_path = tmp_path / "review_contract.json"
    output_path = tmp_path / "quality_report.json"
    store_root = tmp_path / "store"
    trace_path.write_text(json.dumps(_trace()), encoding="utf-8")
    review_contract_path.write_text(json.dumps(_review_contract()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_runtime_lab_memory_quality_report.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
            "--as-of",
            "2026-05-09T00:00:00+08:00",
            "--review-contract-json",
            str(review_contract_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["coverage"]["consumer_summary_projection_present"] is True
    assert (
        report["coverage"]["consumer_summary_projection_artifact_type"]
        == "runtime_lab_memory_consumer_summary_projection"
    )
    assert report["next_allowed_downstream_slices"] == [
        "recommendation_shadow_summary_consumer",
        "rescue_shadow_summary_consumer",
        "proactive_no_send_summary_consumer",
    ]
    assert all(
        item["status"] == "ready_for_shadow_build"
        for item in report["downstream_shadow_readiness"].values()
    )
    assert report["claim_boundaries"]["durable_product_memory_written"] is False


def test_quality_report_runner_blocks_failed_review_contract_projection(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    review_contract_path = tmp_path / "blocked_review_contract.json"
    output_path = tmp_path / "quality_report.json"
    store_root = tmp_path / "store"
    trace_path.write_text(json.dumps(_trace()), encoding="utf-8")
    review_contract_path.write_text(
        json.dumps(_review_contract(status="blocked")),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_runtime_lab_memory_quality_report.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
            "--as-of",
            "2026-05-09T00:00:00+08:00",
            "--review-contract-json",
            str(review_contract_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert "consumer_summary_projection.status_not_pass" in report["blockers"]
    assert all(
        item["status"] == "blocked_by_claim_boundary"
        for item in report["downstream_shadow_readiness"].values()
    )
