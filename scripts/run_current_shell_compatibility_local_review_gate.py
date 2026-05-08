from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.current_shell_compatibility_ids import (  # noqa: E402
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402
from scripts.build_current_shell_compatibility_local_review_decision_pack import (  # noqa: E402
    build_current_shell_compatibility_local_review_decision_pack,
)
from scripts.build_current_shell_compatibility_local_review_evidence_manifest import (  # noqa: E402
    DEFAULT_EVIDENCE_PATHS,
    build_current_shell_compatibility_local_review_evidence_manifest,
)

DEFAULT_MANIFEST_OUTPUT = (
    ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_local_review_evidence_manifest.json"
)
DEFAULT_DECISION_OUTPUT = (
    ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_local_review_decision_pack.json"
)


def _parse_artifact_overrides(values: list[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--artifact must be group_id=path, got: {value}")
        group_id, raw_path = value.split("=", 1)
        if group_id not in DEFAULT_EVIDENCE_PATHS:
            raise ValueError(f"Unknown CurrentShell compatibility evidence group: {group_id}")
        overrides[group_id] = Path(raw_path)
    return overrides


def run_current_shell_compatibility_local_review_gate(
    *,
    manifest_output: Path,
    decision_output: Path,
    path_overrides: dict[str, Path] | None = None,
) -> dict[str, object]:
    manifest = build_current_shell_compatibility_local_review_evidence_manifest(
        path_overrides=path_overrides
    )
    decision_pack = build_current_shell_compatibility_local_review_decision_pack(manifest)
    write_json_artifact(manifest_output, manifest)
    write_json_artifact(decision_output, decision_pack)

    manifest_metadata = manifest["_manifest_metadata"]
    return {
        "manifest": str(manifest_output),
        "decision_pack": str(decision_output),
        "manifest_status": manifest_metadata["status"],
        "decision_status": decision_pack["status"],
        "missing_evidence": decision_pack["missing_evidence"],
        "blockers": decision_pack["blockers"],
    }


def run_pl_ce_local_review_gate(
    *,
    manifest_output: Path,
    decision_output: Path,
    path_overrides: dict[str, Path] | None = None,
) -> dict[str, object]:
    return run_current_shell_compatibility_local_review_gate(
        manifest_output=manifest_output,
        decision_output=decision_output,
        path_overrides=path_overrides,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local CurrentShell compatibility review evidence manifest "
            "and decision gate."
        )
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Override an evidence path as group_id=path. May be passed multiple times.",
    )
    parser.add_argument("--manifest-output", default=str(DEFAULT_MANIFEST_OUTPUT))
    parser.add_argument("--decision-output", default=str(DEFAULT_DECISION_OUTPUT))
    args = parser.parse_args(argv)

    try:
        path_overrides = _parse_artifact_overrides(args.artifact)
    except ValueError as exc:
        parser.error(str(exc))
    summary = run_current_shell_compatibility_local_review_gate(
        manifest_output=Path(args.manifest_output),
        decision_output=Path(args.decision_output),
        path_overrides=path_overrides,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return (
        0
        if summary["manifest_status"] == "complete"
        and summary["decision_status"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
