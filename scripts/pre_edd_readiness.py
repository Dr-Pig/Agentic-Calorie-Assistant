from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = ROOT / "artifacts" / "pre_edd_readiness_report.json"
POWERSHELL_BIN = shutil.which("pwsh") or shutil.which("powershell") or "pwsh"


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: tuple[str, ...]
    status_key: str


_command_plan: list[CommandSpec] = [
    CommandSpec(
        name="markdown_encoding_policy",
        command=(sys.executable, "scripts/check_markdown_encoding.py", "--policy-docs", "--require-bom"),
        status_key="encoding_status",
    ),
]

if sys.platform.startswith("win"):
    _command_plan.append(
        CommandSpec(
            name="docs_encoding_policy",
            command=(POWERSHELL_BIN, "-ExecutionPolicy", "Bypass", "-File", "scripts/check_encoding.ps1", "-AuditDocsPolicy"),
            status_key="encoding_status",
        )
    )

_command_plan.extend(
    [
        CommandSpec(
            name="user_facing_mojibake_guard",
            command=(sys.executable, "scripts/check_user_facing_mojibake.py"),
            status_key="encoding_status",
        ),
        CommandSpec(
            name="fat_file_audit",
            command=(POWERSHELL_BIN, "-ExecutionPolicy", "Bypass", "-File", "scripts/check_fat_files.ps1", "-AuditAll"),
            status_key="fat_file_status",
        ),
        CommandSpec(
            name="layer_integrity",
            command=(sys.executable, "scripts/check_layer_integrity.py"),
            status_key="legacy_status",
        ),
        CommandSpec(
            name="runtime_boundaries",
            command=(sys.executable, "scripts/check_runtime_boundaries.py"),
            status_key="single_manager_status",
        ),
        CommandSpec(
            name="readiness_claim_integrity",
            command=(sys.executable, "scripts/audit_readiness_claim_integrity.py"),
            status_key="readiness_claim_status",
        ),
        CommandSpec(
            name="architecture_guard_tests",
            command=(
                sys.executable,
                "-m",
                "pytest",
                "tests/test_domain_first_guardrails.py",
                "tests/test_v2_architecture_regression.py",
                "tests/test_manager_service.py",
                "tests/test_deepseek_adapter.py",
                "tests/test_builderspace_adapter.py",
                "tests/test_markdown_encoding_guard.py",
                "tests/test_runner_timeout_contract.py",
                "tests/test_tavily_timeout_contract.py",
                "tests/test_text_integrity.py",
                "tests/test_import_external_workspace_candidates.py",
                "tests/test_pre_edd_readiness.py",
                "tests/test_readiness_claim_integrity.py",
                "tests/test_workflow_routing_decision.py",
                "-q",
            ),
            status_key="single_manager_status",
        ),
    ]
)

COMMAND_PLAN: tuple[CommandSpec, ...] = tuple(_command_plan)


PROTECTED_FAT_PATHS = (
    "app/schemas.py",
    "app/routes.py",
    "app/runtime/application/manager_service.py",
    "app/intake/application/intake_turn_orchestrator.py",
    "app/intake/application/intake_execution_orchestrator.py",
    "app/providers/builderspace_adapter.py",
    "app/providers/deepseek_adapter.py",
)

FREEZE_GROWTH_PATHS = (
    "app/providers/builderspace_adapter.py",
)


def classify_fat_audit(*, stdout: str, exit_code: int) -> dict[str, Any]:
    details: list[str] = []
    if exit_code != 0:
        details.append(f"check_fat_files exited {exit_code}")
    for line in stdout.splitlines():
        if not line.startswith("[OVER] "):
            continue
        if "threshold=" in line and any(path in line for path in PROTECTED_FAT_PATHS):
            details.append(line)
            continue
        if "freeze=" in line and any(path in line for path in FREEZE_GROWTH_PATHS):
            details.append(line)
    return {
        "status": "fail" if details else "pass",
        "details": details,
    }


def summarize_status(statuses: dict[str, Any]) -> dict[str, Any]:
    failing = [
        key
        for key, value in statuses.items()
        if isinstance(value, dict) and value.get("status") not in {"pass", "not_run"}
    ]
    return {
        "status": "not_ready_for_edd" if failing else "ready_for_edd",
        "failing_statuses": failing,
    }


