from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_pl_ce_local_mvp_candidate_bundle import (  # noqa: E402
    REQUIRED_INPUTS,
    build_pl_ce_local_mvp_candidate_bundle_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_ARTIFACT_PATHS = {
    "ui_same_truth_contract": ROOT / "artifacts" / "accurate_intake_ui_same_truth_render_contract.json",
    "context_quality_pack": ROOT / "artifacts" / "accurate_intake_context_quality_pack.json",
    "short_term_context_runtime_replay": ROOT
    / "artifacts"
    / "accurate_intake_short_term_context_runtime_replay.json",
    "context_coverage_matrix": ROOT / "artifacts" / "accurate_intake_pl_ce_context_coverage_matrix.json",
    "context_live_diagnostic_case_matrix": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_case_matrix.json",
    "context_live_diagnostic_anti_overfit_guard": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_anti_overfit_guard.json",
    "context_conditioned_intent_wall": ROOT
    / "artifacts"
    / "accurate_intake_context_conditioned_intent_wall_ci.json",
    "correction_removal_fixture_flow": ROOT
    / "artifacts"
    / "accurate_intake_correction_removal_fixture_flow_ci.json",
    "responder_input_contract_fake_smoke": ROOT
    / "artifacts"
    / "accurate_intake_responder_input_contract_fake_smoke_ci.json",
    "fixture_packet_emulator": ROOT / "artifacts" / "accurate_intake_fixture_evidence_packet_emulator.json",
    "fake_provider_tool_loop_smoke": ROOT / "artifacts" / "accurate_intake_fake_provider_tool_loop_smoke.json",
    "review_eval_candidate_pipeline": ROOT / "artifacts" / "accurate_intake_review_eval_candidate_pipeline.json",
    "local_operator_data_hygiene_bundle": ROOT
    / "artifacts"
    / "accurate_intake_local_operator_data_hygiene_bundle.json",
    "current_shell_fixture_e2e": ROOT
    / "artifacts"
    / "accurate_intake_current_shell_fixture_e2e.json",
    "mvp_gate_summary": ROOT / "artifacts" / "accurate_intake_mvp_gate.json",
}


def _parse_artifact_override(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--artifact must be formatted as group_id=path")
    group_id, path = value.split("=", 1)
    group_id = group_id.strip()
    if not group_id:
        raise argparse.ArgumentTypeError("artifact group_id cannot be empty")
    return group_id, Path(path.strip())


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "artifact_type": "missing",
            "status": "missing",
            "autofix_attempted": False,
            "_source_artifact_path": str(path),
        }
    except json.JSONDecodeError:
        return {
            "artifact_type": "invalid_json",
            "status": "invalid_json",
            "autofix_attempted": False,
            "_source_artifact_path": str(path),
        }
    if not isinstance(payload, dict):
        return {
            "artifact_type": "invalid_json_shape",
            "status": "invalid_json_shape",
            "autofix_attempted": False,
            "_source_artifact_path": str(path),
        }
    payload["_source_artifact_path"] = str(path)
    return payload


def build_input_artifacts(path_overrides: dict[str, Path] | None = None) -> dict[str, dict[str, Any]]:
    paths = {artifact_id: Path(path) for artifact_id, path in DEFAULT_ARTIFACT_PATHS.items()}
    paths.update(dict(path_overrides or {}))
    return {artifact_id: _read_payload(paths[artifact_id]) for artifact_id in REQUIRED_INPUTS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE local MVP candidate bundle from existing artifacts."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        type=_parse_artifact_override,
        default=[],
        help="Override artifact input path as group_id=path. Repeatable.",
    )
    parser.add_argument(
        "--optional-browser-artifact",
        help="Optional browser evidence path. Blocked browser is recorded as activation gap, not pass.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_pl_ce_local_mvp_candidate_bundle.json",
    )
    args = parser.parse_args(argv)

    path_overrides = dict(args.artifact or [])
    unknown_artifact_groups = sorted(set(path_overrides) - set(REQUIRED_INPUTS))
    if unknown_artifact_groups:
        print(
            json.dumps(
                {
                    "status": "invalid_arguments",
                    "unknown_artifact_groups": unknown_artifact_groups,
                    "autofix_attempted": False,
                },
                ensure_ascii=False,
            )
        )
        return 2
    input_artifacts = build_input_artifacts(path_overrides=path_overrides)
    if args.optional_browser_artifact:
        input_artifacts["optional_browser_evidence"] = _read_payload(
            Path(args.optional_browser_artifact)
        )
    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(input_artifacts)
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "activation_gate_status": artifact["activation_gate_status"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
