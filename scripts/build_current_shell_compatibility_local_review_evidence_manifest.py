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
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPE,
    LEGACY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPES,
    set_legacy_alias_metadata,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.build_current_shell_compatibility_local_review_decision_pack import (  # noqa: E402
    REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE,
)

DEFAULT_EVIDENCE_PATHS = {
    "browser_shell_smoke": ROOT / "artifacts" / "accurate_intake_browser_shell_smoke.json",
    "browser_fixture_dogfood": ROOT / "artifacts" / "accurate_intake_browser_one_day_fixture_dogfood.json",
    "browser_realistic_dogfood": ROOT / "artifacts" / "accurate_intake_browser_realistic_web_dogfood_v2.json",
    "fixture_full_product_loop_e2e": ROOT / "artifacts" / "accurate_intake_fixture_full_product_loop_e2e.json",
    "pl_ce_review_bundle": ROOT / "artifacts" / "accurate_intake_product_loop_review_bundle.json",
    "context_review": ROOT / "artifacts" / "accurate_intake_context_review_artifact.json",
    "context_target_candidate_eval": ROOT / "artifacts" / "accurate_intake_context_target_candidate_eval.json",
    "context_replay_pack": ROOT / "artifacts" / "accurate_intake_context_replay_pack.json",
    "context_window_diagnostic": ROOT / "artifacts" / "accurate_intake_context_window_diagnostic.json",
    "context_quality_pack": ROOT / "artifacts" / "accurate_intake_context_quality_pack.json",
    "fixture_evidence_packet_emulator": ROOT / "artifacts" / "accurate_intake_fixture_evidence_packet_emulator.json",
    "fake_provider_tool_loop_smoke": ROOT / "artifacts" / "accurate_intake_fake_provider_tool_loop_smoke.json",
    "review_eval_candidate_pipeline": ROOT / "artifacts" / "accurate_intake_review_eval_candidate_pipeline.json",
    "local_operator_data_hygiene_bundle": ROOT
    / "artifacts"
    / "accurate_intake_local_operator_data_hygiene_bundle.json",
    "mvp_gate": ROOT / "artifacts" / "accurate_intake_mvp_gate.json",
}
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "artifacts"
    / "accurate_intake_current_shell_compatibility_local_review_evidence_manifest.json"
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _missing_payload(group_id: str, path: Path) -> dict[str, Any]:
    return {
        "artifact_type": "missing_current_shell_compatibility_local_review_evidence",
        "status": "missing",
        "group_id": group_id,
        "artifact_path": str(path),
        "autofix_attempted": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_truth_updated": False,
        "production_db_used": False,
    }


def _read_or_missing(group_id: str, path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return _missing_payload(group_id, path), True
    payload = read_json_artifact(path)
    payload.setdefault("artifact_path", str(path))
    return payload, False


def build_current_shell_compatibility_local_review_evidence_manifest(
    *,
    path_overrides: dict[str, Path] | None = None,
) -> dict[str, Any]:
    evidence_paths = {
        group_id: Path(path_overrides.get(group_id, default_path)) if path_overrides else default_path
        for group_id, default_path in DEFAULT_EVIDENCE_PATHS.items()
    }
    missing_evidence: list[str] = []
    evidence: dict[str, Any] = {}
    for group_id in REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE:
        payload, missing = _read_or_missing(group_id, evidence_paths[group_id])
        evidence[group_id] = payload
        if missing:
            missing_evidence.append(group_id)
    status = "blocked_missing_evidence" if missing_evidence else "complete"
    metadata = {
        "artifact_schema_version": "1.0",
        "artifact_type": (
            CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPE
        ),
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "required_evidence": list(
            REQUIRED_CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_EVIDENCE
        ),
        "missing_evidence": missing_evidence,
        "autofix_attempted": False,
        "local_only": True,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "evidence_paths": {
            group_id: str(path)
            for group_id, path in evidence_paths.items()
        },
    }
    set_legacy_alias_metadata(
        metadata,
        legacy_artifact_types=LEGACY_LOCAL_REVIEW_EVIDENCE_MANIFEST_ARTIFACT_TYPES,
    )
    return _json_safe({"_manifest_metadata": metadata, **evidence})


def build_pl_ce_local_review_evidence_manifest(
    *,
    path_overrides: dict[str, Path] | None = None,
) -> dict[str, Any]:
    return build_current_shell_compatibility_local_review_evidence_manifest(
        path_overrides=path_overrides
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect local CurrentShell compatibility review JSON artifacts into "
            "decision-pack input."
        )
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Override an evidence path as group_id=path. May be passed multiple times.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    manifest = build_current_shell_compatibility_local_review_evidence_manifest(
        path_overrides=_parse_artifact_overrides(args.artifact)
    )
    write_json_artifact(Path(args.output), manifest)
    summary = {
        "artifact": args.output,
        "status": manifest["_manifest_metadata"]["status"],
        "missing_evidence": manifest["_manifest_metadata"]["missing_evidence"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