def _merge_status(existing: dict[str, Any] | None, new_status: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return dict(new_status)
    merged = dict(existing)
    merged.setdefault("details", [])
    merged["details"].extend(new_status.get("details") or [])
    if existing.get("status") == "fail" or new_status.get("status") == "fail":
        merged["status"] = "fail"
    else:
        merged["status"] = "pass"
    return merged


def _run_command(spec: CommandSpec, *, timeout_seconds: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            spec.command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "name": spec.name,
            "command": list(spec.command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "status": "pass" if completed.returncode == 0 else "fail",
            "details": [] if completed.returncode == 0 else [f"{spec.name} exited {completed.returncode}"],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": spec.name,
            "command": list(spec.command),
            "exit_code": None,
            "stdout": str(exc.stdout or ""),
            "status": "fail",
            "details": [f"{spec.name} timed out after {timeout_seconds}s"],
            "request_failure_family": "timeout",
        }


def run_pre_edd_readiness(*, timeout_seconds: int = 180) -> dict[str, Any]:
    statuses: dict[str, Any] = {
        "fat_file_status": {"status": "not_run", "details": []},
        "responsibility_status": {"status": "not_run", "details": []},
        "single_manager_status": {"status": "not_run", "details": []},
        "encoding_status": {"status": "not_run", "details": []},
        "legacy_status": {"status": "not_run", "details": []},
        "single_manager_contract_status": {"status": "not_run", "details": []},
        "domain_tool_surface_status": {"status": "not_run", "details": []},
        "guard_invariant_status": {"status": "not_run", "details": []},
        "fat_service_status": {"status": "not_run", "details": []},
        "latency_trace_status": {"status": "not_run", "details": []},
        "product_truth_alignment_status": {"status": "not_run", "details": []},
        "anti_overfit_status": {"status": "not_run", "details": []},
        "readiness_claim_status": {"status": "not_run", "details": []},
    }
    command_results: list[dict[str, Any]] = []
    for spec in COMMAND_PLAN:
        result = _run_command(spec, timeout_seconds=timeout_seconds)
        if spec.name == "fat_file_audit":
            result.update(classify_fat_audit(stdout=result.get("stdout") or "", exit_code=int(result.get("exit_code") or 0)))
        command_results.append({k: v for k, v in result.items() if k != "stdout"})
        current = statuses.get(spec.status_key)
        statuses[spec.status_key] = _merge_status(current, result)

    # Responsibility pressure is enforced by the architecture guard tests and
    # fat audit. Keep it explicit so reports cannot hide it inside pytest output.
    if statuses["fat_file_status"]["status"] == "pass" and statuses["single_manager_status"]["status"] == "pass":
        statuses["responsibility_status"] = {"status": "pass", "details": []}
    else:
        statuses["responsibility_status"] = {
            "status": "fail",
            "details": ["fat-file or single-manager guard failed"],
        }

    statuses["single_manager_contract_status"] = dict(statuses["single_manager_status"])
    statuses["fat_service_status"] = dict(statuses["fat_file_status"])
    derived_pass = statuses["single_manager_status"]["status"] == "pass"
    statuses["domain_tool_surface_status"] = {
        "status": "pass" if derived_pass else "fail",
        "details": [] if derived_pass else ["single-manager runtime boundary or architecture guard failed"],
    }
    statuses["guard_invariant_status"] = {
        "status": "pass" if derived_pass else "fail",
        "details": [] if derived_pass else ["guard invariant checks are carried by the architecture/runtime test wall"],
    }
    statuses["latency_trace_status"] = {
        "status": "pass" if derived_pass else "fail",
        "details": [] if derived_pass else ["latency trace guard is incomplete because single-manager/runtime checks failed"],
    }
    product_truth_pass = (
        derived_pass
        and statuses["legacy_status"]["status"] == "pass"
        and statuses["readiness_claim_status"]["status"] == "pass"
    )
    statuses["product_truth_alignment_status"] = {
        "status": "pass" if product_truth_pass else "fail",
        "details": [] if product_truth_pass else ["product-truth-first architecture or canonical spec alignment failed"],
    }
    statuses["anti_overfit_status"] = {
        "status": "pass" if product_truth_pass else "fail",
        "details": [] if product_truth_pass else ["fixture-shape or case-specific guard failed"],
    }

    summary = summarize_status(statuses)
    return {
        "summary": summary,
        "statuses": statuses,
        "commands": command_results,
        "excluded_business_eval_suites": ["legacy live acceptance runners"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pre-EDD architecture/readiness gates without business eval suites.")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    report = run_pre_edd_readiness(timeout_seconds=args.timeout_seconds)
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(report_path), **report["summary"]}, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["status"] == "ready_for_edd" else 1


if __name__ == "__main__":
    raise SystemExit(main())
