"""
Unit Tests for Karl's Educational AI Sandbox
============================================
Covers TfidfEmbedder, CharTokenizer, and MiniGPT.
"""

import pytest
import numpy as np
import torch
from app.utils.custom_embeddings import TfidfEmbedder
from app.engine.mini_transformer import CharTokenizer, MiniGPT

def test_tfidf_embedder():
    embedder = TfidfEmbedder()
    
    # 1. Test tokenization
    tokens = embedder.tokenize("The quick brown fox jumps over the lazy dog!")
    assert "the" not in tokens  # Stop word removed
    assert "fox" in tokens
    assert "dog" in tokens
    assert len(tokens) == 7    # quick, brown, fox, jumps, over, lazy, dog

    # 2. Test fitting
    docs = [
        "The quick brown fox",
        "The lazy dog",
        "Foxes and dogs run fast"
    ]
    embedder.fit(docs)
    assert len(embedder.vocabulary) > 0
    assert embedder.doc_count == 3
    
    # 3. Test transformation
    vec = embedder.transform("quick fox")
    assert vec.shape == (len(embedder.vocabulary),)
    # Norm should be 1.0 (L2 normalized)
    assert np.isclose(np.linalg.norm(vec), 1.0)
    
    # 4. Test cosine similarity
    vec1 = embedder.transform("quick fox")
    vec2 = embedder.transform("lazy dog")
    vec3 = embedder.transform("quick fox")
    
    sim_diff = TfidfEmbedder.cosine_similarity(vec1, vec2)
    sim_same = TfidfEmbedder.cosine_similarity(vec1, vec3)
    
    assert sim_same == pytest.approx(1.0)
    assert sim_diff < 1.0


def test_char_tokenizer():
    tokenizer = CharTokenizer()
    text = "hello world"
    tokenizer.fit(text)
    
    assert tokenizer.vocab_size == len(set(text))
    encoded = tokenizer.encode("hello")
    assert len(encoded) == 5
    decoded = tokenizer.decode(encoded)
    assert decoded == "hello"
    
    # Check out-of-vocab handling
    oov_encoded = tokenizer.encode("z")
    assert len(oov_encoded) == 1
    assert oov_encoded[0] == 0  # Fallback to index 0


def test_mini_gpt():
    vocab_size = 10
    n_embd = 32
    n_heads = 2
    n_layers = 1
    block_size = 16
    
    model = MiniGPT(
        vocab_size=vocab_size,
        n_embd=n_embd,
        n_heads=n_heads,
        n_layers=n_layers,
        block_size=block_size,
        dropout=0.0
    )
    
    # Test forward pass without targets
    idx = torch.randint(0, vocab_size, (2, 8))  # Batch size 2, Context length 8
    logits, loss = model(idx)
    
    assert logits.shape == (2, 8, vocab_size)
    assert loss is None
    
    # Test forward pass with targets
    targets = torch.randint(0, vocab_size, (2, 8))
    logits, loss = model(idx, targets)
    
    assert logits.shape == (2, 8, vocab_size)
    assert loss is not None
    assert isinstance(loss, torch.Tensor)
    
    # Test generation
    idx_start = torch.zeros((1, 1), dtype=torch.long)
    gen = model.generate(idx_start, max_new_tokens=5, temperature=1.0, top_k=2)
    assert gen.shape == (1, 6)
