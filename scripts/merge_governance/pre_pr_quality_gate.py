from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import fnmatch
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.repo_policy import (  # noqa: E402
    category_for_repo_path,
    effective_cap_for_repo_path,
    load_active_code_policy,
    normalize_repo_path,
    target_cap_for_repo_path,
)
from scripts.merge_governance.build_merge_debt_matrix import infer_track, normalize_track  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "pre_pr_quality_gate_report.json"
FUTURE_SHADOW_TRACKS = {"LongTermContextLab", "RecommendationShadow", "RescueShadow", "ProactiveShadow"}
FUTURE_ACTIVE_SURFACE_PATTERNS = (
    "app/routes.py",
    "app/main.py",
    "app/runtime/agent/",
    "app/runtime/interface/",
    "app/composition/",
    "alembic/",
    "migrations/",
)

PROTECTED_THRESHOLDS: dict[str, int] = {
    "app/schemas.py": 450,
    "app/routes.py": 400,
    "app/runtime/application/manager_service.py": 500,
    "app/intake/application/intake_turn_orchestrator.py": 360,
    "app/intake/application/intake_execution_orchestrator.py": 360,
    "app/providers/builderspace_adapter.py": 1100,
    "app/providers/deepseek_adapter.py": 500,
    "app/runtime/agent/manager_branch_contract.py": 550,
}


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str
    old_text: str | None
    new_text: str | None


def _line_count(text: str | None) -> int:
    if not text:
        return 0
    return len(text.replace("\r\n", "\n").splitlines())


def _is_active_python(path: str, policy: dict[str, Any]) -> bool:
    root = str(policy.get("active_code", {}).get("root") or "app").strip("/\\")
    normalized = normalize_repo_path(path)
    if not normalized.startswith(f"{root}/") or not normalized.endswith(".py"):
        return False
    for pattern in policy.get("active_code", {}).get("excluded_globs", []):
        if fnmatch.fnmatch(normalized, str(pattern)):
            return False
    return True


def _finding(*, code: str, path: str, message: str, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"code": code, "path": path, "message": message}
    payload.update(extra)
    return payload


