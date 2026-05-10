from __future__ import annotations

from pathlib import Path

from tests.long_term_context_shadow_fixture import _fixture_payload


def _reviewed_fixture() -> dict:
    fixture = _fixture_payload()
    fixture["review_actions"] = [
        {
            "action_id": "accept-golden-order",
            "target_candidate_ids": ["golden-order-morning-bar-oatmeal-latte"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Useful repeat order for recommendation shadow tests.",
        },
        {
            "action_id": "correct-golden-order",
            "target_candidate_ids": ["golden-order-morning-bar-oatmeal-latte"],
            "action_type": "correct_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Correction from review feedback.",
            "corrected_memory_text": (
                "User often chooses Morning Bar oatmeal; latte should be optional."
            ),
        },
        {
            "action_id": "accept-negative-preference",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Explicit dislike is useful for recommendation suppression.",
        },
        {
            "action_id": "delete-bias-pattern",
            "target_candidate_ids": ["intake-estimation-bias-likely-underestimate"],
            "action_type": "delete_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Reviewer requested lab deletion after poor attribution.",
        },
    ]
    return fixture


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "fixture-user",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
        "run_id": "review-store-run-001",
    }
    scope.update(overrides)
    return scope


def _review_loop_artifact(scope_keys: dict[str, str] | None = None) -> dict:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_reviewed_fixture())[
        "memory_lab_review_loop_state"
    ]
    scope = dict(scope_keys or _scope())
    for record in artifact["lab_memory_records"]:
        record["scope_keys"] = scope
    return artifact


def test_reviewed_memory_store_persists_review_loop_records_with_audit(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    artifact = store.write_review_loop_state(_review_loop_artifact())
    records = store.list_records(_scope())

    assert artifact["artifact_type"] == "runtime_lab_reviewed_memory_store_write"
    assert artifact["status"] == "pass"
    assert artifact["stored_record_count"] == 3
    assert artifact["tombstone_record_count"] == 1
    assert artifact["lab_isolated"] is True
    assert artifact["canonical_db_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert [record["source_candidate_id"] for record in records] == [
        "golden-order-morning-bar-oatmeal-latte",
        "negative-preference-ingredient-cilantro",
        "intake-estimation-bias-likely-underestimate",
    ]

    corrected = store.read_record(
        "lab-shadow-memory-record-golden-order-morning-bar-oatmeal-latte",
        _scope(),
    )
    assert corrected["record_state"] == "corrected_shadow"
    assert corrected["store_version"] == 1
    assert corrected["memory_text"] == (
        "User often chooses Morning Bar oatmeal; latte should be optional."
    )
    assert corrected["history"][0]["review_revision"] == 2
    assert corrected["active_in_lab_context"] is True
    assert corrected["runtime_effect_allowed"] is False
    assert corrected["can_be_runtime_loaded"] is False


def test_reviewed_memory_store_preserves_versions_and_scopes(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    artifact = _review_loop_artifact()
    store.write_review_loop_state(artifact)
    record = dict(artifact["lab_memory_records"][0])
    record["revision"] = 3
    record["memory_text"] = "Reviewer revised the breakfast memory again."
    store.write_record(record)

    updated = store.read_record(record["memory_record_id"], _scope())
    history = store.record_history(record["memory_record_id"], _scope())

    assert updated["store_version"] == 2
    assert updated["memory_text"] == "Reviewer revised the breakfast memory again."
    assert [event["store_version"] for event in history] == [1, 2]
    assert [event["review_revision"] for event in history] == [2, 3]
    assert store.read_record(
        record["memory_record_id"],
        _scope(project_id="other-project"),
    ) is None


def test_reviewed_memory_store_forget_keeps_tombstone_history(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    store.write_review_loop_state(_review_loop_artifact())
    tombstone = store.forget_record(
        "lab-shadow-memory-record-negative-preference-ingredient-cilantro",
        _scope(),
        reason="reviewer_forget",
    )

    assert tombstone["record_type"] == "runtime_lab_reviewed_memory_tombstone"
    assert tombstone["deleted"] is True
    assert tombstone["memory_text"] is None
    assert store.read_record(
        "lab-shadow-memory-record-negative-preference-ingredient-cilantro",
        _scope(),
    ) is None
    assert store.record_history(
        "lab-shadow-memory-record-negative-preference-ingredient-cilantro",
        _scope(),
    )[-1] == {
        "store_version": 2,
        "action": "forget",
        "record_state": "deleted_shadow",
        "review_revision": None,
        "reason": "reviewer_forget",
    }


def test_reviewed_memory_store_blocks_scope_or_activation_drift(
    tmp_path: Path,
) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    artifact = _review_loop_artifact(scope_keys={"user_id": "fixture-user"})

    try:
        store.write_review_loop_state(artifact)
    except ValueError as exc:
        assert str(exc) == "missing_scope_keys:workspace_id,project_id,surface,run_id"
    else:
        raise AssertionError("expected missing scope rejection")

    record = _review_loop_artifact()["lab_memory_records"][0]
    record["durable_memory_written"] = True
    try:
        store.write_record(record)
    except ValueError as exc:
        assert str(exc) == "activation_flag_not_allowed:durable_memory_written"
    else:
        raise AssertionError("expected activation drift rejection")
