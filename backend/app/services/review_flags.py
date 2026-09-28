from __future__ import annotations

import re

from app.core.config import settings
from app.models import InsightType

_WHITESPACE = re.compile(r"\s+")


def normalize_for_quote_match(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().casefold()


def quote_in_chunk(quote: str, chunk_text: str) -> bool:
    needle = normalize_for_quote_match(quote)
    haystack = normalize_for_quote_match(chunk_text)
    return bool(needle) and needle in haystack


def canonicalize_theme(proposed: str | None, existing_labels: list[str]) -> str | None:
    if proposed is None:
        return None
    cleaned = " ".join(proposed.split())
    if not cleaned:
        return None
    mapping = {label.casefold(): label for label in existing_labels if label}
    return mapping.get(cleaned.casefold(), cleaned)


def compute_needs_review(
    *,
    source_quote: str | None,
    chunk_text: str,
    participant_id: object | None,
    type_confidence: float | None,
    alternate_types: list[InsightType],
) -> bool:
    if not (source_quote or "").strip():
        return True
    if not quote_in_chunk(source_quote or "", chunk_text):
        return True
    if participant_id is None:
        return True
    if (
        type_confidence is not None
        and type_confidence < settings.TYPE_CONFIDENCE_THRESHOLD
    ):
        return True
    if alternate_types:
        return True
    return False