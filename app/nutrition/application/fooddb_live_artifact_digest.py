from __future__ import annotations

import hashlib
import json
import re
from typing import Any


ARTIFACT_DIGEST_ALGORITHM = "sha256"
ARTIFACT_DIGEST_SCOPE = "semantic_artifact_without_generated_at_utc"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fooddb_semantic_artifact_digest(artifact: dict[str, Any]) -> str:
    payload = {key: value for key, value in artifact.items() if key != "generated_at_utc"}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_fooddb_artifact_digest(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if _SHA256_RE.match(text) else "invalid_artifact_digest"


def verify_fooddb_artifact_digest(
    *,
    digest: str,
    artifact: dict[str, Any] | None,
) -> bool:
    if not isinstance(artifact, dict) or not _SHA256_RE.match(digest):
        return False
    return fooddb_semantic_artifact_digest(artifact) == digest


__all__ = [
    "ARTIFACT_DIGEST_ALGORITHM",
    "ARTIFACT_DIGEST_SCOPE",
    "fooddb_semantic_artifact_digest",
    "safe_fooddb_artifact_digest",
    "verify_fooddb_artifact_digest",
]
