from typing import Any

from fastapi import APIRouter
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, OwnedReport, SessionDep, get_owned_project
from app.models import (
    Document,
    Insight,
    Report,
    ReportCreate,
    ReportPublic,
    ReportStatus,
    ReviewStatus,
)
from app.services.report_generation import _reviewed_count, build_report_markdown

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/", response_model=ReportPublic)
def generate_report(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: ReportCreate,
) -> Any:
    """
    Generate an executive-summary Markdown report from a project's structured
    insight objects. Deterministic assembly — no LLM call.
    """
    project = get_owned_project(session, current_user, body.project_id)
    insights = list(
        session.exec(
            select(Insight)
            .where(
                Insight.project_id == project.id,
                Insight.review_status != ReviewStatus.rejected,
            )
            .order_by(col(Insight.created_at))
        ).all()
    )
    document_count = session.exec(
        select(func.count())
        .select_from(Document)
        .where(Document.project_id == project.id)
    ).one()
    report = Report(
        project_id=project.id,
        status=ReportStatus.generating,
        insight_count_at_generation=len(insights),
        reviewed_count_at_generation=_reviewed_count(insights),
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    try:
        report.markdown_content = build_report_markdown(
            project, insights, document_count
        )
        report.status = ReportStatus.ready
    except Exception:
        report.status = ReportStatus.failed
        report.markdown_content = None
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


@router.get("/{id}", response_model=ReportPublic)
def read_report(report: OwnedReport) -> Any:
    """Retrieve a generated report by ID, including its Markdown content when ready."""
    return report