from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time
from types import SimpleNamespace
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.agent.manager import SINGLE_MANAGER_SYSTEM_PROMPT, run_intake_manager
from app.runtime.agent.phase_b1_selection import (
    PHASE_B1_PASS_1_COMMON_COMMERCIAL_DRINK_ID,
    PHASE_B1_PASS_1_COMMON_COMMERCIAL_MEAL_ID,
    PHASE_B1_PASS_1_COMMON_FOOD_ITEM_ID,
    PHASE_B1_PASS_1_FORCED_ID,
    PHASE_B1_PASS_1_NATURAL_FALLBACK_ID,
    PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID,
    PHASE_B1_PASS_2_COMMON_COMMERCIAL_DRINK_ID,
    PHASE_B1_PASS_2_COMMON_COMMERCIAL_MEAL_ID,
    PHASE_B1_PASS_2_COMMON_FOOD_ITEM_ID,
    PHASE_B1_PASS_2_GENERIC_ID,
    PHASE_B1_PASS_2_LISTED_INGREDIENT_ID,
    build_phase_b1_selector_inputs,
    select_phase_b1_profile_route,
    select_phase_b1_task_payload,
)
from app.runtime.agent.phase_b1_profile_route_rules import (
    phase_b1_local_diagnostic_requested_profile_allowed,
    resolve_phase_b1_local_diagnostic_cli_defaults,
)
from app.runtime.agent.manager_branch_contract import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
    CLARIFICATION_BRANCH_CONFLICTING_FIELDS,
    MANAGER_OUTPUT_CONTRACT_VIOLATION,
)
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.providers.builderspace_adapter import BuilderSpaceResponseError

DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
LATEST_REPORT = DEFAULT_OUTPUT_DIR / "wave1_phase_b_minimal_tool_loop_smoke.json"
FORCED_MODE = "forced_tool_request_smoke"
NATURAL_MODE = "natural_tool_selection_probe"
CLI_MODES = {"forced": FORCED_MODE, "natural-probe": NATURAL_MODE}
DEFAULT_PROVIDER_TIMEOUT_MS = 180_000
FULL_SMOKE_LATENCY_TARGET_MS = 180_000
FULL_READINESS_SCOPE = "full_actual_smoke"
DIAGNOSTIC_READINESS_SCOPE = "diagnostic"
RUNNER_RETRY_MAX_ATTEMPTS = 2
RUNNER_RETRY_BASE_BACKOFF_SECONDS = 0.25
MANAGER_CONTRACT_VALIDATION_ERROR = "manager_contract_validation_error"

CORE_SMOKE_CASES = (
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了滷味",
    "我吃了豆干、海帶、貢丸的滷味",
    "珍珠奶茶大概多少熱量？",
)
CORE_SMOKE_CASE_IDS = tuple(f"B1-{index:03d}" for index in range(1, len(CORE_SMOKE_CASES) + 1))
CORE_SMOKE_CASE_MAP = dict(zip(CORE_SMOKE_CASE_IDS, CORE_SMOKE_CASES))
AVAILABLE_READ_TOOLS = (
    "lookup_generic_food",
    "retrieve_web_food_evidence",
    "load_taiwan_food_semantics_skill",
)
ESTIMATE_READ_TOOLS = {"lookup_generic_food", "retrieve_web_food_evidence"}
PROVIDER_PARAM_KEYS = (
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "response_format",
    "timeout",
    "retry_policy",
    "tool_choice",
    "request_id",
    "provider_profile_id",
    "provider_profile_provider",
    "provider_profile_model",
    "provider_profile_cost_tier",
    "provider_profile_manual_only",
    "provider_profile_role",
    "provider_profile_transport_mode",
    "provider_profile_selection_reason",
    "manager_candidate_status",
    "documented_reasoning_status",
    "documented_tool_call_support",
    "production_selected",
    "allow_expensive_model_probe",
    "artifact_tool_call_reliability",
    "provider_profile_route_mode",
    "provider_profile_route_reason",
    "profile_routing_rule_id",
    "profile_routing_scope",
    "profile_routing_artifact_basis",
)


@dataclass(frozen=True)
class _PhaseB1ProviderProfile:
    profile_id: str
    provider: str
    model: str
    cost_tier: str
    manual_only: bool
    provider_profile_role: str
    allow_expensive_model_probe: bool
    transport_mode: str
    selection_reason: str
    documented_tool_call_support: str
    documented_reasoning_status: str
    artifact_tool_call_reliability: str
    manager_candidate_status: str = "not_applicable"
    production_selected: bool = False
    default_for_build_loop: bool = False
    branch_scope: str | None = None
    manager_role_scope: str | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class _PhaseB1ProfileRoute:
    profile: _PhaseB1ProviderProfile
    route_mode: str
    route_reason: str
    rule_id: str
    routing_scope: str
    artifact_basis: dict[str, Any] | None = None
    uses_case_id_local_debt: bool = False
    should_migrate_post_b1: bool = False


PHASE_B1_PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    "builderspace-deepseek-default": {
        "provider": "builderspace",
        "model": "deepseek",
        "cost_tier": "low",
        "manual_only": False,
        "provider_profile_role": "default_build_loop",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "default low-cost build-loop profile",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "not_documented",
        "artifact_tool_call_reliability": "B1-003_failed",
        "manager_candidate_status": "not_applicable",
        "production_selected": False,
        "default_for_build_loop": True,
        "branch_scope": None,
        "manager_role_scope": None,
        "temperature": 0.0,
    },
    "builderspace-grok-4-fast-b1003-probe": {
        "provider": "builderspace",
        "model": "grok-4-fast",
        "cost_tier": "low",
        "manual_only": False,
        "provider_profile_role": "low_cost_transport_probe",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "lowest-cost alternate candidate for B1-003 decision transport probe",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "documented",
        "artifact_tool_call_reliability": "B1-003_passed",
        "manager_candidate_status": "not_applicable",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 0.0,
    },
    "builderspace-grok-4-fast-b1004-probe": {
        "provider": "builderspace",
        "model": "grok-4-fast",
        "cost_tier": "low",
        "manual_only": False,
        "provider_profile_role": "low_cost_transport_probe",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "lowest-cost alternate candidate for B1-004 clarify-only provider-profile probe",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "documented",
        "artifact_tool_call_reliability": "B1-004_probe_pending",
        "manager_candidate_status": "not_applicable",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 0.0,
    },
    "builderspace-grok-4-fast-b1005-probe": {
        "provider": "builderspace",
        "model": "grok-4-fast",
        "cost_tier": "low",
        "manual_only": False,
        "provider_profile_role": "low_cost_transport_probe",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "lowest-cost alternate candidate for B1-005 listed-ingredient tool-selection probe",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "documented",
        "artifact_tool_call_reliability": "B1-005_passed",
        "manager_candidate_status": "not_applicable",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_LISTED_INGREDIENT_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 0.0,
    },
    "builderspace-grok-4-fast-b1006-probe": {
        "provider": "builderspace",
        "model": "grok-4-fast",
        "cost_tier": "low",
        "manual_only": False,
        "provider_profile_role": "low_cost_transport_probe",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "lowest-cost alternate candidate for B1-006 structured decision probe",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "documented",
        "artifact_tool_call_reliability": "B1-006_passed",
        "manager_candidate_status": "not_applicable",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 0.0,
    },
    "builderspace-kimi-k2.5-candidate": {
        "provider": "builderspace",
        "model": "kimi-k2.5",
        "cost_tier": "medium-low",
        "manual_only": False,
        "provider_profile_role": "manager_candidate_primary",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "primary future manager candidate hypothesis from upstream ToolCalls, JSON mode, and long-context suitability",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "partial",
        "artifact_tool_call_reliability": "unknown",
        "manager_candidate_status": "hypothesis_only",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 1.0,
    },
    "builderspace-gemini-3-flash-preview-candidate": {
        "provider": "builderspace",
        "model": "gemini-3-flash-preview",
        "cost_tier": "medium",
        "manual_only": False,
        "provider_profile_role": "manager_candidate_secondary",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "secondary future manager candidate hypothesis for reasoning and memory-heavy long-context work",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "documented",
        "artifact_tool_call_reliability": "unknown",
        "manager_candidate_status": "hypothesis_only",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 0.0,
    },
    "builderspace-gpt-5-manual": {
        "provider": "builderspace",
        "model": "gpt-5",
        "cost_tier": "high",
        "manual_only": True,
        "provider_profile_role": "expensive_manual_baseline",
        "allow_expensive_model_probe": False,
        "transport_mode": "tool_call_decision_transport",
        "selection_reason": "manual-only expensive confirmation probe",
        "documented_tool_call_support": "documented_at_endpoint_surface",
        "documented_reasoning_status": "documented",
        "artifact_tool_call_reliability": "unknown",
        "manager_candidate_status": "manual_baseline_only",
        "production_selected": False,
        "default_for_build_loop": False,
        "branch_scope": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        "manager_role_scope": "pass_1_tool_request",
        "temperature": 1.0,
    },
}
PASS_1_FORBIDDEN_FIELDS = {
    "final_kcal",
    "kcal_range",
    "likely_kcal",
    "evidence_used",
    "final_response",
    "mutation_result",
    "ledger_delta",
    "canonical_ledger_entry",
}
PASS_2_FORBIDDEN_MUTATION_FIELDS = {"mutation_result", "ledger_delta", "canonical_ledger_entry"}
PASS_1_TOOL_REQUEST_PAYLOAD = (
    "Phase B-1 Pass 1 HARD CONTRACT.\n"
    "This is Manager Pass 1. You MUST return manager_action='call_tools'.\n"
    "Do not choose manager_action='final' in Pass 1.\n"
    "Even for call_tools, include interaction_family, response_mode, operations=[], and answer_contract={} to satisfy the active manager schema.\n"
    "Do not return final nutrition truth, evidence_used, answer text, mutation result, ledger delta, or renderer response.\n"
    "Request read tools needed for the current user message using available tool names.\n"
    "In this B-1 smoke, every food_logging or nutrition_info_query case must call at least one read tool in Pass 1; never skip directly to final in Pass 1.\n"
    "For estimable common foods, request lookup_generic_food.\n"
    "For listed ingredients inside a self-selected basket, request lookup_generic_food for the listed ingredients.\n"
    "For web evidence candidates, request retrieve_web_food_evidence.\n"
    "For self-selected basket foods without listed ingredients, still expose requested estimate tools so the runtime router can block them.\n"
    "The runtime, not the model, validates allowed and blocked tools.\n"
    "JSON example for tea egg:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"茶葉蛋\"}}]}\n"
    "JSON example for nutrition query:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"nutrition_info_query\",\"response_mode\":\"info_answer\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"珍珠奶茶\"}}]}\n"
    "JSON example for self-selected basket blocking trace:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"clarification\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"滷味\"}},{\"name\":\"retrieve_web_food_evidence\",\"arguments\":{\"query\":\"滷味 熱量\"}}]}"
)
PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE = (
    "Phase B-1 natural-probe tool selection guidance.\n"
    "This probe evaluates whether Manager Pass 1 naturally selects appropriate read tools without the forced smoke contract.\n"
    "For this probe, already-consumed estimable common foods, common commercial drinks, common commercial meals, listed ingredients, and nutrition information queries are evidence-needed scenarios before B-1 can continue to synthesis.\n"
    "Mutation intent changes evidence threshold: logged consumption cases require the evidence path before final intake or commit decisions, while no-mutation nutrition queries may still remain answer-only.\n"
    "When the user reports an already-consumed estimable common food, common commercial drink, common commercial meal, or listed ingredients, select appropriate read tools when evidence is needed.\n"
    "For evidence-needed scenarios, return manager_action='call_tools' with tool_calls rather than producing final nutrition or logging output from model memory.\n"
    "For evidence-needed logged common foods, logged common drinks, and logged common meals, do not answer from model memory first and do not claim that tools are unavailable before you request the canonical read tool path.\n"
    "Do not treat lookup_generic_food as unavailable when it is listed among the available runtime tool names.\n"
    "For evidence-needed logged generic-evidence cases, do not ask the user to provide nutrition details instead of requesting lookup_generic_food first.\n"
    "When returning manager_action='call_tools', include the active wrapper fields: interaction_family, response_mode, operations=[], and answer_contract={}.\n"
    "For common_food_item, common_commercial_drink, and common_commercial_meal Pass 1 branches, Output exactly one JSON object.\n"
    "The first non-whitespace character of your response must be '{'.\n"
    "Do not write prose preamble, markdown bullets, or policy recap before JSON.\n"
    "Do not use fenced code blocks.\n"
    "Do not emit duplicated JSON objects.\n"
    "Do not write final-synthesis narration.\n"
    "Do not explain tool availability or tool failure in the output.\n"
    "Do not echo policy or guidance text in the output.\n"
    "This is still Pass 1, not Pass 2.\n"
    "Do not produce item_results, likely_kcal, kcal_range, or final calorie claims.\n"
    "Do not produce final logging, commit, or record_calories posture.\n"
    "Do not summarize calories or evidence in prose.\n"
    "Each tool_calls item should include name and arguments; use available tool names only.\n"
    "If you choose a tool path, the tool name must be the canonical runtime name exactly.\n"
    "Use lookup_generic_food for generic common foods and item-level listed ingredients.\n"
    "High-variance generic items still belong to the generic evidence path when the item identity and generic category are known.\n"
    "A high-variance generic item still has known item identity and known generic category.\n"
    "For a high-variance generic item, uncertainty comes from serving size, customization, recipe, sugar level, brand, or portion variation; it does not come from a missing item list.\n"
    "For common commercial drinks and common commercial meals, preserve a range and uncertainty posture rather than implying a precise single-point truth from model memory alone.\n"
    "logged common drinks and logged common meals still begin with lookup_generic_food even when Pass 2 will later preserve range and uncertainty.\n"
    "Do not collapse a high-variance generic item into a clarify-only boundary when the item identity is already known.\n"
    "For listed-ingredient baskets, use item-level lookup_generic_food calls for the listed ingredients rather than a basket-level lookup for the whole basket name.\n"
    "For a listed-ingredient basket, use one lookup_generic_food call per listed ingredient.\n"
    'Do not collapse listed ingredients into lookup_generic_food("basket_name").\n'
    "If listed ingredients are already present, do not ask a clarification question instead of item-level lookup.\n"
    "For listed ingredients already present, return only item-level tool intent in JSON rather than narrative evidence synthesis.\n"
    "For listed-ingredient baskets, do not use final_action='log_food' or final_action='log_consumption' in Pass 1.\n"
    "For listed-ingredient baskets, manager_action must not be 'final' in Pass 1.\n"
    "For already-consumed estimable common foods and listed ingredients, request lookup_generic_food rather than a generic search alias or a web-evidence-only substitute.\n"
    "For an evidence-needed common food logging case, a response that omits lookup_generic_food or replaces it with search/extract/web_search/food_lookup is not valid.\n"
    "For an evidence-needed common food logging case, Pass 1 must not return a final logging or commit decision before lookup_generic_food.\n"
    "Do not start synthesis, summarize packet evidence, calculate calories, or write a final answer in Pass 1.\n"
    "Do not use unsupported aliases such as search, extract, web_search, or food_lookup; retrieve_web_food_evidence is the canonical web evidence tool when web evidence is appropriate.\n"
    "Unsupported aliases are invalid tool choices and will be rejected by the runtime.\n"
    "For generic common foods and listed ingredients, lookup_generic_food is the core tool; web evidence may be extra but does not replace lookup_generic_food.\n"
    "A nutrition information query may use read tools for answer support, but it must not mutate the ledger.\n"
    "For composition-unknown self-selected baskets, Pass 1 may return a clarify-style final decision only when it does not synthesize nutrition truth, does not mutate, asks for missing item composition or listed ingredients, and uses no fake-final delegation.\n"
    "A composition-unknown self-selected basket means the user-selected item list is missing, so generic lookup would collapse unknown composition into fake evidence.\n"
    "For composition-unknown self-selected baskets, use the clarification-only JSON shape shown below rather than mixing clarification with intake/logging posture fields.\n"
    "For that boundary path, use final_action='request_clarification'; it must not log_food or log_consumption.\n"
    "For composition-unknown self-selected baskets without listed ingredients, do not request any tools at all in Pass 1.\n"
    "For composition-unknown self-selected baskets without listed ingredients, manager_action must not be 'call_tools' in Pass 1.\n"
    "If only the basket label is present, do not request lookup_generic_food for the basket label itself.\n"
    "For composition-unknown self-selected baskets, keep the clarification text limited to asking for the missing item list.\n"
    "For composition-unknown self-selected baskets, do not use response_mode='intake_result', workflow_effect='pass_to_next_round', or uncertainty_posture='high_variance_generic_item'.\n"
    "Do not treat a composition-unknown self-selected basket as a high-variance generic item.\n"
    "When the item list is missing for a self-selected basket, Pass 1 must not request lookup_generic_food or retrieve_web_food_evidence.\n"
    "For a self-selected basket without listed ingredients, do not execute estimate tools, do not invent alias tools, and do not force generic lookup; ask for the missing composition or let the runtime block estimate tools if they are requested.\n"
    "JSON example for common food logging:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"common_food_item\"}}]}\n"
    "Compact JSON example for common_food_item:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"茶葉蛋\"}}]}\n"
    "Compact JSON example for common_commercial_drink:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"珍珠奶茶\"}}]}\n"
    "Compact JSON example for common_commercial_meal:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"便當\"}}]}\n"
    "JSON example for composition-unknown basket boundary:\n"
    "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"clarification\",\"final_action\":\"request_clarification\",\"operations\":[],\"answer_contract\":{\"text\":\"Please list the specific items in the basket so I can estimate accurately.\"}}\n"
    "Do not use intake/logging/high-variance fields in this clarification-only branch."
    "This is not forced mode: do not call tools when the input does not need evidence."
)
PASS_1_COMMON_FOOD_ITEM_ANTI_FINAL_FRAGMENT = (
    "\n"
    "common_food_item anti-final-synthesis discipline.\n"
    "This is Pass 1 only. Your only job is to request tools.\n"
    "Do not synthesize evidence.\n"
    "Do not produce final answer.\n"
    "Do not emit manager_action='final'.\n"
    "Do not write evidence recap.\n"
    "Do not say \"I now have sufficient evidence\".\n"
    "Do not say \"Let me synthesize the final answer\".\n"
    "Bad pattern for common_food_item Pass 1:\n"
    "\"I now have sufficient evidence... Let me synthesize the final answer...\"\n"
    "Good pattern for common_food_item Pass 1:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"茶葉蛋\"}}]}\n"
)
PASS_1_COMMON_COMMERCIAL_MEAL_ANTI_FINAL_FRAGMENT = (
    "\n"
    "common_commercial_meal anti-final-synthesis discipline.\n"
    "This is Pass 1 only. Your only job is to request tools.\n"
    "Do not synthesize evidence.\n"
    "Do not produce final answer.\n"
    "Do not emit manager_action='final'.\n"
    "Do not write evidence recap.\n"
    "Do not say \"I now have sufficient evidence\".\n"
    "Do not say \"Let me synthesize the final answer\".\n"
    "Bad pattern for common_commercial_meal Pass 1:\n"
    "\"I now have sufficient evidence... Let me synthesize the final answer...\"\n"
    "Good pattern for common_commercial_meal Pass 1:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"便當\"}}]}\n"
)
PASS_1_COMMON_COMMERCIAL_DRINK_ANTI_FINAL_FRAGMENT = (
    "\n"
    "common_commercial_drink anti-final-synthesis discipline.\n"
    "This is Pass 1 only. Your only job is to request tools.\n"
    "Do not synthesize evidence.\n"
    "Do not produce final answer.\n"
    "Do not emit manager_action='final'.\n"
    "Do not write evidence recap.\n"
    "Do not say \"I now have sufficient evidence\".\n"
    "Do not say \"Let me synthesize the final answer\".\n"
    "For no-mutation calorie queries about a known common commercial drink, keep query posture rather than logging posture.\n"
    "For no-mutation calorie queries about a known common commercial drink, prefer interaction_family='nutrition_info_query' and response_mode='info_answer'.\n"
    "Good pattern for logged common_commercial_drink Pass 1:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"珍珠奶茶\"}}]}\n"
    "Good pattern for no-mutation common_commercial_drink query Pass 1:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"nutrition_info_query\",\"response_mode\":\"info_answer\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"珍珠奶茶\"}}]}\n"
)
PASS_2_SYNTHESIS_PAYLOAD = (
    "Phase B-1 minimal tool-loop smoke mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Raw tool outputs are trace-only and are not visible as synthesis input.\n"
    "You may produce item_results, kcal_range, likely_kcal, uncertainty, and evidence_used from packet refs.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response."
)
PASS_2_COMMON_FOOD_ITEM_COMPACT_JSON_FIRST_PAYLOAD = (
    "Phase B-1 common-food-item Pass 2 compact synthesis mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Output exactly one compact JSON object.\n"
    "The first non-whitespace character of your response must be '{'.\n"
    "Do not write evidence essay, long source recap, markdown bullets, fenced code blocks, or reasoning text before JSON.\n"
    "Do not replay the runner payload envelope like {\"stage\": ..., \"payload\": ...}.\n"
    "Prefer direct top-level item_results as the canonical output surface.\n"
    "Retain the active wrapper fields required by the current branch: response_mode, intent, workflow_effect, target_attachment, operations, and answer_contract.\n"
    "Use operations=[].\n"
    "Use answer_contract={} unless a minimal compatibility wrapper is strictly required.\n"
    "You may produce compact item_results-oriented synthesis only.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response.\n"
    "Compact JSON example:\n"
    "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"intent\":\"log_food_item\",\"workflow_effect\":\"item_logged\",\"target_attachment\":\"茶葉蛋\",\"item_results\":[{\"food_name\":\"茶葉蛋\",\"kcal_range\":[70,90],\"likely_kcal\":80,\"uncertainty\":\"medium\",\"evidence_used\":[\"generic_food_db:茶葉蛋\"]}],\"operations\":[],\"answer_contract\":{}}"
)
PASS_2_COMMON_COMMERCIAL_DRINK_COMPACT_JSON_FIRST_PAYLOAD = (
    "Phase B-1 common-commercial-drink Pass 2 compact synthesis mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Output exactly one compact JSON object.\n"
    "The first non-whitespace character of your response must be '{'.\n"
    "Do not write evidence essay, source recap, markdown bullets, fenced code blocks, or reasoning text before JSON.\n"
    "You must retain response_mode.\n"
    "You must retain operations=[].\n"
    "You must retain answer_contract.\n"
    "You may use canonical item_results and evidence_used as the result surface.\n"
    "Do not emit final synthesis while dropping required wrapper fields.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response.\n"
    "Compact JSON example:\n"
    "{\"manager_action\":\"final\",\"interaction_family\":\"nutrition_info_query\",\"response_mode\":\"info_answer\",\"intent\":\"query_food_calories\",\"workflow_effect\":\"complete\",\"target_attachment\":\"food_item\",\"item_results\":[{\"food_name\":\"珍珠奶茶\",\"kcal_range\":[350,450],\"likely_kcal\":400,\"uncertainty\":\"medium\",\"evidence_used\":[\"generic_food_db:珍珠奶茶\"]}],\"evidence_used\":[\"generic_food_db:珍珠奶茶\"],\"operations\":[],\"answer_contract\":{}}"
)
PASS_2_COMMON_COMMERCIAL_MEAL_COMPACT_JSON_FIRST_PAYLOAD = (
    "Phase B-1 common-commercial-meal Pass 2 compact synthesis mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Output exactly one compact JSON object.\n"
    "The first non-whitespace character of your response must be '{'.\n"
    "Do not write evidence essay, long source recap, markdown bullets, fenced code blocks, or reasoning text before JSON.\n"
    "Do not replay the runner payload envelope like {\"stage\": ..., \"payload\": ...}.\n"
    "You must retain response_mode.\n"
    "You must retain operations=[].\n"
    "You must retain answer_contract.\n"
    "Do not emit final synthesis while dropping required wrapper fields.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response.\n"
    "Compact JSON example:\n"
    "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"intent\":\"estimate_calories\",\"workflow_effect\":\"complete\",\"target_attachment\":\"generic_taiwanese_bento\",\"answer_contract\":{\"item_results\":[{\"item_name\":\"靘輻\",\"item_quantity\":1,\"item_unit\":\"serving\"}],\"kcal_range\":[550,960],\"likely_kcal\":750,\"uncertainty\":\"medium\",\"evidence_used\":[\"generic_food_db:靘輻\"]},\"operations\":[]}"
)
PASS_2_LISTED_INGREDIENT_COMPACT_JSON_FIRST_PAYLOAD = (
    "Phase B-1 listed-ingredient Pass 2 compact synthesis mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Output exactly one compact JSON object.\n"
    "The first non-whitespace character of your response must be '{'.\n"
    "Do not write narrative preamble, markdown bullets, fenced code blocks, reasoning text, or evidence essay before JSON.\n"
    "Do not summarize packet evidence in prose before JSON.\n"
    "Even in compact mode, include the active manager wrapper fields required by the current schema: intent, workflow_effect, target_attachment, exactness, confidence, evidence_posture, and repair_ack.\n"
    "Prefer direct top-level item_results as the canonical output surface.\n"
    "If needed for compatibility, you may instead place per-item results in answer_contract.items[].item_results.\n"
    "For listed ingredients, keep food_name at the ingredient level rather than collapsing to the basket name.\n"
    "You may produce item_results, kcal_range, likely_kcal, uncertainty, and evidence_used from packet refs.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response.\n"
    "Compact JSON example:\n"
    "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"intent\":\"estimate_calories\",\"workflow_effect\":\"complete\",\"target_attachment\":{\"kind\":\"food_logging_estimate\"},\"exactness\":\"approximate\",\"confidence\":\"medium\",\"evidence_posture\":\"packetized_generic_db\",\"repair_ack\":false,\"item_results\":[{\"food_name\":\"豆干\",\"kcal_range\":[70,90],\"likely_kcal\":80,\"uncertainty\":\"medium\",\"evidence_used\":[\"generic_food_db:豆干\"]}],\"operations\":[],\"answer_contract\":{}}"
)


