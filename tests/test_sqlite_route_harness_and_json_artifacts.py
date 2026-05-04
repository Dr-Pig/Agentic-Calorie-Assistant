from __future__ import annotations

import json

from fastapi import Depends, FastAPI
from sqlalchemy import text

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
from app.shared.infra.sqlite_route_harness import LocalSQLiteRouteHarness


def _get_db_placeholder():
    raise RuntimeError("test override was not installed")


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping(db=Depends(_get_db_placeholder)) -> dict[str, int]:
        return {"value": db.execute(text("select 1")).scalar_one()}

    return app


def test_local_sqlite_route_harness_restores_override_and_releases_file(tmp_path) -> None:
    app = _app()
    db_path = tmp_path / "route.sqlite3"

    with LocalSQLiteRouteHarness(
        app=app,
        db_dependency=_get_db_placeholder,
        db_path=db_path,
    ) as harness:
        assert harness.client.get("/ping").json() == {"value": 1}
        assert _get_db_placeholder in app.dependency_overrides

    assert _get_db_placeholder not in app.dependency_overrides
    db_path.unlink()
    assert not db_path.exists()


def test_json_artifact_writer_roundtrips_cjk_without_literal_backslash_n(tmp_path) -> None:
    output = tmp_path / "artifact.json"
    payload = {"status": "generated", "text": "珍珠奶茶", "nested": {"ok": True}}

    write_json_artifact(output, payload)

    raw = output.read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\\n")
    assert json.loads(raw.decode("utf-8")) == payload
    assert read_json_artifact(output) == payload
