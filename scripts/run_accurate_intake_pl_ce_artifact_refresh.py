from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

DEFAULT_ARTIFACT_DIR = ROOT / "artifacts"
DEFAULT_REPORT_PATH = DEFAULT_ARTIFACT_DIR / "accurate_intake_pl_ce_artifact_refresh.json"
DEFAULT_REQUIRED_BROWSER_REPORT_PATH = (
    DEFAULT_ARTIFACT_DIR / "accurate_intake_pl_ce_artifact_refresh_required_browser.json"
)
READY_STATUS = "pl_ce_artifact_refresh_ready_for_human_review"


@dataclass(frozen=True)
class StepRunResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RefreshStep:
    step_id: str
    command: tuple[str, ...]
    output_path: Path
    expected_statuses: frozenset[str]
    browser_required: bool = False


RunStep = Callable[[RefreshStep], StepRunResult]
OUTPUT_EXCERPT_LIMIT = 2000


def _artifact_path(artifact_dir: Path, filename: str) -> Path:
    return artifact_dir / filename


def _python_command(python_executable: str, script: str, *args: str) -> tuple[str, ...]:
    return (python_executable, script, *args)


def _append_browser_flags(
    command: tuple[str, ...],
    *,
    require_browser_execution: bool,
    headed: bool,
    show_browser_flag: str = "--headed",
) -> tuple[str, ...]:
    updated = list(command)
    if require_browser_execution:
        updated.append("--require-browser-execution")
    if headed:
        updated.append(show_browser_flag)
    return tuple(updated)


def _local_review_artifact_args(paths: dict[str, Path]) -> list[str]:
    mapping = {
        "browser_shell_smoke": paths["browser_shell_smoke"],
        "browser_fixture_dogfood": paths["browser_fixture_dogfood"],
        "browser_realistic_dogfood": paths["browser_realistic_dogfood"],
        "fixture_full_product_loop_e2e": paths["fixture_full_product_loop_e2e"],
        "pl_ce_review_bundle": paths["pl_ce_review_bundle"],
        "context_review": paths["context_review"],
        "context_target_candidate_eval": paths["context_target_candidate_eval"],
        "context_replay_pack": paths["context_replay_pack"],
        "context_window_diagnostic": paths["context_window_diagnostic"],
        "context_quality_pack": paths["context_quality_pack"],
        "fixture_evidence_packet_emulator": paths["fixture_evidence_packet_emulator"],
        "fake_provider_tool_loop_smoke": paths["fake_provider_tool_loop_smoke"],
        "review_eval_candidate_pipeline": paths["review_eval_candidate_pipeline"],
        "local_operator_data_hygiene_bundle": paths["local_operator_data_hygiene_bundle"],
        "mvp_gate": paths["mvp_gate"],
    }
    args: list[str] = []
    for group_id, path in mapping.items():
        args.extend(["--artifact", f"{group_id}={path}"])
    return args


def _metadata_freshness_artifact_args(paths: dict[str, Path]) -> list[str]:
    mapping = {
        "context_quality_pack": paths["context_quality_pack"],
        "product_pages_visual_qa": paths["product_pages_visual_qa"],
        "pl_ce_local_review_decision_pack": paths["pl_ce_local_review_decision_pack"],
        "ui_same_truth_render_contract": paths["ui_same_truth_render_contract"],
    }
    args: list[str] = []
    for group_id, path in mapping.items():
        args.extend(["--artifact", f"{group_id}={path}"])
    return args


