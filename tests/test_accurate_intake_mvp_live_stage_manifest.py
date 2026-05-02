from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_stage_manifest import (
    build_accurate_intake_live_stage_manifest,
    write_accurate_intake_live_stage_manifest,
)


def _live_artifact(
    *,
    stage_id: str,
    status: str,
    failure_layer: str | None = None,
    failure_family: str | None = None,
    overclaim: bool = False,
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "claim_scope": "live_diagnostic",
        "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        "provider_profile_model": "grok-4-fast",
        "transport_mode": "synthetic_tool_transport",
        "schema_name": "founder_live_manager_contract",
        "schema_version": "v1",
        "readiness_claimed": overclaim,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "live_provider_used_as_truth": False,
        "stages": [
            {
                "stage_id": stage_id,
                "status": status,
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
                "transport_mode": "synthetic_tool_transport",
                "attempt_count": 1 if status != "blocked" else 0,
                "latency_ms": 123,
                "timeout_budget_ms": 180000,
                "failure_layer": failure_layer,
                "failure_family": failure_family,
                "retry_policy_applied": False,
            }
        ],
        "summary": {
            "case_count": 0,
            "strict_pass_count": 0,
            "repaired_pass_count": 0,
            "contract_fail_count": 0,
            "timeout_count": 0,
            "provider_timeout_count": 0,
            "failure_layers": [failure_layer] if failure_layer else [],
            "failure_families": [failure_family] if failure_family else [],
        },
        "cases": [],
    }


def test_live_stage_manifest_links_stage_artifacts_and_preserves_non_claims(tmp_path: Path) -> None:
    health = tmp_path / "health.json"
    schema = tmp_path / "schema.json"
    single = tmp_path / "single.json"
    health.write_text(json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass")), encoding="utf-8")
    schema.write_text(json.dumps(_live_artifact(stage_id="schema_contract_probe", status="pass")), encoding="utf-8")
    single.write_text(
        json.dumps(
            _live_artifact(
                stage_id="single_case_live_probe",
                status="fail",
                failure_layer="provider_contract_non_adherence",
                failure_family="synthetic_decision_tool_call_missing",
            )
        ),
        encoding="utf-8",
    )

    manifest = build_accurate_intake_live_stage_manifest([health, schema, single])

    assert manifest["artifact_type"] == "accurate_intake_mvp_live_stage_manifest"
    assert manifest["claim_scope"] == "live_diagnostic_stage_manifest"
    assert manifest["readiness_claimed"] is False
    assert manifest["product_readiness_claimed"] is False
    assert manifest["private_self_use_approved"] is False
    assert manifest["production_selected"] is False
    assert manifest["mutation_rollout_approved"] is False
    assert manifest["runtime_web_activation_approved"] is False
    assert manifest["input_integrity"]["passed"] is True
    assert manifest["stage_summary"]["single_case_probe_status"] == "fail"
    assert manifest["stage_summary"]["stage_failures"] == [
        {
            "stage_id": "single_case_live_probe",
            "status": "fail",
            "failure_layer": "provider_contract_non_adherence",
            "failure_family": "synthetic_decision_tool_call_missing",
        }
    ]
    assert [stage["artifact_path"] for stage in manifest["stages"]] == [str(health), str(schema), str(single)]


def test_live_stage_manifest_integrity_blocks_overclaiming_source(tmp_path: Path) -> None:
    health = tmp_path / "health.json"
    health.write_text(
        json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass", overclaim=True)),
        encoding="utf-8",
    )

    manifest = build_accurate_intake_live_stage_manifest([health])

    assert manifest["input_integrity"]["passed"] is False
    assert "source_0_readiness_claimed" in manifest["input_integrity"]["blockers"]
    assert manifest["readiness_claimed"] is False


def test_live_stage_manifest_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "health.json"
    source.write_text(json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass")), encoding="utf-8")

    output = write_accurate_intake_live_stage_manifest(stage_artifact_paths=[source], output_dir=tmp_path)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_live_stage_manifest.json"
    assert payload["artifact_type"] == "accurate_intake_mvp_live_stage_manifest"
    assert payload["stage_summary"]["provider_health_status"] == "pass"
