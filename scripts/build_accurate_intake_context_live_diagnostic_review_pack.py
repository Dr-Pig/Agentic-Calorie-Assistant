from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_review_pack import (  # noqa: E402
    REQUIRED_INPUTS,
    build_context_live_diagnostic_review_pack_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_ARTIFACT_PATHS = {
    "context_live_diagnostic_case_matrix": (
        ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_case_matrix.json"
    ),
    "context_live_diagnostic_anti_overfit_guard": (
        ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_anti_overfit_guard.json"
    ),
    "context_live_provider_input_preflight": (
        ROOT / "artifacts" / "accurate_intake_context_live_provider_input_preflight.json"
    ),
    "context_live_response_contract_dry_run": (
        ROOT / "artifacts" / "accurate_intake_context_live_response_contract_dry_run.json"
    ),
    "context_live_diagnostic_canary": (
        ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_canary.json"
    ),
}
DEFAULT_OUTPUT_PATH = (
    ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_review_pack.json"
)


def _parse_artifact_override(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--artifact must use group_id=path")
    group_id, path_text = value.split("=", 1)
    group_id = group_id.strip()
    if group_id not in REQUIRED_INPUTS:
        allowed = ", ".join(REQUIRED_INPUTS)
        raise argparse.ArgumentTypeError(f"unknown artifact group {group_id!r}; expected one of {allowed}")
    path = Path(path_text.strip())
    return group_id, path


def _read_payload(group_id: str, path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "artifact_type": "missing",
            "status": "missing",
            "autofix_attempted": False,
            "_source_artifact_path": str(path),
        }
    except json.JSONDecodeError as exc:
        return {
            "artifact_type": "invalid_json",
            "status": "invalid_json",
            "json_error": str(exc),
            "autofix_attempted": False,
            "_source_artifact_path": str(path),
        }
    result = dict(payload) if isinstance(payload, dict) else {
        "artifact_type": "invalid_json_shape",
        "status": "invalid_json_shape",
        "autofix_attempted": False,
    }
    result.setdefault("_source_artifact_path", str(path))
    result.setdefault("_artifact_group_id", group_id)
    return result


def _input_paths(overrides: list[tuple[str, Path]]) -> dict[str, Path]:
    paths = dict(DEFAULT_ARTIFACT_PATHS)
    for group_id, path in overrides:
        paths[group_id] = path
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context live diagnostic review pack from local artifacts."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        type=_parse_artifact_override,
        help="Override an input artifact path as group_id=path.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    paths = _input_paths(args.artifact)
    inputs = {
        group_id: _read_payload(group_id, paths[group_id])
        for group_id in REQUIRED_INPUTS
    }
    artifact = build_context_live_diagnostic_review_pack_artifact(inputs)
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0 if artifact["status"].startswith("context_live_diagnostic_review_ready_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
