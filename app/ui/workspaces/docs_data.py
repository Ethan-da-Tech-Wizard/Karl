# -*- coding: utf-8 -*-
"""
Exhaustive reference guides for Karl's Codex workspace.
Provides complete, self-contained documentation of grammar, compilers, runtime loops,
APIs, and optimization tactics for offline code generation.
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
        <p style='color:#9090A8; line-height:1.4;'>Python is an interpreted, multi-paradigm language. This manual defines namespaces resolution, descriptors protocol, asyncio executors, and CPython runtime internals.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Scope Resolution (LEGB) & Closure Compilation</h3>
        <p style='color:#9090A8; line-height:1.4;'>Variables resolve via Local, Enclosing, Global, and Built-in boundaries. Nested scopes capture enclosing states in cells, creating closures.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import functools

def limit_concurrency(max_active=5):
    def decorator(func):
        active_count = 0  # Enclosed scope variable stored in __closure__ cell
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal active_count  # Points to cell reference, bypassing new local binding
            if active_count >= max_active:
                raise RuntimeError("Rate limit hit")
            active_count += 1
            try:
                return func(*args, **kwargs)
            finally:
                active_count -= 1
        return wrapper
    return decorator
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Metaprogramming, Custom Descriptors & Slots</h3>
        <p style='color:#9090A8; line-height:1.4;'>Descriptors intercept property reads/writes. Metaclasses manipulate the <code>__new__</code> creation process of class types. <code>__slots__</code> suppresses the instance <code>__dict__</code> to save RAM.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Descriptor Protocol validation
class TypedField:
    def __init__(self, expected_type):
        self.expected_type = expected_type
    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"
    def __get__(self, instance, owner):
        if instance is None: return self
        return getattr(instance, self.private_name, None)
    def __set__(self, instance, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f"Expected {self.expected_type}")
        setattr(instance, self.private_name, value)

# Metaclass enforcing Slots allocation
class SlotEnforcer(type):
    def __new__(cls, name, bases, attrs):
        if "__slots__" not in attrs:
            # Generate immutable slots from current annotations
            attrs["__slots__"] = tuple(attrs.get("__annotations__", {}).keys())
        return super().__new__(cls, name, bases, attrs)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Asyncio, Event Loops & TaskGroups</h3>
        <p style='color:#9090A8; line-height:1.4;'>Asyncio cooperative multitasking executes coroutines on an event loop. <code>TaskGroup</code> (Python 3.11+) ensures tasks are completed or cancelled atomically.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import asyncio

async def fetch_endpoint(id: int, sem: asyncio.Semaphore) -> dict:
    async with sem:
        await asyncio.sleep(0.05)  # Cooperative yield
        return {"id": id, "data": "payload"}

async def run_pipeline():
    sem = asyncio.Semaphore(3)  # Max 3 concurrent operations
    async with asyncio.TaskGroup() as tg:
        # Spawns tasks concurrently; any exception triggers automatic cancel of peers
        tasks = [tg.create_task(fetch_endpoint(i, sem)) for i in range(10)]
    results = [t.result() for t in tasks]
    print(results)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. CPython Memory Layout & GIL Mechanics</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Topic</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Internal Mechanics</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Optimizations & APIs</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Reference Counting</td>
            <td style='padding:4px;'>Increments on assignments, decrements on delete. Zero value triggers immediate garbage collection.</td>
            <td style='padding:4px;'>Fast lookup. Bypasses stop-the-world phases. API: <code>sys.getrefcount(obj)</code>.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Generational GC</td>
            <td style='padding:4px;'>Generations 0, 1, and 2. GC tracks container types. Breaks cyclic dependencies by verifying reference decreases.</td>
            <td style='padding:4px;'>Configured via <code>gc.set_threshold()</code>. Can be disabled dynamically during batch processes.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Global Interpreter Lock</td>
            <td style='padding:4px;'>CPython uses a mutex to prevent threads from concurrently accessing memory structures. Limit to single-core.</td>
            <td style='padding:4px;'>Bypass using <code>multiprocessing</code>, or write C/Rust extensions releasing the lock.</td>
          </tr>
        </table>
    """,
    "C++": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ C++ Exhaustive Reference Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>C++ provides systems-level primitives alongside zero-overhead abstractions. This document covers alignment, value categories, smart pointer layout blocks, template constraints, and concurrent memory models.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Memory Alignment, Packing & Struct Padding</h3>
        <p style='color:#9090A8; line-height:1.4;'>CPUs access memory in aligned words (e.g. 4 or 8 bytes). Struct members must align to sizes, triggering compiler padding if misordered.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Padding triggers: char (1 byte) followed by double (8 bytes) -> 7 bytes padding
struct BadPadding {
    char a;      // 1 byte + 7 bytes padding
    double b;    // 8 bytes
    int c;       // 4 bytes + 4 bytes padding
}; // sizeof == 24 bytes

// Optimized ordering (largest to smallest)
struct GoodPadding {
    double b;    // 8 bytes
    int c;       // 4 bytes
    char a;      // 1 byte + 3 bytes padding
}; // sizeof == 16 bytes

#pragma pack(push, 1) // Disables padding completely (useful for networking structs)
struct PackedStruct {
    char a;
    double b;
}; // sizeof == 9 bytes
#pragma pack(pop)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Lvalues, Rvalues & Value Categories</h3>
        <p style='color:#9090A8; line-height:1.4;'>Move semantics transfer heap resource allocations instead of copying them. Universal references (<code>T&&</code>) use reference collapsing to preserve value types.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <utility>

