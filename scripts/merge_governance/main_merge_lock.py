from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


READY_MARKER = "READY_FOR_QUEUE"
DEFAULT_MATRIX_PATH = Path("artifacts/merge_debt_matrix.json")


def _text(value: object) -> str:
    return str(value or "")


def _allowed_verdicts(*, allow_dormant_shadow: bool) -> list[str]:
    verdicts = ["merge_candidate"]
    if allow_dormant_shadow:
        verdicts.append("dormant_shadow_candidate")
    return verdicts


def _fat_file_allowed(entry: dict[str, Any], *, allow_dormant_shadow: bool) -> bool:
    fat_status = _text(entry.get("fat_file_status"))
    if fat_status == "pass":
        return True
    return (
        allow_dormant_shadow
        and _text(entry.get("recommended_verdict")) == "dormant_shadow_candidate"
        and fat_status == "warning"
    )


def evaluate_candidate(
    entry: dict[str, Any],
    *,
    pr_body: str,
    main_branch: str,
    allow_dormant_shadow: bool = False,
    require_ready_marker: bool = True,
) -> dict[str, Any]:
    allowed_verdicts = _allowed_verdicts(allow_dormant_shadow=allow_dormant_shadow)
    blockers: list[str] = []

    verdict = _text(entry.get("recommended_verdict"))
    if verdict not in allowed_verdicts:
        blockers.append(f"verdict_not_allowed:{verdict}")

    if require_ready_marker and READY_MARKER not in pr_body:
        blockers.append(f"missing_ready_marker:{READY_MARKER}")

    for reason in entry.get("blocking_reasons") or []:
        blockers.append(f"matrix_blocking_reason:{reason}")

    expected_values = {
        "base_branch": main_branch,
        "ci_status": "pass",
        "base_drift_status": "current",
        "boundary_status": "pass",
        "deterministic_boundary_status": "pass",
        "runtime_activation_status": "inactive",
        "merge_state_status": "CLEAN",
    }
    for key, expected in expected_values.items():
        actual = _text(entry.get(key))
        if actual != expected:
            if key == "base_branch":
                blockers.append(f"base_branch_not_{main_branch}:{actual}")
            elif key == "merge_state_status":
                blockers.append(f"merge_state_not_clean:{actual}")
            else:
                blockers.append(f"{key}_not_{expected}:{actual}")

    if bool(entry.get("is_draft")):
        blockers.append("draft_pr_not_mergeable")

    if not _fat_file_allowed(entry, allow_dormant_shadow=allow_dormant_shadow):
        blockers.append(f"fat_file_status_not_pass:{_text(entry.get('fat_file_status'))}")

    if verdict == "merge_candidate" and _text(entry.get("mainline_status")) != "mvp_mainline":
        blockers.append(f"mainline_status_not_mvp_mainline:{_text(entry.get('mainline_status'))}")
    if verdict == "dormant_shadow_candidate" and _text(entry.get("mainline_status")) != "future_shadow":
        blockers.append(f"mainline_status_not_future_shadow:{_text(entry.get('mainline_status'))}")

    return {
        "artifact_type": "main_merge_lock_candidate_evaluation",
        "pr_number": int(entry.get("pr_number") or 0),
        "status": "pass" if not blockers else "fail",
        "allowed_verdicts": allowed_verdicts,
        "recommended_verdict": verdict,
        "blocking_reasons": blockers,
        "head_branch": _text(entry.get("head_branch")),
        "base_branch": _text(entry.get("base_branch")),
    }


def _load_entry(matrix_path: Path, pr_number: int) -> dict[str, Any]:
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    for entry in matrix.get("entries") or []:
        if int(entry.get("pr_number") or 0) == pr_number:
            return entry
    raise ValueError(f"PR #{pr_number} not found in {matrix_path}")


def _assert_candidate(args: argparse.Namespace) -> int:
    entry = _load_entry(args.matrix_json, args.pr_number)
    pr_body = args.pr_body_file.read_text(encoding="utf-8") if args.pr_body_file else ""
    report = evaluate_candidate(
        entry,
        pr_body=pr_body,
        main_branch=args.main_branch,
        allow_dormant_shadow=args.allow_dormant_shadow,
        require_ready_marker=not args.no_ready_marker_required,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate whether a PR may pass the serialized main merge lock.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    assert_parser = subparsers.add_parser("assert-candidate")
    assert_parser.add_argument("--pr-number", type=int, required=True)
    assert_parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_PATH)
    assert_parser.add_argument("--pr-body-file", type=Path)
    assert_parser.add_argument("--main-branch", default="main")
    assert_parser.add_argument("--allow-dormant-shadow", action="store_true")
    assert_parser.add_argument("--no-ready-marker-required", action="store_true")
    assert_parser.set_defaults(func=_assert_candidate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
