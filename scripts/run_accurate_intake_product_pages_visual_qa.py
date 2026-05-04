from __future__ import annotations

import argparse
import binascii
import json
import os
import secrets
import struct
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
from scripts.run_accurate_intake_product_pages_browser_smoke import (  # noqa: E402
    DEFAULT_CJK_MESSAGE,
    DEFAULT_LOCAL_DATE,
    BrowserSmokeDependencyMissing,
    DeterministicSelfUseManagerProvider,
    _build_app,
    _capture_fetches,
    _free_port,
    _is_visible_product_text_clean,
    _load_sync_playwright,
    _nav_session_query_preserved,
    _open_page,
    _overflow_state,
    _page_url,
    _restore_runtime,
    _run_uvicorn_in_thread,
    _seed_body_plan,
    _session_factory,
    _storage_state,
    _wait_for_http,
)


DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_product_pages_visual_qa.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_product_pages_visual_qa.json"
DEFAULT_SCREENSHOT_DIR = ROOT / "artifacts" / "product_pages_visual_qa"
DEFAULT_USER_ID = "product-pages-visual-qa-user"
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
    "private_self_use_approved",
]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    screenshot_dir: Path,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_product_pages_visual_qa",
        "claim_scope": "local_product_pages_visual_qa_diagnostic",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "screenshot_dir": str(screenshot_dir),
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "desktop_screenshots_captured": False,
        "mobile_screenshots_captured": False,
        "chat_surface_verified": False,
        "today_surface_verified": False,
        "body_surface_verified": False,
        "three_distinct_pages_verified": False,
        "desktop_no_overflow": False,
        "mobile_no_overflow": False,
        "visible_trace_debug_terms_absent": False,
        "forbidden_storage_used": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "screenshots": {"desktop": {}, "mobile": {}},
        "surface_text": {},
        "fetch_sequence": [],
    }


def _surface_verified(page: Any, page_name: str, *, timeout_ms: int) -> bool:
    requirements = {
        "chat": (
            '[data-surface-role="chat"]',
            "#chat-scroll",
            "#composer",
            "#message-input",
        ),
        "today": (
            '[data-surface-role="today-diary"]',
            "#budget-kcal",
            "#meal-list",
            "#day-strip",
        ),
        "body": (
            '[data-surface-role="body-plan"]',
            "#body-plan-summary",
            "#weight-form",
            "#onboarding-form",
        ),
    }
    return all(page.locator(selector).count() > 0 for selector in requirements[page_name])


