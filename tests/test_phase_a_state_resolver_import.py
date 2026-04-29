from __future__ import annotations

import importlib


def test_phase_a_state_resolver_import_smoke() -> None:
    module = importlib.import_module("app.runtime.application.state_resolver")

    assert module.__name__ == "app.runtime.application.state_resolver"
