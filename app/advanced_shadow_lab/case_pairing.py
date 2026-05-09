from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.case_pairing"
)


def build_case_pairing(
    *,
    baseline: list[Mapping[str, Any]],
    advanced: list[Mapping[str, Any]],
    false_flags: tuple[str, ...],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not baseline and not advanced:
        return _summary("not_run", 0, 0, 0, [], []), []
    base_by_id, adv_by_id = _by_case_id(baseline), _by_case_id(advanced)
    case_ids = sorted(set(base_by_id) | set(adv_by_id))
    rows: list[dict[str, str]] = []
    gaps: list[str] = []
    violations: list[str] = []
    for case_id in case_ids:
        base, adv = base_by_id.get(case_id), adv_by_id.get(case_id)
        if base is None:
            gaps.append(f"{case_id}.missing_baseline_artifact")
        if adv is None:
            gaps.append(f"{case_id}.missing_advanced_artifact")
        if base and adv:
            rows.append(_row(case_id, base, adv))
        for side, artifact in (("baseline", base), ("advanced", adv)):
            if artifact:
                violations.extend(
                    f"{case_id}.{side}.{flag}"
                    for flag in (*false_flags, "runtime_connected")
                    if artifact.get(flag) is True
                )
    status = "pairable" if not gaps and not violations else "not_pairable"
    return _summary(status, len(baseline), len(advanced), len(rows), gaps, violations), rows


def _row(case_id: str, base: Mapping[str, Any], adv: Mapping[str, Any]) -> dict[str, str]:
    base_status = str(base.get("status") or "missing")
    adv_status = str(adv.get("status") or "missing")
    return {
        "case_id": case_id,
        "baseline_artifact_type": str(base.get("artifact_type") or ""),
        "advanced_artifact_type": str(adv.get("artifact_type") or ""),
        "baseline_status": base_status,
        "advanced_status": adv_status,
        "finding": "pairable_no_activation_drift"
        if base_status == adv_status == "pass"
        else "status_variance",
    }


def _summary(
    status: str,
    base_count: int,
    adv_count: int,
    paired: int,
    gaps: list[str],
    violations: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "baseline_case_count": base_count,
        "advanced_case_count": adv_count,
        "paired_case_count": paired,
        "schema_gaps": gaps,
        "activation_violations": violations,
    }


def _by_case_id(items: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item.get("case_id") or ""): item
        for item in items
        if str(item.get("case_id") or "")
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_case_pairing"]
