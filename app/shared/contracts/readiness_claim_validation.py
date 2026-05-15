from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def validate_readiness_claim_payload(
    artifact: dict[str, Any],
    *,
    artifact_path: str | None,
    claim_model: type[BaseModel],
    required_claim_fields: tuple[str, ...],
    ready_flag_allowed_scopes: dict[str, set[str]],
    legacy_lineage_tokens: tuple[str, ...],
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
        return _failed_result(artifact_path, readiness_flags, blockers, warnings)

    missing = [field for field in required_claim_fields if field not in raw_claim]
    if missing:
        for field in missing:
            _add(
                blockers,
                "readiness_claim_missing_required_field",
                f"readiness_claim is missing required field: {field}.",
                field=field,
                artifact_path=artifact_path,
            )
        return _failed_result(artifact_path, readiness_flags, blockers, warnings)

    try:
        claim = claim_model(**raw_claim)
    except Exception as exc:  # pydantic version-neutral validation surface
        _add(
            blockers,
            "readiness_claim_invalid",
            f"readiness_claim does not match the shared contract: {exc}",
            artifact_path=artifact_path,
        )
        return _failed_result(artifact_path, readiness_flags, blockers, warnings)

    _validate_nested_readiness_claimed(artifact, claim, blockers, artifact_path)
    _validate_evidence_lineage(claim.evidence_lineage, blockers, artifact_path, legacy_lineage_tokens)
    if claim.semantic_authority_source == "forbidden_legacy_oracle":
        _add(
            blockers,
            "readiness_claim_forbidden_semantic_authority",
            "Legacy oracles cannot be semantic authority for readiness claims.",
            artifact_path=artifact_path,
        )

    semantic_owner_integrity = artifact.get("semantic_owner_integrity")
    if readiness_flags and isinstance(semantic_owner_integrity, dict) and semantic_owner_integrity.get("passed") is False:
        _add(
            blockers,
            "semantic_owner_integrity_blocks_readiness",
            "Artifacts with semantic-owner integrity failures cannot set ready_for_* true.",
            artifact_path=artifact_path,
        )

    _validate_readiness_scope(claim.claim_scope, readiness_flags, blockers, artifact_path, ready_flag_allowed_scopes)
    _validate_producer_honesty(claim.producer_honesty, readiness_flags, blockers, artifact_path)

    return {
        "passed": not blockers, "artifact_path": artifact_path, "readiness_flags": readiness_flags,
        "claim_scope": claim.claim_scope, "activation_stage": claim.activation_stage,
        "semantic_authority_source": claim.semantic_authority_source, "blockers": blockers, "warnings": warnings,
    }


def _validate_nested_readiness_claimed(artifact: dict[str, Any], claim: BaseModel, blockers: list[dict[str, Any]], artifact_path: str | None) -> None:
    top_level_present = "readiness_claimed" in artifact
    top_level_value = artifact.get("readiness_claimed")
    nested_value = getattr(claim, "readiness_claimed")
    mismatch = top_level_present and top_level_value is not nested_value
    nested_claim_without_top_level_flag = nested_value is True and top_level_value is not True
    if mismatch or nested_claim_without_top_level_flag:
        _add(
            blockers,
            "readiness_claim_flag_mismatch",
            "Top-level readiness_claimed must match readiness_claim.readiness_claimed.",
            artifact_path=artifact_path,
            top_level_readiness_claimed=top_level_value,
            nested_readiness_claimed=nested_value,
        )


def _validate_evidence_lineage(lineage: dict[str, Any], blockers: list[dict[str, Any]], artifact_path: str | None, legacy_lineage_tokens: tuple[str, ...]) -> None:
    if not (lineage.get("artifacts") or lineage.get("producers")):
        _add(
            blockers,
            "readiness_claim_evidence_lineage_missing",
            "readiness_claim.evidence_lineage must name at least one producer or artifact.",
            artifact_path=artifact_path,
        )

    legacy_matches = _legacy_lineage_matches(lineage, legacy_lineage_tokens)
    if legacy_matches:
        _add(
            blockers,
            "readiness_claim_legacy_lineage",
            "Readiness evidence lineage must not depend on legacy bundles, archives, obsolete eval oracles, or snapshots.",
            matches=legacy_matches,
            artifact_path=artifact_path,
        )


def _validate_readiness_scope(claim_scope: str, readiness_flags: dict[str, bool], blockers: list[dict[str, Any]], artifact_path: str | None, ready_flag_allowed_scopes: dict[str, set[str]]) -> None:
    for flag_name in readiness_flags:
        allowed_scopes = ready_flag_allowed_scopes.get(flag_name, set())
        if claim_scope not in allowed_scopes:
            _add(
                blockers,
                "readiness_claim_overreach",
                f"{flag_name}=true is not supported by claim_scope={claim_scope}.",
                flag=flag_name,
                claim_scope=claim_scope,
                allowed_scopes=sorted(allowed_scopes),
            artifact_path=artifact_path,
        )

def _validate_producer_honesty(producer_honesty: dict[str, Any], readiness_flags: dict[str, bool], blockers: list[dict[str, Any]], artifact_path: str | None) -> None:
    if readiness_flags and producer_honesty.get("runner_inferred_semantics") is True:
        _add(
            blockers,
            "producer_honesty_semantics_inferred_for_readiness",
            "Runner-inferred semantics cannot support a readiness claim.",
            artifact_path=artifact_path,
        )

    if readiness_flags and (
        producer_honesty.get("final_mapping_fabricated") is True
        or producer_honesty.get("mutation_fabricated") is True
    ):
        _add(
            blockers,
            "producer_honesty_fabricated_runtime_truth",
            "Fabricated final mapping or mutation cannot support a readiness claim.",
            artifact_path=artifact_path,
        )


def _readiness_flags(artifact: dict[str, Any]) -> dict[str, bool]:
    flags = {key: True for key, value in artifact.items() if key.startswith("ready_for_") and value is True}
    if artifact.get("readiness_claimed") is True:
        flags["readiness_claimed"] = True
    return flags


def _legacy_lineage_matches(lineage: dict[str, Any], legacy_lineage_tokens: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for value in _flatten_strings(lineage):
        lowered = value.replace("\\", "/").lower()
        matches.extend(token for token in legacy_lineage_tokens if token in lowered)
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
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_strings(item))
        return flattened
    return []


def _failed_result(artifact_path: str | None, readiness_flags: dict[str, bool], blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "passed": False,
        "artifact_path": artifact_path,
        "readiness_flags": readiness_flags,
        "blockers": blockers,
        "warnings": warnings,
    }


def _add(blockers: list[dict[str, Any]], code: str, detail: str, **extra: Any) -> None:
    payload: dict[str, Any] = {"code": code, "detail": detail}
    payload.update({key: value for key, value in extra.items() if value is not None})
    blockers.append(payload)
