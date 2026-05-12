from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID


FAKE_PROVIDER_MODE = "fake_provider_contract_test"
BLOCKED_PROVIDER_MODE = "not_invoked"


def attach_live_evidence_status(artifact: dict[str, Any]) -> dict[str, Any]:
    status = str(artifact.get("status") or "")
    evidence_class = diagnostic_evidence_class(artifact)
    fake_pass = evidence_class == "fake_contract" and status == "pass"
    live_pass = evidence_class == "live_grokfast" and status == "pass"
    artifact.update(
        {
            "diagnostic_evidence_class": evidence_class,
            "fake_contract_pass": fake_pass,
            "live_grokfast_diagnostic_pass": live_pass,
            "live_milestone_status": live_milestone_status(
                evidence_class=evidence_class,
                fake_contract_pass=fake_pass,
                live_grokfast_diagnostic_pass=live_pass,
                status=status,
            ),
            "live_completion_claim_allowed": live_pass,
        }
    )
    return artifact


def diagnostic_evidence_class(artifact: Mapping[str, Any]) -> str:
    provider_mode = str(artifact.get("provider_mode") or "")
    provider_profile_id = str(artifact.get("provider_profile_id") or "")
    live_invoked = artifact.get("live_invoked") is True
    provider_invoked = artifact.get("provider_invoked") is True
    live_provider_used = artifact.get("live_provider_used") is True

    if provider_mode == BLOCKED_PROVIDER_MODE and not live_invoked:
        return "blocked_not_invoked"
    if provider_mode == FAKE_PROVIDER_MODE and not live_invoked:
        return "fake_contract"
    if (
        provider_profile_id == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
        and provider_mode == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
        and live_invoked
        and provider_invoked
        and live_provider_used
    ):
        return "live_grokfast"
    return "noncanonical"


def live_milestone_status(
    *,
    evidence_class: str,
    fake_contract_pass: bool,
    live_grokfast_diagnostic_pass: bool,
    status: str,
) -> str:
    if live_grokfast_diagnostic_pass:
        return "satisfied_live_grokfast"
    if fake_contract_pass:
        return "not_satisfied_fake_contract"
    if evidence_class == "blocked_not_invoked":
        return "blocked_not_invoked"
    if status == "provider_error":
        return "blocked_provider_error"
    if status == "blocked":
        return "blocked_contract_or_guard"
    return "not_satisfied_noncanonical"


__all__ = [
    "attach_live_evidence_status",
    "diagnostic_evidence_class",
    "live_milestone_status",
]
