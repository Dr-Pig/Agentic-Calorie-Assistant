from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.persistent_desktop_dogfood_baseline import (  # noqa: E402
    DEFAULT_DB_PATH,
    _dogfood_route_context,
    build_persistent_desktop_dogfood_baseline_report,
)
from scripts.run_accurate_intake_browser_one_day_fixture_dogfood import (  # noqa: E402
    _desktop_entry_state,
    _free_port,
    _run_desktop_loop_sequence,
    _run_uvicorn_in_thread,
    _wait_for_http,
)
from scripts.run_accurate_intake_browser_shell_smoke import (  # noqa: E402
    BrowserSmokeDependencyMissing,
    _install_fetch_recorder,
    _load_sync_playwright,
)
from scripts.run_accurate_intake_desktop_dogfood_launcher import (  # noqa: E402
    build_app_for_desktop_dogfood,
    close_desktop_dogfood_app,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_persistent_desktop_dogfood_baseline.json"


def _expected_today_summary(report: dict[str, object]) -> dict[str, str]:
    today = dict(dict(report.get("after_restart") or {}).get("today") or {})
    return {
        "budget_kcal": str(today["budget_kcal"]),
        "consumed_kcal": str(today["consumed_kcal"]),
        "remaining_kcal": str(today["remaining_kcal"]),
    }


def _browser_blockers(browser: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    entry = dict(browser.get("desktop_entry") or {})
    loop = dict(browser.get("desktop_loop") or {})
    for key, blocker in (
        ("surface_loaded", "desktop_entry_not_loaded"),
        ("session_connected", "desktop_entry_session_not_connected"),
    ):
        if entry.get(key) is not True:
            blockers.append(blocker)
    if entry.get("token_in_url") is True or loop.get("local_debug_token_in_url") is True:
        blockers.append("local_debug_token_in_url")
    if browser.get("forbidden_storage_used") is True or loop.get("forbidden_storage_used") is True:
        blockers.append("forbidden_browser_storage_used")
    navigation = dict(loop.get("page_navigation") or {})
    for page_name in ("chat", "today", "body", "feedback", "review", "data"):
        if navigation.get(page_name) is not True:
            blockers.append(f"desktop_page_not_loaded:{page_name}")
    for key, blocker in (
        ("today_same_truth_checked", "today_same_truth_not_checked"),
        ("feedback_submitted", "feedback_not_submitted"),
        ("review_queue_ingested_feedback", "review_queue_not_ingested"),
        ("data_export_sidecars_included", "export_sidecars_not_included"),
    ):
        if loop.get(key) is not True:
            blockers.append(blocker)
    return blockers


def _run_persistent_browser_sequence(
    *,
    db_path: Path,
    report: dict[str, object],
    user_external_id: str,
    local_date: str,
    local_debug_token: str,
    feedback_dir: Path,
    backup_dir: Path,
    export_dir: Path,
    review_queue_artifact_path: Path,
    timeout_ms: int,
    headless: bool,
) -> dict[str, object]:
    sync_playwright = _load_sync_playwright()
    app = None
    server = None
    thread = None
    try:
        with _dogfood_route_context(
            feedback_dir=feedback_dir,
            backup_dir=backup_dir,
            export_dir=export_dir,
            review_queue_artifact_path=review_queue_artifact_path,
            local_debug_token=local_debug_token,
        ):
            app = build_app_for_desktop_dogfood(db_path)
            port = _free_port()
            server, thread = _run_uvicorn_in_thread(app, port=port)
            base_url = f"http://127.0.0.1:{port}"
            _wait_for_http(f"{base_url}/static/accurate-intake-desktop.html")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=headless)
                page = browser.new_page()
                page.add_init_script(
                    f"window.LOCAL_DEBUG_API_TOKEN = {json.dumps(local_debug_token)};"
                )
                _install_fetch_recorder(page)
                try:
                    page.goto(
                        f"{base_url}/static/accurate-intake-desktop.html?user_id={user_external_id}&local_date={local_date}",
                        wait_until="networkidle",
                        timeout=timeout_ms,
                    )
                    page.wait_for_selector('[data-surface-role="desktop-dogfood-entry"]', timeout=timeout_ms)
                    page.fill("#local-debug-token", local_debug_token)
                    page.click("#establish-local-session")
                    page.wait_for_function(
                        """() => (document.querySelector("#entry-status")?.textContent || "").includes("Session connected")""",
                        timeout=timeout_ms,
                    )
                    entry = _desktop_entry_state(page)
                    loop = _run_desktop_loop_sequence(
                        page,
                        base_url=base_url,
                        expected_today_summary=_expected_today_summary(report),
                        feedback_dir=feedback_dir,
                        review_queue_artifact_path=review_queue_artifact_path,
                        timeout_ms=timeout_ms,
                        user_external_id=user_external_id,
                        local_date=local_date,
                    )
                    storage = page.evaluate(
                        """() => ({
                          localStorageKeys: Object.keys(window.localStorage || {}),
                          sessionStorageKeys: Object.keys(window.sessionStorage || {})
                        })"""
                    )
                    return {
                        "browser_name": "chromium",
                        "desktop_entry": entry,
                        "desktop_loop": loop,
                        "storage": storage,
                        "forbidden_storage_used": bool(
                            storage["localStorageKeys"] or storage["sessionStorageKeys"]
                        ),
                    }
                finally:
                    browser.close()
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=5)
        if app is not None:
            close_desktop_dogfood_app(app)


