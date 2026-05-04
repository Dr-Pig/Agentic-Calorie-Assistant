from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.capability_catalog import (
    _candidate_type_to_context_domain,
    _capability_families,
    _consumer_contracts,
)
from app.memory.application.long_term_context_shadow.context_domain_catalog import (
    _context_domain_catalog,
)
from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _product_capability_context_map_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    context_domains = _context_domain_catalog()
    candidate_types = sorted({candidate.candidate_type for candidate in candidates})
    expected_candidate_types = {
        "app_usage_style",
        "conversation_recall_context",
        "food_preference",
        "golden_order",
        "intake_estimation_bias",
        "interaction_preference",
        "logging_adherence_pattern",
        "negative_preference",
        "pattern",
        "temporary_preference",
        "user_language_pattern",
    }
    return _base_artifact(
        artifact_type="product_capability_context_map",
        fixture=fixture,
        extra={
            "runtime_effect_allowed": False,
            "canonical_truth_replaced_by_memory": False,
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md",
                "docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md",
                "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md",
                "docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md",
                "docs/specs/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md",
                "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md",
            ],
            "capability_families": _capability_families(),
            "context_domains": context_domains,
            "consumer_contracts": _consumer_contracts(),
            "candidate_type_to_context_domain": _candidate_type_to_context_domain(),
            "available_candidate_types": candidate_types,
            "coverage_gaps": {
                "fixture_missing_candidate_types": sorted(
                    expected_candidate_types.difference(candidate_types)
                ),
                "runtime_not_integrated_domains": [
                    domain["context_domain_id"] for domain in context_domains
                ],
                "reason": (
                    "Fixture-only shadow lab records product capability pressure "
                    "without claiming durable memory or runtime integration."
                ),
            },
            "llm_deterministic_boundary": {
                "deterministic_role": [
                    "derive L2a statistical patterns",
                    "validate scope keys and non-claim flags",
                    "compile consumer-specific context packs",
                    "reject runtime mutation or injection",
                ],
                "llm_role_later_only": [
                    "extract L2b semantic patterns",
                    "summarize conversation recall candidates",
                    "classify nuanced interaction preference candidates",
                ],
                "human_role": [
                    "accept or reject memory candidates",
                    "confirm durable preference promotion",
                    "approve any future runtime activation",
                ],
                "do_not_override": [
                    "MealThread",
                    "DayBudgetLedger",
                    "BodyPlan",
                    "ProposalContainer",
                    "FoodDB truth",
                    "ManagerContextPacket boundary",
                ],
            },
        },
    )
