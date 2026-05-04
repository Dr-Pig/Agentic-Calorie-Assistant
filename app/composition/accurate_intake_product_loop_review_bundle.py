from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.composition.dogfood_review_queue import (
    build_dogfood_review_queue_artifact,
    build_review_candidate_from_product_loop_diagnostic,
)

FORBIDDEN_TRUE_CLAIM_FLAGS = (
    "fooddb_evidence_used",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "live_llm_invoked",
    "web_tavily_used",
    "fooddb_truth_updated",
    "manager_context_packet_schema_changed",
    "frontend_semantic_owner",
)

FIXTURE_REQUIRED_ARTIFACTS = (
    "browser_fixture_dogfood",
    "browser_realistic_dogfood",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _artifact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    claim_flags = {
        flag: payload.get(flag)
        for flag in (*FORBIDDEN_TRUE_CLAIM_FLAGS, "fixture_evidence_used")
        if flag in payload
    }
    return {
        "artifact_type": str(payload.get("artifact_type") or "unknown"),
        "status": str(payload.get("status") or "unknown"),
        "present": bool(payload),
        "claim_flags": claim_flags,
    }


def _review_candidates_from_diagnostics(
    diagnostics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        build_review_candidate_from_product_loop_diagnostic(diagnostic)
        for diagnostic in diagnostics
        if isinstance(diagnostic, dict) and diagnostic
    ]


def _input_claim_boundary_blockers(
    artifacts: dict[str, dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    for artifact_id, payload in artifacts.items():
        for flag in FORBIDDEN_TRUE_CLAIM_FLAGS:
            if payload.get(flag) is True:
                blockers.append(f"{artifact_id}.{flag}")
        if (
            artifact_id in FIXTURE_REQUIRED_ARTIFACTS
            and payload.get("fixture_evidence_used") is not True
        ):
            blockers.append(f"{artifact_id}.fixture_evidence_used_missing")
    return blockers


def build_product_loop_review_bundle_artifact(
    *,
    browser_shell_smoke: dict[str, Any],
    browser_fixture_dogfood: dict[str, Any],
    browser_realistic_dogfood: dict[str, Any],
    context_review: dict[str, Any],
    context_target_candidate_eval: dict[str, Any],
    context_window_diagnostic: dict[str, Any],
) -> dict[str, Any]:
    input_artifacts = {
        "browser_shell_smoke": browser_shell_smoke,
        "browser_fixture_dogfood": browser_fixture_dogfood,
        "browser_realistic_dogfood": browser_realistic_dogfood,
        "context_review": context_review,
        "context_target_candidate_eval": context_target_candidate_eval,
        "context_window_diagnostic": context_window_diagnostic,
    }
    input_claim_boundary_blockers = _input_claim_boundary_blockers(input_artifacts)
    diagnostics = [
        context_review,
        context_target_candidate_eval,
        context_window_diagnostic,
        browser_realistic_dogfood,
    ]
    review_queue = build_dogfood_review_queue_artifact(
        review_candidates=_review_candidates_from_diagnostics(diagnostics),
        correction_feedback_events=[],
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_product_loop_review_bundle_v1",
            "status": "blocked_input_overclaim"
            if input_claim_boundary_blockers
            else "product_loop_context_diagnostic_ready_for_human_review",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "product_loop_context_review_checkpoint",
            "local_only": True,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "input_claim_boundary_ok": not input_claim_boundary_blockers,
            "input_claim_boundary_blockers": input_claim_boundary_blockers,
            "ready_for_fdb_integration": False,
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "manager_context_packet_schema_changed": False,
            "frontend_semantic_owner": False,
            "included_artifacts": {
                artifact_id: _artifact_summary(payload)
                for artifact_id, payload in input_artifacts.items()
            },
            "included_artifact_statuses": {
                "browser_shell_smoke": _artifact_summary(browser_shell_smoke),
                "browser_fixture_dogfood": _artifact_summary(browser_fixture_dogfood),
                "browser_realistic_dogfood": _artifact_summary(browser_realistic_dogfood),
                "context_review": _artifact_summary(context_review),
                "context_target_candidate_eval": _artifact_summary(
                    context_target_candidate_eval
                ),
                "context_window_diagnostic": _artifact_summary(context_window_diagnostic),
            },
            "review_checkpoints": [
                "context_review_labels",
                "target_candidate_eval_scenarios",
                "review_queue_taxonomy",
                "fixture_only_waiting_for_fooddb_boundary",
            ],
            "review_queue": review_queue,
        }
    )


__all__ = [
    "FORBIDDEN_TRUE_CLAIM_FLAGS",
    "build_product_loop_review_bundle_artifact",
]
