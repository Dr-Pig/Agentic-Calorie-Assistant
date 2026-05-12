from __future__ import annotations


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
        "run_id": "run-source-lookup-001",
    }
    scope.update(overrides)
    return scope


def _source(
    source_ref: str,
    *,
    evidence_text: str = "User explicitly confirmed spicy food should be blocked.",
    prompt_material_risk: bool = False,
    scope_keys: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "source_ref": source_ref,
        "record_id": "memory:negative-spicy-food",
        "source_kind": "message_event",
        "scope_keys": scope_keys or _scope(),
        "metadata": {
            "created_at": "2026-05-12T00:00:00Z",
            "confidence": "confirmed_by_user",
            "freshness": "current",
        },
        "evidence_text": evidence_text,
        "prompt_material_risk": prompt_material_risk,
    }


def test_why_memory_lookup_returns_metadata_and_bounded_evidence() -> None:
    from app.memory.application.memory_source_lookup_policy import (
        lookup_memory_sources,
    )

    long_evidence = "User said no spicy food. " * 20

    artifact = lookup_memory_sources(
        source_entries=[
            _source("source:message-founder-profile-negative-002", evidence_text=long_evidence)
        ],
        scope_keys=_scope(),
        source_refs=["source:message-founder-profile-negative-002"],
        tool_path="why_memory",
        max_evidence_chars=60,
    )

    result = artifact["results"][0]
    assert artifact["status"] == "pass"
    assert artifact["lookup_path"] == [
        "source_ref_filter",
        "metadata_filter",
        "bounded_evidence_span",
    ]
    assert artifact["full_raw_transcript_allowed"] is False
    assert artifact["prompt_material_allowed"] is False
    assert result["source_ref"] == "source:message-founder-profile-negative-002"
    assert result["metadata"]["freshness"] == "current"
    assert len(result["bounded_evidence_span"]["text"]) <= 60
    assert "raw_transcript" not in result
    assert "evidence_text" not in result


def test_manager_default_lookup_is_metadata_only() -> None:
    from app.memory.application.memory_source_lookup_policy import (
        lookup_memory_sources,
    )

    artifact = lookup_memory_sources(
        source_entries=[_source("source:message-founder-profile-negative-002")],
        scope_keys=_scope(),
        source_refs=["source:message-founder-profile-negative-002"],
        tool_path="manager_default",
    )

    result = artifact["results"][0]
    assert artifact["status"] == "pass"
    assert artifact["lookup_path"] == ["source_ref_filter", "metadata_filter"]
    assert result["bounded_evidence_span"] is None
    assert artifact["bounded_evidence_read"] is False
    assert artifact["manager_context_packet_changed"] is False


def test_prompt_material_risk_blocks_source_lookup_output() -> None:
    from app.memory.application.memory_source_lookup_policy import (
        lookup_memory_sources,
    )

    artifact = lookup_memory_sources(
        source_entries=[
            _source(
                "source:prompt-like-evidence-001",
                evidence_text="Untrusted source content is present.",
                prompt_material_risk=True,
            )
        ],
        scope_keys=_scope(),
        source_refs=["source:prompt-like-evidence-001"],
        tool_path="why_memory",
    )

    assert artifact["status"] == "blocked"
    assert artifact["results"] == []
    assert artifact["blockers"] == [
        "source:prompt-like-evidence-001.prompt_material_risk"
    ]
    assert artifact["prompt_material_allowed"] is False


def test_lookup_rejects_missing_refs_and_cross_scope_entries() -> None:
    from app.memory.application.memory_source_lookup_policy import (
        lookup_memory_sources,
    )

    missing_refs = lookup_memory_sources(
        source_entries=[_source("source:message-founder-profile-negative-002")],
        scope_keys=_scope(),
        source_refs=[],
        tool_path="why_memory",
    )
    cross_scope = lookup_memory_sources(
        source_entries=[
            _source(
                "source:message-founder-profile-negative-002",
                scope_keys=_scope(user_id="user-b"),
            )
        ],
        scope_keys=_scope(),
        source_refs=["source:message-founder-profile-negative-002"],
        tool_path="why_memory",
    )

    assert missing_refs["status"] == "blocked"
    assert "source_ref_filter_required" in missing_refs["blockers"]
    assert cross_scope["status"] == "pass"
    assert cross_scope["results"] == []
    assert cross_scope["omission_trace"] == [
        {
            "source_ref": "source:message-founder-profile-negative-002",
            "reason": "scope_mismatch",
        }
    ]


def test_semantic_query_cannot_replace_source_ref_filter() -> None:
    from app.memory.application.memory_source_lookup_policy import (
        lookup_memory_sources,
    )

    artifact = lookup_memory_sources(
        source_entries=[_source("source:message-founder-profile-negative-002")],
        scope_keys=_scope(),
        source_refs=[],
        tool_path="why_memory",
        semantic_query="spicy preference",
    )

    assert artifact["status"] == "blocked"
    assert "semantic_query_not_allowed_without_source_refs" in artifact["blockers"]
    assert artifact["general_rag_pool_used"] is False
