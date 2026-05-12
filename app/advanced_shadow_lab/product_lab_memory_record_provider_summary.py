from __future__ import annotations

from typing import Any, Mapping


def provider_contract_summary(live_diagnostic_artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_mode": str(live_diagnostic_artifact.get("provider_mode") or ""),
        "provider_profile_id": str(
            live_diagnostic_artifact.get("provider_profile_id") or ""
        ),
        "live_invoked": bool(live_diagnostic_artifact.get("live_invoked")),
        "live_provider_used": bool(live_diagnostic_artifact.get("live_provider_used")),
        "diagnostic_evidence_class": str(
            live_diagnostic_artifact.get("diagnostic_evidence_class") or ""
        ),
        "fake_contract_pass": live_diagnostic_artifact.get("fake_contract_pass") is True,
        "live_grokfast_diagnostic_pass": (
            live_diagnostic_artifact.get("live_grokfast_diagnostic_pass") is True
        ),
        "live_milestone_status": str(
            live_diagnostic_artifact.get("live_milestone_status") or ""
        ),
    }


__all__ = ["provider_contract_summary"]
