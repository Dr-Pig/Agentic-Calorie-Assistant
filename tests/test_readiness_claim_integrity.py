from __future__ import annotations

import json
from pathlib import Path

from app.shared.contracts.readiness_claim import (
    build_readiness_claim,
    validate_readiness_claim_integrity,
)
from scripts.audit_readiness_claim_integrity import audit_readiness_claim_integrity


def _claim(**overrides: object) -> dict[str, object]:
    payload = build_readiness_claim(
        claim_scope="fixture_scaffold",
        activation_stage="fake",
        semantic_authority_source="fake_manager_structured_output",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": True,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": ["artifacts/example.json"],
            "producers": ["tests/test_readiness_claim_integrity.py"],
            "legacy_oracle_used": False,
        },
        allowed_next_stage="deterministic",
        forbidden_claims=["manager_semantics_ready", "user_facing_ready"],
        readiness_claimed=False,
    )
    payload.update(overrides)
    return payload


def test_missing_readiness_claim_fields_block_ready_flag() -> None:
    result = validate_readiness_claim_integrity(
        {
            "artifact_type": "example",
            "ready_for_phase_b1_implementation": True,
            "readiness_claim": {
                "claim_scope": "fixture_scaffold",
            },
        }
    )

    assert result["passed"] is False
    assert any(item["code"] == "readiness_claim_missing_required_field" for item in result["blockers"])


def test_forced_b1_fixture_scope_cannot_claim_phase_b1_readiness() -> None:
    result = validate_readiness_claim_integrity(
        {
            "artifact_type": "wave1_phase_b_minimal_tool_loop_readiness",
            "ready_for_phase_b1_implementation": True,
            "readiness_claim": _claim(
                claim_scope="fixture_scaffold",
                activation_stage="fake",
                allowed_next_stage="deterministic",
            ),
        }
    )

    assert result["passed"] is False
    assert any(item["code"] == "readiness_claim_overreach" for item in result["blockers"])


def test_founder_deterministic_pass_does_not_claim_readiness() -> None:
    result = validate_readiness_claim_integrity(
        {
            "artifact_type": "wave1_founder_e2e_deterministic_diagnostic",
            "provider_mode": "deterministic",
            "readiness_claimed": False,
            "summary": {"pass_count": 7, "fail_count": 0},
            "readiness_claim": _claim(
                claim_scope="deterministic_runtime",
                activation_stage="deterministic",
                semantic_authority_source="fake_manager_structured_output",
                allowed_next_stage="live_diagnostic",
                forbidden_claims=["live_ready", "user_facing_ready", "mutation_ready"],
            ),
        }
    )

    assert result["passed"] is True
    assert result["readiness_flags"] == {}


def test_b2_semantic_owner_inversion_blocks_ready_flag() -> None:
    result = validate_readiness_claim_integrity(
        {
            "artifact_type": "wave1_phase_b2_evidence_synthesis_readiness",
            "ready_for_phase_b2_implementation": True,
            "semantic_owner_integrity": {
                "passed": False,
                "failure_family": "semantic_owner_inversion",
            },
            "readiness_claim": _claim(
                claim_scope="deterministic_runtime",
                activation_stage="deterministic",
                semantic_authority_source="deterministic_validator",
                allowed_next_stage="live_diagnostic",
            ),
        }
    )

    assert result["passed"] is False
    assert any(item["code"] == "semantic_owner_integrity_blocks_readiness" for item in result["blockers"])


def test_audit_script_fails_missing_lineage(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        json.dumps(
            {
                "artifact_type": "example",
                "ready_for_phase_b1_implementation": True,
                "readiness_claim": _claim(evidence_lineage={}),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = audit_readiness_claim_integrity([artifact])

    assert report["passed"] is False
    assert report["artifact_results"][0]["passed"] is False
    assert any(
        item["code"] == "readiness_claim_evidence_lineage_missing"
        for item in report["artifact_results"][0]["blockers"]
    )


def test_readiness_claim_blocks_split_built_legacy_lineage_tokens() -> None:
    result = validate_readiness_claim_integrity(
        {
            "artifact_type": "example",
            "readiness_claim": _claim(
                evidence_lineage={
                    "artifacts": ["artifacts/example.json"],
                    "producers": ["tests/test_readiness_claim_integrity.py"],
                    "legacy_path": "docs/" + "archive/old.md",
                    "oracle": "stale " + "oracle",
                }
            ),
        }
    )

    assert result["passed"] is False
    blockers = [item for item in result["blockers"] if item["code"] == "readiness_claim_legacy_lineage"]
    assert blockers
    assert "docs/" + "archive" in blockers[0]["matches"]
    assert "stale " + "oracle" in blockers[0]["matches"]
