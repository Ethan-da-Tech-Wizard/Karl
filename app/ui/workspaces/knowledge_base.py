"""
Knowledge Base — RAG management workspace.

Left:  ingested sources tree + ingest controls
Right: chunk inspector + search tester
"""

from __future__ import annotations

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

    def __init__(self, rag, filepath: str):
        super().__init__()
        self.rag = rag
        self.filepath = filepath

    def run(self):
        try:
            n = self.rag.ingest_file(self.filepath)
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

        # stats row
        self._stats_lbl = QLabel("0 sources · 0 chunks")
        self._stats_lbl.setObjectName("lbl-muted")
        layout.addWidget(self._stats_lbl)

        # source list
        self._source_list = QListWidget()
        self._source_list.currentTextChanged.connect(self._on_source_selected)
        layout.addWidget(self._source_list, 1)

        # ingest controls
        layout.addWidget(_hline())
        layout.addWidget(_section("INGEST"))

        ingest_btn = QPushButton("+ add file")
        ingest_btn.setObjectName("btn-primary")
        ingest_btn.clicked.connect(self._ingest_file)
        layout.addWidget(ingest_btn)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)  # indeterminate
        layout.addWidget(self._progress)

        self._ingest_status = QLabel("")
        self._ingest_status.setObjectName("lbl-muted")
        self._ingest_status.setWordWrap(True)
        layout.addWidget(self._ingest_status)

        layout.addWidget(_hline())

        # retrieval threshold
        layout.addWidget(_section("RETRIEVAL"))

        thresh_row = QWidget()
        tr_layout = QHBoxLayout(thresh_row)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        tr_layout.setSpacing(8)
        tr_layout.addWidget(QLabel("threshold"))
        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.0, 2.0)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setValue(0.0)
        self._threshold_spin.setToolTip(
            "Max L2 distance. 0 = no filter (return all top-k)."
        )
        self._threshold_spin.setFixedWidth(80)
        tr_layout.addWidget(self._threshold_spin)
        tr_layout.addStretch()
        layout.addWidget(thresh_row)

        topk_row = QWidget()
        tk_layout = QHBoxLayout(topk_row)
        tk_layout.setContentsMargins(0, 0, 0, 0)
        tk_layout.setSpacing(8)
        tk_layout.addWidget(QLabel("top-k"))
        self._topk_spin = QSpinBox()
        self._topk_spin.setRange(1, 20)
        self._topk_spin.setValue(3)
        self._topk_spin.setFixedWidth(80)
        tk_layout.addWidget(self._topk_spin)
        tk_layout.addStretch()
        layout.addWidget(topk_row)

        # danger zone
        layout.addStretch()
        layout.addWidget(_hline())
        clear_btn = QPushButton("clear index")
        clear_btn.setObjectName("btn-danger")
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
        self._search_input.returnPressed.connect(self._run_search)
        sr_layout.addWidget(self._search_input, 1)
        search_btn = QPushButton("search")
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
        lines = [f"— {source} — {len(docs)} chunks\n"]
        for i, d in enumerate(docs[:20]):
            lines.append(f"[{d['chunk_id']}]  {d['text'][:160]}{'...' if len(d['text']) > 160 else ''}\n")
        if len(docs) > 20:
            lines.append(f"\n...and {len(docs) - 20} more chunks.")
        self._search_results.setPlainText("".join(lines))

    def _ingest_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add File to Knowledge Base", "",
            "Documents (*.pdf *.docx *.txt *.md *.py *.csv);;All Files (*)"
        )
        if not path:
            return
        self._progress.setVisible(True)
        self._ingest_status.setText("ingesting...")
        self._ingest_thread = _IngestThread(self.state.rag, path)
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
            self._search_results.setPlainText("Knowledge base is empty.")
            return

        top_k = self._topk_spin.value()
        results = self.state.rag.retrieve_with_metadata(query, top_k=top_k)

        threshold = self._threshold_spin.value()
        if threshold > 0:
            results = [r for r in results if r["distance"] <= threshold]

        if not results:
            self._search_results.setPlainText(
                f"No results above threshold {threshold:.2f} for: {query}"
            )
            return

        lines = [f"query: {query}\n{len(results)} results\n\n"]
        for r in results:
            lines.append(
                f"[{r['chunk_id']}] {r['source_file']}  dist={r['distance']:.4f}\n"
                f"{r['text'][:300]}{'...' if len(r['text']) > 300 else ''}\n\n"
            )
        self._search_results.setPlainText("".join(lines))

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
