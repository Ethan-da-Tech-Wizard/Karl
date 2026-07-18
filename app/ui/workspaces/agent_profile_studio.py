"""
Karl Swarm Agent Profile Studio
================================
Provides a PyQt6 user interface to visual customize Specialist Agent roles,
system prompt instructions, allowed permission structures, and parameter overrides.
"""

from __future__ import annotations

import logging
from typing import Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QTextEdit, QCheckBox, QDoubleSpinBox,
    QSpinBox, QFormLayout, QGroupBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from app.utils.swarm_agent_profiles import (
    PROFILE_ID_RE,
    load_agent_profiles,
    save_agent_profile,
)

logger = logging.getLogger("karl.agent_profile_studio")


class AgentProfileStudioWorkspace(QWidget):
    """Visual workspace for managing and synchronizing swarm agent profiles."""

    profile_saved = pyqtSignal(str)  # Emits profile name when saved

    def __init__(self, state: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = state
        self._profiles: dict[str, dict] = {}
        self._current_id = ""
        self._init_ui()
        self._load_profiles()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left panel: list of profiles
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Agent Specialist Roles"))
        self._list_widget = QListWidget()
        self._list_widget.currentRowChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self._list_widget)

        self._btn_new = QPushButton("New Specialist")
        self._btn_new.clicked.connect(self._on_new_profile)
        left_layout.addWidget(self._btn_new)
        
        layout.addWidget(left_panel, 1)

        # Right panel: Profile Editor
        self._editor_panel = QGroupBox("Profile Editor")
        editor_layout = QVBoxLayout(self._editor_panel)
        form_layout = QFormLayout()

        self._name_input = QLineEdit()
        form_layout.addRow("Role Name:", self._name_input)

        self._id_input = QLineEdit()
        self._id_input.setPlaceholderText("architect, coder, tester, security_reviewer")
        form_layout.addRow("Profile ID:", self._id_input)

        self._icon_input = QLineEdit()
        form_layout.addRow("Icon/Avatar (emoji):", self._icon_input)

        self._prompt_input = QTextEdit()
        self._prompt_input.setPlaceholderText("Instructions for the model guiding this role...")
        form_layout.addRow("System Instructions:", self._prompt_input)

        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.1)
        self._temp_spin.setValue(0.7)
        form_layout.addRow("Temperature:", self._temp_spin)

        self._tokens_spin = QSpinBox()
        self._tokens_spin.setRange(256, 8192)
        self._tokens_spin.setSingleStep(256)
        self._tokens_spin.setValue(2048)
        form_layout.addRow("Max Tokens Limit:", self._tokens_spin)

        editor_layout.addLayout(form_layout)

        # Permissions Group
        perm_group = QGroupBox("Allowed Specialist Permissions")
        perm_layout = QVBoxLayout(perm_group)
        self._chk_read = QCheckBox("Read Workspace Files")
        self._chk_write = QCheckBox("Write/Modify Workspace Files")
        self._chk_terminal = QCheckBox("Execute Sandbox Terminal Commands")
        self._chk_rag = QCheckBox("Query RAG Vector Database")
        
        perm_layout.addWidget(self._chk_read)
        perm_layout.addWidget(self._chk_write)
        perm_layout.addWidget(self._chk_terminal)
        perm_layout.addWidget(self._chk_rag)
        editor_layout.addWidget(perm_group)

        # Save/Revert Buttons
        btn_layout = QHBoxLayout()
        self._btn_revert = QPushButton("Revert")
        self._btn_revert.clicked.connect(self._on_revert_profile)
        btn_layout.addWidget(self._btn_revert)

        self._btn_save = QPushButton("Save Profile")
        self._btn_save.clicked.connect(self._on_save_profile)
        btn_layout.addWidget(self._btn_save)
        
        editor_layout.addLayout(btn_layout)
        layout.addWidget(self._editor_panel, 2)

    def _load_profiles(self):
        """Loads profiles from JSON and populates the list widget."""
        self._profiles = load_agent_profiles()
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        for profile_id, profile in sorted(self._profiles.items()):
            label = f"{profile.get('icon', '')} {profile.get('name', profile_id)}"
            self._list_widget.addItem(label.strip())
            self._list_widget.item(self._list_widget.count() - 1).setData(256, profile_id)
        self._list_widget.blockSignals(False)
        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    def _on_profile_selected(self, index: int):
        """Populates form controls with the selected profile settings."""
        item = self._list_widget.item(index)
        if item is None:
            return
        profile_id = item.data(256)
        self._current_id = profile_id
        self._load_profile_into_form(profile_id)

    def _on_new_profile(self):
        """Clears the editor form to create a new profile configuration."""
        self._current_id = ""
        self._list_widget.clearSelection()
        self._id_input.setReadOnly(False)
        self._id_input.setText("")
        self._name_input.setText("")
        self._icon_input.setText("")
        self._prompt_input.clear()
        self._temp_spin.setValue(0.2)
        self._tokens_spin.setValue(2048)
        for checkbox in self._permission_checkboxes().values():
            checkbox.setChecked(False)

    def _on_revert_profile(self):
        """Discards current unsaved edits in the editor panel."""
        if self._current_id:
            self._load_profile_into_form(self._current_id)
        else:
            self._on_new_profile()

    def _on_save_profile(self):
        """Serializes current editor values and saves to JSON."""
        profile_id = self._id_input.text().strip()
        if not PROFILE_ID_RE.match(profile_id):
            QMessageBox.warning(self, "Agent Profiles", "Profile ID must start with a letter and use only letters, numbers, '_' or '-'.")
            return
        profile = {
            "name": self._name_input.text().strip() or profile_id,
            "icon": self._icon_input.text().strip() or profile_id[:1].upper(),
            "system_prompt": self._prompt_input.toPlainText(),
            "temperature": self._temp_spin.value(),
            "context_limit": self._tokens_spin.value(),
            "tools": {
                key: checkbox.isChecked()
                for key, checkbox in self._permission_checkboxes().items()
            },
        }
        try:
            saved = save_agent_profile(profile_id, profile)
        except Exception as exc:
            QMessageBox.warning(self, "Agent Profiles", f"Failed to save profile: {exc}")
            return
        self._profiles[profile_id] = saved
        self._current_id = profile_id
        self._load_profiles()
        for row in range(self._list_widget.count()):
            if self._list_widget.item(row).data(256) == profile_id:
                self._list_widget.setCurrentRow(row)
                break
        self.profile_saved.emit(profile_id)

    def _permission_checkboxes(self) -> dict[str, QCheckBox]:
        return {
            "read_files": self._chk_read,
            "write_files": self._chk_write,
            "execute_sandbox": self._chk_terminal,
            "query_rag": self._chk_rag,
        }

    def _load_profile_into_form(self, profile_id: str):
        profile = self._profiles.get(profile_id)
        if not profile:
            return
        self._id_input.setText(profile_id)
        self._id_input.setReadOnly(profile.get("builtin", False))
        self._name_input.setText(profile.get("name", profile_id))
        self._icon_input.setText(profile.get("icon", ""))
        self._prompt_input.setPlainText(profile.get("system_prompt", ""))
        self._temp_spin.setValue(float(profile.get("temperature", 0.2)))
        self._tokens_spin.setValue(int(profile.get("context_limit", 2048)))
        tools = profile.get("tools", {})
        for key, checkbox in self._permission_checkboxes().items():
            checkbox.setChecked(bool(tools.get(key, False)))
