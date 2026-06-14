"""
Flywheel Studio — Model self-improvement and optimization dashboard.

Coordinating traces, curation datasets, evaluations, and loss metrics.
"""

from __future__ import annotations

import os
import json
import glob
import re
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QTabWidget, QFrame,
    QSizePolicy, QTableWidget, QTableWidgetItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QLinearGradient, QPainterPath

from app.ui.themes import MONO
from app.ui.widgets.glow_panel import GlowPanel


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _label(text: str, obj: str = "") -> QLabel:
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
    return l


# ── Custom Interactive Line Chart Widget ──────────────────────────────────────

class CustomLineChart(QWidget):
    def __init__(self, title: str, x_label: str, y_label: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.points: list[tuple[float, float]] = []
        self.labels: list[str] = []
        self.setMouseTracking(True)
        self.hovered_idx = -1
        self.hover_pos = None

    def set_data(self, points: list[tuple[float, float]], labels: list[str] = None):
        self.points = points
        self.labels = labels or []
        self.hovered_idx = -1
        self.update()

    def set_metric(self, title: str, y_label: str):
        self.title = title
        self.y_label = y_label
        self.update()

    def mouseMoveEvent(self, event):
        if not self.points:
            return
        
        w, h = self.width(), self.height()
        margin_left = 70
        margin_right = 30
        margin_top = 40
        margin_bottom = 50
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        if len(self.points) < 1:
            return

        min_x = min(p[0] for p in self.points) if len(self.points) > 1 else 0
        max_x = max(p[0] for p in self.points) if len(self.points) > 1 else 1
        min_y = min(p[1] for p in self.points)
        max_y = max(p[1] for p in self.points)
        
        y_range = max_y - min_y
        if y_range == 0:
            min_y -= 0.1
            max_y += 0.1
        else:
            min_y -= y_range * 0.1
            max_y += y_range * 0.1
            
        screen_points = []
        for x, y in self.points:
            if max_x == min_x:
                sx = margin_left + plot_w / 2
            else:
                sx = margin_left + ((x - min_x) / (max_x - min_x)) * plot_w
                
            if max_y == min_y:
                sy = margin_top + plot_h / 2
            else:
                sy = margin_top + plot_h - ((y - min_y) / (max_y - min_y)) * plot_h
            screen_points.append((sx, sy))
            
        nearest_idx = -1
        min_dist = float('inf')
        m_x, m_y = event.position().x(), event.position().y()
        for idx, (sx, sy) in enumerate(screen_points):
            dist = ((sx - m_x) ** 2 + (sy - m_y) ** 2) ** 0.5
            if dist < 25 and dist < min_dist:
                min_dist = dist
                nearest_idx = idx
                
        if nearest_idx != self.hovered_idx:
            self.hovered_idx = nearest_idx
            self.hover_pos = event.position()
            self.update()

    def leaveEvent(self, event):
        self.hovered_idx = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        margin_left = 70
        margin_right = 30
        margin_top = 40
        margin_bottom = 50
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        bg_color = QColor(13, 13, 27)
        grid_color = QColor(31, 31, 61)
        text_color = QColor(144, 144, 168)
        accent_color = QColor(0, 194, 255)
        line_color = QColor(0, 194, 255, 220)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, w, h, 6, 6)
        
        painter.setPen(QPen(grid_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(margin_left, margin_top, plot_w, plot_h)
        
        painter.setPen(QPen(QColor(240, 245, 255), 1))
        painter.setFont(QFont("Outfit, Inter, sans-serif", 9, QFont.Weight.Bold))
        painter.drawText(margin_left, 25, self.title)
        
        if not self.points:
            painter.setPen(QPen(text_color, 1))
            painter.setFont(QFont("Outfit, Inter, sans-serif", 9))
            painter.drawText(margin_left + plot_w // 4, margin_top + plot_h // 2, "No data points found to plot.")
            return
            
        painter.setFont(QFont("JetBrains Mono, Courier New", 7))
        painter.setPen(QPen(text_color, 1))
        
        min_x = min(p[0] for p in self.points) if len(self.points) > 1 else 0
        max_x = max(p[0] for p in self.points) if len(self.points) > 1 else 1
        min_y = min(p[1] for p in self.points)
        max_y = max(p[1] for p in self.points)
        
        y_range = max_y - min_y
        if y_range == 0:
            min_y -= 0.1
            max_y += 0.1
        else:
            min_y -= y_range * 0.1
            max_y += y_range * 0.1
            
        # Draw Y-axis labels and grid lines
        for i in range(5):
            val = min_y + (max_y - min_y) * (i / 4.0)
            sy = margin_top + plot_h - (i / 4.0) * plot_h
            if i > 0 and i < 4:
                painter.setPen(QPen(QColor(grid_color.red(), grid_color.green(), grid_color.blue(), 100), 1, Qt.PenStyle.DashLine))
                painter.drawLine(margin_left, int(sy), margin_left + plot_w, int(sy))
            painter.setPen(QPen(text_color, 1))
            label = f"{val:.1f}" if val >= 1 else f"{val:.3f}"
            painter.drawText(10, int(sy + 4), label)
            
        # Draw X-axis labels
        step_x = max(1, len(self.points) // 4)
        for idx in range(0, len(self.points), step_x):
            x, y = self.points[idx]
            if max_x == min_x:
                sx = margin_left + plot_w / 2
            else:
                sx = margin_left + ((x - min_x) / (max_x - min_x)) * plot_w
                
            lbl = self.labels[idx] if idx < len(self.labels) else f"{x:.0f}"
            if idx > 0 and idx < len(self.points) - 1:
                painter.setPen(QPen(QColor(grid_color.red(), grid_color.green(), grid_color.blue(), 80), 1, Qt.PenStyle.DashLine))
                painter.drawLine(int(sx), margin_top, int(sx), margin_top + plot_h)
            painter.setPen(QPen(text_color, 1))
            painter.drawText(int(sx - 15), margin_top + plot_h + 18, lbl)
            
        screen_points = []
        for x, y in self.points:
            if max_x == min_x:
                sx = margin_left + plot_w / 2
            else:
                sx = margin_left + ((x - min_x) / (max_x - min_x)) * plot_w
                
            if max_y == min_y:
                sy = margin_top + plot_h / 2
            else:
                sy = margin_top + plot_h - ((y - min_y) / (max_y - min_y)) * plot_h
            screen_points.append((sx, sy))
            
        # Smooth Bezier Curve Path
        path = QPainterPath()
        if len(screen_points) >= 2:
            path.moveTo(screen_points[0][0], screen_points[0][1])
            for i in range(len(screen_points) - 1):
                p1 = screen_points[i]
                p2 = screen_points[i+1]
                cp1_x = p1[0] + (p2[0] - p1[0]) / 2
                path.cubicTo(cp1_x, p1[1], cp1_x, p2[1], p2[0], p2[1])
        
        # Fill area under curve
        area_path = QPainterPath(path)
        area_path.lineTo(screen_points[-1][0], margin_top + plot_h)
        area_path.lineTo(screen_points[0][0], margin_top + plot_h)
        area_path.closeSubpath()
        
        grad = QLinearGradient(0, margin_top, 0, margin_top + plot_h)
        grad.setColorAt(0, QColor(0, 194, 255, 60))
        grad.setColorAt(1, QColor(0, 194, 255, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(area_path)
        
        # Draw the curve line
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(line_color, 2))
        painter.drawPath(path)
        
        # Draw points
        for idx, (sx, sy) in enumerate(screen_points):
            is_hovered = (idx == self.hovered_idx)
            r = 5 if is_hovered else 3
            dot_color = QColor(255, 255, 255) if is_hovered else accent_color
            painter.setPen(QPen(accent_color, 1))
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(int(sx - r), int(sy - r), int(r * 2), int(r * 2))
            
        # Hover Tooltip
        if self.hovered_idx != -1:
            hx, hy = screen_points[self.hovered_idx]
            x_val, y_val = self.points[self.hovered_idx]
            lbl = self.labels[self.hovered_idx] if self.hovered_idx < len(self.labels) else f"X: {x_val:.1f}"
            
            painter.setPen(QPen(QColor(255, 255, 255, 80), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(hx), margin_top, int(hx), margin_top + plot_h)
            
            tooltip_text = f"{self.x_label}: {lbl}\n{self.y_label}: {y_val:.4f}"
            painter.setFont(QFont("JetBrains Mono, Courier New", 7))
            fm = painter.fontMetrics()
            lines = tooltip_text.split('\n')
            t_w = max(fm.horizontalAdvance(line) for line in lines) + 16
            t_h = fm.height() * len(lines) + 10
            
            tx = hx + 10
            ty = hy - t_h - 10
            if tx + t_w > w:
                tx = hx - t_w - 10
            if ty < 0:
                ty = hy + 10
                
            painter.setPen(QPen(grid_color, 1))
            painter.setBrush(QBrush(QColor(22, 22, 45, 240)))
            painter.drawRoundedRect(int(tx), int(ty), int(t_w), int(t_h), 4, 4)
            
            painter.setPen(QPen(QColor(240, 245, 255), 1))
            for i, line in enumerate(lines):
                painter.drawText(int(tx + 8), int(ty + 13 + i * fm.height()), line)


# ── Stats Loader Background Thread ───────────────────────────────────────────

class _FlywheelDashboardLoader(QThread):
    loaded = pyqtSignal(dict, list, list, dict) # stats, failure_pairs, training_history, quant_data

    def run(self):
        stats = {}
        failure_pairs = []
        training_history = []
        quant_data = {}
        
        try:
            # 0. Load Quantization Comparison Data
            quant_path = "data/quantization_comparison.json"
            if os.path.exists(quant_path):
                try:
                    with open(quant_path, "r", encoding="utf-8") as f:
                        quant_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Error reading {quant_path}: {e}")

            # 1. Gather Trace Logs metrics
            total_traces = 0
            trace_files = glob.glob("data/logs/traces/*.jsonl")
            for fp in trace_files:
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        total_traces += sum(1 for line in f if line.strip())
                except Exception:
                    pass
            stats["total_traces"] = total_traces

            # 2. Gather Curated Dataset Metrics
            thumbs_up = 0
            corrected = 0
            total_curated = 0
            curated_path = "data/training/curated.jsonl"
            
            # Group by prompt key to identify failure pairs
            groups = {}
            
            if os.path.exists(curated_path):
                with open(curated_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            total_curated += 1
                            src = entry.get("source", "")
                            if src == "thumbs_up":
                                thumbs_up += 1
                            elif src == "corrected":
                                corrected += 1
                                
                            # Parse prompt context
                            msgs = entry.get("messages", [])
                            if len(msgs) >= 3:
                                sys_p = msgs[0].get("content", "")
                                user_p = msgs[1].get("content", "")
                                response = msgs[2].get("content", "")
                                
                                key = (sys_p, user_p)
                                if key not in groups:
                                    groups[key] = {"chosen": None, "rejected": None}
                                    
                                if src == "eval_chosen":
                                    groups[key]["chosen"] = response
                                elif src == "eval_rejected":
                                    groups[key]["rejected"] = response
                        except Exception:
                            pass
                            
            stats["total_curated"] = total_curated
            stats["thumbs_up"] = thumbs_up
            stats["corrected"] = corrected
            stats["curation_rate"] = (total_curated / total_traces) if total_traces > 0 else 0.0

            # Filter out populated eval failure pairs
            for (sys_p, user_p), val in groups.items():
                if val["chosen"] and val["rejected"]:
                    failure_pairs.append({
                        "system_prompt": sys_p,
                        "user_msg": user_p,
                        "chosen": val["chosen"],
                        "rejected": val["rejected"]
                    })

            # 3. Read Evaluation History
            eval_reports = []
            report_files = sorted(glob.glob("eval/results/*.jsonl"), key=os.path.getmtime)
            for fp in report_files:
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        line = f.readline()
                        if line:
                            summary = json.loads(line)
                            if summary.get("type") == "summary":
                                eval_reports.append(summary)
                except Exception:
                    pass

            stats["last_eval_score"] = 0.0
            stats["last_eval_avg_score"] = 0.0
            if os.path.exists("data/eval_last.json"):
                try:
                    with open("data/eval_last.json", "r", encoding="utf-8") as f:
                        eval_last = json.load(f)
                        stats["last_eval_score"] = float(eval_last.get("score", 0.0))
                        stats["last_eval_avg_score"] = float(eval_last.get("avg_score", 0.0))
                except Exception:
                    pass
            elif eval_reports:
                stats["last_eval_score"] = float(eval_reports[-1].get("pass_rate", 0.0))
                stats["last_eval_avg_score"] = float(eval_reports[-1].get("avg_score", 0.0))

            stats["eval_reports"] = eval_reports

            # 4. Read Training adapter histories
            history_files = glob.glob("data/adapters/*/train_history.json")
            for hf in history_files:
                try:
                    with open(hf, "r", encoding="utf-8") as f:
                        hist_data = json.load(f)
                        adapter_name = os.path.basename(os.path.dirname(hf))
                        training_history.append({
                            "adapter": adapter_name,
                            "logs": hist_data
                        })
                except Exception:
                    pass

        except Exception as e:
            stats["error"] = str(e)

        self.loaded.emit(stats, failure_pairs, training_history, quant_data)


# ── Flywheel Studio Workspace Widget ─────────────────────────────────────────

class FlywheelStudioWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._active_loader = None
        self._stats_data = {}
        self._failure_pairs = []
        self._training_history = []
        self._quant_data = {}
        
        self._build_ui()
        self.reload_dashboard()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left Column (Telemetry Cards + Actions)
        left_col = QWidget()
        left_col.setFixedWidth(320)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_layout.addWidget(_section("FLYWHEEL DASHBOARD"))

        # Dashboard stats panel
        self._stats_panel = GlowPanel(self.state)
        sp_lay = QVBoxLayout(self._stats_panel)
        sp_lay.setContentsMargins(12, 12, 12, 12)
        sp_lay.setSpacing(8)

        sp_lay.addWidget(_label("Trace Logs Total:", "lbl-muted"))
        self._lbl_total_traces = _label("0", "lbl-accent")
        self._lbl_total_traces.setStyleSheet("font-size: 11pt; font-weight: bold;")
        sp_lay.addWidget(self._lbl_total_traces)

        sp_lay.addWidget(_label("Dataset Volume (Curated):", "lbl-muted"))
        self._lbl_total_curated = _label("0 examples", "lbl-accent")
        self._lbl_total_curated.setStyleSheet("font-size: 11pt; font-weight: bold;")
        sp_lay.addWidget(self._lbl_total_curated)

        sp_lay.addWidget(_label("Curation Capture Rate:", "lbl-muted"))
        self._lbl_curation_rate = _label("0.0%", "lbl-accent")
        self._lbl_curation_rate.setStyleSheet("font-size: 11pt; font-weight: bold;")
        sp_lay.addWidget(self._lbl_curation_rate)

        sp_lay.addWidget(_label("Last Evaluation Pass Rate:", "lbl-muted"))
        self._lbl_eval_score = _label("0.0%", "lbl-accent")
        self._lbl_eval_score.setStyleSheet("font-size: 11pt; font-weight: bold;")
        sp_lay.addWidget(self._lbl_eval_score)

        left_layout.addWidget(self._stats_panel)

        # Detailed Counters Panel
        counters_box = GlowPanel(self.state)
        cp_lay = QVBoxLayout(counters_box)
        cp_lay.setContentsMargins(12, 12, 12, 12)
        cp_lay.setSpacing(6)
        cp_lay.addWidget(_section("CURATION BREAKDOWN"))
        
        self._lbl_thumbs_up = QLabel("Thumbs Up: 0")
        self._lbl_thumbs_up.setObjectName("lbl-muted")
        cp_lay.addWidget(self._lbl_thumbs_up)
        
        self._lbl_corrected = QLabel("Corrections: 0")
        self._lbl_corrected.setObjectName("lbl-muted")
        cp_lay.addWidget(self._lbl_corrected)

        left_layout.addWidget(counters_box)

        # Quick Actions
        actions_box = GlowPanel(self.state)
        ap_lay = QVBoxLayout(actions_box)
        ap_lay.setContentsMargins(12, 12, 12, 12)
        ap_lay.setSpacing(8)
        ap_lay.addWidget(_section("ACTIONS"))

        reload_btn = QPushButton("↻ Refresh Telemetry")
        reload_btn.setObjectName("btn-ghost")
        reload_btn.clicked.connect(self.reload_dashboard)
        ap_lay.addWidget(reload_btn)

        export_sft_btn = QPushButton("Export SFT JSONL")
        export_sft_btn.setObjectName("btn-primary")
        export_sft_btn.clicked.connect(self._export_sft)
        ap_lay.addWidget(export_sft_btn)

        export_dpo_btn = QPushButton("Export DPO JSONL")
        export_dpo_btn.setObjectName("btn-primary")
        export_dpo_btn.clicked.connect(self._export_dpo)
        ap_lay.addWidget(export_dpo_btn)

        left_layout.addWidget(actions_box)
        left_layout.addStretch()
        root.addWidget(left_col)

        # Right Column (Tabbed Charts + Failure Inspector)
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("main-tabs")

        # Tab 1: Charts Playground
        charts_tab = QWidget()
        ct_lay = QHBoxLayout(charts_tab)
        ct_lay.setContentsMargins(8, 8, 8, 8)
        ct_lay.setSpacing(10)

        self._eval_chart = CustomLineChart("Evaluation Trend History", "Run Index", "Score")
        ct_lay.addWidget(self._eval_chart, 1)

        self._loss_chart = CustomLineChart("Training Loss Curve", "Steps/Epochs", "Loss")
        ct_lay.addWidget(self._loss_chart, 1)

        self._tabs.addTab(charts_tab, "Optimization Curves")

        # Tab 2: Quantization Benchmarks (New)
        quant_tab = QWidget()
        qt_lay = QVBoxLayout(quant_tab)
        qt_lay.setContentsMargins(12, 12, 12, 12)
        qt_lay.setSpacing(10)

        quant_header = QWidget()
        qh_lay = QHBoxLayout(quant_header)
        qh_lay.setContentsMargins(0, 0, 0, 0)
        qh_lay.addWidget(_section("QUANTIZATION COMPARISON BENCHMARKS"))
        qh_lay.addStretch()
        
        qh_lay.addWidget(_label("Metric:", "lbl-muted"))
        self._quant_metric_combo = QComboBox()
        self._quant_metric_combo.addItems(["Perplexity Score", "VRAM Usage (MB)", "Token Speed (tok/sec)"])
        self._quant_metric_combo.currentIndexChanged.connect(self._on_quant_metric_changed)
        qh_lay.addWidget(self._quant_metric_combo)
        qt_lay.addWidget(quant_header)

        self._quant_chart = CustomLineChart("Quantization Impact Analysis", "Format", "Value")
        qt_lay.addWidget(self._quant_chart, 1)
        
        self._tabs.addTab(quant_tab, "Quantization Benchmarks")

        # Tab 3: Curated Failure Pairs Inspector
        ft_lay = QVBoxLayout(failures_tab)
        ft_lay.setContentsMargins(12, 12, 12, 12)
        ft_lay.setSpacing(10)

        ft_lay.addWidget(_section("CURATED EVALUATION FAILURE PAIRS"))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left: Failure list
        self._failures_list = QListWidget()
        self._failures_list.setToolTip("Select a curated failed evaluation pair to inspect")
        self._failures_list.currentRowChanged.connect(self._on_failure_selected)
        splitter.addWidget(self._failures_list)

        # Right: Diff view
        diff_panel = QWidget()
        dp_lay = QVBoxLayout(diff_panel)
        dp_lay.setContentsMargins(0, 0, 0, 0)
        dp_lay.setSpacing(6)

        self._lbl_fail_prompt = QLabel("Prompt: Select a failure case")
        self._lbl_fail_prompt.setWordWrap(True)
        self._lbl_fail_prompt.setStyleSheet("font-weight: bold; font-size: 8.5pt;")
        dp_lay.addWidget(self._lbl_fail_prompt)

        body_splitter = QSplitter(Qt.Orientation.Vertical)
        body_splitter.setHandleWidth(1)

        chosen_box = QWidget()
        cb_lay = QVBoxLayout(chosen_box)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.addWidget(QLabel("Expected Good Response (Chosen):"))
        self._chosen_txt = QTextBrowser()
        self._chosen_txt.setStyleSheet(f"font-family: {MONO}; font-size: 8.5pt;")
        cb_lay.addWidget(self._chosen_txt)
        body_splitter.addWidget(chosen_box)

        rejected_box = QWidget()
        rb_lay = QVBoxLayout(rejected_box)
        rb_lay.setContentsMargins(0, 0, 0, 0)
        rb_lay.addWidget(QLabel("Actual Failed Response (Rejected):"))
        self._rejected_txt = QTextBrowser()
        self._rejected_txt.setStyleSheet(f"font-family: {MONO}; font-size: 8.5pt;")
        rb_lay.addWidget(self._rejected_txt)
        body_splitter.addWidget(rejected_box)

        dp_lay.addWidget(body_splitter, 1)
        splitter.addWidget(diff_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        ft_lay.addWidget(splitter, 1)
        self._tabs.addTab(failures_tab, "Eval Failure Pairs Inspector")

        self._tabs.addTab(self._build_leaderboard_tab(), "Leaderboard")

        right_layout.addWidget(self._tabs)
        root.addWidget(right_col, 1)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_dashboard()

    def reload_dashboard(self):
        if self._active_loader and self._active_loader.isRunning():
            return
        
        self._active_loader = _FlywheelDashboardLoader()
        self._active_loader.loaded.connect(self._on_dashboard_loaded)
        self._active_loader.start()

    def _on_dashboard_loaded(self, stats: dict, failure_pairs: list[dict], training_history: list[dict], quant_data: dict):
        self._active_loader = None
        self._stats_data = stats
        self._failure_pairs = failure_pairs
        self._training_history = training_history
        self._quant_data = quant_data

        # Update labels
        self._lbl_total_traces.setText(str(stats.get("total_traces", 0)))
        self._lbl_total_curated.setText(f"{stats.get('total_curated', 0)} examples")
        
        c_rate = stats.get("curation_rate", 0.0)
        self._lbl_curation_rate.setText(f"{c_rate:.2%}")
        
        e_score = stats.get("last_eval_score", 0.0)
        self._lbl_eval_score.setText(f"{e_score:.1%}")

        self._lbl_thumbs_up.setText(f"Thumbs Up: {stats.get('thumbs_up', 0)}")
        self._lbl_corrected.setText(f"Corrections: {stats.get('corrected', 0)}")

        # Populate failures list
        self._failures_list.clear()
        for i, pair in enumerate(failure_pairs):
            user_msg = pair.get("user_msg", "")
            trimmed = user_msg[:30] + "..." if len(user_msg) > 30 else user_msg
            item = QListWidgetItem(f"Pair {i+1}: {trimmed}")
            self._failures_list.addItem(item)

        # Render Evaluation Trend Chart
        eval_reports = stats.get("eval_reports", [])
        if eval_reports:
            chart_points = []
            labels = []
            for idx, r in enumerate(eval_reports):
                rate = r.get("pass_rate", 0.0)
                chart_points.append((float(idx), rate))
                ts = r.get("timestamp", "")
                labels.append(ts[5:10] if len(ts) >= 10 else f"R{idx}")
            self._eval_chart.set_data(chart_points, labels)
        else:
            # Generate simulated mock history trend if empty, to illustrate standard dashboard progression
            self._eval_chart.set_data([], [])

        # Render Loss Curve Chart
        if training_history:
            # Draw curve of the latest training history
            latest_run = training_history[-1]
            logs = latest_run.get("logs", [])
            points = []
            labels = []
            for item in logs:
                if isinstance(item, dict) and "loss" in item:
                    step = item.get("step", 0)
                    loss = item.get("loss", 0.0)
                    points.append((float(step), loss))
                    epoch = item.get("epoch", 0.0)
                    labels.append(f"{epoch:.2f}e")
            self._loss_chart.title = f"Loss Curve: {latest_run['adapter']}"
            self._loss_chart.set_data(points, labels)
        else:
            self._loss_chart.title = "Training Loss Curve"
            self._loss_chart.set_data([], [])

        # Initial Render of Quantization Chart
        self._on_quant_metric_changed()

    def _on_quant_metric_changed(self):
        if not self._quant_data:
            self._quant_chart.set_data([], [])
            return
            
        metric_name = self._quant_metric_combo.currentText()
        # Mapping UI names to JSON keys
        key_map = {
            "Perplexity Score": "perplexity",
            "VRAM Usage (MB)": "vram_mb",
            "Token Speed (tok/sec)": "tps"
        }
        json_key = key_map.get(metric_name, "perplexity")
        
        points = []
        labels = []
        
        # Expecting quant_data to be a list of dicts like: 
        # [{"format": "Q4_K_M", "perplexity": 5.2, "vram_mb": 4500, "tps": 45.5}, ...]
        benchmarks = self._quant_data.get("benchmarks", [])
        for idx, b in enumerate(benchmarks):
            val = b.get(json_key, 0.0)
            points.append((float(idx), float(val)))
            labels.append(b.get("format", f"B{idx}"))
            
        self._quant_chart.set_metric(f"Quantization Analysis: {metric_name}", metric_name)
        self._quant_chart.set_data(points, labels)

    def _on_failure_selected(self, idx: int):
        if idx < 0 or idx >= len(self._failure_pairs):
            self._lbl_fail_prompt.setText("Prompt: Select a failure case")
            self._chosen_txt.clear()
            self._rejected_txt.clear()
            return
            
        pair = self._failure_pairs[idx]
        user_p = pair.get("user_msg", "")
        self._lbl_fail_prompt.setText(f"Prompt: {user_p}")
        self._chosen_txt.setPlainText(pair.get("chosen", ""))
        self._rejected_txt.setPlainText(pair.get("rejected", ""))

    def _build_leaderboard_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_row = QWidget()
        hl = QHBoxLayout(header_row)
        hl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Evaluation Leaderboard")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("btn-secondary")
        refresh_btn.clicked.connect(self._refresh_leaderboard)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(refresh_btn)
        layout.addWidget(header_row)

        self._leaderboard_table = QTableWidget(0, 6)
        self._leaderboard_table.setHorizontalHeaderLabels(
            ["Timestamp", "Model", "Adapter", "Accuracy", "MRR", "Items"]
        )
        self._leaderboard_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._leaderboard_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._leaderboard_table.horizontalHeader().setStretchLastSection(True)
        self._leaderboard_table.itemDoubleClicked.connect(self._open_leaderboard_item)
        layout.addWidget(self._leaderboard_table, 1)

        dpo_row = QWidget()
        dr = QHBoxLayout(dpo_row)
        dr.setContentsMargins(0, 0, 0, 0)
        self._dpo_count_lbl = QLabel("DPO pairs ready: 0")
        self._dpo_count_lbl.setObjectName("lbl-muted")
        export_dpo_btn = QPushButton("Export DPO Dataset")
        export_dpo_btn.setObjectName("btn-primary")
        export_dpo_btn.clicked.connect(self._export_dpo_from_evals)
        dr.addWidget(self._dpo_count_lbl)
        dr.addStretch()
        dr.addWidget(export_dpo_btn)
        layout.addWidget(dpo_row)
        return w

    def _refresh_leaderboard(self):
        from app.utils.training_curator import list_eval_results, get_all_examples
        results = list_eval_results()
        self._leaderboard_table.setRowCount(0)
        for meta in results:
            row = self._leaderboard_table.rowCount()
            self._leaderboard_table.insertRow(row)
            self._leaderboard_table.setItem(row, 0, QTableWidgetItem(meta["timestamp"][:16]))
            self._leaderboard_table.setItem(row, 1, QTableWidgetItem(meta["model_name"]))
            self._leaderboard_table.setItem(row, 2, QTableWidgetItem(meta["adapter_name"] or "base"))
            acc_item = QTableWidgetItem(f"{meta['accuracy']:.1%}")
            acc_item.setForeground(QColor("#2DD4A0") if meta["accuracy"] > 0.7 else QColor("#FFB400"))
            self._leaderboard_table.setItem(row, 3, acc_item)
            self._leaderboard_table.setItem(row, 4, QTableWidgetItem(f"{meta.get('mrr', 0):.3f}"))
            self._leaderboard_table.setItem(row, 5, QTableWidgetItem(str(meta["item_count"])))
            self._leaderboard_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, meta["path"])
        self._leaderboard_table.resizeColumnsToContents()
        chosen = sum(1 for e in get_all_examples() if e.get("source") == "eval_chosen")
        rejected = sum(1 for e in get_all_examples() if e.get("source") == "eval_rejected")
        self._dpo_count_lbl.setText(
            f"DPO pairs ready: {min(chosen, rejected)} (chosen: {chosen}, rejected: {rejected})"
        )

    def _export_dpo_from_evals(self):
        from app.utils.training_curator import export_dpo
        path = export_dpo()
        QMessageBox.information(self, "DPO Export", f"Exported DPO dataset to:\n{path}")

    def _open_leaderboard_item(self, item):
        path = self._leaderboard_table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            detail = json.dumps(data, indent=2)[:3000]
            QMessageBox.information(self, "Eval Report", detail)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _export_sft(self):
        try:
            path = self.state.curator.export_unsloth()
            QMessageBox.information(
                self, "Export Complete",
                f"SFT Dataset exported successfully to Unsloth format:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Export encountered an error:\n{e}")

    def _export_dpo(self):
        try:
            path = self.state.curator.export_dpo()
            QMessageBox.information(
                self, "Export Complete",
                f"DPO Dataset exported successfully to Unsloth format:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Export encountered an error:\n{e}")