PASS_2_B1_004_CLARIFY_ONLY_PAYLOAD = (
    "Phase B-1 B1-004 clarify-only Pass 2 boundary-preservation mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Output exactly one compact JSON object.\n"
    "The first non-whitespace character of your response must be '{'.\n"
    "Keep request_clarification as the canonical outcome.\n"
    "Retain response_mode='clarification', final_action='request_clarification', operations=[], and answer_contract.\n"
    "Do not turn this case into a logged estimate, final calorie answer, mutation, or tool request.\n"
    "Trace-only item_results may appear in the raw model payload, but they must not replace the clarification outcome.\n"
    "Do not replay the runner payload envelope like {\"stage\": ..., \"payload\": ...}.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response.\n"
    "Compact JSON example:\n"
    "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"clarification\",\"final_action\":\"request_clarification\",\"operations\":[],\"answer_contract\":{\"text\":\"Please list the specific items in the basket so I can estimate accurately.\"}}"
)

PHASE_B1_TASK_PAYLOADS: dict[str, str] = {
    PHASE_B1_PASS_1_FORCED_ID: PASS_1_TOOL_REQUEST_PAYLOAD,
    PHASE_B1_PASS_1_COMMON_FOOD_ITEM_ID: PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE + PASS_1_COMMON_FOOD_ITEM_ANTI_FINAL_FRAGMENT,
    PHASE_B1_PASS_1_COMMON_COMMERCIAL_DRINK_ID: PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE + PASS_1_COMMON_COMMERCIAL_DRINK_ANTI_FINAL_FRAGMENT,
    PHASE_B1_PASS_1_COMMON_COMMERCIAL_MEAL_ID: PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE + PASS_1_COMMON_COMMERCIAL_MEAL_ANTI_FINAL_FRAGMENT,
    PHASE_B1_PASS_1_NATURAL_FALLBACK_ID: PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE,
    PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID: PASS_2_B1_004_CLARIFY_ONLY_PAYLOAD,
    PHASE_B1_PASS_2_COMMON_FOOD_ITEM_ID: PASS_2_COMMON_FOOD_ITEM_COMPACT_JSON_FIRST_PAYLOAD,
    PHASE_B1_PASS_2_COMMON_COMMERCIAL_DRINK_ID: PASS_2_COMMON_COMMERCIAL_DRINK_COMPACT_JSON_FIRST_PAYLOAD,
    PHASE_B1_PASS_2_COMMON_COMMERCIAL_MEAL_ID: PASS_2_COMMON_COMMERCIAL_MEAL_COMPACT_JSON_FIRST_PAYLOAD,
    PHASE_B1_PASS_2_LISTED_INGREDIENT_ID: PASS_2_LISTED_INGREDIENT_COMPACT_JSON_FIRST_PAYLOAD,
    PHASE_B1_PASS_2_GENERIC_ID: PASS_2_SYNTHESIS_PAYLOAD,
}


class _ManagerPayloadShapeError(RuntimeError):
    def __init__(
        self,
        *,
        stage: str,
        round_index: int,
        decision_payload: Any,
        partial_trace: dict[str, Any] | None = None,
        reason: str = "manager_payload_shape_error",
        failing_component: str | None = None,
        violation_family: str | None = None,
        actual_shape: str | None = None,
    ) -> None:
        self.stage = stage
        self.round_index = round_index
        self.decision_payload = _json_safe(decision_payload)
        self.partial_trace = _json_safe(partial_trace) if partial_trace is not None else None
        self.reason = reason
        self.failing_component = failing_component
        self.violation_family = violation_family
        self.actual_shape = actual_shape
        excerpt = json.dumps(self.decision_payload, ensure_ascii=False, default=str)[:300]
        super().__init__(f"{reason} stage={stage} round_index={round_index} payload={excerpt}")


class _ProviderTraceShapeError(RuntimeError):
    def __init__(
        self,
        *,
        trace_field: str,
        observed_value: Any,
        stage: str | None,
        failing_component: str,
    ) -> None:
        self.trace_field = trace_field
        self.observed_value = _json_safe(observed_value)
        self.observed_type = _observed_type_name(observed_value)
        self.value_excerpt, self.value_truncated = _value_excerpt(observed_value)
        self.stage = stage
        self.failing_component = failing_component
        super().__init__(
            f"provider_trace_shape_error trace_field={trace_field} observed_type={self.observed_type} stage={stage or 'unknown'}"
        )


