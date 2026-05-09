from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _candidate(candidate_id: str = "candidate-001") -> dict:
    return {
        "candidate_id": candidate_id,
        "candidate_type": "preference",
        "scope_keys": _scope(),
        "source_trace_ids": ["trace-001"],
        "source_object_refs": ["message:preference-001"],
        "review_status": "pending",
        "retention_posture": "runtime_lab_shadow_only",
        "payload": {"candidate_type": "preference", "promotion_allowed_now": False},
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
        "run_id": "store-run-001",
    }
    scope.update(overrides)
    return scope


def _candidate_trace() -> dict:
    return {
        "request_id": "rt-lab-store-001",
        "trace_meta": {
            "request_id": "rt-lab-store-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "store-run-001",
        },
        "request": {"user_id": "user-a", "text": "structured dogfood replay"},
        "manager_final_decision": {"workflow_effect": "commit_meal_log"},
        "memory_lab_candidate_signal": {
            "candidate_type": "preference",
            "manager_decision_field": "memory_candidate_requested",
            "source_refs": ["message:dogfood-store-001"],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["explicit_user_preference"],
        },
    }


def test_lab_store_scoped_write_read_list_and_history(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    written = store.write_candidate(_candidate())
    read_back = store.read_candidate("candidate-001", _scope())
    listed = store.list_candidates(_scope())
    history = store.candidate_history("candidate-001", _scope())

    assert written["record_type"] == "runtime_lab_memory_candidate_record"
    assert written["version"] == 1
    assert read_back["candidate"]["candidate_id"] == "candidate-001"
    assert [record["candidate_id"] for record in listed] == ["candidate-001"]
    assert history == [
        {
            "version": 1,
            "action": "write",
            "review_status": "pending",
            "source_object_refs": ["message:preference-001"],
        }
    ]
    assert written["lab_isolated"] is True
    assert written["durable_product_memory_written"] is False
    assert written["canonical_db_changed"] is False


def test_lab_store_cross_scope_isolation(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    store.write_candidate(_candidate())

    assert store.read_candidate("candidate-001", _scope(user_id="user-b")) is None
    assert store.list_candidates(_scope(project_id="other-project")) == []
    assert store.candidate_history("candidate-001", _scope(run_id="other-run")) == []


def test_lab_store_update_preserves_version_history(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    store.write_candidate(_candidate())
    updated = _candidate()
    updated["review_status"] = "accepted"
    updated["source_object_refs"] = ["message:preference-001", "message:confirm-001"]

    written = store.write_candidate(updated)
    history = store.candidate_history("candidate-001", _scope())

    assert written["version"] == 2
    assert written["candidate"]["review_status"] == "accepted"
    assert [event["version"] for event in history] == [1, 2]
    assert history[-1]["source_object_refs"] == [
        "message:preference-001",
        "message:confirm-001",
    ]


def test_lab_store_forget_deletes_candidate_payload_but_keeps_tombstone_history(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    store.write_candidate(_candidate())
    tombstone = store.forget_candidate("candidate-001", _scope(), reason="user_forget")

    assert tombstone["record_type"] == "runtime_lab_memory_candidate_tombstone"
    assert tombstone["deleted"] is True
    assert tombstone["candidate"] is None
    assert store.read_candidate("candidate-001", _scope()) is None
    assert store.list_candidates(_scope()) == []
    assert store.candidate_history("candidate-001", _scope())[-1] == {
        "version": 2,
        "action": "forget",
        "review_status": "deleted",
        "source_object_refs": [],
        "reason": "user_forget",
    }


def test_lab_store_rejects_missing_scope(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    candidate = _candidate()
    candidate["scope_keys"].pop("project_id")

    try:
        store.write_candidate(candidate)
    except ValueError as exc:
        assert str(exc) == "missing_scope_keys:project_id"
    else:
        raise AssertionError("expected missing scope rejection")


def test_lab_store_runner_writes_only_to_isolated_store(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "store_artifact.json"
    store_root = tmp_path / "runtime_lab_store"
    trace_path.write_text(json.dumps(_candidate_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_store_replay.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "runtime_lab_memory_store_replay"
    assert artifact["stored_candidate_count"] == 1
    assert artifact["lab_isolated"] is True
    assert artifact["canonical_db_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert list(store_root.rglob("*.json"))
    assert not list(ROOT.glob("alembic/versions/*runtime_lab_memory*"))
