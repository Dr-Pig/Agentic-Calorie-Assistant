from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.nutrition.application.grokfast_fooddb_contract_probe import (
    build_grokfast_fooddb_contract_probe,
)
from app.providers.builderspace_runtime_contract import response_schema_for_stage
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


def _packet_artifact() -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def test_grokfast_fooddb_contract_probe_detects_schema_drift_without_live_output() -> None:
    artifact = build_grokfast_fooddb_contract_probe(
        packet_artifact=_packet_artifact(),
        response_schema_for_constraints=_schema_for_constraints,
    )

    assert artifact["artifact_type"] == "accurate_intake_grokfast_fooddb_contract_probe"
    assert artifact["classification"] == "diagnostic_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_attempted"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["status"] == "contract_drift_detected"
    assert artifact["summary"]["issue_counts"]["schema_allows_forbidden_top_level_evidence_used"] >= 1
    assert (
        artifact["summary"]["issue_counts"]["schema_does_not_require_strict_top_level_item_results"]
        >= 1
    )
    assert artifact["next_recommended_slice"] == "narrow_grokfast_fooddb_profile_schema"


def test_grokfast_fooddb_contract_probe_records_live_provider_shape_drift() -> None:
    packet_artifact = _packet_artifact()
    diagnostic_artifact = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "live_provider_used": True,
        "cases": [
            {
                "case_id": "bare_luwei",
                "manager_output": {
                    "item_results": [],
                    "evidence_used": [],
                    "answer_contract": {},
                },
            },
            {
                "case_id": "boba_large_half_sugar",
                "manager_output": {
                    "answer_contract": {
                        "item_results": [
                            {
                                "food_name": "boba milk tea",
                                "evidence_used": ["custom_drink_boba_milk_tea"],
                            }
                        ]
                    }
                },
            },
        ],
    }

    artifact = build_grokfast_fooddb_contract_probe(
        packet_artifact=packet_artifact,
        response_schema_for_constraints=_schema_for_constraints,
        diagnostic_artifact=diagnostic_artifact,
    )

    bare = next(case for case in artifact["cases"] if case["case_id"] == "bare_luwei")
    boba = next(case for case in artifact["cases"] if case["case_id"] == "boba_large_half_sugar")
    assert "provider_emitted_forbidden_top_level_evidence_used" in bare["issues"]
    assert "provider_put_item_results_in_answer_contract" in boba["issues"]
    assert artifact["source_live_provider_used"] is True


def test_grokfast_fooddb_contract_probe_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_grokfast_fooddb_contract_probe import main

    packet_path = tmp_path / "packet.json"
    output_path = tmp_path / "probe.json"
    write_json_artifact(packet_path, _packet_artifact())

    assert main(["--packet-smoke", str(packet_path), "--output", str(output_path)]) == 0

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "contract_drift_detected"
    assert artifact["non_claims"]


def test_grokfast_fooddb_contract_probe_has_no_live_imports() -> None:
    paths = [
        Path("app/nutrition/application/grokfast_fooddb_contract_probe.py"),
        Path("scripts/build_accurate_intake_grokfast_fooddb_contract_probe.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "httpx.",
        "requests.",
        "allow_live",
        "Kimi",
        "Tavily",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def _schema_for_constraints(constraints: dict) -> dict | None:
    return response_schema_for_stage(MANAGER_LOOP_STAGE, constraints=constraints)
