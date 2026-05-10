from __future__ import annotations

import json
import sys

from fastapi import Depends, FastAPI
import pytest
from sqlalchemy import text

from app.shared.infra.json_artifacts import (
    artifact_path_exists,
    read_json_artifact,
    write_json_artifact,
)
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


def test_json_artifact_helpers_roundtrip_windows_long_paths(tmp_path) -> None:
    if sys.platform != "win32":
        pytest.skip("Windows MAX_PATH regression guard")

    output_dir = tmp_path
    while len(str(output_dir / "artifact.json")) <= 260:
        output_dir = output_dir / "segment1234567890"

    output = output_dir / "artifact.json"
    payload = {"status": "generated", "path_length": len(str(output))}

    write_json_artifact(output, payload)

    assert read_json_artifact(output) == payload


def test_json_artifact_path_exists_handles_windows_long_paths(tmp_path) -> None:
    if sys.platform != "win32":
        pytest.skip("Windows MAX_PATH regression guard")

    output_dir = tmp_path
    while len(str(output_dir / "artifact.json")) <= 260:
        output_dir = output_dir / "segment1234567890"

    output = output_dir / "artifact.json"
    write_json_artifact(output, {"status": "generated"})

    assert artifact_path_exists(output) is True
    assert artifact_path_exists(output_dir / "missing.json") is False
