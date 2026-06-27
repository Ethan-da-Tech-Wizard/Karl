"""Branch panel — branches tree tab, branch navigation."""

from __future__ import annotations

import logging
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from app.ui.themes import get_theme_colors

logger = logging.getLogger("karl.workbench.branch_panel")


def build_branch_tab(w) -> QWidget:
    """Build the Branches tab widget; attaches w._branch_stats_lbl, w._branches_tree."""
    branches_tab = QWidget()
    bl = QVBoxLayout(branches_tab)
    bl.setContentsMargins(4, 4, 4, 4)
    bl.setSpacing(4)

    w._branch_stats_lbl = QLabel("Branches: 0 · Depth: 0 · Active: root")
    w._branch_stats_lbl.setObjectName("lbl-muted")
    w._branch_stats_lbl.setWordWrap(True)
    bl.addWidget(w._branch_stats_lbl)

    w._branch_focus_btn = QPushButton("Fork From Selected")
    w._branch_focus_btn.setObjectName("btn-ghost")
    w._branch_focus_btn.setToolTip(
        "Move the active conversation cursor to the selected message "
        "and continue a new branch from there."
    )
    w._branch_focus_btn.clicked.connect(w._branch_from_selected_tree_item)
    bl.addWidget(w._branch_focus_btn)

    w._branches_tree = QTreeWidget()
    w._branches_tree.setHeaderHidden(True)
    w._branches_tree.itemClicked.connect(w._on_branch_clicked)
    bl.addWidget(w._branches_tree, 1)

    return branches_tab


# ── tree population ───────────────────────────────────────────────────────────

def populate_branches_tree(w) -> None:
    w._branches_tree.blockSignals(True)
    w._branches_tree.clear()

    if not w.chat_history:
        if hasattr(w, "_branch_stats_lbl"):
            w._branch_stats_lbl.setText("Branches: 0 · Depth: 0 · Active: root")
        w._branches_tree.blockSignals(False)
        return

    root_node = w.chat_history.root
    w._tree_items_map = {}
    stats = w.chat_history.stats()
    if hasattr(w, "_branch_stats_lbl"):
        w._branch_stats_lbl.setText(
            f"Branches: {stats.leaf_count} · Messages: {stats.message_nodes} · "
            f"Depth: {w.chat_history.node_depth()} · Active: {w.chat_history.active_branch_label()}"
        )

    def _add_node(session_node, parent_item):
        snippet = re.sub(r"<think>.*?</think>", "", session_node.content, flags=re.DOTALL).strip()
        if len(snippet) > 25:
            snippet = snippet[:22] + "..."

        role_label = "User" if session_node.role == "user" else "Karl"
        label = f"[{role_label}] {snippet}"

        if parent_item is None:
            item = QTreeWidgetItem(w._branches_tree)
        else:
            item = QTreeWidgetItem(parent_item)

        item.setText(0, label)
        item.setData(0, Qt.ItemDataRole.UserRole, session_node.id)

        if session_node.id == w.chat_history.current_id:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            colors = get_theme_colors(w.state) if w.state else {}
            accent = colors.get("accent", "#00C2FF")
            item.setForeground(0, QColor(accent))
            w._branches_tree.setCurrentItem(item)

        w._tree_items_map[session_node.id] = item
        item.setExpanded(True)

        for child in session_node.children:
            _add_node(child, item)

    for child in root_node.children:
        _add_node(child, None)

    w._branches_tree.blockSignals(False)


# ── branch navigation ─────────────────────────────────────────────────────────

def on_branch_clicked(w, item, column) -> None:
    node_id = item.data(0, Qt.ItemDataRole.UserRole)
    if not node_id or node_id == w.chat_history.current_id:
        return
    branch_from_node(w, node_id)


def branch_from_selected_tree_item(w) -> None:
    item = w._branches_tree.currentItem()
    if not item:
        return
    node_id = item.data(0, Qt.ItemDataRole.UserRole)
    if node_id:
        branch_from_node(w, node_id)


def branch_from_node(w, node_id: str) -> None:
    if not w.chat_history:
        return
    if not w.chat_history.set_current_node(node_id):
        w._chat_view.append_system_note("branch target no longer exists")
        return
    w._update_expert_strip()

    node = w.chat_history.get_node(node_id)
    if node and node.role == "assistant":
        w._last_response = node.content
        w._last_thought = node.thought or ""
        w._reasoning_view.setPlainText(w._last_thought)
        w._thumb_btn.setEnabled(True)
        w._thumb_down_btn.setEnabled(True)
        w._correct_btn.setEnabled(True)
    else:
        w._last_response = ""
        w._last_thought = ""
        w._reasoning_view.clear()
        w._thumb_btn.setEnabled(False)
        w._thumb_down_btn.setEnabled(False)
        w._correct_btn.setEnabled(False)

    w._chat_view.clear_display()
    active_path = w.chat_history.get_active_path()
    w._chat_view._messages = [
        (n.role, n.content, n.id, getattr(n, "attachments", []))
        for n in active_path
    ]
    w._chat_view._render_all()

    populate_branches_tree(w)
    w._update_token_budget()
    w._input.setFocus()
    w._chat_view.append_system_note(
        "branch cursor moved - write the next prompt to fork from this message"
    )
    w._save_current_session()
