from __future__ import annotations

from pathlib import Path


SHELL_PATH = Path("static/accurate-intake-local-shell.html")


def _shell_html() -> str:
    return SHELL_PATH.read_text(encoding="utf-8")


def test_local_web_shell_is_a_static_runtime_mirror_surface() -> None:
    html = _shell_html()

    assert 'data-shell-id="accurate-intake-local-shell-v1"' in html
    assert 'data-runtime-endpoint="/estimate"' in html
    assert 'data-budget-endpoint="/today/current-budget"' in html
    assert 'data-body-plan-endpoint="/body-plan/active"' in html
    assert 'data-debug-endpoint="/accurate-intake/debug"' in html
    assert 'data-chat-history-endpoint="/accurate-intake/chat-history"' in html
    assert 'data-frontend-semantic-owner="false"' in html
    assert 'data-live-llm-required="false"' in html
    assert 'data-production-readiness-claimed="false"' in html


def test_local_web_shell_posts_raw_message_to_runtime_without_semantic_routing() -> None:
    html = _shell_html()

    assert 'body: JSON.stringify({ text, user_id: userId(), allow_search: false })' in html
    assert 'X-Canary-Page-Version' in html
    assert "payload.coach_message" in html

    forbidden_fragments = [
        "routeByKeyword",
        "rawTextRouting",
        "message.includes",
        "input.includes",
        "text.includes",
        "switch (text",
        "estimateKcal",
        "estimatedKcal",
        "workflow_effect",
        "target_attachment",
        "final_action =",
        "mutation_allowed =",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in html


def test_local_web_shell_reads_chat_history_from_backend_sqlite_surface() -> None:
    html = _shell_html()

    assert 'chatHistory: "/accurate-intake/chat-history"' in html
    assert "renderChatHistory(chatHistory)" in html
    assert "source === \"sqlite_message_buffer\"" in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_local_web_shell_displays_read_models_without_recomputing_budget_truth() -> None:
    html = _shell_html()

    assert "renderBudget(budget)" in html
    assert "renderBodyPlan(bodyPlan)" in html
    assert "renderDebug(debug)" in html
    assert '<span id="consumed-kcal">unavailable</span>' in html
    assert 'source: ${sameTruth.source_truth || "unavailable"}' in html
    assert "view.budget_kcal" in html
    assert "view.consumed_kcal" in html
    assert "view.remaining_kcal" in html

    forbidden_budget_recomputations = [
        "budget - consumed",
        "budget_kcal - consumed_kcal",
        "daily_target_kcal - consumed_kcal",
        "consumed +",
        "remaining =",
        "remainingKcal =",
    ]
    for fragment in forbidden_budget_recomputations:
        assert fragment not in html


def test_local_web_shell_uses_backend_budget_date_instead_of_browser_date_truth() -> None:
    html = _shell_html()

    assert 'id="local-date-display" readonly' in html
    assert 'id="local-date" type="date"' not in html
    assert "function todayLabel()" not in html
    assert "let backendLocalDate = null;" in html
    assert "backendLocalDate = budget.local_date || null;" in html
    assert 'writeText("local-date-display", backendLocalDate);' in html
    assert "local_date: backendLocalDate" in html
    assert "local_date: localDate()" not in html


def test_local_web_shell_uses_manual_target_api_without_owning_body_plan_truth() -> None:
    html = _shell_html()

    assert 'manualTarget: "/body-plan/manual-daily-target"' in html
    assert "daily_target_kcal: target" in html
    assert 'source: "user_ui"' in html
    assert "payload.current_budget?.budget_kcal" in html
    assert "set_manual_daily_target" not in html


def test_self_use_runbook_documents_local_browser_shell_boundary() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(encoding="utf-8-sig")

    assert "/static/accurate-intake-local-shell.html" in runbook
    assert "posts raw chat text to `/estimate`" in runbook
    assert "must not infer intent, workflow, target attachment, disposition, kcal" in runbook