def _provider_contract_violation_trace(
    *,
    case_id: str,
    message: str,
    pass1_mode: str,
    trace: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    case_family = (
        str(trace.get("selector_inputs", {}).get("case_family") or "")
        if isinstance(trace.get("selector_inputs"), dict)
        else ""
    ) or _phase_b1_case_family_for_message(message)
    requested_tools = _tool_call_names(payload)
    router_trace = _route_tools(message=message, requested_tools=requested_tools)
    packetizer_outputs: list[dict[str, Any]] = []
    if _is_self_selected_basket_without_ingredients(message):
        packetizer_outputs.append(
            {
                "packet_type": "TaiwanSkillPacket",
                "truth_level": "rule_hint",
                "fixture_id": f"{case_id}_self_selected_basket",
                "fixture_hash": _hash({"case_id": case_id, "rule": "self_selected_basket_without_ingredients"}),
                "fixture_only": True,
                "generated_by": "deterministic_fixture",
                "rule_id": "self_selected_basket_without_ingredients",
            }
        )
    return {
        "case_id": case_id,
        "input_message": message,
        "case_started_at_utc": trace.get("started_at_utc"),
        "case_ended_at_utc": trace.get("ended_at_utc"),
        "case_latency_ms": trace.get("latency_ms"),
        "semantic_boundary": "self_selected_basket_without_ingredients" if _is_self_selected_basket_without_ingredients(message) else None,
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "runner_derived_item_results": False,
        "is_live_tavily_canary": False,
        "uses_deterministic_stub_fixtures": True,
        "stub_fixture_source": "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
        "stub_generated_by_llm": False,
        "manager_pass_1": {
            "manager_round": 0,
            "manager_role": "pass_1_tool_request",
            "prompt_hash": _case_prompt_hash(
                manager_role="pass_1_tool_request",
                pass1_mode=pass1_mode,
                case_family=case_family,
            ),
            "started_at_utc": trace.get("started_at_utc"),
            "ended_at_utc": trace.get("ended_at_utc"),
            "latency_ms": trace.get("latency_ms"),
            "provider_params": _provider_params(trace),
            "phase_b1_task_payload_id": trace.get("phase_b1_task_payload_id"),
            "phase_b1_task_payload_hash": trace.get("phase_b1_task_payload_hash"),
            "selector_inputs": _selector_trace_dict(trace, "selector_inputs"),
            "manager_contract_selection": _selector_trace_dict(trace, "manager_contract_selection"),
            "provider_profile_selection": _selector_trace_dict(trace, "provider_profile_selection"),
            "requested_read_tools": requested_tools,
            "forbidden_final_truth_fields_present": _contains_any_key(payload, PASS_1_FORBIDDEN_FIELDS),
            **_payload_shape_fields(payload),
        },
        "runtime_tool_router": router_trace,
        "read_tool_executions": [],
        "packetizer": {
            "outputs": packetizer_outputs,
            "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"}),
        },
        "manager_pass_2": {
            "manager_round": 1,
            "manager_role": "pass_2_synthesis",
            "prompt_hash": _case_prompt_hash(
                manager_role="pass_2_synthesis",
                pass1_mode=pass1_mode,
                case_family=case_family,
            ),
            "started_at_utc": None,
            "ended_at_utc": None,
            "latency_ms": None,
            "provider_params": {"provider": None, "model": None, "request_id": None},
            "phase_b1_task_payload_id": None,
            "phase_b1_task_payload_hash": None,
            "selector_inputs": _selector_inputs_trace(
                case_family=case_family,
                manager_role="pass_2_synthesis",
                probe_mode=pass1_mode,
                case_id=case_id,
            ),
            "manager_contract_selection": _manager_contract_selection_trace(
                manager_role="pass_2_synthesis",
                probe_mode=NATURAL_MODE,
                case_family=case_family,
            ),
            "provider_profile_selection": {},
            "item_results": [],
            "mutation_attempted": False,
            "forbidden_mutation_fields_present": [],
            "decision_payload": None,
            "decision_payload_type": None,
            "payload_shape_valid": True,
            "payload_shape_error": None,
        },
        "mutation": {
            "mutation_attempted": False,
            "reason": "no_mutation_intent",
            "mutation_result": None,
        },
        "guard": {"ran": True, "ran_before_mutation": True, "result": "no_mutation"},
        "renderer": {"input": {}, "final_response": "", "invented_facts": []},
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _elapsed_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _case_ids_for_smoke_cases(smoke_cases: list[str] | tuple[str, ...]) -> list[str]:
    resolved: list[str] = []
    for index, message in enumerate(smoke_cases, start=1):
        case_id = next((candidate for candidate, candidate_message in CORE_SMOKE_CASE_MAP.items() if candidate_message == message), None)
        resolved.append(case_id or f"CUSTOM-{index:03d}")
    return resolved


def _resolve_targeted_smoke_cases(raw_case_ids: str) -> dict[str, Any]:
    requested = [item.strip().upper() for item in raw_case_ids.split(",") if item.strip()]
    deduped = _dedup_preserve_order(requested)
    invalid = [item for item in deduped if item not in CORE_SMOKE_CASE_MAP]
    if invalid:
        legal = ", ".join(CORE_SMOKE_CASE_IDS)
        raise ValueError(f"Invalid Phase B-1 case id(s): {', '.join(invalid)}. Legal case ids: {legal}.")
    return {
        "case_set": "targeted",
        "requested_case_ids": deduped,
        "smoke_cases": [CORE_SMOKE_CASE_MAP[item] for item in deduped],
    }


def _mode_slug(pass1_mode: str) -> str:
    return "natural-probe" if pass1_mode == NATURAL_MODE else "forced"


def _case_ids_slug(requested_case_ids: list[str]) -> str:
    return "-".join(requested_case_ids) if requested_case_ids else "no-cases"


def _phase_b1_provider_profile(profile_id: str) -> _PhaseB1ProviderProfile:
    raw = PHASE_B1_PROVIDER_PROFILES[profile_id]
    return _PhaseB1ProviderProfile(profile_id=profile_id, **raw)


def _default_phase_b1_provider_profile() -> _PhaseB1ProviderProfile:
    return _phase_b1_provider_profile("builderspace-deepseek-default")


def _resolve_phase_b1_provider_profile(
    *,
    requested_profile_id: str | None,
    case_set: str,
    requested_case_ids: list[str],
    allow_expensive_model_probe: bool,
) -> _PhaseB1ProviderProfile:
    default_profile = _default_phase_b1_provider_profile()
    if not requested_profile_id:
        return default_profile
    profile = _phase_b1_provider_profile(requested_profile_id)
    if profile.cost_tier == "high" and not allow_expensive_model_probe:
        raise ValueError("expensive provider profile is disabled by default")
    if not phase_b1_local_diagnostic_requested_profile_allowed(
        requested_profile_id=requested_profile_id,
        case_set=case_set,
        requested_case_ids=requested_case_ids,
    ):
        return default_profile
    return profile


def _profile_applies_to_round(
    profile: _PhaseB1ProviderProfile,
    *,
    manager_role: str,
    constraints: dict[str, Any],
) -> bool:
    if profile.default_for_build_loop:
        return True
    if profile.manager_role_scope and manager_role != profile.manager_role_scope:
        return False
    if profile.branch_scope and constraints.get("phase_b1_case_family") != profile.branch_scope:
        return False
    return True


def _resolve_round_phase_b1_profile_route(
    *,
    selected_profile: _PhaseB1ProviderProfile,
    requested_profile_id: str | None,
    case_set: str,
    pass1_mode: str,
    manager_role: str,
    constraints: dict[str, Any],
) -> _PhaseB1ProfileRoute:
    default_profile = _default_phase_b1_provider_profile()
    decision = select_phase_b1_profile_route(
        case_set=case_set,
        requested_profile_id=requested_profile_id,
        probe_mode=pass1_mode,
        manager_role=manager_role,
        case_id=str(constraints.get("phase_b1_case_id") or ""),
        case_family=str(constraints.get("phase_b1_case_family") or "") or None,
        selected_profile_id=selected_profile.profile_id,
        default_profile_id=default_profile.profile_id,
        profile_applies=_profile_applies_to_round(selected_profile, manager_role=manager_role, constraints=constraints),
    )
    return _PhaseB1ProfileRoute(
        profile=_phase_b1_provider_profile(decision.profile_id),
        route_mode=decision.route_mode,
        route_reason=decision.route_reason,
        rule_id=decision.route_rule_id,
        routing_scope=decision.route_scope,
        artifact_basis=decision.artifact_basis,
        uses_case_id_local_debt=decision.uses_case_id_local_debt,
        should_migrate_post_b1=decision.should_migrate_post_b1,
    )


def _apply_profile_override(provider: Any, profile: _PhaseB1ProviderProfile) -> dict[str, Any]:
    original: dict[str, Any] = {}
    if hasattr(provider, "manager_model"):
        original["manager_model"] = getattr(provider, "manager_model")
        setattr(provider, "manager_model", profile.model)
    if hasattr(provider, "manager_temperature") and profile.temperature is not None:
        original["manager_temperature"] = getattr(provider, "manager_temperature")
        setattr(provider, "manager_temperature", profile.temperature)
    if hasattr(provider, "model"):
        original["model"] = getattr(provider, "model")
        setattr(provider, "model", profile.model)
    if hasattr(provider, "temperature") and profile.temperature is not None:
        original["temperature"] = getattr(provider, "temperature")
        setattr(provider, "temperature", profile.temperature)
    return original


def _restore_profile_override(provider: Any, original: dict[str, Any]) -> None:
    for key, value in original.items():
        setattr(provider, key, value)


def _inject_provider_profile_trace_fields(
    trace: dict[str, Any],
    *,
    route: _PhaseB1ProfileRoute,
) -> None:
    profile = route.profile
    trace["provider_profile_id"] = profile.profile_id
    trace["provider_profile_provider"] = profile.provider
    trace["provider_profile_model"] = profile.model
    trace["provider_profile_cost_tier"] = profile.cost_tier
    trace["provider_profile_manual_only"] = profile.manual_only
    trace["provider_profile_role"] = profile.provider_profile_role
    trace["provider_profile_transport_mode"] = profile.transport_mode
    trace["provider_profile_selection_reason"] = profile.selection_reason
    trace["manager_candidate_status"] = profile.manager_candidate_status
    trace["documented_reasoning_status"] = profile.documented_reasoning_status
    trace["documented_tool_call_support"] = profile.documented_tool_call_support
    trace["production_selected"] = profile.production_selected
    trace["allow_expensive_model_probe"] = profile.allow_expensive_model_probe
    trace["artifact_tool_call_reliability"] = profile.artifact_tool_call_reliability
    trace["provider_profile_route_mode"] = route.route_mode
    trace["provider_profile_route_reason"] = route.route_reason
    trace["profile_routing_rule_id"] = route.rule_id
    trace["profile_routing_scope"] = route.routing_scope
    trace["profile_routing_artifact_basis"] = route.artifact_basis
    trace["provider_profile_route_uses_case_id_local_debt"] = route.uses_case_id_local_debt
    trace["provider_profile_should_migrate_post_b1"] = route.should_migrate_post_b1


def _build_artifact_path(
    *,
    output_dir: Path,
    pass1_mode: str,
    case_set: str,
    requested_case_ids: list[str],
) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    suffix = uuid4().hex[:6]
    filename = (
        f"wave1_phase_b_minimal_tool_loop_smoke_{timestamp}_{_mode_slug(pass1_mode)}_"
        f"{case_set}_{_case_ids_slug(requested_case_ids)}_{suffix}.json"
    )
    return output_dir / filename


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _prompt_hash(*, manager_role: str, case_family: str | None = None) -> str:
    if manager_role == "pass_1_tool_request":
        _, task_payload = _pass_1_task_payload(FORCED_MODE, case_family=case_family)
    else:
        _, task_payload = _pass_2_task_payload(case_family=case_family)
    return _hash({"manager_role": manager_role, "system_prompt": SINGLE_MANAGER_SYSTEM_PROMPT, "task_payload": task_payload})


def _selector_inputs_trace(
    *,
    case_family: str | None,
    manager_role: str,
    probe_mode: str,
    case_id: str | None = None,
) -> dict[str, Any]:
    return build_phase_b1_selector_inputs(
        case_family=case_family,
        manager_role=manager_role,
        probe_mode=probe_mode,
        case_id=case_id,
    ).to_trace_dict()


def _manager_contract_selection_trace(
    *,
    manager_role: str,
    probe_mode: str,
    case_family: str | None,
) -> dict[str, Any]:
    return select_phase_b1_task_payload(
        manager_role=manager_role,
        probe_mode=probe_mode,
        case_family=case_family,
    ).to_trace_dict()


def _pass_1_task_payload(pass1_mode: str, *, case_family: str | None = None) -> tuple[str, str]:
    selection = select_phase_b1_task_payload(
        manager_role="pass_1_tool_request",
        probe_mode=pass1_mode,
        case_family=case_family,
    )
    return selection.task_payload_id, PHASE_B1_TASK_PAYLOADS[selection.task_payload_id]


def _pass_2_task_payload(*, case_family: str | None) -> tuple[str, str]:
    selection = select_phase_b1_task_payload(
        manager_role="pass_2_synthesis",
        probe_mode=NATURAL_MODE,
        case_family=case_family,
    )
    return selection.task_payload_id, PHASE_B1_TASK_PAYLOADS[selection.task_payload_id]


def _task_payload_for_round(*, round_index: int, pass1_mode: str, case_family: str | None) -> tuple[str, str]:
    if round_index == 0:
        return _pass_1_task_payload(pass1_mode, case_family=case_family)
    return _pass_2_task_payload(case_family=case_family)


def _case_prompt_hash(*, manager_role: str, pass1_mode: str, case_family: str | None = None) -> str:
    if manager_role == "pass_1_tool_request":
        _, task_payload = _pass_1_task_payload(pass1_mode, case_family=case_family)
    else:
        _, task_payload = _pass_2_task_payload(case_family=case_family)
    return _hash({"manager_role": manager_role, "system_prompt": SINGLE_MANAGER_SYSTEM_PROMPT, "task_payload": task_payload})


def _provider_profile_selection_trace(route: _PhaseB1ProfileRoute) -> dict[str, Any]:
    return {
        "provider_profile_id": route.profile.profile_id,
        "route_mode": route.route_mode,
        "route_reason": route.route_reason,
        "route_rule_id": route.rule_id,
        "route_scope": route.routing_scope,
        "artifact_basis": route.artifact_basis,
        "uses_case_id_local_debt": route.uses_case_id_local_debt,
        "should_migrate_post_b1": route.should_migrate_post_b1,
    }


def _selector_trace_dict(trace: dict[str, Any], key: str) -> dict[str, Any]:
    value = trace.get(key)
    return _json_safe(value) if isinstance(value, dict) else {}


def _provider_params(trace: dict[str, Any]) -> dict[str, Any]:
    return {key: trace.get(key) for key in PROVIDER_PARAM_KEYS}


def _observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return "unknown"


def _value_excerpt(value: Any, *, max_chars: int = 1000) -> tuple[str, bool]:
    rendered = json.dumps(_json_safe(value), ensure_ascii=False, default=str)
    if len(rendered) <= max_chars:
        return rendered, False
    return rendered[:max_chars], True


def _looks_like_length_truncated_json_attempt(*, finish_reason: Any, raw_content_excerpt: Any, value_excerpt: Any) -> bool:
    if str(finish_reason or "") != "length":
        return False
    excerpt = ""
    if isinstance(raw_content_excerpt, str) and raw_content_excerpt:
        excerpt = raw_content_excerpt
    elif isinstance(value_excerpt, str):
        excerpt = value_excerpt
    if not excerpt:
        return False
    if "```json" in excerpt.lower():
        return True
    return bool(re.search(r'\{\s*"[A-Za-z_]', excerpt)) and not excerpt.rstrip().endswith("}")


def _require_trace_shape(
    *,
    value: Any,
    trace_field: str,
    expected_type: type[Any] | tuple[type[Any], ...],
    stage: str | None,
    failing_component: str,
) -> Any:
    if isinstance(value, expected_type):
        return value
    raise _ProviderTraceShapeError(
        trace_field=trace_field,
        observed_value=value,
        stage=stage,
        failing_component=failing_component,
    )


