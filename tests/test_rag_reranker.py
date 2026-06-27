"""
Cross-Encoder Reranker integration tests for RAGPipeline.retrieve_hybrid.

Strategy
--------
All tests use a _DeterministicEncoder (hash-based, no model weights needed) so
the FAISS index and TF-IDF retrieval work in isolation.  The CrossEncoder is
replaced by a unittest.mock.MagicMock whose predict() side_effect returns
pre-determined scores keyed on chunk text — this lets us assert that the
output order follows the mocked scores rather than the RRF distances.
"""

from __future__ import annotations

import shutil
import tempfile
from unittest.mock import MagicMock, PropertyMock, patch

import numpy as np
import pytest

from app.utils.rag_pipeline import RAGPipeline, _RERANKER_UNAVAILABLE


# ── Shared helpers ────────────────────────────────────────────────────────────

class _DeterministicEncoder:
    """Hash-based encoder: identical inputs → identical vectors, no model file."""

    def encode(self, texts, batch_size: int = 32, show_progress_bar: bool = False):
        if isinstance(texts, str):
            texts = [texts]
        vectors = []
        for text in texts:
            vec = np.zeros(384, dtype="float32")
            for token in text.lower().split():
                vec[hash(token) % 384] += 1.0
            norm = np.linalg.norm(vec)
            if norm:
                vec /= norm
            vectors.append(vec)
        return np.vstack(vectors).astype("float32")


def _make_pipeline(index_path: str) -> RAGPipeline:
    rag = RAGPipeline(index_path=index_path)
    rag._encoder = _DeterministicEncoder()
    return rag


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def rag(tmp_dir):
    return _make_pipeline(tmp_dir)


# Five documents with distinctive single-word identifiers that the mock
# predict() uses to return a pre-determined relevance score.
_DOCS = {
    "epsilon": (
        "epsilon document about natural language understanding and text parsing",
        0.91,  # highest reranker score → rank 1 after reranking
    ),
    "alpha": (
        "alpha document about machine learning algorithms and deep neural networks",
        0.82,  # second
    ),
    "gamma": (
        "gamma document about signal processing and fourier transform wavelets",
        0.67,  # third
    ),
    "delta": (
        "delta document about computer vision image classification recognition",
        0.45,  # fourth
    ),
    "beta": (
        "beta document about relational database indexing and sql query optimisation",
        0.15,  # lowest
    ),
}

_QUERY = "artificial intelligence research applications"


def _ingest_all(rag: RAGPipeline) -> None:
    for key, (text, _score) in _DOCS.items():
        rag.ingest_text(text, source_name=f"{key}.txt", chunk_size=200, overlap=0)


def _make_reranker_mock() -> MagicMock:
    """Return a mock CrossEncoder whose predict() uses text content to look up scores."""

    def _predict(pairs: list[tuple[str, str]]) -> np.ndarray:
        scores = []
        for _query, text in pairs:
            score = 0.0
            for keyword, (_doc_text, s) in _DOCS.items():
                if keyword in text:
                    score = s
                    break
            scores.append(score)
        return np.array(scores, dtype="float32")

    mock = MagicMock()
    mock.predict.side_effect = _predict
    return mock


# ── Core reranking behaviour ──────────────────────────────────────────────────

def test_reranker_overrides_rrf_ordering(rag):
    """
    Main regression: output order must reflect CrossEncoder scores, not RRF distances.

    The mock assigns epsilon=0.91 > alpha=0.82 > gamma=0.67 … regardless of
    which order RRF selects them.  With top_k=3, the first three results must
    be epsilon, alpha, gamma in that order.
    """
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    results = rag.retrieve_hybrid(
        _QUERY, top_k=3, use_reranker=True, rerank_candidates=5
    )

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    texts = [r["text"] for r in results]
    assert "epsilon" in texts[0], (
        f"Rank-1 result should be the epsilon doc (score 0.91); got {texts[0]!r}"
    )
    assert "alpha" in texts[1], (
        f"Rank-2 result should be the alpha doc (score 0.82); got {texts[1]!r}"
    )
    assert "gamma" in texts[2], (
        f"Rank-3 result should be the gamma doc (score 0.67); got {texts[2]!r}"
    )


