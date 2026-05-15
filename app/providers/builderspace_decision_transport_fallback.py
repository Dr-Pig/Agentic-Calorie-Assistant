from __future__ import annotations

from typing import Any

from .builderspace_parsing import BuilderSpaceParseError


def should_fallback_decision_transport_parse_error(
    exc: BuilderSpaceParseError,
    constraints: dict[str, Any],
) -> bool:
    return (
        getattr(exc, "failure_family", None) == "tool_call_transport_contract_breach"
        and constraints.get("manager_contract_profile_id") == "founder_live_contract"
        and constraints.get("manager_contract_transport_policy") == "synthetic_tool_transport"
    )
