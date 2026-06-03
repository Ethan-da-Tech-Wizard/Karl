"""
RAG Pipeline — Karl Workbench (Hardened)
=========================================
Changes from original:
  - Persistent FAISS index: saved/loaded from data/vector_db/
  - File-level metadata attached to every chunk
  - Optional contextual chunk headers (source + chunk ID prefix)
  - source_filter param on retrieve() to restrict by file
  - Retrieval eval metrics: hit@k and reciprocal rank
"""

import json
import os
import time

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import fitz   # PyMuPDF
import docx


class RAGPipeline:
    INDEX_FILE = "data/vector_db/index.faiss"
    META_FILE  = "data/vector_db/metadata.json"

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: str = "data/vector_db",
        contextual_headers: bool = False,
    ):
        """
        Args:
            model_name:          SentenceTransformer model for embeddings.
            index_path:          Directory for persisted index files.
            contextual_headers:  If True, prepend "[Source: file | Chunk N]" to
                                 each retrieved chunk — aids model citation.
        """
        # Load the embedding model quietly -- suppress "Loading weights" progress
        # bar and the "BertModel LOAD REPORT" table that sentence-transformers
        # prints to stdout/stderr on every cold start.
        import io, contextlib
        _sink = io.StringIO()
        with contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
            self.encoder = SentenceTransformer(model_name)
        self.index_path = index_path
        self.INDEX_FILE = os.path.join(index_path, "index.faiss")
        self.META_FILE  = os.path.join(index_path, "metadata.json")
        self.contextual_headers = contextual_headers

        os.makedirs(self.index_path, exist_ok=True)

        self.dimension = self.encoder.get_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)

        # Each entry: {"text": str, "source_file": str, "chunk_id": int, "ingested_at": str}
        self.documents: list[dict] = []

        # Load persisted index if it exists
        self._load_index()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_index(self):
        """Load FAISS index and metadata from disk if they exist."""
        if os.path.exists(self.INDEX_FILE) and os.path.exists(self.META_FILE):
            try:
                self.index = faiss.read_index(self.INDEX_FILE)
                with open(self.META_FILE, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                print(f"[RAG] Loaded {self.index.ntotal} vectors from {self.INDEX_FILE}")
            except Exception as e:
                print(f"[RAG] WARNING: Could not load persisted index: {e}. Starting fresh.")
                self.index = faiss.IndexFlatL2(self.dimension)
                self.documents = []

    def save_index(self):
        """Write FAISS index and metadata to disk."""
        try:
            faiss.write_index(self.index, self.INDEX_FILE)
            with open(self.META_FILE, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[RAG] WARNING: Could not persist index: {e}")

    def clear_index(self):
        """Wipe the in-memory index and delete persisted files."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        for path in (self.INDEX_FILE, self.META_FILE):
            if os.path.exists(path):
                os.remove(path)
        print("[RAG] Index cleared.")

    # ── Text Extraction ───────────────────────────────────────────────────────

    def extract_text(self, filepath: str) -> str:
        ext = os.path.splitext(filepath)[1].lower()
        text = ""
        try:
            if ext == ".pdf":
                doc = fitz.open(filepath)
                for page in doc:
                    text += page.get_text() + "\n"
            elif ext == ".docx":
                doc = docx.Document(filepath)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            else:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
        except Exception as e:
            print(f"[RAG] Error reading {filepath}: {e}")
        return text

    # ── Chunking ──────────────────────────────────────────────────────────────

    def chunk_text(self, text: str, chunk_size: int = 200, overlap: int = 50) -> list[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest_file(self, filepath: str, chunk_size: int = 200, overlap: int = 50) -> int:
        """
        Extract, chunk, embed, and add a file to the index.
        Saves the index to disk after each successful ingest.

        Returns:
            Number of chunks added.
        """
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".csv":
            import csv
            chunks = []
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for row in reader:
                        if not row:
                            continue
                        if header and "Description" in header:
                            desc_idx = header.index("Description")
                            # Safely handle shorter rows
                            val = row[desc_idx] if desc_idx < len(row) else ", ".join(row)
                            chunks.append(val)
                        else:
                            chunks.append(", ".join(f"{h}: {v}" for h, v in zip(header, row) if v) if header else ", ".join(row))
            except Exception as e:
                print(f"[RAG] Error reading CSV {filepath}: {e}")
                return 0
        else:
            text = self.extract_text(filepath)
            if not text.strip():
                return 0
            chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        if not chunks:
            return 0

        embeddings = self.encoder.encode(chunks)
        self.index.add(np.array(embeddings).astype("float32"))

        source_file = os.path.basename(filepath)
        ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        start_id = len(self.documents)

        for i, chunk_text in enumerate(chunks):
            self.documents.append({
                "text": chunk_text,
                "source_file": source_file,
                "chunk_id": start_id + i,
                "ingested_at": ingested_at,
            })

        self.save_index()
        print(f"[RAG] Added {len(chunks)} chunks from {source_file}")
        return len(chunks)

    def ingest_text(self, text: str, source_name: str = "inline", chunk_size: int = 200, overlap: int = 50) -> int:
        """Ingest raw text string directly (no file needed). Useful for eval harness."""
        chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return 0

        embeddings = self.encoder.encode(chunks)
        self.index.add(np.array(embeddings).astype("float32"))

        ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        start_id = len(self.documents)

        for i, chunk_text in enumerate(chunks):
            self.documents.append({
                "text": chunk_text,
                "source_file": source_name,
                "chunk_id": start_id + i,
                "ingested_at": ingested_at,
            })
        # No save_index() here — transient ingest for eval use
        return len(chunks)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        source_filter: str | None = None,
        threshold: float = 0.0,
    ) -> list[str]:
        """
        Retrieve top-k chunks relevant to `query`.

        Args:
            query:         User query string.
            top_k:         Number of chunks to return.
            source_filter: If set, restrict results to chunks from this filename.
            threshold:     Max L2 distance. 0.0 = no filtering.

        Returns:
            List of text strings (with optional contextual headers prepended).
        """
        results = self.retrieve_with_metadata(
            query,
            top_k=top_k,
            source_filter=source_filter,
        )
        if threshold > 0.0:
            results = [r for r in results if r["distance"] <= threshold]

        formatted = []
        for r in results:
            text = r["text"]
            if self.contextual_headers:
                header = f"[Source: {r['source_file']} | Chunk {r['chunk_id']}]\n"
                text = header + text
            formatted.append(text)
        return formatted


    def retrieve_with_metadata(
        self,
        query: str,
        top_k: int = 3,
        source_filter: str | None = None,
    ) -> list[dict]:
        """
        Like retrieve() but returns full metadata dicts including distance scores.
        Used by benchmark_rag.py and retrieval eval metrics.
        """
        if self.index.ntotal == 0:
            return []

        # Hybrid Search: check if query wants to list/show all workers in a specific department
        exact_matches = []
        import re
        
        dept_match = None
        for dept in ["IT", "Finance", "Admin", "EVS", "Marketing"]:
            if re.search(r"\b" + re.escape(dept) + r"\b", query, re.IGNORECASE):
                # Check for listing indicator keywords
                if any(w in query.lower() for w in ["all", "list", "everyone", "who works", "workers in", "employees in", "show me", "people in"]):
                    dept_match = dept
                    break

        if dept_match:
            for doc in self.documents:
                if source_filter and doc.get("source_file") != source_filter:
                    continue
                if re.search(r"\b" + re.escape(dept_match) + r"\b", doc["text"], re.IGNORECASE):
                    exact_matches.append({
                        **doc,
                        "rank": 0,
                        "distance": 0.0,
                    })
            if exact_matches:
                return exact_matches

        # Alphanumeric ID matching
        id_tokens = re.findall(r"\b[A-Z0-9]{3,10}\b", query)
        for token in id_tokens:
            # Must contain both letters and numbers to be an ID/code
            if any(c.isalpha() for c in token) and any(c.isdigit() for c in token):
                for doc in self.documents:
                    if source_filter and doc.get("source_file") != source_filter:
                        continue
                    if re.search(r"\b" + re.escape(token) + r"\b", doc["text"]):
                        if not any(e["chunk_id"] == doc["chunk_id"] for e in exact_matches):
                            exact_matches.append({
                                **doc,
                                "rank": 0,
                                "distance": 0.0,
                            })

        # Run vector search
        query_vector = self.encoder.encode([query]).astype("float32")
        fetch_k = min(top_k * 5 if source_filter else top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vector, fetch_k)

        results = list(exact_matches)
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1 or idx >= len(self.documents):
                continue
            doc = self.documents[idx]
            if source_filter and doc.get("source_file") != source_filter:
                continue
            # Avoid duplicates of exact matches
            if any(e["chunk_id"] == doc["chunk_id"] for e in results):
                continue
            results.append({
                **doc,
                "rank": rank + len(exact_matches),
                "distance": float(dist),
            })
            if len(results) >= top_k:
                break

        return results[:top_k]

    # ── Retrieval Eval Metrics ─────────────────────────────────────────────────

    def eval_retrieval(
        self,
        query: str,
        expected_chunk_ids: list[int],
        top_k: int = 5,
    ) -> dict:
        """
        Measure retrieval quality for a single query.

        Args:
            query:              Query string.
            expected_chunk_ids: List of chunk_id values that count as relevant.
            top_k:              Evaluation cutoff.

        Returns:
            {
              "hit_at_1": bool,
              "hit_at_3": bool,
              "hit_at_k": bool,
              "reciprocal_rank": float,   # 1/rank of first hit, 0 if not found
              "retrieved_ids": list[int]
            }
        """
        retrieved = self.retrieve_with_metadata(query, top_k=top_k)
        retrieved_ids = [r["chunk_id"] for r in retrieved]
        expected_set = set(expected_chunk_ids)

        rr = 0.0
        for rank, cid in enumerate(retrieved_ids, 1):
            if cid in expected_set:
                rr = 1.0 / rank
                break

        return {
            "hit_at_1": bool(retrieved_ids[:1] and retrieved_ids[0] in expected_set),
            "hit_at_3": bool(any(cid in expected_set for cid in retrieved_ids[:3])),
            "hit_at_k": bool(any(cid in expected_set for cid in retrieved_ids)),
            "reciprocal_rank": round(rr, 4),
            "retrieved_ids": retrieved_ids,
        }

    # ── Convenience ───────────────────────────────────────────────────────────

    def list_sources(self) -> list[str]:
        """Return unique source filenames currently in the index."""
        seen = set()
        sources = []
        for doc in self.documents:
            sf = doc.get("source_file", "unknown")
            if sf not in seen:
                seen.add(sf)
                sources.append(sf)
        return sources

    @property
    def total_chunks(self) -> int:
        return len(self.documents)
