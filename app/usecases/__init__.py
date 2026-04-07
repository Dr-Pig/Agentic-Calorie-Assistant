"""
Use Cases Package - Food estimation pipeline components.

Modules:
- text_meal_orchestrator: Main pipeline orchestrator
- passes: LLM pass modules (planner, decision, nutrition, final_response)
- evidence: Evidence retrieval and grounding
- context: Context building and state management
"""

from .text_meal_orchestrator import TextMealOrchestrator
from .passes import (
    PassResult,
    PassConfig,
    run_text_stage,
    run_planner_pass,
    run_decision_pass,
    run_nutrition_resolution_pass,
    run_final_response_pass,
)
from .evidence import EvidenceRetrieval, GroundingPipeline
from .context import ContextBuilder, ConversationStateManager

__all__ = [
    # Main orchestrator
    "TextMealOrchestrator",
    # Passes
    "PassResult",
    "PassConfig",
    "run_text_stage",
    "run_planner_pass",
    "run_decision_pass",
    "run_nutrition_resolution_pass",
    "run_final_response_pass",
    # Evidence
    "EvidenceRetrieval",
    "GroundingPipeline",
    # Context
    "ContextBuilder",
    "ConversationStateManager",
]
