from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.budget.interface.today_surface import resolve_today_local_date  # noqa: E402
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
from scripts.run_accurate_intake_product_pages_browser_smoke import (  # noqa: E402
    _capture_fetches,
    _is_visible_product_text_clean,
    _nav_session_query_preserved,
    _page_url,
    _storage_state,
)


DEFAULT_DB_PATH = (
    ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_long_session_navigation.sqlite3"
)
DEFAULT_OUTPUT_PATH = (
    ROOT / "artifacts" / "accurate_intake_product_pages_long_session_navigation_smoke.json"
)
DEFAULT_USER_ID = "product-pages-long-session-user"
DEFAULT_LOCAL_DATE = resolve_today_local_date(None)
DEFAULT_MESSAGE_COUNT = 32
DEFAULT_CJK_STEM = "\u9577\u5c0d\u8a71\u6e2c\u8a66\u8c46\u5e72"

NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
    "private_self_use_approved",
]

REQUIRED_FETCH_ENDPOINTS = (
    "/estimate",
    "/accurate-intake/chat-history",
    "/today/current-budget",
    "/body-plan/active",
)


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    local_date: str,
    message_count: int,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_product_pages_long_session_navigation_smoke",
        "smoke_id": "accurate_intake_product_pages_long_session_navigation_smoke_v1",
        "claim_scope": "local_product_pages_long_session_navigation_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "local_date": local_date,
        "message_count_requested": message_count,
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "long_session_message_count": 0,
        "first_cjk_message_rendered": False,
        "middle_cjk_message_rendered": False,
        "last_cjk_message_rendered": False,
        "chat_scroll_overflow_checked": False,
        "chat_scroll_bottom_checked": False,
        "reload_preserved_long_history": False,
        "click_chat_to_today_preserved_session": False,
        "click_today_to_body_preserved_session": False,
        "click_body_to_chat_preserved_session": False,
        "chat_return_preserved_latest_message": False,
        "navigation_fetch_sequence_checked": False,
        "forbidden_storage_used": False,
        "visible_debug_trace_leaked": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "fetch_sequence": [],
    }


def _open_page(browser: Any, *, viewport: dict[str, int], url: str, timeout_ms: int, token: str) -> Any:
    page = browser.new_page(viewport=viewport)
    _install_fetch_recorder(page)
    page.add_init_script(f"window.LOCAL_DEBUG_API_TOKEN = {json.dumps(token)};")
    page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    return page


