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
        
        <h4 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Programmatic Prompt Manipulation</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Dynamic Variable Interpolation, Context Budget Trimming, Cognitive State Compression, and Tag Stripping.</p>
    """,
    "Python": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐍 Python Reference Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Python is a multi-paradigm language. This guide details namespaces scoping, metaclass bindings, descriptor protocols, cooperative concurrency, and memory GC thresholds.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Namespaces Scopes (LEGB) & Closure Cells</h3>
        <p style='color:#9090A8; line-height:1.4;'>CPython resolves variables dynamically traversing Local, Enclosing, Global, and Built-in boundaries. Closures store outer variable references in cell arrays inside the <code>__closure__</code> attribute.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import functools

def rate_limiter(max_invocations: int):
    def decorator(func):
        counter = 0  # Captured variable compiled into a cell reference
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal counter  # Bypasses new local binding, mutating cell storage
            counter += 1
            if counter > max_invocations:
                raise RuntimeError("Execution limit hit")
            return func(*args, **kwargs)
        return wrapper
    return decorator
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Metaprogramming & Descriptors</h3>
        <p style='color:#9090A8; line-height:1.4;'>Descriptors hook attribute access. Metaclasses run during class compilation to customize namespaces before instantiating types.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
class StringField:
    def __set_name__(self, owner, name):
        self.storage_name = f"_{name}"
    def __get__(self, instance, owner):
        if instance is None: return self
        return getattr(instance, self.storage_name, "")
    def __set__(self, instance, value):
        if not isinstance(value, str):
            raise TypeError("Expected string value")
        setattr(instance, self.storage_name, value)

class SchemaMetaclass(type):
    def __new__(cls, name, bases, attrs):
        # Enforce slots allocation based on declared string fields to optimize RAM
        fields = [k for k, v in attrs.items() if isinstance(v, StringField)]
        if fields:
            attrs["__slots__"] = tuple(f"_{f}" for f in fields)
        return super().__new__(cls, name, bases, attrs)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Asyncio, Event Loops & TaskGroups</h3>
        <p style='color:#9090A8; line-height:1.4;'>Asyncio executes coroutines using an event loop. <code>TaskGroup</code> (Python 3.11+) handles group lifecycles, propagating nested exceptions cleanly.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import asyncio

async def fetch_api(item: int) -> dict:
    await asyncio.sleep(0.01)  # Cooperative yield yielding thread execution
    return {"item": item, "status": "resolved"}

async def main():
    async with asyncio.TaskGroup() as tg:
        # Spawns tasks concurrently; failures cancel all siblings immediately
        tasks = [tg.create_task(fetch_api(i)) for i in range(5)]
    results = [t.result() for t in tasks]
    print(results)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. CPython Memory Layout & GIL Mechanics</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Feature</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Internal Mechanics</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Diagnostic Methods</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Reference Counting</td>
            <td style='padding:4px;'>Every PyObject holds ref counts. Value dropping to 0 frees memory structures instantly.</td>
            <td style='padding:4px;'><code>sys.getrefcount(obj)</code></td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>Generational GC</td>
            <td style='padding:4px;'>Tracks circular references across three generations (0, 1, 2) utilizing thresholds.</td>
            <td style='padding:4px;'><code>gc.collect()</code>, <code>gc.set_threshold()</code></td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>GIL</td>
            <td style='padding:4px;'>Protects CPython interpreter state from concurrent execution races. Limits threads to single core.</td>
            <td style='padding:4px;'>Bypass via <code>multiprocessing</code> or C/Rust extensions.</td>
          </tr>
        </table>
    """,
    "C++": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ C++ Comprehensive Reference Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>C++ provides systems-level hardware control combined with zero-overhead abstractions. This manual defines low-level memory layouts, RAII systems, smart pointer designs, templates, and concurrent memory models.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Struct Alignment, Packing & Cache Lines</h3>
        <p style='color:#9090A8; line-height:1.4;'>Compilers align structures to word byte boundaries based on struct layouts to prevent performance penalties. Misaligned variables trigger split-reads on memory buses.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Padding example: char (1B) + double (8B) -> compiler inserts 7 bytes padding
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

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Lvalues, Rvalues & Move Semantics</h3>
        <p style='color:#9090A8; line-height:1.4;'>Lvalues have identifiable memory addresses. Rvalues are temporary values. Move semantics transfer heap resource allocations instead of copying them.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <utility>

