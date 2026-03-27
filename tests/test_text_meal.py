from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.routes import provider, search


client = TestClient(app)


def test_ping_exposes_version_and_schema() -> None:
    response = client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["canary_version"].startswith("text-meal-canary")
    assert "schema_signature" in data


def test_direct_estimate(monkeypatch) -> None:
    async def fake_complete(*, system_prompt, user_payload):
        return {
            "meal_title": "雙培根蛋吐司加早餐紅茶",
            "meal_category": "breakfast_bread_wrap",
            "components": ["培根", "蛋", "吐司", "早餐紅茶"],
            "known_quantities": ["雙培根", "一杯紅茶"],
            "implicit_components": ["抹醬"],
            "missing_modifiers": [],
            "highest_impact_modifier": None,
            "parse_confidence": 0.92,
            "macro_confidence": 0.88,
            "external_verifiability": "medium",
            "search_eligibility": True,
            "can_estimate_with_defaults": True,
            "confidence_level": "high",
            "decision": "estimate",
            "decision_reason": "常見早餐組合，可直接估。",
            "assumptions": ["紅茶先以微糖估。"],
            "component_estimates": [
                {"name": "培根", "source": "explicit", "quantity_hint": "2 份", "estimated_kcal": 120, "protein_g": 8, "carb_g": 0, "fat_g": 10}
            ],
            "estimated_kcal": 620,
            "protein_g": 24,
            "carb_g": 58,
            "fat_g": 28,
            "search_query": None,
        }

    monkeypatch.setattr(provider, "complete_structured", fake_complete)
    response = client.post("/estimate", json={"text": "雙培根蛋吐司加早餐紅茶", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "direct_estimate"
    assert payload["components"] == ["培根", "蛋", "吐司", "早餐紅茶"]
    assert payload["estimated_kcal"] == 620


def test_estimate_with_assumptions(monkeypatch) -> None:
    async def fake_complete(*, system_prompt, user_payload):
        return {
            "meal_title": "拉麵",
            "meal_category": "noodle_soup",
            "components": ["麵", "湯底", "叉燒"],
            "known_quantities": [],
            "implicit_components": ["湯底油脂"],
            "missing_modifiers": ["broth_consumption"],
            "highest_impact_modifier": "broth_consumption",
            "parse_confidence": 0.7,
            "macro_confidence": 0.58,
            "external_verifiability": "medium",
            "search_eligibility": True,
            "can_estimate_with_defaults": True,
            "confidence_level": "provisional",
            "decision": "estimate",
            "decision_reason": "可先估，但湯喝多少會影響很大。",
            "assumptions": ["先以部分喝湯估算。"],
            "component_estimates": [],
            "estimated_kcal": 780,
            "protein_g": 28,
            "carb_g": 72,
            "fat_g": 38,
        }

    monkeypatch.setattr(provider, "complete_structured", fake_complete)
    response = client.post("/estimate", json={"text": "拉麵", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "estimate_with_assumptions"
    assert payload["highest_impact_modifier"] == "broth_consumption"


def test_clarify_before_search(monkeypatch) -> None:
    async def fake_complete(*, system_prompt, user_payload):
        return {
            "meal_title": "珍珠奶茶",
            "meal_category": "drink",
            "components": ["奶茶", "珍珠"],
            "known_quantities": [],
            "implicit_components": ["糖"],
            "missing_modifiers": ["sugar_level", "cup_size"],
            "highest_impact_modifier": "sugar_level",
            "parse_confidence": 0.8,
            "macro_confidence": 0.35,
            "external_verifiability": "low",
            "search_eligibility": True,
            "can_estimate_with_defaults": False,
            "confidence_level": "low",
            "decision": "clarify",
            "decision_reason": "糖度是高影響資訊，先問一題。",
            "followup_question": "你這杯是無糖、微糖、半糖還是全糖？",
            "assumptions": [],
            "component_estimates": [],
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
        }

    monkeypatch.setattr(provider, "complete_structured", fake_complete)
    response = client.post("/estimate", json={"text": "珍珠奶茶", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "clarify_before_search"
    assert payload["followup_question"] == "你這杯是無糖、微糖、半糖還是全糖？"


def test_home_cooked_forces_no_search(monkeypatch) -> None:
    async def fake_complete(*, system_prompt, user_payload):
        return {
            "meal_title": "我媽煮的早餐",
            "meal_category": "unknown",
            "components": [],
            "known_quantities": [],
            "implicit_components": [],
            "missing_modifiers": ["main_components"],
            "highest_impact_modifier": "main_components",
            "parse_confidence": 0.2,
            "macro_confidence": 0.0,
            "external_verifiability": "high",
            "search_eligibility": True,
            "can_estimate_with_defaults": False,
            "confidence_level": "low",
            "decision": "search",
            "decision_reason": "先搜看看。",
            "followup_question": None,
            "assumptions": [],
            "component_estimates": [],
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "search_query": "台灣家常早餐 菜色 熱量",
        }

    monkeypatch.setattr(provider, "complete_structured", fake_complete)
    response = client.post("/estimate", json={"text": "我媽煮的早餐", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "clarify_before_search"
    assert payload["search_eligibility"] is False


def test_answer_after_search(monkeypatch) -> None:
    calls = {"count": 0}

    async def fake_complete(*, system_prompt, user_payload):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "meal_title": "某店限定海陸總匯堡",
                "meal_category": "chain_menu_item",
                "components": ["漢堡"],
                "known_quantities": [],
                "implicit_components": ["醬料"],
                "missing_modifiers": [],
                "highest_impact_modifier": None,
                "parse_confidence": 0.4,
                "macro_confidence": 0.3,
                "external_verifiability": "high",
                "search_eligibility": True,
                "can_estimate_with_defaults": False,
                "confidence_level": "low",
                "decision": "search",
                "decision_reason": "限定品需要外部 evidence。",
                "assumptions": [],
                "component_estimates": [],
                "estimated_kcal": 0,
                "protein_g": 0,
                "carb_g": 0,
                "fat_g": 0,
                "search_query": "某店限定海陸總匯堡 菜單 熱量",
            }
        return {
            "resolution": "answer",
            "resolution_reason": "外部 evidence 足夠。",
            "search_acceptability": True,
            "assumptions": ["以店家菜單描述估算。"],
            "followup_question": None,
            "component_estimates": [],
            "estimated_kcal": 890,
            "protein_g": 34,
            "carb_g": 71,
            "fat_g": 51,
        }

    async def fake_search(query, max_results=3):
        return [{"title": "某店限定海陸總匯堡", "url": "https://example.com", "snippet": "店家限定商品"}]

    monkeypatch.setattr(provider, "complete_structured", fake_complete)
    monkeypatch.setattr(search, "search", fake_search)
    response = client.post("/estimate", json={"text": "某店限定海陸總匯堡", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "answer_after_search"
    assert payload["used_search"] is True
    assert payload["estimated_kcal"] == 890


def test_clarify_after_search(monkeypatch) -> None:
    calls = {"count": 0}

    async def fake_complete(*, system_prompt, user_payload):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "meal_title": "媽寶堡的早餐",
                "meal_category": "unknown",
                "components": ["早餐"],
                "known_quantities": [],
                "implicit_components": [],
                "missing_modifiers": ["main_components"],
                "highest_impact_modifier": "main_components",
                "parse_confidence": 0.3,
                "macro_confidence": 0.1,
                "external_verifiability": "medium",
                "search_eligibility": True,
                "can_estimate_with_defaults": False,
                "confidence_level": "low",
                "decision": "search",
                "decision_reason": "先搜尋看看是否為店家。",
                "assumptions": [],
                "component_estimates": [],
                "estimated_kcal": 0,
                "protein_g": 0,
                "carb_g": 0,
                "fat_g": 0,
                "search_query": "媽寶堡 早餐 菜單",
            }
        return {
            "resolution": "clarify",
            "resolution_reason": "搜尋到的只是近似店家，不能直接套用。",
            "search_acceptability": False,
            "assumptions": [],
            "followup_question": "你說的媽寶堡是店名嗎？如果是，這份早餐實際吃了哪些品項？",
            "component_estimates": [],
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
        }

    async def fake_search(query, max_results=3):
        return [{"title": "摩斯漢堡早餐", "url": "https://example.com", "snippet": "近似但非同店"}]

    monkeypatch.setattr(provider, "complete_structured", fake_complete)
    monkeypatch.setattr(search, "search", fake_search)
    response = client.post("/estimate", json={"text": "媽寶堡的早餐", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "clarify_after_search"
    assert payload["followup_question"]
