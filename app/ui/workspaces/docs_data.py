# -*- coding: utf-8 -*-
"""
Default reference guides for Karl's Codex workspace.
All guides are structured HTML fragments loaded dynamically.
"""

DEFAULT_LIBRARY = {
    "Workbench": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ Workbench Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>The Workbench is Karl's command center. It features a responsive triple-pane layout: Sessions (Left), Live Reasoning Thought Stream (Center), and Chat Interface (Right).</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Live Reasoning Thought Stream</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>DeepSeek-R1 models reason step-by-step. To ensure the model enters reasoning mode, Karl pre-seeds the assistant prompt with a <code>&lt;think&gt;\\n</code> tag. Reasoning tokens stream in real time to the Center panel. Upon detecting the closing <code>&lt;/think&gt;</code> tag, Karl switches routing, sending the final answer to the Right chat panel.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Parameters Drawer</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Click the chevron next to the user input bar to collapse/expand the parameters drawer. Here, you can adjust hyperparameters (Temperature, Top-P, Max Tokens), enable/disable RAG context retrieval, toggle multi-pass agentic loops, and select model/adapter combinations on the fly.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Conversation Branching Tree</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Karl represents chat history as a tree rather than a flat list. Every message bubble has a <b>branch</b> link. Clicking it lets you fork the conversation from that exact message, allowing you to explore alternate prompting paths. You can switch between branches using the <b>Branches Tree</b> widget on the Left panel.</p>
    """,
    "Prompt Lab": """
        <h2 style='color:#00C2FF; margin-top:0;'>⊕ Prompt Lab Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Prompt Lab allows side-by-side prompt engineering comparison, difference tracking, and token inspection.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Side-by-Side Prompting</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Use Column A and Column B to test variations in system prompts, user prompts, or hyperparameter variables. Saved configurations can be loaded, saved, or deleted as JSON files in <code>data/prompt_pairs/</code> using the Left panel.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Difference & Tokenizer Visualizer</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>The bottom tab widget contains two modules:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Difference View:</b> Renders a character-level diff of the outputs (additions highlighted in green, deletions in red).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Tokenizer Visualizer:</b> Detokenizes and highlights Byte-Pair Encoding (BPE) subwords color-coded by classification type (special, punctuation, word-start, continuation) with interactive ID hover tooltips.</li>
        </ul>
    """,
    "Knowledge Base": """
        <h2 style='color:#00C2FF; margin-top:0;'>⊞ Knowledge Base Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Knowledge Base manages local document ingestion and context matching for Retrieval-Augmented Generation (RAG).</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Document Ingestion</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Upload documents (PDF, CSV, TXT, MD, PY) to split, embed, and index them. You can adjust text chunk size and chunk overlap before clicking <b>+ add file</b>.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Alphanumeric Exact-Match Hybrid Search</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>To resolve dense embedding limitations with precise numeric identifiers, Karl extracts alphanumeric patterns from queries and runs a high-priority exact substring match before running the L2-normalized vector search.</p>
    """,
    "RAG Customization": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ RAG Customization & Tuning</h2>
        <p style='color:#9090A8; line-height:1.4;'>Retrieval-Augmented Generation (RAG) grounds LLM responses with local data. You can tune indexing parameters and check search matching quality offline.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Customizing Chunking Parameters</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Configure <code>chunk_size</code> and <code>overlap</code> when ingesting standard documents. Large chunks capture broad context; small chunks capture specific details.</p>
    """,
    "Training Studio": """
        <h2 style='color:#00C2FF; margin-top:0;'>⬡ Training Studio Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Training Studio houses dataset configuration tools and the local PEFT LoRA training configurator.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. SFT & DPO Dataset Exports</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Export examples in HuggingFace/Unsloth formats:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>SFT (Supervised Fine-Tuning):</b> Exports single/multi-turn messages in conversational chat templates.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>DPO (Direct Preference Optimization):</b> Groups queries, pairing chosen and rejected examples.</li>
        </ul>
    """,
    "Eval Suite": """
        <h2 style='color:#00C2FF; margin-top:0;'>◎ Eval Suite Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Eval Suite benchmarks model pass rates and accuracy using automated grading criteria.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Grading Tasks</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Choose the appropriate grader algorithm for the target workflow (exact_match, json_valid, keyword_hit, groundedness).</p>
    """,
    "Workflows & Modes": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ Workflows & Modes</h2>
        <p style='color:#9090A8; line-height:1.4;'>Karl groups configuration settings into high-level workflows. Each workflow binds a default system prompt, a prompt template, RAG requirements, and an evaluation grader.</p>
    """,
    "Extension Scripts": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ Extension Scripts (Hackable Core)</h2>
        <p style='color:#9090A8; line-height:1.4;'>The core of Karl's reasoning logic is defined in hot-reloadable Python modules under the <code>core/</code> folder (interaction_loop.py, agentic_loop.py, workflows.py, prompt_templates.py).</p>
    """,
    "CLI & Testing Tools": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ CLI & Testing Tools</h2>
        <p style='color:#9090A8; line-height:1.4;'>Karl includes diagnostic terminal tools to support offline development, testing, and dataset validation (run_all_tests.py, engine_test.py, smoke_test.py).</p>
    """,
    "System": """
        <h2 style='color:#00C2FF; margin-top:0;'>≡ System Configuration Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>System Config manages identity details, local settings, model downloads, and hardware instrumentation.</p>
    """,
    "Steering Tactics": """
        <h2 style='color:#00C2FF; margin-top:0;'>🌳 Prompt & AI Steering Tactics</h2>
        <p style='color:#9090A8; line-height:1.4;'>A complete guide to prompt engineering, dynamic prompt manipulation, and behavioral model steering techniques as they are applied and tested in Karl.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Prompt Engineering Tactics</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Chain-of-Thought (CoT), Zero/Few-shot learning, RAG Context Anchoring, and Output Constraints.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Programmatic Prompt Manipulation</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Dynamic Variable Interpolation, Context Budget Trimming, Cognitive State Compression, and Tag Stripping.</p>
    """,
    "Python": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐍 Python Exhaustive Reference Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>Python is a highly dynamic, multi-paradigm interpreted language. This manual delivers a low-level and high-level structural reference on the CPython runtime, scopes, descriptors, metaprogramming, and concurrent event loops.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Scopes, Decorators & Closures</h3>
        <p style='color:#9090A8; line-height:1.4;'>CPython resolves variables using the <b>LEGB</b> scoping rule (Local, Enclosing, Global, Built-in). Closures bind lexical scopes to nested scopes even when calling outside enclosing environments.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import functools

def register_call(limit=100):
    def decorator(func):
        calls = 0  # Enclosed scope variable
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal calls  # Modifies variable in enclosing scope
            calls += 1
            if calls > limit:
                raise RuntimeError(f"{func.__name__} limit exceeded")
            return func(*args, **kwargs)
        return wrapper
    return decorator
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Metaprogramming & Descriptors</h3>
        <p style='color:#9090A8; line-height:1.4;'>Metaclasses customize class instantiation lifecycle. Descriptors customize attribute access by implementing the descriptor protocol.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Descriptor Protocol for type validation
class NonNegative:
    def __set_name__(self, owner, name):
        self.name = name
    def __get__(self, instance, owner):
        if instance is None: return self
        return instance.__dict__.get(self.name, 0)
    def __set__(self, instance, value):
        if value < 0:
            raise ValueError(f"{self.name} cannot be negative")
        instance.__dict__[self.name] = value

# Metaclass enforcing class-wide slot allocations
class StrictMeta(type):
    def __new__(cls, name, bases, attrs):
        if "__slots__" not in attrs:
            # Enforce slots to optimize memory and disable dynamic __dict__
            attrs["__slots__"] = tuple(k for k in attrs.keys() if not k.startswith("__"))
        return super().__new__(cls, name, bases, attrs)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Asyncio, Event Loops & Cooperative Tasks</h3>
        <p style='color:#9090A8; line-height:1.4;'>Asyncio implements single-threaded cooperative multitasking. Cooperative yields are triggered explicitly using `await` on awaitables.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import asyncio

async def worker(queue: asyncio.Queue, id: int):
    while True:
        task_id = await queue.get()
        try:
            print(f"Worker {id} processing {task_id}")
            await asyncio.sleep(0.1)  # Cooperative yield
        finally:
            queue.task_done()

async def main():
    queue = asyncio.Queue()
    for item in range(20):
        await queue.put(item)
    
    # TaskGroups ensure clean exception propagation
    async with asyncio.TaskGroup() as tg:
        workers = [tg.create_task(worker(queue, i)) for i in range(3)]
        await queue.join()
        for w in workers:
            w.cancel()
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. CPython Memory Management & GIL</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Mechanism</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Operation Strategy & Impact</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Reference Counting</td>
            <td style='padding:4px;'>Every PyObject tracks active references. Reaches zero yields instant memory deallocation.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Cyclic Garbage Collector</td>
            <td style='padding:4px;'>Generational GC (Gen 0/1/2) scanning container objects to break reference cycles using heuristics.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Global Interpreter Lock (GIL)</td>
            <td style='padding:4px;'>Protects internal state from race conditions. Threads yield control periodically, bypassing multi-core compute.</td>
          </tr>
        </table>
    """,
    "C++": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ C++ Comprehensive Reference Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>C++ delivers systems-level hardware control combined with zero-overhead abstractions. This manual explores structure padding, lifetime rules, compile-time metaprogramming, and smart pointer layouts.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Struct Padding, Cache Lines & Alignment</h3>
        <p style='color:#9090A8; line-height:1.4;'>Compilers insert alignment padding to match byte-boundaries of targeted CPU architectures. Misaligned fields penalize read/write memory transactions.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Padding Optimization: Order members largest to smallest
struct Optimized {
    double c;  // 8 bytes
    int b;     // 4 bytes
    char a;    // 1 byte
    char pad[3]; // 3 bytes alignment padding automatically generated
}; // sizeof(Optimized) == 16 bytes

// Align to CPU cache lines (typically 64 bytes) to prevent false sharing
struct alignas(64) ThreadData {
    int value;
    char pad[60]; // Isolates cache line
};
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Lvalues, Rvalues & Move Semantics</h3>
        <p style='color:#9090A8; line-height:1.4;'>Move semantics transfer ownership of heap-allocated buffers instead of deep-copying them, using rvalue references.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <utility>

class Buffer {
    size_t size;
    int* data;
public:
    Buffer(size_t s) : size(s), data(new int[s]) {}
    ~Buffer() { delete[] data; }
    
    // Move Constructor (transfer ownership, nullify source pointer)
    Buffer(Buffer&& other) noexcept : size(other.size), data(other.data) {
        other.size = 0;
        other.data = nullptr;
    }
    
    // Move Assignment operator
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            delete[] data;
            size = other.size;
            data = other.data;
            other.size = 0;
            other.data = nullptr;
        }
        return *this;
    }
    
    // Disable copies to enforce exclusive ownership (RAII)
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;
};
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Templates, SFINAE & C++20 Concepts</h3>
        <p style='color:#9090A8; line-height:1.4;'>SFINAE filters compiler function overloads. C++20 Concepts constraint templated parameters directly, providing cleaner compile-time errors.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <concepts>
