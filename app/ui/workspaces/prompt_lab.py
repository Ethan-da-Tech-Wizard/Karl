"""
Prompt Lab — side-by-side prompt engineering workspace.

Left prompt (A) vs right prompt (B): run both, compare outputs.
All runs are logged to trace.
"""

from __future__ import annotations

import logging

import json
import os
import re
import html
import difflib

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QTextEdit, QLabel,
    QFrame, QComboBox, QListWidget, QLineEdit,
    QMessageBox, QTabWidget, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from app.ui.themes import MONO


logger = logging.getLogger("karl.prompt_lab")


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def generate_char_diff_html(a: str, b: str) -> str:
    """
    Computes character-level diff and returns HTML with highlighted additions/deletions.
    Preserves text spaces and newlines using pre-wrap wrapper.
    """
    diff = difflib.ndiff(list(a), list(b))
    html_parts = [
        f"<div style='font-family:{MONO}; font-size:9.5pt; color:#E4E4F0; line-height:1.5; white-space:pre-wrap;'>"
    ]
    
    current_op = None
    current_chunk = []
    
    def flush():
        nonlocal current_op, current_chunk
        if not current_chunk:
            return
        text = "".join(current_chunk)
        escaped = html.escape(text)
        if current_op == '-':
            # Deletion (in A, not in B)
            html_parts.append(
                f"<span style='background-color: rgba(240, 80, 80, 0.2); "
                f"color: #F05050; text-decoration: line-through;'>{escaped}</span>"
            )
        elif current_op == '+':
            # Addition (in B, not in A)
            html_parts.append(
                f"<span style='background-color: rgba(45, 212, 160, 0.2); "
                f"color: #2DD4A0;'>{escaped}</span>"
            )
        else:
            # Unchanged
            html_parts.append(escaped)
        current_chunk = []
        
    for code in diff:
        op = code[0]
        char = code[2:]
        if op == '?':
            continue
            
        if op != current_op:
            flush()
            current_op = op
            
        current_chunk.append(char)
        
    flush()
    html_parts.append("</div>")
    return "".join(html_parts)


# ── single-shot run thread (thin wrapper around ModelLoader) ─────────────────

class _RunThread(QThread):
    token = pyqtSignal(str)
    done  = pyqtSignal(str, dict)
    live_stats = pyqtSignal(int, float)
    error = pyqtSignal(str)

    def __init__(self, system_prompt: str, user_prompt: str, hyperparams: dict,
                 model_name: str | None = None, adapter_name: str | None = None,
                 retrieved_chunks: list[str] | None = None):
        super().__init__()
        self.system_prompt = system_prompt
        self.user_prompt   = user_prompt
        self.hyperparams   = hyperparams
        self.model_name    = model_name
        self.adapter_name  = adapter_name
        self.retrieved_chunks = retrieved_chunks or []

    def run(self):
        try:
            from app.engine.model_loader import ModelLoader
            import core.interaction_loop
            import importlib
            import time
            importlib.reload(core.interaction_loop)

            model_path = None
            if self.model_name:
                model_path = os.path.join("data", "models", self.model_name)

            llm = ModelLoader.get_instance(model_path=model_path, adapter_name=self.adapter_name)
            history = [{"role": "user", "content": self.user_prompt}]
            
            system_prompt = self.system_prompt
            if self.retrieved_chunks:
                context_str = "\n".join(self.retrieved_chunks)
                if "{rag_context}" in system_prompt:
                    system_prompt = system_prompt.replace("{rag_context}", context_str)
                else:
                    system_prompt += "\n\nRetrieved Context:\n" + context_str

            prompt  = core.interaction_loop.build_prompt(system_prompt, history)
            logger.debug(f"system_prompt={repr(self.system_prompt)} model={repr(ModelLoader.model_name())} active_adapter={repr(getattr(ModelLoader, '_active_adapter', None))} prompt={repr(prompt)}")

            # Tokenize prompt to get accurate prompt token count
            prompt_tokens = len(llm.tokenize(prompt.encode('utf-8')))

            start_time = time.time()
            first_token_time = None
            full = ""
            gen_token_count = 0
            for chunk in llm(
                prompt,
                max_tokens=self.hyperparams.get("max_tokens", 1024),
                temperature=self.hyperparams.get("temperature", 0.7),
                top_p=self.hyperparams.get("top_p", 0.95),
                stream=True,
                stop=["<|im_end|>", "<|endoftext|>", "<|im_start|>"],
                echo=False,
            ):
                if "choices" not in chunk:
                    continue
                text = chunk["choices"][0].get("text", "")
                if text:
                    if first_token_time is None:
                        first_token_time = time.time()
                    
                    chunk_tokens = len(llm.tokenize(text.encode('utf-8'), add_bos=False))
                    gen_token_count += chunk_tokens
                    elapsed = time.time() - first_token_time
                    speed = gen_token_count / elapsed if elapsed > 0 else 0.0
                    self.live_stats.emit(gen_token_count, speed)
                    
                    full += text
                    self.token.emit(text)

            end_time = time.time()
            prefill_time = (first_token_time - start_time) if first_token_time is not None else (end_time - start_time)
            if prefill_time <= 0:
                prefill_time = 0.001
            prefill_tps = prompt_tokens / prefill_time

            generation_time = (end_time - first_token_time) if first_token_time is not None else 0.0
            generation_tokens = len(llm.tokenize(full.encode('utf-8'), add_bos=False))
            if generation_time <= 0:
                generation_tps = generation_tokens / 0.001 if generation_tokens > 0 else 0.0
            else:
                generation_tps = generation_tokens / generation_time

            total_time = end_time - start_time
            total_tokens = prompt_tokens + generation_tokens
            total_tps = total_tokens / total_time if total_time > 0 else 0.0

            diagnostics = {
                "prompt_tokens": prompt_tokens,
                "prefill_time": prefill_time,
                "prefill_tps": prefill_tps,
                "generation_tokens": generation_tokens,
                "generation_time": generation_time,
                "generation_tps": generation_tps,
                "total_time": total_time,
                "total_tps": total_tps,
            }

            # strip think block from shown output
            from core.cognitive_parser import parse_thought_stream
            _, response = parse_thought_stream(full)
            self.done.emit(response, diagnostics)

        except Exception as e:
            self.error.emit(str(e))