// std::forward preserves lvalue/rvalue category (Perfect Forwarding)
template <typename T>
void factory(T&& arg) {
    process(std::forward<T>(arg));
}

// Move Constructor
class Buffer {
    size_t size;
    int* ptr;
public:
    Buffer(Buffer&& other) noexcept : size(other.size), ptr(other.ptr) {
        other.size = 0;
        other.ptr = nullptr; // Clear source to prevent double-free
    }
};
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Templates, SFINAE & C++20 Concepts</h3>
        <p style='color:#9090A8; line-height:1.4;'>Compile-time checking. SFINAE filters function candidates. C++20 Concepts constraint parameters directly.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <concepts>
#include <iostream>

// Define template concept
template <typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

template <Numeric T>
T multiply(T a, T b) {
    return a * b;
}

// SFINAE style (pre-C++20)
template <typename T>
typename std::enable_if<std::is_integral<T>::value, T>::type
add(T a, T b) {
    return a + b;
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Memory Models, Barriers & Concurrency</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Memory Order</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Behavior & CPU Pipeline Details</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Use Cases</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::memory_order_relaxed</td>
            <td style='padding:4px;'>Guarantees atomic operation; does not impose any execution ordering constraints on surrounding memory read/writes.</td>
            <td style='padding:4px;'>Counters, statistics, thread identifiers.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::memory_order_acquire / release</td>
            <td style='padding:4px;'>Acquire: prevents subsequent reads/writes from migrating before lock. Release: prevents preceding writes from migrating after unlock.</td>
            <td style='padding:4px;'>Mutex locks, spinlocks, message queues.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::memory_order_seq_cst</td>
            <td style='padding:4px;'>Sequential Consistency. Default option. Enforces total global order across all execution threads. Inserts hardware memory fence.</td>
            <td style='padding:4px;'>Multi-threaded state flags, strict memory operations.</td>
          </tr>
        </table>
    """,
    "SQL": """
        <h2 style='color:#00C2FF; margin-top:0;'>🖧 SQL Engine & Indexing Reference Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Relational database engines parse, rewrite, plan, and execute SQL statements. This guide explains parser pipelines, window frames, join algorithms, indexing, and transactions isolation.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. SQL Query Parser Execution Steps</h3>
        <p style='color:#9090A8; line-height:1.4;'>Syntactic order differs from logical processing order. Select aliases are invalid in WHERE or JOIN constraints since calculations run in subsequent phases:</p>
        <ol style='color:#9090A8; line-height:1.3;'>
          <li><b>FROM / JOIN:</b> Resolves datasets and compiles product tables.</li>
          <li><b>WHERE:</b> Filters records before groupings.</li>
          <li><b>GROUP BY:</b> Collapses matched rows into distinct grouping keys.</li>
          <li><b>HAVING:</b> Filters records based on aggregate fields.</li>
          <li><b>SELECT / WINDOW:</b> Projects columns and evaluates window metrics.</li>
          <li><b>DISTINCT:</b> Eliminates redundant duplicates.</li>
          <li><b>ORDER BY:</b> Sorts records based on defined fields.</li>
          <li><b>OFFSET / LIMIT:</b> Limits output rows.</li>
        </ol>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Window Framing & Partition Blocks</h3>
        <p style='color:#9090A8; line-height:1.4;'>Window clauses compute parameters across segments. Specifying boundaries prevents parsing the entire dataset partitions on each row iteration.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
SELECT employee_id, dept_id, salary,
       -- Cumulative running sum limited to the current partition
       SUM(salary) OVER (
           PARTITION BY dept_id 
           ORDER BY salary DESC
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) as running_sum,
       -- Moving average over 5 records
       AVG(salary) OVER (
           PARTITION BY dept_id
           ORDER BY salary DESC
           ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
       ) as moving_avg
FROM employees;
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Recursive CTE Hierarchies</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
WITH RECURSIVE assembly_tree AS (
    -- Anchor Member (Root part item)
    SELECT part_id, parent_id, name, 1 as level
    FROM parts WHERE parent_id IS NULL
    UNION ALL
    -- Recursive Member (Join next level child components)
    SELECT p.part_id, p.parent_id, p.name, at.level + 1
    FROM parts p
    JOIN assembly_tree at ON p.parent_id = at.part_id
)
SELECT * FROM assembly_tree ORDER BY level;
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Index Scans, Joins & ACID Isolation Levels</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Concept</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Mechanism & Behavior</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Tuning Strategy</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Index Seek vs Scan</td>
            <td style='padding:4px;'>Seek: traverses B-tree nodes straight to leaf keys. Scan: traverses the entire index list sequentially.</td>
            <td style='padding:4px;'>Index seeking requires specific predicates. Covered indexes prevent table read steps.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Join Algorithms</td>
            <td style='padding:4px;'>Hash Join: builds hash maps on smaller inputs. Merge Join: merges pre-sorted keys. Nested Loop: evaluates inputs row-by-row.</td>
            <td style='padding:4px;'>Enable index sorting to force Merge joins over heavy nested loops.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Serializable MVCC</td>
            <td style='padding:4px;'>Highest isolation tier. Implements range locks and snapshot serialization to prevent write-skew anomalies.</td>
            <td style='padding:4px;'>Postgres/MySQL use Multi-Version Concurrency control; read transactions do not block write locks.</td>
          </tr>
        </table>
    """,
    "Rust": """
        <h2 style='color:#00C2FF; margin-top:0;'>🦀 Rust Memory, Lifetimes & Systems Programming Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Rust ensures memory safety at compile-time without garbage collectors by implementing strict borrowing and ownership rules, lifetime tracking, and algebraic type models.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Ownership, Borrow Checker & Lifetimes</h3>
        <p style='color:#9090A8; line-height:1.4;'>Variables own heap assets exclusively. You can lease resources using immutable references (<code>&T</code>) or a single mutable reference (<code>&mut T</code>). Lifetimes enforce compile-time bounds constraints.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Segment captures a slice, referencing array memory
struct Segment<'a> {
    buffer: &'a [u8], // Reference must not outlive the array lifetime 'a
}

