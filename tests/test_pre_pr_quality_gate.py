from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.merge_governance import pre_pr_quality_gate
from scripts.merge_governance.pre_pr_quality_gate import (
    ChangedFile,
    build_quality_report_from_changes,
    main,
)


ROOT = Path(__file__).resolve().parents[1]


POLICY = {
    "active_code": {
        "root": "app",
        "new_active_python_file_default_cap": 8,
        "excluded_globs": ["app/**/__pycache__/**"],
    },
    "category_caps": {
        "application_orchestration": 10,
        "boundary_surface": 6,
    },
    "category_rules": [
        {"pattern": "app/composition/*.py", "category": "application_orchestration"},
        {"pattern": "app/routes.py", "category": "boundary_surface"},
    ],
    "transition_overrides": {},
}


def _lines(count: int) -> str:
    return "\n".join(f"line_{index}" for index in range(count))


def _blocker_codes(report: dict[str, object]) -> set[str]:
    return {str(item["code"]) for item in report["blockers"]}  # type: ignore[index]


def _event_file(tmp_path: Path, body: str) -> Path:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"body": body}}), encoding="utf-8")
    return event


def test_new_active_python_file_over_cap_fails() -> None:
    report = build_quality_report_from_changes(
        [
            ChangedFile(
                path="app/composition/new_gate.py",
                status="A",
                old_text=None,
                new_text=_lines(9),
            )
        ],
        policy=POLICY,
        track="FoodDB",
        run_boundary_checks=False,
    )

    assert report["status"] == "fail"
    assert "new_active_python_file_over_cap" in _blocker_codes(report)


def test_existing_over_cap_file_cannot_grow() -> None:
    report = build_quality_report_from_changes(
        [
            ChangedFile(
                path="app/composition/existing_gate.py",
                status="M",
                old_text=_lines(12),
                new_text=_lines(13),
            )
        ],
        policy=POLICY,
        track="PLCE",
        run_boundary_checks=False,
    )

    assert report["status"] == "fail"
    assert "active_file_grew_over_target_cap" in _blocker_codes(report)


def test_changed_file_crossing_effective_cap_fails() -> None:
    report = build_quality_report_from_changes(
        [
            ChangedFile(
                path="app/composition/crossing_gate.py",
                status="M",
                old_text=_lines(10),
                new_text=_lines(11),
            )
        ],
        policy=POLICY,
        track="FoodDB",
        run_boundary_checks=False,
    )

    assert report["status"] == "fail"
    assert "active_file_crossed_effective_cap" in _blocker_codes(report)


def test_untouched_existing_fat_file_does_not_block_delta_gate() -> None:
    report = build_quality_report_from_changes(
        [],
        policy=POLICY,
        track="FoodDB",
        run_boundary_checks=False,
    )

    assert report["status"] == "pass"
    assert report["blockers"] == []


def test_unmapped_active_python_file_fails() -> None:
    report = build_quality_report_from_changes(
        [
            ChangedFile(
                path="app/unmapped/example.py",
                status="A",
                old_text=None,
                new_text="value = 1\n",
            )
        ],
        policy=POLICY,
        track="FoodDB",
        run_boundary_checks=False,
    )

    assert report["status"] == "fail"
    assert "active_python_file_unmapped" in _blocker_codes(report)


def test_dsa_findings_are_advisory_only() -> None:
    source = "\n".join(
        [
            "def tangled(items):",
            "    total = 0",
            "    for item in items:",
            "        if item:",
            "            for nested in item:",
            "                if nested:",
            "                    if nested > 0:",
            "                        total += nested",
            "                    else:",
            "                        total -= nested",
            "                elif nested == 0:",
            "                    total += 1",
            "            if total > 100:",
            "                break",
            "    return total",
        ]
    )
    report = build_quality_report_from_changes(
        [
            ChangedFile(
                path="app/composition/small_gate.py",
                status="M",
                old_text="def tangled(items):\n    return 0\n",
                new_text=source,
            )
        ],
        policy={**POLICY, "category_caps": {**POLICY["category_caps"], "application_orchestration": 50}},
        track="PLCE",
        run_boundary_checks=False,
    )

    assert report["status"] == "pass"
    assert report["blockers"] == []
    assert report["advisories"]


def test_future_shadow_active_surface_fails() -> None:
    report = build_quality_report_from_changes(
        [
            ChangedFile(
                path="app/routes.py",
                status="M",
                old_text=_lines(4),
                new_text=_lines(4),
            )
        ],
        policy=POLICY,
        track="LongTermContextLab",
        run_boundary_checks=False,
    )

    assert report["status"] == "fail"
    assert "future_shadow_touches_active_surface" in _blocker_codes(report)


