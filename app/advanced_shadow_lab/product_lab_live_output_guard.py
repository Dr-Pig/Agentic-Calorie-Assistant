from __future__ import annotations

from typing import Any, Mapping


DELIVERY_CLAIMS = (
    "was delivered",
    "were delivered",
    "has been delivered",
    "sent to the user",
    "notified the user",
    "push notification sent",
)
MUTATION_CLAIMS = (
    "was committed",
    "were committed",
    "has been committed",
    "saved to product state",
    "applied to product state",
    "mutated canonical",
)


def product_lab_live_output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if output.get("claim_scope") != "diagnostic_only":
        blockers.append("model_output.claim_scope_not_diagnostic")
    for key, blocker in (
        ("action_request", "model_output.action_request_not_allowed"),
        ("delivery_request", "model_output.delivery_request_not_allowed"),
        ("mutation_request", "model_output.mutation_request_not_allowed"),
    ):
        if output.get(key) is True:
            blockers.append(blocker)
    text = _text(output)
    if _contains_claim(text, DELIVERY_CLAIMS):
        blockers.append("model_output.delivery_language_present")
    if _contains_claim(text, MUTATION_CLAIMS):
        blockers.append("model_output.mutation_language_present")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def _text(output: Mapping[str, Any]) -> str:
    return f"{output.get('diagnostic_notes') or ''} {output.get('risk_notes') or ''}".lower()


def _contains_claim(text: str, phrases: tuple[str, ...]) -> bool:
    for phrase in phrases:
        index = text.find(phrase)
        if index < 0:
            continue
        window = text[max(0, index - 36) : index + len(phrase) + 12]
        if not _is_negated(window):
            return True
    return False


def _is_negated(text: str) -> bool:
    negations = (
        "not sent",
        "not delivered",
        "no delivery",
        "no mutation",
        "not committed",
        "not saved",
        "without saving",
        "without committing",
    )
    return any(phrase in text for phrase in negations)


__all__ = ["product_lab_live_output_guard"]
