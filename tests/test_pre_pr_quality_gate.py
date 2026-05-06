from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

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


def test_cli_writes_report_for_empty_head_diff(tmp_path: Path) -> None:
    output = tmp_path / "pre_pr_quality_gate_report.json"

    assert main(["--base-ref", "HEAD", "--head-ref", "HEAD", "--output", str(output), "--skip-boundary-checks"]) == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["changed_file_count"] == 0


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
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "pass"
