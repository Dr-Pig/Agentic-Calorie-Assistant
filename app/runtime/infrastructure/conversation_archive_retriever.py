from __future__ import annotations

import re
from typing import Iterable

from app.shared.domain import ConversationArchiveRecord, ConversationRetrievalHit


def _tokenize(text: str) -> list[str]:
    normalized = (text or "").lower()
    return [token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized) if len(token) > 1]


def _record_text(record: ConversationArchiveRecord) -> str:
    excerpt_text = " ".join(str(message.content or "") for message in record.transcript_excerpt)
    return " ".join([record.summary_text, excerpt_text]).strip()


class ConversationArchiveRetriever:
    def retrieve(
        self,
        *,
        archive: Iterable[ConversationArchiveRecord],
        query: str,
        latest_meal_title: str | None,
        pending_question: str | None,
        limit: int = 4,
    ) -> list[ConversationRetrievalHit]:
        query_terms = set(_tokenize(query))
        meal_terms = set(_tokenize(latest_meal_title or ""))
        question_terms = set(_tokenize(pending_question or ""))
        scored: list[ConversationRetrievalHit] = []

        archive_list = list(archive)
        total = len(archive_list)
        for index, record in enumerate(archive_list):
            content_terms = set(_tokenize(_record_text(record)))
            lexical_overlap = query_terms.intersection(content_terms)
            meal_overlap = meal_terms.intersection(content_terms)
            question_overlap = question_terms.intersection(content_terms)

            recency_boost = (index + 1) / max(total, 1)
            score = (
                len(lexical_overlap) * 3.0
                + len(meal_overlap) * 2.0
                + len(question_overlap) * 2.5
                + recency_boost
            )
            if score <= 0:
                continue
            scored.append(
                ConversationRetrievalHit(
                    record_id=record.record_id,
                    summary_text=record.summary_text,
                    local_date=record.local_date,
                    score=round(score, 3),
                    matched_terms=sorted(lexical_overlap.union(meal_overlap).union(question_overlap)),
                    rationale="archive_summary",
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]