def _normalize_provider_trace(trace: Any, *, manager_role: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    stage = None
    normalized = dict(
        _require_trace_shape(
            value=trace,
            trace_field="trace",
            expected_type=dict,
            stage=stage,
            failing_component="normalize_provider_trace",
        )
    )
    stage = str(normalized.get("stage")) if normalized.get("stage") not in (None, "") else None
    raw_request_payload = normalized.get("request_payload")
    if raw_request_payload is None:
        request_payload: dict[str, Any] = {}
    else:
        request_payload = dict(
            _require_trace_shape(
                value=raw_request_payload,
                trace_field="request_payload",
                expected_type=dict,
                stage=stage,
                failing_component="normalize_provider_trace",
            )
        )
    for field_name in ("transport_attempts", "parse_attempts"):
        raw_value = normalized.get(field_name)
        if raw_value is not None:
            _require_trace_shape(
                value=raw_value,
                trace_field=field_name,
                expected_type=list,
                stage=stage,
                failing_component="normalize_provider_trace",
            )
    def pick(key: str, fallback: Any) -> Any:
        value = normalized.get(key)
        return fallback if value in (None, "") else value

    normalized.setdefault("provider", "builderspace")
    normalized.setdefault("model", request_payload.get("model"))
    normalized["temperature"] = pick("temperature", request_payload.get("temperature"))
    normalized["max_tokens"] = pick("max_tokens", request_payload.get("max_tokens"))
    normalized["response_format"] = pick("response_format", request_payload.get("response_format"))
    normalized["timeout"] = pick("timeout", normalized.get("timeout_seconds"))
    normalized["retry_policy"] = pick("retry_policy", {"source": "provider_trace_unavailable"})
    normalized["tool_choice"] = pick("tool_choice", "none")
    if not normalized.get("request_id"):
        normalized["request_id"] = f"phase_b1_{manager_role}_{_hash({'user_payload': user_payload, 'raw_content': normalized.get('raw_content')})}"
    return normalized


class _PhaseB1ManagerProvider:
    def __init__(
        self,
        provider: Any,
        *,
        pass1_mode: str,
        provider_timeout_ms: int,
        provider_profile: _PhaseB1ProviderProfile,
        case_set: str,
        requested_profile_id: str | None,
    ) -> None:
        self._provider = provider
        self.pass1_mode = pass1_mode
        self.provider_timeout_ms = provider_timeout_ms
        self.provider_profile = provider_profile
        self.case_set = case_set
        self.requested_profile_id = requested_profile_id
        self._current_case_rounds: list[dict[str, Any]] = []

    def begin_case(self) -> None:
        self._current_case_rounds = []

    def case_rounds(self) -> list[dict[str, Any]]:
        return _json_safe(self._current_case_rounds)

    def readiness(self) -> dict[str, Any]:
        if hasattr(self._provider, "readiness"):
            readiness = self._provider.readiness()
            return dict(readiness or {})
        return {"configured": False, "reason": "provider_missing_readiness"}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        round_index = int(user_payload.get("round_index") or 0)
        manager_role = "pass_1_tool_request" if round_index == 0 else "pass_2_synthesis"
        raw_user_input = str(user_payload.get("raw_user_input") or "")
        case_family = str(user_payload.get("constraints", {}).get("phase_b1_case_family") or "") or None
        if case_family is None:
            derived_case_family = _phase_b1_case_family_for_message(raw_user_input)
            case_family = derived_case_family or None
        task_payload_id, task_payload = _task_payload_for_round(
            round_index=round_index,
            pass1_mode=self.pass1_mode,
            case_family=case_family,
        )
        constraints = dict(user_payload.get("constraints") or {})
        constraints.update(
            {
                "phase_b1_manager_role": manager_role,
                "phase_b1_pass1_mode": self.pass1_mode,
                "phase_b1_task_payload_id": task_payload_id,
            }
        )
        if case_family:
            constraints["phase_b1_case_family"] = case_family
        user_payload["constraints"] = constraints
        kwargs["user_payload"] = user_payload
        selector_inputs_trace = _selector_inputs_trace(
            case_family=case_family,
            manager_role=manager_role,
            probe_mode=self.pass1_mode,
            case_id=str(constraints.get("phase_b1_case_id") or "") or None,
        )
        manager_contract_selection = _manager_contract_selection_trace(
            manager_role=manager_role,
            probe_mode=self.pass1_mode if round_index == 0 else NATURAL_MODE,
            case_family=case_family,
        )
        route = _resolve_round_phase_b1_profile_route(
            selected_profile=self.provider_profile,
            requested_profile_id=self.requested_profile_id,
            case_set=self.case_set,
            pass1_mode=self.pass1_mode,
            manager_role=manager_role,
            constraints=constraints,
        )
        provider_profile_selection = _provider_profile_selection_trace(route)
        active_profile = route.profile
        if round_index == 0 and self.pass1_mode == NATURAL_MODE:
            kwargs["system_prompt"] = f"{task_payload}\n\n{str(kwargs.get('system_prompt') or '')}"
        elif round_index == 0 and self.pass1_mode == FORCED_MODE:
            kwargs["system_prompt"] = task_payload
        else:
            kwargs["system_prompt"] = f"{task_payload}\n\n{kwargs.get('system_prompt')}\n\n{task_payload}"
        started_at_utc = _utc_now()
        started_perf = time.perf_counter()
        original_provider_state = _apply_profile_override(self._provider, active_profile)
        try:
            payload, trace = await asyncio.wait_for(
                self._provider.complete_with_trace(**kwargs),
                timeout=self.provider_timeout_ms / 1000,
            )
        except Exception as exc:
            _restore_profile_override(self._provider, original_provider_state)
            provider_trace = dict(getattr(exc, "trace", {}) or {}) if isinstance(getattr(exc, "trace", {}), dict) else {}
            _inject_provider_profile_trace_fields(provider_trace, route=route)
            setattr(exc, "trace", provider_trace)
            failure_family = provider_trace.get("failure_family") or provider_trace.get("request_failure_family")
            if round_index == 0 and failure_family == MANAGER_OUTPUT_CONTRACT_VIOLATION:
                normalized_trace = _normalize_provider_trace(provider_trace, manager_role=manager_role, user_payload=user_payload)
                normalized_trace["manager_role"] = manager_role
                normalized_trace["pass1_mode"] = self.pass1_mode
                normalized_trace["started_at_utc"] = started_at_utc
                normalized_trace["ended_at_utc"] = _utc_now()
                normalized_trace["latency_ms"] = _elapsed_ms(started_perf)
                normalized_trace["phase_b1_task_payload_id"] = constraints["phase_b1_task_payload_id"]
                normalized_trace["phase_b1_task_payload_hash"] = _hash(task_payload)
                normalized_trace["selector_inputs"] = selector_inputs_trace
                normalized_trace["manager_contract_selection"] = manager_contract_selection
                normalized_trace["provider_profile_selection"] = provider_profile_selection
                parsed_payload = provider_trace.get("parsed_object") if isinstance(provider_trace.get("parsed_object"), dict) else {}
                partial_trace = _provider_contract_violation_trace(
                    case_id=str(user_payload.get("constraints", {}).get("phase_b1_case_id") or ""),
                    message=str(user_payload.get("raw_user_input") or ""),
                    pass1_mode=self.pass1_mode,
                    trace=normalized_trace,
                    payload=parsed_payload,
                )
                raise _ManagerPayloadShapeError(
                    stage=manager_role,
                    round_index=round_index,
                    decision_payload=parsed_payload,
                    partial_trace=partial_trace,
                    reason=MANAGER_OUTPUT_CONTRACT_VIOLATION,
                    failing_component=str(provider_trace.get("failing_component") or "provider_adapter.branch_validation"),
                    violation_family=str(provider_trace.get("violation_family") or MANAGER_CONTRACT_VALIDATION_ERROR),
                    actual_shape=str(provider_trace.get("actual_shape") or _pass1_actual_shape(payload=parsed_payload, requested_tools=_tool_call_names(parsed_payload))),
                ) from exc
            raise
        _restore_profile_override(self._provider, original_provider_state)
        ended_at_utc = _utc_now()
        latency_ms = _elapsed_ms(started_perf)
        trace = _normalize_provider_trace(trace, manager_role=manager_role, user_payload=user_payload)
        _inject_provider_profile_trace_fields(trace, route=route)
        trace["manager_role"] = manager_role
        trace["pass1_mode"] = self.pass1_mode
        trace["started_at_utc"] = started_at_utc
        trace["ended_at_utc"] = ended_at_utc
        trace["latency_ms"] = latency_ms
        trace["phase_b1_task_payload_id"] = constraints["phase_b1_task_payload_id"]
        trace["phase_b1_task_payload_hash"] = _hash(task_payload)
        trace["selector_inputs"] = selector_inputs_trace
        trace["manager_contract_selection"] = manager_contract_selection
        trace["provider_profile_selection"] = provider_profile_selection
        self._current_case_rounds.append(
            {
                "round_index": round_index,
                "stage": MANAGER_LOOP_STAGE,
                "decision": _json_safe(payload),
                "trace": _json_safe(trace),
            }
        )
        if not isinstance(payload, dict):
            raise _ManagerPayloadShapeError(
                stage=manager_role,
                round_index=round_index,
                decision_payload=payload,
            )
        if round_index == 0 and self.pass1_mode == NATURAL_MODE:
            _validate_b1_natural_pass1_contract(
                payload=payload,
                raw_user_input=str(user_payload.get("raw_user_input") or ""),
            )
        return payload, trace


def _contains_any_key(value: Any, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(key)
            found.extend(_contains_any_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(_contains_any_key(item, keys))
    return sorted(set(found))


def _payload_shape_fields(payload: Any) -> dict[str, Any]:
    safe_payload = _json_safe(payload)
    payload_type = type(payload).__name__
    return {
        "decision_payload": safe_payload if isinstance(payload, dict) else None,
        "decision_payload_type": payload_type,
        "payload_shape_valid": isinstance(payload, dict),
        "payload_shape_error": None if isinstance(payload, dict) else f"expected_object_got_{payload_type}",
    }


def _ensure_decision_payload_dict(
    *,
    payload: Any,
    stage: str,
    round_index: int,
    partial_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    raise _ManagerPayloadShapeError(
        stage=stage,
        round_index=round_index,
        decision_payload=payload,
        partial_trace=partial_trace,
    )


def _tool_call_names(payload: dict[str, Any]) -> list[str]:
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    names: list[str] = []
    for item in tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
            if name:
                names.append(name)
    return names


def _contains_estimate_fields(payload: dict[str, Any]) -> bool:
    return any(_contains_any_key(payload, {key_name}) for key_name in ("item_results", "kcal_range", "likely_kcal"))


def _pass1_actual_shape(*, payload: dict[str, Any], requested_tools: list[str] | None = None) -> str:
    requested = list(requested_tools or [])
    manager_action = str(payload.get("manager_action") or "")
    final_action = str(payload.get("final_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    mutation_intent = bool(payload.get("mutation_intent"))
    tool_call_names = _tool_call_names(payload)
    actual_parts: list[str] = []
    if manager_action:
        actual_parts.append(manager_action)
    if final_action:
        actual_parts.append(final_action)
    if tool_call_names:
        actual_parts.extend(tool_call_names)
    elif requested:
        actual_parts.extend(requested)
    if response_mode:
        actual_parts.append(f"response_mode={response_mode}")
    if workflow_effect:
        actual_parts.append(f"workflow_effect={workflow_effect}")
    if uncertainty_posture:
        actual_parts.append(f"uncertainty_posture={uncertainty_posture}")
    if _contains_estimate_fields(payload):
        actual_parts.append("pass1_estimate_fields")
    if mutation_intent:
        actual_parts.append("mutation_intent=true")
    return ".".join(actual_parts) if actual_parts else "empty"


def _validate_b1_natural_pass1_contract(*, payload: dict[str, Any], raw_user_input: str) -> None:
    if not _is_self_selected_basket_without_ingredients(raw_user_input):
        return
    manager_action = str(payload.get("manager_action") or "")
    final_action = str(payload.get("final_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    requested_tools = _tool_call_names(payload)
    has_logging_or_intake_signals = (
        response_mode == "intake_result"
        or workflow_effect in {"logging", "commit", "log_pending", "pass_to_next_round", "record_food"}
        or final_action in {"log_food", "log_consumption", "record_food", "commit"}
        or uncertainty_posture == "high_variance_generic_item"
        or bool(payload.get("mutation_intent"))
    )
    valid_shape = (
        manager_action == "final"
        and final_action == "request_clarification"
        and response_mode == "clarification"
        and not requested_tools
        and not _contains_estimate_fields(payload)
        and not has_logging_or_intake_signals
    )
    if valid_shape:
        return
    raise _ManagerPayloadShapeError(
        stage="pass_1_tool_request",
        round_index=0,
        decision_payload=payload,
        reason="manager_output_contract_violation",
        failing_component="phase_b1_manager_provider.pass1_branch_validation",
        violation_family="clarification_branch_conflicting_fields",
        actual_shape=_pass1_actual_shape(payload=payload, requested_tools=requested_tools),
    )


def _is_self_selected_basket_without_ingredients(message: str) -> bool:
    return message.strip() == str(CORE_SMOKE_CASE_MAP.get("B1-004") or "")


def _is_listed_ingredient_basket(message: str) -> bool:
    return message.strip() == str(CORE_SMOKE_CASE_MAP.get("B1-005") or "")


def _phase_b1_case_family_for_message(message: str) -> str | None:
    normalized = message.strip()
    if normalized == str(CORE_SMOKE_CASE_MAP.get("B1-004") or ""):
        return B1_COMPOSITION_UNKNOWN_CASE_FAMILY
    if normalized == str(CORE_SMOKE_CASE_MAP.get("B1-005") or ""):
        return B1_LISTED_INGREDIENT_CASE_FAMILY
    if normalized == str(CORE_SMOKE_CASE_MAP.get("B1-001") or ""):
        return B1_COMMON_FOOD_ITEM_CASE_FAMILY
    if normalized in {
        str(CORE_SMOKE_CASE_MAP.get("B1-002") or ""),
        str(CORE_SMOKE_CASE_MAP.get("B1-006") or ""),
    }:
        return B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY
    if normalized == str(CORE_SMOKE_CASE_MAP.get("B1-003") or ""):
        return B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY
    return None


def _is_common_food_item(message: str) -> bool:
    return _phase_b1_case_family_for_message(message) == B1_COMMON_FOOD_ITEM_CASE_FAMILY


def _is_common_commercial_drink(message: str) -> bool:
    return _phase_b1_case_family_for_message(message) == B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY


def _is_common_commercial_meal(message: str) -> bool:
    return _phase_b1_case_family_for_message(message) == B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY


def _is_no_mutation_query(message: str) -> bool:
    return "多少熱量" in message or "大概多少熱量" in message


def _fixture_packet(*, case_id: str, tool_name: str, food_name: str, truth_level: str = "candidate") -> dict[str, Any]:
    fixture_id = f"{case_id}_{tool_name}_{_hash(food_name)}"
    if tool_name == "load_taiwan_food_semantics_skill":
        return {
            "packet_type": "TaiwanSkillPacket",
            "truth_level": "rule_hint",
            "fixture_id": fixture_id,
            "fixture_hash": _hash({"fixture_id": fixture_id, "food_name": food_name, "tool_name": tool_name}),
            "fixture_only": True,
            "generated_by": "deterministic_fixture",
            "rule_id": "taiwan_food_semantic_hint",
            "trigger_food_name": food_name,
        }
    packet_type = "GenericFoodDbPacket" if tool_name == "lookup_generic_food" else "SearchCandidatePacket"
    packet = {
        "packet_type": packet_type,
        "truth_level": truth_level,
        "fixture_id": fixture_id,
        "fixture_hash": _hash({"fixture_id": fixture_id, "food_name": food_name, "tool_name": tool_name}),
        "fixture_only": True,
        "generated_by": "deterministic_fixture",
        "candidates": [{"food_name": food_name, "kcal_range": [70, 90], "likely_kcal": 80}],
    }
    if packet_type == "SearchCandidatePacket":
        packet.update(
            {
                "query": food_name,
                "source_quality_label": "third_party",
                "candidates": [{"food_name": food_name, "url": "https://example.test/phase-b1", "snippet": "candidate only"}],
            }
        )
    return packet


def _raw_stub_output(*, case_id: str, tool_name: str, food_name: str) -> dict[str, Any]:
    return {
        "truth_level": "candidate",
        "fixture_id": f"raw_{case_id}_{tool_name}_{_hash(food_name)}",
        "fixture_only": True,
        "generated_by": "deterministic_fixture",
        "candidate": {"food_name": food_name},
    }


def _food_names_for_message(message: str) -> list[str]:
    if "豆干" in message and "海帶" in message and "貢丸" in message:
        return ["豆干", "海帶", "貢丸"]
    if "珍珠奶茶" in message:
        return ["珍珠奶茶"]
    if "便當" in message:
        return ["便當"]
    if "滷味" in message:
        return ["滷味"]
    return ["茶葉蛋"]


def _route_tools(*, message: str, requested_tools: list[str]) -> dict[str, Any]:
    supported_tools = list(AVAILABLE_READ_TOOLS)
    supported_tool_set = set(supported_tools)
    blocked_tools: list[str] = []
    block_reasons: list[dict[str, Any]] = []
    for tool_name in requested_tools:
        if tool_name not in supported_tool_set:
            blocked_tools.append(tool_name)
            block_reasons.append(
                {
                    "tool_name": tool_name,
                    "reason": "unsupported_read_tool_name",
                    "supported_tools": supported_tools,
                    "normalization_attempted": False,
                }
            )
    if _is_self_selected_basket_without_ingredients(message):
        for tool_name in sorted(ESTIMATE_READ_TOOLS):
            if tool_name not in blocked_tools:
                blocked_tools.append(tool_name)
            block_reasons.append(
                {
                    "tool_name": tool_name,
                    "reason": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                    "rule": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                    "detail": "Composition is unknown; ask for ingredients before generic DB or web estimate.",
                }
            )
    blocked_tool_set = set(blocked_tools)
    allowed_tools = [tool for tool in requested_tools if tool in supported_tool_set and tool not in blocked_tool_set]
    return {
        "available_read_tools": supported_tools,
        "canonical_tool_catalog_hash": _hash(supported_tools),
        "requested_read_tools": list(requested_tools),
        "manager_requested_tools": list(requested_tools),
        "allowed_tools": allowed_tools,
        "filtered_tool_plan": list(allowed_tools),
        "blocked_tools": blocked_tools,
        "block_reasons": block_reasons,
    }


def _renderer_trace(*, item_results: list[dict[str, Any]], mutation: dict[str, Any]) -> dict[str, Any]:
    return {
        "input": {
            "allowed_facts": ["item_results", "ledger_mutation_result"],
            "forbidden_claims": ["invent calories not in item_results", "invent logged status outside mutation_result"],
            "item_results": item_results,
            "ledger_mutation_result": mutation["mutation_result"],
        },
        "final_response": "Renderer mirrors allowed facts.",
        "invented_facts": [],
    }


def _mutation_trace(*, message: str, item_results: list[dict[str, Any]]) -> dict[str, Any]:
    if _is_no_mutation_query(message) or _is_self_selected_basket_without_ingredients(message):
        return {"mutation_attempted": False, "reason": "no_mutation_intent", "mutation_result": None}
    if not item_results:
        return {"mutation_attempted": False, "reason": "missing_item_results_guard", "mutation_result": None}
    return {
        "mutation_attempted": True,
        "reason": "guard_approved_logging",
        "mutation_result": {"truth_level": "mutation_result", "ledger_item_ids": [f"item_{_hash(item_results)}"]},
    }


def _should_complete_b1_004_pass2_trace(
    *,
    case_id: str,
    message: str,
    pass1_mode: str,
    rounds: list[dict[str, Any]],
    pass1_decision: dict[str, Any],
    router_trace: dict[str, Any],
    packetizer_outputs: list[dict[str, Any]],
) -> bool:
    return (
        case_id == "B1-004"
        and pass1_mode == NATURAL_MODE
        and _is_self_selected_basket_without_ingredients(message)
        and len(rounds) == 1
        and bool(packetizer_outputs)
        and str(pass1_decision.get("manager_action") or "") == "final"
        and str(pass1_decision.get("final_action") or "") == "request_clarification"
        and str(pass1_decision.get("response_mode") or "") == "clarification"
        and not (router_trace.get("requested_read_tools") or [])
        and not _tool_call_names(pass1_decision)
    )


def _b1_004_packetizer_hint_tool_results(packetizer_outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tool_name": "packetize_food_evidence",
            "truth_level": "hint",
            "packetizer_outputs": _json_safe(packetizer_outputs),
        }
    ]


async def _complete_b1_004_real_pass2_trace(
    *,
    provider: Any,
    message: str,
    resolved_state_payload: Any,
    constraints: dict[str, Any],
    packetizer_outputs: list[dict[str, Any]],
) -> None:
    await provider.complete_with_trace(
        system_prompt=SINGLE_MANAGER_SYSTEM_PROMPT,
        user_payload={
            "raw_user_input": message,
            "resolved_state": resolved_state_payload,
            "available_tools": list(AVAILABLE_READ_TOOLS),
            "tool_results": _b1_004_packetizer_hint_tool_results(packetizer_outputs),
            "round_index": 1,
            "constraints": dict(constraints),
            "guard_feedback": None,
        },
        stage=MANAGER_LOOP_STAGE,
        max_tokens=900,
    )


def _allow_root_answer_contract_item_results_bridge(*, case_id: str, message: str) -> bool:
    return case_id == "B1-003" and _phase_b1_case_family_for_message(message) == B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY


def _item_results_from_payload(
    payload: dict[str, Any],
    packets: list[dict[str, Any]],
    *,
    allow_packet_fallback: bool,
    allow_root_answer_contract_bridge: bool,
    allow_nested_answer_contract_bridge: bool,
) -> tuple[list[dict[str, Any]], bool, str, str | None, list[str]]:
    raw_item_results = payload.get("item_results")
    if isinstance(raw_item_results, list) and raw_item_results:
        return [dict(item) for item in raw_item_results if isinstance(item, dict)], False, "manager_pass_2_payload", None, []
    if allow_root_answer_contract_bridge:
        bridged, parent_fallback_fields = _item_results_from_answer_contract_root(payload, packets)
        if bridged:
            return bridged, False, "answer_contract_bridge", "answer_contract.item_results", parent_fallback_fields
    if allow_nested_answer_contract_bridge:
        bridged = _item_results_from_answer_contract_nested(payload, packets)
        if bridged:
            return bridged, False, "answer_contract_bridge", "answer_contract.items[].item_results", []
    if not allow_packet_fallback:
        return [], False, "none", None, []
    results: list[dict[str, Any]] = []
    for packet in packets:
        candidates = packet.get("candidates") if isinstance(packet, dict) else None
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if isinstance(candidate, dict):
                results.append(
                    {
                        "food_name": candidate.get("food_name"),
                        "kcal_range": candidate.get("kcal_range"),
                        "likely_kcal": candidate.get("likely_kcal"),
                        "uncertainty": "moderate",
                        "evidence_used": [packet.get("fixture_id")],
                    }
                )
    return results, bool(results), ("runner_packet_fallback" if results else "none"), None, []


def _item_results_owner_class(*, item_results_source: str, runner_derived_item_results: bool) -> str:
    if runner_derived_item_results or item_results_source == "runner_packet_fallback":
        return "runner_fallback"
    if item_results_source == "manager_pass_2_payload":
        return "runtime_payload"
    if item_results_source == "answer_contract_bridge":
        return "compatibility_bridge"
    return "none"


def _item_results_from_answer_contract_root(
    payload: dict[str, Any], packets: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    answer_contract = payload.get("answer_contract")
    if not isinstance(answer_contract, dict):
        return [], []
    items = answer_contract.get("item_results")
    if not isinstance(items, list):
        return [], []
    packet_refs = _packet_fixture_ids_by_food_name(packets)
    bridged: list[dict[str, Any]] = []
    parent_fallback_fields: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized_food_name = _normalize_item_level_food_name(
            str(item.get("food_name") or item.get("item_name") or "")
        )
        if not normalized_food_name:
            continue

        kcal_range = item.get("kcal_range")
        if kcal_range is None and "kcal_range" in answer_contract:
            kcal_range = answer_contract.get("kcal_range")
            parent_fallback_fields.add("kcal_range")

        likely_kcal = item.get("likely_kcal")
        if likely_kcal is None and "likely_kcal" in answer_contract:
            likely_kcal = answer_contract.get("likely_kcal")
            parent_fallback_fields.add("likely_kcal")

        uncertainty = item.get("uncertainty")
        if uncertainty is None and "uncertainty" in answer_contract:
            uncertainty = answer_contract.get("uncertainty")
            parent_fallback_fields.add("uncertainty")

        evidence_used = item.get("evidence_used")
        if isinstance(evidence_used, list) and evidence_used:
            normalized_evidence_used = list(evidence_used)
        elif isinstance(answer_contract.get("evidence_used"), list) and answer_contract.get("evidence_used"):
            normalized_evidence_used = list(answer_contract.get("evidence_used"))
            parent_fallback_fields.add("evidence_used")
        else:
            normalized_evidence_used = list(packet_refs.get(normalized_food_name, []))

        bridged.append(
            {
                "food_name": normalized_food_name,
                "kcal_range": kcal_range,
                "likely_kcal": likely_kcal,
                "uncertainty": uncertainty,
                "evidence_used": normalized_evidence_used,
            }
        )
    return bridged, sorted(parent_fallback_fields)


def _item_results_from_answer_contract_nested(payload: dict[str, Any], packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    answer_contract = payload.get("answer_contract")
    if not isinstance(answer_contract, dict):
        return []
    items = answer_contract.get("items")
    if not isinstance(items, list):
        return []
    packet_refs = _packet_fixture_ids_by_food_name(packets)
    bridged: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("item_results")
        if not isinstance(nested, dict):
            continue
        normalized_food_name = _normalize_item_level_food_name(
            str(item.get("food_name") or item.get("item_name") or "")
        )
        if not normalized_food_name:
            continue
        bridged_item = {
            "food_name": normalized_food_name,
            "kcal_range": nested.get("kcal_range"),
            "likely_kcal": nested.get("likely_kcal"),
            "uncertainty": nested.get("uncertainty"),
            "evidence_used": list(packet_refs.get(normalized_food_name, [])),
        }
        bridged.append(bridged_item)
    return bridged


def _packet_fixture_ids_by_food_name(packets: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        fixture_id = str(packet.get("fixture_id") or "")
        candidates = packet.get("candidates")
        if not fixture_id or not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            food_name = _normalize_item_level_food_name(str(candidate.get("food_name") or ""))
            if not food_name:
                continue
            mapping.setdefault(food_name, [])
            if fixture_id not in mapping[food_name]:
                mapping[food_name].append(fixture_id)
    return mapping


def _normalize_item_level_food_name(raw_name: str) -> str:
    value = str(raw_name or "").strip()
    if not value:
        return ""
    for open_char, close_char in (("(", ")"), ("（", "）")):
        if open_char in value and value.endswith(close_char):
            value = value.split(open_char, 1)[0].strip()
    return value


async def _run_case(*, case_id: str, message: str, provider: Any, pass1_mode: str) -> dict[str, Any]:
    case_started_at_utc = _utc_now()
    case_started_perf = time.perf_counter()
    case_family = _phase_b1_case_family_for_message(message)
    resolved_state = SimpleNamespace(onboarding_ready=True)
    resolved_state_payload = _json_safe(resolved_state)
    constraints = {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "manager_pass_contract": "pass1_requests_tools_pass2_synthesizes",
        "phase_b1_case_id": case_id,
    }
    router_trace: dict[str, Any] = {
        "requested_read_tools": [],
        "manager_requested_tools": [],
        "allowed_tools": [],
        "filtered_tool_plan": [],
        "blocked_tools": [],
        "block_reasons": [],
        "available_read_tools": list(AVAILABLE_READ_TOOLS),
        "canonical_tool_catalog_hash": _hash(list(AVAILABLE_READ_TOOLS)),
    }
    read_tool_executions: list[dict[str, Any]] = []
    packetizer_outputs: list[dict[str, Any]] = []

    async def tool_executor(*, tool_calls: list[dict[str, Any]], **_: Any) -> list[dict[str, Any]]:
        nonlocal router_trace, read_tool_executions, packetizer_outputs
        requested_tools = [str(call.get("name") or call.get("tool_name") or "") for call in tool_calls if isinstance(call, dict)]
        requested_tools = [tool for tool in requested_tools if tool]
        router_trace = _route_tools(message=message, requested_tools=requested_tools)
        for tool_name in router_trace["allowed_tools"]:
            for food_name in _food_names_for_message(message):
                raw_output = _raw_stub_output(case_id=case_id, tool_name=tool_name, food_name=food_name)
                packet = _fixture_packet(case_id=case_id, tool_name=tool_name, food_name=food_name)
                read_tool_executions.append(
                    {
                        "tool_name": tool_name,
                        "raw_tool_output_ref": f"artifacts/raw/{case_id}_{tool_name}_{_hash(food_name)}.json",
                        "output": raw_output,
                    }
                )
                packetizer_outputs.append(packet)
        if _is_self_selected_basket_without_ingredients(message) and not packetizer_outputs:
            packetizer_outputs.append(
                {
                    "packet_type": "TaiwanSkillPacket",
                    "truth_level": "rule_hint",
                    "fixture_id": f"{case_id}_self_selected_basket",
                    "fixture_hash": _hash({"case_id": case_id, "rule": "self_selected_basket_without_ingredients"}),
                    "fixture_only": True,
                    "generated_by": "deterministic_fixture",
                    "rule_id": "self_selected_basket_without_ingredients",
                }
            )
        return [
            {
                "tool_name": "packetize_food_evidence",
                "truth_level": "hint",
                "packetizer_outputs": _json_safe(packetizer_outputs),
            }
        ]

    if hasattr(provider, "begin_case"):
        provider.begin_case()
    try:
        result = await run_intake_manager(
            provider=provider,
            raw_user_input=message,
            resolved_state=resolved_state,
            available_tools=AVAILABLE_READ_TOOLS,
            tool_executor=tool_executor,
            constraints=constraints,
            max_rounds=2,
        )
    except _ManagerPayloadShapeError as exc:
        round_history = provider.case_rounds() if hasattr(provider, "case_rounds") else []
        if exc.round_index == 0 and round_history and exc.reason == "manager_output_contract_violation":
            pass1_round = round_history[0]
            pass1_trace = dict(pass1_round.get("trace") or {})
            pass1_decision = dict(pass1_round.get("decision") or {}) if isinstance(pass1_round.get("decision"), dict) else {}
            pass1_shape = _payload_shape_fields(pass1_round.get("decision"))
            requested_tools = _tool_call_names(pass1_decision)
            router_trace = _route_tools(message=message, requested_tools=requested_tools)
            if _is_self_selected_basket_without_ingredients(message) and not packetizer_outputs:
                packetizer_outputs.append(
                    {
                        "packet_type": "TaiwanSkillPacket",
                        "truth_level": "rule_hint",
                        "fixture_id": f"{case_id}_self_selected_basket",
                        "fixture_hash": _hash({"case_id": case_id, "rule": "self_selected_basket_without_ingredients"}),
                        "fixture_only": True,
                        "generated_by": "deterministic_fixture",
                        "rule_id": "self_selected_basket_without_ingredients",
                    }
                )
            exc.partial_trace = {
                "case_id": case_id,
                "input_message": message,
                "case_started_at_utc": case_started_at_utc,
                "case_ended_at_utc": _utc_now(),
                "case_latency_ms": _elapsed_ms(case_started_perf),
                "semantic_boundary": "self_selected_basket_without_ingredients" if _is_self_selected_basket_without_ingredients(message) else None,
                "pass1_mode": pass1_mode,
                "forced_tool_request_contract": pass1_mode == FORCED_MODE,
                "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
                "runner_derived_item_results": False,
                "is_live_tavily_canary": False,
                "uses_deterministic_stub_fixtures": True,
                "stub_fixture_source": "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
                "stub_generated_by_llm": False,
                "manager_pass_1": {
                    "manager_round": 0,
                    "manager_role": "pass_1_tool_request",
                    "prompt_hash": _case_prompt_hash(
                        manager_role="pass_1_tool_request",
                        pass1_mode=pass1_mode,
                        case_family=case_family,
                    ),
                    "started_at_utc": pass1_trace.get("started_at_utc"),
                    "ended_at_utc": pass1_trace.get("ended_at_utc"),
                    "latency_ms": pass1_trace.get("latency_ms"),
                    "usage": pass1_trace.get("usage"),
                    "provider_params": _provider_params(pass1_trace),
                    "phase_b1_task_payload_id": pass1_trace.get("phase_b1_task_payload_id"),
                    "phase_b1_task_payload_hash": pass1_trace.get("phase_b1_task_payload_hash"),
                    "selector_inputs": _selector_trace_dict(pass1_trace, "selector_inputs"),
                    "manager_contract_selection": _selector_trace_dict(pass1_trace, "manager_contract_selection"),
                    "provider_profile_selection": _selector_trace_dict(pass1_trace, "provider_profile_selection"),
                    "requested_read_tools": requested_tools,
                    "forbidden_final_truth_fields_present": _contains_any_key(pass1_decision, PASS_1_FORBIDDEN_FIELDS),
                    **pass1_shape,
                },
                "runtime_tool_router": router_trace,
                "read_tool_executions": read_tool_executions,
                "packetizer": {
                    "outputs": packetizer_outputs,
                    "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"}),
                },
                "manager_pass_2": {
                    "manager_round": 1,
                    "manager_role": "pass_2_synthesis",
                    "prompt_hash": _case_prompt_hash(
                        manager_role="pass_2_synthesis",
                        pass1_mode=pass1_mode,
                        case_family=case_family,
                    ),
                    "started_at_utc": None,
                    "ended_at_utc": None,
                    "latency_ms": None,
                    "usage": None,
                    "provider_params": {"provider": None, "model": None, "request_id": None},
                    "phase_b1_task_payload_id": None,
                    "phase_b1_task_payload_hash": None,
                    "selector_inputs": _selector_inputs_trace(
                        case_family=case_family,
                        manager_role="pass_2_synthesis",
                        probe_mode=pass1_mode,
                        case_id=case_id,
                    ),
                    "manager_contract_selection": _manager_contract_selection_trace(
                        manager_role="pass_2_synthesis",
                        probe_mode=NATURAL_MODE,
                        case_family=case_family,
                    ),
                    "provider_profile_selection": {},
                    "item_results": [],
                    "mutation_attempted": False,
                    "forbidden_mutation_fields_present": [],
                    "decision_payload": None,
                    "decision_payload_type": None,
                    "payload_shape_valid": True,
                    "payload_shape_error": None,
                },
                "mutation": {
                    "mutation_attempted": False,
                    "reason": "no_mutation_intent",
                    "mutation_result": None,
                },
                "guard": {"ran": True, "ran_before_mutation": True, "result": "no_mutation"},
                "renderer": {"input": {}, "final_response": "", "invented_facts": []},
            }
        if exc.round_index == 1 and round_history:
            pass1_round = round_history[0] if round_history else {"decision": {}, "trace": {}}
            pass2_round = round_history[-1]
            pass1_trace = dict(pass1_round.get("trace") or {})
            pass1_decision = dict(pass1_round.get("decision") or {}) if isinstance(pass1_round.get("decision"), dict) else {}
            pass1_shape = _payload_shape_fields(pass1_round.get("decision"))
            pass2_trace = dict(pass2_round.get("trace") or {})
            pass2_shape = _payload_shape_fields(pass2_round.get("decision"))
            exc.partial_trace = {
                "case_id": case_id,
                "input_message": message,
                "case_started_at_utc": case_started_at_utc,
                "case_ended_at_utc": _utc_now(),
                "case_latency_ms": _elapsed_ms(case_started_perf),
                "semantic_boundary": "self_selected_basket_without_ingredients" if _is_self_selected_basket_without_ingredients(message) else None,
                "pass1_mode": pass1_mode,
                "forced_tool_request_contract": pass1_mode == FORCED_MODE,
                "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
                "runner_derived_item_results": False,
                "is_live_tavily_canary": False,
                "uses_deterministic_stub_fixtures": True,
                "stub_fixture_source": "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
                "stub_generated_by_llm": False,
                "manager_pass_1": {
                    "manager_round": 0,
                    "manager_role": "pass_1_tool_request",
                    "prompt_hash": _case_prompt_hash(
                        manager_role="pass_1_tool_request",
                        pass1_mode=pass1_mode,
                        case_family=case_family,
                    ),
                    "started_at_utc": pass1_trace.get("started_at_utc"),
                    "ended_at_utc": pass1_trace.get("ended_at_utc"),
                    "latency_ms": pass1_trace.get("latency_ms"),
                    "usage": pass1_trace.get("usage"),
                    "provider_params": _provider_params(pass1_trace),
                    "phase_b1_task_payload_id": pass1_trace.get("phase_b1_task_payload_id"),
                    "phase_b1_task_payload_hash": pass1_trace.get("phase_b1_task_payload_hash"),
                    "selector_inputs": _selector_trace_dict(pass1_trace, "selector_inputs"),
                    "manager_contract_selection": _selector_trace_dict(pass1_trace, "manager_contract_selection"),
                    "provider_profile_selection": _selector_trace_dict(pass1_trace, "provider_profile_selection"),
                    "requested_read_tools": router_trace["requested_read_tools"],
                    "forbidden_final_truth_fields_present": _contains_any_key(pass1_decision, PASS_1_FORBIDDEN_FIELDS),
                    **pass1_shape,
                },
                "runtime_tool_router": router_trace,
                "read_tool_executions": read_tool_executions,
                "packetizer": {
                    "outputs": packetizer_outputs,
                    "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"}),
                },
                "manager_pass_2": {
                    "manager_round": 1,
                    "manager_role": "pass_2_synthesis",
                    "prompt_hash": _case_prompt_hash(
                        manager_role="pass_2_synthesis",
                        pass1_mode=pass1_mode,
                        case_family=case_family,
                    ),
                    "started_at_utc": pass2_trace.get("started_at_utc"),
                    "ended_at_utc": pass2_trace.get("ended_at_utc"),
                    "latency_ms": pass2_trace.get("latency_ms"),
                    "usage": pass2_trace.get("usage"),
                    "provider_params": _provider_params(pass2_trace),
                    "phase_b1_task_payload_id": pass2_trace.get("phase_b1_task_payload_id"),
                    "phase_b1_task_payload_hash": pass2_trace.get("phase_b1_task_payload_hash"),
                    "selector_inputs": _selector_trace_dict(pass2_trace, "selector_inputs"),
                    "manager_contract_selection": _selector_trace_dict(pass2_trace, "manager_contract_selection"),
                    "provider_profile_selection": _selector_trace_dict(pass2_trace, "provider_profile_selection"),
                    "item_results": [],
                    "mutation_attempted": False,
                    "forbidden_mutation_fields_present": [],
                    **pass2_shape,
                },
            }
        raise
    if _is_self_selected_basket_without_ingredients(message) and not router_trace["blocked_tools"]:
        router_trace = _route_tools(message=message, requested_tools=[])
        if not packetizer_outputs:
            packetizer_outputs.append(
                {
                    "packet_type": "TaiwanSkillPacket",
                    "truth_level": "rule_hint",
                    "fixture_id": f"{case_id}_self_selected_basket",
                    "fixture_hash": _hash({"case_id": case_id, "rule": "self_selected_basket_without_ingredients"}),
                    "fixture_only": True,
                    "generated_by": "deterministic_fixture",
                    "rule_id": "self_selected_basket_without_ingredients",
                }
            )
    rounds = provider.case_rounds() if hasattr(provider, "case_rounds") else list(result.manager_rounds)
    pass1_round = rounds[0] if rounds else {"decision": {}, "trace": {}}
    pass1_trace = dict(pass1_round.get("trace") or {})
    pass1_shape = _payload_shape_fields(pass1_round.get("decision"))
    if not pass1_shape["payload_shape_valid"]:
        raise _ManagerPayloadShapeError(
            stage="pass_1_tool_request",
            round_index=0,
            decision_payload=pass1_round.get("decision"),
        )
    pass1_decision = _ensure_decision_payload_dict(
        payload=pass1_round.get("decision"),
        stage="pass_1_tool_request",
        round_index=0,
    )
    if _should_complete_b1_004_pass2_trace(
        case_id=case_id,
        message=message,
        pass1_mode=pass1_mode,
        rounds=rounds,
        pass1_decision=pass1_decision,
        router_trace=router_trace,
        packetizer_outputs=packetizer_outputs,
    ):
        await _complete_b1_004_real_pass2_trace(
            provider=provider,
            message=message,
            resolved_state_payload=resolved_state_payload,
            constraints=constraints,
            packetizer_outputs=packetizer_outputs,
        )
        rounds = provider.case_rounds() if hasattr(provider, "case_rounds") else list(result.manager_rounds)
    pass1_round = rounds[0] if rounds else {"decision": {}, "trace": {}}
    pass2_round = rounds[-1] if len(rounds) > 1 else {"decision": {}, "trace": {}}
    pass1_trace = dict(pass1_round.get("trace") or {})
    pass2_trace = dict(pass2_round.get("trace") or {})
    pass1_shape = _payload_shape_fields(pass1_round.get("decision"))
    pass2_shape = _payload_shape_fields(pass2_round.get("decision"))
    pass1_decision = _ensure_decision_payload_dict(
        payload=pass1_round.get("decision"),
        stage="pass_1_tool_request",
        round_index=0,
    )
    partial_trace_base = {
        "case_id": case_id,
        "input_message": message,
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "manager_pass_1": {
            "manager_round": 0,
            "manager_role": "pass_1_tool_request",
            "prompt_hash": _case_prompt_hash(
                manager_role="pass_1_tool_request",
                pass1_mode=pass1_mode,
                case_family=case_family,
            ),
            "started_at_utc": pass1_trace.get("started_at_utc"),
            "ended_at_utc": pass1_trace.get("ended_at_utc"),
            "latency_ms": pass1_trace.get("latency_ms"),
            "usage": pass1_trace.get("usage"),
            "provider_params": _provider_params(pass1_trace),
            "phase_b1_task_payload_id": pass1_trace.get("phase_b1_task_payload_id"),
            "phase_b1_task_payload_hash": pass1_trace.get("phase_b1_task_payload_hash"),
            "selector_inputs": _selector_trace_dict(pass1_trace, "selector_inputs"),
            "manager_contract_selection": _selector_trace_dict(pass1_trace, "manager_contract_selection"),
            "provider_profile_selection": _selector_trace_dict(pass1_trace, "provider_profile_selection"),
            "requested_read_tools": router_trace["requested_read_tools"],
            "forbidden_final_truth_fields_present": _contains_any_key(pass1_decision, PASS_1_FORBIDDEN_FIELDS),
            **pass1_shape,
        },
        "runtime_tool_router": router_trace,
        "read_tool_executions": read_tool_executions,
        "packetizer": {
            "outputs": packetizer_outputs,
            "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"}),
        },
    }
    if len(rounds) <= 1:
        pass2_decision: dict[str, Any] = {}
    else:
        if not pass2_shape["payload_shape_valid"]:
            partial_trace = {
                **partial_trace_base,
                "manager_pass_2": {
                    "manager_round": 1,
                    "manager_role": "pass_2_synthesis",
                    "prompt_hash": _case_prompt_hash(
                        manager_role="pass_2_synthesis",
                        pass1_mode=pass1_mode,
                        case_family=case_family,
                    ),
                    "started_at_utc": pass2_trace.get("started_at_utc"),
                    "ended_at_utc": pass2_trace.get("ended_at_utc"),
                    "latency_ms": pass2_trace.get("latency_ms"),
                    "usage": pass2_trace.get("usage"),
                    "provider_params": _provider_params(pass2_trace),
                    "phase_b1_task_payload_id": pass2_trace.get("phase_b1_task_payload_id"),
                    "phase_b1_task_payload_hash": pass2_trace.get("phase_b1_task_payload_hash"),
                    "selector_inputs": _selector_trace_dict(pass2_trace, "selector_inputs"),
                    "manager_contract_selection": _selector_trace_dict(pass2_trace, "manager_contract_selection"),
                    "provider_profile_selection": _selector_trace_dict(pass2_trace, "provider_profile_selection"),
                    "item_results": [],
                    "mutation_attempted": False,
                    "forbidden_mutation_fields_present": [],
                    **pass2_shape,
                },
                "runner_derived_item_results": False,
            }
            raise _ManagerPayloadShapeError(
                stage="pass_2_synthesis",
                round_index=1,
                decision_payload=pass2_round.get("decision"),
                partial_trace=partial_trace,
            )
        pass2_decision = _ensure_decision_payload_dict(
            payload=pass2_round.get("decision"),
            stage="pass_2_synthesis",
            round_index=1,
        )
    item_results, runner_derived_item_results, item_results_source, item_results_bridge_shape, item_results_bridge_parent_fallback_fields = _item_results_from_payload(
        pass2_decision,
        packetizer_outputs,
        allow_packet_fallback=pass1_mode == FORCED_MODE,
        allow_root_answer_contract_bridge=_allow_root_answer_contract_item_results_bridge(case_id=case_id, message=message),
        allow_nested_answer_contract_bridge=_is_listed_ingredient_basket(message),
    )
    if _is_self_selected_basket_without_ingredients(message):
        item_results = []
        runner_derived_item_results = False
        item_results_source = "none"
        item_results_bridge_shape = None
        item_results_bridge_parent_fallback_fields = []
    mutation = _mutation_trace(message=message, item_results=item_results)
    guard = {"ran": True, "ran_before_mutation": True, "result": "no_mutation" if not mutation["mutation_attempted"] else "pass"}
    case_ended_at_utc = _utc_now()
    return {
        "case_id": case_id,
        "input_message": message,
        "case_started_at_utc": case_started_at_utc,
        "case_ended_at_utc": case_ended_at_utc,
        "case_latency_ms": _elapsed_ms(case_started_perf),
        "semantic_boundary": "self_selected_basket_without_ingredients" if _is_self_selected_basket_without_ingredients(message) else None,
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "runner_derived_item_results": runner_derived_item_results,
        "is_live_tavily_canary": False,
        "uses_deterministic_stub_fixtures": True,
        "stub_fixture_source": "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
        "stub_generated_by_llm": False,
        "manager_pass_1": {
            "manager_round": 0,
            "manager_role": "pass_1_tool_request",
            "prompt_hash": _case_prompt_hash(
                manager_role="pass_1_tool_request",
                pass1_mode=pass1_mode,
                case_family=case_family,
            ),
            "started_at_utc": pass1_trace.get("started_at_utc"),
            "ended_at_utc": pass1_trace.get("ended_at_utc"),
            "latency_ms": pass1_trace.get("latency_ms"),
            "usage": pass1_trace.get("usage"),
            "provider_params": _provider_params(pass1_trace),
            "phase_b1_task_payload_id": pass1_trace.get("phase_b1_task_payload_id"),
            "phase_b1_task_payload_hash": pass1_trace.get("phase_b1_task_payload_hash"),
            "selector_inputs": _selector_trace_dict(pass1_trace, "selector_inputs"),
            "manager_contract_selection": _selector_trace_dict(pass1_trace, "manager_contract_selection"),
            "provider_profile_selection": _selector_trace_dict(pass1_trace, "provider_profile_selection"),
            "requested_read_tools": router_trace["requested_read_tools"],
            "forbidden_final_truth_fields_present": _contains_any_key(pass1_decision, PASS_1_FORBIDDEN_FIELDS),
            **pass1_shape,
        },
        "runtime_tool_router": router_trace,
        "read_tool_executions": read_tool_executions,
        "packetizer": {"outputs": packetizer_outputs, "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"})},
        "manager_pass_2": {
            "manager_round": 1,
            "manager_role": "pass_2_synthesis",
            "prompt_hash": _case_prompt_hash(
                manager_role="pass_2_synthesis",
                pass1_mode=pass1_mode,
                case_family=case_family,
            ),
            "started_at_utc": pass2_trace.get("started_at_utc"),
            "ended_at_utc": pass2_trace.get("ended_at_utc"),
            "latency_ms": pass2_trace.get("latency_ms"),
            "usage": pass2_trace.get("usage"),
            "provider_params": _provider_params(pass2_trace),
            "phase_b1_task_payload_id": pass2_trace.get("phase_b1_task_payload_id"),
            "phase_b1_task_payload_hash": pass2_trace.get("phase_b1_task_payload_hash"),
            "selector_inputs": _selector_trace_dict(pass2_trace, "selector_inputs"),
            "manager_contract_selection": _selector_trace_dict(pass2_trace, "manager_contract_selection"),
            "provider_profile_selection": _selector_trace_dict(pass2_trace, "provider_profile_selection"),
            "item_results": item_results,
            "item_results_source": item_results_source,
            "item_results_owner_class": _item_results_owner_class(
                item_results_source=item_results_source,
                runner_derived_item_results=runner_derived_item_results,
            ),
            "item_results_bridge_shape": item_results_bridge_shape,
            "item_results_bridge_parent_fallback_fields": item_results_bridge_parent_fallback_fields,
            "mutation_attempted": False,
            "forbidden_mutation_fields_present": _contains_any_key(pass2_decision, PASS_2_FORBIDDEN_MUTATION_FIELDS),
            **pass2_shape,
        },
        "guard": guard,
        "mutation": mutation,
        "renderer": _renderer_trace(item_results=item_results, mutation=mutation),
        "tavily_canary": None,
    }


def _runtime_blocker_report(
    *,
    readiness: dict[str, Any],
    artifact_path: Path,
    smoke_cases: list[str] | tuple[str, ...],
    traces: list[dict[str, Any]],
    blocker: _ManagerPayloadShapeError,
    pass1_mode: str,
    started_perf: float,
    case_set: str,
    requested_case_ids: list[str],
) -> dict[str, Any]:
    runtime_blocker = {
        "blocker": True,
        "reason": blocker.reason,
        "stage": blocker.stage,
        "round_index": blocker.round_index,
        "decision_payload_type": type(blocker.decision_payload).__name__,
        "decision_payload_excerpt": json.dumps(blocker.decision_payload, ensure_ascii=False, default=str)[:300],
        "completed_trace_count": len(traces),
        "expected_case_count": len(smoke_cases),
    }
    if blocker.failing_component:
        runtime_blocker["failing_component"] = blocker.failing_component
    if blocker.violation_family:
        runtime_blocker["violation_family"] = blocker.violation_family
    if blocker.actual_shape:
        runtime_blocker["actual_shape"] = blocker.actual_shape
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider") or "builderspace",
        "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "runtime_blocker": runtime_blocker,
        "runtime_latency": _runtime_latency_summary(
            started_perf=started_perf,
            traces=traces,
            pass1_mode=pass1_mode,
            readiness_claim_scope=FULL_READINESS_SCOPE if case_set == "full" else DIAGNOSTIC_READINESS_SCOPE,
        ),
        **_report_case_metadata(
            smoke_cases=smoke_cases,
            traces=traces,
            case_set=case_set,
            requested_case_ids=requested_case_ids,
        ),
        "tool_loop_traces": _json_safe(traces),
        "artifact_path": str(artifact_path),
    }


def _runtime_latency_summary(
    *,
    started_perf: float,
    traces: list[dict[str, Any]],
    pass1_mode: str,
    readiness_claim_scope: str,
) -> dict[str, Any]:
    return {
        "latency_budget_type": "b1_full_smoke_reporting_target",
        "not_user_runtime_budget": True,
        "full_smoke_target_ms": FULL_SMOKE_LATENCY_TARGET_MS,
        "total_latency_ms": _elapsed_ms(started_perf),
        "trace_count": len(traces),
        "completed_trace_count": len(traces),
        "mode": pass1_mode,
        "readiness_claim_scope": readiness_claim_scope,
    }


def _report_case_metadata(
    *,
    smoke_cases: list[str] | tuple[str, ...],
    traces: list[dict[str, Any]],
    case_set: str,
    requested_case_ids: list[str],
) -> dict[str, Any]:
    return {
        "case_set": case_set,
        "requested_case_ids": list(requested_case_ids),
        "completed_case_count": len(traces),
        "expected_full_case_count": len(CORE_SMOKE_CASES),
        "full_readiness_claimed": case_set == "full",
        "core_smoke_cases_run": list(smoke_cases)[: len(traces)],
    }


def _provider_runtime_summary_for_error(
    *,
    readiness: dict[str, Any],
    traces: list[dict[str, Any]],
    error: Exception,
    smoke_cases: list[str] | tuple[str, ...],
    provider_timeout_ms: int,
    runner_case_attempt_count: int | None = None,
) -> dict[str, Any]:
    raw_provider_trace = getattr(error, "trace", {})
    provider_trace = dict(raw_provider_trace) if isinstance(raw_provider_trace, dict) else {}
    transport_attempts = (
        provider_trace.get("transport_attempts") if isinstance(provider_trace.get("transport_attempts"), list) else []
    )
    latest_transport_attempt = next(
        (
            attempt
            for attempt in reversed(transport_attempts)
            if isinstance(attempt, dict) and attempt.get("error_type")
        ),
        None,
    )
    timeout_error_types = {"TimeoutError", "ReadTimeout", "ConnectTimeout", "WriteTimeout", "PoolTimeout"}
    transient_statuses = {429, 500, 503}
    transient_transport_error_types = timeout_error_types | {"ConnectError"}
    transport_timeout = any(
        isinstance(attempt, dict) and str(attempt.get("error_type") or "") in timeout_error_types
        for attempt in transport_attempts
    )
    transient_status = any(
        isinstance(attempt, dict) and int(attempt.get("http_status") or 0) in transient_statuses
        for attempt in transport_attempts
    )
    is_timeout = (
        isinstance(error, TimeoutError)
        or transport_timeout
        or (isinstance(error, BuilderSpaceResponseError) and "timeout" in str(error).lower())
    )
    if isinstance(error, TimeoutError):
        timeout_layer = "outer_provider_timeout"
    elif is_timeout:
        timeout_layer = "adapter_http_timeout"
    else:
        timeout_layer = None
    readiness_timeout = readiness.get("timeout_seconds")
    stage = provider_trace.get("stage")
    model = provider_trace.get("model") or readiness.get("manager_model") or readiness.get("model")
    base_url = provider_trace.get("base_url") or readiness.get("base_url")
    retry_count = readiness.get("transport_retry_count")
    compact_transport_attempts = [
        _compact_transport_attempt(
            attempt=attempt,
            timeout_error_types=timeout_error_types,
            transient_transport_error_types=transient_transport_error_types,
            transient_statuses=transient_statuses,
            parent_error_message=str(error),
        )
        for attempt in transport_attempts
        if isinstance(attempt, dict)
    ]
    failing_component = getattr(error, "failing_component", None) or provider_trace.get("failing_component")
    if failing_component is None and isinstance(error, BuilderSpaceResponseError):
        failing_component = "builderspace_adapter.complete_with_trace"
    finish_reason = provider_trace.get("finish_reason")
    raw_content_excerpt = provider_trace.get("raw_content_excerpt")
    value_excerpt = provider_trace.get("value_excerpt")
    length_truncated_before_json_completion = _looks_like_length_truncated_json_attempt(
        finish_reason=finish_reason,
        raw_content_excerpt=raw_content_excerpt,
        value_excerpt=value_excerpt,
    )
    provider_runtime: dict[str, Any] = {
        "configured": bool(readiness.get("configured")),
        "blocker": True,
        "reason": "provider_timeout" if is_timeout else "provider_runtime_error",
        "error_type": str(latest_transport_attempt.get("error_type")) if latest_transport_attempt is not None else type(error).__name__,
        "error": str(error),
        "provider": provider_trace.get("provider") or readiness.get("provider"),
        "model": model,
        "stage": stage,
        "adapter_timeout_seconds": provider_trace.get("timeout_seconds") or readiness_timeout,
        "outer_provider_timeout_ms": provider_timeout_ms,
        "timeout_layer": timeout_layer,
        "attempt_count": len(transport_attempts) if transport_attempts else 1,
        "retry_count": retry_count,
        "configured_transport_retry_count": retry_count,
        "transport_attempt_count": len(compact_transport_attempts),
        "runner_case_attempt_count": runner_case_attempt_count or 1,
        "completed_trace_count": len(traces),
        "expected_case_count": len(smoke_cases),
        "base_url": base_url,
        "transport_attempts": compact_transport_attempts,
        "failing_component": failing_component,
        "failure_family": provider_trace.get("failure_family") or provider_trace.get("request_failure_family"),
        "observed_type": provider_trace.get("observed_type"),
        "value_excerpt": provider_trace.get("value_excerpt"),
        "value_truncated": provider_trace.get("value_truncated"),
        "raw_content_excerpt": provider_trace.get("raw_content_excerpt"),
        "raw_response_excerpt": provider_trace.get("raw_response_excerpt"),
        "response_status": provider_trace.get("response_status"),
        "status": provider_trace.get("status"),
        "incomplete_details": provider_trace.get("incomplete_details"),
        "usage": provider_trace.get("usage"),
        "finish_reason": finish_reason,
        "parse_contract_status": provider_trace.get("parse_contract_status"),
        "parse_recovery_used": provider_trace.get("parse_recovery_used"),
        "parse_recovery_strategy": provider_trace.get("parse_recovery_strategy"),
        "parse_recovery_ambiguous": provider_trace.get("parse_recovery_ambiguous"),
        "structured_output_transport_attempted": provider_trace.get("structured_output_transport_attempted"),
        "structured_output_transport_mode": provider_trace.get("structured_output_transport_mode"),
        "structured_output_transport_accepted": provider_trace.get("structured_output_transport_accepted"),
        "structured_output_transport_fallback": provider_trace.get("structured_output_transport_fallback"),
        "fallback_reason": provider_trace.get("fallback_reason"),
        "structured_output_transport_constraint_snapshot": provider_trace.get("structured_output_transport_constraint_snapshot"),
        "effective_response_format_type": provider_trace.get("effective_response_format_type"),
        "decision_transport_attempted": provider_trace.get("decision_transport_attempted"),
        "decision_transport_mode": provider_trace.get("decision_transport_mode"),
        "decision_transport_accepted": provider_trace.get("decision_transport_accepted"),
        "decision_transport_fallback": provider_trace.get("decision_transport_fallback"),
        "decision_transport_fallback_reason": provider_trace.get("decision_transport_fallback_reason"),
        "decision_transport_contract_breach": provider_trace.get("decision_transport_contract_breach"),
        "decision_transport_constraint_snapshot": provider_trace.get("decision_transport_constraint_snapshot"),
        "provider_profile_id": provider_trace.get("provider_profile_id"),
        "provider_profile_provider": provider_trace.get("provider_profile_provider"),
        "provider_profile_model": provider_trace.get("provider_profile_model"),
        "provider_profile_cost_tier": provider_trace.get("provider_profile_cost_tier"),
        "provider_profile_manual_only": provider_trace.get("provider_profile_manual_only"),
        "provider_profile_role": provider_trace.get("provider_profile_role"),
        "provider_profile_transport_mode": provider_trace.get("provider_profile_transport_mode"),
        "provider_profile_selection_reason": provider_trace.get("provider_profile_selection_reason"),
        "provider_profile_route_mode": provider_trace.get("provider_profile_route_mode"),
        "provider_profile_route_reason": provider_trace.get("provider_profile_route_reason"),
        "profile_routing_rule_id": provider_trace.get("profile_routing_rule_id"),
        "profile_routing_scope": provider_trace.get("profile_routing_scope"),
        "profile_routing_artifact_basis": provider_trace.get("profile_routing_artifact_basis"),
        "manager_candidate_status": provider_trace.get("manager_candidate_status"),
        "documented_reasoning_status": provider_trace.get("documented_reasoning_status"),
        "documented_tool_call_support": provider_trace.get("documented_tool_call_support"),
        "production_selected": provider_trace.get("production_selected"),
        "allow_expensive_model_probe": provider_trace.get("allow_expensive_model_probe"),
        "artifact_tool_call_reliability": provider_trace.get("artifact_tool_call_reliability"),
        "length_truncated_before_json_completion": length_truncated_before_json_completion,
        "truncation_failure_family": "incomplete_json_due_to_length" if length_truncated_before_json_completion else None,
        "transient_status_retryable": transient_status,
    }
    if is_timeout:
        provider_runtime["timeout_ms"] = provider_timeout_ms
        provider_runtime["completed_traces"] = len(traces)
    return provider_runtime


def _compact_transport_attempt(
    *,
    attempt: dict[str, Any],
    timeout_error_types: set[str],
    transient_transport_error_types: set[str],
    transient_statuses: set[int],
    parent_error_message: str,
) -> dict[str, Any]:
    error_type = str(attempt.get("error_type") or "") or None
    status_code = int(attempt.get("http_status") or 0) or None
    timeout_layer = "adapter_http_timeout" if error_type in timeout_error_types else None
    if error_type in timeout_error_types:
        exception_family = "timeout"
    elif error_type == "ConnectError":
        exception_family = "network"
    elif status_code in transient_statuses:
        exception_family = "http_status"
    else:
        exception_family = "transport"
    message_source = str(attempt.get("error") or parent_error_message or "")
    message_excerpt = _truncate_text(message_source, limit=240) if message_source else None
    return {
        "attempt_index": attempt.get("attempt_index"),
        "started_at_utc": attempt.get("started_at_utc"),
        "ended_at_utc": attempt.get("ended_at_utc"),
        "error_type": error_type,
        "retryable": bool(error_type in transient_transport_error_types or status_code in transient_statuses),
        "status_code": status_code,
        "timeout_layer": timeout_layer,
        "exception_family": exception_family,
        "message_excerpt": message_excerpt,
    }


def _truncate_text(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."


def _is_retryable_provider_error(error: Exception) -> bool:
    if isinstance(error, TimeoutError):
        return True
    if not isinstance(error, BuilderSpaceResponseError):
        return False
    trace = getattr(error, "trace", {})
    if not isinstance(trace, dict):
        lowered = str(error).lower()
        return "timeout" in lowered or "connecterror" in lowered or "connection attempts failed" in lowered
    transport_attempts = trace.get("transport_attempts") if isinstance(trace.get("transport_attempts"), list) else []
    timeout_error_types = {"TimeoutError", "ReadTimeout", "ConnectTimeout", "WriteTimeout", "PoolTimeout"}
    transient_transport_error_types = timeout_error_types | {"ConnectError"}
    if "timeout" in str(error).lower():
        return True
    lowered = str(error).lower()
    if "connecterror" in lowered or "connection attempts failed" in lowered:
        return True
    for attempt in transport_attempts:
        if not isinstance(attempt, dict):
            continue
        if str(attempt.get("error_type") or "") in transient_transport_error_types:
            return True
        if int(attempt.get("http_status") or 0) in {429, 500, 503}:
            return True
    return False


def _runner_retry_delay_seconds(*, attempt_index: int, base_seconds: float, jitter_func: Any) -> float:
    jitter = max(0.0, float(jitter_func()))
    return max(0.0, base_seconds * (2 ** max(0, attempt_index - 1)) + jitter)


async def _sleep_backoff(*, delay_seconds: float, sleep_func: Any) -> None:
    if delay_seconds <= 0:
        return
    await sleep_func(delay_seconds)


def _resolve_cli_targeted_case_ids(*, cases: str | None, case_set: str | None, case_id: str | None) -> list[str] | None:
    if cases:
        targeted = _resolve_targeted_smoke_cases(cases)
        return targeted["requested_case_ids"]
    if case_set is None and case_id is None:
        return None
    normalized_case_set = (case_set or "targeted").strip().lower()
    if normalized_case_set != "targeted":
        raise ValueError("Only targeted case-set overrides are supported by this smoke CLI.")
    if not case_id:
        raise ValueError("A targeted case-set override requires --case-id.")
    targeted = _resolve_targeted_smoke_cases(case_id)
    return targeted["requested_case_ids"]


def _legacy_cli_defaults_for_targeted_case(
    *,
    requested_case_ids: list[str] | None,
    mode: str,
    provider_profile_id: str | None,
    used_legacy_targeting: bool,
) -> tuple[str, str | None]:
    return resolve_phase_b1_local_diagnostic_cli_defaults(
        requested_case_ids=requested_case_ids,
        mode=mode,
        provider_profile_id=provider_profile_id,
        used_legacy_targeting=used_legacy_targeting,
    )


def _provider_unavailable_report(
    *,
    readiness: dict[str, Any],
    artifact_path: Path,
    pass1_mode: str,
    started_perf: float,
    smoke_cases: list[str] | tuple[str, ...],
    case_set: str,
    requested_case_ids: list[str],
) -> dict[str, Any]:
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider"),
        "manager_model": readiness.get("manager_model"),
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "provider_runtime": {"configured": False, "blocker": True, "reason": readiness.get("reason") or "provider_not_configured"},
        "runtime_latency": _runtime_latency_summary(
            started_perf=started_perf,
            traces=[],
            pass1_mode=pass1_mode,
            readiness_claim_scope=FULL_READINESS_SCOPE if case_set == "full" else DIAGNOSTIC_READINESS_SCOPE,
        ),
        **_report_case_metadata(
            smoke_cases=smoke_cases,
            traces=[],
            case_set=case_set,
            requested_case_ids=requested_case_ids,
        ),
        "tool_loop_traces": [],
        "artifact_path": str(artifact_path),
    }


def _provider_profile_mismatch_report(
    *,
    readiness: dict[str, Any],
    selected_profile: _PhaseB1ProviderProfile,
    artifact_path: Path,
    pass1_mode: str,
    started_perf: float,
    smoke_cases: list[str] | tuple[str, ...],
    case_set: str,
    requested_case_ids: list[str],
) -> dict[str, Any]:
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider"),
        "manager_model": readiness.get("manager_model"),
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "provider_runtime": {
            "configured": bool(readiness.get("configured")),
            "blocker": True,
            "reason": "provider_profile_mismatch",
            "readiness_provider": readiness.get("provider"),
            "selected_profile_provider": selected_profile.provider,
            "provider_profile_id": selected_profile.profile_id,
            "provider_profile_model": selected_profile.model,
        },
        "runtime_latency": _runtime_latency_summary(
            started_perf=started_perf,
            traces=[],
            pass1_mode=pass1_mode,
            readiness_claim_scope=FULL_READINESS_SCOPE if case_set == "full" else DIAGNOSTIC_READINESS_SCOPE,
        ),
        **_report_case_metadata(
            smoke_cases=smoke_cases,
            traces=[],
            case_set=case_set,
            requested_case_ids=requested_case_ids,
        ),
        "tool_loop_traces": [],
        "artifact_path": str(artifact_path),
    }