template <typename T>
void factory(T&& arg) {
    // std::forward preserves lvalue/rvalue category (Perfect Forwarding)
    process(std::forward<T>(arg));
}

// Move constructor
class ResourceManager {
    int* data;
public:
    ResourceManager(ResourceManager&& other) noexcept : data(other.data) {
        other.data = nullptr; // Clear source reference to prevent double-free
    }
};
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Smart Pointer Reference</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Pointer Class</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Ownership Strategy & API methods</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::unique_ptr&lt;T&gt;</td>
            <td style='padding:4px;'>Exclusive ownership. Cannot be copied. Release using <code>.release()</code> or transfer ownership using <code>std::move()</code>.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::shared_ptr&lt;T&gt;</td>
            <td style='padding:4px;'>Reference-counted ownership. Allocates a control block on heap. API: <code>.use_count()</code>, <code>.reset()</code>.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>std::weak_ptr&lt;T&gt;</td>
            <td style='padding:4px;'>Non-owning observer. Must resolve into shared pointer using <code>.lock()</code> before access. Prevents cyclic leaks.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Templates, SFINAE & Concepts</h3>
        <p style='color:#9090A8; line-height:1.4;'>Compile-time metaprogramming. SFINAE (Substitution Failure Is Not An Error) filters function choices. C++20 Concepts constraint templates explicitly.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <concepts>
#include <iostream>

// C++20 Concept
template <typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

template <Numeric T>
T add_numeric(T a, T b) {
    return a + b;
}
        </pre>
    """,
    "SQL": """
        <h2 style='color:#00C2FF; margin-top:0;'>🖧 SQL Optimization, Indexing & MVCC Overhaul Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>SQL engines execute queries declarative. This guide focuses on logical parse pipelines, B+ Tree indexing layout, join execution mechanisms, and transaction concurrency isolation.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. SQL Query Parsing Pipeline & Optimizer</h3>
        <p style='color:#9090A8; line-height:1.4;'>Queries parse into an AST, rewritten by rules, and analyzed by the Cost-Based Optimizer (CBO). Execution executes in a strict order different from syntactical layout:</p>
        <pre style='color:#E4E4F0; background:#0F0F1A; padding:8px; border-radius:4px; font-family:monospace; font-size:9pt;'>
FROM/JOIN ➔ WHERE ➔ GROUP BY ➔ HAVING ➔ SELECT ➔ DISTINCT ➔ ORDER BY ➔ OFFSET/LIMIT
        </pre>
        <p style='color:#9090A8; line-height:1.4;'>SELECT column aliases are unavailable in WHERE because filters run before projection.</p>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. B+ Tree Indexing Internals & Covered Indexes</h3>
        <p style='color:#9090A8; line-height:1.4;'>Indices are structured as balanced trees. Clustered index leaf nodes hold actual row values. Non-clustered index leaf nodes store pointers to primary values. Under a <b>Covered Index Scan</b>, all selected attributes exist within index keys, bypassing table heap reads entirely.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
-- Create composite index covering select fields
CREATE INDEX idx_user_status_created ON users(status, created_at) INCLUDE (username);

-- Covers query: Index Seek reads data directly from index leaf nodes
EXPLAIN ANALYZE
SELECT username FROM users 
WHERE status = 'active' AND created_at > '2026-01-01';
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Join Execution Mechanics</h3>
        <p style='color:#9090A8; line-height:1.4;'>Engines select join algorithms based on sizes, indexes, and sorting states:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Nested Loop Join:</b> For each outer row, scans inner tables. High performance on small inputs with inner index keys: <code>O(M * log N)</code>.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Hash Join:</b> Loads smaller tables into memory hash tables, scanning larger tables to find key matches: <code>O(M + N)</code>.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Merge Join:</b> Merges two sorted input buffers. High performance on sorted records: <code>O(M + N)</code>.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Window Functions & Framing</h3>
        <p style='color:#9090A8; line-height:1.4;'>Window functions evaluate parameters across partition groups without collapsing records. Framing limits evaluated boundaries dynamically.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
