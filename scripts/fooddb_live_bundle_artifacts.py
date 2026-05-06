from __future__ import annotations

from pathlib import Path
from typing import Any


_EXPECTED_MANIFEST_TYPE = "accurate_intake_fooddb_live_diagnostic_bundle_manifest"


def build_fooddb_live_bundle_artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "retrieval_eval_wall": output_dir / "accurate_intake_retrieval_eval_wall.json",
        "fooddb_status_packet": output_dir / "accurate_intake_fooddb_evidence_status_packet.json",
        "manager_packet_smoke": output_dir / "accurate_intake_fooddb_manager_packet_smoke.json",
        "index_backend_parity": output_dir / "accurate_intake_fooddb_index_backend_parity.json",
        "case_matrix": output_dir
        / "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix.json",
        "preflight": output_dir / "accurate_intake_grokfast_fooddb_diagnostic_preflight.json",
        "router_readiness": output_dir
        / "accurate_intake_food_evidence_retriever_router_readiness.json",
        "live_runner_readiness": output_dir
        / "accurate_intake_grokfast_fooddb_live_runner_readiness_packet.json",
        "diagnostic": output_dir / "accurate_intake_grokfast_fooddb_packet_smoke.json",
        "report": output_dir / "accurate_intake_fooddb_live_diagnostic_report.json",
        "manager_contract_probe": output_dir / "accurate_intake_fooddb_manager_contract_probe.json",
        "manager_contract_repair_pack": output_dir
        / "accurate_intake_fooddb_manager_contract_repair_pack.json",
        "manager_contract_handoff": output_dir
        / "accurate_intake_fooddb_manager_contract_handoff.json",
        "fooddb_status_packet_post_contract": output_dir
        / "accurate_intake_fooddb_evidence_status_post_contract.json",
        "manifest": output_dir / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json",
        "sqlite_db": output_dir / "accurate_intake_fooddb_bundle_backend_parity.sqlite",
    }


def validate_fooddb_live_bundle_manifest(manifest: dict[str, Any]) -> None:
    if str(manifest.get("artifact_type") or "") != _EXPECTED_MANIFEST_TYPE:
        raise ValueError("unsupported_fooddb_live_bundle_manifest")


def bundle_artifact_path_from_manifest(
    manifest: dict[str, Any],
    *,
    key: str,
) -> Path | None:
    validate_fooddb_live_bundle_manifest(manifest)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("fooddb_live_bundle_manifest_missing_artifacts")
    ref = artifacts.get(key)
    if not ref:
        return None
    return Path(str(ref))


__all__ = [
    "build_fooddb_live_bundle_artifact_paths",
    "bundle_artifact_path_from_manifest",
    "validate_fooddb_live_bundle_manifest",
]
