from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (  # noqa: E402
    REQUIRED_INPUTS,
    build_pl_ce_context_coverage_matrix_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_ARTIFACT_PATHS = {
    "context_conditioned_intent_wall": ROOT
    / "artifacts"
    / "accurate_intake_context_conditioned_intent_wall.json",
    "short_term_context_runtime_replay": ROOT
    / "artifacts"
    / "accurate_intake_short_term_context_runtime_replay.json",
    "fake_provider_context_smoke": ROOT / "artifacts" / "accurate_intake_fake_provider_context_smoke.json",
    "context_quality_pack": ROOT / "artifacts" / "accurate_intake_context_quality_pack.json",
}
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_pl_ce_context_coverage_matrix.json"


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
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    except json.JSONDecodeError:
        return {
            "artifact_type": "invalid_json",
            "status": "invalid_json",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    if not isinstance(payload, dict):
        return {
            "artifact_type": "invalid_json_shape",
            "status": "invalid_json_shape",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    payload["_source_artifact_path"] = str(path)
    return payload


def _inputs_from_paths(path_overrides: dict[str, Path]) -> dict[str, dict[str, Any]]:
    paths = {artifact_id: Path(path) for artifact_id, path in DEFAULT_ARTIFACT_PATHS.items()}
    paths.update(path_overrides)
    return {artifact_id: _read_payload(paths[artifact_id]) for artifact_id in REQUIRED_INPUTS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build PL+CE short-term context coverage matrix artifact."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        type=_parse_artifact_override,
        default=[],
        help="Override artifact input path as group_id=path. Repeatable.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    path_overrides = dict(args.artifact or [])
    unknown_artifact_groups = sorted(set(path_overrides) - set(REQUIRED_INPUTS))
    if unknown_artifact_groups:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "blockers": [
                        f"unknown_artifact_group:{group_id}"
                        for group_id in unknown_artifact_groups
                    ],
                },
                ensure_ascii=False,
            )
        )
        return 2

    artifact = build_pl_ce_context_coverage_matrix_artifact(**_inputs_from_paths(path_overrides))
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
