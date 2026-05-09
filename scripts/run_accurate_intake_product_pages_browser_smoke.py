from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.budget.interface.today_surface import resolve_today_local_date  # noqa: E402
from app.composition.current_shell_fooddb_triad_same_truth_contract import (  # noqa: E402
    EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES,
    FOODDB_TRIAD_SAME_TRUTH_REQUIRED_NON_CLAIMS,
)
from app.database import get_or_create_user  # noqa: E402
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV  # noqa: E402
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    _build_app,
    _free_port,
    _install_fetch_recorder,
    _load_sync_playwright,
    _restore_runtime,
    _run_uvicorn_in_thread,
    _seed_body_plan,
    _session_factory,
    _wait_for_http,
)
from scripts.run_accurate_intake_mvp_manager_style_smoke import (  # noqa: E402
    DeterministicSelfUseManagerProvider,
)
from app.nutrition.application.approved_packet_ready_fooddb_artifact import (  # noqa: E402
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_manager_packet_smoke import (  # noqa: E402
    build_fooddb_manager_packet_smoke,
)


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_browser_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_browser_smoke.json"
DEFAULT_USER_ID = "product-pages-browser-smoke-user"
DEFAULT_LOCAL_DATE = resolve_today_local_date(None)
DEFAULT_CJK_MESSAGE = "早餐吃茶葉蛋和拿鐵"
DEFAULT_MACRO_EXACT_ITEM_MESSAGE = "統一巧克力牛乳(400ml)"
DEFAULT_MACRO_MISSING_EXACT_ITEM_MESSAGE = "\u722d\u9bae\u7126\u7cd6\u9bae\u9b5a\u5169\u8cab"
EXPECTED_MACRO_EXACT_ITEM_VALUES = {
    "macro_state": "visible",
    "protein_text": "12",
    "carbs_text": "48",
    "fat_text": "6",
}
EXPECTED_MACRO_MISSING_EXACT_ITEM_VALUES = {
    "macro_state": "guarded",
    "macro_grid_hidden": True,
    "macro_guard_reason_hidden": False,
    "macro_guard_reason_text": "no_macro_data",
    "protein_text": "--",
    "carbs_text": "--",
    "fat_text": "--",
}
EXPECTED_MACRO_PRESENT_CURRENT_BUDGET = {
    "consumed_kcal": 300,
    "consumed_protein": 12,
    "consumed_carbs": 48,
    "consumed_fat": 6,
    "show_macro": True,
    "macro_guard_reason": "committed_and_aligned",
}
EXPECTED_MACRO_MISSING_CURRENT_BUDGET = {
    "consumed_kcal": 130,
    "consumed_protein": 0,
    "consumed_carbs": 0,
    "consumed_fat": 0,
    "show_macro": False,
    "macro_guard_reason": "no_macro_data",
}
ROUTE_BACKED_MACRO_NON_CLAIMS = {
    "live_llm_invoked": False,
    "web_tavily_used": False,
    "fooddb_truth_updated": False,
    "product_readiness_claimed": False,
    "private_self_use_approved": False,
}
FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS = {
    flag: False for flag in FOODDB_TRIAD_SAME_TRUTH_REQUIRED_NON_CLAIMS
}
REQUIRED_FETCH_METHODS = {
    "/accurate-intake/chat-history": "GET",
    "/estimate": "POST",
    "/today/current-budget": "GET",
    "/body-plan/active": "GET",
    "/weight/observations": "GET",
    "/weight/observation": "POST",
    "/onboarding/bootstrap": "POST",
    "/body-plan/manual-daily-target": "POST",
}
FORBIDDEN_VISIBLE_TERMS = ("trace", "debug", "last payload", "last turn trace", "status:")


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    local_date: str,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
        "claim_scope": "local_product_pages_browser_e2e_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "local_date": local_date,
        "previous_local_date": _previous_local_date(local_date),
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "chat_page_loaded": False,
        "chat_sent_cjk_message": False,
        "chat_assistant_bubble_rendered": False,
        "chat_history_reloaded": False,
        "chat_url_state_preserved_after_date_change": False,
        "chat_reload_preserved_selected_date": False,
        "chat_user_url_state_preserved_after_user_change": False,
        "chat_reload_preserved_user_id": False,
        "chat_enter_key_send_checked": False,
        "chat_shift_enter_multiline_checked": False,
        "chat_scrollable": False,
        "chat_scroll_behavior_checked": False,
        "chat_reload_scroll_behavior_checked": False,
        "chat_session_status_rendered": False,
        "chat_context_status_rendered": False,
        "chat_no_debug_trace": False,
        "today_page_loaded": False,
        "today_date_switch_checked": False,
        "today_previous_day_empty_checked": False,
        "today_current_day_restored_checked": False,
        "today_url_state_preserved_after_date_change": False,
        "today_reload_preserved_selected_date": False,
        "today_user_url_state_preserved_after_user_change": False,
        "today_reload_preserved_user_id": False,
        "today_summary_rendered": False,
        "today_meal_list_rendered": False,
        "macro_present_exact_item_browser_checked": False,
        "macro_present_exact_item_values": {},
        "macro_missing_exact_item_browser_checked": False,
        "macro_missing_exact_item_values": {},
        "route_backed_macro_browser_checked": False,
        "route_backed_macro_present_current_budget": {},
        "route_backed_macro_missing_current_budget": {},
        "route_backed_macro_non_claims": dict(ROUTE_BACKED_MACRO_NON_CLAIMS),
        "fooddb_triad_same_truth_browser_checked": False,
        "fooddb_triad_same_truth_cases": {},
        "fooddb_triad_same_truth_non_claims": dict(FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS),
        "today_session_status_rendered": False,
        "today_no_debug_trace": False,
        "body_page_loaded": False,
        "body_query_user_id_honored": False,
        "body_url_state_preserved_after_date_change": False,
        "body_reload_preserved_selected_date": False,
        "body_user_url_state_preserved_after_user_change": False,
        "body_reload_preserved_user_id": False,
        "body_active_plan_rendered": False,
        "body_plan_read_model_fields_rendered": False,
        "body_weight_checkin_saved": False,
        "body_latest_weight_rendered_from_backend": False,
        "body_weight_history_date_scoped_readback": False,
        "body_budget_read_models_rendered": False,
        "body_plan_form_saved": False,
        "body_manual_target_saved": False,
        "body_plan_readback_checked": False,
        "body_manual_target_read_model_rendered": False,
        "today_manual_target_readback_checked": False,
        "body_session_status_rendered": False,
        "body_no_debug_trace": False,
        "desktop_no_overflow": False,
        "mobile_no_overflow": False,
        "mobile_populated_state_checked": False,
        "mobile_no_debug_trace": False,
        "product_cjk_copy_rendered": False,
        "nav_session_query_preserved": False,
        "forbidden_storage_used": False,
        "fetch_sequence": [],
        "body_plan_read_model_values": {},
        "body_budget_read_model_values": {},
    }


def _previous_local_date(local_date: str) -> str:
    return (date.fromisoformat(local_date) - timedelta(days=1)).isoformat()


def _page_url(base_url: str, page_name: str, *, user_external_id: str, local_date: str) -> str:
    return (
        f"{base_url}/static/accurate-intake-{page_name}.html"
        f"?user_id={user_external_id}&local_date={local_date}"
    )


def _is_visible_product_text_clean(text: str) -> bool:
    lowered = text.lower()
    return not any(term in lowered for term in FORBIDDEN_VISIBLE_TERMS)


def _capture_fetches(page: Any) -> list[dict[str, Any]]:
    fetches = page.evaluate("window.__accurateIntakeFetches || []")
    return [item for item in fetches if isinstance(item, dict)]


def _storage_state(page: Any) -> dict[str, list[str]]:
    return page.evaluate(
        """() => ({
          localStorageKeys: Object.keys(window.localStorage || {}),
          sessionStorageKeys: Object.keys(window.sessionStorage || {})
        })"""
    )


