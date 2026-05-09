from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


SYNC_CONTRACT_PATH = Path("docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml")
MANAGER_RUNTIME_GATE_LEDGER_PATH = Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml")
UPSTREAM_RUNTIME_GATE = "rt6_bootstrap_no_plan_body_closure"
BODY_OBSERVATION_SAME_TRUTH_READY_STATUS = "body_observation_same_truth_gate_ready_for_human_review"
REQUIRED_BROWSER_FLAGS = (
    "body_active_plan_rendered",
    "body_weight_checkin_saved",
    "body_latest_weight_rendered_from_backend",
    "body_weight_history_date_scoped_readback",
    "body_plan_readback_checked",
    "body_manual_target_read_model_rendered",
    "today_manual_target_readback_checked",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(loaded) if isinstance(loaded, dict) else {}


def build_body_observation_same_truth_gate_artifact(
    *,
    browser_smoke_artifact: dict[str, Any],
    manager_runtime_gate_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    gate_ledger = manager_runtime_gate_ledger or _read_yaml(MANAGER_RUNTIME_GATE_LEDGER_PATH)
    sync_contract = _read_yaml(SYNC_CONTRACT_PATH)

    gates = {
        str(entry.get("gate_id")): dict(entry)
        for entry in list(gate_ledger.get("gates") or [])
        if isinstance(entry, dict) and entry.get("gate_id")
    }
    upstream_gate = gates.get(UPSTREAM_RUNTIME_GATE, {})
    upstream_status = str(upstream_gate.get("status") or "missing")

    if str(browser_smoke_artifact.get("status") or "") != "pass":
        blockers.append(f"browser_smoke.unexpected_status:{browser_smoke_artifact.get('status')}")
    if browser_smoke_artifact.get("browser_executed") is not True:
        blockers.append("browser_smoke.browser_executed_not_true")

    for field in REQUIRED_BROWSER_FLAGS:
        if browser_smoke_artifact.get(field) is not True:
            blockers.append(f"browser_smoke.{field}_not_true")

    if upstream_status != "green":
        blockers.append(f"upstream_gate.{UPSTREAM_RUNTIME_GATE}_not_green:{upstream_status}")

    status = BODY_OBSERVATION_SAME_TRUTH_READY_STATUS if not blockers else "blocked"
    browser_truth = {
        field: browser_smoke_artifact.get(field)
        for field in REQUIRED_BROWSER_FLAGS
    }
    browser_truth["body_plan_read_model_values"] = dict(browser_smoke_artifact.get("body_plan_read_model_values") or {})
    browser_truth["body_budget_read_model_values"] = dict(browser_smoke_artifact.get("body_budget_read_model_values") or {})

    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_body_observation_same_truth_gate",
            "status": status,
            "pass_type": "browser_executed",
            "browser_executed": browser_smoke_artifact.get("browser_executed") is True,
            "claim_scope": "appshell_body_observation_same_truth_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "journeys": ["G", "H"],
            "upstream_runtime_gate": UPSTREAM_RUNTIME_GATE,
            "upstream_runtime_gate_status": upstream_status,
            "current_shell_sync_contract_source": SYNC_CONTRACT_PATH.as_posix(),
            "manager_runtime_gate_ledger_source": MANAGER_RUNTIME_GATE_LEDGER_PATH.as_posix(),
            "current_shell_target": sync_contract.get("current_shell_target"),
            "browser_smoke_artifact_type": browser_smoke_artifact.get("artifact_type"),
            "browser_smoke_status": browser_smoke_artifact.get("status"),
            "browser_truth": browser_truth,
            "summary": {
                "required_browser_flag_count": len(REQUIRED_BROWSER_FLAGS),
                "all_required_browser_flags_true": all(
                    browser_smoke_artifact.get(field) is True for field in REQUIRED_BROWSER_FLAGS
                ),
                "upstream_gate_green": upstream_status == "green",
            },
            "blockers": blockers,
            "local_only": True,
            "diagnostic_only": True,
            "frontend_semantic_owner": False,
            "frontend_calculates_body_truth": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        }
    )


__all__ = [
    "BODY_OBSERVATION_SAME_TRUTH_READY_STATUS",
    "REQUIRED_BROWSER_FLAGS",
    "build_body_observation_same_truth_gate_artifact",
]
