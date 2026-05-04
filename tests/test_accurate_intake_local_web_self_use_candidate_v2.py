from __future__ import annotations

from scripts.build_accurate_intake_local_web_self_use_candidate_v2 import build_local_web_self_use_candidate_v2

def _clean_evidence() -> dict:
    return {
        "browser_shell_smoke": {"status": "pass", "source": "test"},
        "chat_history_reload": {"status": "pass", "source": "test"},
        "free_text_manual_target": {"status": "pass", "source": "test"},
        "dogfood_review_queue": {"status": "generated", "source": "test"},
        "local_dogfood_data_hygiene": {"status": "pass", "source": "test"},
        "pre_live_decision_pack": {
            "status": "generated",
            "source": "test",
            "ready_for_pl_ce_local_review": True,
            "ready_for_live_diagnostic_decision": False,
            "live_canary_approved": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "pl_ce_local_review_decision_pack": {
            "status": "ready_for_human_pl_ce_review",
            "source": "test",
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "mvp_gate": {"status": "pass"},
        "phase_c_gate": {"status": "pass"},
    }

def test_candidate_prepared_when_all_clean() -> None:
    evidence = _clean_evidence()
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is True
    assert pack["local_web_self_use_candidate_v2"]["blockers"] == []

def test_candidate_blocked_when_browser_shell_smoke_missing() -> None:
    evidence = _clean_evidence()
    del evidence["browser_shell_smoke"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: browser_shell_smoke" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_chat_history_reload_missing() -> None:
    evidence = _clean_evidence()
    del evidence["chat_history_reload"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: chat_history_reload" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_free_text_manual_target_missing() -> None:
    evidence = _clean_evidence()
    del evidence["free_text_manual_target"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: free_text_manual_target" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_dogfood_review_queue_missing() -> None:
    evidence = _clean_evidence()
    del evidence["dogfood_review_queue"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: dogfood_review_queue" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_local_dogfood_data_hygiene_missing() -> None:
    evidence = _clean_evidence()
    del evidence["local_dogfood_data_hygiene"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: local_dogfood_data_hygiene" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_pre_live_decision_pack_missing() -> None:
    evidence = _clean_evidence()
    del evidence["pre_live_decision_pack"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: pre_live_decision_pack" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_when_pl_ce_local_review_decision_pack_missing() -> None:
    evidence = _clean_evidence()
    del evidence["pl_ce_local_review_decision_pack"]
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "missing evidence: pl_ce_local_review_decision_pack" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_requires_pre_live_pack_to_reference_pl_ce_local_review() -> None:
    evidence = _clean_evidence()
    evidence["pre_live_decision_pack"]["ready_for_pl_ce_local_review"] = False
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "pre-live missing PL+CE local review gate" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocks_pre_live_live_decision_or_canary_approval() -> None:
    for flag in ("ready_for_live_diagnostic_decision", "live_canary_approved"):
        evidence = _clean_evidence()
        evidence["pre_live_decision_pack"][flag] = True
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert "pre-live overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocks_pl_ce_decision_pack_overclaims() -> None:
    evidence = _clean_evidence()
    evidence["pl_ce_local_review_decision_pack"].update(
        {
            "ready_for_live_diagnostic_decision": True,
            "ready_for_fdb_integration": True,
            "real_fooddb_pass_claimed": True,
        }
    )
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "PL+CE local review overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_private_self_use_approved_true() -> None:
    evidence = _clean_evidence()
    evidence["some_evil_artifact"] = {"private_self_use_approved": True}
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "private self-use approval attempted" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_kimi_activated_or_live_provider_used() -> None:
    evidence = _clean_evidence()
    evidence["some_artifact"] = {"kimi_activated": True}
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "Kimi activated" in pack["local_web_self_use_candidate_v2"]["blockers"]
    
    evidence2 = _clean_evidence()
    evidence2["some_artifact"] = {"live_provider_called": True}
    pack2 = build_local_web_self_use_candidate_v2(evidence2)
    assert pack2["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "live provider used" in pack2["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_live_llm_grokfast_or_websearch_used() -> None:
    cases = (
        ("live_llm_invoked", "live provider used"),
        ("web_tavily_used", "websearch used"),
        ("web_tavily_invoked", "websearch used"),
        ("web_tavily", "websearch used"),
        ("websearch_evidence_used", "websearch used"),
        ("WebSearch", "websearch used"),
        ("grokfast_activated", "GrokFast activated"),
        ("GrokFast", "GrokFast activated"),
    )
    for flag, blocker in cases:
        evidence = _clean_evidence()
        evidence["some_artifact"] = {flag: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert blocker in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_any_artifact_claims_fooddb_truth_or_integration() -> None:
    cases = (
        "ready_for_fdb_integration",
        "fooddb_truth_updated",
        "fooddb_evidence_used",
        "real_fooddb_pass_claimed",
        "fooddb_schema_changed",
        "food_evidence_promotion_policy_changed",
    )
    for flag in cases:
        evidence = _clean_evidence()
        evidence["some_artifact"] = {flag: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert "FoodDB overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_never_sets_product_readiness_claimed_true() -> None:
    pack = build_local_web_self_use_candidate_v2(_clean_evidence())
    assert pack["local_web_self_use_candidate_v2"]["product_readiness_claimed"] is False
    assert pack["local_web_self_use_candidate_v2"]["private_self_use_approved"] is False
    assert pack["local_web_self_use_candidate_v2"]["kimi_activated"] is False

def test_candidate_blocked_if_production_selected_or_rollout_approved_or_live_manager_required() -> None:
    for field in ("production_selected", "rollout_approved", "live_manager_required", "web_ready", "product_ready"):
        evidence = _clean_evidence()
        evidence["some_artifact"] = {field: True}
        pack = build_local_web_self_use_candidate_v2(evidence)
        assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
        assert "readiness overclaim" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_candidate_blocked_if_production_db_touched() -> None:
    evidence = _clean_evidence()
    evidence["some_artifact"] = {"production_db_touched": True}
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "production DB touched" in pack["local_web_self_use_candidate_v2"]["blockers"]

def test_present_evidence_with_failed_status_blocks_as_failed_evidence() -> None:
    evidence = _clean_evidence()
    evidence["browser_shell_smoke"]["status"] = "blocked"
    pack = build_local_web_self_use_candidate_v2(evidence)
    assert pack["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "failed evidence: browser_shell_smoke status=blocked" in pack["local_web_self_use_candidate_v2"]["blockers"]
