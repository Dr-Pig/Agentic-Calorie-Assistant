"""
Text Meal Orchestrator - Main coordination for food estimation.

This module is the entry point for the food estimation pipeline.
It coordinates all passes, manages state, and produces the final payload.

Best Practices:
- Single responsibility: orchestration
- Passes are isolated and testable
- State flows through dataclasses
- Full trace maintained for observability
"""

from __future__ import annotations

from typing import Any

from .context import ContextBuilder, ConversationStateManager
from .evidence import EvidenceRetrieval, GroundingPipeline
from .passes import (
    run_planner_pass,
    run_decision_pass,
    run_nutrition_resolution_pass,
    run_final_response_pass,
)
from .passes.base import PassContext


MAX_SELECTED_EVIDENCE_ITEMS = 3
MAX_DURABLE_MEMORY_HITS = 3


class TextMealOrchestrator:
    """
    Main orchestrator for the food estimation pipeline.

    Coordinates:
    1. State loading
    2. Planner pass (intent + meal boundary)
    3. Evidence retrieval (local knowledge)
    4. Decision pass (route decision)
    5. Grounding pass (search if needed)
    6. Nutrition resolution pass
    7. Final response pass
    8. State persistence
    """

    def __init__(self):
        self.state_manager = ConversationStateManager()
        self.context_builder = ContextBuilder()
        self.evidence_retrieval = EvidenceRetrieval()
        self.grounding_pipeline = GroundingPipeline()

    async def run(
        self,
        request: Any,
        provider: Any,
        planner_provider: Any | None = None,
        request_id: str = "",
        search_adapter: Any | None = None,
        db: Any | None = None,
    ) -> dict[str, Any]:
        """
        Execute the full food estimation pipeline.

        Returns:
            EstimatePayload compatible dict
        """
        # Initialize context
        ctx = PassContext(
            request_id=request_id,
            user_id=getattr(request, "user_id", "default_user"),
            user_input=request.text,
            allow_search=getattr(request, "allow_search", True),
        )

        # Load conversation state
        loaded = self.state_manager.load(
            db,
            ctx.user_id,
            ctx.user_input,
        )
        if loaded:
            ctx.conversation_state = loaded.state.model_dump()
            ctx.user = loaded.user
            ctx.debug_steps.append({
                "request_id": request_id,
                "step": "state_load",
                "success": True,
            })
        else:
            ctx.debug_steps.append({
                "request_id": request_id,
                "step": "state_load",
                "success": False,
            })

        # Step 1: Planner Pass (Intent + Meal Boundary)
        planner_result, task_meal_link_result, context_str = await run_planner_pass(
            provider=provider,
            planner_provider=planner_provider,
            request_id=request_id,
            user_input=ctx.user_input,
            conversation_state=loaded.state if loaded else None,
            llm_traces=ctx.llm_traces,
            debug_steps=ctx.debug_steps,
        )

        ctx.planner_result = planner_result.model_dump()
        ctx.task_meal_link_result = task_meal_link_result.model_dump()

        # Build canonical meal state
        canonical = self._build_canonical_meal_state(
            loaded.latest_log if loaded else None,
            loaded.state if loaded else None,
        )
        ctx.canonical_meal_state = canonical.model_dump() if canonical else None

        # Step 2: Evidence Retrieval (Local Knowledge)
        retrieval_query = (
            planner_result.resolved_query.strip()
            or ctx.user_input
        )
        evidence_result = self.evidence_retrieval.execute(
            retrieval_query=retrieval_query,
            evidence_strategy=planner_result.planning_brief.evidence_strategy,
            input_signals=planner_result.input_signals,
            user_input=ctx.user_input,
        )

        ctx.retrieved_knowledge = evidence_result.filtered_knowledge
        ctx.executed_tool_calls.extend(evidence_result.executed_tool_calls)

        ctx.debug_steps.append({
            "request_id": request_id,
            "step": "local_retrieval",
            "retrieval_query": retrieval_query,
            "result_count": len(ctx.retrieved_knowledge),
        })

        # Step 3: Decision Pass
        available_tools = ["resolve_exact_item", "get_meal_calibration", "resolve_ingredient_anchors"]
        if ctx.allow_search and search_adapter:
            available_tools.extend(["search_official_nutrition", "read_official_doc_fragment"])

        decision_result, _ = await run_decision_pass(
            provider=provider,
            request_id=request_id,
            user_input=ctx.user_input,
            task_meal_link_result=task_meal_link_result,
            canonical_meal_state=canonical,
            filtered_knowledge=ctx.retrieved_knowledge,
            request=request,
            search_adapter=search_adapter,
            llm_traces=ctx.llm_traces,
            debug_steps=ctx.debug_steps,
        )

        ctx.decision_result = decision_result.model_dump()

        # Step 4: Grounding (Search if needed)
        grounding_result = await self.grounding_pipeline.execute(
            decision_result=decision_result,
            retrieval_query=retrieval_query,
            planner_result=planner_result,
            request=request,
            search_adapter=search_adapter,
            canonical_meal_state=canonical,
            task_meal_link_result=task_meal_link_result,
            existing_sources=ctx.sources,
            existing_filtered=ctx.retrieved_knowledge,
            executed_tool_calls=ctx.executed_tool_calls,
        )

        ctx.sources = grounding_result.sources
        ctx.used_search = grounding_result.used_search
        ctx.search_query = grounding_result.search_query
        ctx.search_quality = grounding_result.search_quality

        # Step 5: Nutrition Resolution Pass
        from ...agent.knowledge_packets import build_gate_packet, match_meal_template
        risk_packet = build_gate_packet(ctx.user_input)
        meal_template = match_meal_template(ctx.user_input, risk_packet)

        # Get normalized evidence for nutrition pass
        from ...application.evidence_assembly import normalize_tool_evidence
        normalized_evidence = normalize_tool_evidence(
            ctx.retrieved_knowledge,
            source_type="local_retrieval",
            query=retrieval_query,
            limit=MAX_SELECTED_EVIDENCE_ITEMS,
        )

        active_meal_context_allowed = (
            task_meal_link_result.meal_link_action == "attach_to_existing_meal"
        )

        (
            current_parsed,
            nutrition_result,
            ctx.retrieved_knowledge,
            ctx.sources,
            ctx.used_search,
            ctx.search_query,
            ctx.search_quality,
        ) = await run_nutrition_resolution_pass(
            provider=provider,
            request_id=request_id,
            user_input=ctx.user_input,
            task_meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            canonical_meal_state=canonical,
            filtered_knowledge=ctx.retrieved_knowledge,
            normalized_evidence=normalized_evidence,
            risk_packet=risk_packet,
            meal_template=meal_template,
            active_meal_context_allowed=active_meal_context_allowed,
            latest_log=loaded.latest_log if loaded else None,
            llm_traces=ctx.llm_traces,
            debug_steps=ctx.debug_steps,
            executed_tool_calls=ctx.executed_tool_calls,
            sources=ctx.sources,
            used_search=ctx.used_search,
            search_query=ctx.search_query,
            search_quality=ctx.search_quality,
            search_adapter=search_adapter,
        )

        ctx.nutrition_result = nutrition_result.model_dump()

        # Step 6: Final Response Pass
        active_meal_summary = (
            loaded.state.active_meal_summary.model_dump()
            if loaded and loaded.state
            else {}
        )

        final_response, asked_follow_up = await run_final_response_pass(
            provider=provider,
            request_id=request_id,
            user_input=ctx.user_input,
            task_meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            nutrition_result=nutrition_result,
            active_meal_summary=active_meal_summary,
            llm_traces=ctx.llm_traces,
        )

        ctx.final_response_result = final_response.model_dump()

        # Step 7: Quality evaluation
        from ...application.answer_support import evaluate_answer, is_private_only_case
        quality = evaluate_answer(current_parsed, risk_packet, meal_template)
        quality["invalid_zero_kcal_candidate"] = current_parsed.get("estimated_kcal", 0) <= 0
        ctx.quality_signals = quality

        private_only = is_private_only_case(current_parsed, risk_packet, ctx.user_input)

        # Determine action
        requires_follow_up = (
            planner_result.meal_boundary == "boundary_clarification"
            or bool(current_parsed.get("follow_up_needed"))
            or str(current_parsed.get("action_taken", "")) == "clarify_before_estimate"
        )

        if requires_follow_up:
            action_taken = "clarify_before_estimate"
            route_target = "clarify_user_private"
        else:
            action_taken = (
                "answer_with_uncertainty"
                if str(current_parsed.get("action_taken", "")) == "answer_with_uncertainty"
                else "direct_answer"
            )
            route_target = "best_effort_answer"

        # Step 8: Persist state
        persistence_decision = None
        if db and loaded:
            persistence_decision = self.state_manager.persist(
                db=db,
                user=loaded.user,
                latest_log=loaded.latest_log,
                planner_intent=planner_result.intent,
                payload=self._build_payload_dict(ctx, action_taken, route_target, quality, private_only),
                raw_input=ctx.user_input,
                request_id=request_id,
                incoming_user_message_id=loaded.incoming_user_message_id,
            )

        # Build final payload
        return self._build_payload_dict(
            ctx, action_taken, route_target, quality, private_only,
            persistence_decision=persistence_decision,
            reply_text=ctx.final_response_result.get("reply_text", ""),
            asked_follow_up=asked_follow_up,
        )

    def _build_canonical_meal_state(self, latest_log: Any, state: Any) -> Any:
        """Build canonical meal state from loaded context."""
        from ...application.state_transition import canonical_meal_state_from_runtime
        from ...application.context_assembly import normalize_text
        return canonical_meal_state_from_runtime(
            latest_log=latest_log,
            state=state,
            normalize_text=normalize_text,
        )

    def _build_payload_dict(
        self,
        ctx: PassContext,
        action_taken: str,
        route_target: str,
        quality: dict[str, Any],
        private_only: bool,
        persistence_decision: dict[str, Any] | None = None,
        reply_text: str = "",
        asked_follow_up: bool = False,
    ) -> dict[str, Any]:
        """Build the final payload dictionary."""
        # Simplified payload building - full implementation would include all fields
        return {
            "request_id": ctx.request_id,
            "meal_title": ctx.nutrition_result.get("answer_payload", {}).get("title", ctx.user_input),
            "components": ctx.nutrition_result.get("answer_payload", {}).get("components", []),
            "protein_g": ctx.nutrition_result.get("answer_payload", {}).get("protein_g", 0),
            "carb_g": ctx.nutrition_result.get("answer_payload", {}).get("carb_g", 0),
            "fat_g": ctx.nutrition_result.get("answer_payload", {}).get("fat_g", 0),
            "estimated_kcal": ctx.nutrition_result.get("answer_payload", {}).get("estimated_kcal", 0),
            "action_taken": action_taken,
            "route_target": route_target,
            "reply_text": reply_text,
            "asked_follow_up": asked_follow_up,
            "debug_steps": ctx.debug_steps,
            "llm_traces": ctx.llm_traces,
            "quality_signals": quality,
            "retrieved_knowledge": ctx.retrieved_knowledge,
            "sources": ctx.sources,
            "used_search": ctx.used_search,
            "search_query": ctx.search_query,
            "search_quality": ctx.search_quality,
        }
