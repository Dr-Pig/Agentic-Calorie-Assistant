from pathlib import Path

from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)
from scripts.build_proactive_no_send_decision_pack import (
    build_proactive_no_send_decision_pack,
    write_proactive_no_send_decision_pack,
)


def _artifact_with_review_candidate() -> dict[str, object]:
    return build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                delivery_surface="app_open",
            )
        ]
    )


def test_decision_pack_keeps_single_no_send_run_out_of_live_promotion() -> None:
    pack = build_proactive_no_send_decision_pack([_artifact_with_review_candidate()])

    assert pack["artifact_type"] == "proactive_no_send_decision_pack"
    assert pack["shadow_mode"] is True
    assert pack["live_delivery_allowed"] is False
    assert pack["scheduler_activation_allowed"] is False
    assert pack["promotion_allowed"] is False
    assert pack["summary"]["run_count"] == 1
    assert pack["summary"]["candidate_for_human_review_trigger_types"] == ["recommendation_prompt"]
    assert pack["promotion_gate"] == {
        "minimum_clean_shadow_runs": 3,
        "human_review_required": True,
        "repeated_clean_shadow_evidence": False,
        "promotion_blockers": [
            "human_review_required_before_live_delivery",
            "live_scheduler_not_enabled",
            "minimum_clean_shadow_runs_not_met",
            "no_send_shadow_only",
        ],
    }


def test_decision_pack_rejects_overclaiming_or_side_effectful_inputs() -> None:
    overclaiming = _artifact_with_review_candidate()
    overclaiming["product_readiness_claimed"] = True
    side_effectful = _artifact_with_review_candidate()
    side_effectful["proactive_sent"] = True

    pack = build_proactive_no_send_decision_pack([overclaiming, side_effectful])

    assert pack["input_integrity"]["passed"] is False
    assert "run_1_product_readiness_claimed" in pack["input_integrity"]["blockers"]
    assert "run_2_proactive_sent" in pack["input_integrity"]["blockers"]
    assert pack["promotion_allowed"] is False


def test_decision_pack_writer_creates_artifact(tmp_path: Path) -> None:
    source_path = tmp_path / "proactive_no_send_simulation.json"
    output_path = tmp_path / "proactive_no_send_decision_pack.json"
    source_path.write_text(
        __import__("json").dumps(_artifact_with_review_candidate(), ensure_ascii=False),
        encoding="utf-8",
    )

    written = write_proactive_no_send_decision_pack(
        no_send_artifact_paths=[source_path],
        output_path=output_path,
    )

    assert written == output_path
    payload = written.read_text(encoding="utf-8")
    assert '"artifact_type": "proactive_no_send_decision_pack"' in payload
    assert '"promotion_allowed": false' in payload
