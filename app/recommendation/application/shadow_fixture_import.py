from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.recommendation.application.shadow_evaluator import (
    validate_recommendation_shadow_fixture,
)
from app.recommendation.domain.shadow import (
    RecommendationShadowContextFixture,
    RecommendationShadowFixtureImportError,
    RecommendationShadowFixtureImportResult,
    RecommendationShadowFixtureValidationError,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.shadow_fixture_import"
)

REQUIRED_SCENARIO_FIELDS = (
    "scenario_id",
    "user_id",
    "local_date",
    "channel",
    "recorded_at",
    "timezone",
    "current_budget_view",
    "active_body_plan_view",
    "recent_committed_meals_view",
    "open_proposals_view",
    "proactive_status_view",
    "preference_profile_summary",
    "negative_preference_summary",
    "golden_order_summary",
    "candidate_spec",
    "candidate_source_fixture",
)

OPTIONAL_SCENARIO_FIELDS = (
    "recommendation_mode",
    "app_usage_style_candidate",
    "user_language_pattern_candidate",
)

REQUIRED_CANDIDATE_SPEC_FIELDS = (
    "desired_meal_style",
    "acceptable_cuisine_families",
    "excluded_item_patterns",
    "soft_target_kcal_band",
    "venue_posture",
    "swaps_allowed",
    "priority_signals",
    "avoid_repeat_from_today",
    "protein_posture",
    "budget_fit_posture",
)

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_id",
    "title",
    "source_type",
    "store_name",
    "estimated_kcal_range",
    "item_kind",
    "staple_type",
    "protein_posture",
    "cuisine_family",
    "item_patterns",
    "confidence",
    "source_refs",
    "store_metadata",
    "hard_avoid_flags",
)

ALLOWED_BUNDLE_FIELDS = (
    "fixture_bundle_type",
    "scenarios",
)
BUNDLE_TYPE = "recommendation_shadow_context_fixtures"


def load_recommendation_shadow_context_fixtures(
    payload: Any,
) -> RecommendationShadowFixtureImportResult:
    scenario_payloads, input_shape = _scenario_payloads(payload)
    failure_codes = _payload_failure_codes(scenario_payloads)
    if failure_codes:
        raise RecommendationShadowFixtureImportError(failure_codes)

    scenarios: list[RecommendationShadowContextFixture] = []
    validation_failures: list[str] = []
    for index, scenario_payload in enumerate(scenario_payloads):
        scenario_id = str(scenario_payload.get("scenario_id", f"index_{index}"))
        try:
            scenario = RecommendationShadowContextFixture.model_validate(scenario_payload)
            validate_recommendation_shadow_fixture(scenario)
        except ValidationError:
            validation_failures.append(f"scenario:{scenario_id}:model_validation_error")
            continue
        except RecommendationShadowFixtureValidationError as exc:
            validation_failures.extend(
                f"scenario:{scenario_id}:{reason_code}"
                for reason_code in exc.reason_codes
            )
            continue
        scenarios.append(scenario)

    if validation_failures:
        raise RecommendationShadowFixtureImportError(validation_failures)

    return RecommendationShadowFixtureImportResult(
        scenarios=scenarios,
        source_summary={
            "input_shape": input_shape,
            "scenario_count": len(scenarios),
            "scenario_ids": [scenario.scenario_id for scenario in scenarios],
        },
    )


