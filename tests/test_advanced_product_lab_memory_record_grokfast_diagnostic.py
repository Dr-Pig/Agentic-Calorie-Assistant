from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_dogfood_summary import (
    build_memory_record_dogfood_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (
    run_memory_record_integrated_e2e_chain,
)
from app.advanced_shadow_lab.product_lab_memory_record_readiness import (
    build_memory_record_readiness_report,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID


def test_memory_record_grokfast_diagnostic_fake_provider_contract(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (
        run_memory_record_live_diagnostic,
    )

    artifact = run_memory_record_live_diagnostic(
        integrated_e2e_artifact=_integrated(tmp_path),
        provider=_CapturingProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_memory_record_live_diagnostic_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["provider_invoked"] is True
    assert artifact["source_memory_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert artifact["source_memory_record_summary_drives_chain"] is True
    assert artifact["source_journey_terminal_evidence_count"] == 6
    assert artifact["model_output_summary"]["claim_scope"] == "diagnostic_only"
    assert artifact["output_guard"] == {"status": "pass", "blockers": []}
    assert artifact["lab_enabled"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["diagnostic_evidence_class"] == "fake_contract"
    assert artifact["fake_contract_pass"] is True
    assert artifact["live_grokfast_diagnostic_pass"] is False
    assert artifact["live_milestone_status"] == "not_satisfied_fake_contract"
    assert artifact["live_completion_claim_allowed"] is False


def test_memory_record_grokfast_diagnostic_payload_is_bounded(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (
        run_memory_record_live_diagnostic,
    )

    provider = _CapturingProvider()
    artifact = run_memory_record_live_diagnostic(
        integrated_e2e_artifact=_integrated(tmp_path),
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "pass"
    assert provider.user_payload["target_surface"] == (
        "advanced_product_lab_memory_record_integrated_diagnostic"
    )
    assert provider.user_payload["memory_record_summary"] == {
        "memory_record_ids": ["golden-breakfast-oatmeal", "negative-cilantro"],
        "summary_drives_chain": True,
        "recommendation_selected_candidate_id": "golden-1",
        "recommendation_source_refs_include_memory_records": True,
    }
    assert provider.user_payload["integrated_ux_summary"] == {
        "journey_terminal_evidence_count": 6,
        "chat_ux_packet_status": "pass",
        "terminal_review_sink_status": "pass",
    }
    assert provider.user_payload["constraints"]["claim_scope_required"] == (
        "diagnostic_only"
    )
    assert "integrated_chain_artifact" not in provider.user_payload
    assert "raw_user_utterance" not in json.dumps(provider.user_payload)


def test_memory_record_grokfast_diagnostic_live_pass_has_canonical_evidence_shape(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (
        run_memory_record_live_diagnostic,
    )

    artifact = run_memory_record_live_diagnostic(
        integrated_e2e_artifact=_integrated(tmp_path),
        provider=_CapturingProvider(),
        provider_mode=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        live_invoked=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["live_invoked"] is True
    assert artifact["live_provider_used"] is True
    assert artifact["diagnostic_evidence_class"] == "live_grokfast"
    assert artifact["fake_contract_pass"] is False
    assert artifact["live_grokfast_diagnostic_pass"] is True
    assert artifact["live_milestone_status"] == "satisfied_live_grokfast"
    assert artifact["live_completion_claim_allowed"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["durable_product_memory_written"] is False


def test_memory_record_grokfast_blocked_not_invoked_is_canonical_non_live(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (
        blocked_not_invoked_artifact,
    )

    artifact = blocked_not_invoked_artifact(
        output_path=tmp_path / "blocked.json",
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        reason="live_gate_not_enabled",
    )

    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["live_invoked"] is False
    assert artifact["diagnostic_evidence_class"] == "blocked_not_invoked"
    assert artifact["fake_contract_pass"] is False
    assert artifact["live_grokfast_diagnostic_pass"] is False
    assert artifact["live_milestone_status"] == "blocked_not_invoked"
    assert artifact["live_completion_claim_allowed"] is False


def _integrated(tmp_path: Path) -> dict[str, object]:
    session = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path / "session",
        session_id="memory-record-live-diagnostic-session",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_memory_record_dogfood_summary(session)
    readiness = build_memory_record_readiness_report(summary)
    return run_memory_record_integrated_e2e_chain(
        summary_artifact=summary,
        readiness_report=readiness,
    )


class _CapturingProvider:
    def __init__(self) -> None:
        self.user_payload: dict[str, object] = {}

    def readiness(self) -> dict[str, object]:
        return {"provider": "capturing", "configured": True}

    async def complete_with_trace(
        self,
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self.user_payload = dict(kwargs["user_payload"])  # type: ignore[index]
        return {
            "diagnostic_notes": "The MemoryRecord integrated lab chain is reviewable.",
            "risk_notes": "Diagnostic only; no outside-lab delivery or mutation.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["memory_record_integrated_e2e"],
        }, {"stage": "memory_record_live_diagnostic", "provider": "capturing"}
