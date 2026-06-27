import os
import json
import shutil
import tempfile
import sys
import numpy as np
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class _SlowParseRAG(RAGPipeline):
    def __init__(self, *args, delay=0.01, **kwargs):
        super().__init__(*args, **kwargs)
        self._encoder = _DeterministicEncoder()
        self.delay = delay

    def _chunks_from_file(self, filepath: str, chunk_size: int, overlap: int):
        time.sleep(self.delay)
        with open(filepath, "r", encoding="utf-8") as f:
            return self.chunk_text(f.read(), chunk_size=chunk_size, overlap=overlap)


def test_rag_pipeline_chunking():
    """Test text chunking helper logic under various sizes and overlaps."""
    pipeline = RAGPipeline(index_path=tempfile.mkdtemp())
    try:
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
        
        # Test basic chunk size 4, overlap 1
        chunks = pipeline.chunk_text(text, chunk_size=4, overlap=1)
        # Expected:
        # Chunk 0: "word1 word2 word3 word4"
        # Chunk 1: "word4 word5 word6 word7"
        # Chunk 2: "word7 word8 word9 word10"
        assert len(chunks) == 4
        assert chunks[0] == "word1 word2 word3 word4"
        assert chunks[1] == "word4 word5 word6 word7"
        assert chunks[2] == "word7 word8 word9 word10"
        assert chunks[3] == "word10"
        
        # Test overlap is handled when valid
        chunks_overlap = pipeline.chunk_text(text, chunk_size=3, overlap=1)
        assert len(chunks_overlap) > 0
        
    finally:
        shutil.rmtree(pipeline.index_path)


@pytest.mark.integration
@pytest.mark.model
def test_rag_pipeline_ingestion_and_retrieval():
    """Test full file ingestion, vector index save/load, metadata filters, and thresholding."""
    import pytest
    from tests.conftest import embedding_model_available
    if not embedding_model_available():
        pytest.skip("sentence-transformers embedding model is unavailable (offline and not cached)")

    temp_dir = tempfile.mkdtemp()
    try:
        pipeline = RAGPipeline(index_path=temp_dir)
        
        # Create dummy text files
        doc1_path = os.path.join(temp_dir, "doc1.txt")
        with open(doc1_path, "w", encoding="utf-8") as f:
            f.write("Deep learning models are neural networks with many hidden layers.")
            
        doc2_path = os.path.join(temp_dir, "doc2.txt")
        with open(doc2_path, "w", encoding="utf-8") as f:
            f.write("A computer processor executes instructions from computer programs.")
            
        # Ingest both documents
        pipeline.ingest_file(doc1_path, chunk_size=5, overlap=1)
        pipeline.ingest_file(doc2_path, chunk_size=5, overlap=1)
        
        assert pipeline.index.ntotal > 0
        assert len(pipeline.documents) > 0
        
        # Save index to temp directory
        pipeline.INDEX_FILE = os.path.join(temp_dir, "index.faiss")
        pipeline.META_DB = os.path.join(temp_dir, "meta.db")
        pipeline.save_index()
        
        # Verify persistence files are created
        assert os.path.exists(pipeline.INDEX_FILE)
        assert os.path.exists(pipeline.META_DB)
        
        # Reload index in a fresh pipeline instance
        new_pipeline = RAGPipeline(index_path=temp_dir)
        new_pipeline.INDEX_FILE = pipeline.INDEX_FILE
        new_pipeline.META_DB = pipeline.META_DB
        new_pipeline._load_index()
        
        assert new_pipeline.index.ntotal == pipeline.index.ntotal
        assert len(new_pipeline.documents) == len(pipeline.documents)
        
        # Retrieve test queries
        results = new_pipeline.retrieve("neural networks", top_k=2)
        assert len(results) > 0
        # The neural network text should appear in the first results
        assert any("neural" in r.lower() for r in results)
        
        # Retrieve with source filter
        results_filtered = new_pipeline.retrieve("neural networks", top_k=2, source_filter="doc2.txt")
        # Should not contain neural network text from doc1.txt
        assert not any("neural" in r.lower() for r in results_filtered)
        
        # Retrieve with metadata and check distance thresholds
        retrieved_meta = new_pipeline.retrieve_with_metadata("processor instructions", top_k=5)
        assert len(retrieved_meta) > 0
        
        # Verify that threshold blocks far away results (using extremely low threshold)
        retrieved_thresh = new_pipeline.retrieve("processor instructions", top_k=5, threshold=0.01)
        # Should return nothing as vectors will not be that identical
        assert len(retrieved_thresh) == 0
        
        # Evaluation check
        eval_metrics = new_pipeline.eval_retrieval(
            query="neural networks",
            expected_chunk_ids=[0], # Check first chunk matches
            top_k=3
        )
        assert "hit_at_1" in eval_metrics
        assert "reciprocal_rank" in eval_metrics
        
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.integration
@pytest.mark.model
def test_rag_pipeline_retrieve_with_metadata_threshold():
    """Test retrieve_with_metadata threshold filtering."""
    import pytest
    from tests.conftest import embedding_model_available
    if not embedding_model_available():
        pytest.skip("sentence-transformers embedding model is unavailable")

    temp_dir = tempfile.mkdtemp()
    try:
        pipeline = RAGPipeline(index_path=temp_dir)
        pipeline.ingest_text("Deep learning models are neural networks.", source_name="doc1.txt")
        
        # Test retrieve_with_metadata with extremely low threshold
        res = pipeline.retrieve_with_metadata("neural networks", top_k=5, threshold=0.001)
        assert len(res) == 0
        
        # Test retrieve_with_metadata with relaxed threshold
        res2 = pipeline.retrieve_with_metadata("neural networks", top_k=5, threshold=2.0)
        assert len(res2) > 0
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.integration
@pytest.mark.model
def test_rag_pipeline_attribution():
    """Test retrieve with attribution parameter and retrieve_with_attribution wrapper."""
    import pytest
    from tests.conftest import embedding_model_available
    if not embedding_model_available():
        pytest.skip("sentence-transformers embedding model is unavailable")

    temp_dir = tempfile.mkdtemp()
    try:
        pipeline = RAGPipeline(index_path=temp_dir)
        pipeline.ingest_text("Deep learning models are neural networks.", source_name="doc1.txt")
        
        # Test retrieve with with_attribution=True
        res = pipeline.retrieve("neural networks", top_k=5, with_attribution=True)
        assert len(res) > 0
        assert isinstance(res[0], dict)
        assert "text" in res[0]
        assert "source_file" in res[0]
        assert "distance" in res[0]
        assert "rank" in res[0]
        assert res[0]["source_file"] == "doc1.txt"

        # Test retrieve_with_attribution wrapper
        res2 = pipeline.retrieve_with_attribution("neural networks", top_k=5)
        assert len(res2) > 0
        assert isinstance(res2[0], dict)
        assert res2[0]["text"] == res[0]["text"]
    finally:
        shutil.rmtree(temp_dir)


