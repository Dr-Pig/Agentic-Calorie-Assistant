from __future__ import annotations

from pathlib import Path

from app.nutrition.application.retrieval_intent import (
    build_diagnostic_retrieval_intent,
    build_retrieval_intent,
)
from app.nutrition.application.retrieval_intent_api_boundary import (
    build_retrieval_intent_api_boundary_artifact,
)


def test_diagnostic_retrieval_intent_builder_is_explicit_alias_for_backward_compatibility() -> None:
    explicit = build_diagnostic_retrieval_intent("珍珠奶茶")
    legacy = build_retrieval_intent("珍珠奶茶")

    assert explicit == legacy
    assert explicit.base_dish == "珍珠奶茶"
    assert explicit.retrieval_goal == "generic_anchor_lookup"


def test_retrieval_intent_api_boundary_reports_no_ambiguous_runtime_call_sites() -> None:
    artifact = build_retrieval_intent_api_boundary_artifact()

    assert artifact["artifact_type"] == "accurate_intake_retrieval_intent_api_boundary_v1"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["ambiguous_builder_call_file_count"] == 0
    assert artifact["summary"]["unexpected_raw_hint_call_file_count"] == 0
    assert artifact["summary"]["runtime_boundary_guard_present"] is True
    assert artifact["ambiguous_builder_audit"]["observed_call_files"] == []


def test_retrieval_intent_api_boundary_blocks_unexpected_ambiguous_builder_runtime_usage() -> None:
    artifact = build_retrieval_intent_api_boundary_artifact(
        ambiguous_builder_call_files=(
            "app/runtime/bad_runtime_path.py",
        )
    )

    assert artifact["status"] == "blocked"
    assert "unexpected_ambiguous_retrieval_builder_call:app/runtime/bad_runtime_path.py" in artifact["blockers"]


def test_retrieval_intent_api_boundary_blocks_unexpected_raw_hint_call_sites() -> None:
    artifact = build_retrieval_intent_api_boundary_artifact(
        raw_hint_call_files=(
            "app/nutrition/application/exact_brand_web_canary.py",
            "app/runtime/bad_runtime_path.py",
        )
    )

    assert artifact["status"] == "blocked"
    assert "unexpected_raw_hint_builder_call:app/runtime/bad_runtime_path.py" in artifact["blockers"]


def test_retrieval_intent_api_boundary_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_retrieval_intent_api_boundary import main

    output = tmp_path / "retrieval_intent_api_boundary.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_retrieval_intent_api_boundary_v1"
    assert artifact["status"] == "pass"
