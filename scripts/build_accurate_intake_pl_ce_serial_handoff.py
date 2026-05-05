from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_pl_ce_serial_handoff import (  # noqa: E402
    build_pl_ce_serial_handoff_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_ACTIVATION_REVIEW_MANIFEST_PATH = (
    ROOT / "artifacts" / "accurate_intake_pl_ce_activation_review_manifest.json"
)
DEFAULT_STACK_JSON_PATH = ROOT / "artifacts" / "accurate_intake_pl_ce_pr_stack_metadata.json"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_pl_ce_serial_handoff.json"


def _read_payload(path: Path, *, missing_type: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "artifact_type": missing_type,
            "status": "missing",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    except json.JSONDecodeError:
        return {
            "artifact_type": f"invalid_{missing_type}",
            "status": "invalid_json",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    if not isinstance(payload, dict):
        return {
            "artifact_type": f"invalid_{missing_type}_shape",
            "status": "invalid_json_shape",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    payload["_source_artifact_path"] = str(path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build PL+CE serial PR handoff artifact for merge-owner review."
    )
    parser.add_argument(
        "--activation-review-manifest",
        default=str(DEFAULT_ACTIVATION_REVIEW_MANIFEST_PATH),
    )
    parser.add_argument("--stack-json", default=str(DEFAULT_STACK_JSON_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Return 0 after writing a blocked artifact. Use only for CI builder smokes.",
    )
    args = parser.parse_args(argv)

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_read_payload(
            Path(args.activation_review_manifest),
            missing_type="missing_activation_review_manifest",
        ),
        stack_metadata=_read_payload(
            Path(args.stack_json),
            missing_type="missing_pl_ce_pr_stack_metadata",
        ),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "blockers": artifact["blockers"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "ready_for_merge_owner_review" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
