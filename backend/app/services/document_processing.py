import uuid

from sqlmodel import Session

from app.core.db import engine
from app.models import Document, ProcessingStatus

def run_document_processing_pipeline(document_id: uuid.UUID) -> None:
    """
    Placeholder for the Phase 4 extract -> chunk -> classify -> theme pipeline.
    Runs as a FastAPI BackgroundTask, so it opens its own session rather than
    reusing the request-scoped one (which is already closed by the time this runs).
    """
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if document is None:
            return
        document.processing_status = ProcessingStatus.processing
        session.add(document)
        session.commit()
        try:
            # TODO(Phase 4): parse file -> chunk -> extract Insight objects ->
            # theme cluster -> embed. For now, mark complete as a no-op.
            document.processing_status = ProcessingStatus.completed
        except Exception as exc:
            document.processing_status = ProcessingStatus.failed
            document.error_message = str(exc)
        session.add(document)
        session.commit()
