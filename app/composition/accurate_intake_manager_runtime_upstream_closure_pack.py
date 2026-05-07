from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import yaml

from app.composition.accurate_intake_context_conditioned_intent_wall import build_context_conditioned_intent_wall_artifact
from app.composition.accurate_intake_context_packet_acceptance_gate import build_context_packet_acceptance_gate_artifact
from app.composition.accurate_intake_manager_tool_choice_regression_wall import build_manager_tool_choice_regression_wall_artifact
from app.composition.accurate_intake_manager_tool_surface_inventory import build_manager_tool_surface_inventory_artifact
from app.composition.accurate_intake_non_fooddb_manager_tool_contract import build_non_fooddb_manager_tool_contract_artifact
from app.composition.accurate_intake_non_fooddb_mutation_tool_guard_smoke import build_non_fooddb_mutation_tool_guard_smoke_artifact
from app.composition.accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke import build_non_fooddb_read_only_tool_loop_fake_smoke_artifact

MANAGER_RUNTIME_GATE_LEDGER_PATH = Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _read_gate_ledger() -> dict[str, Any]:
    payload = yaml.safe_load(MANAGER_RUNTIME_GATE_LEDGER_PATH.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, dict) else {}


def _gate_index(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("gate_id")): dict(entry)
        for entry in list(ledger.get("gates") or [])
        if isinstance(entry, dict) and entry.get("gate_id")
    }


def _gate_entry(*, gate_id: str, title: str, pass_type: str, blockers: list[str], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "title": title,
        "pass_type": pass_type,
        "status": "green" if not blockers else "blocked",
        "blockers": sorted(set(str(blocker) for blocker in blockers)),
        "evidence": evidence,
    }