# ── single prompt column ──────────────────────────────────────────────────────

class _PromptColumn(QWidget):
    run_requested = pyqtSignal(str, str)   # (label, user_text)
    generation_done = pyqtSignal(str, dict)      # response text, diagnostics
    generation_failed = pyqtSignal()

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.label = label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(_section(f"PROMPT  {label}"))

        self._model_combo = QComboBox()
        self._model_combo.setToolTip(f"Select model/adapter combination for Column {self.label}")
        layout.addWidget(self._model_combo)

        # RAG and Loop configurations
        cb_row = QWidget()
        cb_layout = QHBoxLayout(cb_row)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.setSpacing(10)

        self._rag_check = QCheckBox("Use RAG")
        self._rag_check.setToolTip(f"Enable Retrieval-Augmented Generation for Column {self.label}")
        cb_layout.addWidget(self._rag_check)

        self._loop_check = QCheckBox("Enable Loop")
        self._loop_check.setToolTip(f"Enable Multi-turn Agentic Loop for Column {self.label}")
        cb_layout.addWidget(self._loop_check)

        cb_layout.addStretch()
        layout.addWidget(cb_row)

        self._system_edit = QTextEdit()
        self._system_edit.setPlaceholderText("system prompt (optional)...")
        self._system_edit.setFixedHeight(60)
        self._system_edit.setToolTip(f"Edit system prompt instructions for Column {self.label}")
        layout.addWidget(self._system_edit)

        self._user_edit = QTextEdit()
        self._user_edit.setPlaceholderText("user message...")
        self._user_edit.setFixedHeight(80)
        self._user_edit.setToolTip(f"Edit user prompt message for Column {self.label}")
        layout.addWidget(self._user_edit)

        out_hdr = QWidget()
        out_hdr_layout = QHBoxLayout(out_hdr)
        out_hdr_layout.setContentsMargins(0, 0, 0, 0)
        out_hdr_layout.setSpacing(6)
        out_hdr_layout.addWidget(_section(f"OUTPUT  {label}"))
        
        self._stats_lbl = QLabel("")
        self._stats_lbl.setObjectName("lbl-muted")
        self._stats_lbl.setStyleSheet("font-size: 8pt; font-weight: normal;")
        out_hdr_layout.addWidget(self._stats_lbl)
        out_hdr_layout.addStretch()
        layout.addWidget(out_hdr)

        self._output = QTextBrowser()
        self._output.setPlaceholderText("output will stream here...")
        self._output.setToolTip(f"Model generation output for Column {self.label}")
        layout.addWidget(self._output, 1)

        btn = QPushButton(f"▶ run {label}")
        btn.setToolTip(f"Run generation using settings in Column {self.label}")
        btn.clicked.connect(self._emit_run)
        layout.addWidget(btn)

        self._thread = None
        self._last_agentic_response = ""
        self._last_agentic_diagnostics = {}
        self._refresh_model_combo()

    def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool:
        import json
        import os
        config_path = os.path.join("data", "adapters", adapter_name, "adapter_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                base_model = config.get("base_model_name_or_path", "").lower()
                model_fn = model_filename.lower()
                if "1.5b" in model_fn and "1.5b" in base_model:
                    return True
                if "8b" in model_fn and "8b" in base_model:
                    return True
            except Exception:
                pass
        # Fallback to simple sub-string matching on name
        if "1.5b" in model_filename.lower() and "1.5b" in adapter_name.lower():
            return True
        if "8b" in model_filename.lower() and "8b" in adapter_name.lower():
            return True
        return False

    def _refresh_model_combo(self):
        self._model_combo.blockSignals(True)
        current_data = self._model_combo.itemData(self._model_combo.currentIndex())
        self._model_combo.clear()
        
        import os
        adapters_dir = "data/adapters"
        adapters = []
        if os.path.exists(adapters_dir):
            try:
                for d in sorted(os.listdir(adapters_dir)):
                    d_path = os.path.join(adapters_dir, d)
                    if os.path.isdir(d_path):
                        files_in_dir = os.listdir(d_path)
                        if any(f.endswith(".gguf") or f.endswith(".bin") for f in files_in_dir):
                            adapters.append(d)
            except Exception as e:
                logger.warning(f"Error scanning adapters for Column {self.label}: {e}")

        models_dir = "data/models"
        files = []
        if os.path.exists(models_dir):
            files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
            
        for f in sorted(files):
            # Base model
            self._model_combo.addItem(f, {"model": f, "adapter": None})
            # List compatible adapters
            for adapter in adapters:
                if self._is_adapter_compatible(f, adapter):
                    self._model_combo.addItem(f"{f} ({adapter})", {"model": f, "adapter": adapter})
                    
        # Restore selection
        if current_data:
            found = False
            for idx in range(self._model_combo.count()):
                d = self._model_combo.itemData(idx)
                if isinstance(d, dict) and d.get("model") == current_data.get("model") and d.get("adapter") == current_data.get("adapter"):
                    self._model_combo.setCurrentIndex(idx)
                    found = True
                    break
            if not found and self._model_combo.count() > 0:
                self._model_combo.setCurrentIndex(0)
        else:
            # Fall back to matching the active model and adapter from ModelLoader
            from app.engine.model_loader import ModelLoader
            active_model = getattr(ModelLoader, "_model_name", None)
            active_adapter = getattr(ModelLoader, "_active_adapter", None)
            found = False
            for idx in range(self._model_combo.count()):
                d = self._model_combo.itemData(idx)
                if isinstance(d, dict) and d.get("model") == active_model and d.get("adapter") == active_adapter:
                    self._model_combo.setCurrentIndex(idx)
                    found = True
                    break
            if not found and self._model_combo.count() > 0:
                self._model_combo.setCurrentIndex(0)
                
        self._model_combo.blockSignals(False)

    def select_model_and_adapter(self, model_name: str, adapter_name: str | None):
        self._model_combo.blockSignals(True)
        for idx in range(self._model_combo.count()):
            d = self._model_combo.itemData(idx)
            if isinstance(d, dict) and d.get("model") == model_name and d.get("adapter") == adapter_name:
                self._model_combo.setCurrentIndex(idx)
                break
        self._model_combo.blockSignals(False)

    def _emit_run(self):
        self.run_requested.emit(self.label, self._user_edit.toPlainText().strip())

    def system_text(self) -> str:
        return self._system_edit.toPlainText().strip()

    def user_text(self) -> str:
        return self._user_edit.toPlainText().strip()

    def set_system_text(self, text: str):
        self._system_edit.setPlainText(text)

    def set_user_text(self, text: str):
        self._user_edit.setPlainText(text)

    def clear_output(self):
        self._output.clear()
        self._stats_lbl.setText("")

    def start_run(self, hyperparams: dict):
        user = self.user_text()
        if not user:
            return
        self._output.clear()
        self._output.setPlainText("generating...")
        self._stats_lbl.setText("")
        
        self._last_agentic_response = ""
        self._last_agentic_diagnostics = {}
        
        # Get selected model and adapter
        model_data = self._model_combo.itemData(self._model_combo.currentIndex())
        if model_data:
            model_name = model_data.get("model")
            adapter_name = model_data.get("adapter")
        else:
            model_name = None
            adapter_name = None

        # RAG retrieval
        chunks = []
        if self._rag_check.isChecked() and hasattr(self, "state") and self.state.rag.total_chunks > 0:
            top_k = getattr(self.state, "rag_top_k", 3)
            threshold = getattr(self.state, "rag_threshold", 0.0)
            retrieved_metadata = self.state.rag.retrieve_with_metadata(
                user,
                top_k=top_k
            )
            if threshold > 0.0:
                retrieved_metadata = [r for r in retrieved_metadata if r["distance"] <= threshold]
            
            if retrieved_metadata:
                sources_text = "\n[Retrieved Context Sources:\n"
                for r in retrieved_metadata:
                    sources_text += f" - {r['source_file']} (distance: {r['distance']:.3f})\n"
                    chunk_text = r["text"]
                    if getattr(self.state.rag, "contextual_headers", False):
                        header = f"[Source: {r['source_file']} | Chunk {r['chunk_id']}]\n"
                        chunk_text = header + chunk_text
                    chunks.append(chunk_text)
                sources_text += "]\n\n"
                self._output.setPlainText("generating...\n" + sources_text)

        if self._loop_check.isChecked():
            from app.engine.agentic_thread import AgenticThread
            initial_history = [{"role": "user", "content": user}]
            self._thread = AgenticThread(
                system_prompt=self.system_text(),
                initial_history=initial_history,
                hyperparams=hyperparams,
                retrieved_chunks=chunks,
                adapter_name=adapter_name,
                model_name=model_name
            )
            self._thread.new_thought_token.connect(self._on_token)
            self._thread.new_chat_token.connect(self._on_token)
            self._thread.live_stats.connect(self._on_live_stats)
            self._thread.iteration_finished.connect(self._on_agentic_iteration)
            self._thread.loop_finished.connect(self._on_agentic_loop_finished)
            self._thread.error_occurred.connect(self._on_error)
        else:
            self._thread = _RunThread(
                system_prompt=self.system_text(),
                user_prompt=user,
                hyperparams=hyperparams,
                model_name=model_name,
                adapter_name=adapter_name,
                retrieved_chunks=chunks
            )
            self._thread.token.connect(self._on_token)
            self._thread.live_stats.connect(self._on_live_stats)
            self._thread.done.connect(self._on_done)
            self._thread.error.connect(self._on_error)

        self._thread.start()

    def _on_token(self, token: str):
        from PyQt6.QtGui import QTextCursor
        curr_text = self._output.toPlainText()
        if curr_text == "generating...":
            self._output.clear()
        elif curr_text.startswith("generating...\n"):
            self._output.setPlainText(curr_text[len("generating...\n"):])
        c = self._output.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        c.insertText(token)
        self._output.setTextCursor(c)
        self._output.ensureCursorVisible()

    def _on_agentic_iteration(self, index: int, thought: str, response: str, diagnostics: dict):
        self._last_agentic_response = response
        self._last_agentic_diagnostics = diagnostics

    def _on_agentic_loop_finished(self, total_iterations: int):
        self._on_done(self._last_agentic_response, self._last_agentic_diagnostics)

    def _on_live_stats(self, count: int, speed: float):
        self._stats_lbl.setText(f"({count} tokens · {speed:.1f} t/s)")

    def _on_done(self, response: str, diagnostics: dict):
        self._stats_lbl.setText("")
        self._output.append(
            f"\n\n[Prefill: {diagnostics.get('prompt_tokens', 0)} tok in {diagnostics.get('prefill_time', 0):.2f}s @ {diagnostics.get('prefill_tps', 0):.1f} t/s | "
            f"Gen: {diagnostics.get('generation_tokens', 0)} tok in {diagnostics.get('generation_time', 0):.2f}s @ {diagnostics.get('generation_tps', 0):.1f} t/s]"
        )
        self.generation_done.emit(response, diagnostics)

    def _on_error(self, msg: str):
        self._stats_lbl.setText("")
        self._output.append(f"\n[error: {msg}]")
        self.generation_failed.emit()


# ── workspace ─────────────────────────────────────────────────────────────────

class PromptLabWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._hyperparams = {"temperature": 0.7, "top_p": 0.95, "max_tokens": 1024}
        self._output_a = ""
        self._output_b = ""
        self._pairs_dir = "data/prompt_pairs"
        os.makedirs(self._pairs_dir, exist_ok=True)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left panel: saved pairs list
        root.addWidget(self._build_left_panel())

        # Right panel: A/B execution space
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Title row + run both
        top_row = QWidget()
        tr_layout = QHBoxLayout(top_row)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        tr_layout.setSpacing(12)
        title = QLabel("Prompt Lab")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        tr_layout.addWidget(title)
        tr_layout.addStretch()

        # Clone A to B
        self._clone_a_to_b_btn = QPushButton("Clone A → B")
        self._clone_a_to_b_btn.setObjectName("btn-ghost")
        self._clone_a_to_b_btn.setStyleSheet("font-size: 8pt; padding: 2px 6px;")
        self._clone_a_to_b_btn.clicked.connect(self._clone_a_to_b)
        tr_layout.addWidget(self._clone_a_to_b_btn)

        # Clone B to A
        self._clone_b_to_a_btn = QPushButton("Clone B → A")
        self._clone_b_to_a_btn.setObjectName("btn-ghost")
        self._clone_b_to_a_btn.setStyleSheet("font-size: 8pt; padding: 2px 6px;")
        self._clone_b_to_a_btn.clicked.connect(self._clone_b_to_a)
        tr_layout.addWidget(self._clone_b_to_a_btn)

        # Lock user prompt
        self._lock_user_prompt_check = QCheckBox("Lock Sync (A ⟷ B)")
        self._lock_user_prompt_check.setToolTip("Sync user modifications between Side A and Side B")
        self._lock_user_prompt_check.toggled.connect(self._on_lock_sync_toggled)
        tr_layout.addWidget(self._lock_user_prompt_check)

        run_both = QPushButton("▶▶ Run Both")
        run_both.setObjectName("btn-primary")
        run_both.setToolTip("Run both Column A and B generations concurrently")
        run_both.clicked.connect(self._run_both)
        tr_layout.addWidget(run_both)
        right_layout.addWidget(top_row)


        desc = QLabel(
            "Side-by-side prompt engineering workspace. Compare different prompt templates, "
            "system messages, hyperparameter settings, or different model/adapter configurations."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px; padding-left: 2px;")
        right_layout.addWidget(desc)

        self._main_tabs = QTabWidget()
        self._main_tabs.setObjectName("main-tabs")

        # 1. Side-by-side playground
        playground_tab = QWidget()
        pt_layout = QVBoxLayout(playground_tab)
        pt_layout.setContentsMargins(0, 8, 0, 0)
        pt_layout.setSpacing(8)

        # Splitter columns
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._col_a = _PromptColumn("A")
        self._col_a.state = self.state
        self._col_b = _PromptColumn("B")
        self._col_b.state = self.state

        self._col_a.run_requested.connect(self._run_column)
        self._col_b.run_requested.connect(self._run_column)

        self._col_a.generation_done.connect(self._on_col_a_done)
        self._col_b.generation_done.connect(self._on_col_b_done)

        self._col_a.generation_failed.connect(self._on_col_a_failed)
        self._col_b.generation_failed.connect(self._on_col_b_failed)

        splitter.addWidget(self._col_a)
        splitter.addWidget(self._col_b)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        pt_layout.addWidget(splitter, 1)

        self._main_tabs.addTab(playground_tab, "A/B Playground")

        # 2. Diff tab
        diff_tab = QWidget()
        dt_layout = QVBoxLayout(diff_tab)
        dt_layout.setContentsMargins(12, 12, 12, 12)
        dt_layout.setSpacing(6)
        dt_layout.addWidget(_section("DIFFERENCE VIEW (A vs B)"))

        self._diff_view = QTextBrowser()
        self._diff_view.setPlaceholderText("Difference view will render here after both outputs complete...")
        self._diff_view.setToolTip("Inline comparison highlighting additions (green) and deletions (red) between Column A and B outputs")
        dt_layout.addWidget(self._diff_view, 1)
        self._main_tabs.addTab(diff_tab, "Difference View")

        # 3. Tokenizer tab
        tokenizer_tab = QWidget()
        tok_layout = QVBoxLayout(tokenizer_tab)
        tok_layout.setContentsMargins(12, 12, 12, 12)
        tok_layout.setSpacing(8)

        # Input row
        input_row = QWidget()
        ir_layout = QHBoxLayout(input_row)
        ir_layout.setContentsMargins(0, 0, 0, 0)
        ir_layout.setSpacing(10)

        self._tok_input = QTextEdit()
        self._tok_input.setPlaceholderText("Type or paste text to tokenize...")
        self._tok_input.setFixedHeight(80)
        self._tok_input.setToolTip("Enter text to visualize Byte-Pair Encoding (BPE) tokens")
        self._tok_input.textChanged.connect(self._on_tokenize_text_changed)
        ir_layout.addWidget(self._tok_input, 1)

        btn_load_a = QPushButton("Load Output A")
        btn_load_a.setToolTip("Load Column A prompt output directly into tokenizer visualizer")
        btn_load_a.clicked.connect(self._load_output_a_to_tokenizer)
        ir_layout.addWidget(btn_load_a)

        btn_load_b = QPushButton("Load Output B")
        btn_load_b.setToolTip("Load Column B prompt output directly into tokenizer visualizer")
        btn_load_b.clicked.connect(self._load_output_b_to_tokenizer)
        ir_layout.addWidget(btn_load_b)

        tok_layout.addWidget(input_row)

        # Output browser
        self._tok_output = QTextBrowser()
        self._tok_output.setPlaceholderText("Tokens will be visualized here...")
        self._tok_output.setToolTip("Tokens colored by type (special: red, punctuation: blue, word-start: purple, continuation: orange) with token IDs on hover")
        tok_layout.addWidget(self._tok_output, 1)

        self._main_tabs.addTab(tokenizer_tab, "Tokenizer Visualizer")

        right_layout.addWidget(self._main_tabs, 1)

        root.addWidget(right_widget, 1)

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("panel")
        w.setFixedWidth(220)
        
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        layout.addWidget(_section("PROMPT PAIRS"))

        self._pair_search = QLineEdit()
        self._pair_search.setPlaceholderText("Search pairs...")
        self._pair_search.setStyleSheet(
            "background-color: #0D0D1B; border: 1px solid #1F1F3D; border-radius: 4px; "
            "color: #F0F5FF; font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; padding: 4px;"
        )
        self._pair_search.textChanged.connect(self._filter_pairs)
        layout.addWidget(self._pair_search)
        
        self._pairs_list = QListWidget()
        self._pairs_list.currentTextChanged.connect(self._on_pair_selected)
        self._pairs_list.setToolTip("List of saved prompt configuration pairs. Double-click or select to load.")
        layout.addWidget(self._pairs_list, 1)
        self._refresh_pairs()
        
        # Save input and controls
        save_section = QWidget()
        ssl = QVBoxLayout(save_section)
        ssl.setContentsMargins(0, 4, 0, 0)
        ssl.setSpacing(6)
        
        self._pair_name_input = QLineEdit()
        self._pair_name_input.setPlaceholderText("Pair name...")
        self._pair_name_input.setToolTip("Enter name to save current A/B system prompts and settings")
        ssl.addWidget(self._pair_name_input)
        
        self._save_btn = QPushButton("Save Pair")
        self._save_btn.setObjectName("btn-primary")
        self._save_btn.setToolTip("Save current A/B system prompts and settings as a named pair")
        self._save_btn.clicked.connect(self._save_pair)
        ssl.addWidget(self._save_btn)
        
        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setObjectName("btn-danger")
        self._delete_btn.setToolTip("Delete the selected saved prompt pair")
        self._delete_btn.clicked.connect(self._delete_pair)
        ssl.addWidget(self._delete_btn)
        
        layout.addWidget(save_section)
        return w


    def _refresh_pairs(self):
        self._pairs_list.clear()
        if not os.path.exists(self._pairs_dir):
            return
        files = [f for f in os.listdir(self._pairs_dir) if f.endswith(".json")]
        for f in sorted(files):
            name = os.path.splitext(f)[0]
            self._pairs_list.addItem(name)

    def _on_pair_selected(self, name: str):
        if not name:
            return
        path = os.path.join(self._pairs_dir, f"{name}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self._col_a.set_system_text(data.get("system_a", ""))
                self._col_a.set_user_text(data.get("user_a", ""))
                self._col_b.set_system_text(data.get("system_b", ""))
                self._col_b.set_user_text(data.get("user_b", ""))
                self._pair_name_input.setText(name)
                
                # Restore checkboxes
                self._col_a._rag_check.setChecked(data.get("rag_a", False))
                self._col_a._loop_check.setChecked(data.get("loop_a", False))
                self._col_b._rag_check.setChecked(data.get("rag_b", False))
                self._col_b._loop_check.setChecked(data.get("loop_b", False))
                
                # Restore model configuration
                model_a = data.get("model_a")
                adapter_a = data.get("adapter_a")
                if model_a:
                    self._col_a.select_model_and_adapter(model_a, adapter_a)
                    
                model_b = data.get("model_b")
                adapter_b = data.get("adapter_b")
                if model_b:
                    self._col_b.select_model_and_adapter(model_b, adapter_b)
                
                # Restore outputs and diff
                self._output_a = data.get("output_a_raw", "")
                self._output_b = data.get("output_b_raw", "")
                self._col_a._output.setPlainText(data.get("output_a_display", ""))
                self._col_b._output.setPlainText(data.get("output_b_display", ""))
                self._update_diff()
            except Exception as e:
                logger.warning(f"Error loading pair '{name}': {e}")

    def _save_pair(self):
        name = self._pair_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a name for the prompt pair.")
            return
            
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
        if safe_name != name:
            name = safe_name
            self._pair_name_input.setText(name)
            
        model_data_a = self._col_a._model_combo.itemData(self._col_a._model_combo.currentIndex()) or {}
        model_data_b = self._col_b._model_combo.itemData(self._col_b._model_combo.currentIndex()) or {}

        data = {
            "name": name,
            "system_a": self._col_a.system_text(),
            "user_a": self._col_a.user_text(),
            "system_b": self._col_b.system_text(),
            "user_b": self._col_b.user_text(),
            "model_a": model_data_a.get("model"),
            "adapter_a": model_data_a.get("adapter"),
            "model_b": model_data_b.get("model"),
            "adapter_b": model_data_b.get("adapter"),
            "rag_a": self._col_a._rag_check.isChecked(),
            "loop_a": self._col_a._loop_check.isChecked(),
            "rag_b": self._col_b._rag_check.isChecked(),
            "loop_b": self._col_b._loop_check.isChecked(),
            "output_a_raw": self._output_a,
            "output_b_raw": self._output_b,
            "output_a_display": self._col_a._output.toPlainText(),
            "output_b_display": self._col_b._output.toPlainText(),
        }
        
        path = os.path.join(self._pairs_dir, f"{name}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            self._pairs_list.blockSignals(True)
            self._refresh_pairs()
            
            items = self._pairs_list.findItems(name, Qt.MatchFlag.MatchFixedString)
            if items:
                self._pairs_list.setCurrentItem(items[0])
            self._pairs_list.blockSignals(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save pair: {e}")

    def _delete_pair(self):
        item = self._pairs_list.currentItem()
        if not item:
            return
        name = item.text()
        
        reply = QMessageBox.question(
            self, "Delete Pair",
            f"Are you sure you want to delete prompt pair '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            path = os.path.join(self._pairs_dir, f"{name}.json")
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    QMessageBox.critical(self, "Delete Error", f"Could not delete file: {e}")
                    return
            
            self._pair_name_input.clear()
            self._refresh_pairs()

    def showEvent(self, event):
        super().showEvent(event)
        self._col_a._refresh_model_combo()
        self._col_b._refresh_model_combo()

    def _run_column(self, label: str, _user_text: str):
        self._running_both = False
        if label == "A":
            self._output_a = ""
            self._diff_view.setHtml("<span style='color:#9090A8;'>Generating output A...</span>")
            self._col_a.start_run(self._hyperparams)
        else:
            self._output_b = ""
            self._diff_view.setHtml("<span style='color:#9090A8;'>Generating output B...</span>")
            self._col_b.start_run(self._hyperparams)

    def _run_both(self):
        self._output_a = ""
        self._output_b = ""
        self._diff_view.setHtml("<span style='color:#9090A8;'>Generating outputs A and B (sequentially)...</span>")
        self._running_both = True
        self._col_a.start_run(self._hyperparams)

    def _on_col_a_done(self, text: str, diagnostics: dict | None = None):
        self._output_a = text
        self._update_diff()
        if getattr(self, "_running_both", False):
            self._col_b.start_run(self._hyperparams)

    def _on_col_b_done(self, text: str, diagnostics: dict | None = None):
        self._output_b = text
        self._update_diff()
        self._running_both = False

    def _on_col_a_failed(self):
        self._running_both = False
        self._diff_view.setHtml("<span style='color:#FF4A5A;'>Generation failed in Column A. Stopped comparison.</span>")

    def _on_col_b_failed(self):
        self._running_both = False
        self._diff_view.setHtml("<span style='color:#FF4A5A;'>Generation failed in Column B. Stopped comparison.</span>")

    def _update_diff(self):
        if not self._output_a or not self._output_b:
            self._diff_view.setHtml(
                "<span style='color:#505068;'>Waiting for both outputs to complete before rendering diff...</span>"
            )
            return
            
        try:
            diff_html = generate_char_diff_html(self._output_a, self._output_b)
            self._diff_view.setHtml(diff_html)
        except Exception as e:
            self._diff_view.setHtml(f"<span style='color:#F05050;'>Error generating diff: {html.escape(str(e))}</span>")

    # ── tokenizer tab logic ───────────────────────────────────────────────────

    def _on_tokenize_text_changed(self):
        text = self._tok_input.toPlainText()
        if not text:
            self._tok_output.clear()
            return
            
        from app.engine.model_loader import ModelLoader
        if not ModelLoader.is_loaded():
            try:
                ModelLoader.get_instance()
            except Exception:
                self._tok_output.setHtml(
                    "<span style='color:#FF4A5A;'>[Error: No active model loaded. Please configure and load a model in the System tab first.]</span>"
                )
                return
                
        try:
            llm = ModelLoader.get_instance()
            tokens = llm.tokenize(text.encode('utf-8'))
            
            html_parts = [
                f"<div style='line-height: 1.8; color: #E4E4F0; font-family: {MONO};'>"
            ]
            
            for t in tokens:
                t_bytes = llm.detokenize([t])
                html_parts.append(self._format_token_html(t, t_bytes))
                
            html_parts.append("</div>")
            
            stats_html = f"<div style='font-size: 8.5pt; color: #9090A8; margin-bottom: 8px;'>Total Tokens: <b>{len(tokens)}</b></div>"
            self._tok_output.setHtml(stats_html + "".join(html_parts))
            
        except Exception as e:
            self._tok_output.setHtml(f"<span style='color:#FF4A5A;'>Error tokenizing: {html.escape(str(e))}</span>")

    def _format_token_html(self, token_id: int, token_bytes: bytes) -> str:
        text = token_bytes.decode('utf-8', errors='replace')
        
        styles = {
            "special": "color: #FF4A5A; background: rgba(255, 74, 90, 0.12); border: 1px solid rgba(255, 74, 90, 0.25);",
            "punctuation": "color: #00C2FF; background: rgba(0, 194, 255, 0.12); border: 1px solid rgba(0, 194, 255, 0.25);",
            "word-start": "color: #B65CFF; background: rgba(182, 92, 255, 0.12); border: 1px solid rgba(182, 92, 255, 0.25);",
            "continuation": "color: #F0B030; background: rgba(240, 176, 48, 0.12); border: 1px solid rgba(240, 176, 48, 0.25);"
        }
        
        token_type = self._classify_token(token_id, token_bytes)
        style = styles.get(token_type, styles["continuation"])
        
        if token_type == "special" and not text:
            display_text = f"[#{token_id}]"
        else:
            escaped = html.escape(text)
            display_text = escaped.replace(" ", "&middot;").replace("\n", "&crarr;<br/>").replace("\t", "&rarr;")
            if not display_text:
                display_text = f"[#{token_id}]"
                
        return (
            f"<span title='Token ID: {token_id} (Type: {token_type})' "
            f"style='display: inline-block; padding: 1px 4px; margin: 2px 1px; border-radius: 3px; font-family: {MONO}; font-size: 9.5pt; {style}'>"
            f"{display_text}"
            f"</span>"
        )

    def _classify_token(self, token_id: int, token_bytes: bytes) -> str:
        text = token_bytes.decode('utf-8', errors='replace')
        if not token_bytes or token_id >= 100000 or text in ("<|im_start|>", "<|im_end|>", "<think>", "</think>"):
            return "special"
            
        import string
        stripped = text.strip()
        if stripped and all(c in string.punctuation for c in stripped):
            return "punctuation"
            
        if token_bytes.startswith(b' ') or token_bytes.startswith(b'\n') or token_bytes.startswith(b'\t'):
            return "word-start"
            
        return "continuation"

    def _load_output_a_to_tokenizer(self):
        if self._output_a:
            self._tok_input.setPlainText(self._output_a)
        else:
            QMessageBox.information(self, "No Output", "Output A is empty. Run prompt A first.")

    def _load_output_b_to_tokenizer(self):
        if self._output_b:
            self._tok_input.setPlainText(self._output_b)
        else:
            QMessageBox.information(self, "No Output", "Output B is empty. Run prompt B first.")

    # ── Upgraded Prompt Lab Features ──────────────────────────────────────────

    def _filter_pairs(self, text):
        query = text.strip().lower()
        for idx in range(self._pairs_list.count()):
            item = self._pairs_list.item(idx)
            item.setHidden(query not in item.text().lower())

    def _clone_a_to_b(self):
        self._col_b.set_system_text(self._col_a.system_text())
        self._col_b.set_user_text(self._col_a.user_text())
        self._col_b._rag_check.setChecked(self._col_a._rag_check.isChecked())
        self._col_b._loop_check.setChecked(self._col_a._loop_check.isChecked())
        idx = self._col_a._model_combo.currentIndex()
        self._col_b._model_combo.setCurrentIndex(idx)

    def _clone_b_to_a(self):
        self._col_a.set_system_text(self._col_b.system_text())
        self._col_a.set_user_text(self._col_b.user_text())
        self._col_a._rag_check.setChecked(self._col_b._rag_check.isChecked())
        self._col_a._loop_check.setChecked(self._col_b._loop_check.isChecked())
        idx = self._col_b._model_combo.currentIndex()
        self._col_a._model_combo.setCurrentIndex(idx)

    def _on_lock_sync_toggled(self, checked):
        if checked:
            self._col_b.set_user_text(self._col_a.user_text())
            self._col_b.set_system_text(self._col_a.system_text())
            self._col_a._user_edit.textChanged.connect(self._sync_user_a_to_b)
            self._col_b._user_edit.textChanged.connect(self._sync_user_b_to_a)
            self._col_a._system_edit.textChanged.connect(self._sync_system_a_to_b)
            self._col_b._system_edit.textChanged.connect(self._sync_system_b_to_a)
        else:
            try:
                self._col_a._user_edit.textChanged.disconnect(self._sync_user_a_to_b)
                self._col_b._user_edit.textChanged.disconnect(self._sync_user_b_to_a)
                self._col_a._system_edit.textChanged.disconnect(self._sync_system_a_to_b)
                self._col_b._system_edit.textChanged.disconnect(self._sync_system_b_to_a)
            except TypeError:
                pass

    def _sync_user_a_to_b(self):
        self._col_b._user_edit.blockSignals(True)
        self._col_b.set_user_text(self._col_a.user_text())
        self._col_b._user_edit.blockSignals(False)

    def _sync_user_b_to_a(self):
        self._col_a._user_edit.blockSignals(True)
        self._col_a.set_user_text(self._col_b.user_text())
        self._col_a._user_edit.blockSignals(False)

    def _sync_system_a_to_b(self):
        self._col_b._system_edit.blockSignals(True)
        self._col_b.set_system_text(self._col_a.system_text())
        self._col_b._system_edit.blockSignals(False)

    def _sync_system_b_to_a(self):
        self._col_a._system_edit.blockSignals(True)
        self._col_a.set_system_text(self._col_b.system_text())
        self._col_a._system_edit.blockSignals(False)

