"""
Custom Embeddings Engine — Pure Python & NumPy TF-IDF Vectorizer
===============================================================
This module implements a transparent, lightweight TF-IDF document vectorizer.
It contains no heavy dependency links (like PyTorch or sentence-transformers)
to make the underlying linear algebra of vector space search fully clear.

Mathematical definitions:
- Term Frequency (TF): occurrences of a word / total words in document.
- Document Frequency (DF): number of documents containing a word.
- Inverse Document Frequency (IDF): log((1 + N) / (1 + DF)) + 1.
- Cosine Similarity: A . B / (||A|| * ||B||) which simplifies to A . B when A and B are L2-normalized.
"""

import math
import re
import numpy as np

class TfidfEmbedder:
    def __init__(self):
        self.vocabulary: dict[str, int] = {}  # maps word -> vocab index
        self.idf: np.ndarray = np.array([])    # IDF values indexed by vocab index
        self.doc_count: int = 0
        self.stop_words: set[str] = {
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "to", "of", "in", "on", "at", "for", "with", "by", "about", "as"
        }

    def tokenize(self, text: str) -> list[str]:
        """Normalize, lowercase, and tokenize text, filtering short words and stop words."""
        # Convert to lowercase and strip non-alphanumeric chars
        words = re.findall(r"\b\w{2,}\b", text.lower())
        return [w for w in words if w not in self.stop_words]

    def fit(self, documents: list[str]):
        """
        Build the vocabulary and compute IDF scores for all unique words.
        documents: List of raw document strings.
        """
        self.doc_count = len(documents)
        if self.doc_count == 0:
            self.vocabulary = {}
            self.idf = np.array([])
            return

        # 1. Gather term frequencies across all documents
        doc_tokens = [self.tokenize(doc) for doc in documents]
        
        # 2. Build unique vocabulary mapping
        unique_words = sorted(list(set(w for tokens in doc_tokens for w in tokens)))
        self.vocabulary = {word: idx for idx, word in enumerate(unique_words)}
        vocab_size = len(self.vocabulary)
        
        if vocab_size == 0:
            self.idf = np.array([])
            return

        # 3. Calculate Document Frequency (DF) for each word
        df = np.zeros(vocab_size)
        for tokens in doc_tokens:
            seen_in_doc = set(tokens)
            for word in seen_in_doc:
                if word in self.vocabulary:
                    df[self.vocabulary[word]] += 1

        # 4. Calculate Inverse Document Frequency (IDF)
        # We use a smoothed IDF formula similar to scikit-learn
        self.idf = np.log((1 + self.doc_count) / (1 + df)) + 1.0

    def transform(self, text: str) -> np.ndarray:
        """
        Convert a raw text string into a normalized TF-IDF vector.
        Returns a float32 NumPy array of size (vocab_size,).
        """
        vocab_size = len(self.vocabulary)
        if vocab_size == 0:
            return np.array([], dtype=np.float32)

        tokens = self.tokenize(text)
        if not tokens:
            return np.zeros(vocab_size, dtype=np.float32)

        # 1. Compute Term Frequency (TF)
        tf = np.zeros(vocab_size)
        for t in tokens:
            if t in self.vocabulary:
                tf[self.vocabulary[t]] += 1
        
        # Normalize TF (number of occurrences divided by total token count)
        tf = tf / len(tokens)

        # 2. Compute TF-IDF
        vector = tf * self.idf

        # 3. L2 Normalization (so dot product maps directly to cosine similarity)
        norm = np.linalg.norm(vector)
        if norm > 0.0:
            vector = vector / norm

        return vector.astype(np.float32)

    def get_top_terms(self, vector: np.ndarray, top_n: int = 5) -> list[tuple[str, float]]:
        """Extract the top N highest-scoring terms and their values from a TF-IDF vector."""
        if len(vector) == 0:
            return []
        
        # Sort terms by descending score
        indices = np.argsort(vector)[::-1]
        
        # Map indices back to words
        inv_vocab = {v: k for k, v in self.vocabulary.items()}
        
        top_terms = []
        for idx in indices[:top_n]:
            if vector[idx] > 0.0:
                top_terms.append((inv_vocab[idx], float(vector[idx])))
        return top_terms

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors. Assumes they are already normalized."""
        if len(v1) == 0 or len(v2) == 0:
            return 0.0
        return float(np.dot(v1, v2))
