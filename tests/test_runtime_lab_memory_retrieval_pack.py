from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
        "run_id": "retrieval-run-001",
    }
    scope.update(overrides)
    return scope


def _candidate(candidate_id: str, candidate_type: str, **payload: object) -> dict:
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "scope_keys": _scope(),
        "source_trace_ids": [f"trace:{candidate_id}"],
        "source_object_refs": [f"message:{candidate_id}"],
        "review_status": "accepted",
        "retention_posture": "runtime_lab_shadow_only",
        "payload": payload,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _candidate_trace() -> dict:
    return {
        "request_id": "rt-lab-retrieval-001",
        "trace_meta": {
            "request_id": "rt-lab-retrieval-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "retrieval-run-001",
        },
        "request": {
            "user_id": "user-a",
            "text": "raw dogfood text must not appear in context pack",
        },
        "manager_final_decision": {"workflow_effect": "commit_meal_log"},
        "memory_lab_candidate_signal": {
            "candidate_type": "preference",
            "manager_decision_field": "memory_candidate_requested",
            "source_refs": ["message:dogfood-retrieval-001"],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["explicit_user_preference"],
            "summary": "prefers lighter lunch suggestions",
        },
    }


def test_retrieval_pack_selects_exact_scope_and_omits_cross_scope(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_retrieval import (
        build_shadow_memory_context_pack,
    )
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    store.write_candidate(_candidate("pref-1", "preference", summary="prefers oats"))
    cross_scope = _candidate("pref-2", "preference", summary="cross scope")
    cross_scope["scope_keys"] = _scope(project_id="other-project")
    store.write_candidate(cross_scope)

    pack = build_shadow_memory_context_pack(store, _scope(), token_budget=120)

    assert pack["artifact_type"] == "shadow_memory_context_pack"
    assert pack["selected_candidate_ids"] == ["pref-1"]
    assert pack["omission_trace"] == []
    assert pack["manager_context_packet_changed"] is False
    assert pack["runtime_effect_allowed"] is False


def test_retrieval_pack_applies_stale_omission_and_negative_blocker(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_retrieval import (
        build_shadow_memory_context_pack,
    )
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    store.write_candidate(_candidate("pref-1", "preference", summary="fresh"))
    store.write_candidate(
        _candidate(
            "neg-1",
            "negative_preference",
            summary="avoid sugary drinks",
            blocks_candidate_types=["preference"],
        )
    )
    store.write_candidate(
        _candidate(
            "pattern-1",
            "pattern",
            summary="stale drink pattern",
            freshness_posture="stale",
        )
    )

    pack = build_shadow_memory_context_pack(store, _scope(), token_budget=120)

    assert pack["selected_candidate_ids"] == ["neg-1"]
    omissions = {item["candidate_id"]: item["reason"] for item in pack["omission_trace"]}
    assert omissions["pref-1"] == "blocked_by_negative_preference"
    assert omissions["pattern-1"] == "stale_or_expired"
    assert pack["negative_preference_blockers"] == ["neg-1"]


def test_retrieval_pack_enforces_token_budget_without_retry_expansion(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_retrieval import (
        build_shadow_memory_context_pack,
    )
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    store.write_candidate(_candidate("pref-1", "preference", summary="one two three"))
    store.write_candidate(_candidate("pref-2", "preference", summary="four five six"))

    pack = build_shadow_memory_context_pack(store, _scope(), token_budget=4)

    assert pack["selected_candidate_ids"] == ["pref-1"]
    assert pack["token_budget"] == 4
    assert pack["token_budget_retry_expansion_used"] is False
    assert pack["omission_trace"][-1] == {
        "candidate_id": "pref-2",
        "reason": "token_budget_exceeded",
    }


def test_retrieval_pack_is_summary_first_and_does_not_dump_raw_transcript(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_retrieval import (
        build_shadow_memory_context_pack,
    )
    from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore

    store = RuntimeLabMemoryStore(tmp_path)
    candidate = _candidate("pref-1", "preference", summary="prefers tofu")
    candidate["payload"]["raw_user_input"] = "RAW TRANSCRIPT SHOULD NOT LEAK"
    store.write_candidate(candidate)

    pack = build_shadow_memory_context_pack(store, _scope(), token_budget=120)
    serialized = json.dumps(pack, ensure_ascii=False)

    assert "RAW TRANSCRIPT SHOULD NOT LEAK" not in serialized
    assert pack["entries"][0]["summary"] == "preference: prefers tofu"
    assert "sanitized_source_trace" not in serialized


def test_retrieval_runner_builds_pack_without_manager_injection(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "context_pack.json"
    store_root = tmp_path / "runtime_lab_store"
    trace_path.write_text(json.dumps(_candidate_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_retrieval_pack.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
            "--token-budget",
            "120",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    pack = json.loads(output_path.read_text(encoding="utf-8"))
    assert pack["artifact_type"] == "shadow_memory_context_pack"
    assert pack["runtime_connected"] is True
    assert pack["shadow_memory_context_pack_used"] is True
    assert pack["manager_context_packet_changed"] is False
    assert pack["manager_context_injected"] is False
    assert "raw dogfood text" not in json.dumps(pack, ensure_ascii=False)