def test_reranker_scores_descend_monotonically(rag):
    """rerank_score attached to each result must decrease from rank 1 to rank N."""
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    results = rag.retrieve_hybrid(
        _QUERY, top_k=4, use_reranker=True, rerank_candidates=5
    )

    scores = [r["rerank_score"] for r in results]
    assert scores == sorted(scores, reverse=True), (
        f"rerank_scores not in descending order: {scores}"
    )


def test_rerank_score_key_attached_to_all_results(rag):
    """Every result returned when use_reranker=True must carry a 'rerank_score' key."""
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    results = rag.retrieve_hybrid(_QUERY, top_k=3, use_reranker=True)

    for i, r in enumerate(results):
        assert "rerank_score" in r, f"Result [{i}] missing 'rerank_score': {r.keys()}"
        assert isinstance(r["rerank_score"], float)


def test_rrf_score_still_present_after_reranking(rag):
    """RRF metadata must be preserved alongside the rerank score."""
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    results = rag.retrieve_hybrid(_QUERY, top_k=3, use_reranker=True)

    for r in results:
        assert "rrf_score" in r, f"rrf_score key missing after reranking: {r.keys()}"


def test_rank_field_reflects_reranked_position(rag):
    """After reranking, r['rank'] must equal 1-based position in the output list."""
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    results = rag.retrieve_hybrid(_QUERY, top_k=3, use_reranker=True)

    for expected_rank, r in enumerate(results, 1):
        assert r["rank"] == expected_rank, (
            f"Expected rank={expected_rank}, got {r['rank']}"
        )


# ── CrossEncoder call contract ────────────────────────────────────────────────

def test_reranker_called_with_query_chunk_pairs(rag):
    """predict() must receive a list of (query, chunk_text) tuples."""
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    rag.retrieve_hybrid(_QUERY, top_k=2, use_reranker=True, rerank_candidates=5)

    rag._reranker.predict.assert_called_once()
    pairs = rag._reranker.predict.call_args[0][0]

    assert isinstance(pairs, list), "predict() arg must be a list"
    for pair in pairs:
        assert isinstance(pair, tuple) and len(pair) == 2, (
            f"Each input must be a (query, text) tuple; got {pair!r}"
        )
        query_str, chunk_str = pair
        assert isinstance(query_str, str) and isinstance(chunk_str, str)
        assert query_str == _QUERY, (
            f"First element of pair must be the query; got {query_str!r}"
        )


def test_reranker_pool_limited_by_rerank_candidates(rag):
    """predict() must receive at most rerank_candidates pairs."""
    _ingest_all(rag)

    received_sizes: list[int] = []

    mock = MagicMock()
    def _predict(pairs):
        received_sizes.append(len(pairs))
        return np.zeros(len(pairs), dtype="float32")
    mock.predict.side_effect = _predict
    rag._reranker = mock

    rag.retrieve_hybrid(_QUERY, top_k=2, use_reranker=True, rerank_candidates=3)

    assert received_sizes, "predict() was never called"
    # With 5 docs ingested and rerank_candidates=3, pool must be at most 3.
    assert received_sizes[0] <= 3, (
        f"predict() received {received_sizes[0]} pairs, expected ≤ 3 (rerank_candidates)"
    )


def test_top_k_slices_after_reranking(rag):
    """retrieve_hybrid must return exactly top_k results even when pool is larger."""
    _ingest_all(rag)
    rag._reranker = _make_reranker_mock()

    for top_k in (1, 2, 3):
        results = rag.retrieve_hybrid(
            _QUERY, top_k=top_k, use_reranker=True, rerank_candidates=5
        )
        assert len(results) == top_k, (
            f"Expected {top_k} results, got {len(results)}"
        )


