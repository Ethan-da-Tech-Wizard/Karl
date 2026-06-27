"""
Inference Service — Karl Engine

Central domain service that abstracts LLM thread selection, token routing,
template compilation, and thread lifecycle management away from UI controllers
and connection handlers.
"""

from __future__ import annotations

import logging
from typing import Callable

from PyQt6.QtCore import Qt, QThread

from app.engine.agentic_thread import AgenticThread
from app.engine.llm_thread import LLMThread

logger = logging.getLogger("karl.inference_service")


class InferenceService:
    """
    Shared service for all LLM generation requests.

    A single instance per ``AppState`` handles thread type selection,
    callback wiring, lifecycle bookkeeping, and telemetry so that UI
    layers and connection handlers stay thin.
    """

    def __init__(self, state) -> None:
        self._state = state
        # Strong references keep threads alive until ``finished`` fires.
        # Without this set, Qt garbage-collects the QThread before its
        # llama-cpp-python destructor runs, causing hard crashes.
        self._active_threads: set[QThread] = set()

    # ── Public API ────────────────────────────────────────────────────────────

    def run_generation(
        self,
        prompt: str,
        system_prompt: str,
        chat_history: list,
        hyperparams: dict,
        on_token_cb: Callable[[str], None] | None = None,
        on_finished_cb: Callable[[str, str, dict], None] | None = None,
        *,
        on_thought_token_cb: Callable[[str], None] | None = None,
        on_error_cb: Callable[[str], None] | None = None,
        on_live_stats_cb: Callable[[int, float], None] | None = None,
        retrieved_chunks: list | None = None,
        agentic: bool = False,
        workflow: str = "general_chat",
        template: str = "reasoning_minimal",
        adapter_name: str | None = None,
        model_name: str | None = None,
        connection_type: Qt.ConnectionType = Qt.ConnectionType.AutoConnection,
    ) -> QThread:
        """
        Boot an inference thread, wire callbacks, and return the started handle.

        Parameters
        ----------
        prompt:
            Current user message text.  Forwarded for logging; the full
            ``chat_history`` drives the prompt context inside the thread.
        system_prompt:
            Compiled system instructions for this turn.
        chat_history:
            Full conversation as ``list[{"role": ..., "content": ...}]``.
        hyperparams:
            Generation hyper-parameters forwarded verbatim to the thread.
        on_token_cb:
            Called for every emitted *chat* token.
        on_finished_cb:
            Called once as ``(thought, response, diagnostics)`` on completion.
            For agentic threads ``diagnostics`` is an empty ``dict``.
        on_thought_token_cb:
            Called for every emitted *reasoning* token.
        on_error_cb:
            Called with the error message on failure.
        on_live_stats_cb:
            Called with ``(token_count, tokens_per_second)`` during generation.
        retrieved_chunks:
            RAG context chunks to inject into the prompt.
        agentic:
            When ``True`` an ``AgenticThread`` is created; otherwise an
            ``LLMThread``.  ``hyperparams["agentic_loop_enabled"]`` is also
            consulted as a fallback.
        workflow:
            Prompt workflow template name.
        template:
            Template identifier within the workflow.
        adapter_name:
            LoRA adapter to load alongside the base model.
        connection_type:
            Qt signal connection type.  Pass ``DirectConnection`` when the
            slot must execute on the signalling thread (e.g. asyncio bridge).

        Returns
        -------
        QThread
            The *already-started* thread handle.  Callers may connect
            additional signals or call ``request_stop()`` on the handle.
        """
        use_agentic = agentic or bool(hyperparams.get("agentic_loop_enabled", False))

        thread: LLMThread | AgenticThread
        if use_agentic:
            thread = AgenticThread(
                system_prompt=system_prompt,
                initial_history=list(chat_history),
                hyperparams=hyperparams,
                retrieved_chunks=list(retrieved_chunks or []),
                workflow=workflow,
                template=template,
                adapter_name=adapter_name,
            )
        else:
            thread = LLMThread(
                system_prompt=system_prompt,
                chat_history=list(chat_history),
                hyperparams=hyperparams,
                retrieved_chunks=list(retrieved_chunks or []),
                workflow=workflow,
                template=template,
                adapter_name=adapter_name,
                model_name=model_name,
            )

        # ── Token callbacks ───────────────────────────────────────────────────
        if on_thought_token_cb is not None:
            thread.new_thought_token.connect(on_thought_token_cb, connection_type)

        if on_token_cb is not None:
            thread.new_chat_token.connect(on_token_cb, connection_type)

        if on_error_cb is not None:
            thread.error_occurred.connect(on_error_cb, connection_type)

        if on_live_stats_cb is not None:
            thread.live_stats.connect(on_live_stats_cb, connection_type)

        # ── Normalised finished callback ──────────────────────────────────────
        # Both thread types emit different signals on completion; the service
        # normalises them to a single (thought, response, diagnostics) shape.
        if on_finished_cb is not None:
            if use_agentic:
                _t = thread  # capture for the closure

                def _agentic_done(total: int) -> None:
                    history = getattr(_t, "chat_history", [])
                    response = ""
                    if history and history[-1].get("role") == "assistant":
                        response = history[-1].get("content", "")
                    on_finished_cb("", response, {})

                thread.loop_finished.connect(_agentic_done, connection_type)
            else:
                def _llm_done(
                    thought: str,
                    response: str,
                    truncated: bool,
                    ended_in_thought: bool,
                    diagnostics: dict,
                ) -> None:
                    on_finished_cb(thought, response, diagnostics)

                thread.generation_finished.connect(_llm_done, connection_type)

        # ── Lifecycle management ──────────────────────────────────────────────
        self._active_threads.add(thread)
        # DirectConnection so discard() runs on the worker thread when finished fires,
        # guaranteeing the set is updated before QThread.wait() returns on the caller.
        thread.finished.connect(
            lambda: self._active_threads.discard(thread),
            Qt.ConnectionType.DirectConnection,
        )
        thread.finished.connect(thread.deleteLater)

        logger.info(
            "InferenceService: starting %s (agentic=%s, workflow=%s, adapter=%s, prompt_len=%d)",
            type(thread).__name__,
            use_agentic,
            workflow,
            adapter_name,
            len(prompt),
        )
        thread.start()
        return thread
