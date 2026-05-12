from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/build_advanced_product_lab_live_edd_decision_pack.py"
PLAN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_memory_live_edd_pr_train.yaml"


def test_live_edd_decision_pack_closes_lab_without_mainline_activation() -> None:
    from app.advanced_shadow_lab.product_lab_live_edd_decision_pack import (
        build_live_edd_decision_pack,
    )

    pack = build_live_edd_decision_pack(
        pr_train=_pr_train(),
        diagnostic_artifacts=_all_live_diagnostics(),
        failure_taxonomy_report=_failure_taxonomy(),
        activation_wall_audit=_activation_wall(),
    )

    assert pack["artifact_type"] == "advanced_product_lab_live_edd_decision_pack"
    assert pack["status"] == "pass"
    assert pack["lab_enabled"] is True
    assert pack["lab_live_edd_complete"] is True
    assert pack["ready_for_lab_dogfood_feedback"] is True
    assert pack["ready_for_mainline_activation"] is False
    assert pack["mainline_activation_enabled"] is False
    assert pack["mainline_runtime_connected"] is False
    assert pack["self_use_v1_affected"] is False
    assert pack["durable_product_memory_written"] is False
    assert pack["canonical_product_mutation_allowed"] is False
    assert pack["production_scheduler_delivery_allowed"] is False
    assert pack["kimi_live_calls_allowed"] is False
    assert pack["dynamic_estimate"]["remaining_pr_count_before_this_pr"] == 1
    assert pack["dynamic_estimate"]["remaining_pr_count_after_pr14_merge"] == 0
    assert pack["milestone_statuses"] == {
        "grokfast_extraction_diagnostic": "satisfied_live_grokfast",
        "memory_tool_lookup_diagnostic": "satisfied_live_grokfast",
        "recommendation_with_blockers": "satisfied_live_grokfast",
        "rescue_memory_context_diagnostic": "satisfied_live_grokfast",
        "proactive_feedback_projection": "satisfied_live_grokfast",
        "integrated_e2e_lab_loop": "satisfied_live_grokfast",
        "failure_taxonomy_and_decision_pack": "satisfied_report_and_wall",
    }
    assert pack["activation_wall_regression"]["status"] == "pass"
    assert pack["blockers"] == []


def test_live_edd_decision_pack_blocks_missing_live_milestone() -> None:
    from app.advanced_shadow_lab.product_lab_live_edd_decision_pack import (
        build_live_edd_decision_pack,
    )

    diagnostics = [
        artifact
        for artifact in _all_live_diagnostics()
        if artifact["artifact_type"]
        != "advanced_product_lab_rescue_memory_context_live_diagnostic"
    ]

    pack = build_live_edd_decision_pack(
        pr_train=_pr_train(),
        diagnostic_artifacts=diagnostics,
        failure_taxonomy_report=_failure_taxonomy(),
        activation_wall_audit=_activation_wall(),
    )

    assert pack["status"] == "blocked"
    assert "milestone.rescue_memory_context_diagnostic.missing_or_not_satisfied" in pack[
        "blockers"
    ]
    assert pack["lab_live_edd_complete"] is False
    assert pack["ready_for_lab_dogfood_feedback"] is False
    assert pack["ready_for_mainline_activation"] is False


def test_live_edd_activation_wall_regression_passes_for_repo_root() -> None:
    from app.advanced_shadow_lab.product_lab_activation_wall_audit import (
        build_product_lab_activation_wall_audit,
    )

    audit = build_product_lab_activation_wall_audit(
        closure_pack=_closure_pack(),
        repo_root=ROOT,
    )

    assert audit["artifact_type"] == "advanced_product_lab_activation_wall_audit"
    assert audit["status"] == "pass"
    assert audit["route_mount_clear"] is True
    assert audit["scheduler_delivery_clear"] is True
    assert audit["production_db_migration_clear"] is True
    assert audit["provider_default_runtime_clear"] is True
    assert audit["mainline_activation_enabled"] is False


def test_live_edd_decision_pack_cli_roundtrip(tmp_path: Path) -> None:
    diagnostics = []
    for index, artifact in enumerate(_all_live_diagnostics(), start=1):
        path = tmp_path / f"diagnostic-{index}.json"
        write_json_artifact(path, artifact)
        diagnostics.extend(["--artifact-json", str(path)])

    failure_taxonomy_path = tmp_path / "failure-taxonomy.json"
    activation_wall_path = tmp_path / "activation-wall.json"
    output = tmp_path / "decision-pack.json"
    write_json_artifact(failure_taxonomy_path, _failure_taxonomy())
    write_json_artifact(activation_wall_path, _activation_wall())

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--pr-train-yaml",
            str(PLAN_PATH),
            *diagnostics,
            "--failure-taxonomy-json",
            str(failure_taxonomy_path),
            "--activation-wall-audit-json",
            str(activation_wall_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_pack = json.loads(result.stdout)
    file_pack = read_json_artifact(output)
    assert stdout_pack == file_pack
    assert file_pack["status"] == "pass"
    assert file_pack["dynamic_estimate"]["remaining_pr_count_after_pr14_merge"] == 0


def _pr_train() -> dict:
    plan = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))
    plan["dynamic_remaining_pr_count"] = 1
    plan["last_completed_pr_number"] = 13
    return plan


def _all_live_diagnostics() -> list[dict[str, object]]:
    return [
        _diagnostic(
            artifact_type="advanced_product_lab_memory_record_grokfast_extraction_diagnostic",
            case_suite="golden",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_memory_record_grokfast_extraction_diagnostic",
            case_suite="negative_holdout",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_memory_tool_lookup_live_diagnostic",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_memory_source_safety_holdout",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_memory_feedback_live_diagnostic",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_proactive_feedback_live_diagnostic",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_recommendation_blocker_live_diagnostic",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_rescue_memory_context_live_diagnostic",
        ),
        _diagnostic(
            artifact_type="advanced_product_lab_integrated_live_e2e",
        ),
    ]


def _diagnostic(*, artifact_type: str, case_suite: str = "") -> dict[str, object]:
    artifact: dict[str, object] = {
        "artifact_type": artifact_type,
        "status": "pass",
        "diagnostic_evidence_class": "live_grokfast",
        "live_milestone_status": "satisfied_live_grokfast",
        "live_completion_claim_allowed": True,
        "provider_profile_id": "builderspace-grok-4-fast",
        "live_invoked": True,
        "provider_invoked": True,
        "live_provider_used": True,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": [],
    }
    if case_suite:
        artifact["case_suite"] = case_suite
    return artifact


def _failure_taxonomy() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_live_failure_taxonomy",
        "status": "pass",
        "failure_count": 0,
        "unclassified_failure_count": 0,
        "summary": {},
        "milestone_statuses": {
            "advanced_product_lab_integrated_live_e2e": "satisfied_live_grokfast"
        },
        "semantic_hardening_allowed": False,
        "product_truth_changed": False,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": [],
    }


def _activation_wall() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_activation_wall_audit",
        "status": "pass",
        "route_mount_clear": True,
        "scheduler_delivery_clear": True,
        "production_db_migration_clear": True,
        "provider_default_runtime_clear": True,
        "lab_enabled": True,
        "lab_product_loop_closed": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": [],
    }


def _closure_pack() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_memory_record_closure_pack",
        "status": "pass",
        "lab_enabled": True,
        "lab_product_loop_closed": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": [],
    }
