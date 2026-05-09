from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BROWSER_PATH_PREFIXES = (
    ".github/workflows/ci.yml",
    "static/accurate-intake-",
    "scripts/run_accurate_intake_product_pages_",
    "scripts/build_accurate_intake_product_pages_",
    "tests/test_accurate_intake_product_pages_",
    "tests/test_current_shell_compatibility_browser_activation",
    "tests/test_current_shell_compatibility_product_pages",
)
BROWSER_PATH_SUBSTRINGS = (
    "product_pages",
    "today_macro",
    "body_observation_same_truth",
    "clarify_commit_correction_same_truth",
    "browser_activation",
    "ui_same_truth",
    "renderer_source",
)
BROWSER_DIFF_TOKENS = (
    "show_macro",
    "macro_guard_reason",
    "renderer_input_basis",
    "coach_message",
    "renderer_output",
    "source_map",
    "target_candidate",
    "pending_followup",
    "body_plan_read_model",
    "body_budget_read_model",
    "consumed_",
)
FAST_PASS_PREFIXES = (
    "docs/",
    "app/memory/application/runtime_lab_",
    "app/recommendation/application/summary_consumer_",
    "app/rescue/application/shadow_",
    "app/nutrition/",
    "scripts/run_runtime_lab_",
    "scripts/build_runtime_lab_",
    "scripts/build_accurate_intake_approved_packet_ready_fooddb_artifact.py",
    "tests/test_runtime_lab_memory_",
    "tests/test_recommendation_shadow_summary_consumer.py",
    "tests/test_rescue_shadow_summary_context.py",
    "tests/test_proactive_no_send_summary_consumer.py",
    "tests/test_accurate_intake_approved_packet_ready_fooddb_artifact.py",
)
FAST_PASS_EXACT = {
    "app/rescue/domain/shadow_status.py",
    "app/memory/application/runtime_lab_downstream_boundary.py",
    "app/runtime/application/proactive_summary_consumer.py",
    "tests/test_sidecar_offline_activation_guard.py",
}


def select_mode(
    *,
    changed_files: list[str],
    diff_text: str,
    event_name: str,
    diff_error: str = "",
) -> dict[str, Any]:
    normalized = [path.replace("\\", "/") for path in changed_files]
    if event_name == "push":
        return _decision(
            "full",
            "main push keeps full browser guard",
            normalized,
            matched_paths=[],
            matched_diff_tokens=[],
            event_name=event_name,
            diff_error=diff_error,
        )
    if diff_error:
        return _decision(
            "full",
            "diff collection failed; defaulting to full browser run",
            normalized,
            matched_paths=[],
            matched_diff_tokens=[],
            event_name=event_name,
            diff_error=diff_error,
        )

    matched_paths = [path for path in normalized if _is_browser_path(path)]
    matched_tokens = [token for token in BROWSER_DIFF_TOKENS if token in diff_text]
    if matched_paths or matched_tokens:
        return _decision(
            "full",
            "changed files or diff touch product page browser surface",
            normalized,
            matched_paths=matched_paths,
            matched_diff_tokens=matched_tokens,
            event_name=event_name,
            diff_error=diff_error,
        )

    if normalized and all(_is_fast_pass_path(path) for path in normalized):
        return _decision(
            "fast_pass",
            "changed files are browser-unrelated",
            normalized,
            matched_paths=[],
            matched_diff_tokens=[],
            event_name=event_name,
            diff_error=diff_error,
        )

    return _decision(
        "full",
        "unknown active code change defaults to full browser run",
        normalized,
        matched_paths=[],
        matched_diff_tokens=[],
        event_name=event_name,
        diff_error=diff_error,
    )


def _decision(
    mode: str,
    reason: str,
    changed_files: list[str],
    *,
    matched_paths: list[str],
    matched_diff_tokens: list[str],
    event_name: str,
    diff_error: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "product_pages_browser_e2e_selection",
        "mode": mode,
        "reason": reason,
        "event_name": event_name,
        "changed_files": changed_files,
        "matched_paths": matched_paths,
        "matched_diff_tokens": matched_diff_tokens,
        "diff_error": diff_error,
    }


def _is_browser_path(path: str) -> bool:
    if any(path.startswith(prefix) or path == prefix for prefix in BROWSER_PATH_PREFIXES):
        return True
    return path.startswith(("app/composition/", "tests/")) and any(
        marker in path for marker in BROWSER_PATH_SUBSTRINGS
    )


def _is_fast_pass_path(path: str) -> bool:
    return path in FAST_PASS_EXACT or any(path.startswith(prefix) for prefix in FAST_PASS_PREFIXES)


def _git_text(args: list[str]) -> tuple[str, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return "", completed.stderr.strip() or completed.stdout.strip()
    return completed.stdout, ""


def collect_changed_files(base_ref: str, head_ref: str) -> tuple[list[str], str]:
    if not base_ref:
        return [], "missing base ref"
    output, error = _git_text(["diff", "--name-only", "--diff-filter=ACMRT", base_ref, head_ref])
    return [line.strip() for line in output.splitlines() if line.strip()], error


def collect_diff_text(base_ref: str, head_ref: str) -> tuple[str, str]:
    if not base_ref:
        return "", "missing base ref"
    return _git_text(["diff", "--unified=0", base_ref, head_ref])


def _write_github_output(path: str, decision: dict[str, Any]) -> None:
    if not path:
        return
    output_path = Path(path)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(f"mode={decision['mode']}\n")
        handle.write(f"reason={decision['reason']}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select product-pages-browser-e2e full or fast-pass mode.")
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", default="")
    args = parser.parse_args(argv)

    changed_files, file_error = collect_changed_files(args.base_ref, args.head_ref)
    diff_text, diff_error = collect_diff_text(args.base_ref, args.head_ref)
    decision = select_mode(
        changed_files=changed_files,
        diff_text=diff_text,
        event_name=args.event_name,
        diff_error=file_error or diff_error,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_github_output(args.github_output, decision)
    print(json.dumps(decision, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
