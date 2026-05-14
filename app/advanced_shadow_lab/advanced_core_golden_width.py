from __future__ import annotations

from typing import Any


def validate_semantic_contract_width(
    contract: dict[str, Any],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    width = dict(contract.get("semantic_contract_width") or {})
    required_axes = [str(axis) for axis in width.get("required_axes") or []]
    axis_case_types_raw = dict(width.get("axis_case_types") or {})
    axis_case_types = {
        str(axis): [str(case_type) for case_type in case_types or []]
        for axis, case_types in axis_case_types_raw.items()
    }
    case_types = {str(case.get("case_type")) for case in cases}

    if not required_axes:
        blockers.append("semantic_contract_width.required_axes_missing")
    if not axis_case_types:
        blockers.append("semantic_contract_width.axis_case_types_missing")

    missing_required_axes = [
        axis for axis in required_axes if not axis_case_types.get(axis)
    ]
    for axis in missing_required_axes:
        blockers.append(f"semantic_contract_width.{axis}.missing_case_types")

    unknown_axis_case_types: list[str] = []
    for axis, mapped_case_types in axis_case_types.items():
        for case_type in mapped_case_types:
            if case_type not in case_types:
                unknown_axis_case_types.append(f"{axis}:{case_type}")
                blockers.append(
                    f"semantic_contract_width.{axis}.unknown_case_type:{case_type}"
                )

    covered_axes = [
        axis
        for axis, mapped_case_types in axis_case_types.items()
        if mapped_case_types
        and all(case_type in case_types for case_type in mapped_case_types)
    ]

    return {
        "required_axes": required_axes,
        "covered_axes": covered_axes,
        "missing_required_axes": missing_required_axes,
        "unknown_axis_case_types": unknown_axis_case_types,
        "blockers": blockers,
    }
