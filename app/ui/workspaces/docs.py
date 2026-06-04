from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QTextBrowser, QLabel, QFrame
from PyQt6.QtCore import Qt

from app.ui.themes import MONO

def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l

def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f

_DOCS = {
    "Workbench": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ Workbench Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>The Workbench is Karl's command center. It features a responsive triple-pane layout: Sessions (Left), Live Reasoning Thought Stream (Center), and Chat Interface (Right).</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Live Reasoning Thought Stream</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>DeepSeek-R1 models reason step-by-step. To ensure the model enters reasoning mode, Karl pre-seeds the assistant prompt with a <code>&lt;think&gt;\\n</code> tag. Reasoning tokens stream in real time to the Center panel. Upon detecting the closing <code>&lt;/think&gt;</code> tag, Karl switches routing, sending the final answer to the Right chat panel.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Parameters Drawer</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Click the chevron next to the user input bar to collapse/expand the parameters drawer. Here, you can adjust hyperparameters (Temperature, Top-P, Max Tokens), enable/disable RAG context retrieval, toggle multi-pass agentic loops, and select model/adapter combinations on the fly.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Conversation Branching Tree</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Karl represents chat history as a tree rather than a flat list. Every message bubble has a <b>branch</b> link. Clicking it lets you fork the conversation from that exact message, allowing you to explore alternate prompting paths. You can switch between branches using the <b>Branches Tree</b> widget on the Left panel.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. User Feedback Curation</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Directly rate model responses. Clicking <b>✓ good</b> logs the prompt and clean output to the training curator database as a positive example. Clicking <b>✗ bad</b> logs a negative (rejected) example. Clicking <b>✏ correct</b> allows you to manually correct the output. These curations drive local model fine-tuning.</p>
    """,
    "Prompt Lab": """
        <h2 style='color:#00C2FF; margin-top:0;'>⊕ Prompt Lab Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Prompt Lab allows side-by-side prompt engineering comparison, difference tracking, and token inspection.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Side-by-Side Prompting</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Use Column A and Column B to test variations in system prompts, user prompts, or hyperparameter variables. Saved configurations can be loaded, saved, or deleted as JSON files in <code>data/prompt_pairs/</code> using the Left panel.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Independent Model & Adapter Selection</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Each column features a dedicated model selection dropdown. You can run Prompt A against a base model (e.g. <code>deepseek-r1-1.5b.gguf</code>) and Prompt B against a fine-tuned adapter version (e.g. <code>deepseek-r1-1.5b.gguf (math_solver)</code>) simultaneously.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Sequential Execution Safety</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>When clicking <b>Run Both</b>, Karl runs the prompts sequentially (Column A first, followed by Column B). This avoids race conditions and VRAM over-allocation on single GPU systems.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Difference & Tokenizer Visualizer</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>The bottom tab widget contains two modules:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Difference View:</b> Renders a character-level diff of the outputs (additions highlighted in <span style="color:#2DD4A0; background:rgba(45,212,160,0.15); padding:1px 3px; border-radius:2px;">green</span>, deletions in <span style="color:#F05050; text-decoration:line-through; background:rgba(240,80,80,0.15); padding:1px 3px; border-radius:2px;">red</span>).</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>Tokenizer Visualizer:</b> Detokenizes and highlights Byte-Pair Encoding (BPE) subwords color-coded by classification type (special, punctuation, word-start, continuation) with interactive ID hover tooltips.</li>
        </ul>
    """,
    "Knowledge Base": """
        <h2 style='color:#00C2FF; margin-top:0;'>⊞ Knowledge Base Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Knowledge Base manages local document ingestion and context matching for Retrieval-Augmented Generation (RAG).</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Document Ingestion</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Upload documents (PDF, CSV, TXT, MD, PY) to split, embed, and index them. You can adjust text chunk size and chunk overlap before clicking <b>+ add file</b>. CSV spreadsheets are parsed row-by-row on the semantic description fields to ensure single-record coherence.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Alphanumeric Exact-Match Hybrid Search</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>To resolve dense embedding limitations with precise numeric identifiers (like Employee IDs, SKU numbers, or dates), Karl extracts alphanumeric patterns from queries and runs a high-priority exact substring match (assigning matching chunks a distance score of <code>0.0000</code>) before running the L2-normalized vector search.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Search & Distance Metrics Tester</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Use the search tester in the Right panel to query the local database. It displays retrieval candidates with their source document, chunk index, distance metrics, and text snippets to verify retrieval accuracy.</p>
    """,
    "RAG Customization": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ RAG Customization & Tuning</h2>
        <p style='color:#9090A8; line-height:1.4;'>Retrieval-Augmented Generation (RAG) grounds LLM responses with local data. While dense retrievers do not undergo traditional neural network fine-tuning, they are "trained" by structuring source data, tuning indexing models, adjusting chunk strategies, and customizing retrieval logic.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Customizing Chunking Parameters</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>To optimize retrieval, you can configure <code>chunk_size</code> and <code>overlap</code> when ingesting standard documents (PDFs, TXT, MD). Large chunks capture broad context but dilute details; small chunks capture specific details but lose global context. In-app sliders in the Knowledge Base tab allow testing different splits.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Swapping the Embedding Model</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Karl defaults to the lightweight <code>all-MiniLM-L6-v2</code> model. If your data requires heavier semantic mapping (or supports another language), you can swap it. Open <code>app/utils/rag_pipeline.py</code> and modify the <code>model_name</code> parameter in the <code>RAGPipeline</code> constructor to point to any HuggingFace model (e.g., <code>"BAAI/bge-small-en-v1.5"</code>). Note: Changing models requires clearing the index and re-ingesting all files.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Hybrid Exact-Match Heuristics</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Dense vector search often fails to match exact alphanumeric codes (like <code>EMP020</code> or product codes). Karl implements a hybrid matching layer in <code>retrieve_with_metadata()</code> that detects alphanumeric strings and overrides vector distances to <code>0.0000</code>. You can customize these regex patterns or add department listing triggers under <code>rag_pipeline.py</code> to suit your domain needs.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Evaluating RAG Quality (Offline)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Measure retrieval performance using the offline benchmark tool: <code>venv/bin/python eval/benchmark_rag.py</code>. This evaluates standard information retrieval metrics like <b>Hit@1</b>, <b>Hit@3</b>, and <b>Mean Reciprocal Rank (MRR)</b> against a pre-defined test set, allowing you to prove whether changes to your chunking or models actually improved retrieval quality.</p>
    """,
    "Training Studio": """
        <h2 style='color:#00C2FF; margin-top:0;'>⬡ Training Studio Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Training Studio houses dataset configuration tools and the local PEFT LoRA training configurator.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Curated Dataset Browser</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Browse the curated feedback dataset. You can view instruction-response text in styled code layouts and delete poor examples to clean up training quality.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. SFT & DPO Dataset Exports</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Export examples in HuggingFace/Unsloth formats:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><b>SFT (Supervised Fine-Tuning):</b> Exports single/multi-turn messages in conversational chat template layout.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><b>DPO (Direct Preference Optimization):</b> Groups queries, pairing positive curations (chosen) with negative thumbs-down curations (rejected) for preference optimization.</li>
        </ul>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Local LoRA/QLoRA Training Configurator</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Fine-tune models inside Karl using parameter sliders (Rank, Alpha, Dropout, Learning Rate, Epochs). The **4-bit QLoRA** mode (enabled by default) quantizes model parameters to NF4, compressing VRAM footprint below 1 GB to support training on consumer GPUs.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Automatic GGUF Compilation</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Upon training completion, Karl automatically compiles PyTorch adapter weights into a GGUF binary format and outputs it directly to the <code>data/adapters/</code> directory for immediate loading in workspaces.</p>
    """,
    "Eval Suite": """
        <h2 style='color:#00C2FF; margin-top:0;'>◎ Eval Suite Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>Eval Suite benchmarks model pass rates and accuracy using automated grading criteria.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Eval Datasets</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Select and load JSONL test suites containing query questions, workflow configs, and expected outputs.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Grading Tasks</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Choose the appropriate grader algorithm for the target workflow:</p>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><code>exact_match</code>: Validates that the response (case-insensitive) matches the expected string exactly.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><code>json_valid</code>: Validates that the model response is valid JSON and contains required keys.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><code>keyword_hit</code>: Verifies that specified keywords are present in the response.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><code>not_in_context</code>: Verifies that the model correctly outputs refusal strings rather than hallucinating when context is absent.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><code>groundedness</code>: Checks assertions against reference texts to prevent hallucinations (at least 60% of output sentences must overlap with context).</li>
        </ul>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Benchmarking & Results Analysis</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Click <b>Run Benchmark</b> to initiate background evaluation. The progress bar updates in real time. The Results Tree shows case names, graders, status (pass/fail), and response snippets. Selecting any row displays a detailed HTML report outlining prompt inputs, expected output templates, and model answers.</p>
    """,
    "Workflows & Modes": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ Workflows & Modes</h2>
        <p style='color:#9090A8; line-height:1.4;'>Karl groups configuration settings into high-level workflows. Each workflow binds a default system prompt, a prompt template, RAG requirements, and an evaluation grader.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. General Chat (<code>general_chat</code>)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Default open-ended conversational mode. Uses the minimal reasoning prompt template (<code>reasoning_minimal</code>), retrieves top-3 context chunks by default (RAG is optional), and uses the <code>keyword_hit</code> evaluation grader.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Document Extractor (<code>document_extractor</code>)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Extracts structured data from ingested documents. RAG is required (retrieves top-5 chunks). Prompt compiles using the <code>json_extractor</code> template. Output is validated against a customizable JSON schema and scored with the <code>json_valid</code> grader.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Grounded Answer (<code>grounded_answer</code>)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Strict QA mode that answers questions exclusively using retrieved documents. RAG is required (retrieves top-5 chunks). Prompt uses the <code>grounded_answer</code> template. The model is instructed to respond with <code>NOT IN CONTEXT</code> if proof is missing. Evaluated using the <code>groundedness</code> grader.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Code Review (<code>code_review</code>)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Automated code analyzer. RAG is disabled. Prompt uses the <code>code_review</code> template. The model generates a JSON array containing code issues (severity, location, description, fix suggestion). Evaluated using the <code>json_valid</code> grader.</p>
    """,
    "Extension Scripts": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ Extension Scripts (Hackable Core)</h2>
        <p style='color:#9090A8; line-height:1.4;'>The core of Karl's reasoning logic is defined in hot-reloadable Python modules under the <code>core/</code> folder. Users can edit these files directly to customize prompt structure, agent logic, templates, and workflows.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Prompt Compilation (<code>core/interaction_loop.py</code>)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Controls how context and message histories are formatted into ChatML. The <code>build_prompt(system, history)</code> function automatically pre-seeds base models and the <code>math_solver</code> adapter with <code>&lt;think&gt;\\n</code> to force them into reasoning mode, while bypassing pre-seeding for custom greeting adapters.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Agentic Decisions (<code>core/agentic_loop.py</code>)</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Controls autonomous multi-pass looping. <code>should_continue(iteration, last_response)</code> defines stop tokens (e.g. <code>FINAL ANSWER:</code> or <code>[DONE]</code>) and loop termination rules. <code>build_next_prompt(last_response, iteration)</code> dictates subsequent queries injected back to the model.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Prompts & Workflows Configurations</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Edit <code>core/prompt_templates.py</code> to configure global template strings. Modify the <code>WORKFLOWS</code> dictionary in <code>core/workflows.py</code> to adjust default top-k settings, schema requirements, and graders for custom workspaces.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Hot-Reloading Mechanism</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Karl executes <code>importlib.reload()</code> on these extension points prior to every generation pass. You can open any core module in your IDE, make changes, save, and see the results instantly in the chat workspace without restarting the application.</p>
    """,
    "CLI & Testing Tools": """
        <h2 style='color:#00C2FF; margin-top:0;'>◈ CLI & Testing Tools</h2>
        <p style='color:#9090A8; line-height:1.4;'>Karl includes diagnostic terminal tools to support offline development, testing, and dataset validation.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Comprehensive Test Runner</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Verify the integrity of all codebases by running the consolidated test script from the virtual environment: <code>venv/bin/python scratch/run_all_tests.py</code>. This runs Karl's 8 unit test suites (RAG, parser, logger, curator, session tree, etc.).</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Headless Diagnostic Scripts</h4>
        <ul>
          <li style='color:#9090A8; margin-bottom:4px;'><code>engine_test.py</code>: Validates that the active GGUF model loads correctly and streams output tokens.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><code>smoke_test.py</code>: Quickly checks template compilation and active workflows.</li>
          <li style='color:#9090A8; margin-bottom:4px;'><code>raw_test.py</code>: Verifies raw token extraction.</li>
        </ul>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Benchmark Tools</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Evaluate model accuracy and RAG precision under <code>eval/</code>: <code>eval/run_eval.py</code> parses JSONL files against grading functions, and <code>eval/benchmark_rag.py</code> tests vector retrieval quality (Hit@k, reciprocal rank).</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Model Setup Utilities</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Run <code>python download_test_model.py</code> to download the default DeepSeek-R1-1.5B model to <code>data/models/</code>. Use <code>python download_all_models.py</code> to acquire the complete range of supported model sizes.</p>
    """,
    "System": """
        <h2 style='color:#00C2FF; margin-top:0;'>≡ System Configuration Workspace</h2>
        <p style='color:#9090A8; line-height:1.4;'>System Config manages identity details, local settings, model downloads, and hardware instrumentation.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>1. Local Model browser & Active Selection</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Scan local model GGUF files in <code>data/models/</code> and double-click to load them. Karl computes file sizes on the fly and highlights the active model in accent-colored tags.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>2. Model Registry Download Manager</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>The Registry tab pulls model options (RAM sizes, context windows, file dimensions) from <code>data/model_registry.json</code>. Click **Download** to stream model GGUF binaries directly from HuggingFace, complete with speeds, percentages, and cancellation controls.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>3. Defaults & Identity Profiles</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Edit default generation parameters (Temperature, Top-P, Max Tokens) and active system prompts (Active identity, assistant description guidelines) applied globally on cold starts.</p>
        
        <h4 style='color:#E4E4F0; margin-bottom:4px;'>4. Hardware Scout Readout</h4>
        <p style='color:#9090A8; margin-top:0; line-height:1.4;'>Read local system resources. Karl checks active CPU core usage, total/used RAM capacity, and GPU indicators (VRAM capacity, active VRAM load, and running temperatures) to keep track of resource overhead.</p>
    """
}

class DocsWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left list panel: guide chapters
        left_panel = QWidget()
        left_panel.setObjectName("panel")
        left_panel.setFixedWidth(200)
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(12, 12, 12, 12)
        lp_layout.setSpacing(8)

        lp_layout.addWidget(_section("DOCUMENTATION"))

        self._topics_list = QListWidget()
        self._topics_list.setToolTip("Select a topic to view its in-app documentation")
        self._topics_list.currentTextChanged.connect(self._on_topic_selected)
        
        for k in _DOCS.keys():
            self._topics_list.addItem(k)

        lp_layout.addWidget(self._topics_list, 1)
        root.addWidget(left_panel)

        # Right browser panel: content reader
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(8)

        self._browser = QTextBrowser()
        self._browser.setToolTip("Read-only documentation viewer")
        rp_layout.addWidget(self._browser, 1)
        root.addWidget(right_panel, 1)

        # Select first topic by default
        self._topics_list.setCurrentRow(0)

    def _on_topic_selected(self, text: str):
        if not text:
            self._browser.clear()
            return
            
        doc_html = _DOCS.get(text, "No guide found.")
        
        # Wrapped with styled div for fonts
        styled_html = (
            f"<div style='font-family:{MONO}; font-size:10pt; color:#E4E4F0; line-height:1.5; padding:8px;'>"
            f"{doc_html}"
            f"</div>"
        )
        self._browser.setHtml(styled_html)
