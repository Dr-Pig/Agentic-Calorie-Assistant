from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_browser_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_browser_smoke.json"
DEFAULT_USER_ID = "product-pages-browser-smoke-user"
DEFAULT_LOCAL_DATE = "2026-05-04"
DEFAULT_CJK_MESSAGE = "早餐吃茶葉蛋和拿鐵"
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
    "private_self_use_approved",
]
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
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
        "claim_scope": "local_product_pages_browser_e2e_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "chat_page_loaded": False,
        "chat_sent_cjk_message": False,
        "chat_assistant_bubble_rendered": False,
        "chat_history_reloaded": False,
        "chat_enter_key_send_checked": False,
        "chat_shift_enter_multiline_checked": False,
        "chat_scrollable": False,
        "chat_scroll_behavior_checked": False,
        "chat_reload_scroll_behavior_checked": False,
        "chat_no_debug_trace": False,
        "today_page_loaded": False,
        "today_date_switch_checked": False,
        "today_previous_day_empty_checked": False,
        "today_current_day_restored_checked": False,
        "today_summary_rendered": False,
        "today_meal_list_rendered": False,
        "today_no_debug_trace": False,
        "body_page_loaded": False,
        "body_query_user_id_honored": False,
        "body_active_plan_rendered": False,
        "body_weight_checkin_saved": False,
        "body_plan_form_saved": False,
        "body_manual_target_saved": False,
        "body_plan_readback_checked": False,
        "today_manual_target_readback_checked": False,
        "body_no_debug_trace": False,
        "desktop_no_overflow": False,
        "mobile_no_overflow": False,
        "mobile_populated_state_checked": False,
        "mobile_no_debug_trace": False,
        "product_cjk_copy_rendered": False,
        "nav_session_query_preserved": False,
        "forbidden_storage_used": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "fetch_sequence": [],
    }


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
    result: dict[str, Any] = {
        "current_step": "not_started",
        "fetch_sequence": [],
        "desktop_overflow": {},
        "mobile_overflow": {},
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
        "product_page_text": "",
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
            reload_scroll_state = _chat_scroll_state(chat)
            result["chat_reload_scroll_state"] = reload_scroll_state
            result["chat_reload_scroll_behavior_checked"] = (
                reload_scroll_state.get("scrollHeight", 0) > reload_scroll_state.get("clientHeight", 0)
                and reload_scroll_state.get("moved") is True
            )
            result["fetch_sequence"].extend(_capture_fetches(chat))
            chat.close()

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
            result["today_summary_rendered"] = all(
                today.locator(selector).inner_text(timeout=timeout_ms).strip() != "--"
                for selector in ("#budget-kcal", "#consumed-kcal", "#remaining-kcal")
            )
            result["today_meal_list_rendered"] = cjk_message in today_text and "kcal" in today_text
            result["today_no_debug_trace"] = _is_visible_product_text_clean(today_text)
            result["current_step"] = "switch_today_date"
            today.evaluate(
                """() => {
                  const input = document.querySelector("#selected-date");
                  input.value = "2026-05-03";
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }"""
            )
            today.wait_for_function(
                """() => document.querySelector("#selected-date")?.value === "2026-05-03" """,
                timeout=timeout_ms,
            )
            today.wait_for_function(
                """() => (document.querySelector("#meal-list")?.textContent || "").includes("No meals logged") """,
                timeout=timeout_ms,
            )
            result["today_previous_day_empty_checked"] = cjk_message not in today.locator("#meal-list").inner_text(
                timeout=timeout_ms
            )
            today.evaluate(
                """() => {
                  const input = document.querySelector("#selected-date");
                  input.value = "2026-05-04";
                  input.dispatchEvent(new Event("change", { bubbles: true }));
                }"""
            )
            today.wait_for_function(
                """() => document.querySelector("#selected-date")?.value === "2026-05-04" """,
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
            body_text = body.locator("body").inner_text(timeout=timeout_ms)
            result["body_page_loaded"] = True
            result["body_query_user_id_honored"] = body.locator("#user-id").input_value(timeout=timeout_ms) == user_external_id
            result["body_active_plan_rendered"] = all(
                body.locator(selector).inner_text(timeout=timeout_ms).strip() != "--"
                for selector in ("#plan-daily-target", "#plan-tdee", "#plan-current-weight")
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
            body.fill("#target-weight-kg", "65")
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
            result["body_plan_readback_checked"] = True
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
    require_true("chat_enter_key_send_checked", "chat_enter_key_send_not_checked")
    require_true("chat_shift_enter_multiline_checked", "chat_shift_enter_multiline_not_checked")
    require_true("chat_scrollable", "chat_not_scrollable")
    require_true("chat_scroll_behavior_checked", "chat_scroll_behavior_not_checked")
    require_true("chat_reload_scroll_behavior_checked", "chat_reload_scroll_behavior_not_checked")
    require_true("chat_no_debug_trace", "chat_debug_trace_leaked")
    require_true("today_page_loaded", "today_page_not_loaded")
    require_true("today_date_switch_checked", "today_date_switch_not_checked")
    require_true("today_previous_day_empty_checked", "today_previous_day_empty_not_checked")
    require_true("today_current_day_restored_checked", "today_current_day_restored_not_checked")
    require_true("today_summary_rendered", "today_summary_not_rendered")
    require_true("today_meal_list_rendered", "today_meal_list_not_rendered")
    require_true("today_no_debug_trace", "today_debug_trace_leaked")
    require_true("body_page_loaded", "body_page_not_loaded")
    require_true("body_query_user_id_honored", "body_query_user_id_not_honored")
    require_true("body_active_plan_rendered", "body_active_plan_not_rendered")
    require_true("body_weight_checkin_saved", "body_weight_checkin_not_saved")
    require_true("body_plan_form_saved", "body_plan_form_not_saved")
    require_true("body_manual_target_saved", "body_manual_target_not_saved")
    require_true("body_plan_readback_checked", "body_plan_readback_not_checked")
    require_true("today_manual_target_readback_checked", "today_manual_target_readback_not_checked")
    require_true("body_no_debug_trace", "body_debug_trace_leaked")
    require_true("desktop_no_overflow", "desktop_overflow_detected")
    require_true("mobile_no_overflow", "mobile_overflow_detected")
    require_true("mobile_populated_state_checked", "mobile_populated_state_not_checked")
    require_true("mobile_no_debug_trace", "mobile_debug_trace_leaked")
    require_true("product_cjk_copy_rendered", "product_cjk_copy_not_rendered")
    require_true("nav_session_query_preserved", "nav_session_query_not_preserved")

    if report.get("frontend_semantic_owner") is True:
        blockers.append("frontend_semantic_owner")
    for key in (
        "live_llm_invoked",
        "web_tavily_used",
        "production_db_used",
        "web_readiness_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
        "forbidden_storage_used",
    ):
        if report.get(key) is True:
            blockers.append(key)

    browser = dict(report.get("browser") or {})
    fetches = list(report.get("fetch_sequence") or browser.get("fetch_sequence") or [])
    for expected, method in REQUIRED_FETCH_METHODS.items():
        if not any(
            expected in str(item.get("url") or "") and str(item.get("method") or "GET").upper() == method
            for item in fetches
            if isinstance(item, dict)
        ):
            blockers.append(f"fetch_missing:{method} {expected}")
    fetch_urls = [str(item.get("url") or "") for item in fetches if isinstance(item, dict)]
    if not any("/today/current-budget" in url and "local_date=2026-05-03" in url for url in fetch_urls):
        blockers.append("today_previous_day_fetch_missing")
    if not any("/today/current-budget" in url and "local_date=2026-05-04" in url for url in fetch_urls):
        blockers.append("today_current_day_fetch_missing")
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
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "pass":
        return 0
    if report["status"] == "blocked" and not args.require_browser_execution:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
