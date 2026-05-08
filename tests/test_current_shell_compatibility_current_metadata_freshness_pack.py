from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from app.composition.accurate_intake_pl_ce_current_metadata_freshness import (
    build_pl_ce_current_metadata_freshness_pack,
)


def _timestamp(offset_hours: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(hours=offset_hours)).isoformat()


def _payload(artifact_type: str, status: str) -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": artifact_type,
        "status": status,
        "generated_at_utc": _timestamp(),
    }


def _evidence() -> dict[str, dict[str, object]]:
    evidence = {
        "ui_same_truth_contract": _payload("accurate_intake_ui_same_truth_render_contract", "pass"),
        "context_quality_pack": _payload(
            "accurate_intake_context_quality_pack",
            "context_quality_diagnostic_pass",
        ),
        "product_pages_visual_qa": _payload("accurate_intake_product_pages_visual_qa", "pass"),
        "product_pages_long_session_navigation_smoke": _payload(
            "accurate_intake_product_pages_long_session_navigation_smoke",
            "pass",
        ),
        "pl_ce_ui_context_alignment_pack": _payload(
            "accurate_intake_pl_ce_ui_context_alignment_pack",
            "ui_context_alignment_ready_for_human_review",
        ),
        "current_shell_compatibility_local_mvp_candidate_bundle": _payload(
            "accurate_intake_current_shell_compatibility_local_mvp_candidate_bundle",
            "current_shell_compatibility_local_mvp_candidate_ready_for_human_review",
        ),
        "pl_ce_product_pages_self_use_flow_gate": _payload(
            "accurate_intake_pl_ce_product_pages_self_use_flow_gate",
            "product_pages_self_use_flow_ready_for_human_review",
        ),
        "pl_ce_browser_activation_evidence_gate": _payload(
            "accurate_intake_pl_ce_browser_activation_evidence_gate",
            "browser_activation_evidence_ready_for_human_review",
        ),
        "non_fooddb_manager_tool_contract": _payload(
            "accurate_intake_non_fooddb_manager_tool_contract",
            "non_fooddb_manager_tool_contract_ready_for_human_review",
        ),
        "current_shell_compatibility_activation_review_manifest": _payload(
            "accurate_intake_current_shell_compatibility_activation_review_manifest",
            "current_shell_compatibility_activation_review_manifest_ready",
        ),
    }
    evidence["current_shell_compatibility_local_mvp_candidate_bundle"]["fooddb_dependency"] = {
        "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
        "ready_for_fdb_integration": False,
    }
    evidence["current_shell_compatibility_activation_review_manifest"]["remaining_stop_gates"] = {
        "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
        "live_provider_status": "blocked_pending_human_approval",
    }
    return evidence


def test_current_metadata_freshness_pack_accepts_current_product_pages_chain() -> None:
    pack = build_pl_ce_current_metadata_freshness_pack(evidence=_evidence())

    assert (
        pack["artifact_type"]
        == "accurate_intake_current_shell_compatibility_current_metadata_freshness_pack"
    )
    assert (
        pack["status"]
        == "current_shell_compatibility_current_metadata_freshness_ready_for_serial_handoff"
    )
    assert pack["ready_for_serial_handoff"] is True
    assert pack["metadata_only"] is True
    assert pack["source_status_only"] is True
    assert "ready_for_live_diagnostic_decision" not in pack
    assert "ready_for_fdb_integration" not in pack
    assert "live_llm_invoked" not in pack
    assert "web_tavily_used" not in pack
    assert "fooddb_evidence_used" not in pack
    assert "real_fooddb_pass_claimed" not in pack
    assert "dogfood_pass" not in pack
    assert "product_readiness_claimed" not in pack
    assert "private_self_use_approved" not in pack
    assert pack["fresh_artifact_count"] == pack["required_artifact_count"] == 10
    assert "product_pages_long_session_navigation_smoke" in pack["required_artifacts"]
    assert "pl_ce_ui_context_alignment_pack" in pack["required_artifacts"]
    assert "pl_ce_product_pages_self_use_flow_gate" in pack["required_artifacts"]
    assert "non_fooddb_manager_tool_contract" in pack["required_artifacts"]
    assert pack["blockers"] == []


def test_current_metadata_freshness_pack_blocks_missing_stale_or_overclaiming_inputs() -> None:
    evidence = _evidence()
    evidence.pop("product_pages_visual_qa")
    evidence["context_quality_pack"]["generated_at_utc"] = _timestamp(-96)
    evidence["pl_ce_product_pages_self_use_flow_gate"]["product_readiness_claimed"] = True

    pack = build_pl_ce_current_metadata_freshness_pack(evidence=evidence, max_age_hours=24)

    assert pack["status"] == "blocked"
    assert "product_pages_visual_qa.missing" in pack["blockers"]
    assert "context_quality_pack.stale" in pack["blockers"]
    assert "pl_ce_product_pages_self_use_flow_gate.product_readiness_claimed" in pack["blockers"]
    assert pack["ready_for_serial_handoff"] is False
    assert "ready_for_fdb_integration" not in pack


def test_current_metadata_freshness_pack_blocks_missing_stop_gates() -> None:
    evidence = _evidence()
    evidence["current_shell_compatibility_activation_review_manifest"]["remaining_stop_gates"] = {
        "fooddb_artifact_status": "ready",
        "live_provider_status": "ready",
    }

    pack = build_pl_ce_current_metadata_freshness_pack(evidence=evidence)

    assert pack["status"] == "blocked"
    assert "current_shell_compatibility_activation_review_manifest.fooddb_stop_gate_missing" in pack["blockers"]
    assert "current_shell_compatibility_activation_review_manifest.live_provider_stop_gate_missing" in pack["blockers"]


def test_current_metadata_freshness_pack_cli_writes_output(tmp_path: Path, capsys) -> None:
    from scripts import build_current_shell_compatibility_current_metadata_freshness_pack as module

    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    for group_id, payload in _evidence().items():
        (artifact_dir / f"{group_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    output_path = tmp_path / "current-metadata.json"
    args = ["--output", str(output_path)]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    pack = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert (
        printed["status"]
        == "current_shell_compatibility_current_metadata_freshness_ready_for_serial_handoff"
    )
    assert (
        pack["status"]
        == "current_shell_compatibility_current_metadata_freshness_ready_for_serial_handoff"
    )


def test_current_metadata_freshness_pack_source_stays_out_of_fooddb_websearch_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_current_metadata_freshness.py"),
        Path("scripts/build_current_shell_compatibility_current_metadata_freshness_pack.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "requests",
        "httpx",
        "ready_for_live_diagnostic_decision = True",
        "fooddb_evidence_used = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for fragment in forbidden:
        assert fragment not in combined_source
