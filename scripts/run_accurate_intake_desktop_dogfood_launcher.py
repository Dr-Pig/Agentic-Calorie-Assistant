from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import get_db  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.runtime.interface.local_debug_auth import (  # noqa: E402
    LOCAL_DEBUG_API_TOKEN_ENV,
    LOCAL_DEBUG_API_TOKEN_HEADER,
)
from app.runtime.interface.base_routes import public_provider_readiness  # noqa: E402
from app.runtime.interface.provider_runtime import (  # noqa: E402
    extract_provider,
    manager_provider,
    search_provider,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_USER_ID = "local-self-use-001"
DEFAULT_DB_PATH = ROOT / "workspace_data" / "local_dogfood" / "accurate_intake.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_desktop_dogfood_launcher.json"
NOT_CLAIMING = [
    "product_ready",
    "private_self_use_approved",
    "production_ready",
    "live_llm_ready",
    "fooddb_expansion_ready",
]


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _launch_url(*, host: str, port: int, user_id: str) -> str:
    query = urlencode({"user_id": user_id})
    return f"http://{host}:{port}/static/accurate-intake-desktop.html?{query}"


def _desktop_provider_status() -> dict[str, dict[str, Any]]:
    manager_status = public_provider_readiness(manager_provider.readiness())
    return {
        "provider": manager_status,
        "manager_provider": manager_status,
        "search": public_provider_readiness(search_provider.readiness()),
        "extract": public_provider_readiness(extract_provider.readiness()),
    }


def build_launch_descriptor(
    *,
    host: str,
    port: int,
    user_id: str,
    db_path: Path,
    local_debug_token: str,
    provider_status: dict[str, dict[str, Any]] | None = None,
    server_started: bool = False,
    browser_open_requested: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_desktop_dogfood_launcher_descriptor",
        "status": "launch_descriptor_ready",
        "entry_surface": "desktop_dogfood_hub",
        "host": host,
        "port": port,
        "user_id": user_id,
        "db_path": _repo_relative(db_path),
        "persistent_local_sqlite": True,
        "reset_db_default": False,
        "server_started": server_started,
        "browser_open_requested": browser_open_requested,
        "launch_url": _launch_url(host=host, port=port, user_id=user_id),
        "entry_pages": [
            "desktop",
            "chat",
            "today",
            "body",
            "feedback",
            "review",
            "data",
        ],
        "provider_status": provider_status or _desktop_provider_status(),
        "local_debug_token": local_debug_token,
        "local_debug_header": LOCAL_DEBUG_API_TOKEN_HEADER,
        "local_debug_token_in_url": False,
        "runtime_truth_changed": False,
        "mutation_legality_changed": False,
        "fooddb_truth_updated": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "not_claiming": list(NOT_CLAIMING),
    }


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def build_app_for_desktop_dogfood(db_path: Path) -> FastAPI:
    engine, SessionLocal = _session_factory(db_path)
    app = FastAPI()
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    app.state.accurate_intake_desktop_engine = engine

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def close_desktop_dogfood_app(app: FastAPI) -> None:
    state = getattr(app, "state", None)
    engine = getattr(state, "accurate_intake_desktop_engine", None)
    if engine is not None:
        engine.dispose()


def _write_descriptor(path: Path, descriptor: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the local Accurate Intake desktop dogfood shell.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--local-debug-token", default="")
    parser.add_argument("--describe-only", action="store_true")
    parser.add_argument("--no-open-browser", action="store_true")
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)
    token = str(args.local_debug_token or "").strip() or secrets.token_urlsafe(24)
    browser_open_requested = not bool(args.describe_only or args.no_open_browser)
    descriptor = build_launch_descriptor(
        host=str(args.host),
        port=int(args.port),
        user_id=str(args.user_id),
        db_path=db_path,
        local_debug_token=token,
        server_started=not bool(args.describe_only),
        browser_open_requested=browser_open_requested,
    )
    _write_descriptor(Path(args.output), descriptor)
    print(json.dumps(descriptor, ensure_ascii=False, indent=2))
    if args.describe_only:
        return 0

    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = token
    app = build_app_for_desktop_dogfood(db_path)
    if browser_open_requested:
        threading.Timer(1.0, lambda: webbrowser.open(descriptor["launch_url"])).start()
    uvicorn.run(app, host=str(args.host), port=int(args.port), log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
