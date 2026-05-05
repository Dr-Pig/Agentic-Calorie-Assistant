from __future__ import annotations

from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from app.nutrition.application.fooddb_retrieval_policy import IndexedFoodRecord


class SQLiteFtsFoodEvidenceIndex:
    """SQLite FTS adapter for FoodEvidenceIndexPort.

    The adapter owns SQLite/FTS details and returns IndexedFoodRecord objects so
    retrieval policy remains backend-agnostic.
    """

    MAX_SEARCH_LIMIT = 100

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    @classmethod
    def rebuild_from_records(
        cls,
        db_path: Path,
        records: Iterable[IndexedFoodRecord],
    ) -> "SQLiteFtsFoodEvidenceIndex":
        index = cls(Path(db_path))
        index.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(index.db_path)) as connection:
            with connection:
                _create_schema(connection)
                connection.execute("DELETE FROM food_evidence_fts")
                connection.execute("DELETE FROM food_evidence_records")
                for rowid, record in enumerate(records, start=1):
                    payload = _record_to_payload(record)
                    connection.execute(
                        """
                        INSERT INTO food_evidence_records (
                            id, anchor_id, canonical_name, aliases_text, runtime_role,
                            runtime_truth_allowed, payload_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            rowid,
                            record.anchor_id,
                            record.canonical_name,
                            " ".join(record.aliases),
                            record.runtime_role,
                            1 if record.runtime_truth_allowed else 0,
                            json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO food_evidence_fts (
                            rowid, anchor_id, canonical_name, aliases_text
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (rowid, record.anchor_id, record.canonical_name, " ".join(record.aliases)),
                    )
                connection.execute("PRAGMA optimize")
        return index

    def load_records(self) -> tuple[IndexedFoodRecord, ...]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                """
                SELECT payload_json
                FROM food_evidence_records
                ORDER BY anchor_id
                """
            )
            rows = cursor.fetchall()
            cursor.close()
        return tuple(_record_from_payload(json.loads(row[0])) for row in rows)

    def search_records(self, query: str, *, limit: int = 20) -> tuple[IndexedFoodRecord, ...]:
        match_query = _fts_match_query(query)
        if not match_query:
            return ()
        bounded_limit = _bounded_limit(limit, maximum=self.MAX_SEARCH_LIMIT)
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                """
                SELECT records.payload_json
                FROM food_evidence_fts AS fts
                JOIN food_evidence_records AS records ON records.id = fts.rowid
                WHERE food_evidence_fts MATCH ?
                ORDER BY bm25(food_evidence_fts)
                LIMIT ?
                """,
                (match_query, bounded_limit),
            )
            rows = cursor.fetchall()
            cursor.close()
        return tuple(_record_from_payload(json.loads(row[0])) for row in rows)

    def describe_index(self) -> dict[str, Any]:
        records = self.load_records()
        runtime_records = [
            record for record in records if record.runtime_role == "common_serving_anchor"
        ]
        semantic_records = [
            record for record in records if record.runtime_role == "basket_family_semantic_only"
        ]
        return {
            "adapter_type": "sqlite_fts_food_evidence_index",
            "db_path": str(self.db_path),
            "record_contract": "IndexedFoodRecord",
            "runtime_truth_boundary": "adapter_returns_indexed_records_not_truth_decisions",
            "runtime_record_count": len(runtime_records),
            "semantic_record_count": len(semantic_records),
            "fts_table": "food_evidence_fts",
            "index_mode": "rebuilt_content_copy",
            "future_backends": ["supabase"],
            "forbidden_policy_dependencies": [
                "supabase_client",
                "webshell",
                "manager_context_packet",
            ],
        }


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS food_evidence_records (
            id INTEGER PRIMARY KEY,
            anchor_id TEXT NOT NULL UNIQUE,
            canonical_name TEXT NOT NULL,
            aliases_text TEXT NOT NULL,
            runtime_role TEXT NOT NULL,
            runtime_truth_allowed INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.execute("DROP TABLE IF EXISTS food_evidence_fts")
    connection.execute(
        """
        CREATE VIRTUAL TABLE food_evidence_fts USING fts5(
            anchor_id,
            canonical_name,
            aliases_text,
            tokenize='unicode61'
        )
        """
    )


def _record_to_payload(record: IndexedFoodRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["aliases"] = list(record.aliases)
    payload["kcal_range"] = list(record.kcal_range) if record.kcal_range else None
    payload["followup_hints"] = list(record.followup_hints)
    payload["major_modifiers"] = list(record.major_modifiers)
    return payload


def _record_from_payload(payload: dict[str, Any]) -> IndexedFoodRecord:
    kcal_range = payload.get("kcal_range")
    return IndexedFoodRecord(
        anchor_id=str(payload.get("anchor_id") or ""),
        canonical_name=str(payload.get("canonical_name") or ""),
        aliases=tuple(str(alias) for alias in payload.get("aliases") or []),
        dish_type=str(payload.get("dish_type") or ""),
        runtime_truth_allowed=payload.get("runtime_truth_allowed") is True,
        runtime_role=str(payload.get("runtime_role") or ""),
        kcal_point=payload.get("kcal_point"),
        kcal_range=tuple(kcal_range) if kcal_range else None,
        serving_basis=str(payload.get("serving_basis") or ""),
        portion_basis=payload.get("portion_basis"),
        followup_hints=tuple(str(hint) for hint in payload.get("followup_hints") or []),
        major_modifiers=tuple(
            modifier for modifier in payload.get("major_modifiers") or [] if isinstance(modifier, dict)
        ),
        runtime_usage_boundary=str(payload.get("runtime_usage_boundary") or ""),
        source_provenance=dict(payload.get("source_provenance") or {}),
        approval_metadata=dict(payload.get("approval_metadata") or {}),
    )


def _fts_match_query(query: str) -> str:
    terms = []
    for raw_term in str(query or "").split():
        term = "".join(ch for ch in raw_term if ch.isalnum() or ch in {"_", "-"}).strip("-_")
        if term:
            terms.append(f'"{term}"')
    return " OR ".join(terms)


def _bounded_limit(limit: int, *, maximum: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return 1
    return min(max(value, 1), maximum)


__all__ = ["SQLiteFtsFoodEvidenceIndex"]