def _capture_product_page(
    browser: Any,
    *,
    base_url: str,
    page_name: str,
    viewport_name: str,
    viewport: dict[str, int],
    user_external_id: str,
    local_date: str,
    timeout_ms: int,
    local_debug_token: str,
    screenshot_dir: Path,
) -> dict[str, Any]:
    page = _open_page(
        browser,
        viewport=viewport,
        url=_page_url(base_url, page_name, user_external_id=user_external_id, local_date=local_date),
        timeout_ms=timeout_ms,
        local_debug_token=local_debug_token,
    )
    try:
        if page_name == "chat":
            page.wait_for_selector('[data-surface-role="chat"]', timeout=timeout_ms)
            page.wait_for_function(
                """() => (document.querySelector("#chat-scroll")?.textContent || "").includes("Logged.") """,
                timeout=timeout_ms,
            )
        if page_name == "today":
            page.wait_for_selector('[data-surface-role="today-diary"]', timeout=timeout_ms)
            page.wait_for_function(
                """() => document.querySelector("#budget-kcal")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )
        if page_name == "body":
            page.wait_for_selector('[data-surface-role="body-plan"]', timeout=timeout_ms)
            page.wait_for_function(
                """() => document.querySelector("#plan-daily-target")?.textContent?.trim() !== "--" """,
                timeout=timeout_ms,
            )

        screenshot_path = screenshot_dir / f"{page_name}-{viewport_name}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        text = page.locator("body").inner_text(timeout=timeout_ms)
        page_id = page.evaluate("() => document.documentElement.dataset.pageId || ''")
        return {
            "page_name": page_name,
            "viewport_name": viewport_name,
            "page_id": page_id,
            "screenshot_path": str(screenshot_path),
            "text": text,
            "surface_verified": _surface_verified(page, page_name, timeout_ms=timeout_ms),
            "visible_text_clean": _is_visible_product_text_clean(text),
            "overflow": _overflow_state(page),
            "storage": _storage_state(page),
            "nav_session_query_preserved": _nav_session_query_preserved(
                page,
                user_external_id=user_external_id,
                local_date=local_date,
            ),
            "fetch_sequence": _capture_fetches(page),
        }
    finally:
        page.close()


def _run_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    local_date: str,
    cjk_message: str,
    timeout_ms: int,
    headless: bool,
    local_debug_token: str,
    screenshot_dir: Path,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "screenshots": {"desktop": {}, "mobile": {}},
        "surface_text": {},
        "page_ids": [],
        "fetch_sequence": [],
        "current_step": "not_started",
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            result["current_step"] = "seed_chat_history"
            chat = _open_page(
                browser,
                viewport={"width": 1440, "height": 1100},
                url=_page_url(base_url, "chat", user_external_id=user_external_id, local_date=local_date),
                timeout_ms=timeout_ms,
                local_debug_token=local_debug_token,
            )
            chat.fill("#message-input", cjk_message)
            chat.click("#send-button")
            chat.wait_for_function(
                """() => (document.querySelector("#chat-scroll")?.textContent || "").includes("Logged.") """,
                timeout=timeout_ms,
            )
            result["fetch_sequence"].extend(_capture_fetches(chat))
            chat.close()

            captures: list[dict[str, Any]] = []
            for viewport_name, viewport in (
                ("desktop", {"width": 1440, "height": 1100}),
                ("mobile", {"width": 390, "height": 844}),
            ):
                for page_name in ("chat", "today", "body"):
                    result["current_step"] = f"capture_{page_name}_{viewport_name}"
                    capture = _capture_product_page(
                        browser,
                        base_url=base_url,
                        page_name=page_name,
                        viewport_name=viewport_name,
                        viewport=viewport,
                        user_external_id=user_external_id,
                        local_date=local_date,
                        timeout_ms=timeout_ms,
                        local_debug_token=local_debug_token,
                        screenshot_dir=screenshot_dir,
                    )
                    captures.append(capture)
                    result["screenshots"][viewport_name][page_name] = capture["screenshot_path"]
                    result["surface_text"][f"{page_name}_{viewport_name}"] = capture["text"]
                    result["page_ids"].append(capture["page_id"])
                    result["fetch_sequence"].extend(capture["fetch_sequence"])

            result["desktop_screenshots_captured"] = all(
                Path(result["screenshots"]["desktop"].get(page_name, "")).is_file()
                for page_name in ("chat", "today", "body")
            )
            result["mobile_screenshots_captured"] = all(
                Path(result["screenshots"]["mobile"].get(page_name, "")).is_file()
                for page_name in ("chat", "today", "body")
            )
            result["chat_surface_verified"] = all(
                item["surface_verified"] for item in captures if item["page_name"] == "chat"
            )
            result["today_surface_verified"] = all(
                item["surface_verified"] for item in captures if item["page_name"] == "today"
            )
            result["body_surface_verified"] = all(
                item["surface_verified"] for item in captures if item["page_name"] == "body"
            )
            result["three_distinct_pages_verified"] = len(set(result["page_ids"])) == 3
            result["desktop_no_overflow"] = all(
                item["overflow"].get("documentScrollWidth") == item["overflow"].get("viewport")
                and not item["overflow"].get("overflowingElements")
                for item in captures
                if item["viewport_name"] == "desktop"
            )
            result["mobile_no_overflow"] = all(
                item["overflow"].get("documentScrollWidth") == item["overflow"].get("viewport")
                and not item["overflow"].get("overflowingElements")
                for item in captures
                if item["viewport_name"] == "mobile"
            )
            result["visible_trace_debug_terms_absent"] = all(item["visible_text_clean"] for item in captures)
            result["forbidden_storage_used"] = any(
                item["storage"].get("localStorageKeys") or item["storage"].get("sessionStorageKeys")
                for item in captures
            )
            result["nav_session_query_preserved"] = all(item["nav_session_query_preserved"] for item in captures)
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

    def png_dimensions(path: Path) -> tuple[int, int] | None:
        data = path.read_bytes()
        if len(data) < 45 or not data.startswith(PNG_SIGNATURE):
            return None
        offset = len(PNG_SIGNATURE)
        dimensions: tuple[int, int] | None = None
        saw_idat = False
        saw_iend = False
        while offset + 12 <= len(data):
            chunk_length = struct.unpack(">I", data[offset : offset + 4])[0]
            chunk_type = data[offset + 4 : offset + 8]
            payload_start = offset + 8
            payload_end = payload_start + chunk_length
            crc_end = payload_end + 4
            if crc_end > len(data):
                return None
            expected_crc = struct.unpack(">I", data[payload_end:crc_end])[0]
            actual_crc = binascii.crc32(chunk_type + data[payload_start:payload_end]) & 0xFFFFFFFF
            if actual_crc != expected_crc:
                return None
            if chunk_type == b"IHDR":
                if chunk_length != 13 or dimensions is not None:
                    return None
                width = struct.unpack(">I", data[payload_start : payload_start + 4])[0]
                height = struct.unpack(">I", data[payload_start + 4 : payload_start + 8])[0]
                if width <= 0 or height <= 0:
                    return None
                dimensions = (width, height)
            elif chunk_type == b"IDAT":
                saw_idat = True
            elif chunk_type == b"IEND":
                if chunk_length != 0:
                    return None
                saw_iend = True
                if crc_end != len(data):
                    return None
                break
            offset = crc_end
        if dimensions is None or not saw_idat or not saw_iend:
            return None
        width, height = dimensions
        if width <= 0 or height <= 0:
            return None
        return dimensions

    def require_screenshot_file(value: Any, *, viewport_name: str, page_name: str) -> None:
        if not value:
            blockers.append(f"screenshot_missing:{viewport_name}:{page_name}")
            return
        path = Path(str(value))
        if path.suffix.lower() != ".png":
            blockers.append(f"screenshot_not_png:{viewport_name}:{page_name}")
            return
        if not path.is_file():
            blockers.append(f"screenshot_file_missing:{viewport_name}:{page_name}")
            return
        if path.stat().st_size <= 0:
            blockers.append(f"screenshot_file_empty:{viewport_name}:{page_name}")
            return
        if png_dimensions(path) is None:
            blockers.append(f"screenshot_invalid_png:{viewport_name}:{page_name}")

    require_true("browser_executed", "browser_not_executed")
    require_true("desktop_screenshots_captured", "desktop_screenshots_not_captured")
    require_true("mobile_screenshots_captured", "mobile_screenshots_not_captured")
    require_true("chat_surface_verified", "chat_surface_not_verified")
    require_true("today_surface_verified", "today_surface_not_verified")
    require_true("body_surface_verified", "body_surface_not_verified")
    require_true("three_distinct_pages_verified", "three_distinct_pages_not_verified")
    require_true("desktop_no_overflow", "desktop_overflow_detected")
    require_true("mobile_no_overflow", "mobile_overflow_detected")
    require_true("visible_trace_debug_terms_absent", "visible_trace_debug_terms_present")

    for viewport_name in ("desktop", "mobile"):
        screenshots = dict(dict(report.get("screenshots") or {}).get(viewport_name) or {})
        for page_name in ("chat", "today", "body"):
            require_screenshot_file(screenshots.get(page_name), viewport_name=viewport_name, page_name=page_name)

    for key in (
        "frontend_semantic_owner",
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

    sequence_error = str(report.get("browser_sequence_error") or "")
    if sequence_error:
        blockers.append(f"browser_sequence_error:{sequence_error.split(':', 1)[0]}")
    return ("pass" if not blockers else "fail"), blockers


def build_product_pages_visual_qa_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    screenshot_dir: Path = DEFAULT_SCREENSHOT_DIR,
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
        screenshot_dir=screenshot_dir,
        browser_execution_required=require_browser_execution,
    )
    try:
        _load_sync_playwright()
    except BrowserSmokeDependencyMissing:
        report["status"] = "blocked" if not require_browser_execution else "fail"
        report["blockers"] = ["playwright_not_installed"]
        report["operator_action"] = "Install Playwright locally and rerun; this artifact must not claim readiness."
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
            cjk_message=cjk_message,
            timeout_ms=timeout_ms,
            headless=headless,
            local_debug_token=local_debug_token,
            screenshot_dir=screenshot_dir,
        )
        report["browser_executed"] = True
        report["browser"] = browser_result
        for key, value in browser_result.items():
            if key in report:
                report[key] = value
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
    parser = argparse.ArgumentParser(description="Capture visual QA screenshots for Accurate Intake product pages.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--screenshot-dir", default=str(DEFAULT_SCREENSHOT_DIR))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--cjk-message", default=DEFAULT_CJK_MESSAGE)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args(argv)

    report = build_product_pages_visual_qa_report(
        db_path=Path(args.db_path),
        screenshot_dir=Path(args.screenshot_dir),
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
