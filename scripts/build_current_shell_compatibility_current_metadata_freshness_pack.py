from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_pl_ce_current_metadata_freshness import (  # noqa: E402
    REQUIRED_CURRENT_CHAIN_ARTIFACTS,
    build_pl_ce_current_metadata_freshness_pack,
)
from app.composition.current_shell_compatibility_ids import (  # noqa: E402
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    LEGACY_ACTIVATION_REVIEW_GROUP_IDS,
    LEGACY_LOCAL_MVP_GROUP_IDS,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_EVIDENCE_PATHS = {
    "ui_same_truth_contract": ROOT / "artifacts" / "accurate_intake_ui_same_truth_render_contract.json",
    "context_quality_pack": ROOT / "artifacts" / "accurate_intake_context_quality_pack.json",
    "product_pages_visual_qa": ROOT / "artifacts" / "accurate_intake_product_pages_visual_qa.json",
    "product_pages_long_session_navigation_smoke": ROOT
    / "artifacts"
    / "accurate_intake_product_pages_long_session_navigation_smoke.json",
    "pl_ce_ui_context_alignment_pack": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_ui_context_alignment_pack.json",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_local_mvp_candidate_bundle.json",
    "pl_ce_product_pages_self_use_flow_gate": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_product_pages_self_use_flow_gate.json",
    "pl_ce_browser_activation_evidence_gate": ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_browser_activation_evidence_gate.json",
    "non_fooddb_manager_tool_contract": ROOT
    / "artifacts"
    / "accurate_intake_non_fooddb_manager_tool_contract.json",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID: ROOT
    / "artifacts"
    / "accurate_intake_pl_ce_activation_review_manifest.json",
}
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_current_metadata_freshness_pack.json"
)


def _fallback_payload(group_id: str, path: Path, *, status: str, error: str = "") -> dict[str, Any]:
    return {
        "artifact_type": f"{status}_pl_ce_current_metadata_input",
        "status": status,
        "group_id": group_id,
        "artifact_path": str(path),
        "_source_artifact_path": str(path),
        "generated_at_utc": "",
        "read_error": error,
        "autofix_attempted": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
    }


def _read_or_fallback(group_id: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return _fallback_payload(group_id, path, status="missing")
    try:
        payload = read_json_artifact(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fallback_payload(group_id, path, status="invalid", error=type(exc).__name__)
    payload.setdefault("_source_artifact_path", str(path))
    return payload


def build_current_shell_compatibility_current_metadata_freshness_report(
    *,
    path_overrides: dict[str, Path] | None = None,
    max_age_hours: int = 72,
) -> dict[str, Any]:
    paths = {
        group_id: Path(path_overrides[group_id]) if path_overrides and group_id in path_overrides else default_path
        for group_id, default_path in DEFAULT_EVIDENCE_PATHS.items()
    }
    evidence = {group_id: _read_or_fallback(group_id, paths[group_id]) for group_id in REQUIRED_CURRENT_CHAIN_ARTIFACTS}
    return build_pl_ce_current_metadata_freshness_pack(evidence=evidence, max_age_hours=max_age_hours)


def build_pl_ce_current_metadata_freshness_report(
    *,
    path_overrides: dict[str, Path] | None = None,
    max_age_hours: int = 72,
) -> dict[str, Any]:
    return build_current_shell_compatibility_current_metadata_freshness_report(
        path_overrides=path_overrides,
        max_age_hours=max_age_hours,
    )


def _parse_artifact_overrides(values: list[str], parser: argparse.ArgumentParser) -> dict[str, Path]:
    allowed_aliases = {
        **DEFAULT_EVIDENCE_PATHS,
        **{
            legacy_group_id: DEFAULT_EVIDENCE_PATHS[CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID]
            for legacy_group_id in LEGACY_LOCAL_MVP_GROUP_IDS
        },
        **{
            legacy_group_id: DEFAULT_EVIDENCE_PATHS[
                CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID
            ]
            for legacy_group_id in LEGACY_ACTIVATION_REVIEW_GROUP_IDS
        },
    }
    overrides: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            parser.error(f"--artifact must be group_id=path, got: {value}")
        group_id, raw_path = value.split("=", 1)
        if group_id not in allowed_aliases:
            parser.error(f"Unknown CurrentShell compatibility current metadata group: {group_id}")
        normalized_group_id = (
            CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID
            if group_id in LEGACY_LOCAL_MVP_GROUP_IDS
            else CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID
            if group_id in LEGACY_ACTIVATION_REVIEW_GROUP_IDS
            else group_id
        )
        overrides[normalized_group_id] = Path(raw_path)
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build CurrentShell compatibility current metadata freshness pack."
    )
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--max-age-hours", type=int, default=72)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    pack = build_current_shell_compatibility_current_metadata_freshness_report(
        path_overrides=_parse_artifact_overrides(args.artifact, parser),
        max_age_hours=args.max_age_hours,
    )
    write_json_artifact(Path(args.output), pack)
    print(json.dumps({"artifact": args.output, "status": pack["status"], "blockers": pack["blockers"]}, ensure_ascii=False))
    return 0 if pack["status"] == CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
