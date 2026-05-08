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
DEFAULT_CURRENT_METADATA_FRESHNESS_PATH = (
    ROOT / "artifacts" / "accurate_intake_pl_ce_current_metadata_freshness_pack.json"
)
DEFAULT_QUEUE_JSON_PATH = ROOT / "artifacts" / "accurate_intake_pl_ce_merge_queue_metadata.json"
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
        description="Build CurrentShell compatibility Merge Queue handoff artifact for review."
    )
    parser.add_argument(
        "--activation-review-manifest",
        default=str(DEFAULT_ACTIVATION_REVIEW_MANIFEST_PATH),
    )
    parser.add_argument(
        "--current-metadata-freshness-pack",
        default=str(DEFAULT_CURRENT_METADATA_FRESHNESS_PATH),
    )
    parser.add_argument("--queue-json", default=None)
    parser.add_argument(
        "--stack-json",
        default=None,
        help="Deprecated alias for --queue-json, kept for old local callers.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Return 0 after writing a blocked artifact. Use only for CI builder smokes.",
    )
    args = parser.parse_args(argv)
    queue_json_path = args.queue_json or args.stack_json or str(DEFAULT_QUEUE_JSON_PATH)

    artifact = build_pl_ce_serial_handoff_artifact(
        activation_review_manifest=_read_payload(
            Path(args.activation_review_manifest),
            missing_type="missing_activation_review_manifest",
        ),
        current_metadata_freshness_pack=_read_payload(
            Path(args.current_metadata_freshness_pack),
            missing_type="missing_current_shell_compatibility_current_metadata_freshness_pack",
        ),
        queue_metadata=_read_payload(
            Path(queue_json_path),
            missing_type="missing_current_shell_compatibility_merge_queue_metadata",
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
    return 0 if artifact["status"] == "ready_for_merge_queue_review" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
