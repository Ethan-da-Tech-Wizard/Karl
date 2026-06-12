"""Workbench package — primary interaction space.

Split into focused modules:
- workspace.py  — WorkbenchWorkspace (layout, sessions, model selection, threads)
- chat_view.py  — ChatView streaming conversation widget
- profiles.py   — agent profile definitions

Importing WorkbenchWorkspace from app.ui.workspaces.workbench keeps working.
"""

from app.ui.workspaces.workbench.chat_view import ChatView
from app.ui.workspaces.workbench.profiles import AGENT_PROFILES
from app.ui.workspaces.workbench.workspace import WorkbenchWorkspace

__all__ = ["AGENT_PROFILES", "ChatView", "WorkbenchWorkspace"]
