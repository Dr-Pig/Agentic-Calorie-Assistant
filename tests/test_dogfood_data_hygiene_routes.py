from __future__ import annotations

import secrets
import tempfile
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.composition import local_data_hygiene_routes
from app.database import get_db
from app.models import Base
from app.routes import router


def _allowed_generated_dir(tmp_path: Path, name: str) -> Path:
    return Path(tempfile.gettempdir()) / "accurate-intake-data-hygiene-tests" / tmp_path.name / name


def _client_with_db(
    *,
    db_path: Path,
    monkeypatch,
    backup_dir: Path,
    export_dir: Path,
) -> tuple[TestClient, str]:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_BACKUP_DIR", backup_dir, raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_EXPORT_DIR", export_dir, raising=False)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), token


def test_local_data_hygiene_route_summarizes_browser_export_boundary(monkeypatch, tmp_path: Path) -> None:
    client, token = _client_with_db(
        db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
        monkeypatch=monkeypatch,
        backup_dir=_allowed_generated_dir(tmp_path, "backups"),
        export_dir=_allowed_generated_dir(tmp_path, "exports"),
    )

    response = client.get("/accurate-intake/local-data-hygiene", headers={"X-Local-Debug-Token": token})

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_type"] == "accurate_intake_local_operator_data_hygiene_bundle"
    assert payload["status"] == "local_operator_data_hygiene_ready"
    assert payload["local_only"] is True
    assert payload["contains_personal_diet_logs"] is True
    assert payload["do_not_commit"] is True
    assert payload["writes_performed"] is False
    assert payload["import_allowed"] is False
    assert payload["backup_required_before_reset"] is True
    assert payload["operation_previews"]["backup"]["would_write_copy"] is True
    assert payload["operation_previews"]["export"]["would_write_copy"] is True
    assert payload["fooddb_truth_updated"] is False
    assert payload["production_db_used"] is False
    assert payload["product_readiness_claimed"] is False
    assert payload["private_self_use_approved"] is False


def test_local_data_hygiene_backup_and_export_routes_copy_only_local_db(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client, token = _client_with_db(
        db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
        monkeypatch=monkeypatch,
        backup_dir=_allowed_generated_dir(tmp_path, "backups"),
        export_dir=_allowed_generated_dir(tmp_path, "exports"),
    )

    backup_response = client.post(
        "/accurate-intake/local-data-hygiene/backup",
        headers={"X-Local-Debug-Token": token},
        json={"label": "browser"},
    )
    export_response = client.post(
        "/accurate-intake/local-data-hygiene/export",
        headers={"X-Local-Debug-Token": token},
        json={"label": "browser"},
    )

    assert backup_response.status_code == 200
    assert export_response.status_code == 200
    backup = backup_response.json()
    export = export_response.json()
    assert backup["status"] == "pass"
    assert export["status"] == "pass"
    assert backup["local_only"] is True
    assert export["local_only"] is True
    assert backup["do_not_commit"] is True
    assert export["do_not_commit"] is True
    assert backup["production_db_used"] is False
    assert export["production_db_used"] is False
    assert backup["fooddb_truth_updated"] is False
    assert export["fooddb_truth_updated"] is False
    assert Path(backup["backup_path"]).exists()
    assert Path(export["export_path"]).exists()
    assert Path(export["manifest_path"]).exists()


def test_local_data_export_preserves_feedback_and_review_sidecars(
    monkeypatch,
    tmp_path: Path,
) -> None:
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    feedback_jsonl = feedback_dir / "accurate_intake_dogfood_feedback.jsonl"
    feedback_jsonl.write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_dogfood_feedback_record",
                "feedback_id": "feedback-export-1",
                "category": "latency",
                "feedback_text": "slow turn",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    review_queue_path = tmp_path / "review_queue.json"
    review_queue_path.write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_dogfood_review_queue",
                "feedback_triage_record_count": 1,
                "review_candidate_count": 0,
                "desktop_feedback_records": [{"feedback_id": "feedback-export-1"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_FEEDBACK_DIR", feedback_dir, raising=False)
    monkeypatch.setattr(
        local_data_hygiene_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        review_queue_path,
        raising=False,
    )
    client, token = _client_with_db(
        db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
        monkeypatch=monkeypatch,
        backup_dir=_allowed_generated_dir(tmp_path, "backups"),
        export_dir=_allowed_generated_dir(tmp_path, "exports"),
    )

    response = client.post(
        "/accurate-intake/local-data-hygiene/export",
        headers={"X-Local-Debug-Token": token},
        json={"label": "browser"},
    )

    assert response.status_code == 200
    payload = response.json()
    sidecars = payload["sidecar_evidence"]
    assert sidecars["feedback_jsonl"]["exists"] is True
    assert sidecars["feedback_jsonl"]["record_count"] == 1
    assert sidecars["feedback_jsonl"]["copied"] is True
    assert Path(sidecars["feedback_jsonl"]["copy_path"]).exists()
    assert sidecars["review_queue"]["exists"] is True
    assert sidecars["review_queue"]["feedback_triage_record_count"] == 1
    assert sidecars["review_queue"]["copied"] is True
    assert Path(sidecars["review_queue"]["copy_path"]).exists()
    assert payload["sidecar_evidence_included"] is True
    assert payload["sidecar_evidence_can_create_product_truth"] is False
    assert payload["sidecar_evidence_can_create_fooddb_truth"] is False
    assert payload["sidecar_evidence_can_create_eval_truth"] is False

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["sidecar_evidence"]["feedback_jsonl"]["record_count"] == 1
    assert manifest["sidecar_evidence"]["review_queue"]["feedback_triage_record_count"] == 1


def test_local_data_hygiene_has_no_reset_or_import_write_route(monkeypatch, tmp_path: Path) -> None:
    client, token = _client_with_db(
        db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
        monkeypatch=monkeypatch,
        backup_dir=_allowed_generated_dir(tmp_path, "backups"),
        export_dir=_allowed_generated_dir(tmp_path, "exports"),
    )

    reset_response = client.post(
        "/accurate-intake/local-data-hygiene/reset",
        headers={"X-Local-Debug-Token": token},
        json={},
    )
    import_response = client.post(
        "/accurate-intake/local-data-hygiene/import",
        headers={"X-Local-Debug-Token": token},
        json={},
    )

    assert reset_response.status_code == 404
    assert import_response.status_code == 404
