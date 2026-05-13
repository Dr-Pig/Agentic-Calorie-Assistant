from __future__ import annotations

from typing import Any, Mapping

_DORMANT_FLAG_NAMES = (
    "mainline_activation_enabled", "mainline_runtime_connected", "served_to_mainline_user",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "durable_product_memory_written",
    "manager_context_packet_changed",
)


def build_recommendation_pair_path_summary(
    label: str,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    tool_loop = _mapping(artifact.get("manager_tool_loop_artifact"))
    tool_results = [
        item for item in tool_loop.get("tool_result_trace") or [] if isinstance(item, Mapping)
    ]
    recommendation = _result_for_tool(tool_results, "recommendation.run")
    return {
        "label": label,
        "status": str(artifact.get("status") or ""),
        "turn_id": str(artifact.get("turn_id") or ""),
        "manager_tool_loop_status": str(tool_loop.get("status") or ""),
        "manager_tool_names": [str(item.get("tool_name") or "") for item in tool_results],
        "manager_tool_loop_source_refs": [
            str(item) for item in artifact.get("manager_tool_loop_source_refs") or []
        ],
        "recommendation_tool_present": bool(recommendation),
        "pending_intake_handoff_created": _pending_handoff_created(recommendation),
        "recommendation_candidate_id": _recommendation_candidate_id(recommendation),
        "recommendation_source_candidate_ids": _source_candidate_ids(recommendation),
        "lab_user_facing_behavior_changed": (
            artifact.get("lab_user_facing_behavior_changed") is True
        ),
        "activation_flags": {
            name: artifact.get(name) is True for name in _DORMANT_FLAG_NAMES
        },
        "blockers": [str(item) for item in artifact.get("blockers") or []],
    }


def build_recommendation_pair_comparison(
    *,
    baseline: Mapping[str, Any],
    recommendation_enabled: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_flags = _mapping(baseline.get("activation_flags"))
    enabled_flags = _mapping(recommendation_enabled.get("activation_flags"))
    return {
        "baseline_non_recommendation_path_valid": (
            baseline.get("status") == "pass"
            and baseline.get("recommendation_tool_present") is False
        ),
        "recommendation_enabled_path_valid": (
            recommendation_enabled.get("status") == "pass"
            and recommendation_enabled.get("recommendation_tool_present") is True
            and recommendation_enabled.get("pending_intake_handoff_created") is True
        ),
        "recommendation_tool_added": (
            baseline.get("recommendation_tool_present") is False
            and recommendation_enabled.get("recommendation_tool_present") is True
        ),
        "pending_intake_handoff_added": (
            baseline.get("pending_intake_handoff_created") is False
            and recommendation_enabled.get("pending_intake_handoff_created") is True
        ),
        "recommendation_candidate_id": str(
            recommendation_enabled.get("recommendation_candidate_id") or ""
        ),
        "lab_response_changed_by_recommendation_path": (
            list(baseline.get("manager_tool_names") or [])
            != list(recommendation_enabled.get("manager_tool_names") or [])
        ),
        "canonical_mutation_changed": _flag_enabled(
            baseline_flags,
            enabled_flags,
            "canonical_product_mutation_allowed",
        ),
        "mainline_activation_changed": _flag_enabled(
            baseline_flags,
            enabled_flags,
            "mainline_activation_enabled",
        ),
        "manager_context_packet_changed": _flag_enabled(
            baseline_flags,
            enabled_flags,
            "manager_context_packet_changed",
        ),
    }


def recommendation_pair_blockers(
    *,
    baseline: Mapping[str, Any],
    recommendation_enabled: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> list[str]:
    return [
        *_path_blockers("baseline", baseline, require_no_recommendation=True),
        *_path_blockers(
            "recommendation_enabled",
            recommendation_enabled,
            require_recommendation=True,
        ),
        *_comparison_blockers(comparison),
    ]


def any_pair_flag_true(
    baseline: Mapping[str, Any],
    recommendation_enabled: Mapping[str, Any],
    flag_name: str,
) -> bool:
    return (
        _mapping(baseline.get("activation_flags")).get(flag_name) is True
        or _mapping(recommendation_enabled.get("activation_flags")).get(flag_name) is True
    )


def _path_blockers(
    prefix: str,
    path: Mapping[str, Any],
    *,
    require_no_recommendation: bool = False,
    require_recommendation: bool = False,
) -> list[str]:
    blockers = [f"{prefix}.{item}" for item in path.get("blockers") or []]
    if path.get("status") != "pass":
        blockers.append(f"{prefix}.status_not_pass")
    if require_no_recommendation and path.get("recommendation_tool_present") is True:
        blockers.append(f"{prefix}.recommendation_tool_present")
    if require_recommendation and path.get("recommendation_tool_present") is not True:
        blockers.append(f"{prefix}.recommendation_tool_missing")
    if require_recommendation and path.get("pending_intake_handoff_created") is not True:
        blockers.append(f"{prefix}.pending_intake_handoff_missing")
    blockers.extend(
        f"{prefix}.activation_flag_true:{name}"
        for name, enabled in _mapping(path.get("activation_flags")).items()
        if enabled is True
    )
    return blockers


def _comparison_blockers(comparison: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if comparison.get("recommendation_tool_added") is not True:
        blockers.append("comparison.recommendation_tool_not_added")
    if comparison.get("pending_intake_handoff_added") is not True:
        blockers.append("comparison.pending_intake_handoff_not_added")
    for field in (
        "canonical_mutation_changed",
        "mainline_activation_changed",
        "manager_context_packet_changed",
    ):
        if comparison.get(field) is True:
            blockers.append(f"comparison.{field}")
    return blockers


def _result_for_tool(
    tool_results: list[Mapping[str, Any]],
    tool_name: str,
) -> Mapping[str, Any]:
    for result in tool_results:
        if str(result.get("tool_name") or "") == tool_name:
            return _mapping(result.get("result_artifact"))
    return {}


def _pending_handoff_created(recommendation: Mapping[str, Any]) -> bool:
    return bool(recommendation) and recommendation.get("pending_intake_handoff_created") is True


def _recommendation_candidate_id(recommendation: Mapping[str, Any]) -> str:
    handoff = _mapping(recommendation.get("pending_intake_handoff_packet"))
    selected = _mapping(_mapping(recommendation.get("offer_synthesis")).get("selected_primary"))
    return str(handoff.get("candidate_id") or selected.get("candidate_id") or "")


def _source_candidate_ids(recommendation: Mapping[str, Any]) -> list[str]:
    retrieval = _mapping(recommendation.get("retrieval_guard_scoring"))
    return [str(item) for item in retrieval.get("source_candidate_ids") or []]


def _flag_enabled(
    baseline_flags: Mapping[str, Any],
    enabled_flags: Mapping[str, Any],
    flag_name: str,
) -> bool:
    return baseline_flags.get(flag_name) is True or enabled_flags.get(flag_name) is True


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
