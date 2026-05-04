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


def test_product_pages_preserve_user_and_date_in_nav_without_token_query() -> None:
    for path in (CHAT, TODAY, BODY):
        html = _html(path)

        assert 'data-nav-target="chat"' in html
        assert 'data-nav-target="today"' in html
        assert 'data-nav-target="body"' in html
        assert "function updateNavigationLinks()" in html
        assert "encodeURIComponent(userId())" in html
        assert "local_date=${encodeURIComponent(selectedDate())}" in html
        assert "updateNavigationLinks();" in html
        assert "local_debug_token" not in html


def test_chat_page_is_line_like_scrollable_conversation_not_trace_dashboard() -> None:
    html = _html(CHAT)

    assert 'data-surface-role="chat"' in html
    assert 'id="chat-scroll"' in html
    assert 'id="chat-day-link"' in html
    assert 'class="action-link" data-nav-target="today"' in html
    assert "overflow-y: auto" in html
    assert 'id="chat-history-status"' in html
    assert "clip: rect(0 0 0 0)" not in html
    assert "Conversation loading" in html or "Conversation history not loaded." in html
    assert 'id="message-input"' in html
    assert "Conversation history not loaded." in html
    assert "<summary>Conversation settings</summary>" in html
    assert "grid-template-columns: 1fr;" in html
    assert 'body: JSON.stringify({ text, user_id: userId(), local_date: selectedDate(), allow_search: false })' in html
    assert 'chatHistory: "/accurate-intake/chat-history"' in html
    assert 'estimate: "/estimate"' in html
    assert "history:" not in html
    assert "messages.sort" not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_chat_composer_supports_enter_send_and_shift_enter_multiline() -> None:
    html = _html(CHAT)

    assert '<textarea id="message-input"' in html
    assert 'rows="1"' in html
    assert 'addEventListener("keydown"' in html
    assert 'event.key === "Enter"' in html
    assert "!event.shiftKey" in html
    assert "event.isComposing" in html
    assert "requestSubmit()" in html


def test_chat_page_can_send_local_access_header_for_history_without_visible_debug_control() -> None:
    html = _html(CHAT)

    assert 'id="local-access-token"' not in html
    assert "Local access token" not in html
    assert "window.LOCAL_DEBUG_API_TOKEN" in html
    assert '"X-Local-Debug-Token": token' in html
    assert "localDebugHeaders" in html
    assert "localDebugHeaders(url)" in html
    assert "local_debug_token" not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_today_page_is_daily_diary_with_date_navigation_and_no_trace_panel() -> None:
    html = _html(TODAY)

    assert 'data-surface-role="today-diary"' in html
    assert 'id="selected-date"' in html
    assert 'id="user-id"' in html
    assert 'el("user-id").value = params.get("user_id") || el("user-id").value;' in html
    assert 'return el("user-id").value.trim() || "default_user";' in html
    assert 'id="previous-day"' in html
    assert 'id="next-day"' in html
    assert 'id="day-strip"' in html
    assert 'aria-label="Previous day"' in html
    assert 'aria-label="Next day"' in html
    assert "day-button-date" in html
    assert "day-button-weekday" in html
    assert 'new Intl.DateTimeFormat("zh-TW", { weekday: "short" })' in html
    assert 'id="budget-kcal"' in html
    assert 'id="consumed-kcal"' in html
    assert 'id="remaining-kcal"' in html
    assert 'id="meal-list"' in html
    assert 'id="chat-link" class="action-link"' in html
    assert "Daily record updated." in html
    assert "overflow-x: auto" in html
    assert 'currentBudget: "/today/current-budget"' in html
    assert 'chatLink.href = `/static/accurate-intake-chat.html?user_id=${encodeURIComponent(userId())}&local_date=${selectedDate()}`;' in html
    assert "status:" not in html
    assert "trace" not in html.lower()
    assert "/accurate-intake/debug" not in html


def test_today_page_updates_current_url_when_selected_date_changes() -> None:
    html = _html(TODAY)

    assert "function updateCurrentUrl()" in html
    assert "window.history.replaceState" in html
    assert 'pageUrl("today")' in html
    assert "updateCurrentUrl();" in html


def test_chat_and_body_pages_update_current_url_when_session_inputs_change() -> None:
    for path, page in ((CHAT, "chat"), (BODY, "body")):
        html = _html(path)

        assert "function updateCurrentUrl()" in html
        assert "window.history.replaceState" in html
        assert f'pageUrl("{page}")' in html
        assert "updateCurrentUrl();" in html
        assert 'el("local-date").addEventListener("change", () => {\n      updateCurrentUrl();' in html
        assert 'el("user-id").addEventListener("change", () => {\n      updateCurrentUrl();' in html


def test_body_page_covers_plan_weight_goal_activity_inputs_without_frontend_tdee_math() -> None:
    html = _html(BODY)

    assert 'data-surface-role="body-plan"' in html
    assert 'class="page-actions"' in html
    assert 'data-nav-target="today"' in html
    assert 'data-nav-target="chat"' in html
    assert 'id="body-plan-summary"' in html
    assert 'id="weight-history"' in html
    assert 'id="weight-kg"' in html
    assert 'aria-describedby="weight-kg-hint"' in html
    assert 'id="target-weight-kg"' in html
    assert 'id="daily-lifestyle"' in html
    assert 'id="weekly-exercise-days-band"' in html
    assert 'id="weekly-target-rate-kg"' in html
    assert 'id="manual-target-form"' in html
    assert 'el("manual-target-form").addEventListener("submit"' in html
    assert 'aria-describedby="weekly-target-rate-hint"' in html
    assert 'aria-describedby="manual-daily-target-hint"' in html
    assert 'inputmode="decimal"' in html
    assert 'inputmode="numeric"' in html
    assert 'bodyPlan: "/body-plan/active"' in html
    assert 'weightHistory: "/weight/observations"' in html
    assert 'weightObservation: "/weight/observation"' in html
    assert 'onboarding: "/onboarding/bootstrap"' in html
    assert 'manualTarget: "/body-plan/manual-daily-target"' in html
    assert "Set up your body plan to see targets." in html
    assert 'const isActive = plan.plan_status === "active";' in html
    assert "Mostly sitting, some walking" in html
    assert "Lose weight" in html
    assert 'placeholder="e.g. 34" required' in html
    assert 'placeholder="e.g. 170" required' in html
    assert 'placeholder="e.g. 70" required' in html
    assert 'placeholder="e.g. 0.5" required' in html
    assert 'placeholder="e.g. 1600"' in html
    assert 'value="34"' not in html
    assert 'value="170"' not in html
    assert 'value="70"' not in html
    assert 'value="0.5"' not in html
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


def test_product_pages_cjk_copy_bytes_are_not_mojibake_or_replacement_text() -> None:
    expected_copy = {
        CHAT: "像 LINE 一樣輸入和回看飲食對話",
        TODAY: "每天一頁看熱量目標",
        BODY: "先把體重、目標、活動量和每日熱量目標整理清楚",
    }

    for path, expected in expected_copy.items():
        html = _html(path)
        assert expected in html
        assert "\ufffd" not in html
        assert "�" not in html
        assert "?" not in html
        assert "瘥予" not in html


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
