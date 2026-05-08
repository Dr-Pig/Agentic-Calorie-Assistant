from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_accurate_intake_rt11c_renderer_input_basis_evidence_pack as module  # noqa: E402


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


def _turn(
    *,
    message: str,
    action: str | None,
    consumed_kcal: int | None,
    status: str = "ready",
    daily_target_kcal: int | None = 1312,
    remaining_kcal: int | None = 900,
) -> dict[str, object]:
    return {
        "turn": 1,
        "request_id": "req-1",
        "coach_message": message,
        "manager_final_action": action,
        "workflow_effect": action or "answer_only",
        "state_delta": {"canonical_commit": action in {"commit", "correction_applied"}},
        "remaining_budget": {
            "status": status,
            "daily_target_kcal": daily_target_kcal,
            "consumed_kcal": consumed_kcal,
            "remaining_kcal": remaining_kcal,
        },
        "show_macro": False,
        "macro_guard_reason": "no_macro_data",
    }


def _exact_artifact() -> dict[str, object]:
    return _live_artifact(
        "exact_item_official_label",
        [_turn(message="Logged. Sandwich 420 kcal. Remaining about 892 kcal today.", action="commit", consumed_kcal=420)],
    )


def _bubble_artifact() -> dict[str, object]:
    first = _turn(message="Logged. Bubble tea 400 kcal.", action="commit", consumed_kcal=400)
    second = _turn(message="Logged. Half sugar large bubble tea 400 kcal.", action="commit", consumed_kcal=400)
    second["turn"] = 2
    return _live_artifact("bubble_milk_tea_refinement", [first, second])


def _luwei_artifact() -> dict[str, object]:
    first = _turn(
        message="Please list the luwei items so I can estimate it.",
        action="ask_followup",
        consumed_kcal=0,
    )
    second = _turn(message="Logged. Luwei basket 400 kcal.", action="commit", consumed_kcal=400)
    second["turn"] = 2
    return _live_artifact("luwei_bare_to_listed_basket", [first, second])


def _no_plan_artifact() -> dict[str, object]:
    return _live_artifact(
        "no_plan_consumed_without_budget_target",
        [
            _turn(
                message="Onboarding is required before I can answer remaining budget.",
                action=None,
                consumed_kcal=420,
                status="onboarding_required",
                daily_target_kcal=None,
                remaining_kcal=None,
            )
        ],
    )


def _correction_artifact() -> dict[str, object]:
    first = _turn(message="Logged. Chicken rice 650 kcal.", action="commit", consumed_kcal=650)
    second = _turn(message="Updated. Chicken rice 320 kcal.", action="correction_applied", consumed_kcal=320)
    second["turn"] = 2
    third = _turn(message="Removed the selected item.", action="correction_applied", consumed_kcal=320)
    third["turn"] = 3
    fourth = _turn(message="Today consumed 320 kcal, remaining 992 kcal.", action=None, consumed_kcal=320)
    fourth["turn"] = 4
    return _live_artifact("chinese_chicken_rice_correction_removal_debug", [first, second, third, fourth])


def _rt6_artifact() -> dict[str, object]:
    return {
        "target_manager_runtime_gate": "rt6_bootstrap_no_plan_body_closure",
        "status": "pass",
        "cases": [
            {
                "case_id": "bootstrap_ready",
                "status": "pass",
                "blockers": [],
                "daily_target_kcal": 1312,
            },
            {
                "case_id": "manager_body_observation_write",
                "status": "pass",
                "blockers": [],
                "latest_weight_value": 70.0,
            },
            {
                "case_id": "weight_route_write",
                "status": "pass",
                "blockers": [],
                "latest_weight_value": 69.5,
            },
        ],
    }


def _build(**overrides: dict[str, object]) -> dict[str, object]:
    payloads = {
        "exact_item_artifact": _exact_artifact(),
        "bubble_artifact": _bubble_artifact(),
        "luwei_artifact": _luwei_artifact(),
        "no_plan_artifact": _no_plan_artifact(),
        "correction_artifact": _correction_artifact(),
        "rt6_artifact": _rt6_artifact(),
    }
    payloads.update(overrides)
    return module.build_rt11c_renderer_input_basis_evidence_pack(**payloads)


def test_rt11c_renderer_input_basis_pack_passes() -> None:
    artifact = _build()

    assert artifact["artifact_type"] == "accurate_intake_rt11c_renderer_input_basis_evidence_pack"
    assert artifact["target_manager_runtime_gate"] == "rt11c_renderer_input_basis_evidence_pack"
    assert artifact["status"] == "pass"
    assert artifact["supports_journeys"] == ["A", "B", "C", "D", "E", "G", "H", "J", "K"]
    assert artifact["appshell_contract_boundary"]["appshell_downstream_consumer_only"] is True
    assert artifact["appshell_contract_boundary"]["frontend_semantic_owner"] is False
    assert artifact["renderer_input_basis_by_surface"]["today"]["degraded_no_plan_checked"] is True


def test_rt11c_blocks_missing_runtime_renderer_fields() -> None:
    bad = _exact_artifact()
    del bad["cases"][0]["turns"][0]["coach_message"]

    artifact = _build(exact_item_artifact=bad)

    assert artifact["status"] == "fail"
    assert "exact_item_commit.renderer_basis_missing:coach_message" in artifact["blockers"]


def test_rt11c_blocks_no_plan_budget_invention() -> None:
    bad = _no_plan_artifact()
    bad["cases"][0]["turns"][0]["remaining_budget"]["daily_target_kcal"] = 1312

    artifact = _build(no_plan_artifact=bad)

    assert artifact["status"] == "fail"
    assert "no_plan.degraded_basis_claimed_daily_target" in artifact["blockers"]


def test_rt11c_blocks_missing_body_basis() -> None:
    bad = _rt6_artifact()
    bad["cases"][1]["latest_weight_value"] = None

    artifact = _build(rt6_artifact=bad)

    assert artifact["status"] == "fail"
    assert "rt6_body_basis.latest_weight_missing:manager_body_observation_write" in artifact["blockers"]


def test_rt11c_cli_writes_artifact(tmp_path: Path) -> None:
    files = {
        "exact": tmp_path / "exact.json",
        "bubble": tmp_path / "bubble.json",
        "luwei": tmp_path / "luwei.json",
        "no_plan": tmp_path / "no_plan.json",
        "correction": tmp_path / "correction.json",
        "rt6": tmp_path / "rt6.json",
    }
    payloads = {
        "exact": _exact_artifact(),
        "bubble": _bubble_artifact(),
        "luwei": _luwei_artifact(),
        "no_plan": _no_plan_artifact(),
        "correction": _correction_artifact(),
        "rt6": _rt6_artifact(),
    }
    for key, path in files.items():
        path.write_text(json.dumps(payloads[key], ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "rt11c.json"

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
            "--rt6-artifact",
            str(files["rt6"]),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