def _provider_runtime_error_report(
    *,
    readiness: dict[str, Any],
    artifact_path: Path,
    smoke_cases: list[str] | tuple[str, ...],
    traces: list[dict[str, Any]],
    error: Exception,
    pass1_mode: str,
    started_perf: float,
    provider_timeout_ms: int,
    case_set: str,
    requested_case_ids: list[str],
) -> dict[str, Any]:
    provider_runtime = _provider_runtime_summary_for_error(
        readiness=readiness,
        traces=traces,
        error=error,
        smoke_cases=smoke_cases,
        provider_timeout_ms=provider_timeout_ms,
    )
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider") or "builderspace",
        "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "provider_runtime": provider_runtime,
        "runtime_latency": _runtime_latency_summary(
            started_perf=started_perf,
            traces=traces,
            pass1_mode=pass1_mode,
            readiness_claim_scope=FULL_READINESS_SCOPE if case_set == "full" else DIAGNOSTIC_READINESS_SCOPE,
        ),
        **_report_case_metadata(
            smoke_cases=smoke_cases,
            traces=traces,
            case_set=case_set,
            requested_case_ids=requested_case_ids,
        ),
        "tool_loop_traces": _json_safe(traces),
        "artifact_path": str(artifact_path),
    }


def _provider_trace_blocker_report(
    *,
    readiness: dict[str, Any],
    artifact_path: Path,
    smoke_cases: list[str] | tuple[str, ...],
    traces: list[dict[str, Any]],
    blocker: _ProviderTraceShapeError,
    pass1_mode: str,
    started_perf: float,
    case_set: str,
    requested_case_ids: list[str],
) -> dict[str, Any]:
    provider_trace_blocker = {
        "blocker": True,
        "reason": "provider_trace_shape_error",
        "trace_field": blocker.trace_field,
        "observed_type": blocker.observed_type,
        "value_excerpt": blocker.value_excerpt,
        "value_truncated": blocker.value_truncated,
        "stage": blocker.stage,
        "failing_component": blocker.failing_component,
        "completed_trace_count": len(traces),
        "expected_case_count": len(smoke_cases),
    }
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider") or "builderspace",
        "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "provider_trace_blocker": provider_trace_blocker,
        "runtime_latency": _runtime_latency_summary(
            started_perf=started_perf,
            traces=traces,
            pass1_mode=pass1_mode,
            readiness_claim_scope=FULL_READINESS_SCOPE if case_set == "full" else DIAGNOSTIC_READINESS_SCOPE,
        ),
        **_report_case_metadata(
            smoke_cases=smoke_cases,
            traces=traces,
            case_set=case_set,
            requested_case_ids=requested_case_ids,
        ),
        "tool_loop_traces": _json_safe(traces),
        "artifact_path": str(artifact_path),
    }


