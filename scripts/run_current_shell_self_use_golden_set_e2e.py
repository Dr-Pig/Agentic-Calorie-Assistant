from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_local_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False, encoding="utf-8-sig")
        return
    except ModuleNotFoundError:
        pass
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_local_env(ROOT / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.composition import intake_chat_turn_routes, intake_routes  # noqa: E402
from app.composition.current_shell_golden_set_grader import (  # noqa: E402
    load_golden_set_manifest,
)
from app.composition.current_shell_golden_set_request_trace_adapter import (  # noqa: E402
    build_golden_case_trace_from_request_trace,
    build_golden_trace_artifact_from_request_traces,
)
from app.composition.onboarding_service import (  # noqa: E402
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_db, get_or_create_user  # noqa: E402
from app.logging import REQUEST_TRACE_DIR  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from scripts.build_current_shell_self_use_golden_set_replay import (  # noqa: E402
    DEFAULT_OUTPUT_PATH as DEFAULT_REPLAY_OUTPUT_PATH,
    build_golden_set_replay,
)
from scripts.run_accurate_intake_mvp_manager_style_smoke import (  # noqa: E402
    DeterministicSelfUseManagerProvider,
)


DEFAULT_MANIFEST_PATH = ROOT / "docs" / "quality" / "current_shell_self_use_golden_set_manifest.yaml"
DEFAULT_DB_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_e2e.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_e2e_report.json"
DEFAULT_TRACE_ARTIFACT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_trace_artifact.json"
DEFAULT_LOCAL_DATE = "2026-05-14"


def build_current_shell_golden_set_e2e_report(
    *,
    case_ids: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    trace_artifact_path: Path = DEFAULT_TRACE_ARTIFACT_PATH,
    replay_output_path: Path = DEFAULT_REPLAY_OUTPUT_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    provider_mode: str = "configured",
    local_date: str = DEFAULT_LOCAL_DATE,
    allow_search: bool = False,
) -> dict[str, Any]:
    manifest = _read_manifest(manifest_path)
    selected_cases = _select_cases(manifest, case_ids)
    engine, SessionLocal = _session_factory(db_path)
    provider = _provider_for_mode(provider_mode)
    client = _build_test_client(SessionLocal, provider=provider)
    case_runs: list[dict[str, Any]] = []
    case_traces: list[dict[str, Any]] = []

    try:
        for case in selected_cases:
            case_run, request_trace = _run_case(
                client=client,
                SessionLocal=SessionLocal,
                case=case,
                local_date=local_date,
                allow_search=allow_search,
            )
            case_runs.append(case_run)
            if request_trace:
                case_traces.append(
                    _build_case_trace(
                        case_id=str(case.get("case_id") or ""),
                        request_trace=request_trace,
                        provider_mode=provider_mode,
                    )
                )
    finally:
        _close_test_client(client)
        engine.dispose()

    trace_artifact = build_golden_trace_artifact_from_request_traces(case_traces)
    replay = build_golden_set_replay(manifest=manifest, trace_artifact=trace_artifact)
    report = _json_safe(
        {
            "artifact_type": "current_shell_self_use_golden_set_e2e_report",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "real_entrypoint_runtime_projection",
            "entrypoint": "/estimate",
            "provider_mode": provider_mode,
            "live_invoked_by_runner": _live_invoked(case_traces),
            "runner_inferred_semantics": False,
            "semantic_keyword_oracle_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "whole_product_mvp_claimed": False,
            "summary": {
                "selected_case_count": len(selected_cases),
                "request_trace_case_count": len(case_traces),
                "strict_golden_set_replay_passed": replay["summary"][
                    "strict_golden_set_replay_passed"
                ],
                "failed_case_count": replay["summary"]["failed_case_count"],
                "missing_case_count": replay["summary"]["missing_case_count"],
            },
            "case_runs": case_runs,
            "trace_artifact": trace_artifact,
            "replay": replay,
        }
    )
    _write_json(trace_artifact_path, trace_artifact)
    _write_json(replay_output_path, replay)
    _write_json(output_path, report)
    return report


def _run_case(
    *,
    client: TestClient,
    SessionLocal: sessionmaker[Session],
    case: dict[str, Any],
    local_date: str,
    allow_search: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    case_id = str(case.get("case_id") or "")
    user_external_id = f"gs-e2e-{case_id.lower()}-{secrets.token_hex(3)}"
    _seed_case_state(SessionLocal, case=case, user_external_id=user_external_id, local_date=local_date)
    turn_reports: list[dict[str, Any]] = []
    last_request_trace: dict[str, Any] | None = None
    for index, turn in enumerate(_script_turns(case), start=1):
        request_id = f"{case_id.lower()}-turn{index}-{secrets.token_hex(8)}"
        trace_path = REQUEST_TRACE_DIR / f"{request_id}.json"
        started = datetime.now(UTC)
        response = client.post(
            "/estimate",
            json={
                "text": str(turn.get("utterance_zh_tw") or turn.get("utterance") or ""),
                "allow_search": allow_search,
                "user_id": user_external_id,
                "local_date": local_date,
                "request_id": request_id,
            },
        )
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        request_trace = _read_json(trace_path) if trace_path.exists() else None
        if request_trace:
            last_request_trace = request_trace
        turn_reports.append(
            {
                "turn": index,
                "entrypoint": "/estimate",
                "request_id": request_id,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "request_trace_path": str(trace_path),
                "request_trace_exists": trace_path.exists(),
                "response_has_payload": bool(_response_json(response).get("payload")),
                "runner_inferred_semantics": False,
                "semantic_keyword_oracle_used": False,
            }
        )
    return (
        {
            "case_id": case_id,
            "entrypoint": "/estimate",
            "user_external_id": user_external_id,
            "local_date": local_date,
            "turns": turn_reports,
            "request_trace_selected": "last_turn",
            "runner_inferred_semantics": False,
        },
        last_request_trace,
    )


def _build_case_trace(
    *,
    case_id: str,
    request_trace: dict[str, Any],
    provider_mode: str,
) -> dict[str, Any]:
    case_trace = build_golden_case_trace_from_request_trace(case_id, request_trace)
    if provider_mode.strip().lower() == "scripted":
        case_trace["manager_provider"] = {
            **_dict(case_trace.get("manager_provider")),
            "provider": "deterministic_self_use_manager_fixture",
            "semantic_source": "fixture_provider",
            "live_llm_invoked": False,
        }
    return case_trace


def _seed_case_state(
    SessionLocal: sessionmaker[Session],
    *,
    case: dict[str, Any],
    user_external_id: str,
    local_date: str,
) -> None:
    db = SessionLocal()
    try:
        user = get_or_create_user(db, user_external_id)
        seed_state = _dict(case.get("seed_state"))
        if seed_state.get("body_plan") != "missing":
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
        db.commit()
    finally:
        db.close()


def _build_test_client(
    SessionLocal: sessionmaker[Session],
    *,
    provider: Any | None,
) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    previous = (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
        intake_chat_turn_routes.SessionLocal,
    )
    if provider is not None:
        intake_routes.manager_provider = provider
        intake_routes.search_provider = None
        intake_routes.extract_provider = None
    intake_chat_turn_routes.SessionLocal = SessionLocal
    app.state.current_shell_golden_set_restore_runtime = previous
    return TestClient(app)


def _close_test_client(client: TestClient) -> None:
    previous = getattr(client.app.state, "current_shell_golden_set_restore_runtime", None)
    client.close()
    if previous is None:
        return
    (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
        intake_chat_turn_routes.SessionLocal,
    ) = previous


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _provider_for_mode(provider_mode: str) -> Any | None:
    normalized = provider_mode.strip().lower()
    if normalized == "scripted":
        return DeterministicSelfUseManagerProvider()
    if normalized == "configured":
        return None
    raise ValueError(f"unsupported provider_mode: {provider_mode}")


def _select_cases(manifest: dict[str, Any], case_ids: list[str] | None) -> list[dict[str, Any]]:
    manifest_cases = [_dict(item) for item in _list(manifest.get("cases"))]
    if not case_ids:
        return manifest_cases
    wanted = {case_id.strip() for case_id in case_ids if case_id.strip()}
    selected = [case for case in manifest_cases if str(case.get("case_id") or "") in wanted]
    missing = sorted(wanted - {str(case.get("case_id") or "") for case in selected})
    if missing:
        raise ValueError(f"unknown golden set case id(s): {', '.join(missing)}")
    return selected


def _script_turns(case: dict[str, Any]) -> list[dict[str, Any]]:
    turns = [_dict(turn) for turn in _list(case.get("script"))]
    if not turns:
        raise ValueError(f"case {case.get('case_id')} has no script turns")
    for turn in turns:
        if not str(turn.get("utterance_zh_tw") or turn.get("utterance") or "").strip():
            raise ValueError(f"case {case.get('case_id')} has an empty turn utterance")
    return turns


def _live_invoked(case_traces: list[dict[str, Any]]) -> bool:
    for case_trace in case_traces:
        manager_provider = _dict(case_trace.get("manager_provider"))
        if manager_provider.get("live_llm_invoked") is True:
            return True
    return False


def _response_json(response: Any) -> dict[str, Any]:
    try:
        loaded = response.json()
    except Exception:
        return {}
    return _dict(loaded)


def _read_manifest(path: Path) -> dict[str, Any]:
    if path == DEFAULT_MANIFEST_PATH:
        return load_golden_set_manifest(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return _dict(loaded)


def _read_json(path: Path) -> dict[str, Any]:
    return _dict(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Current Shell self-use Golden Set cases through the real /estimate entrypoint."
    )
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--trace-artifact", default=str(DEFAULT_TRACE_ARTIFACT_PATH))
    parser.add_argument("--replay-output", default=str(DEFAULT_REPLAY_OUTPUT_PATH))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--provider-mode", choices=("configured", "scripted"), default="configured")
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--allow-search", action="store_true")
    args = parser.parse_args(argv)
    report = build_current_shell_golden_set_e2e_report(
        case_ids=list(args.case_id),
        db_path=Path(args.db_path),
        output_path=Path(args.output),
        trace_artifact_path=Path(args.trace_artifact),
        replay_output_path=Path(args.replay_output),
        manifest_path=Path(args.manifest),
        provider_mode=str(args.provider_mode),
        local_date=str(args.local_date),
        allow_search=bool(args.allow_search),
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "trace_artifact": str(Path(args.trace_artifact)),
                "replay_output": str(Path(args.replay_output)),
                "provider_mode": report["provider_mode"],
                "live_invoked_by_runner": report["live_invoked_by_runner"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["summary"]["strict_golden_set_replay_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
