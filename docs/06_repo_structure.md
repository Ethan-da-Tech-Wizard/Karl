# Repository Structure & File Specifications

The repository is structured to separate the complex, volatile UI/Threading code from the simple, hackable ML logic.

```text
neat_llm_tool/
│
├── main.py                     # App Entry Point. Initializes QApplication and loads stylesheets.
├── requirements.txt            # Strict dependency list (llama-cpp-python, pyqt6, faiss-cpu, etc.)
│
├── core/                       # THE HACKABLE LAYER - Highly visible and documented.
│   ├── interaction_loop.py     # Main hook. Takes UI state, builds prompt, calls LLM, yields to UI.
│   ├── rag_pipeline.py         # Defines chunk size, overlap, embedding model, and FAISS queries.
│   └── examples/               
│       └── ralph_wiggum.py     # Example code showing an autonomous self-reflection loop.
│
├── app/                        # THE APPLICATION LAYER - Users generally do not edit this.
│   ├── engine/                 
│   │   ├── model_loader.py     # Singleton class managing the loaded Llama instance.
│   │   └── llm_thread.py       # PyQt QThread wrapper that executes core/interaction_loop.py safely.
│   │
│   ├── ui/                     
│   │   ├── main_window.py      # PyQt QMainWindow definition, splitters, and layout.
│   │   ├── widgets/            
│   │   │   ├── chat_view.py    # Custom widget for rendering markdown chat bubbles.
│   │   │   ├── config_panel.py # Form for sliders (Temp, Top P) and System Prompt text area.
│   │   │   └── memory_list.py  # Sidebar widget showing saved chat sessions.
│   │   └── styles/
│   │       └── neutral.qss     # Highly optimized Qt StyleSheet for the dark neutral aesthetic.
│   │
│   └── utils/
│       ├── memory_manager.py   # JSON serialization/deserialization for chat histories.
│       └── error_handler.py    # Catches exceptions from `core/` and formats them nicely for the UI.
│
└── data/                       # LOCAL STATE DIRECTORY (Added to .gitignore)
    ├── models/                 # DeepSeek .gguf files placed here by the user.
    ├── vector_store/           
    │   ├── index.faiss         # The serialized float32 vectors.
    │   └── meta.db             # SQLite DB linking vector IDs to text chunks.
    └── sessions/               # Saved chat history JSON files.
```

## Architectural Decoupling
The separation between `app/` and `core/` is the defining feature of this software. 
- The `app/engine/llm_thread.py` file dynamically imports `core/interaction_loop.py` using Python's `importlib`. 
- This means the UI is simply a "dumb terminal" passing data into the `core/` scripts. 
- If a Prompt Engineer wants to test a "Chain of Thought" prompt strategy, they do not touch `main_window.py`. They open `core/interaction_loop.py`, write the logic to prompt the model, parse the reasoning, append it invisibly to history, and prompt again for the final answer. The UI will faithfully display whatever the script yields back to it.
