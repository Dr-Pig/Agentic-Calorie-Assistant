from __future__ import annotations

from typing import Any

from .fooddb_modifier_priority import P0_MODIFIERS


def coverage_checks(status_packet: dict[str, Any]) -> list[dict[str, Any]]:
    thresholds = status_packet["activation_thresholds"]
    return [
        _check(
            check_id="minimum_common_serving_anchor_count",
            check_group="coverage",
            passed=thresholds["meets_common_serving_anchor_minimum"] is True,
            details={
                "actual": status_packet["summary"]["runtime_common_serving_anchor_count"],
                "minimum": thresholds["minimum_common_serving_anchors"],
            },
        ),
        _check(
            check_id="minimum_listed_component_anchor_count",
            check_group="coverage",
            passed=thresholds["meets_listed_component_minimum"] is True,
            details={
                "actual": status_packet["summary"]["listed_component_anchor_count"],
                "minimum": thresholds["minimum_listed_component_anchors"],
            },
        ),
        _check(
            check_id="source_evidence_not_counted_as_runtime_anchor",
            check_group="coverage",
            passed=status_packet["fooddb_status"]["runtime_anchor_catalog_included"] is False,
            details={
                "source_evidence_only_count": status_packet["summary"]["source_evidence_only_count"],
                "runtime_anchor_catalog_included": status_packet["fooddb_status"][
                    "runtime_anchor_catalog_included"
                ],
            },
        ),
    ]


