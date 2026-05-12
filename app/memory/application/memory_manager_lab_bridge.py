from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_manager_lab_bridge"
)

LAB_CONTEXT_FIELD = "lab_memory_context_block"


def build_memory_manager_lab_bridge(
    *,
    manager_input: Mapping[str, Any],
    shadow_memory_context_pack: Mapping[str, Any],
    enable_lab_memory_context: bool,
) -> dict[str, Any]:
    baseline = deepcopy(dict(manager_input))
    blockers = _bridge_blockers(shadow_memory_context_pack)
    attach = enable_lab_memory_context and not blockers and _has_entries(shadow_memory_context_pack)
    augmented = deepcopy(baseline)
    if attach:
        augmented[LAB_CONTEXT_FIELD] = _context_block(shadow_memory_context_pack)
    return _artifact(
        baseline=baseline,
        augmented=augmented,
        shadow_memory_context_pack=shadow_memory_context_pack,
        enable_lab_memory_context=enable_lab_memory_context,
        attached=attach,
        blockers=blockers,
    )


def _artifact(
    *,
    baseline: dict[str, Any],
    augmented: dict[str, Any],
    shadow_memory_context_pack: Mapping[str, Any],
    enable_lab_memory_context: bool,
    attached: bool,
    blockers: list[str],
) -> dict[str, Any]:
    selected_ids = _string_list(shadow_memory_context_pack.get("selected_record_ids"))
    return {
        "artifact_type": "memory_manager_lab_bridge_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "lab_enabled": enable_lab_memory_context,
        "lab_user_facing_behavior_changed": attached,
        "baseline_manager_input": baseline,
        "memory_augmented_manager_input": augmented,
        "shadow_memory_context_pack_used": attached,
        "lab_manager_context_attached": attached,
        "selected_record_ids": selected_ids if attached else [],
        "negative_preference_blockers": (
            _string_list(shadow_memory_context_pack.get("negative_preference_blockers"))
            if attached
            else []
        ),
        "paired_trace": _paired_trace(
            baseline=baseline,
            augmented=augmented,
            selected_ids=selected_ids,
            attached=attached,
            shadow_memory_context_pack=shadow_memory_context_pack,
        ),
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "manager_context_injected": False,
        "manager_context_packet_changed": False,
        "mainline_runtime_connected": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "blockers": blockers,
        **NON_MUTATION_FLAGS,
    }


def _context_block(pack: Mapping[str, Any]) -> dict[str, Any]:
    entries = [
        _entry(entry)
        for entry in pack.get("entries") or []
        if isinstance(entry, Mapping)
    ]
    return {
        "artifact_type": "lab_memory_context_block",
        "source_artifact_type": str(pack.get("artifact_type") or ""),
        "summary_first": pack.get("summary_first") is True,
        "source_lookup_required_for_evidence": True,
        "selected_record_ids": _string_list(pack.get("selected_record_ids")),
        "negative_preference_blockers": _string_list(
            pack.get("negative_preference_blockers")
        ),
        "negative_blocker_subject_keys": _string_list(
            pack.get("negative_blocker_subject_keys")
        ),
        "entries": entries,
        "source_refs": _dedupe([ref for entry in entries for ref in entry["source_refs"]]),
        "omission_trace": [
            {"record_id": str(item.get("record_id") or ""), "reason": str(item.get("reason") or "")}
            for item in pack.get("omission_trace") or []
            if isinstance(item, Mapping)
        ],
        "token_estimate": int(pack.get("token_estimate") or 0),
    }


def _entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": str(entry.get("record_id") or ""),
        "record_type": str(entry.get("record_type") or ""),
        "family": str(entry.get("family") or ""),
        "summary": str(entry.get("summary") or ""),
        "polarity": str(entry.get("polarity") or ""),
        "strength": str(entry.get("strength") or ""),
        "subject_keys": _string_list(entry.get("subject_keys")),
        "source_refs": _string_list(entry.get("source_refs")),
        "store_name": str(entry.get("store_name") or ""),
        "item_names": _string_list(entry.get("item_names")),
        "estimated_kcal": _int_or_none(entry.get("estimated_kcal")),
        "surface_role": "lab_memory_manager_context_summary",
    }


def _bridge_blockers(pack: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"shadow_memory_context_pack.{blocker}"
        for blocker in pack.get("blockers") or []
    ]
    if pack.get("status") not in {"pass", None}:
        blockers.append(f"shadow_memory_context_pack.status_{pack.get('status')}")
    if pack.get("manager_context_packet_changed") is True:
        blockers.append("shadow_memory_context_pack.manager_context_packet_changed")
    if pack.get("manager_context_injected") is True:
        blockers.append("shadow_memory_context_pack.manager_context_injected")
    return [str(blocker) for blocker in blockers]


def _paired_trace(
    *,
    baseline: Mapping[str, Any],
    augmented: Mapping[str, Any],
    selected_ids: list[str],
    attached: bool,
    shadow_memory_context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "baseline_keys": sorted(str(key) for key in baseline),
        "memory_augmented_keys": sorted(str(key) for key in augmented),
        "baseline_has_lab_memory_context": LAB_CONTEXT_FIELD in baseline,
        "memory_run_has_lab_memory_context": LAB_CONTEXT_FIELD in augmented,
        "selected_record_ids": selected_ids if attached else [],
        "omitted_record_ids": [
            str(item.get("record_id") or "")
            for item in shadow_memory_context_pack.get("omission_trace") or []
            if isinstance(item, Mapping)
        ],
        "manager_context_packet_changed": False,
        "lab_context_field": LAB_CONTEXT_FIELD if attached else "",
    }


def _has_entries(pack: Mapping[str, Any]) -> bool:
    return bool([entry for entry in pack.get("entries") or [] if isinstance(entry, Mapping)])


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "LAB_CONTEXT_FIELD",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_manager_lab_bridge",
]
