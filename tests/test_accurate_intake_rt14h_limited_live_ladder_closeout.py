from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_accurate_intake_rt14h_limited_live_ladder_closeout as module  # noqa: E402


def _ledger() -> dict[str, object]:
    return yaml.safe_load((ROOT / "docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml").read_text(encoding="utf-8"))


def _artifact(gate_id: str, *, status: str = "pass", runtime_backed: bool = True) -> dict[str, object]:
    return {
        "artifact_type": f"artifact_for_{gate_id}",
        "target_manager_runtime_gate": gate_id,
        "status": status,
        "pass_type": "runtime_backed" if runtime_backed else "contract",
        "runtime_backed": runtime_backed,
        "live_llm_invoked": runtime_backed,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "non_claims": {
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "whole_product_mvp_ready": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
        },
    }


def _artifacts(**overrides: dict[str, object]) -> dict[str, dict[str, object]]:
    artifacts = {
        gate_id: _artifact(gate_id, runtime_backed=gate_id != "rt14g_response_language_prompt_polish")
        for gate_id in module.REQUIRED_CLOSEOUT_ARTIFACT_GATES
    }
    artifacts.update(overrides)
    return artifacts


def _decision_pack(*, selected_option: str = "offline_shadow_replay") -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_decision_pack",
        "claim_scope": "live_diagnostic_decision_pack",
        "selected_option": selected_option,
        "selection_reason": "model_diversity_missing",
        "private_self_use_candidate_prepared": False,
        "requires_human_approval_for_private_self_use": False,
        "decision_boundary": {
            "live_diagnostic_is_product_readiness": False,
            "runtime_web_activation_allowed": False,
            "mutation_rollout_allowed": False,
            "production_manager_selected": False,
        },
    }


def _build(
    *,
    ledger: dict[str, object] | None = None,
    artifacts: dict[str, dict[str, object]] | None = None,
    decision_pack: dict[str, object] | None = None,
) -> dict[str, object]:
    return module.build_rt14h_limited_live_ladder_closeout(
        gate_ledger=ledger or _ledger(),
        gate_artifacts=artifacts or _artifacts(),
        live_decision_pack=decision_pack or _decision_pack(),
    )


def test_rt14h_closeout_passes_when_ladder_dependencies_and_decision_pack_are_clean() -> None:
    artifact = _build()

    assert artifact["artifact_type"] == "accurate_intake_rt14h_limited_live_ladder_closeout"
    assert artifact["target_manager_runtime_gate"] == "rt14_limited_live_ladder"
    assert artifact["status"] == "pass"
    assert artifact["pass_type"] == "runtime_backed"
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is True
    assert artifact["summary"]["dependency_gate_count"] >= 20
    assert artifact["summary"]["artifact_gate_count"] == len(module.REQUIRED_CLOSEOUT_ARTIFACT_GATES)
    assert artifact["decision_pack_sync"] == {
        "source_artifact_type": "accurate_intake_mvp_live_decision_pack",
        "selected_option": "offline_shadow_replay",
        "selection_reason": "model_diversity_missing",
        "private_self_use_candidate_prepared": False,
        "next_mainline": "continue_current_shell_appshell_browser_runtime_closure",
    }
    assert artifact["semantic_boundary"]["deterministic_role"] == "validate_gate_closure_and_claim_boundary"
    assert artifact["non_claims"]["private_self_use_approved"] is False


def test_rt14h_closeout_blocks_missing_or_non_green_ledger_dependencies() -> None:
    ledger = _ledger()
    gates = ledger["gates"]
    for gate in gates:
        if gate["gate_id"] == "rt14g_response_language_prompt_polish":
            gate["status"] = "pending"

    artifact = _build(ledger=ledger)

    assert artifact["status"] == "fail"
    assert "ledger_dependency.rt14g_response_language_prompt_polish_not_green" in artifact["blockers"]


def test_rt14h_closeout_blocks_failed_dependency_artifacts() -> None:
    artifact = _build(
        artifacts=_artifacts(
            rt13b_latency_cost_cache_budget_pack=_artifact(
                "rt13b_latency_cost_cache_budget_pack",
                status="fail",
            )
        )
    )

    assert artifact["status"] == "fail"
    assert "gate_artifact.rt13b_latency_cost_cache_budget_pack_not_pass" in artifact["blockers"]


def test_rt14h_closeout_blocks_live_decision_pack_still_in_diagnostic_failure_mode() -> None:
    artifact = _build(decision_pack=_decision_pack(selected_option="stay_diagnostic"))

    assert artifact["status"] == "fail"
    assert "decision_pack.blocking_selected_option:stay_diagnostic" in artifact["blockers"]


def test_rt14h_cli_writes_artifact(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.yaml"
    decision = tmp_path / "decision.json"
    output = tmp_path / "rt14h.json"
    artifact_paths: list[str] = []

    ledger.write_text(yaml.safe_dump(_ledger(), sort_keys=False), encoding="utf-8")
    decision.write_text(json.dumps(_decision_pack(), ensure_ascii=False), encoding="utf-8")
    for gate_id, artifact in _artifacts().items():
        path = tmp_path / f"{gate_id}.json"
        path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        artifact_paths.extend(["--gate-artifact", str(path)])

    rc = module.main(
        [
            "--gate-ledger",
            str(ledger),
            "--live-decision-pack",
            str(decision),
            "--output",
            str(output),
            *artifact_paths,
        ]
    )

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
