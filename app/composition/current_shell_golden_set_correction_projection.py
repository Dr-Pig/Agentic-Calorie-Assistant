from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_version_projection import old_version_not_counted


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def correction_operation(
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    phase_c_mutation: dict[str, Any],
) -> str:
    payloads = (
        _dict(manager_final.get("target_attachment")),
        _dict(_dict(manager_final.get("semantic_decision")).get("target_attachment")),
        _dict(manager_decision.get("target_attachment")),
        _dict(_dict(manager_decision.get("semantic_decision")).get("target_attachment")),
        _dict(phase_c_mutation.get("canonical_ids")),
    )
    for payload in payloads:
        operation = str(payload.get("operation") or payload.get("correction_operation") or "").strip()
        if operation:
            return operation
    return ""


def attach_removed_version_projection(
    runtime: dict[str, Any],
    *,
    request_trace: dict[str, Any],
    state_delta: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    phase_c_mutation: dict[str, Any],
) -> None:
    if "removed_versions_excluded_from_ledger" in runtime:
        return
    not_counted = old_version_not_counted(request_trace, state_delta)
    if not_counted is not None and correction_operation(manager_final, manager_decision, phase_c_mutation) == "remove_meal":
        runtime["removed_versions_excluded_from_ledger"] = not_counted
