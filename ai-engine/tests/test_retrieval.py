"""Offline baseline behavior, exercised against real in-memory Chroma."""

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from holoassist.rag.chunking import chunk_document
from holoassist.rag.store import ChromaKnowledgeStore, embed, tokens

chromadb = pytest.importorskip("chromadb", reason="install .[rag] for Chroma integration tests")
Settings = pytest.importorskip("chromadb.config").Settings

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "datasets/fixtures/synthetic-guide.json"


@pytest.fixture
def store():
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    return ChromaKnowledgeStore(
        "unused", source_kind="synthetic", client=client, collection_name="test_" + uuid4().hex
    )


def test_hash_embedding_is_deterministic_and_normalized():
    vector = embed("Sıcaklık temperature temperature")
    assert len(vector) == 512
    assert vector == embed("temperature Sıcaklık")
    assert math.isclose(sum(x * x for x in vector), 1.0)
    assert tokens("İÇİN ve") == frozenset()
    assert embed("ve ile") == [0.0] * 512


def test_index_and_search_return_matching_source(store):
    raw = FIXTURE.read_bytes()
    assert store.index_document(raw) == 2
    hits = store.search("temperature", equipment_id="synthetic-rig")
    assert len(hits) == 1
    hit = hits[0]
    assert hit.page == 2
    assert hit.section == "Sentetik sensör kayıtları"
    assert hit.source_kind == "synthetic"
    assert hit.license == "CC0-1.0"
    assert hit.checksum == hashlib.sha256(raw).hexdigest()
    assert hit.retrieval_score is not None
    assert hit.excerpt in json.loads(raw.decode("utf-8-sig"))["blocks"][1]["text"]


def test_repeated_index_is_idempotent(store):
    raw = FIXTURE.read_bytes()
    store.index_document(raw)
    first = store.search("temperature", equipment_id="synthetic-rig")
    assert store.index_document(raw) == 2
    assert store.collection.count() == 2
    assert store.search("temperature", equipment_id="synthetic-rig") == first


def test_missing_results_are_empty(store):
    assert store.search("temperature", equipment_id="synthetic-rig") == ()
    store.index_document(FIXTURE.read_bytes())
    assert store.search("temperature", equipment_id="another-rig") == ()
    assert store.search("astronomy quasar", equipment_id="synthetic-rig") == ()
    assert store.search("ve için", equipment_id="synthetic-rig") == ()


def test_revision_change_is_rejected_without_mutation(store):
    store.index_document(FIXTURE.read_bytes())
    payload = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    payload["document_version"] = "new-version"
    with pytest.raises(ValueError, match="revision or chunk layout"):
        store.index_document(json.dumps(payload).encode())
    assert store.collection.count() == 2
    assert store.search("temperature", equipment_id="synthetic-rig")[0].document_version == "test-1"


def test_changed_chunk_layout_is_rejected(store):
    store.index_document(FIXTURE.read_bytes())
    with pytest.raises(ValueError, match="chunk layout"):
        store.index_document(FIXTURE.read_bytes(), max_chars=80, overlap=15)
    assert store.collection.count() == 2


def test_source_kind_mismatch_is_rejected(store):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    payload["source_kind"] = "manufacturer"
    with pytest.raises(ValueError, match="source_kind"):
        store.index_document(json.dumps(payload).encode())
    assert store.collection.count() == 0


def test_collection_source_and_embedding_configuration_are_checked(store):
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    with pytest.raises(ValueError, match="metadata differs"):
        ChromaKnowledgeStore(
            "unused",
            source_kind="manufacturer",
            client=client,
            collection_name=store.collection.name,
        )


def test_corrupt_stored_document_is_not_returned(store):
    raw = FIXTURE.read_bytes()
    store.index_document(raw)
    chunk = chunk_document(raw)[1]
    store.collection.update(
        ids=[chunk.evidence_id],
        documents=["corrupt temperature"],
        embeddings=[embed("temperature")],
    )
    with pytest.raises(ValueError, match="inconsistent"):
        store.search("temperature", equipment_id="synthetic-rig")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"query": ""},
        {"query": " "},
        {"equipment_id": ""},
        {"top_k": 0},
        {"top_k": True},
        {"top_k": 21},
        {"max_distance": float("nan")},
        {"max_distance": float("inf")},
        {"max_distance": -1},
        {"max_distance": True},
    ],
)
def test_invalid_queries_are_rejected(store, kwargs):
    args = {"query": "temperature", "equipment_id": "synthetic-rig"} | kwargs
    with pytest.raises(ValueError):
        store.search(**args)


def test_top_k_and_distance_filter(store):
    store.index_document(FIXTURE.read_bytes())
    assert len(store.search("belge sensör", equipment_id="synthetic-rig", top_k=1)) <= 1
    assert store.search("temperature", equipment_id="synthetic-rig", max_distance=0) == ()


def test_cli_persistence_and_source_isolation_across_processes():
    # Keep native database files inside the ignored workspace data directory.
    db = ROOT / "data" / "test-chroma" / uuid4().hex
    prefix = [sys.executable, "-m", "holoassist.rag.search", "--db", str(db)]
    env = os.environ | {"PYTHONIOENCODING": "utf-8"}

    def run(*args):
        result = subprocess.run(
            prefix + list(args), capture_output=True, env=env, encoding="utf-8", check=False
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    indexed = run("--source-kind", "synthetic", "index", str(FIXTURE))
    assert indexed["indexed_chunks"] == 2
    hits = run(
        "--source-kind", "synthetic", "query", "temperature", "--equipment-id", "synthetic-rig"
    )
    assert hits[0]["page"] == 2
    assert hits[0]["source_kind"] == "synthetic"
    assert (
        run(
            "--source-kind",
            "manufacturer",
            "query",
            "temperature",
            "--equipment-id",
            "synthetic-rig",
        )
        == []
    )