def test_parallel_batch_ingestion_benchmark_100_mock_python_files():
    temp_dir = tempfile.mkdtemp()
    seq_dir = tempfile.mkdtemp()
    par_dir = tempfile.mkdtemp()
    try:
        files = []
        body = "\n".join(
            f"def function_{i}(): return 'parallel rag ingestion benchmark {i}'"
            for i in range(50)
        )
        for i in range(100):
            path = os.path.join(temp_dir, f"mock_{i:03d}.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            files.append(path)

        sequential = _SlowParseRAG(index_path=seq_dir, delay=0.01)
        parallel = _SlowParseRAG(index_path=par_dir, delay=0.01)

        t0 = time.perf_counter()
        sequential.ingest_files(files, chunk_size=80, overlap=10, max_workers=1, batch_size=32)
        sequential_time = time.perf_counter() - t0

        t1 = time.perf_counter()
        parallel.ingest_files(files, chunk_size=80, overlap=10, max_workers=8, batch_size=32)
        parallel_time = time.perf_counter() - t1

        assert parallel.index.ntotal == sequential.index.ntotal
        assert len(parallel.documents) == len(sequential.documents)
        assert sequential_time / max(parallel_time, 0.001) >= 4.0
    finally:
        shutil.rmtree(temp_dir)
        shutil.rmtree(seq_dir)
        shutil.rmtree(par_dir)


def test_parallel_batch_ingestion_matches_sequential_index_results():
    temp_dir = tempfile.mkdtemp()
    seq_dir = tempfile.mkdtemp()
    par_dir = tempfile.mkdtemp()
    try:
        files = []
        for i in range(20):
            topic = "neural vector search" if i % 2 == 0 else "processor instruction cache"
            path = os.path.join(temp_dir, f"doc_{i:02d}.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write((f"# {topic}\nprint('{topic} {i}')\n") * 25)
            files.append(path)

        sequential = _SlowParseRAG(index_path=seq_dir, delay=0.0)
        parallel = _SlowParseRAG(index_path=par_dir, delay=0.0)

        sequential.ingest_files(files, chunk_size=40, overlap=5, max_workers=1, batch_size=32)
        parallel.ingest_files(files, chunk_size=40, overlap=5, max_workers=8, batch_size=32)

        assert [d["text"] for d in parallel.documents] == [d["text"] for d in sequential.documents]
        assert [d["source_file"] for d in parallel.documents] == [d["source_file"] for d in sequential.documents]

        seq_results = sequential.retrieve_with_metadata("neural vector search", top_k=5, threshold=2.0)
        par_results = parallel.retrieve_with_metadata("neural vector search", top_k=5, threshold=2.0)

        assert [r["chunk_id"] for r in par_results] == [r["chunk_id"] for r in seq_results]
        assert [r["source_file"] for r in par_results] == [r["source_file"] for r in seq_results]
        assert [round(r["distance"], 6) for r in par_results] == [
            round(r["distance"], 6) for r in seq_results
        ]
    finally:
        shutil.rmtree(temp_dir)
        shutil.rmtree(seq_dir)
        shutil.rmtree(par_dir)


if __name__ == "__main__":
    test_rag_pipeline_chunking()
    test_rag_pipeline_ingestion_and_retrieval()
    test_rag_pipeline_retrieve_with_metadata_threshold()
    test_rag_pipeline_attribution()
    test_parallel_batch_ingestion_benchmark_100_mock_python_files()
    test_parallel_batch_ingestion_matches_sequential_index_results()
    print("All RAG pipeline unit tests PASSED!")
