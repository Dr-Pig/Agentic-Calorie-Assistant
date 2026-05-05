from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

import app.composition.conversation_state_loader as conversation_state_loader
import app.nutrition.application.small_anchor_store as small_anchor_store
import app.nutrition.infrastructure.exact_item_search as exact_item_search
import app.runtime.interface.base_routes as base_routes
from app.database import get_meal_log_history
from app.nutrition.application.retrieval_intent import RetrievalIntent


def _clear_small_anchor_store_default_caches() -> None:
    small_anchor_store._load_default_small_anchor_items.cache_clear()
    small_anchor_store._load_default_anchor_records.cache_clear()
    small_anchor_store._load_default_anchor_lookup_index.cache_clear()


def test_exact_item_search_card_index_is_cached(monkeypatch) -> None:
    exact_item_search._load_cards.cache_clear()
    exact_item_search._cards_by_id.cache_clear()
    calls = {"count": 0}

    def _fake_loader() -> list[dict[str, object]]:
        calls["count"] += 1
        return [
            {
                "card_id": "card-1",
                "title": "Test Drink",
                "aliases": ["drink"],
                "brand": "brand",
            }
        ]

    monkeypatch.setattr(exact_item_search, "load_exact_item_card_seed_records", _fake_loader)

    try:
        assert exact_item_search._cards_by_id()["card-1"]["title"] == "Test Drink"
        assert exact_item_search._cards_by_id()["card-1"]["brand"] == "brand"
        assert calls["count"] == 1
    finally:
        exact_item_search._load_cards.cache_clear()
        exact_item_search._cards_by_id.cache_clear()


def test_exact_item_search_accepts_injected_engine(monkeypatch) -> None:
    exact_item_search._load_cards.cache_clear()
    exact_item_search._cards_by_id.cache_clear()
    engine = create_engine("sqlite:///:memory:")

    def _fake_loader() -> list[dict[str, object]]:
        return [
            {
                "card_id": "card-1",
                "title": "Test Drink",
                "aliases": ["Test Drink"],
                "brand": "Test Brand",
                "kcal": 123,
                "protein_g": 1,
                "carb_g": 2,
                "fat_g": 3,
                "serving_basis": "one bottle",
            }
        ]

    monkeypatch.setattr(exact_item_search, "load_exact_item_card_seed_records", _fake_loader)

    try:
        rows = exact_item_search.resolve_exact_item_fts("Test Drink", engine=engine)

        assert rows[0]["item_id"] == "card-1"
        assert rows[0]["source_class"] == "exact_item_db"
        assert rows[0]["kcal"] == 123
    finally:
        exact_item_search._load_cards.cache_clear()
        exact_item_search._cards_by_id.cache_clear()


def test_small_anchor_store_anchor_record_conversion_is_cached(monkeypatch) -> None:
    _clear_small_anchor_store_default_caches()
    calls = {"count": 0}

    def _fake_loader() -> list[dict[str, object]]:
        calls["count"] += 1
        return [
            {
                "record_kind": "generic_anchor",
                "anchor_id": "tea-egg",
                "canonical_name": "茶葉蛋",
                "aliases": ["茶葉蛋"],
                "dish_type": "snack",
                "semantic_hints": [],
                "followup_hints": [],
                "clarify_required": False,
                "baseline_kcal_range": [70, 80],
                "baseline_likely_kcal": 75,
                "major_modifiers": [],
                "composition_hints": [],
            }
        ]

    class _FakeEvidenceStore:
        def load_small_anchor_records(self) -> list[dict[str, object]]:
            return _fake_loader()

        def load_exact_item_card_records(self) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr(small_anchor_store, "default_nutrition_evidence_store", lambda: _FakeEvidenceStore())

    try:
        first = small_anchor_store._load_default_anchor_records()
        second = small_anchor_store._load_default_anchor_records()

        assert first == second
        assert first[0].canonical_name == "茶葉蛋"
        assert calls["count"] == 1
    finally:
        _clear_small_anchor_store_default_caches()


