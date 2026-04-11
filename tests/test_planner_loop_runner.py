from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts import run_planner_loop_v1 as runner


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_planner_loop_v1.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_repo(tmp_path: Path, active_task_id: str = "TASK-AAA") -> Path:
    _write(
        tmp_path / "docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md",
        f"""# Current Execution Plan

## Active Task Artifacts

- [Task](C:/tmp/docs/exec-plans/active/tasks/{active_task_id}.md)

## Current Bounded Wave

- `{active_task_id}`
""",
    )
    _write(
        tmp_path / "scripts/check_layer_integrity.py",
        "print('layer-ok')\n",
    )
    _write(
        tmp_path / "scripts/check_fat_files.ps1",
        "Write-Output 'fat-ok'\nexit 0\n",
    )
    _write(
        tmp_path / "scripts/check_task_checkin_and_handoff.ps1",
        "Write-Output 'checkin-ok'\nexit 0\n",
    )
    return tmp_path


def _task_text(
    task_id: str,
    *,
    status: str = "ACTIVE",
    planned_touch_files: list[str] | None = None,
    forbidden_files: list[str] | None = None,
    tests_to_run: list[str] | None = None,
    extra: str = "",
) -> str:
    planned_touch_files = planned_touch_files or ["app/application/example.py"]
    forbidden_files = forbidden_files or ["app/routes.py"]
    tests_to_run = tests_to_run or ['python -c "print(\'task-test\')"']
    planned = "\n".join(f"- `{item}`" for item in planned_touch_files)
    forbidden = "\n".join(f"- `{item}`" for item in forbidden_files)
    tests = "\n".join(f"- `{item}`" for item in tests_to_run)
    return f"""# Task Artifact

- `task_id`: `{task_id}`
- `slice_id`: `slice-x`
- `status`: `{status}`
- `owner`: `delegated-worker`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [truth](C:/tmp/docs/spec.md)

## Goal

bounded task

## Planned Touch Files

{planned}

## Forbidden Files

{forbidden}

## Tests To Run

{tests}
{extra}
"""


def _run(repo: Path, *args: str, env: dict[str, str] | None = None) -> dict[str, object]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=merged_env,
    )
    return json.loads(result.stdout.strip())


def _worker_payload(*, needs_followup: bool = False, proposed_task_status: str = "COMPLETED") -> str:
    return json.dumps(
        {
            "changed_files": ["app/application/example.py"],
            "attempted_actions": ["implemented bounded change"],
            "tests_run": ["python -c \"print('task-test')\""],
            "known_risks": [],
        }
    )


def _reviewer_payload(*, approved: bool = True, needs_followup: bool = False) -> str:
    return json.dumps(
        {
            "approved": approved,
            "issues": [] if approved else ["boundary drift"],
            "known_risks": [],
        }
    )


def _python_print_cmd(payload: str) -> str:
    escaped = payload.replace("{", "{{").replace("}", "}}").replace('"', '\\"')
    return f'python -c "print(\\"{escaped}\\")"'


def _write_payload_stub(repo: Path, name: str, payload: str) -> Path:
    stub = repo / f"{name}.py"
    escaped = payload.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    _write(stub, f'print("""{escaped}""")\n')
    return stub


def test_metadata_failure_returns_replan_required(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo / "docs/exec-plans/active/tasks/TASK-BAD.md", "# Task Artifact\n")
    payload = _run(repo, "--task-id", "TASK-BAD")
    assert payload["status"] == "REPLAN_REQUIRED"
    assert payload["summary_path"]

    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "TASK_METADATA_INVALID"


def test_non_executable_tests_to_run_entry_returns_replan(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path, active_task_id="TASK-BAD-TEST")
    _write(
        repo / "docs/exec-plans/active/tasks/TASK-BAD-TEST.md",
        _task_text(
            "TASK-BAD-TEST",
            tests_to_run=["python -m pytest tests/test_example.py -q only if needed"],
        ),
    )
    payload = _run(repo, "--task-id", "TASK-BAD-TEST")
    assert payload["status"] == "REPLAN_REQUIRED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "TASK_METADATA_INVALID"


def test_blocked_task_followup_outside_wave_returns_replan(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path, active_task_id="TASK-BLOCKED")
    _write(
        repo / "docs/exec-plans/active/tasks/TASK-BLOCKED.md",
        _task_text(
            "TASK-BLOCKED",
            status="BLOCKED",
            extra="""

## Blocked Record

- `followup_task_ids[]`:
  - `TASK-NEXT`
""",
        ),
    )
    _write(repo / "docs/exec-plans/active/tasks/TASK-NEXT.md", _task_text("TASK-NEXT"))
    payload = _run(repo, "--task-id", "TASK-BLOCKED")

    assert payload["status"] == "REPLAN_REQUIRED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "FOLLOWUP_NOT_ALLOWED"


def test_worker_schema_invalid_returns_replan(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo / "docs/exec-plans/active/tasks/TASK-AAA.md", _task_text("TASK-AAA"))
    stub = _write_payload_stub(repo, "worker_invalid_stub", json.dumps({"changed_files": []}))
    payload = _run(
        repo,
        "--task-id",
        "TASK-AAA",
        "--allow-delegation",
        env={
            "PLANNER_LOOP_WORKER_CMD_TEMPLATE": f'python "{stub}"',
        },
    )

    assert payload["status"] == "REPLAN_REQUIRED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "WORKER_RESULT_INVALID"


