"""
Knowledge Base — RAG management workspace.

Left:  ingested sources tree + ingest controls
Right: chunk inspector + search tester
"""

from __future__ import annotations

import html
import os
import math

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLineEdit, QLabel,
    QListWidget, QFileDialog,
    QSpinBox, QDoubleSpinBox, QFrame, QProgressBar,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QMouseEvent
from app.utils.custom_embeddings import TfidfEmbedder



def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section-header")
    return lbl


def _label(text: str, obj: str = "") -> QLabel:
    lbl = QLabel(text)
    if obj:
        lbl.setObjectName(obj)
    return lbl


# ── background ingest thread ──────────────────────────────────────────────────

class _IngestThread(QThread):
    done = pyqtSignal(str, int)   # filename, chunk_count
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int, str, int, str)  # current, total, filename, chunks, status

    def __init__(self, rag, filepaths, chunk_size: int = 200, overlap: int = 50):
        super().__init__()
        self.rag = rag
        if isinstance(filepaths, (list, tuple)):
            self.filepaths = list(filepaths)
        else:
            self.filepaths = [filepaths]
        self.chunk_size = chunk_size
        self.overlap = overlap

    def run(self):
        try:
            def _progress(current, total, event):
                self.progress.emit(
                    int(current),
                    int(total),
                    str(event.get("filename", "")),
                    int(event.get("chunks", 0) or 0),
                    str(event.get("status", "")),
                )

            result = self.rag.ingest_files(
                self.filepaths,
                chunk_size=self.chunk_size,
                overlap=self.overlap,
                batch_size=32,
                progress_cb=_progress,
            )
            self.done.emit(
                f"{result.get('file_count', 0)} files",
                int(result.get("chunks_added", 0)),
            )
        except Exception as e:
            self.error.emit(str(e))


class _RagOperationThread(QThread):
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, rag, operation: str, argument: str | None = None):
        super().__init__()
        self.rag = rag
        self.operation = operation
        self.argument = argument

    def run(self):
        try:
            if self.operation == "preload":
                self.rag.preload_encoder()
                self.done.emit("Encoder ready.")
            elif self.operation == "remove_source":
                self.rag.remove_source(self.argument or "")
                self.done.emit(f"Removed source: {self.argument}")
            elif self.operation == "rebuild":
                self.rag.rebuild_index()
                self.done.emit("Index rebuilt successfully.")
            elif self.operation == "clear":
                self.rag.clear_index()
                self.done.emit("Index cleared.")
            else:
                raise ValueError(f"unknown RAG operation: {self.operation}")
        except Exception as e:
            self.error.emit(str(e))


class _SearchThread(QThread):
    done = pyqtSignal(str, list)
    error = pyqtSignal(str)

    def __init__(self, rag, query: str, top_k: int, mode: str):
        super().__init__()
        self.rag = rag
        self.query = query
        self.top_k = top_k
        self.mode = mode

    def run(self):
        try:
            results = self.rag.retrieve_with_metadata(
                self.query,
                top_k=self.top_k,
                mode=self.mode,
            )
            self.done.emit(self.query, results)
        except Exception as e:
            self.error.emit(str(e))


