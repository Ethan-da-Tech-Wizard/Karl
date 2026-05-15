# Functional Requirements Document (FRD) — Karl v2

## 1. UI Architecture

Three-column PyQt6 layout with a vertical splitter in the center.

```
┌──────────────────┬──────────────────────────────────────┬────────────────────┐
│  LEFT            │  CENTER                              │  RIGHT             │
│  Sessions + RAG  │  Raw Archive (toggle)                │  Config Panel      │
│                  │  Diagnostic Lane (thought trace)     │                    │
│                  │  Chat + all controls                 │                    │
└──────────────────┴──────────────────────────────────────┴────────────────────┘
```

---

## 2. Left Panel

### Sessions
- `QListWidget` — sorted newest-first by mtime, alpha tiebreaker
- Double-click to load
- **New** — clears history, resets session file pointer
- **Save** — persists to `data/sessions/session_TIMESTAMP.json`
- **⑂ Fork** — clones selected session to `_fork_TIMESTAMP.json`, switches to fork
- **📌 Save Version** — prompts for tag, saves to `_v_TAG.json`

### Knowledge Base (RAG)
- `QListWidget` showing ingested files with chunk counts
- **Ingest Document** — file dialog, supports PDF / DOCX / TXT / PY / MD / CSV
- Ingested files persist in FAISS across restarts

---

## 3. Center Column

### Raw Token Archive
- Hidden by default; **Show** checkbox reveals it
- Monospace dark-green on near-black
- Populated by `new_raw_token` signal with microsecond timestamps

### Diagnostic Lane
- Label: `🔬 Diagnostic Lane (reasoning trace)`
- Grey palette — visually demoted from primary output
- Populated by `new_thought_token` (content inside `<think>...</think>`)

### Chat Interface

**Display:** `QTextBrowser` — HTML rendered, external links enabled

**Input row:**
- `QLineEdit` — placeholder: "Type prompt OR fake thought..."
- `Force Thought` — appends typed text as a `<think>` block to history, no generation
- `Generate` / `Send + Loop` (label changes with Auto-Loop state)

**Report / heatmap row:**
- `Workflow Report` checkbox (default on) — shows/hides report display
- `Confidence Heatmap` checkbox (default off) — shows/hides heatmap display

**Workflow Report display:**
- `QTextBrowser`, max 80px height, monospace green-on-dark
- Content: `workflow=X  template=Y  rag_chunks=N  sources=[...]  latency=Z.Zs`

**Confidence Heatmap display:**
- `QTextBrowser`, max 100px height, hidden by default
- HTML `<span style="color:...">` per token, colour mapped from logprob (0→−5 = green→red)
- Renders immediately when toggled on if cached logprobs exist

**Confidence bar + tool row:**
- `Token confidence:` label + colour-coded logprob label
  - Green: avg ≥ −0.5 | Amber: avg ≥ −1.5 | Red: below −1.5
- `🔍 Prompt Diff` button → opens `DiffViewerDialog`
- `📊 Eval` button → opens `EvalDashboardDialog`

**Rating row:**
- `👍 Good` and `👎 Fix` — enabled after each generation, disabled after rating
- 👍 saves SFT example (`source: thumbs_up`)
- 👎 opens correction dialog pre-populated with last response; saving stores SFT + DPO pair with `rejected_response`

**Agentic row:**
- `Auto-Loop` checkbox
- `▶ Run Agentic Loop` button
- `■ Stop` button
- `Agentic: Idle / Running… / Done (N iterations)` status label

---

## 4. Right Panel — Configuration

### System Prompt
- `QTextEdit`, max 180px — used directly in `general_chat`; overridden by template in other workflows

### Workflow Mode
- **Workflow:** `QComboBox` — changing selection syncs template combo and RAG top-k spinner
- **Template:** `QComboBox` — manual override of workflow default
- **RAG top-k:** `QSpinBox` 0–10
- **Contextual chunk headers** checkbox — prepends `[Source: file | Chunk N]`

