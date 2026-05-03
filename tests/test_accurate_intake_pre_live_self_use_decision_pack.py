from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (
    REQUIRED_PRE_LIVE_EVIDENCE,
    build_pre_live_self_use_decision_pack,
)


def _evidence(**overrides: dict) -> dict:
    evidence = {
        "phase_c_gate": {"status": "pass"},
        "accurate_intake_mvp_gate": {"status": "pass"},
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "chat_history_reload_gate": {"status": "pass"},
        "free_text_manual_target_gate": {"status": "pass"},
        "dogfood_review_queue": {"status": "generated"},
        "local_dogfood_data_hygiene": {"status": "pass"},
    }
    evidence.update(overrides)
    return evidence


def test_pre_live_decision_pack_lists_required_evidence_without_approving_live() -> None:
    pack = build_pre_live_self_use_decision_pack(_evidence())

    assert pack["artifact_type"] == "accurate_intake_pre_live_self_use_decision_pack"
    assert pack["claim_scope"] == "pre_live_local_web_self_use_decision_pack"
    assert pack["required_evidence"] == list(REQUIRED_PRE_LIVE_EVIDENCE)
    assert pack["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert pack["missing_evidence"] == []
    assert pack["live_llm_invoked"] is False
    assert pack["live_canary_approved"] is False
    assert pack["kimi_active_runtime_default_allowed"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["runtime_web_activation_approved"] is False


def test_pre_live_decision_pack_stays_local_when_review_or_data_hygiene_evidence_missing() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            dogfood_review_queue={"status": "missing"},
            local_dogfood_data_hygiene={"status": "blocked"},
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert pack["live_canary_approved"] is False
    assert pack["missing_evidence"] == [
        "dogfood_review_queue",
        "local_dogfood_data_hygiene",
    ]


def test_pre_live_decision_pack_requires_browser_executed_evidence_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(browser_shell_smoke={"status": "blocked", "browser_executed": False})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "browser_shell_smoke" in pack["missing_evidence"]
    assert pack["evidence_status"]["browser_shell_smoke"]["browser_executed"] is False


def test_pre_live_decision_pack_script_writes_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "pre_live_pack.json"
    evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_pre_live_self_use_decision_pack import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert artifact["live_canary_approved"] is False
