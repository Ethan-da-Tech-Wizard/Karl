"""
Swarm Agents — Karl Workbench
==============================
Defines the specialized ArchitectAgent, CoderAgent, and TesterAgent subclasses
orchestrating local LLM calls and system prompts to perform codebase tasks.
"""

import os
import re
import json
import logging
import subprocess
import glob
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Callable
from app.engine.model_loader import ModelLoader
from app.engine.agent_memory import CodebaseMemory, keywords_from_task
from core.interaction_loop import build_prompt

logger = logging.getLogger("karl.swarm_agents")


_SECURITY_BLOCK_MSG = "ERROR: Security Block: Path traversal outside workspace boundary is prohibited."


def _safe_workspace_path(workspace_path: str, rel: str) -> str | None:
    """
    Returns the fully-resolved absolute path for *rel* inside *workspace_path*,
    or None if the path escapes the workspace via any mechanism (parent traversal,
    absolute injection, or symlink escape).

    Symlink escape example:
        workspace/evil -> /etc/passwd
        os.path.realpath(workspace/evil) == /etc/passwd  → blocked
    """
    if not rel:
        return None
    ws_real = os.path.realpath(workspace_path)
    target = os.path.realpath(os.path.join(ws_real, rel))
    if target == ws_real or target.startswith(ws_real + os.sep):
        return target
    return None


# ── Tool Registry ─────────────────────────────────────────────────────────────
# Tools are registered here so both CoderAgent and external callers can extend
# the dispatch table. Each value is (executor_fn, description_for_prompt).

_TOOL_REGISTRY: dict[str, tuple[Callable, str]] = {}

def register_tool(name: str, description: str):
    """Decorator to register a tool function in the global tool registry."""
    def decorator(fn):
        _TOOL_REGISTRY[name] = (fn, description)
        return fn
    return decorator

def get_tool_schema_block() -> str:
    """Returns the tool schema XML block to inject into coder prompts."""
    lines = ["<tools>"]
    for name, (_, desc) in _TOOL_REGISTRY.items():
        lines.append(f"  <tool name='{name}'>{desc}</tool>")
    lines.append("</tools>")
    return "\n".join(lines)


@register_tool("write_file", "write_file(path, content) — overwrite a workspace file. path is relative to workspace root.")
def _tool_write_file(workspace_path: str, args: dict) -> str:
    import pathlib
    rel = args.get("path", "")
    content = args.get("content", "")
    target = _safe_workspace_path(workspace_path, rel)
    if target is None:
        logger.warning("SECURITY ALERT: path traversal blocked in write_file. rel=%r workspace=%r", rel, workspace_path)
        return _SECURITY_BLOCK_MSG
    full = pathlib.Path(target)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content.splitlines())} lines to {rel}"

@register_tool("read_file", "read_file(path) — read current contents of a workspace file.")
def _tool_read_file(workspace_path: str, args: dict) -> str:
    import pathlib
    rel = args.get("path", "")
    target = _safe_workspace_path(workspace_path, rel)
    if target is None:
        logger.warning("SECURITY ALERT: path traversal blocked in read_file. rel=%r workspace=%r", rel, workspace_path)
        return _SECURITY_BLOCK_MSG
    full = pathlib.Path(target)
    if not full.exists():
        return f"ERROR: file not found: {rel}"
    try:
        return full.read_text(encoding="utf-8", errors="ignore")[:6000]
    except Exception as e:
        return f"ERROR: {e}"

@register_tool("grep_workspace", "grep_workspace(pattern) — find lines matching regex pattern across all .py files in workspace.")
def _tool_grep_workspace(workspace_path: str, args: dict) -> str:
    import pathlib, re as _re
    pattern = args.get("pattern", "")
    if not pattern:
        return "ERROR: pattern required"
    try:
        compiled = _re.compile(pattern)
    except _re.error as e:
        return f"ERROR: invalid regex: {e}"
    results = []
    for f in pathlib.Path(workspace_path).rglob("*.py"):
        if ".git" in f.parts or "venv" in f.parts or "__pycache__" in f.parts:
            continue
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if compiled.search(line):
                    results.append(f"{f.relative_to(workspace_path)}:{i}: {line.rstrip()}")
                    if len(results) >= 40:
                        break
        except Exception:
            pass
    return "\n".join(results) if results else "No matches found."

