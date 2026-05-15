# Problem Statement — Karl Prompt Engineering Workbench

## Version History
| Version | Scope |
|---|---|
| 1.0 | LLM introspection toy — see how a model thinks |
| 1.1 | Introspection pivot — structured logging, thought/response split |
| 2.0 | **Prompt Engineering Workbench** — measurable, reproducible, tool-first workflows |

---

## 1. Executive Summary

Prompt Engineers and AI application developers face a critical tooling gap. Consumer-facing LLM applications are abundant. Professional-grade environments designed for **rapid iteration, rigorous testing, and systematic optimisation** of LLM behaviour are not.

Current solutions force developers to choose between:
- **Security compromises** — cloud APIs that transmit proprietary data and prompts over the internet
- **Architectural opacity** — local daemons (Ollama, LM Studio) that hide the interaction loop entirely
- **Excessive friction** — raw Python scripts with no GUI, no logging, no measurement

The deeper problem is not just tooling. It is **methodology**. Most practitioners treat prompt engineering as intuition — they iterate by feel, declare success when an output looks right, and have no reproducible way to measure whether a change actually improved behaviour.

Karl exists to make prompt engineering a measurable, reproducible engineering discipline.

---

## 2. Core Deficiencies in Existing Solutions

### 2.1 Security and Privacy

- **Cloud dependency:** SaaS providers require transmitting proprietary data, sensitive documents, and experimental prompts over the internet — incompatible with air-gapped or compliance-sensitive environments
- **Localhost exposure:** Ollama, vLLM, and LM Studio bind local web servers to `127.0.0.1` or `0.0.0.0`; in enterprise environments this triggers intrusion detection or violates IT policy
- **Hidden telemetry:** Most existing tools include telemetry, crash reporting, or update checks that cannot be fully disabled

### 2.2 No Measurement

The most significant gap: existing tools have no evaluation infrastructure.

A prompt engineer using LM Studio cannot:
- Define what "correct" output looks like for a given task
- Run the same prompt across a dataset and get a pass rate
- Compare two prompt variants with a confidence-backed result
- Detect whether a change regressed previous behaviour

Without measurement, prompt engineering is guesswork with a polished UI.

### 2.3 Opacity

- Existing GUIs hide the exact string sent to the model, the tokenisation, the system prompt injection, and the retrieved RAG chunks
- The reasoning process is either invisible or mixed into the final response
- No audit trail of what was actually run — no reproducibility

### 2.4 Rigid Workflows

- Tools assume a strict User → AI → User turn paradigm
- No support for agentic loops, self-reflection patterns, or structured output workflows
- No way to define named prompt profiles and switch between them programmatically

---

## 3. The Solution

**Karl** is a natively offline application that embeds the inference engine directly within its own process — no servers, no ports, no network calls. Built in Python so the interaction loop, prompt templates, and RAG logic are fully visible and modifiable.

Beyond the original introspection goals, Karl v2 addresses the measurement gap:

- **Workflow Engine** — named modes linking a prompt template, RAG config, and eval grader
- **Eval Harness** — headless and UI-driven runner that scores outputs against defined criteria
- **Prompt Diff Viewer** — side-by-side comparison of any two generation traces
- **Training Pipeline** — curate → validate → export → train, with full DPO pair support
- **Logit Bias Editor** — direct token-level inference control without prompt changes
- **Session Branching** — fork and version sessions to explore variants without losing history
- **Token Confidence Heatmap** — per-token logprob visualisation

The result: "did this prompt change work?" has a number, not an opinion.

---

## 4. Target Persona

**Primary: Prompt Engineer / AI Solutions Architect**
- Python-proficient; understands tokenisation, embeddings, hyperparameters, fine-tuning
- Needs reproducible experiments, not black-box interactions
- Works in privacy-sensitive or air-gapped environments

**Secondary: ML Engineer evaluating fine-tuning readiness**
- Needs to determine whether a behaviour problem requires prompting, RAG, or fine-tuning
- Needs structured training data collection and pre-flight validation before a training run