def _evaluate_active_python_size(change: ChangedFile, policy: dict[str, Any]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    blockers: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    path = normalize_repo_path(change.path)
    if change.new_text is None or not _is_active_python(path, policy):
        return blockers, warnings

    category = category_for_repo_path(path, policy)
    if category is None:
        blockers.append(
            _finding(
                code="active_python_file_unmapped",
                path=path,
                message="Active app Python file is not mapped to an active_code_policy category.",
            )
        )
        return blockers, warnings

    old_lines = _line_count(change.old_text)
    new_lines = _line_count(change.new_text)
    new_file_cap = int(policy["active_code"]["new_active_python_file_default_cap"])
    target_cap = int(target_cap_for_repo_path(path, policy) or 0)
    effective_cap = int(effective_cap_for_repo_path(path, policy) or target_cap)

    if old_lines == 0 and new_lines > new_file_cap:
        blockers.append(
            _finding(
                code="new_active_python_file_over_cap",
                path=path,
                message=f"New active Python file exceeds the new-file cap ({new_lines}>{new_file_cap}).",
                old_lines=old_lines,
                new_lines=new_lines,
                cap=new_file_cap,
            )
        )
    elif old_lines > target_cap and new_lines > old_lines:
        blockers.append(
            _finding(
                code="active_file_grew_over_target_cap",
                path=path,
                message=f"Changed active Python file grew while already over target cap {target_cap}.",
                old_lines=old_lines,
                new_lines=new_lines,
                cap=target_cap,
            )
        )
    elif old_lines <= effective_cap < new_lines:
        blockers.append(
            _finding(
                code="active_file_crossed_effective_cap",
                path=path,
                message=f"Changed active Python file crossed effective cap {effective_cap}.",
                old_lines=old_lines,
                new_lines=new_lines,
                cap=effective_cap,
            )
        )
    elif new_lines > target_cap:
        warnings.append(
            _finding(
                code="active_file_over_target_cap",
                path=path,
                message=f"Changed active Python file remains over target cap {target_cap}.",
                old_lines=old_lines,
                new_lines=new_lines,
                cap=target_cap,
            )
        )
    return blockers, warnings


def _evaluate_protected_growth(change: ChangedFile) -> list[dict[str, object]]:
    path = normalize_repo_path(change.path)
    threshold = PROTECTED_THRESHOLDS.get(path)
    if threshold is None or change.new_text is None:
        return []
    old_lines = _line_count(change.old_text)
    new_lines = _line_count(change.new_text)
    if old_lines > threshold and new_lines > old_lines:
        return [
            _finding(
                code="protected_file_grew_over_threshold",
                path=path,
                message=f"Protected file grew while already over threshold {threshold}.",
                old_lines=old_lines,
                new_lines=new_lines,
                cap=threshold,
            )
        ]
    if old_lines <= threshold < new_lines:
        return [
            _finding(
                code="protected_file_crossed_threshold",
                path=path,
                message=f"Protected file crossed threshold {threshold}.",
                old_lines=old_lines,
                new_lines=new_lines,
                cap=threshold,
            )
        ]
    return []


def _evaluate_future_shadow_surface(track: str, change: ChangedFile) -> list[dict[str, object]]:
    if track not in FUTURE_SHADOW_TRACKS:
        return []
    path = normalize_repo_path(change.path)
    for pattern in FUTURE_ACTIVE_SURFACE_PATTERNS:
        if path == pattern or path.startswith(pattern):
            return [
                _finding(
                    code="future_shadow_touches_active_surface",
                    path=path,
                    message=f"{track} changes must stay dormant/no-runtime and cannot touch active runtime surfaces.",
                )
            ]
    return []


def _dsa_advisories(change: ChangedFile) -> list[dict[str, object]]:
    path = normalize_repo_path(change.path)
    source = change.new_text
    if source is None or not path.endswith(".py") or path.startswith("tests/"):
        return []

    advisories: list[dict[str, object]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            _finding(
                code="python_parse_error",
                path=path,
                message=f"Unable to parse changed Python file for advisory analysis: {exc.msg}.",
            )
        ]

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        function_lines = int(getattr(node, "end_lineno", node.lineno) or node.lineno) - int(node.lineno) + 1
        branch_nodes = sum(
            isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match, ast.BoolOp))
            for child in ast.walk(node)
        )
        if function_lines >= 80 or branch_nodes >= 6:
            advisories.append(
                _finding(
                    code="changed_function_complexity_signal",
                    path=path,
                    message="Changed function has enough length/branching to deserve review, but this is advisory only.",
                    function=getattr(node, "name", "<anonymous>"),
                    function_lines=function_lines,
                    branch_nodes=branch_nodes,
                )
            )

    scan_tokens = {
        "broad_file_scan_signal": ("rglob(", "glob(", "os.walk("),
        "repeated_io_signal": (".read_text(", "open("),
        "repeated_json_parse_signal": ("json.loads(", "json.load("),
        "subprocess_hot_path_signal": ("subprocess.run(",),
    }
    for code, tokens in scan_tokens.items():
        hits = sum(source.count(token) for token in tokens)
        if hits >= 2:
            advisories.append(
                _finding(
                    code=code,
                    path=path,
                    message="Repeated scan/IO/parse style operation detected in changed file; review for hot-path placement.",
                    hits=hits,
                )
            )
    return advisories


