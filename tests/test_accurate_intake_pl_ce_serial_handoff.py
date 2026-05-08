from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_pl_ce_serial_handoff import (
    build_pl_ce_serial_handoff_artifact,
)


def _activation_manifest() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_current_shell_compatibility_activation_review_manifest",
        "status": "current_shell_compatibility_activation_review_manifest_ready",
        "blockers": [],
        "aggregate_only": True,
        "self_generated_evidence_used": False,
        "human_review_required": True,
        "live_diagnostic_human_approval_required": True,
        "remaining_stop_gates": {
            "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
            "live_provider_status": "blocked_pending_human_approval",
        },
    }


def _queue_metadata() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_current_shell_compatibility_merge_queue_metadata",
        "metadata_source": "github_merge_queue_snapshot",
        "queue_policy": {
            "merge_mechanism": "github_merge_queue",
            "old_main_merge_lock_used": False,
            "manual_main_merge_forbidden": True,
            "wait_for_pr_merged_before_next_slice": True,
            "cleanup_only_after_merged_and_clean": True,
        },
        "queue_items": [
            {
                "slice_id": "plce_merge_queue_handoff_refresh",
                "pr_number": 458,
                "head": "codex/plce-merge-queue-handoff-refresh",
                "base": "main",
                "state": "open",
                "draft": False,
                "ready_for_queue": True,
                "checks": "success",
                "merge_queue_status": "queued",
            },
        ],
        "merge_queue_required": True,
        "producer_should_manual_merge": False,
    }


def _current_metadata_freshness_pack() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_current_shell_compatibility_current_metadata_freshness_pack",
        "status": "current_shell_compatibility_current_metadata_freshness_ready_for_serial_handoff",
        "blockers": [],
        "metadata_only": True,
        "source_status_only": True,
        "ready_for_serial_handoff": True,
        "fresh_artifact_count": 10,
        "required_artifact_count": 10,
    }


def test_serial_handoff_reports_merge_queue_ready_for_review_only() -> None:
    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        current_metadata_freshness_pack=_current_metadata_freshness_pack(),
        queue_metadata=_queue_metadata(),
    )

    assert artifact["artifact_type"] == "accurate_intake_current_shell_compatibility_serial_handoff"
    assert artifact["status"] == "ready_for_merge_queue_review"
    assert artifact["producer_track"] == "CurrentShell"
    assert artifact["delivery_mode"] == "github_merge_queue"
    assert artifact["merge_queue_required"] is True
    assert artifact["producer_should_manual_merge"] is False
    assert artifact["producer_should_wait_for_queue_merge"] is True
    assert artifact["producer_should_continue_after_merge"] is True
    assert artifact["old_main_merge_lock_used"] is False
    assert artifact["queue_metadata_valid"] is True
    assert artifact["activation_review_manifest_ready"] is True
    assert artifact["current_metadata_freshness_ready"] is True
    assert "ready_for_live_diagnostic_decision" not in artifact
    assert "ready_for_fdb_integration" not in artifact
    assert "live_llm_invoked" not in artifact
    assert "web_tavily_used" not in artifact
    assert "fooddb_evidence_used" not in artifact
    assert "real_fooddb_pass_claimed" not in artifact
    assert "dogfood_pass" not in artifact
    assert "product_readiness_claimed" not in artifact
    assert "private_self_use_approved" not in artifact
    assert artifact["remaining_stop_gates"]["fooddb_artifact_status"] == (
        "blocked_waiting_for_fdb_artifact"
    )
    assert artifact["remaining_stop_gates"]["live_provider_status"] == (
        "blocked_pending_human_approval"
    )
    assert artifact["blockers"] == []
    assert artifact["remaining_stop_gates"]["merge_queue_status"] == "required"


def test_serial_handoff_blocks_activation_manifest_overclaim() -> None:
    manifest = _activation_manifest()
    manifest["ready_for_live_diagnostic_decision"] = True
    manifest["product_readiness_claimed"] = True
    manifest["real_fooddb_pass_claimed"] = {"claimed": True}

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=manifest,
        current_metadata_freshness_pack=_current_metadata_freshness_pack(),
        queue_metadata=_queue_metadata(),
    )

    assert artifact["status"] == "blocked"
    assert "activation_review_manifest.ready_for_live_diagnostic_decision" in artifact["blockers"]
    assert "activation_review_manifest.product_readiness_claimed" in artifact["blockers"]
    assert "activation_review_manifest.real_fooddb_pass_claimed" in artifact["blockers"]
    assert "ready_for_live_diagnostic_decision" not in artifact
    assert "product_readiness_claimed" not in artifact


def test_serial_handoff_blocks_manual_merge_or_stacked_child_claim() -> None:
    queue = _queue_metadata()
    queue["producer_should_manual_merge"] = True
    queue["queue_policy"]["old_main_merge_lock_used"] = True
    queue["queue_items"][0]["base"] = "codex/parent-stack-branch"
    queue["queue_items"][0]["checks"] = "failure"

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        current_metadata_freshness_pack=_current_metadata_freshness_pack(),
        queue_metadata=queue,
    )

    assert artifact["status"] == "blocked"
    assert "queue.plce_merge_queue_handoff_refresh.base_not_main:codex/parent-stack-branch" in artifact["blockers"]
    assert "queue.plce_merge_queue_handoff_refresh.checks_failure" in artifact["blockers"]
    assert "queue.producer_should_manual_merge_not_false" in artifact["blockers"]
    assert "queue.old_main_merge_lock_used" in artifact["blockers"]
    assert artifact["producer_should_manual_merge"] is False


