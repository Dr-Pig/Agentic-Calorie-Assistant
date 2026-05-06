from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_pl_ce_activation_review_manifest import (  # noqa: E402
    REQUIRED_INPUTS,
    build_pl_ce_activation_review_manifest_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_ARTIFACT_PATHS = {
    "pl_ce_local_mvp_candidate_bundle": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_local_mvp_candidate_bundle.json",
    "pl_ce_browser_activation_evidence_gate": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_browser_activation_evidence_gate.json",
    "pl_ce_ui_context_alignment_pack": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_ui_context_alignment_pack.json",
    "context_live_diagnostic_dry_run_evaluator": ROOT
    / "artifacts"
    / "accurate_intake_context_live_diagnostic_dry_run_evaluator.json",
    "context_live_response_contract_dry_run": ROOT
    / "artifacts"
    / "accurate_intake_context_live_response_contract_dry_run.json",
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
    paths = {group_id: Path(path) for group_id, path in DEFAULT_ARTIFACT_PATHS.items()}
    paths.update(dict(path_overrides or {}))
    return {group_id: _read_payload(paths[group_id]) for group_id in REQUIRED_INPUTS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE activation review manifest from existing gate artifacts."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        type=_parse_artifact_override,
        default=[],
        help="Override artifact input path as group_id=path. Repeatable.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_pl_ce_activation_review_manifest.json",
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

    artifact = build_pl_ce_activation_review_manifest_artifact(
        build_input_artifacts(path_overrides=path_overrides)
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "human_review_required": artifact["human_review_required"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