class VectorProjectionWidget(QFrame):
    """Interactive 2D projection canvas for query/document vector relationships."""

    def __init__(self, parent=None):
        """Create the projection widget and initialize hover/fade state."""
        super().__init__(parent)
        self.setObjectName("vector-projection-widget")
        self.setMinimumHeight(200)  # Reduced minimum height to avoid sizing conflicts on collapse/smaller windows
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.query_point = None  # (x, y)
        self.doc_points = []     # list of dicts
        self.axis_labels = ("", "") # (label_x, label_y)
        self.hovered_point = None
        self.setMouseTracking(True)
        
        # Smooth fade-in animation
        self.opacity = 1.0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate_step)

    def start_fade_in(self):
        self.opacity = 0.0
        self.animation_timer.start(25)  # ~40 FPS

    def _animate_step(self):
        self.opacity += 0.08
        if self.opacity >= 1.0:
            self.opacity = 1.0
            self.animation_timer.stop()
        self.update()

    def set_query(self, x: float, y: float):
        self.query_point = (x, y)
        self.start_fade_in()

    def set_documents(self, docs: list[dict]):
        self.doc_points = docs
        self.start_fade_in()

    def set_axes(self, label_x: str, label_y: str):
        self.axis_labels = (label_x, label_y)
        self.start_fade_in()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        px = pos.x()
        py = pos.y()
        
        # Expanded margins matching the paintEvent coordinates
        margin_left = 85
        margin_right = 40
        margin_top = 40
        margin_bottom = 60
        
        plot_w = self.width() - margin_left - margin_right
        plot_h = self.height() - margin_top - margin_bottom
        
        closest = None
        min_d = 12.0  # pixels
        
        if plot_w > 0 and plot_h > 0:
            for dp in self.doc_points:
                dx = margin_left + dp["x"] * plot_w
                dy = margin_top + (1.0 - dp["y"]) * plot_h
                dist = math.hypot(px - dx, py - dy)
                if dist < min_d:
                    min_d = dist
                    closest = dp
            
            if self.query_point is not None:
                qx = margin_left + self.query_point[0] * plot_w
                qy = margin_top + (1.0 - self.query_point[1]) * plot_h
                dist = math.hypot(px - qx, py - qy)
                if dist < min_d:
                    min_d = dist
                    closest = {
                        "is_query": True,
                        "x": self.query_point[0],
                        "y": self.query_point[1]
                    }
        
        if closest != self.hovered_point:
            self.hovered_point = closest
            self.update()

    def leaveEvent(self, event):
        self.hovered_point = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Polished, perfectly aligned layout margins
        margin_left = 85
        margin_right = 40
        margin_top = 40
        margin_bottom = 60
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        # Draw background card
        painter.setBrush(QBrush(QColor("#0B0B16")))
        painter.setPen(QPen(QColor("#1F1F3D"), 1))
        painter.drawRoundedRect(0, 0, w, h, 8.0, 8.0)
        
        if plot_w <= 0 or plot_h <= 0:
            return
            
        # Helper for applying fade opacity to colors
        def apply_alpha(color_val, default_alpha: int = 255) -> QColor:
            col = QColor(color_val)
            col.setAlpha(int(default_alpha * self.opacity))
            return col
            
        # Draw grid lines & tick marks
        grid_pen = QPen(apply_alpha("#15152F"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        
        font = QFont("JetBrains Mono", 8)
        painter.setFont(font)
        
        ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
        for tick in ticks:
            tx = margin_left + tick * plot_w
            ty = margin_top + (1.0 - tick) * plot_h
            
            # Skip drawing dashed lines directly on top of the solid main axes (tick = 0.0)
            if tick > 0.0:
                # Vertical grid line
                painter.drawLine(int(tx), margin_top, int(tx), margin_top + plot_h)
                # Horizontal grid line
                painter.drawLine(margin_left, int(ty), margin_left + plot_w, int(ty))
            
            # Draw tick label text
            painter.setPen(QPen(apply_alpha("#70708F")))
            # X tick labels
            painter.drawText(int(tx) - 20, margin_top + plot_h + 5, 40, 15, Qt.AlignmentFlag.AlignCenter, f"{tick:.2f}")
            # Y tick labels
            painter.drawText(margin_left - 45, int(ty) - 7, 40, 15, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{tick:.2f}")
            painter.setPen(grid_pen)

        # Draw main X and Y solid axis lines
        axis_pen = QPen(apply_alpha("#3A3A6A"), 2)
        painter.setPen(axis_pen)
        # X Axis
        painter.drawLine(margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h)
        # Y Axis
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + plot_h)
        
        # Axis labels (truncated dynamically based on screen width to prevent overlap)
        label_font = QFont("JetBrains Mono", 8, QFont.Weight.Bold)
        painter.setFont(label_font)
        painter.setPen(QPen(apply_alpha("#00C2FF")))
        
        max_chars = max(5, int(plot_w / 15))
        
        # X label
        x_lbl = self.axis_labels[0]
        if x_lbl:
            x_trunc = x_lbl[:max_chars] + "..." if len(x_lbl) > max_chars else x_lbl
            x_text = f"X: {x_trunc}" if plot_w < 220 else f"X: {x_trunc} (DF)"
            painter.drawText(margin_left, margin_top + plot_h + 25, plot_w, 20, Qt.AlignmentFlag.AlignCenter, x_text)
            
        # Y label
        y_lbl = self.axis_labels[1]
        if y_lbl:
            y_trunc = y_lbl[:max_chars] + "..." if len(y_lbl) > max_chars else y_lbl
            y_text = f"Y: {y_trunc}" if plot_h < 220 else f"Y: {y_trunc} (DF)"
            # Draw vertical Y label centered within the plot height boundaries
            painter.save()
            painter.translate(margin_left - 68, margin_top + plot_h / 2)
            painter.rotate(-90)
            y_box_w = int(plot_h)
            painter.drawText(-int(y_box_w / 2), -10, y_box_w, 20, Qt.AlignmentFlag.AlignCenter, y_text)
            painter.restore()

        # Draw lines and elements
        if self.query_point is not None:
            qx = margin_left + self.query_point[0] * plot_w
            qy = margin_top + (1.0 - self.query_point[1]) * plot_h
            
            # Draw lines to docs first (so circles render on top)
            for dp in self.doc_points:
                dx = margin_left + dp["x"] * plot_w
                dy = margin_top + (1.0 - dp["y"]) * plot_h
                
                # Draw dashed projection line
                line_pen = QPen(apply_alpha("#00C2FF", 60), 1, Qt.PenStyle.DashLine)
                painter.setPen(line_pen)
                painter.drawLine(int(qx), int(qy), int(dx), int(dy))
                
                # Draw similarity bubble in the middle of the line
                mx = (qx + dx) / 2
                my = (qy + dy) / 2
                sim_text = f"{dp['similarity']:.2f}"
                
                painter.save()
                font = QFont("JetBrains Mono", 7)
                painter.setFont(font)
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(sim_text)
                th = fm.height()
                
                rx = int(mx - tw/2 - 3)
                ry = int(my - th/2 - 1)
                rw = int(tw + 6)
                rh = int(th + 2)
                
                painter.setBrush(QBrush(apply_alpha("#141424")))
                painter.setPen(QPen(apply_alpha("#28283F"), 1))
                painter.drawRoundedRect(rx, ry, rw, rh, 3.0, 3.0)
                
                painter.setPen(apply_alpha("#00C2FF"))
                painter.drawText(rx, ry, rw, rh, Qt.AlignmentFlag.AlignCenter, sim_text)
                painter.restore()

            # Draw query point with neon glow and correct thin white border
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(apply_alpha("#00C2FF", 40)))
            painter.drawEllipse(int(qx) - 12, int(qy) - 12, 24, 24)
            painter.setBrush(QBrush(apply_alpha("#00C2FF", 80)))
            painter.drawEllipse(int(qx) - 9, int(qy) - 9, 18, 18)

            painter.setBrush(QBrush(apply_alpha("#00C2FF")))
            painter.setPen(QPen(apply_alpha("#FFFFFF", 220), 1))
            painter.drawEllipse(int(qx) - 6, int(qy) - 6, 12, 12)
            
            # Query point text label next to it
            painter.setFont(QFont("JetBrains Mono", 7, QFont.Weight.Bold))
            painter.setPen(apply_alpha("#00C2FF"))
            painter.drawText(int(qx) + 8, int(qy) - 5, "Query")

        # Draw doc points with neon glow and correct thin white border
        for dp in self.doc_points:
            dx = margin_left + dp["x"] * plot_w
            dy = margin_top + (1.0 - dp["y"]) * plot_h
            
            # Subtle neon green glow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(apply_alpha("#00FF88", 40)))
            painter.drawEllipse(int(dx) - 10, int(dy) - 10, 20, 20)

            painter.setBrush(QBrush(apply_alpha("#00FF88")))
            painter.setPen(QPen(apply_alpha("#FFFFFF", 220), 1))
            painter.drawEllipse(int(dx) - 5, int(dy) - 5, 10, 10)
            
            # Label
            painter.setFont(QFont("JetBrains Mono", 7))
            painter.setPen(apply_alpha("#9090A8"))
            painter.drawText(int(dx) + 8, int(dy) + 4, f"D{dp['id']}")

        # Draw Hover Tooltip Card with Similarity Math
        if self.hovered_point is not None:
            hp = self.hovered_point
            card_w = 320
            card_h = 120
            
            # Determine card position dynamically to avoid overlap
            hx = margin_left + hp["x"] * plot_w
            if hx < margin_left + plot_w / 2:
                card_x = w - margin_right - card_w - 15
            else:
                card_x = margin_left + 15
            card_y = margin_top + 10
            
            # Clamp card position to ensure it is always rendered inside the widget bounds
            card_x = max(10, min(card_x, w - card_w - 10))
            card_y = max(10, min(card_y, h - card_h - 10))
            
            painter.save()
            # Draw card background with a translucent Obsidian glass appearance
            painter.setBrush(QBrush(QColor(15, 15, 30, 225)))
            if hp.get("is_query"):
                painter.setPen(QPen(QColor(0, 194, 255, 180), 1.5))
            else:
                painter.setPen(QPen(QColor(0, 255, 136, 180), 1.5))
            painter.drawRoundedRect(card_x, card_y, card_w, card_h, 6.0, 6.0)
            
            # Write card content
            painter.setPen(QColor("#F0F5FF"))
            if hp.get("is_query"):
                painter.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
                painter.drawText(card_x + 10, card_y + 18, "Query Point")
                painter.setFont(QFont("JetBrains Mono", 7.5))
                painter.setPen(QColor("#9090A8"))
                
                norm_q = math.hypot(hp["x"], hp["y"])
                painter.drawText(card_x + 10, card_y + 36, f"X ({self.axis_labels[0]}): {hp['x']:.4f}")
                painter.drawText(card_x + 10, card_y + 52, f"Y ({self.axis_labels[1]}): {hp['y']:.4f}")
                painter.drawText(card_x + 10, card_y + 68, f"Norm ||Q||₂: {norm_q:.4f}")
                
                painter.setFont(QFont("JetBrains Mono", 7))
                painter.setPen(QColor("#00C2FF"))
                painter.drawText(card_x + 10, card_y + 86, "Active search query vector (2D projection)")
            else:
                # Hovered document point math
                x = hp["x"]
                y = hp["y"]
                qx, qy = self.query_point[0], self.query_point[1] if self.query_point else (0.0, 0.0)
                
                # Math calculations
                dot_prod = x * qx + y * qy
                norm_a = math.hypot(x, y)
                norm_b = math.hypot(qx, qy)
                denom = norm_a * norm_b
                sim_2d = dot_prod / denom if denom > 0.0 else 0.0
                
                # Clip similarity to [-1.0, 1.0] for arccos safety
                sim_2d_clipped = max(-1.0, min(1.0, sim_2d))
                angle_rad = math.acos(sim_2d_clipped)
                angle_deg = math.degrees(angle_rad)
                
                painter.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#00FF88"))
                painter.drawText(card_x + 10, card_y + 16, f"Document D{hp['id']} Projection Math")
                
                painter.setFont(QFont("JetBrains Mono", 7.5))
                painter.setPen(QColor("#9090A8"))
                
                # Line 1: Dot Product components
                painter.drawText(card_x + 10, card_y + 32, f"A · B = ({x:.2f} × {qx:.2f}) + ({y:.2f} × {qy:.2f}) = {dot_prod:.4f}")
                
                # Line 2: Norms
                painter.drawText(card_x + 10, card_y + 48, f"||A||₂ = {norm_a:.4f}  |  ||B||₂ = {norm_b:.4f}")
                
                # Line 3: Cosine Similarity Equation
                painter.drawText(card_x + 10, card_y + 64, f"Cosine Sim (2D) = A·B / (||A||₂×||B||₂) = {sim_2d:.4f}")
                
                # Line 4: Angle
                painter.setPen(QColor("#00FF88"))
                painter.setFont(QFont("JetBrains Mono", 7.5, QFont.Weight.Bold))
                painter.drawText(card_x + 10, card_y + 82, f"Angle θ = {angle_deg:.1f}° (2D Space)")
                
                # Line 5: Full vocabulary similarity (semantic RAG score)
                painter.setPen(QColor("#00C2FF"))
                painter.drawText(card_x + 10, card_y + 100, f"Global Cosine Sim (N-Dim) = {hp['similarity']:.4f}")
                
            painter.restore()


# ── workspace ─────────────────────────────────────────────────────────────────

class KnowledgeBaseWorkspace(QWidget):
    """RAG source manager with ingest queue, search tester, and vector sandbox."""

    def __init__(self, state, parent=None):
        """Create KB controls, enable file drag-and-drop, and load RAG settings."""
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self.setAcceptDrops(True)
        self._load_rag_config()
        self._active_threads = set()
        self._rag_operation_thread = None
        self._search_thread = None
        self._ingest_queue = []
        self._tfidf = TfidfEmbedder()
        self._build_ui()
        self._refresh_sources()
        self._update_encoder_status()

    def dragEnterEvent(self, event):
        """Accept drag events that contain local file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Keep accepting supported URL drags while hovering over the workspace."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Queue dropped supported files for ingestion."""
        urls = event.mimeData().urls()
        supported_exts = {".pdf", ".docx", ".txt", ".md", ".py", ".csv"}
        new_paths = []
        for url in urls:
            filepath = url.toLocalFile()
            if os.path.isfile(filepath):
                ext = os.path.splitext(filepath)[1].lower()
                if ext in supported_exts:
                    new_paths.append(filepath)
        if new_paths:
            for p in new_paths:
                if not any(item["path"] == p for item in self._ingest_queue):
                    self._ingest_queue.append({"path": p, "status": "Pending", "error": ""})
            self._update_queue_ui()
            self._process_ingest_queue()
            self._ingest_status.setText(f"Queued {len(new_paths)} file(s) via Drag & Drop.")

    def _build_ui(self):
        """Build explorer, ingest, search, and vector sandbox tabs."""
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
        root.addWidget(title_row)

        # Status cluster on its own row: title + 5 status widgets competing
        # for one line overflowed the app's 760px minimum width, clipping
        # whichever widget the layout ran out of room for first (observed:
        # the encoder status label). A dedicated row has room regardless of
        # window width.
        status_row = QWidget()
        sr = QHBoxLayout(status_row)
        sr.setContentsMargins(0, 0, 0, 0)

        # Lazy model loader indicator
        self._model_status_lbl = QLabel("Encoder: Not loaded")
        self._model_status_lbl.setObjectName("lbl-muted")
        sr.addWidget(self._model_status_lbl)

        self._preload_btn = QPushButton("Preload")
        self._preload_btn.setObjectName("btn-ghost")
        self._preload_btn.setStyleSheet("font-size: 8pt; padding: 2px 6px;")
        self._preload_btn.clicked.connect(self._preload_encoder)
        sr.addWidget(self._preload_btn)

        sr.addWidget(_label("|", "lbl-muted"))

        self._health_lbl = QLabel("Index Health: Healthy")
        self._health_lbl.setObjectName("lbl-muted")
        sr.addWidget(self._health_lbl)

        sr.addWidget(_label("|", "lbl-muted"))

        self._stats_lbl = QLabel("0 sources · 0 chunks")
        self._stats_lbl.setObjectName("lbl-muted")
        sr.addWidget(self._stats_lbl)
        sr.addStretch()
        root.addWidget(status_row)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_explorer_tab(), "Index Explorer")
        self._tabs.addTab(self._build_ingest_tab(), "Ingestion Hub")
        self._tabs.addTab(self._build_search_tab(), "Semantic Search")
        self._tabs.addTab(self._build_sandbox_tab(), "Vector Sandbox")
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

        self._clear_btn = QPushButton("clear database")
        self._clear_btn.setObjectName("btn-danger")
        self._clear_btn.setToolTip("Wipe the vector database index and all ingested document text")
        self._clear_btn.clicked.connect(self._clear_index)
        ll.addWidget(self._clear_btn)

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

        # Ensure dynamic attribute exists
        if not hasattr(self.state, "rag_mode"):
            self.state.rag_mode = "dense"

        pl.addWidget(QLabel("Retrieval Mode:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["dense", "sparse", "hybrid"])
        self._mode_combo.setCurrentText(self.state.rag_mode)
        self._mode_combo.setFixedWidth(90)
        self._mode_combo.setToolTip("Dense (neural embeddings), Sparse (TF-IDF keywords), or Hybrid (RRF merged)")
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        pl.addWidget(self._mode_combo)

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

        self._search_btn = QPushButton("Search Index")
        self._search_btn.setObjectName("btn-primary")
        self._search_btn.clicked.connect(self._run_search)
        sr.addWidget(self._search_btn)

        self._send_to_workbench_btn = QPushButton("Send to Workbench")
        self._send_to_workbench_btn.setObjectName("btn-ghost")
        self._send_to_workbench_btn.setToolTip("Switch to Workbench workspace and paste this query")
        self._send_to_workbench_btn.clicked.connect(self._send_query_to_workbench)
        sr.addWidget(self._send_to_workbench_btn)

        layout.addWidget(search_row)

        # Search results view
        self._search_results = QTextBrowser()
        self._search_results.setPlaceholderText("Search query results will be rendered here with distances and file references...")
        self._search_results.setOpenLinks(False)
        self._search_results.anchorClicked.connect(self._handle_search_result_link)
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
        self._start_rag_operation(
            "preload",
            status_text="Loading encoder...",
            done_cb=lambda _msg: self._update_encoder_status(),
            error_cb=lambda msg: self._model_status_lbl.setText(f"Encoder Error: {msg}"),
        )

    def _update_health_lbl(self):
        index_file = self.state.rag.INDEX_FILE
        index_size_kb = 0
        if os.path.exists(index_file):
            index_size_kb = os.path.getsize(index_file) / 1024
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
        self._process_ingest_queue()

    def _update_queue_ui(self):
        self._queue_list.clear()
        for item in self._ingest_queue:
            fname = os.path.basename(item["path"])
            status = item["status"]
            err = f" - {item['error']}" if item["error"] else ""
            self._queue_list.addItem(f"[{status}] {fname}{err}")

    def _process_next_in_queue(self):
        self._process_ingest_queue()

    def _process_ingest_queue(self):
        pending = [item for item in self._ingest_queue if item["status"] == "Pending"]
        if not pending:
            self._progress.setVisible(False)
            self._ingest_status.setText("All files processed.")
            self._refresh_sources()
            self._update_encoder_status()
            return

        for item in pending:
            item["status"] = "Queued"
        self._update_queue_ui()

        paths = [item["path"] for item in pending]
        self._ingest_status.setText(f"Parsing {len(paths)} file(s)...")
        self._progress.setVisible(True)
        self._progress.setRange(0, len(paths))
        self._progress.setValue(0)
        
        self._ingest_thread = _IngestThread(
            self.state.rag,
            paths,
            chunk_size=self._chunk_size_spin.value(),
            overlap=self._overlap_spin.value()
        )
        self._active_threads.add(self._ingest_thread)
        self._ingest_thread.finished.connect(
            lambda t=self._ingest_thread: self._active_threads.discard(t)
        )
        self._ingest_thread.finished.connect(self._ingest_thread.deleteLater)
        
        def on_progress(current, total, filename, chunks, status):
            self._progress.setRange(0, max(1, total))
            self._progress.setValue(current)
            if filename:
                self._ingest_status.setText(
                    f"Parsed {current}/{total}: {filename} ({chunks} chunks)"
                )
                for item in self._ingest_queue:
                    if os.path.basename(item["path"]) == filename:
                        item["status"] = "Done" if status == "parsed" else status.title()
                        break
            self._update_queue_ui()

        def on_done(filename, count):
            for item in self._ingest_queue:
                if item["status"] in {"Queued", "Parsed"}:
                    item["status"] = "Done"
            self._update_queue_ui()
            self._progress.setVisible(False)
            self._ingest_status.setText(f"Ingested {count} chunks from {filename}.")
            self._refresh_sources()
            self._update_encoder_status()
            
        def on_error(msg):
            for item in self._ingest_queue:
                if item["status"] in {"Queued", "Parsed"}:
                    item["status"] = "Failed"
                    item["error"] = msg
            self._update_queue_ui()
            self._progress.setVisible(False)
            self._ingest_status.setText(f"Ingest error: {msg}")
            
        self._ingest_thread.progress.connect(on_progress)
        self._ingest_thread.done.connect(on_done)
        self._ingest_thread.error.connect(on_error)
        self._ingest_thread.start()

    def _set_index_controls_enabled(self, enabled: bool):
        for control in (
            getattr(self, "_remove_btn", None),
            getattr(self, "_rebuild_btn", None),
            getattr(self, "_clear_btn", None),
            getattr(self, "_preload_btn", None),
        ):
            if control is not None:
                control.setEnabled(enabled)

    def _start_rag_operation(
        self,
        operation: str,
        argument: str | None = None,
        *,
        status_text: str,
        done_cb=None,
        error_cb=None,
    ):
        if self._rag_operation_thread is not None and self._rag_operation_thread.isRunning():
            self._ingest_status.setText("Another index operation is already running.")
            return False

        self._ingest_status.setText(status_text)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._set_index_controls_enabled(False)

        thread = _RagOperationThread(self.state.rag, operation, argument)

        def on_done(msg: str):
            if done_cb is not None:
                done_cb(msg)
            else:
                self._refresh_sources()
                self._update_encoder_status()
                self._ingest_status.setText(msg)

        def on_error(msg: str):
            if error_cb is not None:
                error_cb(msg)
            else:
                self._ingest_status.setText(f"Index operation error: {msg}")

        def on_finished():
            self._progress.setVisible(False)
            self._progress.setRange(0, 100)
            self._set_index_controls_enabled(True)
            self._update_encoder_status()
            self._active_threads.discard(thread)
            if self._rag_operation_thread is thread:
                self._rag_operation_thread = None

        thread.done.connect(on_done)
        thread.error.connect(on_error)
        thread.finished.connect(on_finished)
        thread.finished.connect(thread.deleteLater)
        self._active_threads.add(thread)
        self._rag_operation_thread = thread
        thread.start()
        return True

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
            self._start_rag_operation(
                "remove_source",
                source_name,
                status_text=f"Removing {source_name}...",
                done_cb=lambda msg: (
                    self._refresh_sources(),
                    self._source_inspector.clear(),
                    self._search_results.clear(),
                    self._ingest_status.setText(msg),
                ),
            )

    def _rebuild_index(self):
        reply = QMessageBox.question(
            self, "Rebuild Index",
            "This will re-encode all chunks in metadata. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_rag_operation(
                "rebuild",
                status_text="Rebuilding index...",
                done_cb=lambda msg: (
                    self._refresh_sources(),
                    self._update_encoder_status(),
                    self._ingest_status.setText(msg),
                ),
            )

    def open_ingest_dialog(self):
        self._tabs.setCurrentIndex(1)
        self._ingest_file()

    def rebuild_index(self):
        self._rebuild_index()

    def _send_query_to_workbench(self):
        query = self._search_input.text().strip()
        if not query:
            return
        self.state.change_workspace_requested.emit(0)
        self.state.replace_workbench_input.emit(query)


    def _run_search(self):
        query = self._search_input.text().strip()
        if not query:
            return
        if self.state.rag.total_chunks == 0:
            self._search_results.setHtml("<div style='color:#F05050;'>Knowledge base is empty.</div>")
            return
        if self._search_thread is not None and self._search_thread.isRunning():
            return

        top_k = self._topk_spin.value()
        mode = getattr(self.state, "rag_mode", "dense")
        self._search_results.setHtml("<div style='color:#9090A8;'>Searching index...</div>")
        self._search_btn.setEnabled(False)
        self._search_input.setEnabled(False)

        thread = _SearchThread(self.state.rag, query, top_k, mode)

        def on_done(done_query: str, results: list):
            self._render_search_results(done_query, results)

        def on_error(msg: str):
            self._search_results.setHtml(
                f"<div style='color:#F05050;'>Search error: {html.escape(msg)}</div>"
            )

        def on_finished():
            self._search_btn.setEnabled(True)
            self._search_input.setEnabled(True)
            self._active_threads.discard(thread)
            if self._search_thread is thread:
                self._search_thread = None

        thread.done.connect(on_done)
        thread.error.connect(on_error)
        thread.finished.connect(on_finished)
        thread.finished.connect(thread.deleteLater)
        self._active_threads.add(thread)
        self._search_thread = thread
        thread.start()

    def _render_search_results(self, query: str, results: list):
        from app.ui.themes import get_theme_colors
        colors = get_theme_colors(self.state)
        accent = colors.get("accent", "#00C2FF")
        text_hi = colors.get("text_hi", "#ECECF5")
        text_mid = colors.get("text_mid", "#9090A8")
        bg_surface = colors.get("bg_surface", "#141424")
        border = colors.get("border", "#28283F")

        threshold = self._threshold_spin.value()
        if threshold > 0:
            results = [r for r in results if r["distance"] <= threshold]

        if not results:
            self._search_results.setHtml(
                f"<div style='color:#9090A8;'>No results found below distance threshold <b>{threshold:.2f}</b> for query: <i>{html.escape(query)}</i></div>"
            )
            return

        lines = [
            f"<div style='font-size:11pt;color:{accent};font-weight:bold;margin-bottom:4px;'>Search Results for: <i>{html.escape(query)}</i></div>"
            f"<div style='font-size:9pt;color:{text_mid};margin-bottom:12px;'>Found {len(results)} chunks:</div>"
        ]
        for idx, r in enumerate(results):
            dist = r["distance"]
            rank = r.get("rank", idx + 1)
            dist_color = "#2DD4A0" if dist < 0.3 else ("#F0B030" if dist <= 0.7 else "#F05050")
            
            # Calculate distance bar percentage (dist / threshold)
            bar_threshold = threshold if threshold > 0.0 else 1.0
            pct = min(100.0, max(0.0, (dist / bar_threshold) * 100.0))
            
            bar_html = (
                f"<div style='margin-top:8px;background:#1e1e30;border-radius:3px;height:6px;width:100%;overflow:hidden;'>"
                f"<div style='background:{dist_color};height:100%;width:{pct:.1f}%;border-radius:3px;'></div>"
                f"</div>"
                f"<div style='font-size:7.5pt;color:{text_mid};margin-top:2px;'>Distance score relative to threshold: {pct:.1f}%</div>"
            )

            lines.append(
                f"<div style='background:{bg_surface};border:1px solid {border};border-radius:6px;padding:12px;margin-bottom:12px;'>"
                f"<div style='font-size:8.5pt;color:{text_mid};margin-bottom:6px;font-weight:bold;'>"
                f"<span style='color:{accent};'>📄 {html.escape(r['source_file'])}</span>"
                f" &nbsp;&middot;&nbsp; <span>Chunk {r['chunk_id']}</span>"
                f" &nbsp;&middot;&nbsp; <span style='background:rgba(240,176,48,0.06); border:1px solid {dist_color}; border-radius:3px; padding:1px 5px; color:{dist_color};'>dist: {dist:.4f}</span>"
                f" &nbsp;&middot;&nbsp; <span style='background:rgba(0,194,255,0.06); border:1px solid {accent}; border-radius:3px; padding:1px 5px; color:{accent};'>Rank: {rank}</span>"
                f" <a href='copy:{r['chunk_id']}' style='color:{accent};text-decoration:none;font-weight:bold;float:right;background:#1A1A2F;border:1px solid {accent};border-radius:3px;padding:1px 6px;font-size:7.5pt;'>Copy chunk</a>"
                f"</div>"
                f"<div style='font-size:9.5pt;color:{text_hi};white-space:pre-wrap;line-height:1.5;'>{html.escape(r['text'])}</div>"
                f"{bar_html}"
                f"</div>"
            )
        self._search_results.setHtml("".join(lines))

    def _handle_search_result_link(self, url):
        link = url.toString()
        if link.startswith("copy:"):
            try:
                chunk_id = int(link.split(":")[1])
                for doc in self.state.rag.documents:
                    if doc.get("chunk_id") == chunk_id:
                        from PyQt6.QtGui import QGuiApplication
                        clipboard = QGuiApplication.clipboard()
                        clipboard.setText(doc["text"])
                        self._ingest_status.setText(f"Copied chunk {chunk_id} to clipboard")
                        break
            except Exception as e:
                import logging
                logging.getLogger("karl.kb").warning(f"Failed to copy chunk: {e}")

    def _clear_index(self):
        reply = QMessageBox.question(
            self, "Clear index",
            "This permanently deletes the vector index and all ingested data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_rag_operation(
                "clear",
                status_text="Clearing index...",
                done_cb=lambda msg: (
                    self._refresh_sources(),
                    self._search_results.clear(),
                    self._source_inspector.clear(),
                    self._ingest_status.setText(msg.lower()),
                ),
            )

    def _load_rag_config(self):
        import json
        cfg_path = os.path.join("data", "rag_config.json")
        self.state.rag_mode = "dense"
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.state.rag_threshold = float(cfg.get("rag_threshold", 0.0))
                    self.state.rag_top_k = int(cfg.get("rag_top_k", 3))
                    self.state.rag_mode = str(cfg.get("rag_mode", "dense"))
            except Exception:
                pass

    def _save_rag_config(self):
        import json
        os.makedirs("data", exist_ok=True)
        cfg_path = os.path.join("data", "rag_config.json")
        try:
            cfg = {
                "rag_threshold": self.state.rag_threshold,
                "rag_top_k": self.state.rag_top_k,
                "rag_mode": getattr(self.state, "rag_mode", "dense")
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

    def _on_mode_changed(self, val):
        self.state.rag_mode = val
        self._save_rag_config()

    # ── Vector Sandbox Implementation ──────────────────────────────────────────

    def _build_sandbox_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left panel: Document builder
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)
        ll.addWidget(_section("SANDBOX DOCUMENTS"))

        desc = QLabel("Add simple sentences to build a custom vector space.")
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        ll.addWidget(desc)

        self._sandbox_doc_list = QListWidget()
        self._sandbox_doc_list.setToolTip("Documents used to fit the TF-IDF vectorizer")
        ll.addWidget(self._sandbox_doc_list, 1)

        # Add document input
        add_row = QHBoxLayout()
        self._sandbox_doc_input = QLineEdit()
        self._sandbox_doc_input.setPlaceholderText("Type a new sentence here...")
        self._sandbox_doc_input.returnPressed.connect(self._add_sandbox_doc)
        add_row.addWidget(self._sandbox_doc_input, 1)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("btn-primary")
        add_btn.clicked.connect(self._add_sandbox_doc)
        add_row.addWidget(add_btn)
        ll.addLayout(add_row)

        # Actions
        actions_row = QHBoxLayout()
        remove_btn = QPushButton("Delete Selected")
        remove_btn.setObjectName("btn-warning")
        remove_btn.clicked.connect(self._remove_sandbox_doc)
        actions_row.addWidget(remove_btn, 1)
        
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.setObjectName("btn-ghost")
        reset_btn.clicked.connect(self._reset_sandbox_docs)
        actions_row.addWidget(reset_btn, 1)
        ll.addLayout(actions_row)

        compute_btn = QPushButton("Fit Vectorizer & Recompute")
        compute_btn.setObjectName("btn-primary")
        compute_btn.setStyleSheet("font-weight: bold; height: 30px;")
        compute_btn.clicked.connect(self._recompute_sandbox)
        ll.addWidget(compute_btn)

        splitter.addWidget(left)

        # Right panel: Vector Math Inspector
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(_section("VECTOR MATH INSPECTOR"))

        self._sandbox_res_tabs = QTabWidget()
        
        # Sub-tab 1: Vocab table
        self._sandbox_vocab_table = QTableWidget()
        self._sandbox_vocab_table.setColumnCount(3)
        self._sandbox_vocab_table.setHorizontalHeaderLabels(["Word / Token", "DF (Doc Freq)", "IDF (Inverse Doc Freq)"])
        self._sandbox_vocab_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._sandbox_vocab_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._sandbox_res_tabs.addTab(self._sandbox_vocab_table, "Vocabulary & IDFs")

        # Sub-tab 2: Matrix table
        self._sandbox_matrix_table = QTableWidget()
        self._sandbox_matrix_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._sandbox_res_tabs.addTab(self._sandbox_matrix_table, "TF-IDF Vector Matrix")

        # Sub-tab 3: Similarity playground
        sim_widget = QWidget()
        sim_layout = QVBoxLayout(sim_widget)
        sim_layout.setContentsMargins(8, 8, 8, 8)
        sim_layout.setSpacing(8)

        query_row = QHBoxLayout()
        self._sandbox_query_input = QLineEdit()
        self._sandbox_query_input.setPlaceholderText("Type a query to search vectors (e.g. 'quick fox' or 'doctor patients')...")
        self._sandbox_query_input.returnPressed.connect(self._run_sandbox_similarity)
        query_row.addWidget(self._sandbox_query_input, 1)
        sim_btn = QPushButton("Calculate Similarity")
        sim_btn.setObjectName("btn-primary")
        sim_btn.clicked.connect(self._run_sandbox_similarity)
        query_row.addWidget(sim_btn)
        sim_layout.addLayout(query_row)

        sim_splitter = QSplitter(Qt.Orientation.Vertical)
        sim_splitter.setHandleWidth(1)
        sim_splitter.setStyleSheet("QSplitter::handle { background-color: #1F1F3D; }")

        self._sandbox_similarity_browser = QTextBrowser()
        self._sandbox_similarity_browser.setPlaceholderText("Vector similarity math breakdown will appear here...")
        sim_splitter.addWidget(self._sandbox_similarity_browser)

        self._sandbox_projection = VectorProjectionWidget()
        sim_splitter.addWidget(self._sandbox_projection)
        
        sim_layout.addWidget(sim_splitter, 1)

        self._sandbox_res_tabs.addTab(sim_widget, "Similarity Playground")

        rl.addWidget(self._sandbox_res_tabs, 1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Pre-populate defaults
        self._reset_sandbox_docs()
        
        return w

    def _reset_sandbox_docs(self):
        self._sandbox_doc_list.clear()
        defaults = [
            "The quick brown fox jumps over the lazy dog",
            "Dogs and foxes are animals that run fast",
            "A doctor heals patients in a hospital clinic",
            "The medical physician treated patients yesterday"
        ]
        for d in defaults:
            self._sandbox_doc_list.addItem(d)
        self._recompute_sandbox()

    def _add_sandbox_doc(self):
        text = self._sandbox_doc_input.text().strip()
        if text:
            self._sandbox_doc_list.addItem(text)
            self._sandbox_doc_input.clear()
            self._recompute_sandbox()

    def _remove_sandbox_doc(self):
        curr = self._sandbox_doc_list.currentItem()
        if curr:
            self._sandbox_doc_list.takeItem(self._sandbox_doc_list.row(curr))
            self._recompute_sandbox()

    def _recompute_sandbox(self):
        # Gather documents
        docs = []
        for i in range(self._sandbox_doc_list.count()):
            docs.append(self._sandbox_doc_list.item(i).text())

        if not docs:
            self._sandbox_vocab_table.setRowCount(0)
            self._sandbox_matrix_table.setRowCount(0)
            self._sandbox_matrix_table.setColumnCount(0)
            return

        # Fit vectorizer
        self._tfidf.fit(docs)
        vocab = self._tfidf.vocabulary
        
        # 1. Populate Vocabulary Table
        self._sandbox_vocab_table.setRowCount(len(vocab))
        inv_vocab = {v: k for k, v in vocab.items()}
        for i in range(len(vocab)):
            word = inv_vocab[i]
            # DF
            df_count = sum(1 for d in docs if word in self._tfidf.tokenize(d))
            idf_val = self._tfidf.idf[i]
            
            self._sandbox_vocab_table.setItem(i, 0, QTableWidgetItem(word))
            self._sandbox_vocab_table.setItem(i, 1, QTableWidgetItem(str(df_count)))
            self._sandbox_vocab_table.setItem(i, 2, QTableWidgetItem(f"{idf_val:.4f}"))

        # 2. Populate Matrix Table
        self._sandbox_matrix_table.setRowCount(len(docs))
        self._sandbox_matrix_table.setColumnCount(len(vocab))
        
        # Set headers
        col_headers = [inv_vocab[col] for col in range(len(vocab))]
        self._sandbox_matrix_table.setHorizontalHeaderLabels(col_headers)
        row_headers = [f"Doc {i+1}: {docs[i][:20]}..." for i in range(len(docs))]
        self._sandbox_matrix_table.setVerticalHeaderLabels(row_headers)

        # Collect all non-zero values to find the max
        all_vals = []
        for doc in docs:
            vec = self._tfidf.transform(doc)
            for val in vec:
                if val > 0.0:
                    all_vals.append(val)
        max_val = max(all_vals) if all_vals else 1.0

        for r_idx, doc in enumerate(docs):
            vec = self._tfidf.transform(doc)
            for c_idx in range(len(vocab)):
                val = vec[c_idx] if len(vec) > c_idx else 0.0
                item = QTableWidgetItem(f"{val:.4f}" if val > 0 else "0.0")
                if val > 0:
                    item.setForeground(Qt.GlobalColor.cyan)
                    # normalize val between 0.05 and 0.4
                    alpha = 0.05 + (val / max_val) * (0.4 - 0.05) if max_val > 0.0 else 0.05
                    item.setBackground(QColor(0, 194, 255, int(alpha * 255)))
                self._sandbox_matrix_table.setItem(r_idx, c_idx, item)

        self._sandbox_matrix_table.resizeColumnsToContents()

        # Update Similarity playground if a query exists
        if self._sandbox_query_input.text().strip():
            self._run_sandbox_similarity()
        else:
            # Query is empty, set empty query but project documents on highest DF axes
            if vocab:
                docs_tokens = [self._tfidf.tokenize(d) for d in docs]
                df_counts = {}
                for word in vocab:
                    df_counts[word] = sum(1 for tokens in docs_tokens if word in tokens)
                
                # Sort terms by DF descending, then alphabetically
                sorted_terms = sorted(vocab.keys(), key=lambda w: (-df_counts[w], w))
                
                term_x, term_y = "", ""
                idx_x, idx_y = -1, -1
                if len(sorted_terms) >= 1:
                    term_x = sorted_terms[0]
                    idx_x = vocab[term_x]
                if len(sorted_terms) >= 2:
                    term_y = sorted_terms[1]
                    idx_y = vocab[term_y]
                    
                self._sandbox_projection.set_axes(term_x or "X Axis", term_y or "Y Axis")
                self._sandbox_projection.query_point = None
                
                doc_points = []
                for doc_idx, doc in enumerate(docs):
                    d_vec = self._tfidf.transform(doc)
                    d_x = float(d_vec[idx_x]) if idx_x >= 0 and len(d_vec) > idx_x else 0.0
                    d_y = float(d_vec[idx_y]) if idx_y >= 0 and len(d_vec) > idx_y else 0.0
                    doc_points.append({
                        "id": doc_idx + 1,
                        "x": d_x,
                        "y": d_y,
                        "similarity": 0.0,
                        "text": doc
                    })
                    self._sandbox_projection.set_documents(doc_points)
            else:
                self._sandbox_projection.query_point = None
                self._sandbox_projection.set_documents([])

    def _run_sandbox_similarity(self):
        query = self._sandbox_query_input.text().strip()
        if not query:
            return

        docs = []
        for i in range(self._sandbox_doc_list.count()):
            docs.append(self._sandbox_doc_list.item(i).text())

        if not docs or not self._tfidf.vocabulary:
            self._sandbox_similarity_browser.setHtml("<div style='color:#FF3B30;'>Vector space is empty. Please add documents.</div>")
            return

        # 1. Transform query
        q_vec = self._tfidf.transform(query)
        q_tokens = self._tfidf.tokenize(query)
        vocab = self._tfidf.vocabulary
        inv_vocab = {v: k for k, v in vocab.items()}

        lines = []
        lines.append("<div style='font-size:12pt; color:#00C2FF; font-weight:bold; margin-bottom:8px;'>Cosine Similarity Calculations</div>")
        lines.append(f"<div style='font-size:10pt; color:#ECECF5; margin-bottom:6px;'><b>Query</b>: <i>{html.escape(query)}</i></div>")
        lines.append(f"<div style='font-size:9pt; color:#9090A8; margin-bottom:12px;'><b>Normalized Query Tokens</b>: {', '.join(f'<b>{t}</b>' for t in q_tokens if t in vocab) or 'none'}</div>")

        # Show query vector non-zero terms
        q_non_zero = []
        for i, val in enumerate(q_vec):
            if val > 0:
                q_non_zero.append(f"{inv_vocab[i]}: {val:.4f}")
        q_vec_str = ", ".join(q_non_zero) if q_non_zero else "None (No overlapping vocabulary words)"
        lines.append(f"<div style='font-size:9pt; color:#9090A8; padding:6px; background:#18182E; border-radius:4px; margin-bottom:12px;'><b>Query Vector:</b> [{q_vec_str}]</div>")

        # Compute cosine similarity for each document and explain
        ranked_docs = []
        for doc_idx, doc in enumerate(docs):
            d_vec = self._tfidf.transform(doc)
            sim = self._tfidf.cosine_similarity(q_vec, d_vec)

            # Detail the math
            overlap_calcs = []
            for i in range(len(vocab)):
                q_val = q_vec[i]
                d_val = d_vec[i]
                if q_val > 0.0 and d_val > 0.0:
                    overlap_calcs.append((inv_vocab[i], q_val, d_val, q_val * d_val))

            equation_parts = []
            for word, qv, dv, prod in overlap_calcs:
                equation_parts.append(f"({word}: {qv:.3f} &times; {dv:.3f} = {prod:.4f})")
            
            calc_text = " + ".join(equation_parts) if equation_parts else "0.0"
            if not equation_parts:
                math_explanation = "No overlapping tokens."
            else:
                math_explanation = f"Dot Product = {calc_text} = <b>{sim:.4f}</b>"

            ranked_docs.append({
                "idx": doc_idx + 1,
                "doc": doc,
                "similarity": sim,
                "math_explanation": math_explanation
            })

        # Sort by similarity descending
        ranked_docs.sort(key=lambda x: x["similarity"], reverse=True)

        for rd in ranked_docs:
            sim = rd["similarity"]
            pct = sim * 100
            color = "#00C2FF" if sim > 0.3 else "#505068"
            bar_style = f"background:{color}; height:100%; width:{pct:.1f}%; border-radius:3px;"
            
            lines.append(
                f"<div style='background:#141424; border:1px solid #28283f; border-radius:6px; padding:12px; margin-bottom:10px;'>"
                f"  <div style='font-size:9.5pt; font-weight:bold; color:#00C2FF; margin-bottom:4px;'>"
                f"    Document {rd['idx']}"
                f"    <span style='float:right; color:{color}; font-weight:bold;'>Similarity: {sim:.4f}</span>"
                f"  </div>"
                f"  <div style='font-size:9.5pt; color:#ECECF5; margin-bottom:6px; font-style:italic;'>\"{html.escape(rd['doc'])}\"</div>"
                f"  <div style='font-size:8.5pt; color:#9090A8; margin-bottom:6px;'>{rd['math_explanation']}</div>"
                f"  <div style='background:#1e1e30; border-radius:3px; height:6px; width:100%;'>"
                f"    <div style='{bar_style}'></div>"
                f"  </div>"
                f"</div>"
            )

        self._sandbox_similarity_browser.setHtml("".join(lines))

        # Update 2D vector projection map
        # Determine the two terms with the highest document frequency
        docs_tokens = [self._tfidf.tokenize(d) for d in docs]
        df_counts = {}
        for word in vocab:
            df_counts[word] = sum(1 for tokens in docs_tokens if word in tokens)
        
        # Sort terms by DF descending, then alphabetically
        sorted_terms = sorted(vocab.keys(), key=lambda w: (-df_counts[w], w))
        
        term_x, term_y = "", ""
        idx_x, idx_y = -1, -1
        if len(sorted_terms) >= 1:
            term_x = sorted_terms[0]
            idx_x = vocab[term_x]
        if len(sorted_terms) >= 2:
            term_y = sorted_terms[1]
            idx_y = vocab[term_y]
            
        self._sandbox_projection.set_axes(term_x or "X Axis", term_y or "Y Axis")
        
        # Compute coordinates for query
        q_x = float(q_vec[idx_x]) if idx_x >= 0 and len(q_vec) > idx_x else 0.0
        q_y = float(q_vec[idx_y]) if idx_y >= 0 and len(q_vec) > idx_y else 0.0
        self._sandbox_projection.set_query(q_x, q_y)
        
        # Compute coordinates for documents
        doc_points = []
        for doc_idx, doc in enumerate(docs):
            d_vec = self._tfidf.transform(doc)
            sim = self._tfidf.cosine_similarity(q_vec, d_vec)
            
            d_x = float(d_vec[idx_x]) if idx_x >= 0 and len(d_vec) > idx_x else 0.0
            d_y = float(d_vec[idx_y]) if idx_y >= 0 and len(d_vec) > idx_y else 0.0
            
            doc_points.append({
                "id": doc_idx + 1,
                "x": d_x,
                "y": d_y,
                "similarity": sim,
                "text": doc
            })
        self._sandbox_projection.set_documents(doc_points)
