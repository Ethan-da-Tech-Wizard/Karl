from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextBrowser, QLineEdit, QPushButton, QSplitter,
                             QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QGroupBox,
                             QListWidget, QFileDialog, QCheckBox, QMessageBox, QDialog,
                             QDialogButtonBox, QComboBox, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline
from app.utils.training_curator import (
    save_example, get_stats, export_unsloth, export_dpo, get_dpo_stats
)
from core.workflows import list_workflows, get_workflow
from core.prompt_templates import get_template, list_templates


# ── Upgrade worker — runs hardware check off the UI thread ────────────────────
class UpgradeCheckThread(QThread):
    upgrade_available = pyqtSignal(dict, dict)  # entry, profile
    no_upgrade = pyqtSignal()

    def run(self):
        try:
            from app.engine.upgrade_manager import check_for_upgrade
            entry, profile = check_for_upgrade()
            if entry:
                self.upgrade_available.emit(entry, profile)
            else:
                self.no_upgrade.emit()
        except Exception:
            self.no_upgrade.emit()


class UpgradeDownloadThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, entry):
        super().__init__()
        self.entry = entry

    def run(self):
        try:
            from app.engine.upgrade_manager import perform_upgrade
            path = perform_upgrade(self.entry, progress_callback=lambda n, t: self.progress.emit(n, t))
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl — Introspection Environment")
        self.resize(1400, 860)

        self.chat_history = []
        self.memory_manager = MemoryManager()
        self.rag_pipeline = RAGPipeline()
        self.current_session_file = None
        self.agentic_thread = None
        self._pending_upgrade_entry = None
        # M11: track last exchange for rating
        self._last_user_msg = ""
        self._last_response = ""
        # Workflow tracking
        self._last_workflow = "general_chat"
        self._last_template = "reasoning_minimal"
        self._last_latency = 0.0
        self._last_chunks_used: list = []
        self._last_logprobs: list = []
        self._last_logit_bias: dict = {}

        self.setup_ui()
        self.refresh_session_list()
        self._run_upgrade_check()
        self._refresh_curator_stats()

    # ── UI Construction ───────────────────────────────────────────────────────

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)

        # LEFT: Sessions + RAG
        left_panel = QWidget()
        ll = QVBoxLayout(left_panel)
        ll.addWidget(QLabel("<b>Saved Sessions</b>"))
        self.session_list = QListWidget()
        self.session_list.itemDoubleClicked.connect(self.load_session)
        ll.addWidget(self.session_list)
        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("New"); self.btn_new.clicked.connect(self.new_session)
        self.btn_save = QPushButton("Save"); self.btn_save.clicked.connect(self.save_session)
        btn_row.addWidget(self.btn_new); btn_row.addWidget(self.btn_save)
        ll.addLayout(btn_row)
        # M16: Branching controls
        branch_row = QHBoxLayout()
        self.btn_fork = QPushButton("⑂ Fork"); self.btn_fork.clicked.connect(self.fork_session)
        self.btn_fork.setToolTip("Clone the current session to a new branch file")
        self.btn_version = QPushButton("📌 Save Version"); self.btn_version.clicked.connect(self.save_version)
        self.btn_version.setToolTip("Snapshot the session with a named tag")
        branch_row.addWidget(self.btn_fork); branch_row.addWidget(self.btn_version)
        ll.addLayout(branch_row)
        ll.addWidget(QLabel("<b>Knowledge Base (RAG)</b>"))
        self.kb_list = QListWidget()
        ll.addWidget(self.kb_list)
        self.btn_ingest = QPushButton("Ingest Document")
        self.btn_ingest.clicked.connect(self.ingest_document)
        ll.addWidget(self.btn_ingest)

        # CENTER: Raw Archive + Thought Stream + Chat
        center_splitter = QSplitter(Qt.Orientation.Vertical)

        # M7: Raw Token Archive (toggleable)
        raw_panel = QWidget()
        raw_layout = QVBoxLayout(raw_panel)
        raw_header = QHBoxLayout()
        raw_header.addWidget(QLabel("<b>Raw Token Archive</b>"))
        self.raw_toggle = QCheckBox("Show")
        self.raw_toggle.setChecked(False)
        self.raw_toggle.stateChanged.connect(self._toggle_raw_panel)
        raw_header.addWidget(self.raw_toggle)
        raw_header.addStretch()
        raw_layout.addLayout(raw_header)
        self.raw_display = QTextBrowser()
        self.raw_display.setStyleSheet("background-color: #0D0D0D; color: #4A7A4A; font-family: 'Consolas'; font-size: 8pt;")
        self.raw_display.setVisible(False)
        raw_layout.addWidget(self.raw_display)

        thought_panel = QWidget()
        tl = QVBoxLayout(thought_panel)
        thought_label = QLabel("🔬  Diagnostic Lane  (reasoning trace)")
        thought_label.setStyleSheet("font-weight: bold; color: #6B7280; font-size: 9pt; padding: 4px 0;")
        tl.addWidget(thought_label)
        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet(
            "background-color: #111827; color: #9CA3AF; font-family: 'Consolas'; "
            "border: 1px solid #374151; border-radius: 4px; padding: 6px;"
        )
        tl.addWidget(self.thought_display)

        chat_panel = QWidget()
        cl = QVBoxLayout(chat_panel)

        # Model loader row
        model_row = QHBoxLayout()
        self.model_path_label = QLabel("No model loaded")
        self.model_path_label.setStyleSheet("color: #9CA3AF; font-size: 9pt;")
        self.model_path_label.setWordWrap(False)
        load_model_btn = QPushButton("Load Model")
        load_model_btn.setFixedWidth(110)
        load_model_btn.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold;")
        load_model_btn.clicked.connect(self._pick_and_load_model)
        model_row.addWidget(self.model_path_label, stretch=1)
        model_row.addWidget(load_model_btn)
        cl.addLayout(model_row)

        chat_top_row = QHBoxLayout()
        chat_label = QLabel("💬  Final Response")
        chat_label.setStyleSheet("font-weight: bold; color: #F3F4F6; font-size: 10pt; padding: 4px 0;")
        clear_chat_btn = QPushButton("Clear Chat")
        clear_chat_btn.setFixedWidth(90)
        clear_chat_btn.setStyleSheet("background-color: #374151; color: #D1D5DB;")
        clear_chat_btn.clicked.connect(self._clear_chat)
        chat_top_row.addWidget(chat_label, stretch=1)
        chat_top_row.addWidget(clear_chat_btn)
        cl.addLayout(chat_top_row)
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setStyleSheet(
            "background-color: #1F2937; color: #F3F4F6; font-family: 'Segoe UI', sans-serif; "
            "border: 1px solid #4B5563; border-radius: 4px; padding: 6px;"
        )
        cl.addWidget(self.chat_display)

        # Input row
        input_row = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type prompt OR fake thought...")
        self.user_input.returnPressed.connect(self.send_message)
        self.force_thought_button = QPushButton("Force Thought")
        self.force_thought_button.setStyleSheet("background-color: #5A2A2A;")
        self.force_thought_button.clicked.connect(self.force_thought)
        self.send_button = QPushButton("Generate")
        self.send_button.clicked.connect(self.send_message)
        input_row.addWidget(self.user_input)
        input_row.addWidget(self.force_thought_button)
        input_row.addWidget(self.send_button)
        cl.addLayout(input_row)

        # Workflow report + heatmap toggle row
        report_row = QHBoxLayout()
        self.report_toggle = QCheckBox("Workflow Report")
        self.report_toggle.setChecked(True)
        self.report_toggle.stateChanged.connect(self._toggle_report_panel)
        report_row.addWidget(self.report_toggle)
        self.heatmap_toggle = QCheckBox("Confidence Heatmap")
        self.heatmap_toggle.setChecked(False)
        self.heatmap_toggle.stateChanged.connect(self._toggle_heatmap_panel)
        report_row.addWidget(self.heatmap_toggle)
        report_row.addStretch()
        cl.addLayout(report_row)

        self.report_display = QTextBrowser()
        self.report_display.setMaximumHeight(80)
        self.report_display.setStyleSheet(
            "background-color: #0F1117; color: #6EE7B7; font-family: 'Consolas'; "
            "font-size: 8pt; border: 1px solid #1F2937; border-radius: 3px; padding: 4px;"
        )
        self.report_display.setPlaceholderText("Workflow report will appear here after each generation.")
        cl.addWidget(self.report_display)

        # M21: Confidence Heatmap
        self.heatmap_display = QTextBrowser()
        self.heatmap_display.setMaximumHeight(100)
        self.heatmap_display.setStyleSheet(
            "background-color: #0A0A0A; font-family: 'Consolas'; font-size: 9pt; "
            "border: 1px solid #1F2937; border-radius: 3px; padding: 4px;"
        )
        self.heatmap_display.setPlaceholderText("Token confidence heatmap appears here after generation.")
        self.heatmap_display.setVisible(False)
        cl.addWidget(self.heatmap_display)

        # M11: Rating row — appears after generation
        rating_row = QHBoxLayout()
        rating_label = QLabel("Rate response:")
        rating_label.setStyleSheet("color: #666; font-size: 9pt;")
        self.thumbs_up_btn = QPushButton("👍  Good")
        self.thumbs_up_btn.setStyleSheet("background-color: #1A3A1A; font-size: 9pt; padding: 2px 8px;")
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_up_btn.clicked.connect(self._rate_thumbs_up)
        self.thumbs_down_btn = QPushButton("👎  Fix")
        self.thumbs_down_btn.setStyleSheet("background-color: #3A1A1A; font-size: 9pt; padding: 2px 8px;")
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_down_btn.clicked.connect(self._rate_thumbs_down)
        rating_row.addWidget(rating_label)
        rating_row.addWidget(self.thumbs_up_btn)
        rating_row.addWidget(self.thumbs_down_btn)
        rating_row.addStretch()
        cl.addLayout(rating_row)

        # Token confidence bar (logprobs)
        conf_row = QHBoxLayout()
        conf_lbl = QLabel("Token confidence:")
        conf_lbl.setStyleSheet("color: #6B7280; font-size: 9pt;")
        self.confidence_bar = QLabel("—")
        self.confidence_bar.setStyleSheet(
            "color: #10B981; font-family: 'Consolas'; font-size: 9pt; "
            "background-color: #0F172A; padding: 2px 6px; border-radius: 3px;"
        )
        self.confidence_bar.setToolTip(
            "Average logprob of response tokens. "
            "Higher (less negative) = more confident.\n"
            "Requires logprobs support in the loaded model."
        )
        conf_row.addWidget(conf_lbl)
        conf_row.addWidget(self.confidence_bar)
        diff_btn = QPushButton("🔍 Prompt Diff")
        diff_btn.setToolTip("Open the side-by-side trace diff viewer (M17)")
        diff_btn.setStyleSheet("font-size: 9pt; padding: 2px 8px;")
        diff_btn.clicked.connect(self._open_diff_viewer)
        conf_row.addWidget(diff_btn)

        eval_btn = QPushButton("📊 Eval")
        eval_btn.setToolTip("Open the Eval Dashboard — history and live runner (M18/M19)")
        eval_btn.setStyleSheet("font-size: 9pt; padding: 2px 8px;")
        eval_btn.clicked.connect(self._open_eval_dashboard)
        conf_row.addWidget(eval_btn)
        conf_row.addStretch()
        cl.addLayout(conf_row)

        # M9: Auto-Loop + Agentic controls row
        agentic_row = QHBoxLayout()
        self.auto_loop_toggle = QCheckBox("Auto-Loop")
        self.auto_loop_toggle.setToolTip("When ON, each response automatically feeds into the next generation.")
        self.auto_loop_toggle.stateChanged.connect(self._on_auto_loop_toggled)
        self.agentic_button = QPushButton("▶  Run Agentic Loop")
        self.agentic_button.setStyleSheet("background-color: #2A3A5A; font-weight: bold;")
        self.agentic_button.clicked.connect(self.start_agentic_loop)
        self.stop_agentic_button = QPushButton("■  Stop")
        self.stop_agentic_button.setStyleSheet("background-color: #3A1A1A;")
        self.stop_agentic_button.setEnabled(False)
        self.stop_agentic_button.clicked.connect(self.stop_agentic_loop)
        self.agentic_status = QLabel("Agentic: Idle")
        self.agentic_status.setStyleSheet("color: #666; font-size: 9pt;")
        agentic_row.addWidget(self.auto_loop_toggle)
        agentic_row.addWidget(self.agentic_button)
        agentic_row.addWidget(self.stop_agentic_button)
        agentic_row.addWidget(self.agentic_status)
        cl.addLayout(agentic_row)

        center_splitter.addWidget(raw_panel)
        center_splitter.addWidget(thought_panel)
        center_splitter.addWidget(chat_panel)
        center_splitter.setSizes([0, 280, 500])

        # RIGHT: Config
        config_panel = QWidget()
        cfg = QVBoxLayout(config_panel)
        cfg.addWidget(QLabel("<b>System Prompt</b>"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlainText(
            "You are a helpful, friendly AI assistant. "
            "Answer questions clearly and concisely."
        )
        self.system_prompt_input.setMaximumHeight(180)
        cfg.addWidget(self.system_prompt_input)

        # Workflow + Template selectors
        mode_group = QGroupBox("Workflow Mode")
        mode_group.setStyleSheet("QGroupBox { font-weight: bold; color: #60A5FA; }")
        ml = QVBoxLayout(mode_group)

        wf_row = QHBoxLayout()
        wf_row.addWidget(QLabel("Workflow:"))
        self.workflow_combo = QComboBox()
        for wf_name, wf_label in list_workflows():
            self.workflow_combo.addItem(wf_label, wf_name)
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        wf_row.addWidget(self.workflow_combo)
        ml.addLayout(wf_row)

        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        for tpl in list_templates():
            self.template_combo.addItem(tpl)
        tpl_row.addWidget(self.template_combo)
        ml.addLayout(tpl_row)

        rag_row = QHBoxLayout()
        rag_row.addWidget(QLabel("RAG top-k:"))
        self.rag_topk_spin = QSpinBox()
        self.rag_topk_spin.setRange(0, 10)
        self.rag_topk_spin.setValue(3)
        rag_row.addWidget(self.rag_topk_spin)
        ml.addLayout(rag_row)

        self.ctx_headers_check = QCheckBox("Contextual chunk headers")
        self.ctx_headers_check.setToolTip(
            "Prepend [Source: file | Chunk N] to each retrieved chunk for model citation."
        )
        self.ctx_headers_check.stateChanged.connect(self._on_headers_toggled)
        ml.addWidget(self.ctx_headers_check)

        cfg.addWidget(mode_group)
        hyper_group = QGroupBox("Generation Hyperparameters")
        hl = QVBoxLayout(hyper_group)

        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperature:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0); self.temp_spin.setSingleStep(0.1); self.temp_spin.setValue(0.7)
        temp_row.addWidget(self.temp_spin); hl.addLayout(temp_row)

        top_p_row = QHBoxLayout()
        top_p_row.addWidget(QLabel("Top-P:"))
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0); self.top_p_spin.setSingleStep(0.05); self.top_p_spin.setValue(0.95)
        top_p_row.addWidget(self.top_p_spin); hl.addLayout(top_p_row)

        tok_row = QHBoxLayout()
        tok_row.addWidget(QLabel("Max Tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1, 4096); self.tokens_spin.setValue(512)
        tok_row.addWidget(self.tokens_spin); hl.addLayout(tok_row)
        cfg.addWidget(hyper_group)

        # M8: Upgrade notification area
        self.upgrade_label = QLabel("")
        self.upgrade_label.setWordWrap(True)
        self.upgrade_label.setStyleSheet("color: #AAAAFF; font-size: 9pt; padding: 4px;")
        self.upgrade_label.setVisible(False)
        cfg.addWidget(self.upgrade_label)
        self.upgrade_button = QPushButton("⬆  Upgrade Karl")
        self.upgrade_button.setStyleSheet("background-color: #2A2A5A; font-weight: bold;")
        self.upgrade_button.setVisible(False)
        self.upgrade_button.clicked.connect(self._confirm_upgrade)
        cfg.addWidget(self.upgrade_button)

        # M11: Curator stats + export
        curator_group = QGroupBox("Training Data Curator")
        curator_group.setStyleSheet("QGroupBox { font-weight: bold; color: #8B8BFF; }")
        cl2 = QVBoxLayout(curator_group)
        self.curator_stats_label = QLabel("Examples: 0  (👍 0  ✏️ 0)")
        self.curator_stats_label.setStyleSheet("font-size: 9pt; color: #AAA;")
        cl2.addWidget(self.curator_stats_label)
        export_btn = QPushButton("📦  Export SFT (Unsloth)")
        export_btn.setStyleSheet("background-color: #1A3A1A;")
        export_btn.clicked.connect(self._export_training_data)
        cl2.addWidget(export_btn)
        dpo_export_btn = QPushButton("⚖️  Export DPO Pairs")
        dpo_export_btn.setStyleSheet("background-color: #1A2A3A;")
        dpo_export_btn.setToolTip("Export chosen/rejected pairs for DPO training (TRL DPOTrainer format)")
        dpo_export_btn.clicked.connect(self._export_dpo_data)
        cl2.addWidget(dpo_export_btn)
        cfg.addWidget(curator_group)

        # M20: Logit Bias Editor
        bias_group = QGroupBox("Logit Bias  (token: ±bias)")
        bias_group.setStyleSheet("QGroupBox { font-weight: bold; color: #F472B6; }")
        bl = QVBoxLayout(bias_group)
        bias_hint = QLabel(
            "<small>One entry per line: <code>word: +5.0</code> or <code>word: -10.0</code><br>"
            "Boosts (+) or bans (-) tokens at inference time.</small>"
        )
        bias_hint.setWordWrap(True)
        bias_hint.setStyleSheet("color: #6B7280; font-size: 8pt;")
        bl.addWidget(bias_hint)
        self.logit_bias_input = QTextEdit()
        self.logit_bias_input.setMaximumHeight(80)
        self.logit_bias_input.setPlaceholderText("Example:\njson: +3.0\nsorry: -5.0")
        self.logit_bias_input.setStyleSheet(
            "background: #0F172A; color: #F9A8D4; font-family: 'Consolas'; "
            "font-size: 9pt; border: 1px solid #374151; border-radius: 3px;"
        )
        bl.addWidget(self.logit_bias_input)
        cfg.addWidget(bias_group)

        hint = QLabel("<small><b>Agentic core:</b> edit <code>core/agentic_loop.py</code> — hot-reloaded per iteration.</small>")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; padding: 6px;")
        cfg.addWidget(hint)
        cfg.addStretch()

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(center_splitter)
        main_splitter.addWidget(config_panel)
        main_splitter.setSizes([230, 820, 310])

    # ── Upgrade (M8 + M10) ────────────────────────────────────────────────────

    def _pick_and_load_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select GGUF Model", "data/models", "GGUF Models (*.gguf);;All Files (*.*)"
        )
        if not path:
            return
        try:
            from app.engine.model_loader import ModelLoader
            ModelLoader.reset_instance()
            ModelLoader.get_instance(model_path=path)
            short = path.split("/")[-1].split("\\")[-1]
            self.model_path_label.setText(f"Model: {short}")
            self.model_path_label.setStyleSheet("color: #34D399; font-size: 9pt;")
            self._clear_chat()
            self.chat_display.append(f"<font color='#34D399'><i>Model loaded: {short} — chat history cleared.</i></font>")
        except Exception as e:
            QMessageBox.critical(self, "Model Load Failed", str(e))

    def _clear_chat(self):
        self.chat_history = []
        self.chat_display.clear()
        self.thought_display.clear()
        self._last_user_msg = ""
        self._last_response = ""
        self._last_logprobs = []

    def _run_upgrade_check(self):
        self._upgrade_check_thread = UpgradeCheckThread()
        self._upgrade_check_thread.upgrade_available.connect(self._on_upgrade_available)
        self._upgrade_check_thread.start()

    def _on_upgrade_available(self, entry, profile):
        self._pending_upgrade_entry = entry
        self.upgrade_label.setText(
            f"Hardware upgrade available!\n"
            f"RAM: {profile['ram_gb']} GB | VRAM: {profile['vram_gb']} GB\n"
            f"→ {entry['name']} (Tier {entry['tier']})"
        )
        self.upgrade_label.setVisible(True)
        self.upgrade_button.setVisible(True)

    def _confirm_upgrade(self):
        if not self._pending_upgrade_entry:
            return
        reply = QMessageBox.question(
            self, "Upgrade Karl",
            f"Download and switch to:\n{self._pending_upgrade_entry['name']}\n\nThis will be committed to GitHub. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.upgrade_button.setEnabled(False)
            self.upgrade_label.setText("Downloading… this may take several minutes.")
            self._dl_thread = UpgradeDownloadThread(self._pending_upgrade_entry)
            self._dl_thread.finished.connect(self._on_upgrade_complete)
            self._dl_thread.error.connect(self._on_upgrade_error)
            self._dl_thread.start()

    def _on_upgrade_complete(self, path):
        self.upgrade_label.setText(f"✅ Upgraded! Restart Karl to use the new model.\n({path})")
        self.upgrade_button.setVisible(False)

    def _on_upgrade_error(self, msg):
        self.upgrade_label.setText(f"❌ Upgrade failed: {msg}")
        self.upgrade_button.setEnabled(True)

    # ── Raw Archive Toggle (M7) ───────────────────────────────────────────────

    def _toggle_raw_panel(self, state):
        self.raw_display.setVisible(bool(state))

    def _toggle_report_panel(self, state):
        self.report_display.setVisible(bool(state))

    # ── Workflow / Template handlers ───────────────────────────────────────────

    def _on_workflow_changed(self, index):
        """Sync template combo to workflow default when workflow changes."""
        wf_name = self.workflow_combo.itemData(index)
        try:
            wf_cfg = get_workflow(wf_name)
            default_tpl = wf_cfg.get("template", "reasoning_minimal")
            # Select the matching template in the combo
            for i in range(self.template_combo.count()):
                if self.template_combo.itemText(i) == default_tpl:
                    self.template_combo.setCurrentIndex(i)
                    break
            # Update RAG top-k to workflow default
            self.rag_topk_spin.setValue(wf_cfg.get("rag_top_k", 3))
        except KeyError:
            pass

    def _on_headers_toggled(self, state):
        """Toggle contextual chunk headers on the RAG pipeline."""
        self.rag_pipeline.contextual_headers = bool(state)

    def _get_current_workflow_name(self) -> str:
        idx = self.workflow_combo.currentIndex()
        return self.workflow_combo.itemData(idx) or "general_chat"

    def _get_current_template_name(self) -> str:
        return self.template_combo.currentText() or "reasoning_minimal"

    def _update_report_panel(self, workflow: str, template: str, chunks: list, latency: float, status: str = ""):
        """Render a one-line workflow report into the report display."""
        chunk_count = len(chunks)
        sources = list({c.split("]")[0].replace("[Source: ", "") for c in chunks if "[Source:" in c})
        source_str = ", ".join(sources) if sources else f"{chunk_count} chunk(s)"
        msg = (
            f"workflow={workflow}  template={template}  "
            f"rag_chunks={chunk_count}  "
            f"{'sources=[' + source_str + ']  ' if chunk_count else ''}"
            f"latency={latency:.1f}s  "
            f"{status}"
        )
        self.report_display.setPlainText(msg)

    def _on_auto_loop_toggled(self, state):
        if state:
            self.send_button.setText("Send + Loop")
        else:
            self.send_button.setText("Generate")

    # ── Sessions ──────────────────────────────────────────────────────────────

    def refresh_session_list(self):
        self.session_list.clear()
        for f in self.memory_manager.list_sessions():
            self.session_list.addItem(f)

    def new_session(self):
        self.chat_history = []
        self.current_session_file = None
        self.chat_display.clear()
        self.thought_display.clear()
        self.raw_display.clear()
        self.chat_display.append("<i>Started new session.</i>")

    def save_session(self):
        if not self.chat_history:
            return
        sys_prompt = self.system_prompt_input.toPlainText()
        self.current_session_file = self.memory_manager.save_session(
            self.chat_history, sys_prompt, self.current_session_file
        )
        self.refresh_session_list()
        self.chat_display.append(f"<i>Session saved as {self.current_session_file}</i>")

    def load_session(self, item):
        filename = item.text()
        sys_prompt, history = self.memory_manager.load_session(filename)
        self.system_prompt_input.setPlainText(sys_prompt)
        self.chat_history = history
        self.current_session_file = filename
        self.chat_display.clear(); self.thought_display.clear(); self.raw_display.clear()
        self.chat_display.append(f"<i>Loaded session {filename}</i>")
        for msg in history:
            role, content = msg.get("role", ""), msg.get("content", "")
            if role == "user":
                self.chat_display.append(f"<b>User:</b> {content}")
            elif role == "assistant":
                if "<think>" in content and "</think>" in content:
                    thought = content.split("</think>")[0].replace("<think>", "").strip()
                    resp = content.split("</think>")[1].strip()
                    self.thought_display.append(f"<b>[Past Thought]</b>\n{thought}\n")
                    self.chat_display.append(f"<b>Assistant:</b> {resp}\n")
                else:
                    self.chat_display.append(f"<b>Assistant:</b> {content}\n")

    # ── M16: Session Branching ────────────────────────────────────────────────

    def fork_session(self):
        if not self.current_session_file:
            QMessageBox.warning(self, "Fork Session", "Save the session first, then fork it.")
            return
        try:
            new_file = self.memory_manager.fork_session(self.current_session_file)
            self.current_session_file = new_file
            self.refresh_session_list()
            self.chat_display.append(f"<i>⑂ Forked to <b>{new_file}</b> — you are now on the fork.</i>")
        except Exception as e:
            QMessageBox.critical(self, "Fork Error", str(e))

    def save_version(self):
        from PyQt6.QtWidgets import QInputDialog
        tag, ok = QInputDialog.getText(
            self, "Save Version", "Enter a short version tag (e.g. v2-with-rag):"
        )
        if not ok or not tag.strip():
            return
        try:
            new_file = self.memory_manager.save_version(
                self.chat_history,
                self.system_prompt_input.toPlainText(),
                self.current_session_file,
                tag.strip(),
            )
            self.refresh_session_list()
            self.chat_display.append(f"<i>📌 Version saved as <b>{new_file}</b></i>")
        except Exception as e:
            QMessageBox.critical(self, "Save Version Error", str(e))

    def ingest_document(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Document", "", "All Files (*.*)")
        if filepath:
            self.chat_display.append(f"<i>Ingesting {filepath}…</i>")
            chunks = self.rag_pipeline.ingest_file(filepath)
            filename = filepath.replace("\\", "/").split("/")[-1]
            if chunks > 0:
                self.kb_list.addItem(f"{filename} ({chunks} chunks)")
                self.chat_display.append(f"<i>Added {filename} to Vector DB!</i>")
            else:
                self.chat_display.append(f"<i><font color='red'>Could not read {filename}.</font></i>")

    # ── Generation helpers ────────────────────────────────────────────────────

    def _get_hyperparams(self):
        return {
            "temperature": self.temp_spin.value(),
            "top_p": self.top_p_spin.value(),
            "max_tokens": self.tokens_spin.value()
        }

    def _set_controls_enabled(self, enabled: bool):
        self.user_input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.force_thought_button.setEnabled(enabled)
        self.btn_ingest.setEnabled(enabled)
        self.agentic_button.setEnabled(enabled)
        self.auto_loop_toggle.setEnabled(enabled)

    def force_thought(self):
        text = self.user_input.text().strip()
        if not text: return
        self.user_input.clear()
        self.thought_display.append(f"\n<b>[FORCED THOUGHT]</b>\n{text}")
        self.chat_history.append({"role": "assistant", "content": f"<think>\n{text}\n</think>"})

    # ── Single Generation ─────────────────────────────────────────────────────

    def send_message(self):
        import time as _time
        text = self.user_input.text().strip()
        if not text: return
        self.user_input.clear()
        self._last_user_msg = text          # M11: track for rating
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_down_btn.setEnabled(False)
        self._set_controls_enabled(False)
        self.stop_agentic_button.setEnabled(self.auto_loop_toggle.isChecked())

        self.confidence_bar.setText("…computing…")
        self.confidence_bar.setStyleSheet(
            "color: #6B7280; font-family: 'Consolas'; font-size: 9pt; "
            "background-color: #0F172A; padding: 2px 6px; border-radius: 3px;"
        )
        self.chat_display.append(f"<b>User:</b> {text}")
        self.chat_display.append("<b>Assistant:</b> ")
        self.thought_display.append(f"\n--- Generation for: '{text[:20]}...' ---")

        self.chat_history.append({"role": "user", "content": text})

        # ── Workflow-aware system prompt construction ──────────────────────────
        wf_name   = self._get_current_workflow_name()
        tpl_name  = self._get_current_template_name()
        top_k     = self.rag_topk_spin.value()

        retrieved = self.rag_pipeline.retrieve(text, top_k=top_k) if top_k > 0 else []
        rag_context = "\n\n".join(retrieved) if retrieved else ""

        # Build system prompt via template if not general_chat, else use text box
        if wf_name != "general_chat":
            sys_prompt = get_template(tpl_name, rag_context=rag_context)
        else:
            sys_prompt = self.system_prompt_input.toPlainText()
            if retrieved:
                sys_prompt += "\n\n# RELEVANT KNOWLEDGE:\n" + "".join(f"- {c}\n" for c in retrieved)

        # Resolve and cache everything needed for this generation + any continuations
        self._last_workflow = wf_name
        self._last_template = tpl_name
        self._last_chunks_used = retrieved
        self._last_logit_bias = self._parse_logit_bias()
        self._gen_start_time = _time.time()

        self.thread = LLMThread(
            sys_prompt, self.chat_history, self._get_hyperparams(), retrieved,
            logit_bias=self._last_logit_bias,
            workflow=wf_name,
            template=tpl_name,
        )
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.new_raw_token.connect(self.handle_raw_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
        self.thread.token_logprobs_ready.connect(self.handle_token_logprobs)
        self.thread.error_occurred.connect(self.handle_error)
        self.thread.start()

    def handle_thought_token(self, token):
        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End); c.insertText(token)
        self.thought_display.setTextCursor(c)

    def handle_chat_token(self, token):
        c = self.chat_display.textCursor()
        c.movePosition(c.MoveOperation.End); c.insertText(token)
        self.chat_display.setTextCursor(c)

    def handle_raw_token(self, token):
        if self.raw_display.isVisible():
            c = self.raw_display.textCursor()
            c.movePosition(c.MoveOperation.End); c.insertText(token)
            self.raw_display.setTextCursor(c)

    def _fire_generation(self, history_override=None, start_in_thought=False):
        """Spin up a new LLMThread. history_override lets continuations bypass chat_history."""
        sys_prompt = self.system_prompt_input.toPlainText()
        history = history_override if history_override is not None else self.chat_history
        self.thread = LLMThread(
            sys_prompt, history, self._get_hyperparams(),
            start_in_thought=start_in_thought,
            logit_bias=getattr(self, "_last_logit_bias", {}),
            workflow=getattr(self, "_last_workflow", "general_chat"),
            template=getattr(self, "_last_template", "reasoning_minimal"),
        )
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.new_raw_token.connect(self.handle_raw_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
        self.thread.token_logprobs_ready.connect(self.handle_token_logprobs)
        self.thread.error_occurred.connect(self.handle_error)
        self.thread.start()

    def handle_generation_finished(self, final_thought, final_response, truncated=False, ended_in_thought=False):
        # Store ONLY the response — think blocks are introspection data.
        self.chat_history.append({"role": "assistant", "content": final_response})
        self._last_response = final_response  # M11: for rating

        if truncated:
            self.new_thought_token_direct("\n[\u21bb continuing...]\n")
            continuation_history = list(self.chat_history) + [{
                "role": "user", "content": "Continue."
            }]
            self._fire_generation(
                history_override=continuation_history,
                start_in_thought=ended_in_thought
            )
            return

        self.chat_display.append("\n")
        # M11: enable rating buttons now that generation is complete
        self.thumbs_up_btn.setEnabled(bool(self._last_user_msg))
        self.thumbs_down_btn.setEnabled(bool(self._last_user_msg))

        # Update workflow report panel
        import time as _time
        latency = _time.time() - getattr(self, "_gen_start_time", _time.time())
        self._last_latency = latency
        self._update_report_panel(
            workflow=self._last_workflow,
            template=self._last_template,
            chunks=self._last_chunks_used,
            latency=latency,
        )


        if self.auto_loop_toggle.isChecked():
            self.start_agentic_loop()
        else:
            self._set_controls_enabled(True)
            self.stop_agentic_button.setEnabled(False)
            self.user_input.setFocus()

    def new_thought_token_direct(self, text):
        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End); c.insertText(text)
        self.thought_display.setTextCursor(c)

    def handle_error(self, msg):
        self.chat_display.append(f"<br><font color='red'>{msg}</font><br>")
        self._set_controls_enabled(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText("Agentic: Error")

    def handle_token_logprobs(self, logprobs: list):
        """Update the confidence bar and heatmap with per-token logprob data."""
        if not logprobs:
            return
        import math
        self._last_logprobs = logprobs
        values = [lp for _, lp in logprobs if lp is not None and not math.isnan(lp)]
        if not values:
            return
        mean_lp = sum(values) / len(values)
        if mean_lp >= -0.5:
            colour = "#10B981"
        elif mean_lp >= -1.5:
            colour = "#F59E0B"
        else:
            colour = "#EF4444"
        self.confidence_bar.setText(f"avg logprob {mean_lp:.3f}  ({len(logprobs)} tokens)")
        self.confidence_bar.setStyleSheet(
            f"color: {colour}; font-family: 'Consolas'; font-size: 9pt; "
            "background-color: #0F172A; padding: 2px 6px; border-radius: 3px;"
        )
        if self.heatmap_display.isVisible():
            self._render_heatmap(logprobs)

    def _render_heatmap(self, logprobs: list):
        """Render HTML spans coloured by token confidence into the heatmap display."""
        import math
        import html as _html

        def _lp_to_colour(lp: float) -> str:
            # Map logprob 0..−5 → green..red via linear interpolation
            clamped = max(-5.0, min(0.0, lp))
            t = -clamped / 5.0   # 0 = certain (green), 1 = uncertain (red)
            r = int(16  + t * (239 - 16))
            g = int(185 - t * (185 - 68))
            b = int(129 - t * (129 - 68))
            return f"#{r:02X}{g:02X}{b:02X}"

        parts = []
        for token_str, lp in logprobs:
            if lp is None or math.isnan(lp):
                parts.append(_html.escape(token_str))
                continue
            colour = _lp_to_colour(lp)
            escaped = _html.escape(token_str).replace(" ", "&nbsp;")
            tip = f"logprob={lp:.3f}"
            parts.append(f'<span style="color:{colour}" title="{tip}">{escaped}</span>')

        self.heatmap_display.setHtml(
            '<div style="font-family:Consolas;font-size:9pt;line-height:1.6;">'
            + "".join(parts)
            + "</div>"
        )

    def _toggle_heatmap_panel(self, state):
        self.heatmap_display.setVisible(bool(state))
        if state and hasattr(self, "_last_logprobs") and self._last_logprobs:
            self._render_heatmap(self._last_logprobs)

    # ── M17: Prompt Diff Viewer ───────────────────────────────────────────────

    def _open_diff_viewer(self):
        from app.ui.diff_viewer import DiffViewerDialog
        dlg = DiffViewerDialog(self)
        dlg.exec()

    # ── M18/M19: Eval Dashboard ───────────────────────────────────────────────

    def _open_eval_dashboard(self):
        from app.ui.eval_dashboard import EvalDashboardDialog
        dlg = EvalDashboardDialog(self)
        dlg.exec()

    # ── M20: Logit Bias ───────────────────────────────────────────────────────

    def _parse_logit_bias(self) -> dict:
        """
        Parse the logit bias text area into {token_id: float}.

        Format: one entry per line — "word: +5.0" or "word: -3.0".
        Token strings are tokenised to their first token ID via the loaded model.
        Lines that can't be parsed are silently skipped.
        """
        raw = self.logit_bias_input.toPlainText().strip()
        if not raw:
            return {}
        try:
            from app.engine.model_loader import ModelLoader
            llm = ModelLoader.get_instance()
        except Exception:
            return {}

        result = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            token_str, _, bias_str = line.partition(":")
            token_str = token_str.strip()
            try:
                bias_val = float(bias_str.strip())
            except ValueError:
                continue
            try:
                token_ids = llm.tokenize(token_str.encode("utf-8"))
                if token_ids:
                    result[token_ids[0]] = bias_val
            except Exception:
                pass
        return result

    # ── Agentic Loop ──────────────────────────────────────────────────────────

    def start_agentic_loop(self):
        if not self.chat_history:
            self.chat_display.append("<font color='orange'><i>Send a message first to seed the loop.</i></font>")
            return
        self._set_controls_enabled(False)
        self.stop_agentic_button.setEnabled(True)
        self.agentic_status.setText("Agentic: Running…")
        self.thought_display.append("\n" + "="*50 + "\n  AGENTIC LOOP STARTED\n" + "="*50)

        self.agentic_thread = AgenticThread(
            self.system_prompt_input.toPlainText(),
            self.chat_history,
            self._get_hyperparams()
        )
        self.agentic_thread.new_thought_token.connect(self.handle_thought_token)
        self.agentic_thread.new_chat_token.connect(self.handle_chat_token)
        self.agentic_thread.new_raw_token.connect(self.handle_raw_token)
        self.agentic_thread.iteration_finished.connect(self.handle_agentic_iteration)
        self.agentic_thread.loop_finished.connect(self.handle_agentic_finished)
        self.agentic_thread.error_occurred.connect(self.handle_error)
        self.agentic_thread.start()

    def stop_agentic_loop(self):
        if self.agentic_thread:
            self.agentic_thread.request_stop()
        self.auto_loop_toggle.setChecked(False)
        self.agentic_status.setText("Agentic: Stopping…")
        self.stop_agentic_button.setEnabled(False)

    def handle_agentic_iteration(self, iteration, thought, response):
        # Store only the response, not the think block
        self.chat_history.append({"role": "assistant", "content": response})
        self.agentic_status.setText(f"Agentic: Iteration {iteration + 1} done")

    def handle_agentic_finished(self, total):
        self._set_controls_enabled(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText(f"Agentic: Done ({total} iterations)")
        self.chat_display.append(
            f"\n<i><font color='#4A9A4A'>— Agentic loop finished after {total} iteration(s) —</font></i>\n"
        )
        self.user_input.setFocus()

    # ── Training Data Curator (M11) ───────────────────────────────────────────

    def _rate_thumbs_up(self):
        if not self._last_user_msg or not self._last_response:
            return
        save_example(
            system_prompt=self.system_prompt_input.toPlainText(),
            user_msg=self._last_user_msg,
            good_response=self._last_response,
            source="thumbs_up"
        )
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_up_btn.setText("✅ Saved")
        self._refresh_curator_stats()

    def _rate_thumbs_down(self):
        """Open correction dialog, then save the corrected response."""
        if not self._last_user_msg:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Correct this response")
        dialog.resize(600, 300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"<b>Prompt:</b> {self._last_user_msg[:120]}"))
        layout.addWidget(QLabel("<b>Write the correct response:</b>"))
        editor = QTextEdit()
        editor.setPlaceholderText("Type the ideal response here...")
        editor.setPlainText(self._last_response)
        layout.addWidget(editor)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            corrected = editor.toPlainText().strip()
            if corrected:
                save_example(
                    system_prompt=self.system_prompt_input.toPlainText(),
                    user_msg=self._last_user_msg,
                    good_response=corrected,
                    source="corrected",
                    rejected_response=self._last_response,
                )
                self.thumbs_up_btn.setEnabled(False)
                self.thumbs_down_btn.setEnabled(False)
                self.thumbs_down_btn.setText("✅ Fixed")
                self._refresh_curator_stats()

    def _refresh_curator_stats(self):
        try:
            stats = get_stats()
            self.curator_stats_label.setText(
                f"Examples: {stats['total']}  (👍 {stats['thumbs_up']}  ✏️ {stats['corrected']})"
            )
        except Exception:
            pass

    def _export_training_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SFT Training Data", "data/training/export_unsloth.jsonl",
            "JSONL Files (*.jsonl)"
        )
        if path:
            out_path, count = export_unsloth(path)
            QMessageBox.information(
                self, "Export Complete",
                f"Exported {count} examples to:\n{out_path}\n\n"
                f"Ready for Unsloth fine-tuning."
            )

    def _export_dpo_data(self):
        dpo_stats = get_dpo_stats()
        if dpo_stats["dpo_pairs"] == 0:
            QMessageBox.information(
                self, "No DPO Pairs",
                "No DPO pairs found.\n\n"
                "DPO pairs are created when you click 👎 Fix and provide a correction. "
                "The original (rejected) response is stored automatically."
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export DPO Pairs", "data/training/export_dpo.jsonl",
            "JSONL Files (*.jsonl)"
        )
        if path:
            out_path, count = export_dpo(path)
            QMessageBox.information(
                self, "DPO Export Complete",
                f"Exported {count} chosen/rejected pairs to:\n{out_path}\n\n"
                f"Compatible with TRL DPOTrainer and Unsloth DPO."
            )
