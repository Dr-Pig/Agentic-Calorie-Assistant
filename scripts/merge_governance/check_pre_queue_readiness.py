from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
DEFAULT_OUTPUT = ROOT / "artifacts" / "pre_queue_readiness_report.json"

PRODUCT_PAGES_JOB = "product-pages-browser-e2e"
REQUIRED_JOB_SNIPPETS: tuple[tuple[str, str], ...] = (
    ("playwright_install", "python -m playwright install --with-deps chromium"),
    (
        "pytest_browser_wall",
        "python -m pytest tests/test_accurate_intake_product_pages_renderer_source_map.py "
        "tests/test_accurate_intake_product_pages_browser_smoke.py "
        "tests/test_accurate_intake_product_pages_short_term_context_smoke.py "
        "tests/test_accurate_intake_product_pages_target_candidate_ui_smoke.py "
        "tests/test_accurate_intake_product_pages_visual_qa.py "
        "tests/test_accurate_intake_product_pages_static.py "
        "tests/test_accurate_intake_static_cjk_copy_integrity.py -q",
    ),
    (
        "browser_smoke",
        "python scripts/run_accurate_intake_product_pages_browser_smoke.py --require-browser-execution "
        "--output artifacts/accurate_intake_product_pages_browser_smoke_ci.json --timeout-ms 25000",
    ),
    (
        "short_term_context_smoke",
        "python scripts/run_accurate_intake_product_pages_short_term_context_smoke.py --require-browser-execution "
        "--output artifacts/accurate_intake_product_pages_short_term_context_smoke_ci.json --timeout-ms 25000",
    ),
    (
        "target_candidate_ui_smoke",
        "python scripts/run_accurate_intake_product_pages_target_candidate_ui_smoke.py --require-browser-execution "
        "--output artifacts/accurate_intake_product_pages_target_candidate_ui_smoke_ci.json --timeout-ms 25000",
    ),
    (
        "visual_qa",
        "python scripts/run_accurate_intake_product_pages_visual_qa.py --require-browser-execution "
        "--output artifacts/accurate_intake_product_pages_visual_qa_ci.json "
        "--screenshot-dir artifacts/product_pages_visual_qa_ci --timeout-ms 25000",
    ),
    (
        "renderer_source_map",
        "python scripts/build_accurate_intake_product_pages_renderer_source_map.py "
        "--output artifacts/accurate_intake_product_pages_renderer_source_map_ci.json",
    ),
)

REQUIRED_UPLOAD_ARTIFACTS = (
    "artifacts/accurate_intake_product_pages_browser_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_short_term_context_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_target_candidate_ui_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_visual_qa_ci.json",
    "artifacts/accurate_intake_product_pages_renderer_source_map_ci.json",
    "artifacts/product_pages_visual_qa_ci",
)


def _job_block(workflow: str, job_name: str) -> str:
    marker = f"  {job_name}:"
    start = workflow.find(marker)
    if start < 0:
        return ""
    next_job = re.search(r"^\s{2}[A-Za-z0-9_-]+:\s*$", workflow[start + len(marker) :], re.MULTILINE)
    if next_job is None:
        return workflow[start:]
    return workflow[start : start + len(marker) + next_job.start()]


def build_report(workflow_text: str) -> dict[str, object]:
    blockers: list[str] = []
    advisories: list[str] = []

    if any(marker in workflow_text for marker in ("<<<<<<<", "=======", ">>>>>>>")):
        blockers.append("workflow_conflict_markers_present")

    job = _job_block(workflow_text, PRODUCT_PAGES_JOB)
    if not job:
        blockers.append(f"missing_job.{PRODUCT_PAGES_JOB}")
        return {
            "status": "fail",
            "checked_job": PRODUCT_PAGES_JOB,
            "blockers": blockers,
            "advisories": advisories,
        }

    for snippet_id, snippet in REQUIRED_JOB_SNIPPETS:
        if snippet not in job:
            blockers.append(f"missing_product_pages_command.{snippet_id}")

    for artifact_path in REQUIRED_UPLOAD_ARTIFACTS:
        if f"\n            {artifact_path}\n" not in job:
            artifact_id = Path(artifact_path).stem.removeprefix("accurate_intake_").removesuffix("_ci")
            blockers.append(f"missing_product_pages_upload_artifact.{artifact_id}")

    return {
        "status": "pass" if not blockers else "fail",
        "checked_job": PRODUCT_PAGES_JOB,
        "blockers": sorted(set(blockers)),
        "advisories": sorted(set(advisories)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check minimal browser merge readiness invariants.")
    parser.add_argument("--workflow-file", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--event-file", default=None)
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
