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
        self.model_name = model_name
        self.index_path = index_path
        self.contextual_headers = contextual_headers
        self._encoder = None
        self._index = None
        self.dimension = 384  # Default for all-MiniLM-L6-v2, updated when encoder loads

        os.makedirs(self.index_path, exist_ok=True)

        # Load metadata only on startup (fast, no heavy imports needed)
        self.documents: list[dict] = []
        self._load_metadata()

    @property
    def encoder(self):
        self._ensure_initialized()
        return self._encoder

    @encoder.setter
    def encoder(self, value):
        self._encoder = value

    @property
    def index(self):
        self._ensure_initialized()
        return self._index

    @index.setter
    def index(self, value):
        self._index = value

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_metadata(self):
        """Load document metadata from disk if it exists."""
        if os.path.exists(self.META_FILE):
            try:
                with open(self.META_FILE, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception as e:
                print(f"[RAG] WARNING: Could not load metadata: {e}")
                self.documents = []

    def _ensure_initialized(self):
        """Lazy load SentenceTransformer model and FAISS index if not already loaded."""
        if self._encoder is None:
            import io
            import contextlib
            from sentence_transformers import SentenceTransformer
            _sink = io.StringIO()
            with contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
                self._encoder = SentenceTransformer(self.model_name)
            self.dimension = self._encoder.get_embedding_dimension()

            # Load or initialize the FAISS index
            if os.path.exists(self.INDEX_FILE):
                try:
                    self._index = faiss.read_index(self.INDEX_FILE)
                    print(f"[RAG] Loaded {self._index.ntotal} vectors from {self.INDEX_FILE}")
                except Exception as e:
                    print(f"[RAG] WARNING: Could not load persisted index: {e}. Starting fresh.")
                    self._index = faiss.IndexFlatL2(self.dimension)
            else:
                self._index = faiss.IndexFlatL2(self.dimension)

    def _load_index(self):
        """Legacy compatibility wrapper."""
        self._ensure_initialized()

    def save_index(self):
        """Write FAISS index and metadata to disk."""
        self._ensure_initialized()
        try:
            faiss.write_index(self._index, self.INDEX_FILE)
            with open(self.META_FILE, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[RAG] WARNING: Could not persist index: {e}")

    def clear_index(self):
        """Wipe the in-memory index and delete persisted files."""
        if self._encoder is not None:
            self._index = faiss.IndexFlatL2(self.dimension)
        else:
            self._index = None
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

            elif ext in (".xlsx", ".xls"):
                text = self._extract_spreadsheet(filepath, ext)

            else:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

        except Exception as e:
            print(f"[RAG] Error reading {filepath}: {e}")
        return text

    def _extract_spreadsheet(self, filepath: str, ext: str) -> str:
        """
        Convert an Excel workbook to readable plain text.
        Each row becomes "Column: Value  |  Column: Value  ..." so
        the model can reason over structured data.
        Returns empty string (and logs a warning) if openpyxl / xlrd
        are not installed.
        """
        lines = []
        try:
            if ext == ".xlsx":
                try:
                    import openpyxl
                except ImportError:
                    print("[RAG] openpyxl not installed. Run: pip install openpyxl")
                    return ""
                wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
                for sheet in wb.worksheets:
                    lines.append(f"[Sheet: {sheet.title}]")
                    rows = list(sheet.iter_rows(values_only=True))
                    if not rows:
                        continue
                    # First row = headers
                    headers = [str(h).strip() if h is not None else f"Col{i}" for i, h in enumerate(rows[0])]
                    for row in rows[1:]:
                        if all(v is None for v in row):
                            continue
                        parts = []
                        for h, v in zip(headers, row):
                            if v is not None:
                                parts.append(f"{h}: {v}")
                        if parts:
                            lines.append("  |  ".join(parts))
                wb.close()

            elif ext == ".xls":
                try:
                    import xlrd
                except ImportError:
                    print("[RAG] xlrd not installed. Run: pip install xlrd")
                    return ""
                wb = xlrd.open_workbook(filepath)
                for sheet in wb.sheets():
                    lines.append(f"[Sheet: {sheet.name}]")
                    if sheet.nrows == 0:
                        continue
                    headers = [str(sheet.cell_value(0, c)).strip() or f"Col{c}" for c in range(sheet.ncols)]
                    for r in range(1, sheet.nrows):
                        parts = []
                        for c, h in enumerate(headers):
                            v = sheet.cell_value(r, c)
                            if v != "":
                                parts.append(f"{h}: {v}")
                        if parts:
                            lines.append("  |  ".join(parts))

        except Exception as e:
            print(f"[RAG] Spreadsheet read error ({filepath}): {e}")
            return ""

        return "\n".join(lines)

    # ── Chunking ──────────────────────────────────────────────────────────────

    def chunk_text(self, text: str, chunk_size: int = 200, overlap: int = 50) -> list[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def chunk_rows(self, text: str, rows_per_chunk: int = 15, overlap_rows: int = 2) -> list[str]:
        """
        Row-aware chunking for tabular data (spreadsheets, CSVs).
        Groups rows_per_chunk lines together with a small row overlap.
        Preserves header lines (lines starting with '[') across every chunk.
        """
        all_lines = [line for line in text.split("\n") if line.strip()]
        # Separate sheet-header lines (e.g. "[Sheet: Sheet1]") from data rows
        header_lines = [line for line in all_lines if line.startswith("[")]
        data_lines   = [line for line in all_lines if not line.startswith("[")]

        if not data_lines:
            return [text] if text.strip() else []

        header_prefix = "\n".join(header_lines) + "\n" if header_lines else ""
        chunks = []
        step = max(1, rows_per_chunk - overlap_rows)
        for i in range(0, len(data_lines), step):
            row_block = data_lines[i : i + rows_per_chunk]
            chunk = header_prefix + "\n".join(row_block)
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
        print(f"[RAG] Ingesting {filepath}...")
        text = self.extract_text(filepath)
        if not text.strip():
            print(f"[RAG] No text extracted from {filepath} — check format/encoding.")
            return 0

        # Tabular files get row-aware chunking so each chunk covers a small,
        # specific set of rows — critical for exact-lookup queries.
        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".xlsx", ".xls", ".csv"):
            chunks = self.chunk_rows(text, rows_per_chunk=15, overlap_rows=2)
        else:
            chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return 0

        self._ensure_initialized()
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

        self._ensure_initialized()
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
    ) -> list[str]:
        """
        Hybrid retrieval: semantic search (FAISS) + keyword re-ranking.

        Steps:
          1. Over-fetch top_k × 4 candidates via FAISS cosine/L2 similarity.
          2. Score each candidate by keyword overlap with the query.
          3. Re-rank: keyword-matching chunks bubble to the top.
          4. Return the best top_k results.

        This makes exact lookups (e.g. "EMP-0001", "employee 1", "IT") accurate
        even when pure semantic similarity would miss the right chunk.
        """
        self._ensure_initialized()
        if self.index.ntotal == 0:
            return []

        query_vector = self.encoder.encode([query]).astype("float32")

        # Over-fetch: more candidates = better chance of keyword hits
        # Also over-fetch when source_filter is set so filtering has enough to work with
        base_fetch = top_k * 4
        fetch_k = min(base_fetch * 5 if source_filter else base_fetch, self.index.ntotal)
        distances, indices = self.index.search(query_vector, fetch_k)

        # Build candidate list in FAISS-rank order
        candidates = []
        for rank, i in enumerate(indices[0]):
            if i == -1 or i >= len(self.documents):
                continue
            doc = self.documents[i]
            if source_filter and doc.get("source_file") != source_filter:
                continue
            candidates.append((rank, doc))

        # Keyword re-ranking --------------------------------------------------
        # Tokenise the query into meaningful terms (skip very short stop words)
        _STOPWORDS = {"a", "an", "the", "is", "in", "of", "to", "do", "for",
                      "and", "or", "what", "how", "many", "does", "work",
                      "which", "who", "where", "this", "that", "my", "their"}
        query_terms = [
            t for t in query.lower().split()
            if t not in _STOPWORDS and len(t) > 1
        ]

        def keyword_score(text: str) -> int:
            tl = text.lower()
            score = 0
            for term in query_terms:
                # Exact substring hit
                if term in tl:
                    score += 2
                # Partial hit (e.g. "emp" matching "emp-0001")
                elif any(term in word for word in tl.split()):
                    score += 1
            return score

        # Sort by (-keyword_score, original_faiss_rank) so high-overlap chunks
        # come first, ties broken by semantic relevance.
        candidates.sort(key=lambda x: (-keyword_score(x[1]["text"]), x[0]))
        # ---------------------------------------------------------------------

        results = []
        for _, doc in candidates:
            text = doc["text"]
            if self.contextual_headers:
                header = f"[Source: {doc['source_file']} | Chunk {doc['chunk_id']}]\n"
                text = header + text
            results.append(text)
            if len(results) >= top_k:
                break

        return results

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
        self._ensure_initialized()
        if self.index.ntotal == 0:
            return []

        query_vector = self.encoder.encode([query]).astype("float32")
        fetch_k = min(top_k * 5 if source_filter else top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vector, fetch_k)

        results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1 or idx >= len(self.documents):
                continue
            doc = self.documents[idx]
            if source_filter and doc.get("source_file") != source_filter:
                continue
            results.append({
                **doc,
                "rank": rank,
                "distance": float(dist),
            })
            if len(results) >= top_k:
                break

        return results

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
