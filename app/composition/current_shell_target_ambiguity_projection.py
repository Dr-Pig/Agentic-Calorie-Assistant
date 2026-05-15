from __future__ import annotations

from typing import Any


def attach_target_ambiguity_validation(
    runtime: dict[str, Any],
    request_trace: dict[str, Any],
    manager_final: dict[str, Any],
) -> None:
    for validation in manager_target_proposal_validations(request_trace, manager_final):
        if validation.get("failure_family") != "manager_thread_target_proposal_ambiguous":
            continue
        if "target_candidates_supplied" not in runtime and validation.get("target_candidates_supplied") is not None:
            runtime["target_candidates_supplied"] = bool(validation.get("target_candidates_supplied"))
        if (
            "deterministic_target_choice_allowed" not in runtime
            and validation.get("deterministic_target_choice_allowed") is not None
        ):
            runtime["deterministic_target_choice_allowed"] = bool(
                validation.get("deterministic_target_choice_allowed")
            )
        return


def manager_target_proposal_validations(
    request_trace: dict[str, Any],
    manager_final: dict[str, Any],
) -> list[dict[str, Any]]:
    validations: list[dict[str, Any]] = []
    for source in _tool_result_sources(request_trace, manager_final):
        for item in _list(source):
            if not isinstance(item, dict):
                continue
            validation = _dict(_dict(_dict(item.get("provenance")).get("correction_target")).get(
                "manager_target_proposal_validation"
            ))
            if validation:
                validations.append(validation)
    return validations


def _tool_result_sources(
    request_trace: dict[str, Any],
    manager_final: dict[str, Any],
) -> tuple[list[Any], list[Any]]:
    return (
        _list(_dict(request_trace.get("tool_outputs")).get("tool_results")),
        _list(manager_final.get("tool_results")),
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
