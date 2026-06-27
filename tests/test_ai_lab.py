import os
import json
import unittest
import tempfile
import shutil
from PyQt6.QtWidgets import QTabWidget

import tests.qt_test_helper  # noqa: F401
from app.state import AppState
from app.ui.workspaces.ai_lab import AILabWorkspace
from app.utils.rag_pipeline import RAGPipeline

class TestAILabWorkspace(unittest.TestCase):
    def setUp(self):
        self.state = AppState()
        self.temp_dir = tempfile.mkdtemp()
        self.state.rag = RAGPipeline(index_path=self.temp_dir, namespace="test")
        
        # Back up custom_agents.json if it exists
        self.custom_agents_path = os.path.join("data", "custom_agents.json")
        self.backup_content = None
        if os.path.exists(self.custom_agents_path):
            with open(self.custom_agents_path, "r", encoding="utf-8") as f:
                self.backup_content = f.read()
                
    def tearDown(self):
        # Clean up temp DB
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Restore backup or remove custom_agents.json
        if os.path.exists(self.custom_agents_path):
            try:
                os.remove(self.custom_agents_path)
            except OSError:
                pass
        if self.backup_content is not None:
            os.makedirs("data", exist_ok=True)
            with open(self.custom_agents_path, "w", encoding="utf-8") as f:
                f.write(self.backup_content)

    def test_construction_and_layout(self):
        workspace = AILabWorkspace(self.state)
        self.assertIsNotNone(workspace)
        self.assertTrue(isinstance(workspace._tabs, QTabWidget))
        self.assertEqual(workspace._tabs.count(), 2)
        
        # Tab A structure
        self.assertEqual(workspace._tabs.tabText(0), "Pipeline Visualizer")
        self.assertEqual(workspace._tabs.tabText(1), "Agent Composer")
        
        # Pipeline widgets
        self.assertTrue(hasattr(workspace, "_sentences_input"))
        self.assertTrue(hasattr(workspace, "_vectorizer_combo"))
        self.assertTrue(hasattr(workspace, "_vocab_table"))
        self.assertTrue(hasattr(workspace, "_matrix_table"))
        self.assertTrue(hasattr(workspace, "_query_input"))
        self.assertTrue(hasattr(workspace, "_rag_results_browser"))
        self.assertTrue(hasattr(workspace, "_projection_widget"))
        self.assertTrue(hasattr(workspace, "_flowchart_widget"))
        
        # Composer widgets
        self.assertTrue(hasattr(workspace, "_agent_name_input"))
        self.assertTrue(hasattr(workspace, "_agent_label_input"))
        self.assertTrue(hasattr(workspace, "_agent_desc_input"))
        self.assertTrue(hasattr(workspace, "_agent_system_input"))
        self.assertTrue(hasattr(workspace, "_base_model_combo"))
        self.assertTrue(hasattr(workspace, "_lora_adapter_combo"))
        self.assertTrue(hasattr(workspace, "_rag_enabled_check"))
        self.assertTrue(hasattr(workspace, "_rag_top_k_spin"))
        self.assertTrue(hasattr(workspace, "_publish_btn"))

    def test_sparse_pipeline_math(self):
        workspace = AILabWorkspace(self.state)
        
        # Set text to sandbox docs
        workspace._sentences_input.setPlainText("hello world\nhello neural agent\nworld search")
        workspace._vectorizer_combo.setCurrentIndex(0) # TF-IDF
        workspace._run_pipeline()
        
        # Verify vocabulary table matches terms
        vocab = workspace._tfidf.vocabulary
        self.assertEqual(workspace._vocab_table.rowCount(), len(vocab))
        
        # Verify document-term matrix populated
        self.assertEqual(workspace._matrix_table.rowCount(), 3)
        self.assertEqual(workspace._matrix_table.columnCount(), len(vocab) + 1)
        
        # Run query and verify similarity calculations
        workspace._query_input.setText("hello search")
        workspace._run_query()
        
        results_html = workspace._rag_results_browser.toHtml()
        self.assertIn("Cosine Similarity", results_html)
        self.assertIn("Dot Product", results_html)
        self.assertIn("Norm", results_html)

    def test_custom_agent_publishing(self):
        workspace = AILabWorkspace(self.state)
        
        # Mock values
        workspace._agent_name_input.setText("expert_karl")
        workspace._agent_label_input.setText("Expert Karl")
        workspace._agent_desc_input.setText("An expert agent profile")
        workspace._agent_system_input.setPlainText("System prompt identity rules.")
        workspace._rag_enabled_check.setChecked(True)
        workspace._rag_top_k_spin.setValue(5)
        
        # Mock message boxes to avoid blocking the thread
        from PyQt6.QtWidgets import QMessageBox
        original_info = QMessageBox.information
        original_warning = QMessageBox.warning
        QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
        QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
        
        # Capture signal
        published_agent_id = []
        workspace.agent_published.connect(published_agent_id.append)
        
        try:
            workspace._publish_agent()
        finally:
            QMessageBox.information = original_info
            QMessageBox.warning = original_warning
            
        # Verify signal emitted
        self.assertEqual(published_agent_id, ["expert_karl"])
        
        # Verify saved in data/custom_agents.json
        self.assertTrue(os.path.exists(self.custom_agents_path))
        with open(self.custom_agents_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertIn("expert_karl", data)
        agent = data["expert_karl"]
        self.assertEqual(agent["label"], "Expert Karl")
        self.assertEqual(agent["description"], "An expert agent profile")
        self.assertEqual(agent["prompt"], "System prompt identity rules.")
        self.assertEqual(agent["system_prompt"], "System prompt identity rules.")
        self.assertEqual(agent["rag_top_k"], 5)
        self.assertTrue(agent["rag_enabled"])
        
        # Verify form reset
        self.assertEqual(workspace._agent_name_input.text(), "")
        self.assertEqual(workspace._agent_label_input.text(), "")
        self.assertEqual(workspace._agent_desc_input.text(), "")
        self.assertEqual(workspace._agent_system_input.toPlainText(), "")

if __name__ == "__main__":
    unittest.main()
