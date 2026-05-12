from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.advanced_shadow_lab.product_lab_simulated_summary import (
    build_simulated_dogfood_summary,
)
from app.shared.infra.json_artifacts import read_json_artifact


def test_memory_record_session_replay_closes_simulated_dogfood_loop(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_session import (
        run_advanced_product_lab_memory_record_session,
    )

    artifact = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path,
        session_id="memory-record-session-1",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_simulated_dogfood_summary(artifact)

    assert artifact["status"] == "pass"
    assert artifact["memory_record_session_replay_enabled"] is True
    assert artifact["lab_memory_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert artifact["memory_record_context_pack_used"] is True
    assert artifact["turn_summaries"][0]["lab_memory_selected_record_ids"] == []
    assert artifact["turn_summaries"][1]["lab_memory_selected_record_ids"] == [
        "negative-cilantro",
        "golden-breakfast-oatmeal",
    ]
    assert artifact["product_recommendation_selected_candidate_ids"] == [
        "golden-1",
        "golden-breakfast-oatmeal",
        "golden-breakfast-oatmeal",
        "golden-breakfast-oatmeal",
        "golden-breakfast-oatmeal",
    ]
    assert summary["advanced_product_lab_product_loop_closed"] is True
    assert summary["advanced_product_lab_closure_missing"] == []
    assert summary["lab_memory_store_written"] is True
    assert summary["lab_memory_context_injected"] is True
    assert summary["mainline_runtime_connected"] is False
    assert summary["durable_product_memory_written"] is False
    assert summary["canonical_product_mutation_allowed"] is False
    assert "raw_user_utterance" not in json.dumps(summary, ensure_ascii=False)

    first_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    write = first_turn["memory_record_write_artifact"]
    assert write["promoted_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert write["pending_or_rejected_signal_ids"] == []


def test_memory_record_session_replay_requires_confirmed_review_gate(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_session import (
        run_advanced_product_lab_memory_record_session,
    )

    artifact = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path,
        session_id="memory-record-session-unconfirmed",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-unconfirmed-memory",
                "post_turn_memory_signal_events": [
                    {
                        "signal_id": "unconfirmed-oatmeal",
                        "signal_type": "golden_order",
                        "summary": "Morning Bar oatmeal might be useful.",
                        "source_object_refs": ["turn:t1:user"],
                        "store_name": "Morning Bar",
                        "item_names": ["oatmeal"],
                        "estimated_kcal": 420,
                        "intended_consumers": ["recommendation"],
                    }
                ],
                "post_turn_memory_review_decisions": [
                    {
                        "candidate_id": "unconfirmed-oatmeal",
                        "decision": "promote",
                        "confirmed": False,
                    }
                ],
            },
            {"turn_id": "t2-next-turn"},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_memory_record_ids"] == []
    assert artifact["memory_record_context_pack_used"] is False
    assert artifact["turn_summaries"][1]["lab_memory_selected_record_ids"] == []
    assert artifact["product_recommendation_selected_candidate_ids"] == [
        "golden-1",
        "golden-1",
    ]

    first_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    write = first_turn["memory_record_write_artifact"]
    assert write["promoted_record_ids"] == []
    assert write["pending_or_rejected_signal_ids"] == ["unconfirmed-oatmeal"]
