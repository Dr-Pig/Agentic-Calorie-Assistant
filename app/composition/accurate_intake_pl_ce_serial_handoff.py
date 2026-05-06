from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


EXPECTED_QUEUE_METADATA_ARTIFACT_TYPE = "accurate_intake_pl_ce_merge_queue_metadata"
ALLOWED_QUEUE_METADATA_SOURCES = {
    "github_merge_queue_snapshot",
    "merge_queue_snapshot",
    "queue_steward_snapshot",
    "human_review_snapshot",
}
READY_QUEUE_STATUSES = {"queued", "merged", "checks_success", "waiting_checks", "ready_for_queue"}
READY_CHECK_STATUSES = {"success", "pending"}

FORBIDDEN_TRUTHY_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "mutation_authority",
    "frontend_semantic_owner",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "canonical_eval_promoted",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return True


def _activation_manifest_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") != "accurate_intake_pl_ce_activation_review_manifest":
        blockers.append(f"activation_review_manifest.unexpected_artifact_type:{payload.get('artifact_type')}")
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append("activation_review_manifest.missing_artifact_schema_version")
    if payload.get("status") != "pl_ce_activation_review_manifest_ready":
        blockers.append(f"activation_review_manifest.unexpected_status:{payload.get('status')}")
    if payload.get("blockers") != []:
        blockers.append("activation_review_manifest.upstream_blockers_present")
    if payload.get("aggregate_only") is not True:
        blockers.append("activation_review_manifest.aggregate_only_not_true")
    if payload.get("self_generated_evidence_used") is not False:
        blockers.append("activation_review_manifest.self_generated_evidence_not_false")
    if payload.get("human_review_required") is not True:
        blockers.append("activation_review_manifest.human_review_required_not_true")
    if payload.get("live_diagnostic_human_approval_required") is not True:
        blockers.append("activation_review_manifest.live_human_approval_not_required")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(payload.get(flag)):
            blockers.append(f"activation_review_manifest.{flag}")
    stop_gates = _object_dict(payload.get("remaining_stop_gates"))
    if stop_gates.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
        blockers.append("activation_review_manifest.fooddb_stop_gate_missing")
    if stop_gates.get("live_provider_status") != "blocked_pending_human_approval":
        blockers.append("activation_review_manifest.live_provider_stop_gate_missing")
    return blockers


