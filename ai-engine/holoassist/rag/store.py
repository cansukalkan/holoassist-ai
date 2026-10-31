"""Local Chroma retrieval baseline with explicit source isolation and citations."""

import hashlib
import math
import re
from pathlib import Path
from typing import Literal

from holoassist.rag.chunking import DocumentChunk, chunk_document

DIMENSIONS = 512
EMBEDDING_ID = "word-hash-sha256-512-v1"
STOP_WORDS = frozenset("ve veya ile bir bu için de da the a an and or of to is in for".split())


def tokens(text: str) -> frozenset[str]:
    """Simple Unicode tokenization; no stemming or semantic understanding."""
    normalized = text.casefold().replace("\u0307", "")
    return frozenset(re.findall(r"[^\W_]+", normalized)) - STOP_WORDS


def embed(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for token in tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vector[int.from_bytes(digest[:4], "big") % DIMENSIONS] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class ChromaKnowledgeStore:
    """Single-writer prototype. One immutable revision/chunk layout per document.

    Embeddings are supplied explicitly: Chroma never downloads a default model.
    Revision replacement is rejected rather than silently retaining stale chunks.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        source_kind: Literal["synthetic", "manufacturer"],
        collection_name: str | None = None,
        client=None,
    ):
        if source_kind not in ("synthetic", "manufacturer"):
            raise ValueError("source_kind must be synthetic or manufacturer")
        if client is None:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=str(path), settings=Settings(anonymized_telemetry=False)
            )
        self.source_kind = source_kind
        metadata = {
            "embedding_id": EMBEDDING_ID,
            "source_kind": source_kind,
            "schema_version": "1.0",
        }
        self.collection = client.get_or_create_collection(
            name=collection_name or f"holoassist_{source_kind}_wordhash_v1",
            embedding_function=None,
            metadata=metadata,
            configuration={"hnsw": {"space": "cosine"}},
        )
        if self.collection.metadata != metadata:
            raise ValueError("collection metadata differs; use a separate compatible collection")

    def index_document(self, raw: bytes, *, max_chars: int = 1000, overlap: int = 100) -> int:
        chunks = chunk_document(raw, max_chars=max_chars, overlap=overlap)
        if any(item.source_kind != self.source_kind for item in chunks):
            raise ValueError("document source_kind does not match collection")
        first = chunks[0]
        where = {"$and": [{"equipment_id": first.equipment_id}, {"document_id": first.document_id}]}
        existing = self.collection.get(where=where, include=["metadatas", "documents"])
        if existing["ids"]:
            expected = {item.evidence_id: item for item in chunks}
            if set(existing["ids"]) != set(expected):
                raise ValueError("document revision or chunk layout changed; use a new collection")
            for record_id, metadata, document in zip(
                existing["ids"], existing["metadatas"], existing["documents"], strict=True
            ):
                if (
                    metadata["chunk_json"] != expected[record_id].model_dump_json()
                    or document != expected[record_id].excerpt
                ):
                    raise ValueError("stored document differs; use a new collection")
            return len(chunks)
        for start in range(0, len(chunks), 128):
            batch = chunks[start : start + 128]
            self.collection.upsert(
                ids=[item.evidence_id for item in batch],
                embeddings=[embed(item.excerpt) for item in batch],
                documents=[item.excerpt for item in batch],
                metadatas=[
                    {
                        "equipment_id": item.equipment_id,
                        "document_id": item.document_id,
                        "source_kind": item.source_kind,
                        "checksum": item.checksum,
                        "chunk_json": item.model_dump_json(),
                    }
                    for item in batch
                ],
            )
        return len(chunks)

    def search(
        self, query: str, *, equipment_id: str, top_k: int = 3, max_distance: float = 0.9
    ) -> tuple[DocumentChunk, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be nonblank text")
        if not isinstance(equipment_id, str) or not equipment_id.strip():
            raise ValueError("equipment_id must be nonblank text")
        if type(top_k) is not int or not 1 <= top_k <= 20:
            raise ValueError("top_k must be an integer between 1 and 20")
        if (
            type(max_distance) not in (int, float)
            or not math.isfinite(max_distance)
            or not 0 <= max_distance <= 2
        ):
            raise ValueError("max_distance must be a finite cosine distance between 0 and 2")
        query_tokens = tokens(query)
        if not query_tokens:
            return ()
        where = {"$and": [{"equipment_id": equipment_id}, {"source_kind": self.source_kind}]}
        eligible = self.collection.get(where=where, include=[])
        if not eligible["ids"]:
            return ()
        results = self.collection.query(
            query_embeddings=[embed(query)],
            n_results=min(len(eligible["ids"]), max(top_k * 4, 20)),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        accepted = []
        for record_id, document, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
            strict=True,
        ):
            chunk = DocumentChunk.model_validate_json(metadata["chunk_json"])
            if (
                chunk.evidence_id != record_id
                or chunk.excerpt != document
                or chunk.equipment_id != equipment_id
                or chunk.source_kind != self.source_kind
                or chunk.checksum != metadata["checksum"]
            ):
                raise ValueError("stored citation metadata is inconsistent")
            if not math.isfinite(distance):
                raise ValueError("database returned a nonfinite distance")
            if distance > max_distance or not query_tokens.intersection(tokens(document)):
                continue
            payload = chunk.model_dump() | {"retrieval_score": 1.0 - float(distance)}
            accepted.append(DocumentChunk.model_validate(payload))
        accepted.sort(key=lambda item: (-item.retrieval_score, item.evidence_id))
        return tuple(accepted[:top_k])
