from __future__ import annotations

from pathlib import Path


SPEC_PATH = Path(
    "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md"
)


def test_recommendation_runtime_graph_spec_locks_final_product_stages() -> None:
    content = SPEC_PATH.read_text(encoding="utf-8-sig")
    normalized = " ".join(content.split())

    required_fragments = [
        "3-node physical graph",
        "5 個 logical stage boundaries",
        "`recommendation_planning`",
        "`candidate_retrieval_guard_scoring`",
        "`offer_synthesis`",
        "3 個 physical responsibility handoffs + 5 個 logical trace artifacts",
        "canonical physical runtime graph",
        "compatibility / observability reference",
        "`recommendation_context_result`",
        "`candidate_spec`",
        "`ranking_result`",
        "`recommendation_response_result`",
        "不是要求 5 個 physical runtime nodes",
    ]
    for fragment in required_fragments:
        assert fragment in normalized
