import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, OwnedInsight, SessionDep, visible_to_user
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
    are omitted unless review_status is set explicitly or include_rejected
    is set.

    needs_review is a permanent extraction-time flag and is not cleared by
    edits/confirms/rejects; combine with review_status=unreviewed to get the
    actionable "still needs a human look" queue rather than the full history.
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
    ownership_filter = visible_to_user(current_user)
    if ownership_filter is not None:
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
def read_insight(insight: OwnedInsight) -> Any:
    return insight


@router.patch("/{id}/review", response_model=InsightPublic)
def review_insight(
    *,
    session: SessionDep,
    insight: OwnedInsight,
    body: InsightReview,
) -> Any:
    """
    Confirm or reject an insight. Rejected rows are kept (soft-delete)
    and filtered out of the default list.
    """
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
    insight: OwnedInsight,
    body: InsightUpdate,
) -> Any:
    """
    Correct an insight's classification (type, theme, sentiment, quote,
    participant, etc.). Any field change marks the insight as edited and
    clears a prior rejection, since a human just corrected it.
    """
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
    # NOTE: any edit reactivates a rejected insight — intentional for v1,
    # revisit if bulk-edit or an AI re-classification pass is ever added.
    insight.review_status = ReviewStatus.edited
    insight.rejection_reason = None

    session.add(insight)
    session.commit()
    session.refresh(insight)
    return insight