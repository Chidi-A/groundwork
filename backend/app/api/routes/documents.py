import io
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, OwnedDocument, SessionDep, get_owned_project, visible_to_user
from app.core import storage
from app.core.config import settings
from app.models import (
    Document,
    DocumentFormat,
    DocumentOrganize,
    DocumentPublic,
    DocumentsPublic,
    Insight,
    Message,
    ProcessingStatus,
    Project,
)
from app.services.document_processing import run_document_processing_pipeline

router = APIRouter(prefix="/documents", tags=["documents"])
EXTENSION_TO_FORMAT: dict[str, DocumentFormat] = {
    "pdf": DocumentFormat.pdf,
    "docx": DocumentFormat.docx,
    "txt": DocumentFormat.txt,
}
MAX_UPLOAD_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/", response_model=DocumentPublic)
def upload_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    project_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
) -> Any:
    """
    Upload a document (PDF/DOCX/TXT). If project_id is omitted, the document
    lands in the current user's inbox until organized into a project.
    """

    if project_id is not None:
        get_owned_project(session, current_user, project_id)
    extension = (file.filename or "").rsplit(".", 1)[-1].lower()
    doc_format = EXTENSION_TO_FORMAT.get(extension)
    if doc_format is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Allowed: pdf, docx, txt.",
        )

    document = Document(
        project_id=project_id,
        uploaded_by_id=current_user.id,
        filename=file.filename or "untitled",
        format=doc_format,
        processing_status=ProcessingStatus.pending,
    )

    storage_key = f"users/{current_user.id}/{document.id}/{document.filename}"
    chunks: list[bytes] = []
    size = 0
    while chunk := file.file.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.",
            )
        chunks.append(chunk)

    storage.upload_document(storage_key, io.BytesIO(b"".join(chunks)), content_type=file.content_type)

    document.storage_key = storage_key
    document.file_size = size

    session.add(document)
    session.commit()
    session.refresh(document)

    background_tasks.add_task(run_document_processing_pipeline, document.id)
    return document


@router.get("/", response_model=DocumentsPublic)
def read_documents(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID | None = None,
    status: ProcessingStatus | None = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List documents, optionally filtered by project or processing status, or
    restricted to the current user's unorganized inbox documents.
    """
    statement = select(Document).outerjoin(Project, col(Document.project_id) == col(Project.id))
    count_statement = (
        select(func.count())
        .select_from(Document)
        .outerjoin(Project, col(Document.project_id) == col(Project.id))
    )

    ownership_filter = visible_to_user(current_user)
    if ownership_filter is not None:
        statement = statement.where(ownership_filter)
        count_statement = count_statement.where(ownership_filter)
    if project_id is not None:
        statement = statement.where(Document.project_id == project_id)
        count_statement = count_statement.where(Document.project_id == project_id)
    if status is not None:
        statement = statement.where(Document.processing_status == status)
        count_statement = count_statement.where(Document.processing_status == status)
    if unassigned_only:
        statement = statement.where(col(Document.project_id).is_(None))
        count_statement = count_statement.where(col(Document.project_id).is_(None))

    count = session.exec(count_statement).one()
    statement = statement.order_by(col(Document.uploaded_at).desc()).offset(skip).limit(limit)
    documents = session.exec(statement).all()

    documents_public = [DocumentPublic.model_validate(d) for d in documents]
    return DocumentsPublic(data=documents_public, count=count)


@router.get("/{id}", response_model=DocumentPublic)
def read_document(document: OwnedDocument) -> Any:
    """
    Get a document by ID (used to poll a single upload's progress).
    """
    return document


@router.get("/{id}/download-url")
def get_document_download_url(document: OwnedDocument) -> dict[str, str]:
    """
    Return a short-lived presigned URL for downloading the original file
    directly from object storage (never proxied through this API).
    """
    if not document.storage_key:
        raise HTTPException(status_code=409, detail="Document has no stored file")

    url = storage.generate_presigned_download_url(document.storage_key, filename=document.filename)
    return {"url": url}


@router.patch("/{id}/organize", response_model=DocumentPublic)
def organize_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    document: OwnedDocument,
    body: DocumentOrganize,
) -> Any:
    """
    Attach a document to a project, retroactively stamping project_id onto
    every insight already extracted from it while it sat in the inbox.
    """
    get_owned_project(session, current_user, body.project_id)

    if document.project_id is not None and document.project_id != body.project_id:
        raise HTTPException(
            status_code=409,
            detail="Document is already in a project",
        )

    document.project_id = body.project_id
    session.add(document)

    insights = session.exec(
        select(Insight).where(Insight.document_id == document.id)
    ).all()
    for insight in insights:
        insight.project_id = body.project_id
        session.add(insight)

    session.commit()
    session.refresh(document)
    return document


@router.delete("/{id}")
def delete_document(session: SessionDep, document: OwnedDocument) -> Message:
    """
    Delete a document, its stored file, and every insight extracted from it.
    Participants cascade-delete with the document; insights cascade via
    Insight.document_id.
    """
    if document.storage_key:
        storage.delete_document(document.storage_key)

    session.delete(document)
    session.commit()
    return Message(message="Document deleted successfully")