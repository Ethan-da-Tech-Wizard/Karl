"""
Eval Harness — Karl Workbench
==============================
Runs a JSONL dataset through the local LLM using a specified workflow and
prompt template, then grades each output and produces an EvalReport.

Dataset JSONL format (one object per line):
  {
    "id":          "unique case ID",
    "prompt":      "user question / instruction",
    "context":     "optional inline context (used if no context_file)",
    "context_file":"optional path to a .txt/.md file to use as context",
    "expected":    "string or JSON object depending on grader",
    "grader":      "exact_match | json_valid | keyword_hit | groundedness | not_in_context",
    "schema_keys": ["key1", "key2"],   // used by json_valid
    "keywords":    ["word1", "word2"], // used by keyword_hit
    "require_all": true                // used by keyword_hit
  }

Usage:
  python eval/run_eval.py --workflow grounded_answer --dataset eval/datasets/grounded_answer.jsonl
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

# Allow running from repo root without install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.graders import run_grader
from core.prompt_templates import get_template
from core.workflows import get_workflow


@dataclass
class CaseResult:
    case_id: str
    prompt: str
    workflow: str
    template: str
    output: str
    grader: str
    grade: dict          # {passed, score, detail}
    latency_s: float
    context_used: list[str]
    error: Optional[str] = None


@dataclass
class EvalReport:
    workflow: str
    template: str
    dataset: str
    total: int
    passed: int
    failed: int
    errors: int
    pass_rate: float
    avg_latency_s: float
    avg_score: float
    timestamp: str
    cases: list[CaseResult] = field(default_factory=list)

    def print_summary(self):
        """Print a human-readable summary table to stdout."""
        bar = "─" * 60
        print(f"\n{bar}")
        print(f"  Karl Eval Report")
        print(f"{bar}")
        print(f"  Workflow  : {self.workflow}")
        print(f"  Template  : {self.template}")
        print(f"  Dataset   : {self.dataset}")
        print(f"  Timestamp : {self.timestamp}")
        print(f"{bar}")
        print(f"  Total cases : {self.total}")
        print(f"  Passed      : {self.passed}  ({self.pass_rate:.1%})")
        print(f"  Failed      : {self.failed}")
        print(f"  Errors      : {self.errors}")
        print(f"  Avg score   : {self.avg_score:.3f}")
        print(f"  Avg latency : {self.avg_latency_s:.2f}s")
        print(f"{bar}")
        print(f"  Per-case results:")
        for c in self.cases:
            status = "✓" if c.grade.get("passed") else ("E" if c.error else "✗")
            score = c.grade.get("score", 0.0)
            print(f"  [{status}] {c.case_id:<20} score={score:.2f}  lat={c.latency_s:.1f}s")
            if not c.grade.get("passed"):
                print(f"       detail: {c.grade.get('detail', '')}")
        print(f"{bar}\n")


class EvalHarness:
    """
    Runs a dataset through the local LLM and grades each output.

    The harness is intentionally model-agnostic: it calls ModelLoader
    directly (same singleton the UI uses) so the active model is whatever
    Karl currently has loaded.
    """

    def __init__(self, rag_pipeline=None):
        """
        Args:
            rag_pipeline: Optional pre-initialised RAGPipeline instance.
                          If None, RAG retrieval is skipped even when workflow
                          requires it (context falls back to case["context"]).
        """
        self.rag = rag_pipeline

    def _load_dataset(self, dataset_path: str) -> list[dict]:
        cases = []
        with open(dataset_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  WARNING: skipping line {i} in {dataset_path}: {e}", file=sys.stderr)
        return cases

    def _resolve_context(self, case: dict, workflow_cfg: dict) -> list[str]:
        """
        Return context chunks for this case.
        Priority: RAG retrieval > context_file > inline context field.
        """
        top_k = workflow_cfg.get("rag_top_k", 3)

        # Try RAG if available and workflow wants it
        if self.rag and top_k > 0:
            chunks = self.rag.retrieve(case["prompt"], top_k=top_k)
            if chunks:
                return chunks

        # Fall back to context_file
        ctx_file = case.get("context_file")
        if ctx_file and os.path.exists(ctx_file):
            with open(ctx_file, "r", encoding="utf-8", errors="ignore") as f:
                return [f.read()]

        # Fall back to inline context
        inline = case.get("context", "")
        if inline:
            return [inline]

        return []

    def _build_system_prompt(self, template_name: str, context_chunks: list[str], case: dict) -> str:
        rag_context = "\n\n".join(context_chunks) if context_chunks else "(No context retrieved.)"
        schema = case.get("schema", "(No schema specified.)")
        code = case.get("code", case.get("context", "(No code provided.)"))
        return get_template(template_name, rag_context=rag_context, schema=schema, code=code)

    def _run_model(
        self,
        system_prompt: str,
        user_prompt: str,
        hyperparams: dict,
        model_name: Optional[str] = None,
        adapter_name: Optional[str] = None,
    ) -> tuple[str, float]:
        """
        Run a single generation. Returns (output_text, latency_seconds).
        Loads model via ModelLoader singleton — same instance as the UI.
        """
        from app.engine.model_loader import ModelLoader
        from core.interaction_loop import build_prompt

        model_path = None
        if model_name:
            model_path = os.path.join("data", "models", model_name)
        llm = ModelLoader.get_instance(model_path=model_path, adapter_name=adapter_name)
        history = [{"role": "user", "content": user_prompt}]
        prompt = build_prompt(system_prompt, history)

        start = time.time()
        response = llm(
            prompt,
            max_tokens=hyperparams.get("max_tokens", 512),
            temperature=hyperparams.get("temperature", 0.3),
            top_p=hyperparams.get("top_p", 0.95),
            stop=["<|im_end|>"],
        )
        latency = time.time() - start

        raw = response["choices"][0]["text"]
        # Strip <think>...</think> from output for grading purposes
        if "</think>" in raw:
            raw = raw.split("</think>", 1)[1].strip()
        return raw, latency

    def _grade(self, output: str, case: dict, context_chunks: list[str]) -> dict:
        grader_name = case.get("grader", "keyword_hit")
        kwargs: dict = {}

        if grader_name == "json_valid":
            kwargs["schema_keys"] = case.get("schema_keys", [])
        elif grader_name == "keyword_hit":
            expected = case.get("expected", "")
            kwargs["keywords"] = case.get("keywords", [expected] if expected else [])
            kwargs["require_all"] = case.get("require_all", True)
        elif grader_name == "exact_match":
            kwargs["expected"] = case.get("expected", "")
        elif grader_name == "groundedness":
            kwargs["context_chunks"] = context_chunks

        return run_grader(grader_name, output, **kwargs)

    def run(
        self,
        dataset_path: str,
        workflow_name: str,
        template_override: Optional[str] = None,
        hyperparams: Optional[dict] = None,
        progress_cb=None,
        model_name: Optional[str] = None,
        adapter_name: Optional[str] = None,
    ) -> EvalReport:
        """
        Run the full eval loop.

        Args:
            dataset_path:      Path to JSONL eval dataset.
            workflow_name:     Workflow key from core/workflows.py.
            template_override: Override the workflow's default template.
            hyperparams:       Generation params. Defaults to low-temp for eval stability.

        Returns:
            EvalReport with per-case results and aggregate metrics.
        """
        from datetime import datetime, timezone
        from app.engine.model_loader import ModelLoader

        # Guard: ensure model is loaded before running eval
        path_to_load = None
        if model_name:
            path_to_load = os.path.join("data", "models", model_name)
        try:
            llm = ModelLoader.get_instance(model_path=path_to_load, adapter_name=adapter_name)
            
            # ── Pre-Flight Device Synchronization Checks ──────────────────────
            # If the model is distributed across multiple GPUs, run a dummy query.
            active_model_name = getattr(ModelLoader, "_model_name", "unknown")
            # Retrieve tensor split info if available in loader (added during hardening)
            # For now we check if more than one GPU is reported as available
            from core.hardware_scout import get_hardware_profile
            hardware = get_hardware_profile()
            gpu_list = hardware.get("gpu_list", [])
            
            if len(gpu_list) > 1:
                print(f"\n  [Pre-flight] Multi-GPU detected ({len(gpu_list)} GPUs). Verifying synchronization...")
                try:
                    # Run a single dummy evaluation query to verify synchronization
                    # Use a very short max_tokens for speed
                    llm("Hello", max_tokens=1, stop=["\n"])
                    print("  [Pre-flight] Device synchronization verified.")
                except Exception as sync_exc:
                    msg = f"Device Synchronization Failure on multi-GPU model '{active_model_name}': {sync_exc}"
                    print(f"  [Pre-flight] {msg}")
                    raise RuntimeError(msg) from sync_exc
            # ─────────────────────────────────────────────────────────────────
            
        except FileNotFoundError as e:
            raise RuntimeError(
                f"No model found at {path_to_load or 'active model'}. Run download_test_model.py or "
                "load a model in System Config."
            ) from e

        workflow_cfg = get_workflow(workflow_name)
        template_name = template_override or workflow_cfg["template"]
        hp = hyperparams or {"max_tokens": 512, "temperature": 0.2, "top_p": 0.95}

        cases = self._load_dataset(dataset_path)
        print(f"\n  Running {len(cases)} cases  |  workflow={workflow_name}  |  template={template_name}")

        results: list[CaseResult] = []
        latencies: list[float] = []
        scores: list[float] = []

        import concurrent.futures
        # Create a thread pool with size 1 since we still want sequential eval
        # but need a way to interrupt a hung model call.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        for i, case in enumerate(cases, 1):
            case_id = case.get("id", f"case_{i:03d}")
            if progress_cb:
                progress_cb(i, len(cases))
            print(f"  [{i}/{len(cases)}] {case_id}...", end="", flush=True)

            context_chunks = self._resolve_context(case, workflow_cfg)
            system_prompt = self._build_system_prompt(template_name, context_chunks, case)
            user_prompt = case.get("prompt", "")

            # ── Thread Deadlock & Timeout Analysis ───────────────────────────
            # Calculate dynamic timeout based on rolling average latency (3x avg)
            # Default to 120s for the first cases
            avg_lat = sum(latencies) / len(latencies) if latencies else 40.0
            timeout_limit = max(60.0, avg_lat * 3.0)
            # ─────────────────────────────────────────────────────────────────

            try:
                # Run model in worker thread with timeout
                future = executor.submit(self._run_model, system_prompt, user_prompt, hp, model_name, adapter_name)
                try:
                    output, latency = future.result(timeout=timeout_limit)
                except concurrent.futures.TimeoutError:
                    # Thread hung - likely a deadlock or context overflow loop
                    print(f" TIMEOUT ({timeout_limit:.1f}s - 3x avg)")
                    # We must attempt to reset ModelLoader lock if it was acquired inside the thread
                    ModelLoader.unlock_instance()
                    raise RuntimeError(f"Evaluation case timed out after {timeout_limit:.1f}s (deadlock guard)")

                grade = self._grade(output, case, context_chunks)
                error = None
                
                # Curate eval failures as SFT/DPO pairs
                if not grade.get("passed"):
                    try:
                        from app.utils.training_curator import save_example
                        expected_ans = case.get("expected", "")
                        if not isinstance(expected_ans, str):
                            expected_ans = json.dumps(expected_ans, ensure_ascii=False)
                        
                        save_example(
                            system_prompt=system_prompt,
                            user_msg=user_prompt,
                            good_response=expected_ans,
                            source="eval_chosen"
                        )
                        save_example(
                            system_prompt=system_prompt,
                            user_msg=user_prompt,
                            good_response=output,
                            source="eval_rejected"
                        )
                    except Exception as curation_exc:
                        print(f"  WARNING: failed to curate eval failure: {curation_exc}")
            except Exception as e:
                output = ""
                latency = 0.0
                grade = {"passed": False, "score": 0.0, "detail": f"EXCEPTION: {e}"}
                error = str(e)
                if "TIMEOUT" not in str(e):
                    print(f" ERROR: {e}")

            status = "✓" if grade["passed"] else "✗"
            if not error:
                print(f" {status} ({latency:.1f}s)")

            results.append(CaseResult(
                case_id=case_id,
                prompt=user_prompt,
                workflow=workflow_name,
                template=template_name,
                output=output,
                grader=case.get("grader", "keyword_hit"),
                grade=grade,
                latency_s=round(latency, 3),
                context_used=context_chunks,
                error=error,
            ))
            if not error:
                latencies.append(latency)
            scores.append(grade.get("score", 0.0))
        
        executor.shutdown(wait=False)

        total = len(results)
        passed = sum(1 for r in results if r.grade.get("passed"))
        errors = sum(1 for r in results if r.error)

        report = EvalReport(
            workflow=workflow_name,
            template=template_name,
            dataset=dataset_path,
            total=total,
            passed=passed,
            failed=total - passed - errors,
            errors=errors,
            pass_rate=passed / total if total else 0.0,
            avg_latency_s=round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            avg_score=round(sum(scores) / len(scores), 3) if scores else 0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cases=results,
        )

        # Persist last eval result for the Flywheel dashboard
        try:
            os.makedirs("data", exist_ok=True)
            summary = {
                "score": report.pass_rate,
                "avg_score": report.avg_score,
                "dataset": os.path.basename(dataset_path),
                "workflow": workflow_name,
                "timestamp": report.timestamp,
                "cases_run": total,
                "passed": passed,
            }
            with open("data/eval_last.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
        except Exception:
            pass

        return report

    def save_report(self, report: EvalReport, output_dir: str = "eval/results") -> str:
        """Write report to a timestamped JSONL file. Returns the file path."""
        os.makedirs(output_dir, exist_ok=True)
        ts = report.timestamp.replace(":", "-").replace(".", "-")[:19]
        filename = f"{report.workflow}_{ts}.jsonl"
        path = os.path.join(output_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            # Summary line
            summary = asdict(report)
            summary.pop("cases")
            f.write(json.dumps({"type": "summary", **summary}) + "\n")
            # Per-case lines
            for case in report.cases:
                f.write(json.dumps({"type": "case", **asdict(case)}) + "\n")

        return path
