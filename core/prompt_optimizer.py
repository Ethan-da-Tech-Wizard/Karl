"""
Prompt Optimizer Engine — Karl Workbench
========================================
Handles automated prompt mutations and evolution loops using the local LLM.

optimize_loop() runs a simple hill-climbing search: split a JSONL eval
dataset into a mini-train and mini-validation slice, mutate the current
system prompt against mini-train failures, score the candidate on
mini-validation via EvalHarness, and keep it only if it scores higher than
the current best. Repeats for a fixed number of iterations.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from app.engine.model_loader import ModelLoader
from core.cognitive_parser import parse_thought_stream
from core.default_prompts import DEFAULT_SYSTEM_PROMPT, load_prompt_presets
from core.interaction_loop import build_prompt
from eval.harness import EvalHarness

logger = logging.getLogger("karl.prompt_optimizer")

_MUTATION_META_PROMPT = (
    "Analyze the following failed cases where the system prompt led to incorrect "
    "results or errors. Propose a refined system prompt that fixes these failures "
    "while remaining concise."
)


class PromptOptimizer:
    """Manages prompt optimization cycles using local model mutations and eval checks."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self._harness = EvalHarness()

    def mutate_prompt(self, current_prompt: str, failed_examples: list[dict]) -> str:
        """
        Query the local model to mutate the current system prompt based on failing cases.

        Args:
            current_prompt: The active system prompt.
            failed_examples: List of evaluation cases that failed.

        Returns:
            The proposed/mutated system prompt.
        """
        logger.info("Mutating prompt based on %d failures...", len(failed_examples))
        if not failed_examples:
            return current_prompt

        cases_block = "\n\n".join(
            f"Failure {i + 1}:\n"
            f"  User message: {ex.get('prompt', '')[:400]}\n"
            f"  Model output: {ex.get('output', '')[:400]}\n"
            f"  Why it failed: {ex.get('detail') or 'unspecified'}"
            for i, ex in enumerate(failed_examples[:8])
        )
        meta_user_message = (
            f"{_MUTATION_META_PROMPT}\n\n"
            f'Current system prompt:\n"""\n{current_prompt}\n"""\n\n'
            f"Failed cases:\n{cases_block}\n\n"
            "Respond with ONLY the full text of the new system prompt. "
            "No explanation, no markdown fences, no preamble."
        )

        try:
            llm = ModelLoader.get_instance(model_path=self._model_path())
        except Exception as exc:
            logger.warning("Could not load model for prompt mutation (%s); keeping current prompt.", exc)
            return current_prompt

        history = [{"role": "user", "content": meta_user_message}]
        prompt = build_prompt(
            "You are an expert prompt engineer refining system prompts for a local LLM.",
            history,
        )

        try:
            response = llm(prompt, max_tokens=768, temperature=0.4, top_p=0.95, stop=["<|im_end|>"])
        except Exception as exc:
            logger.warning("Prompt mutation generation failed (%s); keeping current prompt.", exc)
            return current_prompt

        raw = response["choices"][0]["text"]
        _thought, parsed = parse_thought_stream(raw, start_in_thought=prompt.rstrip().endswith("<think>"))
        mutated = self._clean_mutation_output(parsed or raw)
        return mutated or current_prompt

    def optimize_loop(
        self,
        prompt_key: str,
        dataset_path: str,
        iterations: int = 3,
        progress_callback: Optional[Callable[[int, int, float, str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> str:
        """
        Run the hill-climbing optimization loop over several iterations.

        Args:
            prompt_key: Key of the prompt in data/system_prompts.json or defaults.
            dataset_path: Path to the JSONL evaluation dataset.
            iterations: Number of optimization mutation rounds.
            progress_callback: Callable taking (current_iter, total_iters, current_score, best_prompt)
            stop_check: Optional callable polled before each iteration; return True
                to stop early and return whatever the best prompt is so far (lets a
                UI Stop button interrupt a long-running loop cooperatively).

        Returns:
            The final optimized system prompt string.
        """
        logger.info("Starting prompt optimization for '%s' using dataset '%s'...", prompt_key, dataset_path)

        presets = load_prompt_presets()
        preset = presets.get(prompt_key)
        if preset:
            current_prompt = preset["prompt"]
        else:
            logger.warning(
                "Prompt key '%s' not found in the registry; starting from the default system prompt.",
                prompt_key,
            )
            current_prompt = DEFAULT_SYSTEM_PROMPT

        cases = self._load_cases(dataset_path)
        if len(cases) < 2:
            raise ValueError(f"Dataset '{dataset_path}' needs at least 2 cases to split into train/val sets.")

        rng = random.Random(13)
        shuffled = list(cases)
        rng.shuffle(shuffled)
        split = max(1, len(shuffled) // 2)
        mini_train, mini_val = shuffled[:split], shuffled[split:] or shuffled[:1]

        workspace = Path(tempfile.mkdtemp(prefix="karl_prompt_opt_"))
        train_path = workspace / "mini_train.jsonl"
        val_path = workspace / "mini_val.jsonl"
        self._write_cases(train_path, mini_train)
        self._write_cases(val_path, mini_val)

        try:
            best_prompt = current_prompt
            best_score, _ = self._evaluate(best_prompt, val_path)
            logger.info("Baseline score for '%s': %.3f", prompt_key, best_score)
            if progress_callback:
                progress_callback(0, iterations, best_score, best_prompt)

            for i in range(1, iterations + 1):
                if stop_check and stop_check():
                    logger.info("Optimization loop stopped early at iteration %d/%d.", i, iterations)
                    break

                _train_score, failures = self._evaluate(best_prompt, train_path)
                if not failures:
                    logger.info("Iteration %d/%d: no mini-train failures, nothing to mutate.", i, iterations)
                    if progress_callback:
                        progress_callback(i, iterations, best_score, best_prompt)
                    continue

                candidate = self.mutate_prompt(best_prompt, failures)
                candidate_score, _ = self._evaluate(candidate, val_path)
                logger.info(
                    "Iteration %d/%d: candidate score %.3f vs best %.3f",
                    i, iterations, candidate_score, best_score,
                )

                if candidate_score > best_score:
                    best_prompt, best_score = candidate, candidate_score

                if progress_callback:
                    progress_callback(i, iterations, best_score, best_prompt)

            return best_prompt
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    # ── internals ────────────────────────────────────────────────────────────

    def _model_path(self) -> Optional[str]:
        return os.path.join("data", "models", self.model_name) if self.model_name else None

    def _evaluate(self, system_prompt: str, dataset_path: Path) -> tuple[float, list[dict]]:
        """Score *system_prompt* against a JSONL dataset via EvalHarness.
        Returns (avg_score, failed_case_dicts)."""
        report = self._harness.run(
            dataset_path=str(dataset_path),
            workflow_name="general_chat",
            hyperparams={"max_tokens": 512, "temperature": 0.2, "top_p": 0.95},
            system_prompt_override=system_prompt,
            model_name=self.model_name,
        )
        failures = [
            {
                "prompt": case.prompt,
                "output": case.output,
                "detail": case.grade.get("detail", ""),
            }
            for case in report.cases
            if not case.grade.get("passed")
        ]
        return report.avg_score, failures

    @staticmethod
    def _load_cases(dataset_path: str) -> list[dict]:
        cases: list[dict] = []
        with open(dataset_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return cases

    @staticmethod
    def _write_cases(path: Path, cases: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as fh:
            for case in cases:
                fh.write(json.dumps(case, ensure_ascii=False) + "\n")

    @staticmethod
    def _clean_mutation_output(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        text = re.sub(r"^(new\s+)?system\s+prompt\s*:\s*", "", text, flags=re.IGNORECASE)
        return text.strip().strip('"').strip()