def test_small_anchor_store_default_lookup_index_is_cached(monkeypatch) -> None:
    _clear_small_anchor_store_default_caches()
    calls = {"count": 0}

    def _fake_loader() -> list[dict[str, object]]:
        calls["count"] += 1
        return [
            {
                "record_kind": "generic_anchor",
                "anchor_id": "test-food",
                "canonical_name": "test food",
                "aliases": ["tf"],
                "dish_type": "snack",
                "semantic_hints": [],
                "followup_hints": [],
                "clarify_required": False,
                "baseline_kcal_range": [10, 20],
                "baseline_likely_kcal": 15,
                "major_modifiers": [],
                "composition_hints": [],
            },
            {
                "record_kind": "generic_semantic_only",
                "canonical_name": "test basket",
                "aliases": ["basket"],
                "dish_type": "mixed_basket",
                "composition_posture": "composition_unknown",
                "variance_level": "high",
                "semantic_hints": ["test_semantic_only"],
                "followup_hints": ["ask_listed_items"],
                "clarify_required": True,
            },
        ]

    class _FakeEvidenceStore:
        def load_small_anchor_records(self) -> list[dict[str, object]]:
            return _fake_loader()

        def load_exact_item_card_records(self) -> list[dict[str, object]]:
            return []

    def _intent(base_dish: str, retrieval_goal: str = "generic_anchor_lookup") -> RetrievalIntent:
        return RetrievalIntent(
            base_dish=base_dish,
            aliases=[],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal=retrieval_goal,
        )

    store = _FakeEvidenceStore()
    monkeypatch.setattr(small_anchor_store, "default_nutrition_evidence_store", lambda: store)

    try:
        canonical = small_anchor_store.lookup_anchor_candidates(_intent("test food"))
        alias = small_anchor_store.lookup_anchor_candidates(_intent("tf"))
        semantic = small_anchor_store.lookup_anchor_candidates(_intent("test basket", "composition_clarification"))

        assert [candidate.canonical_name for candidate in canonical.candidates] == ["test food"]
        assert alias.candidates[0].matched_alias == "tf"
        assert alias.candidates[0].match_path == "alias_exact"
        assert semantic.clarify_support is not None
        assert semantic.clarify_support.canonical_name == "test basket"
        assert calls["count"] == 1
    finally:
        _clear_small_anchor_store_default_caches()


def test_load_conversation_state_uses_bounded_in_memory_retrieval_without_request_sidecar_sync(monkeypatch) -> None:
    calls: list[str] = []
    archive_limits: list[int | None] = []

    monkeypatch.setattr(conversation_state_loader, "get_or_create_user", lambda db, user_id: SimpleNamespace(id=user_id))
    monkeypatch.setattr(conversation_state_loader, "get_latest_log", lambda db, user: None)
    monkeypatch.setattr(conversation_state_loader, "get_meal_log_history", lambda db, user, limit, include_superseded: [])
    monkeypatch.setattr(conversation_state_loader, "get_recent_messages", lambda db, user, limit: [])

    def _fake_archive(db, user, limit=None):
        archive_limits.append(limit)
        return []

    monkeypatch.setattr(conversation_state_loader, "get_conversation_archive", _fake_archive)
    monkeypatch.setattr(conversation_state_loader, "build_session_transcript_records", lambda session_id, archive_messages: [])
    monkeypatch.setattr(conversation_state_loader, "build_session_meal_records", lambda session_id, meal_history: [])
    monkeypatch.setattr(conversation_state_loader, "build_archive_records", lambda archive_messages: [])

    def _fake_retrieve_from_records(**kwargs):
        calls.append("memory")
        return [], [], None, {"source": "memory"}

    def _fake_sync(**kwargs):
        raise AssertionError("request path should not synchronously rewrite session sidecar by default")

    class _FakeRetriever:
        def retrieve(self, **kwargs):
            return []

    monkeypatch.setattr(conversation_state_loader, "retrieve_manager_context_from_records", _fake_retrieve_from_records)
    monkeypatch.setattr(conversation_state_loader, "sync_session_records", _fake_sync)
    monkeypatch.setattr(conversation_state_loader, "ConversationArchiveRetriever", _FakeRetriever)
    monkeypatch.setattr(
        conversation_state_loader,
        "assemble_conversation_state",
        lambda **kwargs: {
            "retrieval_diagnostics": kwargs["retrieval_diagnostics"],
            "archive_hits": kwargs["archive_hits"],
        },
    )

    loaded = conversation_state_loader.load_conversation_state(
        db=object(),
        user_id="user-1",
        incoming_user_text="hello",
        persist_incoming_user_text=False,
    )

    assert calls == ["memory"]
    assert archive_limits == [conversation_state_loader.DEFAULT_CONVERSATION_ARCHIVE_LIMIT]
    assert loaded.state["retrieval_diagnostics"] == {"source": "memory"}


