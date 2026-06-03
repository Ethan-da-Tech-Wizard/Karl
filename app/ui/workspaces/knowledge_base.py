"""
Knowledge Base — RAG management workspace.

Left:  ingested sources tree + ingest controls
Right: chunk inspector + search tester
"""

from __future__ import annotations

import html
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QFileDialog,
    QSpinBox, QDoubleSpinBox, QFrame, QProgressBar,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


# ── background ingest thread ──────────────────────────────────────────────────

class _IngestThread(QThread):
    done = pyqtSignal(str, int)   # filename, chunk_count
    error = pyqtSignal(str)

    def __init__(self, rag, filepath: str, chunk_size: int = 200, overlap: int = 50):
        super().__init__()
        self.rag = rag
        self.filepath = filepath
        self.chunk_size = chunk_size
        self.overlap = overlap

    def run(self):
        try:
            n = self.rag.ingest_file(self.filepath, chunk_size=self.chunk_size, overlap=self.overlap)
            import os
            self.done.emit(os.path.basename(self.filepath), n)
        except Exception as e:
            self.error.emit(str(e))


# ── workspace ─────────────────────────────────────────────────────────────────

class KnowledgeBaseWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._active_threads = set()
        self._build_ui()
        self._refresh_sources()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        root.addWidget(splitter)

    # ── left panel ────────────────────────────────────────────────────────────

    def _build_left(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(_section("KNOWLEDGE BASE"))

        desc = QLabel(
            "Manage documents and search indexes. Files are ingested, chunked, "
            "embedded, and stored in a local vector database for Retrieval-Augmented Generation (RAG)."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px;")
        layout.addWidget(desc)

        # stats row
        self._stats_lbl = QLabel("0 sources · 0 chunks")
        self._stats_lbl.setObjectName("lbl-muted")
        layout.addWidget(self._stats_lbl)

        # source list
        self._source_list = QListWidget()
        self._source_list.currentTextChanged.connect(self._on_source_selected)
        layout.addWidget(self._source_list, 1)

        # Ingest container
        layout.addWidget(_hline())
        layout.addWidget(_section("INGEST"))

        ingest_box = QWidget()
        ingest_box.setObjectName("panel")
        ib_layout = QVBoxLayout(ingest_box)
        ib_layout.setContentsMargins(10, 10, 10, 10)
        ib_layout.setSpacing(10)

        # Chunk size & overlap row
        chunk_row = QWidget()
        chunk_layout = QHBoxLayout(chunk_row)
        chunk_layout.setContentsMargins(0, 0, 0, 0)
        chunk_layout.setSpacing(6)

        chunk_layout.addWidget(QLabel("size"))
        self._chunk_size_spin = QSpinBox()
        self._chunk_size_spin.setRange(50, 2000)
        self._chunk_size_spin.setSingleStep(50)
        self._chunk_size_spin.setValue(200)
        self._chunk_size_spin.setFixedWidth(65)
        self._chunk_size_spin.setToolTip("Size of text chunks in words")
        chunk_layout.addWidget(self._chunk_size_spin)

        chunk_layout.addSpacing(5)

        chunk_layout.addWidget(QLabel("overlap"))
        self._overlap_spin = QSpinBox()
        self._overlap_spin.setRange(0, 1000)
        self._overlap_spin.setSingleStep(10)
        self._overlap_spin.setValue(50)
        self._overlap_spin.setFixedWidth(60)
        self._overlap_spin.setToolTip("Number of overlapping words between consecutive chunks")
        chunk_layout.addWidget(self._overlap_spin)
        chunk_layout.addStretch()
        ib_layout.addWidget(chunk_row)

        # Add file button
        ingest_btn = QPushButton("+ add file")
        ingest_btn.setObjectName("btn-primary")
        ingest_btn.setToolTip("Extract text and split it into vector chunks to load into knowledge base")
        ingest_btn.clicked.connect(self._ingest_file)
        ib_layout.addWidget(ingest_btn)

        # Progress indicator
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)  # indeterminate
        ib_layout.addWidget(self._progress)

        # Status text
        self._ingest_status = QLabel("")
        self._ingest_status.setObjectName("lbl-muted")
        self._ingest_status.setWordWrap(True)
        ib_layout.addWidget(self._ingest_status)

        layout.addWidget(ingest_box)
        layout.addWidget(_hline())

        # Retrieval settings row
        layout.addWidget(_section("RETRIEVAL"))

        ret_row = QWidget()
        ret_layout = QHBoxLayout(ret_row)
        ret_layout.setContentsMargins(0, 4, 0, 4)
        ret_layout.setSpacing(8)

        ret_layout.addWidget(QLabel("threshold"))
        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.0, 2.0)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setValue(self.state.rag_threshold)
        self._threshold_spin.setToolTip(
            "Maximum L2 distance score for retrieved chunks. Lower is more relevant."
        )
        self._threshold_spin.setFixedWidth(65)
        self._threshold_spin.valueChanged.connect(self._on_threshold_changed)
        ret_layout.addWidget(self._threshold_spin)

        ret_layout.addSpacing(10)

        ret_layout.addWidget(QLabel("top-k"))
        self._topk_spin = QSpinBox()
        self._topk_spin.setRange(1, 20)
        self._topk_spin.setValue(self.state.rag_top_k)
        self._topk_spin.setToolTip("Number of relevant context chunks to retrieve")
        self._topk_spin.setFixedWidth(50)
        self._topk_spin.valueChanged.connect(self._on_topk_changed)
        ret_layout.addWidget(self._topk_spin)

        ret_layout.addStretch()
        layout.addWidget(ret_row)

        # danger zone
        layout.addStretch()
        layout.addWidget(_hline())
        clear_btn = QPushButton("clear index")
        clear_btn.setObjectName("btn-danger")
        clear_btn.setToolTip("Wipe the vector database index and documents metadata")
        clear_btn.clicked.connect(self._clear_index)
        layout.addWidget(clear_btn)
        return w

    # ── right panel ───────────────────────────────────────────────────────────

    def _build_right(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(_section("SEARCH TEST"))

        search_row = QWidget()
        sr_layout = QHBoxLayout(search_row)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.setSpacing(8)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Enter query to test retrieval...")
        self._search_input.setToolTip("Enter a search query to test retrieval relevance")
        self._search_input.returnPressed.connect(self._run_search)
        sr_layout.addWidget(self._search_input, 1)
        search_btn = QPushButton("search")
        search_btn.setToolTip("Query the vector database for matching chunks")
        search_btn.clicked.connect(self._run_search)
        sr_layout.addWidget(search_btn)
        layout.addWidget(search_row)

        self._search_results = QTextBrowser()
        self._search_results.setPlaceholderText(
            "Search results and chunk inspector will appear here."
        )
        layout.addWidget(self._search_results, 1)

        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _refresh_sources(self):
        self._source_list.clear()
        sources = self.state.rag.list_sources()
        for s in sources:
            self._source_list.addItem(s)
        total = self.state.rag.total_chunks
        self._stats_lbl.setText(f"{len(sources)} sources · {total} chunks")

    def _on_source_selected(self, source: str):
        if not source:
            return
        docs = [
            d for d in self.state.rag.documents
            if d.get("source_file") == source
        ]
        lines = [
            f"<div style='font-size:11pt;color:#00C2FF;font-weight:bold;margin-bottom:4px;'>Source: {html.escape(source)}</div>"
            f"<div style='font-size:9pt;color:#9090A8;margin-bottom:12px;'>Total {len(docs)} chunks ingested</div>"
        ]
        for d in docs[:20]:
            lines.append(
                f"<div style='background:#14141F;border:1px solid #252535;border-radius:4px;padding:8px;margin-bottom:8px;'>"
                f"<div style='font-size:8.5pt;color:#9090A8;margin-bottom:4px;font-weight:bold;'>Chunk {d['chunk_id']}</div>"
                f"<div style='font-size:9.5pt;color:#E4E4F0;white-space:pre-wrap;'>{html.escape(d['text'][:250])}{'...' if len(d['text']) > 250 else ''}</div>"
                f"</div>"
            )
        if len(docs) > 20:
            lines.append(f"<div style='font-size:9pt;color:#505068;text-align:center;margin-top:8px;'>...and {len(docs) - 20} more chunks.</div>")
            
        self._search_results.setHtml("".join(lines))

    def _ingest_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add File to Knowledge Base", "",
            "Documents (*.pdf *.docx *.txt *.md *.py *.csv);;All Files (*)"
        )
        if not path:
            return
        self._progress.setVisible(True)
        self._ingest_status.setText("ingesting...")
        self._ingest_thread = _IngestThread(
            self.state.rag,
            path,
            chunk_size=self._chunk_size_spin.value(),
            overlap=self._overlap_spin.value()
        )
        self._active_threads.add(self._ingest_thread)
        self._ingest_thread.finished.connect(
            lambda t=self._ingest_thread: self._active_threads.discard(t)
        )
        self._ingest_thread.finished.connect(self._ingest_thread.deleteLater)
        self._ingest_thread.done.connect(self._on_ingest_done)
        self._ingest_thread.error.connect(self._on_ingest_error)
        self._ingest_thread.start()

    def _on_ingest_done(self, filename: str, count: int):
        self._progress.setVisible(False)
        self._ingest_status.setText(f"added {count} chunks from {filename}")
        self._refresh_sources()

    def _on_ingest_error(self, msg: str):
        self._progress.setVisible(False)
        self._ingest_status.setText(f"error: {msg}")

    def _run_search(self):
        query = self._search_input.text().strip()
        if not query:
            return
        if self.state.rag.total_chunks == 0:
            self._search_results.setHtml("<div style='color:#F05050;'>Knowledge base is empty.</div>")
            return

        top_k = self._topk_spin.value()
        results = self.state.rag.retrieve_with_metadata(query, top_k=top_k)

        threshold = self._threshold_spin.value()
        if threshold > 0:
            results = [r for r in results if r["distance"] <= threshold]

        if not results:
            self._search_results.setHtml(
                f"<div style='color:#9090A8;'>No results found below distance threshold <b>{threshold:.2f}</b> for query: <i>{html.escape(query)}</i></div>"
            )
            return

        lines = [
            f"<div style='font-size:11pt;color:#00C2FF;font-weight:bold;margin-bottom:4px;'>Search Results for: <i>{html.escape(query)}</i></div>"
            f"<div style='font-size:9pt;color:#9090A8;margin-bottom:12px;'>Found {len(results)} chunks:</div>"
        ]
        for r in results:
            lines.append(
                f"<div style='background:#14141F;border:1px solid #252535;border-radius:4px;padding:10px;margin-bottom:10px;'>"
                f"<div style='font-size:8.5pt;color:#9090A8;margin-bottom:4px;font-weight:bold;'>"
                f"Chunk {r['chunk_id']} &middot; {r['source_file']} &middot; <span style='color:#F0B030;'>dist={r['distance']:.4f}</span>"
                f"</div>"
                f"<div style='font-size:9.5pt;color:#E4E4F0;white-space:pre-wrap;line-height:1.4;'>{html.escape(r['text'])}</div>"
                f"</div>"
            )
        self._search_results.setHtml("".join(lines))

    def _clear_index(self):
        reply = QMessageBox.question(
            self, "Clear index",
            "This permanently deletes the vector index and all ingested data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.state.rag.clear_index()
            self._refresh_sources()
            self._search_results.clear()
            self._ingest_status.setText("index cleared")

    def _on_threshold_changed(self, val):
        self.state.rag_threshold = val

    def _on_topk_changed(self, val):
        self.state.rag_top_k = val

