# -*- coding: utf-8 -*-
"""
Exhaustive reference guides for Karl's Codex workspace.
Provides complete, self-contained documentation of grammar, compilers, runtime loops,
APIs, and optimization tactics for offline code generation.
"""

# Heavenscape Styling Tokens
STYLE_H2 = "color:#00C2FF; margin-top:0; border-bottom: 1px solid #1F1F3D; padding-bottom: 4px;"
STYLE_H4 = "color:#E4E4F0; margin-bottom:4px; margin-top:16px;"
STYLE_P = "color:#9090A8; line-height:1.6;"
STYLE_PRE = "background:#050510; border:1px solid #1F1F3D; color:#A0AEC0; padding:12px; font-family:'JetBrains Mono', monospace; border-radius:4px; margin: 10px 0;"
STYLE_CODE = "color:#00C2FF; background:#10101C; padding:2px 4px; border-radius:3px;"
STYLE_LI = "color:#9090A8; margin-bottom:8px; line-height:1.4;"
STYLE_TABLE = "width:100%; border-collapse:collapse; margin:10px 0;"
STYLE_TH = "text-align:left; color:#00C2FF; border-bottom:1px solid #1F1F3D; padding:8px;"
STYLE_TD = "padding:8px; border-bottom:1px solid #10101C; color:#9090A8;"

