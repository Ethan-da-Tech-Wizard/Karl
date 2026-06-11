import subprocess
import os
from typing import List, Dict, Any

def codebase_search(query: str, workspace_path: str) -> List[Dict[str, Any]]:
    """
    Invokes ripgrep (rg) from sub-process to search the codebase.
    Returns a list of matching lines with filepath, line number, column, and content.
    """
    if not query:
        return []

    try:
        # Run ripgrep with --vimgrep for precise parser-friendly output:
        # filepath:line:col:content
        res = subprocess.run(
            ["rg", "--vimgrep", "--no-config", "--follow", query, workspace_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        results = []
        for line in res.stdout.splitlines():
            parts = line.split(":", 3)
            if len(parts) >= 4:
                abs_path = parts[0]
                rel_path = os.path.relpath(abs_path, workspace_path)
                try:
                    line_num = int(parts[1])
                    col_num = int(parts[2])
                except ValueError:
                    continue
                content = parts[3]
                results.append({
                    "filepath": rel_path,
                    "line": line_num,
                    "column": col_num,
                    "content": content
                })
        return results
    except Exception as e:
        print(f"[CodebaseSearch] Error calling ripgrep: {e}")
        return []