// Lifetime Elision: Compiler maps input lifetimes to output references
fn parse_header<'a>(data: &'a [u8]) -> Result<Segment<'a>, &'static str> {
    if data.len() < 4 { return Err("Too short"); }
    Ok(Segment { buffer: &data[..4] })
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Trait Dispatch: Static vs Dynamic</h3>
        <p style='color:#9090A8; line-height:1.4;'>Polymorphism resolves using static templates generation (monomorphization) or dynamic virtual table pointer redirects.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
trait Target {
    fn execute(&self);
}

// Static Dispatch (Generates a copy of function for each type. Zero runtime overhead)
fn run_static(item: impl Target) {
    item.execute();
}

// Dynamic Dispatch (Requires a vtable pointer lookup. Bypasses code expansion)
fn run_dynamic(item: &dyn Target) {
    item.execute(); // Traverses vtable pointer at runtime
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Concurrency Safety: Send, Sync & Smart Containers</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Container</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Target Allocation & Thread-Safety Behavior</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Box&lt;T&gt;</td>
            <td style='padding:4px;'>Smart pointer for heap allocation. Exclusive ownership. Implements <code>Send</code> if T is <code>Send</code>.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Rc&lt;T&gt; / RefCell&lt;T&gt;</td>
            <td style='padding:4px;'>Single-threaded reference counting. RefCell allows mutating contents through immutable shells (interior mutability). Not thread-safe.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Arc&lt;T&gt; / Mutex&lt;T&gt;</td>
            <td style='padding:4px;'>Atomic Reference Counter. Mutex guarantees exclusive write locks. Safe to share across execution threads.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Unsafe & FFI boundaries</h3>
        <p style='color:#9090A8; line-height:1.4;'>Unsafe blocks enable raw memory dereferencing, mutating static fields, and calling foreign C bindings.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Interacting with external C headers
extern "C" {
    fn abs(input: i32) -> i32;
}

fn raw_math() {
    let mut num = 42;
    let raw_ptr = &mut num as *mut i32;
    unsafe {
        // Dereference raw pointer directly, bypassing borrow rules
        *raw_ptr = abs(-100);
    }
}
        </pre>
    """,
    "React": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚛ React Architecture & Lifecycle Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>React organizes interfaces using a declarative, component-based paradigm. This manual covers rendering lifecycles, hooks optimization, and React Server Components.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Fiber Reconciler & Concurrent Execution</h3>
        <p style='color:#9090A8; line-height:1.4;'>React leverages Fiber nodes (virtual DOM) to pause and prioritize rendering workloads. In concurrent mode, updates execute on parallel threads without locking main threads.</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Render Phase:</b> Asynchronous traversal compiling the virtual tree. Can be interrupted by user inputs.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Commit Phase:</b> Synchronous operations writing mutations directly to DOM. Runs side-effects once complete.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Advanced Hooks API Reference</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Hook</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Lifecycle Mechanism & Targets</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useRef(init)</td>
            <td style='padding:4px;'>Allocates mutable objects persisting across renders. Does not trigger redraws on change. Holds DOM nodes.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useReducer(reducer, state)</td>
            <td style='padding:4px;'>State engine variant. Decouples state mutations into action dispatch blocks.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useMemo(()=>val, deps)</td>
            <td style='padding:4px;'>Caches complex data operations. Bypasses execution until dependencies mutate.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useCallback(fn, deps)</td>
            <td style='padding:4px;'>Caches function instances to prevent children from re-rendering due to changing property references.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Performance Tuning: Virtualization & Custom Hooks</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import { useState, useEffect, useRef } from 'react';

// Custom Hook tracking window intersections
export function useLazyLoad(options) {
    const targetRef = useRef(null);
    const [isIntersecting, setIsIntersecting] = useState(false);

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
                setIsIntersecting(true);
                observer.unobserve(entry.target); // Unsubscribe once visible
            }
        }, options);

        if (targetRef.current) observer.observe(targetRef.current);
        return () => observer.disconnect();
    }, [options]);

    return [targetRef, isIntersecting];
}
        </pre>
    """,
    "Node.js": """
        <h2 style='color:#00C2FF; margin-top:0;'>⬢ Node.js Architecture & Engine Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Node.js integrates Google V8 execution with libuv. This manual explains event loops, custom streams, backpressure boundaries, and clustering configurations.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Libuv Event Loop & Microtask Priority</h3>
        <p style='color:#9090A8; line-height:1.4;'>The event loop executes asynchronous callbacks across six key phases. Microtasks (Promise resolutions and process.nextTick) execute completely before yielding to the next phase.</p>
        <ol style='color:#9090A8; line-height:1.3;'>
          <li><b>Timers:</b> Processes scheduled <code>setTimeout</code> and <code>setInterval</code> loops.</li>
          <li><b>Pending:</b> Executes deferred connection callbacks.</li>
          <li><b>Idle, Prepare:</b> System indicators.</li>
          <li><b>Poll:</b> Blocks to retrieve new I/O events, executing connection callbacks.</li>
          <li><b>Check:</b> Executes <code>setImmediate</code> hooks.</li>
          <li><b>Close:</b> Processes socket/file close callbacks.</li>
        </ol>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Streams backpressure & Pipelines</h3>
        <p style='color:#9090A8; line-height:1.4;'>Streams minimize memory allocations by processing data in chunks. Backpressure pauses source reading operations if write queues fill up.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
const { pipeline, Transform } = require('stream');
const fs = require('fs');

const uppercaseTransformer = new Transform({
    transform(chunk, encoding, callback) {
        callback(null, chunk.toString().toUpperCase());
    }
});

// pipeline coordinates backpressure and handles error cleanups
pipeline(
    fs.createReadStream('input.txt'),
    uppercaseTransformer,
    fs.createWriteStream('output.txt'),
    (err) => {
        if (err) console.error('Stream failed:', err);
    }
);
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Threading vs Cluster Process Scaling</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Cluster Module:</b> Spawns child processes using <code>child_process.fork()</code>. All child processes share port allocations, using round-robin routing handles to balance load.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Worker Threads:</b> Spawns separate threads sharing memory zones via <code>SharedArrayBuffer</code>. Ideal for intensive computing within single process scopes.</li>
        </ul>
    """,
    "Go": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐹 Go Runtime & Concurrency Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>Go runs on a runtime compiler that targets native hardware. This document details scheduling loops, channels CSP model, array/slice bounds, and panic recovery.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. The GMP Scheduler</h3>
        <p style='color:#9090A8; line-height:1.4;'>The Go runtime handles concurrent execution multiplexing three structures:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>G (Goroutine):</b> Holds call stack, instruction pointer, and scheduling details. Allocation overhead is extremely low (starts at 2KB).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>M (Machine):</b> Represents OS threads. Managed directly by the kernel scheduler.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>P (Processor):</b> Represents logical context resource limits. Handles queues of runnable goroutines, stealing workloads from other processors if queues empty out.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Channels CSP State Lookup Matrix</h3>
        <p style='color:#9090A8; line-height:1.4;'>Channels coordinate Goroutine data sharing. Select blocks multiplex execution across active channel operations.</p>
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
        <h2 style='color:#00C2FF; margin-top:0;'>🗲 Agile Agile & Scrum Frameworks</h2>
        <p style='color:#9090A8; line-height:1.4;'>Agile processes organize software pipelines incrementally. This reference details Scrum roles, planning poker rules, and team flow metrics.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Scrum Team Roles</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Product Owner:</b> Owns value optimizations, user story specs, and roadmap priorities.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Scrum Master:</b> Eliminates pipeline roadblocks, coaches developers, and facilitates meetings.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Developers:</b> Own sprint task estimation, implementation plans, and quality outputs.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Agile Metrics Reference</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Metric</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Internal Mechanics</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Sprint Impact</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Velocity</td>
            <td style='padding:4px;'>Story points delivered per sprint.</td>
            <td style='padding:4px;'>Forecasts future capacity limits.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Lead vs Cycle Time</td>
            <td style='padding:4px;'>Lead: creation to release. Cycle: active development to release.</td>
            <td style='padding:4px;'>Measures development velocity and workflow efficiency.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>WIP Limits</td>
            <td style='padding:4px;'>Imposes limits on maximum active items per column.</td>
            <td style='padding:4px;'>Exposes task bottlenecks in the deployment pipelines.</td>
          </tr>
        </table>
    """,
    "Xcode": """
        <h2 style='color:#00C2FF; margin-top:0;'>🛠 Xcode Developer & Diagnostics Reference</h2>
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
# Now let's inject a gigantic body of reference material into all language manuals to cover them in exhaustive detail.
# This makes it fully self-contained for offline code generators.

# Python Exhaustive Addition
DEFAULT_LIBRARY["Python"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. Standard Library Deep Dive & Patterns</h3>
        <p style='color:#9090A8; line-height:1.4;'>The Python Standard Library provides modules optimized in C for common algorithmic operations:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>collections:</b> <code>deque</code> (thread-safe double-ended queue with O(1) appends/pops), <code>defaultdict</code>, <code>Counter</code>.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>itertools:</b> <code>chain</code>, <code>groupby</code>, <code>permutations</code>, <code>combinations</code>. Lazy generators that keep memory footprints at O(1).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>functools:</b> <code>lru_cache(maxsize=128)</code> (memoization), <code>partial</code> (argument pre-binding), <code>reduce</code>.</li>
        </ul>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
from collections import deque
import itertools

# BFS implementation using deque
def bfs(graph, start):
    visited, queue = set([start]), deque([start])
    while queue:
        vertex = queue.popleft()
        for neighbor in graph[vertex]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited

# Infinite counter combined with zip to paginate data
for index, item in zip(itertools.count(start=1, step=2), ["a", "b", "c"]):
    print(f"Index: {index}, Item: {item}")
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>6. Diagnostics, Profiling & Type Hints</h3>
        <p style='color:#9090A8; line-height:1.4;'>Compile-time type checking via static tools (e.g. MyPy) uses the <code>typing</code> module. Profiles CPU execution using <code>cProfile</code> and memory using <code>tracemalloc</code>.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import cProfile
from typing import Callable, TypeVar, Generator

T = TypeVar('T')

# Generic Type signature for generic generator execution
def stream_processor(stream: Generator[T, None, None], process: Callable[[T], T]) -> Generator[T, None, None]:
    for item in stream:
        yield process(item)

# CPU profiling hook
def run_profile():
    pr = cProfile.Profile()
    pr.enable()
    # targeted routine here
    pr.disable()
    pr.print_stats(sort='cumulative')
        </pre>
"""

# C++ Exhaustive Addition
DEFAULT_LIBRARY["C++"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. STL Containers Internals & Performance Tuning</h3>
        <p style='color:#9090A8; line-height:1.4;'>STL containers allocation strategies define their runtime complexity boundaries:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>std::vector:</b> Contiguous memory array. Size grows exponentially (growth factor 1.5x in MSVC, 2x in GCC). Reallocation invalidates all active iterators. Always use <code>.reserve()</code>.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>std::unordered_map:</b> Hash table with bucket chain array. Load factor > 1.0 triggers rehashing. Cache-unfriendly due to node allocation layouts. Use custom allocators or <code>std::map</code> (Red-Black tree) if memory sorting is required.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Small String Optimization (SSO):</b> <code>std::string</code> stores strings &lt; 15-22 characters directly on stack inside instance payload, bypassing heap operations.</li>
        </ul>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <vector>
#include <unordered_map>

void optimize_stl() {
    std::vector<int> vec;
    vec.reserve(10000); // Pre-allocates heap to prevent 13 reallocation iterations
    
    std::unordered_map<int, std::string> map;
    map.reserve(1000); // Presets bucket size to prevent load factor trigger rehashing
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>6. Advanced Concurrency: std::jthread & Latches</h3>
        <p style='color:#9090A8; line-height:1.4;'>C++20 introduces cooperatively interruptible threads (<code>std::jthread</code>) that join automatically on destruction, alongside latches and barriers.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <thread>
#include <latch>
#include <vector>
#include <iostream>

void run_task(std::latch& work_done, int id) {
    // Perform processing step
    work_done.count_down(); // Decrements sync counter
}

int main() {
    std::latch sync_point(5); // Synchronization point for 5 threads
    std::vector<std::jthread> pool;
    for (int i = 0; i < 5; ++i) {
        pool.emplace_back(run_task, std::ref(sync_point), i);
    }
    sync_point.wait(); // Blocks main thread until all 5 threads count down
    std::cout << "All workers ready" << std::endl;
}
        </pre>
"""

# SQL Exhaustive Addition
DEFAULT_LIBRARY["SQL"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. Execution Plan Tuning & Covered Indexes</h3>
        <p style='color:#9090A8; line-height:1.4;'>Query tuning requires inspecting execution pipelines via <code>EXPLAIN ANALYZE</code>. An index covers a query if the B-Tree holds all requested columns, bypassing secondary heap lookup steps.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
-- Composite Index covering filter and selection attributes
CREATE INDEX idx_user_status_email ON users(status) INCLUDE (email);

-- Query execution plan check
EXPLAIN ANALYZE
SELECT email FROM users 
WHERE status = 'active' AND created_at > '2026-01-01';
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>6. Isolation Anomalies & Lock Granularity</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Isolation Level</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Dirty Reads</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Non-Repeatable Reads</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Phantom Reads</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Read Uncommitted</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Read Committed</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Repeatable Read</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#FF5555;'>Possible (depends on DB)</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Serializable</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
          </tr>
        </table>
"""

# Rust Exhaustive Addition
DEFAULT_LIBRARY["Rust"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. Advanced Lifetimes: Variance & Subtyping</h3>
        <p style='color:#9090A8; line-height:1.4;'>Variance defines how type parameters relate. <code>&'a T</code> is covariant over <code>'a</code> and <code>T</code>. <code>&mut T</code> is invariant over <code>T</code> to prevent type mutations violating safety guidelines.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Covariance: 'a outlives 'b implies &'a T can subtype &'b T
fn assign_lifetime<'a, 'b: 'a>(short: &'a str, long: &'b str) -> &'a str {
    long // Safe subtyping coercion
}

// Invariance: Mutability forces invariant types
fn mutate_invariant<'a>(r: &mut &'a str, temp: &'static str) {
    // If &mut T were covariant, this could write static strings into shorter scopes,
    // leading to use-after-free bugs.
    *r = temp;
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>6. Pinning & Future State Machine Internals</h3>
        <p style='color:#9090A8; line-height:1.4;'>Async functions compile down to self-referential generator state machines. <code>Pin&lt;P&gt;</code> guarantees objects won't be moved in memory, keeping self-references valid.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
use std::pin::Pin;
use std::future::Future;
use std::task::{Context, Poll};

struct DelayedCounter {
    value: i32,
}

impl Future for DelayedCounter {
    type Output = i32;
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        // Safe access to inner values once guaranteed unmovable
        let this = self.get_mut();
        if this.value > 5 {
            Poll::Ready(this.value)
        } else {
            this.value += 1;
            cx.waker().wake_by_ref(); // Queue task back onto scheduler loop
            Poll::Pending
        }
    }
}
        </pre>
"""

# React Exhaustive Addition
DEFAULT_LIBRARY["React"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. React Server Components & Hydration Pipelines</h3>
        <p style='color:#9090A8; line-height:1.4;'>React Server Components (RSC) evaluate on server runtimes, compiling markup output as a JSON-serialized stream payload. Client components form boundary slots initialized via client hydration.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Server Component (Default in Next.js App Router)
import DatabaseConnection from '@/lib/db';
import ClientCard from './ClientCard'; // Client Component boundary

export default async function ProductCatalog() {
    // Runs directly on server, bypassing client bundle steps
    const products = await DatabaseConnection.query("SELECT * FROM products");
    
    return (
        <div>
            <h2>Server Product Catalog</h2>
            {products.map(p => (
                // Client boundary slots. Data is serialized down
                <ClientCard key={p.id} initialLikes={p.likes} details={p} />
            ))}
        </div>
    );
}
        </pre>
"""

# Node.js Exhaustive Addition
DEFAULT_LIBRARY["Node.js"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Advanced Worker Thread Concurrency</h3>
        <p style='color:#9090A8; line-height:1.4;'>Spawning threads enables offloading CPU-bound tasks. SharedArrayBuffer allows threads to read/write shared memory addresses using the <code>Atomics</code> module.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
const { Worker, isMainThread, parentPort } = require('worker_threads');

if (isMainThread) {
    // Main Thread allocates 4 bytes shared buffer
    const sharedBuffer = new SharedArrayBuffer(4);
    const int32Array = new Int32Array(sharedBuffer);
    int32Array[0] = 100;
    
    const worker = new Worker(__filename);
    worker.postMessage(sharedBuffer);
    
    worker.on('message', () => {
        // Atomic read ensures operations are completed securely across threads
        console.log('Value updated atomically:', Atomics.load(int32Array, 0));
    });
} else {
    parentPort.on('message', (sharedBuffer) => {
        const int32Array = new Int32Array(sharedBuffer);
        // Safely add 50 atomically
        Atomics.add(int32Array, 0, 50);
        parentPort.postMessage('done');
    });
}
        </pre>
"""

# Go Exhaustive Addition
DEFAULT_LIBRARY["Go"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Go Slice & Map Mechanics</h3>
        <p style='color:#9090A8; line-height:1.4;'>Go slices reference array structures. Reaching slice capacities triggers reallocation, doubling array sizes (or increasing by 1.25x for elements > 256). Maps allocate key-value buckets inside memory cells.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
package main

import "fmt"

func sliceGrowth() {
    // Make slice with len=0, cap=3. Prevents allocation overhead up to index 3
    s := make([]int, 0, 3)
    s = append(s, 1, 2, 3)
    
    // This append exceeds cap=3, triggering reallocation:
    // A new array of cap=6 is allocated, data is copied, and s is updated.
    s = append(s, 4)
    fmt.Printf("len: %d, cap: %d", len(s), cap(s)) // len: 4, cap: 6
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. Defer Stack, Panics & Recoveries</h3>
        <p style='color:#9090A8; line-height:1.4;'>Defer statements evaluate arguments immediately but execute in LIFO order when surrounding scopes return. Recover catches panic exceptions only if evaluated within deferred routines.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
package main

import "fmt"

func handleTransaction() {
    defer func() {
        if r := recover(); r != NULL {
            fmt.Println("Transaction recovered from error:", r)
        }
    }()
    
    fmt.Println("Running database steps...")
    panic("Database connection lost") // Triggers unwinding stack
    fmt.Println("This line is bypassed")
}
        </pre>
"""

# Agile Exhaustive Addition
DEFAULT_LIBRARY["Agile"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Agile Story Estimation & Prioritization</h3>
        <p style='color:#9090A8; line-height:1.4;'>Teams estimate items using relative scales. Prioritizations balance developer capacity against business value impact.</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Fibonacci Scale (1, 2, 3, 5, 8, 13):</b> Minimizes granular planning errors on large, ambiguous items.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>MoSCoW Rules:</b> Categorizes backlog items into Must Have, Should Have, Could Have, and Won't Have.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>WSJF (Weighted Shortest Job First):</b> Prioritizes tasks using: <code>Cost of Delay / Job Duration</code>.</li>
        </ul>
"""

# Xcode Exhaustive Addition
DEFAULT_LIBRARY["Xcode"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Custom Xcode xcconfig & Build Configurations</h3>
        <p style='color:#9090A8; line-height:1.4;'>Build settings can be customized using <code>.xcconfig</code> files, decoupling targets variables from project binaries.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Release.xcconfig configuration
SERVER_URL = https:/\\/api.release.domain
GCC_OPTIMIZATION_LEVEL = s // Optimize binaries for size
OTHER_SWIFT_FLAGS = -D RELEASE_LOGS
        </pre>
"""

# Swift Exhaustive Addition
DEFAULT_LIBRARY["Swift"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Swift Concurrency: Actors & Reentrancy</h3>
        <p style='color:#9090A8; line-height:1.4;'>Actors serialize memory access. Execution yields at <code>await</code> boundaries, allowing other tasks to execute (actor reentrancy). View updates must route to the MainActor.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import Foundation

actor FeedCache {
    private var cachedData: [String: Data] = [:]
    
    // Actor method handles concurrent reads/writes safely
    func write(_ data: Data, forKey key: String) {
        cachedData[key] = data
    }
}

@MainActor
class FeedViewModel: ObservableObject {
    @Published var feedItems: [String] = []
    private let cache = FeedCache()
    
    func updateFeed() async {
        // Runs on MainActor/UI Thread
        self.feedItems = ["Loading..."]
        // Async steps offload execution to concurrent thread pools
        await cache.write(Data(), forKey: "feed_cache")
        self.feedItems = ["Updated Feed"]
    }
}
        </pre>
"""

# Fortran Exhaustive Addition
DEFAULT_LIBRARY["Fortran"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Coarray Parallelism (PGAS)</h3>
        <p style='color:#9090A8; line-height:1.4;'>Fortran supports Partitioned Global Address Space (PGAS) models natively using coarrays. Variables designate square brackets representing parallel execution units (images).</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
program coarray_sample
    implicit none
    integer :: value[*] ! Coarray variable allocated on all images
    integer :: img, num_imgs
    
    img = this_image()
    num_imgs = num_images()
    
    value = img * 10 ! Assign local value
    sync all ! Synchronization barrier
    
    if (img == 1) then
        ! Retrieve remote value from image 2
        print *, "Image 1 read value from Image 2: ", value[2]
    end if
end program coarray_sample
        </pre>
"""

# C# Exhaustive Addition
DEFAULT_LIBRARY["C#"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. ASP.NET Core Middleware & DI Lifecycles</h3>
        <p style='color:#9090A8; line-height:1.4;'>Middleware components form requests-response pipelines. Dependencies validate lifetimes depending on scopes:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Transient:</b> Spawns a new instance on every request call.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Scoped:</b> Spawns a single instance per HTTP connection session.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Singleton:</b> Spawns a single instance on startup that is shared across all request calls.</li>
        </ul>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

// Register dependencies with appropriate lifetimes
builder.Services.AddTransient<IEmailService, EmailService>();
builder.Services.AddScoped<IDbContext, AppDbContext>();
builder.Services.AddSingleton<ICacheProvider, RedisCacheProvider>();

var app = builder.Build();

// Custom inline middleware component
app.Use(async (context, next) => {
    // Before route processing
    context.Response.Headers.Add("X-Execution-Header", "DotNetCore");
    await next(context); // Yields to subsequent middleware components
    // After route processing
});

app.MapGet("/", () => "Pipeline executing");
app.Run();
        </pre>
"""

# C Exhaustive Addition
DEFAULT_LIBRARY["C"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Unions, Struct alignment & Bit Packing</h3>
        <p style='color:#9090A8; line-height:1.4;'>Unions store different types in the same memory address location. Struct packing disables padding to optimize layout allocations.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <stdio.h>

// Disable alignment padding to restrict size limits
#pragma pack(push, 1)
struct AlignedHeader {
    char type;     // 1 byte
    int version;   // 4 bytes
}; // sizeof == 5 bytes (would be 8 bytes with default padding)
#pragma pack(pop)

union DataPacket {
    int value;
    char bytes[4]; // Allows accessing integer bytes directly (type punning)
};

void run_diagnostics() {
    union DataPacket packet;
    packet.value = 0x12345678;
    if (packet.bytes[0] == 0x78) {
        printf("System CPU Architecture: Little Endian\\n");
    }
}
        </pre>
"""

# Docker Exhaustive Addition
DEFAULT_LIBRARY["Docker"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Network Topologies & Port Mappings</h3>
        <p style='color:#9090A8; line-height:1.4;'>Containers run isolated network stacks. Custom bridge networks resolve container names to IP addresses dynamically.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Create bridge network
docker network create app-net

# Run database container inside custom network
docker run -d --name pg-db --network app-net -e POSTGRES_PASSWORD=pass postgres:alpine

# Run web app container inside same network, exposing port 8080
docker run -d --name web-app --network app-net -p 8080:8000 node:alpine
# web-app can resolve pg-db host address dynamically via DNS names: 'pg-db:5432'
        </pre>
"""

# Kubernetes Exhaustive Addition
DEFAULT_LIBRARY["Kubernetes"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Persistent Volumes & Claim Configurations</h3>
        <p style='color:#9090A8; line-height:1.4;'>Pods are ephemeral. Decouple storage setups using PersistentVolumes (PV) and PersistentVolumeClaims (PVC).</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: static-pvc
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: web
          image: nginx:alpine
          volumeMounts:
            - mountPath: "/usr/share/nginx/html"
              name: data-volume
      volumes:
        - name: data-volume
          persistentVolumeClaim:
            claimName: static-pvc
        </pre>
"""

# CSS Exhaustive Addition
DEFAULT_LIBRARY["CSS"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. CSS Custom Properties & responsive clamp limits</h3>
        <p style='color:#9090A8; line-height:1.4;'>CSS variables support lexical scopes. Use responsive functions like clamp to scale font sizes dynamically without media query overhead.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
:root {
    --primary-accent: #00C2FF;
    --font-size-adaptive: clamp(1rem, 2vw + 0.5rem, 2.5rem);
}

.title-adaptive {
    color: var(--primary-accent);
    font-size: var(--font-size-adaptive);
    padding: calc(var(--font-size-adaptive) * 0.5);
}
        </pre>
"""

# HTML Exhaustive Addition
DEFAULT_LIBRARY["HTML"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Form Constraints & Accessibility ARIA Roles</h3>
        <p style='color:#9090A8; line-height:1.4;'>Browser native validations use regular expressions constraint attributes. ARIA roles allow accessibility features to align with DOM structures.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
<!-- Accessible form with constraint validations -->
<form id="billingForm">
    <label for="cardNumber">Card Number:</label>
    <input type="text" id="cardNumber" required
           pattern="\\\\d{16}"
           aria-required="true"
           aria-describedby="cardHelp" />
    <span id="cardHelp" role="tooltip">Must be exactly 16 digits</span>
    <button type="submit">Pay</button>
</form>
        </pre>
"""

# TypeScript Exhaustive Addition
DEFAULT_LIBRARY["TypeScript"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. TS Compiler Configurations & Flags</h3>
        <p style='color:#9090A8; line-height:1.4;'>TS compiler validations enforce safety limits dynamically when configurations are structured. Standard configurations reside in <code>tsconfig.json</code>.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,                 // Enforces all strict type checking flags
    "noImplicitAny": true,          // Error out on inferred 'any' bindings
    "strictNullChecks": true,       // Exclude null/undefined from variable assignments
    "noUnusedLocals": true,         // Error out on unused variables
    "esModuleInterop": true
  }
}
        </pre>
"""

# Java Exhaustive Addition
DEFAULT_LIBRARY["Java"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. JVM Garbage Collectors & Virtual Threads</h3>
        <p style='color:#9090A8; line-height:1.4;'>Garbage Collection (GC) tracks object generation boundaries. Java 21+ Virtual Threads offload concurrency blockages from OS thread limits.</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>G1 Collector:</b> Segments heap memory into regional slices. Collects regions concurrently to minimize execution pause times.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>ZGC (Z Garbage Collector):</b> Ultra low-latency collector. Performs compaction concurrently with application execution, reducing pause times to sub-milliseconds.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Virtual Threads (Project Loom):</b> Lightweight, M:N multiplexed threads. Bypasses OS thread count constraints.</li>
        </ul>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import java.util.concurrent.Executors;

public class ConcurrencySystem {
    public void startVirtualWorkers() {
        // Spawns tasks on virtual thread pools
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 1000; i++) {
                final int taskId = i;
                executor.submit(() -> {
                    System.out.println("Processing task " + taskId);
                });
            }
        } // Executor auto-closes on completion
    }
}
        </pre>
"""

# JavaScript Exhaustive Addition
DEFAULT_LIBRARY["JavaScript"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. ES6+ Proxies & Reflection</h3>
        <p style='color:#9090A8; line-height:1.4;'>Proxies intercept and redefine standard object operations. Reflect provides access to target object descriptors.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
const targetData = { name: "admin" };

const dataProxy = new Proxy(targetData, {
    // Intercept property reads
    get(target, prop, receiver) {
        console.log(`Accessing property: ${prop}`);
        return Reflect.get(target, prop, receiver);
    },
    // Intercept property writes
    set(target, prop, value, receiver) {
        if (prop === "id" && typeof value !== "number") {
            throw new TypeError("ID must be numeric");
        }
        return Reflect.set(target, prop, value, receiver);
    }
});

dataProxy.id = 500; // Succeeds
// dataProxy.id = "bad"; // Throws TypeError
        </pre>
"""

# APIs Exhaustive Addition
DEFAULT_LIBRARY["APIs"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Security: OAuth2, JWT & CORS preflights</h3>
        <p style='color:#9090A8; line-height:1.4;'>JWTs encode user attributes securely. CORS preflights verify server authorization headers using HTTP OPTIONS requests.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
-- Example CORS preflight request/response headers
-- Client sends:
OPTIONS /api/data HTTP/1.1
Host: api.domain
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Authorization

-- Server responds:
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Authorization
        </pre>
"""

# Uvicorn Exhaustive Addition
DEFAULT_LIBRARY["Uvicorn"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. ASGI Lifecycle & Connection States</h3>
        <p style='color:#9090A8; line-height:1.4;'>Uvicorn maps incoming HTTP requests to ASGI applications, coordinating connection lifecycles via lifespan events.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# ASGI application structure
async def app(scope, receive, send):
    assert scope['type'] == 'http'
    
    # Wait for request payload events
    event = await receive()
    
    # Send HTTP headers and body response
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            [b'content-type', b'text/plain']
        ]
    })
    await send({
        'type': 'http.response.body',
        'body': b'Hello from ASGI app'
    })
        </pre>
"""

# FastAPI Exhaustive Addition
DEFAULT_LIBRARY["FastAPI"] += """
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Async SQLAlchemy & Scoped Sessions</h3>
        <p style='color:#9090A8; line-height:1.4;'>FastAPI coordinates asynchronous database connections by combining yield dependencies with SQLAlchemy's asyncio mapping layers.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

Base = declarative_base()
engine = create_async_engine("sqlite+aiosqlite:///./test.db")

async def get_session() -> AsyncSession:
    async with AsyncSession(engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

app = FastAPI()

@app.get("/users")
async def read_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()
        </pre>
"""
