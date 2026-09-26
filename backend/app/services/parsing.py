from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pdfplumber
from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from app.models import DocumentFormat

@dataclass(frozen=True)
class TextUnit:
    text: str
    source_location: str


class ParseError(ValueError):
    pass


def parse_document(data: bytes, format: DocumentFormat) -> list[TextUnit]:
    if not data:
        raise ParseError("Document is empty")
    if format == DocumentFormat.pdf:
        return _parse_pdf(data)
    if format == DocumentFormat.docx:
        return _parse_docx(data)
    if format == DocumentFormat.txt:
        return _parse_txt(data)
    raise ParseError(f"Unsupported document format: {format}")


def _parse_pdf(data: bytes) -> list[TextUnit]:
    units: list[TextUnit] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if not pdf.pages:
                raise ParseError("PDF has no pages")
            for index, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    units.append(TextUnit(text=text, source_location=f"p.{index}"))
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(f"Failed to parse PDF: {exc}") from exc
    if not units:
        raise ParseError("PDF contained no extractable text")
    return units


def _parse_docx(data: bytes) -> list[TextUnit]:
    try:
        document = DocxDocument(io.BytesIO(data))
    except Exception as exc:
        raise ParseError(f"Failed to parse DOCX: {exc}") from exc
    units: list[TextUnit] = []
    section = "Document"
    buffer: list[str] = []
    def flush() -> None:
        text = "\n".join(buffer).strip()
        buffer.clear()
        if text:
            units.append(TextUnit(text=text, source_location=section))
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        heading = _docx_heading(paragraph)
        if heading is not None:
            flush()
            section = heading
            continue
        buffer.append(text)
    flush()
    if not units:
        raise ParseError("DOCX contained no extractable text")
    return units


def _docx_heading(paragraph: Paragraph) -> str | None:
    style = paragraph.style
    name = (style.name if style is not None else "") or ""
    match = re.match(r"Heading\s+(\d+)$", name, flags=re.IGNORECASE)
    if match:
        return paragraph.text.strip() or f"Heading {match.group(1)}"
    style_id = paragraph._p.get(qn("w:pStyle"))
    if style_id and re.match(r"Heading\d+$", style_id, flags=re.IGNORECASE):
        return paragraph.text.strip() or style_id
    return None


def _parse_txt(data: bytes) -> list[TextUnit]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("TXT is not valid UTF-8") from exc
    lines = text.splitlines()
    blocks: list[tuple[int, int, str]] = []
    start: int | None = None
    buffer: list[str] = []
    def flush_block(end_line: int) -> None:
        nonlocal start
        if start is None:
            return
        block = "\n".join(buffer).strip()
        buffer.clear()
        if block:
            blocks.append((start, end_line, block))
        start = None
    for index, line in enumerate(lines, start=1):
        if line.strip() == "":
            if start is not None:
                flush_block(index - 1)
            continue
        if start is None:
            start = index
        buffer.append(line.rstrip())
    if start is not None:
        flush_block(len(lines))
    if not blocks:
        raise ParseError("TXT contained no extractable text")
    return [
        TextUnit(text=block, source_location=_line_range(start, end))
        for start, end, block in blocks
    ]


def _line_range(start: int, end: int) -> str:
    if start == end:
        return f"line {start}"
    return f"lines {start}–{end}"