from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_pl_ce_serial_handoff_metadata import (
    current_metadata_freshness_blockers,
    current_metadata_freshness_summary,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_CLAIM_SCOPE,
    LEGACY_SERIAL_HANDOFF_ARTIFACT_TYPES,
    LEGACY_SERIAL_HANDOFF_CLAIM_SCOPES,
    set_legacy_alias_metadata,
)
from app.composition.current_shell_serial_handoff_policy import (
    EXPECTED_QUEUE_METADATA_ARTIFACT_TYPE,
    _activation_manifest_blockers,
    _queue_blockers,
    _queue_items,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _included_artifacts(
    activation_review_manifest: dict[str, Any],
    current_metadata_freshness_pack: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        "activation_review_manifest": {
            "artifact_type": activation_review_manifest.get("artifact_type", "not_available"),
            "status": activation_review_manifest.get("status", "not_available"),
            "source_artifact_path": activation_review_manifest.get(
                "_source_artifact_path",
                "not_available",
            ),
        },
        "current_metadata_freshness_pack": current_metadata_freshness_summary(
            current_metadata_freshness_pack
        ),
    }


def build_pl_ce_serial_handoff_artifact(
    *,
    activation_review_manifest: dict[str, Any],
    current_metadata_freshness_pack: dict[str, Any] | None = None,
    queue_metadata: dict[str, Any] | None = None,
    stack_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = _object_dict(activation_review_manifest)
    current_metadata = _object_dict(current_metadata_freshness_pack)
    queue = _object_dict(queue_metadata if queue_metadata is not None else stack_metadata)
    blockers = [
        *_activation_manifest_blockers(manifest),
        *current_metadata_freshness_blockers(current_metadata),
        *_queue_blockers(queue),
    ]
    status = "ready_for_merge_queue_review" if not blockers else "blocked"
    stop_gates = _object_dict(manifest.get("remaining_stop_gates"))
    queue_metadata_valid = not any(
        blocker.startswith(("queue.", "queue_metadata.", "stack_metadata.")) for blocker in blockers
    )
    policy = _object_dict(queue.get("queue_policy"))
    payload = {
        "artifact_schema_version": "1.0",
        "artifact_type": CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_ARTIFACT_TYPE,
        "claim_scope": CURRENT_SHELL_COMPATIBILITY_SERIAL_HANDOFF_CLAIM_SCOPE,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "producer_track": "CurrentShell",
        "delivery_mode": "github_merge_queue",
        "blockers": blockers,
        "included_artifacts": _included_artifacts(manifest, current_metadata),
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
        "current_metadata_freshness_ready": not any(
            blocker.startswith("current_metadata_freshness_pack.") for blocker in blockers
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
        "shared_contract_changed": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "production_db_used": False,
        "manager_context_packet_schema_changed": False,
        "mutation_authority": False,
    }
    set_legacy_alias_metadata(
        payload,
        legacy_artifact_types=LEGACY_SERIAL_HANDOFF_ARTIFACT_TYPES,
        legacy_claim_scopes=LEGACY_SERIAL_HANDOFF_CLAIM_SCOPES,
    )
    return _json_safe(payload)
