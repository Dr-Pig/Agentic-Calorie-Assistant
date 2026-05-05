from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


READY_MARKER = "READY_FOR_QUEUE"
DEFAULT_MATRIX_PATH = Path("artifacts/merge_debt_matrix.json")
DEFAULT_CONFIG_PATH = ROOT / ".merge-governance.yml"
DEFAULT_REQUIRED_CHECKS = [
    "repo-hygiene-and-architecture",
    "pre-edd-readiness",
    "runtime-contract-tests",
    "wave1-phase-a-contracts",
    "wave1-phase-b-contracts",
]
DEFAULT_ADVISORY_CHECKS = ["phase-c-environment-gate", "accurate-intake-mvp-gate"]
SUCCESS_CONCLUSIONS = {"SUCCESS", "SKIPPED", "NEUTRAL"}
FAIL_CONCLUSIONS = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
RETRYABLE_MERGE_STATES = {"UNKNOWN", "UNSTABLE", "BLOCKED"}


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


def expected_lock_check_names(config: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("required_checks", "advisory_checks"):
        for name in config.get(key) or []:
            text = _text(name)
            if text and text not in names:
                names.append(text)
    return names


def load_lock_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config: dict[str, Any] = {
        "required_checks": list(DEFAULT_REQUIRED_CHECKS),
        "advisory_checks": list(DEFAULT_ADVISORY_CHECKS),
    }
    if not path.exists():
        return config

    current_key: str | None = None
    parsed: dict[str, list[str]] = {"required_checks": [], "advisory_checks": []}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            key, _, value = line.partition(":")
            current_key = key.strip()
            if current_key in parsed and value.strip():
                parsed[current_key].append(value.strip().strip('"').strip("'"))
            continue
        if current_key in parsed and line.strip().startswith("- "):
            parsed[current_key].append(line.strip()[2:].strip().strip('"').strip("'"))

    for key, values in parsed.items():
        if values:
            config[key] = values
    return config


def _check_name(check: dict[str, Any]) -> str:
    return _text(check.get("name") or check.get("context"))


def _check_is_pass(check: dict[str, Any]) -> bool:
    status = _text(check.get("status")).upper()
    conclusion = _text(check.get("conclusion")).upper()
    state = _text(check.get("state")).upper()
    if state:
        return state in SUCCESS_CONCLUSIONS
    return status == "COMPLETED" and conclusion in SUCCESS_CONCLUSIONS


def _check_is_fail(check: dict[str, Any]) -> bool:
    conclusion = _text(check.get("conclusion")).upper()
    state = _text(check.get("state")).upper()
    if state:
        return state not in {"", "PENDING"} and state not in SUCCESS_CONCLUSIONS
    return conclusion in FAIL_CONCLUSIONS or (
        _text(check.get("status")).upper() == "COMPLETED"
        and conclusion != ""
        and conclusion not in SUCCESS_CONCLUSIONS
    )


def evaluate_wait_readiness(pr: dict[str, Any], *, expected_checks: list[str]) -> dict[str, Any]:
    merge_state = _text(pr.get("mergeStateStatus")).upper()
    checks = pr.get("statusCheckRollup") or []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for check in checks:
        name = _check_name(check)
        if name:
            by_name.setdefault(name, []).append(check)

    pending: list[str] = []
    failed: list[str] = []
    for expected in expected_checks:
        matches = by_name.get(expected) or []
        if not matches:
            pending.append(f"missing_check:{expected}")
            continue
        if any(_check_is_fail(check) for check in matches):
            failed.append(f"failed_check:{expected}")
        elif not any(_check_is_pass(check) for check in matches):
            pending.append(f"pending_check:{expected}")

    merge_blocker = ""
    if merge_state != "CLEAN":
        merge_blocker = f"merge_state_not_clean:{merge_state or 'UNKNOWN'}"
        if merge_state not in RETRYABLE_MERGE_STATES:
            failed.append(merge_blocker)
        else:
            pending.append(merge_blocker)

    if failed:
        status = "fail"
    elif pending:
        status = "pending"
    else:
        status = "pass"

    return {
        "artifact_type": "main_merge_lock_wait_readiness",
        "status": status,
        "merge_state_status": merge_state,
        "expected_checks": expected_checks,
        "pending_reasons": pending,
        "failed_reasons": failed,
    }


def _load_pr_readiness(pr_number: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "mergeStateStatus,statusCheckRollup",
        ],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"failed to load PR #{pr_number}")
    return json.loads(completed.stdout)


def _wait_ready(args: argparse.Namespace) -> int:
    config = load_lock_config(args.config)
    expected_checks = expected_lock_check_names(config)
    deadline = time.monotonic() + args.timeout_seconds
    attempt = 0
    while True:
        attempt += 1
        report = evaluate_wait_readiness(_load_pr_readiness(args.pr_number), expected_checks=expected_checks)
        print(json.dumps({"attempt": attempt, **report}, ensure_ascii=False, indent=2))
        if report["status"] == "pass":
            return 0
        if report["status"] == "fail":
            return 1
        if time.monotonic() >= deadline:
            print("Timed out waiting for PR checks and clean merge state.", file=sys.stderr)
            return 1
        time.sleep(args.interval_seconds)


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

    wait_parser = subparsers.add_parser("wait-ready")
    wait_parser.add_argument("--pr-number", type=int, required=True)
    wait_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    wait_parser.add_argument("--timeout-seconds", type=int, default=900)
    wait_parser.add_argument("--interval-seconds", type=int, default=15)
    wait_parser.set_defaults(func=_wait_ready)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
