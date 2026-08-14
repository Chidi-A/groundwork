import uuid
from typing import Any
from enum import Enum

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core import storage
from app.models import (
    Document,
    Message,
    Project,
    ProjectCreate,
    ProjectPublic,
    ProjectsPublic,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectStatusFilter(str, Enum):
    active = "active"
    archived = "archived"
    all = "all"


@router.get("/", response_model=ProjectsPublic)
def read_projects(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: ProjectStatusFilter = ProjectStatusFilter.active,
) -> Any:
    """
    Retrieve projects.
    """
    count_statement = select(func.count()).select_from(Project)
    statement = select(Project)

    if not current_user.is_superuser:
        count_statement = count_statement.where(Project.owner_id == current_user.id)
        statement = statement.where(Project.owner_id == current_user.id)

    if status == ProjectStatusFilter.active:
        count_statement = count_statement.where(col(Project.is_archived).is_(False))
        statement = statement.where(col(Project.is_archived).is_(False))
    elif status == ProjectStatusFilter.archived:
        count_statement = count_statement.where(col(Project.is_archived).is_(True))
        statement = statement.where(col(Project.is_archived).is_(True))
    # status == "all" -> no is_archived filter

    count = session.exec(count_statement).one()
    statement = statement.order_by(col(Project.created_at).desc()).offset(skip).limit(limit)
    projects = session.exec(statement).all()

    projects_public = [ProjectPublic.model_validate(project) for project in projects]
    return ProjectsPublic(data=projects_public, count=count)


@router.get("/{id}", response_model=ProjectPublic)
def read_project(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get project by ID.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and (project.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project


@router.post("/", response_model=ProjectPublic)
def create_project(
    *, session: SessionDep, current_user: CurrentUser, project_in: ProjectCreate
) -> Any:
    """
    Create new project.
    """
    project = Project.model_validate(project_in, update={"owner_id": current_user.id})
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.patch("/{id}", response_model=ProjectPublic)
def update_project(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    project_in: ProjectUpdate,
) -> Any:
    """
    Rename a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and (project.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = project_in.model_dump(exclude_unset=True)
    project.sqlmodel_update(update_dict)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{id}")
def delete_project(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a project. Documents, insights, chat messages, and reports
    cascade-delete via the relationships defined on Project; document files
    in object storage are cleaned up here first, since the DB cascade has
    no way to reach into the storage backend on its own.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and (project.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    documents = session.exec(select(Document).where(Document.project_id == id)).all()
    for document in documents:
        if document.storage_key:
            storage.delete_document(document.storage_key)

    session.delete(project)
    session.commit()
    return Message(message="Project deleted successfully")