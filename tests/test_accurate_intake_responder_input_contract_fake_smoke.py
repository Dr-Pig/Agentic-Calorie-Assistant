from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_responder_input_contract_fake_smoke as module
from app.composition.accurate_intake_responder_input_contract_fake_smoke import (
    build_responder_input_contract_fake_smoke_artifact,
)


REQUIRED_SCENARIOS = [
    "clarification_no_commit",
    "candidate_supported_no_mutation",
    "committed_backend_budget",
    "degraded_budget_unavailable",
    "correction_ambiguity",
    "macro_hidden_no_visible_claim",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(scenario["scenario_id"]): scenario
        for scenario in artifact["scenarios"]  # type: ignore[index]
    }


def test_responder_input_contract_fake_smoke_is_local_diagnostic_only() -> None:
    artifact = build_responder_input_contract_fake_smoke_artifact()

    assert artifact["artifact_type"] == "accurate_intake_responder_input_contract_fake_smoke"
    assert artifact["status"] == "pass"
    assert artifact["fake_responder_used"] is True
    assert artifact["structured_allowed_facts_required"] is True
    assert artifact["responder_claims_require_allowed_fact_id"] is True
    assert artifact["semantic_owner"] == "manager_and_backend_structured_runtime_facts"
    assert artifact["responder_role"] == "mirror_allowed_facts_only"
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_called"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert [scenario["scenario_id"] for scenario in artifact["scenarios"]] == REQUIRED_SCENARIOS


def test_responder_input_contract_allows_only_claims_grounded_in_allowed_facts() -> None:
    artifact = build_responder_input_contract_fake_smoke_artifact()
    by_id = _by_id(artifact)

    no_commit = by_id["clarification_no_commit"]
    committed = by_id["committed_backend_budget"]
    macro_hidden = by_id["macro_hidden_no_visible_claim"]
    renderer_input = no_commit["renderer"]["input"]  # type: ignore[index]

    assert isinstance(renderer_input["allowed_facts"], list)
    assert isinstance(renderer_input["forbidden_claims"], list)
    assert isinstance(renderer_input["item_results"], list)
    assert renderer_input["ledger_mutation_result"]["mutation_authority"] is False  # type: ignore[index]
    assert "readiness_or_self_use_approval" in renderer_input["forbidden_claims"]

    assert no_commit["accepted_response"]["verdict"] == "accepted"  # type: ignore[index]
    assert no_commit["rejected_response"]["verdict"] == "blocked"  # type: ignore[index]
    assert "invented_logged_status" in no_commit["rejected_response"]["blockers"]  # type: ignore[index]
    assert "invented_kcal_claim" in no_commit["rejected_response"]["blockers"]  # type: ignore[index]

    assert committed["accepted_response"]["verdict"] == "accepted"  # type: ignore[index]
    accepted_claims = committed["accepted_response"]["claims"]  # type: ignore[index]
    assert {claim["claim_type"] for claim in accepted_claims} == {  # type: ignore[index]
        "logged_status",
        "kcal",
        "remaining",
        "show_macro",
        "macro_guard_reason",
        "protein_g",
        "carbs_g",
        "fat_g",
    }
    assert committed["rejected_response"]["verdict"] == "blocked"  # type: ignore[index]
    assert "invented_exactness_claim" in committed["rejected_response"]["blockers"]  # type: ignore[index]
    assert "readiness_claim_forbidden" in committed["rejected_response"]["blockers"]  # type: ignore[index]

    assert macro_hidden["accepted_response"]["verdict"] == "accepted"  # type: ignore[index]
    accepted_hidden_claims = macro_hidden["accepted_response"]["claims"]  # type: ignore[index]
    assert {claim["claim_type"] for claim in accepted_hidden_claims} == {  # type: ignore[index]
        "show_macro",
        "macro_guard_reason",
    }
    assert macro_hidden["rejected_response"]["verdict"] == "blocked"  # type: ignore[index]
    assert "invented_protein_claim" in macro_hidden["rejected_response"]["blockers"]  # type: ignore[index]
    assert "invented_macro_visibility_claim" in macro_hidden["rejected_response"]["blockers"]  # type: ignore[index]


