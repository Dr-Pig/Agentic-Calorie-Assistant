from __future__ import annotations

from pathlib import Path


CHAT = Path("static/accurate-intake-chat.html")
TODAY = Path("static/accurate-intake-today.html")
BODY = Path("static/accurate-intake-body.html")


def _html(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_product_pages_are_three_separate_static_surfaces_with_shared_nav() -> None:
    for path, page_id in (
        (CHAT, "accurate-intake-chat-page-v1"),
        (TODAY, "accurate-intake-today-page-v1"),
        (BODY, "accurate-intake-body-page-v1"),
    ):
        html = _html(path)
        assert f'data-page-id="{page_id}"' in html
        assert 'href="/static/accurate-intake-chat.html"' in html
        assert 'href="/static/accurate-intake-today.html"' in html
        assert 'href="/static/accurate-intake-body.html"' in html
        assert "product_readiness_claimed=false" in html
        assert "private_self_use_approved=false" in html


def test_chat_page_is_line_like_scrollable_conversation_not_trace_dashboard() -> None:
    html = _html(CHAT)

    assert 'data-surface-role="chat"' in html
    assert 'id="chat-scroll"' in html
    assert "overflow-y: auto" in html
    assert 'id="chat-history-status"' in html
    assert 'id="message-input"' in html
    assert "Conversation history not loaded." in html
    assert "<summary>Conversation settings</summary>" in html
    assert "grid-template-columns: 1fr;" in html
    assert 'body: JSON.stringify({ text, user_id: userId(), allow_search: false })' in html
    assert 'chatHistory: "/accurate-intake/chat-history"' in html
    assert 'estimate: "/estimate"' in html
    assert "history:" not in html
    assert "messages.sort" not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_chat_page_can_send_local_access_header_for_history_without_storage() -> None:
    html = _html(CHAT)

    assert 'id="local-access-token"' in html
    assert "window.LOCAL_DEBUG_API_TOKEN" in html
    assert '"X-Local-Debug-Token": token' in html
    assert "localDebugHeaders" in html
    assert "localDebugHeaders(url)" in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_today_page_is_daily_diary_with_date_navigation_and_no_trace_panel() -> None:
    html = _html(TODAY)

    assert 'data-surface-role="today-diary"' in html
    assert 'id="selected-date"' in html
    assert 'id="previous-day"' in html
    assert 'id="next-day"' in html
    assert 'id="day-strip"' in html
    assert 'id="budget-kcal"' in html
    assert 'id="consumed-kcal"' in html
    assert 'id="remaining-kcal"' in html
    assert 'id="meal-list"' in html
    assert "Daily record updated." in html
    assert "overflow-x: auto" in html
    assert 'currentBudget: "/today/current-budget"' in html
    assert 'chatLink.href = `/static/accurate-intake-chat.html?user_id=${encodeURIComponent(userId())}&local_date=${selectedDate()}`;' in html
    assert "status:" not in html
    assert "trace" not in html.lower()
    assert "/accurate-intake/debug" not in html


def test_body_page_covers_plan_weight_goal_activity_inputs_without_frontend_tdee_math() -> None:
    html = _html(BODY)

    assert 'data-surface-role="body-plan"' in html
    assert 'id="body-plan-summary"' in html
    assert 'id="weight-history"' in html
    assert 'id="weight-kg"' in html
    assert 'id="target-weight-kg"' in html
    assert 'id="daily-lifestyle"' in html
    assert 'id="weekly-exercise-days-band"' in html
    assert 'id="weekly-target-rate-kg"' in html
    assert 'bodyPlan: "/body-plan/active"' in html
    assert 'weightHistory: "/weight/observations"' in html
    assert 'weightObservation: "/weight/observation"' in html
    assert 'onboarding: "/onboarding/bootstrap"' in html
    assert 'manualTarget: "/body-plan/manual-daily-target"' in html
    assert "Set up your body plan to see targets." in html
    assert 'const isActive = plan.plan_status === "active";' in html
    assert "Mostly sitting, some walking" in html
    assert "Lose weight" in html
    assert "status:" not in html
    forbidden_math = [
        "calculateTdee",
        "calculateBmr",
        "activityMultiplier",
        "dailyDeficit =",
        "7700",
    ]
    for fragment in forbidden_math:
        assert fragment not in html


def test_product_pages_do_not_claim_fooddb_websearch_live_or_debug_truth() -> None:
    combined = "\n".join(_html(path) for path in (CHAT, TODAY, BODY)).lower()

    forbidden = [
        "fooddb_evidence_used=true",
        "real_fooddb_pass_claimed=true",
        "web_tavily_used=true",
        "live_llm_invoked=true",
        "web_readiness_claimed=true",
        "debug surface",
        "last runtime payload",
        "last turn trace",
    ]
    for fragment in forbidden:
        assert fragment not in combined
