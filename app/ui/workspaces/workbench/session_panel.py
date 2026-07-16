"""Session panel — sessions list tab, CRUD operations, load/save."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from app.utils.session_tree import SessionTree
from app.ui.themes import get_theme_colors

if TYPE_CHECKING:
    pass

logger = logging.getLogger("karl.workbench.session_panel")


def build_session_tab(w) -> QWidget:
    """Build the Sessions tab widget; attaches w._session_search, w._sessions_list."""
    sessions_tab = QWidget()
    sl = QVBoxLayout(sessions_tab)
    sl.setContentsMargins(4, 4, 4, 4)
    sl.setSpacing(4)

    w._session_search = QLineEdit()
    w._session_search.setPlaceholderText("Search sessions...")
    apply_session_panel_styles(w)
    w._session_search.textChanged.connect(w._filter_sessions)
    sl.addWidget(w._session_search)

    w._sessions_list = QListWidget()
    w._sessions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    w._sessions_list.customContextMenuRequested.connect(w._show_session_context_menu)
    w._sessions_list.currentItemChanged.connect(w._on_session_clicked)
    sl.addWidget(w._sessions_list, 1)

    return sessions_tab


# ── session list ──────────────────────────────────────────────────────────────

def refresh_sessions(w) -> None:
    if not hasattr(w, "_sessions_list"):
        return
    w._sessions_list.blockSignals(True)
    w._sessions_list.clear()
    import datetime
    for meta in SessionTree.list_sessions():
        mtime_dt = datetime.datetime.fromtimestamp(meta["mtime"])
        time_str = mtime_dt.strftime("%b %d, %H:%M")
        display_text = f"{meta['preview']} ({time_str})" if meta["preview"] else f"Session {meta['session_id']} ({time_str})"
        item = QListWidgetItem(display_text)
        item.setToolTip(meta["path"])
        item.setData(Qt.ItemDataRole.UserRole, meta["path"])
        w._sessions_list.addItem(item)

    if getattr(w, "_current_session_file", None):
        for idx in range(w._sessions_list.count()):
            item = w._sessions_list.item(idx)
            if item.data(Qt.ItemDataRole.UserRole) == w._current_session_file:
                w._sessions_list.setCurrentItem(item)
                break
    w._sessions_list.blockSignals(False)
    if hasattr(w, "_session_search"):
        filter_sessions(w, w._session_search.text())


def filter_sessions(w, text: str) -> None:
    query = text.strip().lower()
    for idx in range(w._sessions_list.count()):
        item = w._sessions_list.item(idx)
        item.setHidden(query not in item.text().lower())


def on_session_clicked(w, current, previous) -> None:
    if not current:
        return
    path = current.data(Qt.ItemDataRole.UserRole)
    if path == getattr(w, "_current_session_file", None):
        return
    w._save_current_session()
    w._load_session(path)


# ── context menu ──────────────────────────────────────────────────────────────

def show_session_context_menu(w, pos) -> None:
    item = w._sessions_list.itemAt(pos)
    if not item:
        return

    colors = get_theme_colors(w.state) if w.state else {}
    bg_input = colors.get("bg_input", "#0D0D1B")
    border = colors.get("border", "#1F1F3D")
    text_hi = colors.get("text_hi", "#F0F5FF")
    accent = colors.get("accent", "#00C2FF")
    bg_deep = colors.get("bg_deep", "#020205")

    menu = QMenu(w)
    menu.setStyleSheet(
        f"QMenu {{ background-color: {bg_input}; border: 1px solid {border}; color: {text_hi}; "
        f"font-family: 'Inter', sans-serif; font-size: 9pt; }}"
        f"QMenu::item:selected {{ background-color: {accent}; color: {bg_deep}; }}"
    )
    rename_action = menu.addAction("Rename Session")
    dup_action = menu.addAction("Duplicate Session")
    del_action = menu.addAction("Delete Session")

    action = menu.exec(w._sessions_list.mapToGlobal(pos))
    if not action:
        return

    path = item.data(Qt.ItemDataRole.UserRole)
    fname = os.path.basename(path)
    if action == rename_action:
        rename_session(w, fname)
    elif action == dup_action:
        duplicate_session(w, fname)
    elif action == del_action:
        delete_session(w, fname)


def rename_session(w, fname: str) -> None:
    new_name, ok = QInputDialog.getText(
        w, "Rename Session", "Enter new filename (must end in .json):", text=fname
    )
    if not ok or not new_name.strip():
        return
    # Strip any directory components the user typed (e.g. "../../foo.json")
    # so the rename can never land outside sessions_dir.
    new_name = os.path.basename(new_name.strip())
    if not new_name or new_name in (".", ".."):
        QMessageBox.warning(w, "Error", "Invalid filename.")
        return
    if not new_name.endswith(".json"):
        new_name = new_name + ".json"

    sessions_dir = os.path.realpath(w.state.memory.sessions_dir)
    old_path = os.path.join(sessions_dir, fname)
    new_path = os.path.join(sessions_dir, new_name)
    if os.path.realpath(new_path) != new_path or os.path.dirname(os.path.realpath(new_path)) != sessions_dir:
        QMessageBox.warning(w, "Error", "Invalid filename.")
        return
    if os.path.exists(new_path):
        QMessageBox.warning(w, "Error", "A session with that name already exists.")
        return
    try:
        os.rename(old_path, new_path)
        if w._current_session_file == fname:
            w._current_session_file = new_name
        refresh_sessions(w)
    except Exception as e:
        QMessageBox.critical(w, "Error", f"Failed to rename file: {e}")


def duplicate_session(w, fname: str) -> None:
    old_path = os.path.join(w.state.memory.sessions_dir, fname)
    base, ext = os.path.splitext(fname)
    new_name = f"{base}_copy{ext}"
    new_path = os.path.join(w.state.memory.sessions_dir, new_name)
    counter = 1
    while os.path.exists(new_path):
        new_name = f"{base}_copy{counter}{ext}"
        new_path = os.path.join(w.state.memory.sessions_dir, new_name)
        counter += 1
    try:
        import shutil
        shutil.copy2(old_path, new_path)
        refresh_sessions(w)
    except Exception as e:
        QMessageBox.critical(w, "Error", f"Failed to duplicate file: {e}")


def delete_session(w, fname: str) -> None:
    reply = QMessageBox.question(
        w, "Confirm Delete",
        f"Are you sure you want to permanently delete session '{fname}'?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    path = os.path.join(w.state.memory.sessions_dir, fname)
    try:
        os.remove(path)
        if w._current_session_file == fname:
            w._current_session_file = None
            w.chat_history.clear()
            w._populate_branches_tree()
            w._chat_view.clear_display()
            w._reasoning_view.clear()
            w._last_response = ""
            w._last_thought = ""
            w._is_correcting = False
        refresh_sessions(w)
    except Exception as e:
        QMessageBox.critical(w, "Error", f"Failed to delete file: {e}")


# ── load / save / autosave / new ──────────────────────────────────────────────

def load_session(w, path: str) -> None:
    try:
        tree, session_id = SessionTree.load(path)
        w.chat_history = tree
        w._session_id = session_id
        w._current_session_file = path

        w._chat_view.clear_display()
        active_path = w.chat_history.get_active_path()
        w._chat_view._messages = [
            (n.role, n.content, n.id, getattr(n, "attachments", []))
            for n in active_path
        ]
        w._chat_view._render_all()
        w._populate_branches_tree()

        w._is_correcting = False
        w._correct_btn.setText("✎ correct")

        last_node = active_path[-1] if active_path else None
        if last_node and last_node.role == "assistant":
            w._last_response = last_node.content
            w._last_thought = last_node.thought or ""
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

        w._update_expert_strip()
        refresh_sessions(w)
    except Exception as e:
        QMessageBox.critical(w, "Load Error", f"Could not load session: {e}")


def save_current_session(w) -> None:
    if not w.chat_history or len(w.chat_history) < 2:
        return
    try:
        path = w.chat_history.save(w._session_id)
        if w._session_id is None:
            w._session_id = os.path.splitext(os.path.basename(path))[0]
            w._current_session_file = path
        refresh_sessions(w)
    except Exception as e:
        logger.warning("Save failed: %s", e)


def autosave_session(w) -> None:
    if not w.chat_history or len(w.chat_history) < 2:
        return
    try:
        path = w.chat_history.save(w._session_id)
        if w._session_id is None:
            w._session_id = os.path.splitext(os.path.basename(path))[0]
            w._current_session_file = path
        refresh_sessions(w)
    except Exception as e:
        logger.warning("Autosave failed: %s", e)


def new_session(w) -> None:
    autosave_session(w)
    w.chat_history = SessionTree()
    w._session_id = None
    w._current_session_file = None
    w._pending_image_attachments = []
    w._pending_generation_history = None
    w._update_expert_strip()
    w._populate_branches_tree()

    w._chat_view.clear_display()
    w._reasoning_view.clear()
    w._last_response = ""
    w._last_thought = ""
    w._is_correcting = False
    w._correct_btn.setText("✎ correct")
    w._thumb_btn.setText("✓ good")
    w._thumb_down_btn.setText("✗ bad")
    w._thumb_btn.setEnabled(False)
    w._thumb_down_btn.setEnabled(False)
    w._correct_btn.setEnabled(False)
    w._sessions_list.blockSignals(True)
    w._sessions_list.setCurrentItem(None)
    w._sessions_list.blockSignals(False)
    w._update_token_budget()


def apply_session_panel_styles(w) -> None:
    """Apply dynamic theme stylesheet to session panel controls."""
    if not hasattr(w, "_session_search") or not w.state:
        return
    colors = get_theme_colors(w.state)
    bg_input = colors.get("bg_input", "#0D0D1B")
    border = colors.get("border", "#1F1F3D")
    text_hi = colors.get("text_hi", "#F0F5FF")
    w._session_search.setStyleSheet(
        f"background-color: {bg_input}; border: 1px solid {border}; border-radius: 4px; "
        f"color: {text_hi}; font-family: 'Inter', sans-serif; font-size: 8.5pt; padding: 4px;"
    )
