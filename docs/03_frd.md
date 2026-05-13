# Functional Requirements Document (FRD)

## 1. User Interface (UI) Architecture
The UI will be built using PyQt6, leveraging its signal/slot mechanism to ensure thread safety.

### 1.1 Layout Specification (Revised for Introspection)
- **Left Panel (20% width):** Session Management & Raw Log Viewer. List of saved sessions and recent generation logs.
- **Center Top Panel (40% width):** The "Thought Stream". A text area with a slightly darker, terminal-like neutral background to display the model's Chain-of-Thought (e.g., `<think>...</think>`) in real-time.
- **Center Bottom Panel (40% width):** The "Main Chat View". Displays the final, polished response. Input text box at the bottom.
- **Right Panel (20% width):** Configuration & Context. Includes System Prompt and Hyperparameter sliders.

## 2. Introspection & Logging Implementation
- **The Trace Logger:** Every time the user clicks "Send", a new entry is created in `data/logs/traces/`.
- **Log Structure:** A JSON Lines (`.jsonl`) file where each entry records:
  - `timestamp`: ISO-8601 string.
  - `compiled_prompt`: The exact string sent to the C++ backend.
  - `hyperparameters`: Temperature, Top_P, etc., used for this specific run.
  - `raw_output`: The full generated string.
  - `parsed_thought`: The extracted reasoning.
  - `parsed_response`: The final answer.

## 3. Cognitive Manipulation Pathways
- To manipulate "how the model thinks", the Prompt Engineer will edit `core/interaction_loop.py`.
- They can intercept the `text` string before it goes to the UI and rewrite the history, forcing the model down a specific logical path.
- The UI will include a "Force Thought" button that allows the user to manually type a reasoning step and append it to the LLM's context window as if the LLM had thought it itself.

## 4. LLM Engine Integration (llama-cpp-python)
- Instantiation MUST happen on a separate `QThread`.
- **Streaming Parser:** The `WorkerThread` must actively parse the streaming tokens. If it detects a reasoning block (like `<think>`), it emits `new_thought_token(str)`. When the block ends, it emits `new_chat_token(str)`. This routes the text to the correct UI panels.

## 5. RAG Pipeline Implementation
- Vector Storage: Local FAISS index.
- The retrieved chunks will be logged in the Trace Logger so the user can verify exactly what memories influenced the thought process.
