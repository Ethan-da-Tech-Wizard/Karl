from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextBrowser, QLineEdit, QPushButton, QSplitter,
                             QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QGroupBox,
                             QListWidget, QFileDialog, QCheckBox, QMessageBox, QDialog,
                             QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline
from app.utils.training_curator import save_example, get_stats, export_unsloth


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
        thought_label = QLabel("🧠  Thought Stream")
        thought_label.setStyleSheet("font-weight: bold; color: #A0A0A0; font-size: 10pt; padding: 4px 0;")
        tl.addWidget(thought_label)
        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet(
            "background-color: #111827; color: #9CA3AF; font-family: 'Consolas'; "
            "border: 1px solid #374151; border-radius: 4px; padding: 6px;"
        )
        tl.addWidget(self.thought_display)

        chat_panel = QWidget()
        cl = QVBoxLayout(chat_panel)
        chat_label = QLabel("💬  Final Response")
        chat_label.setStyleSheet("font-weight: bold; color: #F3F4F6; font-size: 10pt; padding: 4px 0;")
        cl.addWidget(chat_label)
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
            "You are a precise, analytical AI assistant.\n"
            "When reasoning inside <think> blocks: be direct, avoid repeating 'Wait' or 'But wait', "
            "and do not re-state conclusions you have already reached.\n"
            "Your final answer after </think> should be clean and concise."
        )
        self.system_prompt_input.setMaximumHeight(180)
        cfg.addWidget(self.system_prompt_input)

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
        export_btn = QPushButton("📦  Export for Unsloth")
        export_btn.setStyleSheet("background-color: #1A3A1A;")
        export_btn.clicked.connect(self._export_training_data)
        cl2.addWidget(export_btn)
        cfg.addWidget(curator_group)

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

    # ── Auto-Loop Toggle (M9) ─────────────────────────────────────────────────

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
        text = self.user_input.text().strip()
        if not text: return
        self.user_input.clear()
        self._last_user_msg = text          # M11: track for rating
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_down_btn.setEnabled(False)
        self._set_controls_enabled(False)
        self.stop_agentic_button.setEnabled(self.auto_loop_toggle.isChecked())

        self.chat_display.append(f"<b>User:</b> {text}")
        self.chat_display.append("<b>Assistant:</b> ")
        self.thought_display.append(f"\n--- Generation for: '{text[:20]}...' ---")

        self.chat_history.append({"role": "user", "content": text})

        retrieved = self.rag_pipeline.retrieve(text, top_k=3)
        sys_prompt = self.system_prompt_input.toPlainText()
        if retrieved:
            sys_prompt += "\n\n# RELEVANT KNOWLEDGE:\n" + "".join(f"- {c}\n" for c in retrieved)

        self.thread = LLMThread(sys_prompt, self.chat_history, self._get_hyperparams(), retrieved)
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.new_raw_token.connect(self.handle_raw_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
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
        self.thread = LLMThread(sys_prompt, history, self._get_hyperparams(),
                                start_in_thought=start_in_thought)
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.new_raw_token.connect(self.handle_raw_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
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
                    source="corrected"
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
            self, "Export Training Data", "data/training/export_unsloth.jsonl",
            "JSONL Files (*.jsonl)"
        )
        if path:
            out_path, count = export_unsloth(path)
            QMessageBox.information(
                self, "Export Complete",
                f"Exported {count} examples to:\n{out_path}\n\n"
                f"Ready for Unsloth fine-tuning."
            )
