import json

from app.providers.builderspace_adapter import BuilderSpaceAdapter
from app.schemas import ComponentEstimate


def test_format_user_message_serializes_pydantic_objects() -> None:
    adapter = BuilderSpaceAdapter()
    payload = {
        "original_answer": {
            "component_estimates": [
                ComponentEstimate(
                    name="Test",
                    source="lookup",
                    evidence_role="ingredient_anchor",
                    estimate_basis="anchored",
                    confidence_tier="medium",
                    estimated_kcal=100,
                    protein_g=5,
                    carb_g=10,
                    fat_g=3,
                )
            ]
        }
    }

    serialized = adapter._format_user_message("final_response_pass", payload)
    parsed = json.loads(serialized)
    assert parsed["original_answer"]["component_estimates"][0]["name"] == "Test"