def _scenario_payloads(payload: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(payload, list):
        if not payload:
            raise RecommendationShadowFixtureImportError(["payload:scenarios_empty"])
        if all(isinstance(item, dict) for item in payload):
            return payload, "scenario_list"
        raise RecommendationShadowFixtureImportError(["payload:scenario_list_not_objects"])

    if not isinstance(payload, dict):
        raise RecommendationShadowFixtureImportError(["payload:unsupported_fixture_shape"])

    if "artifact_type" in payload or "evals" in payload:
        raise RecommendationShadowFixtureImportError(["payload:eval_artifact_not_context_fixture"])

    if "scenarios" in payload:
        unexpected_bundle_fields = sorted(set(payload) - set(ALLOWED_BUNDLE_FIELDS))
        if unexpected_bundle_fields:
            raise RecommendationShadowFixtureImportError(
                [
                    f"payload:unexpected_field:{field_name}"
                    for field_name in unexpected_bundle_fields
                ]
            )
        if (
            "fixture_bundle_type" in payload
            and payload["fixture_bundle_type"] != BUNDLE_TYPE
        ):
            raise RecommendationShadowFixtureImportError(
                ["payload:wrong_fixture_bundle_type"]
            )
        scenarios = payload["scenarios"]
        if not isinstance(scenarios, list):
            raise RecommendationShadowFixtureImportError(["payload:scenarios_not_list"])
        if not scenarios:
            raise RecommendationShadowFixtureImportError(["payload:scenarios_empty"])
        if not all(isinstance(item, dict) for item in scenarios):
            raise RecommendationShadowFixtureImportError(["payload:scenarios_not_objects"])
        return scenarios, "scenario_bundle"

    if "scenario_id" in payload:
        return [payload], "single_scenario"

    raise RecommendationShadowFixtureImportError(["payload:unsupported_fixture_shape"])


def _payload_failure_codes(scenario_payloads: list[dict[str, Any]]) -> list[str]:
    failure_codes: list[str] = []
    for index, scenario_payload in enumerate(scenario_payloads):
        scenario_id = str(scenario_payload.get("scenario_id", f"index_{index}"))
        prefix = f"scenario:{scenario_id}"
        allowed_scenario_fields = {
            *REQUIRED_SCENARIO_FIELDS,
            *OPTIONAL_SCENARIO_FIELDS,
        }
        for field_name in sorted(set(scenario_payload) - allowed_scenario_fields):
            failure_codes.append(f"{prefix}:unexpected_field:{field_name}")

        for field_name in REQUIRED_SCENARIO_FIELDS:
            if field_name not in scenario_payload:
                failure_codes.append(f"{prefix}:missing_field:{field_name}")

        candidate_spec = scenario_payload.get("candidate_spec")
        if isinstance(candidate_spec, dict):
            for field_name in REQUIRED_CANDIDATE_SPEC_FIELDS:
                if field_name not in candidate_spec:
                    failure_codes.append(
                        f"{prefix}:candidate_spec:missing_field:{field_name}"
                    )
            for field_name in sorted(
                set(candidate_spec) - set(REQUIRED_CANDIDATE_SPEC_FIELDS)
            ):
                failure_codes.append(
                    f"{prefix}:candidate_spec:unexpected_field:{field_name}"
                )
        elif "candidate_spec" in scenario_payload:
            failure_codes.append(f"{prefix}:candidate_spec_not_object")

        candidates = scenario_payload.get("candidate_source_fixture")
        if not isinstance(candidates, list):
            if "candidate_source_fixture" in scenario_payload:
                failure_codes.append(f"{prefix}:candidate_source_fixture_not_list")
            continue

        for candidate_index, candidate_payload in enumerate(candidates):
            if not isinstance(candidate_payload, dict):
                failure_codes.append(
                    f"{prefix}:candidate_index:{candidate_index}:not_object"
                )
                continue
            for field_name in REQUIRED_CANDIDATE_FIELDS:
                if field_name not in candidate_payload:
                    failure_codes.append(
                        f"{prefix}:candidate_index:{candidate_index}:missing_field:{field_name}"
                    )
            for field_name in sorted(
                set(candidate_payload) - set(REQUIRED_CANDIDATE_FIELDS)
            ):
                failure_codes.append(
                    f"{prefix}:candidate_index:{candidate_index}:unexpected_field:{field_name}"
                )

    return failure_codes


__all__ = [
    "REQUIRED_CANDIDATE_FIELDS",
    "REQUIRED_CANDIDATE_SPEC_FIELDS",
    "REQUIRED_SCENARIO_FIELDS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "BUNDLE_TYPE",
    "RecommendationShadowFixtureImportError",
    "load_recommendation_shadow_context_fixtures",
]
