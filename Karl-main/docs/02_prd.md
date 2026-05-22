# Product Requirements Document (PRD) — Karl

## 1. Product Vision & Philosophy
**Karl** is a surgical instrument for Prompt Engineers. It is not designed for the general public; it is designed for professionals who need absolute control over the LLM generation lifecycle. The philosophy is "UI for convenience, Code for control, Introspection for insight." Karl provides a polished PyQt6 GUI for interacting with the model, but critically, it completely exposes the model's "internal monologue."

## 2. Target Persona
- **Role:** Prompt Engineer / AI Solutions Architect.
- **Skills:** Proficient in Python, understands tokenization, embeddings, vector math, and LLM hyperparameters.
- **Needs:** Rapid iteration, absolute privacy, deterministic outputs, the ability to read the model's exact reasoning traces, and explicit pathways to manipulate that reasoning.

## 3. Strict Constraints & Acceptance Criteria

### 3.1 Network & Privacy Isolation
- **AC1:** The application MUST NOT initiate any outbound network requests.
- **AC2:** All telemetry MUST be actively disabled.
- **AC3:** Inference must run in-process via `llama-cpp-python` C-bindings.

### 3.2 The Introspection Engine (NEW)
- **AC1:** The application must explicitly capture and separate the model's "thinking process" (e.g., Chain of Thought reasoning) from its final output.
- **AC2:** Every single generation must be rigorously logged to a local file (`data/logs/`), containing the exact prompt submitted, the raw unparsed response, generation speed, and the internal reasoning block.
- **AC3:** The user must have a clear, visual pathway in the UI to monitor the "thought stream" as it happens, distinct from the chat interface.

### 3.3 The "Hackable" Core & Cognitive Manipulation
- **AC1:** The `core/interaction_loop.py` must expose not only the prompt structure but also the generation parameters (Temperature, Top-K, Top-P, Logit Bias).
- **AC2:** The user must be able to manipulate how the model "thinks" by injecting thoughts into the context window, appending fake `<think>` blocks, or altering the generation hyperparameters directly in the Python script.
- **AC3:** The application must gracefully handle Python exceptions originating from user modifications.

## 4. Feature Specifications

### 4.1 Session & Memory Management
- **Definition:** A "Session" is a continuous interaction context.
- **Capabilities:** Users can save sessions to disk as raw JSON.
- **System Prompt:** A permanent, sticky text field that dictates the overall behavior.

### 4.2 The "Ralph Wiggum" Loop Capability
- **Mechanism:** By altering `interaction_loop.py`, the user can instruct the LLM to output a response, parse its own response, append it to the context, and generate again without user intervention.

### 4.3 Universal Document RAG (NEW)
- **Mechanism:** The system must be capable of ingesting almost any document type (PDF, DOCX, TXT, PY, MD, CSV) into a local vector database (`faiss-cpu`) using `sentence-transformers`.
- **Flow:** User clicks "Ingest Document" -> text is extracted based on file extension -> chunked -> encoded -> saved to index.
- **Retrieval:** Relevant chunks are automatically retrieved and appended to the System Prompt during generation.

### 4.4 Aesthetic Design
- **Theme:** Strict neutral palette to reduce eye strain.
- **Layout:** Three distinct resizable areas: Chat Panel (what the AI says), Thought Panel (how the AI thinks), and Configuration Panel.