@register_tool("shell_run", "shell_run(command) — run a shell command in the workspace directory. Returns stdout+stderr. Timeout 15s.")
def _tool_shell_run(workspace_path: str, args: dict) -> str:
    cmd = args.get("command", "")
    if not cmd:
        return "ERROR: command required"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=workspace_path, timeout=15
        )
        out = (result.stdout + result.stderr).strip()
        return out[:3000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out (15s)"
    except Exception as e:
        return f"ERROR: {e}"

@register_tool("lint_python", "lint_python(path) — run pyflakes on a Python file and return violations.")
def _tool_lint_python(workspace_path: str, args: dict) -> str:
    import pathlib
    rel = args.get("path", "")
    target = _safe_workspace_path(workspace_path, rel)
    if target is None:
        logger.warning("SECURITY ALERT: path traversal blocked in lint_python. rel=%r workspace=%r", rel, workspace_path)
        return _SECURITY_BLOCK_MSG
    full = pathlib.Path(target)
    if not full.exists():
        return f"ERROR: file not found: {rel}"
    try:
        result = subprocess.run(
            ["python", "-m", "pyflakes", str(full)],
            capture_output=True, text=True, timeout=10
        )
        out = (result.stdout + result.stderr).strip()
        return out if out else "No violations found."
    except Exception as e:
        return f"ERROR: {e}"


class BaseSwarmAgent:
    def __init__(self, system_prompt: str, temperature: float = 0.2, max_tokens: int = 2048):
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens

    def clean_output(self, raw: str) -> str:
        """Strips DeepSeek reasoning tags and markdown fences from the output."""
        if "</think>" in raw:
            raw = raw.split("</think>", 1)[1]
        cleaned = raw.strip()
        # Clean markdown code block fences (e.g. ```json ... ```)
        cleaned = re.sub(r"```(?:[a-zA-Z0-9+#-]+)?\s*", "", cleaned).replace("```", "").strip()
        return cleaned

    def call_llm(self, user_prompt: str) -> str:
        """Invokes the local LLM singleton in a thread-safe manner."""
        llm = ModelLoader.get_instance()
        history = [{"role": "user", "content": user_prompt}]
        prompt = build_prompt(self.system_prompt, history)

        response = llm(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=0.95,
            stop=["<|im_end|>"],
        )
        return response["choices"][0]["text"]


# ── Architect Agent ───────────────────────────────────────────────────────────

class ArchitectAgent(BaseSwarmAgent):
    SYSTEM_PROMPT = (
        "You are an Architect Agent. Your job is to analyze the user's objective and "
        "propose a step-by-step implementation plan. You must inspect the codebase files "
        "provided and specify exactly which files need to be edited.\n\n"
        "You MUST respond ONLY in a valid JSON object matching this schema:\n"
        "{\n"
        "  \"explanation\": \"A high-level summary of the solution,\",\n"
        "  \"tasks\": [\n"
        "    {\n"
        "      \"filepath\": \"relative/path/to/file.py\",\n"
        "      \"instructions\": \"Clear description of what edits are needed inside this file\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Do not output any introductory or concluding text. Output ONLY the JSON."
    )

    def __init__(self):
        super().__init__(self.SYSTEM_PROMPT, temperature=0.1, max_tokens=1536)

    def create_plan(self, objective: str, files_context: Dict[str, str]) -> Dict[str, Any]:
        context_str = ""
        for path, content in files_context.items():
            context_str += f"=== FILE: {path} ===\n{content}\n\n"

        prompt = (
            f"Objective: {objective}\n\n"
            f"Here is the context of the files:\n{context_str}\n"
            f"Produce your JSON plan now."
        )

        raw = self.call_llm(prompt)
        cleaned = self.clean_output(raw)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Fallback if model did not return valid JSON
            return {
                "explanation": f"Failed to parse JSON plan from model. Raw output: {cleaned[:200]}",
                "tasks": []
            }


def parse_reasoning_and_tool(raw_text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parses agent output to enforce that any <tool_call> is preceded by <reasoning>.
    Returns (reasoning_content, tool_content).
    
    If <tool_call> is present but not preceded by <reasoning>, raises ValueError.
    """
    reasoning_matches = list(re.finditer(r"<reasoning>(.*?)</reasoning>", raw_text, re.DOTALL | re.IGNORECASE))
    tool_matches = list(re.finditer(r"<tool_call(?:\s+[^>]*)?>(.*?)</tool_call>", raw_text, re.DOTALL | re.IGNORECASE))

    if tool_matches:
        first_tool_pos = tool_matches[0].start()
        has_prior_reasoning = False
        reasoning_content = None
        for rm in reasoning_matches:
            if rm.end() <= first_tool_pos:
                has_prior_reasoning = True
                reasoning_content = rm.group(1).strip()
                break
        
        if not has_prior_reasoning:
            raise ValueError(
                "Action blocked: You must write down your reasoning inside <reasoning>...</reasoning> "
                "tags before calling a tool."
            )
        
        tool_content = tool_matches[0].group(1).strip()
        return reasoning_content, tool_content

    return None, None


# ── Coder Agent ───────────────────────────────────────────────────────────────

class CoderAgent(BaseSwarmAgent):
    SYSTEM_PROMPT = (
        "You are a Coder Agent. Your job is to modify a single file's contents "
        "based on the instructions provided. You will receive the current file contents, "
        "the goal, and optional compiler/test feedback from previous failures.\n\n"
        "You must write down your reasoning inside <reasoning>...</reasoning> tags. "
        "After explaining your approach, you must invoke the write_file tool by wrapping "
        "the COMPLETE new content of the file inside <tool_call name=\"write_file\">...</tool_call> tags.\n\n"
        "Example output:\n"
        "<reasoning>\n"
        "We need to fix the division by zero error by adding a check.\n"
        "</reasoning>\n"
        "<tool_call name=\"write_file\">\n"
        "def divide(a, b):\n"
        "    if b == 0:\n"
        "        return 0\n"
        "    return a / b\n"
        "</tool_call>\n\n"
        "Do not include any conversational text or markdown code fences outside these tags. "
        "The content inside the tool call will replace the target file directly."
    )

    def __init__(self):
        super().__init__(self.SYSTEM_PROMPT, temperature=0.3, max_tokens=4096)

    def generate(self, task: dict, workspace_context: dict,
                 workspace_path: str = ".",
                 token_callback: Callable[[str], None] | None = None) -> str:
        """
        Multi-turn tool loop. Model reads workspace, thinks, writes files.
        Returns the final written content for the primary task file, or an error string.
        token_callback: if provided, called with each generated token for streaming.
        """
        llm = ModelLoader.get_instance()
        tool_schema = get_tool_schema_block()
        memory_reference = ""
        try:
            memory = CodebaseMemory(workspace_path)
            memory.build_index()
            memory_reference = memory.query_memory(keywords_from_task(task))
        except Exception as exc:
            logger.debug("CodebaseMemory lookup failed: %s", exc)
    
        # Build initial prompt
        context_snippet = "\n".join(
            f"--- {k} ---\n{v[:800]}" for k, v in list(workspace_context.items())[:8]
        )
        memory_block = ""
        if memory_reference:
            memory_block = (
                "\n\nCodebase Interfaces & Signatures Reference:\n"
                "Use the following existing codebase signatures to ensure integration:\n"
                f"{memory_reference}"
            )
        system = (
            "You are an expert software engineer. You MUST reason before acting.\n"
            "Use the tools below to read existing code, then write correct, tested changes.\n"
            "Always call read_file before writing to understand the existing implementation.\n"
            "After writing files, call lint_python and fix any violations.\n"
            "When finished with ALL changes, call done() with no arguments.\n\n"
            f"{tool_schema}\n\n"
            "Tool call format:\n"
            "<tool_call name='TOOL_NAME'>\n"
            "  param_name: value\n"
            "</tool_call>\n\n"
            "To finish: <tool_call_call name='done'></tool_call_call>"
            f"{memory_block}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                f"Task: Edit {task['filepath']}\n\n"
                f"Instructions: {task['instructions']}\n\n"
                f"Workspace context:\n{context_snippet}"
            )}
        ]

        written_content = ""

        for _turn in range(8):
            # Build prompt and generate
            from core.interaction_loop import build_prompt
            prompt_text = build_prompt(system, messages[1:])
    
            raw = ""
            if token_callback:
                try:
                    res = llm(prompt_text, max_tokens=self.max_tokens,
                              temperature=self.temperature, stream=True,
                              stop=["</tool_call>", "<|im_end|>"], echo=False)
                    if hasattr(res, "__iter__") and not isinstance(res, dict):
                        for chunk in res:
                            tok = chunk["choices"][0].get("text", "")
                            raw += tok
                            token_callback(tok)
                    else:
                        if isinstance(res, dict):
                            raw = res["choices"][0]["text"]
                        else:
                            raw = str(res)
                except Exception:
                    res = llm(prompt_text, max_tokens=self.max_tokens,
                              temperature=self.temperature, stream=False,
                              stop=["<|im_end|>"], echo=False)
                    if isinstance(res, dict):
                        raw = res["choices"][0]["text"]
                    else:
                        raw = str(res)
            else:
                res = llm(prompt_text, max_tokens=self.max_tokens,
                           temperature=self.temperature, stream=False,
                           stop=["<|im_end|>"], echo=False)
                if isinstance(res, dict):
                    raw = res["choices"][0]["text"]
                else:
                    raw = str(res)
    
            messages.append({"role": "assistant", "content": raw})
    
            # Parse tool calls from raw output
            tool_calls = re.findall(
                r"<tool_call name='([^']+)'>(.*?)</tool_call>",
                raw, re.DOTALL
            )

            if not tool_calls:
                if _turn == 0:
                    try:
                        reasoning, tool_content = parse_reasoning_and_tool(raw)
                        if tool_content is not None:
                            written_content = tool_content
                        else:
                            written_content = self.clean_output(raw)
                    except ValueError:
                        written_content = self.clean_output(raw)
                break

            tool_results = []
            done_called = False

            for tool_name, tool_body in tool_calls:
                if tool_name == "done":
                    done_called = True
                    break

                # Parse YAML-style args (key: value per line)
                args = {}
                for line in tool_body.strip().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        args[k.strip()] = v.strip()

                if tool_name in _TOOL_REGISTRY:
                    executor, _ = _TOOL_REGISTRY[tool_name]
                    try:
                        result_text = executor(workspace_path, args)
                    except Exception as ex:
                        result_text = f"ERROR: tool raised exception: {ex}"

                    # Capture written content for return value
                    if tool_name == "write_file":
                        written_content = args.get("content", "")
                else:
                    result_text = f"ERROR: unknown tool '{tool_name}'"
    
                tool_results.append(f"<tool_result name='{tool_name}'>\n{result_text}\n</tool_result>")
    
            if done_called:
                break

            if tool_results:
                messages.append({"role": "user", "content": "\n".join(tool_results)})

        return written_content or f"# CoderAgent completed task: {task['filepath']}"

    def edit_file(
        self,
        filepath: str,
        current_content: str,
        instructions: str,
        test_failure_trace: Optional[str] = None
    ) -> str:
        task = {"filepath": filepath, "instructions": instructions}
        workspace_context = {filepath: current_content}
        if test_failure_trace:
            task["instructions"] += f"\nPrevious failure: {test_failure_trace}"
        return self.generate(task, workspace_context)


# ── Tester Agent ──────────────────────────────────────────────────────────────

class TesterAgent:
    """
    Programmatic Tester Agent. Runs test scripts or subprocess commands
    locally and parses exit codes and tracebacks.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def run(self, command: str, workspace_path: str) -> tuple[bool, str]:
        """Runs a subprocess command and returns (passed, trace)."""
        res = self.run_test_command(command)
        return res["passed"], res["error_trace"] or res["output"]

    def run_test_command(self, test_cmd: str) -> Dict[str, Any]:
        """Runs a shell test command inside the workspace and captures results."""
        try:
            res = subprocess.run(
                test_cmd,
                shell=True,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            passed = res.returncode == 0
            output = res.stdout + "\n" + res.stderr
            
            # Simple trace extractor
            error_trace = ""
            if not passed:
                # Extract Python traceback from stderr/stdout
                lines = output.split("\n")
                tb_idx = -1
                for idx, line in enumerate(lines):
                    if "Traceback (most recent call first):" in line or "Traceback (recent call last):" in line:
                        tb_idx = idx
                        break
                if tb_idx != -1:
                    error_trace = "\n".join(lines[tb_idx:])
                else:
                    # Capture the last 20 lines of log as trace
                    error_trace = "\n".join(lines[-20:])

            return {
                "passed": passed,
                "output": output,
                "error_trace": error_trace
            }
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "output": "Test execution timed out after 30 seconds.",
                "error_trace": "TimeoutExpired"
            }
        except Exception as e:
            return {
                "passed": False,
                "output": f"Failed to execute tests: {e}",
                "error_trace": str(e)
            }
