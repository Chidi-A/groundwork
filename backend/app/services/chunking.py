from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.parsing import TextUnit

DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 200

@dataclass(frozen=True)
class Chunk:
    text: str
    source_location: str


def chunk_units(
    units: list[TextUnit],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
    pieces: list[TextUnit] = []
    for unit in units:
        text = unit.text.strip()
        if not text:
            continue
        if len(text) <= chunk_size:
            pieces.append(TextUnit(text=text, source_location=unit.source_location))
        else:
            pieces.extend(_split_long_unit(text, unit.source_location, chunk_size))
    if not pieces:
        return []
    chunks: list[Chunk] = []
    current_texts: list[str] = []
    current_locations: list[str] = []
    current_len = 0
    def flush() -> None:
        nonlocal current_len
        if not current_texts:
            return
        chunks.append(
            Chunk(
                text="\n\n".join(current_texts).strip(),
                source_location=_format_locations(current_locations),
            )
        )
        if chunk_overlap == 0:
            current_texts.clear()
            current_locations.clear()
            current_len = 0
            return
        overlap_text = _tail("\n\n".join(current_texts), chunk_overlap)
        overlap_location = current_locations[-1]
        current_texts.clear()
        current_locations.clear()
        current_len = 0
        if overlap_text:
            current_texts.append(overlap_text)
            current_locations.append(overlap_location)
            current_len = len(overlap_text)
    for piece in pieces:
        extra = len(piece.text) if not current_texts else len(piece.text) + 2
        if current_texts and current_len + extra > chunk_size:
            flush()
        current_texts.append(piece.text)
        current_locations.append(piece.source_location)
        current_len = len("\n\n".join(current_texts))
        if current_len >= chunk_size:
            flush()
    if current_texts:
        joined = "\n\n".join(current_texts).strip()
        if chunks and joined == chunks[-1].text:
            pass
        elif joined:
            chunks.append(
                Chunk(text=joined, source_location=_format_locations(current_locations))
            )
    return [chunk for chunk in chunks if chunk.text]


def _split_long_unit(text: str, location: str, chunk_size: int) -> list[TextUnit]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    segments = paragraphs if paragraphs else [text]
    out: list[TextUnit] = []
    buf: list[str] = []
    def flush_buf() -> None:
        if buf:
            out.append(TextUnit(text="\n\n".join(buf), source_location=location))
            buf.clear()
    for segment in segments:
        if len(segment) > chunk_size:
            flush_buf()
            out.extend(_split_on_whitespace(segment, location, chunk_size))
            continue
        candidate = segment if not buf else "\n\n".join(buf) + "\n\n" + segment
        if buf and len(candidate) > chunk_size:
            flush_buf()
        buf.append(segment)
    flush_buf()
    return out


def _split_on_whitespace(text: str, location: str, chunk_size: int) -> list[TextUnit]:
    words = text.split()
    if not words:
        return []
    out: list[TextUnit] = []
    buf: list[str] = []
    size = 0
    for word in words:
        extra = len(word) if not buf else len(word) + 1
        if buf and size + extra > chunk_size:
            out.append(TextUnit(text=" ".join(buf), source_location=location))
            buf = [word]
            size = len(word)
        else:
            buf.append(word)
            size += extra
    if buf:
        out.append(TextUnit(text=" ".join(buf), source_location=location))
    return out
def _tail(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    clipped = text[-max_len:]
    space = clipped.find(" ")
    if space == -1:
        return clipped.lstrip()
    return clipped[space:].strip()


_PAGE_RE = re.compile(r"^p\.(\d+)$")


def _format_locations(locations: list[str]) -> str:
    unique: list[str] = []
    for location in locations:
        if location not in unique:
            unique.append(location)
    if len(unique) == 1:
        return unique[0]
    pages = [_PAGE_RE.match(loc) for loc in unique]
    if all(pages):
        nums = [int(match.group(1)) for match in pages if match]
        if nums == list(range(nums[0], nums[-1] + 1)):
            return f"p.{nums[0]}–{nums[-1]}"
    return "; ".join(unique)