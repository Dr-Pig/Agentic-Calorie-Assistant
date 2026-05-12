from __future__ import annotations

from pathlib import Path


CHAT = Path("static/accurate-intake-chat.html")
TODAY = Path("static/accurate-intake-today.html")
BODY = Path("static/accurate-intake-body.html")
FEEDBACK = Path("static/accurate-intake-feedback.html")
REVIEW = Path("static/accurate-intake-review.html")
DATA = Path("static/accurate-intake-data.html")
DESKTOP = Path("static/accurate-intake-desktop.html")


def _html(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_product_pages_are_three_separate_static_surfaces_with_shared_nav() -> None:
    for path, page_id in (
        (DESKTOP, "accurate-intake-desktop-entry-v1"),
        (CHAT, "accurate-intake-chat-page-v1"),
        (TODAY, "accurate-intake-today-page-v1"),
        (BODY, "accurate-intake-body-page-v1"),
        (FEEDBACK, "accurate-intake-feedback-page-v1"),
        (REVIEW, "accurate-intake-review-page-v1"),
        (DATA, "accurate-intake-data-page-v1"),
    ):
        html = _html(path)
        assert f'data-page-id="{page_id}"' in html
        assert 'href="/static/accurate-intake-desktop.html"' in html
        assert 'href="/static/accurate-intake-chat.html"' in html
        assert 'href="/static/accurate-intake-today.html"' in html
        assert 'href="/static/accurate-intake-body.html"' in html
        assert 'href="/static/accurate-intake-feedback.html"' in html
        assert 'href="/static/accurate-intake-review.html"' in html
        assert 'href="/static/accurate-intake-data.html"' in html


def test_product_pages_preserve_user_and_date_in_nav_without_token_query() -> None:
    for path in (CHAT, TODAY, BODY, FEEDBACK, REVIEW, DATA, DESKTOP):
        html = _html(path)

        assert 'data-nav-target="desktop"' in html
        assert 'data-nav-target="chat"' in html
        assert 'data-nav-target="today"' in html
        assert 'data-nav-target="body"' in html
        assert 'data-nav-target="feedback"' in html
        assert 'data-nav-target="review"' in html
        assert 'data-nav-target="data"' in html
        assert "function updateNavigationLinks()" in html
        assert "new URLSearchParams" in html
        assert "user_id" in html
        assert "local_date" in html
        assert 'query.set("source_page"' in html
        assert "updateNavigationLinks();" in html
        assert "local_debug_token=" not in html


def test_desktop_entry_page_is_local_hub_not_runtime_truth_owner() -> None:
    html = _html(DESKTOP)

    assert 'data-surface-role="desktop-dogfood-entry"' in html
    assert 'data-claim-scope="local_desktop_operator_entry"' in html
    assert 'data-product-truth-owner="backend_local_sqlite"' in html
    assert 'data-frontend-semantic-owner="false"' in html
    assert 'data-manager-context-injection="false"' in html
    assert 'data-fooddb-truth-update-allowed="false"' in html
    assert 'data-canonical-eval-promotion-allowed="false"' in html
    assert 'data-token-in-url-allowed="false"' in html
    assert 'id="user-id"' in html
    assert 'id="local-date"' in html
    assert 'id="local-debug-token"' in html
    assert 'id="establish-local-session"' in html
    assert 'localDebugSession: "/accurate-intake/local-debug-session"' in html
    assert "async function checkLocalDebugSession()" in html
    assert "checkLocalDebugSession();" in html
    assert "window.establishLocalDebugSessionForSmoke = establishLocalDebugSession;" in html
    assert 'body: JSON.stringify({ token })' in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html
    assert "product_readiness_claimed=true" not in html
    assert "private_self_use_approved=true" not in html


def test_data_page_is_local_only_export_surface_not_truth_or_readiness_surface() -> None:
    html = _html(DATA)

    assert 'data-surface-role="local-data-hygiene"' in html
    assert 'data-claim-scope="local_operator_data_hygiene_review_checkpoint"' in html
    assert 'data-product-truth-owner="backend_local_sqlite"' in html
    assert 'data-fooddb-truth-update-allowed="false"' in html
    assert 'data-canonical-eval-promotion-allowed="false"' in html
    assert 'hygiene: "/accurate-intake/local-data-hygiene"' in html
    assert 'backup: "/accurate-intake/local-data-hygiene/backup"' in html
    assert 'export: "/accurate-intake/local-data-hygiene/export"' in html
    assert 'id="inspect-data"' in html
    assert 'id="backup-data"' in html
    assert 'id="export-data"' in html
    assert 'id="data-status"' in html
    assert "Inspect local data" in html
    assert "Backup local SQLite" in html
    assert "Export review bundle" in html
    assert "Data backup & export" in html
    assert "Inspect local data shows where the local SQLite and review evidence live." in html
    assert "Backup local SQLite copies the local database before risky manual changes." in html
    assert "Export review bundle packages feedback, traces, and local metadata for later review." in html
    assert "HTTP 403 usually means this page was opened before the local session cookie was established." in html
    assert "function dataErrorMessage(kind, error)" in html
    assert "function friendlyPageUrl(page)" in html
    assert 'friendlyPageUrl("data")' in html
    assert "reconnect_attempted" in html
    assert "error.status = response.status;" in html
    assert 'id="data-action-summary"' in html
    assert 'id="result-operation"' in html
    assert 'id="result-db-path"' in html
    assert 'id="result-backup-path"' in html
    assert 'id="result-export-path"' in html
    assert 'id="result-manifest-path"' in html
    assert 'id="result-sidecars"' in html
    assert "Raw local response" in html
    assert "Open Feedback" not in html
    assert "Open Review" not in html
    assert "backup_required_before_reset" in html
    assert "operation_previews" in html
    for forbidden in (
        "localStorage",
        "sessionStorage",
        "product_ready",
        "private_self_use_approved: true",
        "fooddb_truth_updated: true",
        "canonical_eval_promoted: true",
        "/accurate-intake/local-data-hygiene/reset",
        "/accurate-intake/local-data-hygiene/import",
    ):
        assert forbidden not in html


def test_chat_page_is_line_like_scrollable_conversation_not_trace_dashboard() -> None:
    html = _html(CHAT)

    assert 'data-surface-role="chat"' in html
    assert 'id="chat-scroll"' in html
    assert 'id="chat-scroll" aria-live="polite" role="log" aria-relevant="additions text"' in html
    assert 'id="chat-day-link"' in html
    assert 'id="chat-session-user"' in html
    assert 'id="chat-session-date"' in html
    assert 'id="chat-context-strip"' in html
    assert 'id="chat-context-policy"' in html
    assert 'id="chat-context-loaded"' in html
    assert 'id="chat-context-omitted"' in html
    assert 'id="chat-context-pins"' in html
    assert 'id="chat-context-targets"' in html
    assert 'id="chat-target-candidate-surface"' in html
    assert 'id="chat-target-candidate-list"' in html
    assert 'aria-readonly="true"' in html
    assert "Latest policy" in html
    assert "Latest pins" in html
    assert "Latest targets" in html
    assert 'class="action-link" data-nav-target="today"' in html
    assert "overflow-y: auto" in html
    assert 'id="chat-history-status"' in html
    assert "function feedbackUrlForMessage(message = {})" in html
    assert 'report.dataset.feedbackAction = "report-message";' in html
    assert 'report.textContent = "Report";' in html
    assert 'source_page: CURRENT_PAGE' in html
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


def test_chat_page_renders_assistant_replies_only_from_backend_sources() -> None:
    html = _html(CHAT)

    assert 'data-reply-source="backend_render_contract"' in html
    assert "function appendMessage(role, text, source = \"backend_message\", message = {})" in html
    assert "row.dataset.messageRole = role;" in html
    assert "bubble.dataset.renderSource = source;" in html
    assert 'appendMessage(role, message.content || "", "chat_history.sqlite_message_buffer", message);' in html
    assert 'data-render-source="static_welcome"' in html
    assert 'pending.dataset.renderSource = "estimate.coach_message";' in html
    assert "pending.textContent = payload.coach_message ||" in html
    assert '"estimate.coach_message"' in html

    forbidden = [
        "payload.final_action",
        "payload.workflow_effect",
        "payload.estimated_kcal",
        "payload.remaining_kcal",
        "payload.macro",
        "coach_message.includes",
        "message.content.includes",
    ]
    for fragment in forbidden:
        assert fragment not in html


def test_chat_page_context_status_renders_only_chat_history_structured_fields() -> None:
    html = _html(CHAT)

    assert "function contextSummaryFromHistory(payload)" in html
    assert "const latestContext = [...messages].reverse().find" in html
    assert "latestContext.context_policy_version" in html
    assert "latestContext.loaded_context_summary" in html
    assert "latestContext.omitted_context_summary" in html
    assert "latestContext.pending_pins_present === true" in html
    assert "Number(latestContext.target_candidate_count)" in html
    assert "Array.isArray(message.target_candidate_names)" in html
    assert "latestContext.target_candidate_names" in html
    assert "function renderTargetCandidates(names)" in html
    assert "not_available" in html
    assert "not_checked" in html
    assert "reduce((count" not in html
    assert "pending_followup_linkage_present === true" not in html

    forbidden = [
        "message.content.includes",
        "message.content.match",
        "raw text intent",
        "context_snapshot_present ?",
        "manager_context_gap",
        "final_action",
        "workflow_effect",
        "calculate",
        "mutation_legality",
    ]
    for fragment in forbidden:
        assert fragment not in html


def test_chat_composer_supports_enter_send_and_shift_enter_multiline() -> None:
    html = _html(CHAT)

    assert '<textarea id="message-input"' in html
    assert 'rows="1"' in html
    assert '<form id="composer" class="composer" aria-busy="false">' in html
    assert 'addEventListener("keydown"' in html
    assert 'event.key === "Enter"' in html
    assert "!event.shiftKey" in html
    assert "event.isComposing" in html
    assert "requestSubmit()" in html
    assert "function setComposerBusy(isBusy)" in html
    assert 'el("composer").setAttribute("aria-busy", isBusy ? "true" : "false");' in html
    assert 'el("message-input").disabled = isBusy;' in html
    assert 'el("send-button").disabled = isBusy;' in html
    assert "function fitComposerInput()" in html
    assert 'el("message-input").addEventListener("input", fitComposerInput);' in html
    assert "setComposerBusy(true);" in html
    assert "setComposerBusy(false);" in html


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
    assert 'data-read-model-source="/today/current-budget"' in html
    assert 'data-overshoot-source="backend_explicit_field_required"' in html
    assert 'id="selected-date"' in html
    assert 'id="user-id"' in html
    assert 'id="today-session-user"' in html
    assert 'id="today-session-date"' in html
    assert 'id="today-chat-state"' in html
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
    assert 'id="macro-panel"' in html
    assert 'id="protein-g"' in html
    assert 'id="carbs-g"' in html
    assert 'id="fat-g"' in html
    assert 'id="macro-guard-reason"' in html
    assert 'id="meal-list"' in html
    assert 'id="chat-link" class="action-link"' in html
    assert "function feedbackUrlForMeal(meal = {})" in html
    assert "meal.meal_thread_id" in html
    assert 'report.dataset.feedbackAction = "report-meal";' in html
    assert 'report.textContent = "Report";' in html
    assert "query.set(\"meal_id\", String(meal.meal_thread_id));" in html
    assert "query.set(\"meal_title\", meal.meal_title);" in html
    assert "Daily record updated." in html
    assert "overflow-x: auto" in html
    assert 'currentBudget: "/today/current-budget"' in html
    assert 'chatLink.href = `/static/accurate-intake-chat.html?user_id=${encodeURIComponent(userId())}&local_date=${selectedDate()}`;' in html
    assert "function updateSessionStrip()" in html
    assert "function renderBudgetSummary(payload)" in html
    assert "renderBudgetSummary(payload);" in html
    assert "function renderMacroPanel(payload)" in html
    assert "renderMacroPanel(payload);" in html
    assert 'el("today-session-user").textContent = userId();' in html
    assert 'el("today-session-date").textContent = selectedDate();' in html
    assert "status:" not in html
    assert "trace" not in html.lower()
    assert "/accurate-intake/debug" not in html
    assert "message.content.includes" not in html
    assert "payload.coach_message" not in html
    assert "meal.meal_title.includes" not in html
    assert "query.set(\"meal_id\", meal.meal_title" not in html


def test_today_page_budget_and_macro_fields_are_backend_read_model_render_sources() -> None:
    html = _html(TODAY)

    for field_id, backend_field in (
        ("budget-kcal", "payload.budget_kcal"),
        ("consumed-kcal", "payload.consumed_kcal"),
        ("remaining-kcal", "payload.remaining_kcal"),
        ("protein-g", "payload.consumed_protein"),
        ("carbs-g", "payload.consumed_carbs"),
        ("fat-g", "payload.consumed_fat"),
        ("macro-guard-reason", "payload.macro_guard_reason"),
    ):
        assert f'id="{field_id}"' in html
        assert f'data-render-field="{backend_field}"' in html

    assert 'data-render-field="payload.show_macro"' in html
    assert 'data-render-status="render_backend_structured_fields_only"' in html
    assert 'writeText("budget-kcal", payload.budget_kcal);' in html
    assert 'writeText("consumed-kcal", payload.consumed_kcal);' in html
    assert 'writeText("remaining-kcal", payload.remaining_kcal);' in html
    assert 'const showMacro = payload.show_macro === true;' in html

    forbidden = [
        "payload.remaining_kcal < 0",
        "payload.remaining_kcal <= 0",
        "Math.abs(payload.remaining_kcal)",
        "remaining_kcal <",
        "frontend_infer_overshoot",
        "payload.consumed_protein +",
        "payload.consumed_carbs +",
        "payload.consumed_fat +",
        "target - consumed",
    ]
    for fragment in forbidden:
        assert fragment not in html



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


def test_body_page_refetches_read_model_when_selected_date_changes() -> None:
    html = _html(BODY)

    expected = (
        'el("local-date").addEventListener("change", () => {\n'
        "      updateCurrentUrl();\n"
        "      updateNavigationLinks();\n"
        "      updateSessionStrip();\n"
        '      loadBody().catch((error) => { el("body-status").textContent = `Could not load body plan: ${error.message}`; });\n'
        "    });"
    )
    assert expected in html


def test_feedback_page_is_local_only_trace_linked_capture_without_frontend_semantics() -> None:
    html = _html(FEEDBACK)

    assert 'data-page-id="accurate-intake-feedback-page-v1"' in html
    assert 'data-surface-role="dogfood-feedback"' in html
    assert 'data-claim-scope="local_dogfood_feedback_triage_record"' in html
    assert 'data-feedback-owner="human_operator"' in html
    assert 'data-feedback-is-product-truth="false"' in html
    assert 'data-manager-context-injection="false"' in html
    assert 'data-fooddb-truth-update-allowed="false"' in html
    assert 'data-canonical-eval-promotion-allowed="false"' in html
    assert 'data-nav-target="chat"' in html
    assert 'data-nav-target="today"' in html
    assert 'data-nav-target="body"' in html
    assert 'data-nav-target="feedback"' in html
    assert 'feedback: "/accurate-intake/feedback"' in html
    assert 'chatHistory: "/accurate-intake/chat-history"' in html
    assert 'name="category"' in html
    assert 'value="manager_behavior"' in html
    assert 'value="nutrition_estimate"' in html
    assert 'value="macro_gap"' in html
    assert 'value="fooddb_gap"' in html
    assert 'value="ui_ux"' in html
    assert 'value="bug"' in html
    assert 'value="latency"' in html
    assert 'value="product_feedback"' in html
    assert '"X-Local-Debug-Token": token' in html
    assert "window.LOCAL_DEBUG_API_TOKEN" in html
    assert "trace_id: el(\"trace-id\").value.trim() || null" in html
    assert 'id="meal-id"' in html
    assert 'id="meal-title-context"' in html
    assert 'el("meal-id").value = params.get("meal_id") || "";' in html
    assert 'el("meal-title-context").textContent = params.get("meal_title") || "No meal selected";' in html
    assert 'meal_id: el("meal-id").value.trim() || null' in html
    assert 'function sourcePage()' in html
    assert 'page: sourcePage()' in html
    assert 'source_page: sourcePage()' in html
    assert 'feedback_route: window.location.pathname' in html
    assert "feedback_text: el(\"feedback-text\").value.trim()" in html

    forbidden = [
        "final_action",
        "workflow_effect",
        "estimated_kcal",
        "remaining_kcal",
        "message.content.includes",
        "message.content.match",
        "localStorage",
        "sessionStorage",
        "fooddb_truth_updated=true",
        "product_readiness_claimed=true",
        "private_self_use_approved=true",
    ]
    for fragment in forbidden:
        assert fragment not in html


def test_body_page_covers_plan_weight_goal_activity_inputs_without_frontend_tdee_math() -> None:
    html = _html(BODY)

    assert 'data-surface-role="body-plan"' in html
    assert 'class="page-actions"' not in html
    assert 'Open Today' not in html
    assert 'Open Chat' not in html
    assert 'Send Feedback' not in html
    assert 'Open Review' not in html
    assert 'id="body-session-user"' in html
    assert 'id="body-session-date"' in html
    assert 'id="body-plan-source"' in html
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
    assert "const historyQuery = new URLSearchParams({ user_id: userId(), local_date: selectedDate() });" in html
    assert "requestJson(`${endpoints.weightHistory}?${historyQuery.toString()}`)" in html
    assert "Set up your body plan to see targets." in html
    assert 'const isActive = plan.plan_status === "active";' in html
    assert "Mostly sitting, some walking" in html
    assert "Lose weight" in html
    assert 'placeholder="e.g. 34" required' in html
    assert 'placeholder="e.g. 170" required' in html
    assert 'placeholder="e.g. 70" required' in html
    assert 'placeholder="e.g. 0.5" required' in html
    assert 'placeholder="e.g. 1600"' in html
    assert "function updateSessionStrip()" in html
    assert 'el("body-session-user").textContent = userId();' in html
    assert 'el("body-session-date").textContent = selectedDate();' in html
    assert 'el("body-plan-source").textContent = "backend read model";' in html
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


def test_body_page_renders_budget_read_models_without_frontend_budget_math() -> None:
    html = _html(BODY)

    assert 'id="body-budget-loop"' in html
    assert 'id="body-active-target"' in html
    assert 'id="body-consumed-kcal"' in html
    assert 'id="body-remaining-kcal"' in html
    assert 'id="body-estimated-deficit"' in html
    assert 'id="body-effective-budget"' in html
    assert 'id="body-weekly-progress"' in html
    assert 'id="body-target-basis"' in html
    assert 'deficitSummary: "/today/deficit-summary"' in html
    assert 'effectiveBudget: "/today/effective-budget"' in html
    assert 'weeklyProgress: "/today/weekly-progress"' in html
    assert "function renderBudgetReadModels(deficit, effective, weekly)" in html
    assert "const readModelQuery = new URLSearchParams({ user_id: userId(), local_date: selectedDate() });" in html
    assert "requestJson(`${endpoints.deficitSummary}?${readModelQuery.toString()}`)" in html
    assert "requestJson(`${endpoints.effectiveBudget}?${readModelQuery.toString()}`)" in html
    assert "requestJson(`${endpoints.weeklyProgress}?${readModelQuery.toString()}`)" in html
    assert "Backend target" in html
    for fragment in (
        "estimatedDailyDeficit =",
        "runtimeEffectiveBudget =",
        "weeklyDeficit =",
        "target - consumed",
        "remaining =",
    ):
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
        assert chr(0xFFFD) not in html
        assert "?" + chr(0xF696) not in html
        assert chr(0x7625) + chr(0xE431) + chr(0x4E88) not in html


def test_product_pages_do_not_claim_fooddb_websearch_live_or_debug_truth() -> None:
    combined = "\n".join(_html(path) for path in (CHAT, TODAY, BODY)).lower()

    forbidden = [
        "fooddb_evidence_used=true",
        "real_fooddb_pass_claimed=true",
        "web_tavily_used=true",
        "live_llm_invoked=true",
        "web_readiness_claimed=true",
        "product_readiness_claimed=false",
        "private_self_use_approved=false",
        "debug surface",
        "last runtime payload",
        "last turn trace",
    ]
    for fragment in forbidden:
        assert fragment not in combined


def test_product_pages_do_not_use_browser_storage_or_operator_debug_routes() -> None:
    for path in (CHAT, TODAY, BODY):
        html = _html(path)
        lower = html.lower()

        assert "localStorage" not in html
        assert "sessionStorage" not in html
        assert "/accurate-intake/debug" not in html
        assert "last runtime payload" not in lower
        assert "last turn trace" not in lower
        assert "operator review" not in lower


def test_product_pages_do_not_own_semantic_or_mutation_decisions() -> None:
    combined = "\n".join(_html(path) for path in (CHAT, TODAY, BODY))

    forbidden = [
        "final_action",
        "workflow_effect",
        "mutation_legality",
        "deterministic_selected_target",
        "raw_text_intent_router",
        "message.content.includes",
        "message.content.match",
        "ready_for_fdb_integration=true",
        "product_readiness_claimed=true",
        "private_self_use_approved=true",
    ]
    for fragment in forbidden:
        assert fragment not in combined