def _overflow_state(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => ({
          viewport: window.innerWidth,
          documentScrollWidth: document.documentElement.scrollWidth,
          overflowingElements: Array.from(document.querySelectorAll("body *"))
            .map((node) => {
              const rect = node.getBoundingClientRect();
              const scrollParent = node.closest("#day-strip");
              return {
                tag: node.tagName,
                id: node.id || "",
                className: String(node.className || ""),
                right: Math.ceil(rect.right),
                insideHorizontalScroller: Boolean(scrollParent),
                text: (node.textContent || "").slice(0, 80)
              };
            })
            .filter((entry) => entry.right > window.innerWidth + 1 && !entry.insideHorizontalScroller)
            .slice(0, 12)
        })"""
    )


def _chat_scroll_state(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const node = document.querySelector("#chat-scroll");
          if (!node) {
            return { present: false, overflowY: "", scrollHeight: 0, clientHeight: 0, moved: false };
          }
          node.scrollTop = 0;
          const before = node.scrollTop;
          node.scrollTop = node.scrollHeight;
          const after = node.scrollTop;
          return {
            present: true,
            overflowY: getComputedStyle(node).overflowY,
            scrollHeight: node.scrollHeight,
            clientHeight: node.clientHeight,
            moved: after > before
          };
        }"""
    )


def _nav_session_query_preserved(page: Any, *, user_external_id: str, local_date: str) -> bool:
    return bool(
        page.evaluate(
            """({ userExternalId, localDate }) => {
              const links = Array.from(document.querySelectorAll("[data-nav-target]"));
              if (links.length < 3) {
                return false;
              }
              return links.every((link) => {
                const url = new URL(link.href, window.location.href);
                return url.searchParams.get("user_id") === userExternalId
                  && url.searchParams.get("local_date") === localDate
                  && !url.searchParams.has("local_debug_token");
              });
            }""",
            {"userExternalId": user_external_id, "localDate": local_date},
        )
    )


def _open_page(
    browser: Any,
    *,
    viewport: dict[str, int],
    url: str,
    timeout_ms: int,
    local_debug_token: str,
) -> Any:
    page = browser.new_page(viewport=viewport)
    _install_fetch_recorder(page)
    page.add_init_script(f"window.LOCAL_DEBUG_API_TOKEN = {json.dumps(local_debug_token)};")
    page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    return page


def _macro_panel_values(page: Any, *, timeout_ms: int) -> dict[str, str]:
    page.wait_for_function(
        """() => document.querySelector("#macro-panel")?.dataset?.macroState === "visible" """,
        timeout=timeout_ms,
    )
    return {
        "macro_state": page.locator("#macro-panel").evaluate("(node) => node.dataset.macroState"),
        "protein_text": page.locator("#protein-g").inner_text(timeout=timeout_ms).strip(),
        "carbs_text": page.locator("#carbs-g").inner_text(timeout=timeout_ms).strip(),
        "fat_text": page.locator("#fat-g").inner_text(timeout=timeout_ms).strip(),
    }


def _macro_guarded_panel_values(page: Any, *, timeout_ms: int) -> dict[str, Any]:
    page.wait_for_function(
        """() => {
          const panel = document.querySelector("#macro-panel");
          const reason = document.querySelector("#macro-guard-reason")?.textContent?.trim();
          const protein = document.querySelector("#protein-g")?.textContent?.trim();
          const carbs = document.querySelector("#carbs-g")?.textContent?.trim();
          const fat = document.querySelector("#fat-g")?.textContent?.trim();
          return panel?.dataset?.macroState === "guarded"
            && reason === "no_macro_data"
            && protein === "--"
            && carbs === "--"
            && fat === "--";
        }""",
        timeout=timeout_ms,
    )
    return {
        "macro_state": page.locator("#macro-panel").evaluate("(node) => node.dataset.macroState"),
        "macro_grid_hidden": page.locator("#macro-grid").evaluate("(node) => node.hidden"),
        "macro_guard_reason_hidden": page.locator("#macro-guard-reason").evaluate("(node) => node.hidden"),
        "macro_guard_reason_text": page.locator("#macro-guard-reason").inner_text(timeout=timeout_ms).strip(),
        "protein_text": page.locator("#protein-g").inner_text(timeout=timeout_ms).strip(),
        "carbs_text": page.locator("#carbs-g").inner_text(timeout=timeout_ms).strip(),
        "fat_text": page.locator("#fat-g").inner_text(timeout=timeout_ms).strip(),
    }


def _current_budget_payload(page: Any, *, user_external_id: str, local_date: str) -> dict[str, Any]:
    payload = page.evaluate(
        """async ({ userExternalId, localDate }) => {
          const params = new URLSearchParams({ user_id: userExternalId, local_date: localDate });
          const response = await fetch(`/today/current-budget?${params.toString()}`);
          return await response.json();
        }""",
        {"userExternalId": user_external_id, "localDate": local_date},
    )
    return payload if isinstance(payload, dict) else {}


def _current_budget_macro_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "consumed_kcal": payload.get("consumed_kcal"),
        "consumed_protein": payload.get("consumed_protein"),
        "consumed_carbs": payload.get("consumed_carbs"),
        "consumed_fat": payload.get("consumed_fat"),
        "show_macro": payload.get("show_macro"),
        "macro_guard_reason": payload.get("macro_guard_reason"),
    }


