from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm import get_sync_client
from app.models import InsightType, Sentiment
from app.services.chunking import Chunk

EXTRACT_INSIGHTS_TOOL: dict[str, Any] = {
    "name": "extract_insights",
    "description": "Extract zero or more research insights from this transcript chunk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [t.value for t in InsightType],
                        },
                        "text": {"type": "string"},
                        "source_quote": {"type": ["string", "null"]},
                        "sentiment": {
                            "type": "string",
                            "enum": [s.value for s in Sentiment],
                        },
                        "theme": {"type": ["string", "null"]},
                        "participant_reference_code": {"type": ["string", "null"]},
                        "type_confidence": {"type": "number"},
                        "alternate_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [t.value for t in InsightType],
                            },
                        },
                    },
                    "required": ["type", "text", "sentiment", "type_confidence"],
                },
            }
        },
        "required": ["insights"],
    },
}

EXTRACT_PARTICIPANTS_TOOL: dict[str, Any] = {
    "name": "extract_participants",
    "description": "List distinct interview participants mentioned in this document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "participants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "reference_code": {
                            "type": "string",
                            "description": "Short code such as P12.",
                        },
                        "age_range": {"type": ["string", "null"]},
                        "segment": {"type": ["string", "null"]},
                    },
                    "required": ["name", "reference_code"],
                },
            }
        },
        "required": ["participants"],
    },
}


class ExtractedParticipant(BaseModel):
    name: str
    reference_code: str
    age_range: str | None = None
    segment: str | None = None


class ExtractedInsight(BaseModel):
    type: InsightType
    text: str
    source_quote: str | None = None
    sentiment: Sentiment = Sentiment.neutral
    theme: str | None = None
    participant_reference_code: str | None = None
    type_confidence: float | None = None
    alternate_types: list[InsightType] = Field(default_factory=list)


def _tool_input(message: Any) -> dict[str, Any]:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise RuntimeError("Extraction model did not call the required tool")


def extract_participants(chunks: list[Chunk]) -> list[ExtractedParticipant]:
    preview = "\n\n".join(chunk.text for chunk in chunks[:3])
    if not preview.strip():
        return []
    client = get_sync_client()
    message = client.messages.create(
        model=settings.ANTHROPIC_EXTRACTION_MODEL,
        max_tokens=2048,
        tools=[EXTRACT_PARTICIPANTS_TOOL],
        tool_choice={"type": "tool", "name": "extract_participants"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Identify distinct research participants in this transcript "
                    "excerpt. Use codes like P1, P12 when present. Skip the "
                    "interviewer unless they are also a research subject.\n\n"
                    f"{preview}"
                ),
            }
        ],
    )
    raw = _tool_input(message).get("participants") or []
    return [ExtractedParticipant.model_validate(item) for item in raw]


def extract_insights_from_chunk(
    chunk: Chunk,
    *,
    participant_codes: list[str],
    existing_themes: list[str],
) -> list[ExtractedInsight]:
    codes = ", ".join(participant_codes) if participant_codes else "(none yet)"
    if existing_themes:
        theme_block = (
            "Prefer one of these existing project themes when it fits; "
            "only invent a new label if none apply:\n- "
            + "\n- ".join(existing_themes)
        )
    else:
        theme_block = (
            "No project theme list yet. Propose a short theme label if one is clear."
        )
    client = get_sync_client()
    message = client.messages.create(
        model=settings.ANTHROPIC_EXTRACTION_MODEL,
        max_tokens=4096,
        tools=[EXTRACT_INSIGHTS_TOOL],
        tool_choice={"type": "tool", "name": "extract_insights"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract research insights from this chunk. "
                    "source_quote must be a verbatim substring of the chunk. "
                    "participant_reference_code must be one of: "
                    f"{codes}, or null.\n"
                    f"{theme_block}\n"
                    f"Location: {chunk.source_location}\n\n"
                    f"{chunk.text}"
                ),
            }
        ],
    )
    raw = _tool_input(message).get("insights") or []
    return [ExtractedInsight.model_validate(item) for item in raw]