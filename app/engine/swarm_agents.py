"""
Swarm Agents — Karl Workbench
==============================
Defines the specialized ArchitectAgent, CoderAgent, and TesterAgent subclasses
orchestrating local LLM calls and system prompts to perform codebase tasks.
"""

import os
import re
import json
import ast
import subprocess
from typing import Dict, Any, List, Optional
from app.engine.model_loader import ModelLoader
from core.interaction_loop import build_prompt


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

    def edit_file(
        self,
        filepath: str,
        current_content: str,
        instructions: str,
        test_failure_trace: Optional[str] = None
    ) -> str:
        prompt = (
            f"File to modify: {filepath}\n\n"
            f"Current file contents:\n```\n{current_content}\n```\n\n"
            f"Instructions:\n{instructions}\n"
        )
        if test_failure_trace:
            prompt += f"\nWarning: Previous test failed with this trace:\n{test_failure_trace}\nCorrect the code to fix this."

        raw = self.call_llm(prompt)
        
        try:
            reasoning, tool_content = parse_reasoning_and_tool(raw)
            if tool_content is not None:
                cleaned = tool_content
            else:
                cleaned = self.clean_output(raw)
        except ValueError as e:
            # Report the enforcer error as syntax/compilation failure comment
            return f"# REASONING ERROR GENERATED: {str(e)}\n"

        # AST validation for Python files
        if filepath.endswith(".py") and cleaned.strip():
            try:
                ast.parse(cleaned)
            except SyntaxError as e:
                # Append a comment with syntax error and return current content so test fails
                error_msg = f"# SYNTAX ERROR GENERATED: Line {e.lineno}: {e.msg}\n"
                return error_msg + cleaned

        return cleaned


# ── Tester Agent ──────────────────────────────────────────────────────────────

class TesterAgent:
    """
    Programmatic Tester Agent. Runs test scripts or subprocess commands
    locally and parses exit codes and tracebacks.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

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
