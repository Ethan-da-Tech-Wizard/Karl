"""
Self-Play RL Background Worker
===============================
Runs an autonomous self-improvement cycle: generates task variations from an
objective, asks the model to solve them, verifies solutions via a shell command,
and curates passing/failing pairs into the training dataset.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("karl.self_play_thread")

# System prompt used to ask the model to generate task variations.
_TASK_GEN_SYSTEM = (
    "You are a task generator for self-play reinforcement learning. "
    "Given an objective, output ONE clear, self-contained task or coding challenge "
    "that tests that objective. Output ONLY the task text — no preamble, no explanation."
)

# System prompt used when prompting the model to solve the generated task.
_SOLVER_SYSTEM = (
    "You are a highly capable AI assistant. Solve the following task precisely and completely. "
    "Show your reasoning, then give your final answer."
)

# Max tokens for task generation and for the solver response.
_TASK_GEN_MAX_TOKENS = 200
_SOLVER_MAX_TOKENS = 768
_VERIFY_TIMEOUT_S = 60


class SelfPlayThread(QThread):
    """
    QThread that runs N rounds of self-play RL.

    Signals
    -------
    iteration_complete(round_index, passed, score)
        Emitted after each round with the 0-based index, pass/fail, and a
        numeric score in [0, 1].
    log_message(text)
        Status / debug lines suitable for display in a live log widget.
    cycle_finished(total_passed, total_run)
        Emitted once when the loop ends (completed or stopped).
    """

    iteration_complete = pyqtSignal(int, bool, float)   # round, passed, score
    log_message = pyqtSignal(str)
    cycle_finished = pyqtSignal(int, int)               # passed, total

    def __init__(
        self,
        *,
        model_path: str | None = None,
        adapter_name: str | None = None,
        objective: str,
        test_command: str = "",
        iteration_count: int = 20,
        workspace: str = "general",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.model_path = model_path
        self.adapter_name = adapter_name
        self.objective = objective.strip() or "Generate a useful coding exercise."
        self.test_command = test_command.strip()
        self.iteration_count = max(1, iteration_count)
        self.workspace = workspace
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True
        self.log_message.emit("[SelfPlay] Stop requested — finishing current round…")

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        from app.engine.model_loader import ModelLoader
        from app.utils.training_curator import save_example

        self.log_message.emit(f"[SelfPlay] Starting {self.iteration_count}-round cycle.")
        self.log_message.emit(f"[SelfPlay] Objective: {self.objective}")

        # Load model once for the whole cycle.
        try:
            llm = ModelLoader.get_instance(
                model_path=self.model_path,
                adapter_name=self.adapter_name,
            )
        except Exception as exc:
            self.log_message.emit(f"[SelfPlay] ERROR loading model: {exc}")
            self.cycle_finished.emit(0, 0)
            return

        total_passed = 0
        total_run = 0

        for i in range(self.iteration_count):
            if self._stop_requested:
                self.log_message.emit("[SelfPlay] Stopped by user request.")
                break

            self.log_message.emit(f"[SelfPlay] ── Round {i + 1}/{self.iteration_count} ──")

            # 1. Generate a task variation using the model itself.
            task = self._generate_task(llm, i)
            self.log_message.emit(f"[SelfPlay] Task: {task[:120]}{'…' if len(task) > 120 else ''}")

            if self._stop_requested:
                break

            # 2. Generate a response from the model.
            response = self._generate_response(llm, task)
            self.log_message.emit(
                f"[SelfPlay] Response ({len(response)} chars): "
                f"{response[:80]}{'…' if len(response) > 80 else ''}"
            )

            if self._stop_requested:
                break

            # 3. Verify the response.
            passed, score = self._verify(response, task, i)
            status = "PASS ✓" if passed else "FAIL ✗"
            self.log_message.emit(f"[SelfPlay] Verification → {status}  (score={score:.3f})")

            # 4. Curate into the training dataset.
            system_prompt = f"{_SOLVER_SYSTEM}\n\nObjective domain: {self.workspace}"
            source = "self_play_chosen" if passed else "self_play_rejected"
            try:
                save_example(
                    system_prompt=system_prompt,
                    user_msg=task,
                    good_response=response,
                    source=source,
                )
                self.log_message.emit(f"[SelfPlay] Saved → curated.jsonl (source={source})")
            except Exception as exc:
                self.log_message.emit(f"[SelfPlay] WARNING: curation save failed: {exc}")

            total_run += 1
            if passed:
                total_passed += 1

            self.iteration_complete.emit(i, passed, score)

        self.log_message.emit(
            f"[SelfPlay] Cycle complete. {total_passed}/{total_run} passed "
            f"({total_passed / total_run:.1%} pass rate)." if total_run else
            "[SelfPlay] Cycle ended — no rounds completed."
        )
        self.cycle_finished.emit(total_passed, total_run)

    # ── Step helpers ──────────────────────────────────────────────────────────

    def _llm_call(self, llm: Any, prompt: str, max_tokens: int, temperature: float) -> str:
        """Low-level call returning stripped text, stripping <think> blocks."""
        try:
            result = llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                stop=["<|im_end|>", "\n\n\n"],
            )
            raw: str = result["choices"][0]["text"]
            if "</think>" in raw:
                raw = raw.split("</think>", 1)[1]
            return raw.strip()
        except Exception as exc:
            logger.warning("LLM call failed: %s", exc)
            return ""

    def _build_prompt(self, system: str, user: str) -> str:
        return (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\n{user}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def _generate_task(self, llm: Any, iteration: int) -> str:
        user_msg = (
            f"Objective: {self.objective}\n\n"
            f"Task variation #{iteration + 1}:"
        )
        prompt = self._build_prompt(_TASK_GEN_SYSTEM, user_msg)
        task = self._llm_call(llm, prompt, _TASK_GEN_MAX_TOKENS, temperature=0.9)
        return task or f"[Fallback task {iteration + 1}] Explain or demonstrate: {self.objective}"

    def _generate_response(self, llm: Any, task: str) -> str:
        system = f"{_SOLVER_SYSTEM}\n\nWorkspace: {self.workspace}"
        prompt = self._build_prompt(system, task)
        return self._llm_call(llm, prompt, _SOLVER_MAX_TOKENS, temperature=0.7)

    def _verify(self, response: str, task: str, iteration: int) -> tuple[bool, float]:
        """Run the verification test command. Falls back to heuristic if no command."""
        if not self.test_command:
            return self._heuristic_verify(response)

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tf:
                tf.write(response)
                tmp_path = tf.name

            env = os.environ.copy()
            env["SELF_PLAY_RESPONSE"] = response
            env["SELF_PLAY_TASK"] = task
            env["SELF_PLAY_OUTPUT_FILE"] = tmp_path
            env["SELF_PLAY_ROUND"] = str(iteration + 1)

            proc = subprocess.run(
                self.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=_VERIFY_TIMEOUT_S,
                env=env,
            )
            passed = proc.returncode == 0
            if proc.stderr.strip():
                self.log_message.emit(f"[SelfPlay] Test stderr: {proc.stderr.strip()[:200]}")
            return passed, 1.0 if passed else 0.0

        except subprocess.TimeoutExpired:
            self.log_message.emit(f"[SelfPlay] Verification timed out after {_VERIFY_TIMEOUT_S}s.")
            return False, 0.0
        except Exception as exc:
            self.log_message.emit(f"[SelfPlay] Verification error: {exc}")
            return False, 0.0
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _heuristic_verify(self, response: str) -> tuple[bool, float]:
        """Fallback: reject responses that look like failures or are too short."""
        if len(response) < 20:
            return False, 0.0
        failure_signals = [
            "i cannot", "i'm unable", "i don't know", "error:", "exception:",
            "undefined", "not possible", "apologies",
        ]
        lower = response.lower()
        penalty = sum(0.2 for sig in failure_signals if sig in lower)
        score = max(0.0, 1.0 - penalty)
        return score >= 0.6, round(score, 3)