def modifier_checks(modifier_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = modifier_catalog["p0_support_matrix"]
    checks = []
    for modifier_name in P0_MODIFIERS:
        modifier = matrix.get(modifier_name) or {}
        checks.append(
            _check(
                check_id=f"p0_modifier_supported:{modifier_name}",
                check_group="modifier",
                passed=modifier.get("supported") is True,
                details={
                    "anchor_count": modifier.get("anchor_count", 0),
                    "supported_values": modifier.get("supported_values", []),
                },
            )
        )
    checks.append(
        _check(
            check_id="modifier_catalog_compact_runtime_only",
            check_group="modifier",
            passed=(
                modifier_catalog["manager_modifier_catalog"]["raw_source_rows_included"] is False
                and modifier_catalog["manager_modifier_catalog"]["candidate_only_records_included"] is False
                and not _contains_forbidden_compact_key(modifier_catalog["manager_modifier_catalog"])
            ),
            details=modifier_catalog["manager_modifier_catalog"],
        )
    )
    return checks


def packet_checks(packet_smoke: dict[str, Any]) -> list[dict[str, Any]]:
    cases = {case["case_id"]: case for case in packet_smoke["cases"]}
    return [
        _check(
            check_id="compact_packet_cases_all_pass",
            check_group="manager_packet",
            passed=packet_smoke["summary"]["compact_packet_pass_count"] == packet_smoke["summary"]["case_count"],
            details=packet_smoke["summary"],
        ),
        _check(
            check_id="boba_packet_has_p0_modifier_compatibility",
            check_group="manager_packet",
            passed=_case_has_compatible_modifiers(
                cases,
                "boba_large_half_sugar",
                {"cup_size", "sugar_level"},
            ),
            details=_case_modifier_details(cases, "boba_large_half_sugar"),
        ),
        _check(
            check_id="bento_packet_has_rice_modifier_compatibility",
            check_group="manager_packet",
            passed=_case_has_compatible_modifiers(
                cases,
                "chicken_bento_less_rice",
                {"rice_portion"},
            ),
            details=_case_modifier_details(cases, "chicken_bento_less_rice"),
        ),
        _check(
            check_id="bare_basket_packet_asks_followup_without_evidence",
            check_group="manager_packet",
            passed=_bare_basket_case_ok(cases),
            details=_case_packet_summary(cases, "bare_luwei"),
        ),
        _check(
            check_id="listed_basket_packet_uses_approved_components_only",
            check_group="manager_packet",
            passed=_listed_basket_case_ok(cases),
            details=_case_packet_summary(cases, "listed_luwei_components"),
        ),
        _check(
            check_id="typo_packet_requires_manager_disambiguation",
            check_group="manager_packet",
            passed=_typo_case_ok(cases),
            details=_case_packet_summary(cases, "boba_typo"),
        ),
    ]


def p0_supported_modifier_count(modifier_catalog: dict[str, Any]) -> int:
    return sum(1 for modifier in modifier_catalog["p0_support_matrix"].values() if modifier.get("supported") is True)


def upstream_next_required_slices(status_packet: dict[str, Any]) -> list[str]:
    next_required = [
        str(slice_id)
        for slice_id in status_packet.get("next_required_slices") or []
        if str(slice_id).strip()
    ]
    allowed = {"local_activation_scenario_wall_real_fooddb_packet"}
    return [slice_id for slice_id in next_required if slice_id not in allowed]


def next_required_slice(
    *,
    status: str,
    upstream_next_required: list[str],
) -> str:
    if status != "pass":
        return "inspect_fooddb_activation_wall_blockers"
    if upstream_next_required:
        return upstream_next_required[0]
    return "local_activation_scenario_wall_real_fooddb_packet"


def _case_has_compatible_modifiers(
    cases: dict[str, dict[str, Any]],
    case_id: str,
    expected_modifier_names: set[str],
) -> bool:
    packet = _case_packet(cases, case_id)
    items = packet.get("evidence_items") or []
    if len(items) != 1:
        return False
    compatibility = items[0].get("modifier_compatibility") or {}
    return all(
        compatibility.get(modifier_name)
        in {"compatible", "compatible_via_normalized_equivalent"}
        for modifier_name in expected_modifier_names
    )


def _case_modifier_details(cases: dict[str, dict[str, Any]], case_id: str) -> dict[str, Any]:
    packet = _case_packet(cases, case_id)
    return {
        "modifier_hints": packet.get("modifier_hints") or {},
        "evidence_modifier_compatibility": [
            item.get("modifier_compatibility") or {}
            for item in packet.get("evidence_items") or []
        ],
    }


def _bare_basket_case_ok(cases: dict[str, dict[str, Any]]) -> bool:
    packet = _case_packet(cases, "bare_luwei")
    return (
        packet.get("retrieval_boundary") == "bare_basket_ask_followup_no_estimate"
        and packet.get("runtime_mutation_allowed") is False
        and packet.get("evidence_items") == []
        and bool(packet.get("followup_hints"))
    )


def _listed_basket_case_ok(cases: dict[str, dict[str, Any]]) -> bool:
    packet = _case_packet(cases, "listed_luwei_components")
    items = packet.get("evidence_items") or []
    return (
        packet.get("retrieval_boundary") == "listed_basket_component_recall"
        and bool(items)
        and all(item.get("runtime_truth_allowed") is True for item in items)
        and all(item.get("runtime_role") == "common_serving_anchor" for item in items)
    )


def _typo_case_ok(cases: dict[str, dict[str, Any]]) -> bool:
    packet = _case_packet(cases, "boba_typo")
    items = packet.get("evidence_items") or []
    return (
        len(items) == 1
        and items[0].get("match_path") == "fuzzy_alias"
        and items[0].get("requires_manager_disambiguation") is True
        and packet.get("truth_selection_forbidden") is True
    )


def _case_packet_summary(cases: dict[str, dict[str, Any]], case_id: str) -> dict[str, Any]:
    packet = _case_packet(cases, case_id)
    items = packet.get("evidence_items") or []
    return {
        "retrieval_boundary": packet.get("retrieval_boundary"),
        "runtime_mutation_allowed": packet.get("runtime_mutation_allowed"),
        "truth_selection_forbidden": packet.get("truth_selection_forbidden"),
        "evidence_item_count": len(items),
        "evidence_anchor_ids": [item.get("anchor_id") for item in items],
        "followup_hints": packet.get("followup_hints") or [],
    }


def _case_packet(cases: dict[str, dict[str, Any]], case_id: str) -> dict[str, Any]:
    return cases[case_id]["manager_evidence_packet"]


def _check(
    *,
    check_id: str,
    check_group: str,
    passed: bool,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "check_group": check_group,
        "status": "pass" if passed else "fail",
        "details": details,
    }


_COMPACT_PACKET_FORBIDDEN_KEYS = frozenset({
    "candidate_only_records",
    "full_fooddb",
    "full_fooddb_dump",
    "raw_payload",
    "raw_row",
    "raw_row_hash",
    "raw_rows",
    "raw_source_payload",
    "raw_source_record",
    "raw_source_records",
    "raw_source_row",
    "raw_source_rows",
    "row_index",
    "source_record",
})


def _contains_forbidden_compact_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in _COMPACT_PACKET_FORBIDDEN_KEYS or _contains_forbidden_compact_key(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_compact_key(item) for item in value)
    return False


__all__ = [
    "coverage_checks",
    "modifier_checks",
    "next_required_slice",
    "p0_supported_modifier_count",
    "packet_checks",
    "upstream_next_required_slices",
]