async def _run_targeted_case_with_retries(
    *,
    case_id: str,
    message: str,
    provider: Any,
    pass1_mode: str,
    provider_timeout_ms: int,
    readiness: dict[str, Any],
    max_attempts: int,
    retry_backoff_seconds: float,
    sleep_func: Any,
    jitter_func: Any,
) -> dict[str, Any]:
    case_started_at = _utc_now()
    case_started_perf = time.perf_counter()
    attempts: list[dict[str, Any]] = []
    for attempt_index in range(1, max_attempts + 1):
        attempts.append({"attempt_index": attempt_index, "started_at_utc": _utc_now()})
        try:
            trace = await _run_case(
                case_id=case_id,
                message=message,
                provider=provider,
                pass1_mode=pass1_mode,
            )
        except _ManagerPayloadShapeError as exc:
            partial_trace = exc.partial_trace if isinstance(exc.partial_trace, dict) else None
            runtime_blocker = {
                "reason": exc.reason,
                "stage": exc.stage,
                "round_index": exc.round_index,
                "decision_payload_type": type(exc.decision_payload).__name__,
            }
            if exc.failing_component:
                runtime_blocker["failing_component"] = exc.failing_component
            if exc.violation_family:
                runtime_blocker["violation_family"] = exc.violation_family
            if exc.actual_shape:
                runtime_blocker["actual_shape"] = exc.actual_shape
            return {
                "case_id": case_id,
                "input_message": message,
                "case_execution_status": "runtime_blocker",
                "attempt_count": attempt_index,
                "trace_present": partial_trace is not None,
                "case_started_at_utc": case_started_at,
                "case_ended_at_utc": _utc_now(),
                "case_latency_ms": _elapsed_ms(case_started_perf),
                "attempts": attempts,
                "runtime_blocker": runtime_blocker,
                **({"trace": partial_trace} if partial_trace is not None else {}),
            }
        except _ProviderTraceShapeError as exc:
            return {
                "case_id": case_id,
                "input_message": message,
                "case_execution_status": "provider_trace_blocker",
                "attempt_count": attempt_index,
                "trace_present": False,
                "case_started_at_utc": case_started_at,
                "case_ended_at_utc": _utc_now(),
                "case_latency_ms": _elapsed_ms(case_started_perf),
                "attempts": attempts,
                "provider_trace_blocker": {
                    "reason": "provider_trace_shape_error",
                    "trace_field": exc.trace_field,
                    "observed_type": exc.observed_type,
                    "failing_component": exc.failing_component,
                },
            }
        except Exception as exc:
            provider_runtime = _provider_runtime_summary_for_error(
                readiness=readiness,
                traces=[],
                error=exc,
                smoke_cases=[message],
                provider_timeout_ms=provider_timeout_ms,
                runner_case_attempt_count=attempt_index,
            )
            retryable = _is_retryable_provider_error(exc)
            attempts[-1]["provider_runtime_reason"] = provider_runtime["reason"]
            attempts[-1]["retryable"] = retryable
            attempts[-1]["error_type"] = provider_runtime["error_type"]
            if retryable and attempt_index < max_attempts:
                delay = _runner_retry_delay_seconds(
                    attempt_index=attempt_index,
                    base_seconds=retry_backoff_seconds,
                    jitter_func=jitter_func,
                )
                attempts[-1]["retry_delay_seconds"] = delay
                await _sleep_backoff(delay_seconds=delay, sleep_func=sleep_func)
                continue
            return {
                "case_id": case_id,
                "input_message": message,
                "case_execution_status": provider_runtime["reason"],
                "attempt_count": attempt_index,
                "trace_present": False,
                "case_started_at_utc": case_started_at,
                "case_ended_at_utc": _utc_now(),
                "case_latency_ms": _elapsed_ms(case_started_perf),
                "attempts": attempts,
                "provider_runtime": provider_runtime,
            }
        return {
            "case_id": case_id,
            "input_message": message,
            "case_execution_status": "completed",
            "attempt_count": attempt_index,
            "trace_present": True,
            "case_started_at_utc": case_started_at,
            "case_ended_at_utc": _utc_now(),
            "case_latency_ms": _elapsed_ms(case_started_perf),
            "attempts": attempts,
            "trace": trace,
        }
    raise AssertionError("unreachable targeted case execution path")