def test_cli_infers_track_from_pull_request_event_body(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(
        tmp_path,
        "\n".join(
            [
                "track: PL_CE",
                "owner_lane: ManagerRuntime",
                "slice_class: runtime_gate",
                "pass_type: contract",
                "upstream_runtime_gate: not_applicable",
                "launch_claim_scope: current_shell_candidate_contract",
                "shell_surface_impacted: false",
                "runtime_truth_changed: false",
                "manager_context_packet_changed: false",
                "mutation_changed: false",
                "product_readiness_claimed: false",
                "non_claims: not_whole_product_mvp,not_private_self_use_approved,not_live_provider_ready",
            ]
        ),
    )

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["track"] == "PLCE"
    assert report["status"] == "pass"


def test_cli_explicit_track_overrides_event_track(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: LongTermContextLab\n")

    assert (
        main(
            [
                "--track",
                "FoodDB",
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["track"] == "FoodDB"


def test_cli_normalizes_fooddb_websearch_track_alias(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: FoodDB_WebSearch\n")

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["track"] == "FoodDB"


def test_cli_allows_merge_governance_track(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: MergeGovernance\n")

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["track"] == "MergeGovernance"


def test_cli_normalizes_governance_track_alias(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: GovernanceGuard\n")

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["track"] == "MergeGovernance"


def test_cli_unknown_declared_track_fails(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: FoodDBWebSearchAndPLCE\n")

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 1
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert "unknown_or_noncanonical_track" in _blocker_codes(report)


def test_cli_uses_github_event_path_env_by_default(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: FoodDB\n")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["track"] == "FoodDB"


def test_cli_event_inferred_future_shadow_track_blocks_active_surface(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(tmp_path, "track: LongTermContextLab\n")

    monkeypatch.setattr(
        pre_pr_quality_gate,
        "collect_changed_files",
        lambda *, base_ref, head_ref: [
            ChangedFile(path="app/routes.py", status="M", old_text=_lines(4), new_text=_lines(4))
        ],
    )
    monkeypatch.setattr(pre_pr_quality_gate, "load_active_code_policy", lambda: POLICY)

    assert (
        pre_pr_quality_gate.main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
    )
        == 1
    )


def test_plce_track_requires_current_shell_metadata(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(
        tmp_path,
        "\n".join(
            [
                "track: PLCE",
                "runtime_truth_changed: false",
                "manager_context_packet_changed: false",
                "mutation_changed: false",
                "product_readiness_claimed: false",
            ]
        ),
    )

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 1
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert "missing_current_shell_metadata:owner_lane" in _blocker_codes(report)


def test_plce_contract_claim_without_runtime_claim_fields_is_advisory_only(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(
        tmp_path,
        "\n".join(
            [
                "track: PLCE",
                "owner_lane: ManagerRuntime",
                "slice_class: runtime_gate",
                "pass_type: contract",
                "upstream_runtime_gate: not_applicable",
                "launch_claim_scope: current_shell_candidate_contract",
                "shell_surface_impacted: false",
                "runtime_truth_changed: false",
                "manager_context_packet_changed: false",
                "mutation_changed: false",
                "product_readiness_claimed: false",
                "non_claims: not_whole_product_mvp,not_private_self_use_approved,not_live_provider_ready",
            ]
        ),
    )

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    advisory_codes = {str(item["code"]) for item in report["advisories"]}  # type: ignore[index]
    assert "advisory_missing_current_shell_metadata:journeys_touched" in advisory_codes
    assert "advisory_missing_current_shell_metadata:visible_fact_provenance" in advisory_codes


def test_plce_appshell_runtime_claim_requires_green_gate(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    event = _event_file(
        tmp_path,
        "\n".join(
            [
                "track: PLCE",
                "owner_lane: AppShell",
                "slice_class: appshell_browser",
                "pass_type: browser_executed",
                "upstream_runtime_gate: bootstrap_no_plan_runtime_gate",
                "launch_claim_scope: current_shell_candidate_browser",
                "shell_surface_impacted: true",
                "runtime_truth_changed: false",
                "manager_context_packet_changed: false",
                "mutation_changed: false",
                "product_readiness_claimed: false",
                "journeys_touched: A,J",
                "visible_fact_provenance: read_model,guard,trace",
                "non_claims: not_whole_product_mvp,not_private_self_use_approved,not_live_provider_ready",
            ]
        ),
    )

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--event-file",
                str(event),
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 1
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert "appshell_runtime_claim_requires_green_gate:bootstrap_no_plan_runtime_gate" in _blocker_codes(report)


def test_cli_writes_report_for_empty_head_diff(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"

    assert (
        main(
            [
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--output",
                str(output),
                "--skip-boundary-checks",
                "--allow-dirty-worktree",
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["changed_file_count"] == 0


def test_cli_dirty_worktree_fails_pre_pr_gate(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"
    monkeypatch.setattr(pre_pr_quality_gate, "collect_changed_files", lambda *, base_ref, head_ref: [])
    monkeypatch.setattr(pre_pr_quality_gate, "load_active_code_policy", lambda: POLICY)
    monkeypatch.setattr(
        pre_pr_quality_gate,
        "working_tree_status_entries",
        lambda: [" M app/example.py", "?? scratch.txt"],
    )

    assert (
        pre_pr_quality_gate.main(
            [
                "--track",
                "FoodDB",
                "--base-ref",
                "HEAD",
                "--head-ref",
                "HEAD",
                "--output",
                str(output),
                "--skip-boundary-checks",
            ]
        )
        == 1
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert "dirty_worktree" in _blocker_codes(report)


def test_script_path_execution_can_import_repo_modules(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/merge_governance/pre_pr_quality_gate.py",
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
            "--output",
            str(output),
            "--skip-boundary-checks",
            "--allow-dirty-worktree",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "pass"
