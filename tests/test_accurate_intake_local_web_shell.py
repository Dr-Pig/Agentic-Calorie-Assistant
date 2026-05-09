from __future__ import annotations

from pathlib import Path


SHELL_PATH = Path("static/accurate-intake-local-shell.html")


def _shell_html() -> str:
    return SHELL_PATH.read_text(encoding="utf-8")


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


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


def test_local_web_shell_has_render_only_review_debug_panels() -> None:
    html = _shell_html()

    for selector in (
        'id="last-turn-trace-list"',
        'id="pending-followup-list"',
        'id="runtime-status-list"',
        'id="failure-signal-list"',
    ):
        assert selector in html

    assert "renderReviewPanel(debug, chatHistory)" in html
    assert "valueOrNotAvailable" in html
    assert "runtime_turn_trace_present" in html
    assert "context_snapshot_present" in html
    assert "trace_chain_complete" in html
    assert "pending_followup_linkage_present" in html
    assert "structured_followup_question" in html
    assert "not_available" in html


def test_local_web_shell_operator_ui_polish_preserves_information_architecture() -> None:
    html = _shell_html()

    assert 'data-ui-polish-version="plce-ui-same-truth-polish-v1"' in html
    assert 'data-read-model-owner="backend"' in html
    assert 'data-mutation-authority="backend-route-only"' in html
    assert 'id="operator-boundary-list"' in html
    assert 'id="sync-status"' in html
    assert 'id="local-debug-token"' in html
    assert "mutation_submit=backend_route_only" in html
    for selector in (
        'id="budget-kcal"',
        'id="consumed-kcal"',
        'id="remaining-kcal"',
        'id="body-plan-list"',
        'id="same-truth-list"',
        'id="meal-thread-list"',
        'id="draft-correction-list"',
        'id="last-turn-trace-list"',
        'id="pending-followup-list"',
        'id="runtime-status-list"',
        'id="failure-signal-list"',
        'id="last-payload"',
    ):
        assert selector in html


def test_local_web_shell_ui_polish_uses_accessible_control_and_focus_tokens() -> None:
    html = _shell_html()

    assert "min-height: 44px" in html
    assert ":focus-visible" in html
    assert "outline:" in html
    assert "letter-spacing: 0;" in html
    assert "overflow-wrap: anywhere" in html
    assert "word-break: break-word" in html
    assert "repeat(auto-fit, minmax(150px, 1fr))" in html
    assert "repeat(auto-fit, minmax(132px, 1fr))" in html
    assert "grid-template-columns: minmax(0, 1fr)" in html
    assert "@media (max-width: 640px)" in html
    assert 'aria-label="Local chat message"' in html
    assert 'aria-label="Local debug token"' in html
    assert "const nextBackendLocalDate = budget.local_date || null;" in html
    chat_history_fetch = (
        'const chatHistory = await requestJson(`${endpoints.chatHistory}?${debugQuery.toString()}`, debugOptions);'
    )
    assert html.index(chat_history_fetch) < html.index("writeText(\"local-date-display\", backendLocalDate);")
    assert "radial-gradient" not in html
    assert "gradient orb" not in html.lower()


def test_local_web_shell_cjk_copy_is_valid_utf8_and_not_mojibake() -> None:
    raw = SHELL_PATH.read_bytes()
    html = raw.decode("utf-8")

    assert raw.startswith(b"\xef\xbb\xbf") is False
    assert "\ufffd" not in html
    assert _contains_cjk(html)
    assert "LINE" in html
    assert "runtime" in html


def test_local_web_shell_renders_manager_context_trace_fields_without_inference() -> None:
    html = _shell_html()

    for fragment in (
        "context_policy_version",
        "loaded_context_summary",
        "omitted_context_summary",
        "pending_pins_present",
        "target_candidate_count",
        "not_checked",
    ):
        assert fragment in html

    for forbidden_fragment in (
        "manager_context_gap",
        "inferManagerContext",
        "inferEvidenceGap",
        "selectTarget",
    ):
        assert forbidden_fragment not in html


def test_local_web_shell_debug_panel_uses_current_backend_read_model_fields_only() -> None:
    html = _shell_html()

    assert "thread.active_version?.total_kcal" in html
    assert "thread.active_version?.status" in html
    assert "thread.active_version?.items" in html
    assert "correction.removed_item_names" in html
    assert "correction.non_target_item_names_preserved" in html
    assert "view.budget_kcal" in html
    assert "view.recommended_target_kcal" in html

    obsolete_fallbacks = [
        "thread.total_kcal",
        "thread.kcal",
        "view.daily_target_kcal",
        "view.target_kcal",
    ]
    for fragment in obsolete_fallbacks:
        assert fragment not in html


def test_local_web_shell_uses_backend_budget_date_instead_of_browser_date_truth() -> None:
    html = _shell_html()

    assert 'id="local-date-display" readonly' in html
    assert 'id="local-date" type="date"' not in html
    assert "function todayLabel()" not in html
    assert "let backendLocalDate = null;" in html
    assert "const nextBackendLocalDate = budget.local_date || null;" in html
    assert "backendLocalDate = nextBackendLocalDate;" in html
    assert 'writeText("local-date-display", backendLocalDate);' in html
    chat_history_fetch = (
        'const chatHistory = await requestJson(`${endpoints.chatHistory}?${debugQuery.toString()}`, debugOptions);'
    )
    assert html.index(chat_history_fetch) < html.index("backendLocalDate = nextBackendLocalDate;")
    assert 'if ("value" in target)' in html
    assert "target.value = rendered;" in html
    assert "local_date: backendLocalDate" in html
    assert "local_date: localDate()" not in html


def test_local_web_shell_uses_explicit_local_debug_token_without_storage() -> None:
    html = _shell_html()

    assert "function localDebugHeaders(url = null)" in html
    assert '"X-Local-Debug-Token": token' in html
    assert "localDebugHeaders()" in html
    assert "window.LOCAL_DEBUG_API_TOKEN" in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


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