def _run_macro_present_exact_item_sequence(
    browser: Any,
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    timeout_ms: int,
    local_debug_token: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    macro_user_id = f"{user_external_id}-macro-exact"
    result: dict[str, Any] = {
        "macro_present_exact_item_browser_checked": False,
        "macro_present_exact_item_values": {},
        "route_backed_macro_present_current_budget": {},
        "fetch_sequence": [],
        "page_text": "",
    }
    chat = _open_page(
        browser,
        viewport=viewport,
        url=_page_url(base_url, "chat", user_external_id=macro_user_id, local_date=local_date),
        timeout_ms=timeout_ms,
        local_debug_token=local_debug_token,
    )
    chat.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
    chat.fill("#message-input", DEFAULT_MACRO_EXACT_ITEM_MESSAGE)
    chat.press("#message-input", "Enter")
    chat.wait_for_function(
        """(message) => {
          const text = document.querySelector("#chat-scroll")?.textContent || "";
          return text.includes(`Logged. ${message}`);
        }""",
        arg=DEFAULT_MACRO_EXACT_ITEM_MESSAGE,
        timeout=timeout_ms,
    )
    result["fetch_sequence"].extend(_capture_fetches(chat))
    chat.close()

    today = _open_page(
        browser,
        viewport=viewport,
        url=_page_url(base_url, "today", user_external_id=macro_user_id, local_date=local_date),
        timeout_ms=timeout_ms,
        local_debug_token=local_debug_token,
    )
    today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
    today.wait_for_function(
        """(message) => (document.querySelector("#meal-list")?.textContent || "").includes(message) """,
        arg=DEFAULT_MACRO_EXACT_ITEM_MESSAGE,
        timeout=timeout_ms,
    )
    result["macro_present_exact_item_values"] = _macro_panel_values(today, timeout_ms=timeout_ms)
    result["route_backed_macro_present_current_budget"] = _current_budget_macro_fields(
        _current_budget_payload(today, user_external_id=macro_user_id, local_date=local_date)
    )
    result["macro_present_exact_item_browser_checked"] = (
        result["macro_present_exact_item_values"] == EXPECTED_MACRO_EXACT_ITEM_VALUES
        and result["route_backed_macro_present_current_budget"]
        == EXPECTED_MACRO_PRESENT_CURRENT_BUDGET
    )
    result["page_text"] = today.locator("body").inner_text(timeout=timeout_ms)
    result["fetch_sequence"].extend(_capture_fetches(today))
    today.close()
    return result


def _run_macro_missing_exact_item_sequence(
    browser: Any,
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    timeout_ms: int,
    local_debug_token: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    macro_user_id = f"{user_external_id}-macro-missing"
    result: dict[str, Any] = {
        "macro_missing_exact_item_browser_checked": False,
        "macro_missing_exact_item_values": {},
        "route_backed_macro_missing_current_budget": {},
        "fetch_sequence": [],
        "page_text": "",
    }
    chat = _open_page(
        browser,
        viewport=viewport,
        url=_page_url(base_url, "chat", user_external_id=macro_user_id, local_date=local_date),
        timeout_ms=timeout_ms,
        local_debug_token=local_debug_token,
    )
    chat.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
    chat.fill("#message-input", DEFAULT_MACRO_MISSING_EXACT_ITEM_MESSAGE)
    chat.press("#message-input", "Enter")
    chat.wait_for_function(
        """() => {
          const text = document.querySelector("#chat-scroll")?.textContent || "";
          return text.includes("Logged.");
        }""",
        timeout=timeout_ms,
    )
    result["fetch_sequence"].extend(_capture_fetches(chat))
    chat.close()

    today = _open_page(
        browser,
        viewport=viewport,
        url=_page_url(base_url, "today", user_external_id=macro_user_id, local_date=local_date),
        timeout_ms=timeout_ms,
        local_debug_token=local_debug_token,
    )
    today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
    today.wait_for_function(
        """() => (document.querySelector("#meal-list")?.textContent || "").includes("kcal") """,
        timeout=timeout_ms,
    )
    result["macro_missing_exact_item_values"] = _macro_guarded_panel_values(today, timeout_ms=timeout_ms)
    result["route_backed_macro_missing_current_budget"] = _current_budget_macro_fields(
        _current_budget_payload(today, user_external_id=macro_user_id, local_date=local_date)
    )
    result["macro_missing_exact_item_browser_checked"] = (
        result["macro_missing_exact_item_values"] == EXPECTED_MACRO_MISSING_EXACT_ITEM_VALUES
        and result["route_backed_macro_missing_current_budget"]
        == EXPECTED_MACRO_MISSING_CURRENT_BUDGET
    )
    result["page_text"] = today.locator("body").inner_text(timeout=timeout_ms)
    result["fetch_sequence"].extend(_capture_fetches(today))
    today.close()
    return result


def _approved_packet_ready_manager_cases() -> list[dict[str, Any]]:
    approved_artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json"
    )
    manager_packet_smoke = build_fooddb_manager_packet_smoke(
        retrieval_records=tuple(),
        approved_packet_ready_artifact=approved_artifact,
    )
    return [
        case
        for case in manager_packet_smoke.get("approved_packet_ready_cases") or []
        if isinstance(case, dict)
    ]


def _renderer_payload_from_manager_case(case: dict[str, Any]) -> dict[str, Any]:
    basis = dict(case.get("final_response_basis") or {})
    kcal_basis = dict(basis.get("kcal_basis") or {})
    macro_basis = dict(basis.get("macro_basis") or {})
    allowed_macro_claims = dict(macro_basis.get("allowed_macro_claims") or {})
    macro_visibility = str(macro_basis.get("macro_visibility_status") or "")
    show_macro = macro_visibility == "visible"
    return {
        "consumed_kcal": kcal_basis.get("kcal_point"),
        "kcal_range": kcal_basis.get("kcal_range") or [],
        "consumed_protein": allowed_macro_claims.get("protein_g"),
        "consumed_carbs": allowed_macro_claims.get("carbs_g"),
        "consumed_fat": allowed_macro_claims.get("fat_g"),
        "show_macro": show_macro,
        "macro_guard_reason": "" if show_macro else macro_visibility,
    }


def _fooddb_triad_dom_values(page: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return page.evaluate(
        """(payload) => {
          renderMacroPanel(payload);
          const byId = (id) => document.getElementById(id);
          return {
            macro_state: byId("macro-panel")?.dataset?.macroState || "",
            macro_grid_hidden: byId("macro-grid")?.hidden === true,
            macro_guard_reason_hidden: byId("macro-guard-reason")?.hidden === true,
            macro_guard_reason_text: (byId("macro-guard-reason")?.textContent || "").trim(),
            protein_text: (byId("protein-g")?.textContent || "").trim(),
            carbs_text: (byId("carbs-g")?.textContent || "").trim(),
            fat_text: (byId("fat-g")?.textContent || "").trim(),
          };
        }""",
        payload,
    )


def _fooddb_triad_case_result(page: Any, case: dict[str, Any]) -> dict[str, Any]:
    source_lane = str(case.get("source_lane") or "")
    basis = dict(case.get("final_response_basis") or {})
    kcal_basis = dict(basis.get("kcal_basis") or {})
    macro_basis = dict(basis.get("macro_basis") or {})
    payload = _renderer_payload_from_manager_case(case)
    dom_values = _fooddb_triad_dom_values(page, payload)
    return {
        "source_lane": source_lane,
        "item_id": str(case.get("item_id") or ""),
        "kcal_point": kcal_basis.get("kcal_point"),
        "kcal_range": kcal_basis.get("kcal_range") or [],
        "macro_visibility_status": macro_basis.get("macro_visibility_status"),
        "macro_state": dom_values.get("macro_state"),
        "protein_text": dom_values.get("protein_text"),
        "carbs_text": dom_values.get("carbs_text"),
        "fat_text": dom_values.get("fat_text"),
        "macro_guard_reason_text": dom_values.get("macro_guard_reason_text"),
        "packet_is_not_mutation_authority": basis.get("packet_is_not_mutation_authority") is True,
    }


def _run_fooddb_triad_same_truth_sequence(
    browser: Any,
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    timeout_ms: int,
    local_debug_token: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    triad_user_id = f"{user_external_id}-fooddb-triad"
    result: dict[str, Any] = {
        "fooddb_triad_same_truth_browser_checked": False,
        "fooddb_triad_same_truth_cases": {},
        "fooddb_triad_same_truth_non_claims": dict(FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS),
        "fetch_sequence": [],
        "page_text": "",
    }
    today = _open_page(
        browser,
        viewport=viewport,
        url=_page_url(base_url, "today", user_external_id=triad_user_id, local_date=local_date),
        timeout_ms=timeout_ms,
        local_debug_token=local_debug_token,
    )
    today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
    cases = {
        str(case.get("source_lane") or ""): _fooddb_triad_case_result(today, case)
        for case in _approved_packet_ready_manager_cases()
    }
    result["fooddb_triad_same_truth_cases"] = cases
    result["fooddb_triad_same_truth_browser_checked"] = (
        cases == EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES
    )
    result["page_text"] = today.locator("body").inner_text(timeout=timeout_ms)
    result["fetch_sequence"].extend(_capture_fetches(today))
    today.close()
    return result


def _run_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    cjk_message: str,
    timeout_ms: int,
    headless: bool,
    local_debug_token: str,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    previous_local_date = _previous_local_date(local_date)
    result: dict[str, Any] = {
        "current_step": "not_started",
        "fetch_sequence": [],
        "desktop_overflow": {},
        "mobile_overflow": {},
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
        "product_page_text": "",
        "macro_present_exact_item_browser_checked": False,
        "macro_present_exact_item_values": {},
        "macro_missing_exact_item_browser_checked": False,
        "macro_missing_exact_item_values": {},
        "fooddb_triad_same_truth_browser_checked": False,
        "fooddb_triad_same_truth_cases": {},
        "fooddb_triad_same_truth_non_claims": dict(FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS),
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            desktop_viewport = {"width": 1440, "height": 1100}
            mobile_viewport = {"width": 390, "height": 844}
            desktop_overflows: list[dict[str, Any]] = []
            mobile_overflows: list[dict[str, Any]] = []
            nav_checks: list[bool] = []
            storage_keys = {"localStorageKeys": [], "sessionStorageKeys": []}
            page_texts: list[str] = []

            result["current_step"] = "open_chat"
            chat = _open_page(
                browser,
                viewport=desktop_viewport,
                url=_page_url(base_url, "chat", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            chat.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
            nav_checks.append(
                _nav_session_query_preserved(chat, user_external_id=user_external_id, local_date=local_date)
            )
            result["chat_page_loaded"] = True
            result["chat_session_status_rendered"] = (
                chat.locator("#chat-session-user").inner_text(timeout=timeout_ms).strip() == user_external_id
                and chat.locator("#chat-session-date").inner_text(timeout=timeout_ms).strip() == local_date
            )
            result["current_step"] = "submit_chat_message"
            enter_message = f"{cjk_message} keyboard enter"
            multiline_first_line = f"{cjk_message} shift enter"
            multiline_second_line = "second line"
            multiline_message = f"{multiline_first_line}\n{multiline_second_line}"
            chat_messages = [enter_message, multiline_message] + [f"{cjk_message} extra {i}" for i in range(3, 11)]

            chat.fill("#message-input", enter_message)
            chat.press("#message-input", "Enter")
            chat.wait_for_function(
                """(message) => {
                  const text = document.querySelector("#chat-scroll")?.textContent || "";
                  return text.includes(`Logged. ${message}`);
                }""",
                arg=enter_message,
                timeout=timeout_ms,
            )
            result["chat_enter_key_send_checked"] = True

            chat.fill("#message-input", multiline_first_line)
            chat.press("#message-input", "Shift+Enter")
            textarea_value = chat.locator("#message-input").input_value(timeout=timeout_ms)
            result["chat_shift_enter_multiline_checked"] = "\n" in textarea_value
            chat.type("#message-input", multiline_second_line)
            chat.click("#send-button")
            chat.wait_for_function(
                """({ firstLine, secondLine }) => {
                  const text = document.querySelector("#chat-scroll")?.textContent || "";
                  return text.includes(firstLine) && text.includes(secondLine) && text.includes("Logged.");
                }""",
                arg={"firstLine": multiline_first_line, "secondLine": multiline_second_line},
                timeout=timeout_ms,
            )

            for message in chat_messages[2:]:
                chat.fill("#message-input", message)
                chat.click("#send-button")
                chat.wait_for_function(
                    """(message) => {
                      const text = document.querySelector("#chat-scroll")?.textContent || "";
                      return text.includes(`Logged. ${message}`);
                    }""",
                    arg=message,
                    timeout=timeout_ms,
                )
            chat_text = chat.locator("body").inner_text(timeout=timeout_ms)
            result["chat_sent_cjk_message"] = cjk_message in chat_text
            result["chat_assistant_bubble_rendered"] = "Logged." in chat_text
            chat_scroll_state = _chat_scroll_state(chat)
            result["chat_scroll_state"] = chat_scroll_state
            result["chat_scrollable"] = chat_scroll_state.get("overflowY") == "auto"
            result["chat_scroll_behavior_checked"] = (
                chat_scroll_state.get("scrollHeight", 0) > chat_scroll_state.get("clientHeight", 0)
                and chat_scroll_state.get("moved") is True
            )
            result["chat_no_debug_trace"] = _is_visible_product_text_clean(chat_text)
            result["fetch_sequence"].extend(_capture_fetches(chat))
            desktop_overflows.append(_overflow_state(chat))
            storage_keys["localStorageKeys"].extend(_storage_state(chat).get("localStorageKeys", []))
            storage_keys["sessionStorageKeys"].extend(_storage_state(chat).get("sessionStorageKeys", []))
            page_texts.append(chat_text)
            result["current_step"] = "reload_chat_history"
            chat.reload(wait_until="networkidle", timeout=timeout_ms)
            chat.wait_for_function(
                """(message) => (document.querySelector("#chat-scroll")?.textContent || "").includes(message)""",
                arg=chat_messages[-1],
                timeout=timeout_ms,
            )
            reload_chat_text = chat.locator("#chat-scroll").inner_text(timeout=timeout_ms)
            result["chat_history_reloaded"] = cjk_message in reload_chat_text and chat_messages[-1] in reload_chat_text
            context_policy = chat.locator("#chat-context-policy").inner_text(timeout=timeout_ms).strip()
            context_loaded = chat.locator("#chat-context-loaded").inner_text(timeout=timeout_ms).strip()
            context_omitted = chat.locator("#chat-context-omitted").inner_text(timeout=timeout_ms).strip()
            context_pins = chat.locator("#chat-context-pins").inner_text(timeout=timeout_ms).strip()
            context_targets = chat.locator("#chat-context-targets").inner_text(timeout=timeout_ms).strip()
            result["chat_context_status"] = {
                "policy": context_policy,
                "loaded": context_loaded,
                "omitted": context_omitted,
                "pins": context_pins,
                "targets": context_targets,
            }
            result["chat_context_status_rendered"] = (
                context_policy not in {"", "not_checked"}
                and context_loaded in {"present", "not_available"}
                and context_omitted in {"present", "not_available"}
                and context_pins in {"present", "not_available"}
                and context_targets not in {"", "not_checked"}
            )
            reload_scroll_state = _chat_scroll_state(chat)
            result["chat_reload_scroll_state"] = reload_scroll_state
            result["chat_reload_scroll_behavior_checked"] = (
                reload_scroll_state.get("scrollHeight", 0) > reload_scroll_state.get("clientHeight", 0)
                and reload_scroll_state.get("moved") is True
            )
            chat.evaluate(
                """(dateValue) => {
                  const input = document.querySelector("#local-date");
                  input.value = dateValue;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=previous_local_date,
            )
            chat.wait_for_function(
                """(dateValue) => new URL(window.location.href).searchParams.get("local_date") === dateValue """,
                arg=previous_local_date,
                timeout=timeout_ms,
            )
            result["chat_url_state_preserved_after_date_change"] = True
            chat.reload(wait_until="networkidle", timeout=timeout_ms)
            chat.wait_for_function(
                """(dateValue) => document.querySelector("#local-date")?.value === dateValue """,
                arg=previous_local_date,
                timeout=timeout_ms,
            )
            result["chat_reload_preserved_selected_date"] = True
            chat.evaluate(
                """(dateValue) => {
                  const input = document.querySelector("#local-date");
                  input.value = dateValue;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=local_date,
            )
            chat.wait_for_function(
                """(dateValue) => new URL(window.location.href).searchParams.get("local_date") === dateValue """,
                arg=local_date,
                timeout=timeout_ms,
            )
            chat.wait_for_function(
                """(message) => (document.querySelector("#chat-scroll")?.textContent || "").includes(message)""",
                arg=chat_messages[-1],
                timeout=timeout_ms,
            )
            alternate_user_id = f"{user_external_id}-alt"
            chat.evaluate(
                """(userId) => {
                  const input = document.querySelector("#user-id");
                  input.value = userId;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=alternate_user_id,
            )
            chat.wait_for_function(
                """(userId) => new URL(window.location.href).searchParams.get("user_id") === userId """,
                arg=alternate_user_id,
                timeout=timeout_ms,
            )
            result["chat_user_url_state_preserved_after_user_change"] = True
            chat.reload(wait_until="networkidle", timeout=timeout_ms)
            chat.wait_for_function(
                """(userId) => document.querySelector("#user-id")?.value === userId """,
                arg=alternate_user_id,
                timeout=timeout_ms,
            )
            result["chat_reload_preserved_user_id"] = True
            chat.evaluate(
                """(userId) => {
                  const input = document.querySelector("#user-id");
                  input.value = userId;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=user_external_id,
            )
            chat.wait_for_function(
                """(userId) => new URL(window.location.href).searchParams.get("user_id") === userId """,
                arg=user_external_id,
                timeout=timeout_ms,
            )
            chat.wait_for_function(
                """(message) => (document.querySelector("#chat-scroll")?.textContent || "").includes(message)""",
                arg=chat_messages[-1],
                timeout=timeout_ms,
            )
            result["fetch_sequence"].extend(_capture_fetches(chat))
            chat.close()

            result["current_step"] = "macro_present_exact_item_browser_check"
            macro_result = _run_macro_present_exact_item_sequence(
                browser,
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
                viewport=desktop_viewport,
            )
            result["macro_present_exact_item_browser_checked"] = macro_result[
                "macro_present_exact_item_browser_checked"
            ]
            result["macro_present_exact_item_values"] = macro_result["macro_present_exact_item_values"]
            result["route_backed_macro_present_current_budget"] = macro_result[
                "route_backed_macro_present_current_budget"
            ]
            result["fetch_sequence"].extend(macro_result["fetch_sequence"])
            page_texts.append(str(macro_result.get("page_text") or ""))

            result["current_step"] = "macro_missing_exact_item_browser_check"
            macro_missing_result = _run_macro_missing_exact_item_sequence(
                browser,
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
                viewport=desktop_viewport,
            )
            result["macro_missing_exact_item_browser_checked"] = macro_missing_result[
                "macro_missing_exact_item_browser_checked"
            ]
            result["macro_missing_exact_item_values"] = macro_missing_result["macro_missing_exact_item_values"]
            result["route_backed_macro_missing_current_budget"] = macro_missing_result[
                "route_backed_macro_missing_current_budget"
            ]
            result["route_backed_macro_non_claims"] = dict(ROUTE_BACKED_MACRO_NON_CLAIMS)
            result["route_backed_macro_browser_checked"] = (
                result["macro_present_exact_item_browser_checked"] is True
                and result["macro_missing_exact_item_browser_checked"] is True
                and result["route_backed_macro_present_current_budget"]
                == EXPECTED_MACRO_PRESENT_CURRENT_BUDGET
                and result["route_backed_macro_missing_current_budget"]
                == EXPECTED_MACRO_MISSING_CURRENT_BUDGET
            )
            result["fetch_sequence"].extend(macro_missing_result["fetch_sequence"])
            page_texts.append(str(macro_missing_result.get("page_text") or ""))

            result["current_step"] = "fooddb_triad_same_truth_browser_check"
            triad_result = _run_fooddb_triad_same_truth_sequence(
                browser,
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
                viewport=desktop_viewport,
            )
            result["fooddb_triad_same_truth_browser_checked"] = triad_result[
                "fooddb_triad_same_truth_browser_checked"
            ]
            result["fooddb_triad_same_truth_cases"] = triad_result[
                "fooddb_triad_same_truth_cases"
            ]
            result["fooddb_triad_same_truth_non_claims"] = triad_result[
                "fooddb_triad_same_truth_non_claims"
            ]
            result["fetch_sequence"].extend(triad_result["fetch_sequence"])
            page_texts.append(str(triad_result.get("page_text") or ""))

            result["current_step"] = "open_today"
            today = _open_page(
                browser,
                viewport=desktop_viewport,
                url=_page_url(base_url, "today", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            today.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
            nav_checks.append(
                _nav_session_query_preserved(today, user_external_id=user_external_id, local_date=local_date)
            )
            today.wait_for_function(
                """() => document.querySelector("#budget-kcal")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
            today_text = today.locator("body").inner_text(timeout=timeout_ms)
            result["today_page_loaded"] = True
            result["today_session_status_rendered"] = (
                today.locator("#today-session-user").inner_text(timeout=timeout_ms).strip() == user_external_id
                and today.locator("#today-session-date").inner_text(timeout=timeout_ms).strip() == local_date
                and today.locator("#today-chat-state").inner_text(timeout=timeout_ms).strip() == "same user/date"
            )
            result["today_summary_rendered"] = all(
                today.locator(selector).inner_text(timeout=timeout_ms).strip() != "--"
                for selector in ("#budget-kcal", "#consumed-kcal", "#remaining-kcal")
            )
            result["today_meal_list_rendered"] = cjk_message in today_text and "kcal" in today_text
            result["today_no_debug_trace"] = _is_visible_product_text_clean(today_text)
            result["current_step"] = "switch_today_date"
            today.evaluate(
                """(dateValue) => {
                  const input = document.querySelector("#selected-date");
                  input.value = dateValue;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=previous_local_date,
            )
            today.wait_for_function(
                """(dateValue) => document.querySelector("#selected-date")?.value === dateValue """,
                arg=previous_local_date,
                timeout=timeout_ms,
            )
            today.wait_for_function(
                """() => (document.querySelector("#meal-list")?.textContent || "").includes("No meals logged") """,
                timeout=timeout_ms,
            )
            result["today_previous_day_empty_checked"] = cjk_message not in today.locator("#meal-list").inner_text(
                timeout=timeout_ms
            )
            result["today_url_state_preserved_after_date_change"] = (
                today.evaluate("""() => new URL(window.location.href).searchParams.get("local_date")""")
                == previous_local_date
            )
            result["fetch_sequence"].extend(_capture_fetches(today))
            today.reload(wait_until="networkidle", timeout=timeout_ms)
            today.wait_for_function(
                """(dateValue) => document.querySelector("#selected-date")?.value === dateValue """,
                arg=previous_local_date,
                timeout=timeout_ms,
            )
            today.wait_for_function(
                """() => (document.querySelector("#meal-list")?.textContent || "").includes("No meals logged") """,
                timeout=timeout_ms,
            )
            result["today_reload_preserved_selected_date"] = cjk_message not in today.locator("#meal-list").inner_text(
                timeout=timeout_ms
            )
            today.evaluate(
                """(dateValue) => {
                  const input = document.querySelector("#selected-date");
                  input.value = dateValue;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=local_date,
            )
            today.wait_for_function(
                """(dateValue) => document.querySelector("#selected-date")?.value === dateValue """,
                arg=local_date,
                timeout=timeout_ms,
            )
            today.wait_for_function(
                """(message) => (document.querySelector("#meal-list")?.textContent || "").includes(message) """,
                arg=cjk_message,
                timeout=timeout_ms,
            )
            result["today_current_day_restored_checked"] = cjk_message in today.locator("#meal-list").inner_text(
                timeout=timeout_ms
            )
            result["today_date_switch_checked"] = True
            result["fetch_sequence"].extend(_capture_fetches(today))
            alternate_today_user_id = f"{user_external_id}-today-alt"
            today.fill("#user-id", alternate_today_user_id)
            today.dispatch_event("#user-id", "change")
            today.wait_for_function(
                """(userId) => new URL(window.location.href).searchParams.get("user_id") === userId """,
                arg=alternate_today_user_id,
                timeout=timeout_ms,
            )
            result["today_user_url_state_preserved_after_user_change"] = True
            today.reload(wait_until="networkidle", timeout=timeout_ms)
            today.wait_for_function(
                """(userId) => document.querySelector("#user-id")?.value === userId """,
                arg=alternate_today_user_id,
                timeout=timeout_ms,
            )
            result["today_reload_preserved_user_id"] = True
            today.fill("#user-id", user_external_id)
            today.dispatch_event("#user-id", "change")
            today.wait_for_function(
                """(userId) => new URL(window.location.href).searchParams.get("user_id") === userId """,
                arg=user_external_id,
                timeout=timeout_ms,
            )
            today.wait_for_function(
                """(message) => (document.querySelector("#meal-list")?.textContent || "").includes(message) """,
                arg=cjk_message,
                timeout=timeout_ms,
            )
            nav_checks.append(
                _nav_session_query_preserved(today, user_external_id=user_external_id, local_date=local_date)
            )
            result["fetch_sequence"].extend(_capture_fetches(today))
            desktop_overflows.append(_overflow_state(today))
            storage_keys["localStorageKeys"].extend(_storage_state(today).get("localStorageKeys", []))
            storage_keys["sessionStorageKeys"].extend(_storage_state(today).get("sessionStorageKeys", []))
            page_texts.append(today_text)
            today.close()

            result["current_step"] = "open_body"
            body = _open_page(
                browser,
                viewport=desktop_viewport,
                url=_page_url(base_url, "body", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            body.wait_for_selector('[data-surface-role="body-plan"]', timeout=timeout_ms)
            nav_checks.append(
                _nav_session_query_preserved(body, user_external_id=user_external_id, local_date=local_date)
            )
            body.wait_for_function(
                """() => document.querySelector("#plan-daily-target")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
            result["body_page_loaded"] = True
            result["body_query_user_id_honored"] = body.locator("#user-id").input_value(timeout=timeout_ms) == user_external_id
            result["body_session_status_rendered"] = (
                body.locator("#body-session-user").inner_text(timeout=timeout_ms).strip() == user_external_id
                and body.locator("#body-session-date").inner_text(timeout=timeout_ms).strip() == local_date
                and body.locator("#body-plan-source").inner_text(timeout=timeout_ms).strip() == "backend read model"
            )
            result["body_active_plan_rendered"] = all(
                body.locator(selector).inner_text(timeout=timeout_ms).strip() != "--"
                for selector in ("#plan-daily-target", "#plan-tdee", "#plan-current-weight")
            )
            body.evaluate(
                """(dateValue) => {
                  const input = document.querySelector("#local-date");
                  input.value = dateValue;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=previous_local_date,
            )
            body.wait_for_function(
                """(dateValue) => new URL(window.location.href).searchParams.get("local_date") === dateValue """,
                arg=previous_local_date,
                timeout=timeout_ms,
            )
            result["body_url_state_preserved_after_date_change"] = True
            body.reload(wait_until="networkidle", timeout=timeout_ms)
            body.wait_for_function(
                """(dateValue) => document.querySelector("#local-date")?.value === dateValue """,
                arg=previous_local_date,
                timeout=timeout_ms,
            )
            result["body_reload_preserved_selected_date"] = True
            body.evaluate(
                """(dateValue) => {
                  const input = document.querySelector("#local-date");
                  input.value = dateValue;
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                arg=local_date,
            )
            body.wait_for_function(
                """(dateValue) => new URL(window.location.href).searchParams.get("local_date") === dateValue """,
                arg=local_date,
                timeout=timeout_ms,
            )
            alternate_user_id = f"{user_external_id}-alt"
            body.fill("#user-id", alternate_user_id)
            body.dispatch_event("#user-id", "change")
            body.wait_for_function(
                """(userId) => new URL(window.location.href).searchParams.get("user_id") === userId """,
                arg=alternate_user_id,
                timeout=timeout_ms,
            )
            result["body_user_url_state_preserved_after_user_change"] = True
            body.reload(wait_until="networkidle", timeout=timeout_ms)
            body.wait_for_function(
                """(userId) => document.querySelector("#user-id")?.value === userId """,
                arg=alternate_user_id,
                timeout=timeout_ms,
            )
            result["body_reload_preserved_user_id"] = True
            body.fill("#user-id", user_external_id)
            body.dispatch_event("#user-id", "change")
            body.wait_for_function(
                """(userId) => new URL(window.location.href).searchParams.get("user_id") === userId """,
                arg=user_external_id,
                timeout=timeout_ms,
            )
            body.wait_for_function(
                """() => document.querySelector("#plan-daily-target")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
            result["current_step"] = "save_weight"
            body.fill("#weight-kg", "70.4")
            body.click('button:has-text("Save weight")')
            body.wait_for_function(
                """() => (document.querySelector("#weight-history")?.textContent || "").includes("70.4") """,
                timeout=timeout_ms,
            )
            result["body_weight_checkin_saved"] = True
            result["current_step"] = "save_body_plan"
            body.select_option("#sex", "female")
            body.fill("#age-years", "34")
            body.fill("#height-cm", "170")
            body.fill("#current-weight-kg", "70")
            body.fill("#target-weight-kg", "65")
            body.select_option("#goal-type", "lose_weight")
            body.select_option("#daily-lifestyle", "sedentary_with_some_walking")
            body.select_option("#weekly-exercise-days-band", "0")
            body.fill("#weekly-target-rate-kg", "0.5")
            body.click('button:has-text("Rebuild plan")')
            body.wait_for_function(
                """() => (document.querySelector("#body-status")?.textContent || "").includes("Plan saved") """,
                timeout=timeout_ms,
            )
            result["body_plan_form_saved"] = True
            result["current_step"] = "save_manual_target"
            body.fill("#manual-daily-target", "1550")
            body.click("#save-manual-target")
            body.wait_for_function(
                """() => (document.querySelector("#body-status")?.textContent || "").includes("1550") """,
                timeout=timeout_ms,
            )
            result["body_manual_target_saved"] = True
            result["fetch_sequence"].extend(_capture_fetches(body))
            body.reload(wait_until="networkidle", timeout=timeout_ms)
            body.wait_for_function(
                """() => document.querySelector("#plan-daily-target")?.textContent?.trim() === "1550 kcal" """,
                timeout=timeout_ms,
            )
            body.wait_for_function(
                """() => document.querySelector("#body-active-target")?.textContent?.trim() === "1550 kcal" """,
                timeout=timeout_ms,
            )
            body.wait_for_function(
                """(expected) => (document.querySelector("#weight-history")?.textContent || "").includes(expected) """,
                arg=f"{local_date} | 70.4 kg",
                timeout=timeout_ms,
            )
            result["body_plan_readback_checked"] = True
            body_plan_values = {
                "daily_target": body.locator("#plan-daily-target").inner_text(timeout=timeout_ms).strip(),
                "tdee": body.locator("#plan-tdee").inner_text(timeout=timeout_ms).strip(),
                "current_weight": body.locator("#plan-current-weight").inner_text(timeout=timeout_ms).strip(),
                "target_weight": body.locator("#plan-target-weight").inner_text(timeout=timeout_ms).strip(),
                "activity": body.locator("#plan-activity").inner_text(timeout=timeout_ms).strip(),
                "goal": body.locator("#plan-goal").inner_text(timeout=timeout_ms).strip(),
                "weight_history": body.locator("#weight-history").inner_text(timeout=timeout_ms).strip(),
            }
            body_budget_values = {
                "active_target": body.locator("#body-active-target").inner_text(timeout=timeout_ms).strip(),
                "consumed": body.locator("#body-consumed-kcal").inner_text(timeout=timeout_ms).strip(),
                "remaining": body.locator("#body-remaining-kcal").inner_text(timeout=timeout_ms).strip(),
                "estimated_deficit": body.locator("#body-estimated-deficit").inner_text(timeout=timeout_ms).strip(),
                "effective_budget": body.locator("#body-effective-budget").inner_text(timeout=timeout_ms).strip(),
                "weekly_progress": body.locator("#body-weekly-progress").inner_text(timeout=timeout_ms).strip(),
            }
            result["body_plan_read_model_values"] = body_plan_values
            result["body_budget_read_model_values"] = body_budget_values
            result["body_plan_read_model_fields_rendered"] = (
                body_plan_values["daily_target"] == "1550 kcal"
                and body_plan_values["tdee"] == "1819 kcal"
                and body_plan_values["current_weight"] == "70 kg"
                and body_plan_values["target_weight"] == "65 kg"
                and body_plan_values["activity"] == "light"
                and body_plan_values["goal"] == "Lose weight"
            )
            result["body_budget_read_models_rendered"] = (
                body_budget_values["active_target"] == "1550 kcal"
                and body_budget_values["consumed"] == "400 kcal"
                and body_budget_values["remaining"] == "1150 kcal"
                and body_budget_values["estimated_deficit"] == "269 kcal"
                and body_budget_values["effective_budget"] == "1550 kcal"
                and "400 kcal consumed" in body_budget_values["weekly_progress"]
            )
            result["body_latest_weight_rendered_from_backend"] = f"{local_date} | 70.4 kg" in body_plan_values[
                "weight_history"
            ]
            body_fetch_urls = [
                str(item.get("url") or "")
                for item in _capture_fetches(body)
                if isinstance(item, dict)
            ]
            result["body_weight_history_date_scoped_readback"] = any(
                "/weight/observations" in url and f"local_date={local_date}" in url
                for url in body_fetch_urls
            )
            result["body_manual_target_read_model_rendered"] = True
            body_text_after = body.locator("body").inner_text(timeout=timeout_ms)
            result["body_no_debug_trace"] = _is_visible_product_text_clean(body_text_after)
            result["fetch_sequence"].extend(_capture_fetches(body))
            desktop_overflows.append(_overflow_state(body))
            storage_keys["localStorageKeys"].extend(_storage_state(body).get("localStorageKeys", []))
            storage_keys["sessionStorageKeys"].extend(_storage_state(body).get("sessionStorageKeys", []))
            page_texts.append(body_text_after)
            body.close()

            result["current_step"] = "mobile_overflow_check"
            for page_name in ("chat", "today", "body"):
                mobile = _open_page(
                    browser,
                    viewport=mobile_viewport,
                    url=_page_url(base_url, page_name, user_external_id=user_external_id, local_date=local_date),
                    timeout_ms=timeout_ms,
                    local_debug_token=local_debug_token,
                )
                if page_name == "chat":
                    mobile.wait_for_function(
                        """(message) => (document.querySelector("#chat-scroll")?.textContent || "").includes(message)""",
                        arg=cjk_message,
                        timeout=timeout_ms,
                    )
                if page_name == "today":
                    mobile.wait_for_function(
                        """() => document.querySelector("#budget-kcal")?.textContent?.trim() === "1550" """,
                        timeout=timeout_ms,
                    )
                    result["today_manual_target_readback_checked"] = True
                if page_name == "body":
                    mobile.wait_for_function(
                        """() => document.querySelector("#plan-daily-target")?.textContent?.trim() === "1550 kcal" """,
                        timeout=timeout_ms,
                    )
                mobile_text = mobile.locator("body").inner_text(timeout=timeout_ms)
                result.setdefault("mobile_page_text", "")
                result["mobile_page_text"] += "\n" + mobile_text
                mobile_overflows.append(_overflow_state(mobile))
                result["fetch_sequence"].extend(_capture_fetches(mobile))
                mobile.close()

            result["desktop_overflow"] = desktop_overflows
            result["mobile_overflow"] = mobile_overflows
            result["desktop_no_overflow"] = all(
                state.get("documentScrollWidth") == state.get("viewport")
                and not state.get("overflowingElements")
                for state in desktop_overflows
            )
            result["mobile_no_overflow"] = all(
                state.get("documentScrollWidth") == state.get("viewport")
                and not state.get("overflowingElements")
                for state in mobile_overflows
            )
            result["mobile_populated_state_checked"] = result.get("today_manual_target_readback_checked") is True
            result["mobile_no_debug_trace"] = _is_visible_product_text_clean(str(result.get("mobile_page_text") or ""))
            result["storage"] = storage_keys
            result["forbidden_storage_used"] = bool(storage_keys["localStorageKeys"] or storage_keys["sessionStorageKeys"])
            result["product_page_text"] = "\n".join(page_texts)
            result["nav_session_query_preserved"] = bool(nav_checks) and all(nav_checks)
            result["product_cjk_copy_rendered"] = all(
                fragment in result["product_page_text"]
                for fragment in ("像 LINE", "每天一頁", "先把體重")
            )
            result["current_step"] = "complete"
            return result
        except Exception as exc:
            result["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            return result
        finally:
            browser.close()


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []

    def require_true(key: str, blocker: str) -> None:
        if report.get(key) is not True:
            blockers.append(blocker)

    require_true("browser_executed", "browser_not_executed")
    require_true("chat_page_loaded", "chat_page_not_loaded")
    require_true("chat_sent_cjk_message", "chat_cjk_message_not_sent")
    require_true("chat_assistant_bubble_rendered", "chat_assistant_bubble_not_rendered")
    require_true("chat_history_reloaded", "chat_history_not_reloaded")
    require_true("chat_url_state_preserved_after_date_change", "chat_url_state_not_preserved_after_date_change")
    require_true("chat_reload_preserved_selected_date", "chat_reload_did_not_preserve_selected_date")
    require_true(
        "chat_user_url_state_preserved_after_user_change",
        "chat_user_url_state_not_preserved_after_user_change",
    )
    require_true("chat_reload_preserved_user_id", "chat_reload_did_not_preserve_user_id")
    require_true("chat_enter_key_send_checked", "chat_enter_key_send_not_checked")
    require_true("chat_shift_enter_multiline_checked", "chat_shift_enter_multiline_not_checked")
    require_true("chat_scrollable", "chat_not_scrollable")
    require_true("chat_scroll_behavior_checked", "chat_scroll_behavior_not_checked")
    require_true("chat_reload_scroll_behavior_checked", "chat_reload_scroll_behavior_not_checked")
    require_true("chat_session_status_rendered", "chat_session_status_not_rendered")
    require_true("chat_context_status_rendered", "chat_context_status_not_rendered")
    require_true("chat_no_debug_trace", "chat_debug_trace_leaked")
    require_true("today_page_loaded", "today_page_not_loaded")
    require_true("today_date_switch_checked", "today_date_switch_not_checked")
    require_true("today_previous_day_empty_checked", "today_previous_day_empty_not_checked")
    require_true("today_current_day_restored_checked", "today_current_day_restored_not_checked")
    require_true(
        "today_url_state_preserved_after_date_change",
        "today_url_state_not_preserved_after_date_change",
    )
    require_true("today_reload_preserved_selected_date", "today_reload_did_not_preserve_selected_date")
    require_true(
        "today_user_url_state_preserved_after_user_change",
        "today_user_url_state_not_preserved_after_user_change",
    )
    require_true("today_reload_preserved_user_id", "today_reload_did_not_preserve_user_id")
    require_true("today_summary_rendered", "today_summary_not_rendered")
    require_true("today_meal_list_rendered", "today_meal_list_not_rendered")
    require_true(
        "macro_present_exact_item_browser_checked",
        "macro_present_exact_item_browser_not_checked",
    )
    require_true(
        "macro_missing_exact_item_browser_checked",
        "macro_missing_exact_item_browser_not_checked",
    )
    require_true(
        "route_backed_macro_browser_checked",
        "route_backed_macro_browser_not_checked",
    )
    require_true("today_session_status_rendered", "today_session_status_not_rendered")
    require_true("today_no_debug_trace", "today_debug_trace_leaked")
    require_true("body_page_loaded", "body_page_not_loaded")
    require_true("body_query_user_id_honored", "body_query_user_id_not_honored")
    require_true("body_url_state_preserved_after_date_change", "body_url_state_not_preserved_after_date_change")
    require_true("body_reload_preserved_selected_date", "body_reload_did_not_preserve_selected_date")
    require_true(
        "body_user_url_state_preserved_after_user_change",
        "body_user_url_state_not_preserved_after_user_change",
    )
    require_true("body_reload_preserved_user_id", "body_reload_did_not_preserve_user_id")
    require_true("body_active_plan_rendered", "body_active_plan_not_rendered")
    require_true("body_plan_read_model_fields_rendered", "body_plan_read_model_fields_not_rendered")
    require_true("body_weight_checkin_saved", "body_weight_checkin_not_saved")
    require_true(
        "body_latest_weight_rendered_from_backend",
        "body_latest_weight_not_rendered_from_backend",
    )
    require_true(
        "body_weight_history_date_scoped_readback",
        "body_weight_history_date_scoped_readback_missing",
    )
    require_true(
        "body_budget_read_models_rendered",
        "body_budget_read_models_not_rendered",
    )
    require_true("body_plan_form_saved", "body_plan_form_not_saved")
    require_true("body_manual_target_saved", "body_manual_target_not_saved")
    require_true("body_plan_readback_checked", "body_plan_readback_not_checked")
    require_true("body_manual_target_read_model_rendered", "body_manual_target_read_model_not_rendered")
    require_true("today_manual_target_readback_checked", "today_manual_target_readback_not_checked")
    require_true("fooddb_triad_same_truth_browser_checked", "fooddb_triad_same_truth_browser_not_checked")
    require_true("body_session_status_rendered", "body_session_status_not_rendered")
    require_true("body_no_debug_trace", "body_debug_trace_leaked")
    require_true("desktop_no_overflow", "desktop_overflow_detected")
    require_true("mobile_no_overflow", "mobile_overflow_detected")
    require_true("mobile_populated_state_checked", "mobile_populated_state_not_checked")
    require_true("mobile_no_debug_trace", "mobile_debug_trace_leaked")
    require_true("product_cjk_copy_rendered", "product_cjk_copy_not_rendered")
    require_true("nav_session_query_preserved", "nav_session_query_not_preserved")

    if report.get("forbidden_storage_used") is True:
        blockers.append("forbidden_storage_used")

    browser = dict(report.get("browser") or {})
    body_values = dict(report.get("body_plan_read_model_values") or browser.get("body_plan_read_model_values") or {})
    local_date = str(report.get("local_date") or DEFAULT_LOCAL_DATE)
    if not body_values:
        blockers.append("body_read_model_values_missing")
    expected_body_values = {
        "daily_target": "1550 kcal",
        "tdee": "1819 kcal",
        "current_weight": "70 kg",
        "target_weight": "65 kg",
        "activity": "light",
        "goal": "Lose weight",
    }
    for field, expected_value in expected_body_values.items():
        if body_values and body_values.get(field) != expected_value:
            blockers.append(f"body_read_model_value_mismatch:{field}")
    if body_values:
        if f"{local_date} | 70.4 kg" not in str(body_values.get("weight_history") or ""):
            blockers.append("body_read_model_value_mismatch:weight_history")
    body_budget_values = dict(report.get("body_budget_read_model_values") or browser.get("body_budget_read_model_values") or {})
    if not body_budget_values:
        blockers.append("body_budget_read_model_values_missing")
    expected_body_budget_values = {
        "active_target": "1550 kcal",
        "consumed": "400 kcal",
        "remaining": "1150 kcal",
        "estimated_deficit": "269 kcal",
        "effective_budget": "1550 kcal",
    }
    for field, expected_value in expected_body_budget_values.items():
        if body_budget_values and body_budget_values.get(field) != expected_value:
            blockers.append(f"body_budget_read_model_value_mismatch:{field}")
    if body_budget_values and "400 kcal consumed" not in str(body_budget_values.get("weekly_progress") or ""):
        blockers.append("body_budget_read_model_value_mismatch:weekly_progress")
    macro_values = dict(report.get("macro_present_exact_item_values") or {})
    for field, expected_value in EXPECTED_MACRO_EXACT_ITEM_VALUES.items():
        if macro_values.get(field) != expected_value:
            blockers.append(f"macro_present_exact_item_value_mismatch:{field}")
    macro_missing_values = dict(report.get("macro_missing_exact_item_values") or {})
    for field, expected_value in EXPECTED_MACRO_MISSING_EXACT_ITEM_VALUES.items():
        if macro_missing_values.get(field) != expected_value:
            blockers.append(f"macro_missing_exact_item_value_mismatch:{field}")
    route_macro_present = dict(report.get("route_backed_macro_present_current_budget") or {})
    for field, expected_value in EXPECTED_MACRO_PRESENT_CURRENT_BUDGET.items():
        if route_macro_present.get(field) != expected_value:
            blockers.append(f"route_backed_macro_present_current_budget_mismatch:{field}")
    route_macro_missing = dict(report.get("route_backed_macro_missing_current_budget") or {})
    for field, expected_value in EXPECTED_MACRO_MISSING_CURRENT_BUDGET.items():
        if route_macro_missing.get(field) != expected_value:
            blockers.append(f"route_backed_macro_missing_current_budget_mismatch:{field}")
    route_macro_non_claims = dict(report.get("route_backed_macro_non_claims") or {})
    for field, expected_value in ROUTE_BACKED_MACRO_NON_CLAIMS.items():
        if route_macro_non_claims.get(field) != expected_value:
            blockers.append(f"route_backed_macro_non_claim_overclaim:{field}")
    triad_cases = dict(report.get("fooddb_triad_same_truth_cases") or {})
    for lane, expected_case in EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES.items():
        actual_case = dict(triad_cases.get(lane) or {})
        if not actual_case:
            blockers.append(f"fooddb_triad_same_truth_case_missing:{lane}")
            continue
        for field, expected_value in expected_case.items():
            if actual_case.get(field) != expected_value:
                blockers.append(f"fooddb_triad_same_truth_case_mismatch:{lane}:{field}")
    triad_non_claims = dict(report.get("fooddb_triad_same_truth_non_claims") or {})
    for field, expected_value in FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS.items():
        if triad_non_claims.get(field) != expected_value:
            blockers.append(f"fooddb_triad_same_truth_non_claim_overclaim:{field}")
    fetches = list(report.get("fetch_sequence") or browser.get("fetch_sequence") or [])
    for expected, method in REQUIRED_FETCH_METHODS.items():
        if not any(
            expected in str(item.get("url") or "") and str(item.get("method") or "GET").upper() == method
            for item in fetches
            if isinstance(item, dict)
        ):
            blockers.append(f"fetch_missing:{method} {expected}")
    fetch_urls = [str(item.get("url") or "") for item in fetches if isinstance(item, dict)]
    previous_local_date = str(report.get("previous_local_date") or _previous_local_date(local_date))
    if not any("/today/current-budget" in url and f"local_date={previous_local_date}" in url for url in fetch_urls):
        blockers.append("today_previous_day_fetch_missing")
    if not any("/today/current-budget" in url and f"local_date={local_date}" in url for url in fetch_urls):
        blockers.append("today_current_day_fetch_missing")
    if not any("/weight/observations" in url and f"local_date={local_date}" in url for url in fetch_urls):
        blockers.append("body_weight_history_date_fetch_missing")
    if any("/weight/observations" in url and "local_date=" not in url for url in fetch_urls):
        blockers.append("body_weight_history_unscoped_fetch_detected")
    for endpoint in ("/today/deficit-summary", "/today/effective-budget", "/today/weekly-progress"):
        if not any(endpoint in url and f"local_date={local_date}" in url for url in fetch_urls):
            blockers.append(f"body_budget_read_model_fetch_missing:{endpoint}")
    estimate_posts = [
        str(item.get("body") or "")
        for item in fetches
        if isinstance(item, dict)
        and "/estimate" in str(item.get("url") or "")
        and str(item.get("method") or "GET").upper() == "POST"
    ]
    if not estimate_posts:
        blockers.append("estimate_post_missing")
    for body in estimate_posts:
        compact = body.replace(" ", "")
        if '"allow_search":false' not in compact or '"allow_search":true' in compact:
            blockers.append("estimate_allow_search_not_false")
            break
    required_post_fragments = {
        "/weight/observation": ('"user_id"', '"local_date"'),
        "/onboarding/bootstrap": ('"user_id"', '"local_date"'),
        "/body-plan/manual-daily-target": ('"user_id"', '"local_date"', '"source":"user_ui"'),
    }
    for endpoint, fragments in required_post_fragments.items():
        bodies = [
            str(item.get("body") or "").replace(" ", "")
            for item in fetches
            if isinstance(item, dict)
            and endpoint in str(item.get("url") or "")
            and str(item.get("method") or "GET").upper() == "POST"
        ]
        if not bodies:
            continue
        if not any(all(fragment in body for fragment in fragments) for body in bodies):
            blockers.append(f"post_body_missing_required_context:{endpoint}")

    storage = dict(browser.get("storage") or {})
    if not storage:
        storage = {"localStorageKeys": [], "sessionStorageKeys": []}
    if storage.get("localStorageKeys") or storage.get("sessionStorageKeys"):
        blockers.append("forbidden_storage_used")

    text = str(browser.get("product_page_text") or report.get("product_page_text") or "")
    if text and not _is_visible_product_text_clean(text):
        blockers.append("product_page_debug_trace_text")

    sequence_error = str(report.get("browser_sequence_error") or "")
    if sequence_error:
        blockers.append(f"browser_sequence_error:{sequence_error.split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_product_pages_browser_smoke_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = DEFAULT_USER_ID,
    local_date: str = DEFAULT_LOCAL_DATE,
    cjk_message: str = DEFAULT_CJK_MESSAGE,
    reset_db: bool = True,
    require_browser_execution: bool = False,
    timeout_ms: int = 15000,
    headless: bool = True,
) -> dict[str, Any]:
    report = _base_report(
        user_external_id=user_external_id,
        db_path=db_path,
        local_date=local_date,
        browser_execution_required=require_browser_execution,
    )
    try:
        _load_sync_playwright()
    except BrowserSmokeDependencyMissing:
        report["status"] = "blocked" if not require_browser_execution else "fail"
        report["blockers"] = ["playwright_not_installed"]
        report["operator_action"] = "Install Playwright locally and rerun; this artifact must not claim web readiness."
        return report

    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    provider = DeterministicSelfUseManagerProvider()
    db = SessionLocal()
    app = _build_app(db, provider)
    port = _free_port()
    previous_debug_token = os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV)
    local_debug_token = secrets.token_urlsafe(24)
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = local_debug_token
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-chat.html")
        get_or_create_user(db, user_external_id)
        _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
        try:
            browser_result = _run_browser_sequence(
                base_url=base_url,
                user_external_id=user_external_id,
                local_date=local_date,
                cjk_message=cjk_message,
                timeout_ms=timeout_ms,
                headless=headless,
                local_debug_token=local_debug_token,
            )
        except Exception as exc:
            report["browser_sequence_error"] = f"{type(exc).__name__}: {exc}"
            report["manager_provider_call_count"] = len(provider.calls)
            report["status"] = "fail"
            report["blockers"] = [f"browser_sequence_error:{type(exc).__name__}"]
            return report

        report["browser_executed"] = True
        report["browser"] = browser_result
        for key, value in browser_result.items():
            if key in report:
                report[key] = value
        report["fetch_sequence"] = browser_result.get("fetch_sequence", [])
        report["manager_provider_call_count"] = len(provider.calls)
        status, blockers = _validate(report)
        report["status"] = status
        report["blockers"] = blockers
        return report
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        _restore_runtime(app)
        if previous_debug_token is None:
            os.environ.pop(LOCAL_DEBUG_API_TOKEN_ENV, None)
        else:
            os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = previous_debug_token
        db.close()
        engine.dispose()
        time.sleep(0.1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run browser smoke for the separate Accurate Intake product pages.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--cjk-message", default=DEFAULT_CJK_MESSAGE)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_product_pages_browser_smoke_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        local_date=args.local_date,
        cjk_message=args.cjk_message,
        reset_db=not args.keep_db,
        require_browser_execution=args.require_browser_execution,
        timeout_ms=args.timeout_ms,
        headless=not args.headed,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report["status"] == "pass":
        return 0
    if report["status"] == "blocked" and not args.require_browser_execution:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
