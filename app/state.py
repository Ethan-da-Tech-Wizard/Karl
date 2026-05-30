"""
Shared application state passed to every workspace.
Workspaces communicate through this object rather than through MainWindow.
"""
from app.utils.rag_pipeline import RAGPipeline
from app.utils.memory_manager import MemoryManager
from app.utils.trace_logger import TraceLogger
from app.utils.training_curator import TrainingCurator


class AppState:
    def __init__(self):
        self.rag = RAGPipeline()
        self.memory = MemoryManager()
        self.logger = TraceLogger()
        self.curator = TrainingCurator()

        # Updated by WorkbenchWorkspace and read by status bar
        self.model_name: str = "none"
        self.adapter_name: str | None = None
        self.generating: bool = False
