import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import or_
from sqlmodel import col, func, select


from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Document,
    Insight,
    InsightPublic,
    InsightReview,
    InsightReviewAction,
    InsightType,
    InsightsPublic,
    Participant,
    InsightUpdate,
    Project,
    ReviewStatus,
    Sentiment,
)

router = APIRouter(prefix="/insights", tags=["insights"])

def _authorize_insight(
    session: SessionDep, current_user: CurrentUser, insight: Insight
) -> None:
    if current_user.is_superuser:
        return
    if insight.project_id is not None:
        project = session.get(Project, insight.project_id)
        if project is None or project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return
    if insight.document_id is not None:
        document = session.get(Document, insight.document_id)
        if document is None:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        if document.project_id is not None:
            project = session.get(Project, document.project_id)
            if project is None or project.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not enough permissions")
        elif document.uploaded_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return
    raise HTTPException(status_code=403, detail="Not enough permissions")


@router.get("/", response_model=InsightsPublic)
def read_insights(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID | None = None,
    type: InsightType | None = None,
    theme: str | None = None,
    sentiment: Sentiment | None = None,
    participant_id: uuid.UUID | None = None,
    review_status: ReviewStatus | None = None,
    include_rejected: bool = False,
    needs_review: bool | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List insights, optionally scoped to a project and filtered by type,
    theme, sentiment, participant, or review status. Rejected insights
    are omitted unless review_status is set explicitly.
    """
    statement = (
        select(Insight)
        .outerjoin(Project, col(Insight.project_id) == col(Project.id))
        .outerjoin(Document, col(Insight.document_id) == col(Document.id))
    )
    count_statement = (
        select(func.count())
        .select_from(Insight)
        .outerjoin(Project, col(Insight.project_id) == col(Project.id))
        .outerjoin(Document, col(Insight.document_id) == col(Document.id))
    )
    if not current_user.is_superuser:
        ownership_filter = or_(
            col(Project.owner_id) == current_user.id,
            col(Document.uploaded_by_id) == current_user.id,
        )
        statement = statement.where(ownership_filter)
        count_statement = count_statement.where(ownership_filter)
    if project_id is not None:
        statement = statement.where(Insight.project_id == project_id)
        count_statement = count_statement.where(Insight.project_id == project_id)
    if type is not None:
        statement = statement.where(Insight.type == type)
        count_statement = count_statement.where(Insight.type == type)
    if theme is not None:
        statement = statement.where(Insight.theme == theme)
        count_statement = count_statement.where(Insight.theme == theme)
    if sentiment is not None:
        statement = statement.where(Insight.sentiment == sentiment)
        count_statement = count_statement.where(Insight.sentiment == sentiment)
    if participant_id is not None:
        statement = statement.where(Insight.participant_id == participant_id)
        count_statement = count_statement.where(Insight.participant_id == participant_id)
    if review_status is not None:
        statement = statement.where(Insight.review_status == review_status)
        count_statement = count_statement.where(Insight.review_status == review_status)
    elif not include_rejected:
        statement = statement.where(Insight.review_status != ReviewStatus.rejected)
        count_statement = count_statement.where(
            Insight.review_status != ReviewStatus.rejected
        )
    if needs_review is not None:
        statement = statement.where(Insight.needs_review == needs_review)
        count_statement = count_statement.where(Insight.needs_review == needs_review)  
    count = session.exec(count_statement).one()
    statement = statement.order_by(col(Insight.created_at).desc()).offset(skip).limit(limit)
    insights = session.exec(statement).all()
    return InsightsPublic(
        data=[InsightPublic.model_validate(i) for i in insights],
        count=count,
    )


@router.get("/{id}", response_model=InsightPublic)
def read_insight(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    insight = session.get(Insight, id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    _authorize_insight(session, current_user, insight)
    return insight


@router.patch("/{id}/review", response_model=InsightPublic)
def review_insight(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    body: InsightReview,
) -> Any:
    """
    Confirm or reject an insight. Rejected rows are kept (soft-delete)
    and filtered out of the default list.
    """
    insight = session.get(Insight, id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    _authorize_insight(session, current_user, insight)
    if body.action == InsightReviewAction.confirm:
        insight.review_status = ReviewStatus.confirmed
        insight.rejection_reason = None
    else:
        if body.rejection_reason is None:
            raise HTTPException(
                status_code=400,
                detail="rejection_reason is required when rejecting an insight.",
            )
        insight.review_status = ReviewStatus.rejected
        insight.rejection_reason = body.rejection_reason
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return insight


@router.patch("/{id}", response_model=InsightPublic)
def update_insight(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    body: InsightUpdate,
) -> Any:
    """
    Correct an insight's classification (type, theme, sentiment, quote,
    participant, etc.). Any field change marks the insight as edited and
    clears a prior rejection, since a human just corrected it.
    """
    insight = session.get(Insight, id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    _authorize_insight(session, current_user, insight)

    update_dict = body.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    if "participant_id" in update_dict and update_dict["participant_id"] is not None:
        participant = session.get(Participant, update_dict["participant_id"])
        if participant is None or participant.document_id != insight.document_id:
            raise HTTPException(
                status_code=400,
                detail="participant_id must belong to the insight's document.",
            )

    insight.sqlmodel_update(update_dict)
    insight.review_status = ReviewStatus.edited
    insight.rejection_reason = None

    session.add(insight)
    session.commit()
    session.refresh(insight)
    return insight