def _queue_items(queue_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    items = queue_metadata.get("queue_items")
    if not isinstance(items, list):
        return []
    return [_object_dict(item) for item in items]


def _queue_blockers(queue_metadata: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not queue_metadata:
        return ["queue_metadata.missing"]
    if queue_metadata.get("artifact_type") in {
        "missing_pl_ce_pr_stack_metadata",
        "missing_pl_ce_merge_queue_metadata",
    }:
        return ["queue_metadata.missing"]
    if queue_metadata.get("artifact_type") in {
        "invalid_missing_pl_ce_pr_stack_metadata",
        "invalid_missing_pl_ce_pr_stack_metadata_shape",
        "invalid_missing_pl_ce_merge_queue_metadata",
        "invalid_missing_pl_ce_merge_queue_metadata_shape",
    }:
        return ["queue_metadata.invalid"]
    if queue_metadata.get("artifact_type") != EXPECTED_QUEUE_METADATA_ARTIFACT_TYPE:
        blockers.append(
            f"queue_metadata.unexpected_artifact_type:{queue_metadata.get('artifact_type')}"
        )
    if queue_metadata.get("metadata_source") not in ALLOWED_QUEUE_METADATA_SOURCES:
        blockers.append(
            f"queue_metadata.untrusted_metadata_source:{queue_metadata.get('metadata_source')}"
        )
    if queue_metadata.get("merge_queue_required") is not True:
        blockers.append("queue.merge_queue_required_not_true")
    if queue_metadata.get("producer_should_manual_merge") is not False:
        blockers.append("queue.producer_should_manual_merge_not_false")

    policy = _object_dict(queue_metadata.get("queue_policy"))
    expected_policy = {
        "merge_mechanism": "github_merge_queue",
        "old_main_merge_lock_used": False,
        "manual_main_merge_forbidden": True,
        "wait_for_pr_merged_before_next_slice": True,
        "cleanup_only_after_merged_and_clean": True,
    }
    for key, expected_value in expected_policy.items():
        actual_value = policy.get(key)
        if actual_value != expected_value:
            if key == "old_main_merge_lock_used" and actual_value is True:
                blockers.append("queue.old_main_merge_lock_used")
            else:
                blockers.append(f"queue.policy.{key}_unexpected:{actual_value}")

    items = _queue_items(queue_metadata)
    if not items:
        blockers.append("queue.no_items")
        return blockers
    for index, item in enumerate(items, start=1):
        slice_id = str(item.get("slice_id") or f"item_{index}")
        if not item.get("slice_id"):
            blockers.append(f"queue.{slice_id}.missing_slice_id")
        pr_number = item.get("pr_number")
        if not isinstance(pr_number, int) or pr_number <= 0:
            blockers.append(f"queue.{slice_id}.invalid_pr_number:{pr_number}")
        head = str(item.get("head") or "")
        if not head.startswith("codex/"):
            blockers.append(f"queue.{slice_id}.unexpected_head:{head or 'missing'}")
        if item.get("base") != "main":
            blockers.append(f"queue.{slice_id}.base_not_main:{item.get('base')}")
        if item.get("state") not in {"open", "merged"}:
            blockers.append(f"queue.{slice_id}.unexpected_state:{item.get('state')}")
        if item.get("draft") is not False:
            blockers.append(f"queue.{slice_id}.draft_not_false")
        if item.get("ready_for_queue") is not True:
            blockers.append(f"queue.{slice_id}.ready_for_queue_not_true")
        checks = str(item.get("checks") or "")
        if checks not in READY_CHECK_STATUSES:
            blockers.append(f"queue.{slice_id}.checks_{checks or 'missing'}")
        queue_status = str(item.get("merge_queue_status") or "")
        if queue_status not in READY_QUEUE_STATUSES:
            blockers.append(f"queue.{slice_id}.merge_queue_status_not_ready:{queue_status or 'missing'}")
    return blockers


def _included_artifacts(activation_review_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "activation_review_manifest": {
            "artifact_type": activation_review_manifest.get("artifact_type", "not_available"),
            "status": activation_review_manifest.get("status", "not_available"),
            "source_artifact_path": activation_review_manifest.get(
                "_source_artifact_path",
                "not_available",
            ),
        }
    }


def build_pl_ce_serial_handoff_artifact(
    *,
    activation_review_manifest: dict[str, Any],
    queue_metadata: dict[str, Any] | None = None,
    stack_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = _object_dict(activation_review_manifest)
    queue = _object_dict(queue_metadata if queue_metadata is not None else stack_metadata)
    blockers = [*_activation_manifest_blockers(manifest), *_queue_blockers(queue)]
    status = "ready_for_merge_queue_review" if not blockers else "blocked"
    stop_gates = _object_dict(manifest.get("remaining_stop_gates"))
    queue_metadata_valid = not any(
        blocker.startswith(("queue.", "queue_metadata.", "stack_metadata.")) for blocker in blockers
    )
    policy = _object_dict(queue.get("queue_policy"))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_serial_handoff",
            "claim_scope": "pl_ce_merge_queue_handoff_for_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "status": status,
            "producer_track": "PL_CE",
            "delivery_mode": "github_merge_queue",
            "blockers": blockers,
            "included_artifacts": _included_artifacts(manifest),
            "queue_items": _queue_items(queue),
            "expected_delivery_policy": {
                "merge_mechanism": "github_merge_queue",
                "source_branch_base": "main",
                "after_pr_ready": "add_to_merge_queue",
                "continue_after": "pr_merged_and_main_ci_green",
                "cleanup": "cleanup_only_after_merged_and_clean",
                "do_not_use": ["main-merge-lock", "manual_main_merge", "long_lived_stack"],
            },
            "queue_metadata_valid": queue_metadata_valid,
            "stack_order_valid": queue_metadata_valid,
            "stack_metadata_valid": queue_metadata_valid,
            "activation_review_manifest_ready": not any(
                blocker.startswith("activation_review_manifest.") for blocker in blockers
            ),
            "merge_queue_required": True,
            "merge_owner_required": False,
            "producer_should_manual_merge": False,
            "producer_should_merge": False,
            "producer_should_wait_for_queue_merge": True,
            "producer_should_continue_after_merge": True,
            "producer_should_continue_building": False,
            "old_main_merge_lock_used": policy.get("old_main_merge_lock_used", "not_available"),
            "cleanup_after_merged_only": True,
            "autofix_attempted": False,
            "local_only": True,
            "diagnostic_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "human_review_required": True,
            "remaining_stop_gates": {
                "fooddb_artifact_status": stop_gates.get(
                    "fooddb_artifact_status",
                    "blocked_waiting_for_fdb_artifact",
                ),
                "live_provider_status": stop_gates.get(
                    "live_provider_status",
                    "blocked_pending_human_approval",
                ),
                "merge_queue_status": "required",
                "manual_merge_status": "forbidden",
            },
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
        }
    )


__all__ = [
    "EXPECTED_QUEUE_METADATA_ARTIFACT_TYPE",
    "build_pl_ce_serial_handoff_artifact",
]
