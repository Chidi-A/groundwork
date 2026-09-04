import json
import uuid
from collections.abc import AsyncIterable
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.llm import get_client
from app.models import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    Insight,
    Project,
    ReviewStatus,
)

router = APIRouter(prefix="/chat", tags=["chat"])

CITE_INSIGHTS_TOOL: dict[str, Any] = {
    "name": "cite_insights",
    "description": (
        "Report which insight IDs from the provided context were used to "
        "support claims in your answer. Call this once after finishing "
        "your written answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "insight_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Insight IDs cited in the answer, in order of first use.",
            }
        },
        "required": ["insight_ids"],
    },
}


def _get_owned_project(
    session: SessionDep, current_user: CurrentUser, project_id: uuid.UUID
) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project



def _build_insight_context(
    session: SessionDep, project_id: uuid.UUID, question: str
) -> list[Insight]:
    base_filters = (
        Insight.project_id == project_id,
        Insight.review_status != ReviewStatus.rejected,
    )
    total = session.exec(
        select(func.count()).select_from(Insight).where(*base_filters)
    ).one()
    if total <= settings.CHAT_CONTEXT_MAX_INSIGHTS:
        statement = select(Insight).where(*base_filters).order_by(col(Insight.created_at))
        return list(session.exec(statement).all())
    tsquery = func.websearch_to_tsquery("english", question)
    statement = (
        select(Insight)
        .where(*base_filters, col(Insight.search_vector).op("@@")(tsquery))
        .order_by(func.ts_rank(col(Insight.search_vector), tsquery).desc())
        .limit(settings.CHAT_CONTEXT_MAX_INSIGHTS)
    )
    return list(session.exec(statement).all())


def _format_insight(insight: Insight) -> str:
    parts = [
        f"id={insight.id}",
        f"type={insight.type.value}",
        f"sentiment={insight.sentiment.value}",
        f"theme={insight.theme or 'none'}",
        f"text={insight.text}",
    ]
    if insight.source_quote:
        parts.append(f'quote="{insight.source_quote}"')
    if insight.source_location:
        parts.append(f"location={insight.source_location}")
    return " | ".join(parts)


def _build_system_prompt(insights: list[Insight]) -> str:
    insight_block = (
        "\n".join(_format_insight(i) for i in insights)
        if insights
        else "(no insights extracted for this project yet)"
    )
    return (
        "You are a research assistant answering questions about a single research "
        "project, using only the structured insight objects listed below. Each "
        "insight has a unique id.\n\n"
        "Rules:\n"
        "- Answer only from the insights provided. Do not use outside knowledge.\n"
        "- Write your answer as plain prose. Do not include inline citation markers "
        "or insight IDs in the answer text.\n"
        "- After you finish the answer, call the cite_insights tool exactly once "
        "with every insight id your answer relied on.\n"
        "- If the insights don't contain enough information to answer, say so plainly "
        "rather than guessing, then call cite_insights with an empty list.\n\n"
        f"Insights:\n{insight_block}"
    )


def _extract_cited_ids(final_message: Any, valid_ids: set[str]) -> list[str]:
    cited_ids: list[str] = []
    for block in final_message.content:
        if block.type != "tool_use" or block.name != "cite_insights":
            continue
        tool_input = block.input
        if isinstance(tool_input, str):
            tool_input = json.loads(tool_input)
        raw_ids = tool_input.get("insight_ids", [])
        if not isinstance(raw_ids, list):
            continue
        cited_ids.extend(
            insight_id for insight_id in raw_ids if insight_id in valid_ids
        )
    return list(dict.fromkeys(cited_ids))


@router.post("/", response_class=EventSourceResponse)
async def chat(
    session: SessionDep,
    current_user: CurrentUser,
    body: ChatRequest,
) -> AsyncIterable[ServerSentEvent]:
    """
    Stream an answer to a question about a project, grounded in that
    project's structured insight objects (not raw document text). Emits
    `token` events with text deltas, then one final `done` event with the
    full answer and schema-validated insight IDs from the cite_insights tool.
    This is a POST endpoint returning SSE, so the frontend must consume it
    via fetch()+ReadableStream, not the native EventSource API (which only
    supports GET).
    """
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500, detail="ANTHROPIC_API_KEY is not configured."
        )

    project = _get_owned_project(session, current_user, body.project_id)

    session.add(ChatMessage(project_id=project.id, role=ChatRole.user, content=body.message))
    session.commit()

    insights = _build_insight_context(session, project.id, body.message)
    system_prompt = _build_system_prompt(insights)
    valid_ids = {str(i.id) for i in insights}

    history = session.exec(
        select(ChatMessage)
        .where(ChatMessage.project_id == project.id)
        .order_by(col(ChatMessage.created_at))
    ).all()
    messages = [{"role": m.role.value, "content": m.content} for m in history]

    full_text = ""
    async with get_client().messages.stream(
        model=settings.ANTHROPIC_CHAT_MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
        tools=[CITE_INSIGHTS_TOOL],
        tool_choice={"type": "auto"},
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
            yield ServerSentEvent(data=text, event="token")

        final_message = await stream.get_final_message()

    cited_ids = _extract_cited_ids(final_message, valid_ids)

    session.add(
        ChatMessage(
            project_id=project.id,
            role=ChatRole.assistant,
            content=full_text,
            cited_insight_ids=cited_ids,
        )
    )
    session.commit()

    yield ServerSentEvent(
        data={"content": full_text, "cited_insight_ids": cited_ids}, event="done"
    )