def test_get_meal_log_history_does_not_count_before_limited_fetch() -> None:
    class _FakeQuery:
        def __init__(self) -> None:
            self.limit_value: int | None = None

        def filter(self, *args):
            return self

        def count(self) -> int:
            raise AssertionError("limited history read should not run an unbounded count query")

        def order_by(self, *args):
            return self

        def limit(self, value: int):
            self.limit_value = value
            return self

        def all(self):
            return ["meal-row"]

    fake_query = _FakeQuery()

    class _FakeDb:
        def query(self, model):
            return fake_query

    rows = get_meal_log_history(_FakeDb(), SimpleNamespace(id=1), limit=30, include_superseded=True)

    assert rows == ["meal-row"]
    assert fake_query.limit_value == 30


def test_intake_execution_response_uses_preloaded_budget_views(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.composition import intake_execution_response as module

    assert not hasattr(module, "build_remaining_budget_answer_contract")

    class _PlanView:
        body_plan_id = 10

        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            return {"body_plan_id": self.body_plan_id}

    class _BudgetView:
        user_id = 1
        local_date = "2026-04-29"
        budget_kcal = 1800
        consumed_kcal = 1100
        remaining_kcal = 700
        active_meal_count = 2

        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            return {
                "user_id": self.user_id,
                "local_date": self.local_date,
                "budget_kcal": self.budget_kcal,
                "consumed_kcal": self.consumed_kcal,
                "remaining_kcal": self.remaining_kcal,
                "active_meal_count": self.active_meal_count,
            }

    class _State:
        user_id = 1
        onboarding_ready = True
        injected_context: dict[str, object] = {}

        def __init__(self) -> None:
            self.active_body_plan_view = _PlanView()
            self.current_budget_view = _BudgetView()

    monkeypatch.setattr(module, "render_intake_reply", lambda **kwargs: f"remaining {kwargs['remaining_budget'].remaining_kcal}")
    monkeypatch.setattr(module, "build_deterministic_sidecar", lambda **kwargs: {"state_mutation_summary": kwargs["state_mutation_summary"]})
    monkeypatch.setattr(
        module,
        "enforce_intake_output_honesty",
        lambda assistant_message, state_delta, sidecar, phase_a_trace, **kwargs: SimpleNamespace(
            assistant_message=assistant_message,
            state_delta=state_delta,
            sidecar=sidecar,
            phase_a_trace=phase_a_trace,
        ),
    )
    monkeypatch.setattr(
        module,
        "apply_shadow_hypothesis_dialogue_cue",
        lambda assistant_message, phase_a_trace: SimpleNamespace(
            assistant_message=assistant_message,
            phase_a_trace=phase_a_trace,
        ),
    )
    monkeypatch.setattr(module, "build_phase_c_trace", lambda **kwargs: {})
    monkeypatch.setattr(module, "build_phase_c_same_truth_gate", lambda **kwargs: {"status": "ok"})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **kwargs: None)
    monkeypatch.setattr(module, "write_intake_execution_trace_artifact", lambda **kwargs: None)
    monkeypatch.setattr(module, "build_trace_refs", lambda **kwargs: {"request_id": kwargs["request_id"]})

    result = module.build_intake_execution_response(
        object(),
        request_id="req-hot-path",
        user_external_id="user-1",
        raw_user_input="milk tea",
        local_date="2026-04-29",
        allow_search=False,
        state_before=_State(),
        state_after=_State(),
        manager_decision=SimpleNamespace(
            intent_type="log_meal",
            workflow_effect="commit",
            response_summary="",
            pending_followup=None,
            tool_calls=[],
            llm_used=False,
            trace={},
        ),
        manager_result=SimpleNamespace(
            final_action="commit",
            workflow_effect="commit",
            manager_rounds=[],
            tool_calls=[],
        ),
        nutrition_artifact=None,
        persistence_result=None,
        budget_summary=None,
        tool_outputs={},
        state_mutation_summary={},
        stage_timings=[],
        phase_a_trace={},
    )

    assert result["remaining_budget"]["remaining_kcal"] == 700


