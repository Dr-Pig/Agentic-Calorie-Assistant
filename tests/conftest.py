from __future__ import annotations

from pathlib import Path

import pytest


SMOKE_FILES = {
    "test_body_observation_persistence.py",
    "test_canonical_persistence.py",
    "test_context_memory_contract.py",
    "test_current_budget_read_model.py",
    "test_knowledge_packets.py",
    "test_pass_runner_and_invariants.py",
    "test_rescue_overlay.py",
    "test_routes_today_ui.py",
    "test_routes_weight_ui.py",
    "test_search_ranking.py",
}

E2E_PATTERNS = (
    "wide_research",
    "benchmark",
    "real_world_regression",
    "trace_eval",
    "eval_runner",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        filename = Path(str(item.fspath)).name
        if filename in SMOKE_FILES:
            item.add_marker(pytest.mark.smoke)
            continue
        if any(pattern in filename for pattern in E2E_PATTERNS):
            item.add_marker(pytest.mark.e2e)
            continue
        item.add_marker(pytest.mark.integration)
