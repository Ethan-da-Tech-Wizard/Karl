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
            ("Switch to Workbench (Chat Space)", lambda: self.main_window._sidebar.select(0)),
            ("Switch to Prompt Lab (Playground)", lambda: self.main_window._sidebar.select(1)),
            ("Switch to Knowledge Base (RAG)", lambda: self.main_window._sidebar.select(2)),
            ("Switch to Training Studio (LoRA)", lambda: self.main_window._sidebar.select(3)),
            ("Switch to Eval Suite (Benchmarks)", lambda: self.main_window._sidebar.select(4)),
            ("Switch to System Config (Settings)", lambda: self.main_window._sidebar.select(5)),
            ("Switch to Codex (Documentation)", lambda: self.main_window._sidebar.select(6)),
            ("Workbench: Start New Session", lambda: self.main_window._workbench._new_session()),
            ("Workbench: Save Session", lambda: self.main_window._workbench._save_current_session()),
            ("Workbench: Toggle RAG Pipeline", lambda: self.main_window._workbench._rag_check.toggle()),
            ("Workbench: Toggle Agentic Loop", lambda: self.main_window._workbench._loop_check.toggle()),
            ("Knowledge Base: Ingest Document", lambda: (self.main_window._sidebar.select(2), self.main_window._knowledge_base._tabs.setCurrentIndex(1), self.main_window._knowledge_base._ingest_file())),
            ("Knowledge Base: Rebuild Search Index", lambda: (self.main_window._sidebar.select(2), self.main_window._knowledge_base._rebuild_index())),
            ("Eval Suite: Run Benchmarks", lambda: (self.main_window._sidebar.select(4), self.main_window._eval._run_suite())),
            ("System Config: Open Settings Tab", lambda: (self.main_window._sidebar.select(5), self.main_window._system._tabs.setCurrentIndex(4))),
        ]

        self._populate_list()
        self.input_edit.setFocus()

    def _populate_list(self):
        self.list_widget.clear()
        for title, _ in self._commands:
            item = QListWidgetItem(title)
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
