from __future__ import annotations

from typing import Any


def nutrition_payload_values_must_be_hidden(trace_contract: dict[str, Any]) -> bool:
    if trace_contract.get("shadow_stub") is True:
        return True
    decision = trace_contract.get("canonical_write_decision")
    if isinstance(decision, dict) and decision.get("can_write_canonical") is False:
        return bool(str(decision.get("failure_family") or "").strip())
    return str(trace_contract.get("response_mode_hint") or "") == "clarify_first"
