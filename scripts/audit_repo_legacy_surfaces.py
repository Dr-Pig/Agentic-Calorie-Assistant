from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonc", ".txt", ".ps1", ".html"}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "artifacts", ".venv", "venv"}


def _join(*parts: str) -> str:
    return "".join(parts)


FORBIDDEN_TRACKED_PATH_PATTERNS = (
    _join("docs/", "archive/"),
    _join("app/", "archive/"),
    "__pycache__",
    ".pyc",
    _join("autonomy-", "prompts"),
    _join("autonomy-", "schemas"),
    _join("docs/quality/V2_EVAL_", "BUNDLE_", "1_CASES.md"),
    _join("docs/quality/V2_EVAL_", "BUNDLE_", "2_CASES.md"),
    _join("docs/quality/", "BUNDLE_V2_", "EVAL_STABILITY_ANALYSIS"),
    _join("static/v2-", "bundle1", "-dashboard.html"),
)

FORBIDDEN_TEXT_MARKERS = (
    _join("app.", "archive"),
    _join("docs/", "archive"),
    _join("run_b1_cli_", "autorun"),
    _join("run_codex_exec_", "with_prompt"),
    _join("manager_", "tools.py"),
    _join("phase_a_", "context.py"),
    _join("nutrition", "_resolution"),
    _join("run_", "nutrition", "_resolution"),
    _join("planner", "_result"),
    _join("planner", "_output"),
    _join("planner", "_used"),
    _join("planner", "_mode"),
    _join("planning", "_brief"),
    _join("decision", "_pass"),
    _join("planner", "_pass"),
    _join("final_response", "_pass"),
    _join("stale ", "oracle"),
    _join("V2_EVAL_", "BUNDLE_", "1_CASES"),
    _join("V2_EVAL_", "BUNDLE_", "2_CASES"),
    _join("run_v2_", "bundle1", "_live_eval"),
    _join("run_v2_", "bundle2", "_live_eval"),
    _join("run_v2_", "benchmark_blocking_eval"),
    _join("eval_", "parity_audit"),
    _join("eval_", "bootstrap"),
    _join("build_", "bundle_verdict"),
    _join("bundle_", "gate"),
    _join("Bundle ", "readiness"),
    _join("Declaring ", "Bundle"),
    _join("official ", "Bundle"),
    _join("official ", "bundle ", "runner"),
    _join("bundle ", "eval packs"),
    _join("bundle ", "reports"),
    _join("--stage ", "bundle2"),
    _join("BUNDLE_V2_", "EVAL_STABILITY_ANALYSIS"),
)

FORBIDDEN_TEXT_PATTERNS = (
    re.compile(_join("draft", r"[-_ ]first")),
)


def _repo_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _git_ls_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(part in SKIP_PARTS or part.startswith(".pytest_tmp") for part in parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _scan_tracked_paths(root: Path, tracked_paths: Iterable[str] | None = None) -> list[dict[str, Any]]:
    tracked = list(tracked_paths) if tracked_paths is not None else _git_ls_files(root)
    findings: list[dict[str, Any]] = []
    for path in tracked:
        normalized = path.replace("\\", "/")
        for marker in FORBIDDEN_TRACKED_PATH_PATTERNS:
            if marker in normalized:
                findings.append(
                    {
                        "kind": "tracked_path",
                        "path": normalized,
                        "marker": marker,
                    }
                )
                break
    return findings


def _scan_text(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(root):
        repo_path = _repo_path(root, path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN_TEXT_MARKERS:
            if marker in text:
                findings.append(
                    {
                        "kind": "text_marker",
                        "path": repo_path,
                        "marker": marker,
                    }
                )
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern.search(text):
                findings.append(
                    {
                        "kind": "text_pattern",
                        "path": repo_path,
                        "marker": pattern.pattern,
                    }
                )
    return findings


def build_report(
    *,
    root: Path = ROOT,
    tracked_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    tracked_findings = _scan_tracked_paths(root, tracked_paths=tracked_paths)
    text_findings = _scan_text(root)
    findings = [*tracked_findings, *text_findings]
    return {
        "artifact_type": "repo_legacy_surface_audit",
        "checked_root": str(root),
        "fails_build": bool(findings),
        "finding_count": len(findings),
        "tracked_path_finding_count": len(tracked_findings),
        "text_finding_count": len(text_findings),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repo-visible legacy surfaces.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    report = build_report()
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["fails_build"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