async def _run_full_case_with_retries(
    *,
    case_id: str,
    message: str,
    provider: Any,
    pass1_mode: str,
    max_attempts: int,
    retry_backoff_seconds: float,
    sleep_func: Any,
    jitter_func: Any,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt_index in range(1, max_attempts + 1):
        try:
            return await _run_case(
                case_id=case_id,
                message=message,
                provider=provider,
                pass1_mode=pass1_mode,
            )
        except Exception as exc:
            last_error = exc
            if _is_retryable_provider_error(exc) and attempt_index < max_attempts:
                delay = _runner_retry_delay_seconds(
                    attempt_index=attempt_index,
                    base_seconds=retry_backoff_seconds,
                    jitter_func=jitter_func,
                )
                await _sleep_backoff(delay_seconds=delay, sleep_func=sleep_func)
                continue
            raise
    raise last_error or AssertionError("unreachable full case execution path")


async def run_phase_b_minimal_tool_loop_smoke(
    *,
    provider: Any,
    smoke_cases: list[str] | tuple[str, ...] = CORE_SMOKE_CASES,
    requested_case_ids: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    write_latest: bool = True,
    mode: str = "forced",
    provider_timeout_ms: int = DEFAULT_PROVIDER_TIMEOUT_MS,
    provider_profile_id: str | None = None,
    allow_expensive_model_probe: bool = False,
    _retry_max_attempts: int = RUNNER_RETRY_MAX_ATTEMPTS,
    _retry_backoff_seconds: float = RUNNER_RETRY_BASE_BACKOFF_SECONDS,
    _sleep_func: Any = asyncio.sleep,
    _jitter_func: Any | None = None,
) -> dict[str, Any]:
    run_started_perf = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    pass1_mode = CLI_MODES.get(mode, mode)
    if pass1_mode not in {FORCED_MODE, NATURAL_MODE}:
        raise ValueError(f"Unsupported B-1 smoke mode: {mode}")
    if requested_case_ids is not None:
        case_set = "targeted"
        canonical_case_ids = _dedup_preserve_order([str(item).upper() for item in requested_case_ids])
        smoke_cases = [CORE_SMOKE_CASE_MAP[item] for item in canonical_case_ids]
    else:
        case_set = "full"
        canonical_case_ids = _case_ids_for_smoke_cases(smoke_cases)
    selected_provider_profile = _resolve_phase_b1_provider_profile(
        requested_profile_id=provider_profile_id,
        case_set=case_set,
        requested_case_ids=canonical_case_ids,
        allow_expensive_model_probe=allow_expensive_model_probe,
    )
    jitter_func = _jitter_func or (lambda: random.uniform(0.0, max(0.0, _retry_backoff_seconds / 2)))
    phase_b_provider = _PhaseB1ManagerProvider(
        provider,
        pass1_mode=pass1_mode,
        provider_timeout_ms=provider_timeout_ms,
        provider_profile=selected_provider_profile,
        case_set=case_set,
        requested_profile_id=provider_profile_id,
    )
    artifact_path = _build_artifact_path(
        output_dir=output_dir,
        pass1_mode=pass1_mode,
        case_set=case_set,
        requested_case_ids=canonical_case_ids,
    )
    readiness = phase_b_provider.readiness()
    if not readiness.get("configured"):
        report = _provider_unavailable_report(
            readiness=dict(readiness),
            artifact_path=artifact_path,
            pass1_mode=pass1_mode,
            started_perf=run_started_perf,
            smoke_cases=smoke_cases,
            case_set=case_set,
            requested_case_ids=canonical_case_ids,
        )
    elif readiness.get("provider") and readiness.get("provider") != selected_provider_profile.provider:
        report = _provider_profile_mismatch_report(
            readiness=dict(readiness),
            selected_profile=selected_provider_profile,
            artifact_path=artifact_path,
            pass1_mode=pass1_mode,
            started_perf=run_started_perf,
            smoke_cases=smoke_cases,
            case_set=case_set,
            requested_case_ids=canonical_case_ids,
        )
    else:
        traces: list[dict[str, Any]] = []
        if case_set == "targeted":
            case_results: list[dict[str, Any]] = []
            for case_id, message in zip(canonical_case_ids, smoke_cases):
                case_result = await _run_targeted_case_with_retries(
                    case_id=case_id,
                    message=message,
                    provider=phase_b_provider,
                    pass1_mode=pass1_mode,
                    provider_timeout_ms=provider_timeout_ms,
                    readiness=dict(readiness),
                    max_attempts=_retry_max_attempts,
                    retry_backoff_seconds=_retry_backoff_seconds,
                    sleep_func=_sleep_func,
                    jitter_func=jitter_func,
                )
                case_results.append(_json_safe({key: value for key, value in case_result.items() if key != "trace"}))
                if case_result.get("trace_present"):
                    traces.append(_json_safe(case_result["trace"]))
            report = {
                "phase": "B-1",
                "scope": "minimal_tool_loop_smoke",
                "b2_evidence_runtime_started": False,
                "nutrition_accuracy_claimed": False,
                "provider": readiness.get("provider") or "builderspace",
                "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
                "mode": "hybrid_canary",
                "pass1_mode": pass1_mode,
                "forced_tool_request_contract": pass1_mode == FORCED_MODE,
                "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
                "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
                "runtime_latency": _runtime_latency_summary(
                    started_perf=run_started_perf,
                    traces=traces,
                    pass1_mode=pass1_mode,
                    readiness_claim_scope=DIAGNOSTIC_READINESS_SCOPE,
                ),
                **_report_case_metadata(
                    smoke_cases=smoke_cases,
                    traces=traces,
                    case_set=case_set,
                    requested_case_ids=canonical_case_ids,
                ),
                "case_results": case_results,
                "tool_loop_traces": _json_safe(traces),
                "artifact_path": str(artifact_path),
            }
        else:
            try:
                for case_id, message in zip(canonical_case_ids, smoke_cases):
                    traces.append(
                        await _run_full_case_with_retries(
                            case_id=case_id,
                            message=message,
                            provider=phase_b_provider,
                            pass1_mode=pass1_mode,
                            max_attempts=_retry_max_attempts,
                            retry_backoff_seconds=_retry_backoff_seconds,
                            sleep_func=_sleep_func,
                            jitter_func=jitter_func,
                        )
                    )
            except _ManagerPayloadShapeError as exc:
                if exc.partial_trace is not None:
                    traces.append(_json_safe(exc.partial_trace))
                report = _runtime_blocker_report(
                    readiness=dict(readiness),
                    artifact_path=artifact_path,
                    smoke_cases=smoke_cases,
                    traces=traces,
                    blocker=exc,
                    pass1_mode=pass1_mode,
                    started_perf=run_started_perf,
                    case_set=case_set,
                    requested_case_ids=canonical_case_ids,
                )
            except _ProviderTraceShapeError as exc:
                report = _provider_trace_blocker_report(
                    readiness=dict(readiness),
                    artifact_path=artifact_path,
                    smoke_cases=smoke_cases,
                    traces=traces,
                    blocker=exc,
                    pass1_mode=pass1_mode,
                    started_perf=run_started_perf,
                    case_set=case_set,
                    requested_case_ids=canonical_case_ids,
                )
            except Exception as exc:
                report = _provider_runtime_error_report(
                    readiness=dict(readiness),
                    artifact_path=artifact_path,
                    smoke_cases=smoke_cases,
                    traces=traces,
                    error=exc,
                    pass1_mode=pass1_mode,
                    started_perf=run_started_perf,
                    provider_timeout_ms=provider_timeout_ms,
                    case_set=case_set,
                    requested_case_ids=canonical_case_ids,
                )
            else:
                report = {
                    "phase": "B-1",
                    "scope": "minimal_tool_loop_smoke",
                    "b2_evidence_runtime_started": False,
                    "nutrition_accuracy_claimed": False,
                    "provider": readiness.get("provider") or "builderspace",
                    "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
                    "mode": "hybrid_canary",
                    "pass1_mode": pass1_mode,
                    "forced_tool_request_contract": pass1_mode == FORCED_MODE,
                    "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
                    "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
                    "runtime_latency": _runtime_latency_summary(
                        started_perf=run_started_perf,
                        traces=traces,
                        pass1_mode=pass1_mode,
                        readiness_claim_scope=FULL_READINESS_SCOPE,
                    ),
                    **_report_case_metadata(
                        smoke_cases=smoke_cases,
                        traces=traces,
                        case_set=case_set,
                        requested_case_ids=canonical_case_ids,
                    ),
                    "tool_loop_traces": _json_safe(traces),
                    "artifact_path": str(artifact_path),
                }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_latest:
        LATEST_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return _json_safe(report)


async def _async_main() -> int:
    parser = argparse.ArgumentParser(description="Run Wave 1 Phase B-1 minimal runtime LLM tool-loop smoke.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--mode", choices=sorted(CLI_MODES), default="forced")
    parser.add_argument("--cases", default=None)
    parser.add_argument("--case-set", choices=("targeted",), default=None)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--provider-timeout-ms", type=int, default=DEFAULT_PROVIDER_TIMEOUT_MS)
    parser.add_argument("--provider-profile-id", default=None)
    parser.add_argument("--allow-expensive-model-probe", action="store_true")
    args = parser.parse_args()
    from app.runtime.interface.provider_runtime import manager_provider

    requested_case_ids = _resolve_cli_targeted_case_ids(
        cases=args.cases,
        case_set=args.case_set,
        case_id=args.case_id,
    )
    mode, provider_profile_id = _legacy_cli_defaults_for_targeted_case(
        requested_case_ids=requested_case_ids,
        mode=args.mode,
        provider_profile_id=args.provider_profile_id,
        used_legacy_targeting=bool(args.case_set or args.case_id),
    )

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=manager_provider,
        output_dir=Path(args.output_dir),
        mode=mode,
        requested_case_ids=requested_case_ids,
        provider_timeout_ms=args.provider_timeout_ms,
        provider_profile_id=provider_profile_id,
        allow_expensive_model_probe=args.allow_expensive_model_probe,
    )
    print(
        json.dumps(
            {
                "phase": report.get("phase"),
                "scope": report.get("scope"),
                "artifact_path": report.get("artifact_path"),
                "trace_count": len(report.get("tool_loop_traces") or []),
                "provider_runtime": report.get("provider_runtime"),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
