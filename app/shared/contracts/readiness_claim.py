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
READY_FLAG_ALLOWED_SCOPES: dict[str, set[str]] = {
    "ready_for_phase_b1_implementation": {"eligible_for_live_diagnostic", "live_diagnostic"},
    "ready_for_phase_b2_implementation": {
        "deterministic_runtime",
        "eligible_for_live_diagnostic",
        "live_diagnostic",
    },
    "readiness_claimed": {"shadow", "canary", "user_facing_ready", "mutation_ready"},
}


def _lineage_token(*parts: str) -> str:
    return "".join(parts)


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
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    readiness_flags = _readiness_flags(artifact)
    raw_claim = artifact.get("readiness_claim")

    if not isinstance(raw_claim, dict):
        _add(
            blockers,
            "readiness_claim_missing",
            "Official readiness artifacts must include a readiness_claim block.",
            artifact_path=artifact_path,
        )
        return {
            "passed": False,
            "artifact_path": artifact_path,
            "readiness_flags": readiness_flags,
            "blockers": blockers,
            "warnings": warnings,
        }

    missing = [field for field in REQUIRED_CLAIM_FIELDS if field not in raw_claim]
    if missing:
        for field in missing:
            _add(
                blockers,
                "readiness_claim_missing_required_field",
                f"readiness_claim is missing required field: {field}.",
                field=field,
                artifact_path=artifact_path,
            )
        return {
            "passed": False,
            "artifact_path": artifact_path,
            "readiness_flags": readiness_flags,
            "blockers": blockers,
            "warnings": warnings,
        }

    try:
        claim = ReadinessClaim(**raw_claim)
    except Exception as exc:  # pydantic version-neutral validation surface
        _add(
            blockers,
            "readiness_claim_invalid",
            f"readiness_claim does not match the shared contract: {exc}",
            artifact_path=artifact_path,
        )
        return {
            "passed": False,
            "artifact_path": artifact_path,
            "readiness_flags": readiness_flags,
            "blockers": blockers,
            "warnings": warnings,
        }

    if not _lineage_has_evidence(claim.evidence_lineage):
        _add(
            blockers,
            "readiness_claim_evidence_lineage_missing",
            "readiness_claim.evidence_lineage must name at least one producer or artifact.",
            artifact_path=artifact_path,
        )

    legacy_matches = _legacy_lineage_matches(claim.evidence_lineage)
    if legacy_matches:
        _add(
            blockers,
            "readiness_claim_legacy_lineage",
            "Readiness evidence lineage must not depend on legacy bundles, archives, obsolete eval oracles, or snapshots.",
            matches=legacy_matches,
            artifact_path=artifact_path,
        )

    if claim.semantic_authority_source == "forbidden_legacy_oracle":
        _add(
            blockers,
            "readiness_claim_forbidden_semantic_authority",
            "Legacy oracles cannot be semantic authority for readiness claims.",
            artifact_path=artifact_path,
        )

    semantic_owner_integrity = artifact.get("semantic_owner_integrity")
    if (
        readiness_flags
        and isinstance(semantic_owner_integrity, dict)
        and semantic_owner_integrity.get("passed") is False
    ):
        _add(
            blockers,
            "semantic_owner_integrity_blocks_readiness",
            "Artifacts with semantic-owner integrity failures cannot set ready_for_* true.",
            artifact_path=artifact_path,
        )

    for flag_name in readiness_flags:
        allowed_scopes = READY_FLAG_ALLOWED_SCOPES.get(flag_name, set())
        if claim.claim_scope not in allowed_scopes:
            _add(
                blockers,
                "readiness_claim_overreach",
                f"{flag_name}=true is not supported by claim_scope={claim.claim_scope}.",
                flag=flag_name,
                claim_scope=claim.claim_scope,
                allowed_scopes=sorted(allowed_scopes),
                artifact_path=artifact_path,
            )

    if readiness_flags and claim.producer_honesty.get("runner_inferred_semantics") is True:
        _add(
            blockers,
            "producer_honesty_semantics_inferred_for_readiness",
            "Runner-inferred semantics cannot support a readiness claim.",
            artifact_path=artifact_path,
        )

    if readiness_flags and (
        claim.producer_honesty.get("final_mapping_fabricated") is True
        or claim.producer_honesty.get("mutation_fabricated") is True
    ):
        _add(
            blockers,
            "producer_honesty_fabricated_runtime_truth",
            "Fabricated final mapping or mutation cannot support a readiness claim.",
            artifact_path=artifact_path,
        )

    return {
        "passed": not blockers,
        "artifact_path": artifact_path,
        "readiness_flags": readiness_flags,
        "claim_scope": claim.claim_scope,
        "activation_stage": claim.activation_stage,
        "semantic_authority_source": claim.semantic_authority_source,
        "blockers": blockers,
        "warnings": warnings,
    }


def _readiness_flags(artifact: dict[str, Any]) -> dict[str, bool]:
    flags = {
        key: True
        for key, value in artifact.items()
        if key.startswith("ready_for_") and value is True
    }
    if artifact.get("readiness_claimed") is True:
        flags["readiness_claimed"] = True
    return flags


def _lineage_has_evidence(lineage: dict[str, Any]) -> bool:
    artifacts = lineage.get("artifacts")
    producers = lineage.get("producers")
    return bool(artifacts) or bool(producers)


def _legacy_lineage_matches(lineage: dict[str, Any]) -> list[str]:
    matches: list[str] = []
    for value in _flatten_strings(lineage):
        lowered = value.replace("\\", "/").lower()
        matches.extend(token for token in LEGACY_LINEAGE_TOKENS if token in lowered)
    return sorted(set(matches))


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for item in value.values():
            flattened.extend(_flatten_strings(item))
        return flattened
    if isinstance(value, list | tuple | set):
        flattened = []
        for item in value:
            flattened.extend(_flatten_strings(item))
        return flattened
    return []


def _add(blockers: list[dict[str, Any]], code: str, detail: str, **extra: Any) -> None:
    payload: dict[str, Any] = {"code": code, "detail": detail}
    payload.update({key: value for key, value in extra.items() if value is not None})
    blockers.append(payload)


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
