from __future__ import annotations

from pathlib import Path


SPEC_PATH = Path(
    "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md"
)


def test_recommendation_runtime_graph_spec_locks_final_product_stages() -> None:
    content = SPEC_PATH.read_text(encoding="utf-8-sig")
    normalized = " ".join(content.split())

    required_fragments = [
        "final product 的 semantic runtime contract",
        "5 個 logical stage boundaries",
        "physical implementation compaction profile",
        "`recommendation_context_result`",
        "`candidate_spec`",
        "`ranking_result`",
        "`recommendation_response_result`",
        "不得省略 `candidate_spec_generation`",
        "不得省略 deterministic retrieval / guard",
        "4-node graph 不是禁用",
        "不是新的 canonical architecture",
    ]
    for fragment in required_fragments:
        assert fragment in normalized