def build_refresh_steps(
    *,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    python_executable: str = sys.executable,
    require_browser_execution: bool = False,
    headed: bool = False,
    timeout_ms: int = 25000,
) -> tuple[RefreshStep, ...]:
    artifact_dir = Path(artifact_dir)
    paths = {
        "product_pages_short_term_context_smoke": _artifact_path(
            artifact_dir, "accurate_intake_product_pages_short_term_context_smoke.json"
        ),
        "context_quality_pack": _artifact_path(artifact_dir, "accurate_intake_context_quality_pack.json"),
        "context_review": _artifact_path(artifact_dir, "accurate_intake_context_review_artifact.json"),
        "context_target_candidate_eval": _artifact_path(
            artifact_dir, "accurate_intake_context_target_candidate_eval.json"
        ),
        "context_replay_pack": _artifact_path(artifact_dir, "accurate_intake_context_replay_pack.json"),
        "context_window_diagnostic": _artifact_path(
            artifact_dir, "accurate_intake_context_window_diagnostic.json"
        ),
        "browser_shell_smoke": _artifact_path(artifact_dir, "accurate_intake_browser_shell_smoke.json"),
        "browser_fixture_dogfood": _artifact_path(
            artifact_dir, "accurate_intake_browser_one_day_fixture_dogfood.json"
        ),
        "browser_realistic_dogfood": _artifact_path(
            artifact_dir, "accurate_intake_browser_realistic_web_dogfood_v2.json"
        ),
        "pl_ce_review_bundle": _artifact_path(
            artifact_dir, "accurate_intake_product_loop_review_bundle.json"
        ),
        "fixture_full_product_loop_e2e": _artifact_path(
            artifact_dir, "accurate_intake_fixture_full_product_loop_e2e.json"
        ),
        "fixture_evidence_packet_emulator": _artifact_path(
            artifact_dir, "accurate_intake_fixture_evidence_packet_emulator.json"
        ),
        "fake_provider_tool_loop_smoke": _artifact_path(
            artifact_dir, "accurate_intake_fake_provider_tool_loop_smoke.json"
        ),
        "review_eval_candidate_pipeline": _artifact_path(
            artifact_dir, "accurate_intake_review_eval_candidate_pipeline.json"
        ),
        "local_operator_data_hygiene_bundle": _artifact_path(
            artifact_dir, "accurate_intake_local_operator_data_hygiene_bundle.json"
        ),
        "ui_same_truth_render_contract": _artifact_path(
            artifact_dir, "accurate_intake_ui_same_truth_render_contract.json"
        ),
        "mvp_gate": _artifact_path(artifact_dir, "accurate_intake_mvp_gate.json"),
        "product_pages_visual_qa": _artifact_path(
            artifact_dir, "accurate_intake_product_pages_visual_qa.json"
        ),
        "pl_ce_local_review_evidence_manifest": _artifact_path(
            artifact_dir, "accurate_intake_pl_ce_local_review_evidence_manifest.json"
        ),
        "pl_ce_local_review_decision_pack": _artifact_path(
            artifact_dir, "accurate_intake_pl_ce_local_review_decision_pack.json"
        ),
        "pl_ce_metadata_freshness_pack": _artifact_path(
            artifact_dir, "accurate_intake_pl_ce_metadata_freshness_pack.json"
        ),
    }
    browser_timeout = str(timeout_ms)
    short_term_context = RefreshStep(
        step_id="product_pages_short_term_context_smoke",
        command=_append_browser_flags(
            _python_command(
                python_executable,
                "scripts/run_accurate_intake_product_pages_short_term_context_smoke.py",
                "--output",
                str(paths["product_pages_short_term_context_smoke"]),
                "--timeout-ms",
                browser_timeout,
            ),
            require_browser_execution=require_browser_execution,
            headed=headed,
            show_browser_flag="--show-browser",
        ),
        output_path=paths["product_pages_short_term_context_smoke"],
        expected_statuses=frozenset({"pass"}),
        browser_required=True,
    )
    steps: list[RefreshStep] = [
        short_term_context,
        RefreshStep(
            step_id="context_quality_pack",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_context_quality_pack.py",
                "--short-term-context-smoke",
                str(paths["product_pages_short_term_context_smoke"]),
                "--require-runtime-trace-input",
                "--output",
                str(paths["context_quality_pack"]),
            ),
            output_path=paths["context_quality_pack"],
            expected_statuses=frozenset({"context_quality_diagnostic_pass"}),
        ),
        RefreshStep(
            step_id="context_review",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_context_review_artifact.py",
                "--output",
                str(paths["context_review"]),
            ),
            output_path=paths["context_review"],
            expected_statuses=frozenset({"generated"}),
        ),
        RefreshStep(
            step_id="context_target_candidate_eval",
            command=_python_command(
                python_executable,
                "scripts/run_accurate_intake_context_target_candidate_eval.py",
                "--output",
                str(paths["context_target_candidate_eval"]),
            ),
            output_path=paths["context_target_candidate_eval"],
            expected_statuses=frozenset({"generated"}),
        ),
        RefreshStep(
            step_id="context_replay_pack",
            command=_python_command(
                python_executable,
                "scripts/run_accurate_intake_context_replay_pack.py",
                "--output",
                str(paths["context_replay_pack"]),
            ),
            output_path=paths["context_replay_pack"],
            expected_statuses=frozenset({"generated"}),
        ),
        RefreshStep(
            step_id="context_window_diagnostic",
            command=_python_command(
                python_executable,
                "scripts/run_accurate_intake_context_window_diagnostic.py",
                "--output",
                str(paths["context_window_diagnostic"]),
            ),
            output_path=paths["context_window_diagnostic"],
            expected_statuses=frozenset({"generated"}),
        ),
        RefreshStep(
            step_id="browser_shell_smoke",
            command=_append_browser_flags(
                _python_command(
                    python_executable,
                    "scripts/run_accurate_intake_browser_shell_smoke.py",
                    "--output",
                    str(paths["browser_shell_smoke"]),
                    "--timeout-ms",
                    browser_timeout,
                ),
                require_browser_execution=require_browser_execution,
                headed=headed,
            ),
            output_path=paths["browser_shell_smoke"],
            expected_statuses=frozenset({"pass"}),
            browser_required=True,
        ),
        RefreshStep(
            step_id="browser_fixture_dogfood",
            command=_append_browser_flags(
                _python_command(
                    python_executable,
                    "scripts/run_accurate_intake_browser_one_day_fixture_dogfood.py",
                    "--output",
                    str(paths["browser_fixture_dogfood"]),
                    "--timeout-ms",
                    browser_timeout,
                ),
                require_browser_execution=require_browser_execution,
                headed=headed,
            ),
            output_path=paths["browser_fixture_dogfood"],
            expected_statuses=frozenset({"browser_fixture_pass"}),
            browser_required=True,
        ),
        RefreshStep(
            step_id="browser_realistic_dogfood",
            command=_append_browser_flags(
                _python_command(
                    python_executable,
                    "scripts/run_accurate_intake_browser_realistic_web_dogfood_v2.py",
                    "--output",
                    str(paths["browser_realistic_dogfood"]),
                    "--timeout-ms",
                    browser_timeout,
                ),
                require_browser_execution=require_browser_execution,
                headed=headed,
            ),
            output_path=paths["browser_realistic_dogfood"],
            expected_statuses=frozenset(
                {
                    "browser_diagnostic_pass_with_fixture_evidence_gap",
                    "browser_diagnostic_pass_with_evidence_gap",
                }
            ),
            browser_required=True,
        ),
        RefreshStep(
            step_id="pl_ce_review_bundle",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_product_loop_review_bundle.py",
                "--browser-shell-smoke",
                str(paths["browser_shell_smoke"]),
                "--browser-fixture-dogfood",
                str(paths["browser_fixture_dogfood"]),
                "--browser-realistic-dogfood",
                str(paths["browser_realistic_dogfood"]),
                "--context-review",
                str(paths["context_review"]),
                "--context-target-candidate-eval",
                str(paths["context_target_candidate_eval"]),
                "--context-window-diagnostic",
                str(paths["context_window_diagnostic"]),
                "--output",
                str(paths["pl_ce_review_bundle"]),
            ),
            output_path=paths["pl_ce_review_bundle"],
            expected_statuses=frozenset({"product_loop_context_diagnostic_ready_for_human_review"}),
        ),
        RefreshStep(
            step_id="fixture_full_product_loop_e2e",
            command=_append_browser_flags(
                _python_command(
                    python_executable,
                    "scripts/run_accurate_intake_fixture_full_product_loop_e2e.py",
                    "--output",
                    str(paths["fixture_full_product_loop_e2e"]),
                    "--timeout-ms",
                    browser_timeout,
                ),
                require_browser_execution=require_browser_execution,
                headed=headed,
            ),
            output_path=paths["fixture_full_product_loop_e2e"],
            expected_statuses=frozenset({"fixture_product_loop_e2e_diagnostic_pass"}),
            browser_required=True,
        ),
        RefreshStep(
            step_id="fixture_evidence_packet_emulator",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_fixture_evidence_packet_emulator.py",
                "--output",
                str(paths["fixture_evidence_packet_emulator"]),
            ),
            output_path=paths["fixture_evidence_packet_emulator"],
            expected_statuses=frozenset({"fixture_packet_emulator_ready"}),
        ),
        RefreshStep(
            step_id="fake_provider_tool_loop_smoke",
            command=_python_command(
                python_executable,
                "scripts/run_accurate_intake_fake_provider_tool_loop_smoke.py",
                "--output",
                str(paths["fake_provider_tool_loop_smoke"]),
            ),
            output_path=paths["fake_provider_tool_loop_smoke"],
            expected_statuses=frozenset({"fake_provider_tool_loop_smoke_pass"}),
        ),
        RefreshStep(
            step_id="review_eval_candidate_pipeline",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_review_eval_candidate_pipeline.py",
                "--output",
                str(paths["review_eval_candidate_pipeline"]),
            ),
            output_path=paths["review_eval_candidate_pipeline"],
            expected_statuses=frozenset({"review_eval_candidate_pipeline_ready"}),
        ),
        RefreshStep(
            step_id="local_operator_data_hygiene_bundle",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_local_operator_data_hygiene_bundle.py",
                "--output",
                str(paths["local_operator_data_hygiene_bundle"]),
            ),
            output_path=paths["local_operator_data_hygiene_bundle"],
            expected_statuses=frozenset({"local_operator_data_hygiene_ready"}),
        ),
        RefreshStep(
            step_id="ui_same_truth_render_contract",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_ui_same_truth_render_contract.py",
                "--output",
                str(paths["ui_same_truth_render_contract"]),
            ),
            output_path=paths["ui_same_truth_render_contract"],
            expected_statuses=frozenset({"pass"}),
        ),
        RefreshStep(
            step_id="mvp_gate",
            command=_python_command(
                python_executable,
                "scripts/verify_accurate_intake_mvp.py",
                "--python",
                python_executable,
                "--output",
                str(paths["mvp_gate"]),
            ),
            output_path=paths["mvp_gate"],
            expected_statuses=frozenset({"pass"}),
        ),
        RefreshStep(
            step_id="product_pages_visual_qa",
            command=_append_browser_flags(
                _python_command(
                    python_executable,
                    "scripts/run_accurate_intake_product_pages_visual_qa.py",
                    "--output",
                    str(paths["product_pages_visual_qa"]),
                    "--screenshot-dir",
                    str(artifact_dir / "product_pages_visual_qa"),
                    "--timeout-ms",
                    browser_timeout,
                ),
                require_browser_execution=require_browser_execution,
                headed=headed,
            ),
            output_path=paths["product_pages_visual_qa"],
            expected_statuses=frozenset({"pass"}),
            browser_required=True,
        ),
        RefreshStep(
            step_id="pl_ce_local_review_gate",
            command=_python_command(
                python_executable,
                "scripts/run_accurate_intake_pl_ce_local_review_gate.py",
                *_local_review_artifact_args(paths),
                "--manifest-output",
                str(paths["pl_ce_local_review_evidence_manifest"]),
                "--decision-output",
                str(paths["pl_ce_local_review_decision_pack"]),
            ),
            output_path=paths["pl_ce_local_review_decision_pack"],
            expected_statuses=frozenset({"ready_for_human_pl_ce_review"}),
        ),
        RefreshStep(
            step_id="pl_ce_metadata_freshness_pack",
            command=_python_command(
                python_executable,
                "scripts/build_accurate_intake_pl_ce_metadata_freshness_pack.py",
                *_metadata_freshness_artifact_args(paths),
                "--output",
                str(paths["pl_ce_metadata_freshness_pack"]),
            ),
            output_path=paths["pl_ce_metadata_freshness_pack"],
            expected_statuses=frozenset({"metadata_freshness_ready_for_pl_ce_local_review"}),
        ),
    ]
    return tuple(steps)


