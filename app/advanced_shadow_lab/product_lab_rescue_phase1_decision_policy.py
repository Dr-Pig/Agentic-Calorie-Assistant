from __future__ import annotations

from typing import Any, Mapping


DIAGNOSTIC_TYPES = {
    "grokfast_rescue_proposal_shaping_diagnostic": (
        "rescue_proposal_shaping_provider_diagnostic"
    ),
    "grokfast_rescue_response_presentation_diagnostic": (
        "rescue_response_presentation_provider_diagnostic"
    ),
}
CLAIM_FALSE_FIELDS = (
    "mainline_activation_enabled",
    "production_scheduler_delivery_allowed",
    "canonical_product_mutation_allowed",
    "durable_product_memory_written",
)


def milestone_statuses(
    *,
    golden_set: Mapping[str, Any],
    replay_artifacts: list[Mapping[str, Any]],
    live_diagnostic_artifacts: list[Mapping[str, Any]],
    journey_statuses: Mapping[str, str],
    accept_dismiss: Mapping[str, Any],
) -> dict[str, str]:
    statuses = {
        "fixture_golden_set_replay": golden_status(golden_set),
        "simulated_self_use_trace_replay": replay_kind_status(
            replay_artifacts, "simulated_self_use"
        ),
        "lab_accept_dismiss_e2e": (
            "satisfied_fixture"
            if accept_dismiss.get("accept_seen") and accept_dismiss.get("dismiss_seen")
            else "missing"
        ),
        "integrated_f_f2_t_e2e_decision_pack": (
            "satisfied_integrated_e2e"
            if all(journey_statuses.get(journey) == "pass" for journey in ("F", "F2", "T"))
            else "missing"
        ),
    }
    for milestone_id, artifact_type in DIAGNOSTIC_TYPES.items():
        statuses[milestone_id] = live_status(live_diagnostic_artifacts, artifact_type)
    return statuses


def journey_statuses(replay_artifacts: list[Mapping[str, Any]]) -> dict[str, str]:
    return {
        journey: (
            "pass"
            if any(case_passed(case, journey_id=journey) for case in replay_artifacts)
            else "missing"
        )
        for journey in ("F", "F2", "T")
    }


def case_passed(case: Mapping[str, Any], *, journey_id: str) -> bool:
    return (
        case.get("journey_id") == journey_id
        and mapping(case.get("session_artifact")).get("status") == "pass"
    )


def accept_dismiss_summary(replay_artifacts: list[Mapping[str, Any]]) -> dict[str, Any]:
    sessions = [mapping(case.get("session_artifact")) for case in replay_artifacts]
    accept_seen = any(
        "rescue_commit_confirmation" in strings(session, "lab_chat_action_outcome_types")
        or "accepted_pending_commit_confirmation"
        in strings(session, "lab_rescue_history_statuses")
        for session in sessions
    )
    dismiss_seen = any(
        "dismiss_current_proposal_instance"
        in strings(session, "lab_rescue_action_decision_kinds")
        or "dismissed" in strings(session, "lab_rescue_history_statuses")
        for session in sessions
    )
    return {
        "accept_seen": accept_seen,
        "dismiss_seen": dismiss_seen,
        "canonical_product_mutation_allowed": False,
    }


def golden_status(golden_set: Mapping[str, Any]) -> str:
    required = {"F", "F2", "T", "N-3"}
    contract = mapping(golden_set.get("suite_contract"))
    observed = {str(item) for item in contract.get("required_journeys") or []}
    if golden_set.get("status") and required.issubset(observed):
        return "satisfied_fixture"
    return "missing"


def replay_kind_status(
    replay_artifacts: list[Mapping[str, Any]],
    replay_kind: str,
) -> str:
    if any(
        case.get("replay_kind") == replay_kind
        and mapping(case.get("session_artifact")).get("status") == "pass"
        for case in replay_artifacts
    ):
        return "satisfied_fixture"
    return "missing"


def live_status(artifacts: list[Mapping[str, Any]], artifact_type: str) -> str:
    for artifact in artifacts:
        if artifact.get("artifact_type") != artifact_type:
            continue
        if (
            artifact.get("status") == "pass"
            and artifact.get("live_llm_invoked") is True
            and artifact.get("live_provider_used") is True
            and "grok" in str(artifact.get("provider_mode") or "").lower()
        ):
            return "satisfied_live_grokfast"
        return "blocked"
    return "missing"


def milestone_blockers(statuses: Mapping[str, str]) -> list[str]:
    return [
        f"milestone.{milestone_id}.missing"
        for milestone_id, status in statuses.items()
        if not status.startswith("satisfied_")
    ]


def pr_train_blockers(pr_train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pr_train.get("artifact_type") != "advanced_product_lab_rescue_phase1_pr_train":
        blockers.append("pr_train.artifact_type_mismatch")
    if int(pr_train.get("planned_pr_count") or 0) != 24:
        blockers.append("pr_train.planned_pr_count_not_24")
    return blockers


def golden_set_blockers(golden_set: Mapping[str, Any]) -> list[str]:
    if golden_set.get("artifact_type") == "advanced_product_lab_rescue_phase1_golden_set":
        return []
    return ["golden_set.artifact_type_mismatch"]


def claim_drift_blockers(
    replay_artifacts: list[Mapping[str, Any]],
    live_artifacts: list[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    sources = [*sessions(replay_artifacts), *live_artifacts]
    for index, source in enumerate(sources, start=1):
        for field in CLAIM_FALSE_FIELDS:
            if source.get(field) is True:
                blockers.append(f"source:{index}.{field}.claim_drift")
    return blockers


def sessions(replay_artifacts: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [mapping(case.get("session_artifact")) for case in replay_artifacts]


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def strings(source: Mapping[str, Any], key: str) -> set[str]:
    return {str(item) for item in source.get(key) or []}


__all__ = [
    "accept_dismiss_summary",
    "claim_drift_blockers",
    "golden_set_blockers",
    "journey_statuses",
    "milestone_blockers",
    "milestone_statuses",
    "pr_train_blockers",
]
