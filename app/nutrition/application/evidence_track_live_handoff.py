from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_EXPECTED_FOODDB_MANIFEST = "accurate_intake_fooddb_live_diagnostic_bundle_manifest"
_EXPECTED_FOODDB_STATUS = "accurate_intake_fooddb_evidence_status_packet_v1"
_EXPECTED_WEBSEARCH_MANIFEST = "accurate_intake_websearch_live_diagnostic_bundle_manifest"
_EXPECTED_WEBSEARCH_STATUS_INSPECTION = "accurate_intake_websearch_status_packet_inspection_v1"
_EXTERNAL_NEXT_STEP = "external_manager_runtime_packet_probe"


def build_evidence_track_live_handoff(
    *,
    fooddb_manifest: dict[str, Any],
    fooddb_status_post_contract: dict[str, Any] | None,
    websearch_manifest: dict[str, Any] | None,
    websearch_status_packet_inspection: dict[str, Any] | None,
) -> dict[str, Any]:
    blockers = _manifest_blockers(fooddb_manifest, expected_type=_EXPECTED_FOODDB_MANIFEST, prefix="fooddb")
    if blockers:
        status = "blocked"
        selected_next_step = "inspect_fooddb_live_bundle"
    else:
        status, selected_next_step, blockers = _derive_track_status(
            fooddb_manifest=fooddb_manifest,
            fooddb_status_post_contract=fooddb_status_post_contract,
            websearch_manifest=websearch_manifest,
            websearch_status_packet_inspection=websearch_status_packet_inspection,
        )

    return {
        "artifact_type": "accurate_intake_evidence_track_live_handoff_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "diagnostic_handoff_only",
        "claim_scope": "fooddb_websearch_live_diagnostic_track_handoff",
        "status": status,
        "selected_next_step": selected_next_step,
        "downstream_owner": "main_integrator_manager_runtime_probe",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "fooddb_bundle_status": str(fooddb_manifest.get("bundle_status") or "unknown"),
            "fooddb_seam_status": str(fooddb_manifest.get("seam_status") or "unknown"),
            "fooddb_live_provider_used": fooddb_manifest.get("live_provider_used") is True,
            "fooddb_status_packet_present": isinstance(fooddb_status_post_contract, dict),
            "websearch_bundle_present": isinstance(websearch_manifest, dict),
            "websearch_bundle_status": (
                None if not isinstance(websearch_manifest, dict) else str(websearch_manifest.get("bundle_status") or "unknown")
            ),
            "websearch_seam_status": (
                None if not isinstance(websearch_manifest, dict) else str(websearch_manifest.get("seam_status") or "unknown")
            ),
            "websearch_live_provider_used": (
                isinstance(websearch_manifest, dict) and websearch_manifest.get("live_provider_used") is True
            ),
            "websearch_status_inspection_passed": (
                isinstance(websearch_status_packet_inspection, dict)
                and websearch_status_packet_inspection.get("status") == "pass"
            ),
        },
        "source_refs": {
            "fooddb_manifest_type": fooddb_manifest.get("artifact_type"),
            "fooddb_status_post_contract_type": None if fooddb_status_post_contract is None else fooddb_status_post_contract.get("artifact_type"),
            "websearch_manifest_type": None if websearch_manifest is None else websearch_manifest.get("artifact_type"),
            "websearch_status_inspection_type": None if websearch_status_packet_inspection is None else websearch_status_packet_inspection.get("artifact_type"),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
            "no_self_use_approval",
        ],
    }


