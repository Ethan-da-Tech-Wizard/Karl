# CodeLens Local Report

Target: /home/ethan/karl

Status: deterministic offline analysis, with optional local LLM summaries and grounded --ask.

## 1. Project Summary

Scanned 597 files. Detected stack: Docker + Python + pyproject.

Index: /home/ethan/karl/codelens-out/codelens.db (597 files, 7750 symbols, 597 search rows).
Diagram: /home/ethan/karl/codelens-out/architecture.mmd.

## 2. Detected Tech Stack

| Technology | Category | Evidence |
|---|---|---|
| Python | language | pyproject.toml |
| Python | language | requirements.txt |
| Docker | tool | Dockerfile |
| pyproject | tool | pyproject.toml |

## 3. Folder Structure

| Folder | Role | Files |
|---|---|---:|
| . | Root files and project manifests | 22 |
| .claude | Project files | 1 |
| .github | Project files | 2 |
| .mypy_cache | Project files | 2 |
| .pytest_cache | Project files | 5 |
| .ruff_cache | Project files | 2 |
| Karl-main | Project files | 43 |
| app | Project files | 190 |
| core | Project files | 6 |
| data | Project files | 78 |
| docs | Project documentation | 15 |
| eval | Project files | 9 |
| helm | Project files | 8 |
| k8s | Project files | 6 |
| neovim | Project files | 1 |
| tests | Tests and fixtures | 62 |
| tools | Project files | 82 |
| training | Project files | 3 |
| vscode-extension | Project files | 20 |

## 4. Important Files

- .pytest_cache/README.md
- Dockerfile
- Karl-main/README.md
- README.md
- main.py
- pyproject.toml
- requirements.txt
- tools/conversion/README.md
- vscode-extension/README.md

## 5. Entry Points

| Path | Reason |
|---|---|
| main.py | Python main script convention |

## 6. Functions & Classes

| File | Kind | Name | Line | Signature |
|---|---|---|---:|---|
| Karl-main/app/engine/agentic_thread.py | class | AgenticThread | 19 | class AgenticThread(QThread) |
| Karl-main/app/engine/agentic_thread.py | function | __init__ | 32 | def __init__(self, system_prompt, initial_history, hyperparams) |
| Karl-main/app/engine/agentic_thread.py | function | request_stop | 40 | def request_stop(self) |
| Karl-main/app/engine/agentic_thread.py | function | _trim_history | 43 | def _trim_history(self, history, system_prompt) |
| Karl-main/app/engine/agentic_thread.py | function | _run_single_generation | 72 | def _run_single_generation(self, llm, prompt, raw_file) |
| Karl-main/app/engine/agentic_thread.py | function | run | 149 | def run(self) |
| Karl-main/app/engine/llm_thread.py | class | LLMThread | 20 | class LLMThread(QThread) |
| Karl-main/app/engine/llm_thread.py | function | __init__ | 28 | def __init__(self, system_prompt, chat_history, hyperparams, retrieved_chunks=None, start_in_thought=False) |
| Karl-main/app/engine/llm_thread.py | function | _trim_history | 37 | def _trim_history(self, history) |
| Karl-main/app/engine/llm_thread.py | function | _cap | 44 | def _cap(msg) |
| Karl-main/app/engine/llm_thread.py | function | run | 63 | def run(self) |
| Karl-main/app/engine/model_loader.py | class | ModelLoader | 4 | class ModelLoader |
| Karl-main/app/engine/model_loader.py | function | get_instance | 8 | def get_instance(cls, model_path="data/models/deepseek-r1-1.5b.gguf") |
| Karl-main/app/engine/model_loader.py | function | reset_instance | 22 | def reset_instance(cls) |
| Karl-main/app/engine/upgrade_manager.py | function | load_registry | 14 | def load_registry() |
| Karl-main/app/engine/upgrade_manager.py | function | load_active_model | 19 | def load_active_model() |
| Karl-main/app/engine/upgrade_manager.py | function | save_active_model | 27 | def save_active_model(entry) |
| Karl-main/app/engine/upgrade_manager.py | function | check_for_upgrade | 33 | def check_for_upgrade() |
| Karl-main/app/engine/upgrade_manager.py | function | download_model | 61 | def download_model(entry, progress_callback=None) |
| Karl-main/app/engine/upgrade_manager.py | function | perform_upgrade | 82 | def perform_upgrade(entry, progress_callback=None) |
| Karl-main/app/engine/upgrade_manager.py | function | _git_record_upgrade | 101 | def _git_record_upgrade(entry) |
| Karl-main/app/ui/main_window.py | class | UpgradeCheckThread | 17 | class UpgradeCheckThread(QThread) |
| Karl-main/app/ui/main_window.py | function | run | 21 | def run(self) |
| Karl-main/app/ui/main_window.py | class | UpgradeDownloadThread | 33 | class UpgradeDownloadThread(QThread) |
| Karl-main/app/ui/main_window.py | function | __init__ | 38 | def __init__(self, entry) |
| Karl-main/app/ui/main_window.py | function | run | 42 | def run(self) |
| Karl-main/app/ui/main_window.py | class | MainWindow | 52 | class MainWindow(QMainWindow) |
| Karl-main/app/ui/main_window.py | function | __init__ | 53 | def __init__(self) |
| Karl-main/app/ui/main_window.py | function | setup_ui | 80 | def setup_ui(self) |
| Karl-main/app/ui/main_window.py | function | _run_upgrade_check | 340 | def _run_upgrade_check(self) |
| Karl-main/app/ui/main_window.py | function | _on_upgrade_available | 345 | def _on_upgrade_available(self, entry, profile) |
| Karl-main/app/ui/main_window.py | function | _confirm_upgrade | 355 | def _confirm_upgrade(self) |
| Karl-main/app/ui/main_window.py | function | _on_upgrade_complete | 371 | def _on_upgrade_complete(self, path) |
| Karl-main/app/ui/main_window.py | function | _on_upgrade_error | 375 | def _on_upgrade_error(self, msg) |
| Karl-main/app/ui/main_window.py | function | _toggle_raw_panel | 381 | def _toggle_raw_panel(self, state) |
| Karl-main/app/ui/main_window.py | function | _toggle_report_panel | 384 | def _toggle_report_panel(self, state) |
| Karl-main/app/ui/main_window.py | function | _on_workflow_changed | 389 | def _on_workflow_changed(self, index) |
| Karl-main/app/ui/main_window.py | function | _on_headers_toggled | 405 | def _on_headers_toggled(self, state) |
| Karl-main/app/ui/main_window.py | function | _get_current_workflow_name | 409 | def _get_current_workflow_name(self) -> str |
| Karl-main/app/ui/main_window.py | function | _get_current_template_name | 413 | def _get_current_template_name(self) -> str |
| Karl-main/app/ui/main_window.py | function | _update_report_panel | 416 | def _update_report_panel(self, workflow: str, template: str, chunks: list, latency: float, status: str = "") |
| Karl-main/app/ui/main_window.py | function | _on_auto_loop_toggled | 430 | def _on_auto_loop_toggled(self, state) |
| Karl-main/app/ui/main_window.py | function | refresh_session_list | 438 | def refresh_session_list(self) |
| Karl-main/app/ui/main_window.py | function | new_session | 443 | def new_session(self) |
| Karl-main/app/ui/main_window.py | function | save_session | 451 | def save_session(self) |
| Karl-main/app/ui/main_window.py | function | load_session | 461 | def load_session(self, item) |
| Karl-main/app/ui/main_window.py | function | ingest_document | 482 | def ingest_document(self) |
| Karl-main/app/ui/main_window.py | function | _get_hyperparams | 496 | def _get_hyperparams(self) |
| Karl-main/app/ui/main_window.py | function | _set_controls_enabled | 503 | def _set_controls_enabled(self, enabled: bool) |
| Karl-main/app/ui/main_window.py | function | force_thought | 511 | def force_thought(self) |
| Karl-main/app/ui/main_window.py | function | send_message | 520 | def send_message(self) |
| Karl-main/app/ui/main_window.py | function | handle_thought_token | 567 | def handle_thought_token(self, token) |
| Karl-main/app/ui/main_window.py | function | handle_chat_token | 572 | def handle_chat_token(self, token) |
| Karl-main/app/ui/main_window.py | function | handle_raw_token | 577 | def handle_raw_token(self, token) |
| Karl-main/app/ui/main_window.py | function | _fire_generation | 583 | def _fire_generation(self, history_override=None, start_in_thought=False) |
| Karl-main/app/ui/main_window.py | function | handle_generation_finished | 596 | def handle_generation_finished(self, final_thought, final_response, truncated=False, ended_in_thought=False) |
| Karl-main/app/ui/main_window.py | function | new_thought_token_direct | 636 | def new_thought_token_direct(self, text) |
| Karl-main/app/ui/main_window.py | function | handle_error | 641 | def handle_error(self, msg) |
| Karl-main/app/ui/main_window.py | function | start_agentic_loop | 649 | def start_agentic_loop(self) |
| Karl-main/app/ui/main_window.py | function | stop_agentic_loop | 671 | def stop_agentic_loop(self) |
| Karl-main/app/ui/main_window.py | function | handle_agentic_iteration | 678 | def handle_agentic_iteration(self, iteration, thought, response) |
| Karl-main/app/ui/main_window.py | function | handle_agentic_finished | 683 | def handle_agentic_finished(self, total) |
| Karl-main/app/ui/main_window.py | function | _rate_thumbs_up | 694 | def _rate_thumbs_up(self) |
| Karl-main/app/ui/main_window.py | function | _rate_thumbs_down | 708 | def _rate_thumbs_down(self) |
| Karl-main/app/ui/main_window.py | function | _refresh_curator_stats | 744 | def _refresh_curator_stats(self) |
| Karl-main/app/ui/main_window.py | function | _export_training_data | 753 | def _export_training_data(self) |
| Karl-main/app/utils/memory_manager.py | class | MemoryManager | 5 | class MemoryManager |
| Karl-main/app/utils/memory_manager.py | function | __init__ | 6 | def __init__(self, sessions_dir="data/sessions") |
| Karl-main/app/utils/memory_manager.py | function | save_session | 10 | def save_session(self, chat_history, system_prompt, filename=None) |
| Karl-main/app/utils/memory_manager.py | function | load_session | 27 | def load_session(self, filename) |
| Karl-main/app/utils/memory_manager.py | function | list_sessions | 37 | def list_sessions(self) |
| Karl-main/app/utils/rag_pipeline.py | class | RAGPipeline | 23 | class RAGPipeline |
| Karl-main/app/utils/rag_pipeline.py | function | __init__ | 27 | def __init__( self, model_name: str = "all-MiniLM-L6-v2", index_path: str = "data/vector_db", |
| Karl-main/app/utils/rag_pipeline.py | function | _load_index | 57 | def _load_index(self) |
| Karl-main/app/utils/rag_pipeline.py | function | save_index | 70 | def save_index(self) |
| Karl-main/app/utils/rag_pipeline.py | function | clear_index | 79 | def clear_index(self) |
| Karl-main/app/utils/rag_pipeline.py | function | extract_text | 90 | def extract_text(self, filepath: str) -> str |
| Karl-main/app/utils/rag_pipeline.py | function | chunk_text | 111 | def chunk_text(self, text: str, chunk_size: int = 200, overlap: int = 50) -> list[str] |
| Karl-main/app/utils/rag_pipeline.py | function | ingest_file | 122 | def ingest_file(self, filepath: str, chunk_size: int = 200, overlap: int = 50) -> int |
| Karl-main/app/utils/rag_pipeline.py | function | ingest_text | 158 | def ingest_text(self, text: str, source_name: str = "inline", chunk_size: int = 200, overlap: int = 50) -> int |
| Karl-main/app/utils/rag_pipeline.py | function | retrieve | 182 | def retrieve( self, query: str, top_k: int = 3, |
| Karl-main/app/utils/rag_pipeline.py | function | retrieve_with_metadata | 226 | def retrieve_with_metadata( self, query: str, top_k: int = 3, |
| Karl-main/app/utils/rag_pipeline.py | function | eval_retrieval | 262 | def eval_retrieval( self, query: str, expected_chunk_ids: list[int], |
| Karl-main/app/utils/rag_pipeline.py | function | list_sources | 305 | def list_sources(self) -> list[str] |
| Karl-main/app/utils/rag_pipeline.py | function | total_chunks | 317 | def total_chunks(self) -> int |
| Karl-main/app/utils/trace_logger.py | class | TraceLogger | 5 | class TraceLogger |
| Karl-main/app/utils/trace_logger.py | function | __init__ | 6 | def __init__(self, log_dir="data/logs/traces") |
| Karl-main/app/utils/trace_logger.py | function | log_generation | 13 | def log_generation( self, compiled_prompt, hyperparams, |
| Karl-main/app/utils/training_curator.py | function | _ensure_dir | 17 | def _ensure_dir() |
| Karl-main/app/utils/training_curator.py | function | save_example | 21 | def save_example(system_prompt: str, user_msg: str, good_response: str, source: str = "thumbs_up") |
| Karl-main/app/utils/training_curator.py | function | get_all_examples | 45 | def get_all_examples() -> list |
| Karl-main/app/utils/training_curator.py | function | get_stats | 61 | def get_stats() -> dict |
| Karl-main/app/utils/training_curator.py | function | export_unsloth | 73 | def export_unsloth(output_path: str = "data/training/export_unsloth.jsonl") |
| Karl-main/app/utils/training_curator.py | function | delete_example | 87 | def delete_example(index: int) |
| Karl-main/core/agentic_loop.py | function | should_continue | 7 | def should_continue(iteration: int, last_response: str) -> bool |
| Karl-main/core/agentic_loop.py | function | build_next_prompt | 27 | def build_next_prompt(last_response: str, iteration: int) -> str |
| Karl-main/core/cognitive_parser.py | function | parse_thought_stream | 4 | def parse_thought_stream(raw_text) |
| Karl-main/core/hardware_scout.py | function | get_hardware_profile | 4 | def get_hardware_profile() |
| Karl-main/core/interaction_loop.py | function | build_prompt | 4 | def build_prompt(system_prompt, chat_history) |
| Karl-main/core/prompt_templates.py | function | get_template | 93 | def get_template(name: str, **kwargs) -> str |
| Karl-main/core/prompt_templates.py | function | list_templates | 131 | def list_templates() -> list[str] |
| Karl-main/core/workflows.py | function | get_workflow | 80 | def get_workflow(name: str) -> dict |
| Karl-main/core/workflows.py | function | list_workflows | 93 | def list_workflows() -> list[tuple[str, str]] |
| Karl-main/download_test_model.py | function | download_file | 5 | def download_file(url, filepath) |
| Karl-main/engine_test.py | function | test_introspection_engine | 7 | def test_introspection_engine() |
| Karl-main/eval/benchmark_rag.py | class | QueryResult | 58 | class QueryResult |
| Karl-main/eval/benchmark_rag.py | function | run_benchmark | 67 | def run_benchmark(top_k: int = 3, contextual_headers: bool = False) -> list[QueryResult] |
| Karl-main/eval/benchmark_rag.py | function | print_results | 113 | def print_results(results: list[QueryResult], top_k: int) |
| Karl-main/eval/benchmark_rag.py | function | main | 148 | def main() |
| Karl-main/eval/graders.py | function | exact_match | 20 | def exact_match(output: str, expected: str) -> dict |
| Karl-main/eval/graders.py | function | json_valid | 37 | def json_valid(output: str, schema_keys: list[str] \| None = None) -> dict |
| Karl-main/eval/graders.py | function | keyword_hit | 97 | def keyword_hit(output: str, keywords: list[str], require_all: bool = True) -> dict |
| Karl-main/eval/graders.py | function | groundedness | 129 | def groundedness(output: str, context_chunks: list[str], min_overlap_words: int = 3) -> dict |
| Karl-main/eval/graders.py | function | not_in_context | 201 | def not_in_context(output: str) -> dict |
| Karl-main/eval/graders.py | function | run_grader | 225 | def run_grader(name: str, output: str, **kwargs) -> dict |
| Karl-main/eval/harness.py | class | CaseResult | 40 | class CaseResult |
| Karl-main/eval/harness.py | class | EvalReport | 54 | class EvalReport |
| Karl-main/eval/harness.py | function | print_summary | 68 | def print_summary(self) |
| Karl-main/eval/harness.py | class | EvalHarness | 96 | class EvalHarness |
| Karl-main/eval/harness.py | function | __init__ | 105 | def __init__(self, rag_pipeline=None) |
| Karl-main/eval/harness.py | function | _load_dataset | 114 | def _load_dataset(self, dataset_path: str) -> list[dict] |
| Karl-main/eval/harness.py | function | _resolve_context | 127 | def _resolve_context(self, case: dict, workflow_cfg: dict) -> list[str] |
| Karl-main/eval/harness.py | function | _build_system_prompt | 153 | def _build_system_prompt(self, template_name: str, context_chunks: list[str], case: dict) -> str |
| Karl-main/eval/harness.py | function | _run_model | 159 | def _run_model(self, system_prompt: str, user_prompt: str, hyperparams: dict) -> tuple[str, float] |
| Karl-main/eval/harness.py | function | _grade | 187 | def _grade(self, output: str, case: dict, context_chunks: list[str]) -> dict |
| Karl-main/eval/harness.py | function | run | 204 | def run( self, dataset_path: str, workflow_name: str, |
| Karl-main/eval/harness.py | function | save_report | 293 | def save_report(self, report: EvalReport, output_dir: str = "eval/results") -> str |
| Karl-main/eval/run_eval.py | function | parse_args | 43 | def parse_args() |
| Karl-main/eval/run_eval.py | function | dry_run_mode | 106 | def dry_run_mode(dataset_path: str, workflow_name: str) |
| Karl-main/eval/run_eval.py | function | main | 157 | def main() |
| Karl-main/main.py | function | main | 5 | def main() |
| Karl-main/training/validate_dataset.py | function | estimate_tokens | 34 | def estimate_tokens(text: str) -> int |
| Karl-main/training/validate_dataset.py | function | validate | 39 | def validate(path: str) -> bool |
| Karl-main/training/validate_dataset.py | function | _pass | 188 | def _pass(msg: str) |
| Karl-main/training/validate_dataset.py | function | _warn | 191 | def _warn(msg: str) |
| Karl-main/training/validate_dataset.py | function | _fail | 194 | def _fail(msg: str) |
| Karl-main/training/validate_dataset.py | function | main | 200 | def main() |
| app/engine/agent_memory.py | class | CodebaseMemory | 18 | class CodebaseMemory |
| app/engine/agent_memory.py | function | __init__ | 19 | def __init__( self, workspace_path: str, db_path: str \| os.PathLike[str] = "data/agent_memory.json", |
| app/engine/agent_memory.py | function | build_index | 28 | def build_index(self) -> dict[str, dict[str, list[dict[str, Any]]]] |
| app/engine/agent_memory.py | function | load | 59 | def load(self) -> dict[str, dict[str, list[dict[str, Any]]]] |
| app/engine/agent_memory.py | function | query_memory | 68 | def query_memory(self, keywords: list[str]) -> str |
| app/engine/agent_memory.py | function | _persist | 88 | def _persist(self) -> None |
| app/engine/agent_memory.py | function | _skip_path | 92 | def _skip_path(self, path: Path) -> bool |
| app/engine/agent_memory.py | function | _function_entry | 96 | def _function_entry(self, node: ast.FunctionDef \| ast.AsyncFunctionDef) -> dict[str, Any] |
| app/engine/agent_memory.py | function | _class_entry | 103 | def _class_entry(self, node: ast.ClassDef) -> dict[str, Any] |
| app/engine/agent_memory.py | function | _args | 115 | def _args(self, args: ast.arguments) -> list[str] |
| app/engine/agent_memory.py | function | _matches | 124 | def _matches(self, item: dict[str, Any], terms: set[str]) -> bool |
| app/engine/agent_memory.py | function | _format_function | 132 | def _format_function(self, rel_path: str, item: dict[str, Any]) -> str |
| app/engine/agent_memory.py | function | _format_class | 138 | def _format_class(self, rel_path: str, item: dict[str, Any]) -> str |
| app/engine/agent_memory.py | function | _format_method | 143 | def _format_method(self, rel_path: str, cls: dict[str, Any], item: dict[str, Any]) -> str |
| app/engine/agent_memory.py | function | keywords_from_task | 150 | def keywords_from_task(task: dict[str, Any]) -> list[str] |
| app/engine/agentic_thread.py | function | _get_gpu_temp | 34 | def _get_gpu_temp() -> float \| None |
| app/engine/agentic_thread.py | class | AgenticThread | 48 | class AgenticThread(QThread) |
| app/engine/agentic_thread.py | function | __init__ | 66 | def __init__(self, system_prompt, initial_history, hyperparams, retrieved_chunks=None, workflow="general_chat", template="reasoning_minimal", adapter_name=None, model_name=None) |
| app/engine/agentic_thread.py | function | request_stop | 101 | def request_stop(self) |
| app/engine/agentic_thread.py | function | _mark_token_activity | 106 | def _mark_token_activity(self) |
| app/engine/agentic_thread.py | function | _emit_watchdog_timeout | 109 | def _emit_watchdog_timeout(self) |
| app/engine/agentic_thread.py | function | _cleanup_after_watchdog_timeout | 115 | def _cleanup_after_watchdog_timeout(self, llm=None) |
| app/engine/agentic_thread.py | function | _start_watchdog | 133 | def _start_watchdog(self, llm=None) -> threading.Thread |
| app/engine/agentic_thread.py | function | _monitor | 139 | def _monitor() |
| app/engine/agentic_thread.py | function | _stop_watchdog | 151 | def _stop_watchdog(self, thread: threading.Thread \| None) |
| app/engine/agentic_thread.py | function | _token_count | 156 | def _token_count(self, llm, text: str) -> int |
| app/engine/agentic_thread.py | function | _message_token_count | 167 | def _message_token_count(self, llm, msg) -> int |
| app/engine/agentic_thread.py | function | _strip_historical_thoughts | 172 | def _strip_historical_thoughts(self, history, llm, budget) |
| app/engine/agentic_thread.py | function | _trim_history | 205 | def _trim_history(self, history, system_prompt, llm) |
| app/engine/agentic_thread.py | function | _run_single_generation | 244 | def _run_single_generation(self, llm, prompt, raw_file, thermal_enabled: bool = False) |
| app/engine/agentic_thread.py | function | run | 468 | def run(self) |
| app/engine/config_store.py | function | read_json | 60 | def read_json(path: str, default: Any = None) -> Any |
| app/engine/config_store.py | function | write_json_atomic | 77 | def write_json_atomic(path: str, data: Any, indent: int \| None = None) -> bool |
| app/engine/config_store.py | function | get_active_model | 107 | def get_active_model() -> dict |
| app/engine/config_store.py | function | set_active_model | 117 | def set_active_model(filename: str, adapter: str \| None = None) -> bool |
| app/engine/config_store.py | function | get_active_draft_model | 128 | def get_active_draft_model() -> dict |
| app/engine/config_store.py | function | set_active_draft_model | 142 | def set_active_draft_model(filename: str \| None, enabled: bool = False) -> bool |
| app/engine/config_store.py | function | get_engine_config | 150 | def get_engine_config() -> dict[str, Any] |
| app/engine/config_store.py | function | set_remote_engine_config | 160 | def set_remote_engine_config( enabled: bool, url: str \| None = None, token: str \| None = None, |
| app/engine/config_store.py | function | get_model_registry | 180 | def get_model_registry() -> list[dict] |
| app/engine/config_store.py | function | registry_entry | 203 | def registry_entry(filename: str) -> dict \| None |
| app/engine/config_store.py | function | registry_n_ctx | 211 | def registry_n_ctx(filename: str) -> int |
| app/engine/config_store.py | function | registry_draft_model_filename | 222 | def registry_draft_model_filename(filename: str) -> str \| None |
| app/engine/config_store.py | function | is_adapter_compatible | 233 | def is_adapter_compatible(model_filename: str, adapter_name: str) -> bool |
| app/engine/config_store.py | function | _validate_field | 297 | def _validate_field(key: str, raw_value: Any, default_value: Any) -> Any |
| app/engine/config_store.py | function | _quarantine_config | 343 | def _quarantine_config() -> None |
| app/engine/config_store.py | function | get_ui_config | 358 | def get_ui_config() -> dict |
| app/engine/config_store.py | function | save_ui_config | 416 | def save_ui_config(config: dict) -> bool |
| app/engine/config_store.py | function | get_mcp_config | 431 | def get_mcp_config() -> dict |
| app/engine/config_store.py | function | add_mcp_server | 439 | def add_mcp_server(name: str, command: str, args: list[str], env: dict \| None = None) -> bool |
| app/engine/config_store.py | function | remove_mcp_server | 448 | def remove_mcp_server(name: str) -> bool |
| app/engine/config_store.py | function | get_model_variants | 455 | def get_model_variants(base_model: str) -> list[dict] |
| app/engine/event_broker.py | class | EventBroker | 4 | class EventBroker |
| app/engine/event_broker.py | function | __init__ | 10 | def __init__(self) |
| app/engine/event_broker.py | function | get_instance | 22 | def get_instance(cls) -> "EventBroker" |
| app/engine/event_broker.py | function | subscribe | 29 | def subscribe(self, topic: str, callback: Callable[[dict], None]) -> None |
| app/engine/event_broker.py | function | unsubscribe | 40 | def unsubscribe(self, topic: str, callback: Callable[[dict], None]) -> None |
| app/engine/event_broker.py | function | publish | 48 | def publish(self, topic: str, data: dict) -> None |
| app/engine/feature_flags.py | class | FeatureFlagStore | 26 | class FeatureFlagStore |
| app/engine/feature_flags.py | function | __init__ | 50 | def __init__(self, path: str = FLAGS_FILE) -> None |
| app/engine/feature_flags.py | function | _load | 58 | def _load(self) -> None |
| app/engine/feature_flags.py | function | _save | 77 | def _save(self) -> None |
| app/engine/feature_flags.py | function | is_enabled | 87 | def is_enabled(self, flag_name: str) -> bool |
| app/engine/feature_flags.py | function | set_flag | 91 | def set_flag(self, flag_name: str, value: bool) -> None |
| app/engine/feature_flags.py | function | enter_safe_mode | 103 | def enter_safe_mode(self) -> None |
| app/engine/feature_flags.py | function | all_flags | 114 | def all_flags(self) -> dict[str, bool] |
| app/engine/feature_flags.py | function | check_boot_lock | 122 | def check_boot_lock(lock_path: str = LOCK_FILE) -> bool |
| app/engine/feature_flags.py | function | create_boot_lock | 127 | def create_boot_lock(lock_path: str = LOCK_FILE) -> None |
| app/engine/feature_flags.py | function | release_boot_lock | 138 | def release_boot_lock(lock_path: str = LOCK_FILE) -> None |
| app/engine/feature_flags.py | function | run_boot_guard | 149 | def run_boot_guard( store: FeatureFlagStore, lock_path: str = LOCK_FILE, ) -> bool |
| app/engine/hot_reload.py | class | HotReloadSignals | 12 | class HotReloadSignals(QObject) |
| app/engine/hot_reload.py | function | compile_and_reload | 21 | def compile_and_reload( module: ModuleType, label: str, notice: Callable[[str], None] \| None = None, |
| app/engine/image_analysis_thread.py | class | ImageAnalysisThread | 9 | class ImageAnalysisThread(QThread) |
| app/engine/image_analysis_thread.py | function | __init__ | 16 | def __init__( self, image_store, image_id: str, |
| app/engine/image_analysis_thread.py | function | run | 32 | def run(self) |
| app/engine/inference_service.py | class | InferenceService | 22 | class InferenceService |
| app/engine/inference_service.py | function | __init__ | 31 | def __init__(self, state) -> None |
| app/engine/inference_service.py | function | run_generation | 40 | def run_generation( self, prompt: str, system_prompt: str, |
| app/engine/inference_service.py | function | _agentic_done | 152 | def _agentic_done(total: int) -> None |
| app/engine/inference_service.py | function | _llm_done | 161 | def _llm_done( thought: str, response: str, truncated: bool, |
| app/engine/kv_cache.py | function | kv_cache_stats | 18 | def kv_cache_stats(llm: Any, prompt: str) -> dict[str, Any] |
| app/engine/kv_cache.py | function | log_cache_stats | 56 | def log_cache_stats(stats: dict[str, Any], ts: str) -> None |
| app/engine/llm_thread.py | function | _free_vram_mb | 39 | def _free_vram_mb() -> float \| None |
| app/engine/llm_thread.py | function | _write_performance_telemetry | 51 | def _write_performance_telemetry(entry: dict) -> None |
| app/engine/llm_thread.py | function | _get_gpu_temp | 69 | def _get_gpu_temp() -> float \| None |
| app/engine/llm_thread.py | class | LLMThread | 83 | class LLMThread(QThread) |
| app/engine/llm_thread.py | function | __init__ | 99 | def __init__(self, system_prompt, chat_history, hyperparams, retrieved_chunks=None, start_in_thought=False, workflow="general_chat", template="reasoning_minimal", adapter_name=None, model_name=None) |
| app/engine/llm_thread.py | function | request_stop | 144 | def request_stop(self) |
| app/engine/llm_thread.py | function | _mark_token_activity | 149 | def _mark_token_activity(self) |
| app/engine/llm_thread.py | function | _emit_watchdog_timeout | 152 | def _emit_watchdog_timeout(self) |
| app/engine/llm_thread.py | function | _cleanup_after_watchdog_timeout | 158 | def _cleanup_after_watchdog_timeout(self, llm=None) |
| app/engine/llm_thread.py | function | _start_watchdog | 176 | def _start_watchdog(self, llm=None) -> threading.Thread |
| app/engine/llm_thread.py | function | _monitor | 182 | def _monitor() |
| app/engine/llm_thread.py | function | _stop_watchdog | 194 | def _stop_watchdog(self, thread: threading.Thread \| None) |
| app/engine/llm_thread.py | function | _token_count | 199 | def _token_count(self, llm, text: str) -> int |
| app/engine/llm_thread.py | function | _message_token_count | 210 | def _message_token_count(self, llm, msg) -> int |
| app/engine/llm_thread.py | function | _strip_historical_thoughts | 217 | def _strip_historical_thoughts(self, history, llm, budget) |
| app/engine/llm_thread.py | function | _trim_history | 250 | def _trim_history(self, history, llm, system_prompt="") |
| app/engine/llm_thread.py | function | _cap | 262 | def _cap(msg) |
| app/engine/llm_thread.py | function | run | 287 | def run(self) |
| app/engine/mcp_client.py | class | MCPClientManager | 30 | class MCPClientManager |
| app/engine/mcp_client.py | function | get_instance | 35 | def get_instance(cls, config_path: str = "data/mcp_config.json") -> "MCPClientManager" |
| app/engine/mcp_client.py | function | reset_instance | 46 | def reset_instance(cls) |
| app/engine/mcp_client.py | function | get_tool_schemas | 54 | def get_tool_schemas(cls) -> list[dict] |
| app/engine/mcp_client.py | function | invalidate_cache | 68 | def invalidate_cache(cls) |
| app/engine/mcp_client.py | function | __init__ | 72 | def __init__(self, config_path: str = "data/mcp_config.json") |
| app/engine/mcp_client.py | function | _start_loop_thread | 79 | def _start_loop_thread(self) |
| app/engine/mcp_client.py | function | _run_event_loop | 85 | def _run_event_loop(self) |
| app/engine/mcp_client.py | function | _await_future | 91 | def _await_future(self, future) |
| app/engine/mcp_client.py | function | start | 98 | def start(self) |
| app/engine/mcp_client.py | function | stop | 105 | def stop(self) |
| app/engine/mcp_client.py | function | list_tools | 120 | def list_tools(self) -> List[Dict[str, Any]] |
| app/engine/mcp_client.py | function | call_tool | 127 | def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any] |
| app/engine/mini_train_thread.py | class | MiniTrainThread | 16 | class MiniTrainThread(QThread) |
| app/engine/mini_train_thread.py | function | __init__ | 24 | def __init__( self, dataset_text: str, config: dict, |
| app/engine/mini_train_thread.py | function | stop | 36 | def stop(self) |
| app/engine/mini_train_thread.py | function | run | 39 | def run(self) |
| app/engine/mini_train_thread.py | function | get_batch | 97 | def get_batch(split) |
| app/engine/mini_train_thread.py | function | estimate_loss | 107 | def estimate_loss() |
| app/engine/mini_transformer.py | class | CharTokenizer | 22 | class CharTokenizer |
| app/engine/mini_transformer.py | function | __init__ | 24 | def __init__(self) |
| app/engine/mini_transformer.py | function | fit | 30 | def fit(self, text: str) |
| app/engine/mini_transformer.py | function | encode | 39 | def encode(self, s: str) -> list[int] |
| app/engine/mini_transformer.py | function | decode | 42 | def decode(self, l: list[int]) -> str |
| app/engine/mini_transformer.py | class | Head | 46 | class Head(nn.Module) |
| app/engine/mini_transformer.py | function | __init__ | 48 | def __init__(self, n_embd: int, head_size: int, block_size: int, dropout: float = 0.1) |
| app/engine/mini_transformer.py | function | forward | 57 | def forward(self, x: torch.Tensor) -> torch.Tensor |
| app/engine/mini_transformer.py | class | MultiHeadAttention | 75 | class MultiHeadAttention(nn.Module) |
| app/engine/mini_transformer.py | function | __init__ | 77 | def __init__(self, n_heads: int, n_embd: int, head_size: int, block_size: int, dropout: float = 0.1) |
| app/engine/mini_transformer.py | function | forward | 83 | def forward(self, x: torch.Tensor) -> torch.Tensor |
| app/engine/mini_transformer.py | class | FeedForward | 92 | class FeedForward(nn.Module) |
| app/engine/mini_transformer.py | function | __init__ | 94 | def __init__(self, n_embd: int, dropout: float = 0.1) |
| app/engine/mini_transformer.py | function | forward | 103 | def forward(self, x: torch.Tensor) -> torch.Tensor |
| app/engine/mini_transformer.py | class | Block | 107 | class Block(nn.Module) |
| app/engine/mini_transformer.py | function | __init__ | 109 | def __init__(self, n_embd: int, n_heads: int, block_size: int, dropout: float = 0.1) |
| app/engine/mini_transformer.py | function | forward | 117 | def forward(self, x: torch.Tensor) -> torch.Tensor |
| app/engine/mini_transformer.py | class | MiniGPT | 124 | class MiniGPT(nn.Module) |
| app/engine/mini_transformer.py | function | __init__ | 126 | def __init__(self, vocab_size: int, n_embd: int = 128, n_heads: int = 4, n_layers: int = 4, block_size: int = 128, dropout: float = 0.1) |
| app/engine/mini_transformer.py | function | forward | 144 | def forward(self, idx: torch.Tensor, targets: torch.Tensor \| None = None) -> tuple[torch.Tensor, torch.Tensor \| None] |
| app/engine/mini_transformer.py | function | generate | 166 | def generate( self, idx: torch.Tensor, max_new_tokens: int, |
| app/engine/model_loader.py | class | ModelMemoryError | 16 | class ModelMemoryError(RuntimeError) |
| app/engine/model_loader.py | function | __init__ | 19 | def __init__(self, message: str, details: dict) |
| app/engine/model_loader.py | class | CircuitBreakerOpenException | 25 | class CircuitBreakerOpenException(RuntimeError) |
| app/engine/model_loader.py | function | __init__ | 34 | def __init__(self, message: str \| None = None) |
| app/engine/model_loader.py | class | ModelCircuitBreaker | 39 | class ModelCircuitBreaker |
| app/engine/model_loader.py | function | __init__ | 52 | def __init__( self, failure_threshold: int = 3, cooldown_duration: float = 30.0, |
| app/engine/model_loader.py | function | before_call | 66 | def before_call(self) -> None |
| app/engine/model_loader.py | function | record_success | 82 | def record_success(self) -> None |
| app/engine/model_loader.py | function | record_failure | 88 | def record_failure(self, exc: BaseException \| None = None) -> None |
| app/engine/model_loader.py | function | reset | 98 | def reset(self) -> None |
| app/engine/model_loader.py | function | _trip | 104 | def _trip(self) -> None |
| app/engine/model_loader.py | class | _LlamaDraftModelAdapter | 109 | class _LlamaDraftModelAdapter |
| app/engine/model_loader.py | function | __init__ | 112 | def __init__(self, draft_model) |
| app/engine/model_loader.py | class | ModelLoader | 116 | class ModelLoader |
| app/engine/model_loader.py | function | _read_registry_n_ctx | 147 | def _read_registry_n_ctx(cls, filename: str) -> int |
| app/engine/model_loader.py | function | _registry_entry | 152 | def _registry_entry(cls, filename: str) -> dict |
| app/engine/model_loader.py | function | _truthy | 159 | def _truthy(value) -> bool |
| app/engine/model_loader.py | function | _quantized_kv_cache_enabled | 167 | def _quantized_kv_cache_enabled(cls) -> bool |
| app/engine/model_loader.py | function | _ggml_type_q8_0 | 182 | def _ggml_type_q8_0() -> int |
| app/engine/model_loader.py | function | _adapter_path | 190 | def _adapter_path(cls, adapter_name: str \| None) -> str \| None |
| app/engine/model_loader.py | function | _resolve_model_path | 207 | def _resolve_model_path(cls, model_path: str) -> str |
| app/engine/model_loader.py | function | _bench_vram_bandwidth | 222 | def _bench_vram_bandwidth() -> float \| None |
| app/engine/model_loader.py | function | load_latency_s | 285 | def load_latency_s(cls) -> float \| None |
| app/engine/model_loader.py | function | vram_bandwidth_gbs | 290 | def vram_bandwidth_gbs(cls) -> float \| None |
| app/engine/model_loader.py | function | _load_adapter_special_tokens | 300 | def _load_adapter_special_tokens(adapter_dir: str) -> list[dict] |
| app/engine/model_loader.py | function | _get_unk_id | 364 | def _get_unk_id(llm) -> int \| None |
| app/engine/model_loader.py | function | _try_register_token_c_layer | 380 | def _try_register_token_c_layer(cls, llm, token_text: str, expected_id: int) -> bool |
| app/engine/model_loader.py | function | _inspect_adapter_vocab | 407 | def _inspect_adapter_vocab(cls, adapter_name: str, llm) -> dict |
| app/engine/model_loader.py | function | vocab_leak_report | 546 | def vocab_leak_report(cls) -> dict |
| app/engine/model_loader.py | function | vocab_leak_tokens | 551 | def vocab_leak_tokens(cls) -> dict |
| app/engine/model_loader.py | function | estimate_load_memory | 569 | def estimate_load_memory(cls, model_path: str, adapter_name: str \| None = None) -> dict |
| app/engine/model_loader.py | function | _show_memory_warning_dialog | 627 | def _show_memory_warning_dialog(cls, message: str) |
| app/engine/model_loader.py | function | preflight_model_load | 639 | def preflight_model_load( cls, model_path: str, adapter_name: str \| None = None, |
| app/engine/model_loader.py | function | _touch_activity | 686 | def _touch_activity(cls) -> None |
| app/engine/model_loader.py | function | _start_idle_watcher | 691 | def _start_idle_watcher(cls) -> None |
| app/engine/model_loader.py | function | _watcher | 697 | def _watcher() |
| app/engine/model_loader.py | function | get_instance | 736 | def get_instance(cls, model_path: str \| None = None, adapter_name: str \| None = None, draft_model_path: str \| None = None) -> Llama |
| app/engine/model_loader.py | function | _attempt_load | 887 | def _attempt_load(ctx_size, ts=None) |
| app/engine/model_loader.py | function | reset_instance | 1143 | def reset_instance(cls) |
| app/engine/model_loader.py | function | _free_vram_mb | 1206 | def _free_vram_mb() -> float \| None |
| app/engine/model_loader.py | function | _attach_kv_cache | 1217 | def _attach_kv_cache(cls) -> None |
| app/engine/model_loader.py | function | _raise_if_inference_active | 1252 | def _raise_if_inference_active(cls, operation: str = "reset ModelLoader") -> None |
| app/engine/model_loader.py | function | lock_instance | 1263 | def lock_instance(cls) -> None |
| app/engine/model_loader.py | function | unlock_instance | 1274 | def unlock_instance(cls) -> None |
| app/engine/model_loader.py | function | acquire_instance | 1286 | def acquire_instance(cls, **kwargs) |
| app/engine/model_loader.py | function | _remote_fallback | 1293 | def _remote_fallback(cls, reason: str) -> None |
| app/engine/model_loader.py | function | last_remote_fallback_reason | 1306 | def last_remote_fallback_reason(cls) -> str \| None |
| app/engine/model_loader.py | function | reset_circuit_breaker | 1310 | def reset_circuit_breaker(cls) -> None |
| app/engine/model_loader.py | function | is_instance_locked | 1316 | def is_instance_locked(cls) -> bool |
| app/engine/model_loader.py | function | context_limit | 1322 | def context_limit(cls) -> int |
| app/engine/model_loader.py | function | model_name | 1327 | def model_name(cls) -> str |
| app/engine/model_loader.py | function | n_ctx | 1333 | def n_ctx(cls) -> int |
| app/engine/model_loader.py | function | is_loaded | 1357 | def is_loaded(cls) -> bool |
| app/engine/model_loader.py | function | is_speculative | 1363 | def is_speculative(cls) -> bool |
| app/engine/model_loader.py | function | get_quantization | 1369 | def get_quantization(cls) -> str \| None |
| app/engine/model_loader.py | function | vram_estimate_gb | 1379 | def vram_estimate_gb(cls) -> float \| None |
| app/engine/offline_guard.py | class | OfflineNetworkError | 32 | class OfflineNetworkError(RuntimeError) |
| app/engine/offline_guard.py | function | _truthy | 36 | def _truthy(value: object) -> bool |
| app/engine/offline_guard.py | function | online_execution_enabled | 40 | def online_execution_enabled() -> bool |
| app/engine/offline_guard.py | function | _is_local_url | 53 | def _is_local_url(url: object) -> bool |
| app/engine/offline_guard.py | function | assert_online_allowed | 61 | def assert_online_allowed(url: object = None, *, operation: str = "network request") -> None |
| app/engine/offline_guard.py | function | install | 75 | def install() -> None |
| app/engine/offline_guard.py | function | guarded_requests_request | 93 | def guarded_requests_request(session, method, url, *args, **kwargs) |
| app/engine/offline_guard.py | function | guarded_urlopen | 106 | def guarded_urlopen(url, *args, **kwargs) |
| app/engine/offline_guard.py | function | guarded_httpx_request | 122 | def guarded_httpx_request(method, url, *args, **kwargs) |
| app/engine/offline_guard.py | function | guarded_httpx_client_request | 126 | def guarded_httpx_client_request(self, method, url, *args, **kwargs) |
| app/engine/offline_guard.py | function | apply_for_current_config | 141 | def apply_for_current_config() -> None |
| app/engine/offline_guard.py | function | is_guard_installed | 170 | def is_guard_installed() -> bool |
| app/engine/offline_guard.py | function | hf_vars_applied | 175 | def hf_vars_applied() -> bool |
| app/engine/quantizer_thread.py | function | _locate_llama_quantize | 40 | def _locate_llama_quantize(input_path: str \| None = None) -> str \| None |
| app/engine/quantizer_thread.py | function | _parse_progress | 74 | def _parse_progress(line: str) -> int \| None |
| app/engine/quantizer_thread.py | class | QuantizerThread | 94 | class QuantizerThread(QThread) |
| app/engine/quantizer_thread.py | function | __init__ | 109 | def __init__( self, input_path: str, output_path: str, |
| app/engine/quantizer_thread.py | function | cancel | 123 | def cancel(self) -> None |
| app/engine/quantizer_thread.py | function | run | 133 | def run(self) -> None |
| app/engine/reflection_loop.py | function | run_reflection_loop | 4 | def run_reflection_loop(task: dict, failed_thought: str, failed_response: str, error_traceback: str) -> tuple[str, str] |
| app/engine/remote_rpc_client.py | class | RemoteRPCError | 17 | class RemoteRPCError(RuntimeError) |
| app/engine/remote_rpc_client.py | function | _is_private_host | 21 | def _is_private_host(hostname: str \| None) -> bool |
| app/engine/remote_rpc_client.py | function | _ssl_context_for_url | 30 | def _ssl_context_for_url(url: str) -> ssl.SSLContext \| None |
| app/engine/remote_rpc_client.py | function | _with_token_query | 42 | def _with_token_query(url: str, token: str) -> str |
| app/engine/remote_rpc_client.py | class | RemoteRPCModel | 50 | class RemoteRPCModel |
| app/engine/remote_rpc_client.py | function | __init__ | 60 | def __init__( self, server_url: str, auth_token: str, |
| app/engine/remote_rpc_client.py | function | tokenize | 76 | def tokenize(self, data: bytes \| str, add_bos: bool = False) -> list[int] |
| app/engine/remote_rpc_client.py | function | __call__ | 88 | def __call__(self, prompt: str, **kwargs) -> Iterator[dict[str, Any]] |
| app/engine/remote_rpc_client.py | function | _stream | 97 | def _stream(self, prompt: str, kwargs: dict[str, Any]) -> Iterator[dict[str, Any]] |
| app/engine/self_play_thread.py | class | SelfPlayThread | 40 | class SelfPlayThread(QThread) |
| app/engine/self_play_thread.py | function | __init__ | 59 | def __init__( self, *, model_path: str \| None = None, |
| app/engine/self_play_thread.py | function | request_stop | 79 | def request_stop(self) -> None |
| app/engine/self_play_thread.py | function | run | 85 | def run(self) -> None |
| app/engine/self_play_thread.py | function | _llm_call | 164 | def _llm_call(self, llm: Any, prompt: str, max_tokens: int, temperature: float) -> str |
| app/engine/self_play_thread.py | function | _build_prompt | 182 | def _build_prompt(self, system: str, user: str) -> str |
| app/engine/self_play_thread.py | function | _generate_task | 189 | def _generate_task(self, llm: Any, iteration: int) -> str |
| app/engine/self_play_thread.py | function | _generate_response | 198 | def _generate_response(self, llm: Any, task: str) -> str |
| app/engine/self_play_thread.py | function | _verify | 203 | def _verify(self, response: str, task: str, iteration: int) -> tuple[bool, float] |
| app/engine/self_play_thread.py | function | _heuristic_verify | 248 | def _heuristic_verify(self, response: str) -> tuple[bool, float] |
| app/engine/swarm_agents.py | function | _safe_workspace_path | 26 | def _safe_workspace_path(workspace_path: str, rel: str) -> str \| None |
| app/engine/swarm_agents.py | function | register_tool | 51 | def register_tool(name: str, description: str) |
| app/engine/swarm_agents.py | function | decorator | 53 | def decorator(fn) |
| app/engine/swarm_agents.py | function | get_tool_schema_block | 58 | def get_tool_schema_block() -> str |
| app/engine/swarm_agents.py | function | _tool_write_file | 68 | def _tool_write_file(workspace_path: str, args: dict) -> str |
| app/engine/swarm_agents.py | function | _tool_read_file | 82 | def _tool_read_file(workspace_path: str, args: dict) -> str |
| app/engine/swarm_agents.py | function | _tool_grep_workspace | 98 | def _tool_grep_workspace(workspace_path: str, args: dict) -> str |
| app/engine/swarm_agents.py | function | _tool_shell_run | 122 | def _tool_shell_run(workspace_path: str, args: dict) -> str |
| app/engine/swarm_agents.py | function | _tool_lint_python | 139 | def _tool_lint_python(workspace_path: str, args: dict) -> str |
| app/engine/swarm_agents.py | class | BaseSwarmAgent | 160 | class BaseSwarmAgent |
| app/engine/swarm_agents.py | function | __init__ | 161 | def __init__(self, system_prompt: str, temperature: float = 0.2, max_tokens: int = 2048) |
| app/engine/swarm_agents.py | function | clean_output | 166 | def clean_output(self, raw: str) -> str |
| app/engine/swarm_agents.py | function | call_llm | 175 | def call_llm(self, user_prompt: str) -> str |
| app/engine/swarm_agents.py | class | ArchitectAgent | 193 | class ArchitectAgent(BaseSwarmAgent) |
| app/engine/swarm_agents.py | function | __init__ | 211 | def __init__(self) |
| app/engine/swarm_agents.py | function | create_plan | 214 | def create_plan(self, objective: str, files_context: Dict[str, str]) -> Dict[str, Any] |
| app/engine/swarm_agents.py | function | parse_reasoning_and_tool | 238 | def parse_reasoning_and_tool(raw_text: str) -> tuple[Optional[str], Optional[str]] |
| app/engine/swarm_agents.py | class | CoderAgent | 272 | class CoderAgent(BaseSwarmAgent) |
| app/engine/swarm_agents.py | function | __init__ | 294 | def __init__(self) |
| app/engine/swarm_agents.py | function | generate | 297 | def generate(self, task: dict, workspace_context: dict, workspace_path: str = ".", token_callback: Callable[[str], None] \| None = None) -> str |
| app/engine/swarm_agents.py | function | edit_file | 447 | def edit_file( self, filepath: str, current_content: str, |
| app/engine/swarm_agents.py | class | TesterAgent | 463 | class TesterAgent |
| app/engine/swarm_agents.py | function | __init__ | 469 | def __init__(self, workspace_path: str) |
| app/engine/swarm_agents.py | function | run | 472 | def run(self, command: str, workspace_path: str) -> tuple[bool, str] |
| app/engine/swarm_agents.py | function | run_test_command | 477 | def run_test_command(self, test_cmd: str) -> Dict[str, Any] |
| app/engine/swarm_orchestrator.py | function | get_python_imports | 25 | def get_python_imports(content: str) -> List[str] |
| app/engine/swarm_orchestrator.py | class | SwarmSessionState | 43 | class SwarmSessionState |
| app/engine/swarm_orchestrator.py | function | __init__ | 45 | def __init__(self, workspace_path: str, objective: str, test_command: str) |
| app/engine/swarm_orchestrator.py | class | SwarmOrchestratorThread | 55 | class SwarmOrchestratorThread(QThread) |
| app/engine/swarm_orchestrator.py | function | __init__ | 71 | def __init__(self, workspace_path: str, objective: str, test_command: str, hyperparams: dict = None) |
| app/engine/swarm_orchestrator.py | function | _process_events_if_main_thread | 92 | def _process_events_if_main_thread(self) |
| app/engine/swarm_orchestrator.py | function | request_stop | 100 | def request_stop(self) |
| app/engine/swarm_orchestrator.py | function | commit_selected_edits | 105 | def commit_selected_edits(self, selected_filepaths: list[str]) |
| app/engine/swarm_orchestrator.py | function | _workspace_root | 110 | def _workspace_root(self) -> Path |
| app/engine/swarm_orchestrator.py | function | _resolve_task_path | 113 | def _resolve_task_path(self, filepath: str) -> tuple[str, Path] |
| app/engine/swarm_orchestrator.py | function | _validate_task | 133 | def _validate_task(self, task: dict[str, Any]) -> dict[str, str] |
| app/engine/swarm_orchestrator.py | function | _validate_tasks | 145 | def _validate_tasks(self, raw_tasks: Any) -> list[dict[str, str]] |
| app/engine/swarm_orchestrator.py | function | scan_workspace | 162 | def scan_workspace(self) -> Dict[str, str] |
| app/engine/swarm_orchestrator.py | function | build_dependency_layers | 183 | def build_dependency_layers(self, tasks: List[Dict[str, str]]) -> List[List[Dict[str, str]]] |
| app/engine/swarm_orchestrator.py | function | _run_layer | 235 | def _run_layer(self, layer_tasks: list, layer_index: int, total_layers: int, layer_failure_traces: dict) -> bool |
| app/engine/swarm_orchestrator.py | function | _run_one | 241 | def _run_one(task: dict) -> tuple[str, bool, str] |
| app/engine/swarm_orchestrator.py | function | _tok_cb | 248 | def _tok_cb(tok: str) |
| app/engine/swarm_orchestrator.py | function | run | 406 | def run(self) |
| app/engine/task_supervisor.py | class | TaskStatus | 40 | class TaskStatus(str, Enum) |
| app/engine/task_supervisor.py | class | TaskRecord | 49 | class TaskRecord |
| app/engine/task_supervisor.py | class | TaskSupervisor | 59 | class TaskSupervisor |
| app/engine/task_supervisor.py | function | __init__ | 65 | def __init__(self) -> None |
| app/engine/task_supervisor.py | function | instance | 71 | def instance(cls) -> TaskSupervisor |
| app/engine/task_supervisor.py | function | reset_instance | 79 | def reset_instance(cls) -> None |
| app/engine/task_supervisor.py | function | register | 86 | def register( self, name: str, *, |
| app/engine/task_supervisor.py | function | update_progress | 124 | def update_progress(self, task_id: str, progress: float) -> None |
| app/engine/task_supervisor.py | function | cancel | 132 | def cancel(self, task_id: str) -> bool |
| app/engine/task_supervisor.py | function | finish | 160 | def finish(self, task_id: str) -> None |
| app/engine/task_supervisor.py | function | fail | 174 | def fail(self, task_id: str, error: str) -> None |
| app/engine/task_supervisor.py | function | add_cleanup_hook | 188 | def add_cleanup_hook(self, task_id: str, hook: Callable[[], None]) -> None |
| app/engine/task_supervisor.py | function | status | 199 | def status(self, task_id: str) -> TaskStatus \| None |
| app/engine/task_supervisor.py | function | progress | 204 | def progress(self, task_id: str) -> float |
| app/engine/task_supervisor.py | function | error | 209 | def error(self, task_id: str) -> str |
| app/engine/task_supervisor.py | function | get | 214 | def get(self, task_id: str) -> TaskRecord \| None |
| app/engine/task_supervisor.py | function | active_tasks | 218 | def active_tasks(self) -> list[TaskRecord] |
| app/engine/task_supervisor.py | function | all_tasks | 226 | def all_tasks(self) -> list[TaskRecord] |
| app/engine/task_supervisor.py | function | cancel_all | 230 | def cancel_all(self) -> int |
| app/engine/task_supervisor.py | function | _run_hooks | 239 | def _run_hooks(self, hooks: list[Callable], task_id: str) -> None |
| app/engine/task_supervisor.py | function | _trace | 246 | def _trace(self, event: str, task_id: str, name: str, *, error: str = "") -> None |
| app/engine/tool_executor.py | function | build_tool_schema_prompt | 13 | def build_tool_schema_prompt(tools: list[dict]) -> str |
| app/engine/tool_executor.py | function | parse_tool_calls | 42 | def parse_tool_calls(text: str) -> list[dict] |
| app/engine/tool_executor.py | function | execute_tool_calls | 58 | def execute_tool_calls(calls: list[dict]) -> list[str] |
| app/engine/websocket_server.py | class | WebSocketServerManager | 41 | class WebSocketServerManager |
| app/engine/websocket_server.py | function | get_instance | 48 | def get_instance(cls, port: int = 8080, state=None) -> "WebSocketServerManager" |
| app/engine/websocket_server.py | function | reset_instance | 56 | def reset_instance(cls) |
| app/engine/websocket_server.py | function | __init__ | 63 | def __init__(self, port: int = 8080, state=None) |
| app/engine/websocket_server.py | function | _ensure_ssl_certs | 166 | def _ensure_ssl_certs(self) |
| app/engine/websocket_server.py | function | _init_security | 187 | def _init_security(self) |
| app/engine/websocket_server.py | function | _generate_token | 239 | def _generate_token(self) -> str |
| app/engine/websocket_server.py | function | _rotate_token | 242 | def _rotate_token(self) -> None |
| app/engine/websocket_server.py | function | _persist_token_store | 258 | def _persist_token_store(self) -> None |
| app/engine/websocket_server.py | function | add_scoped_token | 275 | def add_scoped_token(self, scopes: list[str]) -> str |
| app/engine/websocket_server.py | function | _get_token_scopes | 285 | def _get_token_scopes(self, token: str) -> list[str] \| None |
| app/engine/websocket_server.py | function | _validate_token | 297 | def _validate_token(self, token: str) -> bool |
| app/engine/websocket_server.py | function | _is_safe_path | 301 | def _is_safe_path(self, path: str) -> bool |
| app/engine/websocket_server.py | function | _seed_codex | 320 | def _seed_codex(self) |
| app/engine/websocket_server.py | function | _active_model_config | 350 | def _active_model_config(self) -> dict |
| app/engine/websocket_server.py | function | _read_model_registry | 353 | def _read_model_registry(self) -> list[dict] |
| app/engine/websocket_server.py | function | _list_models | 356 | def _list_models(self) -> dict |
| app/engine/websocket_server.py | function | _set_active_model | 422 | def _set_active_model(self, filename: str, adapter: str \| None = None) -> dict |
| app/engine/websocket_server.py | function | _prompt_pairs_dir | 448 | def _prompt_pairs_dir(self) -> str |
| app/engine/websocket_server.py | function | _safe_prompt_pair_name | 453 | def _safe_prompt_pair_name(self, name: str) -> str |
| app/engine/websocket_server.py | function | _prompt_pair_path | 459 | def _prompt_pair_path(self, name: str) -> str |
| app/engine/websocket_server.py | function | _list_prompt_pairs | 462 | def _list_prompt_pairs(self) -> dict |
| app/engine/websocket_server.py | function | _get_prompt_pair | 486 | def _get_prompt_pair(self, name: str) -> dict |
| app/engine/websocket_server.py | function | _save_prompt_pair | 496 | def _save_prompt_pair(self, params: dict) -> dict |
| app/engine/websocket_server.py | function | _delete_prompt_pair | 521 | def _delete_prompt_pair(self, name: str) -> dict |
| app/engine/websocket_server.py | function | _kb_supported_extensions | 528 | def _kb_supported_extensions(self) -> set[str] |
| app/engine/websocket_server.py | function | _kb_snapshot | 531 | def _kb_snapshot(self) -> dict |
| app/engine/websocket_server.py | function | _collect_kb_files | 557 | def _collect_kb_files(self, path: str, recursive: bool) -> list[str] |
| app/engine/websocket_server.py | function | _start_kb_ingest | 588 | def _start_kb_ingest(self, params: dict) -> dict |
| app/engine/websocket_server.py | function | worker | 607 | def worker() |
| app/engine/websocket_server.py | function | progress_cb | 610 | def progress_cb(current: int, total_files: int, event: dict) |
| app/engine/websocket_server.py | function | _search_kb | 681 | def _search_kb(self, params: dict) -> dict |
| app/engine/websocket_server.py | function | _runtime_status | 720 | def _runtime_status(self) -> dict |
| app/engine/websocket_server.py | function | _rpc_error_response | 761 | def _rpc_error_response( self, code: int, req_id: Any = None, |
| app/engine/websocket_server.py | function | _rpc_result_response | 780 | def _rpc_result_response(self, req_id: Any, result: Any) -> dict |
| app/engine/websocket_server.py | function | _parse_json_rpc_request | 800 | def _parse_json_rpc_request(self, message: str) -> tuple[dict \| None, dict \| None] |
| app/engine/websocket_server.py | function | _validate_rpc_params | 833 | def _validate_rpc_params(self, method: str, params: dict) -> str \| None |
| app/engine/websocket_server.py | function | require_string | 834 | def require_string(name: str) -> str \| None |
| app/engine/websocket_server.py | function | _record_generation_metrics | 870 | def _record_generation_metrics(self, diagnostics: dict \| None) -> None |
| app/engine/websocket_server.py | function | _metric_float | 893 | def _metric_float(self, value: Any) -> float |
| app/engine/websocket_server.py | function | _process_rss_bytes | 901 | def _process_rss_bytes(self) -> int |
| app/engine/websocket_server.py | function | _prometheus_metrics | 908 | def _prometheus_metrics(self) -> str |
| app/engine/websocket_server.py | function | _http_response | 939 | def _http_response(self, status_code: int, reason: str, content_type: str, body: str) -> Response |
| app/engine/websocket_server.py | function | _is_websocket_upgrade | 950 | def _is_websocket_upgrade(self, request) -> bool |
| app/engine/websocket_server.py | function | _process_http_request | 959 | def _process_http_request(self, connection, request) -> Response \| None |
| app/engine/websocket_server.py | function | force_revoke | 1001 | def force_revoke(self) -> None |
| app/engine/websocket_server.py | function | _start_loop_thread | 1035 | def _start_loop_thread(self) |
| app/engine/websocket_server.py | function | _run_loop | 1041 | def _run_loop(self) |
| app/engine/websocket_server.py | function | _build_ssl_context | 1051 | def _build_ssl_context(self) |
| app/engine/websocket_server.py | function | _write_service_discovery | 1097 | def _write_service_discovery(self) -> None |
| app/engine/websocket_server.py | function | _remove_service_discovery | 1113 | def _remove_service_discovery(self) -> None |
| app/engine/websocket_server.py | function | stop | 1121 | def stop(self) |
| app/engine/websocket_server.py | function | _on_chat_finished | 1558 | def _on_chat_finished( thought: str, response: str, diagnostics: dict ) -> None |
| app/engine/websocket_server.py | function | _on_chat_error | 1568 | def _on_chat_error(err: str) -> None |
| app/engine/websocket_server.py | function | run_auto_train | 1780 | def run_auto_train() |
| app/engine/websocket_server.py | function | get_client_info | 2002 | def get_client_info(self) -> list[dict] |
| app/engine/websocket_server.py | function | _send_notification | 2021 | def _send_notification(self, method: str, params: dict) |
| app/engine/websocket_server.py | function | client_count | 2028 | def client_count(self) -> int |
| app/repository/session_repository.py | class | SessionRepository | 5 | class SessionRepository |
| app/repository/session_repository.py | function | __init__ | 12 | def __init__(self, sessions_dir="data/sessions") |
| app/repository/session_repository.py | function | save | 16 | def save(self, session_id: str, session_tree: dict) -> None |
| app/repository/session_repository.py | function | get | 32 | def get(self, session_id: str) -> dict \| None |
| app/repository/session_repository.py | function | list_all | 43 | def list_all(self) -> list[dict] |
| app/repository/session_repository.py | function | delete | 69 | def delete(self, session_id: str) -> bool |
| app/state.py | class | AppState | 37 | class AppState(QObject) |
| app/state.py | function | __init__ | 40 | def __init__(self) |
| app/state.py | function | cached_bridge_token | 100 | def cached_bridge_token(self) -> str \| None |
| app/state.py | function | save_to_disk | 103 | def save_to_disk(self) -> bool |
| app/state.py | function | load_from_disk | 112 | def load_from_disk(self) -> None |
| app/state.py | function | _load_from_disk_silent | 124 | def _load_from_disk_silent(self) -> None |
| app/state.py | function | _emit_state_changed | 137 | def _emit_state_changed(self, name: str, value: object) -> None |
| app/state.py | function | __setattr__ | 140 | def __setattr__(self, name, value) |
| app/ui/main_window.py | class | _ModelInitThread | 35 | class _ModelInitThread(QThread) |
| app/ui/main_window.py | function | run | 41 | def run(self) |
| app/ui/main_window.py | class | MainWindow | 54 | class MainWindow(QMainWindow) |
| app/ui/main_window.py | function | __init__ | 57 | def __init__(self) |
| app/ui/main_window.py | function | _setup_shortcuts | 80 | def _setup_shortcuts(self) |
| app/ui/main_window.py | function | _make_workspace_switcher | 124 | def _make_workspace_switcher(self, idx) |
| app/ui/main_window.py | function | _open_command_palette | 127 | def _open_command_palette(self) |
| app/ui/main_window.py | function | _focus_active_input | 132 | def _focus_active_input(self) |
| app/ui/main_window.py | function | _build_ui | 146 | def _build_ui(self) |
| app/ui/main_window.py | function | resizeEvent | 201 | def resizeEvent(self, event) |
| app/ui/main_window.py | function | _connect_signals | 206 | def _connect_signals(self) |
| app/ui/main_window.py | function | _setup_autosave_checkpoint_timer | 219 | def _setup_autosave_checkpoint_timer(self) |
| app/ui/main_window.py | function | _autosave_active_checkpoint | 225 | def _autosave_active_checkpoint(self) |
| app/ui/main_window.py | function | _check_autosave_recovery | 248 | def _check_autosave_recovery(self) |
| app/ui/main_window.py | function | _restore_autosave_checkpoint | 272 | def _restore_autosave_checkpoint(self, checkpoint: dict) |
| app/ui/main_window.py | function | _init_model | 320 | def _init_model(self) |
| app/ui/main_window.py | function | _on_startup_model_loaded | 329 | def _on_startup_model_loaded(self, name: str, adapter: object) |
| app/ui/main_window.py | function | _on_startup_model_failed | 349 | def _on_startup_model_failed(self, message: str) |
| app/ui/main_window.py | function | _on_status_changed | 354 | def _on_status_changed(self, text: str, active: bool) |
| app/ui/main_window.py | function | _on_adapter_changed | 365 | def _on_adapter_changed(self, name: str) |
| app/ui/main_window.py | function | _on_state_changed | 368 | def _on_state_changed(self, name: str, value: object) |
| app/ui/main_window.py | function | _open_appearance_controls | 384 | def _open_appearance_controls(self) |
| app/ui/main_window.py | function | _load_theme_config | 389 | def _load_theme_config(self) |
| app/ui/main_window.py | function | _apply_theme_from_state | 409 | def _apply_theme_from_state(self) |
| app/ui/main_window.py | function | apply_layout_preset | 427 | def apply_layout_preset(self, preset_name: str) |
| app/ui/main_window.py | function | _init_websocket_server | 467 | def _init_websocket_server(self) |
| app/ui/main_window.py | function | showEvent | 474 | def showEvent(self, event) |
| app/ui/main_window.py | function | _poll_bridge_status | 486 | def _poll_bridge_status(self) |
| app/ui/main_window.py | function | closeEvent | 504 | def closeEvent(self, event) |
| app/ui/sidebar.py | class | _SidebarButton | 19 | class _SidebarButton(QPushButton) |
| app/ui/sidebar.py | function | __init__ | 22 | def __init__(self, icon: str, label: str, index: int, parent=None) |
| app/ui/sidebar.py | function | set_compact | 36 | def set_compact(self, compact: bool) |
| app/ui/sidebar.py | function | set_active | 47 | def set_active(self, active: bool) |
| app/ui/sidebar.py | class | Sidebar | 54 | class Sidebar(QWidget) |
| app/ui/sidebar.py | function | __init__ | 59 | def __init__(self, parent=None) |
| app/ui/sidebar.py | function | _select | 100 | def _select(self, index: int) |
| app/ui/sidebar.py | function | select | 105 | def select(self, index: int) |
| app/ui/sidebar.py | function | set_compact | 109 | def set_compact(self, compact: bool) |
| app/ui/themes.py | function | darken_hex_color | 432 | def darken_hex_color(hex_str: str, factor: float = 0.7) -> str |
| app/ui/themes.py | function | _tint_hex_color | 448 | def _tint_hex_color(hex_str: str, r_mod: int, g_mod: int, b_mod: int) -> str |
| app/ui/themes.py | function | hex_to_rgba | 464 | def hex_to_rgba(hex_str: str, alpha: float) -> str |
| app/ui/themes.py | function | get_theme_colors | 477 | def get_theme_colors(state_or_name, custom_accent=None, bg_tone="Default", mode: str = None) -> dict |
| app/ui/themes.py | function | get_theme_stylesheet | 576 | def get_theme_stylesheet(state_or_name, custom_accent=None, bg_tone="Default", mode: str = None) -> str |
| app/ui/themes.py | function | stylesheet | 1248 | def stylesheet(accent: str = ACCENT_DEFAULT, mode: str = "midnight") -> str |
| app/ui/themes.py | class | DummyState | 1250 | class DummyState |
| app/ui/widgets/command_palette.py | class | CommandPalette | 5 | class CommandPalette(QDialog) |
| app/ui/widgets/command_palette.py | function | __init__ | 6 | def __init__(self, main_window, parent=None) |
| app/ui/widgets/command_palette.py | function | _populate_list | 69 | def _populate_list(self) |
| app/ui/widgets/command_palette.py | function | _filter_commands | 76 | def _filter_commands(self, text) |
| app/ui/widgets/command_palette.py | function | keyPressEvent | 86 | def keyPressEvent(self, event: QKeyEvent) |
| app/ui/widgets/command_palette.py | function | _execute_selected | 105 | def _execute_selected(self) |
| app/ui/widgets/command_palette.py | function | showEvent | 124 | def showEvent(self, event) |
| app/ui/widgets/glow_panel.py | class | GlowPanel | 5 | class GlowPanel(QFrame) |
| app/ui/widgets/glow_panel.py | function | __init__ | 10 | def __init__(self, state, parent=None, glow_color=None, blur_radius=12) |
| app/ui/widgets/glow_panel.py | function | set_glow_color | 21 | def set_glow_color(self, hex_color: str) |
| app/ui/widgets/glow_panel.py | function | _apply_glow | 25 | def _apply_glow(self) |
| app/ui/widgets/glow_panel.py | function | update_style | 48 | def update_style(self) |
| app/ui/widgets/model_combo.py | class | ModelComboBox | 15 | class ModelComboBox(QComboBox) |
| app/ui/widgets/model_combo.py | function | __init__ | 18 | def __init__(self, state, parent=None, short_labels: bool = True) |
| app/ui/widgets/model_combo.py | function | update_theme | 24 | def update_theme(self) |
| app/ui/widgets/model_combo.py | function | refresh_models | 29 | def refresh_models(self) |
| app/ui/widgets/model_combo.py | function | select_model | 107 | def select_model(self, model_filename: str \| None, adapter_name: str \| None) -> bool |
| app/ui/widgets/model_combo.py | function | _model_file_size_label | 136 | def _model_file_size_label(self, filename: str) -> str |
| app/ui/widgets/model_combo.py | function | _model_registry_detail | 143 | def _model_registry_detail(self, filename: str, meta: dict, size: str) -> str |
| app/ui/widgets/model_combo.py | function | _model_tooltip | 158 | def _model_tooltip(self, filename: str, meta: dict, size: str, adapter: str \| None) -> str |
| app/ui/widgets/section_shell.py | class | SectionShell | 3 | class SectionShell(QWidget) |
| app/ui/widgets/section_shell.py | function | __init__ | 8 | def __init__(self, title: str, content_widget: QWidget, desc_text: str = "", parent=None) |
| app/ui/widgets/shortcuts_overlay.py | function | _kbd | 24 | def _kbd(text: str, accent: str, border: str, bg_raised: str, text_hi: str) -> QLabel |
| app/ui/widgets/shortcuts_overlay.py | class | ShortcutsOverlay | 41 | class ShortcutsOverlay(QWidget) |
| app/ui/widgets/shortcuts_overlay.py | function | __init__ | 49 | def __init__(self, parent: QWidget) |
| app/ui/widgets/shortcuts_overlay.py | function | _build | 61 | def _build(self, parent: QWidget) |
| app/ui/widgets/shortcuts_overlay.py | function | _reposition | 155 | def _reposition(self) |
| app/ui/widgets/shortcuts_overlay.py | function | show_overlay | 167 | def show_overlay(self) |
| app/ui/widgets/shortcuts_overlay.py | function | toggle | 172 | def toggle(self) |
| app/ui/widgets/shortcuts_overlay.py | function | eventFilter | 180 | def eventFilter(self, obj, event) |
| app/ui/widgets/status_bar.py | function | _lbl | 7 | def _lbl(text: str, parent: QWidget) -> QLabel |
| app/ui/widgets/status_bar.py | function | _sep | 13 | def _sep(parent: QWidget) -> QLabel |
| app/ui/widgets/status_bar.py | class | StatusBar | 19 | class StatusBar(QWidget) |
| app/ui/widgets/status_bar.py | function | __init__ | 20 | def __init__(self, parent=None) |
| app/ui/widgets/status_bar.py | function | _toggle_thermal_visibility | 89 | def _toggle_thermal_visibility(self) |
| app/ui/widgets/status_bar.py | function | _tick | 94 | def _tick(self) |
| app/ui/widgets/status_bar.py | function | set_thermal_throttling | 126 | def set_thermal_throttling(self, active: bool) -> None |
| app/ui/widgets/status_bar.py | function | _set_thermal_warning | 130 | def _set_thermal_warning(self, active: bool) -> None |
| app/ui/widgets/status_bar.py | function | set_model | 143 | def set_model(self, name: str) |
| app/ui/widgets/status_bar.py | function | set_adapter | 149 | def set_adapter(self, name: str \| None) |
| app/ui/widgets/status_bar.py | function | set_speculative_active | 152 | def set_speculative_active(self, active: bool) |
| app/ui/widgets/status_bar.py | function | set_state | 158 | def set_state(self, text: str, active: bool = False) |
| app/ui/widgets/status_bar.py | function | set_context_stats | 165 | def set_context_stats(self, total: int, hist: int, rag: int, budget: int) |
| app/ui/widgets/status_bar.py | function | set_load_stats | 177 | def set_load_stats( self, latency_s: float \| None, bandwidth_gbs: float \| None, |
| app/ui/widgets/status_bar.py | function | set_bridge_status | 240 | def set_bridge_status(self, state: str, clients: int = 0, client_info: list[dict] \| None = None) |
| app/ui/widgets/symbolic_icon.py | class | BaseSymbol | 6 | class BaseSymbol(QWidget) |
| app/ui/widgets/symbolic_icon.py | function | __init__ | 8 | def __init__(self, state, color_role="accent", size=16, parent=None) |
| app/ui/widgets/symbolic_icon.py | function | set_color_role | 15 | def set_color_role(self, role: str) |
| app/ui/widgets/symbolic_icon.py | function | get_color | 19 | def get_color(self) -> QColor |
| app/ui/widgets/symbolic_icon.py | class | HamburgerIcon | 25 | class HamburgerIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 27 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | BrainIcon | 44 | class BrainIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 46 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | ThumbsUpIcon | 81 | class ThumbsUpIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 83 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | ThumbsDownIcon | 114 | class ThumbsDownIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 116 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | DocIcon | 144 | class DocIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 146 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | CheckIcon | 176 | class CheckIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 178 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | CrossIcon | 193 | class CrossIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 195 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | GearIcon | 210 | class GearIcon(BaseSymbol) |
| app/ui/widgets/symbolic_icon.py | function | paintEvent | 212 | def paintEvent(self, event) |
| app/ui/widgets/symbolic_icon.py | class | IconBtn | 242 | class IconBtn(QPushButton) |
| app/ui/widgets/symbolic_icon.py | function | __init__ | 245 | def __init__(self, icon_widget_class, state, color_role="accent", tooltip="", size=28, parent=None) |
| app/ui/widgets/symbolic_icon.py | function | update_style | 260 | def update_style(self) |
| app/ui/widgets/toast.py | class | ToastOverlay | 5 | class ToastOverlay(QWidget) |
| app/ui/widgets/toast.py | function | __init__ | 8 | def __init__(self, parent: QWidget, message: str, duration_ms: int = 3000) |
| app/ui/widgets/toast.py | function | show_toast | 45 | def show_toast(self) |
| app/ui/widgets/toast.py | function | _fade_out | 60 | def _fade_out(self) |
| app/ui/widgets/tracing_panel.py | class | TracingPanel | 6 | class TracingPanel(QFrame) |
| app/ui/widgets/tracing_panel.py | function | __init__ | 12 | def __init__(self, state, parent=None) |
| app/ui/widgets/tracing_panel.py | function | set_active | 27 | def set_active(self, active: bool) |
| app/ui/widgets/tracing_panel.py | function | set_accent_color | 32 | def set_accent_color(self, hex_color: str) |
| app/ui/widgets/tracing_panel.py | function | _update_timer_state | 36 | def _update_timer_state(self) |
| app/ui/widgets/tracing_panel.py | function | _on_tick | 47 | def _on_tick(self) |
| app/ui/widgets/tracing_panel.py | function | update_style | 70 | def update_style(self) |
| app/ui/widgets/tracing_panel.py | function | paintEvent | 74 | def paintEvent(self, event) |
| app/ui/workspaces/ai_lab.py | function | _hline | 28 | def _hline() -> QFrame |
| app/ui/workspaces/ai_lab.py | function | _section | 35 | def _section(text: str) -> QLabel |
| app/ui/workspaces/ai_lab.py | function | _label | 42 | def _label(text: str, obj: str = "") -> QLabel |
| app/ui/workspaces/ai_lab.py | function | _row | 49 | def _row(label_text: str, widget: QWidget) -> QWidget |
| app/ui/workspaces/ai_lab.py | class | ExecutionTraceFlowchart | 63 | class ExecutionTraceFlowchart(QWidget) |
| app/ui/workspaces/ai_lab.py | function | __init__ | 64 | def __init__(self, parent=None) |
| app/ui/workspaces/ai_lab.py | function | set_mode | 78 | def set_mode(self, is_sparse: bool) |
| app/ui/workspaces/ai_lab.py | function | paintEvent | 84 | def paintEvent(self, event) |
| app/ui/workspaces/ai_lab.py | class | AILabWorkspace | 152 | class AILabWorkspace(QWidget) |
| app/ui/workspaces/ai_lab.py | function | __init__ | 155 | def __init__(self, state: AppState, parent=None) |
| app/ui/workspaces/ai_lab.py | function | _build_pipeline_tab | 185 | def _build_pipeline_tab(self) |
| app/ui/workspaces/ai_lab.py | function | _build_vector_math_subtab | 281 | def _build_vector_math_subtab(self) |
| app/ui/workspaces/ai_lab.py | function | _build_rag_playground_subtab | 332 | def _build_rag_playground_subtab(self) |
| app/ui/workspaces/ai_lab.py | function | _build_projection_subtab | 361 | def _build_projection_subtab(self) |
| app/ui/workspaces/ai_lab.py | function | _build_execution_trace_subtab | 371 | def _build_execution_trace_subtab(self) |
| app/ui/workspaces/ai_lab.py | function | _build_composer_tab | 384 | def _build_composer_tab(self) |
| app/ui/workspaces/ai_lab.py | function | _on_state_changed | 461 | def _on_state_changed(self, name: str, value: object) |
| app/ui/workspaces/ai_lab.py | function | _on_vectorizer_changed | 467 | def _on_vectorizer_changed(self) |
| app/ui/workspaces/ai_lab.py | function | _run_pipeline | 473 | def _run_pipeline(self) |
| app/ui/workspaces/ai_lab.py | function | _populate_sparse_math_tables | 520 | def _populate_sparse_math_tables(self, sentences: list[str]) |
| app/ui/workspaces/ai_lab.py | function | _populate_dense_math_table | 555 | def _populate_dense_math_table(self) |
| app/ui/workspaces/ai_lab.py | function | _run_query | 570 | def _run_query(self) |
| app/ui/workspaces/ai_lab.py | function | _project_pca_docs_and_query | 682 | def _project_pca_docs_and_query(self, doc_embeddings: list[np.ndarray], query_embedding: np.ndarray) -> tuple[list[tuple[float, float]], tuple[float, float]] |
| app/ui/workspaces/ai_lab.py | function | showEvent | 707 | def showEvent(self, event) |
| app/ui/workspaces/ai_lab.py | function | _refresh_combos | 713 | def _refresh_combos(self) |
| app/ui/workspaces/ai_lab.py | function | _publish_agent | 741 | def _publish_agent(self) |
| app/ui/workspaces/docs.py | function | _section | 16 | def _section(text: str) -> QLabel |
| app/ui/workspaces/docs.py | function | _hline | 21 | def _hline() -> QFrame |
| app/ui/workspaces/docs.py | class | DocsWorkspace | 26 | class DocsWorkspace(QWidget) |
| app/ui/workspaces/docs.py | function | __init__ | 27 | def __init__(self, state, workbench_ref=None, parent=None) |
| app/ui/workspaces/docs.py | function | set_workbench | 35 | def set_workbench(self, wb) |
| app/ui/workspaces/docs.py | function | _init_library | 38 | def _init_library(self) |
| app/ui/workspaces/docs.py | function | _build_ui | 104 | def _build_ui(self) |
| app/ui/workspaces/docs.py | function | _filter_topics | 187 | def _filter_topics(self, text: str) |
| app/ui/workspaces/docs.py | function | _on_topic_selected | 249 | def _on_topic_selected(self, text: str) |
| app/ui/workspaces/docs.py | function | _generate_toc | 290 | def _generate_toc(self, content: str) |
| app/ui/workspaces/docs.py | function | _add_anchors | 300 | def _add_anchors(self, content: str) -> str |
| app/ui/workspaces/docs.py | function | replacer | 302 | def replacer(match) |
| app/ui/workspaces/docs.py | function | _jump_to_anchor | 312 | def _jump_to_anchor(self, text: str) |
| app/ui/workspaces/docs.py | function | _send_to_workbench | 317 | def _send_to_workbench(self) |
| app/ui/workspaces/docs_data.py | function | get_examples | 88 | def get_examples() |
| app/ui/workspaces/eval_suite.py | function | _section | 30 | def _section(text: str) -> QLabel |
| app/ui/workspaces/eval_suite.py | function | _hline | 36 | def _hline() -> QFrame |
| app/ui/workspaces/eval_suite.py | class | _EvalThread | 44 | class _EvalThread(QThread) |
| app/ui/workspaces/eval_suite.py | function | __init__ | 49 | def __init__(self, dataset_path: str, workflow_name: str, rag, model_name: str \| None = None, adapter_name: str \| None = None) |
| app/ui/workspaces/eval_suite.py | function | run | 57 | def run(self) |
| app/ui/workspaces/eval_suite.py | class | EvalSuiteWorkspace | 100 | class EvalSuiteWorkspace(QWidget) |
| app/ui/workspaces/eval_suite.py | function | __init__ | 103 | def __init__(self, state, parent=None) |
| app/ui/workspaces/eval_suite.py | function | _build_ui | 112 | def _build_ui(self) |
| app/ui/workspaces/eval_suite.py | function | _build_left | 127 | def _build_left(self) -> QWidget |
| app/ui/workspaces/eval_suite.py | function | _build_right | 393 | def _build_right(self) -> QWidget |
| app/ui/workspaces/eval_suite.py | function | _browse | 465 | def _browse(self) |
| app/ui/workspaces/eval_suite.py | function | _run | 480 | def _run(self) |
| app/ui/workspaces/eval_suite.py | function | _on_progress | 531 | def _on_progress(self, current: int, total: int) |
| app/ui/workspaces/eval_suite.py | function | _on_done | 557 | def _on_done(self, report) |
| app/ui/workspaces/eval_suite.py | function | _on_error | 603 | def _on_error(self, msg: str) |
| app/ui/workspaces/eval_suite.py | function | _on_result_selected | 608 | def _on_result_selected(self, item, _prev) |
| app/ui/workspaces/eval_suite.py | function | _is_adapter_compatible | 685 | def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool |
| app/ui/workspaces/eval_suite.py | function | _refresh_model_combo | 705 | def _refresh_model_combo(self) |
| app/ui/workspaces/eval_suite.py | function | showEvent | 763 | def showEvent(self, event) |
| app/ui/workspaces/eval_suite.py | function | _load_dataset_for_editing | 769 | def _load_dataset_for_editing(self, path: str) |
| app/ui/workspaces/eval_suite.py | function | _on_edit_case_selected | 801 | def _on_edit_case_selected(self, current, previous) |
| app/ui/workspaces/eval_suite.py | function | _save_fields_to_case | 812 | def _save_fields_to_case(self, index: int) |
| app/ui/workspaces/eval_suite.py | function | _load_case_to_fields | 857 | def _load_case_to_fields(self, index: int) |
| app/ui/workspaces/eval_suite.py | function | _add_case | 893 | def _add_case(self) |
| app/ui/workspaces/eval_suite.py | function | _delete_case | 911 | def _delete_case(self) |
| app/ui/workspaces/eval_suite.py | function | _save_dataset | 932 | def _save_dataset(self) |
| app/ui/workspaces/eval_suite.py | function | _clear_fields | 950 | def _clear_fields(self) |
| app/ui/workspaces/eval_suite.py | function | _block_form_signals | 960 | def _block_form_signals(self, block: bool) |
| app/ui/workspaces/eval_suite.py | function | _save_current_form_to_memory | 969 | def _save_current_form_to_memory(self) |
| app/ui/workspaces/eval_suite.py | function | _on_grader_changed | 975 | def _on_grader_changed(self, grader: str) |
| app/ui/workspaces/eval_suite.py | function | _update_grader_fields_visibility | 979 | def _update_grader_fields_visibility(self, grader: str) |
| app/ui/workspaces/eval_suite.py | function | _apply_results_filter | 994 | def _apply_results_filter(self) |
| app/ui/workspaces/eval_suite.py | function | _export_eval_report | 1003 | def _export_eval_report(self) |
| app/ui/workspaces/flywheel_studio.py | function | _section | 33 | def _section(text: str) -> QLabel |
| app/ui/workspaces/flywheel_studio.py | function | _label | 39 | def _label(text: str, obj: str = "") -> QLabel |
| app/ui/workspaces/flywheel_studio.py | class | CustomLineChart | 48 | class CustomLineChart(QWidget) |
| app/ui/workspaces/flywheel_studio.py | function | __init__ | 49 | def __init__(self, title: str, x_label: str, y_label: str, parent=None, accent_hex: str = "#00C2FF") |
| app/ui/workspaces/flywheel_studio.py | function | set_data | 61 | def set_data(self, points: list[tuple[float, float]], labels: list[str] = None) |
| app/ui/workspaces/flywheel_studio.py | function | set_metric | 67 | def set_metric(self, title: str, y_label: str) |
| app/ui/workspaces/flywheel_studio.py | function | mouseMoveEvent | 72 | def mouseMoveEvent(self, event) |
| app/ui/workspaces/flywheel_studio.py | function | leaveEvent | 128 | def leaveEvent(self, event) |
| app/ui/workspaces/flywheel_studio.py | function | paintEvent | 132 | def paintEvent(self, event) |
| app/ui/workspaces/flywheel_studio.py | class | _FlywheelDashboardLoader | 301 | class _FlywheelDashboardLoader(QThread) |
| app/ui/workspaces/flywheel_studio.py | function | run | 304 | def run(self) |
| app/ui/workspaces/flywheel_studio.py | class | FlywheelStudioWorkspace | 440 | class FlywheelStudioWorkspace(QWidget) |
| app/ui/workspaces/flywheel_studio.py | function | __init__ | 441 | def __init__(self, state, parent=None) |
| app/ui/workspaces/flywheel_studio.py | function | _build_ui | 456 | def _build_ui(self) |
| app/ui/workspaces/flywheel_studio.py | function | showEvent | 651 | def showEvent(self, event) |
| app/ui/workspaces/flywheel_studio.py | function | reload_dashboard | 655 | def reload_dashboard(self) |
| app/ui/workspaces/flywheel_studio.py | function | _on_dashboard_loaded | 663 | def _on_dashboard_loaded(self, stats: dict, failure_pairs: list[dict], training_history: list[dict], quant_data: dict) |
| app/ui/workspaces/flywheel_studio.py | function | _on_quant_metric_changed | 729 | def _on_quant_metric_changed(self) |
| app/ui/workspaces/flywheel_studio.py | function | _on_failure_selected | 757 | def _on_failure_selected(self, idx: int) |
| app/ui/workspaces/flywheel_studio.py | function | _build_leaderboard_tab | 770 | def _build_leaderboard_tab(self) -> QWidget |
| app/ui/workspaces/flywheel_studio.py | function | _refresh_leaderboard | 814 | def _refresh_leaderboard(self) |
| app/ui/workspaces/flywheel_studio.py | function | _export_dpo_from_evals | 837 | def _export_dpo_from_evals(self) |
| app/ui/workspaces/flywheel_studio.py | function | _open_leaderboard_item | 842 | def _open_leaderboard_item(self, item) |
| app/ui/workspaces/flywheel_studio.py | function | _export_sft | 854 | def _export_sft(self) |
| app/ui/workspaces/flywheel_studio.py | function | _export_dpo | 864 | def _export_dpo(self) |
| app/ui/workspaces/flywheel_studio.py | function | _build_log_inspector_tab | 876 | def _build_log_inspector_tab(self) -> QWidget |
| app/ui/workspaces/flywheel_studio.py | function | _auto_authorize_logs | 990 | def _auto_authorize_logs(self) -> None |
| app/ui/workspaces/flywheel_studio.py | function | _on_authorize_logs | 998 | def _on_authorize_logs(self) -> None |
| app/ui/workspaces/flywheel_studio.py | function | _do_authorize_with_token | 1007 | def _do_authorize_with_token(self, token_text: str, manual: bool = False) -> None |
| app/ui/workspaces/flywheel_studio.py | function | _on_lock_logs | 1050 | def _on_lock_logs(self) -> None |
| app/ui/workspaces/flywheel_studio.py | function | _populate_log_dashboard | 1060 | def _populate_log_dashboard(self, logs: list[dict]) -> None |
| app/ui/workspaces/knowledge_base.py | function | _hline | 28 | def _hline() -> QFrame |
| app/ui/workspaces/knowledge_base.py | function | _section | 34 | def _section(text: str) -> QLabel |
| app/ui/workspaces/knowledge_base.py | function | _label | 40 | def _label(text: str, obj: str = "") -> QLabel |
| app/ui/workspaces/knowledge_base.py | class | _IngestThread | 49 | class _IngestThread(QThread) |
| app/ui/workspaces/knowledge_base.py | function | __init__ | 54 | def __init__(self, rag, filepaths, chunk_size: int = 200, overlap: int = 50) |
| app/ui/workspaces/knowledge_base.py | function | run | 64 | def run(self) |
| app/ui/workspaces/knowledge_base.py | function | _progress | 66 | def _progress(current, total, event) |
| app/ui/workspaces/knowledge_base.py | class | VectorProjectionWidget | 90 | class VectorProjectionWidget(QFrame) |
| app/ui/workspaces/knowledge_base.py | function | __init__ | 93 | def __init__(self, parent=None) |
| app/ui/workspaces/knowledge_base.py | function | start_fade_in | 111 | def start_fade_in(self) |
| app/ui/workspaces/knowledge_base.py | function | _animate_step | 115 | def _animate_step(self) |
| app/ui/workspaces/knowledge_base.py | function | set_query | 122 | def set_query(self, x: float, y: float) |
| app/ui/workspaces/knowledge_base.py | function | set_documents | 126 | def set_documents(self, docs: list[dict]) |
| app/ui/workspaces/knowledge_base.py | function | set_axes | 130 | def set_axes(self, label_x: str, label_y: str) |
| app/ui/workspaces/knowledge_base.py | function | resizeEvent | 134 | def resizeEvent(self, event) |
| app/ui/workspaces/knowledge_base.py | function | mouseMoveEvent | 138 | def mouseMoveEvent(self, event: QMouseEvent) |
| app/ui/workspaces/knowledge_base.py | function | leaveEvent | 180 | def leaveEvent(self, event) |
| app/ui/workspaces/knowledge_base.py | function | paintEvent | 184 | def paintEvent(self, event) |
| app/ui/workspaces/knowledge_base.py | function | apply_alpha | 209 | def apply_alpha(color_val, default_alpha: int = 255) -> QColor |
| app/ui/workspaces/knowledge_base.py | class | KnowledgeBaseWorkspace | 442 | class KnowledgeBaseWorkspace(QWidget) |
| app/ui/workspaces/knowledge_base.py | function | __init__ | 445 | def __init__(self, state, parent=None) |
| app/ui/workspaces/knowledge_base.py | function | dragEnterEvent | 459 | def dragEnterEvent(self, event) |
| app/ui/workspaces/knowledge_base.py | function | dragMoveEvent | 466 | def dragMoveEvent(self, event) |
| app/ui/workspaces/knowledge_base.py | function | dropEvent | 473 | def dropEvent(self, event) |
| app/ui/workspaces/knowledge_base.py | function | _build_ui | 492 | def _build_ui(self) |
| app/ui/workspaces/knowledge_base.py | function | _build_explorer_tab | 540 | def _build_explorer_tab(self) -> QWidget |
| app/ui/workspaces/knowledge_base.py | function | _build_ingest_tab | 599 | def _build_ingest_tab(self) -> QWidget |
| app/ui/workspaces/knowledge_base.py | function | _build_search_tab | 681 | def _build_search_tab(self) -> QWidget |
| app/ui/workspaces/knowledge_base.py | function | _update_encoder_status | 766 | def _update_encoder_status(self) |
| app/ui/workspaces/knowledge_base.py | function | _preload_encoder | 772 | def _preload_encoder(self) |
| app/ui/workspaces/knowledge_base.py | function | _update_health_lbl | 783 | def _update_health_lbl(self) |
| app/ui/workspaces/knowledge_base.py | function | _refresh_sources | 792 | def _refresh_sources(self) |
| app/ui/workspaces/knowledge_base.py | function | _on_source_selected | 801 | def _on_source_selected(self, source: str) |
| app/ui/workspaces/knowledge_base.py | function | _ingest_file | 824 | def _ingest_file(self) |
| app/ui/workspaces/knowledge_base.py | function | _update_queue_ui | 836 | def _update_queue_ui(self) |
| app/ui/workspaces/knowledge_base.py | function | _process_next_in_queue | 844 | def _process_next_in_queue(self) |
| app/ui/workspaces/knowledge_base.py | function | _process_ingest_queue | 847 | def _process_ingest_queue(self) |
| app/ui/workspaces/knowledge_base.py | function | on_progress | 878 | def on_progress(current, total, filename, chunks, status) |
| app/ui/workspaces/knowledge_base.py | function | on_done | 891 | def on_done(filename, count) |
| app/ui/workspaces/knowledge_base.py | function | on_error | 901 | def on_error(msg) |
| app/ui/workspaces/knowledge_base.py | function | _remove_selected_source | 915 | def _remove_selected_source(self) |
| app/ui/workspaces/knowledge_base.py | function | _rebuild_index | 933 | def _rebuild_index(self) |
| app/ui/workspaces/knowledge_base.py | function | _send_query_to_workbench | 957 | def _send_query_to_workbench(self) |
| app/ui/workspaces/knowledge_base.py | function | _run_search | 968 | def _run_search(self) |
| app/ui/workspaces/knowledge_base.py | function | _handle_search_result_link | 1025 | def _handle_search_result_link(self, url) |
| app/ui/workspaces/knowledge_base.py | function | _clear_index | 1041 | def _clear_index(self) |
| app/ui/workspaces/knowledge_base.py | function | _load_rag_config | 1054 | def _load_rag_config(self) |
| app/ui/workspaces/knowledge_base.py | function | _save_rag_config | 1068 | def _save_rag_config(self) |
| app/ui/workspaces/knowledge_base.py | function | _on_threshold_changed | 1083 | def _on_threshold_changed(self, val) |
| app/ui/workspaces/knowledge_base.py | function | _on_topk_changed | 1087 | def _on_topk_changed(self, val) |
| app/ui/workspaces/knowledge_base.py | function | _on_mode_changed | 1091 | def _on_mode_changed(self, val) |
| app/ui/workspaces/knowledge_base.py | function | _build_sandbox_tab | 1097 | def _build_sandbox_tab(self) -> QWidget |
| app/ui/workspaces/knowledge_base.py | function | _reset_sandbox_docs | 1221 | def _reset_sandbox_docs(self) |
| app/ui/workspaces/knowledge_base.py | function | _add_sandbox_doc | 1233 | def _add_sandbox_doc(self) |
| app/ui/workspaces/knowledge_base.py | function | _remove_sandbox_doc | 1240 | def _remove_sandbox_doc(self) |
| app/ui/workspaces/knowledge_base.py | function | _recompute_sandbox | 1246 | def _recompute_sandbox(self) |
| app/ui/workspaces/knowledge_base.py | function | _run_sandbox_similarity | 1351 | def _run_sandbox_similarity(self) |
| app/ui/workspaces/prompt_lab.py | function | _section | 33 | def _section(text: str) -> QLabel |
| app/ui/workspaces/prompt_lab.py | function | _hline | 39 | def _hline() -> QFrame |
| app/ui/workspaces/prompt_lab.py | function | _scan_model_files | 45 | def _scan_model_files() -> list[str] |
| app/ui/workspaces/prompt_lab.py | function | generate_char_diff_html | 53 | def generate_char_diff_html(a: str, b: str) -> str |
| app/ui/workspaces/prompt_lab.py | function | flush | 66 | def flush() |
| app/ui/workspaces/prompt_lab.py | class | _RunThread | 108 | class _RunThread(QThread) |
| app/ui/workspaces/prompt_lab.py | function | __init__ | 114 | def __init__(self, system_prompt: str, user_prompt: str, hyperparams: dict, model_name: str \| None = None, adapter_name: str \| None = None, retrieved_chunks: list[str] \| None = None) |
| app/ui/workspaces/prompt_lab.py | function | run | 125 | def run(self) |
| app/ui/workspaces/prompt_lab.py | class | _PromptColumn | 222 | class _PromptColumn(QWidget) |
| app/ui/workspaces/prompt_lab.py | function | __init__ | 227 | def __init__(self, label: str, parent=None) |
| app/ui/workspaces/prompt_lab.py | function | _is_adapter_compatible | 297 | def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool |
| app/ui/workspaces/prompt_lab.py | function | _refresh_model_combo | 320 | def _refresh_model_combo(self) |
| app/ui/workspaces/prompt_lab.py | function | select_model_and_adapter | 380 | def select_model_and_adapter(self, model_name: str, adapter_name: str \| None) |
| app/ui/workspaces/prompt_lab.py | function | _emit_run | 389 | def _emit_run(self) |
| app/ui/workspaces/prompt_lab.py | function | system_text | 392 | def system_text(self) -> str |
| app/ui/workspaces/prompt_lab.py | function | user_text | 395 | def user_text(self) -> str |
| app/ui/workspaces/prompt_lab.py | function | set_system_text | 398 | def set_system_text(self, text: str) |
| app/ui/workspaces/prompt_lab.py | function | set_user_text | 401 | def set_user_text(self, text: str) |
| app/ui/workspaces/prompt_lab.py | function | clear_output | 404 | def clear_output(self) |
| app/ui/workspaces/prompt_lab.py | function | start_run | 408 | def start_run(self, hyperparams: dict) |
| app/ui/workspaces/prompt_lab.py | function | _on_token | 484 | def _on_token(self, token: str) |
| app/ui/workspaces/prompt_lab.py | function | _on_agentic_iteration | 497 | def _on_agentic_iteration(self, index: int, thought: str, response: str, diagnostics: dict) |
| app/ui/workspaces/prompt_lab.py | function | _on_agentic_loop_finished | 501 | def _on_agentic_loop_finished(self, total_iterations: int) |
| app/ui/workspaces/prompt_lab.py | function | _on_live_stats | 504 | def _on_live_stats(self, count: int, speed: float) |
| app/ui/workspaces/prompt_lab.py | function | _on_done | 507 | def _on_done(self, response: str, diagnostics: dict) |
| app/ui/workspaces/prompt_lab.py | function | _on_error | 515 | def _on_error(self, msg: str) |
| app/ui/workspaces/prompt_lab.py | class | _TelemetryCard | 523 | class _TelemetryCard(QFrame) |
| app/ui/workspaces/prompt_lab.py | function | __init__ | 526 | def __init__(self, label: str, parent=None) |
| app/ui/workspaces/prompt_lab.py | function | _muted_label | 551 | def _muted_label(text: str) -> QLabel |
| app/ui/workspaces/prompt_lab.py | function | reset | 557 | def reset(self) |
| app/ui/workspaces/prompt_lab.py | function | update_from | 564 | def update_from(self, telemetry: dict) |
| app/ui/workspaces/prompt_lab.py | class | _ModelCompareThread | 598 | class _ModelCompareThread(QThread) |
| app/ui/workspaces/prompt_lab.py | function | __init__ | 616 | def __init__(self, model_a_filename: str, model_b_filename: str, system_prompt: str, user_prompt: str, hyperparams: dict) |
| app/ui/workspaces/prompt_lab.py | function | _stream | 627 | def _stream(self, llm, prompt: str, token_signal: pyqtSignal) -> tuple[int, float, float, int] |
| app/ui/workspaces/prompt_lab.py | function | run | 678 | def run(self) |
| app/ui/workspaces/prompt_lab.py | class | PromptLabWorkspace | 762 | class PromptLabWorkspace(QWidget) |
| app/ui/workspaces/prompt_lab.py | function | __init__ | 765 | def __init__(self, state, parent=None) |
| app/ui/workspaces/prompt_lab.py | function | _build_ui | 777 | def _build_ui(self) |
| app/ui/workspaces/prompt_lab.py | function | _build_left_panel | 1041 | def _build_left_panel(self) -> QWidget |
| app/ui/workspaces/prompt_lab.py | function | _refresh_pairs | 1094 | def _refresh_pairs(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_pair_selected | 1103 | def _on_pair_selected(self, name: str) |
| app/ui/workspaces/prompt_lab.py | function | _save_pair | 1144 | def _save_pair(self) |
| app/ui/workspaces/prompt_lab.py | function | _delete_pair | 1194 | def _delete_pair(self) |
| app/ui/workspaces/prompt_lab.py | function | showEvent | 1217 | def showEvent(self, event) |
| app/ui/workspaces/prompt_lab.py | function | _run_column | 1223 | def _run_column(self, label: str, _user_text: str) |
| app/ui/workspaces/prompt_lab.py | function | _run_both | 1234 | def _run_both(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_col_a_done | 1241 | def _on_col_a_done(self, text: str, diagnostics: dict \| None = None) |
| app/ui/workspaces/prompt_lab.py | function | _on_col_b_done | 1247 | def _on_col_b_done(self, text: str, diagnostics: dict \| None = None) |
| app/ui/workspaces/prompt_lab.py | function | _on_col_a_failed | 1252 | def _on_col_a_failed(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_col_b_failed | 1256 | def _on_col_b_failed(self) |
| app/ui/workspaces/prompt_lab.py | function | _update_diff | 1260 | def _update_diff(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_tokenize_text_changed | 1275 | def _on_tokenize_text_changed(self) |
| app/ui/workspaces/prompt_lab.py | function | _format_token_html | 1311 | def _format_token_html(self, token_id: int, token_bytes: bytes) -> str |
| app/ui/workspaces/prompt_lab.py | function | _classify_token | 1339 | def _classify_token(self, token_id: int, token_bytes: bytes) -> str |
| app/ui/workspaces/prompt_lab.py | function | _load_output_a_to_tokenizer | 1354 | def _load_output_a_to_tokenizer(self) |
| app/ui/workspaces/prompt_lab.py | function | _load_output_b_to_tokenizer | 1360 | def _load_output_b_to_tokenizer(self) |
| app/ui/workspaces/prompt_lab.py | function | _filter_pairs | 1368 | def _filter_pairs(self, text) |
| app/ui/workspaces/prompt_lab.py | function | _clone_a_to_b | 1374 | def _clone_a_to_b(self) |
| app/ui/workspaces/prompt_lab.py | function | _clone_b_to_a | 1382 | def _clone_b_to_a(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_lock_sync_toggled | 1390 | def _on_lock_sync_toggled(self, checked) |
| app/ui/workspaces/prompt_lab.py | function | _sync_user_a_to_b | 1407 | def _sync_user_a_to_b(self) |
| app/ui/workspaces/prompt_lab.py | function | _sync_user_b_to_a | 1412 | def _sync_user_b_to_a(self) |
| app/ui/workspaces/prompt_lab.py | function | _sync_system_a_to_b | 1417 | def _sync_system_a_to_b(self) |
| app/ui/workspaces/prompt_lab.py | function | _sync_system_b_to_a | 1422 | def _sync_system_b_to_a(self) |
| app/ui/workspaces/prompt_lab.py | function | _refresh_compare_model_combos | 1429 | def _refresh_compare_model_combos(self) |
| app/ui/workspaces/prompt_lab.py | function | _run_comparative_lab | 1443 | def _run_comparative_lab(self) |
| app/ui/workspaces/prompt_lab.py | function | _cmp_append | 1483 | def _cmp_append(self, browser: QTextBrowser, token: str) |
| app/ui/workspaces/prompt_lab.py | function | _on_cmp_model_a_done | 1491 | def _on_cmp_model_a_done(self, telemetry: dict) |
| app/ui/workspaces/prompt_lab.py | function | _on_cmp_vram_flushing | 1494 | def _on_cmp_vram_flushing(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_cmp_model_b_done | 1499 | def _on_cmp_model_b_done(self, telemetry: dict) |
| app/ui/workspaces/prompt_lab.py | function | _on_cmp_finished | 1502 | def _on_cmp_finished(self) |
| app/ui/workspaces/prompt_lab.py | function | _on_cmp_error | 1506 | def _on_cmp_error(self, msg: str) |
| app/ui/workspaces/swarm_studio.py | class | SwarmStudioWorkspace | 41 | class SwarmStudioWorkspace(QWidget) |
| app/ui/workspaces/swarm_studio.py | function | __init__ | 44 | def __init__(self, state, parent=None) |
| app/ui/workspaces/swarm_studio.py | function | _build_ui | 63 | def _build_ui(self) |
| app/ui/workspaces/swarm_studio.py | function | _build_left_panel | 91 | def _build_left_panel(self) -> QWidget |
| app/ui/workspaces/swarm_studio.py | function | _build_center_panel | 154 | def _build_center_panel(self) -> QWidget |
| app/ui/workspaces/swarm_studio.py | function | _build_right_panel | 230 | def _build_right_panel(self) -> QWidget |
| app/ui/workspaces/swarm_studio.py | function | _load_history | 301 | def _load_history(self) |
| app/ui/workspaces/swarm_studio.py | function | _save_history_item | 311 | def _save_history_item(self, objective: str, workspace_path: str, test_command: str) |
| app/ui/workspaces/swarm_studio.py | function | _load_history_item | 325 | def _load_history_item(self, item: QListWidgetItem) |
| app/ui/workspaces/swarm_studio.py | function | _launch | 335 | def _launch(self) |
| app/ui/workspaces/swarm_studio.py | function | _reset_run_ui | 376 | def _reset_run_ui(self) |
| app/ui/workspaces/swarm_studio.py | function | _stop | 400 | def _stop(self) |
| app/ui/workspaces/swarm_studio.py | function | _tick | 405 | def _tick(self) |
| app/ui/workspaces/swarm_studio.py | function | _on_status | 410 | def _on_status(self, message: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_plan | 413 | def _on_plan(self, plan: dict) |
| app/ui/workspaces/swarm_studio.py | function | _on_layers | 419 | def _on_layers(self, layers: list) |
| app/ui/workspaces/swarm_studio.py | function | _on_layer_started | 435 | def _on_layer_started(self, index: int, total: int, tasks: list) |
| app/ui/workspaces/swarm_studio.py | function | _on_layer_finished | 440 | def _on_layer_finished(self, index: int, success: bool, summary: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_task_status | 444 | def _on_task_status(self, filepath: str, status: str, detail: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_verification_started | 455 | def _on_verification_started(self, layer_index: int, command: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_traceback | 459 | def _on_traceback(self, key: str, trace: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_file_edited | 463 | def _on_file_edited(self, filepath: str, content: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_test_result | 468 | def _on_test_result(self, passed: bool, trace: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_finished | 476 | def _on_finished(self, success: bool, summary: str) |
| app/ui/workspaces/swarm_studio.py | function | _on_coder_token | 490 | def _on_coder_token(self, filepath: str, token: str) |
| app/ui/workspaces/swarm_studio.py | function | _ensure_task_row | 499 | def _ensure_task_row(self, filepath: str, status: str, layer: str, detail: str) |
| app/ui/workspaces/swarm_studio.py | function | _render_dependency_graph | 517 | def _render_dependency_graph(self, layers: list[list[dict]]) -> None |
| app/ui/workspaces/swarm_studio.py | function | _update_graph_node_status | 598 | def _update_graph_node_status(self, filepath: str, status: str) -> None |
| app/ui/workspaces/swarm_studio.py | function | _layer_for_file | 619 | def _layer_for_file(self, filepath: str) -> str |
| app/ui/workspaces/swarm_studio.py | function | _sync_selection_preview | 628 | def _sync_selection_preview(self) |
| app/ui/workspaces/swarm_studio.py | function | _on_edits_proposed | 649 | def _on_edits_proposed(self, edits: list) |
| app/ui/workspaces/swarm_studio.py | function | _on_cherry_pick_item_clicked | 661 | def _on_cherry_pick_item_clicked(self, item: QListWidgetItem) |
| app/ui/workspaces/swarm_studio.py | function | _cherry_select_all | 666 | def _cherry_select_all(self) |
| app/ui/workspaces/swarm_studio.py | function | _cherry_select_none | 670 | def _cherry_select_none(self) |
| app/ui/workspaces/swarm_studio.py | function | _on_commit_edits | 674 | def _on_commit_edits(self) |
| app/ui/workspaces/swarm_studio.py | function | _on_verification_failed | 693 | def _on_verification_failed(self, context: str, traceback_text: str) |
| app/ui/workspaces/swarm_studio.py | function | _format_traceback_html | 696 | def _format_traceback_html(self, trace: str, context: str = "") -> str |
| app/ui/workspaces/swarm_studio.py | function | closeEvent | 724 | def closeEvent(self, event) |
| app/ui/workspaces/swarm_workspace.py | class | PhaseChip | 18 | class PhaseChip(QFrame) |
| app/ui/workspaces/swarm_workspace.py | function | __init__ | 19 | def __init__(self, name: str, label: str, parent=None) |
| app/ui/workspaces/swarm_workspace.py | function | _setup_ui | 28 | def _setup_ui(self) |
| app/ui/workspaces/swarm_workspace.py | function | update_style | 52 | def update_style(self, pulse_color=None) |
| app/ui/workspaces/swarm_workspace.py | class | CollapsiblePlanPanel | 92 | class CollapsiblePlanPanel(QWidget) |
| app/ui/workspaces/swarm_workspace.py | function | __init__ | 93 | def __init__(self, parent=None) |
| app/ui/workspaces/swarm_workspace.py | function | toggle | 111 | def toggle(self) |
| app/ui/workspaces/swarm_workspace.py | class | SwarmWorkspace | 117 | class SwarmWorkspace(QWidget) |
| app/ui/workspaces/swarm_workspace.py | function | __init__ | 118 | def __init__(self, state, parent=None) |
| app/ui/workspaces/swarm_workspace.py | function | _build_ui | 134 | def _build_ui(self) |
| app/ui/workspaces/swarm_workspace.py | function | _load_history | 327 | def _load_history(self) |
| app/ui/workspaces/swarm_workspace.py | function | _refresh_history_list | 331 | def _refresh_history_list(self) |
| app/ui/workspaces/swarm_workspace.py | function | _add_to_history | 342 | def _add_to_history(self, objective, workspace_path, test_command) |
| app/ui/workspaces/swarm_workspace.py | function | _on_history_clicked | 357 | def _on_history_clicked(self, item) |
| app/ui/workspaces/swarm_workspace.py | function | _on_tick | 368 | def _on_tick(self) |
| app/ui/workspaces/swarm_workspace.py | function | set_active_phase | 387 | def set_active_phase(self, phase_name: str) |
| app/ui/workspaces/swarm_workspace.py | function | _on_launch | 405 | def _on_launch(self) |
| app/ui/workspaces/swarm_workspace.py | function | _on_stop | 465 | def _on_stop(self) |
| app/ui/workspaces/swarm_workspace.py | function | _on_status_update | 472 | def _on_status_update(self, message: str) |
| app/ui/workspaces/swarm_workspace.py | function | _on_plan_created | 482 | def _on_plan_created(self, plan: dict) |
| app/ui/workspaces/swarm_workspace.py | function | _on_file_edited | 502 | def _on_file_edited(self, filepath: str, content: str) |
| app/ui/workspaces/swarm_workspace.py | function | _on_file_selected | 535 | def _on_file_selected(self, current, previous) |
| app/ui/workspaces/swarm_workspace.py | function | _on_test_result | 542 | def _on_test_result(self, passed: bool, trace: str) |
| app/ui/workspaces/swarm_workspace.py | function | _on_finished_swarm | 568 | def _on_finished_swarm(self, success: bool, summary: str) |
| app/ui/workspaces/swarm_workspace.py | function | closeEvent | 586 | def closeEvent(self, event) |
| app/ui/workspaces/system_config.py | class | QuantizationThread | 40 | class QuantizationThread(QThread) |
| app/ui/workspaces/system_config.py | function | __init__ | 46 | def __init__(self, input_path: str, output_path: str, quant_format: str) |
| app/ui/workspaces/system_config.py | function | run | 52 | def run(self) |
| app/ui/workspaces/system_config.py | class | QuantizationDialog | 69 | class QuantizationDialog(QDialog) |
| app/ui/workspaces/system_config.py | function | __init__ | 70 | def __init__(self, model_name: str, parent=None) |
| app/ui/workspaces/system_config.py | function | selected_format | 102 | def selected_format(self) -> str |
| app/ui/workspaces/system_config.py | function | _section | 106 | def _section(text: str) -> QLabel |
| app/ui/workspaces/system_config.py | function | _hline | 112 | def _hline() -> QFrame |
| app/ui/workspaces/system_config.py | function | _row | 118 | def _row(label_text: str, widget: QWidget) -> QWidget |
| app/ui/workspaces/system_config.py | class | DownloadThread | 134 | class DownloadThread(QThread) |
| app/ui/workspaces/system_config.py | function | __init__ | 141 | def __init__(self, url: str, target_path: str) |
| app/ui/workspaces/system_config.py | function | cancel | 147 | def cancel(self) |
| app/ui/workspaces/system_config.py | function | run | 150 | def run(self) |
| app/ui/workspaces/system_config.py | class | SystemConfigWorkspace | 215 | class SystemConfigWorkspace(QWidget) |
| app/ui/workspaces/system_config.py | function | __init__ | 219 | def __init__(self, state, workbench_ref=None, parent=None) |
| app/ui/workspaces/system_config.py | function | set_workbench | 240 | def set_workbench(self, wb) |
| app/ui/workspaces/system_config.py | function | showEvent | 243 | def showEvent(self, event) |
| app/ui/workspaces/system_config.py | function | _build_ui | 264 | def _build_ui(self) |
| app/ui/workspaces/system_config.py | function | show_theme_tab | 295 | def show_theme_tab(self) |
| app/ui/workspaces/system_config.py | function | _build_model_tab | 302 | def _build_model_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _browse_quant_source | 535 | def _browse_quant_source(self) |
| app/ui/workspaces/system_config.py | function | _start_quantize | 547 | def _start_quantize(self) |
| app/ui/workspaces/system_config.py | function | _cancel_quantize | 593 | def _cancel_quantize(self) |
| app/ui/workspaces/system_config.py | function | _on_quant_progress | 604 | def _on_quant_progress(self, pct: int) |
| app/ui/workspaces/system_config.py | function | _on_quant_done | 608 | def _on_quant_done(self, out_path: str) |
| app/ui/workspaces/system_config.py | function | _on_quant_error | 624 | def _on_quant_error(self, msg: str) |
| app/ui/workspaces/system_config.py | function | _build_registry_tab | 637 | def _build_registry_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _load_registry | 683 | def _load_registry(self) |
| app/ui/workspaces/system_config.py | function | _get_active_model_name | 741 | def _get_active_model_name(self) -> str |
| app/ui/workspaces/system_config.py | function | _populate_registry | 750 | def _populate_registry(self) |
| app/ui/workspaces/system_config.py | function | _on_quantize_clicked | 831 | def _on_quantize_clicked(self, filename: str, model_name: str) |
| app/ui/workspaces/system_config.py | function | _on_quant_done | 861 | def _on_quant_done(self, output_path: str) |
| app/ui/workspaces/system_config.py | function | _activate_registry_model | 875 | def _activate_registry_model(self, filename: str) |
| app/ui/workspaces/system_config.py | function | _start_download | 900 | def _start_download(self, url: str, filename: str) |
| app/ui/workspaces/system_config.py | function | _cancel_download | 925 | def _cancel_download(self) |
| app/ui/workspaces/system_config.py | function | _set_ui_enabled_for_download | 934 | def _set_ui_enabled_for_download(self, enabled: bool) |
| app/ui/workspaces/system_config.py | function | _on_download_progress | 943 | def _on_download_progress(self, percent: int) |
| app/ui/workspaces/system_config.py | function | _on_download_speed | 946 | def _on_download_speed(self, speed_str: str) |
| app/ui/workspaces/system_config.py | function | _on_download_log | 950 | def _on_download_log(self, text: str) |
| app/ui/workspaces/system_config.py | function | _on_download_error | 953 | def _on_download_error(self, err_msg: str) |
| app/ui/workspaces/system_config.py | function | _on_download_done | 959 | def _on_download_done(self, filename: str) |
| app/ui/workspaces/system_config.py | function | _build_params_tab | 967 | def _build_params_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _on_reduced_motion_changed | 1099 | def _on_reduced_motion_changed(self, state) |
| app/ui/workspaces/system_config.py | function | _on_theme_mode_changed | 1109 | def _on_theme_mode_changed(self, text: str) |
| app/ui/workspaces/system_config.py | function | _on_log_rotation_changed | 1116 | def _on_log_rotation_changed(self, val) |
| app/ui/workspaces/system_config.py | function | _on_log_retention_changed | 1120 | def _on_log_retention_changed(self, val) |
| app/ui/workspaces/system_config.py | function | _on_single_session_auth_changed | 1124 | def _on_single_session_auth_changed(self, state) |
| app/ui/workspaces/system_config.py | function | _on_thermal_protection_enabled_changed | 1129 | def _on_thermal_protection_enabled_changed(self, state) |
| app/ui/workspaces/system_config.py | function | _on_thermal_threshold_changed | 1134 | def _on_thermal_threshold_changed(self, val: int) |
| app/ui/workspaces/system_config.py | function | _build_identity_tab | 1140 | def _build_identity_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _build_vision_tab | 1184 | def _build_vision_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _refresh_vision_status | 1258 | def _refresh_vision_status(self) |
| app/ui/workspaces/system_config.py | function | _set_active_vision_model_from_combo | 1316 | def _set_active_vision_model_from_combo(self) |
| app/ui/workspaces/system_config.py | function | _load_active_vision_model | 1325 | def _load_active_vision_model(self) |
| app/ui/workspaces/system_config.py | function | _reset_vision_runtime | 1330 | def _reset_vision_runtime(self) |
| app/ui/workspaces/system_config.py | function | _build_hardware_tab | 1336 | def _build_hardware_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _update_live_hardware | 1465 | def _update_live_hardware(self) |
| app/ui/workspaces/system_config.py | function | _refresh_hardware | 1490 | def _refresh_hardware(self) |
| app/ui/workspaces/system_config.py | function | _browse_model | 1521 | def _browse_model(self) |
| app/ui/workspaces/system_config.py | function | _load_model | 1528 | def _load_model(self) |
| app/ui/workspaces/system_config.py | function | _browse_draft_model | 1551 | def _browse_draft_model(self) |
| app/ui/workspaces/system_config.py | function | _load_speculative | 1558 | def _load_speculative(self) |
| app/ui/workspaces/system_config.py | function | _clear_draft_model | 1597 | def _clear_draft_model(self) |
| app/ui/workspaces/system_config.py | function | _scan_models | 1606 | def _scan_models(self, force=False) |
| app/ui/workspaces/system_config.py | function | _apply_identity | 1661 | def _apply_identity(self) |
| app/ui/workspaces/system_config.py | function | _scan_adapters | 1667 | def _scan_adapters(self, force=False) |
| app/ui/workspaces/system_config.py | function | _load_adapter | 1694 | def _load_adapter(self) |
| app/ui/workspaces/system_config.py | function | refresh_filesystem_cache | 1721 | def refresh_filesystem_cache(self) |
| app/ui/workspaces/system_config.py | function | _on_settings_search_changed | 1728 | def _on_settings_search_changed(self, text: str) |
| app/ui/workspaces/system_config.py | function | _run_model_preflight_checks | 1736 | def _run_model_preflight_checks(self) |
| app/ui/workspaces/system_config.py | function | _apply_defaults | 1872 | def _apply_defaults(self) |
| app/ui/workspaces/system_config.py | function | _build_theme_tab | 1894 | def _build_theme_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _add_preview_elements | 2095 | def _add_preview_elements(self, card_layout: QVBoxLayout) |
| app/ui/workspaces/system_config.py | function | _load_active_appearance_config | 2188 | def _load_active_appearance_config(self) |
| app/ui/workspaces/system_config.py | function | _sync_appearance_controls_from_state | 2242 | def _sync_appearance_controls_from_state(self) |
| app/ui/workspaces/system_config.py | function | _update_accent_button_text | 2293 | def _update_accent_button_text(self) |
| app/ui/workspaces/system_config.py | function | _on_preset_changed | 2307 | def _on_preset_changed(self) |
| app/ui/workspaces/system_config.py | function | _pick_custom_accent | 2315 | def _pick_custom_accent(self) |
| app/ui/workspaces/system_config.py | function | _reset_custom_accent | 2327 | def _reset_custom_accent(self) |
| app/ui/workspaces/system_config.py | function | _on_control_changed | 2332 | def _on_control_changed(self) |
| app/ui/workspaces/system_config.py | function | _apply_active_theme | 2355 | def _apply_active_theme(self) |
| app/ui/workspaces/system_config.py | function | _update_swatches | 2383 | def _update_swatches(self) |
| app/ui/workspaces/system_config.py | function | _update_theme_gallery | 2425 | def _update_theme_gallery(self) |
| app/ui/workspaces/system_config.py | function | _apply_theme_preset_from_gallery | 2501 | def _apply_theme_preset_from_gallery(self, name: str) |
| app/ui/workspaces/system_config.py | function | _save_appearance_config_silent | 2506 | def _save_appearance_config_silent(self) |
| app/ui/workspaces/system_config.py | function | _save_appearance_config | 2524 | def _save_appearance_config(self) |
| app/ui/workspaces/system_config.py | function | _build_mcp_tab | 2540 | def _build_mcp_tab(self) -> QWidget |
| app/ui/workspaces/system_config.py | function | _refresh_mcp_display | 2588 | def _refresh_mcp_display(self) |
| app/ui/workspaces/system_config.py | function | _add_mcp_server | 2606 | def _add_mcp_server(self) |
| app/ui/workspaces/system_config.py | function | _remove_mcp_server | 2619 | def _remove_mcp_server(self) |
| app/ui/workspaces/system_config.py | function | _restart_mcp_client | 2626 | def _restart_mcp_client(self) |
| app/ui/workspaces/system_config/appearance_panel.py | class | AppearancePanelMixin | 19 | class AppearancePanelMixin |
| app/ui/workspaces/system_config/appearance_panel.py | function | _build_theme_tab | 20 | def _build_theme_tab(self) -> QWidget |
| app/ui/workspaces/system_config/appearance_panel.py | function | _add_preview_elements | 222 | def _add_preview_elements(self, card_layout: QVBoxLayout) |
| app/ui/workspaces/system_config/appearance_panel.py | function | _load_active_appearance_config | 316 | def _load_active_appearance_config(self) |
| app/ui/workspaces/system_config/appearance_panel.py | function | _sync_appearance_controls_from_state | 370 | def _sync_appearance_controls_from_state(self) |
| app/ui/workspaces/system_config/appearance_panel.py | function | _update_accent_button_text | 422 | def _update_accent_button_text(self) |
| app/ui/workspaces/system_config/appearance_panel.py | function | _on_preset_changed | 437 | def _on_preset_changed(self) |
| app/ui/workspaces/system_config/appearance_panel.py | function | _pick_custom_accent | 446 | def _pick_custom_accent(self) |
| app/ui/workspaces/system_config/appearance_panel.py | function | _reset_custom_accent | 459 | def _reset_custom_accent(self) |
| app/ui/workspaces/system_config/appearance_runtime.py | class | AppearanceRuntimeMixin | 16 | class AppearanceRuntimeMixin |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _on_control_changed | 17 | def _on_control_changed(self) |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _apply_active_theme | 42 | def _apply_active_theme(self) |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _update_swatches | 72 | def _update_swatches(self) |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _update_theme_gallery | 116 | def _update_theme_gallery(self) |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _apply_theme_preset_from_gallery | 194 | def _apply_theme_preset_from_gallery(self, name: str) |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _save_appearance_config_silent | 201 | def _save_appearance_config_silent(self) |
| app/ui/workspaces/system_config/appearance_runtime.py | function | _save_appearance_config | 226 | def _save_appearance_config(self) |
| app/ui/workspaces/system_config/common.py | function | _section | 4 | def _section(text: str) -> QLabel |
| app/ui/workspaces/system_config/common.py | function | _hline | 10 | def _hline() -> QFrame |
| app/ui/workspaces/system_config/common.py | function | _row | 16 | def _row(label_text: str, widget: QWidget) -> QWidget |
| app/ui/workspaces/system_config/defaults_panel.py | class | DefaultsPanelMixin | 15 | class DefaultsPanelMixin |
| app/ui/workspaces/system_config/defaults_panel.py | function | _build_params_tab | 16 | def _build_params_tab(self) -> QWidget |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_reduced_motion_changed | 149 | def _on_reduced_motion_changed(self, state) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_theme_mode_changed | 160 | def _on_theme_mode_changed(self, text: str) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_log_rotation_changed | 168 | def _on_log_rotation_changed(self, val) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_log_retention_changed | 173 | def _on_log_retention_changed(self, val) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_single_session_auth_changed | 178 | def _on_single_session_auth_changed(self, state) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_thermal_protection_enabled_changed | 184 | def _on_thermal_protection_enabled_changed(self, state) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_thermal_threshold_changed | 190 | def _on_thermal_threshold_changed(self, val: int) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _build_identity_tab | 197 | def _build_identity_tab(self) -> QWidget |
| app/ui/workspaces/system_config/defaults_panel.py | function | _apply_identity | 242 | def _apply_identity(self) |
| app/ui/workspaces/system_config/defaults_panel.py | function | _on_settings_search_changed | 249 | def _on_settings_search_changed(self, text: str) |
| app/ui/workspaces/system_config/download_threads.py | class | QuantizationThread | 13 | class QuantizationThread(QThread) |
| app/ui/workspaces/system_config/download_threads.py | function | __init__ | 19 | def __init__(self, input_path: str, output_path: str, quant_format: str) |
| app/ui/workspaces/system_config/download_threads.py | function | run | 25 | def run(self) |
| app/ui/workspaces/system_config/download_threads.py | class | QuantizationDialog | 42 | class QuantizationDialog(QDialog) |
| app/ui/workspaces/system_config/download_threads.py | function | __init__ | 43 | def __init__(self, model_name: str, parent=None) |
| app/ui/workspaces/system_config/download_threads.py | function | selected_format | 75 | def selected_format(self) -> str |
| app/ui/workspaces/system_config/download_threads.py | class | DownloadThread | 80 | class DownloadThread(QThread) |
| app/ui/workspaces/system_config/download_threads.py | function | __init__ | 87 | def __init__(self, url: str, target_path: str) |
| app/ui/workspaces/system_config/download_threads.py | function | cancel | 93 | def cancel(self) |
| app/ui/workspaces/system_config/download_threads.py | function | request_stop | 96 | def request_stop(self) |
| app/ui/workspaces/system_config/download_threads.py | function | run | 99 | def run(self) |
| app/ui/workspaces/system_config/mcp_panel.py | class | McpPanelMixin | 15 | class McpPanelMixin |
| app/ui/workspaces/system_config/mcp_panel.py | function | _build_mcp_tab | 16 | def _build_mcp_tab(self) -> QWidget |
| app/ui/workspaces/system_config/mcp_panel.py | function | _refresh_mcp_display | 80 | def _refresh_mcp_display(self) |
| app/ui/workspaces/system_config/mcp_panel.py | function | _add_mcp_server | 98 | def _add_mcp_server(self) |
| app/ui/workspaces/system_config/mcp_panel.py | function | _remove_mcp_server | 112 | def _remove_mcp_server(self) |
| app/ui/workspaces/system_config/mcp_panel.py | function | _restart_mcp_client | 120 | def _restart_mcp_client(self) |
| app/ui/workspaces/system_config/model_panel.py | class | ModelPanelMixin | 21 | class ModelPanelMixin |
| app/ui/workspaces/system_config/model_panel.py | function | _build_model_tab | 22 | def _build_model_tab(self) -> QWidget |
| app/ui/workspaces/system_config/model_panel.py | function | _browse_model | 265 | def _browse_model(self) |
| app/ui/workspaces/system_config/model_panel.py | function | _load_model | 273 | def _load_model(self) |
| app/ui/workspaces/system_config/model_panel.py | function | _browse_draft_model | 303 | def _browse_draft_model(self) |
| app/ui/workspaces/system_config/model_panel.py | function | _on_draft_combo_changed | 315 | def _on_draft_combo_changed(self, text: str) |
| app/ui/workspaces/system_config/model_panel.py | function | _load_speculative | 322 | def _load_speculative(self) |
| app/ui/workspaces/system_config/model_panel.py | function | _clear_draft_model | 366 | def _clear_draft_model(self) |
| app/ui/workspaces/system_config/model_panel.py | function | _populate_draft_selector | 382 | def _populate_draft_selector(self) |
| app/ui/workspaces/system_config/model_panel.py | function | _scan_models | 418 | def _scan_models(self, force=False) |
| app/ui/workspaces/system_config/model_panel.py | function | _scan_adapters | 476 | def _scan_adapters(self, force=False) |
| app/ui/workspaces/system_config/model_panel.py | function | _load_adapter | 504 | def _load_adapter(self) |
| app/ui/workspaces/system_config/model_panel.py | function | refresh_filesystem_cache | 538 | def refresh_filesystem_cache(self) |
| app/ui/workspaces/system_config/model_preflight.py | class | ModelPreflightMixin | 11 | class ModelPreflightMixin |
| app/ui/workspaces/system_config/model_preflight.py | function | _run_model_preflight_checks | 12 | def _run_model_preflight_checks(self) |
| app/ui/workspaces/system_config/observability_tab.py | class | ObservabilityTab | 16 | class ObservabilityTab(QWidget) |
| app/ui/workspaces/system_config/observability_tab.py | function | __init__ | 17 | def __init__(self, state, parent=None) |
| app/ui/workspaces/system_config/observability_tab.py | function | _build_ui | 22 | def _build_ui(self) |
| app/ui/workspaces/system_config/observability_tab.py | function | _create_pill | 88 | def _create_pill(self, label: str, val: str) -> QFrame |
| app/ui/workspaces/system_config/observability_tab.py | function | refresh_metrics | 116 | def refresh_metrics(self) |
| app/ui/workspaces/system_config/observability_tab.py | function | _apply_policy_and_clean | 175 | def _apply_policy_and_clean(self) |
| app/ui/workspaces/system_config/quantization_panel.py | class | QuantizationPanelMixin | 16 | class QuantizationPanelMixin |
| app/ui/workspaces/system_config/quantization_panel.py | function | _browse_quant_source | 17 | def _browse_quant_source(self) |
| app/ui/workspaces/system_config/quantization_panel.py | function | _start_quantize | 31 | def _start_quantize(self) |
| app/ui/workspaces/system_config/quantization_panel.py | function | _cancel_quantize | 79 | def _cancel_quantize(self) |
| app/ui/workspaces/system_config/quantization_panel.py | function | _on_quant_progress | 92 | def _on_quant_progress(self, pct: int) |
| app/ui/workspaces/system_config/quantization_panel.py | function | _on_quant_error | 98 | def _on_quant_error(self, msg: str) |
| app/ui/workspaces/system_config/registry_panel.py | class | RegistryPanelMixin | 17 | class RegistryPanelMixin |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_quant_done | 18 | def _on_quant_done(self, out_path: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _build_registry_tab | 35 | def _build_registry_tab(self) -> QWidget |
| app/ui/workspaces/system_config/registry_panel.py | function | _load_registry | 82 | def _load_registry(self) |
| app/ui/workspaces/system_config/registry_panel.py | function | _get_active_model_name | 140 | def _get_active_model_name(self) -> str |
| app/ui/workspaces/system_config/registry_panel.py | function | _populate_registry | 150 | def _populate_registry(self) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_quantize_clicked | 232 | def _on_quantize_clicked(self, filename: str, model_name: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_quant_done | 263 | def _on_quant_done(self, output_path: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _activate_registry_model | 278 | def _activate_registry_model(self, filename: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _start_download | 312 | def _start_download(self, url: str, filename: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _cancel_download | 338 | def _cancel_download(self) |
| app/ui/workspaces/system_config/registry_panel.py | function | _set_ui_enabled_for_download | 348 | def _set_ui_enabled_for_download(self, enabled: bool) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_download_progress | 358 | def _on_download_progress(self, percent: int) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_download_speed | 362 | def _on_download_speed(self, speed_str: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_download_log | 367 | def _on_download_log(self, text: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_download_error | 371 | def _on_download_error(self, err_msg: str) |
| app/ui/workspaces/system_config/registry_panel.py | function | _on_download_done | 378 | def _on_download_done(self, filename: str) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | class | VisionHardwarePanelMixin | 22 | class VisionHardwarePanelMixin |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _build_vision_tab | 23 | def _build_vision_tab(self) -> QWidget |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _refresh_vision_status | 98 | def _refresh_vision_status(self) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _set_active_vision_model_from_combo | 157 | def _set_active_vision_model_from_combo(self) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _load_active_vision_model | 167 | def _load_active_vision_model(self) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _reset_vision_runtime | 173 | def _reset_vision_runtime(self) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _build_hardware_tab | 180 | def _build_hardware_tab(self) -> QWidget |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _update_live_hardware | 369 | def _update_live_hardware(self) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _refresh_hardware | 395 | def _refresh_hardware(self) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _on_engine_config_changed | 427 | def _on_engine_config_changed(self, *_args) |
| app/ui/workspaces/system_config/vision_hardware_panel.py | function | _sync_engine_controls_enabled | 443 | def _sync_engine_controls_enabled(self) |
| app/ui/workspaces/system_config/workspace.py | class | SystemConfigWorkspace | 29 | class SystemConfigWorkspace( RegistryPanelMixin, QuantizationPanelMixin, ModelPanelMixin, |
| app/ui/workspaces/system_config/workspace.py | function | __init__ | 46 | def __init__(self, state, workbench_ref=None, parent=None) |
| app/ui/workspaces/system_config/workspace.py | function | set_workbench | 68 | def set_workbench(self, wb) |
| app/ui/workspaces/system_config/workspace.py | function | showEvent | 71 | def showEvent(self, event) |
| app/ui/workspaces/system_config/workspace.py | function | _build_ui | 98 | def _build_ui(self) |
| app/ui/workspaces/system_config/workspace.py | function | show_theme_tab | 136 | def show_theme_tab(self) |
| app/ui/workspaces/system_config/workspace.py | function | _apply_defaults | 143 | def _apply_defaults(self) |
| app/ui/workspaces/training_studio.py | function | _section | 33 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio.py | function | _hline | 39 | def _hline() -> QFrame |
| app/ui/workspaces/training_studio.py | class | TrainingThread | 47 | class TrainingThread(QThread) |
| app/ui/workspaces/training_studio.py | function | __init__ | 54 | def __init__(self, hf_base_dir: str, adapter_name: str, config: dict) |
| app/ui/workspaces/training_studio.py | function | run | 60 | def run(self) |
| app/ui/workspaces/training_studio.py | class | TrainerProgressCallback | 152 | class TrainerProgressCallback(TrainerCallback) |
| app/ui/workspaces/training_studio.py | function | on_log | 153 | def on_log(self, args, state, control, logs=None, **kwargs) |
| app/ui/workspaces/training_studio.py | function | on_step_end | 160 | def on_step_end(self, args, state, control, **kwargs) |
| app/ui/workspaces/training_studio.py | class | AutoTrainThread | 227 | class AutoTrainThread(QThread) |
| app/ui/workspaces/training_studio.py | function | __init__ | 232 | def __init__(self, topic: str, adapter_name: str, config: dict) |
| app/ui/workspaces/training_studio.py | function | run | 239 | def run(self) |
| app/ui/workspaces/training_studio.py | class | _FlywheelStatsThread | 290 | class _FlywheelStatsThread(QThread) |
| app/ui/workspaces/training_studio.py | function | run | 294 | def run(self) |
| app/ui/workspaces/training_studio.py | class | LossChartWidget | 402 | class LossChartWidget(QFrame) |
| app/ui/workspaces/training_studio.py | function | __init__ | 403 | def __init__(self, parent=None) |
| app/ui/workspaces/training_studio.py | function | set_loss_history | 416 | def set_loss_history(self, history: list[float]) |
| app/ui/workspaces/training_studio.py | function | paintEvent | 420 | def paintEvent(self, event) |
| app/ui/workspaces/training_studio.py | class | TrainingStudioWorkspace | 537 | class TrainingStudioWorkspace(QWidget) |
| app/ui/workspaces/training_studio.py | function | __init__ | 538 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio.py | function | _build_ui | 545 | def _build_ui(self) |
| app/ui/workspaces/training_studio.py | function | _build_flywheel_tab | 586 | def _build_flywheel_tab(self) -> QWidget |
| app/ui/workspaces/training_studio.py | function | _flywheel_card | 694 | def _flywheel_card(self, title: str, field_ids: list) -> QWidget |
| app/ui/workspaces/training_studio.py | function | _on_tab_changed | 725 | def _on_tab_changed(self, idx: int) |
| app/ui/workspaces/training_studio.py | function | _load_flywheel_stats | 729 | def _load_flywheel_stats(self) |
| app/ui/workspaces/training_studio.py | function | _apply_flywheel_stats | 740 | def _apply_flywheel_stats(self, stats: dict) |
| app/ui/workspaces/training_studio.py | function | _flywheel_export_sft | 752 | def _flywheel_export_sft(self) |
| app/ui/workspaces/training_studio.py | function | _flywheel_export_dpo | 756 | def _flywheel_export_dpo(self) |
| app/ui/workspaces/training_studio.py | function | _open_training_folder | 760 | def _open_training_folder(self) |
| app/ui/workspaces/training_studio.py | function | _flywheel_goto_eval | 769 | def _flywheel_goto_eval(self) |
| app/ui/workspaces/training_studio.py | function | _build_dataset_tab | 779 | def _build_dataset_tab(self) -> QWidget |
| app/ui/workspaces/training_studio.py | function | _build_export_tab | 821 | def _build_export_tab(self) -> QWidget |
| app/ui/workspaces/training_studio.py | function | _build_train_tab | 884 | def _build_train_tab(self) -> QWidget |
| app/ui/workspaces/training_studio.py | function | showEvent | 1066 | def showEvent(self, event) |
| app/ui/workspaces/training_studio.py | function | _refresh | 1070 | def _refresh(self) |
| app/ui/workspaces/training_studio.py | function | _load_custom_models | 1101 | def _load_custom_models(self) -> list[dict] |
| app/ui/workspaces/training_studio.py | function | _save_custom_model | 1111 | def _save_custom_model(self, display_name: str, item_data: str, is_path: bool) |
| app/ui/workspaces/training_studio.py | function | _browse_hf_model | 1128 | def _browse_hf_model(self) |
| app/ui/workspaces/training_studio.py | function | _add_hf_repo | 1158 | def _add_hf_repo(self) |
| app/ui/workspaces/training_studio.py | function | _refresh_base_models | 1177 | def _refresh_base_models(self) |
| app/ui/workspaces/training_studio.py | function | _on_example_selected | 1274 | def _on_example_selected(self, row: int) |
| app/ui/workspaces/training_studio.py | function | _delete_selected | 1309 | def _delete_selected(self) |
| app/ui/workspaces/training_studio.py | function | _export | 1321 | def _export(self, mode: str) |
| app/ui/workspaces/training_studio.py | function | _get_hf_model_path | 1359 | def _get_hf_model_path(self) -> tuple[str \| None, str] |
| app/ui/workspaces/training_studio.py | function | _check_deps | 1408 | def _check_deps(self) |
| app/ui/workspaces/training_studio.py | function | _begin_training | 1453 | def _begin_training(self) |
| app/ui/workspaces/training_studio.py | function | _on_train_log | 1552 | def _on_train_log(self, text: str) |
| app/ui/workspaces/training_studio.py | function | _on_train_loss | 1555 | def _on_train_loss(self, step: int, value: float, epoch: float) |
| app/ui/workspaces/training_studio.py | function | _on_train_progress | 1558 | def _on_train_progress(self, current: int, total: int, epoch: float) |
| app/ui/workspaces/training_studio.py | function | _on_train_done | 1563 | def _on_train_done(self, adapter_path: str) |
| app/ui/workspaces/training_studio.py | function | _on_train_error | 1573 | def _on_train_error(self, msg: str) |
| app/ui/workspaces/training_studio.py | function | _update_export_path_preview | 1580 | def _update_export_path_preview(self, name) |
| app/ui/workspaces/training_studio.py | function | _build_auto_train_tab | 1588 | def _build_auto_train_tab(self) -> QWidget |
| app/ui/workspaces/training_studio.py | function | _begin_auto_training | 1722 | def _begin_auto_training(self) |
| app/ui/workspaces/training_studio.py | function | _on_auto_log | 1766 | def _on_auto_log(self, text: str) |
| app/ui/workspaces/training_studio.py | function | _on_auto_done | 1769 | def _on_auto_done(self, adapter_name: str) |
| app/ui/workspaces/training_studio.py | function | _on_auto_error | 1779 | def _on_auto_error(self, msg: str) |
| app/ui/workspaces/training_studio.py | function | _build_mini_gpt_tab | 1787 | def _build_mini_gpt_tab(self) -> QWidget |
| app/ui/workspaces/training_studio.py | function | _on_mini_dataset_changed | 2010 | def _on_mini_dataset_changed(self, text: str) |
| app/ui/workspaces/training_studio.py | function | _on_mini_browse_file | 2013 | def _on_mini_browse_file(self) |
| app/ui/workspaces/training_studio.py | function | _get_mini_dataset_text | 2019 | def _get_mini_dataset_text(self) -> str |
| app/ui/workspaces/training_studio.py | function | _start_mini_training | 2101 | def _start_mini_training(self) |
| app/ui/workspaces/training_studio.py | function | _stop_mini_training | 2166 | def _stop_mini_training(self) |
| app/ui/workspaces/training_studio.py | function | _on_mini_log | 2171 | def _on_mini_log(self, text: str) |
| app/ui/workspaces/training_studio.py | function | _on_mini_loss | 2174 | def _on_mini_loss(self, step: int, val_loss: float) |
| app/ui/workspaces/training_studio.py | function | _on_mini_progress | 2183 | def _on_mini_progress(self, step: int, max_steps: int, sample_text: str) |
| app/ui/workspaces/training_studio.py | function | _on_mini_done | 2193 | def _on_mini_done(self, save_dir: str) |
| app/ui/workspaces/training_studio.py | function | _on_mini_error | 2212 | def _on_mini_error(self, msg: str) |
| app/ui/workspaces/training_studio.py | function | _run_mini_inference | 2230 | def _run_mini_inference(self) |
| app/ui/workspaces/training_studio/__init__.py | class | TrainingStudioWorkspace | 11 | class TrainingStudioWorkspace(QWidget) |
| app/ui/workspaces/training_studio/__init__.py | function | __init__ | 14 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/__init__.py | function | _build_ui | 21 | def _build_ui(self) |
| app/ui/workspaces/training_studio/__init__.py | function | _on_tab_changed | 71 | def _on_tab_changed(self, idx: int) |
| app/ui/workspaces/training_studio/__init__.py | function | showEvent | 75 | def showEvent(self, event) |
| app/ui/workspaces/training_studio/__init__.py | function | _refresh | 79 | def _refresh(self) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _section | 13 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _hline | 19 | def _hline() -> QFrame |
| app/ui/workspaces/training_studio/auto_train_tab.py | class | AutoTrainTab | 25 | class AutoTrainTab(QWidget) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | __init__ | 26 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _build_ui | 33 | def _build_ui(self) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _begin_auto_training | 165 | def _begin_auto_training(self) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _on_auto_log | 208 | def _on_auto_log(self, text: str) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _on_auto_done | 211 | def _on_auto_done(self, adapter_name: str) |
| app/ui/workspaces/training_studio/auto_train_tab.py | function | _on_auto_error | 221 | def _on_auto_error(self, msg: str) |
| app/ui/workspaces/training_studio/dataset_tab.py | class | DatasetListModel | 11 | class DatasetListModel(QAbstractListModel) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | __init__ | 12 | def __init__(self, dataset_list=None) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | rowCount | 16 | def rowCount(self, parent=QModelIndex()) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | data | 19 | def data(self, index, role=Qt.ItemDataRole.DisplayRole) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | get_item | 28 | def get_item(self, row) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | update_data | 33 | def update_data(self, new_dataset) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _section | 39 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio/dataset_tab.py | class | _MergeThread | 47 | class _MergeThread(QThread) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | __init__ | 52 | def __init__(self, primary: str, incoming: str, parent=None) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | run | 57 | def run(self) |
| app/ui/workspaces/training_studio/dataset_tab.py | class | DatasetTab | 68 | class DatasetTab(QWidget) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | __init__ | 71 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _build_ui | 78 | def _build_ui(self) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _on_row_changed | 128 | def _on_row_changed(self, current, previous) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | refresh | 134 | def refresh(self) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _on_example_selected | 160 | def _on_example_selected(self, row: int) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _delete_selected | 201 | def _delete_selected(self) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _import_team_traces | 216 | def _import_team_traces(self) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _on_merge_finished | 267 | def _on_merge_finished(self, stats: dict) |
| app/ui/workspaces/training_studio/dataset_tab.py | function | _on_merge_error | 300 | def _on_merge_error(self, error_text: str) |
| app/ui/workspaces/training_studio/export_tab.py | function | _section | 10 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio/export_tab.py | class | ExportTab | 16 | class ExportTab(QWidget) |
| app/ui/workspaces/training_studio/export_tab.py | function | __init__ | 17 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/export_tab.py | function | _build_ui | 22 | def _build_ui(self) |
| app/ui/workspaces/training_studio/export_tab.py | function | _export | 80 | def _export(self, mode: str) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _section | 13 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _hline | 19 | def _hline() -> QFrame |
| app/ui/workspaces/training_studio/flywheel_tab.py | class | FlywheelTab | 25 | class FlywheelTab(QWidget) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | __init__ | 26 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _build_ui | 32 | def _build_ui(self) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _flywheel_card | 137 | def _flywheel_card(self, title: str, field_ids: list) -> QWidget |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | load_stats | 168 | def load_stats(self) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _apply_flywheel_stats | 179 | def _apply_flywheel_stats(self, stats: dict) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _flywheel_export_sft | 191 | def _flywheel_export_sft(self) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _flywheel_export_dpo | 195 | def _flywheel_export_dpo(self) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _open_training_folder | 199 | def _open_training_folder(self) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _flywheel_goto_eval | 208 | def _flywheel_goto_eval(self) |
| app/ui/workspaces/training_studio/flywheel_tab.py | function | _export | 216 | def _export(self, mode: str) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _section | 17 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _hline | 23 | def _hline() -> QFrame |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | class | LossChartWidget | 29 | class LossChartWidget(QFrame) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | __init__ | 30 | def __init__(self, parent=None) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | set_loss_history | 43 | def set_loss_history(self, history: list[float]) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | paintEvent | 47 | def paintEvent(self, event) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | class | MiniGptTab | 164 | class MiniGptTab(QWidget) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | __init__ | 165 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _build_ui | 173 | def _build_ui(self) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_dataset_changed | 390 | def _on_mini_dataset_changed(self, text: str) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_browse_file | 393 | def _on_mini_browse_file(self) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _get_mini_dataset_text | 399 | def _get_mini_dataset_text(self) -> str |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _start_mini_training | 481 | def _start_mini_training(self) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _stop_mini_training | 545 | def _stop_mini_training(self) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_log | 550 | def _on_mini_log(self, text: str) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_loss | 553 | def _on_mini_loss(self, step: int, val_loss: float) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_progress | 562 | def _on_mini_progress(self, step: int, max_steps: int, sample_text: str) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_done | 572 | def _on_mini_done(self, save_dir: str) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _on_mini_error | 591 | def _on_mini_error(self, msg: str) |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | function | _run_mini_inference | 609 | def _run_mini_inference(self) |
| app/ui/workspaces/training_studio/threads.py | class | TrainingThread | 8 | class TrainingThread(QThread) |
| app/ui/workspaces/training_studio/threads.py | function | __init__ | 15 | def __init__(self, hf_base_dir: str, adapter_name: str, config: dict) |
| app/ui/workspaces/training_studio/threads.py | function | request_stop | 21 | def request_stop(self) |
| app/ui/workspaces/training_studio/threads.py | function | run | 24 | def run(self) |
| app/ui/workspaces/training_studio/threads.py | class | TrainerProgressCallback | 122 | class TrainerProgressCallback(TrainerCallback) |
| app/ui/workspaces/training_studio/threads.py | function | on_log | 123 | def on_log(self, args, state, control, logs=None, **kwargs) |
| app/ui/workspaces/training_studio/threads.py | function | on_step_end | 130 | def on_step_end(self, args, state, control, **kwargs) |
| app/ui/workspaces/training_studio/threads.py | class | AutoTrainThread | 202 | class AutoTrainThread(QThread) |
| app/ui/workspaces/training_studio/threads.py | function | __init__ | 207 | def __init__(self, topic: str, adapter_name: str, config: dict) |
| app/ui/workspaces/training_studio/threads.py | function | request_stop | 214 | def request_stop(self) |
| app/ui/workspaces/training_studio/threads.py | function | run | 222 | def run(self) |
| app/ui/workspaces/training_studio/threads.py | class | _FlywheelStatsThread | 280 | class _FlywheelStatsThread(QThread) |
| app/ui/workspaces/training_studio/threads.py | function | run | 284 | def run(self) |
| app/ui/workspaces/training_studio/threads.py | class | MiniTrainThread | 392 | class MiniTrainThread(QThread) |
| app/ui/workspaces/training_studio/threads.py | function | __init__ | 400 | def __init__( self, dataset_text: str, config: dict, |
| app/ui/workspaces/training_studio/threads.py | function | stop | 412 | def stop(self) |
| app/ui/workspaces/training_studio/threads.py | function | request_stop | 415 | def request_stop(self) |
| app/ui/workspaces/training_studio/threads.py | function | run | 418 | def run(self) |
| app/ui/workspaces/training_studio/threads.py | function | get_batch | 486 | def get_batch(split) |
| app/ui/workspaces/training_studio/threads.py | function | estimate_loss | 496 | def estimate_loss() |
| app/ui/workspaces/training_studio/train_tab.py | function | _section | 17 | def _section(text: str) -> QLabel |
| app/ui/workspaces/training_studio/train_tab.py | function | _hline | 23 | def _hline() -> QFrame |
| app/ui/workspaces/training_studio/train_tab.py | class | TrainTab | 29 | class TrainTab(QWidget) |
| app/ui/workspaces/training_studio/train_tab.py | function | __init__ | 30 | def __init__(self, state, parent=None) |
| app/ui/workspaces/training_studio/train_tab.py | function | _build_ui | 37 | def _build_ui(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | refresh | 215 | def refresh(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | _load_custom_models | 218 | def _load_custom_models(self) -> list[dict] |
| app/ui/workspaces/training_studio/train_tab.py | function | _save_custom_model | 228 | def _save_custom_model(self, display_name: str, item_data: str, is_path: bool) |
| app/ui/workspaces/training_studio/train_tab.py | function | _browse_hf_model | 245 | def _browse_hf_model(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | _add_hf_repo | 275 | def _add_hf_repo(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | _refresh_base_models | 293 | def _refresh_base_models(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | _get_hf_model_path | 389 | def _get_hf_model_path(self) -> tuple[str \| None, str] |
| app/ui/workspaces/training_studio/train_tab.py | function | _check_deps | 438 | def _check_deps(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | _begin_training | 483 | def _begin_training(self) |
| app/ui/workspaces/training_studio/train_tab.py | function | _on_train_log | 580 | def _on_train_log(self, text: str) |
| app/ui/workspaces/training_studio/train_tab.py | function | _on_train_loss | 583 | def _on_train_loss(self, step: int, value: float, epoch: float) |
| app/ui/workspaces/training_studio/train_tab.py | function | _on_train_progress | 586 | def _on_train_progress(self, current: int, total: int, epoch: float) |
| app/ui/workspaces/training_studio/train_tab.py | function | _on_train_done | 591 | def _on_train_done(self, adapter_path: str) |
| app/ui/workspaces/training_studio/train_tab.py | function | _on_train_error | 601 | def _on_train_error(self, msg: str) |
| app/ui/workspaces/training_studio/train_tab.py | function | _update_export_path_preview | 608 | def _update_export_path_preview(self, name) |
| app/ui/workspaces/vision_workbench.py | class | VisionWorkbench | 27 | class VisionWorkbench(QWidget) |
| app/ui/workspaces/vision_workbench.py | function | __init__ | 28 | def __init__(self, state, workbench_ref=None, parent=None) |
| app/ui/workspaces/vision_workbench.py | function | _build_ui | 40 | def _build_ui(self) |
| app/ui/workspaces/vision_workbench.py | function | refresh | 218 | def refresh(self) |
| app/ui/workspaces/vision_workbench.py | function | _on_selected | 240 | def _on_selected(self, current, _previous) |
| app/ui/workspaces/vision_workbench.py | function | _render_record | 248 | def _render_record(self, record) |
| app/ui/workspaces/vision_workbench.py | function | _clear_details | 280 | def _clear_details(self) |
| app/ui/workspaces/vision_workbench.py | function | _selected_record | 291 | def _selected_record(self) |
| app/ui/workspaces/vision_workbench.py | function | _import_image | 296 | def _import_image(self) |
| app/ui/workspaces/vision_workbench.py | function | _open_file | 314 | def _open_file(self) |
| app/ui/workspaces/vision_workbench.py | function | _send_to_workbench | 319 | def _send_to_workbench(self) |
| app/ui/workspaces/vision_workbench.py | function | _run_analysis | 326 | def _run_analysis(self) |
| app/ui/workspaces/vision_workbench.py | function | _on_analysis_progress | 352 | def _on_analysis_progress(self, msg: str) |
| app/ui/workspaces/vision_workbench.py | function | _on_ocr_done | 356 | def _on_ocr_done(self, image_id: str, ocr) |
| app/ui/workspaces/vision_workbench.py | function | _on_vision_done | 360 | def _on_vision_done(self, image_id: str, vision) |
| app/ui/workspaces/vision_workbench.py | function | _on_analysis_done | 365 | def _on_analysis_done(self, image_id: str, _record) |
| app/ui/workspaces/vision_workbench.py | function | _on_analysis_error | 370 | def _on_analysis_error(self, msg: str) |
| app/ui/workspaces/vision_workbench.py | function | _save_metadata | 374 | def _save_metadata(self) |
| app/ui/workspaces/vision_workbench.py | function | _save_ocr_correction | 387 | def _save_ocr_correction(self) |
| app/ui/workspaces/vision_workbench.py | function | _save_caption_correction | 395 | def _save_caption_correction(self) |
| app/ui/workspaces/vision_workbench.py | function | _update_vision_status | 403 | def _update_vision_status(self) |
| app/ui/workspaces/workbench/branch_panel.py | function | build_branch_tab | 18 | def build_branch_tab(w) -> QWidget |
| app/ui/workspaces/workbench/branch_panel.py | function | populate_branches_tree | 49 | def populate_branches_tree(w) -> None |
| app/ui/workspaces/workbench/branch_panel.py | function | _add_node | 68 | def _add_node(session_node, parent_item) |
| app/ui/workspaces/workbench/branch_panel.py | function | on_branch_clicked | 107 | def on_branch_clicked(w, item, column) -> None |
| app/ui/workspaces/workbench/branch_panel.py | function | branch_from_selected_tree_item | 114 | def branch_from_selected_tree_item(w) -> None |
| app/ui/workspaces/workbench/branch_panel.py | function | branch_from_node | 123 | def branch_from_node(w, node_id: str) -> None |
| app/ui/workspaces/workbench/chat_view.py | function | _escape | 12 | def _escape(text: str) -> str |
| app/ui/workspaces/workbench/chat_view.py | function | _escape_pre | 21 | def _escape_pre(text: str) -> str |
| app/ui/workspaces/workbench/chat_view.py | class | ChatView | 29 | class ChatView(QTextBrowser) |
| app/ui/workspaces/workbench/chat_view.py | function | __init__ | 32 | def __init__(self, parent=None) |
| app/ui/workspaces/workbench/chat_view.py | function | set_theme | 56 | def set_theme(self, theme_colors: dict) |
| app/ui/workspaces/workbench/chat_view.py | function | push_user | 62 | def push_user(self, text: str, node_id: str, attachments: list[dict] \| None = None) |
| app/ui/workspaces/workbench/chat_view.py | function | _get_karl_hdr | 67 | def _get_karl_hdr(self, node_id: str) -> str |
| app/ui/workspaces/workbench/chat_view.py | function | _get_user_html | 82 | def _get_user_html(self, text: str, node_id: str, attachments: list[dict] \| None = None) -> str |
| app/ui/workspaces/workbench/chat_view.py | function | _attachments_html | 100 | def _attachments_html(self, attachments: list[dict]) -> str |
| app/ui/workspaces/workbench/chat_view.py | function | begin_stream | 130 | def begin_stream(self, node_id: str = "") |
| app/ui/workspaces/workbench/chat_view.py | function | append_token | 139 | def append_token(self, token: str) |
| app/ui/workspaces/workbench/chat_view.py | function | finalize_stream | 149 | def finalize_stream(self, node_id: str = "") |
| app/ui/workspaces/workbench/chat_view.py | function | clear_display | 162 | def clear_display(self) |
| app/ui/workspaces/workbench/chat_view.py | function | replace_last_assistant | 168 | def replace_last_assistant(self, text: str) |
| app/ui/workspaces/workbench/chat_view.py | function | append_system_note | 173 | def append_system_note(self, text: str) |
| app/ui/workspaces/workbench/chat_view.py | function | append_diagnostics | 186 | def append_diagnostics(self, model: str, n_ctx: int, diag: dict) |
| app/ui/workspaces/workbench/chat_view.py | function | append_rag_sources | 219 | def append_rag_sources(self, results: list[dict]) |
| app/ui/workspaces/workbench/chat_view.py | function | _finalize_stream | 252 | def _finalize_stream(self) |
| app/ui/workspaces/workbench/chat_view.py | function | _render_all | 256 | def _render_all(self) |
| app/ui/workspaces/workbench/chat_view.py | function | _scroll_to_bottom | 277 | def _scroll_to_bottom(self) |
| app/ui/workspaces/workbench/feedback_panel.py | function | on_thumb_up | 6 | def on_thumb_up(w) -> None |
| app/ui/workspaces/workbench/feedback_panel.py | function | on_thumb_down | 15 | def on_thumb_down(w) -> None |
| app/ui/workspaces/workbench/feedback_panel.py | function | on_correct | 24 | def on_correct(w) -> None |
| app/ui/workspaces/workbench/hud_toolbar.py | function | build_hud_toolbar | 8 | def build_hud_toolbar(w) -> None |
| app/ui/workspaces/workbench/hud_toolbar.py | function | update_hud_btn_styles | 77 | def update_hud_btn_styles(w) -> None |
| app/ui/workspaces/workbench/hud_toolbar.py | function | toggle_rag_hud | 98 | def toggle_rag_hud(w) -> None |
| app/ui/workspaces/workbench/hud_toolbar.py | function | toggle_context_hud | 104 | def toggle_context_hud(w) -> None |
| app/ui/workspaces/workbench/hud_toolbar.py | function | toggle_all_huds | 112 | def toggle_all_huds(w) -> None |
| app/ui/workspaces/workbench/input_panel.py | function | build_input_area | 16 | def build_input_area(w) -> QWidget |
| app/ui/workspaces/workbench/orchestrator.py | class | WorkbenchOrchestrator | 20 | class WorkbenchOrchestrator(QObject) |
| app/ui/workspaces/workbench/orchestrator.py | function | __init__ | 39 | def __init__(self, state, parent=None) |
| app/ui/workspaces/workbench/orchestrator.py | function | is_running | 53 | def is_running(self) -> bool |
| app/ui/workspaces/workbench/orchestrator.py | function | add_user_message | 56 | def add_user_message( self, display_text: str, prompt_text: str, |
| app/ui/workspaces/workbench/orchestrator.py | function | correct_last_response | 75 | def correct_last_response(self, text: str, system_prompt: str) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | save_feedback | 91 | def save_feedback(self, source: str, system_prompt: str) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | retrieve_rag_context | 103 | def retrieve_rag_context(self, prompt_text: str, enabled: bool) -> tuple[list[str], list[dict]] |
| app/ui/workspaces/workbench/orchestrator.py | function | start_generation | 142 | def start_generation( self, *, agentic: bool, |
| app/ui/workspaces/workbench/orchestrator.py | function | _on_thread_finished | 196 | def _on_thread_finished() |
| app/ui/workspaces/workbench/orchestrator.py | function | _on_thread_error | 202 | def _on_thread_error(msg: str) |
| app/ui/workspaces/workbench/orchestrator.py | function | stop_generation | 214 | def stop_generation(self) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | clear_thread | 220 | def clear_thread(self) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | _on_generation_finished | 224 | def _on_generation_finished( self, thought: str, response: str, |
| app/ui/workspaces/workbench/orchestrator.py | function | _on_iteration_finished | 244 | def _on_iteration_finished( self, index: int, thought: str, |
| app/ui/workspaces/workbench/orchestrator.py | function | _on_loop_finished | 256 | def _on_loop_finished(self, total: int) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | _on_error | 272 | def _on_error(self, msg: str) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | diagnostics_context | 275 | def diagnostics_context(self) -> tuple[str, int] |
| app/ui/workspaces/workbench/orchestrator.py | function | load_session | 278 | def load_session(self, path: str) -> tuple[SessionTree, str] |
| app/ui/workspaces/workbench/orchestrator.py | function | save_current_session | 288 | def save_current_session(self) -> str \| None |
| app/ui/workspaces/workbench/orchestrator.py | function | autosave_session | 298 | def autosave_session(self) -> str \| None |
| app/ui/workspaces/workbench/orchestrator.py | function | reset_session | 305 | def reset_session(self) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | set_session_identity | 315 | def set_session_identity(self, session_id: str \| None, current_file: str \| None) -> None |
| app/ui/workspaces/workbench/orchestrator.py | function | set_chat_history | 319 | def set_chat_history(self, tree: SessionTree) -> None |
| app/ui/workspaces/workbench/params_drawer.py | function | _label | 12 | def _label(text: str, obj: str = "") -> QLabel |
| app/ui/workspaces/workbench/params_drawer.py | function | _hline | 19 | def _hline() -> QFrame |
| app/ui/workspaces/workbench/params_drawer.py | function | build_settings_overlay | 25 | def build_settings_overlay(w) -> None |
| app/ui/workspaces/workbench/params_drawer.py | function | toggle_settings_overlay | 152 | def toggle_settings_overlay(w) -> None |
| app/ui/workspaces/workbench/profiles.py | function | reload_profiles | 65 | def reload_profiles() -> None |
| app/ui/workspaces/workbench/session_panel.py | function | build_session_tab | 24 | def build_session_tab(w) -> QWidget |
| app/ui/workspaces/workbench/session_panel.py | function | refresh_sessions | 48 | def refresh_sessions(w) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | filter_sessions | 70 | def filter_sessions(w, text: str) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | on_session_clicked | 77 | def on_session_clicked(w, current, previous) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | show_session_context_menu | 89 | def show_session_context_menu(w, pos) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | rename_session | 124 | def rename_session(w, fname: str) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | duplicate_session | 147 | def duplicate_session(w, fname: str) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | delete_session | 165 | def delete_session(w, fname: str) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | load_session | 193 | def load_session(w, path: str) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | save_current_session | 234 | def save_current_session(w) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | autosave_session | 247 | def autosave_session(w) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | new_session | 260 | def new_session(w) -> None |
| app/ui/workspaces/workbench/session_panel.py | function | apply_session_panel_styles | 287 | def apply_session_panel_styles(w) -> None |
| app/ui/workspaces/workbench/workspace.py | function | _hline | 51 | def _hline() -> QFrame |
| app/ui/workspaces/workbench/workspace.py | function | _label | 57 | def _label(text: str, obj: str = "") -> QLabel |
| app/ui/workspaces/workbench/workspace.py | class | WorkbenchWorkspace | 69 | class WorkbenchWorkspace(QMainWindow) |
| app/ui/workspaces/workbench/workspace.py | function | __init__ | 78 | def __init__(self, state, parent=None) |
| app/ui/workspaces/workbench/workspace.py | function | _build_ui | 155 | def _build_ui(self) |
| app/ui/workspaces/workbench/workspace.py | function | _build_sessions_panel | 199 | def _build_sessions_panel(self) -> QWidget |
| app/ui/workspaces/workbench/workspace.py | function | _build_reasoning_panel | 249 | def _build_reasoning_panel(self) -> QWidget |
| app/ui/workspaces/workbench/workspace.py | function | _build_chat_panel | 273 | def _build_chat_panel(self) -> QWidget |
| app/ui/workspaces/workbench/workspace.py | function | _build_command_header | 463 | def _build_command_header(self) -> QWidget |
| app/ui/workspaces/workbench/workspace.py | function | _build_settings_overlay | 551 | def _build_settings_overlay(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_settings_overlay | 656 | def _toggle_settings_overlay(self) |
| app/ui/workspaces/workbench/workspace.py | function | _responsive_mode_for_width | 704 | def _responsive_mode_for_width(self, width: int) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _set_button_text_width | 713 | def _set_button_text_width(self, button: QPushButton, text: str, width: int) -> None |
| app/ui/workspaces/workbench/workspace.py | function | _apply_responsive_layout | 717 | def _apply_responsive_layout(self, width: int) -> None |
| app/ui/workspaces/workbench/workspace.py | function | _setup_glow_effects | 785 | def _setup_glow_effects(self) |
| app/ui/workspaces/workbench/workspace.py | function | _update_glow_pulse | 804 | def _update_glow_pulse(self) |
| app/ui/workspaces/workbench/workspace.py | function | _setup_chat_animations | 840 | def _setup_chat_animations(self) |
| app/ui/workspaces/workbench/workspace.py | function | custom_set_html | 842 | def custom_set_html(html) |
| app/ui/workspaces/workbench/workspace.py | function | _fade_in_chat | 847 | def _fade_in_chat(self) |
| app/ui/workspaces/workbench/workspace.py | function | _populate_hud_toolbar | 859 | def _populate_hud_toolbar(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_rag_hud | 916 | def _toggle_rag_hud(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_context_hud | 921 | def _toggle_context_hud(self) |
| app/ui/workspaces/workbench/workspace.py | function | _update_hud_btn_styles | 928 | def _update_hud_btn_styles(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_all_huds | 944 | def _toggle_all_huds(self) |
| app/ui/workspaces/workbench/workspace.py | function | resizeEvent | 969 | def resizeEvent(self, event) |
| app/ui/workspaces/workbench/workspace.py | function | update_model_state | 978 | def update_model_state(self, state: str) |
| app/ui/workspaces/workbench/workspace.py | function | _connect_shortcuts | 990 | def _connect_shortcuts(self) |
| app/ui/workspaces/workbench/workspace.py | function | eventFilter | 994 | def eventFilter(self, obj, event) |
| app/ui/workspaces/workbench/workspace.py | function | _send | 1003 | def _send(self) |
| app/ui/workspaces/workbench/workspace.py | function | _clipboard_has_image | 1097 | def _clipboard_has_image(self) -> bool |
| app/ui/workspaces/workbench/workspace.py | function | _attach_clipboard_image | 1102 | def _attach_clipboard_image(self) |
| app/ui/workspaces/workbench/workspace.py | function | attach_existing_image | 1128 | def attach_existing_image(self, image_id: str) |
| app/ui/workspaces/workbench/workspace.py | function | _start_image_analysis | 1147 | def _start_image_analysis(self, image_id: str) |
| app/ui/workspaces/workbench/workspace.py | function | _on_image_analysis_progress | 1159 | def _on_image_analysis_progress(self, image_id: str, msg: str) |
| app/ui/workspaces/workbench/workspace.py | function | _on_image_ocr_done | 1165 | def _on_image_ocr_done(self, image_id: str, ocr) |
| app/ui/workspaces/workbench/workspace.py | function | _on_image_vision_done | 1176 | def _on_image_vision_done(self, image_id: str, vision) |
| app/ui/workspaces/workbench/workspace.py | function | _on_image_analysis_done | 1186 | def _on_image_analysis_done(self, image_id: str, _record) |
| app/ui/workspaces/workbench/workspace.py | function | _on_image_analysis_error | 1191 | def _on_image_analysis_error(self, image_id: str, msg: str) |
| app/ui/workspaces/workbench/workspace.py | function | _build_image_prompt_context | 1198 | def _build_image_prompt_context(self, text: str, attachments: list[dict]) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _current_workflow | 1233 | def _current_workflow(self) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _current_template | 1236 | def _current_template(self) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _update_token_budget | 1243 | def _update_token_budget(self) |
| app/ui/workspaces/workbench/workspace.py | function | _on_reload_success | 1266 | def _on_reload_success(self, label: str) |
| app/ui/workspaces/workbench/workspace.py | function | _on_reload_failed | 1270 | def _on_reload_failed(self, label: str, tb_str: str) |
| app/ui/workspaces/workbench/workspace.py | function | _show_reload_notice | 1296 | def _show_reload_notice(self, module_name: str) |
| app/ui/workspaces/workbench/workspace.py | function | _start_single | 1301 | def _start_single(self, chunks: list[str]) |
| app/ui/workspaces/workbench/workspace.py | function | _start_agentic | 1336 | def _start_agentic(self, chunks: list[str]) |
| app/ui/workspaces/workbench/workspace.py | function | _stop | 1371 | def _stop(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_reasoning | 1376 | def _toggle_reasoning(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_sessions | 1380 | def _toggle_sessions(self) |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_params | 1384 | def _toggle_params(self) |
| app/ui/workspaces/workbench/workspace.py | function | _on_max_tokens_changed | 1390 | def _on_max_tokens_changed(self, value: int) |
| app/ui/workspaces/workbench/workspace.py | function | _on_agent_selected | 1394 | def _on_agent_selected(self, *_args) |
| app/ui/workspaces/workbench/workspace.py | function | _on_header_agent_selected | 1404 | def _on_header_agent_selected(self, *_args) |
| app/ui/workspaces/workbench/workspace.py | function | _pick_header_accent | 1414 | def _pick_header_accent(self) |
| app/ui/workspaces/workbench/workspace.py | function | _active_system_prompt | 1431 | def _active_system_prompt(self) -> str |
| app/ui/workspaces/workbench/workspace.py | function | showEvent | 1438 | def showEvent(self, event) |
| app/ui/workspaces/workbench/workspace.py | function | _is_adapter_compatible | 1442 | def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool |
| app/ui/workspaces/workbench/workspace.py | function | _refresh_model_combo | 1446 | def _refresh_model_combo(self) |
| app/ui/workspaces/workbench/workspace.py | function | _select_model_combo_value | 1473 | def _select_model_combo_value(self, combo: QComboBox, active_model: str \| None, active_adapter: str \| None) |
| app/ui/workspaces/workbench/workspace.py | function | _model_selection_entries | 1491 | def _model_selection_entries(self) -> list[dict] |
| app/ui/workspaces/workbench/workspace.py | function | _model_file_size_label | 1539 | def _model_file_size_label(self, filename: str) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _model_registry_detail | 1547 | def _model_registry_detail(self, filename: str, meta: dict, size: str) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _model_tooltip | 1562 | def _model_tooltip(self, filename: str, meta: dict, size: str, adapter: str \| None) -> str |
| app/ui/workspaces/workbench/workspace.py | function | _on_model_selected | 1577 | def _on_model_selected(self, index: int) |
| app/ui/workspaces/workbench/workspace.py | function | _on_header_model_staged | 1581 | def _on_header_model_staged(self, *_args) |
| app/ui/workspaces/workbench/workspace.py | function | _load_header_selected_model | 1584 | def _load_header_selected_model(self) |
| app/ui/workspaces/workbench/workspace.py | function | _reload_active_model | 1588 | def _reload_active_model(self) |
| app/ui/workspaces/workbench/workspace.py | function | _load_model_selection | 1599 | def _load_model_selection(self, data: dict \| None) |
| app/ui/workspaces/workbench/workspace.py | function | _update_model_pill | 1664 | def _update_model_pill(self) |
| app/ui/workspaces/workbench/workspace.py | function | _update_header_model_status | 1673 | def _update_header_model_status(self, staged: bool = False, error: str \| None = None) |
| app/ui/workspaces/workbench/workspace.py | function | _autosave_session | 1696 | def _autosave_session(self) |
| app/ui/workspaces/workbench/workspace.py | function | _load_session | 1709 | def _load_session(self, path: str) |
| app/ui/workspaces/workbench/workspace.py | function | _new_session | 1748 | def _new_session(self) |
| app/ui/workspaces/workbench/workspace.py | function | _on_context_stats | 1774 | def _on_context_stats(self, total: int, hist: int, rag: int, budget: int) |
| app/ui/workspaces/workbench/workspace.py | function | _on_rag_context_used | 1781 | def _on_rag_context_used(self, chunks: list) |
| app/ui/workspaces/workbench/workspace.py | function | _on_thought | 1807 | def _on_thought(self, token: str) |
| app/ui/workspaces/workbench/workspace.py | function | _on_chat | 1814 | def _on_chat(self, token: str) |
| app/ui/workspaces/workbench/workspace.py | function | _on_live_stats | 1819 | def _on_live_stats(self, count: int, speed: float) |
| app/ui/workspaces/workbench/workspace.py | function | _on_done | 1822 | def _on_done(self, thought: str, response: str, truncated: bool, _ended_in_thought: bool, diagnostics: dict \| None = None) |
| app/ui/workspaces/workbench/workspace.py | function | _on_iteration | 1852 | def _on_iteration(self, index: int, _thought: str, response: str, diagnostics: dict \| None = None) |
| app/ui/workspaces/workbench/workspace.py | function | _on_loop_done | 1862 | def _on_loop_done(self, total: int) |
| app/ui/workspaces/workbench/workspace.py | function | _on_error | 1893 | def _on_error(self, msg: str) |
| app/ui/workspaces/workbench/workspace.py | function | _on_thumb_up | 1904 | def _on_thumb_up(self) |
| app/ui/workspaces/workbench/workspace.py | function | _on_thumb_down | 1918 | def _on_thumb_down(self) |
| app/ui/workspaces/workbench/workspace.py | function | _on_correct | 1932 | def _on_correct(self) |
| app/ui/workspaces/workbench/workspace.py | function | _save_current_session | 1941 | def _save_current_session(self) |
| app/ui/workspaces/workbench/workspace.py | function | _refresh_sessions | 1955 | def _refresh_sessions(self) |
| app/ui/workspaces/workbench/workspace.py | function | _on_session_clicked | 1978 | def _on_session_clicked(self, current, previous) |
| app/ui/workspaces/workbench/workspace.py | function | on_close | 1988 | def on_close(self) |
| app/ui/workspaces/workbench/workspace.py | function | update_theme | 1991 | def update_theme(self) |
| app/ui/workspaces/workbench/workspace.py | function | _set_busy | 2015 | def _set_busy(self, busy: bool) |
| app/ui/workspaces/workbench/workspace.py | function | _on_chat_link_clicked | 2025 | def _on_chat_link_clicked(self, url) |
| app/ui/workspaces/workbench/workspace.py | function | _branch_from_node | 2031 | def _branch_from_node(self, node_id) |
| app/ui/workspaces/workbench/workspace.py | function | _populate_branches_tree | 2067 | def _populate_branches_tree(self) |
| app/ui/workspaces/workbench/workspace.py | function | _add_node | 2085 | def _add_node(session_node, parent_item) |
| app/ui/workspaces/workbench/workspace.py | function | _on_branch_clicked | 2121 | def _on_branch_clicked(self, item, column) |
| app/ui/workspaces/workbench/workspace.py | function | _branch_from_selected_tree_item | 2129 | def _branch_from_selected_tree_item(self) |
| app/ui/workspaces/workbench/workspace.py | function | _build_expert_strip | 2139 | def _build_expert_strip(self) -> QWidget |
| app/ui/workspaces/workbench/workspace.py | function | _toggle_expert_strip | 2198 | def _toggle_expert_strip(self) |
| app/ui/workspaces/workbench/workspace.py | function | _update_expert_strip | 2216 | def _update_expert_strip(self) |
| app/ui/workspaces/workbench/workspace.py | function | _filter_sessions | 2254 | def _filter_sessions(self, text) |
| app/ui/workspaces/workbench/workspace.py | function | _show_session_context_menu | 2260 | def _show_session_context_menu(self, pos) |
| app/ui/workspaces/workbench/workspace.py | function | _rename_session | 2287 | def _rename_session(self, fname) |
| app/ui/workspaces/workbench/workspace.py | function | _duplicate_session | 2314 | def _duplicate_session(self, fname) |
| app/ui/workspaces/workbench/workspace.py | function | _delete_session | 2334 | def _delete_session(self, fname) |
| app/ui/workspaces/workbench/workspace.py | function | set_system_prompt | 2361 | def set_system_prompt(self, prompt: str) |
| app/ui/workspaces/workbench/workspace.py | function | set_hyperparams | 2364 | def set_hyperparams(self, params: dict) |
| app/ui/workspaces/workbench/workspace.py | function | append_to_input | 2379 | def append_to_input(self, text: str) |
| app/utils/codebase_search.py | function | codebase_search | 9 | def codebase_search(query: str, workspace_path: str) -> List[Dict[str, Any]] |
| app/utils/conversion/__init__.py | function | load_all_models | 298 | def load_all_models() -> None |
| app/utils/conversion/__init__.py | function | get_model_class | 319 | def get_model_class(name: str, mmproj: bool = False) -> Type[ModelBase] |
| app/utils/conversion/__init__.py | function | print_registered_models | 330 | def print_registered_models() -> None |
| app/utils/conversion/afmoe.py | class | AfmoeModel | 16 | class AfmoeModel(LlamaModel) |
| app/utils/conversion/afmoe.py | function | set_gguf_parameters | 19 | def set_gguf_parameters(self) |
| app/utils/conversion/afmoe.py | function | filter_tensors | 41 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/afmoe.py | function | modify_tensors | 49 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/arctic.py | class | ArcticModel | 19 | class ArcticModel(TextModel) |
| app/utils/conversion/arctic.py | function | set_vocab | 22 | def set_vocab(self) |
| app/utils/conversion/arctic.py | function | set_gguf_parameters | 106 | def set_gguf_parameters(self) |
| app/utils/conversion/arctic.py | function | modify_tensors | 114 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/arctic.py | function | prepare_tensors | 155 | def prepare_tensors(self) |
| app/utils/conversion/baichuan.py | class | BaichuanModel | 12 | class BaichuanModel(TextModel) |
| app/utils/conversion/baichuan.py | function | set_vocab | 15 | def set_vocab(self) |
| app/utils/conversion/baichuan.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/baichuan.py | function | modify_tensors | 24 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/baichuan.py | function | _reverse_hf_permute | 41 | def _reverse_hf_permute(self, weights: Tensor, n_head: int, n_kv_head: int \| None = None) -> Tensor |
| app/utils/conversion/baichuan.py | function | _reverse_hf_permute_part | 51 | def _reverse_hf_permute_part( self, weights: Tensor, n_part: int, n_head: int, n_head_kv: int \| None = None, ) -> Tensor |
| app/utils/conversion/baichuan.py | function | _reverse_hf_part | 57 | def _reverse_hf_part(self, weights: Tensor, n_part: int) -> Tensor |
| app/utils/conversion/bailingmoe.py | class | BailingMoeModel | 14 | class BailingMoeModel(TextModel) |
| app/utils/conversion/bailingmoe.py | function | set_vocab | 17 | def set_vocab(self) |
| app/utils/conversion/bailingmoe.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/bailingmoe.py | function | permute | 37 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| app/utils/conversion/bailingmoe.py | function | modify_tensors | 44 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bailingmoe.py | function | prepare_tensors | 100 | def prepare_tensors(self) |
| app/utils/conversion/bailingmoe.py | class | BailingMoeV2Model | 111 | class BailingMoeV2Model(TextModel) |
| app/utils/conversion/bailingmoe.py | function | __init__ | 114 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/bailingmoe.py | function | set_vocab | 120 | def set_vocab(self) |
| app/utils/conversion/bailingmoe.py | function | set_gguf_parameters | 123 | def set_gguf_parameters(self) |
| app/utils/conversion/bailingmoe.py | function | filter_tensors | 144 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bailingmoe.py | function | modify_tensors | 152 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bailingmoe.py | function | prepare_tensors | 181 | def prepare_tensors(self) |
| app/utils/conversion/bailingmoe.py | class | SarvamMoEModel | 192 | class SarvamMoEModel(BailingMoeV2Model) |
| app/utils/conversion/bailingmoe.py | function | set_gguf_parameters | 198 | def set_gguf_parameters(self) |
| app/utils/conversion/bailingmoe.py | function | filter_tensors | 207 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bailingmoe.py | function | gen | 213 | def gen() |
| app/utils/conversion/base.py | class | SentencePieceTokenTypes | 61 | class SentencePieceTokenTypes(IntEnum) |
| app/utils/conversion/base.py | class | ModelType | 70 | class ModelType(IntEnum) |
| app/utils/conversion/base.py | class | ModelBase | 75 | class ModelBase |
| app/utils/conversion/base.py | function | __init__ | 115 | def __init__(self, dir_model: Path, ftype: gguf.LlamaFileType, fname_out: Path, *, is_big_endian: bool = False, use_temp_file: bool = False, eager: bool = False, metadata_override: Path \| None = None, model_name: str \| None = None, split_max_tensors: int = 0, split_max_size: int = 0, dry_run: bool = False, |
| app/utils/conversion/base.py | function | add_prefix_to_filename | 182 | def add_prefix_to_filename(cls, path: Path, prefix: str) -> Path |
| app/utils/conversion/base.py | function | find_hparam | 187 | def find_hparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| app/utils/conversion/base.py | function | index_tensors | 195 | def index_tensors(self, remote_hf_model_id: str \| None = None) -> dict[str, Callable[[], Tensor]] |
| app/utils/conversion/base.py | function | _scale_is_trivial | 287 | def _scale_is_trivial(scale: Tensor) -> bool |
| app/utils/conversion/base.py | function | _write_scale_tensor | 290 | def _write_scale_tensor(self, scale_name: str, scale: Tensor) |
| app/utils/conversion/base.py | function | _write_scales_tensor | 296 | def _write_scales_tensor(self, scale_name: str, scales: list[float]) |
| app/utils/conversion/base.py | function | dequant_model | 302 | def dequant_model(self) |
| app/utils/conversion/base.py | function | dequant_bitnet | 313 | def dequant_bitnet(weight: Tensor, scale: Tensor) -> Tensor |
| app/utils/conversion/base.py | function | dequant_simple | 325 | def dequant_simple(weight: Tensor, scale: Tensor, block_size: Sequence[int] \| None = None) -> Tensor |
| app/utils/conversion/base.py | function | dequant_gptq | 342 | def dequant_gptq(g_idx: Tensor, qweight: Tensor, qzeros: Tensor, scales: Tensor) -> Tensor |
| app/utils/conversion/base.py | function | dequant_packed | 384 | def dequant_packed(w: Tensor, scale: Tensor, shape_tensor: Tensor, zero_point: Tensor \| None, num_bits: int, group_size: int) |
| app/utils/conversion/base.py | function | filter_tensors | 566 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/base.py | function | get_tensors | 577 | def get_tensors(self) -> Iterator[tuple[str, Tensor]] |
| app/utils/conversion/base.py | function | format_tensor_name | 581 | def format_tensor_name(self, key: gguf.MODEL_TENSOR, bid: int \| None = None, suffix: str = ".weight") -> str |
| app/utils/conversion/base.py | function | match_model_tensor_name | 590 | def match_model_tensor_name(self, name: str, key: gguf.MODEL_TENSOR, bid: int \| None, suffix: str = ".weight") -> bool |
| app/utils/conversion/base.py | function | map_tensor_name | 603 | def map_tensor_name(self, name: str, try_suffixes: Sequence[str] = (".weight", ".bias")) -> str |
| app/utils/conversion/base.py | function | set_gguf_parameters | 609 | def set_gguf_parameters(self) |
| app/utils/conversion/base.py | function | modify_tensors | 612 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/base.py | function | tensor_force_quant | 639 | def tensor_force_quant(self, name: str, new_name: str, bid: int \| None, n_dims: int) -> gguf.GGMLQuantizationType \| bool |
| app/utils/conversion/base.py | function | generate_extra_tensors | 647 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/base.py | function | _nvfp4_pack | 651 | def _nvfp4_pack(weight: Tensor, scale: Tensor) -> tuple[np.ndarray, list[int]] |
| app/utils/conversion/base.py | function | _repack_nvfp4 | 675 | def _repack_nvfp4(self, name: str, weight: Tensor, scale: Tensor, scale2: Tensor, input_scale: Tensor) |
| app/utils/conversion/base.py | function | _generate_nvfp4_tensors | 685 | def _generate_nvfp4_tensors(self) |
| app/utils/conversion/base.py | function | _flush_nvfp4_experts | 761 | def _flush_nvfp4_experts(self, key, expert_blocks, expert_scales, expert_input_scales, expert_shapes, bid, proj_type) |
| app/utils/conversion/base.py | function | prepare_tensors | 782 | def prepare_tensors(self) |
| app/utils/conversion/base.py | function | inverse_scale | 830 | def inverse_scale(gen) |
| app/utils/conversion/base.py | function | load | 831 | def load() |
| app/utils/conversion/base.py | function | set_type | 978 | def set_type(self) |
| app/utils/conversion/base.py | function | prepare_metadata | 981 | def prepare_metadata(self, vocab_only: bool) |
| app/utils/conversion/base.py | function | write_vocab | 1016 | def write_vocab(self) |
| app/utils/conversion/base.py | function | write | 1019 | def write(self) |
| app/utils/conversion/base.py | function | get_model_part_names | 1028 | def get_model_part_names(dir_model: Path, prefix: str, suffix: str) -> list[str] |
| app/utils/conversion/base.py | function | load_hparams | 1039 | def load_hparams(dir_model: Path, is_mistral_format: bool) |
| app/utils/conversion/base.py | function | register | 1072 | def register(cls, *names: str) -> Callable[[AnyModel], AnyModel] |
| app/utils/conversion/base.py | function | func | 1075 | def func(modelcls: AnyModel) -> AnyModel |
| app/utils/conversion/base.py | function | print_registered_models | 1083 | def print_registered_models(cls) |
| app/utils/conversion/base.py | function | from_model_architecture | 1090 | def from_model_architecture(cls, arch: str, model_type = ModelType.TEXT) -> type[ModelBase] |
| app/utils/conversion/base.py | class | TextModel | 1097 | class TextModel(ModelBase) |
| app/utils/conversion/base.py | function | __init__ | 1101 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/base.py | function | __init_subclass__ | 1130 | def __init_subclass__(cls) |
| app/utils/conversion/base.py | function | filter_tensors | 1137 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/base.py | function | set_vocab | 1153 | def set_vocab(self) |
| app/utils/conversion/base.py | function | prepare_metadata | 1156 | def prepare_metadata(self, vocab_only: bool) |
| app/utils/conversion/base.py | function | set_gguf_parameters | 1184 | def set_gguf_parameters(self) |
| app/utils/conversion/base.py | function | write_vocab | 1296 | def write_vocab(self) |
| app/utils/conversion/base.py | function | does_token_look_special | 1305 | def does_token_look_special(self, token: str \| bytes) -> bool |
| app/utils/conversion/base.py | function | get_vocab_base | 1329 | def get_vocab_base(self) -> tuple[list[str], list[int], str] |
| app/utils/conversion/base.py | function | get_vocab_base_pre | 1377 | def get_vocab_base_pre(self, tokenizer) -> str |
| app/utils/conversion/base.py | function | _set_vocab_none | 1682 | def _set_vocab_none(self) -> None |
| app/utils/conversion/base.py | function | _set_vocab_gpt2 | 1685 | def _set_vocab_gpt2(self) -> None |
| app/utils/conversion/base.py | function | _set_vocab_hybriddna | 1695 | def _set_vocab_hybriddna(self) |
| app/utils/conversion/base.py | function | _set_vocab_qwen | 1736 | def _set_vocab_qwen(self) |
| app/utils/conversion/base.py | function | _set_vocab_sentencepiece | 1792 | def _set_vocab_sentencepiece(self, add_to_gguf=True) |
| app/utils/conversion/base.py | function | _create_vocab_sentencepiece | 1804 | def _create_vocab_sentencepiece(self) |
| app/utils/conversion/base.py | function | _set_vocab_llama_hf | 1894 | def _set_vocab_llama_hf(self) |
| app/utils/conversion/base.py | function | _set_vocab_rwkv_world | 1916 | def _set_vocab_rwkv_world(self) |
| app/utils/conversion/base.py | function | _set_vocab_builtin | 1961 | def _set_vocab_builtin(self, model_name: Literal["gpt-neox", "llama-spm"], vocab_size: int) |
| app/utils/conversion/base.py | function | _try_set_pooling_type | 2006 | def _try_set_pooling_type(self) -> None |
| app/utils/conversion/base.py | function | _set_vocab_glmedge | 2040 | def _set_vocab_glmedge(self) |
| app/utils/conversion/base.py | function | _set_vocab_glm | 2055 | def _set_vocab_glm(self) |
| app/utils/conversion/base.py | function | _set_vocab_interns1 | 2072 | def _set_vocab_interns1(self) |
| app/utils/conversion/base.py | function | _set_vocab_mistral | 2121 | def _set_vocab_mistral(self) |
| app/utils/conversion/base.py | function | _set_vocab_plamo | 2196 | def _set_vocab_plamo(self) |
| app/utils/conversion/base.py | class | MmprojModel | 2275 | class MmprojModel(ModelBase) |
| app/utils/conversion/base.py | function | __init__ | 2290 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/base.py | function | filter_tensors | 2362 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/base.py | function | get_vision_config | 2371 | def get_vision_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/base.py | function | get_audio_config | 2375 | def get_audio_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/base.py | function | set_type | 2379 | def set_type(self) |
| app/utils/conversion/base.py | function | prepare_metadata | 2382 | def prepare_metadata(self, vocab_only: bool) |
| app/utils/conversion/base.py | function | set_gguf_parameters | 2393 | def set_gguf_parameters(self) |
| app/utils/conversion/base.py | function | write_vocab | 2429 | def write_vocab(self) |
| app/utils/conversion/base.py | function | find_vparam | 2432 | def find_vparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| app/utils/conversion/base.py | function | find_aparam | 2436 | def find_aparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| app/utils/conversion/base.py | function | _find_param | 2440 | def _find_param(self, obj: dict[str, Any], keys: Iterable[str], optional: bool = False) -> Any |
| app/utils/conversion/base.py | function | tensor_force_quant | 2448 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/base.py | class | LazyTorchTensor | 2454 | class LazyTorchTensor(gguf.LazyBase) |
| app/utils/conversion/base.py | function | numpy | 2508 | def numpy(self) -> gguf.LazyNumpyTensor |
| app/utils/conversion/base.py | function | meta_with_dtype_and_shape | 2517 | def meta_with_dtype_and_shape(cls, dtype: torch.dtype, shape: tuple[int, ...]) -> Tensor |
| app/utils/conversion/base.py | function | from_safetensors_slice | 2521 | def from_safetensors_slice(cls, st_slice: Any) -> Tensor |
| app/utils/conversion/base.py | function | from_local_tensor | 2528 | def from_local_tensor(cls, t: gguf.utility.LocalTensor) -> Tensor |
| app/utils/conversion/base.py | function | load_tensor | 2529 | def load_tensor(tensor: gguf.utility.LocalTensor) -> Tensor |
| app/utils/conversion/base.py | function | byteswap_tensor | 2530 | def byteswap_tensor(tensor: np.ndarray, dtype: type) -> np.ndarray |
| app/utils/conversion/base.py | function | from_remote_tensor | 2544 | def from_remote_tensor(cls, remote_tensor: gguf.utility.RemoteTensor) |
| app/utils/conversion/base.py | function | byteswap_tensor | 2545 | def byteswap_tensor(tensor: np.ndarray, dtype: type) -> np.ndarray |
| app/utils/conversion/base.py | function | __torch_function__ | 2558 | def __torch_function__(cls, func, types, args=(), kwargs=None) |
| app/utils/conversion/base.py | function | get_model_architecture | 2571 | def get_model_architecture(hparams: dict[str, Any], model_type: ModelType) -> str |
| app/utils/conversion/bert.py | class | BertModel | 18 | class BertModel(TextModel) |
| app/utils/conversion/bert.py | function | __init__ | 21 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 31 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | set_vocab | 39 | def set_vocab(self) |
| app/utils/conversion/bert.py | function | phantom | 49 | def phantom(tok, toktype) |
| app/utils/conversion/bert.py | function | filter_tensors | 69 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | function | modify_tensors | 93 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bert.py | function | _xlmroberta_tokenizer_init | 104 | def _xlmroberta_tokenizer_init(self) -> None |
| app/utils/conversion/bert.py | function | _xlmroberta_set_vocab | 113 | def _xlmroberta_set_vocab(self) -> None |
| app/utils/conversion/bert.py | class | DistilBertModel | 243 | class DistilBertModel(BertModel) |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 246 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | filter_tensors | 252 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | class | RobertaModel | 266 | class RobertaModel(BertModel) |
| app/utils/conversion/bert.py | function | __init__ | 269 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/bert.py | function | set_vocab | 280 | def set_vocab(self) |
| app/utils/conversion/bert.py | function | filter_tensors | 295 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | function | modify_tensors | 305 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bert.py | class | NomicBertModel | 315 | class NomicBertModel(BertModel) |
| app/utils/conversion/bert.py | function | __init__ | 318 | def __init__(self, dir_model: Path, ftype: gguf.LlamaFileType, fname_out: Path, **kwargs: Any) |
| app/utils/conversion/bert.py | function | set_vocab | 356 | def set_vocab(self) -> None |
| app/utils/conversion/bert.py | function | filter_tensors | 362 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | function | modify_tensors | 371 | def modify_tensors(self, data_torch: torch.Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, torch.Tensor]] |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 384 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | _is_tokenizer_xlmroberta | 390 | def _is_tokenizer_xlmroberta(self) -> bool |
| app/utils/conversion/bert.py | class | NeoBert | 402 | class NeoBert(BertModel) |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 405 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | filter_tensors | 420 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | class | EuroBertModel | 433 | class EuroBertModel(TextModel) |
| app/utils/conversion/bert.py | function | set_vocab | 436 | def set_vocab(self) |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 440 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | filter_tensors | 451 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | class | XLMRobertaModel | 461 | class XLMRobertaModel(BertModel) |
| app/utils/conversion/bert.py | function | __init__ | 466 | def __init__(self, dir_model: Path, ftype: gguf.LlamaFileType, fname_out: Path, **kwargs: Any) |
| app/utils/conversion/bert.py | function | generate_extra_tensors | 478 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bert.py | function | set_type | 486 | def set_type(self) |
| app/utils/conversion/bert.py | function | set_vocab | 492 | def set_vocab(self) |
| app/utils/conversion/bert.py | function | filter_tensors | 496 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | function | modify_tensors | 512 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 540 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | write | 553 | def write(self) |
| app/utils/conversion/bert.py | class | JinaBertV2Model | 563 | class JinaBertV2Model(BertModel) |
| app/utils/conversion/bert.py | function | set_vocab | 566 | def set_vocab(self) |
| app/utils/conversion/bert.py | class | ModernBertModel | 581 | class ModernBertModel(BertModel) |
| app/utils/conversion/bert.py | function | set_vocab | 584 | def set_vocab(self) |
| app/utils/conversion/bert.py | function | set_gguf_parameters | 590 | def set_gguf_parameters(self) |
| app/utils/conversion/bert.py | function | filter_tensors | 599 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/bert.py | function | modify_tensors | 607 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bitnet.py | class | BitnetModel | 12 | class BitnetModel(TextModel) |
| app/utils/conversion/bitnet.py | function | set_vocab | 15 | def set_vocab(self) |
| app/utils/conversion/bitnet.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/bitnet.py | function | weight_quant | 23 | def weight_quant(self, weight: Tensor) -> Tensor |
| app/utils/conversion/bitnet.py | function | modify_tensors | 34 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/bloom.py | class | BloomModel | 16 | class BloomModel(TextModel) |
| app/utils/conversion/bloom.py | function | set_gguf_parameters | 19 | def set_gguf_parameters(self) |
| app/utils/conversion/bloom.py | function | modify_tensors | 33 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/chameleon.py | class | ChameleonModel | 15 | class ChameleonModel(TextModel) |
| app/utils/conversion/chameleon.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/chameleon.py | function | set_vocab | 22 | def set_vocab(self) |
| app/utils/conversion/chameleon.py | function | filter_tensors | 26 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/chameleon.py | function | modify_tensors | 36 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/chameleon.py | function | _reverse_hf_permute | 54 | def _reverse_hf_permute(data_torch, n_heads, hidden_dim) |
| app/utils/conversion/chatglm.py | class | ChatGLMModel | 12 | class ChatGLMModel(TextModel) |
| app/utils/conversion/chatglm.py | function | set_vocab_chatglm3 | 15 | def set_vocab_chatglm3(self) |
| app/utils/conversion/chatglm.py | function | token_bytes_to_string | 83 | def token_bytes_to_string(b) |
| app/utils/conversion/chatglm.py | function | bpe | 89 | def bpe(mergeable_ranks: dict[bytes, int], token: bytes, max_rank: int \| None = None) -> list[bytes] |
| app/utils/conversion/chatglm.py | function | set_vocab | 105 | def set_vocab(self) |
| app/utils/conversion/chatglm.py | function | set_gguf_parameters | 133 | def set_gguf_parameters(self) |
| app/utils/conversion/chatglm.py | function | filter_tensors | 159 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/codeshell.py | class | CodeShellModel | 7 | class CodeShellModel(TextModel) |
| app/utils/conversion/codeshell.py | function | set_gguf_parameters | 10 | def set_gguf_parameters(self) |
| app/utils/conversion/cogvlm.py | class | CogVLMVisionModel | 14 | class CogVLMVisionModel(MmprojModel) |
| app/utils/conversion/cogvlm.py | function | set_gguf_parameters | 16 | def set_gguf_parameters(self) |
| app/utils/conversion/cogvlm.py | function | filter_tensors | 22 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/cogvlm.py | class | CogVLMModel | 32 | class CogVLMModel(LlamaModel) |
| app/utils/conversion/command_r.py | class | CommandR2Model | 14 | class CommandR2Model(TextModel) |
| app/utils/conversion/command_r.py | function | __init__ | 17 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/command_r.py | function | set_gguf_parameters | 25 | def set_gguf_parameters(self) |
| app/utils/conversion/command_r.py | class | Cohere2Model | 32 | class Cohere2Model(TextModel) |
| app/utils/conversion/command_r.py | function | set_gguf_parameters | 35 | def set_gguf_parameters(self) |
| app/utils/conversion/command_r.py | function | modify_tensors | 48 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/dbrx.py | class | DbrxModel | 12 | class DbrxModel(TextModel) |
| app/utils/conversion/dbrx.py | function | set_gguf_parameters | 15 | def set_gguf_parameters(self) |
| app/utils/conversion/dbrx.py | function | modify_tensors | 39 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/dbrx.py | function | tensor_force_quant | 72 | def tensor_force_quant(self, name: str, new_name: str, bid: int \| None, n_dims: int) -> gguf.GGMLQuantizationType \| bool |
| app/utils/conversion/deci.py | class | DeciModel | 16 | class DeciModel(TextModel) |
| app/utils/conversion/deci.py | function | _ffn_mult_to_intermediate_size | 20 | def _ffn_mult_to_intermediate_size(ffn_mult: float, n_embd: int) -> int |
| app/utils/conversion/deci.py | function | _find_multiple | 26 | def _find_multiple(n: int, k: int) -> int |
| app/utils/conversion/deci.py | function | __init__ | 32 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/deci.py | function | set_vocab | 80 | def set_vocab(self) |
| app/utils/conversion/deci.py | function | set_gguf_parameters | 96 | def set_gguf_parameters(self) |
| app/utils/conversion/deci.py | function | permute | 127 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| app/utils/conversion/deci.py | function | modify_tensors | 134 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/deci.py | function | generate_extra_tensors | 153 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/deci.py | function | prepare_tensors | 183 | def prepare_tensors(self) |
| app/utils/conversion/deepseek.py | class | DeepseekOCRVisionModel | 18 | class DeepseekOCRVisionModel(MmprojModel) |
| app/utils/conversion/deepseek.py | function | __init__ | 19 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/deepseek.py | function | set_gguf_parameters | 23 | def set_gguf_parameters(self) |
| app/utils/conversion/deepseek.py | function | get_vision_config | 49 | def get_vision_config(self) -> dict[str, Any] |
| app/utils/conversion/deepseek.py | function | tensor_force_quant | 66 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/deepseek.py | function | modify_tensors | 72 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/deepseek.py | function | filter_tensors | 78 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/deepseek.py | class | DeepseekOCR2VisionModel | 94 | class DeepseekOCR2VisionModel(DeepseekOCRVisionModel) |
| app/utils/conversion/deepseek.py | function | __init__ | 95 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/deepseek.py | function | set_gguf_parameters | 99 | def set_gguf_parameters(self) |
| app/utils/conversion/deepseek.py | function | get_vision_config | 112 | def get_vision_config(self) -> dict[str, Any] |
| app/utils/conversion/deepseek.py | class | DeepseekModel | 121 | class DeepseekModel(TextModel) |
| app/utils/conversion/deepseek.py | function | set_vocab | 124 | def set_vocab(self) |
| app/utils/conversion/deepseek.py | function | set_gguf_parameters | 130 | def set_gguf_parameters(self) |
| app/utils/conversion/deepseek.py | function | permute | 148 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| app/utils/conversion/deepseek.py | function | modify_tensors | 155 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/deepseek.py | function | prepare_tensors | 195 | def prepare_tensors(self) |
| app/utils/conversion/deepseek.py | class | DeepseekV2Model | 213 | class DeepseekV2Model(TextModel) |
| app/utils/conversion/deepseek.py | function | __init__ | 221 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/deepseek.py | function | filter_tensors | 235 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/deepseek.py | function | set_vocab | 242 | def set_vocab(self) |
| app/utils/conversion/deepseek.py | function | set_gguf_parameters | 296 | def set_gguf_parameters(self) |
| app/utils/conversion/deepseek.py | function | modify_tensors | 361 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/deepseek.py | function | prepare_tensors | 425 | def prepare_tensors(self) |
| app/utils/conversion/deepseek.py | class | DeepseekV32Model | 436 | class DeepseekV32Model(DeepseekV2Model) |
| app/utils/conversion/deepseek.py | function | __init__ | 440 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/deepseek.py | function | set_vocab | 445 | def set_vocab(self) |
| app/utils/conversion/deepseek.py | function | set_gguf_parameters | 451 | def set_gguf_parameters(self) |
| app/utils/conversion/dots1.py | class | Dots1Model | 14 | class Dots1Model(Qwen2MoeModel) |
| app/utils/conversion/dots1.py | function | __init__ | 17 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/dots1.py | function | set_gguf_parameters | 21 | def set_gguf_parameters(self) |
| app/utils/conversion/dots1.py | function | modify_tensors | 28 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| app/utils/conversion/dotsocr.py | class | DotsOCRVisionModel | 12 | class DotsOCRVisionModel(MmprojModel) |
| app/utils/conversion/dotsocr.py | function | __init__ | 13 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/dotsocr.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/dotsocr.py | function | filter_tensors | 28 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/dotsocr.py | function | modify_tensors | 47 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/dream.py | class | DreamModel | 12 | class DreamModel(TextModel) |
| app/utils/conversion/dream.py | function | get_vocab_base | 15 | def get_vocab_base(self) -> tuple[list[str], list[int], str] |
| app/utils/conversion/dream.py | function | set_vocab | 52 | def set_vocab(self) |
| app/utils/conversion/dream.py | function | set_gguf_parameters | 58 | def set_gguf_parameters(self) |
| app/utils/conversion/dream.py | function | modify_tensors | 70 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ernie.py | class | Ernie4_5Model | 18 | class Ernie4_5Model(TextModel) |
| app/utils/conversion/ernie.py | function | set_vocab | 21 | def set_vocab(self) |
| app/utils/conversion/ernie.py | function | set_gguf_parameters | 31 | def set_gguf_parameters(self) |
| app/utils/conversion/ernie.py | function | filter_tensors | 35 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/ernie.py | function | modify_tensors | 43 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ernie.py | class | Ernie4_5MoeModel | 76 | class Ernie4_5MoeModel(Ernie4_5Model) |
| app/utils/conversion/ernie.py | function | __init__ | 80 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/ernie.py | function | set_gguf_parameters | 84 | def set_gguf_parameters(self) |
| app/utils/conversion/ernie.py | function | filter_tensors | 98 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/ernie.py | function | modify_tensors | 121 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ernie.py | function | prepare_tensors | 148 | def prepare_tensors(self) |
| app/utils/conversion/ernie.py | class | PaddleOCRModel | 159 | class PaddleOCRModel(Ernie4_5Model) |
| app/utils/conversion/ernie.py | class | PaddleOCRVisionModel | 164 | class PaddleOCRVisionModel(MmprojModel) |
| app/utils/conversion/ernie.py | function | __init__ | 169 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/ernie.py | function | set_gguf_parameters | 176 | def set_gguf_parameters(self) |
| app/utils/conversion/ernie.py | function | filter_tensors | 187 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/exaone.py | class | ExaoneModel | 17 | class ExaoneModel(TextModel) |
| app/utils/conversion/exaone.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/exaone.py | function | generate_extra_tensors | 30 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/exaone.py | class | Exaone4Model | 62 | class Exaone4Model(TextModel) |
| app/utils/conversion/exaone.py | function | set_vocab | 65 | def set_vocab(self) |
| app/utils/conversion/exaone.py | function | set_gguf_parameters | 75 | def set_gguf_parameters(self) |
| app/utils/conversion/exaone.py | function | generate_extra_tensors | 95 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/exaone.py | class | ExaoneMoEModel | 126 | class ExaoneMoEModel(Exaone4Model) |
| app/utils/conversion/exaone.py | function | __init__ | 129 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/exaone.py | function | set_gguf_parameters | 134 | def set_gguf_parameters(self) |
| app/utils/conversion/exaone.py | function | modify_tensors | 151 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/exaone.py | function | prepare_tensors | 204 | def prepare_tensors(self) |
| app/utils/conversion/falcon.py | class | FalconModel | 14 | class FalconModel(TextModel) |
| app/utils/conversion/falcon.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| app/utils/conversion/falcon.py | function | modify_tensors | 36 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/falcon_h1.py | class | FalconH1Model | 15 | class FalconH1Model(Mamba2Model) |
| app/utils/conversion/falcon_h1.py | function | __init__ | 18 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/falcon_h1.py | function | find_hparam | 46 | def find_hparam(self, keys: Iterable[str], *args, **kwargs) -> Any |
| app/utils/conversion/falcon_h1.py | function | set_vocab | 56 | def set_vocab(self) |
| app/utils/conversion/falcon_h1.py | function | modify_tensors | 59 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/falcon_h1.py | function | set_gguf_parameters | 97 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | class | GemmaModel | 17 | class GemmaModel(TextModel) |
| app/utils/conversion/gemma.py | function | set_vocab | 20 | def set_vocab(self) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 36 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | filter_tensors | 51 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/gemma.py | function | modify_tensors | 62 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | Gemma2Model | 71 | class Gemma2Model(TextModel) |
| app/utils/conversion/gemma.py | function | set_vocab | 74 | def set_vocab(self) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 79 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | filter_tensors | 101 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/gemma.py | function | modify_tensors | 112 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | Gemma3Model | 121 | class Gemma3Model(TextModel) |
| app/utils/conversion/gemma.py | function | norm_shift | 124 | def norm_shift(self, name: str) -> float |
| app/utils/conversion/gemma.py | function | set_vocab | 127 | def set_vocab(self) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 134 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | modify_tensors | 153 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | EmbeddingGemma | 177 | class EmbeddingGemma(Gemma3Model) |
| app/utils/conversion/gemma.py | function | __init__ | 182 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/gemma.py | function | generate_extra_tensors | 207 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | function | _get_dense_prefix | 222 | def _get_dense_prefix(module_path) -> str |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 227 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | class | Gemma3VisionModel | 251 | class Gemma3VisionModel(MmprojModel) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 252 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | tensor_force_quant | 270 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/gemma.py | function | filter_tensors | 279 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/gemma.py | function | modify_tensors | 293 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | ConformerAudioModel | 304 | class ConformerAudioModel(MmprojModel) |
| app/utils/conversion/gemma.py | function | is_audio_tensor | 308 | def is_audio_tensor(name: str) |
| app/utils/conversion/gemma.py | function | tensor_force_quant | 311 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/gemma.py | function | modify_tensors | 317 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | Gemma3nVisionAudioModel | 355 | class Gemma3nVisionAudioModel(ConformerAudioModel) |
| app/utils/conversion/gemma.py | function | __init__ | 386 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 413 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | tensor_force_quant | 426 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/gemma.py | function | custom_map | 434 | def custom_map(self, name: str) -> str |
| app/utils/conversion/gemma.py | function | modify_tensors | 447 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | Gemma3NModel | 474 | class Gemma3NModel(Gemma3Model) |
| app/utils/conversion/gemma.py | function | __init__ | 480 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/gemma.py | function | norm_shift | 494 | def norm_shift(self, name: str) -> float |
| app/utils/conversion/gemma.py | function | set_vocab | 498 | def set_vocab(self) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 518 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | _stack_matrices | 537 | def _stack_matrices(self, matrices: list[Tensor]) -> Tensor \| None |
| app/utils/conversion/gemma.py | function | filter_tensors | 545 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/gemma.py | function | modify_tensors | 553 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | Gemma4Model | 618 | class Gemma4Model(Gemma3Model) |
| app/utils/conversion/gemma.py | function | norm_shift | 621 | def norm_shift(self, name: str) -> float |
| app/utils/conversion/gemma.py | function | set_vocab | 625 | def set_vocab(self) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 655 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | generate_extra_tensors | 702 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | function | _generate_nvfp4_tensors | 719 | def _generate_nvfp4_tensors(self) |
| app/utils/conversion/gemma.py | function | filter_tensors | 744 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/gemma.py | function | modify_tensors | 754 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gemma.py | class | Gemma4VisionAudioModel | 769 | class Gemma4VisionAudioModel(MmprojModel) |
| app/utils/conversion/gemma.py | function | __init__ | 773 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/gemma.py | function | set_gguf_parameters | 785 | def set_gguf_parameters(self) |
| app/utils/conversion/gemma.py | function | is_audio_tensor | 799 | def is_audio_tensor(self, name: str) -> bool |
| app/utils/conversion/gemma.py | function | tensor_force_quant | 802 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/gemma.py | function | modify_tensors | 810 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/glm.py | class | Glm4Model | 16 | class Glm4Model(TextModel) |
| app/utils/conversion/glm.py | function | __init__ | 21 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/glm.py | function | set_vocab | 28 | def set_vocab(self) |
| app/utils/conversion/glm.py | function | set_gguf_parameters | 44 | def set_gguf_parameters(self) |
| app/utils/conversion/glm.py | function | normal_to_neox | 51 | def normal_to_neox(weights: Tensor, n_head: int, n_head_kv: int, head_dim: int, partial_rotary_factor: float) -> Tensor |
| app/utils/conversion/glm.py | function | modify_tensors | 72 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/glm.py | class | GlmOCRModel | 87 | class GlmOCRModel(Glm4Model) |
| app/utils/conversion/glm.py | function | __init__ | 94 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/glm.py | function | set_gguf_parameters | 100 | def set_gguf_parameters(self) |
| app/utils/conversion/glm.py | class | Glm4MoeModel | 108 | class Glm4MoeModel(TextModel) |
| app/utils/conversion/glm.py | function | __init__ | 111 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/glm.py | function | set_vocab | 117 | def set_vocab(self) |
| app/utils/conversion/glm.py | function | set_gguf_parameters | 120 | def set_gguf_parameters(self) |
| app/utils/conversion/glm.py | function | modify_tensors | 158 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/glm.py | function | prepare_tensors | 195 | def prepare_tensors(self) |
| app/utils/conversion/glm.py | class | Glm4MoeLiteModel | 205 | class Glm4MoeLiteModel(DeepseekV2Model) |
| app/utils/conversion/glm.py | function | set_vocab | 208 | def set_vocab(self) |
| app/utils/conversion/glm.py | class | GlmMoeDsaModel | 213 | class GlmMoeDsaModel(DeepseekV2Model) |
| app/utils/conversion/glm.py | function | __init__ | 217 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/glm.py | function | set_vocab | 222 | def set_vocab(self) |
| app/utils/conversion/glm.py | function | set_gguf_parameters | 225 | def set_gguf_parameters(self) |
| app/utils/conversion/glm.py | class | SolarOpenModel | 243 | class SolarOpenModel(Glm4MoeModel) |
| app/utils/conversion/glm.py | function | set_vocab | 246 | def set_vocab(self) |
| app/utils/conversion/gpt2.py | class | GPT2Model | 14 | class GPT2Model(TextModel) |
| app/utils/conversion/gpt2.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| app/utils/conversion/gpt2.py | function | modify_tensors | 26 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gpt2.py | class | RuGPT3XLModel | 41 | class RuGPT3XLModel(TextModel) |
| app/utils/conversion/gpt2.py | function | modify_tensors | 46 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gpt2.py | function | prepare_tensors | 71 | def prepare_tensors(self) |
| app/utils/conversion/gpt_oss.py | class | GptOssModel | 14 | class GptOssModel(TextModel) |
| app/utils/conversion/gpt_oss.py | function | dequant_model | 18 | def dequant_model(self) |
| app/utils/conversion/gpt_oss.py | function | transform_nibble_layout | 23 | def transform_nibble_layout(self, tensor) |
| app/utils/conversion/gpt_oss.py | function | repack_mxfp4 | 48 | def repack_mxfp4(self, new_name: str, blocks: Tensor, scales: Tensor) |
| app/utils/conversion/gpt_oss.py | function | generate_extra_tensors | 63 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gpt_oss.py | function | filter_tensors | 84 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/gpt_oss.py | function | modify_tensors | 92 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/gpt_oss.py | function | set_vocab | 124 | def set_vocab(self) |
| app/utils/conversion/gpt_oss.py | function | set_gguf_parameters | 127 | def set_gguf_parameters(self) |
| app/utils/conversion/gptneox.py | class | GPTNeoXModel | 16 | class GPTNeoXModel(TextModel) |
| app/utils/conversion/gptneox.py | function | set_gguf_parameters | 19 | def set_gguf_parameters(self) |
| app/utils/conversion/gptneox.py | function | modify_tensors | 31 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/granite.py | class | GraniteModel | 17 | class GraniteModel(LlamaModel) |
| app/utils/conversion/granite.py | function | set_gguf_parameters | 21 | def set_gguf_parameters(self) |
| app/utils/conversion/granite.py | function | filter_tensors | 50 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/granite.py | class | GraniteMoeModel | 58 | class GraniteMoeModel(GraniteModel) |
| app/utils/conversion/granite.py | function | set_gguf_parameters | 62 | def set_gguf_parameters(self) |
| app/utils/conversion/granite.py | function | modify_tensors | 71 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/granite.py | class | GraniteHybridModel | 108 | class GraniteHybridModel(Mamba2Model, GraniteMoeModel) |
| app/utils/conversion/granite.py | function | __init__ | 114 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/granite.py | function | get_attn_layers | 153 | def get_attn_layers(self) |
| app/utils/conversion/granite.py | function | find_hparam | 174 | def find_hparam(self, keys: Iterable[str], *args, **kwargs) -> Any |
| app/utils/conversion/granite.py | function | modify_tensors | 184 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/granite.py | function | set_gguf_parameters | 201 | def set_gguf_parameters(self) |
| app/utils/conversion/granite.py | function | set_vocab | 243 | def set_vocab(self) |
| app/utils/conversion/granite.py | class | GraniteSpeechMmprojModel | 249 | class GraniteSpeechMmprojModel(MmprojModel) |
| app/utils/conversion/granite.py | function | get_audio_config | 255 | def get_audio_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/granite.py | function | set_gguf_parameters | 258 | def set_gguf_parameters(self) |
| app/utils/conversion/granite.py | function | tensor_force_quant | 280 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/granite.py | function | filter_tensors | 287 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/granite.py | function | modify_tensors | 293 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/grok.py | class | GrokModel | 16 | class GrokModel(TextModel) |
| app/utils/conversion/grok.py | function | set_vocab | 19 | def set_vocab(self) |
| app/utils/conversion/grok.py | function | __init__ | 30 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/grok.py | function | set_gguf_parameters | 33 | def set_gguf_parameters(self) |
| app/utils/conversion/grok.py | function | modify_tensors | 67 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/grovemoe.py | class | GroveMoeModel | 14 | class GroveMoeModel(TextModel) |
| app/utils/conversion/grovemoe.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| app/utils/conversion/grovemoe.py | function | modify_tensors | 32 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/grovemoe.py | function | prepare_tensors | 95 | def prepare_tensors(self) |
| app/utils/conversion/hunyuan.py | class | HunYuanMoEModel | 19 | class HunYuanMoEModel(TextModel) |
| app/utils/conversion/hunyuan.py | function | set_vocab | 22 | def set_vocab(self) |
| app/utils/conversion/hunyuan.py | function | set_gguf_parameters | 73 | def set_gguf_parameters(self) |
| app/utils/conversion/hunyuan.py | function | modify_tensors | 112 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/hunyuan.py | function | prepare_tensors | 147 | def prepare_tensors(self) |
| app/utils/conversion/hunyuan.py | class | HunYuanModel | 156 | class HunYuanModel(TextModel) |
| app/utils/conversion/hunyuan.py | function | _get_eod_token_id | 159 | def _get_eod_token_id(self) -> int \| None |
| app/utils/conversion/hunyuan.py | function | _get_eot_token_id | 163 | def _get_eot_token_id(self) -> int \| None |
| app/utils/conversion/hunyuan.py | function | _fix_special_tokens | 175 | def _fix_special_tokens(self) |
| app/utils/conversion/hunyuan.py | function | set_vocab | 184 | def set_vocab(self) |
| app/utils/conversion/hunyuan.py | function | set_gguf_parameters | 253 | def set_gguf_parameters(self) |
| app/utils/conversion/hunyuan.py | function | modify_tensors | 282 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/hunyuan.py | class | HunyuanVLVisionModel | 292 | class HunyuanVLVisionModel(MmprojModel) |
| app/utils/conversion/hunyuan.py | function | __init__ | 293 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/hunyuan.py | function | set_gguf_parameters | 300 | def set_gguf_parameters(self) |
| app/utils/conversion/hunyuan.py | function | filter_tensors | 312 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/hunyuan.py | function | modify_tensors | 320 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/hunyuan.py | function | tensor_force_quant | 326 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/hunyuan.py | class | HunyuanVLTextModel | 335 | class HunyuanVLTextModel(HunYuanModel) |
| app/utils/conversion/hunyuan.py | function | __init__ | 338 | def __init__(self, dir_model: Path, *args, **kwargs) |
| app/utils/conversion/hunyuan.py | function | set_gguf_parameters | 341 | def set_gguf_parameters(self) |
| app/utils/conversion/internlm.py | class | InternLM2Model | 17 | class InternLM2Model(TextModel) |
| app/utils/conversion/internlm.py | function | set_vocab | 20 | def set_vocab(self) |
| app/utils/conversion/internlm.py | function | modify_tensors | 146 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/internlm.py | class | InternLM3Model | 173 | class InternLM3Model(TextModel) |
| app/utils/conversion/internlm.py | function | set_vocab | 176 | def set_vocab(self) |
| app/utils/conversion/internlm.py | function | set_gguf_parameters | 206 | def set_gguf_parameters(self) |
| app/utils/conversion/internlm.py | function | filter_tensors | 216 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/internlm.py | function | modify_tensors | 225 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/internvl.py | class | InternVisionModel | 12 | class InternVisionModel(MmprojModel) |
| app/utils/conversion/internvl.py | function | __init__ | 17 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/internvl.py | function | set_gguf_parameters | 23 | def set_gguf_parameters(self) |
| app/utils/conversion/internvl.py | function | tensor_force_quant | 51 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/internvl.py | function | filter_tensors | 57 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/internvl.py | function | modify_tensors | 82 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/jais.py | class | Jais2Model | 14 | class Jais2Model(TextModel) |
| app/utils/conversion/jais.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| app/utils/conversion/jais.py | class | JaisModel | 25 | class JaisModel(TextModel) |
| app/utils/conversion/jais.py | function | __init__ | 28 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/jais.py | function | set_vocab | 56 | def set_vocab(self) |
| app/utils/conversion/jais.py | function | set_gguf_parameters | 59 | def set_gguf_parameters(self) |
| app/utils/conversion/jais.py | function | filter_tensors | 69 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/jais.py | function | modify_tensors | 78 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/jais.py | function | prepare_tensors | 102 | def prepare_tensors(self) |
| app/utils/conversion/jamba.py | class | JambaModel | 14 | class JambaModel(TextModel) |
| app/utils/conversion/jamba.py | function | set_vocab | 17 | def set_vocab(self) |
| app/utils/conversion/jamba.py | function | set_gguf_parameters | 24 | def set_gguf_parameters(self) |
| app/utils/conversion/jamba.py | function | modify_tensors | 58 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/jamba.py | function | prepare_tensors | 112 | def prepare_tensors(self) |
| app/utils/conversion/januspro.py | class | JanusProModel | 14 | class JanusProModel(LlamaModel) |
| app/utils/conversion/januspro.py | function | filter_tensors | 18 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/januspro.py | class | JanusProVisionModel | 37 | class JanusProVisionModel(MmprojModel) |
| app/utils/conversion/januspro.py | function | __init__ | 38 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/januspro.py | function | set_gguf_parameters | 47 | def set_gguf_parameters(self) |
| app/utils/conversion/januspro.py | function | _map_aligner_tensor | 61 | def _map_aligner_tensor(self, data_torch: Tensor, name: str) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/januspro.py | function | filter_tensors | 86 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/januspro.py | function | modify_tensors | 105 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/kimi_linear.py | class | KimiLinearModel | 16 | class KimiLinearModel(TextModel) |
| app/utils/conversion/kimi_linear.py | function | set_vocab | 22 | def set_vocab(self) |
| app/utils/conversion/kimi_linear.py | function | set_gguf_parameters | 77 | def set_gguf_parameters(self) |
| app/utils/conversion/kimi_linear.py | function | prepare_tensors | 143 | def prepare_tensors(self) |
| app/utils/conversion/kimi_linear.py | function | modify_tensors | 150 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/kimivl.py | class | KimiVLModel | 14 | class KimiVLModel(MmprojModel) |
| app/utils/conversion/kimivl.py | function | __init__ | 15 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/kimivl.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/kimivl.py | function | filter_tensors | 30 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/kimivl.py | function | modify_tensors | 40 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/kimivl.py | class | KimiK25Model | 55 | class KimiK25Model(MmprojModel) |
| app/utils/conversion/kimivl.py | function | __init__ | 58 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/kimivl.py | function | set_gguf_parameters | 71 | def set_gguf_parameters(self) |
| app/utils/conversion/kimivl.py | function | permute | 100 | def permute(weights: Tensor, n_head: int) -> Tensor |
| app/utils/conversion/kimivl.py | function | filter_tensors | 108 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/kimivl.py | function | modify_tensors | 119 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/lfm2.py | class | LFM2Model | 16 | class LFM2Model(TextModel) |
| app/utils/conversion/lfm2.py | function | _add_feed_forward_length | 19 | def _add_feed_forward_length(self) |
| app/utils/conversion/lfm2.py | function | set_gguf_parameters | 34 | def set_gguf_parameters(self) |
| app/utils/conversion/lfm2.py | function | filter_tensors | 48 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/lfm2.py | function | modify_tensors | 59 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/lfm2.py | class | LFM2ColBertModel | 68 | class LFM2ColBertModel(LFM2Model) |
| app/utils/conversion/lfm2.py | function | modify_tensors | 72 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/lfm2.py | function | generate_extra_tensors | 78 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/lfm2.py | class | LFM2MoeModel | 89 | class LFM2MoeModel(TextModel) |
| app/utils/conversion/lfm2.py | function | set_gguf_parameters | 92 | def set_gguf_parameters(self) |
| app/utils/conversion/lfm2.py | function | filter_tensors | 112 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/lfm2.py | function | modify_tensors | 120 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/lfm2.py | function | prepare_tensors | 156 | def prepare_tensors(self) |
| app/utils/conversion/lfm2.py | class | LFM2VLModel | 162 | class LFM2VLModel(MmprojModel) |
| app/utils/conversion/lfm2.py | function | __init__ | 163 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/lfm2.py | function | set_gguf_parameters | 169 | def set_gguf_parameters(self) |
| app/utils/conversion/lfm2.py | function | filter_tensors | 180 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/lfm2.py | function | modify_tensors | 188 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/lfm2.py | class | LFM2AudioModel | 196 | class LFM2AudioModel(ConformerAudioModel) |
| app/utils/conversion/lfm2.py | function | get_audio_config | 201 | def get_audio_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/lfm2.py | function | set_gguf_parameters | 204 | def set_gguf_parameters(self) |
| app/utils/conversion/lfm2.py | function | filter_tensors | 215 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/lfm2.py | class | LFM25AudioTokenizer | 234 | class LFM25AudioTokenizer(LFM2Model) |
| app/utils/conversion/lfm2.py | function | set_vocab | 237 | def set_vocab(self) |
| app/utils/conversion/lfm2.py | function | set_gguf_parameters | 240 | def set_gguf_parameters(self) |
| app/utils/conversion/lfm2.py | function | filter_tensors | 246 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/lighton_ocr.py | class | LightOnOCRVisionModel | 14 | class LightOnOCRVisionModel(LlavaVisionModel) |
| app/utils/conversion/lighton_ocr.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/lighton_ocr.py | function | filter_tensors | 23 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/llada.py | class | LLaDAModel | 14 | class LLaDAModel(TextModel) |
| app/utils/conversion/llada.py | function | get_vocab_base | 18 | def get_vocab_base(self) -> tuple[list[str], list[int], str] |
| app/utils/conversion/llada.py | function | set_vocab | 55 | def set_vocab(self) |
| app/utils/conversion/llada.py | function | set_gguf_parameters | 61 | def set_gguf_parameters(self) |
| app/utils/conversion/llada.py | function | permute | 94 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| app/utils/conversion/llada.py | function | modify_tensors | 101 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/llada.py | class | LLaDAMoEModel | 117 | class LLaDAMoEModel(TextModel) |
| app/utils/conversion/llada.py | function | set_gguf_parameters | 120 | def set_gguf_parameters(self) |
| app/utils/conversion/llada.py | function | modify_tensors | 132 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/llada.py | function | prepare_tensors | 165 | def prepare_tensors(self) |
| app/utils/conversion/llama.py | class | LlamaModel | 26 | class LlamaModel(TextModel) |
| app/utils/conversion/llama.py | function | __init__ | 30 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/llama.py | function | set_vocab | 42 | def set_vocab(self) |
| app/utils/conversion/llama.py | function | set_gguf_parameters | 88 | def set_gguf_parameters(self) |
| app/utils/conversion/llama.py | function | permute | 100 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| app/utils/conversion/llama.py | function | _repack_nvfp4 | 107 | def _repack_nvfp4(self, name: str, weight: Tensor, scale: Tensor, scale2: Tensor, input_scale: Tensor) |
| app/utils/conversion/llama.py | function | filter_tensors | 124 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/llama.py | function | modify_tensors | 132 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/llama.py | function | generate_extra_tensors | 177 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/llama.py | function | prepare_tensors | 207 | def prepare_tensors(self) |
| app/utils/conversion/llama.py | class | ArceeModel | 218 | class ArceeModel(LlamaModel) |
| app/utils/conversion/llama.py | function | set_gguf_parameters | 221 | def set_gguf_parameters(self) |
| app/utils/conversion/llama.py | class | Llama4Model | 230 | class Llama4Model(LlamaModel) |
| app/utils/conversion/llama.py | function | __init__ | 234 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/llama.py | function | set_vocab | 240 | def set_vocab(self) |
| app/utils/conversion/llama.py | function | set_gguf_parameters | 243 | def set_gguf_parameters(self) |
| app/utils/conversion/llama.py | function | modify_tensors | 252 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| app/utils/conversion/llama.py | class | LlamaEmbedNemotronModel | 271 | class LlamaEmbedNemotronModel(LlamaModel) |
| app/utils/conversion/llama.py | class | SmolLM3Model | 276 | class SmolLM3Model(LlamaModel) |
| app/utils/conversion/llama.py | class | ApertusModel | 281 | class ApertusModel(LlamaModel) |
| app/utils/conversion/llama.py | function | modify_tensors | 290 | def modify_tensors(self, data_torch, name, bid) |
| app/utils/conversion/llama4.py | class | Llama4VisionModel | 12 | class Llama4VisionModel(MmprojModel) |
| app/utils/conversion/llama4.py | function | set_gguf_parameters | 13 | def set_gguf_parameters(self) |
| app/utils/conversion/llama4.py | function | filter_tensors | 22 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/llama4.py | function | modify_tensors | 33 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/llava.py | class | LlavaVisionModel | 19 | class LlavaVisionModel(MmprojModel) |
| app/utils/conversion/llava.py | function | __init__ | 23 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/llava.py | function | get_token_id | 45 | def get_token_id(self, token: str) -> int |
| app/utils/conversion/llava.py | function | get_mistral_token_id | 60 | def get_mistral_token_id(self, token: str) -> int |
| app/utils/conversion/llava.py | function | set_gguf_parameters | 78 | def set_gguf_parameters(self) |
| app/utils/conversion/llava.py | function | modify_tensors | 97 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/maincoder.py | class | MaincoderModel | 7 | class MaincoderModel(TextModel) |
| app/utils/conversion/maincoder.py | function | set_gguf_parameters | 10 | def set_gguf_parameters(self) |
| app/utils/conversion/mamba.py | class | MambaModel | 17 | class MambaModel(TextModel) |
| app/utils/conversion/mamba.py | function | __init__ | 20 | def __init__(self, dir_model: Path, *args, **kwargs) |
| app/utils/conversion/mamba.py | function | set_vocab | 28 | def set_vocab(self) |
| app/utils/conversion/mamba.py | function | set_gguf_parameters | 45 | def set_gguf_parameters(self) |
| app/utils/conversion/mamba.py | function | modify_tensors | 77 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/mamba.py | class | Mamba2Model | 103 | class Mamba2Model(TextModel) |
| app/utils/conversion/mamba.py | function | __init__ | 106 | def __init__(self, dir_model: Path, *args, **kwargs) |
| app/utils/conversion/mamba.py | function | set_vocab | 120 | def set_vocab(self) |
| app/utils/conversion/mamba.py | function | set_gguf_parameters | 140 | def set_gguf_parameters(self) |
| app/utils/conversion/mamba.py | function | filter_tensors | 168 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/mamba.py | function | modify_tensors | 180 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/mimo.py | class | MimoV2Model | 16 | class MimoV2Model(TextModel) |
| app/utils/conversion/mimo.py | function | __init__ | 23 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/mimo.py | function | _tp_aware_qkv_dequant | 30 | def _tp_aware_qkv_dequant(weight: Tensor, scale_inv: Tensor, n_q: int, n_kv: int, hd: int, vhd: int, bs: int = 128) -> Tensor |
| app/utils/conversion/mimo.py | function | dequant_model | 95 | def dequant_model(self) |
| app/utils/conversion/mimo.py | function | set_gguf_parameters | 135 | def set_gguf_parameters(self) |
| app/utils/conversion/mimo.py | function | filter_tensors | 171 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/mimo.py | function | modify_tensors | 179 | def modify_tensors(self, data_torch, name, bid) |
| app/utils/conversion/mimo.py | function | prepare_tensors | 221 | def prepare_tensors(self) |
| app/utils/conversion/mimo.py | class | MiMoV2VisionModel | 232 | class MiMoV2VisionModel(MmprojModel) |
| app/utils/conversion/mimo.py | function | __init__ | 233 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/mimo.py | function | set_gguf_parameters | 256 | def set_gguf_parameters(self) |
| app/utils/conversion/mimo.py | function | tensor_force_quant | 269 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/mimo.py | function | filter_tensors | 277 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/mimo.py | function | modify_tensors | 283 | def modify_tensors(self, data_torch, name, bid) |
| app/utils/conversion/minicpm.py | class | MiniCPMModel | 17 | class MiniCPMModel(TextModel) |
| app/utils/conversion/minicpm.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/minicpm.py | function | generate_extra_tensors | 32 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/minicpm.py | function | set_vocab | 49 | def set_vocab(self) |
| app/utils/conversion/minicpm.py | function | modify_tensors | 52 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/minicpm.py | class | MiniCPM3Model | 66 | class MiniCPM3Model(TextModel) |
| app/utils/conversion/minicpm.py | function | set_gguf_parameters | 69 | def set_gguf_parameters(self) |
| app/utils/conversion/minicpm.py | function | generate_extra_tensors | 87 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/minicpm.py | function | set_vocab | 104 | def set_vocab(self) |
| app/utils/conversion/minicpm.py | function | _reverse_hf_permute | 107 | def _reverse_hf_permute(self, weights: Tensor, n_head: int, n_kv_head: int \| None = None) -> Tensor |
| app/utils/conversion/minicpm.py | class | MiniCPMV4_6TextModel | 124 | class MiniCPMV4_6TextModel(Qwen3_5TextModel) |
| app/utils/conversion/minicpm.py | function | filter_tensors | 128 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/minicpm.py | class | MiniCPMV4_6VisionModel | 141 | class MiniCPMV4_6VisionModel(MmprojModel) |
| app/utils/conversion/minicpm.py | function | __init__ | 142 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/minicpm.py | function | set_gguf_parameters | 155 | def set_gguf_parameters(self) |
| app/utils/conversion/minicpm.py | function | filter_tensors | 177 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/minimax.py | class | MiniMaxM2Model | 14 | class MiniMaxM2Model(TextModel) |
| app/utils/conversion/minimax.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/minimax.py | function | modify_tensors | 24 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| app/utils/conversion/mistral.py | class | MistralModel | 24 | class MistralModel(LlamaModel) |
| app/utils/conversion/mistral.py | function | __init__ | 31 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/mistral.py | function | dequant_model | 41 | def dequant_model(self) |
| app/utils/conversion/mistral.py | function | get_community_chat_template | 54 | def get_community_chat_template(vocab: MistralVocab, templates_dir: Path, is_mistral_format: bool) |
| app/utils/conversion/mistral.py | function | set_gguf_parameters | 92 | def set_gguf_parameters(self) |
| app/utils/conversion/mistral.py | function | set_mistral_config | 97 | def set_mistral_config(gguf_writer: gguf.GGUFWriter, hparams: dict) |
| app/utils/conversion/mistral.py | class | MistralMoeModel | 112 | class MistralMoeModel(DeepseekV2Model) |
| app/utils/conversion/mistral.py | function | __init__ | 118 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/mistral.py | function | set_vocab | 169 | def set_vocab(self) |
| app/utils/conversion/mistral.py | function | set_gguf_parameters | 172 | def set_gguf_parameters(self) |
| app/utils/conversion/mistral.py | function | filter_tensors | 184 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/mistral3.py | class | Mistral3Model | 18 | class Mistral3Model(TextModel) |
| app/utils/conversion/mistral3.py | class | Ministral3Model | 19 | class Ministral3Model(LlamaModel) |
| app/utils/conversion/mistral3.py | function | set_gguf_parameters | 22 | def set_gguf_parameters(self) |
| app/utils/conversion/mistral3.py | class | Mistral4Model | 31 | class Mistral4Model(DeepseekV2Model) |
| app/utils/conversion/mistral3.py | function | modify_tensors | 36 | def modify_tensors(self, data_torch, name, bid) |
| app/utils/conversion/mistral3.py | function | __init__ | 44 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/mistral3.py | function | set_vocab | 51 | def set_vocab(self) |
| app/utils/conversion/mistral3.py | function | set_gguf_parameters | 54 | def set_gguf_parameters(self) |
| app/utils/conversion/mistral3.py | function | modify_tensors | 57 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| app/utils/conversion/mistral3.py | function | prepare_tensors | 60 | def prepare_tensors(self) |
| app/utils/conversion/mistral3.py | function | write_vocab | 63 | def write_vocab(self) |
| app/utils/conversion/mistral3.py | function | write | 66 | def write(self) |
| app/utils/conversion/mpt.py | class | MPTModel | 12 | class MPTModel(TextModel) |
| app/utils/conversion/mpt.py | function | set_vocab | 15 | def set_vocab(self) |
| app/utils/conversion/mpt.py | function | set_gguf_parameters | 26 | def set_gguf_parameters(self) |
| app/utils/conversion/mpt.py | function | modify_tensors | 42 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/nemotron.py | class | NemotronNanoV2VLModel | 19 | class NemotronNanoV2VLModel(MmprojModel) |
| app/utils/conversion/nemotron.py | function | get_vision_config | 26 | def get_vision_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/nemotron.py | function | set_gguf_parameters | 42 | def set_gguf_parameters(self) |
| app/utils/conversion/nemotron.py | function | tensor_force_quant | 56 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/nemotron.py | function | filter_tensors | 62 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/nemotron.py | function | modify_tensors | 81 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/nemotron.py | class | NemotronModel | 111 | class NemotronModel(TextModel) |
| app/utils/conversion/nemotron.py | function | set_vocab | 114 | def set_vocab(self) |
| app/utils/conversion/nemotron.py | function | set_gguf_parameters | 119 | def set_gguf_parameters(self) |
| app/utils/conversion/nemotron.py | function | modify_tensors | 140 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/nemotron.py | class | NemotronHModel | 152 | class NemotronHModel(GraniteHybridModel) |
| app/utils/conversion/nemotron.py | function | __init__ | 157 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/nemotron.py | function | get_attn_layers | 195 | def get_attn_layers(self) |
| app/utils/conversion/nemotron.py | function | set_gguf_parameters | 205 | def set_gguf_parameters(self) |
| app/utils/conversion/nemotron.py | function | set_vocab | 243 | def set_vocab(self) |
| app/utils/conversion/nemotron.py | function | modify_tensors | 309 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/nemotron.py | function | prepare_tensors | 377 | def prepare_tensors(self) |
| app/utils/conversion/olmo.py | class | OlmoModel | 17 | class OlmoModel(TextModel) |
| app/utils/conversion/olmo.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/olmo.py | function | modify_tensors | 29 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/olmo.py | class | SeedOssModel | 42 | class SeedOssModel(TextModel) |
| app/utils/conversion/olmo.py | class | Olmo2Model | 48 | class Olmo2Model(TextModel) |
| app/utils/conversion/olmo.py | function | set_gguf_parameters | 51 | def set_gguf_parameters(self) |
| app/utils/conversion/olmo.py | class | OlmoeModel | 70 | class OlmoeModel(TextModel) |
| app/utils/conversion/olmo.py | function | set_gguf_parameters | 73 | def set_gguf_parameters(self) |
| app/utils/conversion/olmo.py | function | modify_tensors | 80 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/olmo.py | function | prepare_tensors | 113 | def prepare_tensors(self) |
| app/utils/conversion/openelm.py | class | OpenELMModel | 12 | class OpenELMModel(TextModel) |
| app/utils/conversion/openelm.py | function | _make_divisible | 16 | def _make_divisible(v: float \| int, divisor: int) -> int |
| app/utils/conversion/openelm.py | function | __init__ | 24 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/openelm.py | function | set_vocab | 40 | def set_vocab(self) |
| app/utils/conversion/openelm.py | function | set_gguf_parameters | 46 | def set_gguf_parameters(self) |
| app/utils/conversion/openelm.py | function | find_hparam | 68 | def find_hparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| app/utils/conversion/openelm.py | function | modify_tensors | 74 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/orion.py | class | OrionModel | 7 | class OrionModel(TextModel) |
| app/utils/conversion/orion.py | function | set_vocab | 10 | def set_vocab(self) |
| app/utils/conversion/orion.py | function | set_gguf_parameters | 13 | def set_gguf_parameters(self) |
| app/utils/conversion/pangu.py | class | PanguEmbeddedModel | 14 | class PanguEmbeddedModel(TextModel) |
| app/utils/conversion/pangu.py | function | set_vocab | 17 | def set_vocab(self) |
| app/utils/conversion/pangu.py | function | set_gguf_parameters | 27 | def set_gguf_parameters(self) |
| app/utils/conversion/pangu.py | function | modify_tensors | 41 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/phi.py | class | Phi2Model | 17 | class Phi2Model(TextModel) |
| app/utils/conversion/phi.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/phi.py | class | Phi3MiniModel | 39 | class Phi3MiniModel(TextModel) |
| app/utils/conversion/phi.py | function | set_vocab | 42 | def set_vocab(self) |
| app/utils/conversion/phi.py | function | set_gguf_parameters | 146 | def set_gguf_parameters(self) |
| app/utils/conversion/phi.py | function | generate_extra_tensors | 173 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/phi.py | class | Phi4VisionMmprojModel | 215 | class Phi4VisionMmprojModel(MmprojModel) |
| app/utils/conversion/phi.py | function | __init__ | 216 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/phi.py | function | set_gguf_parameters | 272 | def set_gguf_parameters(self) |
| app/utils/conversion/phi.py | function | filter_tensors | 283 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/phi.py | function | modify_tensors | 299 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/phi.py | class | PhiMoeModel | 341 | class PhiMoeModel(Phi3MiniModel) |
| app/utils/conversion/phi.py | function | set_gguf_parameters | 346 | def set_gguf_parameters(self) |
| app/utils/conversion/phi.py | function | modify_tensors | 351 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/phi.py | function | prepare_tensors | 383 | def prepare_tensors(self) |
| app/utils/conversion/pixtral.py | class | PixtralModel | 10 | class PixtralModel(LlavaVisionModel) |
| app/utils/conversion/pixtral.py | function | set_gguf_parameters | 15 | def set_gguf_parameters(self) |
| app/utils/conversion/pixtral.py | function | map_tensor_name | 32 | def map_tensor_name(self, name: str, try_suffixes: Sequence[str] = (".weight", ".bias")) -> str |
| app/utils/conversion/plamo.py | class | PlamoModel | 16 | class PlamoModel(TextModel) |
| app/utils/conversion/plamo.py | function | set_vocab | 19 | def set_vocab(self) |
| app/utils/conversion/plamo.py | function | set_gguf_parameters | 22 | def set_gguf_parameters(self) |
| app/utils/conversion/plamo.py | function | shuffle_attn_q_weight | 34 | def shuffle_attn_q_weight(self, data_torch) |
| app/utils/conversion/plamo.py | function | shuffle_attn_output_weight | 41 | def shuffle_attn_output_weight(self, data_torch) |
| app/utils/conversion/plamo.py | function | modify_tensors | 48 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/plamo.py | class | Plamo2Model | 61 | class Plamo2Model(TextModel) |
| app/utils/conversion/plamo.py | function | set_vocab | 64 | def set_vocab(self) |
| app/utils/conversion/plamo.py | function | set_gguf_parameters | 67 | def set_gguf_parameters(self) |
| app/utils/conversion/plamo.py | function | modify_tensors | 117 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/plamo.py | class | Plamo3Model | 150 | class Plamo3Model(TextModel) |
| app/utils/conversion/plamo.py | function | set_vocab | 153 | def set_vocab(self) |
| app/utils/conversion/plamo.py | function | set_gguf_parameters | 173 | def set_gguf_parameters(self) |
| app/utils/conversion/plamo.py | function | modify_tensors | 180 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/plm.py | class | PLMModel | 7 | class PLMModel(TextModel) |
| app/utils/conversion/plm.py | function | set_vocab | 10 | def set_vocab(self) |
| app/utils/conversion/plm.py | function | set_gguf_parameters | 13 | def set_gguf_parameters(self) |
| app/utils/conversion/plm.py | function | prepare_tensors | 22 | def prepare_tensors(self) |
| app/utils/conversion/qwen.py | class | QwenModel | 14 | class QwenModel(TextModel) |
| app/utils/conversion/qwen.py | function | token_bytes_to_string | 18 | def token_bytes_to_string(b) |
| app/utils/conversion/qwen.py | function | bpe | 24 | def bpe(mergeable_ranks: dict[bytes, int], token: bytes, max_rank: int \| None = None) -> list[bytes] |
| app/utils/conversion/qwen.py | function | set_vocab | 40 | def set_vocab(self) |
| app/utils/conversion/qwen.py | class | Qwen2Model | 52 | class Qwen2Model(TextModel) |
| app/utils/conversion/qwen.py | function | set_vocab | 55 | def set_vocab(self) |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 61 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | function | modify_tensors | 65 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen.py | class | Qwen2MoeModel | 72 | class Qwen2MoeModel(TextModel) |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 75 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | function | modify_tensors | 86 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen.py | function | prepare_tensors | 143 | def prepare_tensors(self) |
| app/utils/conversion/qwen.py | class | Qwen3Model | 154 | class Qwen3Model(Qwen2Model) |
| app/utils/conversion/qwen.py | function | __init__ | 163 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/qwen.py | function | _is_qwen3_reranker | 173 | def _is_qwen3_reranker(self) -> bool |
| app/utils/conversion/qwen.py | function | set_vocab | 196 | def set_vocab(self) |
| app/utils/conversion/qwen.py | function | _find_rerank_config | 204 | def _find_rerank_config(self) |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 216 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | function | _get_cls_out_tensor | 228 | def _get_cls_out_tensor(self, data_torch: Tensor) -> Tensor |
| app/utils/conversion/qwen.py | function | modify_tensors | 234 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen.py | class | Qwen3MoeModel | 252 | class Qwen3MoeModel(Qwen2MoeModel) |
| app/utils/conversion/qwen.py | function | __init__ | 255 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/qwen.py | function | set_vocab | 260 | def set_vocab(self) |
| app/utils/conversion/qwen.py | class | Qwen3NextModel | 270 | class Qwen3NextModel(Qwen2MoeModel) |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 273 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | function | filter_tensors | 286 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwen.py | function | modify_tensors | 295 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen.py | class | RND1Model | 339 | class RND1Model(Qwen2MoeModel) |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 342 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | class | _LinearAttentionVReorderBase | 353 | class _LinearAttentionVReorderBase(Qwen3NextModel) |
| app/utils/conversion/qwen.py | function | _reorder_v_heads | 367 | def _reorder_v_heads(tensor: Tensor, dim: int, num_k_heads: int, num_v_per_k: int, head_dim: int) -> Tensor |
| app/utils/conversion/qwen.py | function | _transform_nvfp4_weight | 378 | def _transform_nvfp4_weight(self, name: str, weight: Tensor, scale: Tensor) -> tuple[Tensor, Tensor] |
| app/utils/conversion/qwen.py | function | unpack_nibbles | 394 | def unpack_nibbles(qs: Tensor) -> Tensor |
| app/utils/conversion/qwen.py | function | pack_nibbles | 399 | def pack_nibbles(codes: Tensor) -> Tensor |
| app/utils/conversion/qwen.py | function | apply_col_perm | 405 | def apply_col_perm(qs: Tensor, scales: Tensor, col_perm: Tensor) -> tuple[Tensor, Tensor] |
| app/utils/conversion/qwen.py | function | reorder_rows | 430 | def reorder_rows(qs: Tensor, scales: Tensor, head_dim: int) -> tuple[Tensor, Tensor] |
| app/utils/conversion/qwen.py | function | _repack_nvfp4 | 465 | def _repack_nvfp4(self, name: str, weight: Tensor, scale: Tensor, scale2: Tensor, input_scale: Tensor) |
| app/utils/conversion/qwen.py | function | modify_tensors | 469 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen.py | class | _Qwen35MRopeMixin | 521 | class _Qwen35MRopeMixin |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 531 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | class | _Qwen35MtpMixin | 537 | class _Qwen35MtpMixin |
| app/utils/conversion/qwen.py | function | __init__ | 553 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/qwen.py | function | index_tensors | 560 | def index_tensors(self, remote_hf_model_id: str \| None = None) -> dict[str, Callable[[], Tensor]] |
| app/utils/conversion/qwen.py | function | filter_tensors | 567 | def filter_tensors(cls, item) |
| app/utils/conversion/qwen.py | function | set_gguf_parameters | 599 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen.py | function | prepare_metadata | 606 | def prepare_metadata(self, vocab_only: bool) |
| app/utils/conversion/qwen.py | class | Qwen3_5TextModel | 621 | class Qwen3_5TextModel(_Qwen35MtpMixin, _Qwen35MRopeMixin, _LinearAttentionVReorderBase) |
| app/utils/conversion/qwen.py | class | Qwen3_5MoeTextModel | 626 | class Qwen3_5MoeTextModel(_Qwen35MtpMixin, _Qwen35MRopeMixin, _LinearAttentionVReorderBase) |
| app/utils/conversion/qwen3vl.py | class | Qwen3VLVisionModel | 17 | class Qwen3VLVisionModel(MmprojModel) |
| app/utils/conversion/qwen3vl.py | function | __init__ | 18 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 42 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | function | filter_tensors | 62 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwen3vl.py | function | modify_tensors | 81 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen3vl.py | class | Qwen3OmniMmprojModel | 147 | class Qwen3OmniMmprojModel(Qwen3VLVisionModel, Qwen25AudioModel) |
| app/utils/conversion/qwen3vl.py | function | get_vision_config | 151 | def get_vision_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/qwen3vl.py | function | get_audio_config | 157 | def get_audio_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 163 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | function | filter_tensors | 172 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwen3vl.py | function | modify_tensors | 194 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen3vl.py | class | Qwen3ASRMmprojModel | 220 | class Qwen3ASRMmprojModel(Qwen3OmniMmprojModel) |
| app/utils/conversion/qwen3vl.py | class | Glm4VVisionModel | 226 | class Glm4VVisionModel(Qwen3VLVisionModel) |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 227 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | function | modify_tensors | 241 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen3vl.py | class | Qwen3VLTextModel | 249 | class Qwen3VLTextModel(Qwen3Model) |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 252 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | function | filter_tensors | 262 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwen3vl.py | class | Qwen3VLMoeTextModel | 271 | class Qwen3VLMoeTextModel(Qwen3MoeModel) |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 274 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | function | filter_tensors | 281 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwen3vl.py | function | modify_tensors | 288 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwen3vl.py | class | Qwen3OmniMoeTextModel | 320 | class Qwen3OmniMoeTextModel(Qwen3VLMoeTextModel) |
| app/utils/conversion/qwen3vl.py | function | set_vocab | 323 | def set_vocab(self) |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 335 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | class | Qwen3ASRTextModel | 341 | class Qwen3ASRTextModel(Qwen3VLTextModel) |
| app/utils/conversion/qwen3vl.py | function | set_gguf_parameters | 344 | def set_gguf_parameters(self) |
| app/utils/conversion/qwen3vl.py | function | set_vocab | 348 | def set_vocab(self) |
| app/utils/conversion/qwenvl.py | class | Qwen2VLModel | 20 | class Qwen2VLModel(TextModel) |
| app/utils/conversion/qwenvl.py | function | set_gguf_parameters | 23 | def set_gguf_parameters(self) |
| app/utils/conversion/qwenvl.py | function | set_vocab | 26 | def set_vocab(self) |
| app/utils/conversion/qwenvl.py | function | filter_tensors | 33 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwenvl.py | class | Qwen2VLVisionModel | 43 | class Qwen2VLVisionModel(MmprojModel) |
| app/utils/conversion/qwenvl.py | function | __init__ | 44 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/qwenvl.py | function | set_gguf_parameters | 55 | def set_gguf_parameters(self) |
| app/utils/conversion/qwenvl.py | function | tensor_force_quant | 82 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/qwenvl.py | function | filter_tensors | 88 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwenvl.py | function | modify_tensors | 96 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwenvl.py | class | Qwen25AudioModel | 122 | class Qwen25AudioModel(MmprojModel) |
| app/utils/conversion/qwenvl.py | function | __init__ | 125 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/qwenvl.py | function | set_gguf_parameters | 132 | def set_gguf_parameters(self) |
| app/utils/conversion/qwenvl.py | function | generate_extra_tensors | 138 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwenvl.py | function | tensor_force_quant | 150 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/qwenvl.py | function | modify_tensors | 155 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/qwenvl.py | class | Qwen25OmniModel | 164 | class Qwen25OmniModel(Qwen2VLVisionModel, Qwen25AudioModel) |
| app/utils/conversion/qwenvl.py | function | get_vision_config | 168 | def get_vision_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/qwenvl.py | function | get_audio_config | 171 | def get_audio_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/qwenvl.py | function | set_gguf_parameters | 174 | def set_gguf_parameters(self) |
| app/utils/conversion/qwenvl.py | function | filter_tensors | 179 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/qwenvl.py | function | modify_tensors | 195 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/refact.py | class | RefactModel | 12 | class RefactModel(TextModel) |
| app/utils/conversion/refact.py | function | set_vocab | 15 | def set_vocab(self) |
| app/utils/conversion/refact.py | function | set_gguf_parameters | 27 | def set_gguf_parameters(self) |
| app/utils/conversion/refact.py | function | modify_tensors | 45 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/rwkv.py | class | Rwkv6Model | 14 | class Rwkv6Model(TextModel) |
| app/utils/conversion/rwkv.py | function | set_vocab | 17 | def set_vocab(self) |
| app/utils/conversion/rwkv.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| app/utils/conversion/rwkv.py | function | modify_tensors | 46 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/rwkv.py | class | RWKV6Qwen2Model | 86 | class RWKV6Qwen2Model(Rwkv6Model) |
| app/utils/conversion/rwkv.py | function | set_vocab | 89 | def set_vocab(self) |
| app/utils/conversion/rwkv.py | function | set_gguf_parameters | 95 | def set_gguf_parameters(self) |
| app/utils/conversion/rwkv.py | function | modify_tensors | 124 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/rwkv.py | class | Rwkv7Model | 139 | class Rwkv7Model(TextModel) |
| app/utils/conversion/rwkv.py | function | set_vocab | 142 | def set_vocab(self) |
| app/utils/conversion/rwkv.py | function | calc_lora_rank | 145 | def calc_lora_rank(self, hidden_size, exponent, multiplier) |
| app/utils/conversion/rwkv.py | function | set_gguf_parameters | 148 | def set_gguf_parameters(self) |
| app/utils/conversion/rwkv.py | function | filter_tensors | 190 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/rwkv.py | function | modify_tensors | 203 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/rwkv.py | class | ARwkv7Model | 264 | class ARwkv7Model(Rwkv7Model) |
| app/utils/conversion/rwkv.py | function | set_vocab | 267 | def set_vocab(self) |
| app/utils/conversion/rwkv.py | function | set_gguf_parameters | 273 | def set_gguf_parameters(self) |
| app/utils/conversion/sarashina2.py | class | Sarashina2VLTextModel | 15 | class Sarashina2VLTextModel(LlamaModel) |
| app/utils/conversion/sarashina2.py | function | filter_tensors | 19 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/sarashina2.py | class | Sarashina2VLVisionModel | 29 | class Sarashina2VLVisionModel(Qwen2VLVisionModel) |
| app/utils/conversion/sarashina2.py | function | __init__ | 30 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/smallthinker.py | class | SmallThinkerModel | 14 | class SmallThinkerModel(TextModel) |
| app/utils/conversion/smallthinker.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| app/utils/conversion/smallthinker.py | function | modify_tensors | 43 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/smallthinker.py | function | prepare_tensors | 75 | def prepare_tensors(self) |
| app/utils/conversion/smolvlm.py | class | SmolVLMModel | 12 | class SmolVLMModel(MmprojModel) |
| app/utils/conversion/smolvlm.py | function | __init__ | 13 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/smolvlm.py | function | set_gguf_parameters | 22 | def set_gguf_parameters(self) |
| app/utils/conversion/smolvlm.py | function | tensor_force_quant | 33 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/smolvlm.py | function | filter_tensors | 39 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/stablelm.py | class | StableLMModel | 14 | class StableLMModel(TextModel) |
| app/utils/conversion/stablelm.py | function | set_vocab | 17 | def set_vocab(self) |
| app/utils/conversion/stablelm.py | function | set_gguf_parameters | 24 | def set_gguf_parameters(self) |
| app/utils/conversion/stablelm.py | function | modify_tensors | 42 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/stablelm.py | function | _stack_qk_norm | 74 | def _stack_qk_norm(self, bid: int, n_head: int, norms: dict[str, Tensor], layer_name: str = "q_layernorm") |
| app/utils/conversion/stablelm.py | function | prepare_tensors | 87 | def prepare_tensors(self) |
| app/utils/conversion/starcoder.py | class | StarCoderModel | 7 | class StarCoderModel(TextModel) |
| app/utils/conversion/starcoder.py | function | set_gguf_parameters | 10 | def set_gguf_parameters(self) |
| app/utils/conversion/starcoder.py | class | StarCoder2Model | 22 | class StarCoder2Model(TextModel) |
| app/utils/conversion/step3.py | class | Step3VLVisionModel | 19 | class Step3VLVisionModel(MmprojModel) |
| app/utils/conversion/step3.py | function | __init__ | 20 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/step3.py | function | set_gguf_parameters | 33 | def set_gguf_parameters(self) |
| app/utils/conversion/step3.py | function | tensor_force_quant | 50 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/step3.py | function | filter_tensors | 58 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/step3.py | function | modify_tensors | 66 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/step3.py | class | Step3VLTextModel | 94 | class Step3VLTextModel(Qwen3Model) |
| app/utils/conversion/step3.py | class | Step35Model | 99 | class Step35Model(TextModel) |
| app/utils/conversion/step3.py | function | set_gguf_parameters | 102 | def set_gguf_parameters(self) |
| app/utils/conversion/step3.py | function | filter_tensors | 169 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/step3.py | function | modify_tensors | 178 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| app/utils/conversion/step3.py | function | generate_extra_tensors | 193 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/t5.py | class | T5Model | 19 | class T5Model(TextModel) |
| app/utils/conversion/t5.py | function | __init__ | 22 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/t5.py | function | set_vocab | 26 | def set_vocab(self) |
| app/utils/conversion/t5.py | function | set_gguf_parameters | 120 | def set_gguf_parameters(self) |
| app/utils/conversion/t5.py | function | modify_tensors | 139 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/t5.py | class | T5EncoderModel | 156 | class T5EncoderModel(TextModel) |
| app/utils/conversion/t5.py | function | __init__ | 159 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/t5.py | function | set_vocab | 163 | def set_vocab(self) |
| app/utils/conversion/t5.py | function | set_gguf_parameters | 257 | def set_gguf_parameters(self) |
| app/utils/conversion/t5.py | function | modify_tensors | 273 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/talkie.py | class | TalkieModel | 14 | class TalkieModel(TextModel) |
| app/utils/conversion/talkie.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| app/utils/conversion/talkie.py | function | modify_tensors | 22 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ultravox.py | class | UltravoxModel | 12 | class UltravoxModel(TextModel) |
| app/utils/conversion/ultravox.py | function | __init__ | 15 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/ultravox.py | class | GlmASRWhisperEncoderModel | 21 | class GlmASRWhisperEncoderModel(MmprojModel) |
| app/utils/conversion/ultravox.py | function | __init__ | 25 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/ultravox.py | function | set_gguf_parameters | 32 | def set_gguf_parameters(self) |
| app/utils/conversion/ultravox.py | function | tensor_force_quant | 39 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/ultravox.py | function | filter_tensors | 45 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/ultravox.py | function | modify_tensors | 67 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ultravox.py | class | WhisperEncoderModel | 85 | class WhisperEncoderModel(MmprojModel) |
| app/utils/conversion/ultravox.py | function | __init__ | 89 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/ultravox.py | function | set_gguf_parameters | 96 | def set_gguf_parameters(self) |
| app/utils/conversion/ultravox.py | function | tensor_force_quant | 102 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/ultravox.py | function | filter_tensors | 108 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/ultravox.py | function | modify_tensors | 117 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ultravox.py | class | UltravoxWhisperEncoderModel | 126 | class UltravoxWhisperEncoderModel(WhisperEncoderModel) |
| app/utils/conversion/ultravox.py | function | set_gguf_parameters | 130 | def set_gguf_parameters(self) |
| app/utils/conversion/ultravox.py | class | MERaLiONWhisperEncoderModel | 137 | class MERaLiONWhisperEncoderModel(WhisperEncoderModel) |
| app/utils/conversion/ultravox.py | function | get_audio_config | 141 | def get_audio_config(self) -> dict[str, Any] \| None |
| app/utils/conversion/ultravox.py | function | set_gguf_parameters | 144 | def set_gguf_parameters(self) |
| app/utils/conversion/ultravox.py | function | filter_tensors | 150 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/ultravox.py | function | modify_tensors | 161 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/ultravox.py | class | VoxtralWhisperEncoderModel | 183 | class VoxtralWhisperEncoderModel(WhisperEncoderModel) |
| app/utils/conversion/ultravox.py | function | set_gguf_parameters | 187 | def set_gguf_parameters(self) |
| app/utils/conversion/ultravox.py | class | AudioFlamingo3WhisperEncoderModel | 194 | class AudioFlamingo3WhisperEncoderModel(WhisperEncoderModel) |
| app/utils/conversion/ultravox.py | function | set_gguf_parameters | 195 | def set_gguf_parameters(self) |
| app/utils/conversion/ultravox.py | function | tensor_force_quant | 199 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| app/utils/conversion/wavtokenizer.py | class | WavTokenizerDecModel | 12 | class WavTokenizerDecModel(TextModel) |
| app/utils/conversion/wavtokenizer.py | function | filter_tensors | 16 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/wavtokenizer.py | function | set_vocab | 28 | def set_vocab(self) |
| app/utils/conversion/wavtokenizer.py | function | set_gguf_parameters | 31 | def set_gguf_parameters(self) |
| app/utils/conversion/xverse.py | class | XverseModel | 14 | class XverseModel(TextModel) |
| app/utils/conversion/xverse.py | function | set_vocab | 17 | def set_vocab(self) |
| app/utils/conversion/xverse.py | function | set_gguf_parameters | 64 | def set_gguf_parameters(self) |
| app/utils/conversion/xverse.py | function | modify_tensors | 70 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/conversion/xverse.py | function | _reverse_hf_permute | 82 | def _reverse_hf_permute(self, weights: Tensor, n_head: int, n_kv_head: int \| None = None) -> Tensor |
| app/utils/conversion/youtuvl.py | class | YoutuVLVisionModel | 12 | class YoutuVLVisionModel(MmprojModel) |
| app/utils/conversion/youtuvl.py | function | __init__ | 13 | def __init__(self, *args, **kwargs) |
| app/utils/conversion/youtuvl.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| app/utils/conversion/youtuvl.py | function | filter_tensors | 47 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| app/utils/conversion/youtuvl.py | function | modify_tensors | 57 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/convert_lora_to_gguf.py | class | PartialLoraTensor | 34 | class PartialLoraTensor |
| app/utils/convert_lora_to_gguf.py | class | LoraTorchTensor | 40 | class LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | __init__ | 45 | def __init__(self, A: Tensor, B: Tensor) |
| app/utils/convert_lora_to_gguf.py | function | get_lora_A_B | 55 | def get_lora_A_B(self) -> tuple[Tensor, Tensor] |
| app/utils/convert_lora_to_gguf.py | function | __getitem__ | 58 | def __getitem__( self, indices: ( SupportsIndex |
| app/utils/convert_lora_to_gguf.py | function | dtype | 117 | def dtype(self) -> torch.dtype |
| app/utils/convert_lora_to_gguf.py | function | shape | 122 | def shape(self) -> tuple[int, ...] |
| app/utils/convert_lora_to_gguf.py | function | size | 126 | def size(self, dim=None) |
| app/utils/convert_lora_to_gguf.py | function | contiguous | 130 | def contiguous(self) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | reshape | 136 | def reshape(self, *shape: int \| tuple[int, ...]) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | reshape_as | 162 | def reshape_as(self, other: Tensor) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | view | 165 | def view(self, *size: int) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | permute | 168 | def permute(self, *dims: int) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | transpose | 181 | def transpose(self, dim0: int, dim1: int) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | swapaxes | 187 | def swapaxes(self, axis0: int, axis1: int) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | split | 190 | def split(self, split_size: int \| Sequence[int], dim: int = 0) -> tuple[LoraTorchTensor, ...] |
| app/utils/convert_lora_to_gguf.py | function | to | 208 | def to(self, *args, **kwargs) |
| app/utils/convert_lora_to_gguf.py | function | __mul__ | 211 | def __mul__(self, other) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | __rmul__ | 218 | def __rmul__(self, other) -> LoraTorchTensor |
| app/utils/convert_lora_to_gguf.py | function | __torch_function__ | 222 | def __torch_function__(cls, func: Callable, types, args=(), kwargs=None) |
| app/utils/convert_lora_to_gguf.py | function | get_base_tensor_name | 269 | def get_base_tensor_name(lora_tensor_name: str) -> str |
| app/utils/convert_lora_to_gguf.py | function | parse_args | 279 | def parse_args() -> argparse.Namespace |
| app/utils/convert_lora_to_gguf.py | function | load_hparams_from_hf | 322 | def load_hparams_from_hf(hf_model_id: str) -> tuple[dict[str, Any], Path \| None] |
| app/utils/convert_lora_to_gguf.py | class | LoraModel | 401 | class LoraModel(model_class):  # ty: ignore[unsupported-base] |
| app/utils/convert_lora_to_gguf.py | function | __init__ | 406 | def __init__(self, *args, dir_lora_model: Path, lora_alpha: float, **kwargs) |
| app/utils/convert_lora_to_gguf.py | function | set_vocab | 413 | def set_vocab(self) |
| app/utils/convert_lora_to_gguf.py | function | set_type | 416 | def set_type(self) |
| app/utils/convert_lora_to_gguf.py | function | set_gguf_parameters | 420 | def set_gguf_parameters(self) |
| app/utils/convert_lora_to_gguf.py | function | generate_extra_tensors | 447 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| app/utils/convert_lora_to_gguf.py | function | get_tensors | 451 | def get_tensors(self) -> Iterator[tuple[str, Tensor]] |
| app/utils/convert_lora_to_gguf.py | function | modify_tensors | 495 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| app/utils/correlation_logger.py | function | set_correlation_id | 20 | def set_correlation_id(cid: str) -> contextvars.Token |
| app/utils/correlation_logger.py | function | get_correlation_id | 25 | def get_correlation_id() -> str |
| app/utils/correlation_logger.py | function | reset_correlation_id | 30 | def reset_correlation_id(token: contextvars.Token) -> None |
| app/utils/correlation_logger.py | function | new_correlation_id | 35 | def new_correlation_id() -> str |
| app/utils/correlation_logger.py | class | CorrelationFilter | 40 | class CorrelationFilter(logging.Filter) |
| app/utils/correlation_logger.py | function | filter | 47 | def filter(self, record: logging.LogRecord) -> bool |
| app/utils/custom_embeddings.py | class | TfidfEmbedder | 19 | class TfidfEmbedder |
| app/utils/custom_embeddings.py | function | __init__ | 20 | def __init__(self) |
| app/utils/custom_embeddings.py | function | tokenize | 29 | def tokenize(self, text: str) -> list[str] |
| app/utils/custom_embeddings.py | function | fit | 35 | def fit(self, documents: list[str]) |
| app/utils/custom_embeddings.py | function | transform | 70 | def transform(self, text: str) -> np.ndarray |
| app/utils/custom_embeddings.py | function | get_top_terms | 102 | def get_top_terms(self, vector: np.ndarray, top_n: int = 5) -> list[tuple[str, float]] |
| app/utils/custom_embeddings.py | function | cosine_similarity | 120 | def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float |
| app/utils/dataset_merger.py | function | _assistant_content | 41 | def _assistant_content(record: dict[str, Any]) -> str |
| app/utils/dataset_merger.py | function | _is_anomalous | 48 | def _is_anomalous(record: dict[str, Any]) -> bool |
| app/utils/dataset_merger.py | function | _exact_hash | 86 | def _exact_hash(record: dict[str, Any]) -> str |
| app/utils/dataset_merger.py | function | _prompt_key | 94 | def _prompt_key(record: dict[str, Any]) -> str |
| app/utils/dataset_merger.py | function | _parse_ts | 103 | def _parse_ts(record: dict[str, Any]) -> datetime |
| app/utils/dataset_merger.py | function | _load_jsonl | 116 | def _load_jsonl(path: str) -> list[dict[str, Any]] |
| app/utils/dataset_merger.py | function | _write_jsonl_atomic | 135 | def _write_jsonl_atomic(path: str, records: list[dict[str, Any]]) -> None |
| app/utils/dataset_merger.py | class | DatasetMerger | 154 | class DatasetMerger |
| app/utils/dataset_merger.py | function | merge_files | 160 | def merge_files(primary_path: str, incoming_path: str) -> dict[str, int] |
| app/utils/dataset_merger.py | function | validate_file | 262 | def validate_file(path: str) -> dict[str, int] |
| app/utils/db_pool.py | class | SQLiteConnectionPool | 12 | class SQLiteConnectionPool |
| app/utils/db_pool.py | function | __init__ | 21 | def __init__(self, db_path: str, pool_size: int = 5) -> None |
| app/utils/db_pool.py | function | _make_connection | 31 | def _make_connection(self) -> sqlite3.Connection |
| app/utils/db_pool.py | function | get_connection | 47 | def get_connection(self) -> Generator[sqlite3.Connection, None, None] |
| app/utils/db_pool.py | function | close_all | 62 | def close_all(self) -> None |
| app/utils/diagnostics.py | function | _c | 41 | def _c(code: str, s: str) -> str |
| app/utils/diagnostics.py | function | _green | 45 | def _green(s: str) -> str:  return _c("32", s) |
| app/utils/diagnostics.py | function | _red | 46 | def _red(s: str) -> str:    return _c("31", s) |
| app/utils/diagnostics.py | function | _yellow | 47 | def _yellow(s: str) -> str: return _c("33", s) |
| app/utils/diagnostics.py | function | _cyan | 48 | def _cyan(s: str) -> str:   return _c("36", s) |
| app/utils/diagnostics.py | function | _bold | 49 | def _bold(s: str) -> str:   return _c("1", s) |
| app/utils/diagnostics.py | function | _dim | 50 | def _dim(s: str) -> str:    return _c("2", s) |
| app/utils/diagnostics.py | function | _row | 58 | def _row(badge: str, label: str, detail: str = "") -> str |
| app/utils/diagnostics.py | function | _metadata_version | 75 | def _metadata_version(name: str) -> str \| None |
| app/utils/diagnostics.py | function | check_dependencies | 85 | def check_dependencies() -> dict[str, Any] |
| app/utils/diagnostics.py | function | _linux_cpu_flags | 99 | def _linux_cpu_flags() -> set[str] |
| app/utils/diagnostics.py | function | _macos_sysctl | 110 | def _macos_sysctl(key: str) -> str |
| app/utils/diagnostics.py | function | check_hardware | 121 | def check_hardware() -> dict[str, Any] |
| app/utils/diagnostics.py | function | _read_active_filename | 168 | def _read_active_filename() -> str \| None |
| app/utils/diagnostics.py | function | _gguf_magic_ok | 176 | def _gguf_magic_ok(path: str) -> bool |
| app/utils/diagnostics.py | function | check_models | 184 | def check_models() -> dict[str, Any] |
| app/utils/diagnostics.py | function | check_port | 230 | def check_port(port: int = 8080) -> dict[str, Any] |
| app/utils/diagnostics.py | function | _render | 242 | def _render(report: dict[str, Any]) -> bool |
| app/utils/diagnostics.py | function | run_diagnostics | 355 | def run_diagnostics() -> int |
| app/utils/ipc_helper.py | function | _process_termination_sanitization | 21 | def _process_termination_sanitization() |
| app/utils/ipc_helper.py | class | SanitizedSharedMemory | 40 | class SanitizedSharedMemory |
| app/utils/ipc_helper.py | function | __init__ | 48 | def __init__(self, name: str \| None = None, create: bool = False, size: int = 0) |
| app/utils/ipc_helper.py | function | __enter__ | 57 | def __enter__(self) |
| app/utils/ipc_helper.py | function | __exit__ | 60 | def __exit__(self, exc_type, exc_val, exc_tb) |
| app/utils/ipc_helper.py | function | close_and_sanitize | 63 | def close_and_sanitize(self) |
| app/utils/ipc_helper.py | class | SharedMemoryManager | 98 | class SharedMemoryManager |
| app/utils/ipc_helper.py | function | __init__ | 105 | def __init__(self) -> None |
| app/utils/ipc_helper.py | function | instance | 109 | def instance(cls) -> "SharedMemoryManager" |
| app/utils/ipc_helper.py | function | allocate | 115 | def allocate(self, size: int = 4096, name: str \| None = None) -> SharedMemory |
| app/utils/ipc_helper.py | function | sanitize_and_free_shm | 123 | def sanitize_and_free_shm(self, shm: SharedMemory) -> None |
| app/utils/ipc_helper.py | function | _cleanup_all | 145 | def _cleanup_all(self) -> None |
| app/utils/ipc_helper.py | function | _install_signal_handlers | 149 | def _install_signal_handlers(self) -> None |
| app/utils/ipc_helper.py | function | _signal_handler | 157 | def _signal_handler(self, signum: int, frame) -> None |
| app/utils/ipc_helper.py | function | active_count | 164 | def active_count(self) -> int |
| app/utils/ipc_helper.py | function | active_names | 169 | def active_names(self) -> list[str] |
| app/utils/keychain_manager.py | function | save_cached_token | 60 | def save_cached_token(token: str) |
| app/utils/keychain_manager.py | function | load_cached_token | 92 | def load_cached_token() -> str \| None |
| app/utils/keychain_manager.py | function | revoke_tokens | 140 | def revoke_tokens() |
| app/utils/keychain_manager.py | function | get_token_scopes | 162 | def get_token_scopes(token: str, token_path: str = TOKEN_PATH) -> list[str] \| None |
| app/utils/keychain_manager.py | function | add_scoped_token | 186 | def add_scoped_token(token: str, scopes: list[str], token_path: str = TOKEN_PATH) -> None |
| app/utils/keychain_manager.py | function | _verify_token | 214 | def _verify_token(token: str) -> bool |
| app/utils/keychain_manager.py | function | _clear_keyring | 219 | def _clear_keyring() |
| app/utils/keychain_manager.py | function | _add_key_kernel | 233 | def _add_key_kernel( key_type: bytes, description: bytes, payload: bytes, |
| app/utils/keychain_manager.py | function | _keyctl_timeout | 278 | def _keyctl_timeout(key_id: int, timeout_seconds: int) -> None |
| app/utils/keychain_manager.py | function | _keyctl_revoke_key | 319 | def _keyctl_revoke_key(key_id: int) -> None |
| app/utils/keychain_manager.py | function | store_session_token | 360 | def store_session_token(token: str, timeout_seconds: int = 43200) -> int |
| app/utils/keychain_manager.py | function | revoke_session_token | 415 | def revoke_session_token(key_id: int) -> None |
| app/utils/memory_manager.py | class | MemoryManager | 10 | class MemoryManager |
| app/utils/memory_manager.py | function | __init__ | 11 | def __init__(self, sessions_dir="data/sessions", repository=None) |
| app/utils/memory_manager.py | function | autosave_path | 17 | def autosave_path(self) -> str |
| app/utils/memory_manager.py | function | _serialize_history | 20 | def _serialize_history(self, chat_history) |
| app/utils/memory_manager.py | function | _clean_node_dict | 23 | def _clean_node_dict(node: SessionNode) -> dict |
| app/utils/memory_manager.py | function | save_autosave_checkpoint | 51 | def save_autosave_checkpoint( self, session_tree, active_workspace, |
| app/utils/memory_manager.py | function | load_autosave_checkpoint | 72 | def load_autosave_checkpoint(self) -> dict \| None |
| app/utils/memory_manager.py | function | clear_autosave_checkpoint | 75 | def clear_autosave_checkpoint(self) |
| app/utils/memory_manager.py | function | save_session | 79 | def save_session(self, chat_history, system_prompt, filename=None, last_model="unknown", adapter_name=None, message_count=0) |
| app/utils/memory_manager.py | function | load_session | 100 | def load_session(self, filename) |
| app/utils/memory_manager.py | function | list_sessions | 123 | def list_sessions(self) |
| app/utils/memory_manager.py | function | list_sessions_with_metadata | 126 | def list_sessions_with_metadata(self) |
| app/utils/memory_manager.py | function | _count_nodes | 141 | def _count_nodes(node) |
| app/utils/memory_manager.py | function | load_swarm_history | 169 | def load_swarm_history(self) |
| app/utils/memory_manager.py | function | save_swarm_history | 173 | def save_swarm_history(self, history) |
| app/utils/rag_pipeline.py | class | _ParsedFile | 41 | class _ParsedFile |
| app/utils/rag_pipeline.py | class | RAGPipeline | 49 | class RAGPipeline |
| app/utils/rag_pipeline.py | function | __init__ | 53 | def __init__( self, model_name: str = "all-MiniLM-L6-v2", index_path: str = "data/vector_db", |
| app/utils/rag_pipeline.py | function | _new_index | 99 | def _new_index(self) |
| app/utils/rag_pipeline.py | function | _connect_db | 102 | def _connect_db(self) -> sqlite3.Connection |
| app/utils/rag_pipeline.py | function | _init_db | 110 | def _init_db(self) |
| app/utils/rag_pipeline.py | function | _legacy_metadata_file | 130 | def _legacy_metadata_file(self) -> str |
| app/utils/rag_pipeline.py | function | _fetch_documents | 135 | def _fetch_documents(self, conn: sqlite3.Connection \| None = None) -> list[dict] |
| app/utils/rag_pipeline.py | function | _next_vector_id | 146 | def _next_vector_id(self, conn: sqlite3.Connection \| None = None) -> int |
| app/utils/rag_pipeline.py | function | _add_embeddings_to_index | 161 | def _add_embeddings_to_index(self, embeddings: np.ndarray, vector_ids: list[int]) |
| app/utils/rag_pipeline.py | function | _write_index_atomic | 165 | def _write_index_atomic(self, index=None) |
| app/utils/rag_pipeline.py | function | _migrate_legacy_metadata | 171 | def _migrate_legacy_metadata(self) |
| app/utils/rag_pipeline.py | function | _ensure_id_index | 202 | def _ensure_id_index(self, loaded_index) |
| app/utils/rag_pipeline.py | function | encoder | 218 | def encoder(self) |
| app/utils/rag_pipeline.py | function | is_encoder_loaded | 228 | def is_encoder_loaded(self) -> bool |
| app/utils/rag_pipeline.py | function | reranker | 232 | def reranker(self) |
| app/utils/rag_pipeline.py | function | preload_encoder | 258 | def preload_encoder(self) |
| app/utils/rag_pipeline.py | function | _load_index | 263 | def _load_index(self) |
| app/utils/rag_pipeline.py | function | save_index | 284 | def save_index(self) |
| app/utils/rag_pipeline.py | function | clear_index | 291 | def clear_index(self) |
| app/utils/rag_pipeline.py | function | extract_text | 307 | def extract_text(self, filepath: str) -> str |
| app/utils/rag_pipeline.py | function | chunk_text | 328 | def chunk_text(self, text: str, chunk_size: int = 200, overlap: int = 50) -> list[str] |
| app/utils/rag_pipeline.py | function | _default_worker_count | 339 | def _default_worker_count(self) -> int |
| app/utils/rag_pipeline.py | function | _iter_supported_files | 347 | def _iter_supported_files(self, path: str, recursive: bool = True) -> list[str] |
| app/utils/rag_pipeline.py | function | _chunks_from_file | 374 | def _chunks_from_file(self, filepath: str, chunk_size: int, overlap: int) -> list[str] |
| app/utils/rag_pipeline.py | function | _parse_file_for_ingest | 401 | def _parse_file_for_ingest( self, index: int, filepath: str, |
| app/utils/rag_pipeline.py | function | _embed_texts_batched | 422 | def _embed_texts_batched(self, texts: list[str], batch_size: int = 32) -> np.ndarray |
| app/utils/rag_pipeline.py | function | _add_chunks_to_index | 440 | def _add_chunks_to_index( self, chunk_records: list[tuple[str, str]], embeddings: np.ndarray, |
| app/utils/rag_pipeline.py | function | ingest_files | 496 | def ingest_files( self, filepaths: list[str], chunk_size: int = 200, |
| app/utils/rag_pipeline.py | function | ingest_directory | 584 | def ingest_directory( self, path: str, recursive: bool = True, |
| app/utils/rag_pipeline.py | function | ingest_file | 604 | def ingest_file(self, filepath: str, chunk_size: int = 200, overlap: int = 50) -> int |
| app/utils/rag_pipeline.py | function | ingest_text | 621 | def ingest_text(self, text: str, source_name: str = "inline", chunk_size: int = 200, overlap: int = 50) -> int |
| app/utils/rag_pipeline.py | function | _is_toc_chunk | 636 | def _is_toc_chunk(self, doc: dict) -> bool |
| app/utils/rag_pipeline.py | function | retrieve | 651 | def retrieve( self, query: str, top_k: int = 5, |
| app/utils/rag_pipeline.py | function | retrieve_with_attribution | 692 | def retrieve_with_attribution( self, query: str, top_k: int = 5, |
| app/utils/rag_pipeline.py | function | retrieve_sparse | 703 | def retrieve_sparse( self, query: str, top_k: int = 3, |
| app/utils/rag_pipeline.py | function | retrieve_hybrid | 746 | def retrieve_hybrid( self, query: str, top_k: int = 3, |
| app/utils/rag_pipeline.py | function | retrieve_with_metadata | 833 | def retrieve_with_metadata( self, query: str, top_k: int = 3, |
| app/utils/rag_pipeline.py | function | eval_retrieval | 993 | def eval_retrieval( self, query: str, expected_chunk_ids: list[int], |
| app/utils/rag_pipeline.py | function | list_sources | 1036 | def list_sources(self) -> list[str] |
| app/utils/rag_pipeline.py | function | total_chunks | 1048 | def total_chunks(self) -> int |
| app/utils/rag_pipeline.py | function | remove_source | 1051 | def remove_source(self, source_name: str) |
| app/utils/rag_pipeline.py | function | rebuild_index | 1089 | def rebuild_index(self) |
| app/utils/session_tree.py | class | SessionTreeStats | 8 | class SessionTreeStats |
| app/utils/session_tree.py | class | SessionNode | 14 | class SessionNode |
| app/utils/session_tree.py | function | __init__ | 15 | def __init__( self, role: str, content: str, |
| app/utils/session_tree.py | function | add_child | 33 | def add_child( self, role: str, content: str, |
| app/utils/session_tree.py | function | to_dict | 45 | def to_dict(self) -> dict |
| app/utils/session_tree.py | function | from_dict | 58 | def from_dict(cls, data: dict, parent: 'SessionNode' = None) -> 'SessionNode' |
| app/utils/session_tree.py | class | SessionTree | 71 | class SessionTree |
| app/utils/session_tree.py | function | __init__ | 72 | def __init__(self, root: SessionNode = None, current_node_id: str = None) |
| app/utils/session_tree.py | function | _rebuild_maps | 83 | def _rebuild_maps(self) |
| app/utils/session_tree.py | function | _walk | 85 | def _walk(node) |
| app/utils/session_tree.py | function | get_node | 92 | def get_node(self, node_id: str) -> SessionNode \| None |
| app/utils/session_tree.py | function | current_node | 96 | def current_node(self) -> SessionNode |
| app/utils/session_tree.py | function | add_message | 102 | def add_message(self, role: str, content: str, attachments: list \| None = None, thought: str = None) -> SessionNode |
| app/utils/session_tree.py | function | branch_from | 109 | def branch_from( self, node_id: str, role: str \| None = None, |
| app/utils/session_tree.py | function | get_active_path | 124 | def get_active_path(self) -> list[SessionNode] |
| app/utils/session_tree.py | function | get_active_path_dicts | 134 | def get_active_path_dicts(self) -> list[dict] |
| app/utils/session_tree.py | function | set_current_node | 143 | def set_current_node(self, node_id: str) -> bool |
| app/utils/session_tree.py | function | update_current_node_content | 152 | def update_current_node_content(self, text: str) |
| app/utils/session_tree.py | function | update_node_content | 155 | def update_node_content(self, node_id: str, text: str) -> bool |
| app/utils/session_tree.py | function | node_depth | 162 | def node_depth(self, node_id: str \| None = None) -> int |
| app/utils/session_tree.py | function | leaf_nodes | 170 | def leaf_nodes(self) -> list[SessionNode] |
| app/utils/session_tree.py | function | _walk | 173 | def _walk(node: SessionNode) |
| app/utils/session_tree.py | function | stats | 183 | def stats(self) -> SessionTreeStats |
| app/utils/session_tree.py | function | _walk | 188 | def _walk(node: SessionNode, depth: int) |
| app/utils/session_tree.py | function | active_branch_label | 205 | def active_branch_label(self) -> str |
| app/utils/session_tree.py | function | to_dict | 212 | def to_dict(self) -> dict |
| app/utils/session_tree.py | function | from_dict | 219 | def from_dict(cls, data: dict) -> 'SessionTree' |
| app/utils/session_tree.py | function | clear | 225 | def clear(self) |
| app/utils/session_tree.py | function | copy | 230 | def copy(self) -> 'SessionTree' |
| app/utils/session_tree.py | function | __len__ | 234 | def __len__(self) |
| app/utils/session_tree.py | function | __getitem__ | 237 | def __getitem__(self, index) |
| app/utils/session_tree.py | function | __iter__ | 241 | def __iter__(self) |
| app/utils/session_tree.py | function | __bool__ | 244 | def __bool__(self) |
| app/utils/session_tree.py | function | append | 247 | def append(self, msg: dict) |
| app/utils/session_tree.py | function | save | 254 | def save(self, session_id: str \| None = None) -> str |
| app/utils/session_tree.py | function | load | 277 | def load(cls, path: str) -> tuple['SessionTree', str] |
| app/utils/session_tree.py | function | list_sessions | 287 | def list_sessions(cls) -> list[dict] |
| app/utils/session_tree.py | function | delete_session_file | 311 | def delete_session_file(self, path: str) |
| app/utils/topic_graph.py | class | TopicNode | 10 | class TopicNode |
| app/utils/topic_graph.py | function | __init__ | 11 | def __init__(self, name: str, parent=None) |
| app/utils/topic_graph.py | class | DynamicTopicGraph | 18 | class DynamicTopicGraph |
| app/utils/topic_graph.py | function | __init__ | 19 | def __init__(self) |
| app/utils/topic_graph.py | function | get_underrepresented_topic | 33 | def get_underrepresented_topic(self) -> str |
| app/utils/topic_graph.py | function | frequencies | 39 | def frequencies(self) -> dict[str, int] |
| app/utils/trace_logger.py | class | TraceLogger | 32 | class TraceLogger |
| app/utils/trace_logger.py | function | __init__ | 33 | def __init__(self, log_dir: str = "data/logs/traces", archive_dir: str = "data/logs/archive") |
| app/utils/trace_logger.py | function | read_jsonl | 45 | def read_jsonl(path: str) -> list[dict] |
| app/utils/trace_logger.py | function | _secure_mem_lock | 65 | def _secure_mem_lock(self) |
| app/utils/trace_logger.py | function | _get_max_bytes | 81 | def _get_max_bytes(self) -> int |
| app/utils/trace_logger.py | function | _get_encryption_key | 93 | def _get_encryption_key(self) -> bytes |
| app/utils/trace_logger.py | function | _zero_bytes | 123 | def _zero_bytes(ba: bytearray) -> None |
| app/utils/trace_logger.py | function | prune_logs | 128 | def prune_logs(self) |
| app/utils/trace_logger.py | function | enforce_retention_policy | 132 | def enforce_retention_policy(self, logs_dir="data/logs") |
| app/utils/trace_logger.py | function | _archive_log | 203 | def _archive_log(self, file_path: str) |
| app/utils/trace_logger.py | function | _archive_log_plaintext | 249 | def _archive_log_plaintext(self, file_path: str) |
| app/utils/trace_logger.py | function | _refresh_path | 264 | def _refresh_path(self) |
| app/utils/trace_logger.py | function | log_generation | 295 | def log_generation( self, compiled_prompt: str, hyperparams: dict, |
| app/utils/trace_logger.py | function | decrypt_in_memory | 391 | def decrypt_in_memory(token: str, file_path: str) -> list[dict] |
| app/utils/trace_logger.py | function | decrypt_to_bytearray | 453 | def decrypt_to_bytearray(file_path: str, key: bytes) -> bytearray |
| app/utils/trace_logger.py | function | update_last_entry_feedback | 471 | def update_last_entry_feedback(self, feedback: str, corrected_response: str \| None = None) |
| app/utils/tracing.py | class | Tracer | 21 | class Tracer |
| app/utils/tracing.py | function | __init__ | 24 | def __init__(self, trace_dir: str \| os.PathLike[str] = "data/logs/traces") -> None |
| app/utils/tracing.py | function | span | 31 | def span(self, name: str, attributes: dict[str, Any] \| None = None) -> "Span" |
| app/utils/tracing.py | function | _push | 34 | def _push(self, span: "Span") -> None |
| app/utils/tracing.py | function | _pop | 39 | def _pop(self, span: "Span") -> None |
| app/utils/tracing.py | function | current_span | 47 | def current_span(self) -> "Span \| None" |
| app/utils/tracing.py | function | _record_root | 51 | def _record_root(self, span: "Span") -> None |
| app/utils/tracing.py | class | Span | 68 | class Span |
| app/utils/tracing.py | function | __init__ | 71 | def __init__( self, name: str, attributes: dict[str, Any] \| None = None, |
| app/utils/tracing.py | function | __enter__ | 91 | def __enter__(self) -> "Span" |
| app/utils/tracing.py | function | __exit__ | 103 | def __exit__(self, exc_type, exc, traceback) -> bool |
| app/utils/tracing.py | function | set_attribute | 116 | def set_attribute(self, key: str, value: Any) -> None |
| app/utils/tracing.py | function | to_dict | 119 | def to_dict(self) -> dict[str, Any] |
| app/utils/training_curator.py | function | _ensure_dir | 18 | def _ensure_dir() |
| app/utils/training_curator.py | function | save_example | 22 | def save_example(system_prompt: str, user_msg: str, good_response: str, source: str = "thumbs_up") |
| app/utils/training_curator.py | function | get_all_examples | 46 | def get_all_examples() -> list |
| app/utils/training_curator.py | function | get_stats | 62 | def get_stats() -> dict |
| app/utils/training_curator.py | function | _is_degraded | 74 | def _is_degraded(record: dict) -> bool |
| app/utils/training_curator.py | function | _classify_example | 79 | def _classify_example(prompt: str) -> str |
| app/utils/training_curator.py | function | export_unsloth | 89 | def export_unsloth(output_path: str = "data/training/export_unsloth.jsonl") |
| app/utils/training_curator.py | function | export_dpo | 131 | def export_dpo(output_path: str = "data/training/export_unsloth_dpo.jsonl") -> str |
| app/utils/training_curator.py | function | delete_example | 213 | def delete_example(index: int) |
| app/utils/training_curator.py | function | save_eval_result | 224 | def save_eval_result(report: dict) -> str |
| app/utils/training_curator.py | function | list_eval_results | 263 | def list_eval_results() -> list[dict] |
| app/utils/training_curator.py | class | TrainingCurator | 293 | class TrainingCurator |
| app/utils/training_curator.py | function | save_example | 299 | def save_example(self, prompt: str, response: str, source: str = "thumbs_up", system_prompt: str = "") |
| app/utils/training_curator.py | function | get_all_examples | 304 | def get_all_examples(self) |
| app/utils/training_curator.py | function | get_stats | 307 | def get_stats(self) |
| app/utils/training_curator.py | function | export_unsloth | 310 | def export_unsloth(self, output_path: str = "data/training/export_unsloth.jsonl") |
| app/utils/training_curator.py | function | export_dpo | 313 | def export_dpo(self, output_path: str = "data/training/export_unsloth_dpo.jsonl") |
| app/utils/training_curator.py | function | delete_example | 316 | def delete_example(self, index: int) |
| app/utils/training_curator.py | function | save_eval_result | 319 | def save_eval_result(self, report: dict) -> str |
| app/utils/training_curator.py | function | list_eval_results | 322 | def list_eval_results(self) -> list[dict] |
| app/vision/image_preprocess.py | function | image_info | 10 | def image_info(path: str) -> dict |
| app/vision/image_preprocess.py | function | make_thumbnail | 21 | def make_thumbnail(src: str, dst: str, max_size: int = 512) -> None |
| app/vision/image_preprocess.py | function | prepare_for_ocr | 36 | def prepare_for_ocr(src: str, dst: str) -> dict |
| app/vision/image_store.py | class | ImageStore | 18 | class ImageStore |
| app/vision/image_store.py | function | __init__ | 19 | def __init__(self, base_dir: str = "data/images") |
| app/vision/image_store.py | function | save_qimage | 35 | def save_qimage(self, image: QImage, source: str = "clipboard") -> ImageRecord |
| app/vision/image_store.py | function | import_file | 44 | def import_file(self, path: str, source: str = "file") -> ImageRecord |
| app/vision/image_store.py | function | get | 58 | def get(self, image_id: str) -> ImageRecord |
| app/vision/image_store.py | function | list_recent | 65 | def list_recent(self, limit: int = 100) -> list[ImageRecord] |
| app/vision/image_store.py | function | update_analysis | 77 | def update_analysis(self, image_id: str, **fields) -> ImageRecord |
| app/vision/image_store.py | function | update_metadata | 85 | def update_metadata(self, image_id: str, kind: str \| None = None, tags: list[str] \| None = None) -> ImageRecord |
| app/vision/image_store.py | function | save_ocr_correction | 93 | def save_ocr_correction(self, image_id: str, corrected_text: str) -> ImageRecord |
| app/vision/image_store.py | function | save_caption_correction | 101 | def save_caption_correction(self, image_id: str, corrected_caption: str) -> ImageRecord |
| app/vision/image_store.py | function | _create_record | 109 | def _create_record(self, image_id: str, original_path: Path, source: str, mime: str) -> ImageRecord |
| app/vision/image_store.py | function | _write_record | 131 | def _write_record(self, record: ImageRecord) -> None |
| app/vision/image_store.py | function | _analysis_path | 136 | def _analysis_path(self, image_id: str) -> Path |
| app/vision/image_store.py | function | _sha256 | 141 | def _sha256(path: Path) -> str |
| app/vision/ocr_engine.py | class | TesseractOcrEngine | 11 | class TesseractOcrEngine |
| app/vision/ocr_engine.py | function | __init__ | 12 | def __init__(self, executable: str = "tesseract") |
| app/vision/ocr_engine.py | function | available | 15 | def available(self) -> bool |
| app/vision/ocr_engine.py | function | version | 18 | def version(self) -> str \| None |
| app/vision/ocr_engine.py | function | analyze | 34 | def analyze(self, image_path: str, lang: str = "eng") -> OcrResult |
| app/vision/ocr_engine.py | function | _parse_tsv | 63 | def _parse_tsv(self, raw: str, lang: str) -> OcrResult |
| app/vision/schemas.py | class | OcrResult | 8 | class OcrResult |
| app/vision/schemas.py | function | from_dict | 16 | def from_dict(cls, data: dict[str, Any] \| None) -> "OcrResult" |
| app/vision/schemas.py | function | to_dict | 26 | def to_dict(self) -> dict[str, Any] |
| app/vision/schemas.py | class | VisionResult | 31 | class VisionResult |
| app/vision/schemas.py | function | from_dict | 41 | def from_dict(cls, data: dict[str, Any] \| None) -> "VisionResult" |
| app/vision/schemas.py | function | to_dict | 53 | def to_dict(self) -> dict[str, Any] |
| app/vision/schemas.py | class | ImageRecord | 58 | class ImageRecord |
| app/vision/schemas.py | function | from_dict | 85 | def from_dict(cls, data: dict[str, Any]) -> "ImageRecord" |
| app/vision/schemas.py | function | to_dict | 105 | def to_dict(self) -> dict[str, Any] |
| app/vision/vision_analyzer.py | class | AnalysisSuggestion | 64 | class AnalysisSuggestion |
| app/vision/vision_analyzer.py | class | VisionAnalyzer | 72 | class VisionAnalyzer |
| app/vision/vision_analyzer.py | function | __init__ | 73 | def __init__(self, vision_loader=VisionModelLoader) |
| app/vision/vision_analyzer.py | function | analyze_record | 76 | def analyze_record( self, record: ImageRecord, ocr: OcrResult \| None = None, |
| app/vision/vision_analyzer.py | function | _heuristic_caption | 110 | def _heuristic_caption(record: ImageRecord, ocr: OcrResult, suggestion: AnalysisSuggestion) -> str |
| app/vision/vision_analyzer.py | function | classify_image | 124 | def classify_image(record: ImageRecord, text: str) -> AnalysisSuggestion |
| app/vision/vision_analyzer.py | function | _layout_hint | 160 | def _layout_hint(record: ImageRecord, text: str) -> str |
| app/vision/vision_analyzer.py | function | _dedupe | 176 | def _dedupe(values: list[str]) -> list[str] |
| app/vision/vision_model_loader.py | class | VisionModelEntry | 20 | class VisionModelEntry |
| app/vision/vision_model_loader.py | function | from_dict | 33 | def from_dict(cls, data: dict[str, Any]) -> "VisionModelEntry" |
| app/vision/vision_model_loader.py | function | model_path | 47 | def model_path(self) -> Path |
| app/vision/vision_model_loader.py | function | projector_path | 50 | def projector_path(self) -> Path |
| app/vision/vision_model_loader.py | function | to_dict | 53 | def to_dict(self) -> dict[str, Any] |
| app/vision/vision_model_loader.py | function | read_vision_registry | 72 | def read_vision_registry(path: Path = REGISTRY_PATH) -> list[VisionModelEntry] |
| app/vision/vision_model_loader.py | function | active_vision_model_id | 81 | def active_vision_model_id(path: Path = ACTIVE_PATH) -> str \| None |
| app/vision/vision_model_loader.py | function | set_active_vision_model | 90 | def set_active_vision_model(model_id: str, path: Path = ACTIVE_PATH) -> None |
| app/vision/vision_model_loader.py | function | installed_vision_models | 96 | def installed_vision_models() -> list[dict[str, Any]] |
| app/vision/vision_model_loader.py | class | VisionModelLoader | 100 | class VisionModelLoader |
| app/vision/vision_model_loader.py | function | status | 107 | def status(cls) -> dict[str, Any] |
| app/vision/vision_model_loader.py | function | reset | 121 | def reset(cls) -> None |
| app/vision/vision_model_loader.py | function | load | 128 | def load(cls, model_id: str \| None = None) |
| app/vision/vision_model_loader.py | function | describe_image | 173 | def describe_image( cls, image_path: str, prompt: str \| None = None, |
| app/vision/vision_model_loader.py | function | _default_entry | 227 | def _default_entry(cls) -> VisionModelEntry \| None |
| app/vision/vision_model_loader.py | function | _resolve_entry | 239 | def _resolve_entry(cls, model_id: str \| None = None) -> VisionModelEntry \| None |
| app/vision/vision_model_loader.py | function | _handler_class | 251 | def _handler_class(family: str) |
| app/vision/vision_model_loader.py | function | _backend_status | 278 | def _backend_status() -> dict[str, Any] |
| app/vision/vision_model_loader.py | function | _image_data_url | 294 | def _image_data_url(image_path: str) -> str |
| app/vision/vision_model_loader.py | function | _looks_like_code | 303 | def _looks_like_code(text: str) -> bool |
| app/vision/vision_model_loader.py | function | _looks_like_error | 309 | def _looks_like_error(text: str) -> bool |
| auto_train.py | function | generate_tasks_for_topic | 56 | def generate_tasks_for_topic(topic: str, count: int, llm) -> list[dict] |
| auto_train.py | function | generate_fallback_tasks | 132 | def generate_fallback_tasks(topic: str, count: int) -> list[dict] |
| auto_train.py | function | solve_task | 159 | def solve_task(task: dict, llm) -> tuple[str, str] |
| auto_train.py | function | verify_solution | 181 | def verify_solution(task: dict, solution: str) -> tuple[bool, str] |
| auto_train.py | function | reflect_and_correct | 202 | def reflect_and_correct(task: dict, failed_thought: str, failed_response: str, traceback: str, llm) -> tuple[str, str, bool] |
| auto_train.py | function | train_adapter | 236 | def train_adapter(dataset_path: str, base_model_path: str, adapter_name: str, args) |
| auto_train.py | function | convert_adapter_to_gguf | 338 | def convert_adapter_to_gguf(base_model_path: str, adapter_name: str) |
| auto_train.py | function | main | 360 | def main() |
| core/agentic_loop.py | function | should_continue | 18 | def should_continue(iteration: int, last_response: str) -> bool |
| core/agentic_loop.py | function | build_next_prompt | 47 | def build_next_prompt(last_response: str, iteration: int) -> str |
| core/cognitive_parser.py | function | parse_thought_stream | 11 | def parse_thought_stream(raw_text: str) -> tuple[str, str] |
| core/hardware_scout.py | function | get_cpu_flags | 6 | def get_cpu_flags() -> list[str] |
| core/hardware_scout.py | function | get_hardware_uuid | 41 | def get_hardware_uuid() -> str |
| core/hardware_scout.py | function | get_hardware_profile | 76 | def get_hardware_profile() |
| core/interaction_loop.py | function | strip_html_tags | 65 | def strip_html_tags(html: str) -> str |
| core/interaction_loop.py | function | matches_keyword | 87 | def matches_keyword(text: str, keyword: str) -> bool |
| core/interaction_loop.py | function | _get_codex_context | 103 | def _get_codex_context(chat_history) |
| core/interaction_loop.py | function | _apply_vocab_leak_bypass | 144 | def _apply_vocab_leak_bypass(text: str) -> str |
| core/interaction_loop.py | function | build_prompt | 167 | def build_prompt(system_prompt, chat_history) |
| core/interaction_loop.py | function | is_greeting | 242 | def is_greeting(text: str) -> bool |
| core/prompt_templates.py | function | get_template | 93 | def get_template(name: str, **kwargs) -> str |
| core/prompt_templates.py | function | list_templates | 131 | def list_templates() -> list[str] |
| core/workflows.py | function | get_workflow | 80 | def get_workflow(name: str) -> dict |
| core/workflows.py | function | list_workflows | 93 | def list_workflows() -> list[tuple[str, str]] |
| data/flywheel/active_learner.py | class | ActiveLearner | 6 | class ActiveLearner |
| data/flywheel/active_learner.py | function | __init__ | 7 | def __init__(self, stats_path: str = STATS_PATH) |
| data/flywheel/active_learner.py | function | load | 12 | def load(self) |
| data/flywheel/active_learner.py | function | save | 20 | def save(self) |
| data/flywheel/active_learner.py | function | record_result | 30 | def record_result(self, topic: str, passed: bool) |
| data/flywheel/active_learner.py | function | should_generate | 37 | def should_generate(self, topic: str) -> bool |
| data/flywheel/agent1_generator.py | function | _ngrams | 28 | def _ngrams(text: str, n: int = _NGRAM_SIZE) -> set |
| data/flywheel/agent1_generator.py | function | _jaccard_ngram | 33 | def _jaccard_ngram(a: str, b: str) -> float |
| data/flywheel/agent1_generator.py | function | _is_duplicate | 41 | def _is_duplicate(candidate: str) -> bool |
| data/flywheel/agent1_generator.py | function | generate_math_problem_3var | 64 | def generate_math_problem_3var() |
| data/flywheel/agent1_generator.py | function | verify | 104 | def verify(response) |
| data/flywheel/agent1_generator.py | function | generate_coding_problem_extended | 121 | def generate_coding_problem_extended(challenge_name: str \| None = None) |
| data/flywheel/agent1_generator.py | function | verify | 179 | def verify(response) |
| data/flywheel/agent1_generator.py | function | verify | 202 | def verify(response) |
| data/flywheel/agent1_generator.py | function | generate_symbolic_problem_extended | 236 | def generate_symbolic_problem_extended() |
| data/flywheel/agent1_generator.py | function | verify | 256 | def verify(response) |
| data/flywheel/agent1_generator.py | function | verify | 277 | def verify(response) |
| data/flywheel/agent1_generator.py | function | generate_quadratic_problem | 294 | def generate_quadratic_problem() |
| data/flywheel/agent1_generator.py | function | _fmt_term | 306 | def _fmt_term(coeff, var="") |
| data/flywheel/agent1_generator.py | function | verify | 331 | def verify(response) |
| data/flywheel/agent1_generator.py | function | main | 364 | def main() |
| data/flywheel/agent3_curator.py | function | _load_stats | 46 | def _load_stats() -> dict |
| data/flywheel/agent3_curator.py | function | _save_stats | 63 | def _save_stats(stats: dict) |
| data/flywheel/agent3_curator.py | function | run_verification | 79 | def run_verification(exec_record: dict) -> tuple[bool, str] |
| data/flywheel/agent3_curator.py | function | _verify_subprocess | 104 | def _verify_subprocess(verification_script: str, model_response: str) -> tuple[bool, str] |
| data/flywheel/agent3_curator.py | function | _verify_sympy | 126 | def _verify_sympy(ground_truth: str, model_response: str) -> tuple[bool, str] |
| data/flywheel/agent3_curator.py | function | generate_correction | 155 | def generate_correction(exec_record: dict) -> tuple[str, str] |
| data/flywheel/agent3_curator.py | function | save_sft_example | 236 | def save_sft_example(exec_record: dict) |
| data/flywheel/agent3_curator.py | function | save_dpo_pair | 250 | def save_dpo_pair( exec_record: dict, corrected_thought: str, corrected_response: str ) |
| data/flywheel/agent3_curator.py | function | process_execution_file | 289 | def process_execution_file(path: str, stats: dict) |
| data/flywheel/agent3_curator.py | function | main | 336 | def main() |
| data/flywheel/executor_sandbox.py | class | SafePythonSandbox | 7 | class SafePythonSandbox |
| data/flywheel/executor_sandbox.py | function | __init__ | 12 | def __init__(self, cpu_timeout_sec: float = 2.0, memory_limit_mb: int = 256) |
| data/flywheel/executor_sandbox.py | function | _is_docker_available | 17 | def _is_docker_available(self) -> bool |
| data/flywheel/executor_sandbox.py | function | run_code | 31 | def run_code(self, code: str, test_code: str) -> tuple[bool, str] |
| data/flywheel/executor_sandbox.py | function | _run_in_docker | 44 | def _run_in_docker(self, script: str) -> tuple[bool, str] |
| data/flywheel/executor_sandbox.py | function | _run_locally | 85 | def _run_locally(self, script: str) -> tuple[bool, str] |
| data/flywheel/executor_sandbox.py | function | set_resource_limits | 91 | def set_resource_limits() |
| download_all_models.py | function | download_file | 7 | def download_file(url, filepath) |
| download_all_models.py | function | main | 25 | def main() |
| download_test_model.py | function | download_file | 5 | def download_file(url, filepath) |
| engine_test.py | function | test_introspection_engine | 25 | def test_introspection_engine() |
| eval/benchmark_rag.py | function | _tokenize | 33 | def _tokenize(text) |
| eval/benchmark_rag.py | function | _get_ngrams | 44 | def _get_ngrams(tokens, n) |
| eval/benchmark_rag.py | function | compute_bleu | 48 | def compute_bleu(reference, hypothesis, n_max=2) |
| eval/benchmark_rag.py | function | compute_rouge_1 | 98 | def compute_rouge_1(reference, hypothesis) |
| eval/benchmark_rag.py | function | compute_rouge_l | 123 | def compute_rouge_l(reference, hypothesis, beta=1.0) |
| eval/benchmark_rag.py | class | QueryResult | 191 | class QueryResult |
| eval/benchmark_rag.py | function | run_benchmark | 200 | def run_benchmark(top_k: int = 3, contextual_headers: bool = False) -> list[QueryResult] |
| eval/benchmark_rag.py | function | print_results | 241 | def print_results(results: list[QueryResult], top_k: int) |
| eval/benchmark_rag.py | function | calculate_metrics | 276 | def calculate_metrics(retrieved_ids: list[int], expected_ids: list[int], top_k: int) -> dict |
| eval/benchmark_rag.py | function | run_code_review_benchmark | 296 | def run_code_review_benchmark(top_k: int = 3, output_path: str = "data/rag_benchmark_results.json") |
| eval/benchmark_rag.py | function | main | 464 | def main() |
| eval/graders.py | function | exact_match | 20 | def exact_match(output: str, expected: str) -> dict |
| eval/graders.py | function | json_valid | 37 | def json_valid(output: str, schema_keys: list[str] \| None = None) -> dict |
| eval/graders.py | function | keyword_hit | 97 | def keyword_hit(output: str, keywords: list[str], require_all: bool = True) -> dict |
| eval/graders.py | function | groundedness | 129 | def groundedness(output: str, context_chunks: list[str], min_overlap_words: int = 3) -> dict |
| eval/graders.py | function | not_in_context | 201 | def not_in_context(output: str) -> dict |
| eval/graders.py | function | run_grader | 225 | def run_grader(name: str, output: str, **kwargs) -> dict |
| eval/harness.py | class | CaseResult | 40 | class CaseResult |
| eval/harness.py | class | EvalReport | 54 | class EvalReport |
| eval/harness.py | function | print_summary | 68 | def print_summary(self) |
| eval/harness.py | class | EvalHarness | 96 | class EvalHarness |
| eval/harness.py | function | __init__ | 105 | def __init__(self, rag_pipeline=None) |
| eval/harness.py | function | _load_dataset | 114 | def _load_dataset(self, dataset_path: str) -> list[dict] |
| eval/harness.py | function | _resolve_context | 127 | def _resolve_context(self, case: dict, workflow_cfg: dict) -> list[str] |
| eval/harness.py | function | _build_system_prompt | 153 | def _build_system_prompt(self, template_name: str, context_chunks: list[str], case: dict) -> str |
| eval/harness.py | function | _run_model | 159 | def _run_model( self, system_prompt: str, user_prompt: str, |
| eval/harness.py | function | _grade | 197 | def _grade(self, output: str, case: dict, context_chunks: list[str]) -> dict |
| eval/harness.py | function | run | 214 | def run( self, dataset_path: str, workflow_name: str, |
| eval/harness.py | function | save_report | 412 | def save_report(self, report: EvalReport, output_dir: str = "eval/results") -> str |
| eval/perplexity_bench.py | function | _query_free_vram_mb | 167 | def _query_free_vram_mb() -> float |
| eval/perplexity_bench.py | function | _vram_used_since | 176 | def _vram_used_since(free_before: float) -> float |
| eval/perplexity_bench.py | function | _softmax | 186 | def _softmax(logits_slice) -> np.ndarray |
| eval/perplexity_bench.py | function | compute_perplexity | 196 | def compute_perplexity(llm: Llama, eval_text: str, max_eval_tokens: int) -> float |
| eval/perplexity_bench.py | function | measure_throughput | 272 | def measure_throughput(llm: Llama, gen_tokens: int) -> float |
| eval/perplexity_bench.py | function | _release_model | 300 | def _release_model(llm: Llama \| None) -> None |
| eval/perplexity_bench.py | function | benchmark_model | 318 | def benchmark_model( model_path: str, eval_tokens: int, gen_tokens: int, |
| eval/perplexity_bench.py | function | _fmt | 391 | def _fmt(value, spec: str, missing: str = "—") -> str |
| eval/perplexity_bench.py | function | print_ascii_grid | 395 | def print_ascii_grid(results: list[dict]) -> None |
| eval/perplexity_bench.py | function | run_benchmark | 430 | def run_benchmark( models_dir: str = MODELS_DIR, eval_tokens: int = DEFAULT_EVAL_TOKENS, gen_tokens: int = DEFAULT_GEN_TOKENS, |
| eval/perplexity_bench.py | function | main | 491 | def main() -> None |
| eval/run_eval.py | function | parse_args | 43 | def parse_args() |
| eval/run_eval.py | function | dry_run_mode | 106 | def dry_run_mode(dataset_path: str, workflow_name: str) |
| eval/run_eval.py | function | main | 157 | def main() |
| eval/run_eval.py | function | get_vram_usage | 198 | def get_vram_usage() |
| flywheel_runner.py | function | write_json_atomic | 23 | def write_json_atomic(path: str, data: dict) |
| flywheel_runner.py | function | process_task | 30 | def process_task(task_path: str, llm) |
| flywheel_runner.py | function | main | 97 | def main() |
| main.py | class | _NullFD | 34 | class _NullFD |
| main.py | function | __enter__ | 36 | def __enter__(self) |
| main.py | function | __exit__ | 42 | def __exit__(self, *_) |
| main.py | function | _assert_not_privileged | 101 | def _assert_not_privileged() -> None |
| main.py | function | _run_headless | 126 | def _run_headless() -> int |
| main.py | function | stop | 142 | def stop(_signum=None, _frame=None) |
| main.py | function | main | 164 | def main() |
| setup_karl.py | function | _enable_windows_ansi | 53 | def _enable_windows_ansi() -> None |
| setup_karl.py | function | _ok | 78 | def _ok(msg: str)   -> None: print(f"{_GREEN}  ✓  {msg}{_RESET}") |
| setup_karl.py | function | _info | 79 | def _info(msg: str) -> None: print(f"{_CYAN}  ·  {msg}{_RESET}") |
| setup_karl.py | function | _warn | 80 | def _warn(msg: str) -> None: print(f"{_YELLOW}  ⚠  {msg}{_RESET}") |
| setup_karl.py | function | _err | 81 | def _err(msg: str)  -> None: print(f"{_RED}  ✗  {msg}{_RESET}", file=sys.stderr) |
| setup_karl.py | function | _sep | 82 | def _sep()          -> None: print(f"{_DIM}{'─' * 60}{_RESET}") |
| setup_karl.py | function | _head | 83 | def _head(msg: str) -> None: print(f"\n{_BOLD}{_CYAN}{msg}{_RESET}") |
| setup_karl.py | class | SystemInfo | 88 | class SystemInfo(NamedTuple) |
| setup_karl.py | function | detect_system | 98 | def detect_system() -> SystemInfo |
| setup_karl.py | function | _probe_nvidia | 139 | def _probe_nvidia() -> str \| None |
| setup_karl.py | function | _probe_apple_chip | 166 | def _probe_apple_chip() -> str |
| setup_karl.py | function | _find_existing_venv | 184 | def _find_existing_venv() -> Path \| None |
| setup_karl.py | function | build_cmake_args | 198 | def build_cmake_args(gpu_type: str, override: str \| None = None) -> str |
| setup_karl.py | function | _venv_executables | 216 | def _venv_executables(venv_dir: Path) -> dict[str, Path] |
| setup_karl.py | function | find_or_create_venv | 226 | def find_or_create_venv(*, force: bool = False) -> Path |
| setup_karl.py | function | _run | 251 | def _run( cmd: list[str], *, desc: str = "", |
| setup_karl.py | function | install_dependencies | 305 | def install_dependencies(pip: Path) -> None |
| setup_karl.py | function | install_llama_cpp | 326 | def install_llama_cpp(pip: Path, cmake_args: str) -> None |
| setup_karl.py | function | _extract_requirement | 356 | def _extract_requirement(name: str) -> str |
| setup_karl.py | function | ensure_data_dirs | 373 | def ensure_data_dirs() -> None |
| setup_karl.py | function | maybe_download_model | 381 | def maybe_download_model(python: Path) -> None |
| setup_karl.py | function | cmd_install | 408 | def cmd_install(args: argparse.Namespace, info: SystemInfo) -> None |
| setup_karl.py | function | cmd_run | 459 | def cmd_run(args: argparse.Namespace, info: SystemInfo) -> None |
| setup_karl.py | function | cmd_info | 505 | def cmd_info(info: SystemInfo) -> None |
| setup_karl.py | function | _print_info | 514 | def _print_info(info: SystemInfo) -> None |
| setup_karl.py | function | _check_python_version | 533 | def _check_python_version() -> None |
| setup_karl.py | function | _build_parser | 544 | def _build_parser() -> argparse.ArgumentParser |
| setup_karl.py | function | main | 573 | def main() -> None |
| tests/conftest.py | function | module_available | 18 | def module_available(name: str) -> bool |
| tests/conftest.py | function | embedding_model_available | 29 | def embedding_model_available() -> bool |
| tests/conftest.py | function | requires_embedding_model | 41 | def requires_embedding_model() |
| tests/mock_mcp_server.py | function | hello | 13 | def hello(name: str) -> str |
| tests/mock_mcp_server.py | function | get_version | 19 | def get_version() -> str |
| tests/test_agent_memory.py | function | test_codebase_memory_indexes_functions_classes_and_methods | 7 | def test_codebase_memory_indexes_functions_classes_and_methods(tmp_path) |
| tests/test_agent_memory.py | function | add | 12 | def add(a, b) |
| tests/test_agent_memory.py | class | Calculator | 16 | class Calculator |
| tests/test_agent_memory.py | function | multiply | 19 | def multiply(self, x, y) |
| tests/test_agent_memory.py | function | test_query_memory_returns_matching_signature_text | 44 | def test_query_memory_returns_matching_signature_text(tmp_path) |
| tests/test_agent_memory.py | function | test_coder_agent_injects_codebase_signature_reference | 60 | def test_coder_agent_injects_codebase_signature_reference(tmp_path) |
| tests/test_agent_memory.py | function | fake_llm | 71 | def fake_llm(prompt, **kwargs) |
| tests/test_ai_lab.py | class | TestAILabWorkspace | 13 | class TestAILabWorkspace(unittest.TestCase) |
| tests/test_ai_lab.py | function | setUp | 14 | def setUp(self) |
| tests/test_ai_lab.py | function | tearDown | 26 | def tearDown(self) |
| tests/test_ai_lab.py | function | test_construction_and_layout | 41 | def test_construction_and_layout(self) |
| tests/test_ai_lab.py | function | test_sparse_pipeline_math | 72 | def test_sparse_pipeline_math(self) |
| tests/test_ai_lab.py | function | test_custom_agent_publishing | 97 | def test_custom_agent_publishing(self) |
| tests/test_app_state_persistence.py | function | _start_patches | 30 | def _start_patches() |
| tests/test_app_state_persistence.py | function | _stop_patches | 35 | def _stop_patches() |
| tests/test_app_state_persistence.py | class | TestAppStatePersistence | 44 | class TestAppStatePersistence(unittest.TestCase) |
| tests/test_app_state_persistence.py | function | setUp | 47 | def setUp(self) |
| tests/test_app_state_persistence.py | function | tearDown | 57 | def tearDown(self) |
| tests/test_app_state_persistence.py | function | test_defaults_when_no_file | 65 | def test_defaults_when_no_file(self) |
| tests/test_app_state_persistence.py | function | test_save_to_disk_creates_file | 89 | def test_save_to_disk_creates_file(self) |
| tests/test_app_state_persistence.py | function | test_save_and_load_roundtrip | 95 | def test_save_and_load_roundtrip(self) |
| tests/test_app_state_persistence.py | function | test_save_preserves_none_custom_accent | 138 | def test_save_preserves_none_custom_accent(self) |
| tests/test_app_state_persistence.py | function | test_unknown_keys_in_file_are_ignored | 149 | def test_unknown_keys_in_file_are_ignored(self) |
| tests/test_app_state_persistence.py | function | test_extra_keys_not_written_back | 159 | def test_extra_keys_not_written_back(self) |
| tests/test_app_state_persistence.py | function | test_corrupt_json_falls_back_to_defaults | 173 | def test_corrupt_json_falls_back_to_defaults(self) |
| tests/test_app_state_persistence.py | function | test_non_dict_json_falls_back_to_defaults | 185 | def test_non_dict_json_falls_back_to_defaults(self) |
| tests/test_app_state_persistence.py | function | test_int_fields_coerced_from_float_on_disk | 196 | def test_int_fields_coerced_from_float_on_disk(self) |
| tests/test_app_state_persistence.py | function | test_float_fields_coerced_from_int_on_disk | 206 | def test_float_fields_coerced_from_int_on_disk(self) |
| tests/test_app_state_persistence.py | function | test_bool_fields_not_coerced_to_int | 216 | def test_bool_fields_not_coerced_to_int(self) |
| tests/test_app_state_persistence.py | function | test_bad_type_on_disk_reverts_to_default | 226 | def test_bad_type_on_disk_reverts_to_default(self) |
| tests/test_app_state_persistence.py | function | test_explicit_load_from_disk_overrides_live_values | 237 | def test_explicit_load_from_disk_overrides_live_values(self) |
| tests/test_app_state_persistence.py | function | test_partial_file_fills_gaps_with_defaults | 250 | def test_partial_file_fills_gaps_with_defaults(self) |
| tests/test_app_state_persistence.py | function | test_persist_fields_matches_ui_config_defaults | 262 | def test_persist_fields_matches_ui_config_defaults(self) |
| tests/test_app_state_persistence.py | function | test_heavy_objects_not_in_persist_fields | 270 | def test_heavy_objects_not_in_persist_fields(self) |
| tests/test_app_state_persistence.py | class | TestConfigCorruptionRecovery | 277 | class TestConfigCorruptionRecovery(unittest.TestCase) |
| tests/test_app_state_persistence.py | function | setUp | 280 | def setUp(self) |
| tests/test_app_state_persistence.py | function | tearDown | 289 | def tearDown(self) |
| tests/test_app_state_persistence.py | function | _data_dir_files | 295 | def _data_dir_files(self) |
| tests/test_app_state_persistence.py | function | test_corrupt_json_quarantines_file | 298 | def test_corrupt_json_quarantines_file(self) |
| tests/test_app_state_persistence.py | function | test_corrupt_json_rewrites_fresh_defaults | 319 | def test_corrupt_json_rewrites_fresh_defaults(self) |
| tests/test_app_state_persistence.py | function | test_non_dict_json_quarantines_file | 334 | def test_non_dict_json_quarantines_file(self) |
| tests/test_app_state_persistence.py | function | test_non_dict_json_rewrites_fresh_defaults | 346 | def test_non_dict_json_rewrites_fresh_defaults(self) |
| tests/test_app_state_persistence.py | function | test_appstate_corrupt_json_returns_defaults | 359 | def test_appstate_corrupt_json_returns_defaults(self) |
| tests/test_app_state_persistence.py | class | TestConfigVersioning | 370 | class TestConfigVersioning(unittest.TestCase) |
| tests/test_app_state_persistence.py | function | setUp | 373 | def setUp(self) |
| tests/test_app_state_persistence.py | function | tearDown | 382 | def tearDown(self) |
| tests/test_app_state_persistence.py | function | test_version_written_on_save | 388 | def test_version_written_on_save(self) |
| tests/test_app_state_persistence.py | function | test_appstate_save_includes_version | 395 | def test_appstate_save_includes_version(self) |
| tests/test_app_state_persistence.py | function | test_version_missing_loads_without_error | 403 | def test_version_missing_loads_without_error(self) |
| tests/test_app_state_persistence.py | function | test_version_older_loads_with_migration | 413 | def test_version_older_loads_with_migration(self) |
| tests/test_app_state_persistence.py | function | test_version_future_loads_without_crash | 422 | def test_version_future_loads_without_crash(self) |
| tests/test_app_state_persistence.py | function | test_version_non_int_treated_as_v0 | 431 | def test_version_non_int_treated_as_v0(self) |
| tests/test_app_state_persistence.py | class | TestConfigFieldValidation | 441 | class TestConfigFieldValidation(unittest.TestCase) |
| tests/test_app_state_persistence.py | function | setUp | 444 | def setUp(self) |
| tests/test_app_state_persistence.py | function | tearDown | 452 | def tearDown(self) |
| tests/test_app_state_persistence.py | function | _write_config | 457 | def _write_config(self, data: dict) |
| tests/test_app_state_persistence.py | function | test_float_above_max_uses_default | 462 | def test_float_above_max_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_float_below_min_uses_default | 468 | def test_float_below_min_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_int_below_min_uses_default | 474 | def test_int_below_min_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_int_above_max_uses_default | 480 | def test_int_above_max_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_bool_field_as_int_uses_default | 486 | def test_bool_field_as_int_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_bool_field_as_string_uses_default | 494 | def test_bool_field_as_string_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_str_field_as_int_uses_default | 500 | def test_str_field_as_int_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_valid_boundary_values_accepted | 506 | def test_valid_boundary_values_accepted(self) |
| tests/test_app_state_persistence.py | function | test_custom_accent_none_is_valid | 520 | def test_custom_accent_none_is_valid(self) |
| tests/test_app_state_persistence.py | function | test_custom_accent_string_is_valid | 526 | def test_custom_accent_string_is_valid(self) |
| tests/test_app_state_persistence.py | function | test_custom_accent_int_uses_default | 532 | def test_custom_accent_int_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_temperature_out_of_range_uses_default | 538 | def test_temperature_out_of_range_uses_default(self) |
| tests/test_app_state_persistence.py | function | test_valid_config_passes_through_unchanged | 544 | def test_valid_config_passes_through_unchanged(self) |
| tests/test_architecture_audit.py | function | test_model_loader_blocks_reset_during_active_inference | 9 | def test_model_loader_blocks_reset_during_active_inference(monkeypatch) |
| tests/test_architecture_audit.py | function | fake_get_instance | 15 | def fake_get_instance(cls, *args, **kwargs) |
| tests/test_architecture_audit.py | function | test_generation_threads_use_guarded_model_acquisition | 36 | def test_generation_threads_use_guarded_model_acquisition() |
| tests/test_architecture_audit.py | function | test_app_state_queues_cross_thread_signal_emissions | 46 | def test_app_state_queues_cross_thread_signal_emissions() |
| tests/test_architecture_audit.py | function | test_websocket_broadcast_prunes_failed_clients | 54 | def test_websocket_broadcast_prunes_failed_clients() |
| tests/test_architecture_audit.py | class | FailingClient | 57 | class FailingClient |
| tests/test_architecture_audit.py | class | GoodClient | 61 | class GoodClient |
| tests/test_architecture_audit.py | function | __init__ | 62 | def __init__(self) |
| tests/test_architecture_audit.py | function | test_websocket_manager_exposes_thread_safe_client_count | 91 | def test_websocket_manager_exposes_thread_safe_client_count() |
| tests/test_auto_train.py | function | _running_under_bwrap | 29 | def _running_under_bwrap() -> bool |
| tests/test_auto_train.py | class | TestAutoTrain | 37 | class TestAutoTrain(unittest.TestCase) |
| tests/test_auto_train.py | function | test_generate_fallback_tasks | 38 | def test_generate_fallback_tasks(self) |
| tests/test_auto_train.py | function | test_verify_solution_passing | 52 | def test_verify_solution_passing(self, mock_sandbox_class) |
| tests/test_auto_train.py | function | test_verify_solution_failing | 66 | def test_verify_solution_failing(self, mock_sandbox_class) |
| tests/test_auto_train.py | function | test_auto_train_thread_init | 79 | def test_auto_train_thread_init(self) |
| tests/test_auto_train.py | function | test_websocket_start_auto_train_rpc | 97 | def test_websocket_start_auto_train_rpc(self) |
| tests/test_codex_integration.py | class | TestCodexIntegration | 9 | class TestCodexIntegration(unittest.TestCase) |
| tests/test_codex_integration.py | function | test_strip_html_tags | 10 | def test_strip_html_tags(self) |
| tests/test_codex_integration.py | function | test_matches_keyword_word_boundaries | 28 | def test_matches_keyword_word_boundaries(self) |
| tests/test_codex_integration.py | function | test_build_prompt_codex_injection | 43 | def test_build_prompt_codex_injection(self) |
| tests/test_codex_integration.py | function | test_build_prompt_limits | 87 | def test_build_prompt_limits(self) |
| tests/test_cognitive_compression.py | class | MockLlama | 22 | class MockLlama |
| tests/test_cognitive_compression.py | function | __init__ | 23 | def __init__(self) |
| tests/test_cognitive_compression.py | function | tokenize | 27 | def tokenize(self, text_bytes, add_bos=True) |
| tests/test_cognitive_compression.py | function | __call__ | 36 | def __call__(self, prompt, **kwargs) |
| tests/test_cognitive_compression.py | function | test_cognitive_compression_and_live_stats | 89 | def test_cognitive_compression_and_live_stats() |
| tests/test_cognitive_compression.py | function | on_live_stats | 109 | def on_live_stats(count, speed) |
| tests/test_cognitive_compression.py | function | on_thought | 112 | def on_thought(token) |
| tests/test_cognitive_compression.py | function | on_chat | 115 | def on_chat(token) |
| tests/test_cognitive_compression.py | function | on_done | 118 | def on_done(thought, response, truncated, ended_in_thought, diagnostics) |
| tests/test_cognitive_compression.py | function | test_agentic_cognitive_compression_and_live_stats | 167 | def test_agentic_cognitive_compression_and_live_stats() |
| tests/test_cognitive_compression.py | function | on_live_stats | 192 | def on_live_stats(count, speed) |
| tests/test_cognitive_compression.py | function | on_iteration_finished | 195 | def on_iteration_finished(iteration, thought, response, diagnostics) |
| tests/test_cognitive_compression.py | function | on_loop_finished | 198 | def on_loop_finished(total) |
| tests/test_cognitive_parser.py | function | test_standard_closed | 8 | def test_standard_closed() |
| tests/test_cognitive_parser.py | function | test_unclosed | 13 | def test_unclosed() |
| tests/test_cognitive_parser.py | function | test_mixed_capitalization | 18 | def test_mixed_capitalization() |
| tests/test_cognitive_parser.py | function | test_multiple_blocks | 23 | def test_multiple_blocks() |
| tests/test_cognitive_parser.py | function | test_no_blocks | 28 | def test_no_blocks() |
| tests/test_cognitive_parser_fuzz.py | function | _rnd | 51 | def _rnd(rng: random.Random, max_len: int = 80) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_nested | 55 | def _gen_nested(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_case_variation | 63 | def _gen_case_variation(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_incomplete | 74 | def _gen_incomplete(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_binary | 88 | def _gen_binary(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_emoji | 101 | def _gen_emoji(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_surrogate | 115 | def _gen_surrogate(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_huge_open_only | 123 | def _gen_huge_open_only(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_huge_close_only | 134 | def _gen_huge_close_only(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_huge_response | 140 | def _gen_huge_response(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_moderate_alternating | 146 | def _gen_moderate_alternating(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_mixed | 157 | def _gen_mixed(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _gen_trivial | 173 | def _gen_trivial(rng: random.Random) -> str |
| tests/test_cognitive_parser_fuzz.py | function | _build_inputs | 206 | def _build_inputs(n: int, seed: int) -> list[str] |
| tests/test_cognitive_parser_fuzz.py | function | _budget_ms | 217 | def _budget_ms(text: str) -> float |
| tests/test_cognitive_parser_fuzz.py | function | test_fuzz_cognitive_parser_5000_cases | 229 | def test_fuzz_cognitive_parser_5000_cases() |
| tests/test_cognitive_parser_fuzz.py | function | test_fixed_regression | 314 | def test_fixed_regression(label: str, text: str) |
| tests/test_config_store.py | function | isolated_data_dir | 15 | def isolated_data_dir(tmp_path, monkeypatch) |
| tests/test_config_store.py | function | test_read_json_missing_returns_default | 24 | def test_read_json_missing_returns_default() |
| tests/test_config_store.py | function | test_read_json_corrupt_returns_default | 28 | def test_read_json_corrupt_returns_default() |
| tests/test_config_store.py | function | test_write_json_atomic_roundtrip | 35 | def test_write_json_atomic_roundtrip() |
| tests/test_config_store.py | function | test_active_model_defaults_when_missing | 44 | def test_active_model_defaults_when_missing() |
| tests/test_config_store.py | function | test_active_model_roundtrip | 50 | def test_active_model_roundtrip() |
| tests/test_config_store.py | function | test_active_model_accepts_legacy_model_key | 56 | def test_active_model_accepts_legacy_model_key() |
| tests/test_config_store.py | function | test_registry_missing_returns_empty | 63 | def test_registry_missing_returns_empty() |
| tests/test_config_store.py | function | test_registry_caches_until_mtime_changes | 67 | def test_registry_caches_until_mtime_changes() |
| tests/test_config_store.py | function | test_registry_n_ctx_lookup_and_default | 81 | def test_registry_n_ctx_lookup_and_default() |
| tests/test_config_store.py | function | test_registry_rejects_non_list_payload | 89 | def test_registry_rejects_non_list_payload() |
| tests/test_config_store.py | function | test_adapter_compatibility_from_config_file | 94 | def test_adapter_compatibility_from_config_file() |
| tests/test_config_store.py | function | test_adapter_compatibility_name_fallback | 105 | def test_adapter_compatibility_name_fallback() |
| tests/test_config_store.py | function | test_ui_config_defaults_when_missing | 111 | def test_ui_config_defaults_when_missing() |
| tests/test_config_store.py | function | test_ui_config_roundtrip_ignores_unknown_keys | 115 | def test_ui_config_roundtrip_ignores_unknown_keys() |
| tests/test_config_store.py | function | test_ui_config_legacy_fallback | 125 | def test_ui_config_legacy_fallback() |
| tests/test_correlation_logging.py | class | _CaptureHandler | 31 | class _CaptureHandler(logging.Handler) |
| tests/test_correlation_logging.py | function | __init__ | 34 | def __init__(self) |
| tests/test_correlation_logging.py | function | emit | 39 | def emit(self, record: logging.LogRecord) -> None |
| tests/test_correlation_logging.py | function | _make_logger | 44 | def _make_logger(name: str) -> tuple[logging.Logger, _CaptureHandler] |
| tests/test_correlation_logging.py | function | test_default_correlation_id_is_system | 59 | def test_default_correlation_id_is_system() |
| tests/test_correlation_logging.py | function | _check | 64 | def _check() |
| tests/test_correlation_logging.py | function | test_concurrent_threads_have_isolated_correlation_ids | 74 | def test_concurrent_threads_have_isolated_correlation_ids() |
| tests/test_correlation_logging.py | function | thread_a | 84 | def thread_a() |
| tests/test_correlation_logging.py | function | thread_b | 90 | def thread_b() |
| tests/test_correlation_logging.py | function | test_correlation_filter_injects_attribute | 119 | def test_correlation_filter_injects_attribute() |
| tests/test_correlation_logging.py | function | test_reset_restores_previous_value | 135 | def test_reset_restores_previous_value() |
| tests/test_correlation_logging.py | function | test_new_correlation_id_returns_nonempty_string | 152 | def test_new_correlation_id_returns_nonempty_string() |
| tests/test_correlation_logging.py | function | test_log_record_format_includes_correlation_id | 159 | def test_log_record_format_includes_correlation_id() |
| tests/test_correlation_logging.py | function | test_asyncio_tasks_have_isolated_correlation_ids | 179 | def test_asyncio_tasks_have_isolated_correlation_ids() |
| tests/test_correlation_logging.py | function | test_thread_default_is_system_even_after_main_thread_sets_id | 212 | def test_thread_default_is_system_even_after_main_thread_sets_id() |
| tests/test_correlation_logging.py | function | _child | 220 | def _child() |
| tests/test_custom_agents.py | function | _running_under_bwrap | 24 | def _running_under_bwrap() -> bool |
| tests/test_custom_agents.py | class | TestCustomAgents | 32 | class TestCustomAgents(unittest.TestCase) |
| tests/test_custom_agents.py | function | setUp | 33 | def setUp(self) |
| tests/test_custom_agents.py | function | tearDown | 61 | def tearDown(self) |
| tests/test_custom_agents.py | function | _get_uri | 85 | def _get_uri(self) |
| tests/test_custom_agents.py | function | _get_ssl_context | 92 | def _get_ssl_context(self) |
| tests/test_custom_agents.py | function | test_profile_reloading | 101 | def test_profile_reloading(self) |
| tests/test_custom_agents.py | function | test_json_rpc_validation_and_listing | 143 | def test_json_rpc_validation_and_listing(self) |
| tests/test_custom_agents.py | function | test_llm_thread_custom_model_and_adapter | 232 | def test_llm_thread_custom_model_and_adapter(self, mock_get_llm) |
| tests/test_custom_agents.py | function | test_websocket_chat_custom_agent_routing | 261 | def test_websocket_chat_custom_agent_routing(self, mock_get_llm) |
| tests/test_dataset_merger.py | function | _record | 30 | def _record( user: str, assistant: str, *, |
| tests/test_dataset_merger.py | function | _write | 53 | def _write(path: str, records: list[dict]) -> None |
| tests/test_dataset_merger.py | function | _read | 60 | def _read(path: str) -> list[dict] |
| tests/test_dataset_merger.py | class | TestIsAnomalous | 67 | class TestIsAnomalous |
| tests/test_dataset_merger.py | function | test_good_record_passes | 68 | def test_good_record_passes(self) |
| tests/test_dataset_merger.py | function | test_missing_messages_key | 71 | def test_missing_messages_key(self) |
| tests/test_dataset_merger.py | function | test_messages_not_a_list | 74 | def test_messages_not_a_list(self) |
| tests/test_dataset_merger.py | function | test_too_few_messages | 77 | def test_too_few_messages(self) |
| tests/test_dataset_merger.py | function | test_no_assistant_turn | 80 | def test_no_assistant_turn(self) |
| tests/test_dataset_merger.py | function | test_empty_assistant_response | 87 | def test_empty_assistant_response(self) |
| tests/test_dataset_merger.py | function | test_traceback_dump_filtered | 91 | def test_traceback_dump_filtered(self) |
| tests/test_dataset_merger.py | function | test_latency_warning_flag_filtered | 99 | def test_latency_warning_flag_filtered(self) |
| tests/test_dataset_merger.py | function | test_long_traceback_not_filtered | 102 | def test_long_traceback_not_filtered(self) |
| tests/test_dataset_merger.py | class | TestHashing | 108 | class TestHashing |
| tests/test_dataset_merger.py | function | test_exact_hash_stable | 109 | def test_exact_hash_stable(self) |
| tests/test_dataset_merger.py | function | test_different_assistant_differs_in_exact_hash | 113 | def test_different_assistant_differs_in_exact_hash(self) |
| tests/test_dataset_merger.py | function | test_same_prompt_shares_prompt_key | 118 | def test_same_prompt_shares_prompt_key(self) |
| tests/test_dataset_merger.py | function | test_different_prompts_differ_in_prompt_key | 123 | def test_different_prompts_differ_in_prompt_key(self) |
| tests/test_dataset_merger.py | function | test_prompt_key_ignores_assistant | 128 | def test_prompt_key_ignores_assistant(self) |
| tests/test_dataset_merger.py | class | TestMergeFiles | 136 | class TestMergeFiles |
| tests/test_dataset_merger.py | function | setup_method | 137 | def setup_method(self) |
| tests/test_dataset_merger.py | function | teardown_method | 141 | def teardown_method(self) |
| tests/test_dataset_merger.py | function | _paths | 144 | def _paths(self) |
| tests/test_dataset_merger.py | function | test_return_keys_match_spec | 152 | def test_return_keys_match_spec(self) |
| tests/test_dataset_merger.py | function | test_new_record_is_added | 161 | def test_new_record_is_added(self) |
| tests/test_dataset_merger.py | function | test_multiple_new_records | 171 | def test_multiple_new_records(self) |
| tests/test_dataset_merger.py | function | test_exact_duplicate_skipped | 181 | def test_exact_duplicate_skipped(self) |
| tests/test_dataset_merger.py | function | test_same_prompt_same_response_is_duplicate | 191 | def test_same_prompt_same_response_is_duplicate(self) |
| tests/test_dataset_merger.py | function | test_multiple_duplicates_all_counted | 200 | def test_multiple_duplicates_all_counted(self) |
| tests/test_dataset_merger.py | function | test_newer_incoming_replaces_older_primary | 211 | def test_newer_incoming_replaces_older_primary(self) |
| tests/test_dataset_merger.py | function | test_older_incoming_does_not_replace_newer_primary | 222 | def test_older_incoming_does_not_replace_newer_primary(self) |
| tests/test_dataset_merger.py | function | test_same_timestamp_conflict_keeps_primary | 233 | def test_same_timestamp_conflict_keeps_primary(self) |
| tests/test_dataset_merger.py | function | test_empty_assistant_response_counted_as_error | 245 | def test_empty_assistant_response_counted_as_error(self) |
| tests/test_dataset_merger.py | function | test_latency_warning_counted_as_error | 253 | def test_latency_warning_counted_as_error(self) |
| tests/test_dataset_merger.py | function | test_traceback_response_counted_as_error | 261 | def test_traceback_response_counted_as_error(self) |
| tests/test_dataset_merger.py | function | test_malformed_json_line_skipped_gracefully | 269 | def test_malformed_json_line_skipped_gracefully(self) |
| tests/test_dataset_merger.py | function | test_missing_messages_key_counted_as_error | 282 | def test_missing_messages_key_counted_as_error(self) |
| tests/test_dataset_merger.py | function | test_does_not_crash_on_empty_incoming | 291 | def test_does_not_crash_on_empty_incoming(self) |
| tests/test_dataset_merger.py | function | test_does_not_crash_on_empty_primary | 299 | def test_does_not_crash_on_empty_primary(self) |
| tests/test_dataset_merger.py | function | test_does_not_crash_when_primary_missing | 306 | def test_does_not_crash_when_primary_missing(self) |
| tests/test_dataset_merger.py | function | test_output_is_valid_jsonl | 316 | def test_output_is_valid_jsonl(self) |
| tests/test_dataset_merger.py | function | test_primary_anomalous_records_cleaned_on_merge | 327 | def test_primary_anomalous_records_cleaned_on_merge(self) |
| tests/test_dataset_merger.py | function | test_write_is_atomic | 341 | def test_write_is_atomic(self) |
| tests/test_dataset_merger.py | function | test_validate_file_counts | 351 | def test_validate_file_counts(self) |
| tests/test_dataset_merger.py | function | test_validate_file_missing_path | 364 | def test_validate_file_missing_path(self) |
| tests/test_db_pool.py | function | _create_table | 18 | def _create_table(db_path: str) -> None |
| tests/test_db_pool.py | function | _row_count | 33 | def _row_count(db_path: str) -> int |
| tests/test_db_pool.py | function | test_connections_use_wal_journal_mode | 43 | def test_connections_use_wal_journal_mode(tmp_path) |
| tests/test_db_pool.py | function | test_connections_use_normal_synchronous | 56 | def test_connections_use_normal_synchronous(tmp_path) |
| tests/test_db_pool.py | function | test_connection_is_returned_to_pool_after_context_exit | 68 | def test_connection_is_returned_to_pool_after_context_exit(tmp_path) |
| tests/test_db_pool.py | function | test_concurrent_inserts_complete_without_lock_errors | 82 | def test_concurrent_inserts_complete_without_lock_errors(tmp_path) |
| tests/test_db_pool.py | function | worker | 97 | def worker(thread_id: int) -> None |
| tests/test_db_pool.py | function | test_final_row_count_matches_expected_acid_safety | 132 | def test_final_row_count_matches_expected_acid_safety(tmp_path) |
| tests/test_db_pool.py | function | worker | 145 | def worker(thread_id: int) -> None |
| tests/test_db_pool.py | function | test_rollback_on_exception_leaves_no_partial_rows | 186 | def test_rollback_on_exception_leaves_no_partial_rows(tmp_path) |
| tests/test_db_pool.py | function | test_semaphore_gates_concurrent_access_to_pool_size | 209 | def test_semaphore_gates_concurrent_access_to_pool_size(tmp_path) |
| tests/test_db_pool.py | function | holder | 223 | def holder() -> None |
| tests/test_db_transactions.py | class | _DeterministicEncoder | 12 | class _DeterministicEncoder |
| tests/test_db_transactions.py | function | encode | 13 | def encode(self, texts, batch_size=32, show_progress_bar=False) |
| tests/test_db_transactions.py | class | _TestRAG | 28 | class _TestRAG(RAGPipeline) |
| tests/test_db_transactions.py | function | __init__ | 29 | def __init__(self, *args, **kwargs) |
| tests/test_db_transactions.py | class | _FailAfterFaissAddRAG | 34 | class _FailAfterFaissAddRAG(_TestRAG) |
| tests/test_db_transactions.py | function | _add_embeddings_to_index | 35 | def _add_embeddings_to_index(self, embeddings, vector_ids) |
| tests/test_db_transactions.py | class | _BlockingAddRAG | 40 | class _BlockingAddRAG(_TestRAG) |
| tests/test_db_transactions.py | function | __init__ | 41 | def __init__(self, *args, entered_add: threading.Event, release_add: threading.Event, **kwargs) |
| tests/test_db_transactions.py | function | _add_embeddings_to_index | 47 | def _add_embeddings_to_index(self, embeddings, vector_ids) |
| tests/test_db_transactions.py | function | _write_doc | 56 | def _write_doc(path, name, body) |
| tests/test_db_transactions.py | function | _db_count | 63 | def _db_count(path) |
| tests/test_db_transactions.py | function | test_ingest_rolls_back_sqlite_and_faiss_when_faiss_add_fails | 71 | def test_ingest_rolls_back_sqlite_and_faiss_when_faiss_add_fails(tmp_path) |
| tests/test_db_transactions.py | function | test_wal_allows_metadata_reads_while_ingest_transaction_is_open | 88 | def test_wal_allows_metadata_reads_while_ingest_transaction_is_open(tmp_path) |
| tests/test_db_transactions.py | function | ingest_in_background | 113 | def ingest_in_background() |
| tests/test_db_transactions.py | function | test_remove_source_deletes_matching_sqlite_rows_and_faiss_vectors | 141 | def test_remove_source_deletes_matching_sqlite_rows_and_faiss_vectors(tmp_path) |
| tests/test_educational_sandbox.py | function | test_tfidf_embedder | 13 | def test_tfidf_embedder() |
| tests/test_educational_sandbox.py | function | test_char_tokenizer | 51 | def test_char_tokenizer() |
| tests/test_educational_sandbox.py | function | test_mini_gpt | 68 | def test_mini_gpt() |
| tests/test_eval_harness.py | class | MockLlama | 12 | class MockLlama |
| tests/test_eval_harness.py | function | tokenize | 13 | def tokenize(self, text_bytes, add_bos=True) |
| tests/test_eval_harness.py | function | __call__ | 16 | def __call__(self, prompt, **kwargs) |
| tests/test_eval_harness.py | function | test_eval_harness_model_and_adapter_selection | 24 | def test_eval_harness_model_and_adapter_selection() |
| tests/test_eval_harness.py | function | mock_get_instance | 35 | def mock_get_instance(model_path=None, adapter_name=None) |
| tests/test_eval_harness.py | function | test_eval_harness_failure_curation | 96 | def test_eval_harness_failure_curation() |
| tests/test_eval_harness.py | class | FailingMockLlama | 112 | class FailingMockLlama |
| tests/test_eval_harness.py | function | tokenize | 113 | def tokenize(self, text_bytes, add_bos=True) |
| tests/test_eval_harness.py | function | __call__ | 115 | def __call__(self, prompt, **kwargs) |
| tests/test_event_broker.py | function | test_event_broker_thread_safety | 9 | def test_event_broker_thread_safety() |
| tests/test_event_broker.py | function | on_event | 15 | def on_event(data) |
| tests/test_event_broker.py | function | publisher | 25 | def publisher(thread_id) |
| tests/test_failure_paths.py | function | test_model_loader_missing_file | 19 | def test_model_loader_missing_file(monkeypatch) |
| tests/test_failure_paths.py | function | mock_exists | 23 | def mock_exists(path) |
| tests/test_failure_paths.py | function | test_model_loader_corrupted_file | 34 | def test_model_loader_corrupted_file(tmp_path, monkeypatch) |
| tests/test_failure_paths.py | function | mock_llama | 41 | def mock_llama(*args, **kwargs) |
| tests/test_failure_paths.py | function | test_llm_thread_crash_recovery | 54 | def test_llm_thread_crash_recovery() |
| tests/test_failure_paths.py | function | test_introspective_parser_empty_and_malformed | 88 | def test_introspective_parser_empty_and_malformed() |
| tests/test_failure_paths.py | function | test_task_supervisor_cancel_timeout | 118 | def test_task_supervisor_cancel_timeout() |
| tests/test_failure_paths.py | class | SlowCancellable | 122 | class SlowCancellable |
| tests/test_failure_paths.py | function | request_stop | 123 | def request_stop(self) |
| tests/test_failure_paths.py | function | test_trace_logger_corrupted_jsonl | 150 | def test_trace_logger_corrupted_jsonl(tmp_path) |
| tests/test_feature_flags.py | function | _reset_safe_mode | 28 | def _reset_safe_mode() |
| tests/test_feature_flags.py | function | flags_path | 36 | def flags_path(tmp_path) -> str |
| tests/test_feature_flags.py | function | lock_path | 41 | def lock_path(tmp_path) -> str |
| tests/test_feature_flags.py | function | store | 46 | def store(flags_path) -> FeatureFlagStore |
| tests/test_feature_flags.py | function | test_default_flags_match_spec | 52 | def test_default_flags_match_spec(store) |
| tests/test_feature_flags.py | function | test_unknown_flag_returns_false | 58 | def test_unknown_flag_returns_false(store) |
| tests/test_feature_flags.py | function | test_defaults_are_persisted_on_first_load | 62 | def test_defaults_are_persisted_on_first_load(flags_path) |
| tests/test_feature_flags.py | function | test_set_flag_updates_in_memory | 74 | def test_set_flag_updates_in_memory(store) |
| tests/test_feature_flags.py | function | test_set_flag_persists_to_disk | 79 | def test_set_flag_persists_to_disk(flags_path, store) |
| tests/test_feature_flags.py | function | test_set_flag_raises_for_unknown_flag | 86 | def test_set_flag_raises_for_unknown_flag(store) |
| tests/test_feature_flags.py | function | test_set_flag_persists_false | 91 | def test_set_flag_persists_false(flags_path, store) |
| tests/test_feature_flags.py | function | test_safe_mode_disables_experimental_flags | 99 | def test_safe_mode_disables_experimental_flags(store) |
| tests/test_feature_flags.py | function | test_safe_mode_preserves_non_experimental_flags | 107 | def test_safe_mode_preserves_non_experimental_flags(store) |
| tests/test_feature_flags.py | function | test_safe_mode_sets_class_flag | 113 | def test_safe_mode_sets_class_flag(store) |
| tests/test_feature_flags.py | function | test_safe_mode_persists_experimental_flags_as_false | 119 | def test_safe_mode_persists_experimental_flags_as_false(flags_path, store) |
| tests/test_feature_flags.py | function | test_check_boot_lock_false_when_absent | 128 | def test_check_boot_lock_false_when_absent(lock_path) |
| tests/test_feature_flags.py | function | test_create_and_check_boot_lock | 132 | def test_create_and_check_boot_lock(lock_path) |
| tests/test_feature_flags.py | function | test_boot_lock_contains_timestamp | 138 | def test_boot_lock_contains_timestamp(lock_path) |
| tests/test_feature_flags.py | function | test_release_boot_lock_removes_file | 148 | def test_release_boot_lock_removes_file(lock_path) |
| tests/test_feature_flags.py | function | test_release_boot_lock_is_idempotent | 154 | def test_release_boot_lock_is_idempotent(lock_path) |
| tests/test_feature_flags.py | function | test_boot_guard_creates_lock_on_clean_boot | 161 | def test_boot_guard_creates_lock_on_clean_boot(flags_path, lock_path) |
| tests/test_feature_flags.py | function | test_boot_guard_returns_false_and_does_not_activate_safe_mode_on_clean_boot | 169 | def test_boot_guard_returns_false_and_does_not_activate_safe_mode_on_clean_boot( flags_path, lock_path ) |
| tests/test_feature_flags.py | function | test_boot_guard_detects_crash_lock_and_enters_safe_mode | 180 | def test_boot_guard_detects_crash_lock_and_enters_safe_mode(flags_path, lock_path) |
| tests/test_feature_flags.py | function | test_boot_guard_crash_recovery_persists_safe_flags | 222 | def test_boot_guard_crash_recovery_persists_safe_flags(flags_path, lock_path) |
| tests/test_feature_flags.py | function | test_boot_guard_does_not_remove_lock_on_crash_detection | 235 | def test_boot_guard_does_not_remove_lock_on_crash_detection(flags_path, lock_path) |
| tests/test_feature_flags.py | function | test_all_flags_returns_complete_dict | 252 | def test_all_flags_returns_complete_dict(store) |
| tests/test_feature_flags.py | function | test_all_flags_returns_copy | 257 | def test_all_flags_returns_copy(store) |
| tests/test_hardware_scout.py | function | test_hardware_profile_structure | 11 | def test_hardware_profile_structure() |
| tests/test_hardware_scout.py | function | test_hardware_profile_gpu_mocking | 30 | def test_hardware_profile_gpu_mocking() |
| tests/test_hardware_scout.py | class | DummyGPU | 32 | class DummyGPU |
| tests/test_hardware_scout.py | function | __init__ | 33 | def __init__(self, memory_free) |
| tests/test_hardware_scout.py | function | test_hardware_profile_gpu_exception_fallback | 45 | def test_hardware_profile_gpu_exception_fallback() |
| tests/test_image_store.py | function | _sample_image | 12 | def _sample_image(width=80, height=48) |
| tests/test_image_store.py | function | test_save_qimage_creates_record_and_files | 18 | def test_save_qimage_creates_record_and_files(tmp_path) |
| tests/test_image_store.py | function | test_import_file_copies_image | 37 | def test_import_file_copies_image(tmp_path) |
| tests/test_image_store.py | function | test_update_analysis_round_trip | 50 | def test_update_analysis_round_trip(tmp_path) |
| tests/test_image_store.py | function | test_update_analysis_accepts_ocr_dict | 61 | def test_update_analysis_accepts_ocr_dict(tmp_path) |
| tests/test_image_store.py | function | test_image_metadata_and_corrections_round_trip | 73 | def test_image_metadata_and_corrections_round_trip(tmp_path) |
| tests/test_inference_safety.py | function | test_model_reset_blocked_during_active_generation | 11 | def test_model_reset_blocked_during_active_generation() |
| tests/test_inference_safety.py | function | test_model_reload_or_adapter_change_blocked_during_active_generation | 26 | def test_model_reload_or_adapter_change_blocked_during_active_generation() |
| tests/test_inference_safety.py | function | test_failed_acquire_does_not_release_existing_generation | 60 | def test_failed_acquire_does_not_release_existing_generation() |
| tests/test_inference_safety.py | function | test_offline_guard_blocks_external_http_by_default | 85 | def test_offline_guard_blocks_external_http_by_default(monkeypatch) |
| tests/test_inference_safety.py | function | test_offline_guard_allows_localhost_by_default | 93 | def test_offline_guard_allows_localhost_by_default(monkeypatch) |
| tests/test_inference_safety.py | function | test_offline_guard_env_allows_external | 101 | def test_offline_guard_env_allows_external(monkeypatch) |
| tests/test_inference_safety.py | function | test_requests_external_call_is_blocked_before_network | 108 | def test_requests_external_call_is_blocked_before_network(monkeypatch) |
| tests/test_inference_safety.py | function | test_agentic_stream_generator_closes_on_cancel | 117 | def test_agentic_stream_generator_closes_on_cancel() |
| tests/test_inference_safety.py | class | FakeStream | 120 | class FakeStream |
| tests/test_inference_safety.py | function | __init__ | 121 | def __init__(self) |
| tests/test_inference_safety.py | function | __iter__ | 124 | def __iter__(self) |
| tests/test_inference_safety.py | function | close | 127 | def close(self) |
| tests/test_inference_safety.py | class | FakeLLM | 130 | class FakeLLM |
| tests/test_inference_safety.py | function | __init__ | 131 | def __init__(self) |
| tests/test_inference_safety.py | function | __call__ | 134 | def __call__(self, *args, **kwargs) |
| tests/test_inference_safety.py | function | tokenize | 137 | def tokenize(self, data, add_bos=False) |
| tests/test_inference_safety.py | function | test_llm_thread_request_stop_sets_flag | 153 | def test_llm_thread_request_stop_sets_flag() |
| tests/test_inference_safety.py | function | test_llm_thread_stop_flag_prevents_generation | 166 | def test_llm_thread_stop_flag_prevents_generation() |
| tests/test_inference_safety.py | class | FakeStream | 171 | class FakeStream |
| tests/test_inference_safety.py | function | __iter__ | 172 | def __iter__(self) |
| tests/test_inference_safety.py | function | close | 175 | def close(self) |
| tests/test_inference_safety.py | function | test_active_generation_count_increments_and_decrements | 196 | def test_active_generation_count_increments_and_decrements() |
| tests/test_inference_safety.py | function | test_inference_error_message_is_descriptive | 221 | def test_inference_error_message_is_descriptive() |
| tests/test_inference_safety.py | function | test_hf_offline_vars_applied_when_offline | 239 | def test_hf_offline_vars_applied_when_offline(monkeypatch) |
| tests/test_inference_safety.py | function | test_hf_offline_vars_cleared_when_online | 257 | def test_hf_offline_vars_cleared_when_online(monkeypatch) |
| tests/test_inference_safety.py | function | test_guard_install_is_idempotent | 275 | def test_guard_install_is_idempotent() |
| tests/test_inference_service.py | class | _FakeLLMThread | 21 | class _FakeLLMThread(QThread) |
| tests/test_inference_service.py | function | __init__ | 40 | def __init__(self, **kwargs) |
| tests/test_inference_service.py | function | run | 45 | def run(self) |
| tests/test_inference_service.py | class | _FakeAgenticThread | 58 | class _FakeAgenticThread(QThread) |
| tests/test_inference_service.py | function | __init__ | 74 | def __init__(self, **kwargs) |
| tests/test_inference_service.py | function | run | 80 | def run(self) |
| tests/test_inference_service.py | function | service | 88 | def service(monkeypatch) |
| tests/test_inference_service.py | function | _drain | 97 | def _drain(ms: int = 200) -> None |
| tests/test_inference_service.py | function | test_single_shot_creates_llm_thread | 108 | def test_single_shot_creates_llm_thread(service, monkeypatch) |
| tests/test_inference_service.py | class | _Spy | 115 | class _Spy(_OrigFake) |
| tests/test_inference_service.py | function | __init__ | 116 | def __init__(self, **kw) |
| tests/test_inference_service.py | function | test_agentic_flag_creates_agentic_thread | 132 | def test_agentic_flag_creates_agentic_thread(service, monkeypatch) |
| tests/test_inference_service.py | class | _Spy | 139 | class _Spy(_OrigFake) |
| tests/test_inference_service.py | function | __init__ | 140 | def __init__(self, **kw) |
| tests/test_inference_service.py | function | test_hyperparams_agentic_flag_selects_agentic_thread | 157 | def test_hyperparams_agentic_flag_selects_agentic_thread(service, monkeypatch) |
| tests/test_inference_service.py | class | _Spy | 164 | class _Spy(_OrigFake) |
| tests/test_inference_service.py | function | __init__ | 165 | def __init__(self, **kw) |
| tests/test_inference_service.py | function | test_on_token_cb_receives_chat_tokens | 184 | def test_on_token_cb_receives_chat_tokens(service) |
| tests/test_inference_service.py | function | test_on_thought_token_cb_receives_thought_tokens | 201 | def test_on_thought_token_cb_receives_thought_tokens(service) |
| tests/test_inference_service.py | function | test_on_finished_cb_called_with_normalised_args_for_llm | 218 | def test_on_finished_cb_called_with_normalised_args_for_llm(service) |
| tests/test_inference_service.py | function | _cb | 222 | def _cb(thought, response, diagnostics) |
| tests/test_inference_service.py | function | test_on_finished_cb_called_for_agentic_thread | 242 | def test_on_finished_cb_called_for_agentic_thread(service) |
| tests/test_inference_service.py | function | _cb | 246 | def _cb(thought, response, diagnostics) |
| tests/test_inference_service.py | function | test_on_error_cb_called_on_error | 266 | def test_on_error_cb_called_on_error(service, monkeypatch) |
| tests/test_inference_service.py | class | _ErrorThread | 270 | class _ErrorThread(_FakeLLMThread) |
| tests/test_inference_service.py | function | run | 271 | def run(self) |
| tests/test_inference_service.py | function | test_on_live_stats_cb_called | 290 | def test_on_live_stats_cb_called(service) |
| tests/test_inference_service.py | function | test_thread_added_to_active_set_while_running | 307 | def test_thread_added_to_active_set_while_running(service) |
| tests/test_inference_service.py | class | _TrackThread | 311 | class _TrackThread(_FakeLLMThread) |
| tests/test_inference_service.py | function | run | 312 | def run(self) |
| tests/test_inference_service.py | function | test_thread_is_already_started_on_return | 340 | def test_thread_is_already_started_on_return(service) |
| tests/test_kv_quantization.py | function | _reset_model_loader_state | 4 | def _reset_model_loader_state(ModelLoader) |
| tests/test_kv_quantization.py | function | _run_loader_with_patches | 15 | def _run_loader_with_patches(fake_llama) |
| tests/test_kv_quantization.py | function | test_quantized_kv_cache_passes_q8_type_overrides_to_llama | 59 | def test_quantized_kv_cache_passes_q8_type_overrides_to_llama() |
| tests/test_kv_quantization.py | function | fake_llama | 62 | def fake_llama(**kwargs) |
| tests/test_kv_quantization.py | function | test_quantized_kv_cache_falls_back_when_type_overrides_are_unsupported | 73 | def test_quantized_kv_cache_falls_back_when_type_overrides_are_unsupported() |
| tests/test_kv_quantization.py | function | fake_llama | 77 | def fake_llama(**kwargs) |
| tests/test_local_tracing.py | function | read_trace_file | 7 | def read_trace_file(trace_dir) |
| tests/test_local_tracing.py | function | test_nested_spans_register_under_parent_and_persist_schema | 15 | def test_nested_spans_register_under_parent_and_persist_schema(tmp_path) |
| tests/test_local_tracing.py | function | test_span_exception_marks_error_and_preserves_exception | 42 | def test_span_exception_marks_error_and_preserves_exception(tmp_path) |
| tests/test_local_tracing.py | function | test_execution_time_is_calculated_accurately_enough | 60 | def test_execution_time_is_calculated_accurately_enough(tmp_path) |
| tests/test_log_governance.py | function | test_log_retention_policy_enforcement | 10 | def test_log_retention_policy_enforcement() |
| tests/test_mcp_client.py | function | _running_under_bwrap | 22 | def _running_under_bwrap() -> bool |
| tests/test_mcp_client.py | class | TestMCPClient | 30 | class TestMCPClient(unittest.TestCase) |
| tests/test_mcp_client.py | function | setUp | 31 | def setUp(self) |
| tests/test_mcp_client.py | function | tearDown | 54 | def tearDown(self) |
| tests/test_mcp_client.py | function | test_mcp_client_lifecycle_and_tools | 60 | def test_mcp_client_lifecycle_and_tools(self) |
| tests/test_memory_manager.py | function | test_memory_manager_flat_history | 12 | def test_memory_manager_flat_history() |
| tests/test_memory_manager.py | function | test_memory_manager_tree_history | 53 | def test_memory_manager_tree_history() |
| tests/test_memory_repository.py | class | MockInMemoryRepository | 8 | class MockInMemoryRepository |
| tests/test_memory_repository.py | function | __init__ | 9 | def __init__(self) |
| tests/test_memory_repository.py | function | save | 12 | def save(self, session_id: str, session_tree: dict) -> None |
| tests/test_memory_repository.py | function | get | 15 | def get(self, session_id: str) -> dict \| None |
| tests/test_memory_repository.py | function | list_all | 18 | def list_all(self) -> list[dict] |
| tests/test_memory_repository.py | function | delete | 25 | def delete(self, session_id: str) -> bool |
| tests/test_memory_repository.py | function | test_memory_manager_with_mock_repository | 31 | def test_memory_manager_with_mock_repository() |
| tests/test_model_circuit_breaker.py | class | FakeClock | 12 | class FakeClock |
| tests/test_model_circuit_breaker.py | function | __init__ | 13 | def __init__(self) |
| tests/test_model_circuit_breaker.py | function | __call__ | 16 | def __call__(self) |
| tests/test_model_circuit_breaker.py | function | advance | 19 | def advance(self, seconds: float) |
| tests/test_model_circuit_breaker.py | function | isolated_model_loader | 24 | def isolated_model_loader() |
| tests/test_model_circuit_breaker.py | function | _loader_patches | 66 | def _loader_patches() |
| tests/test_model_circuit_breaker.py | function | test_model_circuit_breaker_trips_after_three_terminal_load_failures | 80 | def test_model_circuit_breaker_trips_after_three_terminal_load_failures(isolated_model_loader) |
| tests/test_model_circuit_breaker.py | function | test_model_circuit_breaker_half_open_success_resets_to_closed | 107 | def test_model_circuit_breaker_half_open_success_resets_to_closed(isolated_model_loader) |
| tests/test_observability_telemetry.py | class | MockState | 11 | class MockState |
| tests/test_observability_telemetry.py | function | test_telemetry_metrics_calculation | 14 | def test_telemetry_metrics_calculation() |
| tests/test_ocr_engine.py | function | test_parse_tsv_extracts_text_confidence_and_boxes | 9 | def test_parse_tsv_extracts_text_confidence_and_boxes() |
| tests/test_ocr_engine.py | function | test_unavailable_tesseract_returns_structured_error | 25 | def test_unavailable_tesseract_returns_structured_error(tmp_path) |
| tests/test_prometheus_exporter.py | function | make_manager | 10 | def make_manager() |
| tests/test_prometheus_exporter.py | function | make_request | 22 | def make_request(path, headers=None) |
| tests/test_prometheus_exporter.py | function | response_text | 26 | def response_text(response) |
| tests/test_prometheus_exporter.py | function | test_prometheus_metrics_exposition_contains_expected_headers | 30 | def test_prometheus_metrics_exposition_contains_expected_headers() |
| tests/test_prometheus_exporter.py | function | test_metrics_http_request_returns_200_prometheus_text | 47 | def test_metrics_http_request_returns_200_prometheus_text() |
| tests/test_prometheus_exporter.py | function | test_non_websocket_http_request_returns_404 | 59 | def test_non_websocket_http_request_returns_404() |
| tests/test_prometheus_exporter.py | function | test_websocket_upgrade_bypasses_http_interceptor | 68 | def test_websocket_upgrade_bypasses_http_interceptor() |
| tests/test_prometheus_exporter.py | function | test_generation_diagnostics_update_last_metrics | 78 | def test_generation_diagnostics_update_last_metrics() |
| tests/test_prompt_caching.py | function | _make_fake_llm | 30 | def _make_fake_llm(tokens_in_cache: int = 0) -> MagicMock |
| tests/test_prompt_caching.py | function | _model_available | 59 | def _model_available() -> bool |
| tests/test_prompt_caching.py | class | TestKvCacheStats | 65 | class TestKvCacheStats |
| tests/test_prompt_caching.py | function | test_no_cache_attached | 66 | def test_no_cache_attached(self) |
| tests/test_prompt_caching.py | function | test_cold_cache_miss | 74 | def test_cold_cache_miss(self) |
| tests/test_prompt_caching.py | function | test_full_cache_hit | 85 | def test_full_cache_hit(self) |
| tests/test_prompt_caching.py | function | test_partial_cache_hit | 101 | def test_partial_cache_hit(self) |
| tests/test_prompt_caching.py | function | test_exception_does_not_raise | 113 | def test_exception_does_not_raise(self) |
| tests/test_prompt_caching.py | class | TestLogCacheStats | 127 | class TestLogCacheStats |
| tests/test_prompt_caching.py | function | test_writes_valid_jsonl | 128 | def test_writes_valid_jsonl(self) |
| tests/test_prompt_caching.py | function | test_appends_multiple_entries | 146 | def test_appends_multiple_entries(self) |
| tests/test_prompt_caching.py | function | test_silently_ignores_io_error | 160 | def test_silently_ignores_io_error(self) |
| tests/test_prompt_caching.py | class | TestAttachKvCache | 170 | class TestAttachKvCache |
| tests/test_prompt_caching.py | function | setup_method | 171 | def setup_method(self) |
| tests/test_prompt_caching.py | function | teardown_method | 177 | def teardown_method(self) |
| tests/test_prompt_caching.py | function | test_attaches_ram_cache_when_vram_sufficient | 182 | def test_attaches_ram_cache_when_vram_sufficient(self) |
| tests/test_prompt_caching.py | function | test_vram_guard_skips_cache_below_500mb | 198 | def test_vram_guard_skips_cache_below_500mb(self) |
| tests/test_prompt_caching.py | function | test_cache_disabled_flag_skips_attachment | 210 | def test_cache_disabled_flag_skips_attachment(self) |
| tests/test_prompt_caching.py | function | test_capacity_clamped_to_2gb_max | 222 | def test_capacity_clamped_to_2gb_max(self) |
| tests/test_prompt_caching.py | function | test_capacity_floored_at_256mb_min | 238 | def test_capacity_floored_at_256mb_min(self) |
| tests/test_prompt_caching.py | class | TestResetClearsCache | 256 | class TestResetClearsCache |
| tests/test_prompt_caching.py | function | test_set_cache_none_called_on_reset | 257 | def test_set_cache_none_called_on_reset(self) |
| tests/test_prompt_caching.py | class | TestAttemptLoadKwargs | 298 | class TestAttemptLoadKwargs |
| tests/test_prompt_caching.py | function | test_n_batch_and_flash_attn_passed_to_llama | 306 | def test_n_batch_and_flash_attn_passed_to_llama(self) |
| tests/test_prompt_caching.py | function | fake_llama | 318 | def fake_llama(**kw) |
| tests/test_prompt_caching.py | function | test_ttft_speedup_with_shared_prefix | 365 | def test_ttft_speedup_with_shared_prefix() |
| tests/test_prompt_caching.py | function | _first_token_latency | 404 | def _first_token_latency(prompt: str) -> float |
| tests/test_prompt_caching.py | function | test_cached_output_matches_noncached_at_zero_temperature | 428 | def test_cached_output_matches_noncached_at_zero_temperature() |
| tests/test_prompt_caching.py | function | _generate | 441 | def _generate(llm: Llama) -> str |
| tests/test_rag_pipeline.py | class | _DeterministicEncoder | 15 | class _DeterministicEncoder |
| tests/test_rag_pipeline.py | function | encode | 16 | def encode(self, texts, batch_size=32, show_progress_bar=False) |
| tests/test_rag_pipeline.py | class | _SlowParseRAG | 31 | class _SlowParseRAG(RAGPipeline) |
| tests/test_rag_pipeline.py | function | __init__ | 32 | def __init__(self, *args, delay=0.01, **kwargs) |
| tests/test_rag_pipeline.py | function | _chunks_from_file | 37 | def _chunks_from_file(self, filepath: str, chunk_size: int, overlap: int) |
| tests/test_rag_pipeline.py | function | test_rag_pipeline_chunking | 43 | def test_rag_pipeline_chunking() |
| tests/test_rag_pipeline.py | function | test_rag_pipeline_ingestion_and_retrieval | 71 | def test_rag_pipeline_ingestion_and_retrieval() |
| tests/test_rag_pipeline.py | function | test_rag_pipeline_retrieve_with_metadata_threshold | 151 | def test_rag_pipeline_retrieve_with_metadata_threshold() |
| tests/test_rag_pipeline.py | function | test_rag_pipeline_attribution | 176 | def test_rag_pipeline_attribution() |
| tests/test_rag_pipeline.py | function | test_parallel_batch_ingestion_benchmark_100_mock_python_files | 207 | def test_parallel_batch_ingestion_benchmark_100_mock_python_files() |
| tests/test_rag_pipeline.py | function | test_parallel_batch_ingestion_matches_sequential_index_results | 243 | def test_parallel_batch_ingestion_matches_sequential_index_results() |
| tests/test_rag_reranker.py | class | _DeterministicEncoder | 27 | class _DeterministicEncoder |
| tests/test_rag_reranker.py | function | encode | 30 | def encode(self, texts, batch_size: int = 32, show_progress_bar: bool = False) |
| tests/test_rag_reranker.py | function | _make_pipeline | 45 | def _make_pipeline(index_path: str) -> RAGPipeline |
| tests/test_rag_reranker.py | function | tmp_dir | 54 | def tmp_dir() |
| tests/test_rag_reranker.py | function | rag | 61 | def rag(tmp_dir) |
| tests/test_rag_reranker.py | function | _ingest_all | 93 | def _ingest_all(rag: RAGPipeline) -> None |
| tests/test_rag_reranker.py | function | _make_reranker_mock | 98 | def _make_reranker_mock() -> MagicMock |
| tests/test_rag_reranker.py | function | _predict | 101 | def _predict(pairs: list[tuple[str, str]]) -> np.ndarray |
| tests/test_rag_reranker.py | function | test_reranker_overrides_rrf_ordering | 119 | def test_reranker_overrides_rrf_ordering(rag) |
| tests/test_rag_reranker.py | function | test_reranker_scores_descend_monotonically | 148 | def test_reranker_scores_descend_monotonically(rag) |
| tests/test_rag_reranker.py | function | test_rerank_score_key_attached_to_all_results | 163 | def test_rerank_score_key_attached_to_all_results(rag) |
| tests/test_rag_reranker.py | function | test_rrf_score_still_present_after_reranking | 175 | def test_rrf_score_still_present_after_reranking(rag) |
| tests/test_rag_reranker.py | function | test_rank_field_reflects_reranked_position | 186 | def test_rank_field_reflects_reranked_position(rag) |
| tests/test_rag_reranker.py | function | test_reranker_called_with_query_chunk_pairs | 201 | def test_reranker_called_with_query_chunk_pairs(rag) |
| tests/test_rag_reranker.py | function | test_reranker_pool_limited_by_rerank_candidates | 223 | def test_reranker_pool_limited_by_rerank_candidates(rag) |
| tests/test_rag_reranker.py | function | _predict | 230 | def _predict(pairs) |
| tests/test_rag_reranker.py | function | test_top_k_slices_after_reranking | 245 | def test_top_k_slices_after_reranking(rag) |
| tests/test_rag_reranker.py | function | test_fallback_to_rrf_when_reranker_property_returns_none | 261 | def test_fallback_to_rrf_when_reranker_property_returns_none(rag) |
| tests/test_rag_reranker.py | function | test_fallback_to_rrf_on_predict_exception | 275 | def test_fallback_to_rrf_on_predict_exception(rag) |
| tests/test_rag_reranker.py | function | test_no_reranker_call_without_use_reranker_flag | 291 | def test_no_reranker_call_without_use_reranker_flag(rag) |
| tests/test_rag_reranker.py | function | test_no_rerank_score_in_plain_hybrid_results | 304 | def test_no_rerank_score_in_plain_hybrid_results(rag) |
| tests/test_rag_reranker.py | function | test_reranker_lazy_loads_on_first_property_access | 318 | def test_reranker_lazy_loads_on_first_property_access(rag) |
| tests/test_rag_reranker.py | function | test_reranker_property_returns_none_and_does_not_retry_on_load_failure | 330 | def test_reranker_property_returns_none_and_does_not_retry_on_load_failure(rag) |
| tests/test_rag_reranker.py | function | test_reranker_property_caches_successful_instance | 351 | def test_reranker_property_caches_successful_instance(rag) |
| tests/test_rag_reranker.py | function | test_retrieve_hybrid_with_reranker_on_empty_index_returns_empty | 365 | def test_retrieve_hybrid_with_reranker_on_empty_index_returns_empty(rag) |
| tests/test_rbac_scopes.py | function | _stub_init_security | 41 | def _stub_init_security(self) -> None |
| tests/test_rbac_scopes.py | class | _TestServer | 50 | class _TestServer |
| tests/test_rbac_scopes.py | function | __enter__ | 53 | def __enter__(self) |
| tests/test_rbac_scopes.py | function | __exit__ | 72 | def __exit__(self, *_) |
| tests/test_rbac_scopes.py | function | _url | 83 | def _url(port: int, token: str) -> str |
| tests/test_rbac_scopes.py | function | test_invalid_token_rejected_with_4001 | 103 | def test_invalid_token_rejected_with_4001() |
| tests/test_rbac_scopes.py | function | test_read_telemetry_scope_allows_get_runtime_status | 129 | def test_read_telemetry_scope_allows_get_runtime_status() |
| tests/test_rbac_scopes.py | function | test_read_telemetry_scope_denied_for_submit_chat | 139 | def test_read_telemetry_scope_denied_for_submit_chat() |
| tests/test_rbac_scopes.py | function | test_read_telemetry_scope_denied_for_submit_task | 154 | def test_read_telemetry_scope_denied_for_submit_task() |
| tests/test_rbac_scopes.py | function | test_read_kb_scope_allows_search_kb_but_denies_ingest | 167 | def test_read_kb_scope_allows_search_kb_but_denies_ingest() |
| tests/test_rbac_scopes.py | function | test_admin_token_can_call_all_scoped_methods | 193 | def test_admin_token_can_call_all_scoped_methods() |
| tests/test_rbac_scopes.py | function | test_method_scopes_map_is_complete | 208 | def test_method_scopes_map_is_complete() |
| tests/test_rbac_scopes.py | function | test_add_scoped_token_registers_new_token | 225 | def test_add_scoped_token_registers_new_token() |
| tests/test_rbac_scopes.py | function | test_generate_scoped_token_cli | 244 | def test_generate_scoped_token_cli(tmp_path) |
| tests/test_remote_offloading.py | function | test_remote_rpc_timeout_disables_remote_and_streams_local_fallback | 6 | def test_remote_rpc_timeout_disables_remote_and_streams_local_fallback(monkeypatch) |
| tests/test_remote_offloading.py | class | FailingWebSocketContext | 15 | class FailingWebSocketContext |
| tests/test_remote_offloading.py | function | fake_connect | 22 | def fake_connect(url, ssl=None, close_timeout=None) |
| tests/test_remote_offloading.py | class | LocalFallbackModel | 34 | class LocalFallbackModel |
| tests/test_remote_offloading.py | function | __call__ | 35 | def __call__(self, prompt, **kwargs) |
| tests/test_remote_offloading.py | function | on_fallback | 40 | def on_fallback(reason) |
| tests/test_remote_offloading.py | function | test_model_loader_remote_fallback_persists_disabled | 74 | def test_model_loader_remote_fallback_persists_disabled(monkeypatch) |
| tests/test_security_guards.py | function | _make_server | 30 | def _make_server() |
| tests/test_security_guards.py | class | TestIsSafePath | 48 | class TestIsSafePath(unittest.TestCase) |
| tests/test_security_guards.py | function | setUp | 50 | def setUp(self) |
| tests/test_security_guards.py | function | test_blocks_etc | 56 | def test_blocks_etc(self) |
| tests/test_security_guards.py | function | test_blocks_root_dir | 59 | def test_blocks_root_dir(self) |
| tests/test_security_guards.py | function | test_blocks_proc | 62 | def test_blocks_proc(self) |
| tests/test_security_guards.py | function | test_blocks_sys | 65 | def test_blocks_sys(self) |
| tests/test_security_guards.py | function | test_blocks_usr_bin | 68 | def test_blocks_usr_bin(self) |
| tests/test_security_guards.py | function | test_tmp_is_not_blocked | 71 | def test_tmp_is_not_blocked(self) |
| tests/test_security_guards.py | function | test_blocks_home_root | 77 | def test_blocks_home_root(self) |
| tests/test_security_guards.py | function | test_blocks_ssh_dir | 81 | def test_blocks_ssh_dir(self) |
| tests/test_security_guards.py | function | test_blocks_aws_credentials | 85 | def test_blocks_aws_credentials(self) |
| tests/test_security_guards.py | function | test_blocks_gnupg | 89 | def test_blocks_gnupg(self) |
| tests/test_security_guards.py | function | test_blocks_kube_config | 93 | def test_blocks_kube_config(self) |
| tests/test_security_guards.py | function | test_allows_project_root_itself | 99 | def test_allows_project_root_itself(self) |
| tests/test_security_guards.py | function | test_allows_file_inside_project | 102 | def test_allows_file_inside_project(self) |
| tests/test_security_guards.py | function | test_allows_data_dir | 107 | def test_allows_data_dir(self) |
| tests/test_security_guards.py | function | test_empty_string_is_unsafe | 114 | def test_empty_string_is_unsafe(self) |
| tests/test_security_guards.py | function | test_none_is_unsafe | 117 | def test_none_is_unsafe(self) |
| tests/test_security_guards.py | function | test_symlink_into_blocked_dir_is_blocked | 122 | def test_symlink_into_blocked_dir_is_blocked(self) |
| tests/test_security_guards.py | function | test_symlink_inside_project_is_allowed | 134 | def test_symlink_inside_project_is_allowed(self) |
| tests/test_security_guards.py | class | TestCollectKbFiles | 150 | class TestCollectKbFiles(unittest.TestCase) |
| tests/test_security_guards.py | function | setUp | 152 | def setUp(self) |
| tests/test_security_guards.py | function | tearDown | 156 | def tearDown(self) |
| tests/test_security_guards.py | function | test_collects_supported_extensions | 159 | def test_collects_supported_extensions(self) |
| tests/test_security_guards.py | function | test_returns_realpath_for_each_file | 171 | def test_returns_realpath_for_each_file(self) |
| tests/test_security_guards.py | function | test_raises_on_unsupported_single_file | 178 | def test_raises_on_unsupported_single_file(self) |
| tests/test_security_guards.py | function | test_raises_on_missing_path | 184 | def test_raises_on_missing_path(self) |
| tests/test_security_guards.py | function | test_symlink_to_blocked_dir_not_followed_in_recursive_walk | 188 | def test_symlink_to_blocked_dir_not_followed_in_recursive_walk(self) |
| tests/test_security_guards.py | class | TestCreateAgentValidation | 206 | class TestCreateAgentValidation(unittest.TestCase) |
| tests/test_security_guards.py | function | setUp | 212 | def setUp(self) |
| tests/test_security_guards.py | function | _validate_base_model | 215 | def _validate_base_model(self, base_model) |
| tests/test_security_guards.py | function | _validate_adapter | 231 | def _validate_adapter(self, adapter) |
| tests/test_security_guards.py | function | test_base_model_none_is_allowed | 249 | def test_base_model_none_is_allowed(self) |
| tests/test_security_guards.py | function | test_base_model_path_separator_rejected | 252 | def test_base_model_path_separator_rejected(self) |
| tests/test_security_guards.py | function | test_base_model_path_separator_slash_rejected | 256 | def test_base_model_path_separator_slash_rejected(self) |
| tests/test_security_guards.py | function | test_base_model_non_gguf_extension_rejected | 260 | def test_base_model_non_gguf_extension_rejected(self) |
| tests/test_security_guards.py | function | test_base_model_empty_string_rejected | 264 | def test_base_model_empty_string_rejected(self) |
| tests/test_security_guards.py | function | test_base_model_valid_requires_file_to_exist | 268 | def test_base_model_valid_requires_file_to_exist(self) |
| tests/test_security_guards.py | function | test_base_model_valid_when_file_exists | 272 | def test_base_model_valid_when_file_exists(self) |
| tests/test_security_guards.py | function | test_adapter_none_is_allowed | 286 | def test_adapter_none_is_allowed(self) |
| tests/test_security_guards.py | function | test_adapter_path_separator_rejected | 289 | def test_adapter_path_separator_rejected(self) |
| tests/test_security_guards.py | function | test_adapter_slash_prefix_rejected | 293 | def test_adapter_slash_prefix_rejected(self) |
| tests/test_security_guards.py | function | test_adapter_empty_string_rejected | 297 | def test_adapter_empty_string_rejected(self) |
| tests/test_security_guards.py | function | test_adapter_valid_requires_dir_to_exist | 301 | def test_adapter_valid_requires_dir_to_exist(self) |
| tests/test_security_guards.py | function | test_adapter_valid_when_dir_exists | 305 | def test_adapter_valid_when_dir_exists(self) |
| tests/test_security_guards.py | class | TestSetActiveModelAdapter | 319 | class TestSetActiveModelAdapter(unittest.TestCase) |
| tests/test_security_guards.py | function | setUp | 321 | def setUp(self) |
| tests/test_security_guards.py | function | test_adapter_with_path_separator_raises | 324 | def test_adapter_with_path_separator_raises(self) |
| tests/test_security_guards.py | function | test_missing_model_raises_file_not_found | 338 | def test_missing_model_raises_file_not_found(self) |
| tests/test_security_guards.py | function | test_model_with_path_separator_raises_value_error | 342 | def test_model_with_path_separator_raises_value_error(self) |
| tests/test_security_guards.py | class | TestAutoTrainInputSanitization | 349 | class TestAutoTrainInputSanitization(unittest.TestCase) |
| tests/test_security_guards.py | function | test_valid_topic | 359 | def test_valid_topic(self) |
| tests/test_security_guards.py | function | test_topic_with_semicolon_rejected | 364 | def test_topic_with_semicolon_rejected(self) |
| tests/test_security_guards.py | function | test_topic_with_backtick_rejected | 367 | def test_topic_with_backtick_rejected(self) |
| tests/test_security_guards.py | function | test_topic_with_slash_rejected | 370 | def test_topic_with_slash_rejected(self) |
| tests/test_security_guards.py | function | test_topic_with_dollar_rejected | 373 | def test_topic_with_dollar_rejected(self) |
| tests/test_security_guards.py | function | test_topic_starting_with_special_char_rejected | 376 | def test_topic_starting_with_special_char_rejected(self) |
| tests/test_security_guards.py | function | test_valid_adapter_name | 381 | def test_valid_adapter_name(self) |
| tests/test_security_guards.py | function | test_adapter_name_with_space_rejected | 386 | def test_adapter_name_with_space_rejected(self) |
| tests/test_security_guards.py | function | test_adapter_name_with_slash_rejected | 389 | def test_adapter_name_with_slash_rejected(self) |
| tests/test_security_guards.py | function | test_adapter_name_with_dot_rejected | 392 | def test_adapter_name_with_dot_rejected(self) |
| tests/test_security_guards.py | function | test_adapter_name_empty_rejected | 395 | def test_adapter_name_empty_rejected(self) |
| tests/test_security_guards.py | class | TestXssEscaping | 401 | class TestXssEscaping(unittest.TestCase) |
| tests/test_security_guards.py | function | setUp | 404 | def setUp(self) |
| tests/test_security_guards.py | function | test_escape_lt_gt | 409 | def test_escape_lt_gt(self) |
| tests/test_security_guards.py | function | test_escape_ampersand | 414 | def test_escape_ampersand(self) |
| tests/test_security_guards.py | function | test_escape_converts_newlines_to_br | 419 | def test_escape_converts_newlines_to_br(self) |
| tests/test_security_guards.py | function | test_escape_pre_keeps_newlines | 424 | def test_escape_pre_keeps_newlines(self) |
| tests/test_security_guards.py | function | test_escape_pre_still_escapes_html | 429 | def test_escape_pre_still_escapes_html(self) |
| tests/test_security_guards.py | function | test_escape_event_handler_injection | 434 | def test_escape_event_handler_injection(self) |
| tests/test_security_guards.py | function | test_escape_script_in_code_block | 439 | def test_escape_script_in_code_block(self) |
| tests/test_security_guards.py | class | TestPromptPairNameSanitization | 448 | class TestPromptPairNameSanitization(unittest.TestCase) |
| tests/test_security_guards.py | function | setUp | 450 | def setUp(self) |
| tests/test_security_guards.py | function | test_alphanumeric_and_safe_chars_preserved | 453 | def test_alphanumeric_and_safe_chars_preserved(self) |
| tests/test_security_guards.py | function | test_special_chars_replaced | 456 | def test_special_chars_replaced(self) |
| tests/test_security_guards.py | function | test_empty_name_raises | 461 | def test_empty_name_raises(self) |
| tests/test_security_guards.py | function | test_spaces_replaced | 465 | def test_spaces_replaced(self) |
| tests/test_security_guards.py | function | test_null_bytes_stripped | 469 | def test_null_bytes_stripped(self) |
| tests/test_security_sandbox.py | function | test_root_block_exits_on_getuid_zero | 24 | def test_root_block_exits_on_getuid_zero() |
| tests/test_security_sandbox.py | function | test_root_block_allows_normal_user | 35 | def test_root_block_allows_normal_user() |
| tests/test_security_sandbox.py | function | test_safe_workspace_path_empty_rel_blocked | 49 | def test_safe_workspace_path_empty_rel_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_safe_workspace_path_parent_traversal_blocked | 53 | def test_safe_workspace_path_parent_traversal_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_safe_workspace_path_absolute_injection_blocked | 58 | def test_safe_workspace_path_absolute_injection_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_safe_workspace_path_normal_file_allowed | 63 | def test_safe_workspace_path_normal_file_allowed(tmp_path) |
| tests/test_security_sandbox.py | function | test_safe_workspace_path_nested_allowed | 70 | def test_safe_workspace_path_nested_allowed(tmp_path) |
| tests/test_security_sandbox.py | function | test_safe_workspace_path_symlink_escape_blocked | 76 | def test_safe_workspace_path_symlink_escape_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_write_file_symlink_escape_blocked | 92 | def test_tool_write_file_symlink_escape_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_write_file_parent_traversal_blocked | 108 | def test_tool_write_file_parent_traversal_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_write_file_normal_path_works | 120 | def test_tool_write_file_normal_path_works(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_read_file_symlink_escape_blocked | 133 | def test_tool_read_file_symlink_escape_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_read_file_absolute_path_blocked | 145 | def test_tool_read_file_absolute_path_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_read_file_parent_traversal_blocked | 150 | def test_tool_read_file_parent_traversal_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_read_file_normal_path_works | 160 | def test_tool_read_file_normal_path_works(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_lint_python_symlink_escape_blocked | 171 | def test_tool_lint_python_symlink_escape_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_lint_python_empty_path_blocked | 182 | def test_tool_lint_python_empty_path_blocked(tmp_path) |
| tests/test_security_sandbox.py | function | test_tool_lint_python_normal_path_works | 187 | def test_tool_lint_python_normal_path_works(tmp_path) |
| tests/test_security_sandbox.py | class | _StubManager | 199 | class _StubManager |
| tests/test_security_sandbox.py | function | __init__ | 205 | def __init__(self) |
| tests/test_security_sandbox.py | function | test_is_safe_path_blocks_etc | 213 | def test_is_safe_path_blocks_etc(tmp_path) |
| tests/test_security_sandbox.py | function | test_is_safe_path_blocks_empty | 218 | def test_is_safe_path_blocks_empty() |
| tests/test_security_sandbox.py | function | test_is_safe_path_blocks_symlink_pointing_to_etc | 223 | def test_is_safe_path_blocks_symlink_pointing_to_etc(tmp_path) |
| tests/test_security_sandbox.py | function | test_is_safe_path_allows_tmp_path | 233 | def test_is_safe_path_allows_tmp_path(tmp_path) |
| tests/test_security_sandbox.py | function | test_is_safe_path_allows_project_root | 240 | def test_is_safe_path_allows_project_root() |
| tests/test_service_discovery.py | function | _noop | 31 | def _noop(self) |
| tests/test_service_discovery.py | function | _stub_init_security | 35 | def _stub_init_security(self) |
| tests/test_service_discovery.py | function | _stub_start_loop | 42 | def _stub_start_loop(self) |
| tests/test_service_discovery.py | function | _build_manager | 53 | def _build_manager(port: int = 8080) |
| tests/test_service_discovery.py | function | _wait_started | 74 | def _wait_started(mgr, timeout: float = 3.0) -> bool |
| tests/test_service_discovery.py | function | _make_serve_factory | 81 | def _make_serve_factory(fail_ports: set[int]) |
| tests/test_service_discovery.py | function | test_server_binds_on_default_port_when_free | 99 | def test_server_binds_on_default_port_when_free(tmp_path) |
| tests/test_service_discovery.py | function | test_port_failover_skips_occupied_port | 130 | def test_port_failover_skips_occupied_port(tmp_path) |
| tests/test_service_discovery.py | function | test_two_concurrent_managers_land_on_different_ports | 152 | def test_two_concurrent_managers_land_on_different_ports(tmp_path) |
| tests/test_service_discovery.py | function | test_discovery_file_removed_on_stop | 198 | def test_discovery_file_removed_on_stop(tmp_path) |
| tests/test_service_discovery.py | function | test_discovery_file_contains_expected_fields | 220 | def test_discovery_file_contains_expected_fields(tmp_path) |
| tests/test_service_discovery.py | function | test_failover_exhausts_range_then_raises | 242 | def test_failover_exhausts_range_then_raises(tmp_path) |
| tests/test_service_discovery.py | function | test_real_socket_conflict_triggers_failover | 266 | def test_real_socket_conflict_triggers_failover(tmp_path) |
| tests/test_session_tree.py | function | test_node_defaults | 13 | def test_node_defaults() |
| tests/test_session_tree.py | function | test_node_add_child | 23 | def test_node_add_child() |
| tests/test_session_tree.py | function | test_node_to_from_dict_round_trip | 31 | def test_node_to_from_dict_round_trip() |
| tests/test_session_tree.py | function | test_node_attachments_round_trip | 46 | def test_node_attachments_round_trip() |
| tests/test_session_tree.py | function | test_tree_empty_on_init | 62 | def test_tree_empty_on_init() |
| tests/test_session_tree.py | function | test_tree_add_message | 68 | def test_tree_add_message() |
| tests/test_session_tree.py | function | test_tree_active_path_content | 78 | def test_tree_active_path_content() |
| tests/test_session_tree.py | function | test_tree_branching | 89 | def test_tree_branching() |
| tests/test_session_tree.py | function | test_tree_serialization_round_trip | 118 | def test_tree_serialization_round_trip() |
| tests/test_session_tree.py | function | test_tree_serialization_with_branch | 134 | def test_tree_serialization_with_branch() |
| tests/test_session_tree.py | function | test_tree_clear | 152 | def test_tree_clear() |
| tests/test_session_tree.py | function | test_tree_copy_is_independent | 160 | def test_tree_copy_is_independent() |
| tests/test_session_tree.py | function | test_tree_duck_typing_len_iter | 170 | def test_tree_duck_typing_len_iter() |
| tests/test_session_tree.py | function | test_tree_getitem | 182 | def test_tree_getitem() |
| tests/test_session_tree.py | function | test_tree_append_dict | 191 | def test_tree_append_dict() |
| tests/test_session_tree.py | function | test_tree_append_invalid_raises | 199 | def test_tree_append_invalid_raises() |
| tests/test_session_tree.py | function | test_tree_update_current_node_content | 208 | def test_tree_update_current_node_content() |
| tests/test_session_tree.py | function | test_tree_nodes_map_consistency | 215 | def test_tree_nodes_map_consistency() |
| tests/test_session_tree.py | function | collect | 225 | def collect(node, ids) |
| tests/test_session_tree.py | function | test_tree_stats_and_branch_label | 236 | def test_tree_stats_and_branch_label() |
| tests/test_session_tree.py | function | test_branch_from_missing_returns_none | 249 | def test_branch_from_missing_returns_none() |
| tests/test_speculative_decoding.py | function | test_registry_companion_draft_is_discoverable | 8 | def test_registry_companion_draft_is_discoverable(tmp_path, monkeypatch) |
| tests/test_speculative_decoding.py | function | test_active_draft_model_persists_enabled_flag | 33 | def test_active_draft_model_persists_enabled_flag(tmp_path, monkeypatch) |
| tests/test_speculative_decoding.py | function | test_model_loader_uses_persisted_draft_setting | 51 | def test_model_loader_uses_persisted_draft_setting() |
| tests/test_speculative_decoding.py | function | test_status_bar_exposes_speculative_indicator | 61 | def test_status_bar_exposes_speculative_indicator() |
| tests/test_swarm.py | class | TestSwarmOrchestrator | 20 | class TestSwarmOrchestrator(unittest.TestCase) |
| tests/test_swarm.py | function | setUp | 21 | def setUp(self) |
| tests/test_swarm.py | function | tearDown | 43 | def tearDown(self) |
| tests/test_swarm.py | function | test_swarm_self_correction_loop | 47 | def test_swarm_self_correction_loop(self, mock_get_llm) |
| tests/test_swarm.py | function | stateful_mock_llm | 54 | def stateful_mock_llm(prompt, **kwargs) |
| tests/test_swarm.py | function | test_swarm_parallel_execution | 144 | def test_swarm_parallel_execution(self, mock_get_llm) |
| tests/test_swarm.py | function | stateful_mock_llm | 146 | def stateful_mock_llm(prompt, **kwargs) |
| tests/test_task_supervisor.py | function | _fresh | 12 | def _fresh() -> TaskSupervisor |
| tests/test_task_supervisor.py | class | TestTaskRegistration | 19 | class TestTaskRegistration(unittest.TestCase) |
| tests/test_task_supervisor.py | function | setUp | 21 | def setUp(self) |
| tests/test_task_supervisor.py | function | tearDown | 24 | def tearDown(self) |
| tests/test_task_supervisor.py | function | test_register_returns_unique_ids | 27 | def test_register_returns_unique_ids(self) |
| tests/test_task_supervisor.py | function | test_register_explicit_task_id | 32 | def test_register_explicit_task_id(self) |
| tests/test_task_supervisor.py | function | test_registered_task_is_running | 36 | def test_registered_task_is_running(self) |
| tests/test_task_supervisor.py | function | test_unknown_task_returns_none_status | 40 | def test_unknown_task_returns_none_status(self) |
| tests/test_task_supervisor.py | function | test_progress_zero_at_registration | 43 | def test_progress_zero_at_registration(self) |
| tests/test_task_supervisor.py | function | test_update_progress_clamped | 47 | def test_update_progress_clamped(self) |
| tests/test_task_supervisor.py | function | test_error_empty_at_registration | 56 | def test_error_empty_at_registration(self) |
| tests/test_task_supervisor.py | class | TestTaskLifecycle | 61 | class TestTaskLifecycle(unittest.TestCase) |
| tests/test_task_supervisor.py | function | setUp | 63 | def setUp(self) |
| tests/test_task_supervisor.py | function | tearDown | 66 | def tearDown(self) |
| tests/test_task_supervisor.py | function | test_finish_transitions_to_finished | 69 | def test_finish_transitions_to_finished(self) |
| tests/test_task_supervisor.py | function | test_finish_sets_progress_to_one | 74 | def test_finish_sets_progress_to_one(self) |
| tests/test_task_supervisor.py | function | test_fail_transitions_to_error | 79 | def test_fail_transitions_to_error(self) |
| tests/test_task_supervisor.py | function | test_fail_stores_error_message | 84 | def test_fail_stores_error_message(self) |
| tests/test_task_supervisor.py | function | test_finish_on_unknown_id_is_noop | 89 | def test_finish_on_unknown_id_is_noop(self) |
| tests/test_task_supervisor.py | function | test_fail_on_unknown_id_is_noop | 92 | def test_fail_on_unknown_id_is_noop(self) |
| tests/test_task_supervisor.py | function | test_active_tasks_includes_running | 95 | def test_active_tasks_includes_running(self) |
| tests/test_task_supervisor.py | function | test_active_tasks_excludes_finished | 99 | def test_active_tasks_excludes_finished(self) |
| tests/test_task_supervisor.py | function | test_all_tasks_returns_all | 104 | def test_all_tasks_returns_all(self) |
| tests/test_task_supervisor.py | class | TestCancellation | 113 | class TestCancellation(unittest.TestCase) |
| tests/test_task_supervisor.py | function | setUp | 115 | def setUp(self) |
| tests/test_task_supervisor.py | function | tearDown | 118 | def tearDown(self) |
| tests/test_task_supervisor.py | function | test_cancel_transitions_to_cancelling | 121 | def test_cancel_transitions_to_cancelling(self) |
| tests/test_task_supervisor.py | class | _Stoppable | 122 | class _Stoppable |
| tests/test_task_supervisor.py | function | request_stop | 123 | def request_stop(self) |
| tests/test_task_supervisor.py | function | test_cancel_calls_request_stop | 131 | def test_cancel_calls_request_stop(self) |
| tests/test_task_supervisor.py | class | _Stoppable | 134 | class _Stoppable |
| tests/test_task_supervisor.py | function | request_stop | 135 | def request_stop(self) |
| tests/test_task_supervisor.py | function | test_cancel_without_cancellable_returns_false | 142 | def test_cancel_without_cancellable_returns_false(self) |
| tests/test_task_supervisor.py | function | test_cancel_finished_task_is_noop | 149 | def test_cancel_finished_task_is_noop(self) |
| tests/test_task_supervisor.py | function | test_cancel_unknown_id_returns_false | 156 | def test_cancel_unknown_id_returns_false(self) |
| tests/test_task_supervisor.py | function | test_cancel_all_cancels_all_active | 159 | def test_cancel_all_cancels_all_active(self) |
| tests/test_task_supervisor.py | class | _Stoppable | 162 | class _Stoppable |
| tests/test_task_supervisor.py | function | request_stop | 163 | def request_stop(self) |
| tests/test_task_supervisor.py | function | test_cancel_all_skips_finished | 172 | def test_cancel_all_skips_finished(self) |
| tests/test_task_supervisor.py | function | test_request_stop_exception_does_not_propagate | 178 | def test_request_stop_exception_does_not_propagate(self) |
| tests/test_task_supervisor.py | class | _Buggy | 180 | class _Buggy |
| tests/test_task_supervisor.py | function | request_stop | 181 | def request_stop(self) |
| tests/test_task_supervisor.py | class | TestCleanupHooks | 192 | class TestCleanupHooks(unittest.TestCase) |
| tests/test_task_supervisor.py | function | setUp | 194 | def setUp(self) |
| tests/test_task_supervisor.py | function | tearDown | 197 | def tearDown(self) |
| tests/test_task_supervisor.py | function | test_cleanup_hook_called_on_finish | 200 | def test_cleanup_hook_called_on_finish(self) |
| tests/test_task_supervisor.py | function | test_cleanup_hook_called_on_fail | 206 | def test_cleanup_hook_called_on_fail(self) |
| tests/test_task_supervisor.py | function | test_multiple_cleanup_hooks_all_called | 212 | def test_multiple_cleanup_hooks_all_called(self) |
| tests/test_task_supervisor.py | function | test_failing_cleanup_hook_does_not_stop_others | 220 | def test_failing_cleanup_hook_does_not_stop_others(self) |
| tests/test_task_supervisor.py | function | _bad | 223 | def _bad() |
| tests/test_task_supervisor.py | function | _good | 226 | def _good() |
| tests/test_task_supervisor.py | function | test_add_cleanup_hook_unknown_id_is_noop | 235 | def test_add_cleanup_hook_unknown_id_is_noop(self) |
| tests/test_task_supervisor.py | class | TestSingleton | 239 | class TestSingleton(unittest.TestCase) |
| tests/test_task_supervisor.py | function | tearDown | 241 | def tearDown(self) |
| tests/test_task_supervisor.py | function | test_instance_is_singleton | 244 | def test_instance_is_singleton(self) |
| tests/test_task_supervisor.py | function | test_reset_produces_fresh_instance | 249 | def test_reset_produces_fresh_instance(self) |
| tests/test_task_supervisor.py | function | test_singleton_thread_safe | 256 | def test_singleton_thread_safe(self) |
| tests/test_task_supervisor.py | function | _get | 261 | def _get() |
| tests/test_task_supervisor.py | class | TestCancellationWithRealThread | 274 | class TestCancellationWithRealThread(unittest.TestCase) |
| tests/test_task_supervisor.py | function | setUp | 277 | def setUp(self) |
| tests/test_task_supervisor.py | function | tearDown | 280 | def tearDown(self) |
| tests/test_task_supervisor.py | function | test_real_thread_stops_when_cancelled | 283 | def test_real_thread_stops_when_cancelled(self) |
| tests/test_task_supervisor.py | class | _Worker | 287 | class _Worker(threading.Thread) |
| tests/test_task_supervisor.py | function | request_stop | 288 | def request_stop(self) |
| tests/test_task_supervisor.py | function | run | 291 | def run(self) |
| tests/test_task_supervisor.py | function | test_finish_after_thread_completes | 311 | def test_finish_after_thread_completes(self) |
| tests/test_task_supervisor.py | class | _Worker | 314 | class _Worker(threading.Thread) |
| tests/test_task_supervisor.py | function | request_stop | 315 | def request_stop(self) |
| tests/test_task_supervisor.py | function | run | 318 | def run(self) |
| tests/test_task_supervisor.py | class | TestModelLoaderGuard | 332 | class TestModelLoaderGuard(unittest.TestCase) |
| tests/test_task_supervisor.py | function | test_locked_during_active_count | 335 | def test_locked_during_active_count(self) |
| tests/test_task_supervisor.py | function | test_unlocked_when_no_active | 348 | def test_unlocked_when_no_active(self) |
| tests/test_technical_guards.py | class | TestTechnicalGuards | 28 | class TestTechnicalGuards(unittest.TestCase) |
| tests/test_technical_guards.py | function | setUp | 29 | def setUp(self) |
| tests/test_technical_guards.py | function | tearDown | 34 | def tearDown(self) |
| tests/test_technical_guards.py | function | test_codebase_search_ripgrep | 38 | def test_codebase_search_ripgrep(self) |
| tests/test_technical_guards.py | function | test_parse_reasoning_and_tool | 53 | def test_parse_reasoning_and_tool(self) |
| tests/test_technical_guards.py | function | test_hot_reload_keeps_previous_module_on_compile_error | 84 | def test_hot_reload_keeps_previous_module_on_compile_error(self) |
| tests/test_technical_guards.py | function | test_llm_trim_history_uses_tokenizer_counts | 103 | def test_llm_trim_history_uses_tokenizer_counts(self) |
| tests/test_technical_guards.py | class | TokenDenseMock | 104 | class TokenDenseMock |
| tests/test_technical_guards.py | function | tokenize | 105 | def tokenize(self, text_bytes, add_bos=False) |
| tests/test_technical_guards.py | function | test_orchestrator_rejects_unsafe_task_paths | 130 | def test_orchestrator_rejects_unsafe_task_paths(self) |
| tests/test_technical_guards.py | function | test_orchestrator_syntax_validation_guards | 158 | def test_orchestrator_syntax_validation_guards(self, mock_get_llm) |
| tests/test_technical_guards.py | function | stateful_mock_llm | 164 | def stateful_mock_llm(prompt, **kwargs) |
| tests/test_technical_guards.py | function | test_proc_maps_page_privacy | 226 | def test_proc_maps_page_privacy(self) |
| tests/test_technical_guards.py | function | test_kernel_keyring_expiry_and_revocation | 255 | def test_kernel_keyring_expiry_and_revocation(self) |
| tests/test_technical_guards.py | function | read_session_token | 270 | def read_session_token(key_id: int) -> str |
| tests/test_token_lifecycle.py | function | _stub_init_security | 37 | def _stub_init_security(self) -> None |
| tests/test_token_lifecycle.py | class | _TestServer | 44 | class _TestServer |
| tests/test_token_lifecycle.py | function | __init__ | 50 | def __init__(self, port: int = _TEST_PORT, token_lifetime: int = 5, audit_interval: int = 1) |
| tests/test_token_lifecycle.py | function | __enter__ | 59 | def __enter__(self) |
| tests/test_token_lifecycle.py | function | __exit__ | 82 | def __exit__(self, *_) |
| tests/test_token_lifecycle.py | function | _ws_url | 93 | def _ws_url(port: int, token: str = _TEST_TOKEN) -> str |
| tests/test_token_lifecycle.py | function | test_expired_session_closes_with_code_4002 | 119 | def test_expired_session_closes_with_code_4002() |
| tests/test_token_lifecycle.py | function | test_refresh_token_extends_session_lease | 134 | def test_refresh_token_extends_session_lease() |
| tests/test_token_lifecycle.py | function | test_refresh_token_invalid_token_returns_error | 188 | def test_refresh_token_invalid_token_returns_error() |
| tests/test_token_lifecycle.py | function | test_force_revoke_closes_all_connections_with_4003 | 213 | def test_force_revoke_closes_all_connections_with_4003() |
| tests/test_token_lifecycle.py | function | test_revoke_wipes_token_file | 254 | def test_revoke_wipes_token_file(tmp_path, monkeypatch) |
| tests/test_trace_logger.py | function | test_schema_fields | 17 | def test_schema_fields() |
| tests/test_trace_logger.py | function | test_file_rotation | 93 | def test_file_rotation() |
| tests/test_trace_logger.py | function | test_log_pruning | 130 | def test_log_pruning() |
| tests/test_trace_logger.py | function | test_cryptographic_memory_zeroing | 158 | def test_cryptographic_memory_zeroing() |
| tests/test_trace_logger.py | function | intercepting_zero | 171 | def intercepting_zero(ba: bytearray) -> None |
| tests/test_trace_logger.py | function | test_decrypted_payload_cleanup | 206 | def test_decrypted_payload_cleanup() |
| tests/test_training_curator.py | function | test_curation_saving_and_sft_export | 12 | def test_curation_saving_and_sft_export() |
| tests/test_training_curator.py | function | test_curator_dpo_pairing | 62 | def test_curator_dpo_pairing() |
| tests/test_ui_drag_drop.py | class | MockState | 11 | class MockState |
| tests/test_ui_drag_drop.py | function | __init__ | 12 | def __init__(self) |
| tests/test_ui_drag_drop.py | class | MockCurator | 13 | class MockCurator |
| tests/test_ui_drag_drop.py | function | __init__ | 14 | def __init__(self) |
| tests/test_ui_drag_drop.py | function | get_all_examples | 19 | def get_all_examples(self) |
| tests/test_ui_drag_drop.py | function | delete_example | 21 | def delete_example(self, row) |
| tests/test_ui_drag_drop.py | class | MockRag | 25 | class MockRag |
| tests/test_ui_drag_drop.py | function | list_sources | 26 | def list_sources(self) |
| tests/test_ui_drag_drop.py | function | is_encoder_loaded | 29 | def is_encoder_loaded(self) |
| tests/test_ui_drag_drop.py | function | total_chunks | 32 | def total_chunks(self) |
| tests/test_ui_drag_drop.py | function | total_sources | 35 | def total_sources(self) |
| tests/test_ui_drag_drop.py | function | test_dataset_list_model | 45 | def test_dataset_list_model() |
| tests/test_ui_drag_drop.py | function | test_drag_drop_filter | 63 | def test_drag_drop_filter() |
| tests/test_ui_drag_drop.py | class | MockDropEvent | 83 | class MockDropEvent |
| tests/test_ui_drag_drop.py | function | __init__ | 84 | def __init__(self, mime_data) |
| tests/test_ui_drag_drop.py | function | mimeData | 87 | def mimeData(self) |
| tests/test_ui_drag_drop.py | function | acceptProposedAction | 89 | def acceptProposedAction(self) |
| tests/test_ui_improvements.py | class | TestUIImprovements | 10 | class TestUIImprovements(unittest.TestCase) |
| tests/test_ui_improvements.py | function | test_theme_qss_generation | 11 | def test_theme_qss_generation(self) |
| tests/test_ui_improvements.py | function | test_theme_config_read_write | 21 | def test_theme_config_read_write(self) |
| tests/test_ui_improvements.py | function | test_codex_library_loading_and_search | 43 | def test_codex_library_loading_and_search(self) |
| tests/test_ui_improvements.py | function | test_workbench_docks | 84 | def test_workbench_docks(self) |
| tests/test_ui_improvements.py | function | test_swarm_studio_constructs | 106 | def test_swarm_studio_constructs(self) |
| tests/test_ui_improvements.py | function | test_agentic_loop_persists_only_final_assistant_answer | 118 | def test_agentic_loop_persists_only_final_assistant_answer(self) |
| tests/test_ui_improvements.py | class | FakeThread | 123 | class FakeThread |
| tests/test_ui_improvements.py | function | __init__ | 124 | def __init__(self, history) |
| tests/test_ui_improvements.py | function | test_system_config_features | 153 | def test_system_config_features(self) |
| tests/test_ui_improvements.py | function | test_codex_rag_features | 188 | def test_codex_rag_features(self) |
| tests/test_vision_analyzer.py | function | _sample_image | 13 | def _sample_image(width=80, height=48) |
| tests/test_vision_analyzer.py | function | test_classify_image_detects_code_error_from_ocr | 19 | def test_classify_image_detects_code_error_from_ocr(tmp_path) |
| tests/test_vision_analyzer.py | function | test_ocr_only_analysis_returns_honest_caption | 33 | def test_ocr_only_analysis_returns_honest_caption(tmp_path) |
| tests/test_vision_model_loader.py | function | test_vision_registry_is_readable | 9 | def test_vision_registry_is_readable() |
| tests/test_vision_model_loader.py | function | test_installed_vision_models_reports_paths_and_install_state | 18 | def test_installed_vision_models_reports_paths_and_install_state() |
| tests/test_vision_workbench.py | function | test_vision_workbench_lists_saved_images | 13 | def test_vision_workbench_lists_saved_images(tmp_path) |
| tests/test_vision_workbench.py | function | test_vision_workbench_saves_metadata_and_corrections | 31 | def test_vision_workbench_saves_metadata_and_corrections(tmp_path) |
| tests/test_watchdog.py | function | test_llm_watchdog_terminates_slow_stream | 10 | def test_llm_watchdog_terminates_slow_stream(monkeypatch) |
| tests/test_watchdog.py | class | SlowStream | 16 | class SlowStream |
| tests/test_watchdog.py | function | __init__ | 17 | def __init__(self) |
| tests/test_watchdog.py | function | __iter__ | 20 | def __iter__(self) |
| tests/test_watchdog.py | function | __next__ | 23 | def __next__(self) |
| tests/test_watchdog.py | function | close | 29 | def close(self) |
| tests/test_watchdog.py | class | FakeLLM | 32 | class FakeLLM |
| tests/test_watchdog.py | function | __init__ | 33 | def __init__(self) |
| tests/test_watchdog.py | function | __call__ | 37 | def __call__(self, *args, **kwargs) |
| tests/test_watchdog.py | function | tokenize | 40 | def tokenize(self, data, add_bos=False) |
| tests/test_watchdog.py | function | reset | 43 | def reset(self) |
| tests/test_watchdog.py | function | test_agentic_watchdog_cleanup_emits_exact_timeout | 88 | def test_agentic_watchdog_cleanup_emits_exact_timeout() |
| tests/test_watchdog.py | class | FakeLLM | 91 | class FakeLLM |
| tests/test_watchdog.py | function | __init__ | 92 | def __init__(self) |
| tests/test_watchdog.py | function | reset | 95 | def reset(self) |
| tests/test_watchdog.py | class | FakeStream | 98 | class FakeStream |
| tests/test_watchdog.py | function | __init__ | 99 | def __init__(self) |
| tests/test_watchdog.py | function | close | 102 | def close(self) |
| tests/test_watchdog.py | function | test_main_window_restores_and_clears_autosave_checkpoint | 128 | def test_main_window_restores_and_clears_autosave_checkpoint(tmp_path, monkeypatch) |
| tests/test_watchdog.py | class | FakeState | 136 | class FakeState(QObject) |
| tests/test_watchdog.py | function | __init__ | 139 | def __init__(self) |
| tests/test_watchdog.py | class | FakeSidebar | 147 | class FakeSidebar(QWidget) |
| tests/test_watchdog.py | function | __init__ | 150 | def __init__(self) |
| tests/test_watchdog.py | function | select | 154 | def select(self, idx) |
| tests/test_watchdog.py | class | FakeStatusBar | 158 | class FakeStatusBar(QWidget) |
| tests/test_watchdog.py | function | set_model | 159 | def set_model(self, value) |
| tests/test_watchdog.py | function | set_adapter | 162 | def set_adapter(self, value) |
| tests/test_watchdog.py | function | set_state | 165 | def set_state(self, *args) |
| tests/test_watchdog.py | function | set_context_stats | 168 | def set_context_stats(self, *args) |
| tests/test_watchdog.py | function | set_load_stats | 171 | def set_load_stats(self, *args) |
| tests/test_watchdog.py | function | set_bridge_status | 174 | def set_bridge_status(self, *args) |
| tests/test_watchdog.py | class | FakeChatView | 177 | class FakeChatView |
| tests/test_watchdog.py | function | __init__ | 178 | def __init__(self) |
| tests/test_watchdog.py | function | clear_display | 181 | def clear_display(self) |
| tests/test_watchdog.py | function | _render_all | 184 | def _render_all(self) |
| tests/test_watchdog.py | class | FakeWorkbench | 187 | class FakeWorkbench(QWidget) |
| tests/test_watchdog.py | function | __init__ | 194 | def __init__(self, state) |
| tests/test_watchdog.py | function | _new_session | 204 | def _new_session(self) |
| tests/test_watchdog.py | function | _save_current_session | 207 | def _save_current_session(self) |
| tests/test_watchdog.py | function | _toggle_all_huds | 210 | def _toggle_all_huds(self) |
| tests/test_watchdog.py | function | _toggle_reasoning | 213 | def _toggle_reasoning(self) |
| tests/test_watchdog.py | function | _toggle_sessions | 216 | def _toggle_sessions(self) |
| tests/test_watchdog.py | function | _toggle_rag_hud | 219 | def _toggle_rag_hud(self) |
| tests/test_watchdog.py | function | _toggle_context_hud | 222 | def _toggle_context_hud(self) |
| tests/test_watchdog.py | function | update_theme | 225 | def update_theme(self) |
| tests/test_watchdog.py | function | _populate_branches_tree | 228 | def _populate_branches_tree(self) |
| tests/test_watchdog.py | function | _refresh_sessions | 231 | def _refresh_sessions(self) |
| tests/test_watchdog.py | function | on_close | 234 | def on_close(self) |
| tests/test_watchdog.py | class | FakeWorkspace | 237 | class FakeWorkspace(QWidget) |
| tests/test_watchdog.py | function | __init__ | 241 | def __init__(self, *args, **kwargs) |
| tests/test_watchdog.py | function | set_workbench | 244 | def set_workbench(self, *args) |
| tests/test_watchdog.py | function | _scan_adapters | 247 | def _scan_adapters(self) |
| tests/test_websocket_bridge.py | function | _running_under_bwrap | 27 | def _running_under_bwrap() -> bool |
| tests/test_websocket_bridge.py | class | FakeBridgeRAG | 35 | class FakeBridgeRAG |
| tests/test_websocket_bridge.py | function | __init__ | 36 | def __init__(self) |
| tests/test_websocket_bridge.py | function | _load_index | 39 | def _load_index(self) |
| tests/test_websocket_bridge.py | function | total_chunks | 43 | def total_chunks(self) |
| tests/test_websocket_bridge.py | function | ingest_file | 46 | def ingest_file(self, filepath, chunk_size=200, overlap=50) |
| tests/test_websocket_bridge.py | function | retrieve | 58 | def retrieve(self, query, top_k=3, source_filter=None, threshold=0.0) |
| tests/test_websocket_bridge.py | function | retrieve_with_metadata | 64 | def retrieve_with_metadata(self, query, top_k=3, source_filter=None) |
| tests/test_websocket_bridge.py | class | TestWebSocketBridge | 78 | class TestWebSocketBridge(unittest.TestCase) |
| tests/test_websocket_bridge.py | function | setUp | 79 | def setUp(self) |
| tests/test_websocket_bridge.py | function | tearDown | 100 | def tearDown(self) |
| tests/test_websocket_bridge.py | function | _get_uri | 105 | def _get_uri(self) |
| tests/test_websocket_bridge.py | function | _get_ssl_context | 112 | def _get_ssl_context(self) |
| tests/test_websocket_bridge.py | function | test_runtime_status_rpc | 121 | def test_runtime_status_rpc(self) |
| tests/test_websocket_bridge.py | function | test_model_registry_rpc | 149 | def test_model_registry_rpc(self) |
| tests/test_websocket_bridge.py | function | test_prompt_pair_rpc | 203 | def test_prompt_pair_rpc(self) |
| tests/test_websocket_bridge.py | function | test_knowledge_base_rpc | 271 | def test_knowledge_base_rpc(self) |
| tests/test_websocket_bridge.py | function | test_websocket_bridge_flow | 344 | def test_websocket_bridge_flow(self, mock_get_llm) |
| tests/test_websocket_bridge.py | function | mock_llm | 346 | def mock_llm(prompt, **kwargs) |
| tests/test_websocket_bridge.py | function | test_websocket_chat_flow | 428 | def test_websocket_chat_flow(self, mock_get_llm) |
| tests/test_websocket_bridge.py | function | mock_llm_stream | 429 | def mock_llm_stream(prompt, **kwargs) |
| tests/test_websocket_bridge.py | function | test_status_bar_reflection | 506 | def test_status_bar_reflection(self) |
| tests/test_websocket_bridge.py | function | test_token_connection_success | 523 | def test_token_connection_success(self) |
| tests/test_websocket_bridge.py | function | test_token_expiry_fail | 534 | def test_token_expiry_fail(self, mock_time) |
| tests/test_websocket_bridge.py | function | test_token_rotation_on_disk | 572 | def test_token_rotation_on_disk(self, mock_time) |
| tests/test_websocket_contract.py | class | MockWebSocket | 10 | class MockWebSocket |
| tests/test_websocket_contract.py | function | __init__ | 11 | def __init__(self, messages) |
| tests/test_websocket_contract.py | function | __aiter__ | 17 | def __aiter__(self) |
| tests/test_websocket_contract.py | function | make_manager | 34 | def make_manager() |
| tests/test_websocket_contract.py | function | assert_rpc_error | 58 | def assert_rpc_error(response, code, req_id) |
| tests/test_websocket_contract.py | function | test_parse_error_returns_json_rpc_error | 65 | def test_parse_error_returns_json_rpc_error() |
| tests/test_websocket_contract.py | function | test_missing_jsonrpc_returns_invalid_request | 70 | def test_missing_jsonrpc_returns_invalid_request() |
| tests/test_websocket_contract.py | function | test_unknown_method_returns_method_not_found | 78 | def test_unknown_method_returns_method_not_found() |
| tests/test_websocket_contract.py | function | test_missing_required_params_returns_invalid_params | 86 | def test_missing_required_params_returns_invalid_params() |
| tests/test_websocket_contract.py | function | test_handler_exception_returns_internal_error | 94 | def test_handler_exception_returns_internal_error() |
| tests/test_websocket_contract.py | function | raise_runtime_error | 97 | def raise_runtime_error() |
| tools/conversion/__init__.py | function | load_all_models | 298 | def load_all_models() -> None |
| tools/conversion/__init__.py | function | get_model_class | 319 | def get_model_class(name: str, mmproj: bool = False) -> Type[ModelBase] |
| tools/conversion/__init__.py | function | print_registered_models | 330 | def print_registered_models() -> None |
| tools/conversion/afmoe.py | class | AfmoeModel | 16 | class AfmoeModel(LlamaModel) |
| tools/conversion/afmoe.py | function | set_gguf_parameters | 19 | def set_gguf_parameters(self) |
| tools/conversion/afmoe.py | function | filter_tensors | 41 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/afmoe.py | function | modify_tensors | 49 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/arctic.py | class | ArcticModel | 19 | class ArcticModel(TextModel) |
| tools/conversion/arctic.py | function | set_vocab | 22 | def set_vocab(self) |
| tools/conversion/arctic.py | function | set_gguf_parameters | 106 | def set_gguf_parameters(self) |
| tools/conversion/arctic.py | function | modify_tensors | 114 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/arctic.py | function | prepare_tensors | 155 | def prepare_tensors(self) |
| tools/conversion/baichuan.py | class | BaichuanModel | 12 | class BaichuanModel(TextModel) |
| tools/conversion/baichuan.py | function | set_vocab | 15 | def set_vocab(self) |
| tools/conversion/baichuan.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/baichuan.py | function | modify_tensors | 24 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/baichuan.py | function | _reverse_hf_permute | 41 | def _reverse_hf_permute(self, weights: Tensor, n_head: int, n_kv_head: int \| None = None) -> Tensor |
| tools/conversion/baichuan.py | function | _reverse_hf_permute_part | 51 | def _reverse_hf_permute_part( self, weights: Tensor, n_part: int, n_head: int, n_head_kv: int \| None = None, ) -> Tensor |
| tools/conversion/baichuan.py | function | _reverse_hf_part | 57 | def _reverse_hf_part(self, weights: Tensor, n_part: int) -> Tensor |
| tools/conversion/bailingmoe.py | class | BailingMoeModel | 14 | class BailingMoeModel(TextModel) |
| tools/conversion/bailingmoe.py | function | set_vocab | 17 | def set_vocab(self) |
| tools/conversion/bailingmoe.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/bailingmoe.py | function | permute | 37 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| tools/conversion/bailingmoe.py | function | modify_tensors | 44 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bailingmoe.py | function | prepare_tensors | 100 | def prepare_tensors(self) |
| tools/conversion/bailingmoe.py | class | BailingMoeV2Model | 111 | class BailingMoeV2Model(TextModel) |
| tools/conversion/bailingmoe.py | function | __init__ | 114 | def __init__(self, *args, **kwargs) |
| tools/conversion/bailingmoe.py | function | set_vocab | 120 | def set_vocab(self) |
| tools/conversion/bailingmoe.py | function | set_gguf_parameters | 123 | def set_gguf_parameters(self) |
| tools/conversion/bailingmoe.py | function | filter_tensors | 144 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bailingmoe.py | function | modify_tensors | 152 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bailingmoe.py | function | prepare_tensors | 181 | def prepare_tensors(self) |
| tools/conversion/bailingmoe.py | class | SarvamMoEModel | 192 | class SarvamMoEModel(BailingMoeV2Model) |
| tools/conversion/bailingmoe.py | function | set_gguf_parameters | 198 | def set_gguf_parameters(self) |
| tools/conversion/bailingmoe.py | function | filter_tensors | 207 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bailingmoe.py | function | gen | 213 | def gen() |
| tools/conversion/base.py | class | SentencePieceTokenTypes | 61 | class SentencePieceTokenTypes(IntEnum) |
| tools/conversion/base.py | class | ModelType | 70 | class ModelType(IntEnum) |
| tools/conversion/base.py | class | ModelBase | 75 | class ModelBase |
| tools/conversion/base.py | function | __init__ | 115 | def __init__(self, dir_model: Path, ftype: gguf.LlamaFileType, fname_out: Path, *, is_big_endian: bool = False, use_temp_file: bool = False, eager: bool = False, metadata_override: Path \| None = None, model_name: str \| None = None, split_max_tensors: int = 0, split_max_size: int = 0, dry_run: bool = False, |
| tools/conversion/base.py | function | add_prefix_to_filename | 182 | def add_prefix_to_filename(cls, path: Path, prefix: str) -> Path |
| tools/conversion/base.py | function | find_hparam | 187 | def find_hparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| tools/conversion/base.py | function | index_tensors | 195 | def index_tensors(self, remote_hf_model_id: str \| None = None) -> dict[str, Callable[[], Tensor]] |
| tools/conversion/base.py | function | _scale_is_trivial | 287 | def _scale_is_trivial(scale: Tensor) -> bool |
| tools/conversion/base.py | function | _write_scale_tensor | 290 | def _write_scale_tensor(self, scale_name: str, scale: Tensor) |
| tools/conversion/base.py | function | _write_scales_tensor | 296 | def _write_scales_tensor(self, scale_name: str, scales: list[float]) |
| tools/conversion/base.py | function | dequant_model | 302 | def dequant_model(self) |
| tools/conversion/base.py | function | dequant_bitnet | 313 | def dequant_bitnet(weight: Tensor, scale: Tensor) -> Tensor |
| tools/conversion/base.py | function | dequant_simple | 325 | def dequant_simple(weight: Tensor, scale: Tensor, block_size: Sequence[int] \| None = None) -> Tensor |
| tools/conversion/base.py | function | dequant_gptq | 342 | def dequant_gptq(g_idx: Tensor, qweight: Tensor, qzeros: Tensor, scales: Tensor) -> Tensor |
| tools/conversion/base.py | function | dequant_packed | 384 | def dequant_packed(w: Tensor, scale: Tensor, shape_tensor: Tensor, zero_point: Tensor \| None, num_bits: int, group_size: int) |
| tools/conversion/base.py | function | filter_tensors | 566 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/base.py | function | get_tensors | 577 | def get_tensors(self) -> Iterator[tuple[str, Tensor]] |
| tools/conversion/base.py | function | format_tensor_name | 581 | def format_tensor_name(self, key: gguf.MODEL_TENSOR, bid: int \| None = None, suffix: str = ".weight") -> str |
| tools/conversion/base.py | function | match_model_tensor_name | 590 | def match_model_tensor_name(self, name: str, key: gguf.MODEL_TENSOR, bid: int \| None, suffix: str = ".weight") -> bool |
| tools/conversion/base.py | function | map_tensor_name | 603 | def map_tensor_name(self, name: str, try_suffixes: Sequence[str] = (".weight", ".bias")) -> str |
| tools/conversion/base.py | function | set_gguf_parameters | 609 | def set_gguf_parameters(self) |
| tools/conversion/base.py | function | modify_tensors | 612 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/base.py | function | tensor_force_quant | 639 | def tensor_force_quant(self, name: str, new_name: str, bid: int \| None, n_dims: int) -> gguf.GGMLQuantizationType \| bool |
| tools/conversion/base.py | function | generate_extra_tensors | 647 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/base.py | function | _nvfp4_pack | 651 | def _nvfp4_pack(weight: Tensor, scale: Tensor) -> tuple[np.ndarray, list[int]] |
| tools/conversion/base.py | function | _repack_nvfp4 | 675 | def _repack_nvfp4(self, name: str, weight: Tensor, scale: Tensor, scale2: Tensor, input_scale: Tensor) |
| tools/conversion/base.py | function | _generate_nvfp4_tensors | 685 | def _generate_nvfp4_tensors(self) |
| tools/conversion/base.py | function | _flush_nvfp4_experts | 761 | def _flush_nvfp4_experts(self, key, expert_blocks, expert_scales, expert_input_scales, expert_shapes, bid, proj_type) |
| tools/conversion/base.py | function | prepare_tensors | 782 | def prepare_tensors(self) |
| tools/conversion/base.py | function | inverse_scale | 830 | def inverse_scale(gen) |
| tools/conversion/base.py | function | load | 831 | def load() |
| tools/conversion/base.py | function | set_type | 978 | def set_type(self) |
| tools/conversion/base.py | function | prepare_metadata | 981 | def prepare_metadata(self, vocab_only: bool) |
| tools/conversion/base.py | function | write_vocab | 1016 | def write_vocab(self) |
| tools/conversion/base.py | function | write | 1019 | def write(self) |
| tools/conversion/base.py | function | get_model_part_names | 1028 | def get_model_part_names(dir_model: Path, prefix: str, suffix: str) -> list[str] |
| tools/conversion/base.py | function | load_hparams | 1039 | def load_hparams(dir_model: Path, is_mistral_format: bool) |
| tools/conversion/base.py | function | register | 1072 | def register(cls, *names: str) -> Callable[[AnyModel], AnyModel] |
| tools/conversion/base.py | function | func | 1075 | def func(modelcls: AnyModel) -> AnyModel |
| tools/conversion/base.py | function | print_registered_models | 1083 | def print_registered_models(cls) |
| tools/conversion/base.py | function | from_model_architecture | 1090 | def from_model_architecture(cls, arch: str, model_type = ModelType.TEXT) -> type[ModelBase] |
| tools/conversion/base.py | class | TextModel | 1097 | class TextModel(ModelBase) |
| tools/conversion/base.py | function | __init__ | 1101 | def __init__(self, *args, **kwargs) |
| tools/conversion/base.py | function | __init_subclass__ | 1130 | def __init_subclass__(cls) |
| tools/conversion/base.py | function | filter_tensors | 1137 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/base.py | function | set_vocab | 1153 | def set_vocab(self) |
| tools/conversion/base.py | function | prepare_metadata | 1156 | def prepare_metadata(self, vocab_only: bool) |
| tools/conversion/base.py | function | set_gguf_parameters | 1184 | def set_gguf_parameters(self) |
| tools/conversion/base.py | function | write_vocab | 1296 | def write_vocab(self) |
| tools/conversion/base.py | function | does_token_look_special | 1305 | def does_token_look_special(self, token: str \| bytes) -> bool |
| tools/conversion/base.py | function | get_vocab_base | 1329 | def get_vocab_base(self) -> tuple[list[str], list[int], str] |
| tools/conversion/base.py | function | get_vocab_base_pre | 1377 | def get_vocab_base_pre(self, tokenizer) -> str |
| tools/conversion/base.py | function | _set_vocab_none | 1682 | def _set_vocab_none(self) -> None |
| tools/conversion/base.py | function | _set_vocab_gpt2 | 1685 | def _set_vocab_gpt2(self) -> None |
| tools/conversion/base.py | function | _set_vocab_hybriddna | 1695 | def _set_vocab_hybriddna(self) |
| tools/conversion/base.py | function | _set_vocab_qwen | 1736 | def _set_vocab_qwen(self) |
| tools/conversion/base.py | function | _set_vocab_sentencepiece | 1792 | def _set_vocab_sentencepiece(self, add_to_gguf=True) |
| tools/conversion/base.py | function | _create_vocab_sentencepiece | 1804 | def _create_vocab_sentencepiece(self) |
| tools/conversion/base.py | function | _set_vocab_llama_hf | 1894 | def _set_vocab_llama_hf(self) |
| tools/conversion/base.py | function | _set_vocab_rwkv_world | 1916 | def _set_vocab_rwkv_world(self) |
| tools/conversion/base.py | function | _set_vocab_builtin | 1961 | def _set_vocab_builtin(self, model_name: Literal["gpt-neox", "llama-spm"], vocab_size: int) |
| tools/conversion/base.py | function | _try_set_pooling_type | 2006 | def _try_set_pooling_type(self) -> None |
| tools/conversion/base.py | function | _set_vocab_glmedge | 2040 | def _set_vocab_glmedge(self) |
| tools/conversion/base.py | function | _set_vocab_glm | 2055 | def _set_vocab_glm(self) |
| tools/conversion/base.py | function | _set_vocab_interns1 | 2072 | def _set_vocab_interns1(self) |
| tools/conversion/base.py | function | _set_vocab_mistral | 2121 | def _set_vocab_mistral(self) |
| tools/conversion/base.py | function | _set_vocab_plamo | 2196 | def _set_vocab_plamo(self) |
| tools/conversion/base.py | class | MmprojModel | 2275 | class MmprojModel(ModelBase) |
| tools/conversion/base.py | function | __init__ | 2290 | def __init__(self, *args, **kwargs) |
| tools/conversion/base.py | function | filter_tensors | 2362 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/base.py | function | get_vision_config | 2371 | def get_vision_config(self) -> dict[str, Any] \| None |
| tools/conversion/base.py | function | get_audio_config | 2375 | def get_audio_config(self) -> dict[str, Any] \| None |
| tools/conversion/base.py | function | set_type | 2379 | def set_type(self) |
| tools/conversion/base.py | function | prepare_metadata | 2382 | def prepare_metadata(self, vocab_only: bool) |
| tools/conversion/base.py | function | set_gguf_parameters | 2393 | def set_gguf_parameters(self) |
| tools/conversion/base.py | function | write_vocab | 2429 | def write_vocab(self) |
| tools/conversion/base.py | function | find_vparam | 2432 | def find_vparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| tools/conversion/base.py | function | find_aparam | 2436 | def find_aparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| tools/conversion/base.py | function | _find_param | 2440 | def _find_param(self, obj: dict[str, Any], keys: Iterable[str], optional: bool = False) -> Any |
| tools/conversion/base.py | function | tensor_force_quant | 2448 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/base.py | class | LazyTorchTensor | 2454 | class LazyTorchTensor(gguf.LazyBase) |
| tools/conversion/base.py | function | numpy | 2508 | def numpy(self) -> gguf.LazyNumpyTensor |
| tools/conversion/base.py | function | meta_with_dtype_and_shape | 2517 | def meta_with_dtype_and_shape(cls, dtype: torch.dtype, shape: tuple[int, ...]) -> Tensor |
| tools/conversion/base.py | function | from_safetensors_slice | 2521 | def from_safetensors_slice(cls, st_slice: Any) -> Tensor |
| tools/conversion/base.py | function | from_local_tensor | 2528 | def from_local_tensor(cls, t: gguf.utility.LocalTensor) -> Tensor |
| tools/conversion/base.py | function | load_tensor | 2529 | def load_tensor(tensor: gguf.utility.LocalTensor) -> Tensor |
| tools/conversion/base.py | function | byteswap_tensor | 2530 | def byteswap_tensor(tensor: np.ndarray, dtype: type) -> np.ndarray |
| tools/conversion/base.py | function | from_remote_tensor | 2544 | def from_remote_tensor(cls, remote_tensor: gguf.utility.RemoteTensor) |
| tools/conversion/base.py | function | byteswap_tensor | 2545 | def byteswap_tensor(tensor: np.ndarray, dtype: type) -> np.ndarray |
| tools/conversion/base.py | function | __torch_function__ | 2558 | def __torch_function__(cls, func, types, args=(), kwargs=None) |
| tools/conversion/base.py | function | get_model_architecture | 2571 | def get_model_architecture(hparams: dict[str, Any], model_type: ModelType) -> str |
| tools/conversion/bert.py | class | BertModel | 18 | class BertModel(TextModel) |
| tools/conversion/bert.py | function | __init__ | 21 | def __init__(self, *args, **kwargs) |
| tools/conversion/bert.py | function | set_gguf_parameters | 31 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | set_vocab | 39 | def set_vocab(self) |
| tools/conversion/bert.py | function | phantom | 49 | def phantom(tok, toktype) |
| tools/conversion/bert.py | function | filter_tensors | 69 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | function | modify_tensors | 93 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bert.py | function | _xlmroberta_tokenizer_init | 104 | def _xlmroberta_tokenizer_init(self) -> None |
| tools/conversion/bert.py | function | _xlmroberta_set_vocab | 113 | def _xlmroberta_set_vocab(self) -> None |
| tools/conversion/bert.py | class | DistilBertModel | 243 | class DistilBertModel(BertModel) |
| tools/conversion/bert.py | function | set_gguf_parameters | 246 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | filter_tensors | 252 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | class | RobertaModel | 266 | class RobertaModel(BertModel) |
| tools/conversion/bert.py | function | __init__ | 269 | def __init__(self, *args, **kwargs) |
| tools/conversion/bert.py | function | set_vocab | 280 | def set_vocab(self) |
| tools/conversion/bert.py | function | filter_tensors | 295 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | function | modify_tensors | 305 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bert.py | class | NomicBertModel | 315 | class NomicBertModel(BertModel) |
| tools/conversion/bert.py | function | __init__ | 318 | def __init__(self, dir_model: Path, ftype: gguf.LlamaFileType, fname_out: Path, **kwargs: Any) |
| tools/conversion/bert.py | function | set_vocab | 356 | def set_vocab(self) -> None |
| tools/conversion/bert.py | function | filter_tensors | 362 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | function | modify_tensors | 371 | def modify_tensors(self, data_torch: torch.Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, torch.Tensor]] |
| tools/conversion/bert.py | function | set_gguf_parameters | 384 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | _is_tokenizer_xlmroberta | 390 | def _is_tokenizer_xlmroberta(self) -> bool |
| tools/conversion/bert.py | class | NeoBert | 402 | class NeoBert(BertModel) |
| tools/conversion/bert.py | function | set_gguf_parameters | 405 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | filter_tensors | 420 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | class | EuroBertModel | 433 | class EuroBertModel(TextModel) |
| tools/conversion/bert.py | function | set_vocab | 436 | def set_vocab(self) |
| tools/conversion/bert.py | function | set_gguf_parameters | 440 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | filter_tensors | 451 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | class | XLMRobertaModel | 461 | class XLMRobertaModel(BertModel) |
| tools/conversion/bert.py | function | __init__ | 466 | def __init__(self, dir_model: Path, ftype: gguf.LlamaFileType, fname_out: Path, **kwargs: Any) |
| tools/conversion/bert.py | function | generate_extra_tensors | 478 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bert.py | function | set_type | 486 | def set_type(self) |
| tools/conversion/bert.py | function | set_vocab | 492 | def set_vocab(self) |
| tools/conversion/bert.py | function | filter_tensors | 496 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | function | modify_tensors | 512 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bert.py | function | set_gguf_parameters | 540 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | write | 553 | def write(self) |
| tools/conversion/bert.py | class | JinaBertV2Model | 563 | class JinaBertV2Model(BertModel) |
| tools/conversion/bert.py | function | set_vocab | 566 | def set_vocab(self) |
| tools/conversion/bert.py | class | ModernBertModel | 581 | class ModernBertModel(BertModel) |
| tools/conversion/bert.py | function | set_vocab | 584 | def set_vocab(self) |
| tools/conversion/bert.py | function | set_gguf_parameters | 590 | def set_gguf_parameters(self) |
| tools/conversion/bert.py | function | filter_tensors | 599 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/bert.py | function | modify_tensors | 607 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bitnet.py | class | BitnetModel | 12 | class BitnetModel(TextModel) |
| tools/conversion/bitnet.py | function | set_vocab | 15 | def set_vocab(self) |
| tools/conversion/bitnet.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/bitnet.py | function | weight_quant | 23 | def weight_quant(self, weight: Tensor) -> Tensor |
| tools/conversion/bitnet.py | function | modify_tensors | 34 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/bloom.py | class | BloomModel | 16 | class BloomModel(TextModel) |
| tools/conversion/bloom.py | function | set_gguf_parameters | 19 | def set_gguf_parameters(self) |
| tools/conversion/bloom.py | function | modify_tensors | 33 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/chameleon.py | class | ChameleonModel | 15 | class ChameleonModel(TextModel) |
| tools/conversion/chameleon.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/chameleon.py | function | set_vocab | 22 | def set_vocab(self) |
| tools/conversion/chameleon.py | function | filter_tensors | 26 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/chameleon.py | function | modify_tensors | 36 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/chameleon.py | function | _reverse_hf_permute | 54 | def _reverse_hf_permute(data_torch, n_heads, hidden_dim) |
| tools/conversion/chatglm.py | class | ChatGLMModel | 12 | class ChatGLMModel(TextModel) |
| tools/conversion/chatglm.py | function | set_vocab_chatglm3 | 15 | def set_vocab_chatglm3(self) |
| tools/conversion/chatglm.py | function | token_bytes_to_string | 83 | def token_bytes_to_string(b) |
| tools/conversion/chatglm.py | function | bpe | 89 | def bpe(mergeable_ranks: dict[bytes, int], token: bytes, max_rank: int \| None = None) -> list[bytes] |
| tools/conversion/chatglm.py | function | set_vocab | 105 | def set_vocab(self) |
| tools/conversion/chatglm.py | function | set_gguf_parameters | 133 | def set_gguf_parameters(self) |
| tools/conversion/chatglm.py | function | filter_tensors | 159 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/codeshell.py | class | CodeShellModel | 7 | class CodeShellModel(TextModel) |
| tools/conversion/codeshell.py | function | set_gguf_parameters | 10 | def set_gguf_parameters(self) |
| tools/conversion/cogvlm.py | class | CogVLMVisionModel | 14 | class CogVLMVisionModel(MmprojModel) |
| tools/conversion/cogvlm.py | function | set_gguf_parameters | 16 | def set_gguf_parameters(self) |
| tools/conversion/cogvlm.py | function | filter_tensors | 22 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/cogvlm.py | class | CogVLMModel | 32 | class CogVLMModel(LlamaModel) |
| tools/conversion/command_r.py | class | CommandR2Model | 14 | class CommandR2Model(TextModel) |
| tools/conversion/command_r.py | function | __init__ | 17 | def __init__(self, *args, **kwargs) |
| tools/conversion/command_r.py | function | set_gguf_parameters | 25 | def set_gguf_parameters(self) |
| tools/conversion/command_r.py | class | Cohere2Model | 32 | class Cohere2Model(TextModel) |
| tools/conversion/command_r.py | function | set_gguf_parameters | 35 | def set_gguf_parameters(self) |
| tools/conversion/command_r.py | function | modify_tensors | 48 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/dbrx.py | class | DbrxModel | 12 | class DbrxModel(TextModel) |
| tools/conversion/dbrx.py | function | set_gguf_parameters | 15 | def set_gguf_parameters(self) |
| tools/conversion/dbrx.py | function | modify_tensors | 39 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/dbrx.py | function | tensor_force_quant | 72 | def tensor_force_quant(self, name: str, new_name: str, bid: int \| None, n_dims: int) -> gguf.GGMLQuantizationType \| bool |
| tools/conversion/deci.py | class | DeciModel | 16 | class DeciModel(TextModel) |
| tools/conversion/deci.py | function | _ffn_mult_to_intermediate_size | 20 | def _ffn_mult_to_intermediate_size(ffn_mult: float, n_embd: int) -> int |
| tools/conversion/deci.py | function | _find_multiple | 26 | def _find_multiple(n: int, k: int) -> int |
| tools/conversion/deci.py | function | __init__ | 32 | def __init__(self, *args, **kwargs) |
| tools/conversion/deci.py | function | set_vocab | 80 | def set_vocab(self) |
| tools/conversion/deci.py | function | set_gguf_parameters | 96 | def set_gguf_parameters(self) |
| tools/conversion/deci.py | function | permute | 127 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| tools/conversion/deci.py | function | modify_tensors | 134 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/deci.py | function | generate_extra_tensors | 153 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/deci.py | function | prepare_tensors | 183 | def prepare_tensors(self) |
| tools/conversion/deepseek.py | class | DeepseekOCRVisionModel | 18 | class DeepseekOCRVisionModel(MmprojModel) |
| tools/conversion/deepseek.py | function | __init__ | 19 | def __init__(self, *args, **kwargs) |
| tools/conversion/deepseek.py | function | set_gguf_parameters | 23 | def set_gguf_parameters(self) |
| tools/conversion/deepseek.py | function | get_vision_config | 49 | def get_vision_config(self) -> dict[str, Any] |
| tools/conversion/deepseek.py | function | tensor_force_quant | 66 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/deepseek.py | function | modify_tensors | 72 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/deepseek.py | function | filter_tensors | 78 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/deepseek.py | class | DeepseekOCR2VisionModel | 94 | class DeepseekOCR2VisionModel(DeepseekOCRVisionModel) |
| tools/conversion/deepseek.py | function | __init__ | 95 | def __init__(self, *args, **kwargs) |
| tools/conversion/deepseek.py | function | set_gguf_parameters | 99 | def set_gguf_parameters(self) |
| tools/conversion/deepseek.py | function | get_vision_config | 112 | def get_vision_config(self) -> dict[str, Any] |
| tools/conversion/deepseek.py | class | DeepseekModel | 121 | class DeepseekModel(TextModel) |
| tools/conversion/deepseek.py | function | set_vocab | 124 | def set_vocab(self) |
| tools/conversion/deepseek.py | function | set_gguf_parameters | 130 | def set_gguf_parameters(self) |
| tools/conversion/deepseek.py | function | permute | 148 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| tools/conversion/deepseek.py | function | modify_tensors | 155 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/deepseek.py | function | prepare_tensors | 195 | def prepare_tensors(self) |
| tools/conversion/deepseek.py | class | DeepseekV2Model | 213 | class DeepseekV2Model(TextModel) |
| tools/conversion/deepseek.py | function | __init__ | 221 | def __init__(self, *args, **kwargs) |
| tools/conversion/deepseek.py | function | filter_tensors | 235 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/deepseek.py | function | set_vocab | 242 | def set_vocab(self) |
| tools/conversion/deepseek.py | function | set_gguf_parameters | 296 | def set_gguf_parameters(self) |
| tools/conversion/deepseek.py | function | modify_tensors | 361 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/deepseek.py | function | prepare_tensors | 425 | def prepare_tensors(self) |
| tools/conversion/deepseek.py | class | DeepseekV32Model | 436 | class DeepseekV32Model(DeepseekV2Model) |
| tools/conversion/deepseek.py | function | __init__ | 440 | def __init__(self, *args, **kwargs) |
| tools/conversion/deepseek.py | function | set_vocab | 445 | def set_vocab(self) |
| tools/conversion/deepseek.py | function | set_gguf_parameters | 451 | def set_gguf_parameters(self) |
| tools/conversion/dots1.py | class | Dots1Model | 14 | class Dots1Model(Qwen2MoeModel) |
| tools/conversion/dots1.py | function | __init__ | 17 | def __init__(self, *args, **kwargs) |
| tools/conversion/dots1.py | function | set_gguf_parameters | 21 | def set_gguf_parameters(self) |
| tools/conversion/dots1.py | function | modify_tensors | 28 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| tools/conversion/dotsocr.py | class | DotsOCRVisionModel | 12 | class DotsOCRVisionModel(MmprojModel) |
| tools/conversion/dotsocr.py | function | __init__ | 13 | def __init__(self, *args, **kwargs) |
| tools/conversion/dotsocr.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/dotsocr.py | function | filter_tensors | 28 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/dotsocr.py | function | modify_tensors | 47 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/dream.py | class | DreamModel | 12 | class DreamModel(TextModel) |
| tools/conversion/dream.py | function | get_vocab_base | 15 | def get_vocab_base(self) -> tuple[list[str], list[int], str] |
| tools/conversion/dream.py | function | set_vocab | 52 | def set_vocab(self) |
| tools/conversion/dream.py | function | set_gguf_parameters | 58 | def set_gguf_parameters(self) |
| tools/conversion/dream.py | function | modify_tensors | 70 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ernie.py | class | Ernie4_5Model | 18 | class Ernie4_5Model(TextModel) |
| tools/conversion/ernie.py | function | set_vocab | 21 | def set_vocab(self) |
| tools/conversion/ernie.py | function | set_gguf_parameters | 31 | def set_gguf_parameters(self) |
| tools/conversion/ernie.py | function | filter_tensors | 35 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/ernie.py | function | modify_tensors | 43 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ernie.py | class | Ernie4_5MoeModel | 76 | class Ernie4_5MoeModel(Ernie4_5Model) |
| tools/conversion/ernie.py | function | __init__ | 80 | def __init__(self, *args, **kwargs) |
| tools/conversion/ernie.py | function | set_gguf_parameters | 84 | def set_gguf_parameters(self) |
| tools/conversion/ernie.py | function | filter_tensors | 98 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/ernie.py | function | modify_tensors | 121 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ernie.py | function | prepare_tensors | 148 | def prepare_tensors(self) |
| tools/conversion/ernie.py | class | PaddleOCRModel | 159 | class PaddleOCRModel(Ernie4_5Model) |
| tools/conversion/ernie.py | class | PaddleOCRVisionModel | 164 | class PaddleOCRVisionModel(MmprojModel) |
| tools/conversion/ernie.py | function | __init__ | 169 | def __init__(self, *args, **kwargs) |
| tools/conversion/ernie.py | function | set_gguf_parameters | 176 | def set_gguf_parameters(self) |
| tools/conversion/ernie.py | function | filter_tensors | 187 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/exaone.py | class | ExaoneModel | 17 | class ExaoneModel(TextModel) |
| tools/conversion/exaone.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/exaone.py | function | generate_extra_tensors | 30 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/exaone.py | class | Exaone4Model | 62 | class Exaone4Model(TextModel) |
| tools/conversion/exaone.py | function | set_vocab | 65 | def set_vocab(self) |
| tools/conversion/exaone.py | function | set_gguf_parameters | 75 | def set_gguf_parameters(self) |
| tools/conversion/exaone.py | function | generate_extra_tensors | 95 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/exaone.py | class | ExaoneMoEModel | 126 | class ExaoneMoEModel(Exaone4Model) |
| tools/conversion/exaone.py | function | __init__ | 129 | def __init__(self, *args, **kwargs) |
| tools/conversion/exaone.py | function | set_gguf_parameters | 134 | def set_gguf_parameters(self) |
| tools/conversion/exaone.py | function | modify_tensors | 151 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/exaone.py | function | prepare_tensors | 204 | def prepare_tensors(self) |
| tools/conversion/falcon.py | class | FalconModel | 14 | class FalconModel(TextModel) |
| tools/conversion/falcon.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| tools/conversion/falcon.py | function | modify_tensors | 36 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/falcon_h1.py | class | FalconH1Model | 15 | class FalconH1Model(Mamba2Model) |
| tools/conversion/falcon_h1.py | function | __init__ | 18 | def __init__(self, *args, **kwargs) |
| tools/conversion/falcon_h1.py | function | find_hparam | 46 | def find_hparam(self, keys: Iterable[str], *args, **kwargs) -> Any |
| tools/conversion/falcon_h1.py | function | set_vocab | 56 | def set_vocab(self) |
| tools/conversion/falcon_h1.py | function | modify_tensors | 59 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/falcon_h1.py | function | set_gguf_parameters | 97 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | class | GemmaModel | 17 | class GemmaModel(TextModel) |
| tools/conversion/gemma.py | function | set_vocab | 20 | def set_vocab(self) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 36 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | filter_tensors | 51 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/gemma.py | function | modify_tensors | 62 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | Gemma2Model | 71 | class Gemma2Model(TextModel) |
| tools/conversion/gemma.py | function | set_vocab | 74 | def set_vocab(self) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 79 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | filter_tensors | 101 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/gemma.py | function | modify_tensors | 112 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | Gemma3Model | 121 | class Gemma3Model(TextModel) |
| tools/conversion/gemma.py | function | norm_shift | 124 | def norm_shift(self, name: str) -> float |
| tools/conversion/gemma.py | function | set_vocab | 127 | def set_vocab(self) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 134 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | modify_tensors | 153 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | EmbeddingGemma | 177 | class EmbeddingGemma(Gemma3Model) |
| tools/conversion/gemma.py | function | __init__ | 182 | def __init__(self, *args, **kwargs) |
| tools/conversion/gemma.py | function | generate_extra_tensors | 207 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | function | _get_dense_prefix | 222 | def _get_dense_prefix(module_path) -> str |
| tools/conversion/gemma.py | function | set_gguf_parameters | 227 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | class | Gemma3VisionModel | 251 | class Gemma3VisionModel(MmprojModel) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 252 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | tensor_force_quant | 270 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/gemma.py | function | filter_tensors | 279 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/gemma.py | function | modify_tensors | 293 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | ConformerAudioModel | 304 | class ConformerAudioModel(MmprojModel) |
| tools/conversion/gemma.py | function | is_audio_tensor | 308 | def is_audio_tensor(name: str) |
| tools/conversion/gemma.py | function | tensor_force_quant | 311 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/gemma.py | function | modify_tensors | 317 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | Gemma3nVisionAudioModel | 355 | class Gemma3nVisionAudioModel(ConformerAudioModel) |
| tools/conversion/gemma.py | function | __init__ | 386 | def __init__(self, *args, **kwargs) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 413 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | tensor_force_quant | 426 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/gemma.py | function | custom_map | 434 | def custom_map(self, name: str) -> str |
| tools/conversion/gemma.py | function | modify_tensors | 447 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | Gemma3NModel | 474 | class Gemma3NModel(Gemma3Model) |
| tools/conversion/gemma.py | function | __init__ | 480 | def __init__(self, *args, **kwargs) |
| tools/conversion/gemma.py | function | norm_shift | 494 | def norm_shift(self, name: str) -> float |
| tools/conversion/gemma.py | function | set_vocab | 498 | def set_vocab(self) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 518 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | _stack_matrices | 537 | def _stack_matrices(self, matrices: list[Tensor]) -> Tensor \| None |
| tools/conversion/gemma.py | function | filter_tensors | 545 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/gemma.py | function | modify_tensors | 553 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | Gemma4Model | 618 | class Gemma4Model(Gemma3Model) |
| tools/conversion/gemma.py | function | norm_shift | 621 | def norm_shift(self, name: str) -> float |
| tools/conversion/gemma.py | function | set_vocab | 625 | def set_vocab(self) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 655 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | generate_extra_tensors | 702 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | function | _generate_nvfp4_tensors | 719 | def _generate_nvfp4_tensors(self) |
| tools/conversion/gemma.py | function | filter_tensors | 744 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/gemma.py | function | modify_tensors | 754 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gemma.py | class | Gemma4VisionAudioModel | 769 | class Gemma4VisionAudioModel(MmprojModel) |
| tools/conversion/gemma.py | function | __init__ | 773 | def __init__(self, *args, **kwargs) |
| tools/conversion/gemma.py | function | set_gguf_parameters | 785 | def set_gguf_parameters(self) |
| tools/conversion/gemma.py | function | is_audio_tensor | 799 | def is_audio_tensor(self, name: str) -> bool |
| tools/conversion/gemma.py | function | tensor_force_quant | 802 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/gemma.py | function | modify_tensors | 810 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/glm.py | class | Glm4Model | 16 | class Glm4Model(TextModel) |
| tools/conversion/glm.py | function | __init__ | 21 | def __init__(self, *args, **kwargs) |
| tools/conversion/glm.py | function | set_vocab | 28 | def set_vocab(self) |
| tools/conversion/glm.py | function | set_gguf_parameters | 44 | def set_gguf_parameters(self) |
| tools/conversion/glm.py | function | normal_to_neox | 51 | def normal_to_neox(weights: Tensor, n_head: int, n_head_kv: int, head_dim: int, partial_rotary_factor: float) -> Tensor |
| tools/conversion/glm.py | function | modify_tensors | 72 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/glm.py | class | GlmOCRModel | 87 | class GlmOCRModel(Glm4Model) |
| tools/conversion/glm.py | function | __init__ | 94 | def __init__(self, *args, **kwargs) |
| tools/conversion/glm.py | function | set_gguf_parameters | 100 | def set_gguf_parameters(self) |
| tools/conversion/glm.py | class | Glm4MoeModel | 108 | class Glm4MoeModel(TextModel) |
| tools/conversion/glm.py | function | __init__ | 111 | def __init__(self, *args, **kwargs) |
| tools/conversion/glm.py | function | set_vocab | 117 | def set_vocab(self) |
| tools/conversion/glm.py | function | set_gguf_parameters | 120 | def set_gguf_parameters(self) |
| tools/conversion/glm.py | function | modify_tensors | 158 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/glm.py | function | prepare_tensors | 195 | def prepare_tensors(self) |
| tools/conversion/glm.py | class | Glm4MoeLiteModel | 205 | class Glm4MoeLiteModel(DeepseekV2Model) |
| tools/conversion/glm.py | function | set_vocab | 208 | def set_vocab(self) |
| tools/conversion/glm.py | class | GlmMoeDsaModel | 213 | class GlmMoeDsaModel(DeepseekV2Model) |
| tools/conversion/glm.py | function | __init__ | 217 | def __init__(self, *args, **kwargs) |
| tools/conversion/glm.py | function | set_vocab | 222 | def set_vocab(self) |
| tools/conversion/glm.py | function | set_gguf_parameters | 225 | def set_gguf_parameters(self) |
| tools/conversion/glm.py | class | SolarOpenModel | 243 | class SolarOpenModel(Glm4MoeModel) |
| tools/conversion/glm.py | function | set_vocab | 246 | def set_vocab(self) |
| tools/conversion/gpt2.py | class | GPT2Model | 14 | class GPT2Model(TextModel) |
| tools/conversion/gpt2.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| tools/conversion/gpt2.py | function | modify_tensors | 26 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gpt2.py | class | RuGPT3XLModel | 41 | class RuGPT3XLModel(TextModel) |
| tools/conversion/gpt2.py | function | modify_tensors | 46 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gpt2.py | function | prepare_tensors | 71 | def prepare_tensors(self) |
| tools/conversion/gpt_oss.py | class | GptOssModel | 14 | class GptOssModel(TextModel) |
| tools/conversion/gpt_oss.py | function | dequant_model | 18 | def dequant_model(self) |
| tools/conversion/gpt_oss.py | function | transform_nibble_layout | 23 | def transform_nibble_layout(self, tensor) |
| tools/conversion/gpt_oss.py | function | repack_mxfp4 | 48 | def repack_mxfp4(self, new_name: str, blocks: Tensor, scales: Tensor) |
| tools/conversion/gpt_oss.py | function | generate_extra_tensors | 63 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gpt_oss.py | function | filter_tensors | 84 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/gpt_oss.py | function | modify_tensors | 92 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/gpt_oss.py | function | set_vocab | 124 | def set_vocab(self) |
| tools/conversion/gpt_oss.py | function | set_gguf_parameters | 127 | def set_gguf_parameters(self) |
| tools/conversion/gptneox.py | class | GPTNeoXModel | 16 | class GPTNeoXModel(TextModel) |
| tools/conversion/gptneox.py | function | set_gguf_parameters | 19 | def set_gguf_parameters(self) |
| tools/conversion/gptneox.py | function | modify_tensors | 31 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/granite.py | class | GraniteModel | 17 | class GraniteModel(LlamaModel) |
| tools/conversion/granite.py | function | set_gguf_parameters | 21 | def set_gguf_parameters(self) |
| tools/conversion/granite.py | function | filter_tensors | 50 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/granite.py | class | GraniteMoeModel | 58 | class GraniteMoeModel(GraniteModel) |
| tools/conversion/granite.py | function | set_gguf_parameters | 62 | def set_gguf_parameters(self) |
| tools/conversion/granite.py | function | modify_tensors | 71 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/granite.py | class | GraniteHybridModel | 108 | class GraniteHybridModel(Mamba2Model, GraniteMoeModel) |
| tools/conversion/granite.py | function | __init__ | 114 | def __init__(self, *args, **kwargs) |
| tools/conversion/granite.py | function | get_attn_layers | 153 | def get_attn_layers(self) |
| tools/conversion/granite.py | function | find_hparam | 174 | def find_hparam(self, keys: Iterable[str], *args, **kwargs) -> Any |
| tools/conversion/granite.py | function | modify_tensors | 184 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/granite.py | function | set_gguf_parameters | 201 | def set_gguf_parameters(self) |
| tools/conversion/granite.py | function | set_vocab | 243 | def set_vocab(self) |
| tools/conversion/granite.py | class | GraniteSpeechMmprojModel | 249 | class GraniteSpeechMmprojModel(MmprojModel) |
| tools/conversion/granite.py | function | get_audio_config | 255 | def get_audio_config(self) -> dict[str, Any] \| None |
| tools/conversion/granite.py | function | set_gguf_parameters | 258 | def set_gguf_parameters(self) |
| tools/conversion/granite.py | function | tensor_force_quant | 280 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/granite.py | function | filter_tensors | 287 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/granite.py | function | modify_tensors | 293 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/grok.py | class | GrokModel | 16 | class GrokModel(TextModel) |
| tools/conversion/grok.py | function | set_vocab | 19 | def set_vocab(self) |
| tools/conversion/grok.py | function | __init__ | 30 | def __init__(self, *args, **kwargs) |
| tools/conversion/grok.py | function | set_gguf_parameters | 33 | def set_gguf_parameters(self) |
| tools/conversion/grok.py | function | modify_tensors | 67 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/grovemoe.py | class | GroveMoeModel | 14 | class GroveMoeModel(TextModel) |
| tools/conversion/grovemoe.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| tools/conversion/grovemoe.py | function | modify_tensors | 32 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/grovemoe.py | function | prepare_tensors | 95 | def prepare_tensors(self) |
| tools/conversion/hunyuan.py | class | HunYuanMoEModel | 19 | class HunYuanMoEModel(TextModel) |
| tools/conversion/hunyuan.py | function | set_vocab | 22 | def set_vocab(self) |
| tools/conversion/hunyuan.py | function | set_gguf_parameters | 73 | def set_gguf_parameters(self) |
| tools/conversion/hunyuan.py | function | modify_tensors | 112 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/hunyuan.py | function | prepare_tensors | 147 | def prepare_tensors(self) |
| tools/conversion/hunyuan.py | class | HunYuanModel | 156 | class HunYuanModel(TextModel) |
| tools/conversion/hunyuan.py | function | _get_eod_token_id | 159 | def _get_eod_token_id(self) -> int \| None |
| tools/conversion/hunyuan.py | function | _get_eot_token_id | 163 | def _get_eot_token_id(self) -> int \| None |
| tools/conversion/hunyuan.py | function | _fix_special_tokens | 175 | def _fix_special_tokens(self) |
| tools/conversion/hunyuan.py | function | set_vocab | 184 | def set_vocab(self) |
| tools/conversion/hunyuan.py | function | set_gguf_parameters | 253 | def set_gguf_parameters(self) |
| tools/conversion/hunyuan.py | function | modify_tensors | 282 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/hunyuan.py | class | HunyuanVLVisionModel | 292 | class HunyuanVLVisionModel(MmprojModel) |
| tools/conversion/hunyuan.py | function | __init__ | 293 | def __init__(self, *args, **kwargs) |
| tools/conversion/hunyuan.py | function | set_gguf_parameters | 300 | def set_gguf_parameters(self) |
| tools/conversion/hunyuan.py | function | filter_tensors | 312 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/hunyuan.py | function | modify_tensors | 320 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/hunyuan.py | function | tensor_force_quant | 326 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/hunyuan.py | class | HunyuanVLTextModel | 335 | class HunyuanVLTextModel(HunYuanModel) |
| tools/conversion/hunyuan.py | function | __init__ | 338 | def __init__(self, dir_model: Path, *args, **kwargs) |
| tools/conversion/hunyuan.py | function | set_gguf_parameters | 341 | def set_gguf_parameters(self) |
| tools/conversion/internlm.py | class | InternLM2Model | 17 | class InternLM2Model(TextModel) |
| tools/conversion/internlm.py | function | set_vocab | 20 | def set_vocab(self) |
| tools/conversion/internlm.py | function | modify_tensors | 146 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/internlm.py | class | InternLM3Model | 173 | class InternLM3Model(TextModel) |
| tools/conversion/internlm.py | function | set_vocab | 176 | def set_vocab(self) |
| tools/conversion/internlm.py | function | set_gguf_parameters | 206 | def set_gguf_parameters(self) |
| tools/conversion/internlm.py | function | filter_tensors | 216 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/internlm.py | function | modify_tensors | 225 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/internvl.py | class | InternVisionModel | 12 | class InternVisionModel(MmprojModel) |
| tools/conversion/internvl.py | function | __init__ | 17 | def __init__(self, *args, **kwargs) |
| tools/conversion/internvl.py | function | set_gguf_parameters | 23 | def set_gguf_parameters(self) |
| tools/conversion/internvl.py | function | tensor_force_quant | 51 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/internvl.py | function | filter_tensors | 57 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/internvl.py | function | modify_tensors | 82 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/jais.py | class | Jais2Model | 14 | class Jais2Model(TextModel) |
| tools/conversion/jais.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| tools/conversion/jais.py | class | JaisModel | 25 | class JaisModel(TextModel) |
| tools/conversion/jais.py | function | __init__ | 28 | def __init__(self, *args, **kwargs) |
| tools/conversion/jais.py | function | set_vocab | 56 | def set_vocab(self) |
| tools/conversion/jais.py | function | set_gguf_parameters | 59 | def set_gguf_parameters(self) |
| tools/conversion/jais.py | function | filter_tensors | 69 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/jais.py | function | modify_tensors | 78 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/jais.py | function | prepare_tensors | 102 | def prepare_tensors(self) |
| tools/conversion/jamba.py | class | JambaModel | 14 | class JambaModel(TextModel) |
| tools/conversion/jamba.py | function | set_vocab | 17 | def set_vocab(self) |
| tools/conversion/jamba.py | function | set_gguf_parameters | 24 | def set_gguf_parameters(self) |
| tools/conversion/jamba.py | function | modify_tensors | 58 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/jamba.py | function | prepare_tensors | 112 | def prepare_tensors(self) |
| tools/conversion/januspro.py | class | JanusProModel | 14 | class JanusProModel(LlamaModel) |
| tools/conversion/januspro.py | function | filter_tensors | 18 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/januspro.py | class | JanusProVisionModel | 37 | class JanusProVisionModel(MmprojModel) |
| tools/conversion/januspro.py | function | __init__ | 38 | def __init__(self, *args, **kwargs) |
| tools/conversion/januspro.py | function | set_gguf_parameters | 47 | def set_gguf_parameters(self) |
| tools/conversion/januspro.py | function | _map_aligner_tensor | 61 | def _map_aligner_tensor(self, data_torch: Tensor, name: str) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/januspro.py | function | filter_tensors | 86 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/januspro.py | function | modify_tensors | 105 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/kimi_linear.py | class | KimiLinearModel | 16 | class KimiLinearModel(TextModel) |
| tools/conversion/kimi_linear.py | function | set_vocab | 22 | def set_vocab(self) |
| tools/conversion/kimi_linear.py | function | set_gguf_parameters | 77 | def set_gguf_parameters(self) |
| tools/conversion/kimi_linear.py | function | prepare_tensors | 143 | def prepare_tensors(self) |
| tools/conversion/kimi_linear.py | function | modify_tensors | 150 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/kimivl.py | class | KimiVLModel | 14 | class KimiVLModel(MmprojModel) |
| tools/conversion/kimivl.py | function | __init__ | 15 | def __init__(self, *args, **kwargs) |
| tools/conversion/kimivl.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/kimivl.py | function | filter_tensors | 30 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/kimivl.py | function | modify_tensors | 40 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/kimivl.py | class | KimiK25Model | 55 | class KimiK25Model(MmprojModel) |
| tools/conversion/kimivl.py | function | __init__ | 58 | def __init__(self, *args, **kwargs) |
| tools/conversion/kimivl.py | function | set_gguf_parameters | 71 | def set_gguf_parameters(self) |
| tools/conversion/kimivl.py | function | permute | 100 | def permute(weights: Tensor, n_head: int) -> Tensor |
| tools/conversion/kimivl.py | function | filter_tensors | 108 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/kimivl.py | function | modify_tensors | 119 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/lfm2.py | class | LFM2Model | 16 | class LFM2Model(TextModel) |
| tools/conversion/lfm2.py | function | _add_feed_forward_length | 19 | def _add_feed_forward_length(self) |
| tools/conversion/lfm2.py | function | set_gguf_parameters | 34 | def set_gguf_parameters(self) |
| tools/conversion/lfm2.py | function | filter_tensors | 48 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/lfm2.py | function | modify_tensors | 59 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/lfm2.py | class | LFM2ColBertModel | 68 | class LFM2ColBertModel(LFM2Model) |
| tools/conversion/lfm2.py | function | modify_tensors | 72 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/lfm2.py | function | generate_extra_tensors | 78 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/lfm2.py | class | LFM2MoeModel | 89 | class LFM2MoeModel(TextModel) |
| tools/conversion/lfm2.py | function | set_gguf_parameters | 92 | def set_gguf_parameters(self) |
| tools/conversion/lfm2.py | function | filter_tensors | 112 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/lfm2.py | function | modify_tensors | 120 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/lfm2.py | function | prepare_tensors | 156 | def prepare_tensors(self) |
| tools/conversion/lfm2.py | class | LFM2VLModel | 162 | class LFM2VLModel(MmprojModel) |
| tools/conversion/lfm2.py | function | __init__ | 163 | def __init__(self, *args, **kwargs) |
| tools/conversion/lfm2.py | function | set_gguf_parameters | 169 | def set_gguf_parameters(self) |
| tools/conversion/lfm2.py | function | filter_tensors | 180 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/lfm2.py | function | modify_tensors | 188 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/lfm2.py | class | LFM2AudioModel | 196 | class LFM2AudioModel(ConformerAudioModel) |
| tools/conversion/lfm2.py | function | get_audio_config | 201 | def get_audio_config(self) -> dict[str, Any] \| None |
| tools/conversion/lfm2.py | function | set_gguf_parameters | 204 | def set_gguf_parameters(self) |
| tools/conversion/lfm2.py | function | filter_tensors | 215 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/lfm2.py | class | LFM25AudioTokenizer | 234 | class LFM25AudioTokenizer(LFM2Model) |
| tools/conversion/lfm2.py | function | set_vocab | 237 | def set_vocab(self) |
| tools/conversion/lfm2.py | function | set_gguf_parameters | 240 | def set_gguf_parameters(self) |
| tools/conversion/lfm2.py | function | filter_tensors | 246 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/lighton_ocr.py | class | LightOnOCRVisionModel | 14 | class LightOnOCRVisionModel(LlavaVisionModel) |
| tools/conversion/lighton_ocr.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/lighton_ocr.py | function | filter_tensors | 23 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/llada.py | class | LLaDAModel | 14 | class LLaDAModel(TextModel) |
| tools/conversion/llada.py | function | get_vocab_base | 18 | def get_vocab_base(self) -> tuple[list[str], list[int], str] |
| tools/conversion/llada.py | function | set_vocab | 55 | def set_vocab(self) |
| tools/conversion/llada.py | function | set_gguf_parameters | 61 | def set_gguf_parameters(self) |
| tools/conversion/llada.py | function | permute | 94 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| tools/conversion/llada.py | function | modify_tensors | 101 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/llada.py | class | LLaDAMoEModel | 117 | class LLaDAMoEModel(TextModel) |
| tools/conversion/llada.py | function | set_gguf_parameters | 120 | def set_gguf_parameters(self) |
| tools/conversion/llada.py | function | modify_tensors | 132 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/llada.py | function | prepare_tensors | 165 | def prepare_tensors(self) |
| tools/conversion/llama.py | class | LlamaModel | 26 | class LlamaModel(TextModel) |
| tools/conversion/llama.py | function | __init__ | 30 | def __init__(self, *args, **kwargs) |
| tools/conversion/llama.py | function | set_vocab | 42 | def set_vocab(self) |
| tools/conversion/llama.py | function | set_gguf_parameters | 88 | def set_gguf_parameters(self) |
| tools/conversion/llama.py | function | permute | 100 | def permute(weights: Tensor, n_head: int, n_head_kv: int \| None) |
| tools/conversion/llama.py | function | _repack_nvfp4 | 107 | def _repack_nvfp4(self, name: str, weight: Tensor, scale: Tensor, scale2: Tensor, input_scale: Tensor) |
| tools/conversion/llama.py | function | filter_tensors | 124 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/llama.py | function | modify_tensors | 132 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/llama.py | function | generate_extra_tensors | 177 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/llama.py | function | prepare_tensors | 207 | def prepare_tensors(self) |
| tools/conversion/llama.py | class | ArceeModel | 218 | class ArceeModel(LlamaModel) |
| tools/conversion/llama.py | function | set_gguf_parameters | 221 | def set_gguf_parameters(self) |
| tools/conversion/llama.py | class | Llama4Model | 230 | class Llama4Model(LlamaModel) |
| tools/conversion/llama.py | function | __init__ | 234 | def __init__(self, *args, **kwargs) |
| tools/conversion/llama.py | function | set_vocab | 240 | def set_vocab(self) |
| tools/conversion/llama.py | function | set_gguf_parameters | 243 | def set_gguf_parameters(self) |
| tools/conversion/llama.py | function | modify_tensors | 252 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| tools/conversion/llama.py | class | LlamaEmbedNemotronModel | 271 | class LlamaEmbedNemotronModel(LlamaModel) |
| tools/conversion/llama.py | class | SmolLM3Model | 276 | class SmolLM3Model(LlamaModel) |
| tools/conversion/llama.py | class | ApertusModel | 281 | class ApertusModel(LlamaModel) |
| tools/conversion/llama.py | function | modify_tensors | 290 | def modify_tensors(self, data_torch, name, bid) |
| tools/conversion/llama4.py | class | Llama4VisionModel | 12 | class Llama4VisionModel(MmprojModel) |
| tools/conversion/llama4.py | function | set_gguf_parameters | 13 | def set_gguf_parameters(self) |
| tools/conversion/llama4.py | function | filter_tensors | 22 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/llama4.py | function | modify_tensors | 33 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/llava.py | class | LlavaVisionModel | 19 | class LlavaVisionModel(MmprojModel) |
| tools/conversion/llava.py | function | __init__ | 23 | def __init__(self, *args, **kwargs) |
| tools/conversion/llava.py | function | get_token_id | 45 | def get_token_id(self, token: str) -> int |
| tools/conversion/llava.py | function | get_mistral_token_id | 60 | def get_mistral_token_id(self, token: str) -> int |
| tools/conversion/llava.py | function | set_gguf_parameters | 78 | def set_gguf_parameters(self) |
| tools/conversion/llava.py | function | modify_tensors | 97 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/maincoder.py | class | MaincoderModel | 7 | class MaincoderModel(TextModel) |
| tools/conversion/maincoder.py | function | set_gguf_parameters | 10 | def set_gguf_parameters(self) |
| tools/conversion/mamba.py | class | MambaModel | 17 | class MambaModel(TextModel) |
| tools/conversion/mamba.py | function | __init__ | 20 | def __init__(self, dir_model: Path, *args, **kwargs) |
| tools/conversion/mamba.py | function | set_vocab | 28 | def set_vocab(self) |
| tools/conversion/mamba.py | function | set_gguf_parameters | 45 | def set_gguf_parameters(self) |
| tools/conversion/mamba.py | function | modify_tensors | 77 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/mamba.py | class | Mamba2Model | 103 | class Mamba2Model(TextModel) |
| tools/conversion/mamba.py | function | __init__ | 106 | def __init__(self, dir_model: Path, *args, **kwargs) |
| tools/conversion/mamba.py | function | set_vocab | 120 | def set_vocab(self) |
| tools/conversion/mamba.py | function | set_gguf_parameters | 140 | def set_gguf_parameters(self) |
| tools/conversion/mamba.py | function | filter_tensors | 168 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/mamba.py | function | modify_tensors | 180 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/mimo.py | class | MimoV2Model | 16 | class MimoV2Model(TextModel) |
| tools/conversion/mimo.py | function | __init__ | 23 | def __init__(self, *args, **kwargs) |
| tools/conversion/mimo.py | function | _tp_aware_qkv_dequant | 30 | def _tp_aware_qkv_dequant(weight: Tensor, scale_inv: Tensor, n_q: int, n_kv: int, hd: int, vhd: int, bs: int = 128) -> Tensor |
| tools/conversion/mimo.py | function | dequant_model | 95 | def dequant_model(self) |
| tools/conversion/mimo.py | function | set_gguf_parameters | 135 | def set_gguf_parameters(self) |
| tools/conversion/mimo.py | function | filter_tensors | 171 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/mimo.py | function | modify_tensors | 179 | def modify_tensors(self, data_torch, name, bid) |
| tools/conversion/mimo.py | function | prepare_tensors | 221 | def prepare_tensors(self) |
| tools/conversion/mimo.py | class | MiMoV2VisionModel | 232 | class MiMoV2VisionModel(MmprojModel) |
| tools/conversion/mimo.py | function | __init__ | 233 | def __init__(self, *args, **kwargs) |
| tools/conversion/mimo.py | function | set_gguf_parameters | 256 | def set_gguf_parameters(self) |
| tools/conversion/mimo.py | function | tensor_force_quant | 269 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/mimo.py | function | filter_tensors | 277 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/mimo.py | function | modify_tensors | 283 | def modify_tensors(self, data_torch, name, bid) |
| tools/conversion/minicpm.py | class | MiniCPMModel | 17 | class MiniCPMModel(TextModel) |
| tools/conversion/minicpm.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/minicpm.py | function | generate_extra_tensors | 32 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/minicpm.py | function | set_vocab | 49 | def set_vocab(self) |
| tools/conversion/minicpm.py | function | modify_tensors | 52 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/minicpm.py | class | MiniCPM3Model | 66 | class MiniCPM3Model(TextModel) |
| tools/conversion/minicpm.py | function | set_gguf_parameters | 69 | def set_gguf_parameters(self) |
| tools/conversion/minicpm.py | function | generate_extra_tensors | 87 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/minicpm.py | function | set_vocab | 104 | def set_vocab(self) |
| tools/conversion/minicpm.py | function | _reverse_hf_permute | 107 | def _reverse_hf_permute(self, weights: Tensor, n_head: int, n_kv_head: int \| None = None) -> Tensor |
| tools/conversion/minicpm.py | class | MiniCPMV4_6TextModel | 124 | class MiniCPMV4_6TextModel(Qwen3_5TextModel) |
| tools/conversion/minicpm.py | function | filter_tensors | 128 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/minicpm.py | class | MiniCPMV4_6VisionModel | 141 | class MiniCPMV4_6VisionModel(MmprojModel) |
| tools/conversion/minicpm.py | function | __init__ | 142 | def __init__(self, *args, **kwargs) |
| tools/conversion/minicpm.py | function | set_gguf_parameters | 155 | def set_gguf_parameters(self) |
| tools/conversion/minicpm.py | function | filter_tensors | 177 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/minimax.py | class | MiniMaxM2Model | 14 | class MiniMaxM2Model(TextModel) |
| tools/conversion/minimax.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/minimax.py | function | modify_tensors | 24 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| tools/conversion/mistral.py | class | MistralModel | 24 | class MistralModel(LlamaModel) |
| tools/conversion/mistral.py | function | __init__ | 31 | def __init__(self, *args, **kwargs) |
| tools/conversion/mistral.py | function | dequant_model | 41 | def dequant_model(self) |
| tools/conversion/mistral.py | function | get_community_chat_template | 54 | def get_community_chat_template(vocab: MistralVocab, templates_dir: Path, is_mistral_format: bool) |
| tools/conversion/mistral.py | function | set_gguf_parameters | 92 | def set_gguf_parameters(self) |
| tools/conversion/mistral.py | function | set_mistral_config | 97 | def set_mistral_config(gguf_writer: gguf.GGUFWriter, hparams: dict) |
| tools/conversion/mistral.py | class | MistralMoeModel | 112 | class MistralMoeModel(DeepseekV2Model) |
| tools/conversion/mistral.py | function | __init__ | 118 | def __init__(self, *args, **kwargs) |
| tools/conversion/mistral.py | function | set_vocab | 169 | def set_vocab(self) |
| tools/conversion/mistral.py | function | set_gguf_parameters | 172 | def set_gguf_parameters(self) |
| tools/conversion/mistral.py | function | filter_tensors | 184 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/mistral3.py | class | Mistral3Model | 18 | class Mistral3Model(TextModel) |
| tools/conversion/mistral3.py | class | Ministral3Model | 19 | class Ministral3Model(LlamaModel) |
| tools/conversion/mistral3.py | function | set_gguf_parameters | 22 | def set_gguf_parameters(self) |
| tools/conversion/mistral3.py | class | Mistral4Model | 31 | class Mistral4Model(DeepseekV2Model) |
| tools/conversion/mistral3.py | function | modify_tensors | 36 | def modify_tensors(self, data_torch, name, bid) |
| tools/conversion/mistral3.py | function | __init__ | 44 | def __init__(self, *args, **kwargs) |
| tools/conversion/mistral3.py | function | set_vocab | 51 | def set_vocab(self) |
| tools/conversion/mistral3.py | function | set_gguf_parameters | 54 | def set_gguf_parameters(self) |
| tools/conversion/mistral3.py | function | modify_tensors | 57 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| tools/conversion/mistral3.py | function | prepare_tensors | 60 | def prepare_tensors(self) |
| tools/conversion/mistral3.py | function | write_vocab | 63 | def write_vocab(self) |
| tools/conversion/mistral3.py | function | write | 66 | def write(self) |
| tools/conversion/mpt.py | class | MPTModel | 12 | class MPTModel(TextModel) |
| tools/conversion/mpt.py | function | set_vocab | 15 | def set_vocab(self) |
| tools/conversion/mpt.py | function | set_gguf_parameters | 26 | def set_gguf_parameters(self) |
| tools/conversion/mpt.py | function | modify_tensors | 42 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/nemotron.py | class | NemotronNanoV2VLModel | 19 | class NemotronNanoV2VLModel(MmprojModel) |
| tools/conversion/nemotron.py | function | get_vision_config | 26 | def get_vision_config(self) -> dict[str, Any] \| None |
| tools/conversion/nemotron.py | function | set_gguf_parameters | 42 | def set_gguf_parameters(self) |
| tools/conversion/nemotron.py | function | tensor_force_quant | 56 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/nemotron.py | function | filter_tensors | 62 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/nemotron.py | function | modify_tensors | 81 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/nemotron.py | class | NemotronModel | 111 | class NemotronModel(TextModel) |
| tools/conversion/nemotron.py | function | set_vocab | 114 | def set_vocab(self) |
| tools/conversion/nemotron.py | function | set_gguf_parameters | 119 | def set_gguf_parameters(self) |
| tools/conversion/nemotron.py | function | modify_tensors | 140 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/nemotron.py | class | NemotronHModel | 152 | class NemotronHModel(GraniteHybridModel) |
| tools/conversion/nemotron.py | function | __init__ | 157 | def __init__(self, *args, **kwargs) |
| tools/conversion/nemotron.py | function | get_attn_layers | 195 | def get_attn_layers(self) |
| tools/conversion/nemotron.py | function | set_gguf_parameters | 205 | def set_gguf_parameters(self) |
| tools/conversion/nemotron.py | function | set_vocab | 243 | def set_vocab(self) |
| tools/conversion/nemotron.py | function | modify_tensors | 309 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/nemotron.py | function | prepare_tensors | 377 | def prepare_tensors(self) |
| tools/conversion/olmo.py | class | OlmoModel | 17 | class OlmoModel(TextModel) |
| tools/conversion/olmo.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/olmo.py | function | modify_tensors | 29 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/olmo.py | class | SeedOssModel | 42 | class SeedOssModel(TextModel) |
| tools/conversion/olmo.py | class | Olmo2Model | 48 | class Olmo2Model(TextModel) |
| tools/conversion/olmo.py | function | set_gguf_parameters | 51 | def set_gguf_parameters(self) |
| tools/conversion/olmo.py | class | OlmoeModel | 70 | class OlmoeModel(TextModel) |
| tools/conversion/olmo.py | function | set_gguf_parameters | 73 | def set_gguf_parameters(self) |
| tools/conversion/olmo.py | function | modify_tensors | 80 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/olmo.py | function | prepare_tensors | 113 | def prepare_tensors(self) |
| tools/conversion/openelm.py | class | OpenELMModel | 12 | class OpenELMModel(TextModel) |
| tools/conversion/openelm.py | function | _make_divisible | 16 | def _make_divisible(v: float \| int, divisor: int) -> int |
| tools/conversion/openelm.py | function | __init__ | 24 | def __init__(self, *args, **kwargs) |
| tools/conversion/openelm.py | function | set_vocab | 40 | def set_vocab(self) |
| tools/conversion/openelm.py | function | set_gguf_parameters | 46 | def set_gguf_parameters(self) |
| tools/conversion/openelm.py | function | find_hparam | 68 | def find_hparam(self, keys: Iterable[str], optional: bool = False) -> Any |
| tools/conversion/openelm.py | function | modify_tensors | 74 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/orion.py | class | OrionModel | 7 | class OrionModel(TextModel) |
| tools/conversion/orion.py | function | set_vocab | 10 | def set_vocab(self) |
| tools/conversion/orion.py | function | set_gguf_parameters | 13 | def set_gguf_parameters(self) |
| tools/conversion/pangu.py | class | PanguEmbeddedModel | 14 | class PanguEmbeddedModel(TextModel) |
| tools/conversion/pangu.py | function | set_vocab | 17 | def set_vocab(self) |
| tools/conversion/pangu.py | function | set_gguf_parameters | 27 | def set_gguf_parameters(self) |
| tools/conversion/pangu.py | function | modify_tensors | 41 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/phi.py | class | Phi2Model | 17 | class Phi2Model(TextModel) |
| tools/conversion/phi.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/phi.py | class | Phi3MiniModel | 39 | class Phi3MiniModel(TextModel) |
| tools/conversion/phi.py | function | set_vocab | 42 | def set_vocab(self) |
| tools/conversion/phi.py | function | set_gguf_parameters | 146 | def set_gguf_parameters(self) |
| tools/conversion/phi.py | function | generate_extra_tensors | 173 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/phi.py | class | Phi4VisionMmprojModel | 215 | class Phi4VisionMmprojModel(MmprojModel) |
| tools/conversion/phi.py | function | __init__ | 216 | def __init__(self, *args, **kwargs) |
| tools/conversion/phi.py | function | set_gguf_parameters | 272 | def set_gguf_parameters(self) |
| tools/conversion/phi.py | function | filter_tensors | 283 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/phi.py | function | modify_tensors | 299 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/phi.py | class | PhiMoeModel | 341 | class PhiMoeModel(Phi3MiniModel) |
| tools/conversion/phi.py | function | set_gguf_parameters | 346 | def set_gguf_parameters(self) |
| tools/conversion/phi.py | function | modify_tensors | 351 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/phi.py | function | prepare_tensors | 383 | def prepare_tensors(self) |
| tools/conversion/pixtral.py | class | PixtralModel | 10 | class PixtralModel(LlavaVisionModel) |
| tools/conversion/pixtral.py | function | set_gguf_parameters | 15 | def set_gguf_parameters(self) |
| tools/conversion/pixtral.py | function | map_tensor_name | 32 | def map_tensor_name(self, name: str, try_suffixes: Sequence[str] = (".weight", ".bias")) -> str |
| tools/conversion/plamo.py | class | PlamoModel | 16 | class PlamoModel(TextModel) |
| tools/conversion/plamo.py | function | set_vocab | 19 | def set_vocab(self) |
| tools/conversion/plamo.py | function | set_gguf_parameters | 22 | def set_gguf_parameters(self) |
| tools/conversion/plamo.py | function | shuffle_attn_q_weight | 34 | def shuffle_attn_q_weight(self, data_torch) |
| tools/conversion/plamo.py | function | shuffle_attn_output_weight | 41 | def shuffle_attn_output_weight(self, data_torch) |
| tools/conversion/plamo.py | function | modify_tensors | 48 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/plamo.py | class | Plamo2Model | 61 | class Plamo2Model(TextModel) |
| tools/conversion/plamo.py | function | set_vocab | 64 | def set_vocab(self) |
| tools/conversion/plamo.py | function | set_gguf_parameters | 67 | def set_gguf_parameters(self) |
| tools/conversion/plamo.py | function | modify_tensors | 117 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/plamo.py | class | Plamo3Model | 150 | class Plamo3Model(TextModel) |
| tools/conversion/plamo.py | function | set_vocab | 153 | def set_vocab(self) |
| tools/conversion/plamo.py | function | set_gguf_parameters | 173 | def set_gguf_parameters(self) |
| tools/conversion/plamo.py | function | modify_tensors | 180 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/plm.py | class | PLMModel | 7 | class PLMModel(TextModel) |
| tools/conversion/plm.py | function | set_vocab | 10 | def set_vocab(self) |
| tools/conversion/plm.py | function | set_gguf_parameters | 13 | def set_gguf_parameters(self) |
| tools/conversion/plm.py | function | prepare_tensors | 22 | def prepare_tensors(self) |
| tools/conversion/qwen.py | class | QwenModel | 14 | class QwenModel(TextModel) |
| tools/conversion/qwen.py | function | token_bytes_to_string | 18 | def token_bytes_to_string(b) |
| tools/conversion/qwen.py | function | bpe | 24 | def bpe(mergeable_ranks: dict[bytes, int], token: bytes, max_rank: int \| None = None) -> list[bytes] |
| tools/conversion/qwen.py | function | set_vocab | 40 | def set_vocab(self) |
| tools/conversion/qwen.py | class | Qwen2Model | 52 | class Qwen2Model(TextModel) |
| tools/conversion/qwen.py | function | set_vocab | 55 | def set_vocab(self) |
| tools/conversion/qwen.py | function | set_gguf_parameters | 61 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | function | modify_tensors | 65 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen.py | class | Qwen2MoeModel | 72 | class Qwen2MoeModel(TextModel) |
| tools/conversion/qwen.py | function | set_gguf_parameters | 75 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | function | modify_tensors | 86 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen.py | function | prepare_tensors | 143 | def prepare_tensors(self) |
| tools/conversion/qwen.py | class | Qwen3Model | 154 | class Qwen3Model(Qwen2Model) |
| tools/conversion/qwen.py | function | __init__ | 163 | def __init__(self, *args, **kwargs) |
| tools/conversion/qwen.py | function | _is_qwen3_reranker | 173 | def _is_qwen3_reranker(self) -> bool |
| tools/conversion/qwen.py | function | set_vocab | 196 | def set_vocab(self) |
| tools/conversion/qwen.py | function | _find_rerank_config | 204 | def _find_rerank_config(self) |
| tools/conversion/qwen.py | function | set_gguf_parameters | 216 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | function | _get_cls_out_tensor | 228 | def _get_cls_out_tensor(self, data_torch: Tensor) -> Tensor |
| tools/conversion/qwen.py | function | modify_tensors | 234 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen.py | class | Qwen3MoeModel | 252 | class Qwen3MoeModel(Qwen2MoeModel) |
| tools/conversion/qwen.py | function | __init__ | 255 | def __init__(self, *args, **kwargs) |
| tools/conversion/qwen.py | function | set_vocab | 260 | def set_vocab(self) |
| tools/conversion/qwen.py | class | Qwen3NextModel | 270 | class Qwen3NextModel(Qwen2MoeModel) |
| tools/conversion/qwen.py | function | set_gguf_parameters | 273 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | function | filter_tensors | 286 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwen.py | function | modify_tensors | 295 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen.py | class | RND1Model | 339 | class RND1Model(Qwen2MoeModel) |
| tools/conversion/qwen.py | function | set_gguf_parameters | 342 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | class | _LinearAttentionVReorderBase | 353 | class _LinearAttentionVReorderBase(Qwen3NextModel) |
| tools/conversion/qwen.py | function | _reorder_v_heads | 367 | def _reorder_v_heads(tensor: Tensor, dim: int, num_k_heads: int, num_v_per_k: int, head_dim: int) -> Tensor |
| tools/conversion/qwen.py | function | _transform_nvfp4_weight | 378 | def _transform_nvfp4_weight(self, name: str, weight: Tensor, scale: Tensor) -> tuple[Tensor, Tensor] |
| tools/conversion/qwen.py | function | unpack_nibbles | 394 | def unpack_nibbles(qs: Tensor) -> Tensor |
| tools/conversion/qwen.py | function | pack_nibbles | 399 | def pack_nibbles(codes: Tensor) -> Tensor |
| tools/conversion/qwen.py | function | apply_col_perm | 405 | def apply_col_perm(qs: Tensor, scales: Tensor, col_perm: Tensor) -> tuple[Tensor, Tensor] |
| tools/conversion/qwen.py | function | reorder_rows | 430 | def reorder_rows(qs: Tensor, scales: Tensor, head_dim: int) -> tuple[Tensor, Tensor] |
| tools/conversion/qwen.py | function | _repack_nvfp4 | 465 | def _repack_nvfp4(self, name: str, weight: Tensor, scale: Tensor, scale2: Tensor, input_scale: Tensor) |
| tools/conversion/qwen.py | function | modify_tensors | 469 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen.py | class | _Qwen35MRopeMixin | 521 | class _Qwen35MRopeMixin |
| tools/conversion/qwen.py | function | set_gguf_parameters | 531 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | class | _Qwen35MtpMixin | 537 | class _Qwen35MtpMixin |
| tools/conversion/qwen.py | function | __init__ | 553 | def __init__(self, *args, **kwargs) |
| tools/conversion/qwen.py | function | index_tensors | 560 | def index_tensors(self, remote_hf_model_id: str \| None = None) -> dict[str, Callable[[], Tensor]] |
| tools/conversion/qwen.py | function | filter_tensors | 567 | def filter_tensors(cls, item) |
| tools/conversion/qwen.py | function | set_gguf_parameters | 599 | def set_gguf_parameters(self) |
| tools/conversion/qwen.py | function | prepare_metadata | 606 | def prepare_metadata(self, vocab_only: bool) |
| tools/conversion/qwen.py | class | Qwen3_5TextModel | 621 | class Qwen3_5TextModel(_Qwen35MtpMixin, _Qwen35MRopeMixin, _LinearAttentionVReorderBase) |
| tools/conversion/qwen.py | class | Qwen3_5MoeTextModel | 626 | class Qwen3_5MoeTextModel(_Qwen35MtpMixin, _Qwen35MRopeMixin, _LinearAttentionVReorderBase) |
| tools/conversion/qwen3vl.py | class | Qwen3VLVisionModel | 17 | class Qwen3VLVisionModel(MmprojModel) |
| tools/conversion/qwen3vl.py | function | __init__ | 18 | def __init__(self, *args, **kwargs) |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 42 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | function | filter_tensors | 62 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwen3vl.py | function | modify_tensors | 81 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen3vl.py | class | Qwen3OmniMmprojModel | 147 | class Qwen3OmniMmprojModel(Qwen3VLVisionModel, Qwen25AudioModel) |
| tools/conversion/qwen3vl.py | function | get_vision_config | 151 | def get_vision_config(self) -> dict[str, Any] \| None |
| tools/conversion/qwen3vl.py | function | get_audio_config | 157 | def get_audio_config(self) -> dict[str, Any] \| None |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 163 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | function | filter_tensors | 172 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwen3vl.py | function | modify_tensors | 194 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen3vl.py | class | Qwen3ASRMmprojModel | 220 | class Qwen3ASRMmprojModel(Qwen3OmniMmprojModel) |
| tools/conversion/qwen3vl.py | class | Glm4VVisionModel | 226 | class Glm4VVisionModel(Qwen3VLVisionModel) |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 227 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | function | modify_tensors | 241 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen3vl.py | class | Qwen3VLTextModel | 249 | class Qwen3VLTextModel(Qwen3Model) |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 252 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | function | filter_tensors | 262 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwen3vl.py | class | Qwen3VLMoeTextModel | 271 | class Qwen3VLMoeTextModel(Qwen3MoeModel) |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 274 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | function | filter_tensors | 281 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwen3vl.py | function | modify_tensors | 288 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwen3vl.py | class | Qwen3OmniMoeTextModel | 320 | class Qwen3OmniMoeTextModel(Qwen3VLMoeTextModel) |
| tools/conversion/qwen3vl.py | function | set_vocab | 323 | def set_vocab(self) |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 335 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | class | Qwen3ASRTextModel | 341 | class Qwen3ASRTextModel(Qwen3VLTextModel) |
| tools/conversion/qwen3vl.py | function | set_gguf_parameters | 344 | def set_gguf_parameters(self) |
| tools/conversion/qwen3vl.py | function | set_vocab | 348 | def set_vocab(self) |
| tools/conversion/qwenvl.py | class | Qwen2VLModel | 20 | class Qwen2VLModel(TextModel) |
| tools/conversion/qwenvl.py | function | set_gguf_parameters | 23 | def set_gguf_parameters(self) |
| tools/conversion/qwenvl.py | function | set_vocab | 26 | def set_vocab(self) |
| tools/conversion/qwenvl.py | function | filter_tensors | 33 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwenvl.py | class | Qwen2VLVisionModel | 43 | class Qwen2VLVisionModel(MmprojModel) |
| tools/conversion/qwenvl.py | function | __init__ | 44 | def __init__(self, *args, **kwargs) |
| tools/conversion/qwenvl.py | function | set_gguf_parameters | 55 | def set_gguf_parameters(self) |
| tools/conversion/qwenvl.py | function | tensor_force_quant | 82 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/qwenvl.py | function | filter_tensors | 88 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwenvl.py | function | modify_tensors | 96 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwenvl.py | class | Qwen25AudioModel | 122 | class Qwen25AudioModel(MmprojModel) |
| tools/conversion/qwenvl.py | function | __init__ | 125 | def __init__(self, *args, **kwargs) |
| tools/conversion/qwenvl.py | function | set_gguf_parameters | 132 | def set_gguf_parameters(self) |
| tools/conversion/qwenvl.py | function | generate_extra_tensors | 138 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwenvl.py | function | tensor_force_quant | 150 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/qwenvl.py | function | modify_tensors | 155 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/qwenvl.py | class | Qwen25OmniModel | 164 | class Qwen25OmniModel(Qwen2VLVisionModel, Qwen25AudioModel) |
| tools/conversion/qwenvl.py | function | get_vision_config | 168 | def get_vision_config(self) -> dict[str, Any] \| None |
| tools/conversion/qwenvl.py | function | get_audio_config | 171 | def get_audio_config(self) -> dict[str, Any] \| None |
| tools/conversion/qwenvl.py | function | set_gguf_parameters | 174 | def set_gguf_parameters(self) |
| tools/conversion/qwenvl.py | function | filter_tensors | 179 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/qwenvl.py | function | modify_tensors | 195 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/refact.py | class | RefactModel | 12 | class RefactModel(TextModel) |
| tools/conversion/refact.py | function | set_vocab | 15 | def set_vocab(self) |
| tools/conversion/refact.py | function | set_gguf_parameters | 27 | def set_gguf_parameters(self) |
| tools/conversion/refact.py | function | modify_tensors | 45 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/rwkv.py | class | Rwkv6Model | 14 | class Rwkv6Model(TextModel) |
| tools/conversion/rwkv.py | function | set_vocab | 17 | def set_vocab(self) |
| tools/conversion/rwkv.py | function | set_gguf_parameters | 20 | def set_gguf_parameters(self) |
| tools/conversion/rwkv.py | function | modify_tensors | 46 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/rwkv.py | class | RWKV6Qwen2Model | 86 | class RWKV6Qwen2Model(Rwkv6Model) |
| tools/conversion/rwkv.py | function | set_vocab | 89 | def set_vocab(self) |
| tools/conversion/rwkv.py | function | set_gguf_parameters | 95 | def set_gguf_parameters(self) |
| tools/conversion/rwkv.py | function | modify_tensors | 124 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/rwkv.py | class | Rwkv7Model | 139 | class Rwkv7Model(TextModel) |
| tools/conversion/rwkv.py | function | set_vocab | 142 | def set_vocab(self) |
| tools/conversion/rwkv.py | function | calc_lora_rank | 145 | def calc_lora_rank(self, hidden_size, exponent, multiplier) |
| tools/conversion/rwkv.py | function | set_gguf_parameters | 148 | def set_gguf_parameters(self) |
| tools/conversion/rwkv.py | function | filter_tensors | 190 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/rwkv.py | function | modify_tensors | 203 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/rwkv.py | class | ARwkv7Model | 264 | class ARwkv7Model(Rwkv7Model) |
| tools/conversion/rwkv.py | function | set_vocab | 267 | def set_vocab(self) |
| tools/conversion/rwkv.py | function | set_gguf_parameters | 273 | def set_gguf_parameters(self) |
| tools/conversion/sarashina2.py | class | Sarashina2VLTextModel | 15 | class Sarashina2VLTextModel(LlamaModel) |
| tools/conversion/sarashina2.py | function | filter_tensors | 19 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/sarashina2.py | class | Sarashina2VLVisionModel | 29 | class Sarashina2VLVisionModel(Qwen2VLVisionModel) |
| tools/conversion/sarashina2.py | function | __init__ | 30 | def __init__(self, *args, **kwargs) |
| tools/conversion/smallthinker.py | class | SmallThinkerModel | 14 | class SmallThinkerModel(TextModel) |
| tools/conversion/smallthinker.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| tools/conversion/smallthinker.py | function | modify_tensors | 43 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/smallthinker.py | function | prepare_tensors | 75 | def prepare_tensors(self) |
| tools/conversion/smolvlm.py | class | SmolVLMModel | 12 | class SmolVLMModel(MmprojModel) |
| tools/conversion/smolvlm.py | function | __init__ | 13 | def __init__(self, *args, **kwargs) |
| tools/conversion/smolvlm.py | function | set_gguf_parameters | 22 | def set_gguf_parameters(self) |
| tools/conversion/smolvlm.py | function | tensor_force_quant | 33 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/smolvlm.py | function | filter_tensors | 39 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/stablelm.py | class | StableLMModel | 14 | class StableLMModel(TextModel) |
| tools/conversion/stablelm.py | function | set_vocab | 17 | def set_vocab(self) |
| tools/conversion/stablelm.py | function | set_gguf_parameters | 24 | def set_gguf_parameters(self) |
| tools/conversion/stablelm.py | function | modify_tensors | 42 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/stablelm.py | function | _stack_qk_norm | 74 | def _stack_qk_norm(self, bid: int, n_head: int, norms: dict[str, Tensor], layer_name: str = "q_layernorm") |
| tools/conversion/stablelm.py | function | prepare_tensors | 87 | def prepare_tensors(self) |
| tools/conversion/starcoder.py | class | StarCoderModel | 7 | class StarCoderModel(TextModel) |
| tools/conversion/starcoder.py | function | set_gguf_parameters | 10 | def set_gguf_parameters(self) |
| tools/conversion/starcoder.py | class | StarCoder2Model | 22 | class StarCoder2Model(TextModel) |
| tools/conversion/step3.py | class | Step3VLVisionModel | 19 | class Step3VLVisionModel(MmprojModel) |
| tools/conversion/step3.py | function | __init__ | 20 | def __init__(self, *args, **kwargs) |
| tools/conversion/step3.py | function | set_gguf_parameters | 33 | def set_gguf_parameters(self) |
| tools/conversion/step3.py | function | tensor_force_quant | 50 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/step3.py | function | filter_tensors | 58 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/step3.py | function | modify_tensors | 66 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/step3.py | class | Step3VLTextModel | 94 | class Step3VLTextModel(Qwen3Model) |
| tools/conversion/step3.py | class | Step35Model | 99 | class Step35Model(TextModel) |
| tools/conversion/step3.py | function | set_gguf_parameters | 102 | def set_gguf_parameters(self) |
| tools/conversion/step3.py | function | filter_tensors | 169 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/step3.py | function | modify_tensors | 178 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) |
| tools/conversion/step3.py | function | generate_extra_tensors | 193 | def generate_extra_tensors(self) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/t5.py | class | T5Model | 19 | class T5Model(TextModel) |
| tools/conversion/t5.py | function | __init__ | 22 | def __init__(self, *args, **kwargs) |
| tools/conversion/t5.py | function | set_vocab | 26 | def set_vocab(self) |
| tools/conversion/t5.py | function | set_gguf_parameters | 120 | def set_gguf_parameters(self) |
| tools/conversion/t5.py | function | modify_tensors | 139 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/t5.py | class | T5EncoderModel | 156 | class T5EncoderModel(TextModel) |
| tools/conversion/t5.py | function | __init__ | 159 | def __init__(self, *args, **kwargs) |
| tools/conversion/t5.py | function | set_vocab | 163 | def set_vocab(self) |
| tools/conversion/t5.py | function | set_gguf_parameters | 257 | def set_gguf_parameters(self) |
| tools/conversion/t5.py | function | modify_tensors | 273 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/talkie.py | class | TalkieModel | 14 | class TalkieModel(TextModel) |
| tools/conversion/talkie.py | function | set_gguf_parameters | 17 | def set_gguf_parameters(self) |
| tools/conversion/talkie.py | function | modify_tensors | 22 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ultravox.py | class | UltravoxModel | 12 | class UltravoxModel(TextModel) |
| tools/conversion/ultravox.py | function | __init__ | 15 | def __init__(self, *args, **kwargs) |
| tools/conversion/ultravox.py | class | GlmASRWhisperEncoderModel | 21 | class GlmASRWhisperEncoderModel(MmprojModel) |
| tools/conversion/ultravox.py | function | __init__ | 25 | def __init__(self, *args, **kwargs) |
| tools/conversion/ultravox.py | function | set_gguf_parameters | 32 | def set_gguf_parameters(self) |
| tools/conversion/ultravox.py | function | tensor_force_quant | 39 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/ultravox.py | function | filter_tensors | 45 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/ultravox.py | function | modify_tensors | 67 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ultravox.py | class | WhisperEncoderModel | 85 | class WhisperEncoderModel(MmprojModel) |
| tools/conversion/ultravox.py | function | __init__ | 89 | def __init__(self, *args, **kwargs) |
| tools/conversion/ultravox.py | function | set_gguf_parameters | 96 | def set_gguf_parameters(self) |
| tools/conversion/ultravox.py | function | tensor_force_quant | 102 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/ultravox.py | function | filter_tensors | 108 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/ultravox.py | function | modify_tensors | 117 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ultravox.py | class | UltravoxWhisperEncoderModel | 126 | class UltravoxWhisperEncoderModel(WhisperEncoderModel) |
| tools/conversion/ultravox.py | function | set_gguf_parameters | 130 | def set_gguf_parameters(self) |
| tools/conversion/ultravox.py | class | MERaLiONWhisperEncoderModel | 137 | class MERaLiONWhisperEncoderModel(WhisperEncoderModel) |
| tools/conversion/ultravox.py | function | get_audio_config | 141 | def get_audio_config(self) -> dict[str, Any] \| None |
| tools/conversion/ultravox.py | function | set_gguf_parameters | 144 | def set_gguf_parameters(self) |
| tools/conversion/ultravox.py | function | filter_tensors | 150 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/ultravox.py | function | modify_tensors | 161 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/ultravox.py | class | VoxtralWhisperEncoderModel | 183 | class VoxtralWhisperEncoderModel(WhisperEncoderModel) |
| tools/conversion/ultravox.py | function | set_gguf_parameters | 187 | def set_gguf_parameters(self) |
| tools/conversion/ultravox.py | class | AudioFlamingo3WhisperEncoderModel | 194 | class AudioFlamingo3WhisperEncoderModel(WhisperEncoderModel) |
| tools/conversion/ultravox.py | function | set_gguf_parameters | 195 | def set_gguf_parameters(self) |
| tools/conversion/ultravox.py | function | tensor_force_quant | 199 | def tensor_force_quant(self, name, new_name, bid, n_dims) |
| tools/conversion/wavtokenizer.py | class | WavTokenizerDecModel | 12 | class WavTokenizerDecModel(TextModel) |
| tools/conversion/wavtokenizer.py | function | filter_tensors | 16 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/wavtokenizer.py | function | set_vocab | 28 | def set_vocab(self) |
| tools/conversion/wavtokenizer.py | function | set_gguf_parameters | 31 | def set_gguf_parameters(self) |
| tools/conversion/xverse.py | class | XverseModel | 14 | class XverseModel(TextModel) |
| tools/conversion/xverse.py | function | set_vocab | 17 | def set_vocab(self) |
| tools/conversion/xverse.py | function | set_gguf_parameters | 64 | def set_gguf_parameters(self) |
| tools/conversion/xverse.py | function | modify_tensors | 70 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/conversion/xverse.py | function | _reverse_hf_permute | 82 | def _reverse_hf_permute(self, weights: Tensor, n_head: int, n_kv_head: int \| None = None) -> Tensor |
| tools/conversion/youtuvl.py | class | YoutuVLVisionModel | 12 | class YoutuVLVisionModel(MmprojModel) |
| tools/conversion/youtuvl.py | function | __init__ | 13 | def __init__(self, *args, **kwargs) |
| tools/conversion/youtuvl.py | function | set_gguf_parameters | 18 | def set_gguf_parameters(self) |
| tools/conversion/youtuvl.py | function | filter_tensors | 47 | def filter_tensors(cls, item: tuple[str, Callable[[], Tensor]]) -> tuple[str, Callable[[], Tensor]] \| None |
| tools/conversion/youtuvl.py | function | modify_tensors | 57 | def modify_tensors(self, data_torch: Tensor, name: str, bid: int \| None) -> Iterable[tuple[str, Tensor]] |
| tools/decrypt_logs.py | function | derive_key | 48 | def derive_key(token: str) -> bytes |
| tools/decrypt_logs.py | function | main | 67 | def main() |
| training/validate_dataset.py | function | _build_token_estimator | 43 | def _build_token_estimator(block_size_override: int \| None) -> tuple |
| training/validate_dataset.py | function | _model_estimate | 59 | def _model_estimate(text: str) -> int |
| training/validate_dataset.py | function | _heuristic_estimate | 69 | def _heuristic_estimate(text: str) -> int |
| training/validate_dataset.py | function | _detect_format | 77 | def _detect_format(rec: dict) -> str |
| training/validate_dataset.py | function | _record_text | 90 | def _record_text(rec: dict, fmt: str) -> str |
| training/validate_dataset.py | function | _validate_sft | 113 | def _validate_sft(rec: dict, lineno: int) -> tuple[list[str], list[str]] |
| training/validate_dataset.py | function | _validate_dpo | 126 | def _validate_dpo(rec: dict, lineno: int) -> tuple[list[str], list[str]] |
| training/validate_dataset.py | function | _validate_chat | 141 | def _validate_chat(rec: dict, lineno: int) -> tuple[list[str], list[str]] |
| training/validate_dataset.py | function | _pass | 163 | def _pass(msg: str) |
| training/validate_dataset.py | function | _fail | 166 | def _fail(msg: str) |
| training/validate_dataset.py | function | _info | 169 | def _info(msg: str) |
| training/validate_dataset.py | function | _indent | 172 | def _indent(lines: list[str], limit: int = 10) |
| training/validate_dataset.py | function | _sanitize_text | 191 | def _sanitize_text(s: str) -> str |
| training/validate_dataset.py | function | _sanitize_record | 196 | def _sanitize_record(rec: dict) -> tuple[dict, bool] |
| training/validate_dataset.py | function | _walk | 203 | def _walk(obj) |
| training/validate_dataset.py | function | _reasoning_guard | 219 | def _reasoning_guard(text: str) -> str |
| training/validate_dataset.py | function | _truncate_text | 230 | def _truncate_text(text: str, max_chars: int) -> str |
| training/validate_dataset.py | function | _truncate_record | 238 | def _truncate_record(rec: dict, fmt: str, char_budget: int) -> dict |
| training/validate_dataset.py | function | _repair_schema | 320 | def _repair_schema(rec: dict, fmt: str) -> tuple[dict, bool] |
| training/validate_dataset.py | function | validate | 365 | def validate(path: str, block_size_override: int \| None = None) -> bool |
| training/validate_dataset.py | function | _print_report | 495 | def _print_report( total: int, json_errors: int, schema_failures: int, |
| training/validate_dataset.py | function | repair | 523 | def repair(path: str, block_size_override: int \| None = None) -> None |
| training/validate_dataset.py | function | install_git_hook | 621 | def install_git_hook() |
| training/validate_dataset.py | function | main | 688 | def main() |
| vscode-extension/extension.js | function | readServiceDiscovery | 21 | function readServiceDiscovery() { |
| vscode-extension/extension.js | function | activate | 31 | function activate(context) { |
| vscode-extension/extension.js | function | register | 50 | const register = (command, handler) => { |
| vscode-extension/extension.js | function | _getSelectionOrFile | 76 | function _getSelectionOrFile(editor) { |
| vscode-extension/extension.js | function | _sendToKarlWebview | 85 | function _sendToKarlWebview(command, payload) { |
| vscode-extension/extension.js | class | MiniGptInlineCompletionProvider | 235 | class MiniGptInlineCompletionProvider { |
| vscode-extension/extension.js | function | killProc | 399 | const killProc = () => { |
| vscode-extension/extension.js | function | settle | 405 | const settle = (fn, value) => { |
| vscode-extension/extension.js | function | deactivate | 475 | function deactivate() { |
| vscode-extension/media/karl.js | function | bindEvents | 116 | function bindEvents() { |
| vscode-extension/media/karl.js | function | startWorkflow | 410 | function startWorkflow(workflowId, data) { |
| vscode-extension/media/karl.js | function | askWorkspace | 449 | function askWorkspace() { |
| vscode-extension/media/karl.js | function | connectAndRun | 455 | function connectAndRun() { |
| vscode-extension/media/karl.js | function | runSwarm | 473 | function runSwarm() { |
| vscode-extension/media/karl.js | function | stopSwarm | 500 | function stopSwarm() { |
| vscode-extension/media/karl.js | function | _initThoughtsPanel | 507 | function _initThoughtsPanel() { |
| vscode-extension/media/karl.js | function | sendChatMessage | 552 | function sendChatMessage() { |
| vscode-extension/media/karl.js | function | handleResponseToken | 579 | function handleResponseToken(token) { |
| vscode-extension/media/karl.js | function | handleChatFinished | 605 | function handleChatFinished() { |
| vscode-extension/media/karl.js | function | activeBranch | 643 | function activeBranch() { |
| vscode-extension/media/karl.js | function | createConversationBranch | 648 | function createConversationBranch(seedTitle = '') { |
| vscode-extension/media/karl.js | function | branchFromLatest | 662 | function branchFromLatest() { |
| vscode-extension/media/karl.js | function | recordConversationTurn | 678 | function recordConversationTurn(user, assistant) { |
| vscode-extension/media/karl.js | function | addPendingEdit | 691 | function addPendingEdit(edit) { |
| vscode-extension/media/karl.js | function | markPendingEdit | 697 | function markPendingEdit(editId, status) { |
| vscode-extension/media/karl.js | function | removePendingEdit | 706 | function removePendingEdit(editId, state) { |
| vscode-extension/media/karl.js | function | runLab | 712 | function runLab() { |
| vscode-extension/media/karl.js | function | sendLabMessage | 733 | function sendLabMessage(target, systemPrompt, userMsg) { |
| vscode-extension/media/karl.js | function | computeLabDiff | 743 | function computeLabDiff() { |
| vscode-extension/media/karl.js | function | loadSelectedPromptPair | 747 | function loadSelectedPromptPair() { |
| vscode-extension/media/karl.js | function | savePromptPair | 752 | function savePromptPair() { |
| vscode-extension/media/karl.js | function | deletePromptPair | 776 | function deletePromptPair() { |
| vscode-extension/media/karl.js | function | applyPromptPair | 781 | function applyPromptPair(result) { |
| vscode-extension/media/karl.js | function | addKbQueuePath | 799 | function addKbQueuePath() { |
| vscode-extension/media/karl.js | function | ingestKbQueue | 809 | function ingestKbQueue() { |
| vscode-extension/media/karl.js | function | ingestNextQueuedPath | 817 | function ingestNextQueuedPath() { |
| vscode-extension/media/karl.js | function | markCurrentKbQueueDone | 832 | function markCurrentKbQueueDone(status) { |
| vscode-extension/media/karl.js | function | ingestKbPath | 840 | function ingestKbPath() { |
| vscode-extension/media/karl.js | function | searchKb | 866 | function searchKb() { |
| vscode-extension/media/karl.js | function | requiresBridgeSupport | 882 | function requiresBridgeSupport(feature, method) { |
| vscode-extension/media/karl.js | function | validateTrainingForm | 896 | function validateTrainingForm() { |
| vscode-extension/media/karl.js | function | rememberTask | 900 | function rememberTask(workflowId, title, objective, filepath) { |
| vscode-extension/media/karl.js | function | rememberKbQuery | 911 | function rememberKbQuery(query) { |
| vscode-extension/media/karl.js | function | addTask | 917 | function addTask(mode, objective) { |
| vscode-extension/media/karl.js | function | finishActiveTask | 924 | function finishActiveTask(status) { |
| vscode-extension/media/karl.js | function | filterCodex | 931 | function filterCodex() { |
| vscode-extension/media/karl.js | function | hyperparams | 938 | function hyperparams() { |
| vscode-extension/media/karl.js | function | _initWsStateObserver | 953 | function _initWsStateObserver() { |
| vscode-extension/media/karl.js | function | _sync | 956 | function _sync() { |
| vscode-extension/media/karl.js | function | _initChatInnerTabs | 969 | function _initChatInnerTabs() { |
| vscode-extension/media/karl.js | function | _switchChatInnerTab | 1047 | function _switchChatInnerTab(panelId) { |
| vscode-extension/media/karl.js | function | _initLogsSubtabs | 1064 | function _initLogsSubtabs() { |
| vscode-extension/media/karl.js | function | fitTfidfVectorizer | 1127 | function fitTfidfVectorizer(documents) { |
| vscode-extension/media/karl.js | function | tokenize | 1130 | function tokenize(text) { |
| vscode-extension/media/karl.js | function | renderVectorizerResults | 1185 | function renderVectorizerResults(vocabulary, vectors, docs) { |
| vscode-extension/media/karl.js | function | handleInterceptedTelemetry | 1216 | function handleInterceptedTelemetry(msg) { |
| vscode-extension/media/karl.js | function | startMiniGptSimulation | 1259 | function startMiniGptSimulation(maxIters, lr) { |
| vscode-extension/media/karl.js | function | generateTypewriterTokens | 1277 | function generateTypewriterTokens() { |
| vscode-extension/media/karl.js | function | updateMiniGptTelemetryUi | 1310 | function updateMiniGptTelemetryUi(step, loss) { |
| vscode-extension/media/karl.js | function | streamTypewriterTokens | 1327 | function streamTypewriterTokens(step, maxIters, text) { |
| vscode-extension/media/karl.js | function | _initEducationalSandbox | 1348 | function _initEducationalSandbox() { |
| vscode-extension/media/karl.js | function | _renderCompletionDiagnostic | 1417 | function _renderCompletionDiagnostic(msg) { |
| vscode-extension/media/karl_render.js | function | escapeHtml | 7 | function escapeHtml(value) { |
| vscode-extension/media/karl_render.js | function | _triggerScroll | 17 | function _triggerScroll(el) { |
| vscode-extension/media/karl_render.js | function | _getOrCreateCursor | 28 | function _getOrCreateCursor() { |
| vscode-extension/media/karl_render.js | function | attachStreamingCursor | 39 | function attachStreamingCursor(contentEl) { |
| vscode-extension/media/karl_render.js | function | removeStreamingCursor | 45 | function removeStreamingCursor() { |
| vscode-extension/media/karl_render.js | function | _appendChatText | 54 | function _appendChatText(el, text) { |
| vscode-extension/media/karl_render.js | function | appendThoughtToken | 78 | function appendThoughtToken(token) { |
| vscode-extension/media/karl_render.js | function | resetThoughtsPanel | 99 | function resetThoughtsPanel() { |
| vscode-extension/media/karl_render.js | function | finalizeThoughts | 113 | function finalizeThoughts() { |
| vscode-extension/media/karl_render.js | function | buildModelCard | 120 | function buildModelCard(title, metaHtml, buttonHtml) { |
| vscode-extension/media/karl_render.js | function | renderModels | 128 | function renderModels(models) { |
| vscode-extension/media/karl_render.js | function | renderDownloadRegistry | 142 | function renderDownloadRegistry(models) { |
| vscode-extension/media/karl_render.js | function | renderThemeCatalog | 162 | function renderThemeCatalog() { |
| vscode-extension/media/karl_render.js | function | formatLineDelta | 191 | function formatLineDelta(edit) { |
| vscode-extension/media/karl_render.js | function | riskLabel | 196 | function riskLabel(edit) { |
| vscode-extension/media/karl_render.js | function | renderPendingEdits | 203 | function renderPendingEdits() { |
| vscode-extension/media/karl_render.js | function | renderLabDiff | 235 | function renderLabDiff(textA, textB) { |
| vscode-extension/media/karl_render.js | function | renderPromptPairs | 260 | function renderPromptPairs(pairs) { |
| vscode-extension/media/karl_render.js | function | renderKbSnapshot | 268 | function renderKbSnapshot(snapshot) { |
| vscode-extension/media/karl_render.js | function | renderKbQueue | 288 | function renderKbQueue() { |
| vscode-extension/media/karl_render.js | function | renderKbSearch | 305 | function renderKbSearch(payload) { |
| vscode-extension/media/karl_render.js | function | renderCodexTopics | 326 | function renderCodexTopics(topics) { |
| vscode-extension/media/karl_render.js | function | renderBranches | 335 | function renderBranches() { |
| vscode-extension/media/karl_render.js | function | renderTaskQueue | 354 | function renderTaskQueue() { |
| vscode-extension/media/karl_render.js | function | renderContextMeta | 372 | function renderContextMeta(meta) { |
| vscode-extension/media/karl_render.js | function | addTimeline | 384 | function addTimeline(title, detail) { |
| vscode-extension/media/karl_render.js | function | log | 409 | function log(message) { |
| vscode-extension/media/karl_render.js | function | renderDiagnosticsList | 417 | function renderDiagnosticsList(diagDetails) { |
| vscode-extension/media/karl_render.js | function | updateCockpitState | 444 | function updateCockpitState(state) { |
| vscode-extension/media/karl_render.js | function | renderRuntimeOffline | 466 | function renderRuntimeOffline() { |
| vscode-extension/media/karl_render.js | function | renderRuntimeStatus | 475 | function renderRuntimeStatus(status, latency = 0) { |
| vscode-extension/media/karl_render.js | function | appendMessageBubble | 545 | function appendMessageBubble(role, text) { |
| vscode-extension/media/karl_render.js | function | appendChatToken | 561 | function appendChatToken(token) { |
| vscode-extension/media/karl_render.js | function | routeThinkMarkup | 572 | function routeThinkMarkup(token, chatTarget) { |
| vscode-extension/media/karl_render.js | function | renderQuickActions | 606 | function renderQuickActions() { |
| vscode-extension/media/karl_render.js | function | renderRecentTasks | 622 | function renderRecentTasks() { |
| vscode-extension/media/karl_render.js | function | renderRecentKbQueries | 639 | function renderRecentKbQueries() { |
| vscode-extension/media/karl_socket.js | function | BridgeRelay | 7 | const BridgeRelay = (() => { |
| vscode-extension/media/karl_socket.js | function | _directSend | 8 | function _directSend(payload) { |
| vscode-extension/media/karl_socket.js | function | _startTokenRefreshTimer | 37 | function _startTokenRefreshTimer() { |
| vscode-extension/media/karl_socket.js | function | _clearTokenRefreshTimer | 42 | function _clearTokenRefreshTimer() { |
| vscode-extension/media/karl_socket.js | function | _checkTokenRefresh | 49 | function _checkTokenRefresh() { |
| vscode-extension/media/karl_socket.js | function | setConnectionState | 60 | function setConnectionState(state, label) { |
| vscode-extension/media/karl_socket.js | function | teardownSocket | 70 | function teardownSocket(isError = false) { |
| vscode-extension/media/karl_socket.js | function | handleDisconnect | 93 | function handleDisconnect(isError = false) { |
| vscode-extension/media/karl_socket.js | function | connect | 115 | function connect() { |
| vscode-extension/media/karl_socket.js | function | disconnect | 128 | function disconnect() { |
| vscode-extension/media/karl_socket.js | function | _directConnect | 148 | function _directConnect() { |
| vscode-extension/media/karl_socket.js | function | rpc | 218 | function rpc(id, method, params) { |
| vscode-extension/media/karl_socket.js | function | isConnected | 228 | function isConnected() { |
| vscode-extension/media/karl_socket.js | function | handleSocketMessage | 234 | function handleSocketMessage(data) { |
| vscode-extension/media/karl_socket.js | function | handleRpcResult | 316 | function handleRpcResult(id, result) { |
| vscode-extension/media/karl_socket.js | function | requestRuntimeStatus | 392 | function requestRuntimeStatus() { |
| vscode-extension/media/karl_socket.js | function | updateBridgeMeta | 397 | function updateBridgeMeta(status) { |
| vscode-extension/media/karl_socket.js | function | loadModels | 421 | function loadModels() { |
| vscode-extension/media/karl_socket.js | function | loadPromptPairs | 429 | function loadPromptPairs() { |
| vscode-extension/media/karl_socket.js | function | loadKbSources | 433 | function loadKbSources() { |
| vscode-extension/media/karl_socket.js | function | loadCodexTopics | 441 | function loadCodexTopics() { |
| vscode-extension/media/karl_state.js | function | $ | 37 | const $ = (id) => document.getElementById(id); |
| vscode-extension/media/karl_state.js | function | hydrate | 39 | function hydrate() { |
| vscode-extension/media/karl_state.js | function | persist | 76 | function persist() { |
| vscode-extension/media/karl_state.js | function | initializeAppearance | 102 | function initializeAppearance() { |
| vscode-extension/media/karl_state.js | function | themeById | 112 | function themeById(id) { |
| vscode-extension/media/karl_state.js | function | layoutById | 117 | function layoutById(id) { |
| vscode-extension/media/karl_state.js | function | applyAppearance | 122 | function applyAppearance() { |
| vscode-extension/media/karl_state.js | function | switchWorkspace | 164 | function switchWorkspace(wsId) { |
| vscode-extension/src/commands.js | function | currentWorkspacePath | 149 | function currentWorkspacePath(fallbackFile) { |
| vscode-extension/src/commands.js | function | groupedDiagnostics | 161 | function groupedDiagnostics(currentFileOnly = false) { |
| vscode-extension/src/commands.js | function | revealKarlPanel | 189 | async function revealKarlPanel(sidebarProvider) { |
| vscode-extension/src/commands.js | function | runWorkflow | 201 | async function runWorkflow(sidebarProvider, workflow, customUri = null) { |
| vscode-extension/src/commands.js | function | runWorkflowById | 270 | async function runWorkflowById(sidebarProvider, workflowId, _payload = {}) { |
| vscode-extension/src/commands.js | function | buildWorkflowContext | 284 | async function buildWorkflowContext(workflow, sidebarProvider, customUri = null) { |
| vscode-extension/src/commands.js | function | sendActiveFileToKb | 423 | async function sendActiveFileToKb(sidebarProvider, uri) { |
| vscode-extension/src/commands.js | function | sendWorkspaceFolderToKb | 444 | async function sendWorkspaceFolderToKb(sidebarProvider, uri) { |
| vscode-extension/src/fileOps.js | function | packageContext | 17 | function packageContext(raw, label, summaryOnly = false) { |
| vscode-extension/src/fileOps.js | function | checkFileExists | 44 | async function checkFileExists(filepath) { |
| vscode-extension/src/fileOps.js | function | writeTempFileAndDiff | 61 | async function writeTempFileAndDiff(filename, targetPath, content, title) { |
| vscode-extension/src/gitOps.js | function | execGit | 10 | function execGit(args, cwd) { |
| vscode-extension/src/gitOps.js | function | getGitBranch | 27 | async function getGitBranch(workspacePath) { |
| vscode-extension/src/sidebarProvider.js | function | getDiagnosticsStats | 26 | function getDiagnosticsStats() { |
| vscode-extension/src/sidebarProvider.js | function | sendActiveStateToWebview | 44 | function sendActiveStateToWebview(sidebarProvider) { |
| vscode-extension/src/sidebarProvider.js | class | KarlSidebarProvider | 88 | class KarlSidebarProvider { |
| vscode-extension/src/sidebarProvider.js | function | clearCache | 187 | const clearCache = () => { |

## 7. Imports/Dependencies

| File | Kind | Name | Line | Signature |
|---|---|---|---:|---|
| Karl-main/app/engine/agentic_thread.py | import | os | 1 |  |
| Karl-main/app/engine/agentic_thread.py | import | time | 2 |  |
| Karl-main/app/engine/agentic_thread.py | import | importlib | 3 |  |
| Karl-main/app/engine/agentic_thread.py | import | datetime | 4 |  |
| Karl-main/app/engine/agentic_thread.py | import | PyQt6.QtCore | 5 |  |
| Karl-main/app/engine/agentic_thread.py | import | app.engine.model_loader | 6 |  |
| Karl-main/app/engine/agentic_thread.py | import | app.utils.trace_logger | 7 |  |
| Karl-main/app/engine/agentic_thread.py | import | core.interaction_loop | 8 |  |
| Karl-main/app/engine/agentic_thread.py | import | core.agentic_loop | 9 |  |
| Karl-main/app/engine/llm_thread.py | import | os | 1 |  |
| Karl-main/app/engine/llm_thread.py | import | time | 2 |  |
| Karl-main/app/engine/llm_thread.py | import | importlib | 3 |  |
| Karl-main/app/engine/llm_thread.py | import | datetime | 4 |  |
| Karl-main/app/engine/llm_thread.py | import | PyQt6.QtCore | 5 |  |
| Karl-main/app/engine/llm_thread.py | import | app.engine.model_loader | 6 |  |
| Karl-main/app/engine/llm_thread.py | import | app.utils.trace_logger | 7 |  |
| Karl-main/app/engine/llm_thread.py | import | core.interaction_loop | 8 |  |
| Karl-main/app/engine/model_loader.py | import | os | 1 |  |
| Karl-main/app/engine/model_loader.py | import | llama_cpp | 2 |  |
| Karl-main/app/engine/upgrade_manager.py | import | os | 1 |  |
| Karl-main/app/engine/upgrade_manager.py | import | json | 2 |  |
| Karl-main/app/engine/upgrade_manager.py | import | subprocess | 3 |  |
| Karl-main/app/engine/upgrade_manager.py | import | requests | 4 |  |
| Karl-main/app/engine/upgrade_manager.py | import | tqdm | 5 |  |
| Karl-main/app/engine/upgrade_manager.py | import | core.hardware_scout | 6 |  |
| Karl-main/app/engine/upgrade_manager.py | import | app.engine.model_loader | 7 |  |
| Karl-main/app/ui/main_window.py | import | PyQt6.QtWidgets | 1 |  |
| Karl-main/app/ui/main_window.py | import | PyQt6.QtCore | 6 |  |
| Karl-main/app/ui/main_window.py | import | app.engine.llm_thread | 7 |  |
| Karl-main/app/ui/main_window.py | import | app.engine.agentic_thread | 8 |  |
| Karl-main/app/ui/main_window.py | import | app.utils.memory_manager | 9 |  |
| Karl-main/app/ui/main_window.py | import | app.utils.rag_pipeline | 10 |  |
| Karl-main/app/ui/main_window.py | import | app.utils.training_curator | 11 |  |
| Karl-main/app/ui/main_window.py | import | core.workflows | 12 |  |
| Karl-main/app/ui/main_window.py | import | core.prompt_templates | 13 |  |
| Karl-main/app/ui/main_window.py | import | app.engine.upgrade_manager | 23 |  |
| Karl-main/app/ui/main_window.py | import | app.engine.upgrade_manager | 44 |  |
| Karl-main/app/ui/main_window.py | import | time as _time | 521 |  |
| Karl-main/app/ui/main_window.py | import | time as _time | 618 |  |
| Karl-main/app/utils/memory_manager.py | import | os | 1 |  |
| Karl-main/app/utils/memory_manager.py | import | json | 2 |  |
| Karl-main/app/utils/memory_manager.py | import | datetime | 3 |  |
| Karl-main/app/utils/rag_pipeline.py | import | json | 12 |  |
| Karl-main/app/utils/rag_pipeline.py | import | os | 13 |  |
| Karl-main/app/utils/rag_pipeline.py | import | time | 14 |  |
| Karl-main/app/utils/rag_pipeline.py | import | faiss | 16 |  |
| Karl-main/app/utils/rag_pipeline.py | import | numpy as np | 17 |  |
| Karl-main/app/utils/rag_pipeline.py | import | sentence_transformers | 18 |  |
| Karl-main/app/utils/rag_pipeline.py | import | fitz   # PyMuPDF | 19 |  |
| Karl-main/app/utils/rag_pipeline.py | import | docx | 20 |  |
| Karl-main/app/utils/trace_logger.py | import | os | 1 |  |
| Karl-main/app/utils/trace_logger.py | import | json | 2 |  |
| Karl-main/app/utils/trace_logger.py | import | datetime | 3 |  |
| Karl-main/app/utils/training_curator.py | import | os | 10 |  |
| Karl-main/app/utils/training_curator.py | import | json | 11 |  |
| Karl-main/app/utils/training_curator.py | import | datetime | 12 |  |
| Karl-main/core/hardware_scout.py | import | os | 1 |  |
| Karl-main/core/hardware_scout.py | import | shutil | 2 |  |
| Karl-main/core/hardware_scout.py | import | psutil | 9 |  |
| Karl-main/core/hardware_scout.py | import | GPUtil | 15 |  |
| Karl-main/core/prompt_templates.py | import | typing | 9 |  |
| Karl-main/core/workflows.py | import | typing | 10 |  |
| Karl-main/download_test_model.py | import | os | 1 |  |
| Karl-main/download_test_model.py | import | requests | 2 |  |
| Karl-main/download_test_model.py | import | tqdm | 3 |  |
| Karl-main/engine_test.py | import | os | 1 |  |
| Karl-main/engine_test.py | import | time | 2 |  |
| Karl-main/engine_test.py | import | llama_cpp | 3 |  |
| Karl-main/engine_test.py | import | app.utils.trace_logger | 4 |  |
| Karl-main/engine_test.py | import | core.cognitive_parser | 5 |  |
| Karl-main/eval/benchmark_rag.py | import | os | 15 |  |
| Karl-main/eval/benchmark_rag.py | import | sys | 16 |  |
| Karl-main/eval/benchmark_rag.py | import | time | 17 |  |
| Karl-main/eval/benchmark_rag.py | import | textwrap | 18 |  |
| Karl-main/eval/benchmark_rag.py | import | dataclasses | 19 |  |
| Karl-main/eval/benchmark_rag.py | import | app.utils.rag_pipeline | 23 |  |
| Karl-main/eval/benchmark_rag.py | import | sentence_transformers | 82 |  |
| Karl-main/eval/benchmark_rag.py | import | numpy as np | 83 |  |
| Karl-main/eval/benchmark_rag.py | import | argparse | 149 |  |
| Karl-main/eval/graders.py | import | json | 13 |  |
| Karl-main/eval/graders.py | import | re | 14 |  |
| Karl-main/eval/graders.py | import | typing | 15 |  |
| Karl-main/eval/harness.py | import | json | 24 |  |
| Karl-main/eval/harness.py | import | os | 25 |  |
| Karl-main/eval/harness.py | import | sys | 26 |  |
| Karl-main/eval/harness.py | import | time | 27 |  |
| Karl-main/eval/harness.py | import | dataclasses | 28 |  |
| Karl-main/eval/harness.py | import | typing | 29 |  |
| Karl-main/eval/harness.py | import | eval.graders | 34 |  |
| Karl-main/eval/harness.py | import | core.prompt_templates | 35 |  |
| Karl-main/eval/harness.py | import | core.workflows | 36 |  |
| Karl-main/eval/harness.py | import | app.engine.model_loader | 164 |  |
| Karl-main/eval/harness.py | import | core.interaction_loop | 165 |  |
| Karl-main/eval/harness.py | import | datetime | 223 |  |
| Karl-main/eval/run_eval.py | import | argparse | 22 |  |
| Karl-main/eval/run_eval.py | import | json | 23 |  |
| Karl-main/eval/run_eval.py | import | os | 24 |  |
| Karl-main/eval/run_eval.py | import | sys | 25 |  |
| Karl-main/eval/run_eval.py | import | core.workflows | 29 |  |
| Karl-main/eval/run_eval.py | import | core.prompt_templates | 30 |  |
| Karl-main/eval/run_eval.py | import | eval.harness | 31 |  |
| Karl-main/eval/run_eval.py | import | eval.graders | 32 |  |
| Karl-main/eval/run_eval.py | import | eval.graders | 112 |  |
| Karl-main/main.py | import | sys | 1 |  |
| Karl-main/main.py | import | PyQt6.QtWidgets | 2 |  |
| Karl-main/main.py | import | app.ui.main_window | 3 |  |
| Karl-main/smoke_test.py | import | sys | 1 |  |
| Karl-main/smoke_test.py | import | core.prompt_templates | 4 |  |
| Karl-main/smoke_test.py | import | core.workflows | 5 |  |
| Karl-main/smoke_test.py | import | eval.graders | 6 |  |
| Karl-main/smoke_test.py | import | json | 28 |  |
| Karl-main/training/validate_dataset.py | import | json | 19 |  |
| Karl-main/training/validate_dataset.py | import | os | 20 |  |
| Karl-main/training/validate_dataset.py | import | sys | 21 |  |
| Karl-main/training/validate_dataset.py | import | argparse | 22 |  |
| Karl-main/training/validate_dataset.py | import | collections | 23 |  |
| app/engine/__init__.py | import | app.engine.offline_guard | 3 |  |
| app/engine/agent_memory.py | import | __future__ | 8 |  |
| app/engine/agent_memory.py | import | ast | 10 |  |
| app/engine/agent_memory.py | import | json | 11 |  |
| app/engine/agent_memory.py | import | os | 12 |  |
| app/engine/agent_memory.py | import | re | 13 |  |
| app/engine/agent_memory.py | import | pathlib | 14 |  |
| app/engine/agent_memory.py | import | typing | 15 |  |
| app/engine/agentic_thread.py | import | logging | 1 |  |
| app/engine/agentic_thread.py | import | os | 2 |  |
| app/engine/agentic_thread.py | import | time | 3 |  |
| app/engine/agentic_thread.py | import | psutil | 4 |  |
| app/engine/agentic_thread.py | import | re | 5 |  |
| app/engine/agentic_thread.py | import | threading | 6 |  |
| app/engine/agentic_thread.py | import | datetime | 7 |  |
| app/engine/agentic_thread.py | import | PyQt6.QtCore | 8 |  |
| app/engine/agentic_thread.py | import | app.engine.hot_reload | 9 |  |
| app/engine/agentic_thread.py | import | app.engine.model_loader | 10 |  |
| app/engine/agentic_thread.py | import | app.engine.kv_cache | 11 |  |
| app/engine/agentic_thread.py | import | app.engine.event_broker | 12 |  |
| app/engine/agentic_thread.py | import | app.utils.trace_logger | 13 |  |
| app/engine/agentic_thread.py | import | core.interaction_loop | 14 |  |
| app/engine/agentic_thread.py | import | core.agentic_loop | 15 |  |
| app/engine/agentic_thread.py | import | core.hardware_scout | 37 |  |
| app/engine/agentic_thread.py | import | app.engine | 514 |  |
| app/engine/agentic_thread.py | import | core.hardware_scout | 602 |  |
| app/engine/config_store.py | import | __future__ | 20 |  |
| app/engine/config_store.py | import | json | 22 |  |
| app/engine/config_store.py | import | logging | 23 |  |
| app/engine/config_store.py | import | os | 24 |  |
| app/engine/config_store.py | import | tempfile | 25 |  |
| app/engine/config_store.py | import | threading | 26 |  |
| app/engine/config_store.py | import | typing | 27 |  |
| app/engine/config_store.py | import | time | 346 |  |
| app/engine/event_broker.py | import | threading | 1 |  |
| app/engine/event_broker.py | import | typing | 2 |  |
| app/engine/feature_flags.py | import | __future__ | 9 |  |
| app/engine/feature_flags.py | import | json | 11 |  |
| app/engine/feature_flags.py | import | logging | 12 |  |
| app/engine/feature_flags.py | import | os | 13 |  |
| app/engine/feature_flags.py | import | time | 14 |  |
| app/engine/hot_reload.py | import | __future__ | 1 |  |
| app/engine/hot_reload.py | import | importlib | 3 |  |
| app/engine/hot_reload.py | import | logging | 4 |  |
| app/engine/hot_reload.py | import | py_compile | 5 |  |
| app/engine/hot_reload.py | import | traceback | 6 |  |
| app/engine/hot_reload.py | import | types | 7 |  |
| app/engine/hot_reload.py | import | typing | 8 |  |
| app/engine/hot_reload.py | import | PyQt6.QtCore | 9 |  |
| app/engine/image_analysis_thread.py | import | __future__ | 1 |  |
| app/engine/image_analysis_thread.py | import | PyQt6.QtCore | 3 |  |
| app/engine/image_analysis_thread.py | import | app.vision.ocr_engine | 5 |  |
| app/engine/image_analysis_thread.py | import | app.vision.vision_analyzer | 6 |  |
| app/engine/inference_service.py | import | __future__ | 9 |  |
| app/engine/inference_service.py | import | logging | 11 |  |
| app/engine/inference_service.py | import | typing | 12 |  |
| app/engine/inference_service.py | import | PyQt6.QtCore | 14 |  |
| app/engine/inference_service.py | import | app.engine.agentic_thread | 16 |  |
| app/engine/inference_service.py | import | app.engine.llm_thread | 17 |  |
| app/engine/kv_cache.py | import | __future__ | 6 |  |
| app/engine/kv_cache.py | import | json | 8 |  |
| app/engine/kv_cache.py | import | logging | 9 |  |
| app/engine/kv_cache.py | import | os | 10 |  |
| app/engine/kv_cache.py | import | typing | 11 |  |
| app/engine/kv_cache.py | import | llama_cpp | 34 |  |
| app/engine/llm_thread.py | import | json | 1 |  |
| app/engine/llm_thread.py | import | logging | 2 |  |
| app/engine/llm_thread.py | import | os | 3 |  |
| app/engine/llm_thread.py | import | time | 4 |  |
| app/engine/llm_thread.py | import | psutil | 5 |  |
| app/engine/llm_thread.py | import | re | 6 |  |
| app/engine/llm_thread.py | import | threading | 7 |  |
| app/engine/llm_thread.py | import | datetime | 8 |  |
| app/engine/llm_thread.py | import | PyQt6.QtCore | 9 |  |
| app/engine/llm_thread.py | import | app.engine.hot_reload | 10 |  |
| app/engine/llm_thread.py | import | app.engine.model_loader | 11 |  |
| app/engine/llm_thread.py | import | app.engine.kv_cache | 12 |  |
| app/engine/llm_thread.py | import | app.engine.event_broker | 13 |  |
| app/engine/llm_thread.py | import | app.engine.task_supervisor | 14 |  |
| app/engine/llm_thread.py | import | app.utils.trace_logger | 15 |  |
| app/engine/llm_thread.py | import | core.interaction_loop | 16 |  |
| app/engine/llm_thread.py | import | core.hardware_scout | 42 |  |
| app/engine/llm_thread.py | import | core.hardware_scout | 72 |  |
| app/engine/llm_thread.py | import | app.engine | 312 |  |
| app/engine/llm_thread.py | import | app.engine.tool_executor | 605 |  |
| app/engine/llm_thread.py | import | core.hardware_scout | 700 |  |
| app/engine/mcp_client.py | import | logging | 9 |  |
| app/engine/mcp_client.py | import | os | 10 |  |
| app/engine/mcp_client.py | import | json | 11 |  |
| app/engine/mcp_client.py | import | asyncio | 12 |  |
| app/engine/mcp_client.py | import | threading | 13 |  |
| app/engine/mcp_client.py | import | concurrent.futures | 14 |  |
| app/engine/mcp_client.py | import | typing | 15 |  |
| app/engine/mcp_client.py | import | mcp | 16 |  |
| app/engine/mcp_client.py | import | mcp.client.stdio | 17 |  |
| app/engine/mini_train_thread.py | import | os | 9 |  |
| app/engine/mini_train_thread.py | import | json | 10 |  |
| app/engine/mini_train_thread.py | import | torch | 11 |  |
| app/engine/mini_train_thread.py | import | torch.nn as nn | 12 |  |
| app/engine/mini_train_thread.py | import | PyQt6.QtCore | 13 |  |
| app/engine/mini_train_thread.py | import | app.engine.mini_transformer | 14 |  |
| app/engine/mini_train_thread.py | import | traceback | 185 |  |
| app/engine/mini_transformer.py | import | torch | 17 |  |
| app/engine/mini_transformer.py | import | torch.nn as nn | 18 |  |
| app/engine/mini_transformer.py | import | torch.nn | 19 |  |
| app/engine/mini_transformer.py | import | math | 20 |  |
| app/engine/model_loader.py | import | json | 1 |  |
| app/engine/model_loader.py | import | logging | 2 |  |
| app/engine/model_loader.py | import | os | 3 |  |
| app/engine/model_loader.py | import | threading | 4 |  |
| app/engine/model_loader.py | import | multiprocessing | 5 |  |
| app/engine/model_loader.py | import | time | 6 |  |
| app/engine/model_loader.py | import | llama_cpp | 7 |  |
| app/engine/model_loader.py | import | app.engine | 9 |  |
| app/engine/model_loader.py | import | core.hardware_scout | 10 |  |
| app/engine/model_loader.py | import | llama_cpp | 184 |  |
| app/engine/model_loader.py | import | torch | 242 |  |
| app/engine/model_loader.py | import | torch | 278 |  |
| app/engine/model_loader.py | import | llama_cpp as _llama_lib | 388 |  |
| app/engine/model_loader.py | import | PyQt6.QtCore | 629 |  |
| app/engine/model_loader.py | import | PyQt6.QtWidgets | 630 |  |
| app/engine/model_loader.py | import | llama_cpp.llama_cpp as _ll | 713 |  |
| app/engine/model_loader.py | import | subprocess | 804 |  |
| app/engine/model_loader.py | import | sys | 805 |  |
| app/engine/model_loader.py | import | gc | 851 |  |
| app/engine/model_loader.py | import | torch | 854 |  |
| app/engine/model_loader.py | import | llama_cpp.llama_cpp as _llama_lib | 958 |  |
| app/engine/model_loader.py | import | gc | 1024 |  |
| app/engine/model_loader.py | import | torch | 1027 |  |
| app/engine/model_loader.py | import | llama_cpp | 1069 |  |
| app/engine/model_loader.py | import | gc | 1181 |  |
| app/engine/model_loader.py | import | torch | 1186 |  |
| app/engine/model_loader.py | import | llama_cpp.llama_cpp as _llama_lib | 1196 |  |
| app/engine/model_loader.py | import | app.engine | 1348 |  |
| app/engine/model_loader.py | import | app.engine | 1371 |  |
| app/engine/model_loader.py | import | app.engine | 1381 |  |
| app/engine/offline_guard.py | import | __future__ | 3 |  |
| app/engine/offline_guard.py | import | logging | 5 |  |
| app/engine/offline_guard.py | import | os | 6 |  |
| app/engine/offline_guard.py | import | threading | 7 |  |
| app/engine/offline_guard.py | import | urllib.parse | 8 |  |
| app/engine/offline_guard.py | import | app.engine | 45 |  |
| app/engine/offline_guard.py | import | requests | 89 |  |
| app/engine/offline_guard.py | import | urllib.request | 102 |  |
| app/engine/offline_guard.py | import | httpx | 116 |  |
| app/engine/quantizer_thread.py | import | os | 14 |  |
| app/engine/quantizer_thread.py | import | re | 15 |  |
| app/engine/quantizer_thread.py | import | shutil | 16 |  |
| app/engine/quantizer_thread.py | import | subprocess | 17 |  |
| app/engine/quantizer_thread.py | import | PyQt6.QtCore | 19 |  |
| app/engine/quantizer_thread.py | import | logging | 21 |  |
| app/engine/reflection_loop.py | import | re | 1 |  |
| app/engine/reflection_loop.py | import | app.engine.model_loader | 2 |  |
| app/engine/remote_rpc_client.py | import | __future__ | 1 |  |
| app/engine/remote_rpc_client.py | import | asyncio | 3 |  |
| app/engine/remote_rpc_client.py | import | json | 4 |  |
| app/engine/remote_rpc_client.py | import | logging | 5 |  |
| app/engine/remote_rpc_client.py | import | ssl | 6 |  |
| app/engine/remote_rpc_client.py | import | time | 7 |  |
| app/engine/remote_rpc_client.py | import | ipaddress | 8 |  |
| app/engine/remote_rpc_client.py | import | queue | 9 |  |
| app/engine/remote_rpc_client.py | import | threading | 10 |  |
| app/engine/remote_rpc_client.py | import | typing | 11 |  |
| app/engine/remote_rpc_client.py | import | urllib.parse | 12 |  |
| app/engine/remote_rpc_client.py | import | websockets.asyncio.client | 147 |  |
| app/engine/self_play_thread.py | import | __future__ | 8 |  |
| app/engine/self_play_thread.py | import | logging | 10 |  |
| app/engine/self_play_thread.py | import | os | 11 |  |
| app/engine/self_play_thread.py | import | subprocess | 12 |  |
| app/engine/self_play_thread.py | import | tempfile | 13 |  |
| app/engine/self_play_thread.py | import | time | 14 |  |
| app/engine/self_play_thread.py | import | typing | 15 |  |
| app/engine/self_play_thread.py | import | PyQt6.QtCore | 17 |  |
| app/engine/self_play_thread.py | import | app.engine.model_loader | 86 |  |
| app/engine/self_play_thread.py | import | app.utils.training_curator | 87 |  |
| app/engine/swarm_agents.py | import | os | 8 |  |
| app/engine/swarm_agents.py | import | re | 9 |  |
| app/engine/swarm_agents.py | import | json | 10 |  |
| app/engine/swarm_agents.py | import | logging | 11 |  |
| app/engine/swarm_agents.py | import | subprocess | 12 |  |
| app/engine/swarm_agents.py | import | glob | 13 |  |
| app/engine/swarm_agents.py | import | concurrent.futures | 14 |  |
| app/engine/swarm_agents.py | import | typing | 15 |  |
| app/engine/swarm_agents.py | import | app.engine.model_loader | 16 |  |
| app/engine/swarm_agents.py | import | app.engine.agent_memory | 17 |  |
| app/engine/swarm_agents.py | import | core.interaction_loop | 18 |  |
| app/engine/swarm_agents.py | import | pathlib | 69 |  |
| app/engine/swarm_agents.py | import | pathlib | 83 |  |
| app/engine/swarm_agents.py | import | pathlib, re as _re | 99 |  |
| app/engine/swarm_agents.py | import | pathlib | 140 |  |
| app/engine/swarm_agents.py | import | core.interaction_loop | 353 |  |
| app/engine/swarm_orchestrator.py | import | os | 8 |  |
| app/engine/swarm_orchestrator.py | import | time | 9 |  |
| app/engine/swarm_orchestrator.py | import | ast | 10 |  |
| app/engine/swarm_orchestrator.py | import | json | 11 |  |
| app/engine/swarm_orchestrator.py | import | threading | 12 |  |
| app/engine/swarm_orchestrator.py | import | logging | 13 |  |
| app/engine/swarm_orchestrator.py | import | pathlib | 14 |  |
| app/engine/swarm_orchestrator.py | import | typing | 15 |  |
| app/engine/swarm_orchestrator.py | import | PyQt6.QtCore | 16 |  |
| app/engine/swarm_orchestrator.py | import | concurrent.futures | 17 |  |
| app/engine/swarm_orchestrator.py | import | app.engine.swarm_agents | 18 |  |
| app/engine/swarm_orchestrator.py | import | app.utils.tracing | 19 |  |
| app/engine/swarm_orchestrator.py | import | threading | 93 |  |
| app/engine/swarm_orchestrator.py | import | PyQt6.QtWidgets | 94 |  |
| app/engine/task_supervisor.py | import | __future__ | 28 |  |
| app/engine/task_supervisor.py | import | logging | 30 |  |
| app/engine/task_supervisor.py | import | threading | 31 |  |
| app/engine/task_supervisor.py | import | uuid | 32 |  |
| app/engine/task_supervisor.py | import | dataclasses | 33 |  |
| app/engine/task_supervisor.py | import | enum | 34 |  |
| app/engine/task_supervisor.py | import | typing | 35 |  |
| app/engine/task_supervisor.py | import | app.utils.trace_logger | 249 |  |
| app/engine/tool_executor.py | import | __future__ | 5 |  |
| app/engine/tool_executor.py | import | logging | 6 |  |
| app/engine/tool_executor.py | import | re | 7 |  |
| app/engine/tool_executor.py | import | typing | 8 |  |
| app/engine/tool_executor.py | import | app.engine.mcp_client | 60 |  |
| app/engine/websocket_server.py | import | logging | 8 |  |
| app/engine/websocket_server.py | import | os | 9 |  |
| app/engine/websocket_server.py | import | json | 10 |  |
| app/engine/websocket_server.py | import | asyncio | 11 |  |
| app/engine/websocket_server.py | import | threading | 12 |  |
| app/engine/websocket_server.py | import | re | 13 |  |
| app/engine/websocket_server.py | import | time | 14 |  |
| app/engine/websocket_server.py | import | uuid | 15 |  |
| app/engine/websocket_server.py | import | ssl | 16 |  |
| app/engine/websocket_server.py | import | subprocess | 17 |  |
| app/engine/websocket_server.py | import | pathlib | 18 |  |
| app/engine/websocket_server.py | import | datetime | 19 |  |
| app/engine/websocket_server.py | import | urllib.parse | 20 |  |
| app/engine/websocket_server.py | import | websockets | 21 |  |
| app/engine/websocket_server.py | import | websockets.datastructures | 22 |  |
| app/engine/websocket_server.py | import | websockets.http11 | 23 |  |
| app/engine/websocket_server.py | import | typing | 24 |  |
| app/engine/websocket_server.py | import | PyQt6.QtCore | 25 |  |
| app/engine/websocket_server.py | import | app.engine | 27 |  |
| app/engine/websocket_server.py | import | app.engine.swarm_orchestrator | 28 |  |
| app/engine/websocket_server.py | import | app.engine.inference_service | 29 |  |
| app/engine/websocket_server.py | import | app.engine.model_loader | 30 |  |
| app/engine/websocket_server.py | import | app.utils.rag_pipeline | 31 |  |
| app/engine/websocket_server.py | import | app.ui.workspaces.docs_data | 32 |  |
| app/engine/websocket_server.py | import | app.ui.workspaces.prompt_lab | 33 |  |
| app/engine/websocket_server.py | import | app.utils.keychain_manager | 34 |  |
| app/engine/websocket_server.py | import | app.utils.correlation_logger | 35 |  |
| app/engine/websocket_server.py | import | psutil | 731 |  |
| app/engine/websocket_server.py | import | psutil | 903 |  |
| app/engine/websocket_server.py | import | app.utils.keychain_manager | 1020 |  |
| app/engine/websocket_server.py | import | app.ui.workspaces.workbench.profiles | 1547 |  |
| app/engine/websocket_server.py | import | re as _re | 1621 |  |
| app/engine/websocket_server.py | import | app.ui.workspaces.workbench.profiles | 1628 |  |
| app/engine/websocket_server.py | import | app.ui.workspaces.workbench.profiles | 1705 |  |
| app/engine/websocket_server.py | import | subprocess | 1777 |  |
| app/engine/websocket_server.py | import | sys | 1778 |  |
| app/engine/websocket_server.py | import | app.utils.custom_embeddings | 1837 |  |
| app/engine/websocket_server.py | import | app.engine.mini_train_thread | 1926 |  |
| app/repository/session_repository.py | import | os | 1 |  |
| app/repository/session_repository.py | import | json | 2 |  |
| app/state.py | import | PyQt6.QtCore | 1 |  |
| app/state.py | import | app.utils.rag_pipeline | 2 |  |
| app/state.py | import | app.utils.memory_manager | 3 |  |
| app/state.py | import | app.utils.trace_logger | 4 |  |
| app/state.py | import | app.utils.training_curator | 5 |  |
| app/state.py | import | app.vision.image_store | 6 |  |
| app/state.py | import | app.utils.keychain_manager | 7 |  |
| app/state.py | import | app.engine | 8 |  |
| app/ui/main_window.py | import | __future__ | 6 |  |
| app/ui/main_window.py | import | logging | 8 |  |
| app/ui/main_window.py | import | PyQt6.QtWidgets | 10 |  |
| app/ui/main_window.py | import | PyQt6.QtCore | 14 |  |
| app/ui/main_window.py | import | PyQt6.QtGui | 15 |  |
| app/ui/main_window.py | import | app.state | 17 |  |
| app/ui/main_window.py | import | app.ui.sidebar | 18 |  |
| app/ui/main_window.py | import | app.ui.widgets.status_bar | 19 |  |
| app/ui/main_window.py | import | app.ui.workspaces.workbench | 20 |  |
| app/ui/main_window.py | import | app.ui.workspaces.prompt_lab | 21 |  |
| app/ui/main_window.py | import | app.ui.workspaces.knowledge_base | 22 |  |
| app/ui/main_window.py | import | app.ui.workspaces.vision_workbench | 23 |  |
| app/ui/main_window.py | import | app.ui.workspaces.training_studio | 24 |  |
| app/ui/main_window.py | import | app.ui.workspaces.eval_suite | 25 |  |
| app/ui/main_window.py | import | app.ui.workspaces.system_config | 26 |  |
| app/ui/main_window.py | import | app.ui.workspaces.docs | 27 |  |
| app/ui/main_window.py | import | app.ui.workspaces.swarm_studio | 28 |  |
| app/ui/main_window.py | import | app.ui.workspaces.flywheel_studio | 29 |  |
| app/ui/main_window.py | import | app.engine.model_loader | 42 |  |
| app/ui/main_window.py | import | app.ui.widgets.command_palette | 128 |  |
| app/ui/main_window.py | import | PyQt6.QtWidgets | 136 |  |
| app/ui/main_window.py | import | app.utils.session_tree | 273 |  |
| app/ui/main_window.py | import | app.engine.model_loader | 338 |  |
| app/ui/main_window.py | import | app.engine.model_loader | 376 |  |
| app/ui/main_window.py | import | app.engine | 390 |  |
| app/ui/main_window.py | import | PyQt6.QtWidgets | 410 |  |
| app/ui/main_window.py | import | app.ui.themes | 411 |  |
| app/ui/main_window.py | import | app.engine.websocket_server | 468 |  |
| app/ui/main_window.py | import | app.engine.feature_flags | 478 |  |
| app/ui/main_window.py | import | app.engine.websocket_server | 488 |  |
| app/ui/main_window.py | import | app.engine.websocket_server | 513 |  |
| app/ui/main_window.py | import | app.utils.keychain_manager | 514 |  |
| app/ui/main_window.py | import | app.utils.ipc_helper | 528 |  |
| app/ui/sidebar.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/sidebar.py | import | PyQt6.QtCore | 2 |  |
| app/ui/sidebar.py | import | PyQt6.QtGui | 3 |  |
| app/ui/widgets/__init__.py | import | .status_bar | 1 |  |
| app/ui/widgets/__init__.py | import | .tracing_panel | 2 |  |
| app/ui/widgets/__init__.py | import | .glow_panel | 3 |  |
| app/ui/widgets/__init__.py | import | .section_shell | 4 |  |
| app/ui/widgets/command_palette.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/command_palette.py | import | PyQt6.QtCore | 2 |  |
| app/ui/widgets/command_palette.py | import | PyQt6.QtGui | 3 |  |
| app/ui/widgets/glow_panel.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/glow_panel.py | import | PyQt6.QtGui | 2 |  |
| app/ui/widgets/glow_panel.py | import | app.ui.themes | 3 |  |
| app/ui/widgets/model_combo.py | import | __future__ | 3 |  |
| app/ui/widgets/model_combo.py | import | logging | 5 |  |
| app/ui/widgets/model_combo.py | import | os | 6 |  |
| app/ui/widgets/model_combo.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/widgets/model_combo.py | import | PyQt6.QtCore | 8 |  |
| app/ui/widgets/model_combo.py | import | app.engine | 10 |  |
| app/ui/widgets/section_shell.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/shortcuts_overlay.py | import | __future__ | 3 |  |
| app/ui/widgets/shortcuts_overlay.py | import | PyQt6.QtWidgets | 5 |  |
| app/ui/widgets/shortcuts_overlay.py | import | PyQt6.QtCore | 8 |  |
| app/ui/widgets/shortcuts_overlay.py | import | app.ui.themes | 62 |  |
| app/ui/widgets/status_bar.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/status_bar.py | import | PyQt6.QtCore | 2 |  |
| app/ui/widgets/status_bar.py | import | psutil | 3 |  |
| app/ui/widgets/status_bar.py | import | os | 4 |  |
| app/ui/widgets/status_bar.py | import | app.engine.websocket_server | 101 |  |
| app/ui/widgets/status_bar.py | import | core.hardware_scout | 113 |  |
| app/ui/widgets/symbolic_icon.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/symbolic_icon.py | import | PyQt6.QtCore | 2 |  |
| app/ui/widgets/symbolic_icon.py | import | PyQt6.QtGui | 3 |  |
| app/ui/widgets/symbolic_icon.py | import | app.ui.themes | 4 |  |
| app/ui/widgets/symbolic_icon.py | import | PyQt6.QtGui | 96 |  |
| app/ui/widgets/symbolic_icon.py | import | PyQt6.QtGui | 127 |  |
| app/ui/widgets/symbolic_icon.py | import | math | 232 |  |
| app/ui/widgets/toast.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/toast.py | import | PyQt6.QtCore | 2 |  |
| app/ui/widgets/tracing_panel.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/widgets/tracing_panel.py | import | PyQt6.QtCore | 2 |  |
| app/ui/widgets/tracing_panel.py | import | PyQt6.QtGui | 3 |  |
| app/ui/widgets/tracing_panel.py | import | app.ui.themes | 4 |  |
| app/ui/workspaces/ai_lab.py | import | __future__ | 5 |  |
| app/ui/workspaces/ai_lab.py | import | os | 7 |  |
| app/ui/workspaces/ai_lab.py | import | json | 8 |  |
| app/ui/workspaces/ai_lab.py | import | re | 9 |  |
| app/ui/workspaces/ai_lab.py | import | numpy as np | 10 |  |
| app/ui/workspaces/ai_lab.py | import | PyQt6.QtWidgets | 12 |  |
| app/ui/workspaces/ai_lab.py | import | PyQt6.QtCore | 19 |  |
| app/ui/workspaces/ai_lab.py | import | PyQt6.QtGui | 20 |  |
| app/ui/workspaces/ai_lab.py | import | app.state | 22 |  |
| app/ui/workspaces/ai_lab.py | import | app.ui.workspaces.knowledge_base | 23 |  |
| app/ui/workspaces/ai_lab.py | import | app.utils.custom_embeddings | 24 |  |
| app/ui/workspaces/ai_lab.py | import | app.ui.themes | 25 |  |
| app/ui/workspaces/docs.py | import | logging | 1 |  |
| app/ui/workspaces/docs.py | import | os | 2 |  |
| app/ui/workspaces/docs.py | import | re | 3 |  |
| app/ui/workspaces/docs.py | import | PyQt6.QtWidgets | 4 |  |
| app/ui/workspaces/docs.py | import | PyQt6.QtCore | 8 |  |
| app/ui/workspaces/docs.py | import | app.ui.themes | 10 |  |
| app/ui/workspaces/docs.py | import | app.ui.workspaces.docs_data | 11 |  |
| app/ui/workspaces/eval_suite.py | import | __future__ | 5 |  |
| app/ui/workspaces/eval_suite.py | import | logging | 7 |  |
| app/ui/workspaces/eval_suite.py | import | json | 9 |  |
| app/ui/workspaces/eval_suite.py | import | os | 10 |  |
| app/ui/workspaces/eval_suite.py | import | html | 11 |  |
| app/ui/workspaces/eval_suite.py | import | datetime | 12 |  |
| app/ui/workspaces/eval_suite.py | import | PyQt6.QtWidgets | 14 |  |
| app/ui/workspaces/eval_suite.py | import | PyQt6.QtCore | 21 |  |
| app/ui/workspaces/eval_suite.py | import | PyQt6.QtGui | 22 |  |
| app/ui/workspaces/eval_suite.py | import | app.ui.themes | 24 |  |
| app/ui/workspaces/eval_suite.py | import | eval.harness | 59 |  |
| app/ui/workspaces/eval_suite.py | import | app.utils.training_curator | 70 |  |
| app/ui/workspaces/eval_suite.py | import | core.workflows | 193 |  |
| app/ui/workspaces/eval_suite.py | import | app.engine.model_loader | 482 |  |
| app/ui/workspaces/eval_suite.py | import | time | 532 |  |
| app/ui/workspaces/eval_suite.py | import | app.engine.model_loader | 748 |  |
| app/ui/workspaces/flywheel_studio.py | import | __future__ | 7 |  |
| app/ui/workspaces/flywheel_studio.py | import | logging | 9 |  |
| app/ui/workspaces/flywheel_studio.py | import | os | 10 |  |
| app/ui/workspaces/flywheel_studio.py | import | json | 11 |  |
| app/ui/workspaces/flywheel_studio.py | import | glob | 12 |  |
| app/ui/workspaces/flywheel_studio.py | import | re | 13 |  |
| app/ui/workspaces/flywheel_studio.py | import | typing | 14 |  |
| app/ui/workspaces/flywheel_studio.py | import | PyQt6.QtWidgets | 16 |  |
| app/ui/workspaces/flywheel_studio.py | import | PyQt6.QtCore | 23 |  |
| app/ui/workspaces/flywheel_studio.py | import | PyQt6.QtGui | 24 |  |
| app/ui/workspaces/flywheel_studio.py | import | app.ui.themes | 26 |  |
| app/ui/workspaces/flywheel_studio.py | import | app.ui.widgets.glow_panel | 27 |  |
| app/ui/workspaces/flywheel_studio.py | import | app.utils.keychain_manager | 28 |  |
| app/ui/workspaces/flywheel_studio.py | import | PyQt6.QtCore | 453 |  |
| app/ui/workspaces/flywheel_studio.py | import | app.utils.training_curator | 815 |  |
| app/ui/workspaces/flywheel_studio.py | import | app.utils.training_curator | 838 |  |
| app/ui/workspaces/flywheel_studio.py | import | app.utils.trace_logger | 1008 |  |
| app/ui/workspaces/knowledge_base.py | import | __future__ | 8 |  |
| app/ui/workspaces/knowledge_base.py | import | html | 10 |  |
| app/ui/workspaces/knowledge_base.py | import | os | 11 |  |
| app/ui/workspaces/knowledge_base.py | import | math | 12 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtWidgets | 14 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtCore | 22 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtGui | 23 |  |
| app/ui/workspaces/knowledge_base.py | import | app.utils.custom_embeddings | 24 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtWidgets | 98 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtWidgets | 775 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtWidgets | 945 |  |
| app/ui/workspaces/knowledge_base.py | import | PyQt6.QtGui | 1032 |  |
| app/ui/workspaces/knowledge_base.py | import | logging | 1038 |  |
| app/ui/workspaces/knowledge_base.py | import | json | 1055 |  |
| app/ui/workspaces/knowledge_base.py | import | json | 1069 |  |
| app/ui/workspaces/prompt_lab.py | import | __future__ | 8 |  |
| app/ui/workspaces/prompt_lab.py | import | logging | 10 |  |
| app/ui/workspaces/prompt_lab.py | import | json | 12 |  |
| app/ui/workspaces/prompt_lab.py | import | os | 13 |  |
| app/ui/workspaces/prompt_lab.py | import | re | 14 |  |
| app/ui/workspaces/prompt_lab.py | import | html | 15 |  |
| app/ui/workspaces/prompt_lab.py | import | difflib | 16 |  |
| app/ui/workspaces/prompt_lab.py | import | PyQt6.QtWidgets | 18 |  |
| app/ui/workspaces/prompt_lab.py | import | PyQt6.QtCore | 24 |  |
| app/ui/workspaces/prompt_lab.py | import | PyQt6.QtGui | 25 |  |
| app/ui/workspaces/prompt_lab.py | import | app.ui.themes | 27 |  |
| app/ui/workspaces/prompt_lab.py | import | app.engine.model_loader | 127 |  |
| app/ui/workspaces/prompt_lab.py | import | core.interaction_loop | 128 |  |
| app/ui/workspaces/prompt_lab.py | import | importlib | 129 |  |
| app/ui/workspaces/prompt_lab.py | import | time | 130 |  |
| app/ui/workspaces/prompt_lab.py | import | core.cognitive_parser | 212 |  |
| app/ui/workspaces/prompt_lab.py | import | json | 298 |  |
| app/ui/workspaces/prompt_lab.py | import | os | 299 |  |
| app/ui/workspaces/prompt_lab.py | import | os | 325 |  |
| app/ui/workspaces/prompt_lab.py | import | app.engine.model_loader | 365 |  |
| app/ui/workspaces/prompt_lab.py | import | app.engine.agentic_thread | 452 |  |
| app/ui/workspaces/prompt_lab.py | import | PyQt6.QtGui | 485 |  |
| app/ui/workspaces/prompt_lab.py | import | time | 635 |  |
| app/ui/workspaces/prompt_lab.py | import | os | 679 |  |
| app/ui/workspaces/prompt_lab.py | import | time | 680 |  |
| app/ui/workspaces/prompt_lab.py | import | app.engine.model_loader | 681 |  |
| app/ui/workspaces/prompt_lab.py | import | app.engine | 682 |  |
| app/ui/workspaces/prompt_lab.py | import | core.interaction_loop | 683 |  |
| app/ui/workspaces/prompt_lab.py | import | importlib | 684 |  |
| app/ui/workspaces/prompt_lab.py | import | app.engine.model_loader | 1281 |  |
| app/ui/workspaces/prompt_lab.py | import | string | 1344 |  |
| app/ui/workspaces/swarm_studio.py | import | __future__ | 1 |  |
| app/ui/workspaces/swarm_studio.py | import | os | 3 |  |
| app/ui/workspaces/swarm_studio.py | import | time | 4 |  |
| app/ui/workspaces/swarm_studio.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/swarm_studio.py | import | PyQt6.QtGui | 7 |  |
| app/ui/workspaces/swarm_studio.py | import | PyQt6.QtWidgets | 8 |  |
| app/ui/workspaces/swarm_studio.py | import | app.engine.swarm_orchestrator | 38 |  |
| app/ui/workspaces/swarm_studio.py | import | html as _html | 697 |  |
| app/ui/workspaces/swarm_workspace.py | import | __future__ | 1 |  |
| app/ui/workspaces/swarm_workspace.py | import | os | 3 |  |
| app/ui/workspaces/swarm_workspace.py | import | time | 4 |  |
| app/ui/workspaces/swarm_workspace.py | import | math | 5 |  |
| app/ui/workspaces/swarm_workspace.py | import | json | 6 |  |
| app/ui/workspaces/swarm_workspace.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/swarm_workspace.py | import | PyQt6.QtCore | 12 |  |
| app/ui/workspaces/swarm_workspace.py | import | PyQt6.QtGui | 13 |  |
| app/ui/workspaces/swarm_workspace.py | import | app.engine.swarm_orchestrator | 15 |  |
| app/ui/workspaces/system_config.py | import | __future__ | 5 |  |
| app/ui/workspaces/system_config.py | import | logging | 7 |  |
| app/ui/workspaces/system_config.py | import | json | 9 |  |
| app/ui/workspaces/system_config.py | import | os | 10 |  |
| app/ui/workspaces/system_config.py | import | html | 11 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtWidgets | 13 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtCore | 21 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtGui | 22 |  |
| app/ui/workspaces/system_config.py | import | app.ui.themes | 24 |  |
| app/ui/workspaces/system_config.py | import | app.ui.widgets.tracing_panel | 25 |  |
| app/ui/workspaces/system_config.py | import | app.ui.widgets.symbolic_icon | 26 |  |
| app/ui/workspaces/system_config.py | import | app.vision.vision_model_loader | 27 |  |
| app/ui/workspaces/system_config.py | import | app.engine.quantizer_thread | 32 |  |
| app/ui/workspaces/system_config.py | import | time | 57 |  |
| app/ui/workspaces/system_config.py | import | time | 151 |  |
| app/ui/workspaces/system_config.py | import | requests | 152 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 248 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 253 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 684 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 744 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 876 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 883 |  |
| app/ui/workspaces/system_config.py | import | app.ui | 1111 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtWidgets | 1112 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtWidgets | 1161 |  |
| app/ui/workspaces/system_config.py | import | psutil | 1467 |  |
| app/ui/workspaces/system_config.py | import | shutil | 1480 |  |
| app/ui/workspaces/system_config.py | import | core.hardware_scout | 1491 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 1537 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 1543 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 1569 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 1573 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 1578 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 1598 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 1599 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 1695 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 1705 |  |
| app/ui/workspaces/system_config.py | import | core.hardware_scout | 1737 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 1796 |  |
| app/ui/workspaces/system_config.py | import | app.engine.model_loader | 1855 |  |
| app/ui/workspaces/system_config.py | import | core.hardware_scout | 1856 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtWidgets | 1873 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 2189 |  |
| app/ui/workspaces/system_config.py | import | PyQt6.QtCore | 2348 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 2507 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 2589 |  |
| app/ui/workspaces/system_config.py | import | app.engine.mcp_client | 2600 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 2614 |  |
| app/ui/workspaces/system_config.py | import | app.engine | 2622 |  |
| app/ui/workspaces/system_config.py | import | app.engine.mcp_client | 2628 |  |
| app/ui/workspaces/system_config/__init__.py | import | .workspace | 1 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | PyQt6.QtCore | 5 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | PyQt6.QtGui | 6 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | app.engine | 11 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | app.ui.themes | 12 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | app.ui.widgets.symbolic_icon | 13 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | app.ui.widgets.tracing_panel | 14 |  |
| app/ui/workspaces/system_config/appearance_panel.py | import | .common | 15 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | os | 4 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | app.engine | 11 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | app.ui.themes | 12 |  |
| app/ui/workspaces/system_config/appearance_runtime.py | import | PyQt6.QtCore | 33 |  |
| app/ui/workspaces/system_config/common.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | PyQt6.QtCore | 5 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | PyQt6.QtWidgets | 6 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | .common | 11 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | app.ui | 162 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | PyQt6.QtWidgets | 163 |  |
| app/ui/workspaces/system_config/defaults_panel.py | import | PyQt6.QtWidgets | 218 |  |
| app/ui/workspaces/system_config/download_threads.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/download_threads.py | import | os | 3 |  |
| app/ui/workspaces/system_config/download_threads.py | import | PyQt6.QtCore | 5 |  |
| app/ui/workspaces/system_config/download_threads.py | import | PyQt6.QtWidgets | 6 |  |
| app/ui/workspaces/system_config/download_threads.py | import | time | 30 |  |
| app/ui/workspaces/system_config/download_threads.py | import | app.engine.task_supervisor | 100 |  |
| app/ui/workspaces/system_config/download_threads.py | import | time | 106 |  |
| app/ui/workspaces/system_config/download_threads.py | import | requests | 107 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | PyQt6.QtWidgets | 5 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | app.engine | 10 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | .common | 11 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | app.engine.mcp_client | 91 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | app.engine | 115 |  |
| app/ui/workspaces/system_config/mcp_panel.py | import | app.engine.mcp_client | 122 |  |
| app/ui/workspaces/system_config/model_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/model_panel.py | import | html | 3 |  |
| app/ui/workspaces/system_config/model_panel.py | import | logging | 4 |  |
| app/ui/workspaces/system_config/model_panel.py | import | os | 5 |  |
| app/ui/workspaces/system_config/model_panel.py | import | PyQt6.QtCore | 7 |  |
| app/ui/workspaces/system_config/model_panel.py | import | PyQt6.QtWidgets | 8 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine | 16 |  |
| app/ui/workspaces/system_config/model_panel.py | import | .common | 17 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine.model_loader | 282 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine | 294 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine | 337 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine.model_loader | 341 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine | 346 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine.model_loader | 367 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine | 368 |  |
| app/ui/workspaces/system_config/model_panel.py | import | app.engine.model_loader | 505 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | os | 4 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | core.hardware_scout | 13 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | app.engine | 72 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | app.engine.model_loader | 131 |  |
| app/ui/workspaces/system_config/model_preflight.py | import | core.hardware_scout | 132 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | os | 1 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | json | 2 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | PyQt6.QtWidgets | 4 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | app.ui.workspaces.system_config.common | 8 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | app.engine | 9 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | app.utils.trace_logger | 184 |  |
| app/ui/workspaces/system_config/observability_tab.py | import | PyQt6.QtWidgets | 192 |  |
| app/ui/workspaces/system_config/quantization_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/quantization_panel.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/quantization_panel.py | import | os | 4 |  |
| app/ui/workspaces/system_config/quantization_panel.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/system_config/quantization_panel.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/system_config/quantization_panel.py | import | app.engine.quantizer_thread | 12 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | logging | 3 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | os | 4 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | app.engine | 11 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | app.ui.themes | 12 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | .download_threads | 13 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | app.engine | 143 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | app.engine.model_loader | 279 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | PyQt6.QtWidgets | 281 |  |
| app/ui/workspaces/system_config/registry_panel.py | import | app.engine | 294 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | __future__ | 1 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | html | 3 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | logging | 4 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | app.ui.themes | 12 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | app.vision.vision_model_loader | 13 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | .common | 18 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | psutil | 371 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | shutil | 384 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | core.hardware_scout | 396 |  |
| app/ui/workspaces/system_config/vision_hardware_panel.py | import | app.engine | 438 |  |
| app/ui/workspaces/system_config/workspace.py | import | __future__ | 5 |  |
| app/ui/workspaces/system_config/workspace.py | import | logging | 7 |  |
| app/ui/workspaces/system_config/workspace.py | import | os | 8 |  |
| app/ui/workspaces/system_config/workspace.py | import | PyQt6.QtCore | 10 |  |
| app/ui/workspaces/system_config/workspace.py | import | PyQt6.QtWidgets | 11 |  |
| app/ui/workspaces/system_config/workspace.py | import | app.engine.quantizer_thread | 13 |  |
| app/ui/workspaces/system_config/workspace.py | import | .appearance_panel | 15 |  |
| app/ui/workspaces/system_config/workspace.py | import | .appearance_runtime | 16 |  |
| app/ui/workspaces/system_config/workspace.py | import | .defaults_panel | 17 |  |
| app/ui/workspaces/system_config/workspace.py | import | .mcp_panel | 18 |  |
| app/ui/workspaces/system_config/workspace.py | import | .model_panel | 19 |  |
| app/ui/workspaces/system_config/workspace.py | import | .model_preflight | 20 |  |
| app/ui/workspaces/system_config/workspace.py | import | .quantization_panel | 21 |  |
| app/ui/workspaces/system_config/workspace.py | import | .registry_panel | 22 |  |
| app/ui/workspaces/system_config/workspace.py | import | .vision_hardware_panel | 23 |  |
| app/ui/workspaces/system_config/workspace.py | import | app.engine | 76 |  |
| app/ui/workspaces/system_config/workspace.py | import | app.engine.model_loader | 87 |  |
| app/ui/workspaces/system_config/workspace.py | import | .observability_tab | 129 |  |
| app/ui/workspaces/system_config/workspace.py | import | PyQt6.QtWidgets | 144 |  |
| app/ui/workspaces/training_studio.py | import | __future__ | 10 |  |
| app/ui/workspaces/training_studio.py | import | json | 12 |  |
| app/ui/workspaces/training_studio.py | import | os | 13 |  |
| app/ui/workspaces/training_studio.py | import | html | 14 |  |
| app/ui/workspaces/training_studio.py | import | re | 15 |  |
| app/ui/workspaces/training_studio.py | import | PyQt6.QtWidgets | 17 |  |
| app/ui/workspaces/training_studio.py | import | PyQt6.QtCore | 24 |  |
| app/ui/workspaces/training_studio.py | import | PyQt6.QtGui | 25 |  |
| app/ui/workspaces/training_studio.py | import | app.ui.widgets.glow_panel | 26 |  |
| app/ui/workspaces/training_studio.py | import | app.engine.mini_train_thread | 27 |  |
| app/ui/workspaces/training_studio.py | import | app.engine.mini_transformer | 28 |  |
| app/ui/workspaces/training_studio.py | import | torch | 29 |  |
| app/ui/workspaces/training_studio.py | import | traceback | 30 |  |
| app/ui/workspaces/training_studio.py | import | os | 62 |  |
| app/ui/workspaces/training_studio.py | import | gc | 63 |  |
| app/ui/workspaces/training_studio.py | import | torch | 64 |  |
| app/ui/workspaces/training_studio.py | import | datasets | 75 |  |
| app/ui/workspaces/training_studio.py | import | transformers | 76 |  |
| app/ui/workspaces/training_studio.py | import | peft | 77 |  |
| app/ui/workspaces/training_studio.py | import | trl | 78 |  |
| app/ui/workspaces/training_studio.py | import | shutil | 189 |  |
| app/ui/workspaces/training_studio.py | import | subprocess | 196 |  |
| app/ui/workspaces/training_studio.py | import | sys | 197 |  |
| app/ui/workspaces/training_studio.py | import | gc | 217 |  |
| app/ui/workspaces/training_studio.py | import | torch | 220 |  |
| app/ui/workspaces/training_studio.py | import | subprocess | 240 |  |
| app/ui/workspaces/training_studio.py | import | sys | 241 |  |
| app/ui/workspaces/training_studio.py | import | glob | 298 |  |
| app/ui/workspaces/training_studio.py | import | time | 314 |  |
| app/ui/workspaces/training_studio.py | import | time as _time | 358 |  |
| app/ui/workspaces/training_studio.py | import | subprocess | 761 |  |
| app/ui/workspaces/training_studio.py | import | app.engine.model_loader | 1257 |  |
| app/ui/workspaces/training_studio.py | import | core.hardware_scout | 1498 |  |
| app/ui/workspaces/training_studio.py | import | app.engine.model_loader | 1524 |  |
| app/ui/workspaces/training_studio.py | import | app.engine.model_loader | 1737 |  |
| app/ui/workspaces/training_studio.py | import | app.engine.model_loader | 2132 |  |
| app/ui/workspaces/training_studio/__init__.py | import | PyQt6.QtWidgets | 1 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.flywheel_tab | 3 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.dataset_tab | 4 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.export_tab | 5 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.train_tab | 6 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.auto_train_tab | 7 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.mini_gpt_tab | 8 |  |
| app/ui/workspaces/training_studio/__init__.py | import | app.ui.workspaces.training_studio.threads | 9 |  |
| app/ui/workspaces/training_studio/auto_train_tab.py | import | re | 1 |  |
| app/ui/workspaces/training_studio/auto_train_tab.py | import | PyQt6.QtWidgets | 3 |  |
| app/ui/workspaces/training_studio/auto_train_tab.py | import | app.ui.widgets.glow_panel | 9 |  |
| app/ui/workspaces/training_studio/auto_train_tab.py | import | app.ui.workspaces.training_studio.threads | 10 |  |
| app/ui/workspaces/training_studio/auto_train_tab.py | import | app.engine.model_loader | 11 |  |
| app/ui/workspaces/training_studio/dataset_tab.py | import | html | 1 |  |
| app/ui/workspaces/training_studio/dataset_tab.py | import | PyQt6.QtWidgets | 3 |  |
| app/ui/workspaces/training_studio/dataset_tab.py | import | PyQt6.QtCore | 8 |  |
| app/ui/workspaces/training_studio/dataset_tab.py | import | app.utils.dataset_merger | 59 |  |
| app/ui/workspaces/training_studio/dataset_tab.py | import | app.utils.training_curator | 235 |  |
| app/ui/workspaces/training_studio/dataset_tab.py | import | os | 239 |  |
| app/ui/workspaces/training_studio/export_tab.py | import | os | 1 |  |
| app/ui/workspaces/training_studio/export_tab.py | import | json | 2 |  |
| app/ui/workspaces/training_studio/export_tab.py | import | PyQt6.QtWidgets | 4 |  |
| app/ui/workspaces/training_studio/export_tab.py | import | app.ui.widgets.glow_panel | 8 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | os | 1 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | json | 2 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | PyQt6.QtWidgets | 4 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | PyQt6.QtCore | 8 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | PyQt6.QtGui | 9 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | app.ui.workspaces.training_studio.threads | 11 |  |
| app/ui/workspaces/training_studio/flywheel_tab.py | import | subprocess | 200 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | os | 1 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | json | 2 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | html | 3 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | traceback | 4 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | PyQt6.QtWidgets | 6 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | PyQt6.QtCore | 11 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | PyQt6.QtGui | 12 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | app.ui.workspaces.training_studio.threads | 14 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | app.engine.model_loader | 15 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | torch | 615 |  |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | import | app.engine.mini_transformer | 616 |  |
| app/ui/workspaces/training_studio/threads.py | import | os | 1 |  |
| app/ui/workspaces/training_studio/threads.py | import | json | 2 |  |
| app/ui/workspaces/training_studio/threads.py | import | sys | 3 |  |
| app/ui/workspaces/training_studio/threads.py | import | subprocess | 4 |  |
| app/ui/workspaces/training_studio/threads.py | import | PyQt6.QtCore | 6 |  |
| app/ui/workspaces/training_studio/threads.py | import | app.engine.task_supervisor | 25 |  |
| app/ui/workspaces/training_studio/threads.py | import | os | 32 |  |
| app/ui/workspaces/training_studio/threads.py | import | gc | 33 |  |
| app/ui/workspaces/training_studio/threads.py | import | torch | 34 |  |
| app/ui/workspaces/training_studio/threads.py | import | datasets | 45 |  |
| app/ui/workspaces/training_studio/threads.py | import | transformers | 46 |  |
| app/ui/workspaces/training_studio/threads.py | import | peft | 47 |  |
| app/ui/workspaces/training_studio/threads.py | import | trl | 48 |  |
| app/ui/workspaces/training_studio/threads.py | import | app.engine.task_supervisor | 134 |  |
| app/ui/workspaces/training_studio/threads.py | import | shutil | 162 |  |
| app/ui/workspaces/training_studio/threads.py | import | subprocess | 169 |  |
| app/ui/workspaces/training_studio/threads.py | import | sys | 170 |  |
| app/ui/workspaces/training_studio/threads.py | import | gc | 192 |  |
| app/ui/workspaces/training_studio/threads.py | import | torch | 195 |  |
| app/ui/workspaces/training_studio/threads.py | import | app.engine.task_supervisor | 223 |  |
| app/ui/workspaces/training_studio/threads.py | import | glob | 288 |  |
| app/ui/workspaces/training_studio/threads.py | import | time | 304 |  |
| app/ui/workspaces/training_studio/threads.py | import | time as _time | 348 |  |
| app/ui/workspaces/training_studio/threads.py | import | app.engine.task_supervisor | 419 |  |
| app/ui/workspaces/training_studio/threads.py | import | torch | 429 |  |
| app/ui/workspaces/training_studio/threads.py | import | app.engine.mini_transformer | 430 |  |
| app/ui/workspaces/training_studio/threads.py | import | app.engine.task_supervisor | 525 |  |
| app/ui/workspaces/training_studio/threads.py | import | traceback | 578 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | os | 1 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | json | 2 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | re | 3 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | PyQt6.QtWidgets | 5 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | app.ui.widgets.glow_panel | 12 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | app.ui.workspaces.training_studio.threads | 13 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | app.engine.model_loader | 14 |  |
| app/ui/workspaces/training_studio/train_tab.py | import | core.hardware_scout | 15 |  |
| app/ui/workspaces/vision_workbench.py | import | __future__ | 1 |  |
| app/ui/workspaces/vision_workbench.py | import | pathlib | 3 |  |
| app/ui/workspaces/vision_workbench.py | import | PyQt6.QtCore | 5 |  |
| app/ui/workspaces/vision_workbench.py | import | PyQt6.QtGui | 6 |  |
| app/ui/workspaces/vision_workbench.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/vision_workbench.py | import | app.engine.image_analysis_thread | 23 |  |
| app/ui/workspaces/vision_workbench.py | import | app.vision.vision_model_loader | 24 |  |
| app/ui/workspaces/workbench/__init__.py | import | app.ui.workspaces.workbench.chat_view | 11 |  |
| app/ui/workspaces/workbench/__init__.py | import | app.ui.workspaces.workbench.profiles | 12 |  |
| app/ui/workspaces/workbench/__init__.py | import | app.ui.workspaces.workbench.workspace | 13 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | logging | 5 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | re | 6 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | PyQt6.QtWidgets | 8 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | PyQt6.QtCore | 11 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | PyQt6.QtGui | 12 |  |
| app/ui/workspaces/workbench/branch_panel.py | import | app.ui.themes | 13 |  |
| app/ui/workspaces/workbench/chat_view.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/chat_view.py | import | pathlib | 5 |  |
| app/ui/workspaces/workbench/chat_view.py | import | PyQt6.QtWidgets | 7 |  |
| app/ui/workspaces/workbench/chat_view.py | import | PyQt6.QtCore | 8 |  |
| app/ui/workspaces/workbench/chat_view.py | import | PyQt6.QtGui | 9 |  |
| app/ui/workspaces/workbench/feedback_panel.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/hud_toolbar.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/hud_toolbar.py | import | PyQt6.QtWidgets | 5 |  |
| app/ui/workspaces/workbench/input_panel.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/input_panel.py | import | PyQt6.QtWidgets | 5 |  |
| app/ui/workspaces/workbench/input_panel.py | import | PyQt6.QtCore | 9 |  |
| app/ui/workspaces/workbench/input_panel.py | import | core.workflows | 11 |  |
| app/ui/workspaces/workbench/input_panel.py | import | app.ui.workspaces.workbench.profiles | 12 |  |
| app/ui/workspaces/workbench/input_panel.py | import | app.ui.widgets.symbolic_icon | 13 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | logging | 5 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | os | 6 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | PyQt6.QtCore | 8 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | app.engine.agentic_thread | 10 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | app.engine.llm_thread | 11 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | app.engine.model_loader | 12 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | app.engine.task_supervisor | 13 |  |
| app/ui/workspaces/workbench/orchestrator.py | import | app.utils.session_tree | 14 |  |
| app/ui/workspaces/workbench/params_drawer.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/params_drawer.py | import | PyQt6.QtWidgets | 5 |  |
| app/ui/workspaces/workbench/params_drawer.py | import | PyQt6.QtCore | 9 |  |
| app/ui/workspaces/workbench/params_drawer.py | import | app.ui.widgets.model_combo | 71 |  |
| app/ui/workspaces/workbench/profiles.py | import | json | 3 |  |
| app/ui/workspaces/workbench/profiles.py | import | os | 4 |  |
| app/ui/workspaces/workbench/session_panel.py | import | __future__ | 3 |  |
| app/ui/workspaces/workbench/session_panel.py | import | logging | 5 |  |
| app/ui/workspaces/workbench/session_panel.py | import | os | 6 |  |
| app/ui/workspaces/workbench/session_panel.py | import | typing | 7 |  |
| app/ui/workspaces/workbench/session_panel.py | import | PyQt6.QtWidgets | 9 |  |
| app/ui/workspaces/workbench/session_panel.py | import | PyQt6.QtCore | 13 |  |
| app/ui/workspaces/workbench/session_panel.py | import | app.utils.session_tree | 15 |  |
| app/ui/workspaces/workbench/session_panel.py | import | app.ui.themes | 16 |  |
| app/ui/workspaces/workbench/session_panel.py | import | shutil | 158 |  |
| app/ui/workspaces/workbench/workspace.py | import | __future__ | 14 |  |
| app/ui/workspaces/workbench/workspace.py | import | logging | 16 |  |
| app/ui/workspaces/workbench/workspace.py | import | PyQt6.QtWidgets | 18 |  |
| app/ui/workspaces/workbench/workspace.py | import | PyQt6.QtCore | 28 |  |
| app/ui/workspaces/workbench/workspace.py | import | PyQt6.QtGui | 29 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.inference_service | 32 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.image_analysis_thread | 33 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.model_loader | 34 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine | 35 |  |
| app/ui/workspaces/workbench/workspace.py | import | core.workflows | 36 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.utils.session_tree | 37 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.widgets.tracing_panel | 38 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.themes | 39 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.widgets.symbolic_icon | 40 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.widgets.toast | 41 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.workspaces.workbench.chat_view | 43 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.workspaces.workbench.profiles | 44 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.utils.correlation_logger | 45 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.themes | 138 |  |
| app/ui/workspaces/workbench/workspace.py | import | core.workflows | 1237 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.model_loader | 1247 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.themes | 1415 |  |
| app/ui/workspaces/workbench/workspace.py | import | PyQt6.QtWidgets | 1416 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.ui.themes | 1417 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine | 1443 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 1492 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine | 1493 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 1540 |  |
| app/ui/workspaces/workbench/workspace.py | import | PyQt6.QtWidgets | 1610 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 1611 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.model_loader | 1631 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine | 1637 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.model_loader | 1676 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 1702 |  |
| app/ui/workspaces/workbench/workspace.py | import | app.engine.model_loader | 1834 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 1947 |  |
| app/ui/workspaces/workbench/workspace.py | import | PyQt6.QtWidgets | 1961 |  |
| app/ui/workspaces/workbench/workspace.py | import | re | 2087 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 2288 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 2315 |  |
| app/ui/workspaces/workbench/workspace.py | import | shutil | 2328 |  |
| app/ui/workspaces/workbench/workspace.py | import | os | 2335 |  |
| app/utils/codebase_search.py | import | logging | 1 |  |
| app/utils/codebase_search.py | import | subprocess | 2 |  |
| app/utils/codebase_search.py | import | os | 3 |  |
| app/utils/codebase_search.py | import | typing | 4 |  |
| app/utils/conversion/__init__.py | import | __future__ | 1 |  |
| app/utils/conversion/__init__.py | import | .base | 3 |  |
| app/utils/conversion/__init__.py | import | typing | 8 |  |
| app/utils/conversion/afmoe.py | import | __future__ | 1 |  |
| app/utils/conversion/afmoe.py | import | typing | 3 |  |
| app/utils/conversion/afmoe.py | import | torch | 5 |  |
| app/utils/conversion/afmoe.py | import | torch | 8 |  |
| app/utils/conversion/afmoe.py | import | .base | 10 |  |
| app/utils/conversion/afmoe.py | import | .llama | 12 |  |
| app/utils/conversion/arctic.py | import | __future__ | 1 |  |
| app/utils/conversion/arctic.py | import | json | 3 |  |
| app/utils/conversion/arctic.py | import | sys | 4 |  |
| app/utils/conversion/arctic.py | import | typing | 6 |  |
| app/utils/conversion/arctic.py | import | torch | 8 |  |
| app/utils/conversion/arctic.py | import | torch | 11 |  |
| app/utils/conversion/arctic.py | import | .base | 13 |  |
| app/utils/conversion/arctic.py | import | .llama | 15 |  |
| app/utils/conversion/arctic.py | import | sentencepiece | 26 |  |
| app/utils/conversion/baichuan.py | import | __future__ | 1 |  |
| app/utils/conversion/baichuan.py | import | typing | 3 |  |
| app/utils/conversion/baichuan.py | import | torch | 6 |  |
| app/utils/conversion/baichuan.py | import | .base | 8 |  |
| app/utils/conversion/bailingmoe.py | import | __future__ | 1 |  |
| app/utils/conversion/bailingmoe.py | import | typing | 3 |  |
| app/utils/conversion/bailingmoe.py | import | torch | 5 |  |
| app/utils/conversion/bailingmoe.py | import | torch | 8 |  |
| app/utils/conversion/bailingmoe.py | import | .base | 10 |  |
| app/utils/conversion/base.py | import | __future__ | 4 |  |
| app/utils/conversion/base.py | import | ast | 6 |  |
| app/utils/conversion/base.py | import | logging | 7 |  |
| app/utils/conversion/base.py | import | contextlib | 8 |  |
| app/utils/conversion/base.py | import | json | 9 |  |
| app/utils/conversion/base.py | import | os | 10 |  |
| app/utils/conversion/base.py | import | re | 11 |  |
| app/utils/conversion/base.py | import | sys | 12 |  |
| app/utils/conversion/base.py | import | enum | 13 |  |
| app/utils/conversion/base.py | import | pathlib | 14 |  |
| app/utils/conversion/base.py | import | hashlib | 15 |  |
| app/utils/conversion/base.py | import | typing | 16 |  |
| app/utils/conversion/base.py | import | itertools | 17 |  |
| app/utils/conversion/base.py | import | transformers | 18 |  |
| app/utils/conversion/base.py | import | numpy as np | 20 |  |
| app/utils/conversion/base.py | import | torch | 21 |  |
| app/utils/conversion/base.py | import | torch | 24 |  |
| app/utils/conversion/base.py | import | gguf | 28 |  |
| app/utils/conversion/base.py | import | gguf.vocab | 29 |  |
| app/utils/conversion/base.py | import | mistral_common.tokens.tokenizers.base | 32 |  |
| app/utils/conversion/base.py | import | mistral_common.tokens.tokenizers.multimodal | 33 |  |
| app/utils/conversion/base.py | import | mistral_common.tokens.tokenizers.tekken | 34 |  |
| app/utils/conversion/base.py | import | mistral_common.tokens.tokenizers.sentencepiece | 35 |  |
| app/utils/conversion/base.py | import | transformers | 1333 |  |
| app/utils/conversion/base.py | import | transformers | 1696 |  |
| app/utils/conversion/base.py | import | .qwen | 1737 |  |
| app/utils/conversion/base.py | import | transformers | 1744 |  |
| app/utils/conversion/base.py | import | sentencepiece | 1805 |  |
| app/utils/conversion/base.py | import | transformers | 2041 |  |
| app/utils/conversion/base.py | import | transformers | 2056 |  |
| app/utils/conversion/base.py | import | transformers | 2076 |  |
| app/utils/conversion/base.py | import | .mistral | 2122 |  |
| app/utils/conversion/base.py | import | copy | 2314 |  |
| app/utils/conversion/bert.py | import | __future__ | 1 |  |
| app/utils/conversion/bert.py | import | json | 3 |  |
| app/utils/conversion/bert.py | import | os | 4 |  |
| app/utils/conversion/bert.py | import | pathlib | 6 |  |
| app/utils/conversion/bert.py | import | typing | 7 |  |
| app/utils/conversion/bert.py | import | torch | 9 |  |
| app/utils/conversion/bert.py | import | torch | 12 |  |
| app/utils/conversion/bert.py | import | .base | 14 |  |
| app/utils/conversion/bert.py | import | sentencepiece | 117 |  |
| app/utils/conversion/bert.py | import | sentencepiece | 118 |  |
| app/utils/conversion/bert.py | import | base64 | 131 |  |
| app/utils/conversion/bert.py | import | transformers | 132 |  |
| app/utils/conversion/bitnet.py | import | __future__ | 1 |  |
| app/utils/conversion/bitnet.py | import | typing | 3 |  |
| app/utils/conversion/bitnet.py | import | torch | 6 |  |
| app/utils/conversion/bitnet.py | import | .base | 8 |  |
| app/utils/conversion/bloom.py | import | __future__ | 1 |  |
| app/utils/conversion/bloom.py | import | re | 3 |  |
| app/utils/conversion/bloom.py | import | typing | 5 |  |
| app/utils/conversion/bloom.py | import | torch | 7 |  |
| app/utils/conversion/bloom.py | import | torch | 10 |  |
| app/utils/conversion/bloom.py | import | .base | 12 |  |
| app/utils/conversion/chameleon.py | import | __future__ | 1 |  |
| app/utils/conversion/chameleon.py | import | typing | 3 |  |
| app/utils/conversion/chameleon.py | import | torch | 6 |  |
| app/utils/conversion/chameleon.py | import | .base | 8 |  |
| app/utils/conversion/chameleon.py | import | .llama | 10 |  |
| app/utils/conversion/chatglm.py | import | __future__ | 1 |  |
| app/utils/conversion/chatglm.py | import | typing | 3 |  |
| app/utils/conversion/chatglm.py | import | torch | 6 |  |
| app/utils/conversion/chatglm.py | import | .base | 8 |  |
| app/utils/conversion/chatglm.py | import | transformers | 22 |  |
| app/utils/conversion/chatglm.py | import | transformers.models.gpt2.tokenization_gpt2 | 84 |  |
| app/utils/conversion/chatglm.py | import | transformers | 115 |  |
| app/utils/conversion/codeshell.py | import | __future__ | 1 |  |
| app/utils/conversion/codeshell.py | import | .base | 3 |  |
| app/utils/conversion/cogvlm.py | import | __future__ | 1 |  |
| app/utils/conversion/cogvlm.py | import | typing | 3 |  |
| app/utils/conversion/cogvlm.py | import | torch | 6 |  |
| app/utils/conversion/cogvlm.py | import | .base | 8 |  |
| app/utils/conversion/cogvlm.py | import | .llama | 10 |  |
| app/utils/conversion/command_r.py | import | __future__ | 1 |  |
| app/utils/conversion/command_r.py | import | typing | 3 |  |
| app/utils/conversion/command_r.py | import | torch | 5 |  |
| app/utils/conversion/command_r.py | import | torch | 8 |  |
| app/utils/conversion/command_r.py | import | .base | 10 |  |
| app/utils/conversion/dbrx.py | import | __future__ | 1 |  |
| app/utils/conversion/dbrx.py | import | typing | 3 |  |
| app/utils/conversion/dbrx.py | import | torch | 6 |  |
| app/utils/conversion/dbrx.py | import | .base | 8 |  |
| app/utils/conversion/deci.py | import | __future__ | 1 |  |
| app/utils/conversion/deci.py | import | math | 3 |  |
| app/utils/conversion/deci.py | import | typing | 5 |  |
| app/utils/conversion/deci.py | import | torch | 7 |  |
| app/utils/conversion/deci.py | import | torch | 10 |  |
| app/utils/conversion/deci.py | import | .base | 12 |  |
| app/utils/conversion/deepseek.py | import | __future__ | 1 |  |
| app/utils/conversion/deepseek.py | import | re | 3 |  |
| app/utils/conversion/deepseek.py | import | typing | 5 |  |
| app/utils/conversion/deepseek.py | import | torch | 7 |  |
| app/utils/conversion/deepseek.py | import | torch | 10 |  |
| app/utils/conversion/deepseek.py | import | .base | 12 |  |
| app/utils/conversion/deepseek.py | import | .qwen | 14 |  |
| app/utils/conversion/deepseek.py | import | transformers | 249 |  |
| app/utils/conversion/deepseek.py | import | transformers | 446 |  |
| app/utils/conversion/dots1.py | import | __future__ | 1 |  |
| app/utils/conversion/dots1.py | import | typing | 3 |  |
| app/utils/conversion/dots1.py | import | torch | 6 |  |
| app/utils/conversion/dots1.py | import | .base | 8 |  |
| app/utils/conversion/dots1.py | import | .qwen | 10 |  |
| app/utils/conversion/dotsocr.py | import | __future__ | 1 |  |
| app/utils/conversion/dotsocr.py | import | typing | 3 |  |
| app/utils/conversion/dotsocr.py | import | torch | 6 |  |
| app/utils/conversion/dotsocr.py | import | .base | 8 |  |
| app/utils/conversion/dream.py | import | __future__ | 1 |  |
| app/utils/conversion/dream.py | import | typing | 3 |  |
| app/utils/conversion/dream.py | import | torch | 6 |  |
| app/utils/conversion/dream.py | import | .base | 8 |  |
| app/utils/conversion/dream.py | import | transformers | 19 |  |
| app/utils/conversion/ernie.py | import | __future__ | 1 |  |
| app/utils/conversion/ernie.py | import | json | 3 |  |
| app/utils/conversion/ernie.py | import | math | 4 |  |
| app/utils/conversion/ernie.py | import | re | 5 |  |
| app/utils/conversion/ernie.py | import | typing | 7 |  |
| app/utils/conversion/ernie.py | import | torch | 9 |  |
| app/utils/conversion/ernie.py | import | torch | 12 |  |
| app/utils/conversion/ernie.py | import | .base | 14 |  |
| app/utils/conversion/exaone.py | import | __future__ | 1 |  |
| app/utils/conversion/exaone.py | import | math | 3 |  |
| app/utils/conversion/exaone.py | import | pathlib | 5 |  |
| app/utils/conversion/exaone.py | import | typing | 6 |  |
| app/utils/conversion/exaone.py | import | torch | 8 |  |
| app/utils/conversion/exaone.py | import | torch | 11 |  |
| app/utils/conversion/exaone.py | import | .base | 13 |  |
| app/utils/conversion/falcon.py | import | __future__ | 1 |  |
| app/utils/conversion/falcon.py | import | typing | 3 |  |
| app/utils/conversion/falcon.py | import | torch | 5 |  |
| app/utils/conversion/falcon.py | import | torch | 8 |  |
| app/utils/conversion/falcon.py | import | .base | 10 |  |
| app/utils/conversion/falcon_h1.py | import | __future__ | 1 |  |
| app/utils/conversion/falcon_h1.py | import | typing | 3 |  |
| app/utils/conversion/falcon_h1.py | import | torch | 6 |  |
| app/utils/conversion/falcon_h1.py | import | .base | 8 |  |
| app/utils/conversion/falcon_h1.py | import | .llama | 10 |  |
| app/utils/conversion/falcon_h1.py | import | .mamba | 11 |  |
| app/utils/conversion/gemma.py | import | __future__ | 1 |  |
| app/utils/conversion/gemma.py | import | json | 3 |  |
| app/utils/conversion/gemma.py | import | re | 4 |  |
| app/utils/conversion/gemma.py | import | typing | 6 |  |
| app/utils/conversion/gemma.py | import | torch | 8 |  |
| app/utils/conversion/gemma.py | import | torch | 11 |  |
| app/utils/conversion/gemma.py | import | .base | 13 |  |
| app/utils/conversion/gemma.py | import | safetensors.torch | 208 |  |
| app/utils/conversion/glm.py | import | __future__ | 1 |  |
| app/utils/conversion/glm.py | import | typing | 3 |  |
| app/utils/conversion/glm.py | import | torch | 5 |  |
| app/utils/conversion/glm.py | import | torch | 8 |  |
| app/utils/conversion/glm.py | import | .base | 10 |  |
| app/utils/conversion/glm.py | import | .deepseek | 12 |  |
| app/utils/conversion/glm.py | import | transformers | 29 |  |
| app/utils/conversion/glm.py | import | transformers | 247 |  |
| app/utils/conversion/gpt2.py | import | __future__ | 1 |  |
| app/utils/conversion/gpt2.py | import | typing | 3 |  |
| app/utils/conversion/gpt2.py | import | torch | 5 |  |
| app/utils/conversion/gpt2.py | import | torch | 8 |  |
| app/utils/conversion/gpt2.py | import | .base | 10 |  |
| app/utils/conversion/gpt_oss.py | import | __future__ | 1 |  |
| app/utils/conversion/gpt_oss.py | import | typing | 3 |  |
| app/utils/conversion/gpt_oss.py | import | torch | 5 |  |
| app/utils/conversion/gpt_oss.py | import | torch | 8 |  |
| app/utils/conversion/gpt_oss.py | import | .base | 10 |  |
| app/utils/conversion/gptneox.py | import | __future__ | 1 |  |
| app/utils/conversion/gptneox.py | import | re | 3 |  |
| app/utils/conversion/gptneox.py | import | typing | 5 |  |
| app/utils/conversion/gptneox.py | import | torch | 7 |  |
| app/utils/conversion/gptneox.py | import | torch | 10 |  |
| app/utils/conversion/gptneox.py | import | .base | 12 |  |
| app/utils/conversion/granite.py | import | __future__ | 1 |  |
| app/utils/conversion/granite.py | import | typing | 3 |  |
| app/utils/conversion/granite.py | import | torch | 5 |  |
| app/utils/conversion/granite.py | import | torch | 8 |  |
| app/utils/conversion/granite.py | import | .base | 10 |  |
| app/utils/conversion/granite.py | import | .llama | 12 |  |
| app/utils/conversion/granite.py | import | .mamba | 13 |  |
| app/utils/conversion/grok.py | import | __future__ | 1 |  |
| app/utils/conversion/grok.py | import | sys | 3 |  |
| app/utils/conversion/grok.py | import | typing | 5 |  |
| app/utils/conversion/grok.py | import | torch | 7 |  |
| app/utils/conversion/grok.py | import | torch | 10 |  |
| app/utils/conversion/grok.py | import | .base | 12 |  |
| app/utils/conversion/grovemoe.py | import | __future__ | 1 |  |
| app/utils/conversion/grovemoe.py | import | typing | 3 |  |
| app/utils/conversion/grovemoe.py | import | torch | 5 |  |
| app/utils/conversion/grovemoe.py | import | torch | 8 |  |
| app/utils/conversion/grovemoe.py | import | .base | 10 |  |
| app/utils/conversion/hunyuan.py | import | __future__ | 1 |  |
| app/utils/conversion/hunyuan.py | import | json | 3 |  |
| app/utils/conversion/hunyuan.py | import | pathlib | 5 |  |
| app/utils/conversion/hunyuan.py | import | typing | 6 |  |
| app/utils/conversion/hunyuan.py | import | torch | 8 |  |
| app/utils/conversion/hunyuan.py | import | torch | 11 |  |
| app/utils/conversion/hunyuan.py | import | .base | 13 |  |
| app/utils/conversion/hunyuan.py | import | .qwen | 15 |  |
| app/utils/conversion/hunyuan.py | import | transformers | 23 |  |
| app/utils/conversion/hunyuan.py | import | transformers | 201 |  |
| app/utils/conversion/internlm.py | import | __future__ | 1 |  |
| app/utils/conversion/internlm.py | import | json | 3 |  |
| app/utils/conversion/internlm.py | import | sys | 4 |  |
| app/utils/conversion/internlm.py | import | typing | 6 |  |
| app/utils/conversion/internlm.py | import | torch | 9 |  |
| app/utils/conversion/internlm.py | import | .base | 11 |  |
| app/utils/conversion/internlm.py | import | .llama | 13 |  |
| app/utils/conversion/internlm.py | import | sentencepiece | 25 |  |
| app/utils/conversion/internlm.py | import | sentencepiece | 26 |  |
| app/utils/conversion/internvl.py | import | __future__ | 1 |  |
| app/utils/conversion/internvl.py | import | typing | 3 |  |
| app/utils/conversion/internvl.py | import | torch | 6 |  |
| app/utils/conversion/internvl.py | import | .base | 8 |  |
| app/utils/conversion/jais.py | import | __future__ | 1 |  |
| app/utils/conversion/jais.py | import | math | 3 |  |
| app/utils/conversion/jais.py | import | typing | 5 |  |
| app/utils/conversion/jais.py | import | torch | 8 |  |
| app/utils/conversion/jais.py | import | .base | 10 |  |
| app/utils/conversion/jamba.py | import | __future__ | 1 |  |
| app/utils/conversion/jamba.py | import | typing | 3 |  |
| app/utils/conversion/jamba.py | import | torch | 5 |  |
| app/utils/conversion/jamba.py | import | torch | 8 |  |
| app/utils/conversion/jamba.py | import | .base | 10 |  |
| app/utils/conversion/januspro.py | import | __future__ | 1 |  |
| app/utils/conversion/januspro.py | import | typing | 3 |  |
| app/utils/conversion/januspro.py | import | torch | 6 |  |
| app/utils/conversion/januspro.py | import | .base | 8 |  |
| app/utils/conversion/januspro.py | import | .llama | 10 |  |
| app/utils/conversion/kimi_linear.py | import | __future__ | 1 |  |
| app/utils/conversion/kimi_linear.py | import | typing | 3 |  |
| app/utils/conversion/kimi_linear.py | import | torch | 5 |  |
| app/utils/conversion/kimi_linear.py | import | torch | 8 |  |
| app/utils/conversion/kimi_linear.py | import | .base | 10 |  |
| app/utils/conversion/kimi_linear.py | import | .qwen | 12 |  |
| app/utils/conversion/kimi_linear.py | import | transformers | 29 |  |
| app/utils/conversion/kimivl.py | import | __future__ | 1 |  |
| app/utils/conversion/kimivl.py | import | typing | 3 |  |
| app/utils/conversion/kimivl.py | import | torch | 5 |  |
| app/utils/conversion/kimivl.py | import | torch | 8 |  |
| app/utils/conversion/kimivl.py | import | .base | 10 |  |
| app/utils/conversion/lfm2.py | import | __future__ | 1 |  |
| app/utils/conversion/lfm2.py | import | typing | 3 |  |
| app/utils/conversion/lfm2.py | import | torch | 5 |  |
| app/utils/conversion/lfm2.py | import | torch | 8 |  |
| app/utils/conversion/lfm2.py | import | .base | 10 |  |
| app/utils/conversion/lfm2.py | import | .gemma | 12 |  |
| app/utils/conversion/lfm2.py | import | safetensors.torch | 80 |  |
| app/utils/conversion/lighton_ocr.py | import | __future__ | 1 |  |
| app/utils/conversion/lighton_ocr.py | import | typing | 3 |  |
| app/utils/conversion/lighton_ocr.py | import | torch | 6 |  |
| app/utils/conversion/lighton_ocr.py | import | .base | 8 |  |
| app/utils/conversion/lighton_ocr.py | import | .llava | 10 |  |
| app/utils/conversion/llada.py | import | __future__ | 1 |  |
| app/utils/conversion/llada.py | import | typing | 3 |  |
| app/utils/conversion/llada.py | import | torch | 5 |  |
| app/utils/conversion/llada.py | import | torch | 8 |  |
| app/utils/conversion/llada.py | import | .base | 10 |  |
| app/utils/conversion/llada.py | import | transformers | 22 |  |
| app/utils/conversion/llama.py | import | __future__ | 1 |  |
| app/utils/conversion/llama.py | import | json | 3 |  |
| app/utils/conversion/llama.py | import | math | 4 |  |
| app/utils/conversion/llama.py | import | typing | 6 |  |
| app/utils/conversion/llama.py | import | torch | 8 |  |
| app/utils/conversion/llama.py | import | torch | 11 |  |
| app/utils/conversion/llama.py | import | .base | 13 |  |
| app/utils/conversion/llama4.py | import | __future__ | 1 |  |
| app/utils/conversion/llama4.py | import | typing | 3 |  |
| app/utils/conversion/llama4.py | import | torch | 6 |  |
| app/utils/conversion/llama4.py | import | .base | 8 |  |
| app/utils/conversion/llava.py | import | __future__ | 1 |  |
| app/utils/conversion/llava.py | import | json | 3 |  |
| app/utils/conversion/llava.py | import | typing | 5 |  |
| app/utils/conversion/llava.py | import | torch | 8 |  |
| app/utils/conversion/llava.py | import | .base | 10 |  |
| app/utils/conversion/llava.py | import | .llama | 12 |  |
| app/utils/conversion/maincoder.py | import | __future__ | 1 |  |
| app/utils/conversion/maincoder.py | import | .base | 3 |  |
| app/utils/conversion/mamba.py | import | __future__ | 1 |  |
| app/utils/conversion/mamba.py | import | json | 3 |  |
| app/utils/conversion/mamba.py | import | pathlib | 5 |  |
| app/utils/conversion/mamba.py | import | typing | 6 |  |
| app/utils/conversion/mamba.py | import | torch | 8 |  |
| app/utils/conversion/mamba.py | import | torch | 11 |  |
| app/utils/conversion/mamba.py | import | .base | 13 |  |
| app/utils/conversion/mimo.py | import | __future__ | 1 |  |
| app/utils/conversion/mimo.py | import | re | 3 |  |
| app/utils/conversion/mimo.py | import | typing | 5 |  |
| app/utils/conversion/mimo.py | import | torch | 7 |  |
| app/utils/conversion/mimo.py | import | torch | 10 |  |
| app/utils/conversion/mimo.py | import | .base | 12 |  |
| app/utils/conversion/minicpm.py | import | __future__ | 1 |  |
| app/utils/conversion/minicpm.py | import | typing | 3 |  |
| app/utils/conversion/minicpm.py | import | torch | 5 |  |
| app/utils/conversion/minicpm.py | import | torch | 8 |  |
| app/utils/conversion/minicpm.py | import | .base | 10 |  |
| app/utils/conversion/minicpm.py | import | .llama | 12 |  |
| app/utils/conversion/minicpm.py | import | .qwen | 13 |  |
| app/utils/conversion/minimax.py | import | __future__ | 1 |  |
| app/utils/conversion/minimax.py | import | typing | 3 |  |
| app/utils/conversion/minimax.py | import | torch | 5 |  |
| app/utils/conversion/minimax.py | import | torch | 8 |  |
| app/utils/conversion/minimax.py | import | .base | 10 |  |
| app/utils/conversion/mistral.py | import | __future__ | 1 |  |
| app/utils/conversion/mistral.py | import | pathlib | 3 |  |
| app/utils/conversion/mistral.py | import | typing | 4 |  |
| app/utils/conversion/mistral.py | import | torch | 7 |  |
| app/utils/conversion/mistral.py | import | .base | 9 |  |
| app/utils/conversion/mistral.py | import | .deepseek | 11 |  |
| app/utils/conversion/mistral.py | import | .llama | 12 |  |
| app/utils/conversion/mistral.py | import | mistral_common.tokens.tokenizers.base | 15 |  |
| app/utils/conversion/mistral.py | import | mistral_common.tokens.tokenizers.tekken | 16 |  |
| app/utils/conversion/mistral.py | import | mistral_common.tokens.tokenizers.sentencepiece | 17 |  |
| app/utils/conversion/mistral3.py | import | __future__ | 1 |  |
| app/utils/conversion/mistral3.py | import | typing | 3 |  |
| app/utils/conversion/mistral3.py | import | torch | 6 |  |
| app/utils/conversion/mistral3.py | import | .base | 8 |  |
| app/utils/conversion/mistral3.py | import | .deepseek | 10 |  |
| app/utils/conversion/mistral3.py | import | .llama | 11 |  |
| app/utils/conversion/mpt.py | import | __future__ | 1 |  |
| app/utils/conversion/mpt.py | import | typing | 3 |  |
| app/utils/conversion/mpt.py | import | torch | 6 |  |
| app/utils/conversion/mpt.py | import | .base | 8 |  |
| app/utils/conversion/nemotron.py | import | __future__ | 1 |  |
| app/utils/conversion/nemotron.py | import | typing | 3 |  |
| app/utils/conversion/nemotron.py | import | torch | 5 |  |
| app/utils/conversion/nemotron.py | import | torch | 8 |  |
| app/utils/conversion/nemotron.py | import | .base | 10 |  |
| app/utils/conversion/nemotron.py | import | .granite | 12 |  |
| app/utils/conversion/nemotron.py | import | torch.nn.functional as F | 85 |  |
| app/utils/conversion/nemotron.py | import | transformers | 251 |  |
| app/utils/conversion/olmo.py | import | __future__ | 1 |  |
| app/utils/conversion/olmo.py | import | typing | 3 |  |
| app/utils/conversion/olmo.py | import | torch | 5 |  |
| app/utils/conversion/olmo.py | import | torch | 8 |  |
| app/utils/conversion/olmo.py | import | .base | 10 |  |
| app/utils/conversion/olmo.py | import | .llama | 12 |  |
| app/utils/conversion/openelm.py | import | __future__ | 1 |  |
| app/utils/conversion/openelm.py | import | typing | 3 |  |
| app/utils/conversion/openelm.py | import | torch | 6 |  |
| app/utils/conversion/openelm.py | import | .base | 8 |  |
| app/utils/conversion/orion.py | import | __future__ | 1 |  |
| app/utils/conversion/orion.py | import | .base | 3 |  |
| app/utils/conversion/pangu.py | import | __future__ | 1 |  |
| app/utils/conversion/pangu.py | import | json | 3 |  |
| app/utils/conversion/pangu.py | import | typing | 5 |  |
| app/utils/conversion/pangu.py | import | torch | 8 |  |
| app/utils/conversion/pangu.py | import | .base | 10 |  |
| app/utils/conversion/phi.py | import | __future__ | 1 |  |
| app/utils/conversion/phi.py | import | json | 3 |  |
| app/utils/conversion/phi.py | import | math | 4 |  |
| app/utils/conversion/phi.py | import | typing | 6 |  |
| app/utils/conversion/phi.py | import | torch | 8 |  |
| app/utils/conversion/phi.py | import | torch | 11 |  |
| app/utils/conversion/phi.py | import | .base | 13 |  |
| app/utils/conversion/phi.py | import | sentencepiece | 52 |  |
| app/utils/conversion/pixtral.py | import | __future__ | 1 |  |
| app/utils/conversion/pixtral.py | import | typing | 3 |  |
| app/utils/conversion/pixtral.py | import | .base | 5 |  |
| app/utils/conversion/pixtral.py | import | .llava | 7 |  |
| app/utils/conversion/plamo.py | import | __future__ | 1 |  |
| app/utils/conversion/plamo.py | import | json | 3 |  |
| app/utils/conversion/plamo.py | import | typing | 5 |  |
| app/utils/conversion/plamo.py | import | torch | 7 |  |
| app/utils/conversion/plamo.py | import | torch | 10 |  |
| app/utils/conversion/plamo.py | import | .base | 12 |  |
| app/utils/conversion/plm.py | import | __future__ | 1 |  |
| app/utils/conversion/plm.py | import | .base | 3 |  |
| app/utils/conversion/qwen.py | import | __future__ | 1 |  |
| app/utils/conversion/qwen.py | import | typing | 3 |  |
| app/utils/conversion/qwen.py | import | torch | 5 |  |
| app/utils/conversion/qwen.py | import | torch | 8 |  |
| app/utils/conversion/qwen.py | import | .base | 10 |  |
| app/utils/conversion/qwen.py | import | transformers.models.gpt2.tokenization_gpt2 | 19 |  |
| app/utils/conversion/qwen.py | import | transformers | 205 |  |
| app/utils/conversion/qwen3vl.py | import | __future__ | 1 |  |
| app/utils/conversion/qwen3vl.py | import | json | 3 |  |
| app/utils/conversion/qwen3vl.py | import | typing | 5 |  |
| app/utils/conversion/qwen3vl.py | import | torch | 8 |  |
| app/utils/conversion/qwen3vl.py | import | .base | 10 |  |
| app/utils/conversion/qwen3vl.py | import | .qwen | 12 |  |
| app/utils/conversion/qwen3vl.py | import | .qwenvl | 13 |  |
| app/utils/conversion/qwenvl.py | import | __future__ | 1 |  |
| app/utils/conversion/qwenvl.py | import | typing | 3 |  |
| app/utils/conversion/qwenvl.py | import | numpy as np | 5 |  |
| app/utils/conversion/qwenvl.py | import | torch | 6 |  |
| app/utils/conversion/qwenvl.py | import | torch | 9 |  |
| app/utils/conversion/qwenvl.py | import | .base | 11 |  |
| app/utils/conversion/refact.py | import | __future__ | 1 |  |
| app/utils/conversion/refact.py | import | typing | 3 |  |
| app/utils/conversion/refact.py | import | torch | 6 |  |
| app/utils/conversion/refact.py | import | .base | 8 |  |
| app/utils/conversion/rwkv.py | import | __future__ | 1 |  |
| app/utils/conversion/rwkv.py | import | typing | 3 |  |
| app/utils/conversion/rwkv.py | import | torch | 5 |  |
| app/utils/conversion/rwkv.py | import | torch | 8 |  |
| app/utils/conversion/rwkv.py | import | .base | 10 |  |
| app/utils/conversion/sarashina2.py | import | __future__ | 1 |  |
| app/utils/conversion/sarashina2.py | import | typing | 3 |  |
| app/utils/conversion/sarashina2.py | import | torch | 6 |  |
| app/utils/conversion/sarashina2.py | import | .base | 8 |  |
| app/utils/conversion/sarashina2.py | import | .llama | 10 |  |
| app/utils/conversion/sarashina2.py | import | .qwenvl | 11 |  |
| app/utils/conversion/smallthinker.py | import | __future__ | 1 |  |
| app/utils/conversion/smallthinker.py | import | typing | 3 |  |
| app/utils/conversion/smallthinker.py | import | torch | 5 |  |
| app/utils/conversion/smallthinker.py | import | torch | 8 |  |
| app/utils/conversion/smallthinker.py | import | .base | 10 |  |
| app/utils/conversion/smolvlm.py | import | __future__ | 1 |  |
| app/utils/conversion/smolvlm.py | import | typing | 3 |  |
| app/utils/conversion/smolvlm.py | import | torch | 6 |  |
| app/utils/conversion/smolvlm.py | import | .base | 8 |  |
| app/utils/conversion/stablelm.py | import | __future__ | 1 |  |
| app/utils/conversion/stablelm.py | import | typing | 3 |  |
| app/utils/conversion/stablelm.py | import | torch | 5 |  |
| app/utils/conversion/stablelm.py | import | torch | 8 |  |
| app/utils/conversion/stablelm.py | import | .base | 10 |  |
| app/utils/conversion/starcoder.py | import | __future__ | 1 |  |
| app/utils/conversion/starcoder.py | import | .base | 3 |  |
| app/utils/conversion/step3.py | import | __future__ | 1 |  |
| app/utils/conversion/step3.py | import | math | 3 |  |
| app/utils/conversion/step3.py | import | re | 4 |  |
| app/utils/conversion/step3.py | import | typing | 6 |  |
| app/utils/conversion/step3.py | import | torch | 8 |  |
| app/utils/conversion/step3.py | import | torch | 11 |  |
| app/utils/conversion/step3.py | import | .base | 13 |  |
| app/utils/conversion/step3.py | import | .qwen | 15 |  |
| app/utils/conversion/t5.py | import | __future__ | 1 |  |
| app/utils/conversion/t5.py | import | json | 3 |  |
| app/utils/conversion/t5.py | import | os | 4 |  |
| app/utils/conversion/t5.py | import | typing | 6 |  |
| app/utils/conversion/t5.py | import | torch | 9 |  |
| app/utils/conversion/t5.py | import | .base | 11 |  |
| app/utils/conversion/t5.py | import | sentencepiece | 30 |  |
| app/utils/conversion/t5.py | import | sentencepiece | 31 |  |
| app/utils/conversion/t5.py | import | sentencepiece | 167 |  |
| app/utils/conversion/t5.py | import | sentencepiece | 168 |  |
| app/utils/conversion/talkie.py | import | __future__ | 1 |  |
| app/utils/conversion/talkie.py | import | typing | 3 |  |
| app/utils/conversion/talkie.py | import | torch | 5 |  |
| app/utils/conversion/talkie.py | import | torch | 8 |  |
| app/utils/conversion/talkie.py | import | .base | 10 |  |
| app/utils/conversion/ultravox.py | import | __future__ | 1 |  |
| app/utils/conversion/ultravox.py | import | typing | 3 |  |
| app/utils/conversion/ultravox.py | import | torch | 6 |  |
| app/utils/conversion/ultravox.py | import | .base | 8 |  |
| app/utils/conversion/wavtokenizer.py | import | __future__ | 1 |  |
| app/utils/conversion/wavtokenizer.py | import | typing | 3 |  |
| app/utils/conversion/wavtokenizer.py | import | torch | 6 |  |
| app/utils/conversion/wavtokenizer.py | import | .base | 8 |  |
| app/utils/conversion/xverse.py | import | __future__ | 1 |  |
| app/utils/conversion/xverse.py | import | re | 3 |  |
| app/utils/conversion/xverse.py | import | typing | 5 |  |
| app/utils/conversion/xverse.py | import | torch | 8 |  |
| app/utils/conversion/xverse.py | import | .base | 10 |  |
| app/utils/conversion/xverse.py | import | transformers | 25 |  |
| app/utils/conversion/youtuvl.py | import | __future__ | 1 |  |
| app/utils/conversion/youtuvl.py | import | typing | 3 |  |
| app/utils/conversion/youtuvl.py | import | torch | 6 |  |
| app/utils/conversion/youtuvl.py | import | .base | 8 |  |
| app/utils/convert_lora_to_gguf.py | import | __future__ | 4 |  |
| app/utils/convert_lora_to_gguf.py | import | dataclasses | 6 |  |
| app/utils/convert_lora_to_gguf.py | import | logging | 7 |  |
| app/utils/convert_lora_to_gguf.py | import | argparse | 8 |  |
| app/utils/convert_lora_to_gguf.py | import | os | 9 |  |
| app/utils/convert_lora_to_gguf.py | import | sys | 10 |  |
| app/utils/convert_lora_to_gguf.py | import | json | 11 |  |
| app/utils/convert_lora_to_gguf.py | import | math | 12 |  |
| app/utils/convert_lora_to_gguf.py | import | pathlib | 13 |  |
| app/utils/convert_lora_to_gguf.py | import | typing | 14 |  |
| app/utils/convert_lora_to_gguf.py | import | transformers | 15 |  |
| app/utils/convert_lora_to_gguf.py | import | torch | 17 |  |
| app/utils/convert_lora_to_gguf.py | import | torch | 20 |  |
| app/utils/convert_lora_to_gguf.py | import | gguf | 24 |  |
| app/utils/convert_lora_to_gguf.py | import | gguf.constants | 25 |  |
| app/utils/convert_lora_to_gguf.py | import | conversion | 28 |  |
| app/utils/convert_lora_to_gguf.py | import | huggingface_hub | 323 |  |
| app/utils/convert_lora_to_gguf.py | import | safetensors.torch | 361 |  |
| app/utils/correlation_logger.py | import | __future__ | 8 |  |
| app/utils/correlation_logger.py | import | contextvars | 10 |  |
| app/utils/correlation_logger.py | import | logging | 11 |  |
| app/utils/correlation_logger.py | import | uuid | 12 |  |
| app/utils/custom_embeddings.py | import | math | 15 |  |
| app/utils/custom_embeddings.py | import | re | 16 |  |
| app/utils/custom_embeddings.py | import | numpy as np | 17 |  |
| app/utils/dataset_merger.py | import | __future__ | 16 |  |
| app/utils/dataset_merger.py | import | hashlib | 18 |  |
| app/utils/dataset_merger.py | import | json | 19 |  |
| app/utils/dataset_merger.py | import | logging | 20 |  |
| app/utils/dataset_merger.py | import | os | 21 |  |
| app/utils/dataset_merger.py | import | datetime | 22 |  |
| app/utils/dataset_merger.py | import | typing | 23 |  |
| app/utils/db_pool.py | import | queue | 5 |  |
| app/utils/db_pool.py | import | sqlite3 | 6 |  |
| app/utils/db_pool.py | import | threading | 7 |  |
| app/utils/db_pool.py | import | contextlib | 8 |  |
| app/utils/db_pool.py | import | typing | 9 |  |
| app/utils/diagnostics.py | import | __future__ | 21 |  |
| app/utils/diagnostics.py | import | importlib | 23 |  |
| app/utils/diagnostics.py | import | importlib.metadata | 24 |  |
| app/utils/diagnostics.py | import | json | 25 |  |
| app/utils/diagnostics.py | import | os | 26 |  |
| app/utils/diagnostics.py | import | platform | 27 |  |
| app/utils/diagnostics.py | import | socket | 28 |  |
| app/utils/diagnostics.py | import | subprocess | 29 |  |
| app/utils/diagnostics.py | import | sys | 30 |  |
| app/utils/diagnostics.py | import | datetime | 31 |  |
| app/utils/diagnostics.py | import | typing | 32 |  |
| app/utils/diagnostics.py | import | torch  # noqa: PLC0415 | 148 |  |
| app/utils/ipc_helper.py | import | os | 8 |  |
| app/utils/ipc_helper.py | import | atexit | 9 |  |
| app/utils/ipc_helper.py | import | logging | 10 |  |
| app/utils/ipc_helper.py | import | signal | 11 |  |
| app/utils/ipc_helper.py | import | threading | 12 |  |
| app/utils/ipc_helper.py | import | multiprocessing.shared_memory | 13 |  |
| app/utils/keychain_manager.py | import | logging | 1 |  |
| app/utils/keychain_manager.py | import | json | 2 |  |
| app/utils/keychain_manager.py | import | os | 3 |  |
| app/utils/keychain_manager.py | import | time | 4 |  |
| app/utils/keychain_manager.py | import | ctypes | 5 |  |
| app/utils/keychain_manager.py | import | sys | 6 |  |
| app/utils/keychain_manager.py | import | keyring | 11 |  |
| app/utils/memory_manager.py | import | os | 1 |  |
| app/utils/memory_manager.py | import | re | 2 |  |
| app/utils/memory_manager.py | import | time | 3 |  |
| app/utils/memory_manager.py | import | datetime | 4 |  |
| app/utils/memory_manager.py | import | app.repository.session_repository | 5 |  |
| app/utils/memory_manager.py | import | app.utils.session_tree | 21 |  |
| app/utils/memory_manager.py | import | app.utils.session_tree | 108 |  |
| app/utils/rag_pipeline.py | import | logging | 12 |  |
| app/utils/rag_pipeline.py | import | json | 13 |  |
| app/utils/rag_pipeline.py | import | os | 14 |  |
| app/utils/rag_pipeline.py | import | sqlite3 | 15 |  |
| app/utils/rag_pipeline.py | import | time | 16 |  |
| app/utils/rag_pipeline.py | import | threading | 17 |  |
| app/utils/rag_pipeline.py | import | concurrent.futures | 18 |  |
| app/utils/rag_pipeline.py | import | dataclasses | 19 |  |
| app/utils/rag_pipeline.py | import | typing | 20 |  |
| app/utils/rag_pipeline.py | import | faiss | 22 |  |
| app/utils/rag_pipeline.py | import | numpy as np | 23 |  |
| app/utils/rag_pipeline.py | import | sentence_transformers | 24 |  |
| app/utils/rag_pipeline.py | import | fitz   # PyMuPDF | 25 |  |
| app/utils/rag_pipeline.py | import | docx | 26 |  |
| app/utils/rag_pipeline.py | import | app.utils.db_pool | 28 |  |
| app/utils/rag_pipeline.py | import | io, contextlib | 220 |  |
| app/utils/rag_pipeline.py | import | sentence_transformers | 221 |  |
| app/utils/rag_pipeline.py | import | io, contextlib | 240 |  |
| app/utils/rag_pipeline.py | import | sentence_transformers | 242 |  |
| app/utils/rag_pipeline.py | import | psutil | 341 |  |
| app/utils/rag_pipeline.py | import | csv | 377 |  |
| app/utils/rag_pipeline.py | import | re | 639 |  |
| app/utils/rag_pipeline.py | import | app.utils.custom_embeddings | 714 |  |
| app/utils/rag_pipeline.py | import | re | 855 |  |
| app/utils/session_tree.py | import | __future__ | 1 |  |
| app/utils/session_tree.py | import | uuid | 3 |  |
| app/utils/session_tree.py | import | dataclasses | 4 |  |
| app/utils/session_tree.py | import | os, json | 256 |  |
| app/utils/session_tree.py | import | uuid | 259 |  |
| app/utils/session_tree.py | import | tempfile, os as _os | 269 |  |
| app/utils/session_tree.py | import | json | 279 |  |
| app/utils/session_tree.py | import | os, json | 289 |  |
| app/utils/session_tree.py | import | os | 312 |  |
| app/utils/trace_logger.py | import | logging | 1 |  |
| app/utils/trace_logger.py | import | os | 2 |  |
| app/utils/trace_logger.py | import | json | 3 |  |
| app/utils/trace_logger.py | import | uuid | 4 |  |
| app/utils/trace_logger.py | import | gzip | 5 |  |
| app/utils/trace_logger.py | import | shutil | 6 |  |
| app/utils/trace_logger.py | import | threading | 7 |  |
| app/utils/trace_logger.py | import | hashlib | 8 |  |
| app/utils/trace_logger.py | import | base64 | 9 |  |
| app/utils/trace_logger.py | import | ctypes | 10 |  |
| app/utils/trace_logger.py | import | sys | 11 |  |
| app/utils/trace_logger.py | import | datetime | 12 |  |
| app/utils/trace_logger.py | import | contextlib | 13 |  |
| app/utils/trace_logger.py | import | app.engine | 86 |  |
| app/utils/trace_logger.py | import | core.hardware_scout | 105 |  |
| app/utils/trace_logger.py | import | app.engine | 138 |  |
| app/utils/trace_logger.py | import | cryptography.fernet | 209 |  |
| app/utils/trace_logger.py | import | core.hardware_scout | 344 |  |
| app/utils/trace_logger.py | import | cryptography.fernet | 405 |  |
| app/utils/trace_logger.py | import | hashlib | 406 |  |
| app/utils/trace_logger.py | import | base64 | 407 |  |
| app/utils/trace_logger.py | import | psutil | 408 |  |
| app/utils/trace_logger.py | import | platform | 409 |  |
| app/utils/trace_logger.py | import | core.hardware_scout | 410 |  |
| app/utils/trace_logger.py | import | cryptography.fernet | 459 |  |
| app/utils/tracing.py | import | __future__ | 9 |  |
| app/utils/tracing.py | import | contextvars | 11 |  |
| app/utils/tracing.py | import | json | 12 |  |
| app/utils/tracing.py | import | os | 13 |  |
| app/utils/tracing.py | import | time | 14 |  |
| app/utils/tracing.py | import | uuid | 15 |  |
| app/utils/tracing.py | import | datetime | 16 |  |
| app/utils/tracing.py | import | pathlib | 17 |  |
| app/utils/tracing.py | import | typing | 18 |  |
| app/utils/training_curator.py | import | os | 10 |  |
| app/utils/training_curator.py | import | json | 11 |  |
| app/utils/training_curator.py | import | datetime | 12 |  |
| app/utils/training_curator.py | import | time | 230 |  |
| app/vision/image_preprocess.py | import | __future__ | 1 |  |
| app/vision/image_preprocess.py | import | os | 3 |  |
| app/vision/image_preprocess.py | import | pathlib | 4 |  |
| app/vision/image_preprocess.py | import | PyQt6.QtCore | 6 |  |
| app/vision/image_preprocess.py | import | PyQt6.QtGui | 7 |  |
| app/vision/image_store.py | import | __future__ | 1 |  |
| app/vision/image_store.py | import | hashlib | 3 |  |
| app/vision/image_store.py | import | json | 4 |  |
| app/vision/image_store.py | import | mimetypes | 5 |  |
| app/vision/image_store.py | import | os | 6 |  |
| app/vision/image_store.py | import | shutil | 7 |  |
| app/vision/image_store.py | import | uuid | 8 |  |
| app/vision/image_store.py | import | datetime | 9 |  |
| app/vision/image_store.py | import | pathlib | 10 |  |
| app/vision/image_store.py | import | PyQt6.QtGui | 12 |  |
| app/vision/image_store.py | import | app.vision.image_preprocess | 14 |  |
| app/vision/image_store.py | import | app.vision.schemas | 15 |  |
| app/vision/ocr_engine.py | import | __future__ | 1 |  |
| app/vision/ocr_engine.py | import | csv | 3 |  |
| app/vision/ocr_engine.py | import | shutil | 4 |  |
| app/vision/ocr_engine.py | import | subprocess | 5 |  |
| app/vision/ocr_engine.py | import | io | 6 |  |
| app/vision/ocr_engine.py | import | app.vision.schemas | 8 |  |
| app/vision/schemas.py | import | __future__ | 1 |  |
| app/vision/schemas.py | import | dataclasses | 3 |  |
| app/vision/schemas.py | import | typing | 4 |  |
| app/vision/vision_analyzer.py | import | __future__ | 1 |  |
| app/vision/vision_analyzer.py | import | re | 3 |  |
| app/vision/vision_analyzer.py | import | dataclasses | 4 |  |
| app/vision/vision_analyzer.py | import | app.vision.schemas | 6 |  |
| app/vision/vision_analyzer.py | import | app.vision.vision_model_loader | 7 |  |
| app/vision/vision_model_loader.py | import | __future__ | 1 |  |
| app/vision/vision_model_loader.py | import | base64 | 3 |  |
| app/vision/vision_model_loader.py | import | json | 4 |  |
| app/vision/vision_model_loader.py | import | threading | 5 |  |
| app/vision/vision_model_loader.py | import | dataclasses | 6 |  |
| app/vision/vision_model_loader.py | import | pathlib | 7 |  |
| app/vision/vision_model_loader.py | import | typing | 8 |  |
| app/vision/vision_model_loader.py | import | app.vision.schemas | 10 |  |
| app/vision/vision_model_loader.py | import | app.engine.config_store | 73 |  |
| app/vision/vision_model_loader.py | import | app.engine.config_store | 82 |  |
| app/vision/vision_model_loader.py | import | app.engine.config_store | 91 |  |
| app/vision/vision_model_loader.py | import | llama_cpp | 146 |  |
| app/vision/vision_model_loader.py | import | llama_cpp.llama_chat_format | 253 |  |
| app/vision/vision_model_loader.py | import | llama_cpp  # noqa: F401 | 280 |  |
| app/vision/vision_model_loader.py | import | llama_cpp.llama_chat_format | 284 |  |
| app/vision/vision_model_loader.py | import | llama_cpp.mtmd_cpp  # noqa: F401 | 288 |  |
| auto_train.py | import | os | 14 |  |
| auto_train.py | import | sys | 15 |  |
| auto_train.py | import | json | 16 |  |
| auto_train.py | import | uuid | 17 |  |
| auto_train.py | import | time | 18 |  |
| auto_train.py | import | argparse | 19 |  |
| auto_train.py | import | subprocess | 20 |  |
| auto_train.py | import | logging | 21 |  |
| auto_train.py | import | pathlib | 22 |  |
| auto_train.py | import | app.engine.model_loader | 47 |  |
| auto_train.py | import | core.cognitive_parser | 48 |  |
| auto_train.py | import | data.flywheel.executor_sandbox | 49 |  |
| auto_train.py | import | core.interaction_loop | 50 |  |
| auto_train.py | import | re | 144 |  |
| auto_train.py | import | torch | 241 |  |
| auto_train.py | import | datasets | 242 |  |
| auto_train.py | import | transformers | 243 |  |
| auto_train.py | import | peft | 244 |  |
| auto_train.py | import | trl | 245 |  |
| auto_train.py | import | shutil | 332 |  |
| core/cognitive_parser.py | import | re | 69 |  |
| core/hardware_scout.py | import | os | 1 |  |
| core/hardware_scout.py | import | shutil | 2 |  |
| core/hardware_scout.py | import | platform | 3 |  |
| core/hardware_scout.py | import | subprocess | 4 |  |
| core/hardware_scout.py | import | uuid | 67 |  |
| core/hardware_scout.py | import | hashlib | 68 |  |
| core/hardware_scout.py | import | psutil | 81 |  |
| core/hardware_scout.py | import | pynvml | 91 |  |
| core/hardware_scout.py | import | GPUtil | 120 |  |
| core/interaction_loop.py | import | logging | 5 |  |
| core/interaction_loop.py | import | os | 6 |  |
| core/interaction_loop.py | import | re | 7 |  |
| core/interaction_loop.py | import | app.engine.model_loader | 8 |  |
| core/prompt_templates.py | import | typing | 9 |  |
| core/workflows.py | import | typing | 10 |  |
| data/flywheel/active_learner.py | import | os | 1 |  |
| data/flywheel/active_learner.py | import | json | 2 |  |
| data/flywheel/agent1_generator.py | import | os | 1 |  |
| data/flywheel/agent1_generator.py | import | sys | 2 |  |
| data/flywheel/agent1_generator.py | import | json | 3 |  |
| data/flywheel/agent1_generator.py | import | uuid | 4 |  |
| data/flywheel/agent1_generator.py | import | time | 5 |  |
| data/flywheel/agent1_generator.py | import | random | 6 |  |
| data/flywheel/agent1_generator.py | import | argparse | 7 |  |
| data/flywheel/agent1_generator.py | import | collections | 8 |  |
| data/flywheel/agent1_generator.py | import | math | 9 |  |
| data/flywheel/agent1_generator.py | import | pathlib as _pathlib | 12 |  |
| data/flywheel/agent1_generator.py | import | re | 105 |  |
| data/flywheel/agent1_generator.py | import | re | 180 |  |
| data/flywheel/agent1_generator.py | import | re | 203 |  |
| data/flywheel/agent1_generator.py | import | re | 257 |  |
| data/flywheel/agent1_generator.py | import | math | 266 |  |
| data/flywheel/agent1_generator.py | import | re | 278 |  |
| data/flywheel/agent1_generator.py | import | re | 332 |  |
| data/flywheel/agent1_generator.py | import | app.utils.topic_graph | 372 |  |
| data/flywheel/agent1_generator.py | import | data.flywheel.active_learner | 402 |  |
| data/flywheel/agent3_curator.py | import | os | 11 |  |
| data/flywheel/agent3_curator.py | import | sys | 12 |  |
| data/flywheel/agent3_curator.py | import | json | 13 |  |
| data/flywheel/agent3_curator.py | import | time | 14 |  |
| data/flywheel/agent3_curator.py | import | logging | 15 |  |
| data/flywheel/agent3_curator.py | import | tempfile | 16 |  |
| data/flywheel/agent3_curator.py | import | subprocess | 17 |  |
| data/flywheel/agent3_curator.py | import | argparse | 18 |  |
| data/flywheel/agent3_curator.py | import | datetime | 19 |  |
| data/flywheel/agent3_curator.py | import | pathlib | 20 |  |
| data/flywheel/agent3_curator.py | import | data.flywheel.executor_sandbox | 26 |  |
| data/flywheel/agent3_curator.py | import | re | 129 |  |
| data/flywheel/agent3_curator.py | import | sympy | 130 |  |
| data/flywheel/agent3_curator.py | import | app.engine.model_loader | 168 |  |
| data/flywheel/agent3_curator.py | import | core.interaction_loop | 169 |  |
| data/flywheel/agent3_curator.py | import | app.utils.training_curator | 239 |  |
| data/flywheel/executor_sandbox.py | import | subprocess | 1 |  |
| data/flywheel/executor_sandbox.py | import | sys | 2 |  |
| data/flywheel/executor_sandbox.py | import | os | 3 |  |
| data/flywheel/executor_sandbox.py | import | tempfile | 4 |  |
| data/flywheel/executor_sandbox.py | import | logging | 5 |  |
| data/flywheel/executor_sandbox.py | import | resource | 94 |  |
| download_all_models.py | import | os | 1 |  |
| download_all_models.py | import | argparse | 2 |  |
| download_all_models.py | import | json | 3 |  |
| download_all_models.py | import | requests | 4 |  |
| download_all_models.py | import | tqdm | 5 |  |
| download_test_model.py | import | os | 1 |  |
| download_test_model.py | import | requests | 2 |  |
| download_test_model.py | import | tqdm | 3 |  |
| engine_test.py | import | os | 14 |  |
| engine_test.py | import | sys | 15 |  |
| engine_test.py | import | time | 16 |  |
| engine_test.py | import | app.engine.model_loader | 20 |  |
| engine_test.py | import | app.utils.trace_logger | 21 |  |
| engine_test.py | import | core.cognitive_parser | 22 |  |
| eval/benchmark_rag.py | import | os | 12 |  |
| eval/benchmark_rag.py | import | sys | 13 |  |
| eval/benchmark_rag.py | import | time | 14 |  |
| eval/benchmark_rag.py | import | textwrap | 15 |  |
| eval/benchmark_rag.py | import | json | 16 |  |
| eval/benchmark_rag.py | import | re | 17 |  |
| eval/benchmark_rag.py | import | math | 18 |  |
| eval/benchmark_rag.py | import | collections | 19 |  |
| eval/benchmark_rag.py | import | dataclasses | 20 |  |
| eval/benchmark_rag.py | import | numpy as np | 21 |  |
| eval/benchmark_rag.py | import | app.utils.rag_pipeline | 25 |  |
| eval/benchmark_rag.py | import | app.engine.model_loader | 26 |  |
| eval/benchmark_rag.py | import | core.interaction_loop | 27 |  |
| eval/benchmark_rag.py | import | core.cognitive_parser | 28 |  |
| eval/benchmark_rag.py | import | argparse | 465 |  |
| eval/graders.py | import | json | 13 |  |
| eval/graders.py | import | re | 14 |  |
| eval/graders.py | import | typing | 15 |  |
| eval/harness.py | import | json | 24 |  |
| eval/harness.py | import | os | 25 |  |
| eval/harness.py | import | sys | 26 |  |
| eval/harness.py | import | time | 27 |  |
| eval/harness.py | import | dataclasses | 28 |  |
| eval/harness.py | import | typing | 29 |  |
| eval/harness.py | import | eval.graders | 34 |  |
| eval/harness.py | import | core.prompt_templates | 35 |  |
| eval/harness.py | import | core.workflows | 36 |  |
| eval/harness.py | import | app.engine.model_loader | 171 |  |
| eval/harness.py | import | core.interaction_loop | 172 |  |
| eval/harness.py | import | datetime | 236 |  |
| eval/harness.py | import | app.engine.model_loader | 237 |  |
| eval/harness.py | import | core.hardware_scout | 251 |  |
| eval/harness.py | import | concurrent.futures | 285 |  |
| eval/harness.py | import | app.utils.training_curator | 325 |  |
| eval/perplexity_bench.py | import | gc | 32 |  |
| eval/perplexity_bench.py | import | json | 33 |  |
| eval/perplexity_bench.py | import | math | 34 |  |
| eval/perplexity_bench.py | import | multiprocessing | 35 |  |
| eval/perplexity_bench.py | import | os | 36 |  |
| eval/perplexity_bench.py | import | sys | 37 |  |
| eval/perplexity_bench.py | import | time | 38 |  |
| eval/perplexity_bench.py | import | argparse | 39 |  |
| eval/perplexity_bench.py | import | logging | 40 |  |
| eval/perplexity_bench.py | import | numpy as np | 42 |  |
| eval/perplexity_bench.py | import | llama_cpp | 46 |  |
| eval/perplexity_bench.py | import | app.engine.model_loader | 47 |  |
| eval/perplexity_bench.py | import | core.hardware_scout | 48 |  |
| eval/perplexity_bench.py | import | torch | 309 |  |
| eval/run_eval.py | import | argparse | 22 |  |
| eval/run_eval.py | import | json | 23 |  |
| eval/run_eval.py | import | os | 24 |  |
| eval/run_eval.py | import | sys | 25 |  |
| eval/run_eval.py | import | core.workflows | 29 |  |
| eval/run_eval.py | import | core.prompt_templates | 30 |  |
| eval/run_eval.py | import | eval.harness | 31 |  |
| eval/run_eval.py | import | eval.graders | 32 |  |
| eval/run_eval.py | import | eval.graders | 112 |  |
| eval/run_eval.py | import | core.hardware_scout | 197 |  |
| flywheel_runner.py | import | os | 1 |  |
| flywheel_runner.py | import | time | 2 |  |
| flywheel_runner.py | import | json | 3 |  |
| flywheel_runner.py | import | uuid | 4 |  |
| flywheel_runner.py | import | logging | 5 |  |
| flywheel_runner.py | import | threading | 6 |  |
| flywheel_runner.py | import | typing | 7 |  |
| flywheel_runner.py | import | app.engine.model_loader | 9 |  |
| flywheel_runner.py | import | app.engine | 10 |  |
| flywheel_runner.py | import | core.cognitive_parser | 11 |  |
| main.py | import | os | 7 |  |
| main.py | import | sys | 12 |  |
| main.py | import | io | 13 |  |
| main.py | import | multiprocessing | 14 |  |
| main.py | import | warnings | 26 |  |
| main.py | import | torch          # noqa: F401  (triggers triton + cpp warnings) | 50 |  |
| main.py | import | faiss          # noqa: F401 | 51 |  |
| main.py | import | sentence_transformers | 52 |  |
| main.py | import | logging | 55 |  |
| main.py | import | absl.logging as _absl_log | 70 |  |
| main.py | import | app.utils.correlation_logger | 79 |  |
| main.py | import | PyQt6.QtWidgets | 92 |  |
| main.py | import | app.ui.main_window | 93 |  |
| main.py | import | platform | 109 |  |
| main.py | import | ctypes | 117 |  |
| main.py | import | signal | 133 |  |
| main.py | import | threading | 134 |  |
| main.py | import | app.engine.websocket_server | 136 |  |
| main.py | import | app.engine.feature_flags | 170 |  |
| main.py | import | app.utils.diagnostics | 174 |  |
| main.py | import | app.utils.keychain_manager | 178 |  |
| main.py | import | uuid as _uuid | 179 |  |
| main.py | import | app.utils.keychain_manager | 209 |  |
| main.py | import | app.engine.websocket_server | 216 |  |
| main.py | import | app.ui.themes | 254 |  |
| main.py | import | app.utils.keychain_manager | 263 |  |
| raw_test.py | import | os | 5 |  |
| raw_test.py | import | llama_cpp | 8 |  |
| setup_karl.py | import | __future__ | 19 |  |
| setup_karl.py | import | argparse | 21 |  |
| setup_karl.py | import | os | 22 |  |
| setup_karl.py | import | platform | 23 |  |
| setup_karl.py | import | shutil | 24 |  |
| setup_karl.py | import | subprocess | 25 |  |
| setup_karl.py | import | sys | 26 |  |
| setup_karl.py | import | pathlib | 27 |  |
| setup_karl.py | import | typing | 28 |  |
| setup_karl.py | import | ctypes | 57 |  |
| smoke_test.py | import | sys | 1 |  |
| smoke_test.py | import | core.prompt_templates | 4 |  |
| smoke_test.py | import | core.workflows | 5 |  |
| smoke_test.py | import | eval.graders | 6 |  |
| smoke_test.py | import | json | 28 |  |
| tests/__init__.py | import | os | 1 |  |
| tests/__init__.py | import | sys | 2 |  |
| tests/__init__.py | import | PyQt6.QtWidgets | 8 |  |
| tests/conftest.py | import | functools | 12 |  |
| tests/conftest.py | import | importlib.util | 13 |  |
| tests/conftest.py | import | pytest | 15 |  |
| tests/conftest.py | import | sentence_transformers | 33 |  |
| tests/mock_mcp_server.py | import | mcp.server.fastmcp | 7 |  |
| tests/qt_test_helper.py | import | os | 1 |  |
| tests/qt_test_helper.py | import | sys | 2 |  |
| tests/qt_test_helper.py | import | PyQt6.QtWidgets | 3 |  |
| tests/test_agent_memory.py | import | json | 1 |  |
| tests/test_agent_memory.py | import | unittest.mock | 2 |  |
| tests/test_agent_memory.py | import | app.engine.agent_memory | 4 |  |
| tests/test_agent_memory.py | import | app.engine.swarm_agents | 61 |  |
| tests/test_ai_lab.py | import | os | 1 |  |
| tests/test_ai_lab.py | import | json | 2 |  |
| tests/test_ai_lab.py | import | unittest | 3 |  |
| tests/test_ai_lab.py | import | tempfile | 4 |  |
| tests/test_ai_lab.py | import | shutil | 5 |  |
| tests/test_ai_lab.py | import | PyQt6.QtWidgets | 6 |  |
| tests/test_ai_lab.py | import | tests.qt_test_helper  # noqa: F401 | 8 |  |
| tests/test_ai_lab.py | import | app.state | 9 |  |
| tests/test_ai_lab.py | import | app.ui.workspaces.ai_lab | 10 |  |
| tests/test_ai_lab.py | import | app.utils.rag_pipeline | 11 |  |
| tests/test_ai_lab.py | import | PyQt6.QtWidgets | 109 |  |
| tests/test_app_state_persistence.py | import | tests.qt_test_helper  # noqa: F401  — must come first to init QApplication | 3 |  |
| tests/test_app_state_persistence.py | import | json | 5 |  |
| tests/test_app_state_persistence.py | import | os | 6 |  |
| tests/test_app_state_persistence.py | import | sys | 7 |  |
| tests/test_app_state_persistence.py | import | unittest | 8 |  |
| tests/test_app_state_persistence.py | import | unittest.mock | 9 |  |
| tests/test_app_state_persistence.py | import | app.state | 13 |  |
| tests/test_app_state_persistence.py | import | app.engine | 14 |  |
| tests/test_app_state_persistence.py | import | tempfile | 48 |  |
| tests/test_app_state_persistence.py | import | shutil | 60 |  |
| tests/test_app_state_persistence.py | import | tempfile | 281 |  |
| tests/test_app_state_persistence.py | import | shutil | 292 |  |
| tests/test_app_state_persistence.py | import | tempfile | 374 |  |
| tests/test_app_state_persistence.py | import | shutil | 385 |  |
| tests/test_app_state_persistence.py | import | tempfile | 445 |  |
| tests/test_app_state_persistence.py | import | shutil | 454 |  |
| tests/test_architecture_audit.py | import | asyncio | 1 |  |
| tests/test_architecture_audit.py | import | inspect | 2 |  |
| tests/test_architecture_audit.py | import | threading | 3 |  |
| tests/test_architecture_audit.py | import | pathlib | 4 |  |
| tests/test_architecture_audit.py | import | pytest | 6 |  |
| tests/test_architecture_audit.py | import | app.engine.model_loader | 11 |  |
| tests/test_architecture_audit.py | import | app.engine.websocket_server | 55 |  |
| tests/test_architecture_audit.py | import | app.engine.websocket_server | 92 |  |
| tests/test_auto_train.py | import | os | 8 |  |
| tests/test_auto_train.py | import | sys | 9 |  |
| tests/test_auto_train.py | import | json | 10 |  |
| tests/test_auto_train.py | import | unittest | 11 |  |
| tests/test_auto_train.py | import | tempfile | 12 |  |
| tests/test_auto_train.py | import | asyncio | 13 |  |
| tests/test_auto_train.py | import | unittest.mock | 14 |  |
| tests/test_auto_train.py | import | tests.qt_test_helper  # noqa: F401 | 19 |  |
| tests/test_auto_train.py | import | PyQt6.QtCore | 20 |  |
| tests/test_auto_train.py | import | websockets | 21 |  |
| tests/test_auto_train.py | import | pytest | 22 |  |
| tests/test_auto_train.py | import | auto_train | 24 |  |
| tests/test_auto_train.py | import | app.ui.workspaces.training_studio | 25 |  |
| tests/test_auto_train.py | import | app.engine.websocket_server | 26 |  |
| tests/test_auto_train.py | import | ssl | 112 |  |
| tests/test_codex_integration.py | import | os | 1 |  |
| tests/test_codex_integration.py | import | sys | 2 |  |
| tests/test_codex_integration.py | import | unittest | 3 |  |
| tests/test_codex_integration.py | import | core.interaction_loop | 7 |  |
| tests/test_codex_integration.py | import | fastapi | 15 |  |
| tests/test_cognitive_compression.py | import | tests.qt_test_helper  # noqa: F401 | 1 |  |
| tests/test_cognitive_compression.py | import | os | 3 |  |
| tests/test_cognitive_compression.py | import | sys | 4 |  |
| tests/test_cognitive_compression.py | import | time | 5 |  |
| tests/test_cognitive_compression.py | import | PyQt6.QtCore | 6 |  |
| tests/test_cognitive_compression.py | import | unittest.mock | 10 |  |
| tests/test_cognitive_compression.py | import | app.engine.model_loader | 11 |  |
| tests/test_cognitive_compression.py | import | app.engine.llm_thread | 12 |  |
| tests/test_cognitive_compression.py | import | app.engine.agentic_thread | 13 |  |
| tests/test_cognitive_compression.py | import | core.agentic_loop | 14 |  |
| tests/test_cognitive_parser.py | import | os | 1 |  |
| tests/test_cognitive_parser.py | import | sys | 2 |  |
| tests/test_cognitive_parser.py | import | core.cognitive_parser | 6 |  |
| tests/test_cognitive_parser_fuzz.py | import | __future__ | 20 |  |
| tests/test_cognitive_parser_fuzz.py | import | random | 22 |  |
| tests/test_cognitive_parser_fuzz.py | import | string | 23 |  |
| tests/test_cognitive_parser_fuzz.py | import | time | 24 |  |
| tests/test_cognitive_parser_fuzz.py | import | typing | 25 |  |
| tests/test_cognitive_parser_fuzz.py | import | pytest | 27 |  |
| tests/test_cognitive_parser_fuzz.py | import | core.cognitive_parser | 29 |  |
| tests/test_config_store.py | import | json | 3 |  |
| tests/test_config_store.py | import | os | 4 |  |
| tests/test_config_store.py | import | sys | 5 |  |
| tests/test_config_store.py | import | pytest | 7 |  |
| tests/test_config_store.py | import | app.engine | 11 |  |
| tests/test_correlation_logging.py | import | __future__ | 13 |  |
| tests/test_correlation_logging.py | import | asyncio | 15 |  |
| tests/test_correlation_logging.py | import | logging | 16 |  |
| tests/test_correlation_logging.py | import | threading | 17 |  |
| tests/test_correlation_logging.py | import | typing | 18 |  |
| tests/test_correlation_logging.py | import | app.utils.correlation_logger | 20 |  |
| tests/test_custom_agents.py | import | tests.qt_test_helper  # noqa: F401 | 7 |  |
| tests/test_custom_agents.py | import | os | 8 |  |
| tests/test_custom_agents.py | import | json | 9 |  |
| tests/test_custom_agents.py | import | asyncio | 10 |  |
| tests/test_custom_agents.py | import | unittest | 11 |  |
| tests/test_custom_agents.py | import | sys | 12 |  |
| tests/test_custom_agents.py | import | unittest.mock | 13 |  |
| tests/test_custom_agents.py | import | websockets | 15 |  |
| tests/test_custom_agents.py | import | pytest | 16 |  |
| tests/test_custom_agents.py | import | PyQt6.QtCore | 17 |  |
| tests/test_custom_agents.py | import | app.engine.websocket_server | 19 |  |
| tests/test_custom_agents.py | import | app.ui.workspaces.workbench.profiles | 20 |  |
| tests/test_custom_agents.py | import | app.engine.llm_thread | 21 |  |
| tests/test_custom_agents.py | import | ssl | 93 |  |
| tests/test_dataset_merger.py | import | __future__ | 12 |  |
| tests/test_dataset_merger.py | import | json | 14 |  |
| tests/test_dataset_merger.py | import | os | 15 |  |
| tests/test_dataset_merger.py | import | tempfile | 16 |  |
| tests/test_dataset_merger.py | import | pytest | 18 |  |
| tests/test_dataset_merger.py | import | app.utils.dataset_merger | 20 |  |
| tests/test_db_pool.py | import | os | 6 |  |
| tests/test_db_pool.py | import | sqlite3 | 7 |  |
| tests/test_db_pool.py | import | threading | 8 |  |
| tests/test_db_pool.py | import | time | 9 |  |
| tests/test_db_pool.py | import | pytest | 11 |  |
| tests/test_db_pool.py | import | app.utils.db_pool | 13 |  |
| tests/test_db_transactions.py | import | os | 1 |  |
| tests/test_db_transactions.py | import | sqlite3 | 2 |  |
| tests/test_db_transactions.py | import | threading | 3 |  |
| tests/test_db_transactions.py | import | time | 4 |  |
| tests/test_db_transactions.py | import | numpy as np | 6 |  |
| tests/test_db_transactions.py | import | pytest | 7 |  |
| tests/test_db_transactions.py | import | app.utils.rag_pipeline | 9 |  |
| tests/test_educational_sandbox.py | import | pytest | 7 |  |
| tests/test_educational_sandbox.py | import | numpy as np | 8 |  |
| tests/test_educational_sandbox.py | import | torch | 9 |  |
| tests/test_educational_sandbox.py | import | app.utils.custom_embeddings | 10 |  |
| tests/test_educational_sandbox.py | import | app.engine.mini_transformer | 11 |  |
| tests/test_eval_harness.py | import | os | 1 |  |
| tests/test_eval_harness.py | import | sys | 2 |  |
| tests/test_eval_harness.py | import | json | 3 |  |
| tests/test_eval_harness.py | import | tempfile | 4 |  |
| tests/test_eval_harness.py | import | shutil | 5 |  |
| tests/test_eval_harness.py | import | app.engine.model_loader | 9 |  |
| tests/test_eval_harness.py | import | eval.harness | 10 |  |
| tests/test_eval_harness.py | import | eval.harness | 98 |  |
| tests/test_eval_harness.py | import | app.engine.model_loader | 99 |  |
| tests/test_eval_harness.py | import | app.utils.training_curator as tc | 100 |  |
| tests/test_event_broker.py | import | os | 1 |  |
| tests/test_event_broker.py | import | sys | 2 |  |
| tests/test_event_broker.py | import | threading | 3 |  |
| tests/test_event_broker.py | import | app.engine.event_broker | 7 |  |
| tests/test_failure_paths.py | import | __future__ | 3 |  |
| tests/test_failure_paths.py | import | os | 5 |  |
| tests/test_failure_paths.py | import | json | 6 |  |
| tests/test_failure_paths.py | import | time | 7 |  |
| tests/test_failure_paths.py | import | pytest | 8 |  |
| tests/test_failure_paths.py | import | unittest.mock | 9 |  |
| tests/test_failure_paths.py | import | app.engine.model_loader | 11 |  |
| tests/test_failure_paths.py | import | app.engine.task_supervisor | 12 |  |
| tests/test_failure_paths.py | import | core.cognitive_parser | 13 |  |
| tests/test_failure_paths.py | import | app.utils.trace_logger | 14 |  |
| tests/test_failure_paths.py | import | llama_cpp | 40 |  |
| tests/test_failure_paths.py | import | app.engine.llm_thread | 56 |  |
| tests/test_feature_flags.py | import | __future__ | 8 |  |
| tests/test_feature_flags.py | import | json | 10 |  |
| tests/test_feature_flags.py | import | os | 11 |  |
| tests/test_feature_flags.py | import | time | 12 |  |
| tests/test_feature_flags.py | import | pytest | 14 |  |
| tests/test_feature_flags.py | import | app.engine.feature_flags | 16 |  |
| tests/test_hardware_scout.py | import | os | 1 |  |
| tests/test_hardware_scout.py | import | sys | 2 |  |
| tests/test_hardware_scout.py | import | unittest.mock as mock | 3 |  |
| tests/test_hardware_scout.py | import | core.hardware_scout | 7 |  |
| tests/test_hardware_scout.py | import | tests.conftest | 8 |  |
| tests/test_image_store.py | import | os | 1 |  |
| tests/test_image_store.py | import | sys | 2 |  |
| tests/test_image_store.py | import | PyQt6.QtGui | 6 |  |
| tests/test_image_store.py | import | app.vision.schemas | 8 |  |
| tests/test_image_store.py | import | app.vision.image_store | 9 |  |
| tests/test_inference_safety.py | import | __future__ | 3 |  |
| tests/test_inference_safety.py | import | io | 5 |  |
| tests/test_inference_safety.py | import | os | 6 |  |
| tests/test_inference_safety.py | import | pytest | 8 |  |
| tests/test_inference_safety.py | import | app.engine.model_loader | 12 |  |
| tests/test_inference_safety.py | import | app.engine.model_loader | 27 |  |
| tests/test_inference_safety.py | import | app.engine.model_loader | 61 |  |
| tests/test_inference_safety.py | import | app.engine.offline_guard | 86 |  |
| tests/test_inference_safety.py | import | app.engine.offline_guard | 94 |  |
| tests/test_inference_safety.py | import | app.engine.offline_guard | 102 |  |
| tests/test_inference_safety.py | import | requests | 109 |  |
| tests/test_inference_safety.py | import | app.engine.offline_guard | 110 |  |
| tests/test_inference_safety.py | import | app.engine.agentic_thread | 118 |  |
| tests/test_inference_safety.py | import | app.engine.llm_thread | 154 |  |
| tests/test_inference_safety.py | import | app.engine.model_loader | 197 |  |
| tests/test_inference_safety.py | import | app.engine.model_loader | 222 |  |
| tests/test_inference_safety.py | import | app.engine | 240 |  |
| tests/test_inference_safety.py | import | app.engine | 258 |  |
| tests/test_inference_safety.py | import | app.engine | 276 |  |
| tests/test_inference_service.py | import | __future__ | 8 |  |
| tests/test_inference_service.py | import | pytest | 10 |  |
| tests/test_inference_service.py | import | tests.qt_test_helper  # noqa: F401 — side-effect: creates QApplication | 12 |  |
| tests/test_inference_service.py | import | PyQt6.QtCore | 14 |  |
| tests/test_inference_service.py | import | app.engine.inference_service | 16 |  |
| tests/test_inference_service.py | import | app.engine.inference_service as svc_mod | 90 |  |
| tests/test_inference_service.py | import | PyQt6.QtCore | 100 |  |
| tests/test_inference_service.py | import | app.engine.inference_service as svc_mod | 110 |  |
| tests/test_inference_service.py | import | app.engine.inference_service as svc_mod | 134 |  |
| tests/test_inference_service.py | import | app.engine.inference_service as svc_mod | 159 |  |
| tests/test_inference_service.py | import | app.engine.inference_service as svc_mod | 268 |  |
| tests/test_inference_service.py | import | app.engine.inference_service as svc_mod | 318 |  |
| tests/test_kv_quantization.py | import | unittest.mock | 1 |  |
| tests/test_kv_quantization.py | import | app.engine.model_loader | 16 |  |
| tests/test_local_tracing.py | import | json | 1 |  |
| tests/test_local_tracing.py | import | time | 2 |  |
| tests/test_local_tracing.py | import | app.utils.tracing | 4 |  |
| tests/test_log_governance.py | import | os | 1 |  |
| tests/test_log_governance.py | import | sys | 2 |  |
| tests/test_log_governance.py | import | tempfile | 3 |  |
| tests/test_log_governance.py | import | time | 4 |  |
| tests/test_log_governance.py | import | app.utils.trace_logger | 8 |  |
| tests/test_log_governance.py | import | app.engine | 42 |  |
| tests/test_log_governance.py | import | shutil | 68 |  |
| tests/test_mcp_client.py | import | tests.qt_test_helper  # noqa: F401 | 8 |  |
| tests/test_mcp_client.py | import | os | 10 |  |
| tests/test_mcp_client.py | import | json | 11 |  |
| tests/test_mcp_client.py | import | tempfile | 12 |  |
| tests/test_mcp_client.py | import | sys | 13 |  |
| tests/test_mcp_client.py | import | unittest | 14 |  |
| tests/test_mcp_client.py | import | pytest | 15 |  |
| tests/test_mcp_client.py | import | app.engine.mcp_client | 17 |  |
| tests/test_memory_manager.py | import | os | 1 |  |
| tests/test_memory_manager.py | import | shutil | 2 |  |
| tests/test_memory_manager.py | import | tempfile | 3 |  |
| tests/test_memory_manager.py | import | sys | 4 |  |
| tests/test_memory_manager.py | import | app.utils.memory_manager | 8 |  |
| tests/test_memory_manager.py | import | app.utils.session_tree | 9 |  |
| tests/test_memory_repository.py | import | os | 1 |  |
| tests/test_memory_repository.py | import | sys | 2 |  |
| tests/test_memory_repository.py | import | app.utils.memory_manager | 6 |  |
| tests/test_model_circuit_breaker.py | import | unittest.mock | 1 |  |
| tests/test_model_circuit_breaker.py | import | pytest | 3 |  |
| tests/test_model_circuit_breaker.py | import | app.engine.model_loader | 5 |  |
| tests/test_observability_telemetry.py | import | os | 1 |  |
| tests/test_observability_telemetry.py | import | sys | 2 |  |
| tests/test_observability_telemetry.py | import | tempfile | 3 |  |
| tests/test_observability_telemetry.py | import | json | 4 |  |
| tests/test_observability_telemetry.py | import | tests.qt_test_helper  # noqa: F401  # Ensures global QApplication runs headlessly | 8 |  |
| tests/test_observability_telemetry.py | import | app.ui.workspaces.system_config.observability_tab | 9 |  |
| tests/test_observability_telemetry.py | import | app.ui.workspaces.system_config.observability_tab as ot | 46 |  |
| tests/test_observability_telemetry.py | import | shutil | 66 |  |
| tests/test_ocr_engine.py | import | os | 1 |  |
| tests/test_ocr_engine.py | import | sys | 2 |  |
| tests/test_ocr_engine.py | import | app.vision.ocr_engine | 6 |  |
| tests/test_prometheus_exporter.py | import | types | 1 |  |
| tests/test_prometheus_exporter.py | import | tests.qt_test_helper  # noqa: F401 | 3 |  |
| tests/test_prometheus_exporter.py | import | websockets.datastructures | 5 |  |
| tests/test_prometheus_exporter.py | import | app.engine.websocket_server | 7 |  |
| tests/test_prompt_caching.py | import | __future__ | 15 |  |
| tests/test_prompt_caching.py | import | json | 17 |  |
| tests/test_prompt_caching.py | import | os | 18 |  |
| tests/test_prompt_caching.py | import | tempfile | 19 |  |
| tests/test_prompt_caching.py | import | time | 20 |  |
| tests/test_prompt_caching.py | import | collections | 21 |  |
| tests/test_prompt_caching.py | import | typing | 22 |  |
| tests/test_prompt_caching.py | import | unittest.mock | 23 |  |
| tests/test_prompt_caching.py | import | pytest | 25 |  |
| tests/test_prompt_caching.py | import | llama_cpp | 37 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 67 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 75 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 86 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 102 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 114 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 129 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 147 |  |
| tests/test_prompt_caching.py | import | app.engine.kv_cache | 161 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 172 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 178 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 183 |  |
| tests/test_prompt_caching.py | import | llama_cpp | 184 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 199 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 211 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 223 |  |
| tests/test_prompt_caching.py | import | llama_cpp | 224 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 239 |  |
| tests/test_prompt_caching.py | import | llama_cpp | 240 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 258 |  |
| tests/test_prompt_caching.py | import | app.engine.model_loader | 307 |  |
| tests/test_prompt_caching.py | import | llama_cpp | 373 |  |
| tests/test_prompt_caching.py | import | llama_cpp | 432 |  |
| tests/test_rag_pipeline.py | import | os | 1 |  |
| tests/test_rag_pipeline.py | import | json | 2 |  |
| tests/test_rag_pipeline.py | import | shutil | 3 |  |
| tests/test_rag_pipeline.py | import | tempfile | 4 |  |
| tests/test_rag_pipeline.py | import | sys | 5 |  |
| tests/test_rag_pipeline.py | import | numpy as np | 6 |  |
| tests/test_rag_pipeline.py | import | time | 7 |  |
| tests/test_rag_pipeline.py | import | pytest | 8 |  |
| tests/test_rag_pipeline.py | import | app.utils.rag_pipeline | 12 |  |
| tests/test_rag_pipeline.py | import | pytest | 73 |  |
| tests/test_rag_pipeline.py | import | tests.conftest | 74 |  |
| tests/test_rag_pipeline.py | import | pytest | 153 |  |
| tests/test_rag_pipeline.py | import | tests.conftest | 154 |  |
| tests/test_rag_pipeline.py | import | pytest | 178 |  |
| tests/test_rag_pipeline.py | import | tests.conftest | 179 |  |
| tests/test_rag_reranker.py | import | __future__ | 13 |  |
| tests/test_rag_reranker.py | import | shutil | 15 |  |
| tests/test_rag_reranker.py | import | tempfile | 16 |  |
| tests/test_rag_reranker.py | import | unittest.mock | 17 |  |
| tests/test_rag_reranker.py | import | numpy as np | 19 |  |
| tests/test_rag_reranker.py | import | pytest | 20 |  |
| tests/test_rag_reranker.py | import | app.utils.rag_pipeline | 22 |  |
| tests/test_rbac_scopes.py | import | __future__ | 14 |  |
| tests/test_rbac_scopes.py | import | asyncio | 16 |  |
| tests/test_rbac_scopes.py | import | json | 17 |  |
| tests/test_rbac_scopes.py | import | time | 18 |  |
| tests/test_rbac_scopes.py | import | unittest.mock | 19 |  |
| tests/test_rbac_scopes.py | import | websockets | 21 |  |
| tests/test_rbac_scopes.py | import | websockets.exceptions | 22 |  |
| tests/test_rbac_scopes.py | import | pytest | 23 |  |
| tests/test_rbac_scopes.py | import | app.engine.websocket_server | 54 |  |
| tests/test_rbac_scopes.py | import | app.engine.websocket_server | 210 |  |
| tests/test_rbac_scopes.py | import | uuid | 246 |  |
| tests/test_rbac_scopes.py | import | app.utils.keychain_manager | 247 |  |
| tests/test_remote_offloading.py | import | __future__ | 1 |  |
| tests/test_remote_offloading.py | import | types | 3 |  |
| tests/test_remote_offloading.py | import | app.engine.remote_rpc_client | 7 |  |
| tests/test_remote_offloading.py | import | app.engine.model_loader | 75 |  |
| tests/test_security_guards.py | import | __future__ | 16 |  |
| tests/test_security_guards.py | import | tests.qt_test_helper  # noqa: F401 | 18 |  |
| tests/test_security_guards.py | import | os | 20 |  |
| tests/test_security_guards.py | import | re | 21 |  |
| tests/test_security_guards.py | import | tempfile | 22 |  |
| tests/test_security_guards.py | import | unittest | 23 |  |
| tests/test_security_guards.py | import | pathlib | 24 |  |
| tests/test_security_guards.py | import | unittest.mock | 25 |  |
| tests/test_security_guards.py | import | app.engine.websocket_server | 35 |  |
| tests/test_security_guards.py | import | shutil | 312 |  |
| tests/test_security_guards.py | import | app.ui.workspaces.workbench.chat_view | 405 |  |
| tests/test_security_sandbox.py | import | os | 10 |  |
| tests/test_security_sandbox.py | import | sys | 11 |  |
| tests/test_security_sandbox.py | import | platform | 12 |  |
| tests/test_security_sandbox.py | import | time | 13 |  |
| tests/test_security_sandbox.py | import | pytest | 14 |  |
| tests/test_security_sandbox.py | import | unittest.mock | 15 |  |
| tests/test_security_sandbox.py | import | main | 29 |  |
| tests/test_security_sandbox.py | import | main | 39 |  |
| tests/test_security_sandbox.py | import | app.engine.swarm_agents | 46 |  |
| tests/test_security_sandbox.py | import | app.engine.swarm_agents | 89 |  |
| tests/test_security_sandbox.py | import | app.engine.websocket_server | 202 |  |
| tests/test_service_discovery.py | import | __future__ | 16 |  |
| tests/test_service_discovery.py | import | pytest | 18 |  |
| tests/test_service_discovery.py | import | asyncio | 22 |  |
| tests/test_service_discovery.py | import | json | 23 |  |
| tests/test_service_discovery.py | import | socket | 24 |  |
| tests/test_service_discovery.py | import | threading | 25 |  |
| tests/test_service_discovery.py | import | unittest.mock | 26 |  |
| tests/test_service_discovery.py | import | app.engine.websocket_server | 59 |  |
| tests/test_session_tree.py | import | os | 1 |  |
| tests/test_session_tree.py | import | sys | 2 |  |
| tests/test_session_tree.py | import | app.utils.session_tree | 6 |  |
| tests/test_speculative_decoding.py | import | __future__ | 3 |  |
| tests/test_speculative_decoding.py | import | pathlib | 5 |  |
| tests/test_speculative_decoding.py | import | app.engine | 9 |  |
| tests/test_speculative_decoding.py | import | app.engine | 34 |  |
| tests/test_swarm.py | import | tests.qt_test_helper  # noqa: F401 | 8 |  |
| tests/test_swarm.py | import | os | 10 |  |
| tests/test_swarm.py | import | sys | 11 |  |
| tests/test_swarm.py | import | json | 12 |  |
| tests/test_swarm.py | import | tempfile | 13 |  |
| tests/test_swarm.py | import | unittest | 14 |  |
| tests/test_swarm.py | import | unittest.mock | 15 |  |
| tests/test_swarm.py | import | app.engine.swarm_orchestrator | 17 |  |
| tests/test_task_supervisor.py | import | __future__ | 3 |  |
| tests/test_task_supervisor.py | import | time | 5 |  |
| tests/test_task_supervisor.py | import | threading | 6 |  |
| tests/test_task_supervisor.py | import | unittest | 7 |  |
| tests/test_task_supervisor.py | import | app.engine.task_supervisor | 9 |  |
| tests/test_task_supervisor.py | import | app.engine.model_loader | 336 |  |
| tests/test_task_supervisor.py | import | app.engine.model_loader | 349 |  |
| tests/test_technical_guards.py | import | tests.qt_test_helper  # noqa: F401 | 8 |  |
| tests/test_technical_guards.py | import | os | 10 |  |
| tests/test_technical_guards.py | import | sys | 11 |  |
| tests/test_technical_guards.py | import | json | 12 |  |
| tests/test_technical_guards.py | import | importlib.util | 13 |  |
| tests/test_technical_guards.py | import | tempfile | 14 |  |
| tests/test_technical_guards.py | import | unittest | 15 |  |
| tests/test_technical_guards.py | import | shutil | 16 |  |
| tests/test_technical_guards.py | import | unittest.mock | 17 |  |
| tests/test_technical_guards.py | import | PyQt6.QtCore | 19 |  |
| tests/test_technical_guards.py | import | app.engine.hot_reload | 20 |  |
| tests/test_technical_guards.py | import | app.engine.model_loader | 21 |  |
| tests/test_technical_guards.py | import | app.engine.llm_thread | 22 |  |
| tests/test_technical_guards.py | import | app.utils.codebase_search | 23 |  |
| tests/test_technical_guards.py | import | app.engine.swarm_agents | 24 |  |
| tests/test_technical_guards.py | import | app.engine.swarm_orchestrator | 25 |  |
| tests/test_technical_guards.py | import | app.utils.keychain_manager | 262 |  |
| tests/test_technical_guards.py | import | ctypes | 263 |  |
| tests/test_technical_guards.py | import | errno | 264 |  |
| tests/test_technical_guards.py | import | time | 265 |  |
| tests/test_token_lifecycle.py | import | __future__ | 18 |  |
| tests/test_token_lifecycle.py | import | asyncio | 20 |  |
| tests/test_token_lifecycle.py | import | json | 21 |  |
| tests/test_token_lifecycle.py | import | time | 22 |  |
| tests/test_token_lifecycle.py | import | unittest.mock | 23 |  |
| tests/test_token_lifecycle.py | import | websockets | 25 |  |
| tests/test_token_lifecycle.py | import | websockets.exceptions | 26 |  |
| tests/test_token_lifecycle.py | import | pytest | 27 |  |
| tests/test_token_lifecycle.py | import | app.engine.websocket_server | 60 |  |
| tests/test_token_lifecycle.py | import | pathlib | 256 |  |
| tests/test_trace_logger.py | import | gc | 1 |  |
| tests/test_trace_logger.py | import | gzip | 2 |  |
| tests/test_trace_logger.py | import | os | 3 |  |
| tests/test_trace_logger.py | import | sys | 4 |  |
| tests/test_trace_logger.py | import | json | 5 |  |
| tests/test_trace_logger.py | import | shutil | 6 |  |
| tests/test_trace_logger.py | import | tempfile | 7 |  |
| tests/test_trace_logger.py | import | unittest.mock | 8 |  |
| tests/test_trace_logger.py | import | pytest | 10 |  |
| tests/test_trace_logger.py | import | app.utils.trace_logger as tl | 14 |  |
| tests/test_trace_logger.py | import | app.utils.trace_logger | 15 |  |
| tests/test_trace_logger.py | import | time | 131 |  |
| tests/test_trace_logger.py | import | unittest.mock | 132 |  |
| tests/test_training_curator.py | import | os | 1 |  |
| tests/test_training_curator.py | import | sys | 2 |  |
| tests/test_training_curator.py | import | json | 3 |  |
| tests/test_training_curator.py | import | shutil | 4 |  |
| tests/test_training_curator.py | import | tempfile | 5 |  |
| tests/test_training_curator.py | import | app.utils.training_curator as tc | 9 |  |
| tests/test_training_curator.py | import | app.utils.training_curator | 10 |  |
| tests/test_ui_drag_drop.py | import | os | 1 |  |
| tests/test_ui_drag_drop.py | import | sys | 2 |  |
| tests/test_ui_drag_drop.py | import | PyQt6.QtCore | 3 |  |
| tests/test_ui_drag_drop.py | import | tests.qt_test_helper  # Ensures global QApplication runs headlessly | 7 |  |
| tests/test_ui_drag_drop.py | import | app.ui.workspaces.knowledge_base | 8 |  |
| tests/test_ui_drag_drop.py | import | app.ui.workspaces.training_studio.dataset_tab | 9 |  |
| tests/test_ui_drag_drop.py | import | tempfile | 72 |  |
| tests/test_ui_improvements.py | import | os | 1 |  |
| tests/test_ui_improvements.py | import | sys | 2 |  |
| tests/test_ui_improvements.py | import | tempfile | 3 |  |
| tests/test_ui_improvements.py | import | unittest | 4 |  |
| tests/test_ui_improvements.py | import | tests.qt_test_helper  # noqa: F401 | 5 |  |
| tests/test_ui_improvements.py | import | pytest | 6 |  |
| tests/test_ui_improvements.py | import | app.ui.themes | 12 |  |
| tests/test_ui_improvements.py | import | app.ui.themes | 22 |  |
| tests/test_ui_improvements.py | import | tests.conftest | 44 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.docs_data | 48 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.docs | 49 |  |
| tests/test_ui_improvements.py | import | app.state | 50 |  |
| tests/test_ui_improvements.py | import | app.state | 85 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.workbench | 86 |  |
| tests/test_ui_improvements.py | import | PyQt6.QtWidgets | 87 |  |
| tests/test_ui_improvements.py | import | app.state | 107 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.swarm_studio | 108 |  |
| tests/test_ui_improvements.py | import | app.state | 119 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.workbench | 120 |  |
| tests/test_ui_improvements.py | import | app.utils.memory_manager | 121 |  |
| tests/test_ui_improvements.py | import | app.state | 154 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.system_config | 155 |  |
| tests/test_ui_improvements.py | import | tests.conftest | 189 |  |
| tests/test_ui_improvements.py | import | app.state | 193 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.docs | 194 |  |
| tests/test_ui_improvements.py | import | app.ui.workspaces.workbench | 195 |  |
| tests/test_ui_improvements.py | import | tempfile | 196 |  |
| tests/test_ui_improvements.py | import | shutil | 197 |  |
| tests/test_ui_improvements.py | import | app.utils.rag_pipeline | 203 |  |
| tests/test_ui_improvements.py | import | PyQt6.QtWidgets | 243 |  |
| tests/test_vision_analyzer.py | import | os | 1 |  |
| tests/test_vision_analyzer.py | import | sys | 2 |  |
| tests/test_vision_analyzer.py | import | PyQt6.QtGui | 6 |  |
| tests/test_vision_analyzer.py | import | app.vision.image_store | 8 |  |
| tests/test_vision_analyzer.py | import | app.vision.schemas | 9 |  |
| tests/test_vision_analyzer.py | import | app.vision.vision_analyzer | 10 |  |
| tests/test_vision_model_loader.py | import | os | 1 |  |
| tests/test_vision_model_loader.py | import | sys | 2 |  |
| tests/test_vision_model_loader.py | import | app.vision.vision_model_loader | 6 |  |
| tests/test_vision_workbench.py | import | os | 1 |  |
| tests/test_vision_workbench.py | import | sys | 2 |  |
| tests/test_vision_workbench.py | import | PyQt6.QtGui | 6 |  |
| tests/test_vision_workbench.py | import | PyQt6.QtCore | 7 |  |
| tests/test_vision_workbench.py | import | app.state | 9 |  |
| tests/test_vision_workbench.py | import | app.ui.workspaces.vision_workbench | 10 |  |
| tests/test_watchdog.py | import | os | 1 |  |
| tests/test_watchdog.py | import | time | 2 |  |
| tests/test_watchdog.py | import | types | 3 |  |
| tests/test_watchdog.py | import | pytest | 5 |  |
| tests/test_watchdog.py | import | PyQt6.QtCore | 6 |  |
| tests/test_watchdog.py | import | PyQt6.QtWidgets | 7 |  |
| tests/test_watchdog.py | import | app.engine.llm_thread | 12 |  |
| tests/test_watchdog.py | import | app.engine.model_loader | 13 |  |
| tests/test_watchdog.py | import | app.engine.llm_thread as llm_thread | 14 |  |
| tests/test_watchdog.py | import | app.engine.agentic_thread | 89 |  |
| tests/test_watchdog.py | import | app.utils.memory_manager | 132 |  |
| tests/test_watchdog.py | import | app.utils.session_tree | 133 |  |
| tests/test_watchdog.py | import | app.ui.main_window as main_window | 134 |  |
| tests/test_websocket_bridge.py | import | tests.qt_test_helper  # noqa: F401 | 8 |  |
| tests/test_websocket_bridge.py | import | os | 10 |  |
| tests/test_websocket_bridge.py | import | sys | 11 |  |
| tests/test_websocket_bridge.py | import | json | 12 |  |
| tests/test_websocket_bridge.py | import | tempfile | 13 |  |
| tests/test_websocket_bridge.py | import | asyncio | 14 |  |
| tests/test_websocket_bridge.py | import | time | 15 |  |
| tests/test_websocket_bridge.py | import | unittest | 16 |  |
| tests/test_websocket_bridge.py | import | unittest.mock | 17 |  |
| tests/test_websocket_bridge.py | import | websockets | 19 |  |
| tests/test_websocket_bridge.py | import | pytest | 20 |  |
| tests/test_websocket_bridge.py | import | PyQt6.QtCore | 21 |  |
| tests/test_websocket_bridge.py | import | app.engine.websocket_server | 22 |  |
| tests/test_websocket_bridge.py | import | ssl | 113 |  |
| tests/test_websocket_bridge.py | import | app.ui.widgets.status_bar | 507 |  |
| tests/test_websocket_bridge.py | import | websockets.exceptions | 551 |  |
| tests/test_websocket_bridge.py | import | websockets.exceptions | 588 |  |
| tests/test_websocket_contract.py | import | asyncio | 1 |  |
| tests/test_websocket_contract.py | import | json | 2 |  |
| tests/test_websocket_contract.py | import | threading | 3 |  |
| tests/test_websocket_contract.py | import | tests.qt_test_helper  # noqa: F401 | 5 |  |
| tests/test_websocket_contract.py | import | app.engine.websocket_server | 7 |  |
| tools/conversion/__init__.py | import | __future__ | 1 |  |
| tools/conversion/__init__.py | import | .base | 3 |  |
| tools/conversion/__init__.py | import | typing | 8 |  |
| tools/conversion/afmoe.py | import | __future__ | 1 |  |
| tools/conversion/afmoe.py | import | typing | 3 |  |
| tools/conversion/afmoe.py | import | torch | 5 |  |
| tools/conversion/afmoe.py | import | torch | 8 |  |
| tools/conversion/afmoe.py | import | .base | 10 |  |
| tools/conversion/afmoe.py | import | .llama | 12 |  |
| tools/conversion/arctic.py | import | __future__ | 1 |  |
| tools/conversion/arctic.py | import | json | 3 |  |
| tools/conversion/arctic.py | import | sys | 4 |  |
| tools/conversion/arctic.py | import | typing | 6 |  |
| tools/conversion/arctic.py | import | torch | 8 |  |
| tools/conversion/arctic.py | import | torch | 11 |  |
| tools/conversion/arctic.py | import | .base | 13 |  |
| tools/conversion/arctic.py | import | .llama | 15 |  |
| tools/conversion/arctic.py | import | sentencepiece | 26 |  |
| tools/conversion/baichuan.py | import | __future__ | 1 |  |
| tools/conversion/baichuan.py | import | typing | 3 |  |
| tools/conversion/baichuan.py | import | torch | 6 |  |
| tools/conversion/baichuan.py | import | .base | 8 |  |
| tools/conversion/bailingmoe.py | import | __future__ | 1 |  |
| tools/conversion/bailingmoe.py | import | typing | 3 |  |
| tools/conversion/bailingmoe.py | import | torch | 5 |  |
| tools/conversion/bailingmoe.py | import | torch | 8 |  |
| tools/conversion/bailingmoe.py | import | .base | 10 |  |
| tools/conversion/base.py | import | __future__ | 4 |  |
| tools/conversion/base.py | import | ast | 6 |  |
| tools/conversion/base.py | import | logging | 7 |  |
| tools/conversion/base.py | import | contextlib | 8 |  |
| tools/conversion/base.py | import | json | 9 |  |
| tools/conversion/base.py | import | os | 10 |  |
| tools/conversion/base.py | import | re | 11 |  |
| tools/conversion/base.py | import | sys | 12 |  |
| tools/conversion/base.py | import | enum | 13 |  |
| tools/conversion/base.py | import | pathlib | 14 |  |
| tools/conversion/base.py | import | hashlib | 15 |  |
| tools/conversion/base.py | import | typing | 16 |  |
| tools/conversion/base.py | import | itertools | 17 |  |
| tools/conversion/base.py | import | transformers | 18 |  |
| tools/conversion/base.py | import | numpy as np | 20 |  |
| tools/conversion/base.py | import | torch | 21 |  |
| tools/conversion/base.py | import | torch | 24 |  |
| tools/conversion/base.py | import | gguf | 28 |  |
| tools/conversion/base.py | import | gguf.vocab | 29 |  |
| tools/conversion/base.py | import | mistral_common.tokens.tokenizers.base | 32 |  |
| tools/conversion/base.py | import | mistral_common.tokens.tokenizers.multimodal | 33 |  |
| tools/conversion/base.py | import | mistral_common.tokens.tokenizers.tekken | 34 |  |
| tools/conversion/base.py | import | mistral_common.tokens.tokenizers.sentencepiece | 35 |  |
| tools/conversion/base.py | import | transformers | 1333 |  |
| tools/conversion/base.py | import | transformers | 1696 |  |
| tools/conversion/base.py | import | .qwen | 1737 |  |
| tools/conversion/base.py | import | transformers | 1744 |  |
| tools/conversion/base.py | import | sentencepiece | 1805 |  |
| tools/conversion/base.py | import | transformers | 2041 |  |
| tools/conversion/base.py | import | transformers | 2056 |  |
| tools/conversion/base.py | import | transformers | 2076 |  |
| tools/conversion/base.py | import | .mistral | 2122 |  |
| tools/conversion/base.py | import | copy | 2314 |  |
| tools/conversion/bert.py | import | __future__ | 1 |  |
| tools/conversion/bert.py | import | json | 3 |  |
| tools/conversion/bert.py | import | os | 4 |  |
| tools/conversion/bert.py | import | pathlib | 6 |  |
| tools/conversion/bert.py | import | typing | 7 |  |
| tools/conversion/bert.py | import | torch | 9 |  |
| tools/conversion/bert.py | import | torch | 12 |  |
| tools/conversion/bert.py | import | .base | 14 |  |
| tools/conversion/bert.py | import | sentencepiece | 117 |  |
| tools/conversion/bert.py | import | sentencepiece | 118 |  |
| tools/conversion/bert.py | import | base64 | 131 |  |
| tools/conversion/bert.py | import | transformers | 132 |  |
| tools/conversion/bitnet.py | import | __future__ | 1 |  |
| tools/conversion/bitnet.py | import | typing | 3 |  |
| tools/conversion/bitnet.py | import | torch | 6 |  |
| tools/conversion/bitnet.py | import | .base | 8 |  |
| tools/conversion/bloom.py | import | __future__ | 1 |  |
| tools/conversion/bloom.py | import | re | 3 |  |
| tools/conversion/bloom.py | import | typing | 5 |  |
| tools/conversion/bloom.py | import | torch | 7 |  |
| tools/conversion/bloom.py | import | torch | 10 |  |
| tools/conversion/bloom.py | import | .base | 12 |  |
| tools/conversion/chameleon.py | import | __future__ | 1 |  |
| tools/conversion/chameleon.py | import | typing | 3 |  |
| tools/conversion/chameleon.py | import | torch | 6 |  |
| tools/conversion/chameleon.py | import | .base | 8 |  |
| tools/conversion/chameleon.py | import | .llama | 10 |  |
| tools/conversion/chatglm.py | import | __future__ | 1 |  |
| tools/conversion/chatglm.py | import | typing | 3 |  |
| tools/conversion/chatglm.py | import | torch | 6 |  |
| tools/conversion/chatglm.py | import | .base | 8 |  |
| tools/conversion/chatglm.py | import | transformers | 22 |  |
| tools/conversion/chatglm.py | import | transformers.models.gpt2.tokenization_gpt2 | 84 |  |
| tools/conversion/chatglm.py | import | transformers | 115 |  |
| tools/conversion/codeshell.py | import | __future__ | 1 |  |
| tools/conversion/codeshell.py | import | .base | 3 |  |
| tools/conversion/cogvlm.py | import | __future__ | 1 |  |
| tools/conversion/cogvlm.py | import | typing | 3 |  |
| tools/conversion/cogvlm.py | import | torch | 6 |  |
| tools/conversion/cogvlm.py | import | .base | 8 |  |
| tools/conversion/cogvlm.py | import | .llama | 10 |  |
| tools/conversion/command_r.py | import | __future__ | 1 |  |
| tools/conversion/command_r.py | import | typing | 3 |  |
| tools/conversion/command_r.py | import | torch | 5 |  |
| tools/conversion/command_r.py | import | torch | 8 |  |
| tools/conversion/command_r.py | import | .base | 10 |  |
| tools/conversion/dbrx.py | import | __future__ | 1 |  |
| tools/conversion/dbrx.py | import | typing | 3 |  |
| tools/conversion/dbrx.py | import | torch | 6 |  |
| tools/conversion/dbrx.py | import | .base | 8 |  |
| tools/conversion/deci.py | import | __future__ | 1 |  |
| tools/conversion/deci.py | import | math | 3 |  |
| tools/conversion/deci.py | import | typing | 5 |  |
| tools/conversion/deci.py | import | torch | 7 |  |
| tools/conversion/deci.py | import | torch | 10 |  |
| tools/conversion/deci.py | import | .base | 12 |  |
| tools/conversion/deepseek.py | import | __future__ | 1 |  |
| tools/conversion/deepseek.py | import | re | 3 |  |
| tools/conversion/deepseek.py | import | typing | 5 |  |
| tools/conversion/deepseek.py | import | torch | 7 |  |
| tools/conversion/deepseek.py | import | torch | 10 |  |
| tools/conversion/deepseek.py | import | .base | 12 |  |
| tools/conversion/deepseek.py | import | .qwen | 14 |  |
| tools/conversion/deepseek.py | import | transformers | 249 |  |
| tools/conversion/deepseek.py | import | transformers | 446 |  |
| tools/conversion/dots1.py | import | __future__ | 1 |  |
| tools/conversion/dots1.py | import | typing | 3 |  |
| tools/conversion/dots1.py | import | torch | 6 |  |
| tools/conversion/dots1.py | import | .base | 8 |  |
| tools/conversion/dots1.py | import | .qwen | 10 |  |
| tools/conversion/dotsocr.py | import | __future__ | 1 |  |
| tools/conversion/dotsocr.py | import | typing | 3 |  |
| tools/conversion/dotsocr.py | import | torch | 6 |  |
| tools/conversion/dotsocr.py | import | .base | 8 |  |
| tools/conversion/dream.py | import | __future__ | 1 |  |
| tools/conversion/dream.py | import | typing | 3 |  |
| tools/conversion/dream.py | import | torch | 6 |  |
| tools/conversion/dream.py | import | .base | 8 |  |
| tools/conversion/dream.py | import | transformers | 19 |  |
| tools/conversion/ernie.py | import | __future__ | 1 |  |
| tools/conversion/ernie.py | import | json | 3 |  |
| tools/conversion/ernie.py | import | math | 4 |  |
| tools/conversion/ernie.py | import | re | 5 |  |
| tools/conversion/ernie.py | import | typing | 7 |  |
| tools/conversion/ernie.py | import | torch | 9 |  |
| tools/conversion/ernie.py | import | torch | 12 |  |
| tools/conversion/ernie.py | import | .base | 14 |  |
| tools/conversion/exaone.py | import | __future__ | 1 |  |
| tools/conversion/exaone.py | import | math | 3 |  |
| tools/conversion/exaone.py | import | pathlib | 5 |  |
| tools/conversion/exaone.py | import | typing | 6 |  |
| tools/conversion/exaone.py | import | torch | 8 |  |
| tools/conversion/exaone.py | import | torch | 11 |  |
| tools/conversion/exaone.py | import | .base | 13 |  |
| tools/conversion/falcon.py | import | __future__ | 1 |  |
| tools/conversion/falcon.py | import | typing | 3 |  |
| tools/conversion/falcon.py | import | torch | 5 |  |
| tools/conversion/falcon.py | import | torch | 8 |  |
| tools/conversion/falcon.py | import | .base | 10 |  |
| tools/conversion/falcon_h1.py | import | __future__ | 1 |  |
| tools/conversion/falcon_h1.py | import | typing | 3 |  |
| tools/conversion/falcon_h1.py | import | torch | 6 |  |
| tools/conversion/falcon_h1.py | import | .base | 8 |  |
| tools/conversion/falcon_h1.py | import | .llama | 10 |  |
| tools/conversion/falcon_h1.py | import | .mamba | 11 |  |
| tools/conversion/gemma.py | import | __future__ | 1 |  |
| tools/conversion/gemma.py | import | json | 3 |  |
| tools/conversion/gemma.py | import | re | 4 |  |
| tools/conversion/gemma.py | import | typing | 6 |  |
| tools/conversion/gemma.py | import | torch | 8 |  |
| tools/conversion/gemma.py | import | torch | 11 |  |
| tools/conversion/gemma.py | import | .base | 13 |  |
| tools/conversion/gemma.py | import | safetensors.torch | 208 |  |
| tools/conversion/glm.py | import | __future__ | 1 |  |
| tools/conversion/glm.py | import | typing | 3 |  |
| tools/conversion/glm.py | import | torch | 5 |  |
| tools/conversion/glm.py | import | torch | 8 |  |
| tools/conversion/glm.py | import | .base | 10 |  |
| tools/conversion/glm.py | import | .deepseek | 12 |  |
| tools/conversion/glm.py | import | transformers | 29 |  |
| tools/conversion/glm.py | import | transformers | 247 |  |
| tools/conversion/gpt2.py | import | __future__ | 1 |  |
| tools/conversion/gpt2.py | import | typing | 3 |  |
| tools/conversion/gpt2.py | import | torch | 5 |  |
| tools/conversion/gpt2.py | import | torch | 8 |  |
| tools/conversion/gpt2.py | import | .base | 10 |  |
| tools/conversion/gpt_oss.py | import | __future__ | 1 |  |
| tools/conversion/gpt_oss.py | import | typing | 3 |  |
| tools/conversion/gpt_oss.py | import | torch | 5 |  |
| tools/conversion/gpt_oss.py | import | torch | 8 |  |
| tools/conversion/gpt_oss.py | import | .base | 10 |  |
| tools/conversion/gptneox.py | import | __future__ | 1 |  |
| tools/conversion/gptneox.py | import | re | 3 |  |
| tools/conversion/gptneox.py | import | typing | 5 |  |
| tools/conversion/gptneox.py | import | torch | 7 |  |
| tools/conversion/gptneox.py | import | torch | 10 |  |
| tools/conversion/gptneox.py | import | .base | 12 |  |
| tools/conversion/granite.py | import | __future__ | 1 |  |
| tools/conversion/granite.py | import | typing | 3 |  |
| tools/conversion/granite.py | import | torch | 5 |  |
| tools/conversion/granite.py | import | torch | 8 |  |
| tools/conversion/granite.py | import | .base | 10 |  |
| tools/conversion/granite.py | import | .llama | 12 |  |
| tools/conversion/granite.py | import | .mamba | 13 |  |
| tools/conversion/grok.py | import | __future__ | 1 |  |
| tools/conversion/grok.py | import | sys | 3 |  |
| tools/conversion/grok.py | import | typing | 5 |  |
| tools/conversion/grok.py | import | torch | 7 |  |
| tools/conversion/grok.py | import | torch | 10 |  |
| tools/conversion/grok.py | import | .base | 12 |  |
| tools/conversion/grovemoe.py | import | __future__ | 1 |  |
| tools/conversion/grovemoe.py | import | typing | 3 |  |
| tools/conversion/grovemoe.py | import | torch | 5 |  |
| tools/conversion/grovemoe.py | import | torch | 8 |  |
| tools/conversion/grovemoe.py | import | .base | 10 |  |
| tools/conversion/hunyuan.py | import | __future__ | 1 |  |
| tools/conversion/hunyuan.py | import | json | 3 |  |
| tools/conversion/hunyuan.py | import | pathlib | 5 |  |
| tools/conversion/hunyuan.py | import | typing | 6 |  |
| tools/conversion/hunyuan.py | import | torch | 8 |  |
| tools/conversion/hunyuan.py | import | torch | 11 |  |
| tools/conversion/hunyuan.py | import | .base | 13 |  |
| tools/conversion/hunyuan.py | import | .qwen | 15 |  |
| tools/conversion/hunyuan.py | import | transformers | 23 |  |
| tools/conversion/hunyuan.py | import | transformers | 201 |  |
| tools/conversion/internlm.py | import | __future__ | 1 |  |
| tools/conversion/internlm.py | import | json | 3 |  |
| tools/conversion/internlm.py | import | sys | 4 |  |
| tools/conversion/internlm.py | import | typing | 6 |  |
| tools/conversion/internlm.py | import | torch | 9 |  |
| tools/conversion/internlm.py | import | .base | 11 |  |
| tools/conversion/internlm.py | import | .llama | 13 |  |
| tools/conversion/internlm.py | import | sentencepiece | 25 |  |
| tools/conversion/internlm.py | import | sentencepiece | 26 |  |
| tools/conversion/internvl.py | import | __future__ | 1 |  |
| tools/conversion/internvl.py | import | typing | 3 |  |
| tools/conversion/internvl.py | import | torch | 6 |  |
| tools/conversion/internvl.py | import | .base | 8 |  |
| tools/conversion/jais.py | import | __future__ | 1 |  |
| tools/conversion/jais.py | import | math | 3 |  |
| tools/conversion/jais.py | import | typing | 5 |  |
| tools/conversion/jais.py | import | torch | 8 |  |
| tools/conversion/jais.py | import | .base | 10 |  |
| tools/conversion/jamba.py | import | __future__ | 1 |  |
| tools/conversion/jamba.py | import | typing | 3 |  |
| tools/conversion/jamba.py | import | torch | 5 |  |
| tools/conversion/jamba.py | import | torch | 8 |  |
| tools/conversion/jamba.py | import | .base | 10 |  |
| tools/conversion/januspro.py | import | __future__ | 1 |  |
| tools/conversion/januspro.py | import | typing | 3 |  |
| tools/conversion/januspro.py | import | torch | 6 |  |
| tools/conversion/januspro.py | import | .base | 8 |  |
| tools/conversion/januspro.py | import | .llama | 10 |  |
| tools/conversion/kimi_linear.py | import | __future__ | 1 |  |
| tools/conversion/kimi_linear.py | import | typing | 3 |  |
| tools/conversion/kimi_linear.py | import | torch | 5 |  |
| tools/conversion/kimi_linear.py | import | torch | 8 |  |
| tools/conversion/kimi_linear.py | import | .base | 10 |  |
| tools/conversion/kimi_linear.py | import | .qwen | 12 |  |
| tools/conversion/kimi_linear.py | import | transformers | 29 |  |
| tools/conversion/kimivl.py | import | __future__ | 1 |  |
| tools/conversion/kimivl.py | import | typing | 3 |  |
| tools/conversion/kimivl.py | import | torch | 5 |  |
| tools/conversion/kimivl.py | import | torch | 8 |  |
| tools/conversion/kimivl.py | import | .base | 10 |  |
| tools/conversion/lfm2.py | import | __future__ | 1 |  |
| tools/conversion/lfm2.py | import | typing | 3 |  |
| tools/conversion/lfm2.py | import | torch | 5 |  |
| tools/conversion/lfm2.py | import | torch | 8 |  |
| tools/conversion/lfm2.py | import | .base | 10 |  |
| tools/conversion/lfm2.py | import | .gemma | 12 |  |
| tools/conversion/lfm2.py | import | safetensors.torch | 80 |  |
| tools/conversion/lighton_ocr.py | import | __future__ | 1 |  |
| tools/conversion/lighton_ocr.py | import | typing | 3 |  |
| tools/conversion/lighton_ocr.py | import | torch | 6 |  |
| tools/conversion/lighton_ocr.py | import | .base | 8 |  |
| tools/conversion/lighton_ocr.py | import | .llava | 10 |  |
| tools/conversion/llada.py | import | __future__ | 1 |  |
| tools/conversion/llada.py | import | typing | 3 |  |
| tools/conversion/llada.py | import | torch | 5 |  |
| tools/conversion/llada.py | import | torch | 8 |  |
| tools/conversion/llada.py | import | .base | 10 |  |
| tools/conversion/llada.py | import | transformers | 22 |  |
| tools/conversion/llama.py | import | __future__ | 1 |  |
| tools/conversion/llama.py | import | json | 3 |  |
| tools/conversion/llama.py | import | math | 4 |  |
| tools/conversion/llama.py | import | typing | 6 |  |
| tools/conversion/llama.py | import | torch | 8 |  |
| tools/conversion/llama.py | import | torch | 11 |  |
| tools/conversion/llama.py | import | .base | 13 |  |
| tools/conversion/llama4.py | import | __future__ | 1 |  |
| tools/conversion/llama4.py | import | typing | 3 |  |
| tools/conversion/llama4.py | import | torch | 6 |  |
| tools/conversion/llama4.py | import | .base | 8 |  |
| tools/conversion/llava.py | import | __future__ | 1 |  |
| tools/conversion/llava.py | import | json | 3 |  |
| tools/conversion/llava.py | import | typing | 5 |  |
| tools/conversion/llava.py | import | torch | 8 |  |
| tools/conversion/llava.py | import | .base | 10 |  |
| tools/conversion/llava.py | import | .llama | 12 |  |
| tools/conversion/maincoder.py | import | __future__ | 1 |  |
| tools/conversion/maincoder.py | import | .base | 3 |  |
| tools/conversion/mamba.py | import | __future__ | 1 |  |
| tools/conversion/mamba.py | import | json | 3 |  |
| tools/conversion/mamba.py | import | pathlib | 5 |  |
| tools/conversion/mamba.py | import | typing | 6 |  |
| tools/conversion/mamba.py | import | torch | 8 |  |
| tools/conversion/mamba.py | import | torch | 11 |  |
| tools/conversion/mamba.py | import | .base | 13 |  |
| tools/conversion/mimo.py | import | __future__ | 1 |  |
| tools/conversion/mimo.py | import | re | 3 |  |
| tools/conversion/mimo.py | import | typing | 5 |  |
| tools/conversion/mimo.py | import | torch | 7 |  |
| tools/conversion/mimo.py | import | torch | 10 |  |
| tools/conversion/mimo.py | import | .base | 12 |  |
| tools/conversion/minicpm.py | import | __future__ | 1 |  |
| tools/conversion/minicpm.py | import | typing | 3 |  |
| tools/conversion/minicpm.py | import | torch | 5 |  |
| tools/conversion/minicpm.py | import | torch | 8 |  |
| tools/conversion/minicpm.py | import | .base | 10 |  |
| tools/conversion/minicpm.py | import | .llama | 12 |  |
| tools/conversion/minicpm.py | import | .qwen | 13 |  |
| tools/conversion/minimax.py | import | __future__ | 1 |  |
| tools/conversion/minimax.py | import | typing | 3 |  |
| tools/conversion/minimax.py | import | torch | 5 |  |
| tools/conversion/minimax.py | import | torch | 8 |  |
| tools/conversion/minimax.py | import | .base | 10 |  |
| tools/conversion/mistral.py | import | __future__ | 1 |  |
| tools/conversion/mistral.py | import | pathlib | 3 |  |
| tools/conversion/mistral.py | import | typing | 4 |  |
| tools/conversion/mistral.py | import | torch | 7 |  |
| tools/conversion/mistral.py | import | .base | 9 |  |
| tools/conversion/mistral.py | import | .deepseek | 11 |  |
| tools/conversion/mistral.py | import | .llama | 12 |  |
| tools/conversion/mistral.py | import | mistral_common.tokens.tokenizers.base | 15 |  |
| tools/conversion/mistral.py | import | mistral_common.tokens.tokenizers.tekken | 16 |  |
| tools/conversion/mistral.py | import | mistral_common.tokens.tokenizers.sentencepiece | 17 |  |
| tools/conversion/mistral3.py | import | __future__ | 1 |  |
| tools/conversion/mistral3.py | import | typing | 3 |  |
| tools/conversion/mistral3.py | import | torch | 6 |  |
| tools/conversion/mistral3.py | import | .base | 8 |  |
| tools/conversion/mistral3.py | import | .deepseek | 10 |  |
| tools/conversion/mistral3.py | import | .llama | 11 |  |
| tools/conversion/mpt.py | import | __future__ | 1 |  |
| tools/conversion/mpt.py | import | typing | 3 |  |
| tools/conversion/mpt.py | import | torch | 6 |  |
| tools/conversion/mpt.py | import | .base | 8 |  |
| tools/conversion/nemotron.py | import | __future__ | 1 |  |
| tools/conversion/nemotron.py | import | typing | 3 |  |
| tools/conversion/nemotron.py | import | torch | 5 |  |
| tools/conversion/nemotron.py | import | torch | 8 |  |
| tools/conversion/nemotron.py | import | .base | 10 |  |
| tools/conversion/nemotron.py | import | .granite | 12 |  |
| tools/conversion/nemotron.py | import | torch.nn.functional as F | 85 |  |
| tools/conversion/nemotron.py | import | transformers | 251 |  |
| tools/conversion/olmo.py | import | __future__ | 1 |  |
| tools/conversion/olmo.py | import | typing | 3 |  |
| tools/conversion/olmo.py | import | torch | 5 |  |
| tools/conversion/olmo.py | import | torch | 8 |  |
| tools/conversion/olmo.py | import | .base | 10 |  |
| tools/conversion/olmo.py | import | .llama | 12 |  |
| tools/conversion/openelm.py | import | __future__ | 1 |  |
| tools/conversion/openelm.py | import | typing | 3 |  |
| tools/conversion/openelm.py | import | torch | 6 |  |
| tools/conversion/openelm.py | import | .base | 8 |  |
| tools/conversion/orion.py | import | __future__ | 1 |  |
| tools/conversion/orion.py | import | .base | 3 |  |
| tools/conversion/pangu.py | import | __future__ | 1 |  |
| tools/conversion/pangu.py | import | json | 3 |  |
| tools/conversion/pangu.py | import | typing | 5 |  |
| tools/conversion/pangu.py | import | torch | 8 |  |
| tools/conversion/pangu.py | import | .base | 10 |  |
| tools/conversion/phi.py | import | __future__ | 1 |  |
| tools/conversion/phi.py | import | json | 3 |  |
| tools/conversion/phi.py | import | math | 4 |  |
| tools/conversion/phi.py | import | typing | 6 |  |
| tools/conversion/phi.py | import | torch | 8 |  |
| tools/conversion/phi.py | import | torch | 11 |  |
| tools/conversion/phi.py | import | .base | 13 |  |
| tools/conversion/phi.py | import | sentencepiece | 52 |  |
| tools/conversion/pixtral.py | import | __future__ | 1 |  |
| tools/conversion/pixtral.py | import | typing | 3 |  |
| tools/conversion/pixtral.py | import | .base | 5 |  |
| tools/conversion/pixtral.py | import | .llava | 7 |  |
| tools/conversion/plamo.py | import | __future__ | 1 |  |
| tools/conversion/plamo.py | import | json | 3 |  |
| tools/conversion/plamo.py | import | typing | 5 |  |
| tools/conversion/plamo.py | import | torch | 7 |  |
| tools/conversion/plamo.py | import | torch | 10 |  |
| tools/conversion/plamo.py | import | .base | 12 |  |
| tools/conversion/plm.py | import | __future__ | 1 |  |
| tools/conversion/plm.py | import | .base | 3 |  |
| tools/conversion/qwen.py | import | __future__ | 1 |  |
| tools/conversion/qwen.py | import | typing | 3 |  |
| tools/conversion/qwen.py | import | torch | 5 |  |
| tools/conversion/qwen.py | import | torch | 8 |  |
| tools/conversion/qwen.py | import | .base | 10 |  |
| tools/conversion/qwen.py | import | transformers.models.gpt2.tokenization_gpt2 | 19 |  |
| tools/conversion/qwen.py | import | transformers | 205 |  |
| tools/conversion/qwen3vl.py | import | __future__ | 1 |  |
| tools/conversion/qwen3vl.py | import | json | 3 |  |
| tools/conversion/qwen3vl.py | import | typing | 5 |  |
| tools/conversion/qwen3vl.py | import | torch | 8 |  |
| tools/conversion/qwen3vl.py | import | .base | 10 |  |
| tools/conversion/qwen3vl.py | import | .qwen | 12 |  |
| tools/conversion/qwen3vl.py | import | .qwenvl | 13 |  |
| tools/conversion/qwenvl.py | import | __future__ | 1 |  |
| tools/conversion/qwenvl.py | import | typing | 3 |  |
| tools/conversion/qwenvl.py | import | numpy as np | 5 |  |
| tools/conversion/qwenvl.py | import | torch | 6 |  |
| tools/conversion/qwenvl.py | import | torch | 9 |  |
| tools/conversion/qwenvl.py | import | .base | 11 |  |
| tools/conversion/refact.py | import | __future__ | 1 |  |
| tools/conversion/refact.py | import | typing | 3 |  |
| tools/conversion/refact.py | import | torch | 6 |  |
| tools/conversion/refact.py | import | .base | 8 |  |
| tools/conversion/rwkv.py | import | __future__ | 1 |  |
| tools/conversion/rwkv.py | import | typing | 3 |  |
| tools/conversion/rwkv.py | import | torch | 5 |  |
| tools/conversion/rwkv.py | import | torch | 8 |  |
| tools/conversion/rwkv.py | import | .base | 10 |  |
| tools/conversion/sarashina2.py | import | __future__ | 1 |  |
| tools/conversion/sarashina2.py | import | typing | 3 |  |
| tools/conversion/sarashina2.py | import | torch | 6 |  |
| tools/conversion/sarashina2.py | import | .base | 8 |  |
| tools/conversion/sarashina2.py | import | .llama | 10 |  |
| tools/conversion/sarashina2.py | import | .qwenvl | 11 |  |
| tools/conversion/smallthinker.py | import | __future__ | 1 |  |
| tools/conversion/smallthinker.py | import | typing | 3 |  |
| tools/conversion/smallthinker.py | import | torch | 5 |  |
| tools/conversion/smallthinker.py | import | torch | 8 |  |
| tools/conversion/smallthinker.py | import | .base | 10 |  |
| tools/conversion/smolvlm.py | import | __future__ | 1 |  |
| tools/conversion/smolvlm.py | import | typing | 3 |  |
| tools/conversion/smolvlm.py | import | torch | 6 |  |
| tools/conversion/smolvlm.py | import | .base | 8 |  |
| tools/conversion/stablelm.py | import | __future__ | 1 |  |
| tools/conversion/stablelm.py | import | typing | 3 |  |
| tools/conversion/stablelm.py | import | torch | 5 |  |
| tools/conversion/stablelm.py | import | torch | 8 |  |
| tools/conversion/stablelm.py | import | .base | 10 |  |
| tools/conversion/starcoder.py | import | __future__ | 1 |  |
| tools/conversion/starcoder.py | import | .base | 3 |  |
| tools/conversion/step3.py | import | __future__ | 1 |  |
| tools/conversion/step3.py | import | math | 3 |  |
| tools/conversion/step3.py | import | re | 4 |  |
| tools/conversion/step3.py | import | typing | 6 |  |
| tools/conversion/step3.py | import | torch | 8 |  |
| tools/conversion/step3.py | import | torch | 11 |  |
| tools/conversion/step3.py | import | .base | 13 |  |
| tools/conversion/step3.py | import | .qwen | 15 |  |
| tools/conversion/t5.py | import | __future__ | 1 |  |
| tools/conversion/t5.py | import | json | 3 |  |
| tools/conversion/t5.py | import | os | 4 |  |
| tools/conversion/t5.py | import | typing | 6 |  |
| tools/conversion/t5.py | import | torch | 9 |  |
| tools/conversion/t5.py | import | .base | 11 |  |
| tools/conversion/t5.py | import | sentencepiece | 30 |  |
| tools/conversion/t5.py | import | sentencepiece | 31 |  |
| tools/conversion/t5.py | import | sentencepiece | 167 |  |
| tools/conversion/t5.py | import | sentencepiece | 168 |  |
| tools/conversion/talkie.py | import | __future__ | 1 |  |
| tools/conversion/talkie.py | import | typing | 3 |  |
| tools/conversion/talkie.py | import | torch | 5 |  |
| tools/conversion/talkie.py | import | torch | 8 |  |
| tools/conversion/talkie.py | import | .base | 10 |  |
| tools/conversion/ultravox.py | import | __future__ | 1 |  |
| tools/conversion/ultravox.py | import | typing | 3 |  |
| tools/conversion/ultravox.py | import | torch | 6 |  |
| tools/conversion/ultravox.py | import | .base | 8 |  |
| tools/conversion/wavtokenizer.py | import | __future__ | 1 |  |
| tools/conversion/wavtokenizer.py | import | typing | 3 |  |
| tools/conversion/wavtokenizer.py | import | torch | 6 |  |
| tools/conversion/wavtokenizer.py | import | .base | 8 |  |
| tools/conversion/xverse.py | import | __future__ | 1 |  |
| tools/conversion/xverse.py | import | re | 3 |  |
| tools/conversion/xverse.py | import | typing | 5 |  |
| tools/conversion/xverse.py | import | torch | 8 |  |
| tools/conversion/xverse.py | import | .base | 10 |  |
| tools/conversion/xverse.py | import | transformers | 25 |  |
| tools/conversion/youtuvl.py | import | __future__ | 1 |  |
| tools/conversion/youtuvl.py | import | typing | 3 |  |
| tools/conversion/youtuvl.py | import | torch | 6 |  |
| tools/conversion/youtuvl.py | import | .base | 8 |  |
| tools/decrypt_logs.py | import | os | 12 |  |
| tools/decrypt_logs.py | import | sys | 13 |  |
| tools/decrypt_logs.py | import | json | 14 |  |
| tools/decrypt_logs.py | import | gzip | 15 |  |
| tools/decrypt_logs.py | import | base64 | 16 |  |
| tools/decrypt_logs.py | import | hashlib | 17 |  |
| tools/decrypt_logs.py | import | shutil | 18 |  |
| tools/decrypt_logs.py | import | argparse | 19 |  |
| tools/decrypt_logs.py | import | getpass | 20 |  |
| tools/decrypt_logs.py | import | platform | 21 |  |
| tools/decrypt_logs.py | import | ctypes | 22 |  |
| tools/decrypt_logs.py | import | psutil | 40 |  |
| tools/decrypt_logs.py | import | cryptography.fernet | 41 |  |
| tools/decrypt_logs.py | import | core.hardware_scout | 42 |  |
| tools/decrypt_logs.py | import | app.utils.keychain_manager | 43 |  |
| tools/decrypt_logs.py | import | core.hardware_scout | 52 |  |
| training/validate_dataset.py | import | json | 27 |  |
| training/validate_dataset.py | import | os | 28 |  |
| training/validate_dataset.py | import | shutil | 29 |  |
| training/validate_dataset.py | import | sys | 30 |  |
| training/validate_dataset.py | import | argparse | 31 |  |
| training/validate_dataset.py | import | collections | 32 |  |
| training/validate_dataset.py | import | app.engine.model_loader | 53 |  |
| training/validate_dataset.py | import | stat | 675 |  |
| vscode-extension/extension.js | import | os | 329 |  |
| vscode-extension/extension.js | import | sys | 330 |  |
| vscode-extension/extension.js | import | json | 331 |  |
| vscode-extension/extension.js | import | torch | 332 |  |

## 8. Setup Guess

- `pip install .`
- `python -m pip install -r requirements.txt`
- `python main.py`

## 9. Plain-English Explanation

This project appears to use Docker + Python + pyproject. Start with the entry points above, then read the important files and top-level folders in order.

## 10. Risky/Confusing Areas

- .mypy_cache/3.12/cache.0.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.1.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.10.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.11.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.12.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.13.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.14.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.15.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.2.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.3.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.4.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.5.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.6.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.7.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.8.db was skipped (max_file_size).
- .mypy_cache/3.12/cache.9.db was skipped (max_file_size).
- .ruff_cache/0.15.20/11151240506088214560 was skipped (binary).
- .ruff_cache/0.15.20/11173252355182146283 was skipped (binary).
- .ruff_cache/0.15.20/1146293954944627483 was skipped (binary).
- .ruff_cache/0.15.20/11972510000338431888 was skipped (binary).
- .ruff_cache/0.15.20/12559792250607600041 was skipped (binary).
- .ruff_cache/0.15.20/12946477700982431300 was skipped (binary).
- .ruff_cache/0.15.20/13842709862046631274 was skipped (binary).
- .ruff_cache/0.15.20/14772501875134088261 was skipped (binary).
- .ruff_cache/0.15.20/15989267376014901249 was skipped (binary).
- .ruff_cache/0.15.20/16549907356470524752 was skipped (binary).
- .ruff_cache/0.15.20/1655524104183051972 was skipped (binary).
- .ruff_cache/0.15.20/17826862415051225304 was skipped (binary).
- .ruff_cache/0.15.20/17857341297625773064 was skipped (binary).
- .ruff_cache/0.15.20/3279835033448734532 was skipped (binary).
- .ruff_cache/0.15.20/3528976186452572868 was skipped (binary).
- .ruff_cache/0.15.20/3615129933027466828 was skipped (binary).
- .ruff_cache/0.15.20/4439090111566271517 was skipped (binary).
- .ruff_cache/0.15.20/5426070964058543367 was skipped (binary).
- .ruff_cache/0.15.20/5575495544498376754 was skipped (binary).
- .ruff_cache/0.15.20/6257482547299503717 was skipped (binary).
- .ruff_cache/0.15.20/6451091466542286850 was skipped (binary).
- .ruff_cache/0.15.20/798352014734019942 was skipped (binary).
- .ruff_cache/0.15.20/8058556805231193550 was skipped (binary).
- .ruff_cache/0.15.20/9641372726687176821 was skipped (binary).

## 11. AI-Assisted Summaries

*AI summaries disabled or unavailable. Run with --llm flag to generate.*

## Scanner Inventory

| Path | Language | Lines | Bytes | Status |
|---|---:|---:|---:|---|
| .claude/settings.local.json | JSON | 25 | 1012 | ok |
| .dockerignore | Unknown | 45 | 436 | ok |
| .github/workflows/ci.yml | YAML | 63 | 1607 | ok |
| .github/workflows/release.yml | YAML | 78 | 2228 | ok |
| .gitignore | Unknown | 58 | 1078 | ok |
| .mypy_cache/.gitignore | Unknown | 2 | 34 | ok |
| .mypy_cache/3.12/cache.0.db | Unknown | 0 | 6135808 | skipped: max_file_size |
| .mypy_cache/3.12/cache.1.db | Unknown | 0 | 6684672 | skipped: max_file_size |
| .mypy_cache/3.12/cache.10.db | Unknown | 0 | 7393280 | skipped: max_file_size |
| .mypy_cache/3.12/cache.11.db | Unknown | 0 | 6381568 | skipped: max_file_size |
| .mypy_cache/3.12/cache.12.db | Unknown | 0 | 6905856 | skipped: max_file_size |
| .mypy_cache/3.12/cache.13.db | Unknown | 0 | 7090176 | skipped: max_file_size |
| .mypy_cache/3.12/cache.14.db | Unknown | 0 | 7995392 | skipped: max_file_size |
| .mypy_cache/3.12/cache.15.db | Unknown | 0 | 6897664 | skipped: max_file_size |
| .mypy_cache/3.12/cache.2.db | Unknown | 0 | 7057408 | skipped: max_file_size |
| .mypy_cache/3.12/cache.3.db | Unknown | 0 | 5545984 | skipped: max_file_size |
| .mypy_cache/3.12/cache.4.db | Unknown | 0 | 7458816 | skipped: max_file_size |
| .mypy_cache/3.12/cache.5.db | Unknown | 0 | 6574080 | skipped: max_file_size |
| .mypy_cache/3.12/cache.6.db | Unknown | 0 | 5599232 | skipped: max_file_size |
| .mypy_cache/3.12/cache.7.db | Unknown | 0 | 5505024 | skipped: max_file_size |
| .mypy_cache/3.12/cache.8.db | Unknown | 0 | 5771264 | skipped: max_file_size |
| .mypy_cache/3.12/cache.9.db | Unknown | 0 | 6340608 | skipped: max_file_size |
| .mypy_cache/CACHEDIR.TAG | Unknown | 3 | 190 | ok |
| .pytest_cache/.gitignore | Unknown | 2 | 37 | ok |
| .pytest_cache/CACHEDIR.TAG | Unknown | 4 | 191 | ok |
| .pytest_cache/README.md | Markdown | 8 | 302 | ok |
| .pytest_cache/v/cache/lastfailed | Unknown | 27 | 2220 | ok |
| .pytest_cache/v/cache/nodeids | Unknown | 582 | 48988 | ok |
| .python-version | Unknown | 1 | 5 | ok |
| .ruff_cache/.gitignore | Unknown | 2 | 35 | ok |
| .ruff_cache/0.15.20/11151240506088214560 | Unknown | 0 | 168 | skipped: binary |
| .ruff_cache/0.15.20/11173252355182146283 | Unknown | 0 | 899 | skipped: binary |
| .ruff_cache/0.15.20/1146293954944627483 | Unknown | 0 | 188 | skipped: binary |
| .ruff_cache/0.15.20/11972510000338431888 | Unknown | 0 | 77 | skipped: binary |
| .ruff_cache/0.15.20/12559792250607600041 | Unknown | 0 | 562 | skipped: binary |
| .ruff_cache/0.15.20/12946477700982431300 | Unknown | 0 | 67 | skipped: binary |
| .ruff_cache/0.15.20/13842709862046631274 | Unknown | 0 | 226 | skipped: binary |
| .ruff_cache/0.15.20/14772501875134088261 | Unknown | 0 | 2255 | skipped: binary |
| .ruff_cache/0.15.20/15989267376014901249 | Unknown | 0 | 250 | skipped: binary |
| .ruff_cache/0.15.20/16549907356470524752 | Unknown | 0 | 75 | skipped: binary |
| .ruff_cache/0.15.20/1655524104183051972 | Unknown | 0 | 2116 | skipped: binary |
| .ruff_cache/0.15.20/17826862415051225304 | Unknown | 0 | 121 | skipped: binary |
| .ruff_cache/0.15.20/17857341297625773064 | Unknown | 0 | 283 | skipped: binary |
| .ruff_cache/0.15.20/3279835033448734532 | Unknown | 0 | 70 | skipped: binary |
| .ruff_cache/0.15.20/3528976186452572868 | Unknown | 0 | 388 | skipped: binary |
| .ruff_cache/0.15.20/3615129933027466828 | Unknown | 0 | 60 | skipped: binary |
| .ruff_cache/0.15.20/4439090111566271517 | Unknown | 0 | 2464 | skipped: binary |
| .ruff_cache/0.15.20/5426070964058543367 | Unknown | 0 | 340 | skipped: binary |
| .ruff_cache/0.15.20/5575495544498376754 | Unknown | 0 | 196 | skipped: binary |
| .ruff_cache/0.15.20/6257482547299503717 | Unknown | 0 | 2468 | skipped: binary |
| .ruff_cache/0.15.20/6451091466542286850 | Unknown | 0 | 186 | skipped: binary |
| .ruff_cache/0.15.20/798352014734019942 | Unknown | 0 | 188 | skipped: binary |
| .ruff_cache/0.15.20/8058556805231193550 | Unknown | 0 | 51 | skipped: binary |
| .ruff_cache/0.15.20/9641372726687176821 | Unknown | 0 | 260 | skipped: binary |
| .ruff_cache/CACHEDIR.TAG | Unknown | 1 | 43 | ok |
| AGENTS.md | Markdown | 746 | 37931 | ok |
| Dockerfile | Dockerfile | 115 | 3605 | ok |
| Karl-main/.gitignore | Unknown | 38 | 751 | ok |
| Karl-main/AGENTS.md | Markdown | 245 | 12395 | ok |
| Karl-main/README.md | Markdown | 76 | 2965 | ok |
| Karl-main/app/engine/agentic_thread.py | Python | 208 | 8096 | ok |
| Karl-main/app/engine/llm_thread.py | Python | 171 | 6814 | ok |
| Karl-main/app/engine/model_loader.py | Python | 24 | 790 | ok |
| Karl-main/app/engine/upgrade_manager.py | Python | 117 | 3457 | ok |
| Karl-main/app/ui/main_window.py | Python | 764 | 35156 | ok |
| Karl-main/app/ui/styles/neutral.qss | Unknown | 48 | 837 | ok |
| Karl-main/app/utils/memory_manager.py | Python | 38 | 1242 | ok |
| Karl-main/app/utils/rag_pipeline.py | Python | 318 | 12133 | ok |
| Karl-main/app/utils/trace_logger.py | Python | 48 | 1582 | ok |
| Karl-main/app/utils/training_curator.py | Python | 95 | 3095 | ok |
| Karl-main/core/agentic_loop.py | Python | 41 | 1517 | ok |
| Karl-main/core/cognitive_parser.py | Python | 26 | 961 | ok |
| Karl-main/core/hardware_scout.py | Python | 38 | 1098 | ok |
| Karl-main/core/interaction_loop.py | Python | 17 | 632 | ok |
| Karl-main/core/prompt_templates.py | Python | 133 | 5879 | ok |
| Karl-main/core/workflows.py | Python | 98 | 3681 | ok |
| Karl-main/data/model_registry.json | JSON | 42 | 1372 | ok |
| Karl-main/docs/01_problem_statement.md | Markdown | 23 | 3190 | ok |
| Karl-main/docs/02_prd.md | Markdown | 45 | 3465 | ok |
| Karl-main/docs/03_frd.md | Markdown | 33 | 2371 | ok |
| Karl-main/docs/04_architecture.md | Markdown | 63 | 2673 | ok |
| Karl-main/docs/05_scope_and_milestones.md | Markdown | 53 | 3279 | ok |
| Karl-main/docs/06_repo_structure.md | Markdown | 47 | 3178 | ok |
| Karl-main/docs/07_risk_register.md | Markdown | 11 | 3144 | ok |
| Karl-main/download_test_model.py | Python | 36 | 1296 | ok |
| Karl-main/engine_test.py | Python | 75 | 2348 | ok |
| Karl-main/eval/__init__.py | Python | 1 | 15 | ok |
| Karl-main/eval/benchmark_rag.py | Python | 177 | 7040 | ok |
| Karl-main/eval/datasets/code_review.jsonl | Unknown | 10 | 6239 | ok |
| Karl-main/eval/datasets/document_extractor.jsonl | Unknown | 10 | 5668 | ok |
| Karl-main/eval/datasets/grounded_answer.jsonl | Unknown | 10 | 4774 | ok |
| Karl-main/eval/graders.py | Python | 240 | 8889 | ok |
| Karl-main/eval/harness.py | Python | 309 | 11572 | ok |
| Karl-main/eval/run_eval.py | Python | 214 | 6599 | ok |
| Karl-main/main.py | Python | 20 | 426 | ok |
| Karl-main/requirements.txt | Unknown | 10 | 103 | ok |
| Karl-main/smoke_test.py | Python | 59 | 2349 | ok |
| Karl-main/training/WHEN_TO_TUNE.md | Markdown | 75 | 3985 | ok |
| Karl-main/training/qlora_config_template.yaml | YAML | 78 | 4321 | ok |
| Karl-main/training/validate_dataset.py | Python | 213 | 8301 | ok |
| README.md | Markdown | 211 | 7959 | ok |
| app/engine/__init__.py | Python | 7 | 143 | ok |
| app/engine/agent_memory.py | Python | 165 | 6056 | ok |
| app/engine/agentic_thread.py | Python | 703 | 31879 | ok |
| app/engine/config_store.py | Python | 458 | 17986 | ok |
| app/engine/event_broker.py | Python | 60 | 2300 | ok |
| app/engine/feature_flags.py | Python | 170 | 6803 | ok |
| app/engine/hot_reload.py | Python | 67 | 1983 | ok |
| app/engine/image_analysis_thread.py | Python | 67 | 2416 | ok |
| app/engine/inference_service.py | Python | 191 | 7832 | ok |
| app/engine/kv_cache.py | Python | 69 | 2291 | ok |
| app/engine/llm_thread.py | Python | 780 | 37334 | ok |
| app/engine/mcp_client.py | Python | 282 | 11362 | ok |
| app/engine/mini_train_thread.py | Python | 187 | 7250 | ok |
| app/engine/mini_transformer.py | Python | 200 | 7848 | ok |
| app/engine/model_loader.py | Python | 1386 | 61809 | ok |
| app/engine/offline_guard.py | Python | 178 | 6225 | ok |
| app/engine/quantizer_thread.py | Python | 197 | 7777 | ok |
| app/engine/reflection_loop.py | Python | 54 | 2152 | ok |
| app/engine/remote_rpc_client.py | Python | 222 | 8701 | ok |
| app/engine/self_play_thread.py | Python | 259 | 10051 | ok |
| app/engine/swarm_agents.py | Python | 523 | 21569 | ok |
| app/engine/swarm_orchestrator.py | Python | 536 | 25443 | ok |
| app/engine/task_supervisor.py | Python | 253 | 9429 | ok |
| app/engine/tool_executor.py | Python | 81 | 3096 | ok |
| app/engine/websocket_server.py | Python | 2060 | 93084 | ok |
| app/repository/session_repository.py | Python | 78 | 2970 | ok |
| app/state.py | Python | 157 | 5666 | ok |
| app/ui/main_window.py | Python | 533 | 23007 | ok |
| app/ui/sidebar.py | Python | 116 | 4485 | ok |
| app/ui/styles/neutral.qss | Unknown | 366 | 8297 | ok |
| app/ui/themes.py | Python | 1255 | 36219 | ok |
| app/ui/widgets/__init__.py | Python | 4 | 148 | ok |
| app/ui/widgets/command_palette.py | Python | 131 | 6470 | ok |
| app/ui/widgets/glow_panel.py | Python | 49 | 2020 | ok |
| app/ui/widgets/model_combo.py | Python | 171 | 6458 | ok |
| app/ui/widgets/section_shell.py | Python | 28 | 1071 | ok |
| app/ui/widgets/shortcuts_overlay.py | Python | 183 | 6849 | ok |
| app/ui/widgets/status_bar.py | Python | 283 | 11562 | ok |
| app/ui/widgets/symbolic_icon.py | Python | 262 | 9680 | ok |
| app/ui/widgets/toast.py | Python | 63 | 2464 | ok |
| app/ui/widgets/tracing_panel.py | Python | 106 | 3896 | ok |
| app/ui/workspaces/__init__.py | Python | 0 | 0 | ok |
| app/ui/workspaces/ai_lab.py | Python | 813 | 32385 | ok |
| app/ui/workspaces/docs.py | Python | 342 | 13269 | ok |
| app/ui/workspaces/docs_data.py | Python | 193 | 14111 | ok |
| app/ui/workspaces/eval_suite.py | Python | 1039 | 43627 | ok |
| app/ui/workspaces/flywheel_studio.py | Python | 1105 | 44974 | ok |
| app/ui/workspaces/knowledge_base.py | Python | 1481 | 62401 | ok |
| app/ui/workspaces/prompt_lab.py | Python | 1509 | 63598 | ok |
| app/ui/workspaces/swarm_studio.py | Python | 728 | 30336 | ok |
| app/ui/workspaces/swarm_workspace.py | Python | 590 | 22199 | ok |
| app/ui/workspaces/system_config.py | Python | 2636 | 112828 | ok |
| app/ui/workspaces/system_config/__init__.py | Python | 3 | 82 | ok |
| app/ui/workspaces/system_config/appearance_panel.py | Python | 464 | 19549 | ok |
| app/ui/workspaces/system_config/appearance_runtime.py | Python | 240 | 9903 | ok |
| app/ui/workspaces/system_config/common.py | Python | 27 | 606 | ok |
| app/ui/workspaces/system_config/defaults_panel.py | Python | 256 | 10255 | ok |
| app/ui/workspaces/system_config/download_threads.py | Python | 171 | 6572 | ok |
| app/ui/workspaces/system_config/mcp_panel.py | Python | 130 | 4840 | ok |
| app/ui/workspaces/system_config/model_panel.py | Python | 543 | 22436 | ok |
| app/ui/workspaces/system_config/model_preflight.py | Python | 147 | 6330 | ok |
| app/ui/workspaces/system_config/observability_tab.py | Python | 196 | 7067 | ok |
| app/ui/workspaces/system_config/quantization_panel.py | Python | 111 | 4175 | ok |
| app/ui/workspaces/system_config/registry_panel.py | Python | 385 | 16225 | ok |
| app/ui/workspaces/system_config/vision_hardware_panel.py | Python | 455 | 19182 | ok |
| app/ui/workspaces/system_config/workspace.py | Python | 163 | 6458 | ok |
| app/ui/workspaces/training_studio.py | Python | 2297 | 95522 | ok |
| app/ui/workspaces/training_studio/__init__.py | Python | 87 | 3423 | ok |
| app/ui/workspaces/training_studio/auto_train_tab.py | Python | 225 | 8859 | ok |
| app/ui/workspaces/training_studio/dataset_tab.py | Python | 309 | 12328 | ok |
| app/ui/workspaces/training_studio/export_tab.py | Python | 114 | 4477 | ok |
| app/ui/workspaces/training_studio/flywheel_tab.py | Python | 249 | 9536 | ok |
| app/ui/workspaces/training_studio/mini_gpt_tab.py | Python | 678 | 28548 | ok |
| app/ui/workspaces/training_studio/threads.py | Python | 581 | 23337 | ok |
| app/ui/workspaces/training_studio/train_tab.py | Python | 614 | 25544 | ok |
| app/ui/workspaces/vision_workbench.py | Python | 453 | 17465 | ok |
| app/ui/workspaces/workbench/__init__.py | Python | 15 | 609 | ok |
| app/ui/workspaces/workbench/branch_panel.py | Python | 161 | 5536 | ok |
| app/ui/workspaces/workbench/chat_view.py | Python | 279 | 12386 | ok |
| app/ui/workspaces/workbench/feedback_panel.py | Python | 29 | 820 | ok |
| app/ui/workspaces/workbench/hud_toolbar.py | Python | 129 | 4867 | ok |
| app/ui/workspaces/workbench/input_panel.py | Python | 138 | 5740 | ok |
| app/ui/workspaces/workbench/orchestrator.py | Python | 320 | 11672 | ok |
| app/ui/workspaces/workbench/params_drawer.py | Python | 198 | 7479 | ok |
| app/ui/workspaces/workbench/profiles.py | Python | 96 | 3738 | ok |
| app/ui/workspaces/workbench/session_panel.py | Python | 298 | 10564 | ok |
| app/ui/workspaces/workbench/workspace.py | Python | 2384 | 104825 | ok |
| app/utils/codebase_search.py | Python | 47 | 1518 | ok |
| app/utils/conversion/__init__.py | Python | 337 | 13000 | ok |
| app/utils/conversion/afmoe.py | Python | 79 | 3175 | ok |
| app/utils/conversion/arctic.py | Python | 162 | 6809 | ok |
| app/utils/conversion/baichuan.py | Python | 59 | 2469 | ok |
| app/utils/conversion/bailingmoe.py | Python | 216 | 9340 | ok |
| app/utils/conversion/base.py | Python | 2596 | 133298 | ok |
| app/utils/conversion/bert.py | Python | 616 | 26021 | ok |
| app/utils/conversion/bitnet.py | Python | 49 | 1811 | ok |
| app/utils/conversion/bloom.py | Python | 67 | 2939 | ok |
| app/utils/conversion/chameleon.py | Python | 58 | 2353 | ok |
| app/utils/conversion/chatglm.py | Python | 167 | 8401 | ok |
| app/utils/conversion/codeshell.py | Python | 21 | 973 | ok |
| app/utils/conversion/cogvlm.py | Python | 33 | 933 | ok |
| app/utils/conversion/command_r.py | Python | 57 | 2241 | ok |
| app/utils/conversion/dbrx.py | Python | 75 | 3643 | ok |
| app/utils/conversion/deci.py | Python | 184 | 9304 | ok |
| app/utils/conversion/deepseek.py | Python | 461 | 20779 | ok |
| app/utils/conversion/dots1.py | Python | 32 | 1151 | ok |
| app/utils/conversion/dotsocr.py | Python | 48 | 2097 | ok |
| app/utils/conversion/dream.py | Python | 72 | 2852 | ok |
| app/utils/conversion/ernie.py | Python | 200 | 8644 | ok |
| app/utils/conversion/exaone.py | Python | 210 | 10126 | ok |
| app/utils/conversion/falcon.py | Python | 58 | 2710 | ok |
| app/utils/conversion/falcon_h1.py | Python | 118 | 5457 | ok |
| app/utils/conversion/gemma.py | Python | 841 | 43091 | ok |
| app/utils/conversion/glm.py | Python | 259 | 12473 | ok |
| app/utils/conversion/gpt2.py | Python | 78 | 3229 | ok |
| app/utils/conversion/gpt_oss.py | Python | 130 | 5935 | ok |
| app/utils/conversion/gptneox.py | Python | 63 | 2905 | ok |
| app/utils/conversion/granite.py | Python | 328 | 15512 | ok |
| app/utils/conversion/grok.py | Python | 116 | 5165 | ok |
| app/utils/conversion/grovemoe.py | Python | 108 | 4816 | ok |
| app/utils/conversion/hunyuan.py | Python | 357 | 17539 | ok |
| app/utils/conversion/internlm.py | Python | 232 | 10889 | ok |
| app/utils/conversion/internvl.py | Python | 98 | 4450 | ok |
| app/utils/conversion/jais.py | Python | 104 | 4041 | ok |
| app/utils/conversion/jamba.py | Python | 119 | 5013 | ok |
| app/utils/conversion/januspro.py | Python | 116 | 4282 | ok |
| app/utils/conversion/kimi_linear.py | Python | 223 | 11617 | ok |
| app/utils/conversion/kimivl.py | Python | 154 | 7020 | ok |
| app/utils/conversion/lfm2.py | Python | 256 | 10055 | ok |
| app/utils/conversion/lighton_ocr.py | Python | 29 | 882 | ok |
| app/utils/conversion/llada.py | Python | 172 | 7017 | ok |
| app/utils/conversion/llama.py | Python | 314 | 13189 | ok |
| app/utils/conversion/llama4.py | Python | 38 | 1576 | ok |
| app/utils/conversion/llava.py | Python | 129 | 6040 | ok |
| app/utils/conversion/maincoder.py | Python | 14 | 409 | ok |
| app/utils/conversion/mamba.py | Python | 199 | 9621 | ok |
| app/utils/conversion/mimo.py | Python | 295 | 13474 | ok |
| app/utils/conversion/minicpm.py | Python | 184 | 8672 | ok |
| app/utils/conversion/minimax.py | Python | 54 | 1903 | ok |
| app/utils/conversion/mistral.py | Python | 201 | 9414 | ok |
| app/utils/conversion/mistral3.py | Python | 67 | 2303 | ok |
| app/utils/conversion/mpt.py | Python | 49 | 2055 | ok |
| app/utils/conversion/nemotron.py | Python | 384 | 18161 | ok |
| app/utils/conversion/olmo.py | Python | 120 | 4286 | ok |
| app/utils/conversion/openelm.py | Python | 83 | 3683 | ok |
| app/utils/conversion/orion.py | Python | 37 | 1669 | ok |
| app/utils/conversion/pangu.py | Python | 46 | 1772 | ok |
| app/utils/conversion/phi.py | Python | 390 | 18109 | ok |
| app/utils/conversion/pixtral.py | Python | 41 | 1408 | ok |
| app/utils/conversion/plamo.py | Python | 195 | 8491 | ok |
| app/utils/conversion/plm.py | Python | 23 | 786 | ok |
| app/utils/conversion/qwen.py | Python | 627 | 28689 | ok |
| app/utils/conversion/qwen3vl.py | Python | 360 | 16321 | ok |
| app/utils/conversion/qwenvl.py | Python | 200 | 8951 | ok |
| app/utils/conversion/refact.py | Python | 68 | 3223 | ok |
| app/utils/conversion/rwkv.py | Python | 302 | 14231 | ok |
| app/utils/conversion/sarashina2.py | Python | 32 | 958 | ok |
| app/utils/conversion/smallthinker.py | Python | 82 | 3454 | ok |
| app/utils/conversion/smolvlm.py | Python | 47 | 2064 | ok |
| app/utils/conversion/stablelm.py | Python | 98 | 3984 | ok |
| app/utils/conversion/starcoder.py | Python | 23 | 885 | ok |
| app/utils/conversion/step3.py | Python | 231 | 11146 | ok |
| app/utils/conversion/t5.py | Python | 286 | 14126 | ok |
| app/utils/conversion/talkie.py | Python | 53 | 2087 | ok |
| app/utils/conversion/ultravox.py | Python | 203 | 8807 | ok |
| app/utils/conversion/wavtokenizer.py | Python | 45 | 1707 | ok |
| app/utils/conversion/xverse.py | Python | 90 | 3870 | ok |
| app/utils/conversion/youtuvl.py | Python | 64 | 2880 | ok |
| app/utils/convert_lora_to_gguf.py | Python | 540 | 22807 | ok |
| app/utils/correlation_logger.py | Python | 49 | 1550 | ok |
| app/utils/custom_embeddings.py | Python | 124 | 4756 | ok |
| app/utils/dataset_merger.py | Python | 273 | 10140 | ok |
| app/utils/db_pool.py | Python | 69 | 2530 | ok |
| app/utils/diagnostics.py | Python | 384 | 14210 | ok |
| app/utils/ipc_helper.py | Python | 171 | 5804 | ok |
| app/utils/keychain_manager.py | Python | 435 | 15339 | ok |
| app/utils/memory_manager.py | Python | 175 | 6737 | ok |
| app/utils/rag_pipeline.py | Python | 1102 | 44795 | ok |
| app/utils/session_tree.py | Python | 314 | 10424 | ok |
| app/utils/topic_graph.py | Python | 41 | 1433 | ok |
| app/utils/trace_logger.py | Python | 504 | 20842 | ok |
| app/utils/tracing.py | Python | 134 | 4653 | ok |
| app/utils/training_curator.py | Python | 323 | 11514 | ok |
| app/vision/__init__.py | Python | 2 | 40 | ok |
| app/vision/image_preprocess.py | Python | 49 | 1368 | ok |
| app/vision/image_store.py | Python | 146 | 5839 | ok |
| app/vision/ocr_engine.py | Python | 99 | 3122 | ok |
| app/vision/schemas.py | Python | 110 | 3366 | ok |
| app/vision/vision_analyzer.py | Python | 185 | 5377 | ok |
| app/vision/vision_model_loader.py | Python | 312 | 10917 | ok |
| auto_train.py | Python | 462 | 17849 | ok |
| core/agentic_loop.py | Python | 73 | 2346 | ok |
| core/cognitive_parser.py | Python | 78 | 3205 | ok |
| core/hardware_scout.py | Python | 168 | 6612 | ok |
| core/interaction_loop.py | Python | 318 | 12939 | ok |
| core/prompt_templates.py | Python | 133 | 5879 | ok |
| core/workflows.py | Python | 98 | 3681 | ok |
| data/agent_memory.json | JSON | 19 | 251 | ok |
| data/bridge_token.json | JSON | 12 | 232 | ok |
| data/bridge_token.txt | Unknown | 1 | 32 | ok |
| data/codex_library/.version | Unknown | 1 | 3 | ok |
| data/codex_library/AI Steering.html | HTML | 8 | 736 | ok |
| data/codex_library/APIs.html | HTML | 21 | 1141 | ok |
| data/codex_library/Agile.html | HTML | 18 | 1852 | ok |
| data/codex_library/C.html | HTML | 47 | 2011 | ok |
| data/codex_library/CLI  Testing Tools.html | HTML | 4 | 293 | ok |
| data/codex_library/CSS.html | HTML | 35 | 1603 | ok |
| data/codex_library/Codex Search.html | HTML | 10 | 869 | ok |
| data/codex_library/Docker.html | HTML | 4 | 267 | ok |
| data/codex_library/Eval Suite.html | HTML | 7 | 497 | ok |
| data/codex_library/Extension Scripts.html | HTML | 4 | 342 | ok |
| data/codex_library/FastAPI.html | HTML | 4 | 255 | ok |
| data/codex_library/Fortran.html | HTML | 33 | 1615 | ok |
| data/codex_library/Go.html | HTML | 37 | 1665 | ok |
| data/codex_library/HTML.html | HTML | 18 | 1142 | ok |
| data/codex_library/Java.html | HTML | 66 | 4797 | ok |
| data/codex_library/JavaScript.html | HTML | 27 | 1305 | ok |
| data/codex_library/Karl Architecture.html | HTML | 32 | 2797 | ok |
| data/codex_library/Knowledge Base.html | HTML | 17 | 1576 | ok |
| data/codex_library/Kubernetes.html | HTML | 51 | 1873 | ok |
| data/codex_library/Mathematical Introspection.html | HTML | 52 | 5643 | ok |
| data/codex_library/Nodejs.html | HTML | 80 | 4826 | ok |
| data/codex_library/Prompt Lab.html | HTML | 14 | 1338 | ok |
| data/codex_library/PySide6.html | HTML | 26 | 1639 | ok |
| data/codex_library/Python.html | HTML | 4 | 263 | ok |
| data/codex_library/RAG Customization.html | HTML | 7 | 638 | ok |
| data/codex_library/React.html | HTML | 74 | 5225 | ok |
| data/codex_library/Rust.html | HTML | 32 | 2029 | ok |
| data/codex_library/SQL.html | HTML | 17 | 1838 | ok |
| data/codex_library/Steering Tactics.html | HTML | 10 | 891 | ok |
| data/codex_library/Swarm Studio.html | HTML | 15 | 1764 | ok |
| data/codex_library/Swift.html | HTML | 44 | 2181 | ok |
| data/codex_library/System.html | HTML | 4 | 252 | ok |
| data/codex_library/Training Studio.html | HTML | 28 | 2965 | ok |
| data/codex_library/TypeScript.html | HTML | 35 | 1822 | ok |
| data/codex_library/Uvicorn.html | HTML | 27 | 1181 | ok |
| data/codex_library/Workbench.html | HTML | 31 | 4362 | ok |
| data/codex_library/Workflows  Modes.html | HTML | 4 | 306 | ok |
| data/codex_library/Xcode.html | HTML | 32 | 2225 | ok |
| data/eval_last.json | JSON | 9 | 182 | ok |
| data/feature_flags.json | JSON | 5 | 116 | ok |
| data/flywheel/active_learner.py | Python | 47 | 1731 | ok |
| data/flywheel/agent1_generator.py | Python | 459 | 16809 | ok |
| data/flywheel/agent3_curator.py | Python | 388 | 13324 | ok |
| data/flywheel/executor_sandbox.py | Python | 126 | 4934 | ok |
| data/flywheel/queue/task_05688ba5-95d2-4207-a6fd-d26efc3380e0.json | JSON | 8 | 1027 | ok |
| data/flywheel/queue/task_3793ccf3-3351-4cb3-844c-c64e37d80e29.json | JSON | 8 | 660 | ok |
| data/flywheel/queue/task_3a262337-289c-4633-877a-d1b5bcafe643.json | JSON | 8 | 656 | ok |
| data/flywheel/queue/task_3fbc7998-40ad-46a1-ae3d-1e81edcb760e.json | JSON | 8 | 1260 | ok |
| data/flywheel/queue/task_599eca1a-ba58-4e10-901c-2f53308f2a19.json | JSON | 8 | 658 | ok |
| data/flywheel/queue/task_5cf44a5d-1318-47a8-83f9-117372e64a85.json | JSON | 8 | 1534 | ok |
| data/flywheel/queue/task_5d600464-b3cb-4d50-afaf-162ea5d57d22.json | JSON | 9 | 980 | ok |
| data/flywheel/queue/task_8a153309-94c8-4db5-a0d9-086fe1e3aa4b.json | JSON | 8 | 1048 | ok |
| data/flywheel/queue/task_e1b88877-a641-480c-9caf-77d499699226.json | JSON | 8 | 951 | ok |
| data/flywheel/queue/task_eb0c3576-02d9-41fb-84df-58dba266d663.json | JSON | 9 | 512 | ok |
| data/mcp_config.json | JSON | 12 | 192 | ok |
| data/model_registry.json | JSON | 52 | 1717 | ok |
| data/prompt_pairs/RAG_LOOP_untrainedWins.json | JSON | 19 | 7711 | ok |
| data/prompt_pairs/Rag_Loop_H2H.json | JSON | 19 | 9691 | ok |
| data/prompt_pairs/Rag_Loop_H2H_v2.json | JSON | 19 | 7233 | ok |
| data/prompt_pairs/code_pair.json | JSON | 15 | 12097 | ok |
| data/prompt_pairs/complex_random_prompt.json | JSON | 15 | 3397 | ok |
| data/prompt_pairs/greeting.json | JSON | 15 | 891 | ok |
| data/prompt_pairs/noRAG_but_trained_on_data.json | JSON | 19 | 3076 | ok |
| data/prompt_pairs/odd_hi_with_sysprmp.json | JSON | 15 | 3392 | ok |
| data/prompt_pairs/polynomial_math_question2.json | JSON | 7 | 551 | ok |
| data/prompt_pairs/polynomial_math_question3.json | JSON | 15 | 2060 | ok |
| data/prompt_pairs/simple_hi.json | JSON | 15 | 8314 | ok |
| data/prompt_pairs/simple_hi_with_sysprmp.json | JSON | 15 | 1351 | ok |
| data/prompt_pairs/unnecessary_RAG_LOOP_applied.json | JSON | 19 | 14459 | ok |
| data/quantization_comparison.json | JSON | 46 | 987 | ok |
| data/rag_benchmark_results.json | JSON | 363 | 6872 | ok |
| data/ssl/localhost.crt | Unknown | 22 | 1318 | ok |
| data/ssl/localhost.key | Unknown | 28 | 1704 | ok |
| data/vision_model_registry.json | JSON | 62 | 2371 | ok |
| docker-compose.yml | YAML | 35 | 911 | ok |
| docs/01_problem_statement.md | Markdown | 50 | 2923 | ok |
| docs/02_prd.md | Markdown | 124 | 8063 | ok |
| docs/02_rag_pipeline.md | Markdown | 145 | 4264 | ok |
| docs/03_frd.md | Markdown | 222 | 9814 | ok |
| docs/03_training_curator.md | Markdown | 120 | 3470 | ok |
| docs/04_architecture.md | Markdown | 507 | 24907 | ok |
| docs/05_multi_agent_swarm.md | Markdown | 254 | 10070 | ok |
| docs/05_scope_and_milestones.md | Markdown | 431 | 19162 | ok |
| docs/06_repo_structure.md | Markdown | 156 | 9282 | ok |
| docs/06_ui_architecture.md | Markdown | 180 | 9581 | ok |
| docs/07_evaluation_suite.md | Markdown | 320 | 9530 | ok |
| docs/07_risk_register.md | Markdown | 138 | 7565 | ok |
| docs/08_vscode_extension.md | Markdown | 294 | 13349 | ok |
| docs/09_vision_implementation_plan.md | Markdown | 1063 | 23129 | ok |
| docs/10_security_and_safety.md | Markdown | 89 | 5052 | ok |
| download_all_models.py | Python | 91 | 3147 | ok |
| download_test_model.py | Python | 36 | 1296 | ok |
| engine_test.py | Python | 111 | 3837 | ok |
| eval/__init__.py | Python | 1 | 15 | ok |
| eval/benchmark_rag.py | Python | 497 | 18658 | ok |
| eval/datasets/code_review.jsonl | Unknown | 10 | 6239 | ok |
| eval/datasets/document_extractor.jsonl | Unknown | 10 | 5668 | ok |
| eval/datasets/grounded_answer.jsonl | Unknown | 10 | 4774 | ok |
| eval/graders.py | Python | 240 | 8889 | ok |
| eval/harness.py | Python | 428 | 17676 | ok |
| eval/perplexity_bench.py | Python | 540 | 23744 | ok |
| eval/run_eval.py | Python | 239 | 8227 | ok |
| flywheel_runner.py | Python | 123 | 4136 | ok |
| helm/karl/Chart.yaml | YAML | 13 | 274 | ok |
| helm/karl/templates/configmap.yaml | YAML | 14 | 613 | ok |
| helm/karl/templates/deployment.yaml | YAML | 111 | 3950 | ok |
| helm/karl/templates/ingress.yaml | YAML | 34 | 1056 | ok |
| helm/karl/templates/pvc.yaml | YAML | 20 | 754 | ok |
| helm/karl/templates/secrets.yaml | YAML | 14 | 510 | ok |
| helm/karl/templates/service.yaml | YAML | 20 | 682 | ok |
| helm/karl/values.yaml | YAML | 125 | 2900 | ok |
| k8s/configmap.yaml | YAML | 50 | 1521 | ok |
| k8s/deployment.yaml | YAML | 106 | 3027 | ok |
| k8s/ingress.yaml | YAML | 30 | 832 | ok |
| k8s/pvc.yaml | YAML | 14 | 268 | ok |
| k8s/secret.yaml | YAML | 10 | 216 | ok |
| k8s/service.yaml | YAML | 17 | 338 | ok |
| karl.sh | Unknown | 32 | 972 | ok |
| main.py | Python | 272 | 10204 | ok |
| neovim/karl.lua | Unknown | 586 | 15063 | ok |
| pyproject.toml | TOML | 44 | 1017 | ok |
| pytest.ini | Unknown | 16 | 873 | ok |
| raw_test.py | Python | 46 | 1209 | ok |
| requirements.txt | Unknown | 17 | 218 | ok |
| setup_gpu.sh | Unknown | 106 | 4330 | ok |
| setup_karl.py | Python | 598 | 22146 | ok |
| smoke_test.py | Python | 59 | 2349 | ok |
| tests/__init__.py | Python | 16 | 544 | ok |
| tests/conftest.py | Python | 46 | 1401 | ok |
| tests/mock_mcp_server.py | Python | 25 | 505 | ok |
| tests/qt_test_helper.py | Python | 11 | 396 | ok |
| tests/test_agent_memory.py | Python | 86 | 2661 | ok |
| tests/test_ai_lab.py | Python | 149 | 6449 | ok |
| tests/test_app_state_persistence.py | Python | 564 | 24275 | ok |
| tests/test_architecture_audit.py | Python | 96 | 3250 | ok |
| tests/test_auto_train.py | Python | 157 | 5709 | ok |
| tests/test_codex_integration.py | Python | 127 | 5151 | ok |
| tests/test_cognitive_compression.py | Python | 250 | 9307 | ok |
| tests/test_cognitive_parser.py | Python | 39 | 1312 | ok |
| tests/test_cognitive_parser_fuzz.py | Python | 341 | 12861 | ok |
| tests/test_config_store.py | Python | 133 | 4833 | ok |
| tests/test_correlation_logging.py | Python | 230 | 7594 | ok |
| tests/test_custom_agents.py | Python | 335 | 14513 | ok |
| tests/test_dataset_merger.py | Python | 366 | 15081 | ok |
| tests/test_db_pool.py | Python | 243 | 8057 | ok |
| tests/test_db_transactions.py | Python | 164 | 5205 | ok |
| tests/test_educational_sandbox.py | Python | 102 | 2917 | ok |
| tests/test_eval_harness.py | Python | 171 | 6955 | ok |
| tests/test_event_broker.py | Python | 41 | 1144 | ok |
| tests/test_failure_paths.py | Python | 180 | 6518 | ok |
| tests/test_feature_flags.py | Python | 261 | 10003 | ok |
| tests/test_hardware_scout.py | Python | 50 | 1751 | ok |
| tests/test_image_store.py | Python | 87 | 3141 | ok |
| tests/test_inference_safety.py | Python | 283 | 10124 | ok |
| tests/test_inference_service.py | Python | 351 | 10923 | ok |
| tests/test_kv_quantization.py | Python | 89 | 3505 | ok |
| tests/test_local_tracing.py | Python | 68 | 2274 | ok |
| tests/test_log_governance.py | Python | 69 | 2510 | ok |
| tests/test_mcp_client.py | Python | 97 | 3140 | ok |
| tests/test_memory_manager.py | Python | 107 | 3992 | ok |
| tests/test_memory_repository.py | Python | 63 | 2030 | ok |
| tests/test_model_circuit_breaker.py | Python | 139 | 4825 | ok |
| tests/test_observability_telemetry.py | Python | 67 | 2167 | ok |
| tests/test_ocr_engine.py | Python | 34 | 1144 | ok |
| tests/test_prometheus_exporter.py | Python | 92 | 3006 | ok |
| tests/test_prompt_caching.py | Python | 451 | 18768 | ok |
| tests/test_rag_pipeline.py | Python | 286 | 11319 | ok |
| tests/test_rag_reranker.py | Python | 373 | 13178 | ok |
| tests/test_rbac_scopes.py | Python | 254 | 10279 | ok |
| tests/test_remote_offloading.py | Python | 106 | 3858 | ok |
| tests/test_security_guards.py | Python | 475 | 19301 | ok |
| tests/test_security_sandbox.py | Python | 244 | 8861 | ok |
| tests/test_service_discovery.py | Python | 314 | 12165 | ok |
| tests/test_session_tree.py | Python | 274 | 7922 | ok |
| tests/test_speculative_decoding.py | Python | 65 | 2050 | ok |
| tests/test_swarm.py | Python | 210 | 9047 | ok |
| tests/test_task_supervisor.py | Python | 362 | 11713 | ok |
| tests/test_technical_guards.py | Python | 334 | 14275 | ok |
| tests/test_token_lifecycle.py | Python | 268 | 10924 | ok |
| tests/test_trace_logger.py | Python | 277 | 11190 | ok |
| tests/test_training_curator.py | Python | 118 | 4587 | ok |
| tests/test_ui_drag_drop.py | Python | 105 | 3474 | ok |
| tests/test_ui_improvements.py | Python | 256 | 10848 | ok |
| tests/test_vision_analyzer.py | Python | 43 | 1532 | ok |
| tests/test_vision_model_loader.py | Python | 26 | 787 | ok |
| tests/test_vision_workbench.py | Python | 57 | 1944 | ok |
| tests/test_watchdog.py | Python | 297 | 8834 | ok |
| tests/test_websocket_bridge.py | Python | 603 | 24415 | ok |
| tests/test_websocket_contract.py | Python | 106 | 3067 | ok |
| tools/conversion/README.md | Markdown | 16 | 706 | ok |
| tools/conversion/__init__.py | Python | 337 | 13000 | ok |
| tools/conversion/afmoe.py | Python | 79 | 3175 | ok |
| tools/conversion/arctic.py | Python | 162 | 6809 | ok |
| tools/conversion/baichuan.py | Python | 59 | 2469 | ok |
| tools/conversion/bailingmoe.py | Python | 216 | 9340 | ok |
| tools/conversion/base.py | Python | 2596 | 133298 | ok |
| tools/conversion/bert.py | Python | 616 | 26021 | ok |
| tools/conversion/bitnet.py | Python | 49 | 1811 | ok |
| tools/conversion/bloom.py | Python | 67 | 2939 | ok |
| tools/conversion/chameleon.py | Python | 58 | 2353 | ok |
| tools/conversion/chatglm.py | Python | 167 | 8401 | ok |
| tools/conversion/codeshell.py | Python | 21 | 973 | ok |
| tools/conversion/cogvlm.py | Python | 33 | 933 | ok |
| tools/conversion/command_r.py | Python | 57 | 2241 | ok |
| tools/conversion/dbrx.py | Python | 75 | 3643 | ok |
| tools/conversion/deci.py | Python | 184 | 9304 | ok |
| tools/conversion/deepseek.py | Python | 461 | 20779 | ok |
| tools/conversion/dots1.py | Python | 32 | 1151 | ok |
| tools/conversion/dotsocr.py | Python | 48 | 2097 | ok |
| tools/conversion/dream.py | Python | 72 | 2852 | ok |
| tools/conversion/ernie.py | Python | 200 | 8644 | ok |
| tools/conversion/exaone.py | Python | 210 | 10126 | ok |
| tools/conversion/falcon.py | Python | 58 | 2710 | ok |
| tools/conversion/falcon_h1.py | Python | 118 | 5457 | ok |
| tools/conversion/gemma.py | Python | 841 | 43091 | ok |
| tools/conversion/glm.py | Python | 259 | 12473 | ok |
| tools/conversion/gpt2.py | Python | 78 | 3229 | ok |
| tools/conversion/gpt_oss.py | Python | 130 | 5935 | ok |
| tools/conversion/gptneox.py | Python | 63 | 2905 | ok |
| tools/conversion/granite.py | Python | 328 | 15512 | ok |
| tools/conversion/grok.py | Python | 116 | 5165 | ok |
| tools/conversion/grovemoe.py | Python | 108 | 4816 | ok |
| tools/conversion/hunyuan.py | Python | 357 | 17539 | ok |
| tools/conversion/internlm.py | Python | 232 | 10889 | ok |
| tools/conversion/internvl.py | Python | 98 | 4450 | ok |
| tools/conversion/jais.py | Python | 104 | 4041 | ok |
| tools/conversion/jamba.py | Python | 119 | 5013 | ok |
| tools/conversion/januspro.py | Python | 116 | 4282 | ok |
| tools/conversion/kimi_linear.py | Python | 223 | 11617 | ok |
| tools/conversion/kimivl.py | Python | 154 | 7020 | ok |
| tools/conversion/lfm2.py | Python | 256 | 10055 | ok |
| tools/conversion/lighton_ocr.py | Python | 29 | 882 | ok |
| tools/conversion/llada.py | Python | 172 | 7017 | ok |
| tools/conversion/llama.py | Python | 314 | 13189 | ok |
| tools/conversion/llama4.py | Python | 38 | 1576 | ok |
| tools/conversion/llava.py | Python | 129 | 6040 | ok |
| tools/conversion/maincoder.py | Python | 14 | 409 | ok |
| tools/conversion/mamba.py | Python | 199 | 9621 | ok |
| tools/conversion/mimo.py | Python | 295 | 13474 | ok |
| tools/conversion/minicpm.py | Python | 184 | 8672 | ok |
| tools/conversion/minimax.py | Python | 54 | 1903 | ok |
| tools/conversion/mistral.py | Python | 201 | 9414 | ok |
| tools/conversion/mistral3.py | Python | 67 | 2303 | ok |
| tools/conversion/mpt.py | Python | 49 | 2055 | ok |
| tools/conversion/nemotron.py | Python | 384 | 18161 | ok |
| tools/conversion/olmo.py | Python | 120 | 4286 | ok |
| tools/conversion/openelm.py | Python | 83 | 3683 | ok |
| tools/conversion/orion.py | Python | 37 | 1669 | ok |
| tools/conversion/pangu.py | Python | 46 | 1772 | ok |
| tools/conversion/phi.py | Python | 390 | 18109 | ok |
| tools/conversion/pixtral.py | Python | 41 | 1408 | ok |
| tools/conversion/plamo.py | Python | 195 | 8491 | ok |
| tools/conversion/plm.py | Python | 23 | 786 | ok |
| tools/conversion/qwen.py | Python | 627 | 28689 | ok |
| tools/conversion/qwen3vl.py | Python | 360 | 16321 | ok |
| tools/conversion/qwenvl.py | Python | 200 | 8951 | ok |
| tools/conversion/refact.py | Python | 68 | 3223 | ok |
| tools/conversion/rwkv.py | Python | 302 | 14231 | ok |
| tools/conversion/sarashina2.py | Python | 32 | 958 | ok |
| tools/conversion/smallthinker.py | Python | 82 | 3454 | ok |
| tools/conversion/smolvlm.py | Python | 47 | 2064 | ok |
| tools/conversion/stablelm.py | Python | 98 | 3984 | ok |
| tools/conversion/starcoder.py | Python | 23 | 885 | ok |
| tools/conversion/step3.py | Python | 231 | 11146 | ok |
| tools/conversion/t5.py | Python | 286 | 14126 | ok |
| tools/conversion/talkie.py | Python | 53 | 2087 | ok |
| tools/conversion/ultravox.py | Python | 203 | 8807 | ok |
| tools/conversion/wavtokenizer.py | Python | 45 | 1707 | ok |
| tools/conversion/xverse.py | Python | 90 | 3870 | ok |
| tools/conversion/youtuvl.py | Python | 64 | 2880 | ok |
| tools/decrypt_logs.py | Python | 145 | 4932 | ok |
| training/WHEN_TO_TUNE.md | Markdown | 75 | 3985 | ok |
| training/qlora_config_template.yaml | YAML | 78 | 4321 | ok |
| training/validate_dataset.py | Python | 738 | 28686 | ok |
| vscode-extension/.eslintrc.json | JSON | 147 | 4582 | ok |
| vscode-extension/.vscodeignore | Unknown | 9 | 104 | ok |
| vscode-extension/BRIDGE.md | Markdown | 286 | 7714 | ok |
| vscode-extension/LICENSE | Unknown | 21 | 1062 | ok |
| vscode-extension/README.md | Markdown | 70 | 4357 | ok |
| vscode-extension/extension.js | JavaScript | 479 | 19421 | ok |
| vscode-extension/jsconfig.json | JSON | 9 | 162 | ok |
| vscode-extension/media/icon.svg | Unknown | 4 | 273 | ok |
| vscode-extension/media/karl.css | CSS | 1624 | 37160 | ok |
| vscode-extension/media/karl.js | JavaScript | 1466 | 60037 | ok |
| vscode-extension/media/karl_render.js | JavaScript | 653 | 31012 | ok |
| vscode-extension/media/karl_socket.js | JavaScript | 443 | 17371 | ok |
| vscode-extension/media/karl_state.js | JavaScript | 196 | 7821 | ok |
| vscode-extension/media/themes.js | JavaScript | 132 | 9861 | ok |
| vscode-extension/package.json | JSON | 318 | 8200 | ok |
| vscode-extension/src/commands.js | JavaScript | 467 | 18272 | ok |
| vscode-extension/src/fileOps.js | JavaScript | 86 | 2947 | ok |
| vscode-extension/src/gitOps.js | JavaScript | 40 | 915 | ok |
| vscode-extension/src/sidebarProvider.js | JavaScript | 1389 | 66804 | ok |
| vscode-extension/src/tests/run.js | JavaScript | 71 | 2378 | ok |
| walkthrough.md | Markdown | 244 | 11026 | ok |