def test_serial_handoff_blocks_not_ready_for_queue_item() -> None:
    queue = _queue_metadata()
    queue["queue_items"][0]["ready_for_queue"] = False
    queue["queue_items"][0]["merge_queue_status"] = "not_queued"

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        current_metadata_freshness_pack=_current_metadata_freshness_pack(),
        queue_metadata=queue,
    )

    assert artifact["status"] == "blocked"
    assert "queue.plce_merge_queue_handoff_refresh.ready_for_queue_not_true" in artifact["blockers"]
    assert "queue.plce_merge_queue_handoff_refresh.merge_queue_status_not_ready:not_queued" in artifact["blockers"]
    assert artifact["queue_metadata_valid"] is False


def test_serial_handoff_blocks_synthetic_stack_metadata() -> None:
    queue = _queue_metadata()
    queue["artifact_type"] = "synthetic_ci_pl_ce_pr_stack_metadata_fixture"
    queue["metadata_source"] = "ci_static_fixture"

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        current_metadata_freshness_pack=_current_metadata_freshness_pack(),
        queue_metadata=queue,
    )

    assert artifact["status"] == "blocked"
    assert (
        "queue_metadata.unexpected_artifact_type:synthetic_ci_pl_ce_pr_stack_metadata_fixture"
        in artifact["blockers"]
    )
    assert "queue_metadata.untrusted_metadata_source:ci_static_fixture" in artifact["blockers"]
    assert artifact["queue_metadata_valid"] is False


def test_serial_handoff_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_serial_handoff import main

    activation_path = tmp_path / "activation.json"
    metadata_path = tmp_path / "current-metadata.json"
    queue_path = tmp_path / "queue.json"
    output_path = tmp_path / "serial-handoff.json"
    activation_path.write_text(
        json.dumps(_activation_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(_current_metadata_freshness_pack(), ensure_ascii=False),
        encoding="utf-8",
    )
    queue_path.write_text(json.dumps(_queue_metadata(), ensure_ascii=False), encoding="utf-8")

    exit_code = main(
        [
            "--activation-review-manifest",
            str(activation_path),
            "--current-metadata-freshness-pack",
            str(metadata_path),
            "--queue-json",
            str(queue_path),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "ready_for_merge_queue_review"
    assert artifact["included_artifacts"]["activation_review_manifest"]["source_artifact_path"]
    assert artifact["included_artifacts"]["current_metadata_freshness_pack"]["source_artifact_path"]


def test_serial_handoff_blocks_missing_or_invalid_current_metadata_freshness_pack() -> None:
    metadata = _current_metadata_freshness_pack()
    metadata["status"] = "blocked"
    metadata["blockers"] = ["pl_ce_product_pages_self_use_flow_gate.stale"]

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_activation_manifest(),
        current_metadata_freshness_pack=metadata,
        queue_metadata=_queue_metadata(),
    )

    assert artifact["status"] == "blocked"
    assert "current_metadata_freshness_pack.unexpected_status:blocked" in artifact["blockers"]
    assert "current_metadata_freshness_pack.upstream_blockers_present" in artifact["blockers"]
    assert artifact["current_metadata_freshness_ready"] is False


def test_serial_handoff_cli_can_write_blocked_builder_smoke_when_allowed(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_serial_handoff import main

    activation_path = tmp_path / "activation.json"
    metadata_path = tmp_path / "current-metadata.json"
    queue_path = tmp_path / "queue.json"
    output_path = tmp_path / "serial-handoff.json"
    activation_path.write_text(
        json.dumps(_activation_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(_current_metadata_freshness_pack(), ensure_ascii=False),
        encoding="utf-8",
    )
    queue = _queue_metadata()
    queue["artifact_type"] = "synthetic_ci_pl_ce_pr_stack_metadata_fixture"
    queue["metadata_source"] = "ci_static_fixture"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")

    exit_code = main(
        [
            "--activation-review-manifest",
            str(activation_path),
            "--current-metadata-freshness-pack",
            str(metadata_path),
            "--queue-json",
            str(queue_path),
            "--output",
            str(output_path),
            "--allow-blocked",
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "blocked"
    assert "queue_metadata.untrusted_metadata_source:ci_static_fixture" in artifact["blockers"]


def test_serial_handoff_cli_rejects_missing_stack_without_autofix(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_pl_ce_serial_handoff import main

    activation_path = tmp_path / "activation.json"
    metadata_path = tmp_path / "current-metadata.json"
    output_path = tmp_path / "serial-handoff.json"
    activation_path.write_text(
        json.dumps(_activation_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(_current_metadata_freshness_pack(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--activation-review-manifest",
            str(activation_path),
            "--current-metadata-freshness-pack",
            str(metadata_path),
            "--queue-json",
            str(tmp_path / "missing-queue.json"),
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert artifact["status"] == "blocked"
    assert "queue_metadata.missing" in artifact["blockers"]
    assert artifact["queue_metadata_valid"] is False
    assert artifact["autofix_attempted"] is False


def test_serial_handoff_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_serial_handoff.py"),
        Path("app/composition/accurate_intake_pl_ce_serial_handoff_metadata.py"),
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


def test_ci_keeps_serial_handoff_artifact_out_of_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "accurate_intake_pl_ce_merge_queue_metadata" not in workflow
    assert "--queue-json" not in workflow
    assert "--allow-blocked" not in workflow
    assert "build_accurate_intake_pl_ce_serial_handoff.py" not in workflow
    assert "--current-metadata-freshness-pack" not in workflow
    assert "accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json" not in workflow
    assert "accurate_intake_pl_ce_serial_handoff_ci.json" not in workflow