def test_responder_input_contract_blocks_remaining_when_budget_is_unavailable() -> None:
    artifact = build_responder_input_contract_fake_smoke_artifact()
    degraded = _by_id(artifact)["degraded_budget_unavailable"]

    assert degraded["accepted_response"]["verdict"] == "accepted"  # type: ignore[index]
    assert degraded["rejected_response"]["verdict"] == "blocked"  # type: ignore[index]
    assert "invented_remaining_claim" in degraded["rejected_response"]["blockers"]  # type: ignore[index]
    assert "degraded_budget_concrete_remaining_forbidden" in degraded["rejected_response"]["blockers"]  # type: ignore[index]


def test_responder_input_contract_blocks_target_selection_and_mutation_for_ambiguity() -> None:
    artifact = build_responder_input_contract_fake_smoke_artifact()
    ambiguity = _by_id(artifact)["correction_ambiguity"]

    assert ambiguity["accepted_response"]["verdict"] == "accepted"  # type: ignore[index]
    assert ambiguity["rejected_response"]["verdict"] == "blocked"  # type: ignore[index]
    assert "invented_target_selection" in ambiguity["rejected_response"]["blockers"]  # type: ignore[index]
    assert "invented_logged_status" in ambiguity["rejected_response"]["blockers"]  # type: ignore[index]


def test_responder_input_contract_validator_rejects_missing_allowed_fact_ids() -> None:
    scenario = module._scenario_specs()[0]
    allowed = module._allowed_fact_map(scenario["allowed_facts"])
    bad_response = {
        "response_id": "bad-missing-fact",
        "claims": [
            {
                "claim_type": "kcal",
                "fact_id": "missing-fact",
                "value": 999,
            }
        ],
    }

    result = module._evaluate_response(
        response=bad_response,
        allowed_facts=allowed,
        budget_status=str(scenario["budget_status"]),
    )

    assert result["verdict"] == "blocked"
    assert "claim_fact_id_not_allowed" in result["blockers"]
    assert "invented_kcal_claim" in result["blockers"]


def test_responder_input_contract_validator_rejects_empty_claims() -> None:
    scenario = module._scenario_specs()[0]
    allowed = module._allowed_fact_map(scenario["allowed_facts"])

    result = module._evaluate_response(
        response={"response_id": "bad-empty-claims", "claims": []},
        allowed_facts=allowed,
        budget_status=str(scenario["budget_status"]),
    )

    assert result["verdict"] == "blocked"
    assert "claims_missing" in result["blockers"]


def test_responder_input_contract_fake_smoke_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "responder_input_contract_fake_smoke.json"

    from scripts.run_accurate_intake_responder_input_contract_fake_smoke import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["scenario_count"] == len(REQUIRED_SCENARIOS)


def test_responder_input_contract_fake_smoke_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_responder_input_contract_claims.py"),
        Path("app/composition/accurate_intake_responder_input_contract_fake_smoke.py"),
        Path("app/composition/accurate_intake_responder_input_contract_scenarios.py"),
        Path("scripts/run_accurate_intake_responder_input_contract_fake_smoke.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "tavily_adapter",
        "Tavily",
        "Kimi",
        "GrokFast",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "manager_context_packet_schema_changed = True",
        "mutation_authority = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source


def test_ci_does_not_make_responder_fake_smoke_a_standalone_required_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_responder_input_contract_fake_smoke.py" not in workflow
    assert "run_accurate_intake_responder_input_contract_fake_smoke.py" not in workflow
    assert "accurate_intake_responder_input_contract_fake_smoke_ci.json" not in workflow
    assert "accurate-intake-responder-input-contract-fake-smoke-report" not in workflow
