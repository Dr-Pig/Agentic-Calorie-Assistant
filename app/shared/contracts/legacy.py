from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .intake import IngredientCandidate


class LegacyDecisionDraft(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    food_type: str = "unknown"
    decision: str = "DIRECT_ANSWER"
    ingredients: list[IngredientCandidate] = Field(default_factory=list)
    ingredients_known_enough: bool = False
    missing_info: list[str] = Field(default_factory=list)
    searchable: bool = False
    recommended_action: str = "ask_user"
    question_for_user: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    retrieval_query: str = ""
    components: list[str] = Field(default_factory=list)
    dish_structure: Literal[
        "single_exact_item",
        "multi_component_simple",
        "composite_cooked_dish",
        "customizable_drink",
        "customizable_bowl",
    ] = "multi_component_simple"
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    estimated_kcal: int = 0
    uncertainty_factors: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    followup_question: str = ""