### Generation Hyperparameters
- Temperature: 0.0–2.0, step 0.1, default 0.7
- Top-P: 0.0–1.0, step 0.05, default 0.95
- Max Tokens: 1–4096, default 512

### Logit Bias
- `QTextEdit`, max 80px, monospace pink
- Format: one entry per line, `word: ±float`
- Tokenised via loaded model at generation time; applied including continuations

### Upgrade Notification
- Hidden at startup; visible when hardware check finds a better-tier model
- Shows RAM/VRAM profile and target model name/tier
- `⬆ Upgrade Karl` triggers `UpgradeDownloadThread`

### Training Data Curator
- Stats: `Examples: N (👍 X ✏️ Y)`
- `📦 Export SFT (Unsloth)` — saves to user-chosen path
- `⚖️ Export DPO Pairs` — disabled if zero DPO pairs; saves TRL-compatible JSONL

---

## 5. Dialog Specifications

### DiffViewerDialog
- Size: 1300×760
- Two panels in horizontal splitter, each with: label, `QComboBox` (all trace entries newest-first), `QTextBrowser`
- Entry display: timestamp, workflow, template, latency, hyperparams, RAG chunks, reasoning trace (2000 char), response (2000 char)
- **Highlight Differences**: line-level diff of `parsed_response`; differing lines get `background:#3B1F1F` in both panels
- **Clear Highlights**: resets all formatting
- Shows fallback message if `data/logs/traces/` is empty or contains no entries

### EvalDashboardDialog
- Size: 1200×700
- **History panel** (left): `QTableWidget` — Timestamp, Workflow, Template, Pass %, Avg Score, Latency; pass-rate colour-coded (green ≥ 80%, amber ≥ 50%, red below); click row for per-case breakdown
- **Runner panel** (right): dataset dropdown, workflow dropdown, `▶ Run Eval`, `QProgressBar`, live status log (`QTextBrowser`)
- `EvalRunThread` fires harness off UI thread; emits `case_done(current, total, id, passed, score)` per case; `run_finished(report)` on completion
- Report auto-saved; history panel auto-refreshes

---

## 6. Threading Model

| Thread | Class | Key Signals |
|---|---|---|
| Main UI | `MainWindow` | — |
| Single generation | `LLMThread` | `new_thought_token`, `new_chat_token`, `new_raw_token`, `generation_finished`, `token_logprobs_ready`, `error_occurred` |
| Agentic loop | `AgenticThread` | `iteration_finished`, `loop_finished`, `error_occurred` |
| Upgrade check | `UpgradeCheckThread` | `upgrade_available`, `no_upgrade` |
| Upgrade download | `UpgradeDownloadThread` | `progress`, `finished`, `error` |
| Eval run | `EvalRunThread` | `case_done`, `run_finished`, `run_error` |

---

## 7. Trace Log Format

`data/logs/traces/trace_YYYY-MM-DD.jsonl` — one entry per generation:

```json
{
  "timestamp": "2025-01-15T10:23:45.123Z",
  "execution_time_seconds": 3.42,
  "workflow": "grounded_answer",
  "template": "grounded_answer",
  "hyperparameters": {"temperature": 0.7, "top_p": 0.95, "max_tokens": 512},
  "rag_context_used": ["chunk 1 text", "chunk 2 text"],
  "compiled_prompt": "<|im_start|>system\n...",
  "raw_output": "<think>...</think> final answer",
  "parsed_thought": "...",
  "parsed_response": "..."
}
```

---

## 8. Data Formats

### SFT export (ShareGPT / Unsloth)
```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

### DPO export (TRL DPOTrainer)
```json
{
  "prompt":   [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "chosen":   [{"role": "assistant", "content": "corrected response"}],
  "rejected": [{"role": "assistant", "content": "original response"}]
}
```

### Eval dataset case
```json
{"id": "case_001", "prompt": "...", "context": "...", "grader": "json_valid", "schema_keys": ["date", "parties"]}
```
