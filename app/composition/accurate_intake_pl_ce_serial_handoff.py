from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


EXPECTED_STACK = (
    {
        "slice_id": "local_mvp_candidate_bundle",
        "pr_number": 281,
        "head": "codex/plce-local-mvp-candidate-bundle-v1",
        "base": "main",
    },
    {
        "slice_id": "browser_activation_evidence_gate",
        "pr_number": 283,
        "head": "codex/plce-browser-activation-evidence-gate-v1",
        "base": "codex/plce-local-mvp-candidate-bundle-v1",
    },
    {
        "slice_id": "activation_review_manifest",
        "pr_number": 287,
        "head": "codex/plce-activation-review-manifest-v1",
        "base": "codex/plce-browser-activation-evidence-gate-v1",
    },
)
EXPECTED_STACK_METADATA_ARTIFACT_TYPE = "accurate_intake_pl_ce_pr_stack_metadata"
ALLOWED_STACK_METADATA_SOURCES = {
    "merge_owner_snapshot",
    "github_pr_metadata_snapshot",
    "human_review_snapshot",
}

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


def _stack_items(stack_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    items = stack_metadata.get("stack_items")
    if not isinstance(items, list):
        return []
    return [_object_dict(item) for item in items]


def _stack_blockers(stack_metadata: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not stack_metadata:
        return ["stack_metadata.missing"]
    if stack_metadata.get("artifact_type") == "missing_pl_ce_pr_stack_metadata":
        return ["stack_metadata.missing"]
    if stack_metadata.get("artifact_type") in {
        "invalid_missing_pl_ce_pr_stack_metadata",
        "invalid_missing_pl_ce_pr_stack_metadata_shape",
    }:
        return ["stack_metadata.invalid"]
    if stack_metadata.get("artifact_type") != EXPECTED_STACK_METADATA_ARTIFACT_TYPE:
        blockers.append(f"stack_metadata.unexpected_artifact_type:{stack_metadata.get('artifact_type')}")
    if stack_metadata.get("metadata_source") not in ALLOWED_STACK_METADATA_SOURCES:
        blockers.append(f"stack_metadata.untrusted_metadata_source:{stack_metadata.get('metadata_source')}")
    if stack_metadata.get("merge_owner_required") is not True:
        blockers.append("stack.merge_owner_required_not_true")
    if stack_metadata.get("producer_should_merge") is not False:
        blockers.append("stack.producer_should_merge_not_false")
    items = _stack_items(stack_metadata)
    if len(items) != len(EXPECTED_STACK):
        blockers.append("stack.unexpected_item_count")
        return blockers
    for expected, item in zip(EXPECTED_STACK, items, strict=True):
        slice_id = expected["slice_id"]
        if item.get("slice_id") != slice_id:
            blockers.append(f"stack.{slice_id}.unexpected_slice_id:{item.get('slice_id')}")
        if item.get("pr_number") != expected["pr_number"]:
            blockers.append(f"stack.{slice_id}.unexpected_pr_number:{item.get('pr_number')}")
        if item.get("head") != expected["head"]:
            blockers.append(f"stack.{slice_id}.unexpected_head:{item.get('head')}")
        if item.get("base") != expected["base"]:
            blockers.append(f"stack.{slice_id}.unexpected_base:{item.get('base')}")
        if item.get("state") != "open":
            blockers.append(f"stack.{slice_id}.not_open:{item.get('state')}")
        if item.get("draft") is not True:
            blockers.append(f"stack.{slice_id}.draft_not_true")
        checks = str(item.get("checks") or "")
        if checks not in {"success", "pending"}:
            blockers.append(f"stack.{slice_id}.checks_{checks or 'missing'}")
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
    stack_metadata: dict[str, Any],
) -> dict[str, Any]:
    manifest = _object_dict(activation_review_manifest)
    stack = _object_dict(stack_metadata)
    blockers = [*_activation_manifest_blockers(manifest), *_stack_blockers(stack)]
    status = "ready_for_merge_owner_review" if not blockers else "blocked"
    stop_gates = _object_dict(manifest.get("remaining_stop_gates"))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_serial_handoff",
            "claim_scope": "pl_ce_serial_pr_handoff_for_merge_owner_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "status": status,
            "producer_track": "PL_CE",
            "blockers": blockers,
            "included_artifacts": _included_artifacts(manifest),
            "stack_items": _stack_items(stack),
            "expected_stack_order": list(EXPECTED_STACK),
            "stack_order_valid": not any(
                blocker.startswith(("stack.", "stack_metadata.")) for blocker in blockers
            ),
            "stack_metadata_valid": not any(
                blocker.startswith(("stack.", "stack_metadata.")) for blocker in blockers
            ),
            "activation_review_manifest_ready": not any(
                blocker.startswith("activation_review_manifest.") for blocker in blockers
            ),
            "merge_owner_required": True,
            "producer_should_merge": False,
            "producer_should_continue_building": True,
            "do_not_delete_stack_branches": True,
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
                "merge_owner_status": "required",
                "producer_merge_status": "forbidden",
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
    "EXPECTED_STACK",
    "build_pl_ce_serial_handoff_artifact",
]
