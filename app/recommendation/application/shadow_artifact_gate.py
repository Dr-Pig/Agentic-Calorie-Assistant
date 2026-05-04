from __future__ import annotations

from collections import Counter
from typing import Any

from app.recommendation.domain.shadow import (
    RecommendationShadowArtifactGateResult,
    RecommendationShadowEvalArtifact,
    RecommendationShadowEvalResult,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.shadow_artifact_gate"
)

REQUIRED_SCENARIO_IDS = {
    "cold_start_lunch",
    "known_negative_preference",
    "golden_order_lunch",
    "avoid_repeat_dinner",
    "budget_tight",
    "app_usage_style_concise",
    "menu_scan_fixture",
    "swap_suggestion_fixture",
}

REQUIRED_MODE_MIN_COUNTS = {
    "general": 6,
    "menu_scan": 1,
    "swap_suggestion": 1,
}

TOP_LEVEL_FALSE_FLAGS = (
    "real_runtime_effect",
    "recommendation_served",
    "intake_committed",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "live_provider_used",
    "product_readiness_claimed",
    "private_self_use_approved",
)

EVAL_FALSE_FLAGS = (
    "runtime_effect_allowed",
    "recommendation_served",
    "intake_committed",
)


def evaluate_recommendation_shadow_artifact_payload(
    payload: dict[str, Any],
) -> RecommendationShadowArtifactGateResult:
    payload_failures = _payload_failure_codes(payload)
    try:
        artifact = RecommendationShadowEvalArtifact.model_validate(payload)
    except ValueError as exc:
        failure_codes = _dedupe([*payload_failures, "payload:model_validation_error"])
        return RecommendationShadowArtifactGateResult(
            passed=False,
            failure_codes=failure_codes,
            summary={
                "failure_count": len(failure_codes),
                "model_validation_error": str(exc),
            },
        )

    gate_result = evaluate_recommendation_shadow_artifact_quality(artifact)
    failure_codes = _dedupe([*payload_failures, *gate_result.failure_codes])
    summary = {
        **gate_result.summary,
        "payload_failure_count": len(payload_failures),
        "failure_count": len(failure_codes),
    }
    return RecommendationShadowArtifactGateResult(
        passed=not failure_codes,
        failure_codes=failure_codes,
        warning_codes=gate_result.warning_codes,
        summary=summary,
        scenario_reports=gate_result.scenario_reports,
    )


def evaluate_recommendation_shadow_artifact_quality(
    artifact: RecommendationShadowEvalArtifact,
) -> RecommendationShadowArtifactGateResult:
    failure_codes: list[str] = []
    warning_codes: list[str] = []
    scenario_reports: list[dict[str, Any]] = []

    if artifact.artifact_type != "recommendation_shadow_eval":
        failure_codes.append("artifact:wrong_artifact_type")
    if artifact.shadow_mode is not True:
        failure_codes.append("artifact:shadow_mode_not_true")

    for flag_name in TOP_LEVEL_FALSE_FLAGS:
        if getattr(artifact, flag_name) is not False:
            failure_codes.append(f"artifact:{flag_name}_true")

    _extend_track_status_failures(artifact.track_status, failure_codes)
    _extend_integrity_failures(artifact.integrity, failure_codes)
    _extend_coverage_failures(artifact, failure_codes)

    for eval_item in artifact.evals:
        scenario_failures, scenario_warnings = _evaluate_scenario(eval_item)
        failure_codes.extend(scenario_failures)
        warning_codes.extend(scenario_warnings)
        scenario_reports.append(
            {
                "scenario_id": eval_item.scenario_id,
                "recommendation_mode": eval_item.recommendation_mode,
                "passed": not scenario_failures,
                "failure_codes": scenario_failures,
                "warning_codes": scenario_warnings,
                "candidate_count": len(eval_item.candidate_items),
                "filtered_count": len(eval_item.filtered_candidates),
                "ranked_count": len(eval_item.ranked_candidates),
                "top_pick_candidate_id": (
                    eval_item.top_pick.candidate_id if eval_item.top_pick else None
                ),
            }
        )

    summary = _summary(artifact, failure_codes, scenario_reports)
    return RecommendationShadowArtifactGateResult(
        passed=not failure_codes,
        failure_codes=failure_codes,
        warning_codes=warning_codes,
        summary=summary,
        scenario_reports=scenario_reports,
    )


