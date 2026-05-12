from __future__ import annotations

import json


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }
    scope.update(overrides)
    return scope


def _record(record_id: str, **overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": record_id,
        "record_type": "confirmed_preference",
        "family": "diet_product",
        "status": "confirmed",
        "summary": f"{record_id} summary",
        "polarity": "positive",
        "strength": "boost",
        "scope_keys": _scope(),
        "source_refs": [f"source:{record_id}"],
        "consumers": ["recommendation_shadow"],
        "history": [f"feedback:{record_id}"],
        "subject_keys": [record_id],
    }
    record.update(overrides)
    return record


def test_context_pack_selects_confirmed_scoped_summary_records() -> None:
    from app.memory.application.memory_record_context_pack import (
        build_memory_record_context_pack,
    )

    cross_scope = _record("cross-scope", scope_keys=_scope(user_id="user-b"))
    pending = _record("pending", status="pending_review")

    pack = build_memory_record_context_pack(
        memory_records=[_record("likes-ramen"), cross_scope, pending],
        scope_keys=_scope(),
        consumer="recommendation_shadow",
        token_budget=120,
    )

    assert pack["status"] == "pass"
    assert pack["artifact_type"] == "shadow_memory_context_pack"
    assert pack["selected_record_ids"] == ["likes-ramen"]
    assert pack["entries"][0]["summary"] == "likes-ramen summary"
    assert {item["record_id"]: item["reason"] for item in pack["omission_trace"]} == {
        "cross-scope": "scope_mismatch",
        "pending": "not_confirmed",
    }
    assert pack["manager_context_packet_changed"] is False
    assert pack["manager_context_injected"] is False


def test_context_pack_includes_negative_preference_blockers_first() -> None:
    from app.memory.application.memory_record_context_pack import (
        build_memory_record_context_pack,
    )

    pack = build_memory_record_context_pack(
        memory_records=[
            _record("likes-ramen", subject_keys=["ramen"]),
            _record(
                "no-spicy",
                record_type="negative_preference",
                summary="User does not eat spicy food.",
                polarity="negative",
                strength="block",
                subject_keys=["spicy_food"],
            ),
        ],
        scope_keys=_scope(),
        consumer="recommendation_shadow",
        token_budget=120,
    )

    assert pack["selected_record_ids"] == ["no-spicy", "likes-ramen"]
    assert pack["negative_preference_blockers"] == ["no-spicy"]
    assert pack["negative_blocker_subject_keys"] == ["spicy_food"]
    assert pack["entries"][0]["polarity"] == "negative"


def test_context_pack_is_summary_first_and_omits_raw_source_fields() -> None:
    from app.memory.application.memory_record_context_pack import (
        build_memory_record_context_pack,
    )

    pack = build_memory_record_context_pack(
        memory_records=[
            _record(
                "raw-risk",
                raw_transcript="RAW TRANSCRIPT SHOULD NOT LEAK",
                evidence_text="bounded evidence must be looked up separately",
            )
        ],
        scope_keys=_scope(),
        consumer="recommendation_shadow",
        token_budget=120,
    )
    serialized = json.dumps(pack, ensure_ascii=False)

    assert "RAW TRANSCRIPT SHOULD NOT LEAK" not in serialized
    assert "bounded evidence must be looked up separately" not in serialized
    assert pack["summary_first"] is True
    assert pack["source_lookup_required_for_evidence"] is True
    assert pack["entries"][0]["source_refs"] == ["source:raw-risk"]


def test_context_pack_omits_expired_temporary_and_enforces_token_budget() -> None:
    from app.memory.application.memory_record_context_pack import (
        build_memory_record_context_pack,
    )

    pack = build_memory_record_context_pack(
        memory_records=[
            _record(
                "temp-expired",
                record_type="temporary_preference",
                summary="temporary low carb",
                validity={"valid_until": "2026-01-01"},
            ),
            _record("long", summary="one two three four five six"),
        ],
        scope_keys=_scope(),
        consumer="recommendation_shadow",
        token_budget=3,
        as_of="2026-05-12T00:00:00+08:00",
    )

    assert pack["selected_record_ids"] == []
    assert pack["token_budget_retry_expansion_used"] is False
    assert {item["record_id"]: item["reason"] for item in pack["omission_trace"]} == {
        "temp-expired": "stale_or_expired",
        "long": "token_budget_exceeded",
    }


def test_context_pack_blocks_invalid_memory_record_contract() -> None:
    from app.memory.application.memory_record_context_pack import (
        build_memory_record_context_pack,
    )

    pack = build_memory_record_context_pack(
        memory_records=[_record("bad", source_refs=[])],
        scope_keys=_scope(),
        consumer="recommendation_shadow",
        token_budget=120,
    )

    assert pack["status"] == "blocked"
    assert "bad.source_refs.missing" in pack["blockers"]
    assert pack["entries"] == []
