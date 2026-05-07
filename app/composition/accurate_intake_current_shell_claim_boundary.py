from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SYNC_CONTRACT_PATH = Path("docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml")
MANAGER_RUNTIME_GATE_LEDGER_PATH = Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml")


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(loaded) if isinstance(loaded, dict) else {}


def build_current_shell_appshell_claim_boundary() -> dict[str, Any]:
    sync_contract = _read_yaml(SYNC_CONTRACT_PATH)
    gate_ledger = _read_yaml(MANAGER_RUNTIME_GATE_LEDGER_PATH)

    appshell_rules = dict(sync_contract.get("appshell_rules") or {})
    in_scope_journeys = list(sync_contract.get("in_scope_journeys") or [])
    gates = {
        str(entry.get("gate_id")): dict(entry)
        for entry in list(gate_ledger.get("gates") or [])
        if isinstance(entry, dict) and entry.get("gate_id")
    }
    journey_gate_map = {
        str(journey): [str(gate_id) for gate_id in list(gate_ids or [])]
        for journey, gate_ids in dict(gate_ledger.get("journey_gate_map") or {}).items()
    }
    required_manager_runtime_gates = sorted(
        {
            gate_id
            for journey in in_scope_journeys
            for gate_id in journey_gate_map.get(str(journey), [])
            if gate_id in gates
        }
    )
    green_manager_runtime_gates = [
        gate_id for gate_id in required_manager_runtime_gates if gates[gate_id].get("status") == "green"
    ]
    non_green_manager_runtime_gates = [
        gate_id for gate_id in required_manager_runtime_gates if gates[gate_id].get("status") != "green"
    ]
    runtime_backed_requires_gate = (
        appshell_rules.get("runtime_backed_requires_upstream_gate_green") is True
    )
    browser_executed_requires_gate = (
        appshell_rules.get("browser_executed_requires_upstream_gate_green") is True
    )
    runtime_backed_claim_ready = (
        not runtime_backed_requires_gate or not non_green_manager_runtime_gates
    )
    browser_executed_claim_ready = (
        not browser_executed_requires_gate or not non_green_manager_runtime_gates
    )

    return {
        "launch_scope": sync_contract.get("launch_scope"),
        "claim_scope": sync_contract.get("claim_scope"),
        "current_shell_sync_contract_source": SYNC_CONTRACT_PATH.as_posix(),
        "manager_runtime_gate_ledger_source": MANAGER_RUNTIME_GATE_LEDGER_PATH.as_posix(),
        "pass_taxonomy": list(sync_contract.get("pass_taxonomy") or []),
        "appshell_rules": appshell_rules,
        "non_claims": dict(sync_contract.get("non_claims") or {}),
        "current_shell_in_scope_journeys": in_scope_journeys,
        "required_manager_runtime_gates": required_manager_runtime_gates,
        "green_manager_runtime_gates": green_manager_runtime_gates,
        "non_green_manager_runtime_gates": non_green_manager_runtime_gates,
        "manager_runtime_gate_statuses": {
            gate_id: {
                "status": gates[gate_id].get("status"),
                "pass_type": gates[gate_id].get("pass_type"),
                "title": gates[gate_id].get("title"),
            }
            for gate_id in required_manager_runtime_gates
        },
        "runtime_backed_claim_ready": runtime_backed_claim_ready,
        "browser_executed_claim_ready": browser_executed_claim_ready,
        "status": (
            "ready_for_runtime_and_browser_claims"
            if runtime_backed_claim_ready and browser_executed_claim_ready
            else "blocked_on_manager_runtime_upstream_gates"
        ),
    }


def build_current_shell_appshell_claim_boundary_fields() -> dict[str, Any]:
    claim_boundary = build_current_shell_appshell_claim_boundary()
    return {
        "pass_type": "contract",
        "current_shell_sync_contract_source": claim_boundary["current_shell_sync_contract_source"],
        "manager_runtime_gate_ledger_source": claim_boundary["manager_runtime_gate_ledger_source"],
        "appshell_claim_boundary": claim_boundary,
    }


__all__ = [
    "build_current_shell_appshell_claim_boundary",
    "build_current_shell_appshell_claim_boundary_fields",
]