def _payload_failure_codes(payload: dict[str, Any]) -> list[str]:
    failure_codes: list[str] = []
    if not isinstance(payload, dict):
        return ["payload:not_object"]

    for field_name in (
        "artifact_type",
        "shadow_mode",
        "track_status",
        "summary",
        "integrity",
        "evals",
        *TOP_LEVEL_FALSE_FLAGS,
    ):
        if field_name not in payload:
            failure_codes.append(f"artifact:missing_field:{field_name}")

    if payload.get("shadow_mode") is not True:
        failure_codes.append("artifact:shadow_mode_not_true")
    for flag_name in TOP_LEVEL_FALSE_FLAGS:
        if flag_name in payload and payload.get(flag_name) is not False:
            failure_codes.append(f"artifact:{flag_name}_true")

    track_status = payload.get("track_status")
    if isinstance(track_status, dict):
        if track_status.get("track") != "RecommendationShadow":
            failure_codes.append("track_status:wrong_track")
        for field_name in (
            "track",
            "slice_id",
            "shadow_mode",
            "recommendation_served",
            "intake_committed",
            "meal_thread_mutated",
            "day_budget_mutated",
            "body_plan_mutated",
            "durable_memory_written",
            "manager_context_injected",
            "live_provider_used",
        ):
            if field_name not in track_status:
                failure_codes.append(f"track_status:missing_field:{field_name}")
        for flag_name in (
            "shadow_mode",
            "recommendation_served",
            "intake_committed",
            "meal_thread_mutated",
            "day_budget_mutated",
            "body_plan_mutated",
            "durable_memory_written",
            "manager_context_injected",
            "live_provider_used",
        ):
            expected = True if flag_name == "shadow_mode" else False
            if flag_name in track_status and track_status.get(flag_name) is not expected:
                failure_codes.append(f"track_status:{flag_name}_unexpected")

    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        for field_name in (
            "validation_status",
            "invalid_scenario_count",
            "runtime_effect_allowed_count",
            "canonical_hint_packet_count",
        ):
            if field_name not in integrity:
                failure_codes.append(f"integrity:missing_field:{field_name}")
        if integrity.get("validation_status") != "pass":
            failure_codes.append("integrity:validation_status_not_pass")
        for count_name in (
            "invalid_scenario_count",
            "runtime_effect_allowed_count",
            "canonical_hint_packet_count",
        ):
            if count_name in integrity and integrity.get(count_name) != 0:
                failure_codes.append(f"integrity:{count_name}_nonzero")

    evals = payload.get("evals")
    if isinstance(evals, list):
        for index, eval_payload in enumerate(evals):
            if not isinstance(eval_payload, dict):
                failure_codes.append(f"eval_index:{index}:not_object")
                continue
            failure_codes.extend(_eval_payload_presence_failure_codes(eval_payload, index))
    return failure_codes


def _eval_payload_presence_failure_codes(
    eval_payload: dict[str, Any],
    index: int,
) -> list[str]:
    failure_codes: list[str] = []
    scenario_id = str(eval_payload.get("scenario_id", f"index_{index}"))
    prefix = f"eval:{scenario_id}"
    for field_name in (
        "scenario_id",
        "recommendation_mode",
        "input_context_summary",
        "candidate_spec",
        "candidate_source_summary",
        "candidate_items",
        "filtered_candidates",
        "ranked_candidates",
        "top_pick",
        "backup_picks",
        "ranking_basis",
        "hint_packet",
        "memory_candidates_used",
        "memory_candidates_ignored",
        "hard_constraints",
        "soft_preferences",
        "cold_start_used",
        "coverage_gaps",
        "risk_if_wrong",
        "expected_user_value",
        "confidence",
        "freshness_notes",
        "presentation_policy",
        "mode_notes",
        "fixture_governance",
        "runtime_effect_allowed",
        "shadow_mode",
        "recommendation_served",
        "intake_committed",
        "flags",
    ):
        if field_name not in eval_payload:
            failure_codes.append(f"{prefix}:missing_field:{field_name}")

    flags = eval_payload.get("flags")
    if isinstance(flags, dict):
        for field_name in (
            "shadow_mode",
            *TOP_LEVEL_FALSE_FLAGS,
        ):
            if field_name not in flags:
                failure_codes.append(f"{prefix}:flags_missing_field:{field_name}")
        if flags.get("shadow_mode") is not True:
            failure_codes.append(f"{prefix}:flags_shadow_mode_not_true")
        for field_name in TOP_LEVEL_FALSE_FLAGS:
            if field_name in flags and flags.get(field_name) is not False:
                failure_codes.append(f"{prefix}:flags_{field_name}_true")

    hint_packet = eval_payload.get("hint_packet")
    if isinstance(hint_packet, dict):
        for field_name in (
            "candidate_id",
            "title",
            "store_metadata",
            "source_type",
            "estimated_kcal_range",
            "current_surface_channel",
            "selection_context",
            "ranking_reason_summary",
            "confidence",
            "source_refs",
            "is_canonical_truth",
        ):
            if field_name not in hint_packet:
                failure_codes.append(
                    f"{prefix}:hint_packet_missing_field:{field_name}"
                )
        if (
            "is_canonical_truth" in hint_packet
            and hint_packet.get("is_canonical_truth") is not False
        ):
            failure_codes.append(f"{prefix}:canonical_hint_packet")

    if eval_payload.get("shadow_mode") is not True:
        failure_codes.append(f"{prefix}:shadow_mode_not_true")
    for field_name in EVAL_FALSE_FLAGS:
        if field_name in eval_payload and eval_payload.get(field_name) is not False:
            failure_codes.append(f"{prefix}:{field_name}_true")
    return failure_codes