def _run_boundary_command(name: str, command: list[str]) -> tuple[str, dict[str, object] | None]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode == 0:
        return "pass", None
    return "fail", {
        "code": f"{name}_failed",
        "path": "",
        "message": f"{name} failed with exit code {completed.returncode}.",
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def _boundary_report() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    results: list[dict[str, object]] = []
    blockers: list[dict[str, object]] = []
    commands = (
        ("layer_integrity", [sys.executable, "scripts/check_layer_integrity.py"]),
        ("runtime_boundaries", [sys.executable, "scripts/check_runtime_boundaries.py"]),
    )
    for name, command in commands:
        status, blocker = _run_boundary_command(name, command)
        results.append({"name": name, "status": status})
        if blocker is not None:
            blockers.append(blocker)
    return results, blockers


def build_quality_report_from_changes(
    changes: list[ChangedFile],
    *,
    policy: dict[str, Any],
    track: str,
    run_boundary_checks: bool = True,
) -> dict[str, object]:
    blockers: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    advisories: list[dict[str, object]] = []
    for change in changes:
        active_blockers, active_warnings = _evaluate_active_python_size(change, policy)
        blockers.extend(active_blockers)
        warnings.extend(active_warnings)
        blockers.extend(_evaluate_protected_growth(change))
        blockers.extend(_evaluate_future_shadow_surface(track, change))
        advisories.extend(_dsa_advisories(change))

    boundary_results: list[dict[str, object]] = []
    if run_boundary_checks:
        boundary_results, boundary_blockers = _boundary_report()
        blockers.extend(boundary_blockers)

    return {
        "artifact_type": "pre_pr_quality_gate_report",
        "status": "fail" if blockers else "pass",
        "track": track,
        "changed_file_count": len(changes),
        "blockers": blockers,
        "warnings": warnings,
        "advisories": advisories,
        "boundary_checks": boundary_results,
    }


def _run_text(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"{' '.join(command)} failed")
    return completed.stdout


def _git_show(ref: str, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def collect_changed_files(*, base_ref: str, head_ref: str) -> list[ChangedFile]:
    raw = _run_text(["git", "diff", "--name-status", "--find-renames", f"{base_ref}...{head_ref}"])
    changes: list[ChangedFile] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            old_path = normalize_repo_path(parts[1])
            new_path = normalize_repo_path(parts[2])
        elif len(parts) >= 2:
            old_path = normalize_repo_path(parts[1])
            new_path = old_path
        else:
            continue
        old_text = None if status.startswith("A") else _git_show(base_ref, old_path)
        new_text = None if status.startswith("D") else _git_show(head_ref, new_path)
        changes.append(ChangedFile(path=new_path, status=status[:1], old_text=old_text, new_text=new_text))
    return changes


def _pull_request_payload_from_event(event_path: Path | None) -> dict[str, Any] | None:
    if event_path is None or not event_path.exists():
        return None
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    head = pull_request.get("head") if isinstance(pull_request.get("head"), dict) else {}
    return {
        "title": pull_request.get("title") or "",
        "body": pull_request.get("body") or "",
        "headRefName": head.get("ref") or pull_request.get("headRefName") or "",
    }


def infer_track_from_event(event_path: Path | None) -> str | None:
    pull_request = _pull_request_payload_from_event(event_path)
    if pull_request is None:
        return None
    track = infer_track(pull_request)
    return None if track == "unknown" else track


def resolve_track(cli_track: str, event_path: Path | None) -> str:
    explicit_track = normalize_track(str(cli_track or "").strip())
    if explicit_track and explicit_track.lower() != "unknown":
        return explicit_track
    return infer_track_from_event(event_path) or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic pre-PR quality gates against changed files.")
    parser.add_argument("--track", default="unknown")
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--event-file", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-boundary-checks", action="store_true")
    args = parser.parse_args(argv)

    event_path = Path(args.event_file) if args.event_file else None
    track = resolve_track(args.track, event_path)
    changes = collect_changed_files(base_ref=args.base_ref, head_ref=args.head_ref)
    report = build_quality_report_from_changes(
        changes,
        policy=load_active_code_policy(),
        track=track,
        run_boundary_checks=not args.skip_boundary_checks,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
