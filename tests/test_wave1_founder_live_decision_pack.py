from __future__ import annotations

import json
from pathlib import Path

from scripts.build_wave1_founder_live_decision_pack import (
    DECISION_OPTION_IDS,
    build_founder_live_decision_pack,
    write_founder_live_decision_pack,
)


def _artifact(
    *,
    live_invoked: bool = True,
    pass_count: int = 1,
    fail_count: int = 6,
    product_decision_required_count: int = 0,
    failure_layers: list[str] | None = None,
    strict_pass_count: int = 1,
    repaired_pass_count: int = 0,
    contract_fail_count: int = 6,
) -> dict[str, object]:
    return {
        "artifact_type": "wave1_founder_e2e_live_diagnostic",
        "readiness_claimed": False,
        "live_invoked": live_invoked,
        "production_selected": False,
        "runtime_web_activation_approved": False,
        "mutation_enabled": False,
        "summary": {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "product_decision_required_count": product_decision_required_count,
            "failure_layers": failure_layers if failure_layers is not None else ["provider_contract_non_adherence"],
            "strict_pass_count": strict_pass_count,
            "repaired_pass_count": repaired_pass_count,
            "contract_fail_count": contract_fail_count,
            "shadow_or_canary_unlock_allowed": False,
        },
        "cases": [
            {"case_id": "case-1", "case_contract_status": "strict_pass"},
            {"case_id": "case-2", "case_contract_status": "fail"},
        ],
    }


def test_founder_live_decision_pack_routes_provider_contract_failures_to_followup() -> None:
    pack = build_founder_live_decision_pack(_artifact())

    assert pack["artifact_type"] == "wave1_founder_live_decision_pack"
    assert pack["decision_options_ordered"] == list(DECISION_OPTION_IDS)
    assert pack["selected_option"] == "narrow_live_contract_followup"
    assert pack["readiness_claimed"] is False
    assert pack["shadow_or_canary_approved"] is False
    assert pack["production_rollout_approved"] is False


def test_founder_live_decision_pack_does_not_unlock_shadow_for_all_repaired_passes() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=0,
            repaired_pass_count=7,
            contract_fail_count=0,
            product_decision_required_count=0,
        )
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "live_clean_but_repair_dependent"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_can_prepare_shadow_candidate_only_for_all_strict_passes() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        )
    )

    assert pack["selected_option"] == "prepare_shadow_candidate"
    assert pack["selection_reason"] == "all_live_cases_strict_pass_diagnostic_only"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_defers_to_product_decision_when_needed() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=6,
            fail_count=0,
            product_decision_required_count=1,
            failure_layers=[],
            strict_pass_count=6,
            repaired_pass_count=0,
            contract_fail_count=0,
        )
    )

    assert pack["selected_option"] == "defer_until_product_decision"
    assert pack["requires_human_decision"] is True


def test_founder_live_decision_pack_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "wave1_founder_e2e_live_diagnostic.json"
    source.write_text(json.dumps(_artifact(), ensure_ascii=False), encoding="utf-8")

    output = write_founder_live_decision_pack(founder_live_artifact_path=source, output_dir=tmp_path)

    pack = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "wave1_founder_live_decision_pack.json"
    assert pack["selected_option"] == "narrow_live_contract_followup"
    assert pack["runtime_web_activation_approved"] is False
