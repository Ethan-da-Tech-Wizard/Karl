import os
import sqlite3
import threading
import time

import numpy as np
import pytest

from app.utils.rag_pipeline import RAGPipeline


class _DeterministicEncoder:
    def encode(self, texts, batch_size=32, show_progress_bar=False):
        if isinstance(texts, str):
            texts = [texts]
        vectors = []
        for text in texts:
            vec = np.zeros(384, dtype="float32")
            for token in text.lower().split():
                vec[hash(token) % 384] += 1.0
            norm = np.linalg.norm(vec)
            if norm:
                vec = vec / norm
            vectors.append(vec)
        return np.vstack(vectors)


class _TestRAG(RAGPipeline):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._encoder = _DeterministicEncoder()


class _FailAfterFaissAddRAG(_TestRAG):
    def _add_embeddings_to_index(self, embeddings, vector_ids):
        super()._add_embeddings_to_index(embeddings, vector_ids)
        raise RuntimeError("forced FAISS add failure")


class _BlockingAddRAG(_TestRAG):
    def __init__(self, *args, entered_add: threading.Event, release_add: threading.Event, **kwargs):
        super().__init__(*args, **kwargs)
        self.entered_add = entered_add
        self.release_add = release_add
        self.block_add = False

    def _add_embeddings_to_index(self, embeddings, vector_ids):
        if not self.block_add:
            return super()._add_embeddings_to_index(embeddings, vector_ids)
        self.entered_add.set()
        if not self.release_add.wait(timeout=5.0):
            raise RuntimeError("timed out waiting to release FAISS add")
        return super()._add_embeddings_to_index(embeddings, vector_ids)


def _write_doc(path, name, body):
    doc_path = os.path.join(path, name)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(body)
    return doc_path


def _db_count(path):
    conn = sqlite3.connect(os.path.join(path, "meta.db"), timeout=1.0)
    try:
        return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    finally:
        conn.close()


def test_ingest_rolls_back_sqlite_and_faiss_when_faiss_add_fails(tmp_path):
    pipeline = _FailAfterFaissAddRAG(index_path=str(tmp_path))
    doc_path = _write_doc(
        str(tmp_path),
        "rollback.txt",
        "alpha beta gamma delta epsilon zeta eta theta iota kappa",
    )

    before_count = pipeline.index.ntotal
    with pytest.raises(RuntimeError, match="forced FAISS add failure"):
        pipeline.ingest_file(doc_path, chunk_size=4, overlap=1)

    assert pipeline.index.ntotal == before_count
    assert pipeline.documents == []
    assert _db_count(str(tmp_path)) == 0


def test_wal_allows_metadata_reads_while_ingest_transaction_is_open(tmp_path):
    seed_path = _write_doc(
        str(tmp_path),
        "seed.txt",
        "stable searchable metadata chunk about neural vector search",
    )
    writer_path = _write_doc(
        str(tmp_path),
        "writer.txt",
        "background writer chunk that should not block existing reads",
    )

    entered_add = threading.Event()
    release_add = threading.Event()
    pipeline = _BlockingAddRAG(
        index_path=str(tmp_path),
        entered_add=entered_add,
        release_add=release_add,
    )
    pipeline.ingest_file(seed_path, chunk_size=20, overlap=0)
    assert _db_count(str(tmp_path)) == 1
    pipeline.block_add = True

    errors = []

    def ingest_in_background():
        try:
            pipeline.ingest_file(writer_path, chunk_size=20, overlap=0)
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=ingest_in_background)
    worker.start()
    assert entered_add.wait(timeout=5.0)

    start = time.perf_counter()
    reader = _TestRAG(index_path=str(tmp_path))
    rows_seen = _db_count(str(tmp_path))
    results = reader.retrieve_with_metadata("neural vector search", top_k=1, threshold=2.0)
    elapsed = time.perf_counter() - start

    release_add.set()
    worker.join(timeout=5.0)

    assert not errors
    assert not worker.is_alive()
    assert rows_seen == 1
    assert elapsed < 1.0
    assert results
    assert results[0]["source_file"] == "seed.txt"
    assert _db_count(str(tmp_path)) == 2


def test_remove_source_deletes_matching_sqlite_rows_and_faiss_vectors(tmp_path):
    pipeline = _TestRAG(index_path=str(tmp_path))
    keep_path = _write_doc(str(tmp_path), "keep.txt", "keep neural vector search chunk")
    drop_path = _write_doc(str(tmp_path), "drop.txt", "drop processor instruction chunk")

    pipeline.ingest_file(keep_path, chunk_size=20, overlap=0)
    pipeline.ingest_file(drop_path, chunk_size=20, overlap=0)
    assert pipeline.index.ntotal == 2
    assert _db_count(str(tmp_path)) == 2

    pipeline.remove_source("drop.txt")

    conn = sqlite3.connect(os.path.join(str(tmp_path), "meta.db"))
    try:
        sources = [
            row[0]
            for row in conn.execute("SELECT source_file FROM documents ORDER BY source_file")
        ]
    finally:
        conn.close()

    assert pipeline.index.ntotal == 1
    assert sources == ["keep.txt"]
    assert pipeline.list_sources() == ["keep.txt"]
