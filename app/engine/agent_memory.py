"""
Offline code-schema memory for swarm agents.

The indexer extracts Python function, method, and class signatures from a
workspace so coding agents can reference existing APIs before editing files.
"""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any


class CodebaseMemory:
    def __init__(
        self,
        workspace_path: str,
        db_path: str | os.PathLike[str] = "data/agent_memory.json",
    ) -> None:
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.db_path = Path(db_path)
        self.index: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def build_index(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        self.index = {}
        if not self.workspace_path.exists():
            self._persist()
            return self.index

        for path in sorted(self.workspace_path.rglob("*.py")):
            if self._skip_path(path):
                continue
            rel = path.relative_to(self.workspace_path).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (SyntaxError, OSError, UnicodeDecodeError):
                continue

            functions = []
            classes = []
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(self._function_entry(node))
                elif isinstance(node, ast.ClassDef):
                    classes.append(self._class_entry(node))

            self.index[rel] = {
                "functions": functions,
                "classes": classes,
            }

        self._persist()
        return self.index

    def load(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.index = data
        except (OSError, json.JSONDecodeError):
            self.index = {}
        return self.index

    def query_memory(self, keywords: list[str]) -> str:
        if not self.index:
            self.load()
        terms = {term.lower() for term in keywords if term}
        if not terms:
            return ""

        lines = []
        for rel_path, payload in sorted(self.index.items()):
            for fn in payload.get("functions", []):
                if self._matches(fn, terms):
                    lines.append(self._format_function(rel_path, fn))
            for cls in payload.get("classes", []):
                if self._matches(cls, terms):
                    lines.append(self._format_class(rel_path, cls))
                for method in cls.get("methods", []):
                    if self._matches(method, terms) or self._matches(cls, terms):
                        lines.append(self._format_method(rel_path, cls, method))
        return "\n".join(lines)

    def _persist(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.write_text(json.dumps(self.index, indent=2, ensure_ascii=False), encoding="utf-8")

    def _skip_path(self, path: Path) -> bool:
        skip_parts = {".git", ".venv", "venv", "__pycache__", "node_modules", "data"}
        return any(part in skip_parts for part in path.parts)

    def _function_entry(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
        return {
            "name": node.name,
            "args": self._args(node.args),
            "doc": ast.get_docstring(node) or "",
        }

    def _class_entry(self, node: ast.ClassDef) -> dict[str, Any]:
        methods = [
            self._function_entry(child)
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return {
            "name": node.name,
            "doc": ast.get_docstring(node) or "",
            "methods": methods,
        }

    def _args(self, args: ast.arguments) -> list[str]:
        names = [arg.arg for arg in args.posonlyargs + args.args]
        if args.vararg:
            names.append("*" + args.vararg.arg)
        names.extend(arg.arg for arg in args.kwonlyargs)
        if args.kwarg:
            names.append("**" + args.kwarg.arg)
        return names

    def _matches(self, item: dict[str, Any], terms: set[str]) -> bool:
        haystack = " ".join([
            str(item.get("name", "")),
            str(item.get("doc", "")),
            " ".join(str(arg) for arg in item.get("args", [])),
        ]).lower()
        return any(term in haystack for term in terms)

    def _format_function(self, rel_path: str, item: dict[str, Any]) -> str:
        args = ", ".join(item.get("args", []))
        doc = item.get("doc", "")
        suffix = f" -> {doc}" if doc else ""
        return f"- {rel_path}: def {item.get('name')}({args}){suffix}"

    def _format_class(self, rel_path: str, item: dict[str, Any]) -> str:
        doc = item.get("doc", "")
        suffix = f" -> {doc}" if doc else ""
        return f"- {rel_path}: class {item.get('name')}{suffix}"

    def _format_method(self, rel_path: str, cls: dict[str, Any], item: dict[str, Any]) -> str:
        args = ", ".join(item.get("args", []))
        doc = item.get("doc", "")
        suffix = f" -> {doc}" if doc else ""
        return f"- {rel_path}: def {cls.get('name')}.{item.get('name')}({args}){suffix}"


def keywords_from_task(task: dict[str, Any]) -> list[str]:
    text = f"{task.get('filepath', '')} {task.get('instructions', '')}"
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
    stop = {
        "the", "and", "for", "with", "that", "this", "into", "from", "file",
        "edit", "use", "using", "define", "create", "update", "return",
    }
    seen = set()
    keywords = []
    for word in words:
        key = word.lower()
        if key in stop or key in seen:
            continue
        seen.add(key)
        keywords.append(word)
    return keywords[:12]
