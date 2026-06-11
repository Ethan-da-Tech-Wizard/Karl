"""
Shared application state passed to every workspace.
Workspaces communicate through this object rather than through MainWindow.
"""
from app.utils.rag_pipeline import RAGPipeline
from app.utils.memory_manager import MemoryManager
from app.utils.trace_logger import TraceLogger
from app.utils.training_curator import TrainingCurator
from app.vision.image_store import ImageStore


class AppState:
    def __init__(self):
        self.rag = RAGPipeline()
        self.codex_rag = RAGPipeline(namespace="codex")
        self.memory = MemoryManager()
        self.logger = TraceLogger()
        self.curator = TrainingCurator()
        self.image_store = ImageStore()

        # Updated by WorkbenchWorkspace and read by status bar
        self.model_name: str = "none"
        self.adapter_name: str | None = None
        self.generating: bool = False

        # RAG retrieval parameters wired between KB and Workbench
        self.rag_threshold: float = 0.0
        self.rag_top_k: int = 3

        # Global UI visual adjustments
        self.reduced_motion: bool = False
        self.theme_preset: str = "Karl Obsidian Core"
        self.custom_accent: str | None = None
        self.layout_preset: str = "Focused Workbench"
        self.glow_enabled: bool = True
        self.animation_intensity: float = 1.0
        self.glow_strength: float = 1.0
