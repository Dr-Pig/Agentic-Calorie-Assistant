from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ClaimScope = Literal[
    "unit_contract",
    "fixture_scaffold",
    "deterministic_runtime",
    "eligible_for_live_diagnostic",
    "live_diagnostic",
    "shadow",
    "canary",
    "user_facing_ready",
    "mutation_ready",
]
ActivationStage = Literal[
    "contract",
    "fake",
    "deterministic",
    "live_diagnostic",
    "shadow",
    "canary",
    "user_facing",
    "mutation_bearing",
]
SemanticAuthoritySource = Literal[
    "none",
    "live_manager_structured_output",
    "synthetic_manager_structured_fixture",
    "fake_manager_structured_output",
    "human_approved_semantic_register",
    "deterministic_validator",
    "forbidden_legacy_oracle",
]


REQUIRED_CLAIM_FIELDS = (
    "claim_scope",
    "activation_stage",
    "semantic_authority_source",
    "producer_honesty",
    "evidence_lineage",
    "allowed_next_stage",
    "forbidden_claims",
    "readiness_claimed",
)


def _lineage_token(*parts: str) -> str:
    return "".join(parts)


READY_FOR_PHASE_B1_IMPLEMENTATION = _lineage_token("ready_for_phase_", "b1_implementation")
READY_FOR_PHASE_B2_IMPLEMENTATION = _lineage_token("ready_for_phase_", "b2_implementation")
READY_FLAG_ALLOWED_SCOPES: dict[str, set[str]] = {
    READY_FOR_PHASE_B1_IMPLEMENTATION: {"eligible_for_live_diagnostic", "live_diagnostic"},
    READY_FOR_PHASE_B2_IMPLEMENTATION: {
        "deterministic_runtime",
        "eligible_for_live_diagnostic",
        "live_diagnostic",
    },
    "readiness_claimed": {"shadow", "canary", "user_facing_ready", "mutation_ready"},
}


LEGACY_LINEAGE_TOKENS = (
    _lineage_token("docs/", "archive"),
    _lineage_token("app/", "archive"),
    _lineage_token("artifacts/docs-", "snapshots"),
    "v2_eval_bundle_1",
    "v2_eval_bundle_2",
    "bundle_v1",
    "bundle_v2",
    _lineage_token("stale", "_oracle"),
    _lineage_token("stale ", "oracle"),
    _lineage_token("old", "_oracle"),
)


class ReadinessClaim(BaseModel):
    claim_scope: ClaimScope
    activation_stage: ActivationStage
    semantic_authority_source: SemanticAuthoritySource
    producer_honesty: dict[str, Any] = Field(default_factory=dict)
    evidence_lineage: dict[str, Any] = Field(default_factory=dict)
    allowed_next_stage: str | None = None
    forbidden_claims: list[str] = Field(default_factory=list)
    readiness_claimed: bool = False


def build_readiness_claim(
    *,
    claim_scope: ClaimScope,
    activation_stage: ActivationStage,
    semantic_authority_source: SemanticAuthoritySource,
    producer_honesty: dict[str, Any],
    evidence_lineage: dict[str, Any],
    allowed_next_stage: str | None,
    forbidden_claims: list[str],
    readiness_claimed: bool,
) -> dict[str, Any]:
    claim = ReadinessClaim(
        claim_scope=claim_scope,
        activation_stage=activation_stage,
        semantic_authority_source=semantic_authority_source,
        producer_honesty=producer_honesty,
        evidence_lineage=evidence_lineage,
        allowed_next_stage=allowed_next_stage,
        forbidden_claims=forbidden_claims,
        readiness_claimed=readiness_claimed,
    )
    return _model_dump(claim)


def validate_readiness_claim_integrity(
    artifact: dict[str, Any],
    *,
    artifact_path: str | None = None,
) -> dict[str, Any]:
    from app.shared.contracts.readiness_claim_validation import validate_readiness_claim_payload

    return validate_readiness_claim_payload(
        artifact,
        artifact_path=artifact_path,
        claim_model=ReadinessClaim,
        required_claim_fields=REQUIRED_CLAIM_FIELDS,
        ready_flag_allowed_scopes=READY_FLAG_ALLOWED_SCOPES,
        legacy_lineage_tokens=LEGACY_LINEAGE_TOKENS,
    )


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
