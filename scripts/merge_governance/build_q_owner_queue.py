from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.merge_governance.build_merge_debt_matrix import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    ROOT,
    build_matrix_from_prs,
    collect_open_prs,
    load_config,
)


DEFAULT_JSON_OUT = ROOT / "artifacts" / "q_owner_queue_status.json"
DEFAULT_MD_OUT = ROOT / "artifacts" / "q_owner_queue_status.md"
READY_MARKER = "READY_FOR_QUEUE"
ALLOWED_QUEUE_VERDICTS = {"merge_candidate", "dormant_shadow_candidate"}

WORKER_PROMPT = """You can continue development, push, open PRs, and fix CI, but do not bypass the official GitHub Merge Queue.

Rules:
1. Do not use the normal merge button or any admin/bypass merge path.
2. Do not enable direct auto-merge outside the official queue.
3. Do not force push or rebase.
4. If syncing main, use a non-destructive merge from origin/main; do not reset.
5. Add the Required Report to the PR body:
   track:
   runtime_truth_changed: false
   manager_context_packet_changed: false
   mutation_changed: false
   product_readiness_claimed: false
6. Add READY_FOR_QUEUE in the PR body.
7. After required checks pass, request promotion with GitHub's Add to merge queue action.
8. After adding to the queue, wait for the queue result; do not merge manually.
9. Future/shadow work must explicitly stay no-runtime, no-route, no-scheduler, no-DB-migration, no-ManagerContextPacket, and no-mutation.
10. Do not retarget or split stacked PRs unless the queue owner asks.
"""


def _has_ready_marker(body: str) -> bool:
    return READY_MARKER in body


def _queue_lane(entry: dict[str, Any]) -> str:
    verdict = str(entry.get("recommended_verdict") or "")
    if verdict == "merge_candidate":
        return "mainline"
    if verdict == "dormant_shadow_candidate":
        return "dormant_shadow"
    if verdict == "rebase_required":
        return "realign"
    return "blocked"


def _queue_status(entry: dict[str, Any], body: str) -> str:
    verdict = str(entry.get("recommended_verdict") or "")
    if verdict not in ALLOWED_QUEUE_VERDICTS:
        return "blocked_by_matrix"
    if not _has_ready_marker(body):
        return "waiting_for_ready_marker"
    return "ready_for_queue"


def _pass_fail(condition: bool) -> str:
    return "pass" if condition else "needs_review"


def _five_axis_status(entry: dict[str, Any]) -> dict[str, str]:
    verdict = str(entry.get("recommended_verdict") or "")
    lane = _queue_lane(entry)
    ci_status = str(entry.get("ci_status") or "")
    base_drift_status = str(entry.get("base_drift_status") or "")
    merge_state_status = str(entry.get("merge_state_status") or "")
    boundary_status = str(entry.get("boundary_status") or "")
    runtime_activation_status = str(entry.get("runtime_activation_status") or "")
    deterministic_status = str(entry.get("deterministic_boundary_status") or "")
    fat_file_status = str(entry.get("fat_file_status") or "")
    return {
        "product_lane": _pass_fail(lane in {"mainline", "dormant_shadow"}),
        "base_and_ci": _pass_fail(
            ci_status == "pass" and base_drift_status == "current" and merge_state_status in {"CLEAN", ""}
        ),
        "boundary_and_runtime": _pass_fail(boundary_status == "pass" and runtime_activation_status == "inactive"),
        "deterministic_boundary": _pass_fail(deterministic_status == "pass"),
        "size_and_reviewability": _pass_fail(fat_file_status in {"pass", "warning"} and verdict in ALLOWED_QUEUE_VERDICTS),
    }


def build_queue_report(matrix: dict[str, Any], *, pr_bodies: dict[int, str]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for entry in matrix.get("entries") or []:
        pr_number = int(entry.get("pr_number") or 0)
        body = pr_bodies.get(pr_number, "")
        queue_status = _queue_status(entry, body)
        entries.append(
            {
                "pr_number": pr_number,
                "title": str(entry.get("title") or ""),
                "url": str(entry.get("url") or ""),
                "track": str(entry.get("track") or ""),
                "head_branch": str(entry.get("head_branch") or ""),
                "base_branch": str(entry.get("base_branch") or ""),
                "recommended_verdict": str(entry.get("recommended_verdict") or ""),
                "queue_lane": _queue_lane(entry),
                "queue_status": queue_status,
                "five_axis_status": _five_axis_status(entry),
                "merge_state_status": str(entry.get("merge_state_status") or ""),
                "ci_status": str(entry.get("ci_status") or ""),
                "base_drift_status": str(entry.get("base_drift_status") or ""),
                "blocking_reasons": list(entry.get("blocking_reasons") or []),
            }
        )

    next_candidate = next((entry for entry in entries if entry["queue_status"] == "ready_for_queue"), None)
    return {
        "artifact_type": "q_owner_queue_status",
        "main_branch": str(matrix.get("main_branch") or "main"),
        "policy": {
            "parallel_build_allowed": True,
            "self_merge_allowed": False,
            "merge_queue_request_allowed": True,
            "ready_marker": READY_MARKER,
            "main_promotion_path": "official_github_merge_queue",
        },
        "script_mutates_repository": False,
        "worker_prompt": WORKER_PROMPT,
        "entry_count": len(entries),
        "next_candidate_pr_number": next_candidate["pr_number"] if next_candidate else None,
        "entries": entries,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Q-Owner Queue Status",
        "",
        f"- Main branch: `{report.get('main_branch')}`",
        f"- Ready marker: `{report['policy']['ready_marker']}`",
        f"- Script mutates repository: `{str(report.get('script_mutates_repository')).lower()}`",
        f"- Next candidate: `{report.get('next_candidate_pr_number')}`",
        "",
        "## Worker Prompt",
        "",
        "```text",
        str(report.get("worker_prompt") or "").rstrip(),
        "```",
        "",
        "| # | Track | Lane | Queue status | Five-axis | Verdict | Blocking reasons |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in report.get("entries") or []:
        blockers = ", ".join(entry.get("blocking_reasons") or []) or "-"
        five_axis = ", ".join(f"{key}={value}" for key, value in (entry.get("five_axis_status") or {}).items())
        lines.append(
            f"| #{entry['pr_number']} | `{entry['track']}` | `{entry['queue_lane']}` | "
            f"`{entry['queue_status']}` | {five_axis} | `{entry['recommended_verdict']}` | {blockers} |"
        )
    return "\n".join(lines) + "\n"


def _load_matrix_and_bodies(args: argparse.Namespace) -> tuple[dict[str, Any], dict[int, str]]:
    if args.matrix_json:
        return json.loads(args.matrix_json.read_text(encoding="utf-8")), {}
    config = load_config(args.config)
    prs = collect_open_prs(config=config, include_diffs=False, limit=args.limit)
    matrix = build_matrix_from_prs(prs, config)
    return matrix, {int(pr.get("number") or 0): str(pr.get("body") or "") for pr in prs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a non-mutating Q-owner queue status artifact.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--matrix-json", type=Path)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args(argv)

    matrix, pr_bodies = _load_matrix_and_bodies(args)
    report = build_queue_report(matrix, pr_bodies=pr_bodies)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json_report": str(args.json_out), "markdown_report": str(args.md_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
