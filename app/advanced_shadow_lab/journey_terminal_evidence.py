from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.edge_case_coverage import load_edge_case_coverage_contract
from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.advanced_shadow_lab.paired_fixture_cases import CASE_DEFINITIONS
from app.advanced_shadow_lab.ux_acceptance_coverage import REQUIRED_UX_JOURNEY_IDS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.journey_terminal_evidence")
TERMINAL_ARTIFACT_REFS = [
    "advanced_shadow_e2e_fixture_chain_artifact",
    "proactive_no_send_review_sink_artifact",
    "advanced_shadow_chat_ux_packet_artifact",
]
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)


def build_journey_terminal_evidence(
    fixture_chain_artifact: Mapping[str, Any],
) -> list[dict[str, Any]]:
    ux_entries = _ux_acceptance_entries_by_id()
    return [_evidence_row(case, ux_entries, fixture_chain_artifact) for case in CASE_DEFINITIONS]


def journey_terminal_evidence_summary(
    fixture_chain_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [
        _mapping(item)
        for item in fixture_chain_artifact.get("journey_terminal_evidence") or []
        if isinstance(item, Mapping)
    ]
    by_id = {str(row.get("journey_id") or ""): row for row in rows}
    missing = [
        journey_id
        for journey_id in REQUIRED_UX_JOURNEY_IDS
        if journey_id not in by_id
    ]
    blocked = [
        journey_id
        for journey_id in REQUIRED_UX_JOURNEY_IDS
        if journey_id in by_id and _row_status(by_id.get(journey_id)) != "pass"
    ]
    activation = _activation_violations(rows)
    return {
        "status": "pass" if not missing and not blocked and not activation else "blocked",
        "required_journey_ids": list(REQUIRED_UX_JOURNEY_IDS),
        "observed_journey_ids": [
            journey_id
            for journey_id in REQUIRED_UX_JOURNEY_IDS
            if journey_id in by_id
        ],
        "evidence_count": len(rows),
        "missing_journey_ids": missing,
        "blocked_journey_ids": blocked,
        "activation_violations": activation,
        "new_report_family_created": False,
    }


def journey_terminal_evidence_blockers(summary: Mapping[str, Any]) -> list[str]:
    return [
        *(f"journey_terminal_evidence.missing_journey:{journey_id}"
          for journey_id in summary.get("missing_journey_ids") or []),
        *(f"journey_terminal_evidence.blocked_journey:{journey_id}"
          for journey_id in summary.get("blocked_journey_ids") or []),
        *(f"journey_terminal_evidence.activation:{violation}"
          for violation in summary.get("activation_violations") or []),
    ]


def journey_terminal_evidence_row(summary: Mapping[str, Any]) -> dict[str, str]:
    status = str(summary.get("status") or "blocked")
    return {
        "surface": "ux_journey_terminal_evidence",
        "fixture_status": status,
        "dogfood_status": "not_applicable",
        "live_status": "not_required",
        "finding": "all_required_journeys_have_terminal_lab_evidence"
        if status == "pass"
        else "journey_terminal_evidence_blocked",
    }


def _evidence_row(
    case: tuple[str, str, str, tuple[str, ...]],
    ux_entries: Mapping[str, Mapping[str, Any]],
    fixture_chain: Mapping[str, Any],
) -> dict[str, Any]:
    journey_id, journey_name, _, source_refs = case
    ux_entry = _mapping(ux_entries.get(journey_id))
    blockers = _terminal_blockers(fixture_chain, ux_entry)
    return {
        "journey_id": journey_id,
        "journey_name": journey_name,
        "status": "blocked" if blockers else "pass",
        "comparison_scope": "ux_journey_terminal_lab_only_evidence",
        "source_artifact_refs": list(source_refs),
        "required_trace_fields": list(ux_entry.get("required_trace_fields") or []),
        "terminal_artifact_refs": list(TERMINAL_ARTIFACT_REFS),
        "terminal_statuses": _terminal_statuses(fixture_chain),
        "no_send_control_evidence": _control_evidence(fixture_chain),
        "blockers": blockers,
        "semantic_truth_owner": "source_artifacts_not_journey_evidence_generator",
        "semantic_decision_inferred_by_runner": False,
        **dict(FALSE_FLAGS),
    }


def _terminal_blockers(
    fixture_chain: Mapping[str, Any],
    ux_entry: Mapping[str, Any],
) -> list[str]:
    statuses = _terminal_statuses(fixture_chain)
    blockers = [
        f"{name}.status_{status}"
        for name, status in statuses.items()
        if status != "pass"
    ]
    if not ux_entry.get("required_trace_fields"):
        blockers.append("required_trace_fields_missing")
    control = _control_evidence(fixture_chain)
    if control["status"] != "pass":
        blockers.append(f"no_send_control_evidence.status_{control['status']}")
    if control["next_signal_required_present"] is not True:
        blockers.append("no_send_control_evidence.next_signal_missing")
    if control["configured_paths"] != {"dismiss": True, "snooze": True, "undo": True}:
        blockers.append("no_send_control_evidence.configured_paths_incomplete")
    return blockers


def _terminal_statuses(fixture_chain: Mapping[str, Any]) -> dict[str, str]:
    return {
        "fixture_chain": str(fixture_chain.get("status") or "missing"),
        "terminal_review_sink": str(
            _mapping(fixture_chain.get("terminal_review_sink")).get("status")
            or "missing"
        ),
        "chat_ux_packet": str(
            _mapping(fixture_chain.get("chat_ux_packet")).get("status")
            or "missing"
        ),
    }


def _control_evidence(fixture_chain: Mapping[str, Any]) -> dict[str, Any]:
    sink = _mapping(fixture_chain.get("terminal_review_sink"))
    control = _mapping(sink.get("control_path_evidence"))
    return {
        "status": str(control.get("status") or "missing"),
        "configured_paths": dict(_mapping(control.get("configured_paths"))),
        "next_signal_required_present": (
            control.get("next_signal_required_present") is True
        ),
    }


def _ux_acceptance_entries_by_id() -> dict[str, Mapping[str, Any]]:
    coverage = load_edge_case_coverage_contract()
    return {
        str(entry.get("journey_id") or ""): _mapping(entry)
        for entry in coverage.get("ux_acceptance_entries") or []
        if isinstance(entry, Mapping)
    }


def _activation_violations(rows: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"{row.get('journey_id') or 'unknown_journey'}.{flag}"
        for row in rows
        for flag in FALSE_FLAG_NAMES
        if row.get(flag) is True
    ]


def _row_status(row: Mapping[str, Any] | None) -> str:
    if row is None:
        return "missing"
    return str(row.get("status") or "blocked")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_journey_terminal_evidence",
    "journey_terminal_evidence_blockers",
    "journey_terminal_evidence_row",
    "journey_terminal_evidence_summary",
]
