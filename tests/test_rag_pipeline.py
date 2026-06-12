import os
import json
import shutil
import tempfile
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.rag_pipeline import RAGPipeline


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
        pipeline.META_FILE = os.path.join(temp_dir, "metadata.json")
        pipeline.save_index()
        
        # Verify persistence files are created
        assert os.path.exists(pipeline.INDEX_FILE)
        assert os.path.exists(pipeline.META_FILE)
        
        # Reload index in a fresh pipeline instance
        new_pipeline = RAGPipeline(index_path=temp_dir)
        new_pipeline.INDEX_FILE = pipeline.INDEX_FILE
        new_pipeline.META_FILE = pipeline.META_FILE
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


if __name__ == "__main__":
    test_rag_pipeline_chunking()
    test_rag_pipeline_ingestion_and_retrieval()
    test_rag_pipeline_retrieve_with_metadata_threshold()
    print("All RAG pipeline unit tests PASSED!")
