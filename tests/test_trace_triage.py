from __future__ import annotations

import json
from pathlib import Path

from app.logging import get_full_trace, get_trace_summaries
from app.observability.trace_triage import build_live_trace_triage


def test_live_trace_triage_fixture_cases_classify_consistently() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "live_trace_triage_cases.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert cases
    for case in cases:
        triage = build_live_trace_triage(case["trace"])
        assert triage["first_bad_pass"] == case["expected_first_bad_pass"]
        assert triage["suspected_root_cause_bucket"] == case["expected_bucket"]
        assert isinstance(triage["owner_file"], list)


def test_trace_summaries_compute_live_triage_when_missing(tmp_path, monkeypatch) -> None:
    request_dir = tmp_path / "requests"
    request_dir.mkdir(parents=True)
    monkeypatch.setattr("app.logging.REQUEST_TRACE_DIR", request_dir)

    artifact = {
        "request_id": "trace-triage-1",
        "timestamp": "2026-04-06T00:00:00Z",
        "request": {"user_id": "u1", "text": "你可以查查軟實力這家店", "allow_search": True},
        "payload": {"reply_text": "請再描述更具體的食物名稱、份量或配料。"},
        "trace_contract": {
            "tool_decision_trace": {
                "candidate_tool_calls": [{"tool_name": "search_official_nutrition"}],
                "executed_tool_calls": [],
            },
            "final_answer_summary": {"estimated_kcal": 0},
        },
        "llm_traces": [
            {"stage": "decision_pass", "parsed_object": {"next_action": "run_tool_lookup", "tool_plan": "search_official_nutrition"}}
        ],
        "diagnosis": {"failed_layer": "grounding", "trace_health": "degraded", "repairability": "high"},
        "north_star_evaluation": {"win_loss_neutral": "loss"},
        "trace_meta": {"request_id": "trace-triage-1", "user_id": "u1", "timestamp": "2026-04-06T00:00:00Z"},
        "token_usage": {"total_tokens": 42},
    }
    (request_dir / "trace-triage-1.json").write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")

    summaries = get_trace_summaries(limit=10)
    assert summaries["traces"][0]["first_bad_pass"] == "decision_pass"
    assert summaries["traces"][0]["root_cause_bucket"] == "tool_routing_gap"

    detail = get_full_trace("trace-triage-1")
    assert detail is not None
    assert detail["live_trace_triage"]["first_bad_pass"] == "decision_pass"
    assert detail["live_trace_triage"]["suspected_root_cause_bucket"] == "tool_routing_gap"
