import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import Document, Insight, Project, Report, TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_owned_project(
    session: Session, current_user: User, project_id: uuid.UUID
) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project


def _assert_owns_project(
    session: Session, current_user: User, project_id: uuid.UUID
) -> None:
    if current_user.is_superuser:
        return
    project = session.get(Project, project_id)
    if project is None or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")


def authorize_document(
    session: Session, current_user: User, document: Document
) -> None:
    if current_user.is_superuser:
        return
    if document.project_id is not None:
        _assert_owns_project(session, current_user, document.project_id)
        return
    if document.uploaded_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")


def get_owned_document(
    session: Session, current_user: User, document_id: uuid.UUID
) -> Document:
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    authorize_document(session, current_user, document)
    return document


def authorize_insight(
    session: Session, current_user: User, insight: Insight
) -> None:
    if current_user.is_superuser:
        return
    if insight.project_id is not None:
        _assert_owns_project(session, current_user, insight.project_id)
        return
    if insight.document_id is not None:
        document = session.get(Document, insight.document_id)
        if document is None:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        authorize_document(session, current_user, document)
        return
    raise HTTPException(status_code=403, detail="Not enough permissions")


def get_owned_insight(
    session: Session, current_user: User, insight_id: uuid.UUID
) -> Insight:
    insight = session.get(Insight, insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    authorize_insight(session, current_user, insight)
    return insight


def get_owned_report(
    session: Session, current_user: User, report_id: uuid.UUID
) -> Report:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    get_owned_project(session, current_user, report.project_id)
    return report


def visible_to_user(current_user: User) -> ColumnElement[bool] | None:
    if current_user.is_superuser:
        return None
    return or_(
        col(Project.owner_id) == current_user.id,
        col(Document.uploaded_by_id) == current_user.id,
    )


def owned_project_by_id(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Project:
    return get_owned_project(session, current_user, id)


def owned_document_by_id(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Document:
    return get_owned_document(session, current_user, id)


def owned_insight_by_id(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Insight:
    return get_owned_insight(session, current_user, id)


def owned_report_by_id(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Report:
    return get_owned_report(session, current_user, id)


OwnedProject = Annotated[Project, Depends(owned_project_by_id)]
OwnedDocument = Annotated[Document, Depends(owned_document_by_id)]
OwnedInsight = Annotated[Insight, Depends(owned_insight_by_id)]
OwnedReport = Annotated[Report, Depends(owned_report_by_id)]
