from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.manifest import build_advanced_shadow_lab_manifest


STAGE_ORDER = ("long_term_memory", "recommendation", "rescue", "proactive")
STAGE_DECISIONS = (
    ("long_term_memory", "runtime_lab_memory_stage_promotion_decision", None),
    (
        "recommendation",
        "recommendation_read_only_runtime_stage_decision",
        "recommendation_read_only_runtime_promoted",
    ),
    (
        "rescue",
        "rescue_read_only_runtime_stage_decision",
        "rescue_read_only_runtime_promoted",
    ),
    (
        "proactive",
        "proactive_read_only_runtime_stage_decision",
        "proactive_read_only_runtime_promoted",
    ),
)
STAGE_FALSE_FLAGS = (
    "mainline_runtime_connected",
    "mainline_runtime_activation_approved",
    "mainline_route_or_api_mount_allowed",
    "route_or_api_activation_allowed",
    "production_scheduler_delivery_allowed",
    "scheduler_activation_allowed",
    "scheduler_enabled",
    "notification_delivery_allowed",
    "live_delivery_allowed",
    "push_or_line_delivery_connected",
    "production_db_migration_allowed",
    "canonical_product_mutation_allowed",
    "canonical_mutation_changed",
    "mutation_changed",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "ledger_entry_created",
    "durable_memory_written",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
    "user_facing_behavior_changed",
    "runtime_effect_allowed",
    "recommendation_served",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "rescue_proposal_committed",
    "rescue_committed",
    "proposal_committed",
    "proactive_sent",
    "product_readiness_claimed",
    "private_self_use_approved",
)


def build_advanced_shadow_lab_stage_snapshot_manifest(
    *,
    memory_stage_decision: Mapping[str, Any],
    recommendation_stage_decision: Mapping[str, Any],
    rescue_stage_decision: Mapping[str, Any],
    proactive_stage_decision: Mapping[str, Any],
) -> dict[str, Any]:
    stage_inputs = (
        _mapping(memory_stage_decision),
        _mapping(recommendation_stage_decision),
        _mapping(rescue_stage_decision),
        _mapping(proactive_stage_decision),
    )
    blockers: list[str] = []
    payloads: list[dict[str, Any]] = []
    source_types: dict[str, Any] = {}
    for contract, decision in zip(STAGE_DECISIONS, stage_inputs, strict=True):
        capability, artifact_type, promoted_flag = contract
        blockers.extend(
            _stage_decision_blockers(capability, artifact_type, promoted_flag, decision)
        )
        payload = _capability_payload(capability, promoted_flag, decision)
        payloads.append(payload)
        source_types[capability] = payload["source_artifact_type"]

    status = "pass" if not blockers else "blocked"
    manifest = build_advanced_shadow_lab_manifest()
    manifest.update(
        {
            "status": status,
            "blockers": blockers,
            "slice_mode": ["diagnostic_only", "manual_promotion", "offline_runtime"],
            "semantic_domains_implemented": list(STAGE_ORDER)
            if status == "pass"
            else [],
            "capability_payloads": payloads if status == "pass" else [],
            "stage_order": list(STAGE_ORDER),
            "lab_stage_snapshot": "read_only_runtime",
            "stage_snapshot_complete": status == "pass",
            "manual_promotion_snapshot_recorded": status == "pass",
            "source_artifact_types": source_types,
            "artifact_classification": "manual_promotion",
            "required_merge_check": False,
            "runtime_truth_changed": False,
            "non_claims": {
                **manifest["non_claims"],
                "not_read_only_runtime_serving_evidence": True,
                "not_scheduler_delivery_evidence": True,
            },
        }
    )
    manifest.update({flag: False for flag in STAGE_FALSE_FLAGS})
    return manifest


def _stage_decision_blockers(
    capability: str,
    artifact_type: str,
    promoted_flag: str | None,
    decision: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    expected_values = {
        "artifact_type": artifact_type,
        "status": "approved",
        "capability": capability,
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
    }
    for field, expected in expected_values.items():
        if decision.get(field) != expected:
            blockers.append(f"{capability}.{_blocker_name(field)}")

    required_true = ("stage_change_recorded", "manual_promotion_approved")
    for flag in required_true:
        if decision.get(flag) is not True:
            blockers.append(f"{capability}.{flag}_missing")
    if decision.get("automatic_stage_promotion_allowed") is True:
        blockers.append(f"{capability}.automatic_promotion_allowed")
    if promoted_flag and decision.get(promoted_flag) is not True:
        blockers.append(f"{capability}.{promoted_flag}_missing")

    for blocker in _string_list(decision.get("blockers")):
        blockers.append(f"{capability}.{blocker}")
    for flag in STAGE_FALSE_FLAGS:
        if decision.get(flag) is True:
            blockers.append(f"{capability}.{flag}")
    for flag, value in _mapping(decision.get("no_go_flags")).items():
        if value is True:
            blockers.append(f"{capability}.no_go_flag_true:{flag}")
    return blockers


def _capability_payload(
    capability: str,
    promoted_flag: str | None,
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "capability": capability,
        "source_artifact_type": decision.get("artifact_type"),
        "source_status": decision.get("status"),
        "current_stage": decision.get("current_stage"),
        "target_stage": decision.get("target_stage"),
        "activation_stage_after_decision": decision.get(
            "activation_stage_after_decision"
        ),
        "stage_change_recorded": decision.get("stage_change_recorded") is True,
        "manual_promotion_approved": decision.get("manual_promotion_approved") is True,
        "scope_keys": dict(_mapping(decision.get("scope_keys"))),
    }
    if promoted_flag:
        payload["promoted_flag"] = promoted_flag
        payload["promoted"] = decision.get(promoted_flag) is True
    return payload


def _blocker_name(field: str) -> str:
    return {
        "artifact_type": "unsupported_artifact_type",
        "status": "status_not_approved",
    }.get(field, f"{field}_mismatch")


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
