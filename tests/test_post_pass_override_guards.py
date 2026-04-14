from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.application.context_assembly import should_soft_avoid_exact_for_generic_drink
from app.schemas import EstimateRequest, FinalResponseResult
from app.usecases.text_meal_response_support import finalize_response_payload


def _trace_envelope() -> SimpleNamespace:
    return SimpleNamespace(
        trace_contract={},
        north_star_evaluation={},
        multi_turn_context={},
        token_usage={},
        trace_meta={},
        span_timeline=[],
        decision_journal={},
        evidence_journal={},
        diagnosis={},
        context_pack_trace={},
        tool_decision_trace={},
        boundary_trace={},
        judge_trace={},
        evidence_resolution_trace={},
        memory_trace={},
    )


def test_finalize_response_does_not_deterministically_rewrite_llm_posture(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_final_response(**_: object) -> FinalResponseResult:
        return FinalResponseResult(reply_text="約 394 kcal。", asked_follow_up=False, ui_hints={})

    def _fake_build_payload(request, **kwargs):
        captured["parsed"] = dict(kwargs["parsed"])
        captured["action_taken"] = kwargs["action_taken"]
        return SimpleNamespace(
            follow_up_needed=kwargs["parsed"].get("follow_up_needed"),
            followup_question=kwargs["parsed"].get("followup_question"),
            action_taken=kwargs["action_taken"],
        )

    monkeypatch.setattr(
        "app.usecases.text_meal_response_support.run_four_pass_final_response",
        _fake_final_response,
    )
    monkeypatch.setattr(
        "app.usecases.text_meal_response_support.build_payload",
        _fake_build_payload,
    )

    payload = asyncio.run(
        finalize_response_payload(
            primary_llm=object(),
            effective_request=EstimateRequest(text="我剛剛喝珍珠奶茶"),
            request_id="req-posture",
            task_meal_link_result=SimpleNamespace(),
            decision_result=SimpleNamespace(),
            nutrition_result=None,
            conversation_state=SimpleNamespace(active_meal_summary=SimpleNamespace(model_dump=lambda mode="json": {})),
            llm_traces=[],
            max_tokens=512,
            run_stage=None,
            best_parsed={
                "title": "珍珠奶茶",
                "estimated_kcal": 394,
                "protein_g": 0,
                "carb_g": 0,
                "fat_g": 0,
                "components": [],
                "estimate_mode": "exact_item",
                "action_taken": "clarify_before_estimate",
                "response_mode_hint": "clarify_first",
                "follow_up_needed": True,
                "followup_question": "杯量是多大？",
                "unresolved_info": ["cup_size"],
                "uncertainty_factors": [],
            },
            risk_packet={},
            action_taken="clarify_before_estimate",
            route_target="clarify_user_private",
            debug_steps=[],
            best_quality={},
            retry_triggered=False,
            retry_reason=None,
            best_source="test",
            best_private=False,
            retrieval_triggered=False,
            retrieval_query=None,
            filtered_knowledge=[],
            used_search=False,
            search_query=None,
            search_quality=None,
            sources=[],
            trace_envelope=_trace_envelope(),
        )
    )

    assert payload.follow_up_needed is False
    assert payload.followup_question in ("", None)
    assert payload.action_taken == "clarify_before_estimate"
    assert captured["parsed"]["response_mode_hint"] == "clarify_first"
    assert captured["parsed"]["action_taken"] == "clarify_before_estimate"
    assert captured["parsed"]["unresolved_info"] == ["cup_size"]


def test_soft_avoid_exact_for_generic_drink_requires_no_explicit_identity_cue() -> None:
    assert (
        should_soft_avoid_exact_for_generic_drink(
            user_input="我剛剛喝珍珠奶茶",
            standardized_drink_like=True,
            packaged_exact_candidate_count=1,
            exact_brand_hints=["7-11 CITY CAFE"],
        )
        is True
    )
    assert (
        should_soft_avoid_exact_for_generic_drink(
            user_input="我剛剛喝 7-11 珍珠奶茶",
            standardized_drink_like=True,
            packaged_exact_candidate_count=1,
            exact_brand_hints=["7-11 CITY CAFE"],
        )
        is False
    )
