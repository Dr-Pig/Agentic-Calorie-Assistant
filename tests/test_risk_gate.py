from app.agent.knowledge_packets import build_gate_packet


def test_risk_gate_matches_ramen_by_exact_keyword() -> None:
    packet = build_gate_packet("醬油豚骨拉麵")
    assert "ramen" in packet["risk_flags"]
    assert any(reason.startswith("keyword:") for reason in packet["risk_match_reasons"]["ramen"])


def test_risk_gate_matches_ramen_by_archetype_pattern() -> None:
    packet = build_gate_packet("叉燒豚骨麵")
    assert "ramen" in packet["risk_flags"]
    assert any(reason.startswith("pattern:") for reason in packet["risk_match_reasons"]["ramen"])


def test_risk_gate_matches_buffet_like_meal_by_pattern() -> None:
    packet = build_gate_packet("雞腿飯")
    assert "buffet" in packet["risk_flags"]
    assert any(reason.startswith("pattern:") for reason in packet["risk_match_reasons"]["buffet"])


def test_risk_gate_matches_shop_brand_mapping() -> None:
    packet = build_gate_packet("鷹流的2929醬油豚骨拉麵")
    assert "ramen" in packet["risk_flags"]
    assert any(reason.startswith("shop:") for reason in packet["risk_match_reasons"]["ramen"])


def test_risk_gate_marks_private_only_for_buffet() -> None:
    packet = build_gate_packet("公司旁邊的雞腿飯便當")
    assert "buffet" in packet["risk_flags"]
    assert packet["private_only"] is True
