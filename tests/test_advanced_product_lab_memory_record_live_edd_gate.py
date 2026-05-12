from __future__ import annotations

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_memory_record_live_artifact import (
    ARTIFACT_TYPE as LIVE_DIAGNOSTIC_ARTIFACT_TYPE,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)


def test_memory_record_live_edd_preflight_separates_fake_from_live_ready() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (
        build_memory_record_live_edd_preflight,
    )

    fake = build_memory_record_live_edd_preflight(
        provider_mode="fake",
        allow_live_provider=False,
        env_live_gate_enabled=False,
    )
    live = build_memory_record_live_edd_preflight(
        provider_mode="live",
        allow_live_provider=True,
        env_live_gate_enabled=True,
    )

    assert fake["status"] == "pass"
    assert fake["reviewed_preflight_status"] == "fake_contract_preflight_passed_non_live"
    assert fake["fake_contract_preflight_pass"] is True
    assert fake["live_milestone_preflight_ready"] is False
    assert fake["live_provider_invocation_allowed"] is False

    assert live["status"] == "pass"
    assert live["reviewed_preflight_status"] == "live_grokfast_preflight_ready"
    assert live["fake_contract_preflight_pass"] is False
    assert live["live_milestone_preflight_ready"] is True
    assert live["live_provider_invocation_allowed"] is True
    assert live["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID


def test_memory_record_live_edd_preflight_blocks_live_without_gate() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (
        build_memory_record_live_edd_preflight,
    )

    artifact = build_memory_record_live_edd_preflight(
        provider_mode="live",
        allow_live_provider=True,
        env_live_gate_enabled=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["reviewed_preflight_status"] == "blocked_not_invoked_preflight"
    assert artifact["live_provider_invocation_allowed"] is False
    assert artifact["live_milestone_preflight_ready"] is False
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["durable_product_memory_written"] is False


def test_memory_record_live_edd_gate_rejects_fake_as_live_completion() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_edd_gate import (
        review_memory_record_live_edd_gate,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (
        build_memory_record_live_edd_preflight,
    )

    gate = review_memory_record_live_edd_gate(
        preflight_artifact=build_memory_record_live_edd_preflight(
            provider_mode="fake",
            allow_live_provider=False,
            env_live_gate_enabled=False,
        ),
        live_diagnostic_artifact=_diagnostic(
            status="pass",
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            provider_invoked=True,
            live_provider_used=False,
        ),
    )

    assert gate["status"] == "blocked"
    assert gate["reviewed_live_status"] == "fake_contract_reviewed_non_live"
    assert gate["live_milestone_complete"] is False
    assert gate["fake_contract_reviewed"] is True
    assert gate["live_grokfast_reviewed"] is False
    assert gate["blockers"] == ["live_diagnostic.fake_contract_not_live_milestone"]


def test_memory_record_live_edd_gate_records_blocked_not_invoked_status() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_edd_gate import (
        review_memory_record_live_edd_gate,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (
        build_memory_record_live_edd_preflight,
    )

    gate = review_memory_record_live_edd_gate(
        preflight_artifact=build_memory_record_live_edd_preflight(
            provider_mode="live",
            allow_live_provider=True,
            env_live_gate_enabled=False,
        ),
        live_diagnostic_artifact=_diagnostic(
            status="blocked",
            provider_mode="not_invoked",
            live_invoked=False,
            provider_invoked=False,
            live_provider_used=False,
            blockers=["live_gate_not_enabled"],
        ),
    )

    assert gate["status"] == "blocked"
    assert gate["reviewed_live_status"] == "blocked_not_invoked_reviewed"
    assert gate["live_milestone_complete"] is False
    assert gate["blockers"] == [
        "preflight.status_blocked",
        "live_diagnostic.blocked_not_invoked",
    ]


def test_memory_record_live_edd_gate_passes_only_live_grokfast_with_preflight() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_edd_gate import (
        review_memory_record_live_edd_gate,
    )
    from app.advanced_shadow_lab.product_lab_memory_record_live_preflight import (
        build_memory_record_live_edd_preflight,
    )

    gate = review_memory_record_live_edd_gate(
        preflight_artifact=build_memory_record_live_edd_preflight(
            provider_mode="live",
            allow_live_provider=True,
            env_live_gate_enabled=True,
        ),
        live_diagnostic_artifact=_diagnostic(
            status="pass",
            provider_mode=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
            live_invoked=True,
            provider_invoked=True,
            live_provider_used=True,
        ),
    )

    assert gate["status"] == "pass"
    assert gate["reviewed_live_status"] == "live_grokfast_reviewed_pass"
    assert gate["live_milestone_complete"] is True
    assert gate["live_grokfast_reviewed"] is True
    assert gate["mainline_activation_enabled"] is False
    assert gate["canonical_product_mutation_allowed"] is False


def _diagnostic(
    *,
    status: str,
    provider_mode: str,
    live_invoked: bool,
    provider_invoked: bool,
    live_provider_used: bool,
    blockers: list[str] | None = None,
) -> dict[str, object]:
    return attach_live_evidence_status(
        {
            "artifact_type": LIVE_DIAGNOSTIC_ARTIFACT_TYPE,
            "status": status,
            "provider_mode": provider_mode,
            "provider_profile_id": ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
            "live_invoked": live_invoked,
            "provider_invoked": provider_invoked,
            "live_provider_used": live_provider_used,
            "blockers": blockers or [],
            "mainline_activation_enabled": False,
            "durable_product_memory_written": False,
            "canonical_product_mutation_allowed": False,
            "user_facing_behavior_changed": False,
        }
    )
