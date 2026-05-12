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