def _dependency_evidence(gates: dict[str, dict[str, Any]], gate_ids: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    evidence: list[dict[str, Any]] = []
    blockers: list[str] = []
    for gate_id in gate_ids:
        gate = gates.get(gate_id)
        if gate is None:
            blockers.append(f"missing_dependency_gate:{gate_id}")
            continue
        status = str(gate.get("status") or "")
        evidence.append(
            {
                "gate_id": gate_id,
                "title": gate.get("title"),
                "status": status,
                "pass_type": gate.get("pass_type"),
                "source": MANAGER_RUNTIME_GATE_LEDGER_PATH.as_posix(),
            }
        )
        if status != "green":
            blockers.append(f"{gate_id}.not_green")
    return evidence, blockers


def _gate_from_dependencies(gates: dict[str, dict[str, Any]], *, gate_id: str, dependency_gate_ids: list[str]) -> dict[str, Any]:
    evidence, blockers = _dependency_evidence(gates, dependency_gate_ids)
    gate = gates[gate_id]
    return _gate_entry(
        gate_id=gate_id,
        title=str(gate["title"]),
        pass_type=str(gate["pass_type"]),
        blockers=blockers,
        evidence=evidence,
    )


def _artifact_evidence(artifact: dict[str, Any], *, expected_status: str) -> tuple[dict[str, Any], list[str]]:
    status = str(artifact.get("status") or "")
    identity = (
        str(artifact.get("artifact_type") or "")
        or str(artifact.get("gate_id") or "")
        or str(artifact.get("claim_scope") or "")
    )
    blockers = list(artifact.get("blockers") or [])
    if status != expected_status:
        blockers.append(f"{identity}.status_not_{expected_status}")
    return (
        {
            "artifact_type": artifact.get("artifact_type"),
            "gate_id": artifact.get("gate_id"),
            "claim_scope": artifact.get("claim_scope"),
            "status": status,
            "source": "builder",
        },
        [str(blocker) for blocker in blockers],
    )


def build_manager_runtime_upstream_closure_pack(
    *,
    manual_target_gate: dict[str, Any],
) -> dict[str, Any]:
    ledger = _read_gate_ledger()
    gates = _gate_index(ledger)

    tool_surface = build_manager_tool_surface_inventory_artifact()
    tool_contract = build_non_fooddb_manager_tool_contract_artifact(inventory=tool_surface)
    tool_choice_wall = build_manager_tool_choice_regression_wall_artifact()
    context_packet_gate = build_context_packet_acceptance_gate_artifact()
    context_conditioned_wall = build_context_conditioned_intent_wall_artifact()
    read_only_tool_loop = build_non_fooddb_read_only_tool_loop_fake_smoke_artifact(
        tool_contract=tool_contract,
        tool_choice_wall=tool_choice_wall,
    )
    mutation_tool_guard = build_non_fooddb_mutation_tool_guard_smoke_artifact(
        tool_contract=tool_contract,
        tool_choice_wall=tool_choice_wall,
    )

    rt2 = _gate_from_dependencies(
        gates,
        gate_id="rt2_coarse_tool_surface_convergence",
        dependency_gate_ids=[
            "rt2a_public_tool_name_normalization",
            "rt2b_entry_fallback_public_tool_surface",
            "rt2c_read_only_public_tool_runtime_smoke",
        ],
    )
    rt3 = _gate_from_dependencies(
        gates,
        gate_id="rt3_react_trace_contract",
        dependency_gate_ids=[
            "rt3a_react_trace_observable_skeleton",
            "rt3b_multi_pass_react_trace_summary",
        ],
    )
    rt4_artifact_evidence, rt4_artifact_blockers = _artifact_evidence(context_packet_gate, expected_status="pass")
    rt4 = _gate_entry(
        gate_id="rt4_context_packet_acceptance",
        title=str(gates["rt4_context_packet_acceptance"]["title"]),
        pass_type=str(gates["rt4_context_packet_acceptance"]["pass_type"]),
        blockers=(
            ([] if rt3["status"] == "green" else ["rt3_react_trace_contract.not_green"])
            + rt4_artifact_blockers
        ),
        evidence=[rt3, rt4_artifact_evidence],
    )

    rt5_evidence: list[dict[str, Any]] = [rt2, rt4]
    rt5_blockers: list[str] = []
    if rt2["status"] != "green":
        rt5_blockers.append("rt2_coarse_tool_surface_convergence.not_green")
    if rt4["status"] != "green":
        rt5_blockers.append("rt4_context_packet_acceptance.not_green")

    for artifact, expected_status in (
        (tool_surface, "manager_tool_surface_inventory_ready_for_human_review"),
        (tool_contract, "non_fooddb_manager_tool_contract_ready_for_human_review"),
        (tool_choice_wall, "manager_tool_choice_regression_wall_pass"),
        (context_conditioned_wall, "pass"),
        (read_only_tool_loop, "non_fooddb_read_only_tool_loop_fake_smoke_pass"),
        (mutation_tool_guard, "non_fooddb_mutation_tool_guard_smoke_pass"),
        (manual_target_gate, "pass"),
    ):
        artifact_evidence, artifact_blockers = _artifact_evidence(artifact, expected_status=expected_status)
        rt5_evidence.append(artifact_evidence)
        rt5_blockers.extend(artifact_blockers)

    rt5 = _gate_entry(
        gate_id="rt5_intent_tool_argument_walls",
        title=str(gates["rt5_intent_tool_argument_walls"]["title"]),
        pass_type=str(gates["rt5_intent_tool_argument_walls"]["pass_type"]),
        blockers=rt5_blockers,
        evidence=rt5_evidence,
    )

    gate_entries = [rt2, rt3, rt4, rt5]
    blockers = [
        f"{entry['gate_id']}.not_green"
        for entry in gate_entries
        if entry["status"] != "green"
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_manager_runtime_upstream_closure_pack",
            "claim_scope": "current_shell_manager_runtime_upstream_closure_pack",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "manager_runtime_gate_ledger_source": MANAGER_RUNTIME_GATE_LEDGER_PATH.as_posix(),
            "target_gate_ids": [entry["gate_id"] for entry in gate_entries],
            "gates": gate_entries,
            "summary": {
                "green_gate_count": sum(1 for entry in gate_entries if entry["status"] == "green"),
                "target_gate_count": len(gate_entries),
            },
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
        }
    )


__all__ = ["build_manager_runtime_upstream_closure_pack"]
