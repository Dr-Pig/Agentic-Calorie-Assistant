from __future__ import annotations

import json
from pathlib import Path

from tests.test_runtime_lab_reviewed_memory_store import _review_loop_artifact, _scope


def test_reviewed_memory_retrieval_uses_persisted_records(tmp_path: Path) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_retrieval import (
        build_shadow_memory_context_pack_from_reviewed_store,
    )
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    store.write_review_loop_state(_review_loop_artifact())

    pack = build_shadow_memory_context_pack_from_reviewed_store(
        store,
        _scope(),
        token_budget=120,
    )

    assert pack["artifact_type"] == "shadow_memory_context_pack"
    assert pack["source_store_type"] == "runtime_lab_reviewed_memory_store"
    assert pack["selected_candidate_ids"] == [
        "golden-order-morning-bar-oatmeal-latte",
        "negative-preference-ingredient-cilantro",
    ]
    assert pack["negative_preference_blockers"] == [
        "negative-preference-ingredient-cilantro"
    ]
    assert pack["reviewed_memory_store_used"] is True
    assert pack["manager_context_packet_changed"] is False
    assert pack["manager_context_injected"] is False
    assert pack["runtime_effect_allowed"] is False


def test_reviewed_memory_retrieval_omits_inactive_or_cross_scope_records(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_retrieval import (
        build_shadow_memory_context_pack_from_reviewed_store,
    )
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    store.write_review_loop_state(_review_loop_artifact())
    cross_scope = _review_loop_artifact(_scope(project_id="other-project"))
    store.write_review_loop_state(cross_scope)

    pack = build_shadow_memory_context_pack_from_reviewed_store(
        store,
        _scope(),
        token_budget=120,
    )

    omissions = {item["candidate_id"]: item["reason"] for item in pack["omission_trace"]}
    assert omissions["intake-estimation-bias-likely-underestimate"] == (
        "deleted_by_reviewer"
    )
    assert "other-project" not in json.dumps(pack, ensure_ascii=False)


def test_reviewed_memory_retrieval_preserves_summary_first_no_raw_audit_dump(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_retrieval import (
        build_shadow_memory_context_pack_from_reviewed_store,
    )
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    artifact = _review_loop_artifact()
    artifact["lab_memory_records"][0]["audit_log"].append(
        {"raw_transcript": "RAW REVIEW TRACE MUST NOT LEAK"}
    )
    store.write_review_loop_state(artifact)

    pack = build_shadow_memory_context_pack_from_reviewed_store(
        store,
        _scope(),
        token_budget=120,
    )
    serialized = json.dumps(pack, ensure_ascii=False)

    assert pack["entries"][0]["summary"] == (
        "golden_order: User often chooses Morning Bar oatmeal; latte should be optional."
    )
    assert "RAW REVIEW TRACE MUST NOT LEAK" not in serialized
    assert "audit_log" not in serialized


def test_reviewed_memory_retrieval_keeps_existing_token_budget_gate(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_retrieval import (
        build_shadow_memory_context_pack_from_reviewed_store,
    )
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    store.write_review_loop_state(_review_loop_artifact())

    pack = build_shadow_memory_context_pack_from_reviewed_store(
        store,
        _scope(),
        token_budget=4,
    )

    assert pack["selected_candidate_ids"] == []
    assert pack["token_budget_retry_expansion_used"] is False
    assert pack["omission_trace"][0] == {
        "candidate_id": "golden-order-morning-bar-oatmeal-latte",
        "reason": "token_budget_exceeded",
    }
