import os
import sys
import tempfile
import unittest
import tests.qt_test_helper  # noqa: F401

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestUIImprovements(unittest.TestCase):
    def test_theme_qss_generation(self):
        from app.ui.themes import THEMES, get_theme_stylesheet
        for theme_name in THEMES.keys():
            qss = get_theme_stylesheet(theme_name)
            self.assertIsNotNone(qss)
            self.assertGreater(len(qss), 100)
            # Check that formatting keys were properly substituted
            self.assertNotIn("{accent}", qss)
            self.assertNotIn("{bg_deep}", qss)

    def test_theme_config_read_write(self):
        from app.ui.themes import darken_hex_color, _tint_hex_color, get_theme_colors
        
        # Test color darkening helper
        self.assertEqual(darken_hex_color("#00C2FF", 0.5), "#00617F")
        
        # Test color tinting helper
        self.assertEqual(_tint_hex_color("#102030", 5, -5, 10), "#151B3A")
        
        # Verify custom combination palette building
        colors = get_theme_colors("macOS Sonoma", custom_accent="#FF0000", bg_tone="Pitch Black")
        self.assertEqual(colors["accent"], "#FF0000")
        self.assertEqual(colors["bg_deep"], "#000000")
        self.assertEqual(colors["sidebar_bg"], "#000000")
        
        # Verify sepia/warm tone shifting
        base_colors = get_theme_colors("Karl Obsidian")
        warm_colors = get_theme_colors("Karl Obsidian", bg_tone="Warm Sepia")
        self.assertNotEqual(warm_colors["bg_deep"], base_colors["bg_deep"])

    def test_codex_library_loading_and_search(self):
        from app.ui.workspaces.docs_data import DEFAULT_LIBRARY
        from app.ui.workspaces.docs import DocsWorkspace
        from app.state import AppState
        
        # Verify default library structure
        self.assertIn("Steering Tactics", DEFAULT_LIBRARY)
        self.assertIn("Python", DEFAULT_LIBRARY)
        self.assertIn("Docker", DEFAULT_LIBRARY)
        self.assertIn("FastAPI", DEFAULT_LIBRARY)
        
        # Instantiate AppState and DocsWorkspace
        state = AppState()
        workspace = DocsWorkspace(state)
        
        # Check cache is populated
        self.assertGreater(len(workspace._cache), 0)
        self.assertIn("Steering Tactics", workspace._cache)
        self.assertIn("Python", workspace._cache)
        
        # Test search filtering logic
        workspace._search_input.setText("rust")
        
        visible_items = []
        for idx in range(workspace._topics_list.count()):
            item = workspace._topics_list.item(idx)
            if not item.isHidden():
                visible_items.append(item.text())
        
        self.assertIn("Rust", visible_items)
        
        # Test selecting a topic loads it dynamically
        workspace._on_topic_selected("Rust")
        rendered_html = workspace._browser.toHtml().lower()
        self.assertIn("borrowing", rendered_html)
        self.assertIn("ownership", rendered_html)

    def test_workbench_docks(self):
        from app.state import AppState
        from app.ui.workspaces.workbench import WorkbenchWorkspace
        from PyQt6.QtWidgets import QMainWindow, QDockWidget

        state = AppState()
        workbench = WorkbenchWorkspace(state)

        # Verify it inherits from QMainWindow
        self.assertTrue(isinstance(workbench, QMainWindow))

        # Verify central widget is set
        self.assertIsNotNone(workbench.centralWidget())

        # Verify the two docks exist
        self.assertTrue(hasattr(workbench, "_sessions_dock"))
        self.assertTrue(hasattr(workbench, "_reasoning_dock"))
        self.assertTrue(isinstance(workbench._sessions_dock, QDockWidget))
        self.assertTrue(isinstance(workbench._reasoning_dock, QDockWidget))

    def test_agentic_loop_persists_only_final_assistant_answer(self):
        from app.state import AppState
        from app.ui.workspaces.workbench import WorkbenchWorkspace
        from app.utils.memory_manager import MemoryManager

        class FakeThread:
            def __init__(self, history):
                self.chat_history = history

        state = AppState()
        with tempfile.TemporaryDirectory() as tmpdir:
            state.memory = MemoryManager(sessions_dir=tmpdir)
            workbench = WorkbenchWorkspace(state)

            user_node = workbench.chat_history.add_message("user", "how many sides does a hexagon have?")
            workbench._chat_view.push_user("how many sides does a hexagon have?", user_node.id)
            workbench._thread = FakeThread([
                {"role": "user", "content": "how many sides does a hexagon have?"},
                {"role": "assistant", "content": "A hexagon has 6 sides."},
                {"role": "user", "content": "[Iteration 2] Continue."},
                {"role": "assistant", "content": "FINAL ANSWER: A hexagon has 6 sides."},
            ])

            workbench._on_loop_done(2)
            active = list(workbench.chat_history)

            self.assertEqual(
                active,
                [
                    {"role": "user", "content": "how many sides does a hexagon have?", "id": active[0]["id"]},
                    {"role": "assistant", "content": "FINAL ANSWER: A hexagon has 6 sides.", "id": active[1]["id"]},
                ],
            )
            self.assertNotIn("Iteration", "\n".join(msg["content"] for msg in active))

if __name__ == "__main__":
    unittest.main()