def _derive_track_status(
    *,
    fooddb_manifest: dict[str, Any],
    fooddb_status_post_contract: dict[str, Any] | None,
    websearch_manifest: dict[str, Any] | None,
    websearch_status_packet_inspection: dict[str, Any] | None,
) -> tuple[str, str, list[str]]:
    fooddb_bundle_status = str(fooddb_manifest.get("bundle_status") or "")
    fooddb_next = _next_step(fooddb_manifest, fallback="inspect_fooddb_live_bundle")
    if fooddb_bundle_status != "pass":
        return "blocked", fooddb_next, ["fooddb_bundle_not_pass"]

    fooddb_seam_status = str(fooddb_manifest.get("seam_status") or "")
    if fooddb_seam_status != "live_diagnostic_pass":
        return "fixture_only_live_not_checked", fooddb_next, []

    status_blockers = _status_packet_blockers(fooddb_status_post_contract)
    if status_blockers:
        return "blocked", "inspect_fooddb_status_packet", status_blockers

    if not isinstance(websearch_manifest, dict):
        return "fooddb_live_pass_websearch_not_run", "grokfast_websearch_packet_live_diagnostic", []

    websearch_blockers = _manifest_blockers(
        websearch_manifest,
        expected_type=_EXPECTED_WEBSEARCH_MANIFEST,
        prefix="websearch",
    )
    if websearch_blockers:
        return "blocked", "inspect_websearch_live_bundle", websearch_blockers

    websearch_bundle_status = str(websearch_manifest.get("bundle_status") or "")
    websearch_next = _next_step(websearch_manifest, fallback="inspect_websearch_status_packet")
    if websearch_bundle_status != "pass":
        return "blocked", websearch_next, ["websearch_bundle_not_pass"]

    websearch_seam_status = str(websearch_manifest.get("seam_status") or "")
    if websearch_seam_status != "live_diagnostic_pass":
        return "fooddb_live_pass_websearch_live_not_checked", websearch_next, []

    inspection_blockers = _inspection_blockers(websearch_status_packet_inspection)
    if inspection_blockers:
        return "blocked", "inspect_websearch_status_packet", inspection_blockers

    return "evidence_track_live_diagnostic_pass", _EXTERNAL_NEXT_STEP, []


def _manifest_blockers(
    artifact: dict[str, Any] | None,
    *,
    expected_type: str,
    prefix: str,
) -> list[str]:
    if not isinstance(artifact, dict):
        return [f"missing_{prefix}_manifest"]
    if str(artifact.get("artifact_type") or "") != expected_type:
        return [f"unsupported_{prefix}_manifest"]
    blockers: list[str] = []
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append(f"{prefix}_manifest_changed_runtime_truth")
    if artifact.get("runtime_mutation_attempted") is not False:
        blockers.append(f"{prefix}_manifest_attempted_runtime_mutation")
    if artifact.get("readiness_claimed") is not False:
        blockers.append(f"{prefix}_manifest_claimed_readiness")
    if artifact.get("self_use_approved") is not False:
        blockers.append(f"{prefix}_manifest_claimed_self_use")
    if artifact.get("production_selected") is not False:
        blockers.append(f"{prefix}_manifest_selected_production")
    return blockers


def _status_packet_blockers(artifact: dict[str, Any] | None) -> list[str]:
    if not isinstance(artifact, dict):
        return ["missing_fooddb_status_post_contract"]
    if str(artifact.get("artifact_type") or "") != _EXPECTED_FOODDB_STATUS:
        return ["unsupported_fooddb_status_post_contract"]
    blockers: list[str] = []
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("fooddb_status_post_contract_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("fooddb_status_post_contract_changed_mutation")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("fooddb_status_post_contract_claimed_readiness")
    next_required_slices = list(artifact.get("next_required_slices") or [])
    if next_required_slices[:1] != ["grokfast_websearch_packet_live_diagnostic"]:
        blockers.append("fooddb_status_post_contract_not_ready_for_websearch_live")
    summary = dict(artifact.get("summary") or {})
    if str(summary.get("manager_contract_live_seam_status") or "") != "live_diagnostic_pass":
        blockers.append("fooddb_status_post_contract_live_seam_not_pass")
    if str(summary.get("manager_contract_handoff_status") or "") != "fooddb_contract_unblocked":
        blockers.append("fooddb_status_post_contract_handoff_not_unblocked")
    return blockers


def _inspection_blockers(artifact: dict[str, Any] | None) -> list[str]:
    if not isinstance(artifact, dict):
        return ["missing_websearch_status_packet_inspection"]
    if str(artifact.get("artifact_type") or "") != _EXPECTED_WEBSEARCH_STATUS_INSPECTION:
        return ["unsupported_websearch_status_packet_inspection"]
    blockers: list[str] = []
    if artifact.get("status") != "pass":
        blockers.append("websearch_status_packet_inspection_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("websearch_status_packet_inspection_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("websearch_status_packet_inspection_changed_mutation")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("websearch_status_packet_inspection_claimed_readiness")
    return blockers


def _next_step(artifact: dict[str, Any], *, fallback: str) -> str:
    text = str(artifact.get("next_recommended_slice") or "").strip()
    if not text:
        return fallback
    if text.startswith("run_explicit_"):
        return text.removeprefix("run_explicit_")
    return text


__all__ = ["build_evidence_track_live_handoff"]