def _extend_track_status_failures(
    track_status: dict[str, Any], failure_codes: list[str]
) -> None:
    if track_status.get("track") != "RecommendationShadow":
        failure_codes.append("track_status:wrong_track")
    for flag_name in (
        "shadow_mode",
        "recommendation_served",
        "intake_committed",
        "meal_thread_mutated",
        "day_budget_mutated",
        "body_plan_mutated",
        "durable_memory_written",
        "manager_context_injected",
        "live_provider_used",
    ):
        expected = True if flag_name == "shadow_mode" else False
        if track_status.get(flag_name) is not expected:
            failure_codes.append(f"track_status:{flag_name}_unexpected")


def _extend_integrity_failures(
    integrity: dict[str, Any], failure_codes: list[str]
) -> None:
    if integrity.get("validation_status") != "pass":
        failure_codes.append("integrity:validation_status_not_pass")
    for count_name in (
        "invalid_scenario_count",
        "runtime_effect_allowed_count",
        "canonical_hint_packet_count",
    ):
        if integrity.get(count_name) != 0:
            failure_codes.append(f"integrity:{count_name}_nonzero")


def _extend_coverage_failures(
    artifact: RecommendationShadowEvalArtifact, failure_codes: list[str]
) -> None:
    scenario_ids = {eval_item.scenario_id for eval_item in artifact.evals}
    for scenario_id in sorted(REQUIRED_SCENARIO_IDS - scenario_ids):
        failure_codes.append(f"artifact:missing_required_scenario:{scenario_id}")

    mode_counts = Counter(eval_item.recommendation_mode for eval_item in artifact.evals)
    for mode, minimum_count in REQUIRED_MODE_MIN_COUNTS.items():
        if mode_counts.get(mode, 0) < minimum_count:
            failure_codes.append(f"artifact:missing_required_mode:{mode}")


def _evaluate_scenario(
    eval_item: RecommendationShadowEvalResult,
) -> tuple[list[str], list[str]]:
    failure_codes: list[str] = []
    warning_codes: list[str] = []
    prefix = f"eval:{eval_item.scenario_id}"

    if eval_item.shadow_mode is not True:
        failure_codes.append(f"{prefix}:shadow_mode_not_true")

    for flag_name in EVAL_FALSE_FLAGS:
        if getattr(eval_item, flag_name) is not False:
            failure_codes.append(f"{prefix}:{flag_name}_true")

    if eval_item.flags.shadow_mode is not True:
        failure_codes.append(f"{prefix}:flags_shadow_mode_not_true")
    for flag_name in TOP_LEVEL_FALSE_FLAGS:
        if getattr(eval_item.flags, flag_name) is not False:
            failure_codes.append(f"{prefix}:flags_{flag_name}_true")

    if not eval_item.candidate_items:
        failure_codes.append(f"{prefix}:no_candidate_items")
    if not eval_item.ranked_candidates:
        failure_codes.append(f"{prefix}:no_ranked_candidates")
    if eval_item.top_pick is None:
        failure_codes.append(f"{prefix}:missing_top_pick")
    if eval_item.hint_packet is None:
        failure_codes.append(f"{prefix}:missing_hint_packet")
    elif eval_item.hint_packet.is_canonical_truth is not False:
        failure_codes.append(f"{prefix}:canonical_hint_packet")

    if (
        eval_item.candidate_source_summary.candidate_count
        != len(eval_item.candidate_items)
    ):
        failure_codes.append(f"{prefix}:candidate_count_mismatch")

    if (
        eval_item.top_pick is not None
        and eval_item.ranked_candidates
        and eval_item.top_pick.candidate_id != eval_item.ranked_candidates[0].candidate_id
    ):
        failure_codes.append(f"{prefix}:top_pick_not_first_ranked_candidate")

    if eval_item.fixture_governance.get("validation_status") != "pass":
        failure_codes.append(f"{prefix}:fixture_governance_not_pass")

    if "all_candidates_filtered" in eval_item.coverage_gaps:
        failure_codes.append(f"{prefix}:all_candidates_filtered")
    elif eval_item.coverage_gaps:
        warning_codes.extend(
            f"{prefix}:coverage_gap:{gap}" for gap in eval_item.coverage_gaps
        )

    return failure_codes, warning_codes


def _summary(
    artifact: RecommendationShadowEvalArtifact,
    failure_codes: list[str],
    scenario_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    scenario_ids = {eval_item.scenario_id for eval_item in artifact.evals}
    mode_counts = Counter(eval_item.recommendation_mode for eval_item in artifact.evals)
    return {
        "scenario_count": len(artifact.evals),
        "mode_counts": dict(sorted(mode_counts.items())),
        "required_scenario_ids": sorted(REQUIRED_SCENARIO_IDS),
        "missing_required_scenario_ids": sorted(REQUIRED_SCENARIO_IDS - scenario_ids),
        "required_mode_min_counts": REQUIRED_MODE_MIN_COUNTS,
        "failed_scenario_count": sum(
            1 for report in scenario_reports if not report["passed"]
        ),
        "failure_count": len(failure_codes),
    }


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "REQUIRED_MODE_MIN_COUNTS",
    "REQUIRED_SCENARIO_IDS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "evaluate_recommendation_shadow_artifact_payload",
    "evaluate_recommendation_shadow_artifact_quality",
]
