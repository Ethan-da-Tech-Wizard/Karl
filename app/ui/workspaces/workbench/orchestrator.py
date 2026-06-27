"""Backend orchestration service for the Workbench workspace."""

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import QObject, pyqtSignal

from app.engine.agentic_thread import AgenticThread
from app.engine.llm_thread import LLMThread
from app.engine.model_loader import ModelLoader
from app.engine.task_supervisor import TaskSupervisor
from app.utils.session_tree import SessionTree


logger = logging.getLogger("karl.workbench.orchestrator")


class WorkbenchOrchestrator(QObject):
    """Owns Workbench generation threads, session state, and retrieval plumbing."""

    generation_started = pyqtSignal(bool)  # agentic
    thought_token = pyqtSignal(str)
    chat_token = pyqtSignal(str)
    live_stats = pyqtSignal(int, float)
    generation_finished = pyqtSignal(str, str, bool, bool, object)
    iteration_finished = pyqtSignal(int, str, str, object)
    loop_finished = pyqtSignal(int, object)
    generation_error = pyqtSignal(str)
    reload_notice = pyqtSignal(str)
    context_stats = pyqtSignal(int, int, int, int)
    rag_context_used = pyqtSignal(object)
    status_update = pyqtSignal(str, bool)
    session_loaded = pyqtSignal(object, str, str)
    session_saved = pyqtSignal(str)
    session_reset = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.chat_history = SessionTree()
        self.thread: LLMThread | AgenticThread | None = None
        self.active_threads: set[LLMThread | AgenticThread] = set()
        self.last_response = ""
        self.last_thought = ""
        self.current_session_file: str | None = None
        self.session_id: str | None = None
        self.pending_generation_history: list[dict] | None = None
        self._current_task_id: str | None = None

    @property
    def is_running(self) -> bool:
        return self.thread is not None

    def add_user_message(
        self,
        display_text: str,
        prompt_text: str,
        attachments: list[dict] | None = None,
    ):
        node = self.chat_history.add_message(
            "user",
            display_text,
            attachments=attachments or [],
        )
        self.pending_generation_history = list(self.chat_history)
        if self.pending_generation_history:
            self.pending_generation_history[-1] = {
                **self.pending_generation_history[-1],
                "content": prompt_text,
            }
        return node

    def correct_last_response(self, text: str, system_prompt: str) -> None:
        if self.chat_history:
            self.chat_history.update_current_node_content(text)
        prompt = self.chat_history[-2]["content"] if len(self.chat_history) >= 2 else ""
        self.state.curator.save_example(
            prompt=prompt,
            response=text,
            source="corrected",
            system_prompt=system_prompt,
        )
        self.state.logger.update_last_entry_feedback(
            feedback="corrected",
            corrected_response=text,
        )
        self.last_response = text

    def save_feedback(self, source: str, system_prompt: str) -> None:
        if not self.last_response:
            return
        prompt = self.chat_history[-2]["content"] if len(self.chat_history) >= 2 else ""
        self.state.curator.save_example(
            prompt=prompt,
            response=self.last_response,
            source=source,
            system_prompt=system_prompt,
        )
        self.state.logger.update_last_entry_feedback(feedback=source)

    def retrieve_rag_context(self, prompt_text: str, enabled: bool) -> tuple[list[str], list[dict]]:
        if not enabled:
            return [], []

        top_k = getattr(self.state, "rag_top_k", 3)
        threshold = getattr(self.state, "rag_threshold", 0.0)
        rag_mode = getattr(self.state, "rag_mode", "dense")
        retrieved_metadata: list[dict] = []

        if self.state.rag.total_chunks > 0:
            retrieved_metadata.extend(
                self.state.rag.retrieve_with_metadata(
                    prompt_text,
                    top_k=top_k,
                    threshold=threshold,
                    mode=rag_mode,
                )
            )
        if hasattr(self.state, "codex_rag") and self.state.codex_rag.total_chunks > 0:
            retrieved_metadata.extend(
                self.state.codex_rag.retrieve_with_metadata(
                    prompt_text,
                    top_k=top_k,
                    threshold=threshold,
                    mode=rag_mode,
                )
            )

        retrieved_metadata.sort(key=lambda x: x.get("distance", 999.0))
        retrieved_metadata = retrieved_metadata[:top_k]
        chunks = []
        for result in retrieved_metadata:
            chunk_text = result["text"]
            if getattr(self.state.rag, "contextual_headers", False):
                header = f"[Source: {result['source_file']} | Chunk {result['chunk_id']}]\n"
                chunk_text = header + chunk_text
            chunks.append(chunk_text)
        return chunks, retrieved_metadata

    def start_generation(
        self,
        *,
        agentic: bool,
        system_prompt: str,
        hyperparams: dict,
        retrieved_chunks: list[str],
        workflow: str,
        template: str,
        adapter_name: str | None,
    ) -> None:
        history = self.pending_generation_history or list(self.chat_history)
        self.pending_generation_history = None
        if agentic:
            thread = AgenticThread(
                system_prompt=system_prompt,
                initial_history=history,
                hyperparams=hyperparams,
                retrieved_chunks=retrieved_chunks,
                workflow=workflow,
                template=template,
                adapter_name=adapter_name,
            )
            thread.iteration_finished.connect(self._on_iteration_finished)
            thread.loop_finished.connect(self._on_loop_finished)
        else:
            thread = LLMThread(
                system_prompt=system_prompt,
                chat_history=history,
                hyperparams=hyperparams,
                retrieved_chunks=retrieved_chunks,
                workflow=workflow,
                template=template,
                adapter_name=adapter_name,
            )
            thread.generation_finished.connect(self._on_generation_finished)

        thread.new_thought_token.connect(self.thought_token)
        thread.new_chat_token.connect(self.chat_token)
        thread.live_stats.connect(self.live_stats)
        thread.error_occurred.connect(self._on_error)
        thread.reload_notice.connect(self.reload_notice)
        thread.context_stats.connect(self.context_stats)
        if hasattr(thread, "rag_context_used"):
            thread.rag_context_used.connect(self.rag_context_used)
        thread.status_update.connect(self.status_update)

        task_name = "Agentic loop" if agentic else "LLM generation"
        task_id = TaskSupervisor.instance().register(
            name=task_name,
            cancellable=thread,
        )
        self._current_task_id = task_id

        def _on_thread_finished():
            self.active_threads.discard(thread)
            sup = TaskSupervisor.instance()
            if sup.status(task_id) not in ("finished", "error"):
                sup.finish(task_id)

        def _on_thread_error(msg: str):
            TaskSupervisor.instance().fail(task_id, msg)

        self.active_threads.add(thread)
        thread.finished.connect(_on_thread_finished)
        thread.finished.connect(thread.deleteLater)
        if hasattr(thread, "error_occurred"):
            thread.error_occurred.connect(_on_thread_error)
        self.thread = thread
        self.generation_started.emit(agentic)
        thread.start()

    def stop_generation(self) -> None:
        if self._current_task_id:
            TaskSupervisor.instance().cancel(self._current_task_id)
        elif self.thread and hasattr(self.thread, "request_stop"):
            self.thread.request_stop()

    def clear_thread(self) -> None:
        self.thread = None
        self._current_task_id = None

    def _on_generation_finished(
        self,
        thought: str,
        response: str,
        truncated: bool,
        ended_in_thought: bool,
        diagnostics: dict | None = None,
    ) -> None:
        node = self.chat_history.add_message("assistant", response)
        node.thought = thought
        self.last_response = response
        self.last_thought = thought
        self.generation_finished.emit(
            thought,
            response,
            truncated,
            ended_in_thought,
            diagnostics or {},
        )

    def _on_iteration_finished(
        self,
        index: int,
        thought: str,
        response: str,
        diagnostics: dict | None = None,
    ) -> None:
        self.last_response = response
        if thought:
            self.last_thought = thought
        self.iteration_finished.emit(index, thought, response, diagnostics or {})

    def _on_loop_finished(self, total: int) -> None:
        final_response = ""
        if self.thread and hasattr(self.thread, "chat_history"):
            thread_history = self.thread.chat_history
            original_len = len(self.chat_history)
            new_msgs = thread_history[original_len:]
            assistant_msgs = [
                msg for msg in new_msgs
                if msg.get("role") == "assistant" and msg.get("content", "").strip()
            ]
            if assistant_msgs:
                final_response = assistant_msgs[-1]["content"]
                self.chat_history.add_message("assistant", final_response)
                self.last_response = final_response
        self.loop_finished.emit(total, final_response)

    def _on_error(self, msg: str) -> None:
        self.generation_error.emit(msg)

    def diagnostics_context(self) -> tuple[str, int]:
        return ModelLoader.model_name(), ModelLoader.n_ctx()

    def load_session(self, path: str) -> tuple[SessionTree, str]:
        tree, session_id = SessionTree.load(path)
        self.chat_history = tree
        self.session_id = session_id
        self.current_session_file = path
        self.last_response = ""
        self.last_thought = ""
        self.session_loaded.emit(tree, session_id, path)
        return tree, session_id

    def save_current_session(self) -> str | None:
        if not self.chat_history or len(self.chat_history) < 2:
            return None
        path = self.chat_history.save(self.session_id)
        if self.session_id is None:
            self.session_id = os.path.splitext(os.path.basename(path))[0]
            self.current_session_file = path
        self.session_saved.emit(path)
        return path

    def autosave_session(self) -> str | None:
        try:
            return self.save_current_session()
        except Exception as exc:
            logger.warning("Autosave failed: %s", exc)
            return None

    def reset_session(self) -> None:
        self.autosave_session()
        self.chat_history = SessionTree()
        self.session_id = None
        self.current_session_file = None
        self.pending_generation_history = None
        self.last_response = ""
        self.last_thought = ""
        self.session_reset.emit()

    def set_session_identity(self, session_id: str | None, current_file: str | None) -> None:
        self.session_id = session_id
        self.current_session_file = current_file

    def set_chat_history(self, tree: SessionTree) -> None:
        self.chat_history = tree
