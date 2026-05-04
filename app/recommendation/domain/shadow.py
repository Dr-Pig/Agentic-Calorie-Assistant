from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, StrictInt

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("recommendation.domain.shadow")

RecommendationMode = Literal[
    "general",
    "menu_scan",
    "swap_suggestion",
    "pre_meal_planning",
]


class RecommendationShadowFlags(BaseModel):
    shadow_mode: Literal[True] = True
    real_runtime_effect: Literal[False] = False
    recommendation_served: Literal[False] = False
    intake_committed: Literal[False] = False
    meal_thread_mutated: Literal[False] = False
    day_budget_mutated: Literal[False] = False
    body_plan_mutated: Literal[False] = False
    durable_memory_written: Literal[False] = False
    manager_context_injected: Literal[False] = False
    live_provider_used: Literal[False] = False
    product_readiness_claimed: Literal[False] = False
    private_self_use_approved: Literal[False] = False


class RecommendationShadowFixtureValidationError(ValueError):
    def __init__(self, reason_codes: list[str]) -> None:
        self.reason_codes = reason_codes
        super().__init__(", ".join(reason_codes))


class CandidateSpec(BaseModel):
    desired_meal_style: str = "any"
    acceptable_cuisine_families: list[str] = Field(default_factory=lambda: ["any"])
    excluded_item_patterns: list[str] = Field(default_factory=list)
    soft_target_kcal_band: dict[str, int] = Field(
        default_factory=lambda: {"min": 250, "max": 700}
    )
    venue_posture: str = "any"
    swaps_allowed: bool = False
    priority_signals: list[str] = Field(default_factory=list)
    avoid_repeat_from_today: bool = True
    protein_posture: str = "any"
    budget_fit_posture: str = "normal"


class RecommendationCandidateFixture(BaseModel):
    candidate_id: str
    title: str
    source_type: str = "safe_fallback"
    store_name: str | None = None
    estimated_kcal_range: dict[str, StrictInt] = Field(
        default_factory=lambda: {"min": 0, "max": 0}
    )
    item_kind: str = "meal"
    staple_type: str | None = None
    protein_posture: str = "medium"
    cuisine_family: str = "generic"
    item_patterns: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    source_refs: list[str] = Field(default_factory=list)
    store_metadata: dict[str, Any] = Field(default_factory=dict)
    hard_avoid_flags: list[str] = Field(default_factory=list)


class RecommendationShadowContextFixture(BaseModel):
    scenario_id: str
    recommendation_mode: RecommendationMode = "general"
    user_id: str
    local_date: str
    channel: str
    recorded_at: str
    timezone: str
    current_budget_view: dict[str, Any]
    active_body_plan_view: dict[str, Any]
    recent_committed_meals_view: dict[str, Any]
    open_proposals_view: dict[str, Any]
    proactive_status_view: dict[str, Any]
    preference_profile_summary: dict[str, Any] = Field(default_factory=dict)
    negative_preference_summary: dict[str, Any] = Field(default_factory=dict)
    golden_order_summary: dict[str, Any] = Field(default_factory=dict)
    app_usage_style_candidate: dict[str, Any] = Field(default_factory=dict)
    user_language_pattern_candidate: dict[str, Any] = Field(default_factory=dict)
    candidate_spec: CandidateSpec = Field(default_factory=CandidateSpec)
    candidate_source_fixture: list[RecommendationCandidateFixture] = Field(default_factory=list)


class CandidateSourceSummary(BaseModel):
    candidate_count: int = 0
    source_counts: dict[str, int] = Field(default_factory=dict)
    coverage_gaps: list[str] = Field(default_factory=list)


class FilteredRecommendationCandidate(BaseModel):
    candidate_id: str
    title: str
    reason_codes: list[str] = Field(default_factory=list)


class RankedRecommendationCandidate(BaseModel):
    candidate_id: str
    title: str
    rank: int
    score: float
    source_type: str
    estimated_kcal_range: dict[str, int]
    store_name: str | None = None
    ranking_reasons: list[str] = Field(default_factory=list)


