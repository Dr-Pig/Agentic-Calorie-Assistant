from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_accurate_intake_rt12b_live_trace_grading_extension as module  # noqa: E402


def _live_artifact(case_id: str, turns: list[dict[str, object]]) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "provider_mode": "live",
        "live_invoked": True,
        "live_llm_invoked": True,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "live_provider_used_as_truth": False,
        "runtime_web_activation_approved": False,
        "cases": [
            {
                "case_id": case_id,
                "case_contract_status": "strict_pass",
                "verdict": "pass",
                "failure_layer": None,
                "turns": turns,
            }
        ],
    }


def _turn(turn: int, *, action: str | None, tools: list[str]) -> dict[str, object]:
    return {
        "turn": turn,
        "manager_final_action": action,
        "runtime_error": None,
        "manager_rounds": [
            {"decision": {"tool_calls": [{"name": tool_name} for tool_name in tools]}}
        ],
    }


def _exact_artifact() -> dict[str, object]:
    return _live_artifact(
        "exact_item_official_label",
        [_turn(1, action="commit", tools=["estimate_nutrition"])],
    )


def _bubble_artifact() -> dict[str, object]:
    return _live_artifact(
        "bubble_milk_tea_refinement",
        [
            _turn(1, action="commit", tools=["estimate_nutrition"]),
            _turn(2, action="commit", tools=["estimate_nutrition"]),
        ],
    )


def _luwei_artifact() -> dict[str, object]:
    return _live_artifact(
        "luwei_bare_to_listed_basket",
        [
            _turn(1, action="ask_followup", tools=[]),
            _turn(2, action="commit", tools=["estimate_nutrition"]),
        ],
    )


def _no_plan_artifact() -> dict[str, object]:
    return _live_artifact(
        "no_plan_consumed_without_budget_target",
        [_turn(1, action=None, tools=[])],
    )


def _correction_artifact() -> dict[str, object]:
    return _live_artifact(
        "chinese_chicken_rice_correction_removal_debug",
        [
            _turn(1, action="commit", tools=["estimate_nutrition"]),
            _turn(2, action="correction_applied", tools=["estimate_nutrition"]),
            _turn(3, action="correction_applied", tools=["resolve_correction_target"]),
            {
                "turn": 4,
                "manager_final_action": None,
                "runtime_error": None,
                "manager_rounds": [],
            },
        ],
    )


def _rt11c_artifact() -> dict[str, object]:
    return {
        "target_manager_runtime_gate": "rt11c_renderer_input_basis_evidence_pack",
        "status": "pass",
        "appshell_contract_boundary": {
            "renderer_input_basis_contract_green": True,
            "frontend_semantic_owner": False,
        },
    }


def _build(**overrides: dict[str, object]) -> dict[str, object]:
    payloads = {
        "exact_item_artifact": _exact_artifact(),
        "bubble_artifact": _bubble_artifact(),
        "luwei_artifact": _luwei_artifact(),
        "no_plan_artifact": _no_plan_artifact(),
        "correction_artifact": _correction_artifact(),
        "rt11c_artifact": _rt11c_artifact(),
    }
    payloads.update(overrides)
    return module.build_rt12b_live_trace_grading_extension(**payloads)


def test_rt12b_live_trace_grading_extension_passes() -> None:
    artifact = _build()

    assert artifact["artifact_type"] == "accurate_intake_rt12b_live_trace_grading_extension"
    assert artifact["target_manager_runtime_gate"] == "rt12b_live_trace_grading_extension"
    assert artifact["status"] == "pass"
    assert artifact["grade_layers"] == [
        "live_trace_shape",
        "live_tool_choice",
        "live_final_action",
        "renderer_input_basis_dependency",
    ]
    assert artifact["summary"]["argument_accuracy_not_locked_in_v1"] is True


def test_rt12b_blocks_missing_live_manager_rounds() -> None:
    bad = _exact_artifact()
    bad["cases"][0]["turns"][0]["manager_rounds"] = []

    artifact = _build(exact_item_artifact=bad)

    assert artifact["status"] == "fail"
    assert "exact_item_official_label.turn1.manager_rounds_missing" in artifact["blockers"]


def test_rt12b_blocks_wrong_live_tool_choice() -> None:
    bad = _correction_artifact()
    bad["cases"][0]["turns"][2]["manager_rounds"][0]["decision"]["tool_calls"] = [
        {"name": "estimate_nutrition"}
    ]

    artifact = _build(correction_artifact=bad)

    assert artifact["status"] == "fail"
    assert any("tool_choice_mismatch" in blocker for blocker in artifact["blockers"])


def test_rt12b_blocks_missing_renderer_basis_dependency() -> None:
    bad = _rt11c_artifact()
    bad["appshell_contract_boundary"]["renderer_input_basis_contract_green"] = False

    artifact = _build(rt11c_artifact=bad)

    assert artifact["status"] == "fail"
    assert "rt11c_renderer_basis.contract_not_green" in artifact["blockers"]


def test_rt12b_cli_writes_artifact(tmp_path: Path) -> None:
    files = {
        "exact": tmp_path / "exact.json",
        "bubble": tmp_path / "bubble.json",
        "luwei": tmp_path / "luwei.json",
        "no_plan": tmp_path / "no_plan.json",
        "correction": tmp_path / "correction.json",
        "rt11c": tmp_path / "rt11c.json",
    }
    payloads = {
        "exact": _exact_artifact(),
        "bubble": _bubble_artifact(),
        "luwei": _luwei_artifact(),
        "no_plan": _no_plan_artifact(),
        "correction": _correction_artifact(),
        "rt11c": _rt11c_artifact(),
    }
    for key, path in files.items():
        path.write_text(json.dumps(payloads[key], ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "rt12b.json"

    rc = module.main(
        [
            "--exact-item-artifact",
            str(files["exact"]),
            "--bubble-artifact",
            str(files["bubble"]),
            "--luwei-artifact",
            str(files["luwei"]),
            "--no-plan-artifact",
            str(files["no_plan"]),
            "--correction-artifact",
            str(files["correction"]),
            "--rt11c-artifact",
            str(files["rt11c"]),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
