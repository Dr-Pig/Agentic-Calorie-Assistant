from __future__ import annotations

from typing import Any


_EXPECTED_DIAGNOSTIC_ARTIFACT_TYPE = "accurate_intake_grokfast_websearch_packet_smoke"


def build_websearch_probe_cases_from_diagnostic_artifact(
    diagnostic_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    if (
        str(diagnostic_artifact.get("artifact_type") or "")
        != _EXPECTED_DIAGNOSTIC_ARTIFACT_TYPE
    ):
        raise ValueError("unsupported_websearch_contract_probe_diagnostic_artifact")

    probe_cases: list[dict[str, Any]] = []
    for index, case in enumerate(diagnostic_artifact.get("cases") or [], start=1):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or case.get("packet_id") or f"case_{index:03d}").strip()
        if not case_id:
            case_id = f"case_{index:03d}"
        probe_cases.append(
            {
                "case_id": case_id,
                "source": "grokfast_websearch_live_diagnostic_artifact",
                "expected_failure_family": _expected_failure_family(case),
                "observed_manager_output": dict(case.get("manager_output") or {}),
                "manager_contract_validation_errors": _string_list(
                    case.get("manager_contract_validation_errors")
                ),
            }
        )
    return probe_cases


def _expected_failure_family(case: dict[str, Any]) -> str | None:
    failure_families = _string_list(case.get("failure_families"))
    if "manager_output_contract_violation" in failure_families:
        return "manager_output_contract_violation"
    if failure_families:
        return failure_families[0]
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


__all__ = ["build_websearch_probe_cases_from_diagnostic_artifact"]
