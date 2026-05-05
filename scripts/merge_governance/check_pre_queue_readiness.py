from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
DEFAULT_OUTPUT = ROOT / "artifacts" / "pre_queue_readiness_report.json"


PRODUCT_PAGES_JOB = "product-pages-browser-e2e"

COMMAND_SNIPPETS = (
    (
        "context_live_diagnostic_case_matrix",
        "build_accurate_intake_context_live_diagnostic_case_matrix.py --output "
        "artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json",
    ),
    (
        "context_live_diagnostic_anti_overfit_guard",
        "build_accurate_intake_context_live_diagnostic_anti_overfit_guard.py --matrix-json "
        "artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json --output "
        "artifacts/accurate_intake_context_live_diagnostic_anti_overfit_guard_ci.json",
    ),
    (
        "context_live_diagnostic_dry_run_evaluator",
        "build_accurate_intake_context_live_diagnostic_dry_run_evaluator.py --matrix-json "
        "artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json --output "
        "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json",
    ),
    (
        "context_live_provider_input_preflight",
        "build_accurate_intake_context_live_provider_input_preflight.py --matrix-json "
        "artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json --anti-overfit-json "
        "artifacts/accurate_intake_context_live_diagnostic_anti_overfit_guard_ci.json --output "
        "artifacts/accurate_intake_context_live_provider_input_preflight_ci.json",
    ),
    (
        "context_live_response_contract_dry_run",
        "build_accurate_intake_context_live_response_contract_dry_run.py "
        "--provider-input-preflight-json "
        "artifacts/accurate_intake_context_live_provider_input_preflight_ci.json --output "
        "artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json",
    ),
)

UPLOAD_ARTIFACTS = (
    "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json",
    "artifacts/accurate_intake_context_live_provider_input_preflight_ci.json",
    "artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json",
)

ACTIVATION_MANIFEST_INPUTS = (
    "--artifact context_live_diagnostic_dry_run_evaluator="
    "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json",
)


def _job_block(workflow: str, job_name: str) -> str:
    marker = f"  {job_name}:"
    start = workflow.find(marker)
    if start < 0:
        return ""
    next_job = re.search(r"^  [A-Za-z0-9_-]+:\s*$", workflow[start + len(marker) :], re.MULTILINE)
    if next_job is None:
        return workflow[start:]
    return workflow[start : start + len(marker) + next_job.start()]


def build_report(workflow_text: str) -> dict[str, Any]:
    blockers: list[str] = []
    if any(marker in workflow_text for marker in ("<<<<<<<", "=======", ">>>>>>>")):
        blockers.append("workflow_conflict_markers_present")

    job = _job_block(workflow_text, PRODUCT_PAGES_JOB)
    if not job:
        blockers.append(f"missing_job.{PRODUCT_PAGES_JOB}")
        return {"status": "fail", "blockers": blockers}

    positions: list[tuple[str, int]] = []
    for artifact_id, snippet in COMMAND_SNIPPETS:
        position = job.find(snippet)
        if position < 0:
            blockers.append(f"missing_product_pages_command.{artifact_id}")
        positions.append((artifact_id, position))

    present_positions = [(artifact_id, position) for artifact_id, position in positions if position >= 0]
    ordered_positions = sorted(present_positions, key=lambda item: item[1])
    if present_positions != ordered_positions:
        blockers.append("product_pages_context_live_artifact_chain_order_invalid")

    for artifact_path in UPLOAD_ARTIFACTS:
        if f"\n            {artifact_path}\n" not in job:
            artifact_id = Path(artifact_path).stem.removeprefix("accurate_intake_").removesuffix("_ci")
            blockers.append(f"missing_product_pages_upload_artifact.{artifact_id}")

    for manifest_input in ACTIVATION_MANIFEST_INPUTS:
        if manifest_input not in job:
            blockers.append("missing_activation_manifest_input.context_live_diagnostic_dry_run_evaluator")

    return {
        "status": "pass" if not blockers else "fail",
        "checked_job": PRODUCT_PAGES_JOB,
        "blockers": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check pre-queue CI readiness invariants.")
    parser.add_argument("--workflow-file", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    workflow_path = Path(args.workflow_file)
    workflow_text = workflow_path.read_text(encoding="utf-8")
    report = build_report(workflow_text)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
