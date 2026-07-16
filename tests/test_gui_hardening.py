import tests.qt_test_helper  # noqa: F401

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt


class _FakeMainWindow:
    def __init__(self):
        self.calls = []

    def switch_workspace(self, index):
        self.calls.append(("switch_workspace", index))

    def start_new_workbench_session(self):
        self.calls.append(("start_new_workbench_session",))

    def save_workbench_session(self):
        self.calls.append(("save_workbench_session",))

    def toggle_workbench_rag(self):
        self.calls.append(("toggle_workbench_rag",))

    def toggle_workbench_agentic_loop(self):
        self.calls.append(("toggle_workbench_agentic_loop",))

    def open_knowledge_ingest(self):
        self.calls.append(("open_knowledge_ingest",))

    def rebuild_knowledge_index(self):
        self.calls.append(("rebuild_knowledge_index",))

    def run_eval_suite(self):
        self.calls.append(("run_eval_suite",))

    def open_system_defaults(self):
        self.calls.append(("open_system_defaults",))


def test_command_palette_uses_public_actions():
    from app.ui.widgets.command_palette import CommandPalette

    fake = _FakeMainWindow()
    host = QWidget()
    palette = CommandPalette(fake, parent=host)

    titles = [title for title, _action in palette._commands]
    assert "System Config: Open Defaults Tab" in titles
    assert "System Config: Open Settings Tab" not in titles

    palette.input_edit.setText("Run Benchmarks")
    item = palette.list_widget.item(0)
    assert item is not None
    assert item.data(Qt.ItemDataRole.UserRole) is not None
    palette.list_widget.setCurrentItem(item)
    palette._execute_selected()

    assert fake.calls == [("run_eval_suite",)]


def test_prompt_column_ignores_run_when_thread_active():
    from app.ui.workspaces.prompt_lab import _PromptColumn

    class FakeThread:
        def isRunning(self):
            return True

    column = _PromptColumn("A")
    emitted = []
    column.run_requested.connect(lambda label, text: emitted.append((label, text)))
    column._user_edit.setPlainText("hello")
    column._thread = FakeThread()

    column._emit_run()

    assert emitted == []


def test_prompt_lab_focus_primary_input_targets_active_editor():
    from app.state import AppState
    from app.ui.workspaces.prompt_lab import PromptLabWorkspace

    workspace = PromptLabWorkspace(AppState())
    workspace.show()
    QApplication.processEvents()

    assert workspace.focus_primary_input() is True
    QApplication.processEvents()
    assert QApplication.focusWidget() is workspace._col_a._user_edit


def test_log_decrypt_thread_unauthorized_without_entries():
    from app.ui.workspaces.flywheel_studio import _LogDecryptThread

    signals = []
    thread = _LogDecryptThread("token", [])
    thread.unauthorized.connect(lambda: signals.append("unauthorized"))

    thread.run()

    assert signals == ["unauthorized"]


def test_workspace_public_action_wrappers_exist():
    from app.state import AppState
    from app.ui.workspaces.eval_suite import EvalSuiteWorkspace
    from app.ui.workspaces.knowledge_base import KnowledgeBaseWorkspace
    from app.ui.workspaces.system_config import SystemConfigWorkspace
    from app.ui.workspaces.workbench import WorkbenchWorkspace

    state = AppState()
    workbench = WorkbenchWorkspace(state)
    kb = KnowledgeBaseWorkspace(state)
    eval_suite = EvalSuiteWorkspace(state)
    system = SystemConfigWorkspace(state)

    for name in (
        "new_session",
        "save_current_session",
        "toggle_rag_pipeline",
        "toggle_agentic_loop",
        "toggle_all_huds",
        "toggle_reasoning_panel",
        "toggle_sessions_panel",
        "toggle_rag_panel",
        "toggle_context_panel",
    ):
        assert callable(getattr(workbench, name))

    assert callable(kb.open_ingest_dialog)
    assert callable(kb.rebuild_index)
    assert callable(eval_suite.run_suite)
    assert callable(system.show_defaults_tab)
