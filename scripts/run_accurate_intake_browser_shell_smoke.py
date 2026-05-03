from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.database import get_db, get_or_create_user  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider  # noqa: E402

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_browser_shell_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_browser_shell_smoke.json"
DEFAULT_CJK_MESSAGE = "早餐吃茶葉蛋和拿鐵"
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


class BrowserSmokeDependencyMissing(RuntimeError):
    pass


def _load_sync_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise BrowserSmokeDependencyMissing("playwright_not_installed") from exc
    return sync_playwright


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=34,
            height_cm=170,
            current_weight_kg=70,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="1_2",
            local_date=local_date,
        ),
    )


def _build_app(db: Session, provider: DeterministicSelfUseManagerProvider) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    previous = (intake_routes.manager_provider, intake_routes.search_provider, intake_routes.extract_provider)
    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None
    app.state.accurate_intake_restore_runtime = previous
    return app


def _restore_runtime(app: FastAPI) -> None:
    previous = getattr(app.state, "accurate_intake_restore_runtime", None)
    if previous is not None:
        intake_routes.manager_provider, intake_routes.search_provider, intake_routes.extract_provider = previous


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - depends on server startup timing
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"server_not_ready: {last_error}")


def _run_uvicorn_in_thread(app: FastAPI, *, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def _install_fetch_recorder(page: Any) -> None:
    page.add_init_script(
        """
        (() => {
          window.__accurateIntakeFetches = [];
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (input, init = {}) => {
            const url = typeof input === "string" ? input : input.url;
            window.__accurateIntakeFetches.push({
              url,
              method: init.method || "GET",
              body: init.body || null
            });
            return originalFetch(input, init);
          };
        })();
        """
    )


def _run_browser_sequence(
    *,
    base_url: str,
    user_external_id: str,
    cjk_message: str,
    timeout_ms: int,
    headless: bool,
) -> dict[str, Any]:
    sync_playwright = _load_sync_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        _install_fetch_recorder(page)
        try:
            page.goto(f"{base_url}/static/accurate-intake-local-shell.html", wait_until="networkidle", timeout=timeout_ms)
            page.fill("#user-id", user_external_id)
            page.wait_for_selector("#message-input", timeout=timeout_ms)
            initial_chat_text = page.locator("#chat-log").inner_text(timeout=timeout_ms)
            shell_markers = page.locator("main.shell").evaluate(
                """(node) => ({
                  frontendSemanticOwner: node.dataset.frontendSemanticOwner,
                  liveLlmRequired: node.dataset.liveLlmRequired,
                  productionReadinessClaimed: node.dataset.productionReadinessClaimed
                })"""
            )
            page.fill("#message-input", cjk_message)
            page.click("#send-button")
            page.wait_for_function(
                """() => {
                  const payload = document.querySelector("#last-payload")?.textContent?.trim();
                  return payload && payload !== "{}";
                }""",
                timeout=timeout_ms,
            )
            page.wait_for_function(
                """() => {
                  const consumed = document.querySelector("#consumed-kcal")?.textContent?.trim();
                  return consumed && consumed !== "unavailable";
                }""",
                timeout=timeout_ms,
            )
            chat_text = page.locator("#chat-log").inner_text(timeout=timeout_ms)
            last_payload_text = page.locator("#last-payload").inner_text(timeout=timeout_ms)
            fetches = page.evaluate("window.__accurateIntakeFetches || []")
            storage = page.evaluate(
                """() => ({
                  localStorageKeys: Object.keys(window.localStorage || {}),
                  sessionStorageKeys: Object.keys(window.sessionStorage || {})
                })"""
            )
            return {
                "browser_name": "chromium",
                "page_url": page.url,
                "shell_markers": shell_markers,
                "initial_cjk_rendered": "今天可以直接記錄飲食" in initial_chat_text,
                "user_cjk_message_rendered": cjk_message in chat_text,
                "assistant_bubble_rendered": "Runtime processing" not in chat_text,
                "last_payload_parseable": bool(json.loads(last_payload_text)),
                "fetch_sequence": fetches,
                "storage": storage,
            }
        finally:
            browser.close()


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if report.get("browser_executed") is not True:
        blockers.append("browser_not_executed")
    browser = dict(report.get("browser") or {})
    shell_markers = dict(browser.get("shell_markers") or {})
    if shell_markers.get("frontendSemanticOwner") != "false":
        blockers.append("frontend_semantic_owner_marker_missing")
    if shell_markers.get("liveLlmRequired") != "false":
        blockers.append("live_llm_marker_missing")
    if shell_markers.get("productionReadinessClaimed") != "false":
        blockers.append("production_readiness_marker_missing")
    if browser.get("initial_cjk_rendered") is not True:
        blockers.append("initial_cjk_not_rendered")
    if browser.get("user_cjk_message_rendered") is not True:
        blockers.append("user_cjk_message_not_rendered")
    if browser.get("assistant_bubble_rendered") is not True:
        blockers.append("assistant_bubble_not_rendered")
    if browser.get("last_payload_parseable") is not True:
        blockers.append("last_payload_not_parseable")
    fetches = list(browser.get("fetch_sequence") or [])
    urls = [str(item.get("url") or "") for item in fetches if isinstance(item, dict)]
    for expected in (
        "/today/current-budget",
        "/body-plan/active",
        "/accurate-intake/debug",
        "/accurate-intake/chat-history",
        "/estimate",
    ):
        if not any(expected in url for url in urls):
            blockers.append(f"fetch_missing:{expected}")
    storage = dict(browser.get("storage") or {})
    if storage.get("localStorageKeys"):
        blockers.append("local_storage_used")
    if storage.get("sessionStorageKeys"):
        blockers.append("session_storage_used")
    return ("pass" if not blockers else "fail"), blockers


def _base_report(
    *,
    user_external_id: str,
    db_path: Path,
    browser_execution_required: bool,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_browser_executed_shell_smoke_v1",
        "claim_scope": "local_browser_executed_shell_smoke_artifact",
        "evidence_scope": "browser_executed_fetch_sequence_when_playwright_available",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(NOT_CLAIMING),
        "user_external_id": user_external_id,
        "db_path": str(db_path),
        "browser_execution_required": browser_execution_required,
        "browser_executed": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "product_readiness_claimed": False,
        "web_readiness_claimed": False,
        "frontend_semantic_owner": False,
    }


def build_browser_shell_smoke_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = "browser-shell-smoke-user",
    reset_db: bool = True,
    require_browser_execution: bool = False,
    timeout_ms: int = 15000,
    headless: bool = True,
    cjk_message: str = DEFAULT_CJK_MESSAGE,
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
        report["operator_action"] = "Install Playwright locally and rerun this script; this is not a web-readiness claim."
        return report

    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    provider = DeterministicSelfUseManagerProvider()
    db = SessionLocal()
    app = _build_app(db, provider)
    port = _free_port()
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-local-shell.html")
        user = get_or_create_user(db, user_external_id)
        local_date = "2026-05-04"
        _seed_body_plan(db, user_external_id=user.external_id, local_date=local_date)
        report["browser"] = _run_browser_sequence(
            base_url=base_url,
            user_external_id=user_external_id,
            cjk_message=cjk_message,
            timeout_ms=timeout_ms,
            headless=headless,
        )
        report["browser_executed"] = True
        report["manager_provider_call_count"] = len(provider.calls)
        status, blockers = _validate(report)
        report["status"] = status
        report["blockers"] = blockers
        return report
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        _restore_runtime(app)
        db.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake browser-executed local shell smoke.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default="browser-shell-smoke-user")
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--require-browser-execution", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--cjk-message", default=DEFAULT_CJK_MESSAGE)
    args = parser.parse_args(argv)

    report = build_browser_shell_smoke_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        reset_db=not args.keep_db,
        require_browser_execution=args.require_browser_execution,
        timeout_ms=args.timeout_ms,
        headless=not args.headed,
        cjk_message=args.cjk_message,
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