DEFAULT_LIBRARY = {
    "Workbench": f"""
        <h2 style='{STYLE_H2}'>◈ Workbench: Primary Interaction Space</h2>
        <p style='{STYLE_P}'>The Workbench is Karl's central nervous system, providing a high-bandwidth interface for local LLM introspection and generation.</p>
        
        <h4 style='{STYLE_H4}'>Toggleable HUD Panels</h4>
        <p style='{STYLE_P}'>Customize your concentration by toggling various workspace elements. Hiding HUD panels creates a decluttered, "Focused" environment for deep work.</p>
        <ul>
          <li style='{STYLE_LI}'><b>Sessions Panel (Dock):</b> Manage your conversation history tree. Quickly jump between alternate generation paths or rename session branches.</li>
          <li style='{STYLE_LI}'><b>Reasoning Log (Dock):</b> Dedicated real-time stream for the model's <code>&lt;think&gt;</code> blocks. See the raw logic before the final answer arrives.</li>
          <li style='{STYLE_LI}'><b>RAG Attribution View:</b> When Knowledge Base is active, this view shows exactly which document chunks were injected into the prompt context.</li>
        </ul>

        <h4 style='{STYLE_H4}'>Keyboard Shortcuts</h4>
        <table style='{STYLE_TABLE}'>
          <tr><th style='{STYLE_TH}'>Shortcut</th><th style='{STYLE_TH}'>Action</th></tr>
          <tr><td style='{STYLE_TD}'><code style='{STYLE_CODE}'>Ctrl+Return</code></td><td style='{STYLE_TD}'>Submit current prompt to model</td></tr>
          <tr><td style='{STYLE_TD}'><code style='{STYLE_CODE}'>Ctrl+L</code></td><td style='{STYLE_TD}'>Focus active input field</td></tr>
          <tr><td style='{STYLE_TD}'><code style='{STYLE_CODE}'>Ctrl+Shift+N</code></td><td style='{STYLE_TD}'>Create new session branch</td></tr>
          <tr><td style='{STYLE_TD}'><code style='{STYLE_CODE}'>Ctrl+Shift+S</code></td><td style='{STYLE_TD}'>Save session snapshot to disk</td></tr>
          <tr><td style='{STYLE_TD}'><code style='{STYLE_CODE}'>Ctrl+K</code> / <code style='{STYLE_CODE}'>Ctrl+P</code></td><td style='{STYLE_TD}'>Open Command Palette</td></tr>
        </table>

        <h4 style='{STYLE_H4}'>Settings & Parameters</h4>
        <p style='{STYLE_P}'>The settings drawer allows granular control over the generation engine:</p>
        <ul>
          <li style='{STYLE_LI}'><b>Temperature:</b> Controls randomness. 0.0 is deterministic, 1.0 is creative.</li>
          <li style='{STYLE_LI}'><b>Top-P:</b> Nucleus sampling threshold. Filters low-probability tokens.</li>
          <li style='{STYLE_LI}'><b>Max Tokens:</b> Hard limit on generation length per turn.</li>
          <li style='{STYLE_LI}'><b>Feedback Curation:</b> Use the 👍/👎/✎ buttons to rate responses. Thumbs up saves to SFT curator; Thumbs down for DPO; Correct (✎) saves the user's manual fix as the new ground truth.</li>
        </ul>
    """,
    "Swarm Studio": f"""
        <h2 style='{STYLE_H2}'>☄ Swarm Studio: Multi-Agent Codegen</h2>
        <p style='{STYLE_P}'>Karl's Swarm Studio orchestrates multiple specialized agents (Architect, Coder, Tester) to solve complex coding objectives autonomously.</p>

        <h4 style='{STYLE_H4}'>Operational Mechanics</h4>
        <ul>
          <li style='{STYLE_LI}'><b>Dependency Sorting:</b> The Architect analyzes the project structure and sorts tasks into a topological order, ensuring parent files are modified before dependents.</li>
          <li style='{STYLE_LI}'><b>Parallel Layers:</b> Tasks with no shared dependencies are executed in parallel across multiple worker threads to maximize throughput.</li>
          <li style='{STYLE_LI}'><b>Live Streams:</b> Every agent's internal thought process is streamed to the dashboard, providing full visibility into planning and coding decisions.</li>
          <li style='{STYLE_LI}'><b>Verification Tracebacks:</b> After code modification, the Tester runs the defined test suite. If an error occurs, the full traceback is fed back into the Coder for automatic correction.</li>
        </ul>

        <h4 style='{STYLE_H4}'>Task Lifecycle</h4>
        <pre style='{STYLE_PRE}'>PENDING ➔ IN_PROGRESS ➔ VERIFYING ➔ [ COMPLETED | FAILED ]</pre>
    """,
    "Training Studio": f"""
        <h2 style='{STYLE_H2}'>⬡ Training Studio: Local Fine-Tuning</h2>
        <p style='{STYLE_P}'>Perform hardware-accelerated LoRA and QLoRA fine-tuning on your curated datasets without leaving Karl.</p>

        <h4 style='{STYLE_H4}'>LoRA/QLoRA Configuration</h4>
        <table style='{STYLE_TABLE}'>
          <tr><th style='{STYLE_TH}'>Parameter</th><th style='{STYLE_TH}'>Description</th></tr>
          <tr><td style='{STYLE_TD}'><b>Rank (R)</b></td><td style='{STYLE_TD}'>Dimension of the update matrices. Higher = more capacity, more VRAM.</td></tr>
          <tr><td style='{STYLE_TD}'><b>Alpha</b></td><td style='{STYLE_TD}'>Scaling factor for LoRA updates. Typically 2x Rank.</td></tr>
          <tr><td style='{STYLE_TD}'><b>Learning Rate</b></td><td style='{STYLE_TD}'>Step size for weight updates. Default: 2e-4.</td></tr>
          <tr><td style='{STYLE_TD}'><b>Dropout</b></td><td style='{STYLE_TD}'>Regularization to prevent overfitting by randomly zeroing weights.</td></tr>
        </table>

        <h4 style='{STYLE_H4}'>Burst & Auto-Train Pipelines</h4>
        <p style='{STYLE_P}'>Karl provides two pathways for rapid iteration:</p>
        <ul>
          <li style='{STYLE_LI}'><b>Auto-Train:</b> A one-click pipeline that generates synthetic tasks, verifies them in the Docker sandbox, and trains an adapter on the fly.</li>
          <li style='{STYLE_LI}'><b>Burst Train:</b> High-intensity training on small, high-quality "fixtures" to rapidly steer model behavior for specific niche tasks.</li>
        </ul>

        <h4 style='{STYLE_H4}'>Example Burst Fixture (<code>*.burst.py</code>)</h4>
        <pre style='{STYLE_PRE}'># Custom fixture for steering model towards strict JSON output
def get_examples():
    return [
        {{"instruction": "Parse user name", "output": "{{\\"name\\": \\"Karl\\"}}"}},
        {{"instruction": "Extract date", "output": "{{\\"date\\": \\"2026-06-13\\"}}"}}
    ]</pre>
    """,
    "Knowledge Base": f"""
        <h2 style='{STYLE_H2}'>⊞ Knowledge Base: RAG Mechanics</h2>
        <p style='{STYLE_P}'>Manage and optimize the local Retrieval-Augmented Generation (RAG) pipeline for grounding LLM responses in your own data.</p>

        <h4 style='{STYLE_H4}'>Ingestion & Chunking</h4>
        <ul>
          <li style='{STYLE_LI}'><b>Chunk Size:</b> The number of words or tokens per segment. Small chunks (200) are better for precise lookup; larger chunks (500+) preserve more context.</li>
          <li style='{STYLE_LI}'><b>Overlap Spacing:</b> The redundancy between adjacent chunks. Prevents "splitting" a fact across two chunks. Recommended: 10-25% of chunk size.</li>
        </ul>

        <h4 style='{STYLE_H4}'>Retrieval Tuning</h4>
        <p style='{STYLE_P}'>Fine-tune how Karl selects relevant context:</p>
        <ul>
          <li style='{STYLE_LI}'><b>Distance Threshold:</b> Limits how "far" a chunk can be from the query in vector space. Lower values ensure higher relevance but may return fewer results.</li>
          <li style='{STYLE_LI}'><b>Top-K:</b> The maximum number of chunks to inject into the prompt. High K provides more breadth but consumes more context budget.</li>
        </ul>
    """,
    "Codex Search": f"""
        <h2 style='{STYLE_H2}'>🔍 Codex: Semantic Information Discovery</h2>
        <p style='{STYLE_P}'>Karl uses a hybrid search strategy to locate relevant documentation in real-time.</p>
        
        <h4 style='{STYLE_H4}'>1. Semantic RAG Search</h4>
        <p style='{STYLE_P}'>Queries are embedded into vector space to find conceptually related documentation, even if no keywords match.</p>
        
        <h4 style='{STYLE_H4}'>2. Keyword & Regex Fallback</h4>
        <p style='{STYLE_P}'>If the vector engine is offline, Karl falls back to high-speed alphanumeric pattern matching to find specific IDs or technical terms.</p>
    """,
    "AI Steering": f"""
        <h2 style='{STYLE_H2}'>◈ AI Steering & Adapter Control</h2>
        <p style='{STYLE_P}'>Steering refers to the fine-grained control of model behavior using lightweight adapters (LoRA/QLoRA).</p>
        <ul>
          <li style='{STYLE_LI}'><b>Adapter Activation:</b> Select an adapter from the Workbench dropdown to shift the model's tone, syntax, or knowledge domain.</li>
          <li style='{STYLE_LI}'><b>Dynamic Scheduling:</b> Karl automatically adjusts entropy based on the generation state (Thinking vs. Answering).</li>
        </ul>
    """,
    "Python": f"""
        <h2 style='{STYLE_H2}'>Python Development Guide</h2>
        <p style='{STYLE_P}'>Best practices for writing Python code with Karl's local assistance.</p>
    """,
    "Docker": f"""
        <h2 style='{STYLE_H2}'>Docker & Sandboxing</h2>
        <p style='{STYLE_P}'>Guidelines for using Docker containers to safely verify model-generated code.</p>
    """,
    "FastAPI": f"""
        <h2 style='{STYLE_H2}'>FastAPI Implementation</h2>
        <p style='{STYLE_P}'>Reference for building robust APIs using FastAPI and Pydantic.</p>
    """,
    "Mathematical Introspection": f"""
        <h2 style='{STYLE_H2}'>◈ Mathematical Introspection</h2>
        <p style='{STYLE_P}'>This reference guide details the mathematical foundations underlying Karl's vector space search retrieval and deep learning transformer self-attention mechanisms.</p>
        
        <h4 style='{STYLE_H4}'>1. Sparse Vector Retrieval (TF-IDF)</h4>
        <p style='{STYLE_P}'>TF-IDF (Term Frequency-Inverse Document Frequency) measures term importance within a document relative to a corpus:</p>
        <ul>
          <li style='{STYLE_LI}'><b>Term Frequency (TF):</b> The density of a term <i>t</i> in document <i>d</i>:
            <pre style='{STYLE_PRE}'>TF(t, d) = count(t in d) / total_words(d)</pre>
          </li>
          <li style='{STYLE_LI}'><b>Inverse Document Frequency (IDF):</b> Penalizes terms that appear frequently across the entire corpus:
            <pre style='{STYLE_PRE}'>IDF(t, D) = ln((1 + N) / (1 + DF(t))) + 1.0</pre>
            where <i>N</i> is the total document count in corpus <i>D</i>, and <i>DF(t)</i> is the count of documents containing term <i>t</i>.
          </li>
          <li style='{STYLE_LI}'><b>TF-IDF Weighting:</b> The composite representation score:
            <pre style='{STYLE_PRE}'>TF-IDF(t, d, D) = TF(t, d) × IDF(t, D)</pre>
          </li>
        </ul>
        
        <h4 style='{STYLE_H4}'>2. Vector Space Proximity (Cosine Similarity)</h4>
        <p style='{STYLE_P}'>To evaluate alignment between query vector <i>A</i> and document vector <i>B</i>, Karl calculates their Cosine Similarity:</p>
        <pre style='{STYLE_PRE}'>
                         A · B         ∑ (A_i × B_i)
CosineSimilarity(A, B) = ─────── = ─────────────────────
                        ‖A‖ ‖B‖    √(∑ A_i²) × √(∑ B_i²)
        </pre>
        <p style='{STYLE_P}'>Since Karl L2-normalizes all document and query vectors (rendering <i>‖A‖ = ‖B‖ = 1.0</i>), the cosine similarity simplifies to a simple dot product:</p>
        <pre style='{STYLE_PRE}'>CosineSimilarity(A, B) = A · B = ∑ (A_i × B_i)</pre>
        
        <h4 style='{STYLE_H4}'>3. Multi-Head Self-Attention (MHSA) Layers</h4>
        <p style='{STYLE_P}'>Transformer self-attention layers route information dynamically between tokens. For input tokens <i>X ∈ ℝ^(T × d_model)</i>:</p>
        <ul>
          <li style='{STYLE_LI}'><b>Linear Projections (Q, K, V):</b> Projections to Query, Key, and Value matrices:
            <pre style='{STYLE_PRE}'>Q = X W^Q,   K = X W^K,   V = X W^V</pre>
            where <i>W^Q, W^K ∈ ℝ^(d_model × d_k)</i> and <i>W^V ∈ ℝ^(d_model × d_v)</i>.
          </li>
          <li style='{STYLE_LI}'><b>Scaled Dot-Product Attention:</b> Derives attention weights and routes values:
            <pre style='{STYLE_PRE}'>Attention(Q, K, V) = softmax( (Q Kᵀ) / √d_k ) V</pre>
            The scaling factor <i>1 / √d_k</i> prevents the dot products from growing excessively large in magnitude, which would push the softmax function into regions with vanishing gradients.
          </li>
          <li style='{STYLE_LI}'><b>Multi-Head Assembly:</b> Aggregates parallel heads representing different aspects of context:
            <pre style='{STYLE_PRE}'>
MultiHead(Q, K, V) = Concat(head_1, ..., head_h) W^O
where head_i = Attention(Q W_i^Q, K W_i^K, V W_i^V)
            </pre>
          </li>
          <li style='{STYLE_LI}'><b>MLP / Feed-Forward Projections:</b> Modern LLM architectures (like DeepSeek-R1) follow this with a <b>SwiGLU</b> Feed-Forward Network:
            <pre style='{STYLE_PRE}'>FFN(x) = ( Swish(x W_gate) ⊙ (x W_up) ) W_down</pre>
            where <i>⊙</i> is the element-wise Hadamard product.
          </li>
        </ul>
    """
}
