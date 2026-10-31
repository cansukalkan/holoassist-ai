"""Tests for content-addressed RAG query caching, equipment isolation, and invalidation."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from holoassist.rag.cache import CachedKnowledgeStore
from holoassist.rag.store import ChromaKnowledgeStore

chromadb = pytest.importorskip("chromadb", reason="install .[rag] for Chroma cache tests")
Settings = pytest.importorskip("chromadb.config").Settings

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "datasets/fixtures/synthetic-guide.json"
DIAG = ROOT / "datasets/fixtures/synthetic-diagnostic.json"


@pytest.fixture
def cached_store():
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    base = ChromaKnowledgeStore(
        "unused",
        source_kind="synthetic",
        client=client,
        collection_name="cache_test_" + uuid4().hex,
    )
    return CachedKnowledgeStore(base, capacity=2)


def test_cold_miss_then_warm_hit_with_token_normalization(cached_store):
    cached_store.index_document(GUIDE.read_bytes())
    first = cached_store.search("temperature Sıcaklık", equipment_id="synthetic-rig")
    assert len(first) == 1
    assert cached_store.stats().misses == 1
    assert cached_store.stats().hits == 0

    second = cached_store.search("sıcaklık temperature temperature", equipment_id="synthetic-rig")
    assert second == first
    assert second[0] is not first[0]
    assert cached_store.stats().misses == 1
    assert cached_store.stats().hits == 1


def test_cross_equipment_queries_never_share_cache_entries(cached_store):
    cached_store.index_document(GUIDE.read_bytes())
    hits_known = cached_store.search("temperature", equipment_id="synthetic-rig")
    hits_other = cached_store.search("temperature", equipment_id="other-rig")
    assert len(hits_known) == 1
    assert hits_other == ()
    assert cached_store.stats().misses == 2
    assert cached_store.stats().hits == 0


def test_indexing_new_document_invalidates_stale_cache_entries(cached_store):
    cached_store.index_document(GUIDE.read_bytes())
    before_digest = cached_store.stats().corpus_digest
    cached_store.search("temperature", equipment_id="synthetic-rig")
    assert cached_store.stats().entries == 1

    cached_store.index_document(DIAG.read_bytes())
    after_stats = cached_store.stats()
    assert after_stats.corpus_digest != before_digest
    assert after_stats.entries == 0
    assert after_stats.invalidations >= 1


def test_lru_capacity_evicts_oldest_entry(cached_store):
    cached_store.index_document(GUIDE.read_bytes())
    cached_store.search("temperature", equipment_id="synthetic-rig")
    cached_store.search("current", equipment_id="synthetic-rig")
    # Refresh "temperature" so "current" becomes least-recently-used
    cached_store.search("temperature", equipment_id="synthetic-rig")
    cached_store.search("vibration", equipment_id="synthetic-rig")
    assert cached_store.stats().entries == 2

    hits_before = cached_store.stats().hits
    cached_store.search("temperature", equipment_id="synthetic-rig")
    assert cached_store.stats().hits == hits_before + 1


def test_direct_collection_mutation_detected_and_invalidated(cached_store):
    cached_store.index_document(GUIDE.read_bytes())
    cached_store.search("temperature", equipment_id="synthetic-rig")
    assert cached_store.stats().entries == 1

    other_doc = json.loads(DIAG.read_text(encoding="utf-8-sig"))
    cached_store.store.index_document(json.dumps(other_doc).encode("utf-8"))
    # Next search detects collection count change and invalidates stale cache automatically
    cached_store.search("temperature", equipment_id="synthetic-rig")
    assert cached_store.stats().invalidations >= 2

