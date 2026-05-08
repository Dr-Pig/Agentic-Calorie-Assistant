from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.current_shell_compatibility_ids import (  # noqa: E402
    CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_CLAIM_SCOPE,
    CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS,
    LEGACY_METADATA_FRESHNESS_ARTIFACT_TYPES,
    LEGACY_METADATA_FRESHNESS_CLAIM_SCOPES,
    LEGACY_METADATA_FRESHNESS_READY_STATUSES,
    matches_alias,
    set_legacy_alias_metadata,
)
from app.composition.accurate_intake_pl_ce_metadata_freshness_pack import (  # noqa: E402
    REQUIRED_PL_CE_METADATA_ARTIFACTS,
    build_pl_ce_metadata_freshness_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

DEFAULT_OUTPUT_PATH = (
    ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_metadata_freshness_pack.json"
)
DEFAULT_EVIDENCE_PATHS = {
    "context_quality_pack": ROOT / "artifacts" / "accurate_intake_context_quality_pack.json",
    "product_pages_visual_qa": ROOT / "artifacts" / "accurate_intake_product_pages_visual_qa.json",
    "pl_ce_local_review_decision_pack": ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_local_review_decision_pack.json",
    "pl_ce_local_mvp_candidate_bundle": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_local_mvp_candidate_bundle.json",
    "pl_ce_activation_review_manifest": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_activation_review_manifest.json",
    "ui_same_truth_render_contract": ROOT
    / "artifacts"
    / "accurate_intake_ui_same_truth_render_contract.json",
}


def _missing_payload(group_id: str, path: Path) -> dict[str, Any]:
    return {
        "artifact_type": "missing_pl_ce_metadata_freshness_input",
        "status": "missing",
        "group_id": group_id,
        "artifact_path": str(path),
        "generated_at_utc": "",
        "autofix_attempted": False,
        "ready_for_live_diagnostic_decision": False,
        "ready_for_fdb_integration": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def _invalid_payload(group_id: str, path: Path, error: Exception) -> dict[str, Any]:
    payload = _missing_payload(group_id, path)
    payload["artifact_type"] = "invalid_pl_ce_metadata_freshness_input"
    payload["status"] = "invalid"
    payload["read_error"] = type(error).__name__
    return payload


def _file_mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def _read_or_missing(group_id: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return _missing_payload(group_id, path)
    try:
        payload = read_json_artifact(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _invalid_payload(group_id, path, exc)
    payload.setdefault("artifact_path", str(path))
    payload.setdefault("file_mtime_utc", _file_mtime_utc(path))
    return payload


def build_legacy_metadata_freshness_report(
    *,
    path_overrides: dict[str, Path] | None = None,
    max_age_hours: int = 72,
) -> dict[str, Any]:
    evidence_paths = {
        group_id: Path(path_overrides.get(group_id, default_path)) if path_overrides else default_path
        for group_id, default_path in DEFAULT_EVIDENCE_PATHS.items()
    }
    evidence = {
        group_id: _read_or_missing(group_id, evidence_paths[group_id])
        for group_id in REQUIRED_PL_CE_METADATA_ARTIFACTS
    }
    return build_pl_ce_metadata_freshness_pack(
        evidence=evidence,
        max_age_hours=max_age_hours,
    )


def canonicalize_metadata_freshness_pack(pack: dict[str, Any]) -> dict[str, Any]:
    payload = dict(pack)
    status = str(payload.get("status") or "")
    if matches_alias(
        status,
        CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS,
        *LEGACY_METADATA_FRESHNESS_READY_STATUSES,
    ):
        payload["status"] = CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS
    payload["artifact_type"] = CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_ARTIFACT_TYPE
    payload["claim_scope"] = CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_CLAIM_SCOPE
    payload["producer_track"] = "CurrentShell"
    payload["intended_consumers"] = [
        "human_operator_review",
        "current_shell_serial_pr_planning",
    ]
    if payload.get("fooddb_dependency_status") == "not_required_for_pl_ce_metadata_freshness":
        payload["fooddb_dependency_status"] = (
            "not_required_for_current_shell_compatibility_metadata_freshness"
        )
    return set_legacy_alias_metadata(
        payload,
        legacy_artifact_types=LEGACY_METADATA_FRESHNESS_ARTIFACT_TYPES,
        legacy_statuses=LEGACY_METADATA_FRESHNESS_READY_STATUSES,
        legacy_claim_scopes=LEGACY_METADATA_FRESHNESS_CLAIM_SCOPES,
    )


def build_current_shell_compatibility_metadata_freshness_report(
    *,
    path_overrides: dict[str, Path] | None = None,
    max_age_hours: int = 72,
) -> dict[str, Any]:
    legacy_pack = build_legacy_metadata_freshness_report(
        path_overrides=path_overrides,
        max_age_hours=max_age_hours,
    )
    return canonicalize_metadata_freshness_pack(legacy_pack)


def _parse_artifact_overrides(values: list[str], parser: argparse.ArgumentParser) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            parser.error(f"--artifact must be group_id=path, got: {value}")
        group_id, raw_path = value.split("=", 1)
        if group_id not in DEFAULT_EVIDENCE_PATHS:
            parser.error(f"Unknown CurrentShell compatibility metadata group: {group_id}")
        overrides[group_id] = Path(raw_path)
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local CurrentShell compatibility metadata freshness pack."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Override an evidence path as group_id=path. May be passed multiple times.",
    )
    parser.add_argument("--max-age-hours", type=int, default=72)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    pack = build_current_shell_compatibility_metadata_freshness_report(
        path_overrides=_parse_artifact_overrides(args.artifact, parser),
        max_age_hours=args.max_age_hours,
    )
    write_json_artifact(Path(args.output), pack)
    summary = {
        "artifact": args.output,
        "status": pack["status"],
        "fresh_artifact_count": pack["fresh_artifact_count"],
        "required_artifact_count": pack["required_artifact_count"],
        "blockers": pack["blockers"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return (
        0
        if pack["status"] == CURRENT_SHELL_COMPATIBILITY_METADATA_FRESHNESS_READY_STATUS
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
