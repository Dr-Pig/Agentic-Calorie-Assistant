from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_pl_ce_reviewer_cockpit as module
from app.composition.accurate_intake_pl_ce_reviewer_cockpit import (
    build_pl_ce_reviewer_cockpit_artifact,
)


REQUIRED_INPUTS = [
    "product_pages_ui_review_bundle",
    "session_context_carryover_qa_bundle",
    "contextual_interaction_matrix",
    "pl_ce_local_mvp_candidate_bundle",
]


def _artifact(artifact_type: str, status: str, **extra: object) -> dict[str, object]:
    return {
        "artifact_type": artifact_type,
        "status": status,
        "blockers": [],
        **extra,
    }


def _inputs() -> dict[str, dict[str, object]]:
    return {
        "product_pages_ui_review_bundle": _artifact(
            "accurate_intake_product_pages_ui_review_bundle",
            "product_pages_ui_review_ready_for_human_review",
            browser_executed=True,
            frontend_render_only=True,
            frontend_semantic_owner=False,
        ),
        "session_context_carryover_qa_bundle": _artifact(
            "accurate_intake_session_context_carryover_qa_bundle",
            "session_context_carryover_qa_ready_for_human_review",
            pending_followup_carryover_checked=True,
            target_candidate_context_checked=True,
            manager_context_packet_schema_changed=False,
        ),
        "contextual_interaction_matrix": _artifact(
            "accurate_intake_contextual_interaction_matrix",
            "pass",
            deterministic_selected_intent=False,
            deterministic_selected_target=False,
            frontend_semantic_owner=False,
            manager_fixture_semantic_source_used=True,
            summary={
                "interaction_count": 11,
                "ambiguity_preserved_interactions": 2,
                "target_candidate_interactions": 5,
            },
        ),
        "pl_ce_local_mvp_candidate_bundle": _artifact(
            "accurate_intake_pl_ce_local_mvp_candidate_bundle",
            "pl_ce_local_mvp_candidate_ready_for_human_review",
            ready_for_live_diagnostic_decision=False,
            ready_for_fdb_integration=False,
            real_fooddb_pass_claimed=False,
            private_self_use_approved=False,
        ),
    }


def test_pl_ce_reviewer_cockpit_aggregates_review_ready_inputs() -> None:
    artifact = build_pl_ce_reviewer_cockpit_artifact(_inputs())

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_reviewer_cockpit"
    assert artifact["status"] == "pl_ce_reviewer_cockpit_ready_for_human_review"
    assert artifact["required_inputs"] == REQUIRED_INPUTS
    assert artifact["review_decision_scope"] == "proceed_narrow_or_stop"
    assert artifact["browser_execution_seen"] is True
    assert artifact["contextual_interaction_matrix_seen"] is True
    assert artifact["session_context_carryover_seen"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_truth_changed"] is False


def test_pl_ce_reviewer_cockpit_blocks_missing_context_matrix() -> None:
    inputs = _inputs()
    inputs.pop("contextual_interaction_matrix")

    artifact = build_pl_ce_reviewer_cockpit_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "contextual_interaction_matrix.missing" in artifact["blockers"]


def test_pl_ce_reviewer_cockpit_blocks_readiness_or_truth_claims() -> None:
    inputs = _inputs()
    inputs["pl_ce_local_mvp_candidate_bundle"]["ready_for_live_diagnostic_decision"] = True
    inputs["contextual_interaction_matrix"]["frontend_semantic_owner"] = True

    artifact = build_pl_ce_reviewer_cockpit_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "pl_ce_local_mvp_candidate_bundle.ready_for_live_diagnostic_decision" in artifact["blockers"]
    assert "contextual_interaction_matrix.frontend_semantic_owner" in artifact["blockers"]


def test_pl_ce_reviewer_cockpit_blocks_unexpected_input_groups() -> None:
    inputs = _inputs()
    inputs["live_probe"] = {
        "artifact_type": "unexpected_live_probe",
        "status": "pass",
        "live_llm_invoked": True,
    }

    artifact = build_pl_ce_reviewer_cockpit_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "unexpected_input:live_probe" in artifact["blockers"]


def test_pl_ce_reviewer_cockpit_blocks_unexpected_status_or_type() -> None:
    inputs = _inputs()
    inputs["session_context_carryover_qa_bundle"]["status"] = "pass"
    inputs["product_pages_ui_review_bundle"]["artifact_type"] = "wrong"

    artifact = build_pl_ce_reviewer_cockpit_artifact(inputs)

    assert "session_context_carryover_qa_bundle.unexpected_status:pass" in artifact["blockers"]
    assert "product_pages_ui_review_bundle.unexpected_artifact_type:wrong" in artifact["blockers"]


def test_pl_ce_reviewer_cockpit_cli_blocks_unexpected_input_group(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import write_json_artifact
    from scripts.build_accurate_intake_pl_ce_reviewer_cockpit import main

    paths: list[str] = []
    for key, payload in _inputs().items():
        path = tmp_path / f"{key}.json"
        write_json_artifact(path, payload)
        paths.append(f"{key}={path}")
    unexpected_path = tmp_path / "live_probe.json"
    write_json_artifact(
        unexpected_path,
        {
            "artifact_type": "unexpected_live_probe",
            "status": "pass",
            "live_llm_invoked": True,
        },
    )
    output_path = tmp_path / "cockpit.json"

    exit_code = main(
        [
            "--output",
            str(output_path),
            *sum([["--artifact", value] for value in paths], []),
            "--artifact",
            f"live_probe={unexpected_path}",
        ]
    )

    assert exit_code == 1
    artifact = json.loads(output_path.read_text(encoding="utf-8-sig"))
    assert "unexpected_input:live_probe" in artifact["blockers"]


def test_pl_ce_reviewer_cockpit_cli_writes_artifact(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import write_json_artifact
    from scripts.build_accurate_intake_pl_ce_reviewer_cockpit import main

    paths: list[str] = []
    for key, payload in _inputs().items():
        path = tmp_path / f"{key}.json"
        write_json_artifact(path, payload)
        paths.append(f"{key}={path}")
    output_path = tmp_path / "cockpit.json"

    exit_code = main(["--output", str(output_path), *sum([["--artifact", value] for value in paths], [])])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8-sig"))
    assert artifact["status"] == "pl_ce_reviewer_cockpit_ready_for_human_review"


def test_pl_ce_reviewer_cockpit_stays_out_of_forbidden_boundaries() -> None:
    for path in [
        Path("app/composition/accurate_intake_pl_ce_reviewer_cockpit.py"),
        Path("scripts/build_accurate_intake_pl_ce_reviewer_cockpit.py"),
    ]:
        source = path.read_text(encoding="utf-8")
        for fragment in [
            "NutritionEvidenceStorePort",
            "FoodEvidenceRecord",
            "PacketReadyAnchor",
            "Tavily",
            "Kimi",
            "GrokFast",
            "manager_context_packet_schema_changed = True",
            "ready_for_live_diagnostic_decision = True",
            "fooddb_truth_changed = True",
        ]:
            assert fragment not in source