def _attach_required_browser_report(
    report: dict[str, object],
    *,
    db_path: Path,
    user_external_id: str,
    local_date: str,
    local_debug_token: str,
    feedback_dir: Path,
    backup_dir: Path,
    export_dir: Path,
    review_queue_artifact_path: Path,
    timeout_ms: int,
    headless: bool,
) -> dict[str, object]:
    report = {**report, "browser_execution_required": True, "browser_executed": False}
    if report.get("status") != "pass":
        return {**report, "status": "fail", "browser_blockers": ["baseline_not_pass"]}
    try:
        browser = _run_persistent_browser_sequence(
            db_path=db_path,
            report=report,
            user_external_id=user_external_id,
            local_date=local_date,
            local_debug_token=local_debug_token,
            feedback_dir=feedback_dir,
            backup_dir=backup_dir,
            export_dir=export_dir,
            review_queue_artifact_path=review_queue_artifact_path,
            timeout_ms=timeout_ms,
            headless=headless,
        )
    except BrowserSmokeDependencyMissing:
        return {**report, "status": "fail", "browser_blockers": ["playwright_not_installed"]}
    except Exception as exc:
        return {
            **report,
            "status": "fail",
            "browser_blockers": [f"browser_sequence_error:{type(exc).__name__}"],
            "browser_sequence_error": f"{type(exc).__name__}: {exc}",
        }
    blockers = _browser_blockers(browser)
    return {
        **report,
        "browser": browser,
        "browser_executed": True,
        "browser_blockers": blockers,
        "status": "pass" if not blockers else "fail",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the persistent desktop dogfood baseline.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--local-date", required=True)
    parser.add_argument("--user-id", default="local-self-use-001")
    parser.add_argument("--local-debug-token", required=True)
    parser.add_argument("--reset-db", action="store_true")
    parser.add_argument("--feedback-dir")
    parser.add_argument("--backup-dir")
    parser.add_argument("--export-dir")
    parser.add_argument("--review-queue-artifact-path")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    db_path = Path(args.db_path)
    feedback_dir = Path(args.feedback_dir) if args.feedback_dir else ROOT / "workspace_data" / "local_dogfood_feedback"
    backup_dir = Path(args.backup_dir) if args.backup_dir else ROOT / "workspace_data" / "local_dogfood_backups"
    export_dir = Path(args.export_dir) if args.export_dir else ROOT / "workspace_data" / "local_dogfood_exports"
    review_queue_artifact_path = (
        Path(args.review_queue_artifact_path)
        if args.review_queue_artifact_path
        else ROOT / "artifacts" / "accurate_intake_dogfood_review_queue.json"
    )
    report = build_persistent_desktop_dogfood_baseline_report(
        db_path=db_path,
        local_date=args.local_date,
        user_external_id=args.user_id,
        local_debug_token=args.local_debug_token,
        reset_db=args.reset_db,
        feedback_dir=feedback_dir,
        backup_dir=backup_dir,
        export_dir=export_dir,
        review_queue_artifact_path=review_queue_artifact_path,
    )
    if args.require_browser_execution:
        report = _attach_required_browser_report(
            report,
            db_path=db_path,
            user_external_id=args.user_id,
            local_date=args.local_date,
            local_debug_token=args.local_debug_token,
            feedback_dir=feedback_dir,
            backup_dir=backup_dir,
            export_dir=export_dir,
            review_queue_artifact_path=review_queue_artifact_path,
            timeout_ms=args.timeout_ms,
            headless=not args.headed,
        )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
