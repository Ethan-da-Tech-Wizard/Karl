# Swarm Perfecting Tasks: Phase 2 Prompts (Detailed Specifications)

This document contains highly specific, line-by-line structural instructions for your two external agents.

---

## Agent 1: Machine-Speak Prompt Integration & Speculative Decoding (Prompt 3)

### Objective
Implement token-efficient prompt compression directly into Karl's live LLM generation loop, and automate speculative decoding setup to boost generation tokens-per-second (TPS).

---

### Task 1: Native Machine-Speak Prompting

#### 1. Modify prompt construction
- **Target File**: [interaction_loop.py](file:///home/ethan/karl/core/interaction_loop.py)
- **Imports**: Add `from app.utils.compactor import compact_trace_for_ai` at the top.
- **Interface updates**:
  - In `build_prompt(system_prompt, chat_history)`:
    - Introduce a check for `machine_speak_enabled` by querying the active hyperparams configuration, falling back to a global config flag (e.g., `enable_machine_speak = True`).
    - If active, process `chat_history` by transforming standard chat dictionaries into compressed trace entries.
    - Format each user and assistant turn:
      - Construct a temporary log-like trace dictionary:
        ```python
        trace_turn = {
            "compiled_prompt": msg.get("content", "") if msg.get("role") == "user" else "",
            "response": msg.get("content", "") if msg.get("role") == "assistant" else "",
            "system_prompt": system_prompt if index == 0 else ""
        }
        ```
      - Pass this dictionary to `compact_trace_for_ai(trace_turn)`.
      - Store the resulting compacted string as the new message content.
    - Append the following instruction to the `system_prompt` buffer to guide the model:
      ```
      [COMPRESSION RULE] The message history has been serialized into token-dense 'Machine Speak' to save context space.
      You must respond in kind using the exact same compressed format:
      1. Shorten all response properties according to the Key Map (e.g., use 'r' for response, 'tk' for thoughts).
      2. Express all code modifications as unified diff blocks ($diff) rather than writing full files.
      ```

#### 2. Streaming Decompression (On-the-fly Parser)
- **Target Files**: `app/engine/llm_thread.py` and `app/engine/agentic_thread.py`
- **Imports**: Add `from app.utils.compactor import decompact_trace` at the top.
- **Decompactor integration**:
  - In the streaming output handler (where tokens are buffered and emitted to PyQt6 signals):
    - Keep a string buffer of the current generation.
    - If the generation stream begins with `{` (indicating a JSON-compacted response structure), buffer the tokens.
    - Once the JSON block closes (or generation finishes):
      - Try parsing the buffer as a compacted trace: `decompact_trace(buffer)`.
      - Extract the decompacted thought from the `thinking` / `tk` key and emit it via `new_thought_token` / `tokens:thought` events.
      - Extract the decompacted response from the `response` / `r` key and emit it via `new_chat_token` / `tokens:chat` events.
    - If it does not start with `{`, bypass the buffer and emit tokens directly (standard stream).

---

### Task 2: Speculative Decoding Automation

#### 1. Setup draft model downloader
- **Target File**: `tools/setup_speculative_decoding.py` [NEW]
- **Requirements**:
  - Write a python script to download a small helper draft model (Qwen 0.5B or 1.5B Instruct) suitable for speculatively decoding Qwen-7B or DeepSeek-R1-1.5B models.
  - Target model URL: `https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q8_0.gguf`
  - Implement a chunked download using `urllib.request` with a CLI progress bar showing transfer rate and remaining time.
  - Save the model to `data/models/qwen2.5-0.5b-instruct-q8_0.gguf`.
  - Write the draft model config to `data/draft_model.json`:
    ```json
    {
      "draft_model_path": "data/models/qwen2.5-0.5b-instruct-q8_0.gguf",
      "n_ctx": 4096,
      "n_gpu_layers": -1
    }
    ```

#### 2. Wire speculative decoding in ModelLoader
- **Target File**: [model_loader.py](file:///home/ethan/karl/app/engine/model_loader.py)
- **Loader integration**:
  - Locate `get_instance(...)` method.
  - Read `data/draft_model.json` to determine if a draft model is configured.
  - If a draft model exists, initialize a second `Llama` handle for speculative decoding:
    ```python
    draft_model = Llama(
        model_path=draft_model_path,
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers
    )
    ```
  - Pass the draft model to the primary model's generation call via the `draft_model` parameter inside the thread run loops.

---
---

## Agent 2: Codebase Scraper & Dataset Booster (Prompt 4)

### Objective
Automatically extract structured SFT training datasets from the local codebase structure, merge it with traces, and validate the output quality before training.

---

### Task 1: Codebase Dataset Scraper

- **Target File**: `tools/generate_code_sft_dataset.py` [NEW]
- **Script logic**:
  - Crawl directories: `app/`, `core/`, and `eval/`. Ignore `venv`, `.git`, `__pycache__`, and test directories.
  - For each Python file found:
    - Load the source code and parse it with `ast.parse()`.
    - Traverse the AST tree using `ast.NodeVisitor` to extract classes, class methods, and functions.
    - For each class / function:
      - Extract docstrings, input arguments, return type annotations, and line ranges.
      - **Generate SFT Pair**:
        - **System Prompt**: Set to the standard Karl Coder prompt.
        - **User Prompt**: Construct a detailed coding task prompt based on the class/function definition.
          - Example template:
            `"Write a Python function '[name]' that accepts parameters '[params]'. Description: [docstring]. Make sure it integrates with existing modules and imports."`
        - **Assistant Response**: Extract the raw Python source code block for the class/function. Wrap it inside code fences:
          ```python
          [extracted function code]
          ```
      - Save the generated SFT row to `data/training/code/synthetic_code_sft.jsonl`.
  - Print summary stats showing the number of files crawled and synthetic examples generated.

---

### Task 2: Dataset Merging & Quality Validation

- **Target File**: [curate_code_datasets.py](file:///home/ethan/karl/tools/curate_code_datasets.py)
- **Features to implement**:
  - Add a dataset merger function `merge_datasets(curated_path: Path, synthetic_path: Path, output_path: Path)`:
    - Read curated examples from `data/training/code/sft.jsonl` and synthetic examples from `data/training/code/synthetic_code_sft.jsonl`.
  - Add a **Quality Validator**:
    - **Syntax Verification**: For every assistant response, parse code blocks using `ast.parse()` to guarantee they contain valid, error-free Python syntax. Filter out invalid rows.
    - **Token Length Guard**: Estimate token count using a character length heuristic (e.g. `chars // 4`). If the combined SFT prompt + response exceeds 3,500 tokens, discard it to prevent OOM errors during GPU training.
  - Merge the verified datasets, shuffle them randomly, and save the output to `data/training/code/merged_sft.jsonl`.

- **Target File**: [auto_train_lora.py](file:///home/ethan/karl/tools/auto_train_lora.py)
  - Change the default `--dataset` command-line argument path to point to `data/training/code/merged_sft.jsonl`.
  - Print a configuration report before launching the trainer, showing total validated examples, training epochs, batch size, and target attention projection modules.

---
---

## Phase 3 Prompts (Swarm Debugging & Prompt Optimization Lab)

The following prompts define the next steps for perfecting the app.

---

### Agent 1: Prompt Evolution Lab & Optimizer (Prompt 5)

#### Objective
Build a local prompt optimization engine that runs mutation cycles (hill-climbing/genetic selection) to refine system prompts based on curated DPO/SFT training logs and evaluation datasets, and integrate it into the PyQt6 Prompt Lab workspace.

#### Steps to Implement:

1. **Create `core/prompt_optimizer.py` [NEW]**:
   - Create a `PromptOptimizer` class.
   - Implement a method `mutate_prompt(current_prompt: str, failed_examples: list[dict]) -> str`:
     - Run a query to the local LLM (`ModelLoader.get_instance()`) with a meta-prompt that says:
       `"Analyze the following failed cases where the system prompt led to incorrect results or errors. Propose a refined system prompt that fixes these failures while remaining concise."`
     - Clean the output to return the mutated prompt.
   - Implement `optimize_loop(prompt_key: str, dataset_path: str, iterations: int = 3) -> str`:
     - Load the base system prompt from `data/system_prompts.json` or registry.
     - Split the dataset into a mini-train (for mutation analysis) and mini-validation (for testing performance).
     - Run the mutation loop:
       1. Mutate prompt using failures on mini-train.
       2. Evaluate mutated prompt using `EvalHarness` on mini-validation.
       3. If the score improves, keep the new prompt; otherwise, discard it.
     - Return the final optimized prompt string.

2. **Modify `app/ui/workspaces/prompt_lab.py`**:
   - Add a new tab `Optimize` alongside A/B streaming:
     - **UI Controls**: 
       - ComboBox to choose the target registry prompt template.
       - File browser to specify the evaluation JSONL dataset.
       - Spinbox for optimization iterations (default: 3).
       - Start/Stop button.
       - Text area for the active system prompt under optimization.
     - **Threaded Execution**:
       - Create `PromptOptimizeThread(QThread)` that handles the optimizer run, emitting signals for iteration progress, intermediate mutation prompts, and evaluation scores.
       - Connect signals to update the UI progress bar and logging area in real time.
     - **Save Action**: Add a "Save to Registry" button that writes the selected prompt back to `data/system_prompts.json`.

---

### Agent 2: Swarm Replays, Live Telemetry & Interactive Debugger (Prompt 6)

#### Objective
Build a visual swarm execution debugger and replay engine. Allow users to pause the swarm execution mid-loop, inspect tasks/diffs, inject custom guidance or edits, view real-time latency and token speed charts, and replay past swarm steps.

#### Steps to Implement:

1. **Create `app/utils/swarm_replay.py` [NEW]**:
   - Implement `SwarmReplayManager` to load daily trace files from `data/logs/traces/` and extract historical swarm runs.
   - Parse execution traces to construct a step-by-step tree/list of actions for each swarm iteration (Architect plans, Coder file changes, and validation outcomes).

2. **Modify `app/engine/swarm_orchestrator.py`**:
   - Add `self.pause_event = threading.Event()` and `self.pause_event.set()` to `SwarmOrchestratorThread`.
   - In the run loop (`_run_layer`), check if `pause_on_step` is enabled in hyperparams. If so, clear the event, emit a `swarm_paused(task_info)` signal, and block on `self.pause_event.wait()`.
   - Implement methods to resume the loop, step, or manually override the active coder task parameters while paused.
   - Calculate and emit real-time telemetry metrics: tokens generated per second (TPS) and cumulative tokens used.

3. **Modify `app/engine/websocket_server.py`**:
   - Map new RPC endpoints to control the pause state and retrieve replay history:
     - `swarm_pause(run_id: str)`: Clears the orchestrator's pause event.
     - `swarm_resume(run_id: str)`: Signals the pause event to let the run resume.
     - `swarm_step(run_id: str)`: Runs exactly one coder iteration and then pauses again.
     - `swarm_get_history(run_id: str)`: Calls `SwarmReplayManager` to return step-by-step logs.
   - Broadcast pause states and live token stats to the VS Code client.

4. **Modify `app/ui/workspaces/swarm_studio.py`**:
   - Enhance the UI layout with:
     - **Interactive Debugger panel**: Adds buttons for Pause, Step, and Resume with a "Pause on Step" checkbox. Shows active step instructions and editable text box for injecting manual guidance mid-run.
     - **Replay panel**: Dropdown to select past runs, showing a timeline of steps. Clicking a step displays the unified code diff and test outputs side-by-side.
     - **Live Charts Widget**: Simple, lightweight canvas to display token speed (TPS) and cumulative token counts during active execution.

---
---

## Phase 4 Prompts (PyPI Library Scraper & QLoRA Optimization)

The following prompts define the next steps for perfecting the app.

---

### Agent 1: PyPI Library Scraper & Doc-to-SFT Compiler (Prompt 7)

#### Objective
Build a Python module scraping utility to parse docstrings, signatures, and library documentation (Sphinx/Markdown) of installed dependencies, query the local LLM to compile synthetic QA instructions, and merge them into the training pipeline.

#### Steps to Implement:

1. **Create `tools/scrape_library_docs.py` [NEW]**:
   - Create a scraper class that:
     - Takes a target package name (e.g., `websockets`, `FastAPI`, `numpy`) and locates its installation path inside `venv/lib/python3.12/site-packages/`.
     - Recursively crawls module files, loading docstrings and inspecting function signatures via `inspect.signature` or AST traversal.
     - Extracts the class names, function names, parameter descriptions, and code examples.
     - For each function/class extracted:
       - Format a generation prompt: *"Construct a practical coding task instruction and valid python solution showing how to use the function '[signature]' described as: '[docstring]'."*
       - Run a query to the local LLM (`ModelLoader.get_instance()`) to generate a clean SFT message structure.
       - Verify that the generated code parses correctly using `ast.parse()`.
       - Write valid SFT blocks to `data/training/code/scraped_library_sft.jsonl`.
     - Accept optional CLI arguments `--package` (e.g., `FastAPI`) and `--max-examples` (default 50).

2. **Modify `tools/curate_code_datasets.py`**:
   - In `merge_datasets`, check for `data/training/code/scraped_library_sft.jsonl` alongside the CodeAlpaca public SFT dataset.
   - Merge its examples into `merged_sft.jsonl`, running length verification and syntax checks.

---

### Agent 2: Advanced QLoRA Trainer & Self-Correction (STaR) Curation (Prompt 8)

#### Objective
Implement sequence packing, cosine decay learning schedule, and dynamic attention target projections inside the QLoRA trainer. Build a self-correction (STaR-style) generation compiler to curate reasoning trace paths from test-correction sequences.

#### Steps to Implement:

1. **Create `tools/generate_self_correction_dataset.py` [NEW]**:
   - Write a self-correction generator script:
     - Load an evaluation dataset from `eval/datasets/`.
     - For each case, query the local LLM with the task.
     - Execute the generated code in a sandboxed shell environment.
     - If verification fails, append the exact compiler stderr output to the chat history as a user turn and query the LLM again.
     - If the model successfully resolves the error (verification returns exit code 0) on the 2nd or 3rd retry:
       - Reconstruct the full trajectory of the successful run: the initial thought, the buggy code, the compiler feedback, the final self-correction thought, and the corrected code.
       - Compile this trace into standard conversational SFT messages and write it to `data/training/code/self_correction_sft.jsonl`.
       - This teaches the model the reasoning behavior of *how to parse tracebacks and fix its own code*.

2. **Modify `tools/auto_train_lora.py`**:
   - Integrate the following trainer enhancements:
     - **Sequence Packing**: Enable `packing=True` inside the `trl.SFTTrainer` call, grouping shorter messages into single 4096-token block sequences to improve GPU throughput.
     - **Cosine Learning Schedule**: Set learning rate scheduler type to `"cosine"` and configure warm-up ratio (default 0.03).
     - **Dynamic Projections**: Query the loaded model's architecture class name to detect its attention layers dynamically. Support common projection names like `q_proj`, `v_proj`, `k_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`, and set them as target modules in `LoraConfig`.
     - **Dataset Loader**: Include `self_correction_sft.jsonl` and `scraped_library_sft.jsonl` in the training setup stats.
