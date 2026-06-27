# RAG Pipeline — Technical Reference

`app/utils/rag_pipeline.py`

---

## Storage Architecture

The pipeline uses two co-located stores under `data/vector_db/`:

| File | Role |
|------|------|
| `index.faiss` | FAISS `IndexIDMap2` (flat L2) over 384-dim MiniLM embeddings |
| `meta.db` | SQLite WAL-mode database — one row per chunk with `vector_id`, `text`, `source`, `chunk_index` |

**Migration note:** Early versions stored metadata in a flat `metadata.json` file.
The current implementation uses `meta.db` with WAL journaling for crash safety.
On first load from a `metadata.json` backup, `RAGPipeline` automatically migrates
the flat list into SQLite and removes the legacy file.

```python
# Schema
CREATE TABLE IF NOT EXISTS documents (
    vector_id   INTEGER PRIMARY KEY,
    text        TEXT NOT NULL,
    source      TEXT,
    chunk_index INTEGER DEFAULT 0
)
# PRAGMA journal_mode = WAL
```

---

## Embedding Model

- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- Loaded lazily; falls back gracefully if `sentence-transformers` is unavailable.
- `HF_HUB_OFFLINE=1` is set by `main.py` before any import — the model must be cached locally.

---

## Ingestion

```python
rag.ingest_file(path: str,
                chunk_size: int = 200,
                overlap: int = 50) -> int
```
Supports PDF, DOCX, TXT, MD, PY, CSV.  Returns the number of chunks added.

```python
rag.ingest_text(text: str,
                source_name: str = "manual",
                chunk_size: int = 200,
                overlap: int = 0) -> int
```
Ingests a raw string directly (used by tests and the agentic loop).

```python
rag.ingest_directory(path: str, **kwargs) -> int
```
Recursively ingests all supported files under `path`.

---

## Retrieval

### Dense-only

```python
rag.retrieve(query, top_k=3, source_filter=None,
             distance_threshold=None) -> list[str]
rag.retrieve_with_metadata(query, top_k=3, ...) -> list[dict]
rag.retrieve_with_attribution(query, top_k=3, ...) -> list[dict]
```

`distance_threshold` filters out chunks whose L2 distance exceeds the threshold.
Results include `text`, `source`, `chunk_index`, `distance`, `rank`.

### Sparse (TF-IDF keyword)

```python
rag.retrieve_sparse(query, top_k=5,
                    source_filter=None) -> list[dict]
```

Fits a fresh `TfidfVectorizer` over all stored document texts, then ranks by
cosine similarity.  Returns `text`, `source`, `chunk_index`, `tfidf_score`, `rank`.

### Hybrid (Reciprocal Rank Fusion)

```python
rag.retrieve_hybrid(query, top_k=3,
                    source_filter=None,
                    rrf_constant=60,
                    use_reranker=False,
                    rerank_candidates=15) -> list[dict]
```

Fuses dense and sparse rankings via RRF:

```
rrf_score(d) = Σ  1 / (k + rank_i(d))
               i ∈ {dense, sparse}
```

Default `k = 60`.  Each result carries `rrf_score`, `dense_rank`, `sparse_rank`, `rank`.

#### CrossEncoder Reranking

When `use_reranker=True`, the pipeline:

1. Builds a candidate pool of `rerank_candidates` (default 15) chunks via RRF
   (the pool uses `fetch_k = rerank_candidates × 2` initial candidates).
2. Calls `CrossEncoder.predict([(query, chunk_text), ...])` on the pool.
3. Sorts by score descending, slices to `top_k`, reassigns `rank`.
4. Attaches `rerank_score` (float) to every result.

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (lazy-loaded, cached locally).

Fallback behaviour:
- If the CrossEncoder model is not cached, loading fails once and the sentinel
  `_RERANKER_UNAVAILABLE` prevents any further load attempts.
- If `predict()` raises, the method logs a warning and returns the RRF-ordered pool.
- In both cases `rerank_score` is absent from the returned dicts.

---

## Evaluation

```python
rag.eval_retrieval(query, expected_ids, top_k) -> dict
```

Returns `{"hit@1": bool, "hit@3": bool, "hit@k": bool, "mrr": float}`.

---

## Known Gaps

- No built-in deduplication on ingest — identical chunks can accumulate across
  multiple ingestion calls for the same source file.
- `retrieve()` and `retrieve_with_metadata()` apply `distance_threshold` but
  `retrieve_hybrid()` does not — all RRF candidates are returned regardless of
  individual L2 distance.
