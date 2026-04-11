from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_PLAN_PATH = Path("docs") / "exec-plans" / "active" / "CURRENT_EXECUTION_PLAN.md"
DEFAULT_LOG_DIR = REPO_ROOT / ".logs" / "planner_loop"

STATUS_COMPLETED = "COMPLETED"
STATUS_REPLAN_REQUIRED = "REPLAN_REQUIRED"
STATUS_HUMAN_GATE_REQUIRED = "HUMAN_GATE_REQUIRED"

REASON_TASK_METADATA_INVALID = "TASK_METADATA_INVALID"
REASON_BLOCKED_BY_HANDOFF = "BLOCKED_BY_HANDOFF"
REASON_WORKER_FAILED = "WORKER_FAILED"
REASON_WORKER_RESULT_INVALID = "WORKER_RESULT_INVALID"
REASON_REVIEW_REJECTED = "REVIEW_REJECTED"
REASON_VALIDATOR_FAILED = "VALIDATOR_FAILED"
REASON_FOLLOWUP_REQUIRED = "FOLLOWUP_REQUIRED"
REASON_FOLLOWUP_NOT_ALLOWED = "FOLLOWUP_NOT_ALLOWED"
REASON_CODEX_UNAVAILABLE = "CODEX_UNAVAILABLE"
REASON_COMPLETION_INCOMPLETE = "COMPLETION_INCOMPLETE"
REASON_HUMAN_GATE_PRECONDITION = "HUMAN_GATE_PRECONDITION"
REASON_HUMAN_GATE_POST_COMPLETION = "HUMAN_GATE_POST_COMPLETION"
REASON_TIMEOUT = "TIMEOUT"

EXECUTABLE_PREFIXES = ("python ", "python3 ", "py ", "powershell ", "pwsh ", "pytest ", "alembic ", "uv ")
NON_EXECUTABLE_MARKERS = ("only if", "if needed", "when needed", "optional:", "for reference", "example:")


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    attempt: int = 1


@dataclass
class Task:
    path: Path
    task_id: str
    slice_id: str
    status: str
    source_refs: list[str]
    planned_touch_files: list[str]
    forbidden_files: list[str]
    tests_to_run: list[str]
    followup_task_ids: list[str]
    handoff_doc_path: str | None
    completed_at: str | None
    actual_touch_files: list[str]
    tests_run: list[str]
    source_of_truth_updated: str | None
    raw_text: str


@dataclass
class Handoff:
    path: Path
    current_status: str
    blockers: list[str]
    next_actions: list[str]


def active_task_dir(repo_root: Path) -> Path:
    return repo_root / "docs" / "exec-plans" / "active" / "tasks"


def completed_task_dir(repo_root: Path) -> Path:
    return repo_root / "docs" / "exec-plans" / "completed" / "tasks"


def active_handoff_dir(repo_root: Path) -> Path:
    return repo_root / "docs" / "handoff" / "active"


def completed_handoff_dir(repo_root: Path) -> Path:
    return repo_root / "docs" / "handoff" / "completed"


def lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def backtick_value(text: str, key: str) -> str | None:
    m = re.search(rf"-\s+`{re.escape(key)}`:\s+`?([^\n`]+)`?", text)
    return m.group(1).strip() if m else None


def section_items(text: str, heading: str) -> list[str]:
    target = f"## {heading}"
    in_section = False
    items: list[str] = []
    for line in lines(text):
        if line.strip() == target:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and re.match(r"^\s*-\s+", line):
            items.append(re.sub(r"^\s*-\s+", "", line).strip().strip("`"))
    return items


def key_list(text: str, key: str) -> list[str]:
    needles = [f"- `{key}`:", f"- {key}:"]
    in_target = False
    out: list[str] = []
    for line in lines(text):
        stripped = line.rstrip()
        if stripped.strip() in needles:
            in_target = True
            continue
        if in_target:
            if stripped.startswith("## "):
                break
            if re.match(r"^\s*-\s+", stripped):
                out.append(re.sub(r"^\s*-\s+", "", stripped).strip().strip("`"))
            elif stripped.strip():
                break
    return out