class RecommendationHintPacket(BaseModel):
    candidate_id: str
    title: str
    store_metadata: dict[str, Any] = Field(default_factory=dict)
    source_type: str
    estimated_kcal_range: dict[str, int]
    current_surface_channel: str
    selection_context: dict[str, Any] = Field(default_factory=dict)
    ranking_reason_summary: str
    confidence: float
    source_refs: list[str] = Field(default_factory=list)
    is_canonical_truth: Literal[False] = False


class RecommendationShadowEvalResult(BaseModel):
    scenario_id: str
    recommendation_mode: RecommendationMode = "general"
    input_context_summary: dict[str, Any]
    candidate_spec: CandidateSpec
    candidate_source_summary: CandidateSourceSummary
    candidate_items: list[RecommendationCandidateFixture] = Field(default_factory=list)
    filtered_candidates: list[FilteredRecommendationCandidate] = Field(default_factory=list)
    ranked_candidates: list[RankedRecommendationCandidate] = Field(default_factory=list)
    top_pick: RankedRecommendationCandidate | None = None
    backup_picks: list[RankedRecommendationCandidate] = Field(default_factory=list)
    ranking_basis: dict[str, Any] = Field(default_factory=dict)
    hint_packet: RecommendationHintPacket | None = None
    memory_candidates_used: list[str] = Field(default_factory=list)
    memory_candidates_ignored: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    cold_start_used: bool = False
    coverage_gaps: list[str] = Field(default_factory=list)
    risk_if_wrong: str = "low"
    expected_user_value: str = "shadow_candidate_quality_signal"
    confidence: float = 0.0
    freshness_notes: list[str] = Field(default_factory=list)
    presentation_policy: str = "standard"
    mode_notes: list[str] = Field(default_factory=list)
    fixture_governance: dict[str, Any] = Field(default_factory=dict)
    runtime_effect_allowed: Literal[False] = False
    shadow_mode: Literal[True] = True
    recommendation_served: Literal[False] = False
    intake_committed: Literal[False] = False
    flags: RecommendationShadowFlags = Field(default_factory=RecommendationShadowFlags)


class RecommendationShadowEvalArtifact(BaseModel):
    artifact_type: Literal["recommendation_shadow_eval"] = "recommendation_shadow_eval"
    shadow_mode: Literal[True] = True
    real_runtime_effect: Literal[False] = False
    recommendation_served: Literal[False] = False
    intake_committed: Literal[False] = False
    meal_thread_mutated: Literal[False] = False
    day_budget_mutated: Literal[False] = False
    body_plan_mutated: Literal[False] = False
    durable_memory_written: Literal[False] = False
    manager_context_injected: Literal[False] = False
    live_provider_used: Literal[False] = False
    product_readiness_claimed: Literal[False] = False
    private_self_use_approved: Literal[False] = False
    track_status: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    integrity: dict[str, Any] = Field(default_factory=dict)
    evals: list[RecommendationShadowEvalResult] = Field(default_factory=list)


class RecommendationShadowArtifactGateResult(BaseModel):
    passed: bool
    failure_codes: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    scenario_reports: list[dict[str, Any]] = Field(default_factory=list)


class RecommendationShadowFixtureImportResult(BaseModel):
    scenarios: list[RecommendationShadowContextFixture] = Field(default_factory=list)
    source_summary: dict[str, Any] = Field(default_factory=dict)


class RecommendationShadowFixtureImportError(ValueError):
    def __init__(self, failure_codes: list[str]) -> None:
        self.failure_codes = failure_codes
        super().__init__(", ".join(failure_codes))


__all__ = [
    "CandidateSourceSummary",
    "CandidateSpec",
    "FilteredRecommendationCandidate",
    "RankedRecommendationCandidate",
    "RecommendationCandidateFixture",
    "RecommendationHintPacket",
    "RecommendationShadowArtifactGateResult",
    "RecommendationShadowContextFixture",
    "RecommendationShadowEvalArtifact",
    "RecommendationShadowEvalResult",
    "RecommendationShadowFixtureValidationError",
    "RecommendationShadowFixtureImportError",
    "RecommendationShadowFixtureImportResult",
    "RecommendationShadowFlags",
    "SIDECAR_ACTIVATION_CONTRACT",
]
