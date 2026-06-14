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
        from tests.conftest import embedding_model_available
        if not embedding_model_available():
            self.skipTest("sentence-transformers embedding model is unavailable (offline and not cached)")

        from app.ui.workspaces.docs_data import DEFAULT_LIBRARY
        from app.ui.workspaces.docs import DocsWorkspace
        from app.state import AppState
        
        # Verify default library structure
        self.assertIn("AI Steering", DEFAULT_LIBRARY)
        self.assertIn("Python", DEFAULT_LIBRARY)
        self.assertIn("Docker", DEFAULT_LIBRARY)
        self.assertIn("FastAPI", DEFAULT_LIBRARY)
        
        # Instantiate AppState and DocsWorkspace
        state = AppState()
        workspace = DocsWorkspace(state)
        
        # Check cache is populated
        self.assertGreater(len(workspace._cache), 0)
        self.assertIn("AI Steering", workspace._cache)
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
        self.assertIn("borrow", rendered_html)
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
        self.assertTrue(hasattr(workbench, "_branch_stats_lbl"))
        self.assertTrue(hasattr(workbench, "_token_remaining_lbl"))

    def test_swarm_studio_constructs(self):
        from app.state import AppState
        from app.ui.workspaces.swarm_studio import SwarmStudioWorkspace

        state = AppState()
        workspace = SwarmStudioWorkspace(state)

        self.assertIsNotNone(workspace)
        self.assertTrue(hasattr(workspace, "_layers_tree"))
        self.assertTrue(hasattr(workspace, "_task_table"))
        self.assertTrue(hasattr(workspace, "_traceback_browser"))

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

    def test_system_config_features(self):
        from app.state import AppState
        from app.ui.workspaces.system_config import SystemConfigWorkspace
        
        state = AppState()
        state.model_name = "deepseek-r1-distill-qwen-1.5b.gguf"
        state.adapter_name = "llama-adapter"
        
        workspace = SystemConfigWorkspace(state)
        
        # Test settings search filtering
        workspace._settings_search_input.setText("temp")
        row_temp = next(r[1] for r in workspace._settings_rows if r[0] == "Temperature")
        row_topp = next(r[1] for r in workspace._settings_rows if r[0] == "Top-P")
        self.assertFalse(row_temp.isHidden())
        self.assertTrue(row_topp.isHidden())
        
        # Clear search and make sure both are visible
        workspace._settings_search_input.setText("")
        self.assertFalse(row_temp.isHidden())
        self.assertFalse(row_topp.isHidden())
        
        # Test preflight checks / health check warnings
        workspace._run_model_preflight_checks()
        status_text = workspace._model_status.text()
        self.assertIn("MODEL DIAGNOSTIC REPORT", status_text)
        self.assertIn("Adapter Compatibility Mismatch", status_text)
        
        # Test cache population
        workspace.refresh_filesystem_cache()
        self.assertIsNotNone(workspace._cached_models_list)
        self.assertIsNotNone(workspace._cached_adapters_list)

    def test_codex_rag_features(self):
        from tests.conftest import embedding_model_available
        if not embedding_model_available():
            self.skipTest("sentence-transformers embedding model is unavailable (offline and not cached)")

        from app.state import AppState
        from app.ui.workspaces.docs import DocsWorkspace
        from app.ui.workspaces.workbench import WorkbenchWorkspace
        import tempfile
        import shutil
        
        state = AppState()
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        
        from app.utils.rag_pipeline import RAGPipeline
        state.rag = RAGPipeline(index_path=temp_dir, namespace="user")
        state.codex_rag = RAGPipeline(index_path=temp_dir, namespace="codex")
        
        workbench = WorkbenchWorkspace(state)
        docs_workspace = DocsWorkspace(state, workbench_ref=workbench)
        
        self.assertIn("codex_index.faiss", state.codex_rag.INDEX_FILE)
        self.assertIn("index.faiss", state.rag.INDEX_FILE)
        
        test_file = os.path.join(temp_dir, "TestTopic.html")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("<h2>TestTopic</h2><p>This is a descriptor metaclass borrow checker query manual.</p>")
            
        state.codex_rag.ingest_file(test_file)
        self.assertGreater(state.codex_rag.total_chunks, 0)
        
        user_file = os.path.join(temp_dir, "UserDoc.txt")
        with open(user_file, "w", encoding="utf-8") as f:
            f.write("Information about local client setups.")
        state.rag.ingest_file(user_file)
        
        docs_workspace._cache["TestTopic"] = {
            "filepath": test_file,
            "content": "<h2>TestTopic</h2><p>This is a descriptor metaclass borrow checker query manual.</p>"
        }
        docs_workspace._cache["OtherTopic"] = {
            "filepath": os.path.join(temp_dir, "OtherTopic.html"),
            "content": "Some other content"
        }
        docs_workspace._topics_list.clear()
        docs_workspace._topics_list.addItem("TestTopic")
        docs_workspace._topics_list.addItem("OtherTopic")
        
        docs_workspace._filter_topics("borrow checker")
        
        current = docs_workspace._topics_list.currentItem()
        self.assertIsNotNone(current)
        self.assertEqual(current.text(), "TestTopic")
        
        from PyQt6.QtWidgets import QMessageBox
        original_info = QMessageBox.information
        QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
        try:
            docs_workspace._send_to_workbench()
        finally:
            QMessageBox.information = original_info
            
        input_text = workbench._input.toPlainText()
        self.assertIn("[Codex: TestTopic]", input_text)
        self.assertIn("descriptor metaclass borrow checker query manual", input_text)

if __name__ == "__main__":
    unittest.main()
