"""Deterministic chunking of explicitly located UTF-8 JSON source documents."""

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from holoassist.contracts.models import Contract, Evidence, NonBlank

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024


class SourceBlock(Contract):
    page: Annotated[int, Field(strict=True, ge=1)] | None = None
    section: NonBlank | None = None
    text: Annotated[str, Field(strict=True, min_length=1)]

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source block text must not be blank")
        return value

    @model_validator(mode="after")
    def require_locator(self) -> Self:
        if self.page is None and self.section is None:
            raise ValueError("source block needs a page or section")
        return self


class SourceDocument(Contract):
    document_id: NonBlank
    document_version: NonBlank
    equipment_id: NonBlank
    title: NonBlank
    source_uri: NonBlank
    source_kind: Literal["synthetic", "manufacturer"]
    license: NonBlank
    permission_reference: NonBlank
    blocks: Annotated[tuple[SourceBlock, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def require_unique_locators(self) -> Self:
        locators = [(block.page, block.section) for block in self.blocks]
        if len(set(locators)) != len(locators):
            raise ValueError("duplicate source locators; combine text or use distinct sections")
        return self


class DocumentChunk(Evidence):
    """Excerpt plus source policy and zero-based character offsets into its block."""

    title: NonBlank
    source_uri: NonBlank
    source_kind: Literal["synthetic", "manufacturer"]
    license: NonBlank
    permission_reference: NonBlank
    block_index: Annotated[int, Field(strict=True, ge=0)]
    start_char: Annotated[int, Field(strict=True, ge=0)]
    end_char: Annotated[int, Field(strict=True, ge=1)]

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        if self.end_char - self.start_char != len(self.excerpt):
            raise ValueError("chunk offsets must match excerpt length")
        return self


def chunk_document(
    raw: bytes, *, max_chars: int = 1000, overlap: int = 100
) -> tuple[DocumentChunk, ...]:
    """Hash original bytes and split each located block independently.

    Offsets use Python Unicode character indices, not bytes or model tokens.
    Overlap never crosses page/section boundaries. Metadata is declared by the
    caller; authenticity and permission must still be reviewed before indexing.
    """
    if type(max_chars) is not int or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    if type(overlap) is not int or not 0 <= overlap < max_chars:
        raise ValueError("overlap must be an integer in [0, max_chars)")
    if not isinstance(raw, bytes):
        raise ValueError("document input must be bytes")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds 5 MiB limit")
    document = SourceDocument.model_validate_json(raw.decode("utf-8-sig"))
    checksum = hashlib.sha256(raw).hexdigest()
    chunks = []
    for block_index, block in enumerate(document.blocks):
        position = 0
        while position < len(block.text):
            end = min(position + max_chars, len(block.text))
            window = block.text[position:end]
            excerpt = window.strip()
            if excerpt:
                start = position + len(window) - len(window.lstrip())
                stop = start + len(excerpt)
                identity = json.dumps(
                    [
                        document.document_id,
                        document.document_version,
                        document.equipment_id,
                        checksum,
                        block_index,
                        start,
                        stop,
                    ],
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                chunks.append(
                    DocumentChunk(
                        evidence_id="chunk-" + hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                        equipment_id=document.equipment_id,
                        document_id=document.document_id,
                        document_version=document.document_version,
                        checksum=checksum,
                        page=block.page,
                        section=block.section,
                        excerpt=excerpt,
                        title=document.title,
                        source_uri=document.source_uri,
                        source_kind=document.source_kind,
                        license=document.license,
                        permission_reference=document.permission_reference,
                        block_index=block_index,
                        start_char=start,
                        end_char=stop,
                    )
                )
            if end == len(block.text):
                break
            position += max_chars - overlap
    # Trimming overlapping whitespace can yield the same source interval twice.
    return tuple({chunk.evidence_id: chunk for chunk in chunks}.values())
