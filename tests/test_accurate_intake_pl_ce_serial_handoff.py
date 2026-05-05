from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_pl_ce_serial_handoff import (
    build_pl_ce_serial_handoff_artifact,
)


def _activation_manifest() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_pl_ce_activation_review_manifest",
        "status": "pl_ce_activation_review_manifest_ready",
        "blockers": [],
        "aggregate_only": True,
        "self_generated_evidence_used": False,
        "human_review_required": True,
        "live_diagnostic_human_approval_required": True,
        "ready_for_live_diagnostic_decision": False,
        "ready_for_fdb_integration": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "remaining_stop_gates": {
            "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
            "live_provider_status": "blocked_pending_human_approval",
        },
    }


def _stack_metadata() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_pl_ce_pr_stack_metadata",
        "metadata_source": "merge_owner_snapshot",
        "stack_items": [
            {
                "slice_id": "local_mvp_candidate_bundle",
                "pr_number": 281,
                "head": "codex/plce-local-mvp-candidate-bundle-v1",
                "base": "main",
                "state": "open",
                "draft": True,
                "checks": "success",
            },
            {
                "slice_id": "browser_activation_evidence_gate",
                "pr_number": 283,
                "head": "codex/plce-browser-activation-evidence-gate-v1",
                "base": "codex/plce-local-mvp-candidate-bundle-v1",
                "state": "open",
                "draft": True,
                "checks": "success",
            },
            {
                "slice_id": "activation_review_manifest",
                "pr_number": 287,
                "head": "codex/plce-activation-review-manifest-v1",
                "base": "codex/plce-browser-activation-evidence-gate-v1",
                "state": "open",
                "draft": True,
                "checks": "pending",
            },
        ],
        "merge_owner_required": True,
        "producer_should_merge": False,
    }


def test_serial_handoff_reports_stack_ready_for_merge_owner_review_only() -> None:
    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        stack_metadata=_stack_metadata(),
    )

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_serial_handoff"
    assert artifact["status"] == "ready_for_merge_owner_review"
    assert artifact["producer_track"] == "PL_CE"
    assert artifact["merge_owner_required"] is True
    assert artifact["producer_should_merge"] is False
    assert artifact["producer_should_continue_building"] is True
    assert artifact["stack_order_valid"] is True
    assert artifact["activation_review_manifest_ready"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["remaining_stop_gates"]["fooddb_artifact_status"] == (
        "blocked_waiting_for_fdb_artifact"
    )
    assert artifact["remaining_stop_gates"]["live_provider_status"] == (
        "blocked_pending_human_approval"
    )
    assert artifact["blockers"] == []


def test_serial_handoff_blocks_activation_manifest_overclaim() -> None:
    manifest = _activation_manifest()
    manifest["ready_for_live_diagnostic_decision"] = True
    manifest["product_readiness_claimed"] = True
    manifest["real_fooddb_pass_claimed"] = {"claimed": True}

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=manifest,
        stack_metadata=_stack_metadata(),
    )

    assert artifact["status"] == "blocked"
    assert "activation_review_manifest.ready_for_live_diagnostic_decision" in artifact["blockers"]
    assert "activation_review_manifest.product_readiness_claimed" in artifact["blockers"]
    assert "activation_review_manifest.real_fooddb_pass_claimed" in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["product_readiness_claimed"] is False


def test_serial_handoff_blocks_broken_stack_order_or_producer_merge_claim() -> None:
    stack = _stack_metadata()
    stack["producer_should_merge"] = True
    stack["stack_items"][1]["base"] = "main"
    stack["stack_items"][2]["checks"] = "failure"

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        stack_metadata=stack,
    )

    assert artifact["status"] == "blocked"
    assert "stack.browser_activation_evidence_gate.unexpected_base:main" in artifact["blockers"]
    assert "stack.activation_review_manifest.checks_failure" in artifact["blockers"]
    assert "stack.producer_should_merge_not_false" in artifact["blockers"]
    assert artifact["producer_should_merge"] is False


