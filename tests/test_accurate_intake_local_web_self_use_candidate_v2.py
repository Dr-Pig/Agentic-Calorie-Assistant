from __future__ import annotations

from scripts.build_accurate_intake_local_web_self_use_candidate_v2 import build_local_web_self_use_candidate_v2

def _clean_evidence() -> dict:
    return {
        "browser_shell_smoke": {"status": "pass", "source": "test"},
        "chat_history_reload": {"status": "pass", "source": "test"},
        "free_text_manual_target": {"status": "pass", "source": "test"},
        "dogfood_review_queue": {"status": "generated", "source": "test"},
        "local_dogfood_data_hygiene": {"status": "pass", "source": "test"},
        "pre_live_decision_pack": {"status": "generated", "source": "test"},
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

def test_candidate_never_sets_product_readiness_claimed_true() -> None:
    pack = build_local_web_self_use_candidate_v2(_clean_evidence())
    assert pack["local_web_self_use_candidate_v2"]["product_readiness_claimed"] is False
    assert pack["local_web_self_use_candidate_v2"]["private_self_use_approved"] is False
    assert pack["local_web_self_use_candidate_v2"]["kimi_activated"] is False
