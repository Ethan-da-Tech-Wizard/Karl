import os
import sys
from PyQt6.QtCore import QMimeData, QUrl, Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.qt_test_helper  # Ensures global QApplication runs headlessly
from app.ui.workspaces.knowledge_base import KnowledgeBaseWorkspace
from app.ui.workspaces.training_studio.dataset_tab import DatasetListModel

class MockState:
    def __init__(self):
        class MockCurator:
            def __init__(self):
                self.examples = [
                    {"instruction": "say hello", "output": "hello there", "source": "thumbs_up"},
                    {"instruction": "fix python syntax", "output": "print('fixed')", "source": "corrected"}
                ]
            def get_all_examples(self):
                return self.examples
            def delete_example(self, row):
                if 0 <= row < len(self.examples):
                    self.examples.pop(row)
        
        class MockRag:
            def list_sources(self):
                return []
            @property
            def is_encoder_loaded(self):
                return False
            @property
            def total_chunks(self):
                return 0
            @property
            def total_sources(self):
                return 0
            INDEX_FILE = "index.faiss"
            META_FILE = "metadata.json"
        
        self.curator = MockCurator()
        self.rag = MockRag()
        self.rag_threshold = 0.5
        self.rag_top_k = 3

def test_dataset_list_model():
    model = DatasetListModel()
    assert model.rowCount() == 0

    data = [
        "✓ positive: test 1",
        "✎ corrected: test 2"
    ]
    model.update_data(data)
    assert model.rowCount() == 2
    assert model.get_item(0) == data[0]
    assert model.get_item(1) == data[1]
    assert model.get_item(2) is None

    # Test display role formatting
    val = model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole)
    assert "test 1" in str(val)

def test_drag_drop_filter():
    state = MockState()
    # Instantiate workspace widget
    workspace = KnowledgeBaseWorkspace(state)
    
    # Verify drops are accepted
    assert workspace.acceptDrops()

    # Create dummy files
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f_py, \
         tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_png:
        py_name = f_py.name
        png_name = f_png.name

    try:
        # Mock drag/drop event
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(py_name), QUrl.fromLocalFile(png_name)])
        
        class MockDropEvent:
            def __init__(self, mime_data):
                self._mime = mime_data
                self.accepted = False
            def mimeData(self):
                return self._mime
            def acceptProposedAction(self):
                self.accepted = True

        mock_event = MockDropEvent(mime)
        workspace.dropEvent(mock_event)
        
        # Verify queue contains the .py file and NOT the .png file
        queue_paths = [item["path"] for item in workspace._ingest_queue]
        assert py_name in queue_paths
        assert png_name not in queue_paths
        assert workspace._ingest_status.text() == "Queued 1 file(s) via Drag & Drop."
        
    finally:
        if os.path.exists(py_name):
            os.remove(py_name)
        if os.path.exists(png_name):
            os.remove(png_name)