#include <type_traits>

// C++20 Concept
template <typename T>
concept Printable = requires(T t) {
    { std::cout << t } -> std::same_as<std::ostream&>;
};

template <Printable T>
void print_element(T value) {
    std::cout << value << std::endl;
}

// SFINAE approach (pre-C++20)
template <typename T, typename std::enable_if<std::is_integral<T>::value, int>::type = 0>
void process_number(T num) {
    // only active for integral types
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Smart Pointers Control Block Internals</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Class</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Heap Allocations & Details</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::unique_ptr&lt;T&gt;</td>
            <td style='padding:4px;'>Zero runtime overhead. Contains a raw pointer and optionally a custom deleter structure. No control block allocation.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::shared_ptr&lt;T&gt;</td>
            <td style='padding:4px;'>Allocates a control block housing strong and weak reference counts, plus custom allocator/deleter. Double pointer layout.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::weak_ptr&lt;T&gt;</td>
            <td style='padding:4px;'>Tracks reference without incrementing the strong pointer limit. Uses `weak.lock()` to obtain a temporary shared_ptr.</td>
          </tr>
        </table>
    """,
    "SQL": """
        <h2 style='color:#00C2FF; margin-top:0;'>🖧 SQL Optimization & Engine Internals</h2>
        <p style='color:#9090A8; line-height:1.4;'>Relational databases isolate queries. This reference sheet details query pipeline execution orders, window function frames, execution plans, and transaction concurrency models.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Logical Query Processing Order</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Step</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Clause</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Engine Action</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>1</td>
            <td style='padding:4px; font-family:monospace;'>FROM / JOIN</td>
            <td style='padding:4px;'>Identifies source datasets and computes virtual cartesian products.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>2</td>
            <td style='padding:4px; font-family:monospace;'>WHERE</td>
            <td style='padding:4px;'>Filters records based on column expressions (cannot access SELECT aliases).</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>3</td>
            <td style='padding:4px; font-family:monospace;'>GROUP BY</td>
            <td style='padding:4px;'>Buckets matched data rows into group keys.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>4</td>
            <td style='padding:4px; font-family:monospace;'>HAVING</td>
            <td style='padding:4px;'>Applies filtering logic to grouped aggregate properties.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>5</td>
            <td style='padding:4px; font-family:monospace;'>SELECT / WINDOW</td>
            <td style='padding:4px;'>Projects columns, computes window calculations, and evaluates expressions.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>6</td>
            <td style='padding:4px; font-family:monospace;'>DISTINCT</td>
            <td style='padding:4px;'>Filters out duplicates.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; color:#2DD4A0;'>7</td>
            <td style='padding:4px; font-family:monospace;'>ORDER BY</td>
            <td style='padding:4px;'>Sorts results using key arrays (has access to projected column aliases).</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Window Functions & Framing Boundaries</h3>
        <p style='color:#9090A8; line-height:1.4;'>Window clauses compute parameters across segments without collapsing records. Specifying frames optimizes processing limits.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
SELECT txn_id, user_id, amount,
       -- Cumulative sum limited to previous 3 transactions plus current row
       SUM(amount) OVER (
           PARTITION BY user_id 
           ORDER BY txn_date 
           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
       ) as moving_sum,
       -- Compare value against user's prior record
       LAG(amount, 1) OVER (PARTITION BY user_id ORDER BY txn_date) as prev_amount
FROM transactions;
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Recursive Common Table Expressions (CTEs)</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
WITH RECURSIVE org_hierarchy AS (
    -- Anchor Member
    SELECT emp_id, manager_id, name, 1 as depth
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    -- Recursive Member
    SELECT e.emp_id, e.manager_id, e.name, oh.depth + 1
    FROM employees e
    JOIN org_hierarchy oh ON e.manager_id = oh.emp_id
)
SELECT * FROM org_hierarchy ORDER BY depth;
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Indexes & Concurrency Isolation Levels</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Index Scan vs Seek:</b> Index Seek traverses B-tree leaves to extract key rows directly. Index Scan evaluates entire indices sequentially, running if tables lack targeted indexes.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>ACID & MVCC:</b> Multi-Version Concurrency Control handles parallel reads/writes without table-wide locks. Read transactions access snapshots while write updates write new node variants.</li>
        </ul>
    """,
    "Rust": """
        <h2 style='color:#00C2FF; margin-top:0;'>🦀 Rust Systems & Memory Management Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Rust delivers performance guarantees alongside memory safety. This guide specifies borrowing semantics, trait dispatch models, concurrency containers, and raw unsafe operations.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Ownership, Lifetimes & Drop Checker</h3>
        <p style='color:#9090A8; line-height:1.4;'>Rust enforces safety at compile-time. Values are owned exclusively by single scopes. References are bounded by explicit lifetimes (<code>'a</code>) to prevent dangling references.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Structure capturing references must specify lifetime mappings
struct Segment<'a> {
    buffer: &'a [u8],
}

// Function returning longest slice enforces matching inputs and output lifetimes
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Static vs Dynamic Dispatch</h3>
        <p style='color:#9090A8; line-height:1.4;'>Traits represent abstract structures. Compilers dispatch them statically using monomorphization, or dynamically using virtual lookup tables (vtables).</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
trait Executor {
    fn run(&self);
}

// Static Dispatch (Generates separate functions at compile-time, zero runtime overhead)
fn process_static<E: Executor>(exec: E) {
    exec.run();
}

// Dynamic Dispatch (Single function using runtime vtable pointers)
fn process_dynamic(exec: &dyn Executor) {
    exec.run();
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Concurrency Safety: Send, Sync & Smart Containers</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Smart Pointer</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Strategy, Thread-Safety & Interior Mutability</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Box&lt;T&gt;</td>
            <td style='padding:4px;'>Standard heap allocation. Exclusive ownership. Implements <code>Send</code> if T is <code>Send</code>.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Rc&lt;T&gt; / RefCell&lt;T&gt;</td>
            <td style='padding:4px;'>Single-threaded reference counting. RefCell enforces write borrowing checks at runtime. Not thread-safe (lacks <code>Send</code> and <code>Sync</code>).</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Arc&lt;T&gt; / Mutex&lt;T&gt;</td>
            <td style='padding:4px;'>Atomic Reference Counter. Mutex wraps objects, locking write threads concurrently. Safe to share across threads.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Unsafe Rust & FFI</h3>
        <p style='color:#9090A8; line-height:1.4;'>Unsafe blocks allow dereferencing raw pointers, calling foreign external C functions, and mutating static variables.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
fn unsafe_swap(a: &mut i32, b: &mut i32) {
    let raw_a = a as *mut i32;
    let raw_b = b as *mut i32;
    unsafe {
        // Direct memory dereference bypasses borrow checker
        let temp = std::ptr::read(raw_a);
        std::ptr::write(raw_a, std::ptr::read(raw_b));
        std::ptr::write(raw_b, temp);
    }
}
        </pre>
    """,
    "React": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚛ React Architecture & Reconciliation Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>React organizes interfaces declarative. This manual details rendering phases, fiber reconciling updates, hook dependencies, and server-side components.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. React Fiber Reconciliation & Double Buffering</h3>
        <p style='color:#9090A8; line-height:1.4;'>React computes mutations on a secondary fiber tree (workInProgress) before writing them to the active layout tree on screen. This prevents intermediate rendering glitches.</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Render Phase:</b> Asynchronous calculation building workInProgress fiber nodes. Can be paused, discarded, or restarted by scheduler.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Commit Phase:</b> Synchronous operations writing changes directly to the browser DOM. Runs side-effects once layout is updated.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Advanced Hooks API Reference</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Hook</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Mechanism & Target Scopes</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useRef(val)</td>
            <td style='padding:4px;'>Allocates a persistent mutable object container. Mutating `.current` does not trigger re-renders. Binds DOM nodes directly.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useMemo(()=>v, deps)</td>
            <td style='padding:4px;'>Caches complex data operations. Bypasses execution across renders until dependencies change.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useCallback(fn, deps)</td>
            <td style='padding:4px;'>Memoizes raw function references to prevent child components from re-evaluating properties.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useTransition()</td>
            <td style='padding:4px;'>Marks state transitions as non-blocking. Allows UI to remain interactive during heavy rendering.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Performance Tuning: Virtualization & Custom Hooks</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import { useState, useEffect, useRef } from 'react';

// Custom Hook tracking layout intersections
export function useElementInView(options) {
    const containerRef = useRef(null);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            setIsVisible(entry.isIntersecting);
        }, options);
        
        if (containerRef.current) {
            observer.observe(containerRef.current);
        }
        
        return () => {
            if (containerRef.current) {
                observer.unobserve(containerRef.current);
            }
        };
    }, [options]);

    return [containerRef, isVisible];
}
        </pre>
    """,
    "Node.js": """
        <h2 style='color:#00C2FF; margin-top:0;'>⬢ Node.js Engine & Concurrency Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Node.js integrates Google's V8 engine with libuv to support high-throughput, non-blocking asynchronous runtimes. This guide details event loop phases, backpressure management, and multi-threaded isolation.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Libuv Event Loop & Microtasks</h3>
        <p style='color:#9090A8; line-height:1.4;'>The event loop processes non-blocking I/O across six key phases. Microtasks (like <code>process.nextTick()</code> and <code>Promise</code> callbacks) execute completely after the active phase finishes, before yielding to the next phase.</p>
        <ol style='color:#9090A8; line-height:1.3;'>
          <li><b>Timers:</b> Executes callbacks scheduled by <code>setTimeout()</code> and <code>setInterval()</code>.</li>
          <li><b>Pending Callbacks:</b> Processes deferred socket and resource handler operations.</li>
          <li><b>Idle, Prepare:</b> Used internally for system tasks.</li>
          <li><b>Poll:</b> Blocks to retrieve new I/O events, executing connection callbacks.</li>
          <li><b>Check:</b> Executes callbacks scheduled by <code>setImmediate()</code>.</li>
          <li><b>Close Callbacks:</b> Processes socket/file close operations (e.g., <code>socket.on('close')</code>).</li>
        </ol>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Streams Pipeline & Backpressure</h3>
        <p style='color:#9090A8; line-height:1.4;'>Streams process data iteratively to prevent memory leaks. Backpressure pauses source reading operations if internal write queues fill up.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
const { pipeline, Transform } = require('stream');
const fs = require('fs');

// Custom encryption/processing stream
const encryptTransformer = new Transform({
    transform(chunk, encoding, callback) {
        for (let i = 0; i < chunk.length; i++) {
            chunk[i] ^= 0x5A; // Simple XOR operation
        }
        callback(null, chunk);
    }
});

// pipeline handles backpressure and automatically closes streams on error
pipeline(
    fs.createReadStream('source.zip'),
    encryptTransformer,
    fs.createWriteStream('encrypted.zip'),
    (err) => {
        if (err) console.error('Processing failed:', err);
        else print('Stream processed successfully');
    }
);
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Thread Isolation vs Clustering</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Cluster Module:</b> Spawns child processes using <code>child_process.fork()</code>. All child processes share port allocations, using round-robin routing handles to balance load.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Worker Threads:</b> Spawns separate threads sharing memory zones via <code>SharedArrayBuffer</code>. Ideal for intensive computing within single process scopes.</li>
        </ul>
    """,
    "Go": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐹 Go Concurrency & Runtime Internals</h2>
        <p style='color:#9090A8; line-height:1.4;'>Go is a statically typed language compiling into structured binary targets. This manual covers goroutine scheduling, channel semantics, maps allocation, and recovery blocks.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. The GMP Scheduler</h3>
        <p style='color:#9090A8; line-height:1.4;'>The Go runtime handles concurrent execution multiplexing three structures:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>G (Goroutine):</b> Holds call stack, instruction pointer, and scheduling details. Allocation overhead is extremely low (starts at 2KB).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>M (Machine):</b> Represents OS threads. Managed directly by the kernel scheduler.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>P (Processor):</b> Represents logical context resource limits. Handles queues of runnable goroutines, stealing workloads from other processors if queues empty out.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Channels, CSP & State Semantics</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
package main

import (
	"context"
	"fmt"
	"time"
)

func worker(ctx context.Context, jobs <-chan int, results chan<- int) {
	for {
		select {
		case <-ctx.Done():
			return
		case job, ok := <-jobs:
			if !ok { return } // Channel closed
			results <- job * job
		}
	}
}
        </pre>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Channel State</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Writing</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Reading</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Closing</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Nil</td>
            <td style='padding:4px;'>Blocks forever</td>
            <td style='padding:4px;'>Blocks forever</td>
            <td style='padding:4px;'>Panics</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Open</td>
            <td style='padding:4px;'>Blocks if full</td>
            <td style='padding:4px;'>Blocks if empty</td>
            <td style='padding:4px;'>Succeeds</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Closed</td>
            <td style='padding:4px;'>Panics</td>
            <td style='padding:4px;'>Returns default, ok=false</td>
            <td style='padding:4px;'>Panics</td>
          </tr>
        </table>
    """,
    "Agile": """
        <h2 style='color:#00C2FF; margin-top:0;'>🗲 Agile Scrum & Kanban Delivery Frameworks</h2>
        <p style='color:#9090A8; line-height:1.4;'>Agile focuses on incremental delivery of product features. This guide covers role parameters, metrics estimation, and flow diagrams.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Scrum Team Roles & Responsibilities</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Product Owner:</b> Owns value optimization, backlog priorities, and product vision management.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Scrum Master:</b> Protects team processes, resolves blockages, and facilitates meetings.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Developers:</b> Own sprint estimates, planning, and task delivery to match target definitions of done.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Agile Metrics Reference</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Metric</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Calculation Strategy & Goal</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Velocity</td>
            <td style='padding:4px;'>Story points delivered per sprint. Forecasts future capacity limits.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Lead Time vs Cycle Time</td>
            <td style='padding:4px;'>Lead time: creation to completion. Cycle time: active work to completion. Tracks process efficiency.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>WIP Limits</td>
            <td style='padding:4px;'>Limits maximum active items per column to expose bottlenecks in pipelines.</td>
          </tr>
        </table>
    """,
    "Xcode": """
        <h2 style='color:#00C2FF; margin-top:0;'>🛠 Xcode Development & Diagnostics Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>Xcode is Apple's native environment. This guide specifies LLDB console routines, memory instrumentation, and target compilation settings.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. LLDB Diagnostic Commands</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Print description of an object
po userProfile

# Inject/change variables dynamically during execution
expr userProfile.accessLevel = "admin"

# Print thread backtrace to identify deadlock origins
bt

# Set symbolic breakpoint matching a namespace/class method
breakpoint set --name "-[UIViewController viewDidLoad]"
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Instruments Profiling Suite</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Time Profiler:</b> Records CPU thread samples every millisecond. Highlights hot paths and call stack delays.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Allocations & Leaks:</b> Tracks object instantiations and identifies memory zones lacking strong pointers cleanup.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Core Data:</b> Visualizes fetch operations, database transactions, and memory cache faults.</li>
        </ul>
    """,
    "Swift": """
        <h2 style='color:#00C2FF; margin-top:0;'>🦅 Swift & SwiftUI Architecture Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Swift is Apple's type-safe, compiled language. This manual defines SwiftUI views rendering, ARC memory retention, and actor concurrency.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. SwiftUI State Management & Properties</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Wrapper</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Target Scope & Lifecycles</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>@State</td>
            <td style='padding:4px;'>Local view properties. Instantiated and managed in storage by the framework.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>@Binding</td>
            <td style='padding:4px;'>Shared reference to State variables owned by parent views. Bypasses duplication.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>@StateObject</td>
            <td style='padding:4px;'>Owns instance of ObservableObject. Managed across view update redraws.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>@ObservedObject</td>
            <td style='padding:4px;'>Observes externally instantiated objects. Does not manage reference lifecycles.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Swift Concurrency: Actors & Structured Tasks</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Actors serialize access to state to prevent data races
actor BankAccount {
    private var balance: Double = 0.0
    
    func deposit(amount: Double) {
        balance += amount
    }
}

// MainActor limits execution to the main UI thread
@MainActor
class ViewModel: ObservableObject {
    @Published var displayBalance: String = "$0.00"
}
        </pre>
    """,
    "Fortran": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ Fortran Scientific Computing Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Fortran is optimized for numeric operations. This reference defines column-major array mechanics, procedures, and OpenMP parallel integration.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Column-Major Arrays & Slicing</h3>
        <p style='color:#9090A8; line-height:1.4;'>Fortran stores arrays in column-major order (memory addresses increment down columns, then across rows). Access patterns must match columns to utilize cache lines.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
program array_opt
    implicit none
    integer :: i, j
    real :: matrix(1000, 1000)
    
    ! Cache-Efficient loop order (outer loops handle columns, inner loops rows)
    do j = 1, 1000
        do i = 1, 1000
            matrix(i, j) = real(i + j)
        end do
    end do
end program array_opt
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. OpenMP Parallel Directives</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
subroutine run_parallel(inputs, outputs, size)
    implicit none
    integer, intent(in) :: size
    real, dimension(size), intent(in) :: inputs
    real, dimension(size), intent(out) :: outputs
    integer :: i
    
    !$OMP PARALLEL DO PRIVATE(i) SHARED(inputs, outputs)
    do i = 1, size
        outputs(i) = sqrt(inputs(i)) * 3.14159
    end do
    !$OMP END PARALLEL DO
end subroutine run_parallel
        </pre>
    """,
    "C#": """
        <h2 style='color:#00C2FF; margin-top:0;'>⧉ C# & .NET Platform Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>C# integrates high-level object modeling with systems-level memory utilities. This manual covers LINQ, garbage collection lifecycles, and memory spans.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. CLR Generational Garbage Collector</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Gen 0:</b> Houses new temporary objects. Collected frequently with minimal pause times.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Gen 1:</b> Buffer layer. Houses objects surviving Gen 0 collections.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Gen 2:</b> Houses long-lived objects. collected using full GC runs.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Large Object Heap (LOH):</b> Houses allocations over 85,000 bytes. Bypasses compaction to prevent performance penalties.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Memory Span & Stack Allocations</h3>
        <p style='color:#9090A8; line-height:1.4;'><code>Span&lt;T&gt;</code> and <code>ReadOnlySpan&lt;T&gt;</code> represent contiguous memory zones, allowing operations without heap allocations.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
using System;

public class MemoryOptimized {
    public void ProcessString(string data) {
        // Obtains slice of input string without heap memory overhead
        ReadOnlySpan<char> span = data.AsSpan();
        ReadOnlySpan<char> slice = span.Slice(0, 10);
        
        // Stack Allocations (garbage collector bypass)
        Span<byte> stackBuffer = stackalloc byte[128];
        stackBuffer[0] = 0xFF;
    }
}
        </pre>
    """,
    "C": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ C Low-Level Memory Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>C provides low-level abstractions and direct hardware mapping. This reference details pointer arithmetic, memory safety, and preprocessor metaprogramming.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Pointer Arithmetic & Allocation Safety</h3>
        <p style='color:#9090A8; line-height:1.4;'>Pointer arithmetic scales dynamically based on type width boundaries. Manual memory management requires guarding bounds explicitly.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <stdlib.h>
#include <stdio.h>

void allocate_buffer() {
    // malloc: raw byte allocation; calloc: zeroed allocation
    int *buffer = (int*) calloc(10, sizeof(int));
    if (buffer == NULL) return; // Guard allocation failure
    
    // Pointer Arithmetic moves address by: 2 * sizeof(int) bytes
    int *ptr = buffer + 2; 
    *ptr = 42;
    
    // realloc: resizes buffer; safety requires temp checks
    int *temp = (int*) realloc(buffer, 20 * sizeof(int));
    if (temp != NULL) {
        buffer = temp;
    } else {
        free(buffer); // Clean up if resize fails
        return;
    }
    
    free(buffer); // Prevent memory leaks
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Preprocessor Macros & Bit Fields</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Token pasting macro
#define DEFINE_STATE(state_name) int STATE_##state_name = 0

// Bit fields optimization
struct ControlRegister {
    unsigned int enable : 1;  // Uses 1 bit
    unsigned int mode   : 3;  // Uses 3 bits
    unsigned int flag   : 1;  // Uses 1 bit
}; // Packaged into single word allocation
        </pre>
    """,
    "Docker": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐳 Docker Engine & Containers Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Docker isolates apps using cgroups and namespaces. This guide maps out multi-stage builds, layering caches, and security isolation.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Layer Cache Optimization</h3>
        <p style='color:#9090A8; line-height:1.4;'>Docker cache invalidates downstream if target layer elements change. Copy dependencies first before modifying source files.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Stage 1: Build compilation
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci # Install dependencies first to cache this layer
COPY . .
RUN npm run build

# Stage 2: Clean runtime environment
FROM alpine:latest
RUN apk add --no-cache nodejs
WORKDIR /root/
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/index.js"]
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Container Security Isolation</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Non-root execution:</b> Enforce <code>USER node</code> or custom system users in Dockerfiles to prevent container escapes.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Read-Only Root File System:</b> Add <code>--read-only</code> flags at runtime to block malicious file modifications.</li>
        </ul>
    """,
    "Kubernetes": """
        <h2 style='color:#00C2FF; margin-top:0;'>☸ Kubernetes Orchestration Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>Kubernetes coordinates containers at scale. This reference outlines resource maps, service topologies, and diagnostic commands.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Service Topologies & Networks</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Service Type</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Mapping Strategy & Scope</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>ClusterIP</td>
            <td style='padding:4px;'>Exposes the Service on a cluster-internal IP. Default option. Only accessible inside cluster scopes.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>NodePort</td>
            <td style='padding:4px;'>Exposes the Service on each Node's IP at a static port (30000-32767).</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>LoadBalancer</td>
            <td style='padding:4px;'>Exposes the Service externally using a cloud provider's load balancer.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Diagnostics Commands Cheatsheet</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# View container resource limits utilization
kubectl top pods -n production

# Inspect events trace of crashing pods
kubectl describe pod/app-pod-name -n production

# Forward traffic to local port for manual database checking
kubectl port-forward svc/database-service 5432:5432

# Stream logs of multiple containers matching selector label
kubectl logs -f -l app=payment-processor --all-containers -n production
        </pre>
    """,
    "CSS": """
        <h2 style='color:#00C2FF; margin-top:0;'>🎨 CSS Layouts & Rendering Engine Mechanics</h2>
        <p style='color:#9090A8; line-height:1.4;'>CSS defines DOM layout rendering properties. This reference sheet details flexbox boundaries, grid structures, animation performance, and custom properties.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Flexbox Alignment & Grid Blueprints</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
/* Flexbox Blueprint: centers elements inside row */
.align-center {
    display: flex;
    justify-content: center;
    align-items: center;
}

/* Grid Layout: auto-adjusting column widths based on min/max margins */
.grid-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Composite Layer Animations & GPU Acceleration</h3>
        <p style='color:#9090A8; line-height:1.4;'>Layout modifications (e.g. `width`, `top`, `margin`) trigger browser redraw cycles. Utilize compositing properties to optimize GPU layers.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
/* Bypasses layout reflow cycles */
.fade-slide-box {
    will-change: transform, opacity;
    transition: transform 0.3s ease, opacity 0.3s ease;
    transform: translate3d(0, 0, 0); /* Forces GPU composition */
}
        </pre>
    """,
    "HTML": """
        <h2 style='color:#00C2FF; margin-top:0;'>🌐 HTML Document Structures & Semantics</h2>
        <p style='color:#9090A8; line-height:1.4;'>HTML structure defines pages natively. This manual covers accessibility guidelines, script loading lifecycles, and form validation attributes.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Semantic Layout outlines</h3>
        <p style='color:#9090A8; line-height:1.4;'>Elements like <code>&lt;header&gt;</code>, <code>&lt;nav&gt;</code>, <code>&lt;main&gt;</code>, <code>&lt;article&gt;</code>, <code>&lt;section&gt;</code>, and <code>&lt;footer&gt;</code> describe content types natively to search spiders and screen readers.</p>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Script Loading Lifecycles</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Load Strategy</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Execution Behavior & Timing</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>&lt;script&gt;</td>
            <td style='padding:4px;'>Blocks HTML parsing. Fetches and executes immediately.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>&lt;script async&gt;</td>
            <td style='padding:4px;'>Fetches in background. Pauses HTML parsing to execute immediately once loaded.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>&lt;script defer&gt;</td>
            <td style='padding:4px;'>Fetches in background. Executes only after HTML parser finishes document structure.</td>
          </tr>
        </table>
    """,
    "TypeScript": """
        <h2 style='color:#00C2FF; margin-top:0;'>⌨ TypeScript Advanced Typing Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>TypeScript adds static typing checks to JavaScript. This manual covers advanced mapped types, utility types, and generic parameters.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Advanced Mapped & Utility Types</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
interface UserProfile {
    id: string;
    email: string;
    token: string;
}

// Omit utility excludes keys from structural models
type PublicProfile = Omit<UserProfile, 'token'>;

// Partial utility marks all attributes optional
type UpdatedProfile = Partial<UserProfile>;
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Conditional & Infer Types</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Extracts the inner type from Promisified types
type UnpackPromise<T> = T extends Promise<infer U> ? U : T;

type ResolvedVal = UnpackPromise<Promise<string>>; // Resolves to: string
        </pre>
    """,
    "Java": """
        <h2 style='color:#00C2FF; margin-top:0;'>☕ Java JVM & Collections Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>Java coordinates execution via the JVM. This manual defines JVM layout segments, garbage collection designs, and stream optimizations.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. JVM Memory Allocation Architecture</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Heap Memory:</b> Shared zone housing objects. Subdivided into Young Generation (Eden, Survivor spaces) and Old Generation (Tenured space).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>JVM Stack:</b> Private thread memory storing stack frames, local variables, and primitive call references.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Metaspace:</b> Native off-heap memory storing class definitions and metadata structures.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Streams Pipeline Processing</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import java.util.List;
import java.util.stream.Collectors;

public class StreamProcessor {
    public List<String> getActiveUsers(List<User> users) {
        return users.parallelStream() // Runs on ForkJoinPool concurrently
            .filter(User::isActive)
            .map(User::getUsername)
            .collect(Collectors.toList()); // Terminal evaluation
    }
}
        </pre>
    """,
    "JavaScript": """
        <h2 style='color:#00C2FF; margin-top:0;'>🕮 JavaScript Complete Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>JavaScript handles non-blocking events via single-threaded runtime loops. This guide covers engines scoping, prototypes, and asynchronous execution loops.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Scope Closures & Prototype Inheritance</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Scope Closures: function retains enclosing variable access
function makeCounter() {
    let count = 0;
    return () => ++count;
}

// Prototype Inheritance chain
const animal = { eats: true };
const rabbit = Object.create(animal); // rabbit.__proto__ references animal
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Microtasks vs Macrotasks</h3>
        <p style='color:#9090A8; line-height:1.4;'>Promise callbacks route to the Microtask Queue. Timers and I/O route to the Macrotask Queue. Microtasks drain completely before yielding to subsequent macrotasks.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
console.log('1'); // Runs synchronously

setTimeout(() => console.log('2'), 0); // Macrotask Queue

Promise.resolve().then(() => console.log('3')); // Microtask Queue

console.log('4'); // Runs synchronously
// Output order: 1, 4, 3, 2
        </pre>
    """,
    "APIs": """
        <h2 style='color:#00C2FF; margin-top:0;'>🌐 REST, GraphQL & gRPC API Blueprints</h2>
        <p style='color:#9090A8; line-height:1.4;'>API structures broker distributed communication. This guide compares endpoints designs, protocol transports, and security handshakes.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Protocols Comparison</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Architecture</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Transport Protocol</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Payload Types</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Details</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>REST</td>
            <td style='padding:4px;'>HTTP/1.1 or HTTP/2</td>
            <td style='padding:4px;'>JSON, XML</td>
            <td style='padding:4px;'>Resource-oriented. Relies on HTTP verbs (GET, POST, PUT, DELETE).</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>GraphQL</td>
            <td style='padding:4px;'>HTTP/1.1 or HTTP/2</td>
            <td style='padding:4px;'>JSON</td>
            <td style='padding:4px;'>Single-endpoint queries. Allows clients to define returned schemas.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>gRPC</td>
            <td style='padding:4px;'>HTTP/2 exclusively</td>
            <td style='padding:4px;'>Protocol Buffers (Binary)</td>
            <td style='padding:4px;'>Highly optimized. Supports bi-directional streaming and binary serialization.</td>
          </tr>
        </table>
    """,
    "Uvicorn": """
        <h2 style='color:#00C2FF; margin-top:0;'>🚀 Uvicorn Production Deployment Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>Uvicorn processes ASGI signals asynchronously using <code>uvloop</code> and <code>httptools</code>. This guide templates production launch commands and Nginx routing configs.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Production Launch Configurations</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Run Uvicorn via Gunicorn wrapper to manage process lifecycles
gunicorn main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 0.0.0.0:8000 \\
    --keep-alive 65 \\
    --access-logfile access.log
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Nginx Reverse Proxy block</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
server {
    listen 80;
    server_name app.domain.internal;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
        </pre>
    """,
    "FastAPI": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚡ FastAPI Core Framework Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>FastAPI leverages Python type hints to enforce data validations (via Pydantic) and auto-generates OpenAPI definitions. This guide details dependency injections, database lifecycles, and scaling rules.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Dependency Injection & Yield Lifecycles</h3>
        <p style='color:#9090A8; line-height:1.4;'>Dependencies resolve hierarchically. Using yield allows wrapping operations with teardown procedures (e.g. database sessions cleanup).</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@host/db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()

# Yield dependency handles database session cleanup
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session  # Yields control to target route
        # Session automatically commits/closes when route finishes
        
@app.get("/records")
async def get_records(db: AsyncSession = Depends(get_db_session)):
    # process records query
    return {"status": "ok"}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Thread Pool Scaling: Async vs Sync routes</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>async def routes:</b> Execute directly on the ASGI event loop. Routes must not run blocking CPU calculations or synchronous I/O.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>def (sync) routes:</b> Offloaded to an external thread pool by the framework. Bypasses blocking issues on the main loop.</li>
        </ul>
    """
}
