from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]

BOOTSTRAP_PATH = [
    "AGENTS.md",
    "docs/index.md",
    "docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md",
    "docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md",
    "docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md",
    "docs/governance/EXECUTION_OPERATING_MODEL.md",
]

RETIRED_ROOT_DIRS = (
    "child_outputs",
    "tmp",
)

ACTIVE_ALLOWED = {
    "CURRENT_EXECUTION_PLAN.md",
    "REPLAN_LOG.md",
}

RETIRED_PATH_PATTERNS = (
    "docs/handoff/",
    "docs/_spec_snapshots/",
)

HISTORICAL_REFERENCE_ALLOWLIST = {
    "docs/exec-plans/active/REPLAN_LOG.md",
    "docs/exec-plans/tech-debt-tracker.md",
    "scripts/harness_garbage_collect.py",
}


@dataclass
class Finding:
    check: str
    severity: str
    message: str


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def normalize(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def collect_markdown_files(base: Path) -> list[Path]:
    return [p for p in base.rglob("*.md") if p.is_file()]


def stale_active_doc_check() -> list[Finding]:
    findings: list[Finding] = []
    active_dir = REPO_ROOT / "docs/exec-plans/active"
    for item in active_dir.iterdir():
        if item.is_dir():
            if item.name != "tasks" and item.name != "handoff":
                findings.append(
                    Finding(
                        "stale-active-doc",
                        "warning",
                        f"unexpected directory under active/: {normalize(item)}",
                    )
                )
            continue
        if item.name not in ACTIVE_ALLOWED:
            findings.append(
                Finding(
                    "stale-active-doc",
                    "warning",
                    f"non-state file under active/: {normalize(item)}",
                )
            )
    return findings


def bootstrap_contract_check() -> list[Finding]:
    findings: list[Finding] = []
    for relative in BOOTSTRAP_PATH:
        path = REPO_ROOT / relative
        if not path.exists():
            findings.append(
                Finding("bootstrap-contract", "error", f"missing bootstrap file: {relative}")
            )
    agents = read_text(REPO_ROOT / "AGENTS.md")
    if "Bootstrap read path is:" not in agents:
        findings.append(
            Finding("bootstrap-contract", "warning", "AGENTS.md no longer states the bootstrap read path.")
        )
    current_plan = read_text(REPO_ROOT / "docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md")
    if "Global Build Ladder" not in current_plan or "Selection State" not in current_plan:
        findings.append(
            Finding(
                "bootstrap-contract",
                "warning",
                "CURRENT_EXECUTION_PLAN.md is missing expected state-machine sections.",
            )
        )
    for retired_dir in RETIRED_ROOT_DIRS:
        if (REPO_ROOT / retired_dir).exists():
            findings.append(
                Finding(
                    "bootstrap-contract",
                    "error",
                    f"retired root scratch directory still exists: {retired_dir}/",
                )
            )
    return findings


def execution_pointer_drift_check() -> list[Finding]:
    findings: list[Finding] = []
    text = read_text(REPO_ROOT / "docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md")
    required_markers = (
        "`current_pointer_bundle`",
        "`recommended_next_slice`",
        "`selected_best_next_slice`",
        "`human_gate`",
    )
    for marker in required_markers:
        if marker not in text:
            findings.append(
                Finding(
                    "execution-pointer-drift",
                    "warning",
                    f"CURRENT_EXECUTION_PLAN.md is missing marker {marker}.",
                )
            )
    if re.search(r"`recommended_next_slice`:\s*`none`", text) and "deferred" in text:
        findings.append(
            Finding(
                "execution-pointer-drift",
                "warning",
                "recommended_next_slice is `none` while deferred branches exist; review next-slice selection.",
            )
        )
    return findings


def artifact_misuse_check() -> list[Finding]:
    findings: list[Finding] = []
    docs_to_scan = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "docs/index.md",
        REPO_ROOT / "docs/governance/TASK_CHECKIN_PROTOCOL.md",
        REPO_ROOT / "docs/governance/HANDOFF_CONTRACT.md",
        REPO_ROOT / "docs/exec-plans/active/tasks/README.md",
    ]
    joined = "\n".join(read_text(p) for p in docs_to_scan if p.exists())
    if "Do not start broad implementation work without a checked-in task artifact." in joined:
        findings.append(
            Finding(
                "artifact-misuse",
                "error",
                "repo still states that task artifacts are mandatory for broad implementation.",
            )
        )
    active_tasks = list((REPO_ROOT / "docs/exec-plans/active/tasks").glob("*.md"))
    active_tasks = [p for p in active_tasks if p.name.lower() != "readme.md"]
    if active_tasks:
        findings.append(
            Finding(
                "artifact-misuse",
                "info",
                f"active task artifacts exist: {len(active_tasks)} file(s) under docs/exec-plans/active/tasks/.",
            )
        )
    return findings


def snapshot_isolation_check() -> list[Finding]:
    findings: list[Finding] = []
    if (REPO_ROOT / "docs/_spec_snapshots").exists():
        findings.append(
            Finding(
                "snapshot-isolation",
                "error",
                "docs/_spec_snapshots still exists inside docs/ ontology.",
            )
        )

    scan_roots = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs",
        REPO_ROOT / "scripts",
    ]
    files: list[Path] = []
    for root in scan_roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(collect_markdown_files(root))
            files.extend([p for p in root.rglob("*.py") if p.is_file()])
            files.extend([p for p in root.rglob("*.ps1") if p.is_file()])

    seen: set[str] = set()
    for path in files:
        relative = normalize(path)
        if relative.startswith("docs/exec-plans/completed/"):
            continue
        if relative.startswith("artifacts/docs-snapshots/"):
            continue
        if relative in HISTORICAL_REFERENCE_ALLOWLIST:
            continue
        text = read_text(path)
        for pattern in RETIRED_PATH_PATTERNS:
            if pattern in text:
                key = f"{relative}:{pattern}"
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        Finding(
                            "snapshot-isolation",
                            "warning",
                            f"live file still references retired path `{pattern}`: {relative}",
                        )
                    )
    return findings


CHECKS = {
    "stale-active-doc": stale_active_doc_check,
    "bootstrap-contract": bootstrap_contract_check,
    "execution-pointer-drift": execution_pointer_drift_check,
    "artifact-misuse": artifact_misuse_check,
    "snapshot-isolation": snapshot_isolation_check,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Advisory harness hygiene scan.")
    parser.add_argument(
        "--check",
        action="append",
        choices=sorted(CHECKS),
        help="Run only the named check. Repeatable.",
    )
    args = parser.parse_args()

    selected = args.check or list(CHECKS)
    findings: list[Finding] = []
    for name in selected:
        findings.extend(CHECKS[name]())

    if not findings:
        print("harness-garbage-collect: clean")
        return 0

    severity_order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 9), f.check, f.message))
    print("harness-garbage-collect: advisory findings")
    for finding in findings:
        print(f"[{finding.severity}] {finding.check}: {finding.message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