def test_serial_handoff_blocks_wrong_pr_numbers() -> None:
    stack = _stack_metadata()
    stack["stack_items"][0]["pr_number"] = 999
    stack["stack_items"][1]["pr_number"] = 998
    stack["stack_items"][2]["pr_number"] = 997

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        stack_metadata=stack,
    )

    assert artifact["status"] == "blocked"
    assert "stack.local_mvp_candidate_bundle.unexpected_pr_number:999" in artifact["blockers"]
    assert "stack.browser_activation_evidence_gate.unexpected_pr_number:998" in artifact["blockers"]
    assert "stack.activation_review_manifest.unexpected_pr_number:997" in artifact["blockers"]
    assert artifact["stack_order_valid"] is False


def test_serial_handoff_blocks_synthetic_stack_metadata() -> None:
    stack = _stack_metadata()
    stack["artifact_type"] = "synthetic_ci_pl_ce_pr_stack_metadata_fixture"
    stack["metadata_source"] = "ci_static_fixture"

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        stack_metadata=stack,
    )

    assert artifact["status"] == "blocked"
    assert (
        "stack_metadata.unexpected_artifact_type:synthetic_ci_pl_ce_pr_stack_metadata_fixture"
        in artifact["blockers"]
    )
    assert "stack_metadata.untrusted_metadata_source:ci_static_fixture" in artifact["blockers"]
    assert artifact["stack_order_valid"] is False


def test_serial_handoff_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_serial_handoff import main

    activation_path = tmp_path / "activation.json"
    stack_path = tmp_path / "stack.json"
    output_path = tmp_path / "serial-handoff.json"
    activation_path.write_text(
        json.dumps(_activation_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )
    stack_path.write_text(json.dumps(_stack_metadata(), ensure_ascii=False), encoding="utf-8")

    exit_code = main(
        [
            "--activation-review-manifest",
            str(activation_path),
            "--stack-json",
            str(stack_path),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "ready_for_merge_owner_review"
    assert artifact["included_artifacts"]["activation_review_manifest"]["source_artifact_path"]


def test_serial_handoff_cli_can_write_blocked_builder_smoke_when_allowed(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_serial_handoff import main

    activation_path = tmp_path / "activation.json"
    stack_path = tmp_path / "stack.json"
    output_path = tmp_path / "serial-handoff.json"
    activation_path.write_text(
        json.dumps(_activation_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )
    stack = _stack_metadata()
    stack["artifact_type"] = "synthetic_ci_pl_ce_pr_stack_metadata_fixture"
    stack["metadata_source"] = "ci_static_fixture"
    stack_path.write_text(json.dumps(stack, ensure_ascii=False), encoding="utf-8")

    exit_code = main(
        [
            "--activation-review-manifest",
            str(activation_path),
            "--stack-json",
            str(stack_path),
            "--output",
            str(output_path),
            "--allow-blocked",
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "blocked"
    assert "stack_metadata.untrusted_metadata_source:ci_static_fixture" in artifact["blockers"]


def test_serial_handoff_cli_rejects_missing_stack_without_autofix(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_pl_ce_serial_handoff import main

    activation_path = tmp_path / "activation.json"
    output_path = tmp_path / "serial-handoff.json"
    activation_path.write_text(
        json.dumps(_activation_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--activation-review-manifest",
            str(activation_path),
            "--stack-json",
            str(tmp_path / "missing-stack.json"),
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert artifact["status"] == "blocked"
    assert "stack_metadata.missing" in artifact["blockers"]
    assert artifact["stack_order_valid"] is False
    assert artifact["autofix_attempted"] is False


def test_serial_handoff_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_serial_handoff.py"),
        Path("scripts/build_accurate_intake_pl_ce_serial_handoff.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "from tavily",
        "import tavily",
        "tavilyclient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "openai",
        "requests",
        "httpx",
        "ready_for_live_diagnostic_decision = True",
        "fooddb_evidence_used = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8").lower() for path in source_paths)

    for fragment in forbidden:
        assert fragment.lower() not in combined_source


def test_ci_builds_serial_handoff_artifact() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_pl_ce_serial_handoff.py" in workflow
    assert "synthetic_ci_pl_ce_pr_stack_metadata_fixture" in workflow
    assert "--allow-blocked" in workflow
    assert "build_accurate_intake_pl_ce_serial_handoff.py" in workflow
    assert "accurate_intake_pl_ce_serial_handoff_ci.json" in workflow
