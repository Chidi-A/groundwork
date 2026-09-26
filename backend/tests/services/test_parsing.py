import io

from docx import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
import pytest

from app.models import DocumentFormat
from app.services.parsing import ParseError, parse_document


def _pdf_with_pages(pages: list[str]) -> bytes:
    def escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    n = len(pages)
    font_id = 3 + n
    content_start = font_id + 1
    bodies: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids ["
        + " ".join(f"{3 + i} 0 R" for i in range(n))
        + f"] /Count {n} >>",
    ]
    for i in range(n):
        bodies.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_start + i} 0 R >>"
        )
    bodies.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({escape(text)}) Tj ET\n"
        bodies.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}endstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(bodies, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref_at = len(out)
    out += f"xref\n0 {len(bodies) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(bodies) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def _docx_bytes(paragraphs: list[tuple[str, str | None]]) -> bytes:
    document = DocxDocument()
    styles = document.styles
    for heading in ("Heading 1", "Heading 2"):
        try:
            styles[heading]
        except KeyError:
            styles.add_style(heading, WD_STYLE_TYPE.PARAGRAPH)
    for text, style in paragraphs:
        para = document.add_paragraph(text)
        if style:
            para.style = style
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_parse_pdf_tags_each_page() -> None:
    data = _pdf_with_pages(["First page findings", "Second page quotes"])
    units = parse_document(data, DocumentFormat.pdf)
    assert [u.source_location for u in units] == ["p.1", "p.2"]
    assert "First page findings" in units[0].text
    assert "Second page quotes" in units[1].text


def test_parse_docx_splits_on_headings() -> None:
    data = _docx_bytes(
        [
            ("Onboarding", "Heading 1"),
            ("Users get stuck on the invite step.", None),
            ("Pricing", "Heading 1"),
            ("The annual plan feels opaque.", None),
        ]
    )
    units = parse_document(data, DocumentFormat.docx)
    assert [(u.source_location, u.text) for u in units] == [
        ("Onboarding", "Users get stuck on the invite step."),
        ("Pricing", "The annual plan feels opaque."),
    ]


def test_parse_txt_keeps_line_ranges() -> None:
    data = b"Alpha block line one\nAlpha line two\n\n\nBeta block\n"
    units = parse_document(data, DocumentFormat.txt)
    assert units[0].source_location == "lines 1–2"
    assert "Alpha block" in units[0].text
    assert units[1].source_location == "line 5"
    assert units[1].text == "Beta block"


def test_parse_rejects_empty() -> None:
    with pytest.raises(ParseError):
        parse_document(b"", DocumentFormat.txt)
    with pytest.raises(ParseError):
        parse_document(b"   \n\n", DocumentFormat.txt)