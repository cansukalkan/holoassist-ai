"""Verify source integrity, boundaries, deterministic IDs and CLI behavior."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from holoassist.rag.chunking import (
    MAX_DOCUMENT_BYTES,
    DocumentChunk,
    SourceDocument,
    chunk_document,
)
from pydantic import ValidationError

FIXTURE = Path(__file__).resolve().parents[2] / "datasets/fixtures/synthetic-guide.json"


@pytest.fixture
def document():
    return json.loads(FIXTURE.read_text(encoding="utf-8-sig"))


def encode(document):
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def test_fixture_keeps_source_offsets_and_metadata():
    raw = FIXTURE.read_bytes()
    source = SourceDocument.model_validate_json(raw.decode("utf-8-sig"))
    chunks = chunk_document(raw, max_chars=80, overlap=15)
    assert len(chunks) > len(source.blocks)
    for chunk in chunks:
        block = source.blocks[chunk.block_index]
        assert chunk.excerpt == block.text[chunk.start_char : chunk.end_char]
        assert chunk.page == block.page
        assert chunk.section == block.section
        assert chunk.checksum == hashlib.sha256(raw).hexdigest()
        for field in (
            "document_id",
            "document_version",
            "equipment_id",
            "title",
            "source_uri",
            "source_kind",
            "license",
            "permission_reference",
        ):
            assert getattr(chunk, field) == getattr(source, field)
        assert chunk.source_kind == "synthetic"
        assert DocumentChunk.model_validate_json(chunk.model_dump_json()) == chunk
    assert len({chunk.evidence_id for chunk in chunks}) == len(chunks)
    assert chunk_document(raw, max_chars=80, overlap=15) == chunks


def test_every_nonwhitespace_character_is_covered(document):
    document["blocks"] = [{"section": "one", "text": "  abç d\n" * 20 + " end  "}]
    source_text = document["blocks"][0]["text"]
    chunks = chunk_document(encode(document), max_chars=17, overlap=4)
    covered = {i for chunk in chunks for i in range(chunk.start_char, chunk.end_char)}
    assert all(i in covered for i, char in enumerate(source_text) if not char.isspace())
    assert all(len(chunk.excerpt) <= 17 for chunk in chunks)
    assert all(chunk.page is None and chunk.section == "one" for chunk in chunks)


def test_exact_overlap_and_final_chunk(document):
    document["blocks"] = [{"page": 1, "text": "abcdefghijklmnopqrstuvw"}]
    chunks = chunk_document(encode(document), max_chars=10, overlap=3)
    assert [(c.start_char, c.end_char) for c in chunks] == [(0, 10), (7, 17), (14, 23)]
    assert chunks[0].excerpt[-3:] == chunks[1].excerpt[:3]


def test_small_page_is_not_combined_with_next(document):
    document["blocks"] = [{"page": 1, "text": "one"}, {"page": 2, "text": "two"}]
    chunks = chunk_document(encode(document))
    assert [(c.page, c.excerpt) for c in chunks] == [(1, "one"), (2, "two")]


@pytest.mark.parametrize(
    "field,value",
    [
        ("document_version", "test-2"),
        ("equipment_id", "another-rig"),
        ("document_id", "another-document"),
    ],
)
def test_changed_metadata_changes_chunk_identity(document, field, value):
    original = chunk_document(encode(document))[0]
    document[field] = value
    changed = chunk_document(encode(document))[0]
    assert changed.evidence_id != original.evidence_id
    assert changed.checksum != original.checksum


def test_changed_text_changes_checksum(document):
    original = chunk_document(encode(document))[0]
    document["blocks"][0]["text"] += " Changed."
    changed = chunk_document(encode(document))[0]
    assert original.checksum != changed.checksum
    assert original.evidence_id != changed.evidence_id


@pytest.mark.parametrize(
    "field", ["license", "permission_reference", "source_kind", "document_version"]
)
def test_missing_source_policy_is_rejected(document, field):
    document.pop(field)
    with pytest.raises(ValidationError):
        chunk_document(encode(document))


@pytest.mark.parametrize(
    "blocks",
    [
        [],
        [{"text": "missing locator"}],
        [{"page": 1, "text": "   "}],
        [{"page": 0, "text": "invalid page"}],
        [{"page": 1, "text": "a"}, {"page": 1, "text": "b"}],
    ],
)
def test_invalid_blocks_are_rejected(document, blocks):
    document["blocks"] = blocks
    with pytest.raises(ValidationError):
        chunk_document(encode(document))


@pytest.mark.parametrize(
    "max_chars,overlap",
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11), (True, 0), (10, False), (10.5, 0)],
)
def test_invalid_chunk_configuration_is_rejected(max_chars, overlap):
    with pytest.raises(ValueError):
        chunk_document(FIXTURE.read_bytes(), max_chars=max_chars, overlap=overlap)


@pytest.mark.parametrize(
    "raw",
    [b"not json", b"\xff", b"{}", b"x" * (MAX_DOCUMENT_BYTES + 1)],
    ids=["malformed", "non-utf8", "missing-fields", "oversized"],
)
def test_invalid_input_rejected(raw):
    with pytest.raises(ValueError):
        chunk_document(raw)


def test_whitespace_windows_do_not_generate_empty_chunks(document):
    document["blocks"] = [{"section": "test", "text": "a" + " " * 100 + "b"}]
    chunks = chunk_document(encode(document), max_chars=10, overlap=0)
    assert [c.excerpt for c in chunks] == ["a", "b"]


def test_cli_outputs_parseable_source_preserving_json():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "holoassist.rag",
            str(FIXTURE),
            "--max-chars",
            "80",
            "--overlap",
            "15",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    # ASCII JSON escapes make output portable across Windows console encodings.
    payload = json.loads(result.stdout.decode("ascii"))
    assert payload
    assert all(item["source_kind"] == "synthetic" for item in payload)


def test_cli_missing_file_returns_clean_error():
    result = subprocess.run(
        [sys.executable, "-m", "holoassist.rag", str(FIXTURE.parent / "nonexistent-document.json")],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert b"Document rejected:" in result.stderr
    assert b"Traceback" not in result.stderr


def test_overlap_does_not_duplicate_identical_source_interval(document):
    document["blocks"] = [{"page": 1, "text": " " * 10 + "a" + " " * 10}]
    chunks = chunk_document(encode(document), max_chars=10, overlap=9)
    assert len(chunks) == 1
    assert chunks[0].excerpt == "a"
    assert (chunks[0].start_char, chunks[0].end_char) == (10, 11)
