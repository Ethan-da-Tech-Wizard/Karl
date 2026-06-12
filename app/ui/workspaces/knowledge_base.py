"""
Knowledge Base — RAG management workspace.

Left:  ingested sources tree + ingest controls
Right: chunk inspector + search tester
"""

from __future__ import annotations

import html
import os

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QFileDialog,
    QSpinBox, QDoubleSpinBox, QFrame, QProgressBar,
    QMessageBox, QTabWidget,
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


def _label(text: str, obj: str = "") -> QLabel:
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
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
        self._load_rag_config()
        self._active_threads = set()
        self._ingest_queue = []
        self._build_ui()
        self._refresh_sources()
        self._update_encoder_status()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Title
        title_row = QWidget()
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Knowledge Base")
        lbl.setObjectName("lbl-accent")
        lbl.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        tr.addWidget(lbl)
        tr.addStretch()
        
        # Lazy model loader indicator
        self._model_status_lbl = QLabel("Encoder: Not loaded")
        self._model_status_lbl.setObjectName("lbl-muted")
        tr.addWidget(self._model_status_lbl)
        
        self._preload_btn = QPushButton("Preload")
        self._preload_btn.setObjectName("btn-ghost")
        self._preload_btn.setStyleSheet("font-size: 8pt; padding: 2px 6px;")
        self._preload_btn.clicked.connect(self._preload_encoder)
        tr.addWidget(self._preload_btn)
        
        tr.addWidget(_label("|", "lbl-muted"))

        self._health_lbl = QLabel("Index Health: Healthy")
        self._health_lbl.setObjectName("lbl-muted")
        tr.addWidget(self._health_lbl)
        
        tr.addWidget(_label("|", "lbl-muted"))

        self._stats_lbl = QLabel("0 sources · 0 chunks")
        self._stats_lbl.setObjectName("lbl-muted")
        tr.addWidget(self._stats_lbl)
        root.addWidget(title_row)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_explorer_tab(), "Index Explorer")
        self._tabs.addTab(self._build_ingest_tab(), "Ingestion Hub")
        self._tabs.addTab(self._build_search_tab(), "Semantic Search")
        root.addWidget(self._tabs, 1)


    def _build_explorer_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left panel: list of sources + clear database
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)
        ll.addWidget(_section("SOURCES"))

        self._source_list = QListWidget()
        self._source_list.currentTextChanged.connect(self._on_source_selected)
        self._source_list.setToolTip("Select a source document to inspect its ingested chunks")
        ll.addWidget(self._source_list, 1)

        self._remove_btn = QPushButton("remove selected source")
        self._remove_btn.setObjectName("btn-warning")
        self._remove_btn.setToolTip("Remove selected source chunks and rebuild search index")
        self._remove_btn.clicked.connect(self._remove_selected_source)
        ll.addWidget(self._remove_btn)

        self._rebuild_btn = QPushButton("rebuild index")
        self._rebuild_btn.setObjectName("btn-ghost")
        self._rebuild_btn.setToolTip("Re-encode all chunks in the vector database index")
        self._rebuild_btn.clicked.connect(self._rebuild_index)
        ll.addWidget(self._rebuild_btn)

        clear_btn = QPushButton("clear database")
        clear_btn.setObjectName("btn-danger")
        clear_btn.setToolTip("Wipe the vector database index and all ingested document text")
        clear_btn.clicked.connect(self._clear_index)
        ll.addWidget(clear_btn)

        splitter.addWidget(left)

        # Right panel: chunk inspector
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(_section("CHUNK INSPECTOR"))

        self._source_inspector = QTextBrowser()
        self._source_inspector.setPlaceholderText("Select a source document to inspect its chunks here...")
        rl.addWidget(self._source_inspector, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
        return w

    def _build_ingest_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        layout.addWidget(_section("DOCUMENT INGESTION"))
        
        desc = QLabel(
            "Extract text from local files (PDF, DOCX, TXT, MD, PY, CSV), split into overlapping "
            "semantic chunks, compute sentence embeddings, and store them in the local vector DB."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        ingest_box = QWidget()
        ingest_box.setObjectName("panel")
        ib_layout = QVBoxLayout(ingest_box)
        ib_layout.setContentsMargins(16, 16, 16, 16)
        ib_layout.setSpacing(14)

        # Chunk parameters grid
        chunk_grid = QHBoxLayout()
        chunk_grid.setContentsMargins(0, 0, 0, 0)
        chunk_grid.setSpacing(12)

        chunk_grid.addWidget(QLabel("Chunk Size (words):"))
        self._chunk_size_spin = QSpinBox()
        self._chunk_size_spin.setRange(50, 2000)
        self._chunk_size_spin.setSingleStep(50)
        self._chunk_size_spin.setValue(200)
        self._chunk_size_spin.setFixedWidth(100)
        self._chunk_size_spin.setToolTip("Target size of each text chunk in words")
        chunk_grid.addWidget(self._chunk_size_spin)

        chunk_grid.addWidget(QLabel("Overlap (words):"))
        self._overlap_spin = QSpinBox()
        self._overlap_spin.setRange(0, 1000)
        self._overlap_spin.setSingleStep(10)
        self._overlap_spin.setValue(50)
        self._overlap_spin.setFixedWidth(100)
        self._overlap_spin.setToolTip("Overlapping words between consecutive text segments")
        chunk_grid.addWidget(self._overlap_spin)
        chunk_grid.addStretch()

        ib_layout.addLayout(chunk_grid)

        # Ingest Action button
        ingest_btn = QPushButton("+ Select and Ingest Document(s)")
        ingest_btn.setObjectName("btn-primary")
        ingest_btn.setFixedHeight(36)
        ingest_btn.setToolTip("Browse and choose files to ingest into the Knowledge Base")
        ingest_btn.clicked.connect(self._ingest_file)
        ib_layout.addWidget(ingest_btn)

        # Batch Queue List widget
        ib_layout.addWidget(QLabel("Ingestion Queue:"))
        self._queue_list = QListWidget()
        self._queue_list.setStyleSheet(
            "background-color: #0D0D1B; border: 1px solid #1F1F3D; border-radius: 4px; "
            "color: #F0F5FF; font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; padding: 4px;"
        )
        self._queue_list.setFixedHeight(120)
        ib_layout.addWidget(self._queue_list)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)  # indeterminate
        ib_layout.addWidget(self._progress)

        # Ingest Status Label
        self._ingest_status = QLabel("")
        self._ingest_status.setObjectName("lbl-mid")
        self._ingest_status.setWordWrap(True)
        ib_layout.addWidget(self._ingest_status)

        layout.addWidget(ingest_box)
        layout.addStretch()
        return w

    def _build_search_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(_section("SEMANTIC RETRIEVAL TESTER"))

        # Parameters row
        params_row = QWidget()
        pl = QHBoxLayout(params_row)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(16)

        pl.addWidget(QLabel("Distance Threshold:"))
        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.0, 2.0)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setValue(self.state.rag_threshold)
        self._threshold_spin.setFixedWidth(80)
        self._threshold_spin.setToolTip("Max L2 distance allowed for search results (lower is tighter/more relevant)")
        self._threshold_spin.valueChanged.connect(self._on_threshold_changed)
        pl.addWidget(self._threshold_spin)

        pl.addWidget(QLabel("Retrieve Top-K Chunks:"))
        self._topk_spin = QSpinBox()
        self._topk_spin.setRange(1, 20)
        self._topk_spin.setValue(self.state.rag_top_k)
        self._topk_spin.setFixedWidth(70)
        self._topk_spin.setToolTip("Maximum number of relevant chunks to retrieve")
        self._topk_spin.valueChanged.connect(self._on_topk_changed)
        pl.addWidget(self._topk_spin)
        pl.addStretch()
        layout.addWidget(params_row)

        # Search Bar
        search_row = QWidget()
        sr = QHBoxLayout(search_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Type a query and press enter to test vector search...")
        self._search_input.returnPressed.connect(self._run_search)
        sr.addWidget(self._search_input, 1)

        search_btn = QPushButton("Search Index")
        search_btn.setObjectName("btn-primary")
        search_btn.clicked.connect(self._run_search)
        sr.addWidget(search_btn)

        self._send_to_workbench_btn = QPushButton("Send to Workbench")
        self._send_to_workbench_btn.setObjectName("btn-ghost")
        self._send_to_workbench_btn.setToolTip("Switch to Workbench workspace and paste this query")
        self._send_to_workbench_btn.clicked.connect(self._send_query_to_workbench)
        sr.addWidget(self._send_to_workbench_btn)

        layout.addWidget(search_row)

        # Search results view
        self._search_results = QTextBrowser()
        self._search_results.setPlaceholderText("Search query results will be rendered here with distances and file references...")
        layout.addWidget(self._search_results, 1)

        return w


    # ── logic ─────────────────────────────────────────────────────────────────

    def _update_encoder_status(self):
        loaded = self.state.rag.is_encoder_loaded
        self._model_status_lbl.setText(f"Encoder: {'Ready' if loaded else 'Lazy-loaded (Not loaded)'}")
        self._model_status_lbl.setStyleSheet(f"color: {'#00C2FF' if loaded else '#9090A8'}; font-weight: bold;")
        self._preload_btn.setEnabled(not loaded)

    def _preload_encoder(self):
        self._model_status_lbl.setText("Encoder: Loading...")
        self._preload_btn.setEnabled(False)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        try:
            self.state.rag.preload_encoder()
            self._update_encoder_status()
        except Exception as e:
            self._model_status_lbl.setText(f"Encoder Error: {e}")

    def _update_health_lbl(self):
        index_file = self.state.rag.INDEX_FILE
        meta_file = self.state.rag.META_FILE
        index_size_kb = 0
        meta_size_kb = 0
        if os.path.exists(index_file):
            index_size_kb = os.path.getsize(index_file) / 1024
        if os.path.exists(meta_file):
            meta_size_kb = os.path.getsize(meta_file) / 1024
        total_chunks = self.state.rag.total_chunks
        status = "Healthy" if total_chunks > 0 and index_size_kb > 0 else "Empty"
        self._health_lbl.setText(f"Health: {status} ({index_size_kb:.1f}KB)")

    def _refresh_sources(self):
        self._source_list.clear()
        sources = self.state.rag.list_sources()
        for s in sources:
            self._source_list.addItem(s)
        total = self.state.rag.total_chunks
        self._stats_lbl.setText(f"{len(sources)} sources · {total} chunks")
        self._update_health_lbl()

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
                f"<div style='background:#141424;border:1px solid #28283f;border-radius:6px;padding:12px;margin-bottom:12px;'>"
                f"<div style='font-size:8.5pt;color:#9090A8;margin-bottom:6px;font-weight:bold;'>Chunk {d['chunk_id']}</div>"
                f"<div style='font-size:9.5pt;color:#ECECF5;white-space:pre-wrap;line-height:1.5;'>{html.escape(d['text'][:250])}{'...' if len(d['text']) > 250 else ''}</div>"
                f"</div>"
            )
        if len(docs) > 20:
            lines.append(f"<div style='font-size:9pt;color:#505068;text-align:center;margin-top:8px;'>...and {len(docs) - 20} more chunks.</div>")
            
        self._source_inspector.setHtml("".join(lines))

    def _ingest_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add File(s) to Knowledge Base", "",
            "Documents (*.pdf *.docx *.txt *.md *.py *.csv);;All Files (*)"
        )
        if not paths:
            return
            
        self._ingest_queue = [{"path": p, "status": "Pending", "error": ""} for p in paths]
        self._update_queue_ui()
        self._process_next_in_queue()

    def _update_queue_ui(self):
        self._queue_list.clear()
        for item in self._ingest_queue:
            fname = os.path.basename(item["path"])
            status = item["status"]
            err = f" - {item['error']}" if item["error"] else ""
            self._queue_list.addItem(f"[{status}] {fname}{err}")

    def _process_next_in_queue(self):
        next_item = None
        for item in self._ingest_queue:
            if item["status"] == "Pending":
                next_item = item
                break
                
        if not next_item:
            self._progress.setVisible(False)
            self._ingest_status.setText("All files processed.")
            self._refresh_sources()
            self._update_encoder_status()
            return
            
        next_item["status"] = "Ingesting"
        self._update_queue_ui()
        
        path = next_item["path"]
        filename = os.path.basename(path)
        self._ingest_status.setText(f"Ingesting {filename}...")
        self._progress.setVisible(True)
        
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
        
        def on_done(filename, count):
            next_item["status"] = "Done"
            self._update_queue_ui()
            self._process_next_in_queue()
            
        def on_error(msg):
            next_item["status"] = "Failed"
            next_item["error"] = msg
            self._update_queue_ui()
            self._process_next_in_queue()
            
        self._ingest_thread.done.connect(on_done)
        self._ingest_thread.error.connect(on_error)
        self._ingest_thread.start()

    def _remove_selected_source(self):
        curr_source = self._source_list.currentItem()
        if not curr_source:
            QMessageBox.warning(self, "No Selection", "Please select a source to remove.")
            return
        source_name = curr_source.text()
        
        reply = QMessageBox.question(
            self, "Remove Source",
            f"Are you sure you want to remove all chunks for '{source_name}' and rebuild the search index?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.state.rag.remove_source(source_name)
            self._refresh_sources()
            self._source_inspector.clear()
            self._search_results.clear()

    def _rebuild_index(self):
        reply = QMessageBox.question(
            self, "Rebuild Index",
            "This will re-encode all chunks in metadata. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._ingest_status.setText("Rebuilding index...")
            self._progress.setVisible(True)
            # Disable the trigger so a second click cannot re-enter while
            # processEvents pumps the queue during the rebuild.
            self._rebuild_btn.setEnabled(False)
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            try:
                self.state.rag.rebuild_index()
                self._refresh_sources()
                self._ingest_status.setText("Index rebuilt successfully.")
            except Exception as e:
                self._ingest_status.setText(f"Rebuild error: {e}")
            finally:
                self._progress.setVisible(False)
                self._rebuild_btn.setEnabled(True)

    def _send_query_to_workbench(self):
        query = self._search_input.text().strip()
        if not query:
            return
        main_win = self.window()
        if main_win and hasattr(main_win, "_sidebar") and hasattr(main_win, "_workbench"):
            main_win._sidebar.select(0)
            main_win._workbench._input.setPlainText(query)
            main_win._workbench._input.setFocus()


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
            dist = r["distance"]
            dist_color = "#2DD4A0" if dist < 0.4 else ("#F0B030" if dist < 0.8 else "#F05050")
            lines.append(
                f"<div style='background:#141424;border:1px solid #28283f;border-radius:6px;padding:12px;margin-bottom:12px;'>"
                f"<div style='font-size:8.5pt;color:#9090A8;margin-bottom:6px;font-weight:bold;'>"
                f"<span style='color:#00C2FF;'>📄 {html.escape(r['source_file'])}</span>"
                f" &nbsp;&middot;&nbsp; <span>Chunk {r['chunk_id']}</span>"
                f" &nbsp;&middot;&nbsp; <span style='background:rgba(240,176,48,0.06); border:1px solid {dist_color}; border-radius:3px; padding:1px 5px; color:{dist_color};'>dist: {dist:.4f}</span>"
                f"</div>"
                f"<div style='font-size:9.5pt;color:#ECECF5;white-space:pre-wrap;line-height:1.5;'>{html.escape(r['text'])}</div>"
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
            self._source_inspector.clear()
            self._ingest_status.setText("index cleared")

    def _load_rag_config(self):
        import json
        cfg_path = os.path.join("data", "rag_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.state.rag_threshold = float(cfg.get("rag_threshold", 0.0))
                    self.state.rag_top_k = int(cfg.get("rag_top_k", 3))
            except Exception:
                pass

    def _save_rag_config(self):
        import json
        os.makedirs("data", exist_ok=True)
        cfg_path = os.path.join("data", "rag_config.json")
        try:
            cfg = {
                "rag_threshold": self.state.rag_threshold,
                "rag_top_k": self.state.rag_top_k
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _on_threshold_changed(self, val):
        self.state.rag_threshold = val
        self._save_rag_config()

    def _on_topk_changed(self, val):
        self.state.rag_top_k = val
        self._save_rag_config()
