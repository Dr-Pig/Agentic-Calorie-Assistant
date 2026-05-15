from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.current_shell_browser_activation_evidence_gate import (  # noqa: E402
    REQUIRED_INPUTS,
    build_current_shell_browser_activation_evidence_gate_artifact,
)
from app.composition.current_shell_compatibility_ids import (  # noqa: E402
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    LEGACY_PRODUCT_PAGES_FLOW_GROUP_IDS,
    LEGACY_LOCAL_MVP_GROUP_IDS,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_ARTIFACT_PATHS = {
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_local_mvp_candidate_bundle.json",
    "product_pages_browser_smoke": ROOT
    / "artifacts"
    / "accurate_intake_product_pages_browser_smoke.json",
    "product_pages_seven_day_diary_smoke": ROOT
    / "artifacts"
    / "accurate_intake_product_pages_seven_day_diary_smoke.json",
    "product_pages_short_term_context_smoke": ROOT
    / "artifacts"
    / "accurate_intake_product_pages_short_term_context_smoke.json",
    "product_pages_target_candidate_ui_smoke": ROOT
    / "artifacts"
    / "accurate_intake_product_pages_target_candidate_ui_smoke.json",
    "product_pages_visual_qa": ROOT / "artifacts" / "accurate_intake_product_pages_visual_qa.json",
    "product_pages_body_noplan_degraded_smoke": ROOT
    / "artifacts"
    / "accurate_intake_product_pages_body_noplan_degraded_smoke.json",
    "body_observation_same_truth_gate": ROOT
    / "artifacts"
    / "accurate_intake_body_observation_same_truth_gate.json",
    "current_shell_fixture_e2e": ROOT
    / "artifacts"
    / "accurate_intake_current_shell_fixture_e2e.json",
    "product_pages_self_use_flow_gate": ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_product_pages_self_use_flow_gate.json",
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
        description="Build CurrentShell browser activation evidence gate from existing browser artifacts."
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
        default=(
            "artifacts/"
            "accurate_intake_current_shell_compatibility_browser_activation_evidence_gate.json"
        ),
    )
    args = parser.parse_args(argv)

    path_overrides = {
        (
            CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID
            if group_id in LEGACY_LOCAL_MVP_GROUP_IDS
            else "product_pages_self_use_flow_gate"
            if group_id in LEGACY_PRODUCT_PAGES_FLOW_GROUP_IDS
            else group_id
        ): path
        for group_id, path in dict(args.artifact or []).items()
    }
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
    artifact = build_current_shell_browser_activation_evidence_gate_artifact(
        build_input_artifacts(path_overrides=path_overrides)
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "all_required_browser_artifacts_executed": artifact[
                    "all_required_browser_artifacts_executed"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
