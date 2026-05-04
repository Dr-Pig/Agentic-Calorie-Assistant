from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.merge_governance import (
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