def _message_metrics(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const scroller = document.querySelector("#chat-scroll");
          const userTexts = Array.from(document.querySelectorAll(".message.user .bubble"))
            .map((node) => node.textContent || "");
          if (!scroller) {
            return { present: false, userTexts, overflowY: "", scrollHeight: 0, clientHeight: 0, moved: false };
          }
          scroller.scrollTop = 0;
          const before = scroller.scrollTop;
          scroller.scrollTop = scroller.scrollHeight;
          const after = scroller.scrollTop;
          return {
            present: true,
            userTexts,
            overflowY: getComputedStyle(scroller).overflowY,
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            moved: after > before
          };
        }"""
    )


def _session_matches(page: Any, *, user_external_id: str, local_date: str, user_selector: str, date_selector: str) -> bool:
    return (
        page.locator(user_selector).inner_text(timeout=5000).strip() == user_external_id
        and page.locator(date_selector).inner_text(timeout=5000).strip() == local_date
        and _nav_session_query_preserved(page, user_external_id=user_external_id, local_date=local_date)
    )


def _fetches_include_required_endpoints(fetch_sequence: list[Any]) -> bool:
    fetches = [item for item in fetch_sequence if isinstance(item, dict)]
    return all(
        any(endpoint in str(item.get("url") or "") for item in fetches)
        for endpoint in REQUIRED_FETCH_ENDPOINTS
    )


def _run_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    message_count: int,
    timeout_ms: int,
    headless: bool,
    local_debug_token: str,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    viewport = {"width": 1440, "height": 1100}
    messages = [f"{DEFAULT_CJK_STEM}-{index:02d}" for index in range(1, message_count + 1)]
    result: dict[str, Any] = {"fetch_sequence": [], "current_step": "not_started"}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = _open_page(
                browser,
                viewport=viewport,
                url=_page_url(base_url, "chat", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                token=local_debug_token,
            )
            page.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
            for message in messages:
                result["current_step"] = f"send_{message}"
                page.fill("#message-input", message)
                page.click("#send-button")
                page.wait_for_function(
                    """(message) => {
                      const text = document.querySelector("#chat-scroll")?.textContent || "";
                      return text.includes(message) && text.includes(`Logged. ${message}`);
                    }""",
                    arg=message,
                    timeout=timeout_ms,
                )
            metrics = _message_metrics(page)
            user_texts = [str(text) for text in metrics.get("userTexts", [])]
            result["long_session_message_count"] = len(user_texts)
            result["first_cjk_message_rendered"] = messages[0] in user_texts
            result["middle_cjk_message_rendered"] = messages[len(messages) // 2] in user_texts
            result["last_cjk_message_rendered"] = messages[-1] in user_texts
            result["chat_scroll_overflow_checked"] = (
                metrics.get("overflowY") == "auto"
                and metrics.get("scrollHeight", 0) > metrics.get("clientHeight", 0)
            )
            result["chat_scroll_bottom_checked"] = metrics.get("moved") is True
            result["fetch_sequence"].extend(_capture_fetches(page))
            storage = _storage_state(page)
            result["forbidden_storage_used"] = bool(storage.get("localStorageKeys") or storage.get("sessionStorageKeys"))

            result["current_step"] = "reload_chat"
            page.reload(wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_function(
                """(message) => (document.querySelector("#chat-scroll")?.textContent || "").includes(message)""",
                arg=messages[-1],
                timeout=timeout_ms,
            )
            reload_metrics = _message_metrics(page)
            reload_user_texts = [str(text) for text in reload_metrics.get("userTexts", [])]
            result["reload_preserved_long_history"] = (
                len(reload_user_texts) >= message_count
                and messages[0] in reload_user_texts
                and messages[-1] in reload_user_texts
            )
            result["fetch_sequence"].extend(_capture_fetches(page))

            result["current_step"] = "click_today"
            page.click('[data-nav-target="today"]')
            page.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
            page.wait_for_function(
                """() => document.querySelector("#today-session-user")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
            result["click_chat_to_today_preserved_session"] = _session_matches(
                page,
                user_external_id=user_external_id,
                local_date=local_date,
                user_selector="#today-session-user",
                date_selector="#today-session-date",
            )
            result["fetch_sequence"].extend(_capture_fetches(page))

            result["current_step"] = "click_body"
            page.click('[data-nav-target="body"]')
            page.wait_for_selector('[data-surface-role="body-plan"]', timeout=timeout_ms)
            page.wait_for_function(
                """() => document.querySelector("#body-session-user")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
            result["click_today_to_body_preserved_session"] = _session_matches(
                page,
                user_external_id=user_external_id,
                local_date=local_date,
                user_selector="#body-session-user",
                date_selector="#body-session-date",
            )
            result["fetch_sequence"].extend(_capture_fetches(page))

            result["current_step"] = "click_chat_return"
            page.click('[data-nav-target="chat"]')
            page.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
            page.wait_for_function(
                """(message) => (document.querySelector("#chat-scroll")?.textContent || "").includes(message)""",
                arg=messages[-1],
                timeout=timeout_ms,
            )
            result["click_body_to_chat_preserved_session"] = (
                page.locator("#chat-session-user").inner_text(timeout=timeout_ms).strip() == user_external_id
                and page.locator("#chat-session-date").inner_text(timeout=timeout_ms).strip() == local_date
            )
            return_metrics = _message_metrics(page)
            return_texts = [str(text) for text in return_metrics.get("userTexts", [])]
            result["chat_return_preserved_latest_message"] = messages[-1] in return_texts
            product_text = page.locator("body").inner_text(timeout=timeout_ms)
            result["visible_debug_trace_leaked"] = not _is_visible_product_text_clean(product_text)
            result["fetch_sequence"].extend(_capture_fetches(page))
            result["navigation_fetch_sequence_checked"] = _fetches_include_required_endpoints(
                result["fetch_sequence"]
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
    if int(report.get("long_session_message_count") or 0) < int(report.get("message_count_requested") or 0):
        blockers.append("long_session_message_count_too_low")
    for key, blocker in (
        ("first_cjk_message_rendered", "first_cjk_message_not_rendered"),
        ("middle_cjk_message_rendered", "middle_cjk_message_not_rendered"),
        ("last_cjk_message_rendered", "last_cjk_message_not_rendered"),
        ("chat_scroll_overflow_checked", "chat_scroll_overflow_not_checked"),
        ("chat_scroll_bottom_checked", "chat_scroll_bottom_not_checked"),
        ("reload_preserved_long_history", "reload_did_not_preserve_long_history"),
        ("click_chat_to_today_preserved_session", "chat_to_today_session_not_preserved"),
        ("click_today_to_body_preserved_session", "today_to_body_session_not_preserved"),
        ("click_body_to_chat_preserved_session", "body_to_chat_session_not_preserved"),
        ("chat_return_preserved_latest_message", "chat_return_latest_message_missing"),
        ("navigation_fetch_sequence_checked", "navigation_fetch_sequence_not_checked"),
    ):
        require_true(key, blocker)
    fetches = [item for item in report.get("fetch_sequence", []) if isinstance(item, dict)]
    for endpoint in REQUIRED_FETCH_ENDPOINTS:
        if not any(endpoint in str(item.get("url") or "") for item in fetches):
            blockers.append(f"fetch_missing:{endpoint}")
    estimate_posts = [
        str(item.get("body") or "").replace(" ", "")
        for item in fetches
        if "/estimate" in str(item.get("url") or "") and str(item.get("method") or "").upper() == "POST"
    ]
    if len(estimate_posts) < int(report.get("message_count_requested") or 0):
        blockers.append("estimate_post_count_too_low")
    if any('"allow_search":false' not in body or '"allow_search":true' in body for body in estimate_posts):
        blockers.append("estimate_allow_search_not_false")
    for key in (
        "forbidden_storage_used",
        "visible_debug_trace_leaked",
        "frontend_semantic_owner",
        "live_llm_invoked",
        "web_tavily_used",
        "production_db_used",
        "web_readiness_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
    ):
        if report.get(key) is True:
            blockers.append(key)
    if report.get("browser_sequence_error"):
        blockers.append(f"browser_sequence_error:{str(report['browser_sequence_error']).split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_product_pages_long_session_navigation_smoke_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = DEFAULT_USER_ID,
    local_date: str = DEFAULT_LOCAL_DATE,
    message_count: int = DEFAULT_MESSAGE_COUNT,
    reset_db: bool = True,
    require_browser_execution: bool = False,
    timeout_ms: int = 25000,
    headless: bool = True,
) -> dict[str, Any]:
    report = _base_report(
        user_external_id=user_external_id,
        db_path=db_path,
        local_date=local_date,
        message_count=message_count,
        browser_execution_required=require_browser_execution,
    )
    try:
        _load_sync_playwright()
    except BrowserSmokeDependencyMissing:
        report["status"] = "blocked" if not require_browser_execution else "fail"
        report["blockers"] = ["playwright_not_installed"]
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
        browser_result = _run_browser_sequence(
            base_url=base_url,
            user_external_id=user_external_id,
            local_date=local_date,
            message_count=message_count,
            timeout_ms=timeout_ms,
            headless=headless,
            local_debug_token=local_debug_token,
        )
        report["browser_executed"] = True
        report["browser"] = browser_result
        report.update({key: value for key, value in browser_result.items() if key in report})
        report["fetch_sequence"] = browser_result.get("fetch_sequence", [])
        report["manager_provider_call_count"] = len(provider.calls)
        report["status"], report["blockers"] = _validate(report)
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
    parser = argparse.ArgumentParser(description="Run long-session navigation smoke for product pages.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--message-count", type=int, default=DEFAULT_MESSAGE_COUNT)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=25000)
    args = parser.parse_args(argv)

    report = build_product_pages_long_session_navigation_smoke_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        local_date=args.local_date,
        message_count=args.message_count,
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
