from app.services.chunking import chunk_units
from app.services.parsing import TextUnit


def test_chunker_carries_page_metadata_across_pages() -> None:
    units = [
        TextUnit(text=" ".join(["pageone"] * 15), source_location="p.1"),
        TextUnit(text="pagetwo extra", source_location="p.2"),
    ]
    chunks = chunk_units(units, chunk_size=80, chunk_overlap=0)
    spanning = [chunk for chunk in chunks if chunk.source_location == "p.1–2"]
    assert spanning
    assert "pageone" in spanning[0].text
    assert "pagetwo" in spanning[0].text


def test_chunker_collapses_consecutive_pages() -> None:
    units = [
        TextUnit(text="one", source_location="p.12"),
        TextUnit(text="two", source_location="p.13"),
        TextUnit(text="three", source_location="p.14"),
    ]
    chunks = chunk_units(units, chunk_size=2000, chunk_overlap=0)
    assert len(chunks) == 1
    assert chunks[0].source_location == "p.12–14"


def test_chunker_splits_oversized_unit_without_losing_location() -> None:
    units = [TextUnit(text="word " * 50, source_location="p.4")]
    chunks = chunk_units(units, chunk_size=40, chunk_overlap=0)
    assert len(chunks) > 1
    assert all(chunk.source_location == "p.4" for chunk in chunks)


def test_chunker_skips_blank_units() -> None:
    units = [
        TextUnit(text="   ", source_location="p.1"),
        TextUnit(text="Kept", source_location="p.2"),
    ]
    chunks = chunk_units(units, chunk_size=2000, chunk_overlap=0)
    assert len(chunks) == 1
    assert chunks[0].source_location == "p.2"
    assert chunks[0].text == "Kept"


def test_chunker_overlap_keeps_prior_location() -> None:
    units = [
        TextUnit(text="alpha beta gamma delta", source_location="p.1"),
        TextUnit(text="epsilon zeta eta theta", source_location="p.2"),
    ]
    chunks = chunk_units(units, chunk_size=30, chunk_overlap=10)
    assert len(chunks) >= 2
    assert chunks[0].source_location == "p.1"