@pytest.mark.asyncio
async def test_tavily_search_reuses_one_client_for_search_and_extract(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.providers import tavily_adapter

    created_clients: list[object] = []

    class _FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class _FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            created_clients.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, object]) -> _FakeResponse:
            if url.endswith("/search"):
                return _FakeResponse({"results": [{"title": "Menu", "url": "https://example.com/menu", "content": "official menu"}]})
            return _FakeResponse({"results": [{"url": "https://example.com/menu", "title": "Menu", "raw_content": "per cup 400 kcal"}]})

    monkeypatch.setattr(tavily_adapter.httpx, "AsyncClient", _FakeAsyncClient)
    adapter = tavily_adapter.TavilyAdapter()
    monkeypatch.setattr(adapter, "_is_configured", lambda: True)

    rows = await adapter.search("milk tea")

    assert rows
    assert len(created_clients) == 1


def test_render_latest_trace_debug_uses_single_trace_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.budget.interface import today_trace_debug as module

    assert not hasattr(module, "find_latest_trace_for_user_date")

    calls: list[tuple[str, str, tuple[str, ...]]] = []

    def _fake_batch_lookup(*, user_id: str, local_date: str, bundles):
        calls.append((user_id, local_date, tuple(bundles)))
        return {
            "intake_execution": {
                "request_id": "req-1",
                "trace_meta": {"request_id": "req-1"},
                "request": {"text": "milk tea"},
                "tool_outputs": {"nutrition_artifact": {"payload": {"estimated_kcal": 400}}},
            },
            "intake_turn": None,
        }

    monkeypatch.setattr(module, "find_latest_traces_for_user_date", _fake_batch_lookup, raising=False)
    monkeypatch.setattr(
        module,
        "find_latest_trace_for_user_date",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not scan trace files once per bundle")),
        raising=False,
    )

    html = module.render_latest_trace_debug(user_id="user-1", local_date="2026-04-29")

    assert "req-1" in html
    legacy_execution_trace = "v2_" + "bundle2"
    legacy_turn_trace = "v2_" + "bundle1"
    assert calls == [("user-1", "2026-04-29", ("intake_execution", "intake_turn", legacy_execution_trace, legacy_turn_trace))]


def test_trace_debug_fields_do_not_carry_prerendered_html() -> None:
    from app.budget.interface import today_trace_debug as module

    field_names = {field.name for field in fields(module._TraceDebugFields)}

    assert "manager_decision_html" not in field_names
    assert "trace_link_html" not in field_names


def test_index_html_loader_caches_disk_read(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    index_path = tmp_path / "index.html"
    index_path.write_text("first", encoding="utf-8")
    monkeypatch.setattr(base_routes, "_INDEX_HTML_PATH", index_path, raising=False)
    monkeypatch.setattr(base_routes, "_INDEX_HTML_CACHE", None, raising=False)

    assert base_routes._load_index_html() == "first"
    index_path.write_text("second", encoding="utf-8")
    assert base_routes._load_index_html() == "first"
