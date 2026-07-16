from PyQt6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QKeyEvent

class CommandPalette(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(QSize(500, 320))

        # Build UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        # Main container styled like a glow panel
        self.container = QListWidget() # We'll subclass/use custom layout
        
        self.input_edit = QLineEdit(self)
        self.input_edit.setObjectName("command-input")
        self.input_edit.setPlaceholderText("Search commands or switch workspaces... (Esc to close)")
        self.input_edit.setStyleSheet(
            "background-color: #0D0D1B; border: 1px solid #00E5FF; border-radius: 4px; "
            "color: #F0F5FF; font-family: 'JetBrains Mono', monospace; font-size: 10pt; "
            "padding: 10px; margin: 4px;"
        )
        self.input_edit.textChanged.connect(self._filter_commands)
        layout.addWidget(self.input_edit)

        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #0D0D1B; border: 1px solid #1F1F3D; border-top: none; "
            "border-radius: 0 0 4px 4px; color: #A0AEC0; font-family: 'JetBrains Mono', monospace; "
            "font-size: 9.5pt; padding: 4px; }"
            "QListWidget::item { padding: 8px; border-radius: 3px; }"
            "QListWidget::item:selected { background-color: #00C2FF; color: #020205; font-weight: bold; }"
            "QListWidget::item:hover { background-color: #14142D; color: #F0F5FF; }"
        )
        self.list_widget.itemDoubleClicked.connect(self._execute_selected)
        layout.addWidget(self.list_widget)

        self._commands = [
            ("Switch to Workbench (Chat Space)", lambda: self.main_window.switch_workspace(0)),
            ("Switch to Prompt Lab (Playground)", lambda: self.main_window.switch_workspace(1)),
            ("Switch to Knowledge Base (RAG)", lambda: self.main_window.switch_workspace(2)),
            ("Switch to Vision Workbench", lambda: self.main_window.switch_workspace(3)),
            ("Switch to Training Studio", lambda: self.main_window.switch_workspace(4)),
            ("Switch to Eval Suite (Benchmarks)", lambda: self.main_window.switch_workspace(5)),
            ("Switch to Swarm Studio", lambda: self.main_window.switch_workspace(6)),
            ("Switch to System Config (Settings)", lambda: self.main_window.switch_workspace(7)),
            ("Switch to Codex (Documentation)", lambda: self.main_window.switch_workspace(8)),
            ("Switch to Flywheel Studio", lambda: self.main_window.switch_workspace(9)),
            ("Workbench: Start New Session", self.main_window.start_new_workbench_session),
            ("Workbench: Save Session", self.main_window.save_workbench_session),
            ("Workbench: Toggle RAG Pipeline", self.main_window.toggle_workbench_rag),
            ("Workbench: Toggle Agentic Loop", self.main_window.toggle_workbench_agentic_loop),
            ("Knowledge Base: Ingest Document", self.main_window.open_knowledge_ingest),
            ("Knowledge Base: Rebuild Search Index", self.main_window.rebuild_knowledge_index),
            ("Eval Suite: Run Benchmarks", self.main_window.run_eval_suite),
            ("System Config: Open Defaults Tab", self.main_window.open_system_defaults),
        ]

        self._populate_list()
        self.input_edit.setFocus()

    def _populate_list(self):
        self.list_widget.clear()
        for title, action in self._commands:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(0)

    def _filter_commands(self, text):
        query = text.strip().lower()
        self.list_widget.clear()
        for title, action in self._commands:
            if not query or query in title.lower():
                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, action)
                self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(0)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Up:
            row = self.list_widget.currentRow()
            if row > 0:
                self.list_widget.setCurrentRow(row - 1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            row = self.list_widget.currentRow()
            if row < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(row + 1)
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._execute_selected()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _execute_selected(self):
        curr_item = self.list_widget.currentItem()
        if not curr_item:
            return
        
        title = curr_item.text()
        action = curr_item.data(Qt.ItemDataRole.UserRole)
        
        # Fallback to search list of commands if not set via filtering UserRole
        if not action:
            for t, act in self._commands:
                if t == title:
                    action = act
                    break
        
        self.accept()
        if action:
            action()

    def showEvent(self, event):
        super().showEvent(event)
        # Position command palette at top center of main window
        if self.parentWidget():
            parent_geom = self.parentWidget().geometry()
            x = parent_geom.x() + (parent_geom.width() - self.width()) // 2
            y = parent_geom.y() + 80
            self.move(x, y)