def _run_subprocess_step(step: RefreshStep) -> StepRunResult:
    completed = subprocess.run(
        list(step.command),
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return StepRunResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _read_step_payload(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return read_json_artifact(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "artifact_type": "invalid_pl_ce_refresh_step_output",
            "status": "invalid",
            "read_error": type(exc).__name__,
        }


def _step_summary(step: RefreshStep, result: StepRunResult) -> tuple[dict[str, object], list[str]]:
    payload = _read_step_payload(step.output_path)
    artifact_status = str(payload.get("status") or "missing")
    blockers: list[str] = []
    if result.returncode != 0:
        blockers.append(f"{step.step_id}.returncode_{result.returncode}")
    if artifact_status not in step.expected_statuses:
        blockers.append(f"{step.step_id}.unexpected_status:{artifact_status}")
    stdout_excerpt = result.stdout[-OUTPUT_EXCERPT_LIMIT:] if blockers and result.stdout else ""
    stderr_excerpt = result.stderr[-OUTPUT_EXCERPT_LIMIT:] if blockers and result.stderr else ""
    artifact_blockers = payload.get("blockers") if isinstance(payload.get("blockers"), list) else []
    return (
        {
            "step_id": step.step_id,
            "command": list(step.command),
            "output_path": str(step.output_path),
            "returncode": result.returncode,
            "artifact_status": artifact_status,
            "artifact_blockers": artifact_blockers,
            "artifact_read_error": payload.get("read_error"),
            "stdout_excerpt": stdout_excerpt,
            "stderr_excerpt": stderr_excerpt,
            "expected_statuses": sorted(step.expected_statuses),
            "browser_required": step.browser_required,
            "blockers": blockers,
        },
        blockers,
    )


def run_pl_ce_artifact_refresh(
    *,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    output_path: Path | None = None,
    python_executable: str = sys.executable,
    require_browser_execution: bool = False,
    headed: bool = False,
    timeout_ms: int = 25000,
    fail_fast: bool = True,
    run_step: RunStep = _run_subprocess_step,
) -> dict[str, object]:
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_output_path = output_path or artifact_dir / "accurate_intake_pl_ce_artifact_refresh.json"
    steps = build_refresh_steps(
        artifact_dir=artifact_dir,
        python_executable=python_executable,
        require_browser_execution=require_browser_execution,
        headed=headed,
        timeout_ms=timeout_ms,
    )
    step_summaries: list[dict[str, object]] = []
    blockers: list[str] = []
    for step in steps:
        result = run_step(step)
        step_report, step_blockers = _step_summary(step, result)
        step_summaries.append(step_report)
        blockers.extend(step_blockers)
        if fail_fast and step_blockers:
            break
    status = READY_STATUS if not blockers and len(step_summaries) == len(steps) else "blocked"
    report = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_pl_ce_artifact_refresh",
        "claim_scope": "pl_ce_local_artifact_refresh_diagnostic",
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "artifact_dir": str(artifact_dir),
        "required_step_count": len(steps),
        "completed_step_count": len(step_summaries),
        "steps": step_summaries,
        "blockers": blockers,
        "fail_fast": fail_fast,
        "browser_execution_required": require_browser_execution,
        "diagnostic_only": True,
        "local_only": True,
        "fixture_only": True,
        "autofix_attempted": False,
        "ready_for_human_pl_ce_review": status == READY_STATUS,
        "ready_for_live_diagnostic_decision": False,
        "ready_for_fdb_integration": False,
        "shared_contract_changed": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "fooddb_evidence_used": False,
        "websearch_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }
    write_json_artifact(report_output_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh local PL+CE diagnostic artifacts and validate freshness."
    )
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--output", default=None)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=25000)
    parser.add_argument("--no-fail-fast", action="store_true")
    args = parser.parse_args(argv)

    default_output = DEFAULT_REQUIRED_BROWSER_REPORT_PATH if args.require_browser_execution else DEFAULT_REPORT_PATH
    output_path = Path(args.output) if args.output else default_output

    report = run_pl_ce_artifact_refresh(
        artifact_dir=Path(args.artifact_dir),
        output_path=output_path,
        python_executable=args.python,
        require_browser_execution=args.require_browser_execution,
        headed=args.headed,
        timeout_ms=args.timeout_ms,
        fail_fast=not args.no_fail_fast,
    )
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": report["status"],
                "completed_step_count": report["completed_step_count"],
                "required_step_count": report["required_step_count"],
                "blockers": report["blockers"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
