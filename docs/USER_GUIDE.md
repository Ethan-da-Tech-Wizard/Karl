# Karl — Complete User Guide

> **Who this is for:** You. Someone using Karl for the first time and wants to understand
> every button, panel, and setting in the app before touching anything.
>
> Read top to bottom once. After that use it as a reference.

---

## Table of Contents

1. [What Karl Is](#1-what-karl-is)
2. [The Layout — Three Columns](#2-the-layout--three-columns)
3. [Left Column — Sessions & Knowledge Base](#3-left-column--sessions--knowledge-base)
4. [Center Column — The Chat Interface](#4-center-column--the-chat-interface)
5. [Right Column — Controls & Settings](#5-right-column--controls--settings)
6. [The Generation Cycle — What Happens When You Hit Generate](#6-the-generation-cycle--what-happens-when-you-hit-generate)
7. [Workflows Explained](#7-workflows-explained)
8. [Training Data Curator](#8-training-data-curator)
9. [Logit Bias — Advanced Token Control](#9-logit-bias--advanced-token-control)
10. [Tips, Gotchas, and Recommended Settings](#10-tips-gotchas-and-recommended-settings)

---

## 1. What Karl Is

Karl is a **local, offline AI chat and prompt engineering tool**. It runs an AI language model
entirely on your own computer — no internet connection required, no data sent to any server,
no API costs. Everything stays on your machine.

What makes Karl different from a normal chat app:

- You can **see the model's internal reasoning** (the "thought stream") before it gives you the
  final answer. This is the "Diagnostic Lane" at the top of the screen.
- You can **control exactly how the model thinks** by changing the system prompt, workflow mode,
  and generation settings.
- Every conversation is **saved and searchable**, and you can branch off into parallel experiments.
- It has a built-in **training data collector** — if the AI gives a bad answer, you can correct it
  and the correction is saved for future fine-tuning.

---

## 2. The Layout — Three Columns

When Karl opens, the window is divided into three vertical sections:

```
┌─────────────────┬──────────────────────────────────┬──────────────────────┐
│   LEFT COLUMN   │         CENTER COLUMN            │    RIGHT COLUMN      │
│                 │                                  │                      │
│  Saved Sessions │  Diagnostic Lane (thoughts)      │  System Prompt       │
│  New / Save     │  ─────────────────────────────── │  Workflow Mode       │
│  Fork / Version │  Load Model bar                  │  Hyperparameters     │
│                 │  Final Response area              │  Training Curator    │
│  Knowledge Base │  ─────────────────────────────── │  Logit Bias          │
│  (RAG)          │  Input box + Generate             │                      │
│                 │  Workflow Report / Heatmap        │                      │
│  Ingest Doc     │  Rate response / Prompt Diff      │                      │
│                 │  Auto-Loop / Agentic buttons      │                      │
└─────────────────┴──────────────────────────────────┴──────────────────────┘
```

You can drag the dividers between columns to resize them.

---

## 3. Left Column — Sessions & Knowledge Base

### Saved Sessions (top of left column)

Every conversation you have in Karl can be saved as a session file. The list here shows all
your saved sessions, with the most recently modified at the top.

- **Double-click a session** to load it. This restores the full conversation history and the
  system prompt that was active when it was saved.
- Sessions are stored as JSON files in the `data/sessions/` folder inside Karl's directory.

### New Button

Clears the current conversation and starts fresh. Does NOT delete the previous session if you
had saved it — it just unloads it from the screen. Think of it like "New Document" in a word
processor.

### Save Button

Saves the current conversation (all messages + the current system prompt) as a `.json` file.
You can name it whatever you want. Save often — Karl does not auto-save.

### Fork Button (v Fork)

Creates an exact copy of the current session at this moment in time. Useful when you want to
try two different approaches from the same point in a conversation without losing either branch.

**Example use case:** You've had a great 10-message conversation. You want to try asking a
follow-up question two different ways to see which gets a better answer. Fork the session, try
one approach in the original, try the other in the fork.

The fork gets a new filename with a timestamp, like `mysession_fork_20250515_143022.json`.

### Save Version Button (📌 Save Version)

Tags the current conversation state with a custom label you provide (e.g. "before_refactor",
"v1_draft"). Like `git tag` for your conversation. Useful when you're iterating on a prompt
and want to snapshot checkpoints without creating full forks.

---

### Knowledge Base (RAG)

RAG stands for **Retrieval-Augmented Generation**. This is the section that lets you feed
documents to Karl so the model can reference them when answering questions.

**How it works:** When you add documents to the Knowledge Base, Karl breaks them into small
chunks of text and indexes them. Every time you send a message, Karl searches the index for
the chunks most relevant to your question and automatically includes them in the model's
context — even if the document is too long to fit in memory all at once.

The Knowledge Base panel shows a list of files currently indexed.

### Ingest Document Button (bottom of left column)

Click this to add a document to the Knowledge Base. Supported formats:

| Format | What it does |
|--------|-------------|
| `.pdf` | Extracts all text from the PDF |
| `.docx` | Extracts text from Word documents |
| `.txt` | Plain text files |
| `.md` | Markdown files |
| `.py` | Python source code files |
| `.csv` | Spreadsheet data |

After ingesting, the file appears in the Knowledge Base list with a chunk count
(e.g. "myfile.pdf (42 chunks)"). The more chunks, the more content was extracted.

**Important:** RAG only activates if the **RAG top-k** setting (in the right column) is
greater than 0. At top-k=3, Karl retrieves the 3 most relevant chunks from your documents
and includes them in the prompt. Set it to 0 to disable RAG entirely for a message.

---

## 4. Center Column — The Chat Interface

This is where the actual conversation happens.

### Diagnostic Lane (top, dark area labeled "reasoning trace")

This is Karl's most unique feature. When a model is capable of showing its "thinking" process
(like DeepSeek-R1), the raw internal reasoning appears here in real time as it streams in —
before the final answer is shown.

Think of it as watching the AI "think out loud." The thoughts are separated from the final
answer automatically. If you're using a model that doesn't have explicit reasoning (like
TinyLlama), this area will stay empty — the model just answers directly.

**Why this matters for prompt engineers:** You can see exactly how the model interpreted your
question. If the reasoning is going in a wrong direction, you know to adjust your prompt — not
just that the answer was wrong, but *why* it was wrong.

### No Model Loaded / Model Status Bar

The gray bar just above "Final Response" shows which model is currently loaded in green text
(e.g. `Model: tinyllama-1.1b.gguf`). If it says "No model loaded" in gray, Karl can't
generate anything yet.

### Load Model Button (blue button, top right of center column)

Click this to load a model file from your computer. A file picker opens — navigate to your
`data/models/` folder (or anywhere else) and select a `.gguf` file.

**What is a GGUF file?** It's the model format used by Karl's inference engine
(llama-cpp-python). You download these from sources like HuggingFace. Smaller files (1–4GB)
run on most computers. Larger files (7GB+) are more capable but need more RAM/VRAM.

**When you load a new model, the chat history is automatically cleared** to prevent the
previous model's conversation from confusing the new one.

### Final Response (main text area, center)

This is where the AI's actual answer appears, streamed in word by word in real time. The
reasoning goes to the Diagnostic Lane; the final response goes here.

If the model uses `<think>` tags internally, Karl automatically routes the content: everything
inside `<think>...</think>` goes to the Diagnostic Lane, and everything outside goes here.

### Clear Chat Button (top right of Final Response area)

Wipes the entire conversation history (both displays) and resets the workflow to General Chat.
Use this to start a fresh conversation without reloading the model. The model stays loaded —
only the conversation is cleared.

---

### Input Box ("Type prompt OR fake thought...")

This is where you type your message. Press **Enter** or click **Generate** to send.

The "fake thought" part refers to an advanced feature: if you want to inject a thought directly
into the Diagnostic Lane as if the model had thought it (useful for testing how priming the
reasoning stream affects the final answer), you can use the **Force Thought** button instead of
Generate.

### Force Thought Button (dark red button)

Takes what you typed in the input box and inserts it directly into the Diagnostic Lane as a
"thought" — as if the model had reasoned through that text itself. Then Karl continues the
generation from that point.

**Use case:** You want the model to arrive at a specific conclusion in its reasoning, then see
what final answer it produces. You plant the thought, let Karl generate the rest.

### Generate Button

Sends your message, builds the full prompt (system prompt + conversation history + any RAG
context), and starts the model generating. Streams tokens in real time to both panels.

While generating, this button becomes a stop control.

---

### Workflow Report (checkbox + text area below input)

When the **Workflow Report** checkbox is checked, a summary report appears after every
generation showing:

- Which workflow and template were used
- How many RAG chunks were retrieved (and from where)
- The generation latency (how long it took)
- The hyperparameters that were active

This is useful for keeping track of what settings produced what results, especially when you're
experimenting with different configurations.

### Confidence Heatmap (checkbox)

When checked, a color-coded version of the final response appears after generation. Each word
is colored based on how "confident" the model was when it generated it:

- **Green** = high confidence (the model strongly preferred this token)
- **Yellow** = moderate confidence
- **Red** = low confidence (the model was uncertain — could have said something else)

**Why this matters:** Low-confidence words are where hallucinations and errors tend to live.
If a factual claim in the response is colored red, treat it with more skepticism. This feature
requires a model loaded with full logprob support — if it shows nothing, your model doesn't
support it.

---

### Rate Response Row

After every generation, two buttons appear:

- **Good (👍)** — Marks this exchange (your question + the AI's answer) as a good training
  example. It's saved to `data/training/curated.jsonl` for future fine-tuning.

- **Fix (🔧)** — Opens a dialog where you can type the *correct* response. Both the original
  (bad) response and your corrected version are saved together as a **DPO pair** — a special
  training format that teaches the model "prefer this answer, not that one."

### Token Confidence Bar

Shows a single bar indicating the average confidence of the last generation. Useful as a quick
gut-check: if the bar is mostly red, the model was very uncertain overall.

### Prompt Diff Button (🔍 Prompt Diff)

Opens a comparison view that lets you pick any two saved trace logs and see exactly how the
AI's response changed between them — line by line, with differences highlighted in red.

**Use case:** You changed the system prompt slightly and want to know if it actually made a
difference to the output. Load the trace from before and after, compare side by side.

### Eval Button (📊 Eval)

Opens the Evaluation Dashboard — a tool for running structured tests against the model.

Instead of chatting manually, Eval runs a dataset of pre-written test cases (from
`data/eval.jsonl`) through the model automatically and scores each response. Results are saved
to `outputs/reports/`. Use this to measure objectively whether a prompt change made the model
better or worse on a standard set of tasks.

---

### Auto-Loop Checkbox

When checked, after every generation Karl automatically kicks off the Agentic Loop (see below).
The model sees its own response as input and continues working on the task without you clicking
anything. Useful for long autonomous tasks.

**Warning:** Leave this unchecked for normal conversation. With Auto-Loop on and a fast model,
it will keep generating indefinitely.

### Run Agentic Loop Button

Starts an autonomous generation loop. The model reads its own previous output and decides
whether to continue working or stop. The stop condition is defined in
`core/agentic_loop.py` — an editable Python file you can customize.

**Use case:** Long research tasks, multi-step code generation, anything where you want the
model to work through multiple steps on its own.

### Stop Button

Immediately kills the current generation or agentic loop. The partial output stays on screen.

### Agentic: Idle Status

Shows the current state of the agentic loop: `Idle`, `Running`, or `Stopped`.

---

## 5. Right Column — Controls & Settings

### System Prompt (top text box)

This is the instruction set that defines how the AI behaves for the entire conversation. It's
sent at the very beginning of every prompt, before your messages.

**Default:** `"You are a helpful, friendly AI assistant. Answer questions clearly and concisely."`

You can change this to anything. Examples:

- `"You are a Python expert. Always include working code examples."`
- `"You are a harsh critic. Find problems with every idea presented to you."`
- `"You are a customer support agent for Acme Corp. Never discuss competitor products."`

**Important:** When the Workflow is set to anything other than General Chat, this text box is
*ignored* — the workflow's own system prompt is used instead. Switch to General Chat to use
the custom system prompt.

---

### Workflow Mode Section

This is the most powerful configuration section. A **workflow** is a preset that changes the
AI's entire behavior: the system prompt, the template used to format the prompt, and the RAG
settings — all at once with a single dropdown.

#### Workflow Dropdown

| Workflow | What it does |
|----------|-------------|
| **General Chat** | Normal conversation. Uses your custom System Prompt text. |
| **Document Extractor** | Extracts structured information from uploaded documents. Requires RAG documents to be loaded. Returns JSON. |
| **Grounded Answer** | Answers questions based ONLY on the content of your RAG documents. Will not use its own knowledge. Good for Q&A over specific documents. |
| **Code Review** | You are a senior engineer. Give it code and it returns a JSON array of findings with severity levels and suggested fixes. |

**When you're just chatting, always use General Chat.** The other workflows have specific
system prompts designed for specific tasks — they will give bizarre responses to casual
conversation (as you saw!).

#### Template Dropdown

A **template** is the detailed formatting of the system prompt used by the workflow. Each
workflow has a default template, but you can override it here. Advanced feature — leave it on
the default unless you know what you're doing.

#### RAG Top-K

How many document chunks Karl retrieves from your Knowledge Base and includes in the prompt.

- **0** = RAG disabled. Model answers from its own training only.
- **3** = Default. Retrieves the 3 most relevant chunks from your documents.
- **5** = Retrieves 5 chunks. Better recall, but uses more of the context window.

Higher values give the model more document context but leave less room for conversation history.

#### Contextual Chunk Headers Checkbox

When checked, retrieved document chunks include a header explaining where they came from
(e.g. `[Source: myfile.pdf, chunk 3 of 12]`). Helps the model cite sources correctly. Adds
a small amount of extra tokens per chunk.

---

### Generation Hyperparameters

These control *how* the model generates text. They don't change what the model knows —
they change how it makes choices between possible next words.

#### Temperature (default: 0.70)

Controls randomness. This is the most important setting to understand.

| Value | Behavior |
|-------|----------|
| 0.0–0.3 | Very deterministic. Almost always picks the most likely next word. Consistent but repetitive. Good for factual tasks. |
| 0.5–0.8 | **Recommended range.** Balanced creativity and coherence. |
| 0.9–1.0 | More random. More creative but can drift or produce nonsense. |
| 1.0+ | High risk of incoherent output, especially with small models. |

**Lesson learned the hard way:** At temperature 1.0 with a 1.5B model, Karl started generating
`</im_end>` as literal text instead of the stop token — meaning it never stopped generating
and rolled into inventing fake conversations. Always stay at or below 0.8 for small models.

#### Top-P (default: 0.95)

Also called "nucleus sampling." Works alongside temperature to limit which words the model
considers at each step.

- At Top-P=0.95, the model only chooses from the smallest set of words whose combined
  probability adds up to 95%. The rarest/strangest words are cut off.
- Lower Top-P = more conservative word choices.
- Higher Top-P = more variety.

In most cases, leave this at 0.95 and only adjust temperature.

#### Max Tokens (default: 512)

The maximum number of tokens (roughly: word-pieces) the model can generate in a single
response. One token ≈ 0.75 words on average.

- 512 tokens ≈ 380 words ≈ a solid paragraph or two
- 1024 tokens ≈ 760 words ≈ a full page
- 256 tokens ≈ 190 words ≈ a short answer

**If responses get cut off mid-sentence**, increase this. If you want faster, shorter answers,
lower it.

#### Reset to Defaults Button

Sets Temperature → 0.70, Top-P → 0.95, Max Tokens → 512 in one click. Use this whenever the
model starts behaving strangely after you've been experimenting with settings.

---

### Training Data Curator

Karl is designed to collect training data as you use it. Every time you rate a response or
correct one, it saves that exchange to disk. Over time you build a dataset of examples that
reflects exactly how you want the AI to behave — in your own use cases, in your own style.

#### Examples Counter

Shows how many training examples have been collected:
- **Total:** total saved examples
- **👍 (thumbsup):** examples marked as Good
- **✏️ (corrected):** examples where you provided a correction

#### Export SFT (Unsloth) Button

Exports all 👍-rated examples as a JSONL file in **Alpaca format** — a standard format used
by fine-tuning tools like Unsloth, LLaMA Factory, and Axolotl.

SFT = Supervised Fine-Tuning. You're teaching the model: "when asked X, respond like Y."

The export goes to `data/training/export_sft.jsonl`.

#### Export DPO Pairs Button

Exports all ✏️-corrected examples as a JSONL file in **DPO format** (Direct Preference
Optimization).

DPO = you're teaching the model not just what to say, but what to *prefer*. Each example
has three parts: the prompt, the good response (your correction), and the bad response
(the original AI answer). This is a more powerful training signal than SFT alone.

The export goes to `data/training/export_dpo.jsonl`.

---

### Logit Bias — Token-Level Inference Control

This is an advanced feature for power users who want fine-grained control over the model's
vocabulary at generation time.

**What it does:** You can force the model to be more or less likely to use specific words
or phrases. You do this by assigning a positive or negative bias value to tokens.

#### Format

One entry per line:
```
word: +5.0
badword: -10.0
excellent: +3.0
```

- `word: +5.0` — the model will strongly prefer this word when it might otherwise not choose it
- `word: -10.0` — the model will almost never say this word (effectively banning it)
- Values typically range from about -10 (strong ban) to +10 (strong boost)

#### Use Cases

- **Ban a word the model overuses:** `sorry: -5.0` if the model apologizes too much
- **Enforce a specific output style:** `certainly: -5.0, absolutely: -5.0` to reduce
  corporate-speak filler words
- **Boost technical vocabulary:** `dtype: +3.0` when doing ML code generation

**Note:** This operates at the token ID level internally. Karl tokenizes your word using the
currently-loaded model to find the right ID. If you switch models, the same word may map to
a different token ID — always reload logit bias settings after switching models.

---

## 6. The Generation Cycle — What Happens When You Hit Generate

Here is the exact sequence of events when you type a message and click Generate:

1. **Karl reads your message** from the input box
2. **Workflow is resolved** — which workflow is selected? What system prompt does it use?
3. **RAG retrieval** — if RAG top-k > 0 and you have documents indexed, Karl searches for
   the most relevant chunks and prepares them
4. **Logit bias is parsed** — if you have anything in the Logit Bias box, Karl tokenizes
   those words using the loaded model to get their token IDs
5. **Prompt is assembled** — system prompt + RAG context + conversation history + your message,
   all formatted in ChatML format:
   ```
   <|im_start|>system
   You are a helpful, friendly AI assistant...
   <|im_end|>
   <|im_start|>user
   hi
   <|im_end|>
   <|im_start|>assistant
   ```
6. **Generation starts** — the model streams tokens one by one
7. **Token routing** — each token is checked:
   - Inside `<think>...</think>`? → goes to Diagnostic Lane
   - Outside? → goes to Final Response
8. **Stop detection** — when the model generates a stop token (`<|im_end|>`, `</s>`, etc.),
   streaming ends
9. **Post-generation** — Workflow Report and Confidence Heatmap update (if enabled), latency
   is recorded, trace log is written to disk
10. **Rating buttons appear** — you can now rate the response as Good or Fix

---

## 7. Workflows Explained

### When to use General Chat
For everything casual: questions, brainstorming, explanations, writing help. This is the
default and what you want 95% of the time.

### When to use Document Extractor
You have a PDF, Word doc, or text file and you want to pull structured data out of it.
Example: "Extract all the names, dates, and dollar amounts from this contract."
Requires: ingest the document first, make sure RAG top-k is set to 3 or higher.

### When to use Grounded Answer
You want the AI to answer questions *only* based on documents you've provided — not from
its own training data. Good for legal documents, proprietary manuals, anything where you
don't want the model making things up from its general knowledge.

### When to use Code Review
Paste code in your message and get back a structured JSON list of issues:
```json
[
  {"severity": "critical", "location": "line 42", "issue": "SQL injection risk", "suggestion": "Use parameterized queries"},
  {"severity": "minor", "location": "function process_data", "issue": "Missing error handling", "suggestion": "Add try/except around file read"}
]
```

---

## 8. Training Data Curator

### The workflow for building training data

1. Have conversations with Karl as normal
2. After each response, decide: is this good or bad?
3. Click **Good** for responses you'd want the model to replicate
4. Click **Fix** for responses that were wrong or off-tone — type the correct answer in the
   dialog that appears
5. After collecting 50+ examples, run the validator to check the dataset:
   ```
   python -m karl_finetune.validate_dataset data/training/curated.jsonl
   ```
6. Export using one of the Export buttons
7. Use the exported file with a fine-tuning tool (or Karl's built-in trainer in
   `karl_finetune/train_lora.py`)

### What makes a good training example
- Clear instruction (the user's question)
- A response that is concise, accurate, and in the style you want
- Avoid examples where the model got lucky — only save ones where the quality is consistently
  what you'd want

---

## 9. Logit Bias — Advanced Token Control

This is the most advanced feature in Karl. Most users will never need it. Here's when you would:

**Scenario A — Vocabulary enforcement:** You're using Karl to generate product descriptions
and the model keeps using the word "revolutionary." You want to ban it.
```
revolutionary: -10.0
```

**Scenario B — Output format control:** You want every response to start with a bullet point.
Boost the bullet token:
```
•: +5.0
-: +3.0
```

**Scenario C — Language restriction:** Working in a bilingual context and the model keeps
code-switching. Heavily penalize tokens from the unwanted language.

**How to find good bias values:** Start with ±5.0 and observe. -10.0 effectively bans a
token entirely. +10.0 makes it almost certain to appear. The effect varies by model size —
smaller models are more sensitive to bias.

---

## 10. Tips, Gotchas, and Recommended Settings

### For beginners

| Setting | Recommended value |
|---------|-----------------|
| Workflow | General Chat |
| Temperature | 0.7 |
| Top-P | 0.95 |
| Max Tokens | 512 |
| RAG Top-K | 0 (unless using documents) |
| Logit Bias | (empty) |

### Common mistakes

**"The model is talking about code review when I just said hi"**
→ Your Workflow dropdown is set to Code Review. Switch it to General Chat.

**"The responses are gibberish / never stop"**
→ Temperature is too high (above 0.9). Hit Reset to Defaults.

**"The model just keeps saying the same thing over and over"**
→ The context window is full. Hit Clear Chat to start fresh. Consider lowering Max Tokens.

**"I loaded a new model and it's acting weird"**
→ Always use Load Model button (don't just rename files). The chat clears automatically
  when you load a model via the button.

**"The Diagnostic Lane is empty"**
→ Your model doesn't produce `<think>` blocks. That's normal for most models.
  Only specialized reasoning models (DeepSeek-R1, QwQ) use it.

**"The Confidence Heatmap shows nothing"**
→ Your model was loaded without logprobs support. Karl silently falls back to no-heatmap.
  This is a model/GGUF limitation, not a bug.

### Model recommendations by use case

| Use case | Recommended model size |
|----------|----------------------|
| Quick experiments, low RAM | TinyLlama-1.1B-Chat (~600MB) |
| General everyday use | Mistral-7B-Instruct (~4GB) |
| Better reasoning | DeepSeek-R1-7B (~4GB) |
| Best quality, need good GPU | Llama-3-8B-Instruct (~5GB) |

All models must be in GGUF format. Download from HuggingFace and place in `data/models/`.

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message (same as Generate) |
| Esc | (while generating) — use Stop button |

---

*This guide covers Karl v2 — all 21 milestones complete.*
*For technical/developer documentation, see `AGENTS.md` and the `docs/` folder.*
