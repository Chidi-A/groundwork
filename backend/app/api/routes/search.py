import uuid
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, or_
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Document,
    Insight,
    InsightPublic,
    PassagePublic,
    Project,
    SearchResults,
)

router = APIRouter(prefix="/search", tags=["search"])



@router.get("/", response_model=SearchResults)
def search(
    session: SessionDep,
    current_user: CurrentUser,
    q: str = Query(min_length=1),
    project_id: uuid.UUID | None = None,
    limit: int = 20,
) -> Any:
    """
    Keyword search across insight objects (primary) and documents (as a
    placeholder for raw passages). Uses Postgres full-text search
    (tsvector/ts_rank), not embeddings.

    Semantic search is intentionally not implemented here — it's blocked
    on the Phase 4 extraction pipeline and embedding stack decision
    (which model, chunk-level vs insight-level, pgvector index type),
    not on anything in this file. This endpoint returns ranked keyword
    matches only; the response shape (insights first, passages second)
    is designed to stay stable once semantic ranking replaces ts_rank
    underneath it.
    """
    tsquery = func.websearch_to_tsquery("english", q)

    insight_statement = (
        select(Insight)
        .outerjoin(Project, col(Insight.project_id) == col(Project.id))
        .outerjoin(Document, col(Insight.document_id) == col(Document.id))
        .where(col(Insight.search_vector).op("@@")(tsquery))
    )
    if not current_user.is_superuser:
        insight_statement = insight_statement.where(
            or_(
                col(Project.owner_id) == current_user.id,
                col(Document.uploaded_by_id) == current_user.id,
            )
        )
    if project_id is not None:
        insight_statement = insight_statement.where(Insight.project_id == project_id)
    insight_statement = insight_statement.order_by(
        func.ts_rank(col(Insight.search_vector), tsquery).desc()
    ).limit(limit)
    insights = session.exec(insight_statement).all()

    document_statement = (
        select(Document)
        .outerjoin(Project, col(Document.project_id) == col(Project.id))
        .where(col(Document.search_vector).op("@@")(tsquery))
    )
    if not current_user.is_superuser:
        document_statement = document_statement.where(
            or_(
                col(Project.owner_id) == current_user.id,
                col(Document.uploaded_by_id) == current_user.id,
            )
        )
    if project_id is not None:
        document_statement = document_statement.where(Document.project_id == project_id)
    document_statement = document_statement.order_by(
        func.ts_rank(col(Document.search_vector), tsquery).desc()
    ).limit(limit)
    documents = session.exec(document_statement).all()

    return SearchResults(
        insights=[InsightPublic.model_validate(i) for i in insights],
        passages=[
            PassagePublic(document_id=d.id, filename=d.filename, snippet=d.filename)
            for d in documents
        ],
    )
