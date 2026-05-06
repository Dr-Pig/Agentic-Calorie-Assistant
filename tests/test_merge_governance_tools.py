from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.merge_governance import (
    check_pre_queue_readiness,
    check_pr_contract_drift,
    check_pr_size_budget,
    check_sidecar_activation,
    check_track_report,
    simulate_merge_candidate,
)


def test_check_track_report_cli_fails_missing_required_fields(tmp_path: Path, capsys) -> None:
    body = tmp_path / "body.txt"
    body.write_text("track: BodyBudgetCalibration\n", encoding="utf-8")

    assert check_track_report.main(["--body-file", str(body)]) == 1

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "fail"
    assert "runtime_truth_changed" in output["missing"]


def test_check_pr_contract_drift_cli_detects_legacy_calibration_gate(tmp_path: Path, capsys) -> None:
    text = tmp_path / "diff.txt"
    text.write_text('assert "calibration_router" not in source\n', encoding="utf-8")

    assert check_pr_contract_drift.main(["--text-file", str(text)]) == 1

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "fail"
    assert output["findings"] == ["legacy_calibration_unmounted_route_gate"]


def test_check_pr_contract_drift_allows_private_router_rejection(tmp_path: Path, capsys) -> None:
    text = tmp_path / "diff.txt"
    text.write_text(
        'assert "from app.composition.calibration_routes import router as calibration_router" not in source\n',
        encoding="utf-8",
    )

    assert check_pr_contract_drift.main(["--text-file", str(text)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "pass"
    assert output["findings"] == []


def test_check_pr_size_budget_cli_reports_future_shadow_warning(tmp_path: Path, capsys) -> None:
    pr_json = tmp_path / "pr.json"
    pr_json.write_text(
        json.dumps(
            {
                "title": "Add long-term context shadow lab",
                "headRefName": "codex/long-term-context-shadow-lab",
                "body": "track: LongTermContextLab",
                "additions": 12042,
                "files": [{"path": "app/memory/application/long_term_context_shadow_lab.py", "additions": 12042}],
            }
        ),
        encoding="utf-8",
    )

    assert check_pr_size_budget.main(["--pr-json", str(pr_json)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["fat_file_status"] == "warning"
    assert output["findings"] == ["future_shadow_additions_over_budget:12042"]


def test_check_pr_size_budget_cli_accepts_string_file_entries(tmp_path: Path, capsys) -> None:
    pr_json = tmp_path / "pr.json"
    pr_json.write_text(
        json.dumps(
            {
                "title": "Add long-term context shadow lab",
                "headRefName": "codex/long-term-context-shadow-lab",
                "body": "track: LongTermContextLab",
                "additions": 12042,
                "files": ["app\\memory\\application\\long_term_context_shadow_lab.py"],
            }
        ),
        encoding="utf-8",
    )

    assert check_pr_size_budget.main(["--pr-json", str(pr_json)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["fat_file_status"] == "warning"


def test_check_sidecar_activation_cli_fails_forbidden_future_flag(tmp_path: Path, capsys) -> None:
    pr_json = tmp_path / "pr.json"
    pr_json.write_text(
        json.dumps(
            {
                "title": "Add proactive no-send shadow evaluator",
                "headRefName": "codex/proactive-no-send-shadow",
                "body": "\n".join(
                    [
                        "track: ProactiveShadow",
                        "runtime_truth_changed: true",
                        "manager_context_packet_changed: false",
                        "mutation_changed: false",
                        "product_readiness_claimed: false",
                    ]
                ),
                "files": [{"path": "app/runtime/application/proactive_no_send_shadow_evaluator.py", "additions": 20}],
            }
        ),
        encoding="utf-8",
    )

    assert check_sidecar_activation.main(["--pr-json", str(pr_json)]) == 1

    output = json.loads(capsys.readouterr().out)
    assert output["boundary_status"] == "fail"
    assert output["runtime_activation_status"] == "active"
    assert output["findings"] == ["forbidden_future_runtime_effect:runtime_truth_changed"]


def test_check_sidecar_activation_cli_accepts_string_file_entries(tmp_path: Path, capsys) -> None:
    pr_json = tmp_path / "pr.json"
    pr_json.write_text(
        json.dumps(
            {
                "title": "Add proactive runtime route",
                "headRefName": "codex/proactive-no-send-shadow",
                "body": "track: ProactiveShadow\nruntime_truth_changed: false\nmanager_context_packet_changed: false\nmutation_changed: false\nproduct_readiness_claimed: false\n",
                "files": ["app\\routes.py"],
            }
        ),
        encoding="utf-8",
    )

    assert check_sidecar_activation.main(["--pr-json", str(pr_json)]) == 1

    output = json.loads(capsys.readouterr().out)
    assert output["boundary_status"] == "fail"
    assert output["runtime_activation_status"] == "active"


def test_pre_queue_readiness_passes_current_product_pages_artifact_chain(tmp_path: Path, capsys) -> None:
    output = tmp_path / "pre-queue.json"

    assert check_pre_queue_readiness.main(["--output", str(output)]) == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["checked_job"] == "product-pages-browser-e2e"
    assert report["blockers"] == []
    assert json.loads(capsys.readouterr().out)["status"] == "pass"


def test_pre_queue_readiness_fails_pull_request_missing_required_report(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"body": "track: FoodDB\n"}}), encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--event-file", str(event), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert "missing_track_report_key:runtime_truth_changed" in report["blockers"]


def test_pre_queue_readiness_fails_missing_product_pages_dry_run_command(
    tmp_path: Path,
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    prefix, marker, suffix = workflow.partition("  product-pages-browser-e2e:")
    suffix = suffix.replace(
        "          python scripts/build_accurate_intake_context_live_diagnostic_dry_run_evaluator.py "
        "--matrix-json artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json "
        "--output artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json\n",
        "",
        1,
    )
    workflow = prefix + marker + suffix
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert "missing_product_pages_command.context_live_diagnostic_dry_run_evaluator" in report["blockers"]
    assert "missing_activation_manifest_input.context_live_diagnostic_dry_run_evaluator" not in report["blockers"]


def test_pre_queue_readiness_fails_missing_response_contract_upload(tmp_path: Path) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = workflow.replace(
        "            artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json\n",
        "",
        1,
    )
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert "missing_product_pages_upload_artifact.context_live_response_contract_dry_run" in report[
        "blockers"
    ]


def test_pre_queue_readiness_fails_missing_context_live_gate_chain_link(tmp_path: Path) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = workflow.replace(
        "          python scripts/run_accurate_intake_context_live_diagnostic_gate.py "
        "--artifact-dir artifacts --output artifacts/accurate_intake_context_live_diagnostic_gate_ci.json\n",
        "",
        1,
    ).replace(
        "            --artifact context_live_diagnostic_gate="
        "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json \\\n",
        "",
        1,
    ).replace(
        "            artifacts/accurate_intake_context_live_diagnostic_gate_ci.json\n",
        "",
        1,
    )
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert "missing_product_pages_command.context_live_diagnostic_gate" in report["blockers"]
    assert "missing_activation_manifest_input.context_live_diagnostic_gate" in report["blockers"]
    assert "missing_product_pages_upload_artifact.context_live_diagnostic_gate" in report["blockers"]


def test_pre_queue_readiness_fails_missing_product_pages_self_use_flow_gate(
    tmp_path: Path,
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = workflow.replace(
        "          python scripts/build_accurate_intake_pl_ce_product_pages_self_use_flow_gate.py \\\n",
        "",
        1,
    ).replace(
        "            artifacts/accurate_intake_pl_ce_product_pages_self_use_flow_gate_ci.json\n",
        "",
        1,
    )
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert (
        "missing_product_pages_command.pl_ce_product_pages_self_use_flow_gate"
        in report["blockers"]
    )
    assert (
        "missing_product_pages_upload_artifact.pl_ce_product_pages_self_use_flow_gate"
        in report["blockers"]
    )


def test_pre_queue_readiness_fails_missing_long_session_navigation_smoke(
    tmp_path: Path,
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = workflow.replace(
        "          python scripts/run_accurate_intake_product_pages_long_session_navigation_smoke.py "
        "--require-browser-execution --output "
        "artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json "
        "--timeout-ms 25000\n",
        "",
        1,
    ).replace(
        "            --artifact product_pages_long_session_navigation_smoke="
        "artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json \\\n",
        "",
        1,
    ).replace(
        "            artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json\n",
        "",
        1,
    )
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert (
        "missing_product_pages_command.product_pages_long_session_navigation_smoke"
        in report["blockers"]
    )
    assert (
        "missing_product_pages_upload_artifact.product_pages_long_session_navigation_smoke"
        in report["blockers"]
    )
    assert (
        "missing_current_metadata_input.product_pages_long_session_navigation_smoke"
        in report["blockers"]
    )


def test_pre_queue_readiness_fails_missing_ui_context_alignment_current_metadata_input(
    tmp_path: Path,
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    metadata_input = (
        "            --artifact pl_ce_ui_context_alignment_pack="
        "artifacts/accurate_intake_pl_ce_ui_context_alignment_pack_ci.json \\\n"
    )
    prefix, marker, suffix = workflow.rpartition(metadata_input)
    assert marker == metadata_input
    workflow = prefix + suffix
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert (
        "missing_current_metadata_input.pl_ce_ui_context_alignment_pack"
        in report["blockers"]
    )


def test_pre_queue_readiness_fails_missing_current_metadata_freshness_pack(
    tmp_path: Path,
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = workflow.replace(
        "          python scripts/build_accurate_intake_pl_ce_current_metadata_freshness_pack.py \\\n",
        "",
        1,
    ).replace(
        "            --current-metadata-freshness-pack "
        "artifacts/accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json \\\n",
        "",
        1,
    ).replace(
        "            artifacts/accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json\n",
        "",
        1,
    )
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert (
        "missing_product_pages_command.pl_ce_current_metadata_freshness_pack"
        in report["blockers"]
    )
    assert (
        "missing_product_pages_upload_artifact.pl_ce_current_metadata_freshness_pack"
        in report["blockers"]
    )
    assert (
        "missing_serial_handoff_input.current_metadata_freshness_pack"
        in report["blockers"]
    )


def test_pre_queue_readiness_fails_product_pages_chain_order_drift(tmp_path: Path) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    provider_line = (
        "          python scripts/build_accurate_intake_context_live_provider_input_preflight.py "
        "--matrix-json artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json "
        "--anti-overfit-json artifacts/accurate_intake_context_live_diagnostic_anti_overfit_guard_ci.json "
        "--output artifacts/accurate_intake_context_live_provider_input_preflight_ci.json\n"
    )
    response_line = (
        "          python scripts/build_accurate_intake_context_live_response_contract_dry_run.py "
        "--provider-input-preflight-json "
        "artifacts/accurate_intake_context_live_provider_input_preflight_ci.json "
        "--output artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json\n"
    )
    workflow = workflow.replace(provider_line + response_line, response_line + provider_line, 1)
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(workflow, encoding="utf-8")

    assert (
        check_pre_queue_readiness.main(
            ["--workflow-file", str(workflow_path), "--output", str(tmp_path / "out.json")]
        )
        == 1
    )

    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert "product_pages_context_live_artifact_chain_order_invalid" in report["blockers"]


def test_simulate_merge_candidate_uses_temp_worktree_and_runs_gates(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []
    removals: list[list[str]] = []
    removed_dirs: list[Path] = []

    def fake_run(command: list[str], *, cwd: Path) -> dict[str, object]:
        calls.append((command, cwd))
        return {"command": command, "exit_code": 0, "output": ""}

    monkeypatch.setattr(simulate_merge_candidate, "_run", fake_run)
    monkeypatch.setattr(
        simulate_merge_candidate.subprocess,
        "run",
        lambda command, **_kwargs: removals.append(command) or SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        simulate_merge_candidate.shutil,
        "rmtree",
        lambda path, ignore_errors=True: removed_dirs.append(Path(path)),
    )

    report = simulate_merge_candidate.simulate(
        pr_head="codex/merge-governance-toolkit",
        main_branch="main",
        gate_commands=[["python", "scripts/check_runtime_boundaries.py"]],
    )

    assert report["status"] == "pass"
    assert calls[0][0][:3] == ["git", "worktree", "add"]
    assert calls[1][0] == ["git", "merge", "--no-commit", "--no-ff", "origin/codex/merge-governance-toolkit"]
    assert calls[2][0] == ["python", "scripts/check_runtime_boundaries.py"]
    assert removals[0][:3] == ["git", "worktree", "remove"]
    assert removed_dirs