SELECT txn_id, user_id, amount,
       -- Cumulative running total
       SUM(amount) OVER (
           PARTITION BY user_id 
           ORDER BY txn_date 
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) as running_total,
       -- Compare against prior record within partition
       LAG(amount, 1) OVER (PARTITION BY user_id ORDER BY txn_date) as prev_amount
FROM transactions;
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. Transactions, Anomalies & Multi-Version Concurrency (MVCC)</h3>
        <p style='color:#9090A8; line-height:1.4;'>Relational engines isolate transactions. MVCC avoids blocking reads during write locks by maintaining version tuples (<code>xmin</code>, <code>xmax</code>).</p>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Isolation Level</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Dirty Read</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Non-Repeatable Read</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Phantom Read</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Write Skew</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Read Uncommitted</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Read Committed</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Repeatable Read</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#FF5555;'>Possible (DB dependent)</td>
            <td style='padding:4px; color:#FF5555;'>Possible</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace;'>Serializable</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
            <td style='padding:4px; color:#2DD4A0;'>Prevented</td>
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
    """,
    "React": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚛ React Architecture, Fiber & Reconciliation Overhaul</h2>
        <p style='color:#9090A8; line-height:1.4;'>React is a declarative UI library. This manual covers Virtual DOM reconciliation parameters, hooks runtime structures, concurrent scheduler priorities, and server components.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Fiber Node Architecture & Double-Buffering</h3>
        <p style='color:#9090A8; line-height:1.4;'>The Fiber Reconciler represents elements as nodes holding state, update queues, and links forming a singly linked list tree structure: <code>child</code>, <code>sibling</code>, and <code>return</code> (parent).</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Simulated Fiber Node layout
interface FiberNode {
    type: any;              // Component type (string, class, function)
    key: string | null;     // Diff identifier
    child: FiberNode | null;
    sibling: FiberNode | null;
    return: FiberNode | null;
    memoizedState: any;     // Linked list of hooks state
    updateQueue: any;       // Scheduled state changes queue
    lanes: number;          // Priority lanes bitmask (React 18+)
    alternate: FiberNode;   // Link to mirroring double-buffer node (workInProgress vs current)
}
        </pre>
        <p style='color:#9090A8; line-height:1.4;'>React performs operations on a <code>workInProgress</code> tree. Once the render phase finishes compiling changes without blocking threads, it swaps the pointer reference, committing changes instantly to the active viewport layout (Double Buffering).</p>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. React Hooks Runtime Architecture</h3>
        <p style='color:#9090A8; line-height:1.4;'>Hooks store values inside a singly linked list attached to the host Fiber's <code>memoizedState</code>. The order of hook calls must remain identical across renders to keep index linkages valid.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Hook Node structure inside Fiber's memoizedState
interface Hook {
    memoizedState: any;  // The actual state value (e.g. for useState/useReducer)
    baseState: any;
    baseQueue: Update | null;
    queue: UpdateQueue | null;
    next: Hook | null;   // Points to the next Hook in the call sequence
}
        </pre>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Hook API</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Internal Runtime Behavior</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useState</td>
            <td style='padding:4px;'>Dispatches updates to the hook queue. Schedules fiber updates matching priority lanes.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useEffect</td>
            <td style='padding:4px;'>Schedules side-effects (passive effects) to run asynchronously *after* layout paint.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useLayoutEffect</td>
            <td style='padding:4px;'>Runs synchronously *after* DOM mutations but *before* browser layout paint blocks.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>useTransition</td>
            <td style='padding:4px;'>Marks state updates as low-priority lanes. Prevents high-priority updates (e.g. typing) from blocking.</td>
          </tr>
        </table>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. React Server Components (RSC) & Hydration</h3>
        <p style='color:#9090A8; line-height:1.4;'>RSC separates computing layers. Server components render to a serialized JSON-like string format (RSC payload) containing markup and client component bundles references. Hydration validates layout trees. Mismatches trigger rendering fallbacks.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Next.js Server Component fetching data directly
export default async function Dashboard() {
    const data = await fetch("https://api.internal/stats").then(r => r.json());
    return (
        <main>
            <h1>Server Statistics</h1>
            <p>Cached Value: {data.value}</p>
            {/* Client Component boundary. Props must be JSON-serializable */}
            <InteractiveChart data={data.chartPoints} />
        </main>
    );
}
        </pre>
    """,
    "Node.js": """
        <h2 style='color:#00C2FF; margin-top:0;'>⬢ Node.js Core, Libuv & Buffer Overhaul Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Node.js wraps Google V8 execution engines with the libuv async library. This manual covers event loop details, microtasks, stream backpressure systems, and worker memory spaces.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Libuv Event Loop Phases & Microtasks</h3>
        <p style='color:#9090A8; line-height:1.4;'>The event loop runs on a single main thread. Asynchronous execution splits across queues. Microtasks (Promise resolvers and <code>process.nextTick</code>) run completely between phases.</p>
        <ol style='color:#9090A8; line-height:1.3;'>
          <li><b>Timers:</b> Executes expired <code>setTimeout</code> and <code>setInterval</code> loops.</li>
          <li><b>Pending:</b> Executes deferred I/O callbacks (e.g. system socket exceptions).</li>
          <li><b>Idle, Prepare:</b> Used internally for system tasks.</li>
          <li><b>Poll:</b> Blocks to retrieve new I/O events, executing connection callbacks.</li>
          <li><b>Check:</b> Executes <code>setImmediate</code> hooks.</li>
          <li><b>Close:</b> Processes socket/file close callbacks (e.g. <code>socket.destroy()</code>).</li>
        </ol>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Microtask execution order: nextTick executes before Promises
process.nextTick(() => console.log("nextTick")); // High priority microtask
Promise.resolve().then(() => console.log("Promise")); // Standard microtask
setImmediate(() => console.log("setImmediate")); // Macrotask
// Output order: nextTick, Promise, setImmediate (in subsequent loop check phase)
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Stream Backpressure Mechanics</h3>
        <p style='color:#9090A8; line-height:1.4;'>If a destination writable stream processes slower than the source readable stream, chunks accumulate in the buffer. The writable stream returns <code>false</code> when <code>highWaterMark</code> is exceeded. Source must pause to prevent memory bloat.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
const fs = require('fs');
const readable = fs.createReadStream('large_source.bin');
const writable = fs.createWriteStream('destination.bin', { highWaterMark: 64 * 1024 });

readable.on('data', (chunk) => {
    const canWrite = writable.write(chunk);
    if (!canWrite) {
        // Queue full: pause source reads to handle backpressure
        readable.pause();
    }
});

writable.on('drain', () => {
    // Queue flushed: resume reading
    readable.resume();
});
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Buffer Allocations Security</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Buffer.alloc(size):</b> Safely allocates a zero-filled segment of memory. Bypasses information leak issues.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Buffer.allocUnsafe(size):</b> Fast allocation returning raw uninitialized memory segment. May expose prior heap allocations contents if read directly.</li>
        </ul>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Fast allocation of 1024 bytes. Always fill or overwrite immediately!
const rawBuffer = Buffer.allocUnsafe(1024);
rawBuffer.fill(0); // Zero-fill memory manually before reading
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Worker Threads Sharing Memory via Atomics</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
const { Worker, isMainThread, parentPort } = require('worker_threads');

if (isMainThread) {
    const sharedBuffer = new SharedArrayBuffer(4); // 4 bytes shared buffer
    const array = new Int32Array(sharedBuffer);
    array[0] = 0;
    
    const worker = new Worker(__filename);
    worker.postMessage(sharedBuffer);
    
    setTimeout(() => {
        // Read value atomically to prevent race conditions
        console.log("Main read value:", Atomics.load(array, 0));
    }, 200);
} else {
    parentPort.on('message', (buf) => {
        const array = new Int32Array(buf);
        // Atomically increment the index 0 by 42
        Atomics.add(array, 0, 42);
        process.exit();
    });
}
        </pre>
    """,
    "Go": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐹 Go Runtime & Concurrency Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>Go is a compiled systems language featuring high concurrency. This manual covers goroutines scheduling, CSP channels, maps/slices allocations, and error propagation patterns.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Go Concurrency: Goroutines & Channels</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
