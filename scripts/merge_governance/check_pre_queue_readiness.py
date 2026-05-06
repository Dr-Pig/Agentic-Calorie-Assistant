from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.merge_governance.build_merge_debt_matrix import REQUIRED_TRACK_REPORT_KEYS, extract_track_report  # noqa: E402

DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
DEFAULT_OUTPUT = ROOT / "artifacts" / "pre_queue_readiness_report.json"


PRODUCT_PAGES_JOB = "product-pages-browser-e2e"

COMMAND_SNIPPETS = (
    (
        "product_pages_long_session_navigation_smoke",
        "run_accurate_intake_product_pages_long_session_navigation_smoke.py --require-browser-execution "
        "--output artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json",
    ),
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
        "context_live_diagnostic_holdout_plan",
        "build_accurate_intake_context_live_diagnostic_holdout_plan.py --matrix-json "
        "artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json --anti-overfit-json "
        "artifacts/accurate_intake_context_live_diagnostic_anti_overfit_guard_ci.json --output "
        "artifacts/accurate_intake_context_live_diagnostic_holdout_plan_ci.json",
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
    (
        "pl_ce_product_pages_self_use_flow_gate",
        "build_accurate_intake_pl_ce_product_pages_self_use_flow_gate.py",
    ),
    (
        "context_live_diagnostic_gate",
        "run_accurate_intake_context_live_diagnostic_gate.py --artifact-dir artifacts --output "
        "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json",
    ),
    (
        "pl_ce_current_metadata_freshness_pack",
        "build_accurate_intake_pl_ce_current_metadata_freshness_pack.py",
    ),
    (
        "pl_ce_serial_handoff",
        "build_accurate_intake_pl_ce_serial_handoff.py",
    ),
)

UPLOAD_ARTIFACTS = (
    "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_holdout_plan_ci.json",
    "artifacts/accurate_intake_context_live_provider_input_preflight_ci.json",
    "artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json",
    "artifacts/accurate_intake_pl_ce_product_pages_self_use_flow_gate_ci.json",
    "artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json",
    "artifacts/accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json",
    "artifacts/accurate_intake_pl_ce_serial_handoff_ci.json",
)

ACTIVATION_MANIFEST_INPUTS = (
    "--artifact context_live_diagnostic_dry_run_evaluator="
    "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json",
    "--artifact context_live_diagnostic_holdout_plan="
    "artifacts/accurate_intake_context_live_diagnostic_holdout_plan_ci.json",
    "--artifact context_live_diagnostic_gate="
    "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json",
)

SERIAL_HANDOFF_INPUTS = (
    (
        "current_metadata_freshness_pack",
        "--current-metadata-freshness-pack "
        "artifacts/accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json",
    ),
)

CURRENT_METADATA_INPUTS = (
    (
        "product_pages_long_session_navigation_smoke",
        "--artifact product_pages_long_session_navigation_smoke="
        "artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json",
    ),
    (
        "pl_ce_ui_context_alignment_pack",
        "--artifact pl_ce_ui_context_alignment_pack="
        "artifacts/accurate_intake_pl_ce_ui_context_alignment_pack_ci.json",
    ),
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


def _command_block(job: str, command_snippet: str) -> str:
    start = job.find(command_snippet)
    if start < 0:
        return ""
    next_command = job.find("\n          python ", start + len(command_snippet))
    if next_command < 0:
        return job[start:]
    return job[start:next_command]


def _track_report_blockers_from_event(event_path: Path | None) -> list[str]:
    if event_path is None or not event_path.exists():
        return []
    event = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return []
    title = str(pull_request.get("title") or "")
    head = pull_request.get("head") if isinstance(pull_request.get("head"), dict) else {}
    head_ref = str(head.get("ref") or "")
    if head_ref.startswith("dependabot/") or title.lower().startswith("bump "):
        return []
    flags = extract_track_report(str(pull_request.get("body") or ""))
    return [f"missing_track_report_key:{key}" for key in REQUIRED_TRACK_REPORT_KEYS if key not in flags]


def build_report(workflow_text: str, *, event_path: Path | None = None) -> dict[str, Any]:
    blockers: list[str] = []
    if any(marker in workflow_text for marker in ("<<<<<<<", "=======", ">>>>>>>")):
        blockers.append("workflow_conflict_markers_present")
    blockers.extend(_track_report_blockers_from_event(event_path))

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
            artifact_id = manifest_input.split("=", 1)[0].removeprefix("--artifact ")
            blockers.append(f"missing_activation_manifest_input.{artifact_id}")
    for artifact_id, serial_input in SERIAL_HANDOFF_INPUTS:
        if serial_input not in job:
            blockers.append(f"missing_serial_handoff_input.{artifact_id}")
    current_metadata_block = _command_block(
        job,
        "python scripts/build_accurate_intake_pl_ce_current_metadata_freshness_pack.py",
    )
    for artifact_id, metadata_input in CURRENT_METADATA_INPUTS:
        if metadata_input not in current_metadata_block:
            blockers.append(f"missing_current_metadata_input.{artifact_id}")

    return {
        "status": "pass" if not blockers else "fail",
        "checked_job": PRODUCT_PAGES_JOB,
        "blockers": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check pre-queue CI readiness invariants.")
    parser.add_argument("--workflow-file", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--event-file", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    workflow_path = Path(args.workflow_file)
    workflow_text = workflow_path.read_text(encoding="utf-8")
    event_path = Path(args.event_file) if args.event_file else None
    report = build_report(workflow_text, event_path=event_path)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
