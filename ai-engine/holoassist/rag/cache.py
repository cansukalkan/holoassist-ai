"""Content-addressed LRU cache for deterministic RAG queries with equipment isolation."""

import hashlib
import json
import math
from collections import OrderedDict
from typing import Annotated

from pydantic import Field

from holoassist.contracts.models import Checksum, Contract
from holoassist.rag.chunking import DocumentChunk
from holoassist.rag.store import ChromaKnowledgeStore, tokens


class CacheStats(Contract):
    hits: Annotated[int, Field(strict=True, ge=0)]
    misses: Annotated[int, Field(strict=True, ge=0)]
    entries: Annotated[int, Field(strict=True, ge=0)]
    capacity: Annotated[int, Field(strict=True, ge=1)]
    invalidations: Annotated[int, Field(strict=True, ge=0)]
    corpus_digest: Checksum


class CachedKnowledgeStore:
    """Bounded LRU wrapper over ChromaKnowledgeStore.

    Cache keys bind `(source_kind, corpus_digest, equipment_id, tokens, top_k, max_distance)`
    so cached results never cross equipment boundaries or outlive indexed document changes.
    """

    def __init__(self, store: ChromaKnowledgeStore, *, capacity: int = 128):
        if not isinstance(store, ChromaKnowledgeStore):
            raise TypeError("store must be a ChromaKnowledgeStore instance")
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.store = store
        self.source_kind = store.source_kind
        self.capacity = capacity
        self._entries: OrderedDict[str, tuple[DocumentChunk, ...]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._cached_corpus_digest: str | None = None
        self._cached_collection_count: int | None = None

    def _compute_corpus_digest(self) -> str:
        current_count = self.store.collection.count()
        if (
            self._cached_corpus_digest is not None
            and self._cached_collection_count == current_count
        ):
            return self._cached_corpus_digest
        if self._entries:
            self._entries.clear()
            self._invalidations += 1
        snapshot = self.store.collection.get(include=["metadatas"])
        pairs = sorted(
            (record_id, str(meta.get("checksum", "")))
            for record_id, meta in zip(snapshot["ids"], snapshot["metadatas"], strict=True)
        )
        digest = hashlib.sha256(
            json.dumps(
                [self.source_kind, pairs],
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        self._cached_corpus_digest = digest
        self._cached_collection_count = current_count
        return digest

    def invalidate(self) -> None:
        self._entries.clear()
        self._invalidations += 1
        self._cached_corpus_digest = None
        self._cached_collection_count = None

    def index_document(self, raw: bytes, *, max_chars: int = 1000, overlap: int = 100) -> int:
        before_digest = self._compute_corpus_digest()
        count = self.store.index_document(raw, max_chars=max_chars, overlap=overlap)
        self._cached_corpus_digest = None
        self._cached_collection_count = None
        after_digest = self._compute_corpus_digest()
        if after_digest != before_digest and self._entries:
            self._entries.clear()
            self._invalidations += 1
        elif after_digest != before_digest:
            self._invalidations += 1
        return count

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
        normalized_tokens = sorted(tokens(query))
        if not normalized_tokens:
            return ()
        corpus_digest = self._compute_corpus_digest()
        key_payload = json.dumps(
            [
                self.source_kind,
                corpus_digest,
                equipment_id,
                normalized_tokens,
                top_k,
                round(float(max_distance), 9),
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        key = hashlib.sha256(key_payload.encode("utf-8")).hexdigest()
        if key in self._entries:
            self._hits += 1
            self._entries.move_to_end(key)
            cached = self._entries[key]
            return tuple(DocumentChunk.model_validate(item.model_dump()) for item in cached)
        self._misses += 1
        fresh = self.store.search(
            query, equipment_id=equipment_id, top_k=top_k, max_distance=max_distance
        )
        stored = tuple(DocumentChunk.model_validate(item.model_dump()) for item in fresh)
        self._entries[key] = stored
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)
        return tuple(DocumentChunk.model_validate(item.model_dump()) for item in stored)

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            entries=len(self._entries),
            capacity=self.capacity,
            invalidations=self._invalidations,
            corpus_digest=self._compute_corpus_digest(),
        )