def section_links(text: str, heading: str) -> list[str]:
    target = f"## {heading}"
    in_section = False
    body: list[str] = []
    for line in lines(text):
        if line.strip() == target:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            body.append(line)
    return [m.group(1) for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", "\n".join(body))]


def parse_task(path: Path) -> Task:
    text = path.read_text(encoding="utf-8")
    return Task(
        path=path,
        task_id=backtick_value(text, "task_id") or "",
        slice_id=backtick_value(text, "slice_id") or "",
        status=(backtick_value(text, "status") or "").upper(),
        source_refs=section_links(text, "Source Of Truth Refs"),
        planned_touch_files=section_items(text, "Planned Touch Files"),
        forbidden_files=section_items(text, "Forbidden Files"),
        tests_to_run=section_items(text, "Tests To Run"),
        followup_task_ids=key_list(text, "followup_task_ids[]"),
        handoff_doc_path=backtick_value(text, "handoff_doc_path"),
        completed_at=backtick_value(text, "completed_at"),
        actual_touch_files=key_list(text, "actual_touch_files[]"),
        tests_run=key_list(text, "tests_run[]"),
        source_of_truth_updated=backtick_value(text, "source_of_truth_updated"),
        raw_text=text,
    )


def parse_handoff(path: Path) -> Handoff:
    text = path.read_text(encoding="utf-8")
    return Handoff(
        path=path,
        current_status=(backtick_value(text, "current_status") or "").upper(),
        blockers=section_items(text, "Blockers"),
        next_actions=section_items(text, "Next Recommended Action"),
    )


def current_plan_text(repo_root: Path) -> str:
    return (repo_root / CURRENT_PLAN_PATH).read_text(encoding="utf-8")


def active_task_paths(plan_text: str) -> list[Path]:
    block = re.search(r"## Active Task Artifacts(?P<body>.*?)(?:\n## |\Z)", plan_text, re.S)
    if not block:
        return []
    return [Path(m.group(1)) for m in re.finditer(r"\[[^\]]+\]\(([^)]+/docs/exec-plans/active/tasks/[^)]+\.md)\)", block.group("body"))]


def current_wave_task_ids(plan_text: str) -> set[str]:
    return set(re.findall(r"TASK-\d{4}-\d{2}-\d{2}-\d{3}-[A-Z0-9\-]+", plan_text))


def choose_task(repo_root: Path, explicit_task_id: str | None) -> tuple[Task, dict[str, Any]]:
    plan = current_plan_text(repo_root)
    wave_ids = current_wave_task_ids(plan)
    meta: dict[str, Any] = {"selection_reason": "explicit" if explicit_task_id else "current_execution_plan", "current_wave_task_ids": sorted(wave_ids)}
    if explicit_task_id:
        task = parse_task(active_task_dir(repo_root) / f"{explicit_task_id}.md")
    else:
        paths = active_task_paths(plan)
        if not paths:
            raise RuntimeError("No active task artifacts found in CURRENT_EXECUTION_PLAN.md")
        task = parse_task(paths[0])

    if task.status == "BLOCKED" and task.followup_task_ids:
        followup_id = task.followup_task_ids[0]
        followup_path = active_task_dir(repo_root) / f"{followup_id}.md"
        if not followup_path.exists():
            meta["followup_not_allowed"] = "follow-up task file is missing"
            return task, meta
        if followup_id not in wave_ids:
            meta["followup_not_allowed"] = "follow-up task is outside current bounded wave"
            return task, meta
        followup = parse_task(followup_path)
        if pre_human_gate(followup):
            meta["followup_not_allowed"] = "follow-up task hits a human gate precondition"
            return task, meta
        meta["selection_reason"] = "followup_from_blocked_task"
        meta["blocked_task_id"] = task.task_id
        return followup, meta
    return task, meta


def metadata_issues(task: Task) -> list[str]:
    issues: list[str] = []
    if not task.task_id:
        issues.append("missing task_id")
    if not task.slice_id:
        issues.append("missing slice_id")
    if not task.status:
        issues.append("missing status")
    if not task.source_refs:
        issues.append("missing source_of_truth_refs")
    if not task.planned_touch_files:
        issues.append("missing planned_touch_files")
    if not task.forbidden_files:
        issues.append("missing forbidden_files")
    if not task.tests_to_run:
        issues.append("missing tests_to_run")
    for cmd in task.tests_to_run:
        stripped = cmd.strip()
        lowered = stripped.lower()
        if any(marker in lowered for marker in NON_EXECUTABLE_MARKERS):
            issues.append(f"non-executable tests_to_run entry: {cmd}")
            continue
        if not lowered.startswith(EXECUTABLE_PREFIXES):
            issues.append(f"unsupported tests_to_run command prefix: {cmd}")
    return issues


def pre_human_gate(task: Task) -> str | None:
    lowered = task.raw_text.lower()
    if any(k in lowered for k in ("manual review", "benchmark seed", "founder-fit", "real example")):
        return "task already declares a manual review / benchmark gate"
    return None


def post_human_gate(task: Task) -> str | None:
    touch_blob = " ".join(task.planned_touch_files).lower()
    text_blob = task.raw_text.lower()
    explicit_gate_markers = (
        "manual review",
        "ui review",
        "surface review",
        "product review",
        "interaction review",
    )
    if "app/web/" in touch_blob or "app/routes.py" in touch_blob or any(marker in text_blob for marker in explicit_gate_markers):
        return "new UI or surface requires manual review"
    if any(k in text_blob for k in ("founder-fit", "benchmark", "real example", "real-world regression")):
        return "benchmark seeds or real examples are required"
    return None


def needs_reviewer(task: Task) -> bool:
    touch_blob = " ".join(task.planned_touch_files).lower()
    return any(t in touch_blob for t in ("canonical_persistence", "current_budget_read_model", "rescue_overlay", "evidence_assembly", "evidence_normalizer", "conversation_state_assembler", "guardrail", "read_model"))


def needs_integration(task: Task) -> bool:
    touch_blob = " ".join(task.planned_touch_files).lower()
    return any(t in touch_blob for t in ("canonical_persistence", "conversation_state_assembler", "conversation_state_loader", "read_model", "evidence_assembly", "evidence_normalizer"))


def cmd_template(kind: str) -> str:
    env_name = "PLANNER_LOOP_WORKER_CMD_TEMPLATE" if kind == "worker" else "PLANNER_LOOP_REVIEWER_CMD_TEMPLATE"
    default = (
        'python scripts/run_codex_exec_with_prompt.py '
        f'--mode {kind} --cd "{{repo_root}}" --prompt-file "{{prompt_file}}"'
    )
    return os.environ.get(env_name, default)


def default_codex_exec_prefix() -> str:
    explicit = os.environ.get("PLANNER_LOOP_CODEX_BIN")
    if explicit:
        return f'"{explicit}" exec'

    direct = shutil.which("codex.cmd") or shutil.which("codex")
    if direct and direct.lower().endswith(".cmd"):
        return f'"{direct}" exec'

    if direct and "windowsapps" not in direct.lower():
        return f'"{direct}" exec'

    winget_node = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_node.exists():
        matches = sorted(winget_node.glob("OpenJS.NodeJS.*/*/codex.cmd"))
        if matches:
            return f'"{matches[-1]}" exec'

    return 'codex exec'


def timeout_seconds() -> int:
    return int(os.environ.get("PLANNER_LOOP_COMMAND_TIMEOUT_SECONDS", "600"))


def max_attempts(kind: str) -> int:
    env_name = "PLANNER_LOOP_MAX_WORKER_ATTEMPTS" if kind == "worker" else "PLANNER_LOOP_MAX_REVIEWER_ATTEMPTS"
    default = "2"
    return int(os.environ.get(env_name, default))


def run_command(command: str, cwd: Path, *, attempt: int) -> CommandResult:
    try:
        proc = subprocess.run(command, cwd=str(cwd), shell=True, capture_output=True, text=True, timeout=timeout_seconds())
        return CommandResult(command, proc.returncode, proc.stdout, proc.stderr, False, attempt)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(command, 124, exc.stdout or "", (exc.stderr or "") + f"\nTimed out after {timeout_seconds()} seconds.", True, attempt)


def run_prompted(kind: str, prompt: str, cwd: Path, log_dir: Path, prefix: str) -> CommandResult:
    log_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = log_dir / f"{prefix}_{kind}_prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    rendered = cmd_template(kind).format(prompt=prompt, prompt_file=str(prompt_file), repo_root=str(cwd))
    last: CommandResult | None = None
    for attempt in range(1, max_attempts(kind) + 1):
        last = run_command(rendered, cwd, attempt=attempt)
        if last.returncode == 0 or last.timed_out or codex_unavailable(last):
            return last
    assert last is not None
    return last


def codex_unavailable(result: CommandResult) -> bool:
    combined = result.stdout + "\n" + result.stderr
    return "@openai/codex-win32-x64" in combined or "Reinstall Codex" in combined


def build_worker_prompt(task: Task) -> str:
    required = json.dumps(
        {
            "changed_files": ["..."],
            "attempted_actions": ["..."],
            "tests_run": ["..."],
            "known_risks": ["..."],
        },
        ensure_ascii=False,
        indent=2,
    )
    return (
        "Role: Worker\n\n"
        f"Task: {task.task_id}\nSlice: {task.slice_id}\n\n"
        "Read AGENTS.md, docs/EXECUTION_LOOP_BRIEF.md, and the assigned task artifact first.\n"
        "Implement only inside the checked-in scope.\n\n"
        "Planned touch files:\n" + "\n".join(f"- {p}" for p in task.planned_touch_files) + "\n\n"
        "Forbidden files:\n" + "\n".join(f"- {p}" for p in task.forbidden_files) + "\n\n"
        "Tests to run:\n" + "\n".join(f"- {p}" for p in task.tests_to_run) + "\n\n"
        "If a re-plan trigger occurs, stop and report it instead of widening scope.\n"
        "If the task completes, update the task artifact using this exact markdown structure:\n"
        "## Completion Record\n"
        "- `completed_at`: `YYYY-MM-DD`\n"
        "- `actual_touch_files[]`:\n"
        "  - `path`\n"
        "- `tests_run[]`:\n"
        "  - `command`\n"
        "- `reality_drift_notes`:\n"
        "  - `note` or `none`\n"
        "- `source_of_truth_updated`:\n"
        "  - `yes` or `no`\n"
        "- `followup_task_ids[]`:\n"
        "  - `TASK-...` or `[]`\n"
        "Do not invent alternate headings like 'Actual Touch Files' or 'Completion'.\n"
        "End your final response with a single JSON object matching exactly this schema:\n" + required + "\n"
    )


def build_reviewer_prompt(task: Task) -> str:
    required = json.dumps({"approved": True, "issues": [], "known_risks": []}, ensure_ascii=False, indent=2)
    return (
        "Role: Reviewer\n\n"
        f"Review task {task.task_id} under slice {task.slice_id}.\n"
        "Read the task artifact, latest relevant handoff, touched files, and source-of-truth refs.\n"
        "Prioritize boundary drift, contract mismatch, guardrail math mismatch, missing tests, and source-of-truth sync.\n"
        "Do not expand scope into new implementation work.\n"
        "End your final response with a single JSON object matching exactly this schema:\n" + required + "\n"
    )


def find_json_dict(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def parse_worker_feedback(result: CommandResult) -> tuple[dict[str, Any] | None, list[str]]:
    payload = find_json_dict(result.stdout)
    if payload is None:
        return None, ["missing JSON worker payload"]
    missing = [k for k in ("changed_files", "attempted_actions", "tests_run", "known_risks") if k not in payload]
    return payload, ([f"missing keys: {', '.join(missing)}"] if missing else [])


def parse_reviewer_feedback(result: CommandResult) -> tuple[dict[str, Any] | None, list[str]]:
    payload = find_json_dict(result.stdout)
    if payload is None:
        return None, ["missing JSON reviewer payload"]
    missing = [k for k in ("approved", "issues", "known_risks") if k not in payload]
    return payload, ([f"missing keys: {', '.join(missing)}"] if missing else [])


def validator_commands(task: Task, run_smoke: bool, run_integration_if_needed: bool) -> list[str]:
    seen: set[str] = set()
    commands: list[str] = []

    def add(cmd: str) -> None:
        normalized = cmd.strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        commands.append(normalized)

    add("python scripts/check_layer_integrity.py")
    add("powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings")
    add("powershell -ExecutionPolicy Bypass -File scripts/check_task_checkin_and_handoff.ps1 -AuditRepo")
    for cmd in task.tests_to_run:
        add(cmd)
    if run_smoke:
        add("python -m pytest -q -m smoke")
    if run_integration_if_needed and needs_integration(task):
        add("python -m pytest -q -m integration")
    return commands


def run_validators(task: Task, repo_root: Path, run_smoke: bool, run_integration_if_needed: bool) -> list[CommandResult]:
    commands = validator_commands(task, run_smoke, run_integration_if_needed)
    return [run_command(cmd, repo_root, attempt=1) for cmd in commands]


def archived_handoff_target(task: Task) -> Path | None:
    if not task.handoff_doc_path:
        return None
    return completed_handoff_dir(REPO_ROOT) / Path(task.handoff_doc_path).name


def completion_issues(task: Task, handoff: Handoff | None, gate_reason: str | None, repo_root: Path) -> list[str]:
    issues: list[str] = []
    if task.status != "COMPLETED":
        issues.append("task status is not COMPLETED")
    if not task.completed_at:
        issues.append("missing completed_at")
    if not task.actual_touch_files:
        issues.append("missing actual_touch_files[]")
    if not task.tests_run:
        issues.append("missing tests_run[]")
    if task.source_of_truth_updated is None:
        issues.append("missing source_of_truth_updated")
    if gate_reason:
        issues.append(f"human gate triggered: {gate_reason}")
    if handoff and handoff.current_status in {"BLOCKED", "HANDOFF", "HANDOFF_NEEDED"}:
        issues.append(f"handoff unresolved: {handoff.current_status}")
    if task.handoff_doc_path:
        active = repo_root / task.handoff_doc_path
        completed = completed_handoff_dir(repo_root) / Path(task.handoff_doc_path).name
        if not active.exists() and (completed is None or not completed.exists()):
            issues.append("handoff_doc_path points to missing file")
    return issues


def archive_completed(task: Task, repo_root: Path) -> dict[str, str]:
    archived: dict[str, str] = {}
    completed_task_dir(repo_root).mkdir(parents=True, exist_ok=True)
    completed_handoff_dir(repo_root).mkdir(parents=True, exist_ok=True)
    if task.path.exists():
        target = completed_task_dir(repo_root) / task.path.name
        shutil.move(str(task.path), str(target))
        archived["task"] = str(target)
    if task.handoff_doc_path:
        active = repo_root / task.handoff_doc_path
        if active.exists():
            target = completed_handoff_dir(repo_root) / active.name
            shutil.move(str(active), str(target))
            archived["handoff"] = str(target)
    return archived


def summary_cmds(results: list[CommandResult]) -> list[dict[str, Any]]:
    return [{"command": r.command, "returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr, "timed_out": r.timed_out, "attempt": r.attempt} for r in results]


def write_summary(log_dir: Path, task: Task, payload: dict[str, Any]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{task.task_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def finish(log_dir: Path, task: Task, payload: dict[str, Any]) -> int:
    out = write_summary(log_dir, task, payload)
    print(json.dumps({"status": payload["status"], "task_id": task.task_id, "summary_path": str(out)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id")
    parser.add_argument("--mode", default="single-task", choices=["single-task"])
    parser.add_argument("--allow-delegation", action="store_true")
    parser.add_argument("--run-smoke", action="store_true")
    parser.add_argument("--run-integration-if-needed", action="store_true")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOG_DIR))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    log_dir = Path(args.logs_dir).resolve()

    task, selection = choose_task(repo_root, args.task_id)
    if selection.get("followup_not_allowed"):
        return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "blocked task follow-up is not eligible for auto-transition", "replan_reason_code": REASON_FOLLOWUP_NOT_ALLOWED, "task_id": task.task_id, "slice_id": task.slice_id, "selection": selection})

    issues = metadata_issues(task)
    if issues:
        return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "task metadata incomplete", "replan_reason_code": REASON_TASK_METADATA_INVALID, "task_id": task.task_id, "slice_id": task.slice_id, "metadata_issues": issues, "selection": selection})

    gate = pre_human_gate(task)
    if gate:
        return finish(log_dir, task, {"status": STATUS_HUMAN_GATE_REQUIRED, "reason": gate, "replan_reason_code": REASON_HUMAN_GATE_PRECONDITION, "task_id": task.task_id, "slice_id": task.slice_id, "blocking_artifacts": [str(task.path)], "recommended_next_action": "resolve the declared manual review / benchmark gate before execution", "selection": selection})

    worker_result = None
    worker_feedback = None
    if args.allow_delegation:
        worker_result = run_prompted("worker", build_worker_prompt(task), repo_root, log_dir, task.task_id)
        if worker_result.timed_out:
            return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "worker command timed out", "replan_reason_code": REASON_TIMEOUT, "task_id": task.task_id, "slice_id": task.slice_id, "worker_result": summary_cmds([worker_result]), "selection": selection})
        if worker_result.returncode != 0:
            code = REASON_CODEX_UNAVAILABLE if codex_unavailable(worker_result) else REASON_WORKER_FAILED
            return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "worker execution failed", "replan_reason_code": code, "task_id": task.task_id, "slice_id": task.slice_id, "worker_result": summary_cmds([worker_result]), "selection": selection})
        worker_feedback, wf_issues = parse_worker_feedback(worker_result)
        if wf_issues:
            return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "worker response did not match required schema", "replan_reason_code": REASON_WORKER_RESULT_INVALID, "task_id": task.task_id, "slice_id": task.slice_id, "worker_result": summary_cmds([worker_result]), "worker_feedback_errors": wf_issues, "selection": selection})

    task = parse_task(task.path)
    handoff = None
    if task.handoff_doc_path:
        active_handoff = repo_root / task.handoff_doc_path
        if active_handoff.exists():
            handoff = parse_handoff(active_handoff)
    if handoff and handoff.current_status == "BLOCKED":
        return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "task is blocked after worker execution", "replan_reason_code": REASON_BLOCKED_BY_HANDOFF, "task_id": task.task_id, "slice_id": task.slice_id, "blocking_artifacts": [str(handoff.path)], "recommended_next_action": "; ".join(handoff.next_actions) or "re-plan from active handoff", "worker_result": summary_cmds([worker_result]) if worker_result else [], "worker_feedback": worker_feedback, "selection": selection})

    reviewer_result = None
    reviewer_feedback = None
    if needs_reviewer(task):
        reviewer_result = run_prompted("reviewer", build_reviewer_prompt(task), repo_root, log_dir, task.task_id)
        if reviewer_result.timed_out:
            return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "reviewer command timed out", "replan_reason_code": REASON_TIMEOUT, "task_id": task.task_id, "slice_id": task.slice_id, "review_result": summary_cmds([reviewer_result]), "selection": selection})
        if reviewer_result.returncode != 0:
            code = REASON_CODEX_UNAVAILABLE if codex_unavailable(reviewer_result) else REASON_REVIEW_REJECTED
            return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "reviewer execution failed", "replan_reason_code": code, "task_id": task.task_id, "slice_id": task.slice_id, "review_result": summary_cmds([reviewer_result]), "selection": selection})
        reviewer_feedback, rf_issues = parse_reviewer_feedback(reviewer_result)
        if rf_issues or not reviewer_feedback or not reviewer_feedback.get("approved", False) or reviewer_feedback.get("issues"):
            return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "reviewer rejected task completion", "replan_reason_code": REASON_REVIEW_REJECTED, "task_id": task.task_id, "slice_id": task.slice_id, "review_result": summary_cmds([reviewer_result]), "reviewer_feedback": reviewer_feedback, "reviewer_feedback_errors": rf_issues, "selection": selection})

    validator_results = run_validators(task, repo_root, args.run_smoke, args.run_integration_if_needed)
    if any(r.returncode != 0 for r in validator_results):
        return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "validator or test failure", "replan_reason_code": REASON_VALIDATOR_FAILED, "task_id": task.task_id, "slice_id": task.slice_id, "worker_result": summary_cmds([worker_result]) if worker_result else [], "worker_feedback": worker_feedback, "review_result": summary_cmds([reviewer_result]) if reviewer_result else [], "reviewer_feedback": reviewer_feedback, "checks": summary_cmds(validator_results), "selection": selection})

    task = parse_task(task.path)
    handoff = None
    if task.handoff_doc_path:
        active_handoff = repo_root / task.handoff_doc_path
        if active_handoff.exists():
            handoff = parse_handoff(active_handoff)
    gate = post_human_gate(task)
    comp_issues = completion_issues(task, handoff, gate, repo_root)
    if comp_issues:
        if gate:
            return finish(log_dir, task, {"status": STATUS_HUMAN_GATE_REQUIRED, "reason": gate, "replan_reason_code": REASON_HUMAN_GATE_POST_COMPLETION, "task_id": task.task_id, "slice_id": task.slice_id, "blocking_artifacts": [str(task.path)] + ([str(repo_root / task.handoff_doc_path)] if task.handoff_doc_path else []), "recommended_next_action": "perform manual review before archival and next task selection", "worker_result": summary_cmds([worker_result]) if worker_result else [], "worker_feedback": worker_feedback, "review_result": summary_cmds([reviewer_result]) if reviewer_result else [], "reviewer_feedback": reviewer_feedback, "checks": summary_cmds(validator_results), "selection": selection})
        return finish(log_dir, task, {"status": STATUS_REPLAN_REQUIRED, "reason": "task did not satisfy hard completion criteria", "replan_reason_code": REASON_COMPLETION_INCOMPLETE, "task_id": task.task_id, "slice_id": task.slice_id, "completion_issues": comp_issues, "worker_result": summary_cmds([worker_result]) if worker_result else [], "worker_feedback": worker_feedback, "review_result": summary_cmds([reviewer_result]) if reviewer_result else [], "reviewer_feedback": reviewer_feedback, "checks": summary_cmds(validator_results), "selection": selection})

    archived = archive_completed(task, repo_root)
    return finish(log_dir, task, {"status": STATUS_COMPLETED, "reason": "task completed and passed all validators", "task_id": task.task_id, "slice_id": task.slice_id, "worker_result": summary_cmds([worker_result]) if worker_result else [], "worker_feedback": worker_feedback, "review_result": summary_cmds([reviewer_result]) if reviewer_result else [], "reviewer_feedback": reviewer_feedback, "checks": summary_cmds(validator_results), "archived": archived, "selection": selection})


if __name__ == "__main__":
    sys.exit(main())
