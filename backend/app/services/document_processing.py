from __future__ import annotations

import uuid

from sqlmodel import Session, col, func, select

from app.core import storage
from app.core.config import settings
from app.core.db import engine
from app.core.embeddings import embed_texts, insight_embedding_input
from app.models import (
    Document,
    Insight,
    Participant,
    ProcessingStatus,
    ReviewStatus,
)
from app.services.chunking import chunk_units
from app.services.extraction import extract_insights_from_chunk, extract_participants
from app.services.parsing import ParseError, parse_document
from app.services.review_flags import canonicalize_theme, compute_needs_review


def run_document_processing_pipeline(document_id: uuid.UUID) -> None:
    """
    Parse, chunk, extract, flag, embed, persist. Opens its own session because
    FastAPI BackgroundTasks run after the request session is closed.
    """
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if document is None:
            return
        document.processing_status = ProcessingStatus.processing
        document.error_message = None
        session.add(document)
        session.commit()
        session.refresh(document)
        try:
            _process_document(session, document)
            document.processing_status = ProcessingStatus.completed
        except Exception as exc:
            document.processing_status = ProcessingStatus.failed
            document.error_message = str(exc)
        session.add(document)
        session.commit()


def _process_document(session: Session, document: Document) -> None:
    if not document.storage_key:
        raise ParseError("Document has no stored file")
    data = storage.download_document_bytes(document.storage_key)
    units = parse_document(data, document.format)
    chunks = chunk_units(
        units,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    if not chunks:
        raise ParseError("Document produced no text chunks")

    _reset_extracted_rows(session, document.id)

    extracted_participants = extract_participants(chunks)
    participants_by_code: dict[str, Participant] = {}
    for item in extracted_participants:
        code = item.reference_code.strip()
        if not code or code in participants_by_code:
            continue
        participant = Participant(
            document_id=document.id,
            name=item.name.strip() or code,
            reference_code=code,
            age_range=item.age_range,
            segment=item.segment,
        )
        session.add(participant)
        participants_by_code[code.casefold()] = participant
    session.flush()

    existing_themes = _project_theme_labels(session, document.project_id)
    pending: list[Insight] = []
    embed_inputs: list[str] = []

    for chunk in chunks:
        extracted = extract_insights_from_chunk(
            chunk,
            participant_codes=[p.reference_code for p in participants_by_code.values()],
            existing_themes=existing_themes,
        )
        for item in extracted:
            text = item.text.strip()
            if not text:
                continue
            quote = (item.source_quote or "").strip() or None
            code = (item.participant_reference_code or "").strip()
            participant = participants_by_code.get(code.casefold()) if code else None
            theme = canonicalize_theme(item.theme, existing_themes)
            if theme and theme not in existing_themes:
                existing_themes.append(theme)
            insight = Insight(
                project_id=document.project_id,
                document_id=document.id,
                participant_id=participant.id if participant else None,
                type=item.type,
                text=text,
                source_quote=quote,
                source_location=chunk.source_location[:500],
                sentiment=item.sentiment,
                theme=theme,
                needs_review=compute_needs_review(
                    source_quote=quote,
                    chunk_text=chunk.text,
                    participant_id=participant.id if participant else None,
                    type_confidence=item.type_confidence,
                    alternate_types=item.alternate_types,
                ),
                review_status=ReviewStatus.unreviewed,
            )
            pending.append(insight)
            embed_inputs.append(insight_embedding_input(text, quote))

    embeddings = embed_texts(embed_inputs) if embed_inputs else []
    if len(embeddings) != len(pending):
        raise RuntimeError("Embedding count did not match insight count")
    for insight, vector in zip(pending, embeddings, strict=True):
        insight.embedding = vector
        session.add(insight)
    session.commit()


def _reset_extracted_rows(session: Session, document_id: uuid.UUID) -> None:
    insights = session.exec(
        select(Insight).where(Insight.document_id == document_id)
    ).all()
    for insight in insights:
        session.delete(insight)
    participants = session.exec(
        select(Participant).where(Participant.document_id == document_id)
    ).all()
    for participant in participants:
        session.delete(participant)
    session.flush()


def _project_theme_labels(
    session: Session, project_id: uuid.UUID | None
) -> list[str]:
    if project_id is None:
        return []
    rows = session.exec(
        select(Insight.theme, func.count())
        .where(
            Insight.project_id == project_id,
            col(Insight.theme).is_not(None),
        )
        .group_by(Insight.theme)
        .order_by(func.count().desc())
        .limit(settings.MAX_THEME_LABELS)
    ).all()
    return [theme for theme, _count in rows if theme]