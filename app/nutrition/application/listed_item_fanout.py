from __future__ import annotations

from dataclasses import dataclass

from .retrieval_intent import RetrievalIntent
from .small_anchor_store import AnchorLookupResult, lookup_anchor_candidates


@dataclass(frozen=True)
class ListedItemFanoutResolution:
    listed_item: str
    sub_intent: RetrievalIntent
    lookup_result: AnchorLookupResult


def fanout_listed_item_anchor_lookups(
    intent: RetrievalIntent,
) -> tuple[ListedItemFanoutResolution, ...]:
    if intent.retrieval_goal != "listed_item_lookup" or not intent.listed_items:
        return ()

    resolutions: list[ListedItemFanoutResolution] = []
    for listed_item in intent.listed_items:
        sub_intent = RetrievalIntent(
            base_dish=intent.base_dish,
            aliases=[],
            brand_hint=intent.brand_hint,
            size_hint=intent.size_hint,
            modifier_hints=list(intent.modifier_hints),
            listed_items=[listed_item],
            retrieval_goal="listed_item_lookup",
        )
        resolutions.append(
            ListedItemFanoutResolution(
                listed_item=listed_item,
                sub_intent=sub_intent,
                lookup_result=lookup_anchor_candidates(sub_intent),
            )
        )
    return tuple(resolutions)


__all__ = ["ListedItemFanoutResolution", "fanout_listed_item_anchor_lookups"]
