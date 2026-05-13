from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextBrowser, QLineEdit, QPushButton, QSplitter, 
                             QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QGroupBox,
                             QListWidget, QFileDialog)
from PyQt6.QtCore import Qt
from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl — Introspection Environment")
        self.resize(1300, 800)
        
        self.chat_history = []
        self.memory_manager = MemoryManager()
        self.rag_pipeline = RAGPipeline()
        self.current_session_file = None
        self.agentic_thread = None
        
        self.setup_ui()
        self.refresh_session_list()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # --- Left Panel: Session & Knowledge Manager ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("<b>Saved Sessions</b>"))
        self.session_list = QListWidget()
        self.session_list.itemDoubleClicked.connect(self.load_session)
        left_layout.addWidget(self.session_list)
        
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_new.clicked.connect(self.new_session)
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_session)
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_save)
        left_layout.addLayout(btn_layout)
        
        left_layout.addWidget(QLabel("<b>Knowledge Base (RAG)</b>"))
        self.kb_list = QListWidget()
        left_layout.addWidget(self.kb_list)
        self.btn_ingest = QPushButton("Ingest Document")
        self.btn_ingest.clicked.connect(self.ingest_document)
        left_layout.addWidget(self.btn_ingest)
        
        # --- Center Area: Thoughts and Chat ---
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        thought_panel = QWidget()
        thought_layout = QVBoxLayout(thought_panel)
        thought_layout.addWidget(QLabel("<b>Thought Stream (Introspection)</b>"))
        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet("background-color: #1A1A1A; color: #A0A0A0; font-family: 'Consolas';")
        thought_layout.addWidget(self.thought_display)
        
        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.addWidget(QLabel("<b>Final Response</b>"))
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        chat_layout.addWidget(self.chat_display)
        
        # Input row
        input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type prompt OR fake thought...")
        self.user_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Generate")
        self.send_button.clicked.connect(self.send_message)
        
        self.force_thought_button = QPushButton("Force Thought")
        self.force_thought_button.setStyleSheet("background-color: #5A2A2A;")
        self.force_thought_button.clicked.connect(self.force_thought)
        
        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.force_thought_button)
        input_layout.addWidget(self.send_button)
        chat_layout.addLayout(input_layout)
        
        # Agentic Mode row
        agentic_layout = QHBoxLayout()
        self.agentic_button = QPushButton("▶  Run Agentic Loop")
        self.agentic_button.setStyleSheet("background-color: #2A3A5A; font-weight: bold;")
        self.agentic_button.clicked.connect(self.start_agentic_loop)
        
        self.stop_agentic_button = QPushButton("■  Stop Loop")
        self.stop_agentic_button.setStyleSheet("background-color: #3A1A1A;")
        self.stop_agentic_button.setEnabled(False)
        self.stop_agentic_button.clicked.connect(self.stop_agentic_loop)
        
        self.agentic_status = QLabel("Agentic: Idle")
        self.agentic_status.setStyleSheet("color: #666666; font-size: 9pt;")
        
        agentic_layout.addWidget(self.agentic_button)
        agentic_layout.addWidget(self.stop_agentic_button)
        agentic_layout.addWidget(self.agentic_status)
        chat_layout.addLayout(agentic_layout)
        
        center_splitter.addWidget(thought_panel)
        center_splitter.addWidget(chat_panel)
        center_splitter.setSizes([300, 500])
        
        # --- Right Area: Configuration ---
        config_panel = QWidget()
        config_layout = QVBoxLayout(config_panel)
        
        config_layout.addWidget(QLabel("<b>System Prompt</b>"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlainText("You are a helpful, analytical AI assistant.")
        self.system_prompt_input.setMaximumHeight(200)
        config_layout.addWidget(self.system_prompt_input)
        
        hyper_group = QGroupBox("Generation Hyperparameters")
        hyper_layout = QVBoxLayout(hyper_group)
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.7)
        temp_layout.addWidget(self.temp_spin)
        hyper_layout.addLayout(temp_layout)
        
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(QLabel("Top-P:"))
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.95)
        top_p_layout.addWidget(self.top_p_spin)
        hyper_layout.addLayout(top_p_layout)
        
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Max Tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1, 4096)
        self.tokens_spin.setValue(1024)
        tokens_layout.addWidget(self.tokens_spin)
        hyper_layout.addLayout(tokens_layout)
        
        config_layout.addWidget(hyper_group)
        
        agentic_hint = QLabel(
            "<b>Agentic Mode</b><br>"
            "<small>Edit <code>core/agentic_loop.py</code> to change the stop condition "
            "and what gets injected between iterations. "
            "Hot-reloaded on every loop.</small>"
        )
        agentic_hint.setWordWrap(True)
        agentic_hint.setStyleSheet("color: #666; padding: 8px;")
        config_layout.addWidget(agentic_hint)
        config_layout.addStretch()
        
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(center_splitter)
        main_splitter.addWidget(config_panel)
        main_splitter.setSizes([250, 750, 300])

    # ── Session Methods ───────────────────────────────────────────────────────

    def refresh_session_list(self):
        self.session_list.clear()
        for f in self.memory_manager.list_sessions():
            self.session_list.addItem(f)

    def new_session(self):
        self.chat_history = []
        self.current_session_file = None
        self.chat_display.clear()
        self.thought_display.clear()
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
        self.chat_display.clear()
        self.thought_display.clear()
        self.chat_display.append(f"<i>Loaded session {filename}</i>")
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self.chat_display.append(f"<b>User:</b> {content}")
            elif role == "assistant":
                if "<think>" in content and "</think>" in content:
                    parts = content.split("</think>")
                    thought = parts[0].replace("<think>", "").strip()
                    resp = parts[1].strip()
                    self.thought_display.append(f"<b>[Past Thought]</b>\n{thought}\n")
                    self.chat_display.append(f"<b>Assistant:</b> {resp}\n")
                else:
                    self.chat_display.append(f"<b>Assistant:</b> {content}\n")

    def ingest_document(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Document", "", "All Files (*.*)")
        if filepath:
            self.chat_display.append(f"<i>Ingesting {filepath}... Please wait.</i>")
            chunks = self.rag_pipeline.ingest_file(filepath)
            filename = filepath.split("/")[-1]
            if chunks > 0:
                self.kb_list.addItem(f"{filename} ({chunks} chunks)")
                self.chat_display.append(f"<i>Successfully added {filename} to Vector DB!</i>")
            else:
                self.chat_display.append(f"<i><font color='red'>Failed to read text from {filename}.</font></i>")

    # ── Generation Methods ────────────────────────────────────────────────────

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

    def force_thought(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self.thought_display.append(f"\n<b>[FORCED THOUGHT]</b>\n{text}")
        self.chat_history.append({"role": "assistant", "content": f"<think>\n{text}\n</think>"})

    def send_message(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self._set_controls_enabled(False)
        
        self.chat_display.append(f"<b>User:</b> {text}")
        self.chat_display.append("<b>Assistant:</b> ")
        self.thought_display.append(f"\n--- Generation for: '{text[:20]}...' ---")
        
        self.chat_history.append({"role": "user", "content": text})
        
        retrieved_chunks = self.rag_pipeline.retrieve(text, top_k=3)
        system_prompt = self.system_prompt_input.toPlainText()
        if retrieved_chunks:
            system_prompt += "\n\n# RELEVANT KNOWLEDGE:\n"
            for chunk in retrieved_chunks:
                system_prompt += f"- {chunk}\n"
        
        self.thread = LLMThread(system_prompt, self.chat_history, self._get_hyperparams(), retrieved_chunks)
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
        self.thread.error_occurred.connect(self.handle_error)
        self.thread.start()

    def handle_thought_token(self, token):
        cursor = self.thought_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self.thought_display.setTextCursor(cursor)

    def handle_chat_token(self, token):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self.chat_display.setTextCursor(cursor)

    def handle_generation_finished(self, final_thought, final_response):
        full = f"<think>\n{final_thought}\n</think>\n{final_response}" if final_thought else final_response
        self.chat_history.append({"role": "assistant", "content": full})
        self.chat_display.append("\n")
        self._set_controls_enabled(True)
        self.user_input.setFocus()

    def handle_error(self, error_msg):
        self.chat_display.append(f"<br><font color='red'>{error_msg}</font><br>")
        self._set_controls_enabled(True)
        self.agentic_status.setText("Agentic: Error")

    # ── Agentic Loop Methods ──────────────────────────────────────────────────

    def start_agentic_loop(self):
        if not self.chat_history:
            self.chat_display.append(
                "<font color='orange'><i>Send at least one message first to seed the agentic loop.</i></font>"
            )
            return
        
        self._set_controls_enabled(False)
        self.stop_agentic_button.setEnabled(True)
        self.agentic_status.setText("Agentic: Running…")
        
        self.thought_display.append("\n" + "="*50)
        self.thought_display.append("  AGENTIC LOOP STARTED")
        self.thought_display.append("="*50)
        
        system_prompt = self.system_prompt_input.toPlainText()
        self.agentic_thread = AgenticThread(system_prompt, self.chat_history, self._get_hyperparams())
        self.agentic_thread.new_thought_token.connect(self.handle_thought_token)
        self.agentic_thread.new_chat_token.connect(self.handle_chat_token)
        self.agentic_thread.iteration_finished.connect(self.handle_agentic_iteration)
        self.agentic_thread.loop_finished.connect(self.handle_agentic_finished)
        self.agentic_thread.error_occurred.connect(self.handle_error)
        self.agentic_thread.start()

    def stop_agentic_loop(self):
        if self.agentic_thread:
            self.agentic_thread.request_stop()
        self.agentic_status.setText("Agentic: Stopping…")
        self.stop_agentic_button.setEnabled(False)

    def handle_agentic_iteration(self, iteration: int, thought: str, response: str):
        full = f"<think>\n{thought}\n</think>\n{response}" if thought else response
        self.chat_history.append({"role": "assistant", "content": full})
        self.agentic_status.setText(f"Agentic: Iteration {iteration + 1} done")

    def handle_agentic_finished(self, total_iterations: int):
        self._set_controls_enabled(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText(f"Agentic: Done ({total_iterations} iterations)")
        self.chat_display.append(
            f"\n<i><font color='#4A9A4A'>— Agentic loop finished after {total_iterations} iteration(s) —</font></i>\n"
        )
        self.user_input.setFocus()