# ── Fallback / graceful degradation ──────────────────────────────────────────

def test_fallback_to_rrf_when_reranker_property_returns_none(rag):
    """When the reranker property yields None, output must be RRF-ordered (no crash)."""
    _ingest_all(rag)

    with patch.object(type(rag), "reranker", new_callable=PropertyMock, return_value=None):
        results = rag.retrieve_hybrid(_QUERY, top_k=3, use_reranker=True)

    assert isinstance(results, list)
    assert len(results) <= 3
    for r in results:
        assert "rrf_score" in r
        assert "rerank_score" not in r, "rerank_score must not appear in RRF fallback"


def test_fallback_to_rrf_on_predict_exception(rag):
    """If predict() raises, retrieve_hybrid must fall back to RRF order gracefully."""
    _ingest_all(rag)

    mock = MagicMock()
    mock.predict.side_effect = RuntimeError("GPU OOM")
    rag._reranker = mock

    results = rag.retrieve_hybrid(_QUERY, top_k=3, use_reranker=True)

    assert isinstance(results, list)
    assert len(results) <= 3
    for r in results:
        assert "rerank_score" not in r


def test_no_reranker_call_without_use_reranker_flag(rag):
    """Default call (use_reranker=False) must not touch the CrossEncoder at all."""
    _ingest_all(rag)
    mock = MagicMock()
    rag._reranker = mock

    results = rag.retrieve_hybrid(_QUERY, top_k=3)   # use_reranker defaults to False

    mock.predict.assert_not_called()
    for r in results:
        assert "rerank_score" not in r


def test_no_rerank_score_in_plain_hybrid_results(rag):
    """rerank_score must not bleed into standard (non-reranker) results."""
    _ingest_all(rag)

    results = rag.retrieve_hybrid(_QUERY, top_k=3)

    for r in results:
        assert "rerank_score" not in r, (
            f"Plain hybrid result unexpectedly contains rerank_score: {r}"
        )


# ── reranker property ─────────────────────────────────────────────────────────

def test_reranker_lazy_loads_on_first_property_access(rag):
    """The CrossEncoder must not be instantiated until reranker is first accessed."""
    assert rag._reranker is None, "reranker must not be created during __init__"

    mock_ce_class = MagicMock(return_value=MagicMock())

    with patch("sentence_transformers.CrossEncoder", mock_ce_class):
        _ = rag.reranker

    mock_ce_class.assert_called_once_with("cross-encoder/ms-marco-MiniLM-L-6-v2")


def test_reranker_property_returns_none_and_does_not_retry_on_load_failure(rag):
    """A failed load must cache the failure and skip all future load attempts."""
    with patch(
        "sentence_transformers.CrossEncoder",
        side_effect=OSError("model weights not cached"),
    ):
        result = rag.reranker

    assert result is None, "Property must return None when load fails"
    assert rag._reranker is _RERANKER_UNAVAILABLE, (
        "Sentinel must be stored after failure so retries are skipped"
    )

    # Second access: CrossEncoder must NOT be called again.
    with patch("sentence_transformers.CrossEncoder") as mock_ce:
        result2 = rag.reranker

    mock_ce.assert_not_called()
    assert result2 is None


def test_reranker_property_caches_successful_instance(rag):
    """After a successful load the same object is returned on every subsequent access."""
    mock_instance = MagicMock()

    with patch("sentence_transformers.CrossEncoder", return_value=mock_instance):
        first  = rag.reranker
        second = rag.reranker

    assert first is mock_instance
    assert second is mock_instance


# ── Empty index edge case ─────────────────────────────────────────────────────

def test_retrieve_hybrid_with_reranker_on_empty_index_returns_empty(rag):
    """retrieve_hybrid must return [] without calling predict when the index is empty."""
    mock = MagicMock()
    rag._reranker = mock

    results = rag.retrieve_hybrid(_QUERY, top_k=3, use_reranker=True)

    assert results == []
    mock.predict.assert_not_called()
