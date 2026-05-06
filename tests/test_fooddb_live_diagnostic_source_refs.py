from __future__ import annotations

from pathlib import Path

import json

from app.nutrition.application.fooddb_live_artifact_digest import (
    ARTIFACT_DIGEST_ALGORITHM,
    ARTIFACT_DIGEST_SCOPE,
    fooddb_semantic_artifact_digest,
)
from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import main


def _packet_artifact() -> dict:
    payload = json.loads(
        Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig")
    )
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def _preflight_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1",
        "status": "clear_for_grokfast_fooddb_packet_live_diagnostic",
        "clear_to_run_live_diagnostic": True,
        "blockers": [],
        "next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
    }


def _router_readiness_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_food_evidence_retriever_router_readiness_v1",
        "status": "pass",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "fail_count": 0,
            "next_required_slice": "inspect_websearch_status_packet",
        },
    }


def _live_runner_readiness_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1",
        "status": "pass",
        "ready_for_grokfast_fooddb_packet_live_diagnostic": True,
        "ready_for_runtime_truth": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "provider_readiness_checked": False,
        "next_required_slice": "run_explicit_grokfast_fooddb_packet_live_diagnostic",
    }


def test_fixture_runner_threads_upstream_refs_when_explicit_artifacts_are_passed(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    preflight_path = tmp_path / "preflight.json"
    router_path = tmp_path / "router.json"
    readiness_path = tmp_path / "readiness.json"
    output_path = tmp_path / "diagnostic.json"
    packet = _packet_artifact()
    preflight = _preflight_artifact()
    router = _router_readiness_artifact()
    readiness = _live_runner_readiness_artifact()
    write_json_artifact(packet_path, packet)
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(router_path, router)
    write_json_artifact(readiness_path, readiness)

    exit_code = main(
        [
            "--mode",
            "fixture",
            "--packet-smoke",
            str(packet_path),
            "--preflight-artifact",
            str(preflight_path),
            "--router-readiness-artifact",
            str(router_path),
            "--live-runner-readiness-artifact",
            str(readiness_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    diagnostic = read_json_artifact(output_path)
    assert diagnostic["preflight_ref"] == {
        "artifact_type": preflight["artifact_type"],
        "status": preflight["status"],
        "clear_to_run_live_diagnostic": True,
        "next_required_slice": preflight["next_required_slice"],
        "preflight_artifact_digest_algorithm": ARTIFACT_DIGEST_ALGORITHM,
        "preflight_artifact_digest_scope": ARTIFACT_DIGEST_SCOPE,
        "preflight_artifact_digest": fooddb_semantic_artifact_digest(preflight),
    }
    assert diagnostic["router_readiness_ref"] == {
        "artifact_type": router["artifact_type"],
        "status": router["status"],
        "fail_count": 0,
        "next_required_slice": "inspect_websearch_status_packet",
        "router_artifact_digest_algorithm": ARTIFACT_DIGEST_ALGORITHM,
        "router_artifact_digest_scope": ARTIFACT_DIGEST_SCOPE,
        "router_artifact_digest": fooddb_semantic_artifact_digest(router),
    }
    assert diagnostic["live_runner_readiness_ref"] == {
        "artifact_type": readiness["artifact_type"],
        "status": readiness["status"],
        "ready_for_grokfast_fooddb_packet_live_diagnostic": True,
        "ready_for_runtime_truth": False,
        "next_required_slice": readiness["next_required_slice"],
        "live_runner_artifact_digest_algorithm": ARTIFACT_DIGEST_ALGORITHM,
        "live_runner_artifact_digest_scope": ARTIFACT_DIGEST_SCOPE,
        "live_runner_artifact_digest": fooddb_semantic_artifact_digest(readiness),
    }
