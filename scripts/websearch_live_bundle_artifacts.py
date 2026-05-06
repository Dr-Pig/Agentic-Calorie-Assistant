from __future__ import annotations

from pathlib import Path
from typing import Any


_EXPECTED_MANIFEST_TYPE = "accurate_intake_websearch_live_diagnostic_bundle_manifest"


def build_websearch_live_bundle_artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "case_matrix": output_dir / "websearch_case_matrix.json",
        "selected_extract": output_dir / "websearch_selected_extract.json",
        "extract_result": output_dir / "websearch_extract_result.json",
        "review_packet": output_dir / "websearch_exact_review_packet.json",
        "preflight": output_dir / "websearch_live_preflight.json",
        "chain_status": output_dir / "websearch_exact_chain_status.json",
        "readiness": output_dir / "websearch_live_readiness.json",
        "diagnostic": output_dir / "grokfast_websearch_packet_smoke.json",
        "report": output_dir / "websearch_live_report.json",
        "manager_contract_probe": output_dir / "websearch_contract_probe.json",
        "manager_contract_repair_pack": output_dir / "websearch_contract_repair.json",
        "manager_contract_handoff": output_dir / "websearch_contract_handoff.json",
        "websearch_evidence_status_packet": output_dir / "websearch_evidence_status_packet.json",
        "websearch_status_packet_inspection": output_dir / "websearch_status_packet_inspection.json",
        "manifest": output_dir / "websearch_live_manifest.json",
    }


def validate_websearch_live_bundle_manifest(manifest: dict[str, Any]) -> None:
    if str(manifest.get("artifact_type") or "") != _EXPECTED_MANIFEST_TYPE:
        raise ValueError("unsupported_websearch_live_bundle_manifest")


def bundle_artifact_path_from_manifest(
    manifest: dict[str, Any],
    *,
    key: str,
) -> Path | None:
    validate_websearch_live_bundle_manifest(manifest)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("websearch_live_bundle_manifest_missing_artifacts")
    ref = artifacts.get(key)
    if not ref:
        return None
    return Path(str(ref))


__all__ = [
    "build_websearch_live_bundle_artifact_paths",
    "bundle_artifact_path_from_manifest",
    "validate_websearch_live_bundle_manifest",
]
