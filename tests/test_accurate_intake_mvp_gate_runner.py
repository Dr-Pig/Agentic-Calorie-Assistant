from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import verify_accurate_intake_mvp


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "quality" / "accurate_intake_mvp_gate_manifest.json"


def test_accurate_intake_mvp_gate_manifest_declares_local_deterministic_scope() -> None:
    manifest = verify_accurate_intake_mvp.load_gate_manifest(MANIFEST_PATH)

    assert manifest["gate_id"] == "accurate_intake_mvp_deterministic_v1"
    assert manifest["gate_version"] == "1.3"
    assert manifest["claim_scope"] == "local_deterministic_mvp_gate"
    assert manifest["evidence_scope"] == "deterministic_regression_evidence"
    assert manifest["live_llm_required"] is False
    assert manifest["web_tavily_required"] is False
    assert manifest["schema_migration_required"] is False
    assert {
        "product_ready",
        "rollout_ready",
        "live_llm_ready",
        "web_ready",
        "production_db_ready",
    } <= set(manifest["not_claiming"])
    assert set(manifest["forbidden_claims"]) == set(manifest["not_claiming"])
    assert manifest["next_promotion_criteria"] == [
        "phase_c_gate_pass",
        "accurate_intake_mvp_gate_pass",
        "food_knowledge_required_group_pass",
        "local_persistence_debug_surface_required_group_pass",
    ]
    assert manifest["semantic_owner"]["food_knowledge"] == "evidence_support_only"
    assert manifest["llm_deterministic_boundary"]["truth_owner"] == "deterministic"


def test_gate_plan_groups_required_mvp_regression_surfaces() -> None:
    manifest = verify_accurate_intake_mvp.load_gate_manifest(MANIFEST_PATH)
    plan = verify_accurate_intake_mvp.build_gate_plan(manifest, python_executable="python")

    group_ids = [group.group_id for group in plan.groups]
    assert group_ids == [
        "turn2_replay_coverage",
        "multi_turn_context",
        "correction_and_no_plan",
        "ledger_truth_and_read_model",
        "food_knowledge_mvp",
        "local_persistence_and_debug_surface",
    ]
    flat_args = " ".join(arg for group in plan.groups for command in group.commands for arg in command)
    for expected_test in (
        "tests/test_turn2_mvp_ux_coverage.py",
        "tests/test_accurate_intake_mvp_regression_wall.py",
        "tests/test_correction_target_reference_state.py",
        "tests/test_no_plan_ledger_policy.py",
        "tests/test_budget_ledger_truth_boundary.py",
        "tests/test_phase_c_same_truth_gate.py",
        "tests/test_food_knowledge_mvp_coverage.py",
        "tests/test_product_loop_mvp_read_model.py",
        "tests/test_local_persistence_self_use.py",
        "tests/test_accurate_intake_debug_surface.py",
    ):
        assert expected_test in flat_args


def test_gate_plan_has_no_optional_mvp_groups_after_food_knowledge_promotion() -> None:
    manifest = verify_accurate_intake_mvp.load_gate_manifest(MANIFEST_PATH)

    default_plan = verify_accurate_intake_mvp.build_gate_plan(manifest, python_executable="python")
    optional_plan = verify_accurate_intake_mvp.build_gate_plan(
        manifest,
        python_executable="python",
        include_optional=True,
    )

    assert "food_knowledge_mvp" in [group.group_id for group in default_plan.groups]
    assert "food_knowledge_mvp" in [group.group_id for group in optional_plan.groups]
    assert optional_plan.included_optional_groups == ()
    food_group = next(group for group in default_plan.groups if group.group_id == "food_knowledge_mvp")
    assert food_group.requirement == "required"
    assert "tests/test_food_knowledge_mvp_coverage.py" in " ".join(food_group.commands[0])


def test_gate_runner_returns_machine_readable_group_summary(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(verify_accurate_intake_mvp.subprocess, "run", fake_run)

    exit_code = verify_accurate_intake_mvp.main(["--python", "python"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "pass"
    assert output["gate_id"] == "accurate_intake_mvp_deterministic_v1"
    assert output["claim_scope"] == "local_deterministic_mvp_gate"
    assert output["not_claiming"]
    assert [group["group_id"] for group in output["groups"]] == [
        "turn2_replay_coverage",
        "multi_turn_context",
        "correction_and_no_plan",
        "ledger_truth_and_read_model",
        "food_knowledge_mvp",
        "local_persistence_and_debug_surface",
    ]
    assert {group["requirement"] for group in output["groups"]} == {"required"}
    assert len(calls) == 6


def test_gate_runner_writes_artifact_output(monkeypatch, tmp_path, capsys) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(verify_accurate_intake_mvp.subprocess, "run", fake_run)
    output_path = tmp_path / "accurate_intake_mvp_gate.json"

    exit_code = verify_accurate_intake_mvp.main(
        [
            "--python",
            "python",
            "--include-optional",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "pass"
    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["included_optional_groups"] == []
    assert all(group["requirement"] == "required" for group in artifact["groups"])
    assert "food_knowledge_mvp" in [group["group_id"] for group in artifact["groups"]]


def test_gate_runner_fails_fast_by_default_and_reports_failed_group(monkeypatch, capsys) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if "tests/test_accurate_intake_mvp_regression_wall.py" in command:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed\n")
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(verify_accurate_intake_mvp.subprocess, "run", fake_run)

    exit_code = verify_accurate_intake_mvp.main(["--python", "python"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["status"] == "fail"
    assert [group["group_id"] for group in output["groups"]] == [
        "turn2_replay_coverage",
        "multi_turn_context",
    ]
    assert output["groups"][-1]["returncode"] == 1


def test_ci_has_independent_accurate_intake_mvp_gate_job() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "accurate-intake-mvp-gate:" in workflow
    assert "python scripts/verify_accurate_intake_mvp.py --python python" in workflow
    assert "--output artifacts/accurate_intake_mvp_gate.json" in workflow
    assert "accurate-intake-mvp-gate-report" in workflow
