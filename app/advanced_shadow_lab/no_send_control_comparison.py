from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.no_send_control_comparison"
)

CONTROL_FIELDS = (
    "configured_paths",
    "interaction_actions_observed",
    "next_signal_required_present",
)


def compare_no_send_control_paths(
    *,
    fixture_sink: Mapping[str, Any],
    dogfood_sink: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    fixture = _mapping(fixture_sink.get("control_path_evidence"))
    dogfood = _mapping(dogfood_sink.get("control_path_evidence"))
    result = {
        "fixture_status": _status(fixture),
        "dogfood_status": _status(dogfood),
        "configured_paths_match": _field_matches(fixture, dogfood, "configured_paths"),
        "observed_actions_match": _field_matches(
            fixture, dogfood, "interaction_actions_observed"
        ),
        "next_signal_required_match": _field_matches(
            fixture, dogfood, "next_signal_required_present"
        ),
    }
    finding = _finding(result)
    result["finding"] = finding
    return result, _row(result), _blockers(result)


def terminal_sink_row(
    *,
    fixture_chain: Mapping[str, Any],
    dogfood_replay: Mapping[str, Any],
) -> dict[str, str]:
    fixture_status = _sink_status(_mapping(fixture_chain.get("terminal_review_sink")))
    dogfood_status = _sink_status(_mapping(dogfood_replay.get("terminal_review_sink_summary")))
    return {
        "surface": "terminal_no_send_review_sink",
        "fixture_status": fixture_status,
        "dogfood_status": dogfood_status,
        "live_status": "not_applicable",
        "finding": "no_drift"
        if fixture_status == dogfood_status == "pass"
        else "terminal_sink_variance",
    }


def control_blockers_if_comparable(
    *,
    source_statuses: Mapping[str, str],
    blockers: list[str],
) -> list[str]:
    if (
        source_statuses.get("fixture_chain") == "pass"
        and source_statuses.get("dogfood_replay") == "pass"
    ):
        return blockers
    return []


def _row(result: Mapping[str, Any]) -> dict[str, str]:
    return {
        "surface": "terminal_no_send_control_paths",
        "fixture_status": str(result.get("fixture_status") or "missing"),
        "dogfood_status": str(result.get("dogfood_status") or "missing"),
        "live_status": "not_applicable",
        "finding": str(result.get("finding") or "control_path_variance"),
    }


def _blockers(result: Mapping[str, Any]) -> list[str]:
    prefix = "terminal_no_send_control_paths"
    if result.get("fixture_status") == "missing":
        return [f"{prefix}.fixture_control_evidence_missing"]
    if result.get("dogfood_status") == "missing":
        return [f"{prefix}.dogfood_control_evidence_missing"]
    if result.get("fixture_status") != "pass" or result.get("dogfood_status") != "pass":
        return [f"{prefix}.status_not_pass"]
    blockers: list[str] = []
    if result.get("configured_paths_match") is not True:
        blockers.append(f"{prefix}.configured_paths_mismatch")
    if result.get("observed_actions_match") is not True:
        blockers.append(f"{prefix}.observed_actions_mismatch")
    if result.get("next_signal_required_match") is not True:
        blockers.append(f"{prefix}.next_signal_required_mismatch")
    return blockers


def _finding(result: Mapping[str, Any]) -> str:
    if result.get("fixture_status") == "missing" or result.get("dogfood_status") == "missing":
        return "control_path_evidence_missing"
    if not all(result.get(key) is True for key in result if key.endswith("_match")):
        return "control_path_variance"
    return "control_paths_match"


def _field_matches(fixture: Mapping[str, Any], dogfood: Mapping[str, Any], field: str) -> bool:
    return _normalize(fixture.get(field)) == _normalize(dogfood.get(field))


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


def _status(evidence: Mapping[str, Any]) -> str:
    return str(evidence.get("status") or "missing") if evidence else "missing"


def _sink_status(sink: Mapping[str, Any]) -> str:
    return str(sink.get("status") or "missing")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "compare_no_send_control_paths",
    "control_blockers_if_comparable",
    "terminal_sink_row",
]