def test_codex_unavailable_maps_to_replan_reason(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo / "docs/exec-plans/active/tasks/TASK-AAA.md", _task_text("TASK-AAA"))
    payload = _run(
        repo,
        "--task-id",
        "TASK-AAA",
        "--allow-delegation",
        env={
            "PLANNER_LOOP_WORKER_CMD_TEMPLATE": 'python -c "import sys; sys.stderr.write(\\"Missing optional dependency @openai/codex-win32-x64. Reinstall Codex\\"); sys.exit(1)"',
        },
    )

    assert payload["status"] == "REPLAN_REQUIRED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "CODEX_UNAVAILABLE"


def test_hard_completion_requirements_block_completed_status(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo / "docs/exec-plans/active/tasks/TASK-AAA.md", _task_text("TASK-AAA", status="COMPLETED"))
    payload = _run(repo, "--task-id", "TASK-AAA")

    assert payload["status"] == "REPLAN_REQUIRED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "COMPLETION_INCOMPLETE"
    assert "missing completed_at" in summary["completion_issues"]


def test_ui_task_hits_post_completion_human_gate(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(
        repo / "docs/exec-plans/active/tasks/TASK-UI.md",
        _task_text(
            "TASK-UI",
            status="COMPLETED",
            planned_touch_files=["app/web/today_routes.py"],
            extra="""

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/web/today_routes.py`
- `tests_run[]`:
  - `python -c "print('task-test')"`
- `source_of_truth_updated`: `no`
- `handoff_doc_path`: `docs/handoff/active/HANDOFF-TASK-UI.md`
""",
        ),
    )
    _write(
        repo / "docs/handoff/active/HANDOFF-TASK-UI.md",
        """# Handoff

- `current_status`: `ACTIVE`

## Blockers

- none

## Next Recommended Action

- manual review
""",
    )
    payload = _run(repo, "--task-id", "TASK-UI")

    assert payload["status"] == "HUMAN_GATE_REQUIRED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["replan_reason_code"] == "HUMAN_GATE_POST_COMPLETION"


def test_non_ui_task_with_surface_word_does_not_hit_human_gate(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(
        repo / "docs/exec-plans/active/tasks/TASK-NON-UI.md",
        _task_text(
            "TASK-NON-UI",
            status="COMPLETED",
            planned_touch_files=["app/search/tavily_adapter.py"],
            extra="""

## Goal

tighten adapter surface without changing UI

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/search/tavily_adapter.py`
- `tests_run[]`:
  - `python -c "print('task-test')"`
- `source_of_truth_updated`: `no`
- `handoff_doc_path`: `docs/handoff/active/HANDOFF-TASK-NON-UI.md`
""",
        ),
    )
    _write(
        repo / "docs/handoff/active/HANDOFF-TASK-NON-UI.md",
        """# Handoff

- `current_status`: `COMPLETED`

## Blockers

## Next Recommended Action

- archive
""",
    )
    payload = _run(repo, "--task-id", "TASK-NON-UI")

    assert payload["status"] == "COMPLETED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["status"] == "COMPLETED"


def test_completed_task_archives_after_green_checks(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(
        repo / "docs/exec-plans/active/tasks/TASK-DONE.md",
        _task_text(
            "TASK-DONE",
            status="COMPLETED",
            extra="""

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/example.py`
- `tests_run[]`:
  - `python -c "print('task-test')"`
- `source_of_truth_updated`: `no`
- `handoff_doc_path`: `docs/handoff/active/HANDOFF-TASK-DONE.md`
""",
        ),
    )
    _write(
        repo / "docs/handoff/active/HANDOFF-TASK-DONE.md",
        """# Handoff

- `current_status`: `COMPLETED`

## Blockers

## Next Recommended Action

- archive
""",
    )
    payload = _run(repo, "--task-id", "TASK-DONE")

    assert payload["status"] == "COMPLETED"
    summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))
    assert summary["status"] == "COMPLETED"
    assert (repo / "docs/exec-plans/completed/tasks/TASK-DONE.md").exists()
    assert (repo / "docs/handoff/completed/HANDOFF-TASK-DONE.md").exists()


def test_default_codex_exec_prefix_prefers_cmd(monkeypatch) -> None:
    monkeypatch.delenv("PLANNER_LOOP_CODEX_BIN", raising=False)
    monkeypatch.setattr(runner.shutil, "which", lambda name: "C:\\tools\\codex.cmd" if name == "codex.cmd" else None)
    assert runner.default_codex_exec_prefix() == '"C:\\tools\\codex.cmd" exec'


def test_default_codex_exec_prefix_skips_windowsapps_and_uses_winget(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PLANNER_LOOP_CODEX_BIN", raising=False)
    monkeypatch.setattr(runner.shutil, "which", lambda name: "C:\\Program Files\\WindowsApps\\OpenAI.Codex\\codex.exe" if name == "codex" else None)
    localapp = tmp_path / "LocalAppData"
    codex_cmd = localapp / "Microsoft" / "WinGet" / "Packages" / "OpenJS.NodeJS.22_Test" / "node-v22.22.2-win-x64" / "codex.cmd"
    _write(codex_cmd, "@echo off\n")
    monkeypatch.setenv("LOCALAPPDATA", str(localapp))
    assert runner.default_codex_exec_prefix() == f'"{codex_cmd}" exec'