package main

import (
	"fmt"
	"time"
)

func fetchStats(ch chan<- string) {
	time.Sleep(100 * time.Millisecond)
	ch <- "Stats retrieved"
}

func main() {
	ch := make(chan string, 1) // Buffered channel
	go fetchStats(ch)

	select {
	case res := <-ch:
		fmt.Println("Result:", res)
	case <-time.After(200 * time.Millisecond):
		fmt.Println("Operation timed out")
	}
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Go Slice & Map Allocation Internals</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Slices:</b> Header structure contains: pointer to underlying array, length (<code>len</code>), and capacity (<code>cap</code>). Reallocating beyond capacity doubles memory footprint.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Maps:</b> Implemented as hash tables. Buckets hold key-value items. Reaches 80% load factor triggers map grow operations (rehashing elements into twice the bucket array size).</li>
        </ul>
    """,
    "Agile": """
        <h2 style='color:#00C2FF; margin-top:0;'>🗲 Agile & Scrum Reference Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Agile practices focus on iterative value delivery. This manual maps out Scrum structures, metrics, and Kanban work pipelines.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Scrum Metrics & Estimation</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Velocity:</b> Cumulative story points delivered in a single sprint. Drives sprint planning capacity forecasts.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>WIP Limits:</b> Work in Progress bounds in Kanban columns. Expose process blockages and maintain optimal cycle times.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Cumulative Flow Diagram:</b> Chart plotting completed tasks, active tasks, and backlog sizes to highlight stability.</li>
        </ul>
    """,
    "Xcode": """
        <h2 style='color:#00C2FF; margin-top:0;'>🛠 Xcode Developer Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>Xcode is Apple's primary IDE. This manual covers LLDB commands, instruments profiling, and target builds.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. LLDB Debugging Reference</h3>
        <table style='width:100%; border-collapse:collapse; color:#9090A8; margin-bottom:10px;'>
          <tr style='border-bottom:1px solid #252535;'>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Command</th>
            <th style='text-align:left; color:#E4E4F0; padding:4px;'>Execution Action</th>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>po objectName</td>
            <td style='padding:4px;'>Print Object description. Evaluates object descriptions at console.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>expr expression</td>
            <td style='padding:4px;'>Evaluate expression dynamically at runtime. Alter variables during freeze.</td>
          </tr>
          <tr style='border-bottom:1px solid #14141F;'>
            <td style='padding:4px; font-family:monospace; color:#2DD4A0;'>bt</td>
            <td style='padding:4px;'>Prints the current stack trace backtrace of the active thread.</td>
          </tr>
        </table>
    """,
    "Swift": """
        <h2 style='color:#00C2FF; margin-top:0;'>🦅 Swift & SwiftUI Architecture Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Swift is Apple's safe, fast systems language. This manual defines SwiftUI, ARC ownership lifecycles, and modern Swift concurrency systems.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Automatic Reference Counting (ARC)</h3>
        <p style='color:#9090A8; line-height:1.4;'>Swift uses ARC to manage heap memory allocations. Circular reference loops require using `weak` or `unowned` properties to prevent VRAM memory leaks.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
class DeviceManager {
    let name: String
    // weak prevents cyclic ownership of resources
    weak var activeDelegate: UserDelegate?
    
    init(name: String) { self.name = name }
}
        </pre>
    """,
    "Fortran": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ Fortran Scientific Computing Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Modern Fortran reference for high-performance computing, array slicing, modules, and OpenMP integration.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. OpenMP Directives</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
!$OMP PARALLEL DO
do i = 1, N
    results(i) = sqrt(inputs(i)) * 3.14159
end do
!$OMP END PARALLEL DO
        </pre>
    """,
    "C#": """
        <h2 style='color:#00C2FF; margin-top:0;'>⧉ C# & .NET Platform Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>C# is Microsoft's primary object-oriented language. This manual defines LINQ, async/await internals, and ASP.NET Core pipelines.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. LINQ Deferred Execution</h3>
        <p style='color:#9090A8; line-height:1.4;'>LINQ queries evaluate lazily. Execution is deferred until the dataset is iterated (e.g. via <code>foreach</code> or <code>.ToList()</code>).</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
// Query expression is stored, NOT executed
IEnumerable<string> activeUsers = users
    .Where(u => u.IsActive)
    .Select(u => u.Username);

// Execution triggers here
foreach (var name in activeUsers) {
    Console.WriteLine(name);
}
        </pre>
    """,
    "C": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚙ C Low-Level Memory Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>C provides low-level abstractions and direct memory management. This reference details pointer arithmetic, allocations, and struct padding.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Pointer Arithmetic & Allocation Safety</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
#include <stdlib.h>

void allocate_buffer() {
    // Allocate buffer of 10 integers
    int *buffer = (int*) malloc(10 * sizeof(int));
    if (buffer == NULL) return; // Guard allocation failure
    
    // Pointer Arithmetic
    int *third_elem = buffer + 2; // Moves pointer by 2 * sizeof(int) bytes
    *third_elem = 42;
    
    free(buffer); // Prevent memory leaks
}
        </pre>
    """,
    "Docker": """
        <h2 style='color:#00C2FF; margin-top:0;'>🐳 Docker Engine & Containers Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Docker isolates applications inside containers. This manual provides optimized multi-stage build templates and network maps.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Multi-Stage Dockerfile Template</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# Stage 1: Build compilation
FROM golang:1.20-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o main_bin .

# Stage 2: Minimal runtime deployment
FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/main_bin .
CMD ["./main_bin"]
        </pre>
    """,
    "Kubernetes": """
        <h2 style='color:#00C2FF; margin-top:0;'>☸ Kubernetes Orchestration Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>Kubernetes manages containerized workloads at scale. This guide contains service patterns and kubectl commands.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Kubectl Daily Commands</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
# View details of all active pods in a namespace
kubectl get pods -n production

# Execute shell command inside running pod
kubectl exec -it my-pod-name -- /bin/sh

# View streams of logs from deployment
kubectl logs -f deployment/my-deployment
        </pre>
    """,
    "CSS": """
        <h2 style='color:#00C2FF; margin-top:0;'>🎨 CSS Layouts & Rendering Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>CSS styles page presentations. This guide defines Grid layouts, Flexbox alignments, responsive designs, and custom transitions.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. CSS Grid & Flexbox blueprints</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
/* Flexbox Alignment container */
.flex-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Grid Template columns */
.grid-gallery {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
}
        </pre>
    """,
    "HTML": """
        <h2 style='color:#00C2FF; margin-top:0;'>🌐 HTML Document Structures & Semantics</h2>
        <p style='color:#9090A8; line-height:1.4;'>HTML structure manual, semantic tags, forms validation, and ARIA roles specifications.</p>
    """,
    "TypeScript": """
        <h2 style='color:#00C2FF; margin-top:0;'>⌨ TypeScript Advanced Typing Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>TypeScript adds static typings to JavaScript. This manual covers advanced mapped types, utility types, and generic parameters.</p>
        
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
    """,
    "Java": """
        <h2 style='color:#00C2FF; margin-top:0;'>☕ Java JVM, Concurrency & Collections Overhaul Manual</h2>
        <p style='color:#9090A8; line-height:1.4;'>Java executes bytecode on the Java Virtual Machine. This reference defines JVM memory sectors, JIT profiling pipelines, garbage collection algorithms, and concurrent virtual threading systems.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. JVM Runtime Memory Layout</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Heap Memory:</b> Shared memory sector storing instantiated objects. Divided into Young Gen (Eden, S0, S1) and Old Gen (Tenured).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>JVM Thread Stacks:</b> Stores frame allocations containing local variable tables, operand stacks, and method return address indicators.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Metaspace:</b> Native memory sector storing metadata, runtime constant pools, and method bytecodes (replaced PermGen).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Off-Heap (Direct Buffer):</b> Bypasses garbage collector scanning allocations. Allocated via <code>ByteBuffer.allocateDirect()</code>.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>2. Garbage Collection (GC) Topologies</h3>
        <p style='color:#9090A8; line-height:1.4;'>JVM tracks object life phases using GC threads. Select algorithms based on latency requirements:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>G1 Collector:</b> Splits heap into 2048 region cells. Performs concurrent mark sweeps to minimize pause limits.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>ZGC (Z Garbage Collector):</b> Scalable low-latency GC processing terabyte heaps with sub-millisecond pauses. Performs compaction concurrently using load barriers.</li>
        </ul>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>3. Java Memory Model & Locks Concurrency</h3>
        <p style='color:#9090A8; line-height:1.4;'>The Java Memory Model (JMM) defines thread visibility rules. <code>volatile</code> guarantees memory visibility and blocks instruction reorderings. Lock structures inflate from Biased locks to Lightweight spinlocks, then to Heavyweight OS monitors.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import java.util.concurrent.locks.ReentrantLock;

public class ThreadSafeCache {
    private final ReentrantLock lock = new ReentrantLock(true); // Fair lock
    private int counter = 0;
    
    public void increment() {
        lock.lock(); // Implements AQS queue thread blocking
        try {
            counter++;
        } finally {
            lock.unlock();
        }
    }
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>4. Virtual Threads (Project Loom)</h3>
        <p style='color:#9090A8; line-height:1.4;'>Virtual threads are lightweight threads multiplexed on carrier OS threads. Yielding operations park virtual threads off carrier threads to prevent blockages.</p>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
import java.util.concurrent.Executors;

public class LoomServer {
    public void start() {
        // Spawns tasks on a virtual thread executor
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10000; i++) {
                executor.submit(() -> {
                    // Performing blocking network socket calls
                    Thread.sleep(100); // Parks virtual thread; carrier thread remains free
                    return "payload";
                });
            }
        }
    }
}
        </pre>

        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>5. HashMap and ConcurrentHashMap internals</h3>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>HashMap:</b> Hash array indexing buckets. Collisions segment nodes into linked lists. Reaching <code>TREEIFY_THRESHOLD = 8</code> converts lists to Red-Black trees to preserve <code>O(log N)</code> lookups.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>ConcurrentHashMap:</b> Implements bucket lock stripping using CAS (Compare-And-Swap) operations and synchronized hooks on head nodes, removing segment locks to support concurrent writes.</li>
        </ul>
    """,
    "JavaScript": """
        <h2 style='color:#00C2FF; margin-top:0;'>🕮 JavaScript Complete Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>JavaScript engine reference, closures, prototype inheritance, event loop phases, and DOM execution.</p>
    """,
    "APIs": """
        <h2 style='color:#00C2FF; margin-top:0;'>🌐 REST, GraphQL & gRPC API blueprints</h2>
        <p style='color:#9090A8; line-height:1.4;'>API broker architectures reference. Covers response formats, security protocols, and multiplexing.</p>
    """,
    "Uvicorn": """
        <h2 style='color:#00C2FF; margin-top:0;'>🚀 Uvicorn Production Deployment Guide</h2>
        <p style='color:#9090A8; line-height:1.4;'>Uvicorn ASGI server deployment config, concurrency tuning, and systemd daemons.</p>
    """,
    "FastAPI": """
        <h2 style='color:#00C2FF; margin-top:0;'>⚡ FastAPI Core Framework Reference</h2>
        <p style='color:#9090A8; line-height:1.4;'>FastAPI framework parameters, dependency injection scopes, database session handling, and background executors.</p>
        
        <h3 style='color:#E4E4F0; margin-bottom:4px; border-bottom:1px solid #252535; padding-bottom:4px;'>1. Dependency Injection Blueprint</h3>
        <pre style='color:#2DD4A0; background:#07070D; padding:8px; border-radius:4px; font-size:9.5pt; font-family:monospace;'>
from fastapi import FastAPI, Depends, HTTPException
from typing import Annotated

app = FastAPI()

async def verify_api_key(token: str):
    if token != "secret-admin-key":
        raise HTTPException(status_code=401, detail="Unauthorized key")
    return token

@app.get("/system/secure-endpoint")
async def secure_route(auth: Annotated[str, Depends(verify_api_key)]):
    return {"access": "granted", "auth_token": auth}
        </pre>
    """
}

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
