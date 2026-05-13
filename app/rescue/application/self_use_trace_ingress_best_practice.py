from __future__ import annotations

from typing import Any


def best_practice_evidence() -> dict[str, Any]:
    return {
        "required": True,
        "sources_checked": [
            "openai_agents_guardrails",
            "openai_agent_evals",
            "openai_agents_sessions",
        ],
        "source_urls": {
            "openai_agents_guardrails": (
                "https://openai.github.io/openai-agents-python/guardrails/"
            ),
            "openai_agent_evals": "https://platform.openai.com/docs/guides/agent-evals",
            "openai_agents_sessions": (
                "https://openai.github.io/openai-agents-python/sessions/"
            ),
        },
        "adopted_guidance": [
            "trace_backed_evals_before_activation",
            "tool_guardrails_before_side_effects",
            "session_history_not_durable_memory_truth",
        ],
        "rejected_guidance": [
            "hidden_rescue_activation_from_trace_observation",
            "raw_trace_dump_as_manager_context",
        ],
        "how_the_design_changed": [
            "adapter_outputs_read_models_only",
            "diagnostic_artifact_records_no_runtime_effect_flags",
        ],
    }
