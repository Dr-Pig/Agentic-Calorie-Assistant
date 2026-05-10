from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.live_bundle_seam_proof"
)
SURFACE_IDS = (
    "recommendation_copy_live_diagnostic",
    "rescue_copy_live_diagnostic",
    "proactive_copy_live_diagnostic",
)


def build_live_seam_proof_summary(
    *,
    preflight: Mapping[str, Any],
    diagnostics: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    guard_status = {
        surface_id: _guard_status(diagnostics.get(surface_id))
        for surface_id in SURFACE_IDS
    }
    live_used = {
        surface_id: _mapping(diagnostics.get(surface_id)).get("live_provider_used") is True
        for surface_id in SURFACE_IDS
    }
    preflight_blockers = [str(item) for item in preflight.get("blockers") or []]
    status = _summary_status(
        preflight_status=str(preflight.get("status") or "blocked"),
        guard_status=guard_status,
        live_used=live_used,
    )
    return {
        "status": status,
        "provider_mode": str(preflight.get("provider_mode") or ""),
        "provider_profile_id": str(preflight.get("provider_profile_id") or ""),
        "profile_role": str(preflight.get("profile_role") or ""),
        "profile_model_id": str(preflight.get("profile_model_id") or ""),
        "preflight_status": str(preflight.get("status") or "blocked"),
        "preflight_blockers": preflight_blockers,
        "diagnostic_surface_ids": list(SURFACE_IDS),
        "provider_mode_by_surface": _field_by_surface(diagnostics, "provider_mode"),
        "live_invoked_by_surface": _bool_by_surface(diagnostics, "live_invoked"),
        "live_provider_used_by_surface": live_used,
        "output_guard_status_by_surface": guard_status,
        "trace_usage_present_by_surface": {
            surface_id: _mapping(
                _mapping(diagnostics.get(surface_id)).get("provider_trace_summary")
            ).get("usage_present")
            is True
            for surface_id in SURFACE_IDS
        },
        "trace_metadata_redacted": True,
        "raw_provider_payload_omitted": True,
        "per_journey_ux_grader_created": False,
        "calibration_live_diagnostic_created": False,
        "new_report_family_created": False,
        "runtime_connected": False,
        "mainline_runtime_connected": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
        "product_readiness_claimed": False,
    }


def _summary_status(
    *,
    preflight_status: str,
    guard_status: Mapping[str, str],
    live_used: Mapping[str, bool],
) -> str:
    if preflight_status != "pass":
        return "blocked_not_invoked"
    if any(status == "blocked" for status in guard_status.values()):
        return "diagnostic_guard_blocked"
    if all(live_used.values()):
        return "live_diagnostic_guarded"
    return "fake_contract_path"


def _field_by_surface(
    diagnostics: Mapping[str, Mapping[str, Any]], field: str
) -> dict[str, str]:
    return {
        surface_id: str(_mapping(diagnostics.get(surface_id)).get(field) or "")
        for surface_id in SURFACE_IDS
    }


def _bool_by_surface(
    diagnostics: Mapping[str, Mapping[str, Any]], field: str
) -> dict[str, bool]:
    return {
        surface_id: _mapping(diagnostics.get(surface_id)).get(field) is True
        for surface_id in SURFACE_IDS
    }


def _guard_status(artifact: Mapping[str, Any] | None) -> str:
    return str(_mapping(_mapping(artifact).get("output_guard")).get("status") or "not_run")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_live_seam_proof_summary"]
