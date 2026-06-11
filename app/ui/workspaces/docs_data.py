# -*- coding: utf-8 -*-
"""
Exhaustive reference guides for Karl's Codex workspace.
Provides complete, self-contained documentation of grammar, compilers, runtime loops,
APIs, and optimization tactics for offline code generation.
"""

DEFAULT_LIBRARY = {
    "Karl Architecture": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙️ Karl Internal Architecture</h2>
        <p style='color:#9090A8; line-height:1.4;'>Karl is a PyQt6 offline LLM cockpit and multi-agent system designed for local execution. This manual documents Karl's internal threading models, trace log structure, and search heuristics.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Threading Execution Model</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Inference and heavy processing are completely offloaded from PySide's main GUI thread using <code>QThread</code>. The system runs two primary worker threads:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>LLMThread (Single-shot):</b> Handles standard streaming requests, pre-seeding the output stream with the <code>&lt;think&gt;</code> tag and capturing stdout/stderr safely.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>AgenticThread (Multi-iteration loop):</b> Runs hot-reloadable agent loops, checking output states via a grader function and deciding if another model invocation is needed.</li>
        </ul>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. JSONL Trace Schema</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Every generation traces an immutable JSONL line to <code>data/logs/traces/</code>. The record schema includes details such as hyperparams, system prompt, compiled prompt, thinking text, response text, and RAG chunk references:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>{
  "id": "uuid4",
  "timestamp": "ISO8601",
  "model": "deepseek-r1-1.5b.gguf",
  "hyperparams": {"temperature": 0.7, "top_p": 0.95},
  "system_prompt": "Persona definition...",
  "compiled_prompt": "Prompt construction...",
  "thinking": "Real-time thinking blocks...",
  "response": "Final parsed answer...",
  "rag_chunks": [{"source_file": "manual.txt", "chunk_id": 42}]
}</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. FAISS Alphanumeric Hybrid Search Heuristics</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>To bypass dense vector search limitations on specific codes or IDs, Karl extracts patterns via regular expressions and prioritizes exact substring matches over standard L2-normalized FAISS queries:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#A8D158; padding:8px; font-family:monospace;'># Extract uppercase alphanumeric codes between 3 and 10 characters
id_tokens = re.findall(r"\\b[A-Z0-9]{3,10}\\b", query)
# Extract decimal section numbering format (e.g. 19.3.2)
section_tokens = re.findall(r"\\b\\d{1,2}\\.\\d{1,2}(?:\\.\\d{1,2})?\\b", query)</pre>
    """,
    "AI Steering": """
        <h2 style='color:#00C2FF; margin-top:0;'>🌳 AI Prompt Steering Tactics</h2>
        <p style='color:#9090A8; line-height:1.4;'>Manual for prompt engineering, dynamic prompt manipulation, and behavioral model steering techniques as they are applied in Karl.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Chain-of-Thought (CoT) and Thinking Control</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>DeepSeek-R1 outputs are steered by pre-seeding the assistant prompt with <code>&lt;think&gt;\\n</code>. This forces the local model to enter reasoning mode rather than attempting to answer immediately. The parser routes incoming tokens based on state transitions:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'># Token-routing state transition logic
if "</think>" in buffer:
    in_thought = False
    new_chat_token.emit(remainder)</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Context Budget Trimming</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>To respect context limits (e.g., 4096 to 32768 tokens depending on the model tier), Karl applies active context pruning, removing the oldest messages in the session tree history while preserving the system prompt and the latest turns.</p>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Cognitive State Compression</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>When history exceeds threshold lengths, Karl invokes the model to summarize intermediate conversation cycles, replacing long sequences of chat history with a single dense summary context block before sending it to the next prompt completion pass.</p>
    """,
    "Python": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐍 Python Deep Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>A complete guide to advanced python memory protocols, cooperative concurrency, metaclasses, and custom descriptors.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Descriptor Protocol</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Descriptors form the core of properties, methods, static methods, and class methods. They are classes implementing <code>__get__</code>, <code>__set__</code>, or <code>__delete__</code>:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>class TypedString:
    def __init__(self, name):
        self.name = f"_{name}"
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name, "")
    def __set__(self, instance, value):
        if not isinstance(value, str):
            raise TypeError("Expected string")
        setattr(instance, self.name, value)</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Metaclass Bindings</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Metaclasses control class construction. They subclass <code>type</code> and intercept class creation via <code>__new__</code>:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>class MetaRegistry(type):
    def __new__(cls, name, bases, attrs):
        attrs["__slots__"] = ("_cached_value",)
        return super().__new__(cls, name, bases, attrs)</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Cooperative Concurrency & GC</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Python concurrency relies on cooperative event loops (<code>asyncio</code>) running coroutines. Memory management utilizes reference counting and an incremental cyclic garbage collector (GC) with three generational thresholds:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>import gc
# Retrieve current generational thresholds
thresholds = gc.get_threshold()  # default: (700, 10, 10)</pre>
    """,
    "Docker": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐳 Docker Containerization</h2>
        <p style='color:#9090A8; line-height:1.4;'>Exhaustive guide to local sandboxing, storage volumes, container network sockets, and compose orchestration.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Virtual Networking Layers</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Docker supports bridge, host, overlay, and macvlan networks. Bridge is default, isolating containers on a virtual sub-interface (typically <code>docker0</code>) with IP assignment:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#A8D158; padding:8px; font-family:monospace;'>docker network create --driver bridge local_isolated_net</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Storage Volumes & Mounting</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Volumes bypass the container's union file system, storing data directly on the host machine. This is crucial for local LLM engines where caching models is mandatory:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#A8D158; padding:8px; font-family:monospace;'>docker run -d -v /home/ethan/karl/data/models:/workspace/models local_llm_server</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Docker Compose Orchestration</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Define and run multi-container setups. Example compose structure combining an LLM inference API and vector DB service:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>version: '3.8'
services:
  inference:
    image: llama-cpp-api
    volumes:
      - ./data/models:/models
    ports:
      - "8000:8000"
  vectordb:
    image: qdrant/qdrant
    ports:
      - "6333:6333"</pre>
    """,
    "FastAPI": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚡ FastAPI & ASGI Systems</h2>
        <p style='color:#9090A8; line-height:1.4;'>Guide to high-performance asynchronous microservice design, WebSocket connections, and dependency injection hierarchies.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. ASGI Async Event Loop & Websockets</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>ASGI serves as the interface between async python web servers (like Uvicorn) and applications. Fast WebSockets handle streaming tokens to chat view wrappers:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        token = await get_new_token_async()
        await websocket.send_text(token)</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Dependency Injection Trees</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>FastAPI's dependency injection system computes dependency trees on-demand, caching outcomes across HTTP/WS requests:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>from fastapi import Depends

async def get_db():
    db = DatabaseSession()
    try:
        yield db
    finally:
        db.close()

@app.get("/items")
async def read_items(db = Depends(get_db)):
    return db.query_items()</pre>
    """,
    "Rust": """
        <h2 style='color:#00C2FF; margin-top:0;'>🦀 Rust System Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>Exhaustive reference documenting memory layouts, borrow checking rules, unsafe blocks, and macro systems.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. The Borrow Checker & Ownership</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Rust tracks resources through ownership. Variables own their values, and values are cleaned up when their owner goes out of scope. Rules: (1) One owner, (2) Multiple read borrows, (3) Exactly one mutable borrow:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>fn process_data() {
    let mut data = vec![1, 2, 3];
    let r1 = &data; // Ok
    let r2 = &data; // Ok
    // let m1 = &mut data; // ERROR: cannot borrow as mutable
}</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Unsafe Blocks & Raw Pointer Boundaries</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Unsafe Rust gives direct access to hardware and raw pointers, bypassing compiler checks. It must be bounded cleanly inside safe abstractions:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>let mut num = 5;
let r1 = &mut num as *mut i32;
unsafe {
    *r1 = 10;
    assert_eq!(*r1, 10);
}</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Declaring Macros</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Macros allow metaprogramming, expanding code patterns during compilation via pattern matching:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>macro_rules! create_dict {
    ( $( $key:expr => $val:expr ),* ) => {{
        let mut temp_map = std::collections::HashMap::new();
        $( temp_map.insert($key, $val); )*
        temp_map
    }};
}</pre>
    """,
    "SQL": """
        <h2 style='color:#00C2FF; margin-top:0;'>💾 SQL Database & Index Design</h2>
        <p style='color:#9090A8; line-height:1.4;'>Complete reference for transaction isolation tiers, index architecture, query performance, and execution plans.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Transaction Isolation & Locking</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Isolation levels control query concurrency anomalies (dirty reads, non-repeatable reads, phantom reads): Read Uncommitted, Read Committed, Repeatable Read, Serializable. Locks control row and table updates:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#A8D158; padding:8px; font-family:monospace;'>-- Explicitly lock rows for updating during transaction
SELECT * FROM sessions WHERE id = 42 FOR UPDATE;</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. B-Tree & Hash Index Structure</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>B-Tree indices maintain sorted key structures for range matches. Hash indices locate matches in O(1) time but do not support range scans:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#A8D158; padding:8px; font-family:monospace;'>CREATE INDEX idx_user_sessions ON sessions (user_id, updated_at);</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Query Performance & Execution Plans</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Analyze performance using database engine execution visualizers to spot index scans vs full table scans:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#A8D158; padding:8px; font-family:monospace;'>EXPLAIN ANALYZE SELECT * FROM sessions WHERE user_id = 10 ORDER BY updated_at DESC;</pre>
    """,
    "PySide6": """
        <h2 style='color:#00C2FF; margin-top:0;'>🖥️ PySide6 / PyQt6 GUI Engine</h2>
        <p style='color:#9090A8; line-height:1.4;'>Manual for PySide6 GUI development, signal-slot mechanics, custom layout architectures, and styling systems.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Signal & Slot Engine</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Signals and slots provide safe communication between PySide components, automatically executing slot callbacks on the main GUI thread when emitted from worker threads:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>from PyQt6.QtCore import QObject, pyqtSignal

class TraceLoader(QObject):
    trace_ready = pyqtSignal(dict)
    
    def process(self):
        result = {"id": "42", "response": "done"}
        self.trace_ready.emit(result)</pre>

        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Custom Painting via QPainter</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Override the <code>paintEvent</code> method to draw custom shapes, borders, vector-painted icons, or active tracing borders using vectors:</p>
        <pre style='background:#10101C; border:1px solid #23233A; color:#E4E4F0; padding:8px; font-family:monospace;'>from PyQt6.QtGui import QPainter, QPen, QColor

class CustomPanel(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor("#00C2FF"), 2)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)</pre>
    """
}
