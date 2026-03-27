from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.routes import provider, search


client = TestClient(app)


def test_ping_exposes_version_and_schema() -> None:
    response = client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["canary_version"] == "text-meal-canary.v5"
    assert "schema_signature" in data


def test_ready_then_direct_answer(monkeypatch) -> None:
    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        if stage == "component_resolution":
            return {
                "meal_title": "早餐店的起司蛋餅",
                "components": ["蛋餅皮", "雞蛋", "起司", "蔥花"],
                "quantity_hints": ["蛋餅 1 份"],
                "source_decision": "ready",
            }, {"stage": stage, "parsed_object": {"source_decision": "ready"}}
        return {
            "protein_g": 14,
            "carb_g": 24,
            "fat_g": 15,
            "estimated_kcal": 280,
            "answer_mode": "direct_answer",
            "component_estimates": [
                {"name": "蛋餅皮", "estimated_kcal": 140, "protein_g": 4, "carb_g": 22, "fat_g": 4},
                {"name": "雞蛋", "estimated_kcal": 70, "protein_g": 6, "carb_g": 1, "fat_g": 5},
                {"name": "起司", "estimated_kcal": 60, "protein_g": 4, "carb_g": 1, "fat_g": 5},
            ],
        }, {"stage": stage, "parsed_object": {"answer_mode": "direct_answer"}}

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    response = client.post("/estimate", json={"text": "早餐店的起司蛋餅", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["source_decision"] == "ready"
    assert payload["route_target"] == "direct_estimate"
    assert payload["estimated_kcal"] == 280
    assert len(payload["llm_traces"]) == 2


def test_ready_then_answer_with_uncertainty(monkeypatch) -> None:
    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        if stage == "component_resolution":
            return {
                "meal_title": "滷排骨便當",
                "components": ["排骨", "白飯", "配菜"],
                "quantity_hints": ["便當 1 份", "飯量未知"],
                "source_decision": "ready",
            }, {"stage": stage, "parsed_object": {"source_decision": "ready"}}
        return {
            "protein_g": 32,
            "carb_g": 68,
            "fat_g": 26,
            "estimated_kcal": 650,
            "answer_mode": "answer_with_uncertainty",
            "uncertain_macro_areas": ["飯量", "排骨油脂"],
        }, {"stage": stage, "parsed_object": {"answer_mode": "answer_with_uncertainty"}}

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    response = client.post("/estimate", json={"text": "滷排骨便當", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "estimate_with_assumptions"
    assert payload["uncertain_macro_areas"] == ["飯量", "排骨油脂"]


def test_ask_user_uses_model_question(monkeypatch) -> None:
    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        return {
            "components": [],
            "source_decision": "ask_user",
            "followup_question": "你早餐實際吃了哪些東西？可以直接跟我說像吐司、蛋、豆漿這樣。",
        }, {"stage": stage, "parsed_object": {"source_decision": "ask_user"}}

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    response = client.post("/estimate", json={"text": "我媽幫我煮的早餐", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "clarify_before_search"
    assert payload["followup_question"] == "你早餐實際吃了哪些東西？可以直接跟我說像吐司、蛋、豆漿這樣。"


def test_ask_user_without_followup_is_logged_not_patched(monkeypatch) -> None:
    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        return {
            "components": [],
            "source_decision": "ask_user",
        }, {"stage": stage, "parsed_object": {"source_decision": "ask_user"}}

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    response = client.post("/estimate", json={"text": "我媽幫我煮的早餐", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "clarify_before_search"
    assert payload["followup_question"] is None
    assert any(step["step"] == "incomplete_followup" for step in payload["debug_steps"])


def test_search_for_components_then_answer(monkeypatch) -> None:
    stages: list[str] = []

    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        stages.append(stage)
        if stage == "component_resolution":
            return {
                "components": [],
                "source_decision": "search",
                "search_query": "勝王辣麻牛肉拉麵 菜單",
            }, {"stage": stage, "parsed_object": {"source_decision": "search"}}
        if stage == "component_resolution_after_search":
            return {
                "meal_title": "勝王辣麻牛肉拉麵",
                "components": ["拉麵", "牛肉", "辣麻湯底"],
                "quantity_hints": ["1 碗"],
                "source_decision": "ready",
            }, {"stage": stage, "parsed_object": {"source_decision": "ready"}}
        return {
            "protein_g": 34,
            "carb_g": 72,
            "fat_g": 30,
            "estimated_kcal": 700,
            "answer_mode": "answer_with_uncertainty",
            "uncertain_macro_areas": ["湯喝了多少"],
        }, {"stage": stage, "parsed_object": {"answer_mode": "answer_with_uncertainty"}}

    async def fake_search(query, max_results=3):
        return [{"title": "勝王辣麻牛肉拉麵", "url": "https://example.com", "snippet": "拉麵、牛肉、辣麻湯底"}]

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    monkeypatch.setattr(search, "search", fake_search)
    response = client.post("/estimate", json={"text": "勝王辣麻牛肉拉麵", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["used_search"] is True
    assert payload["route_target"] == "answer_after_search"
    assert stages == ["component_resolution", "component_resolution_after_search", "macro_estimation"]


def test_search_then_ask_user(monkeypatch) -> None:
    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        if stage == "component_resolution":
            return {
                "components": [],
                "source_decision": "search",
                "search_query": "媽寶堡 早餐 菜單",
            }, {"stage": stage, "parsed_object": {"source_decision": "search"}}
        return {
            "components": [],
            "source_decision": "ask_user",
            "followup_question": "你說的媽寶堡早餐裡面實際吃了哪些東西？可以直接列品項給我。",
        }, {"stage": stage, "parsed_object": {"source_decision": "ask_user"}}

    async def fake_search(query, max_results=3):
        return [{"title": "不夠像的結果", "url": "https://example.com", "snippet": "弱相似資訊"}]

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    monkeypatch.setattr(search, "search", fake_search)
    response = client.post("/estimate", json={"text": "媽寶堡的早餐", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] == "clarify_after_search"
    assert payload["followup_question"]


def test_macro_fallback_when_phase_two_fails(monkeypatch) -> None:
    async def fake_complete(*, stage, system_prompt, user_payload, max_tokens=0):
        if stage == "component_resolution":
            return {
                "meal_title": "早餐店蘿蔔糕",
                "components": ["早餐店蘿蔔糕"],
                "quantity_hints": ["早餐店常見 1 份"],
                "source_decision": "ready",
            }, {"stage": stage, "parsed_object": {"source_decision": "ready"}}
        raise RuntimeError("timeout")

    monkeypatch.setattr(provider, "complete_with_trace", fake_complete)
    response = client.post("/estimate", json={"text": "早餐店蘿蔔糕", "allow_search": True})
    payload = response.json()["payload"]
    assert payload["route_target"] in {"direct_estimate", "estimate_with_assumptions"}
    assert payload["estimated_kcal"] >= 200
    assert any(step["step"] == "macro_fallback" for step in payload["debug_steps"])
