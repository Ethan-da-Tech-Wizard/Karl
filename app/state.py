from PyQt6.QtCore import QObject, Q_ARG, QMetaObject, Qt, pyqtSignal, pyqtSlot
from app.utils.rag_pipeline import RAGPipeline
from app.utils.memory_manager import MemoryManager
from app.utils.trace_logger import TraceLogger
from app.utils.training_curator import TrainingCurator
from app.vision.image_store import ImageStore
from app.utils.keychain_manager import load_cached_token
from app.engine import config_store

# Ordered tuple of every AppState attribute that is persisted to ui_config.json.
# Heavy objects (rag, memory, logger, curator, image_store) are intentionally
# excluded — only plain Python scalars are safe to round-trip as JSON.
_PERSIST_FIELDS: tuple[str, ...] = (
    "rag_threshold",
    "rag_top_k",
    "theme_mode",
    "theme_preset",
    "custom_accent",
    "layout_preset",
    "reduced_motion",
    "glow_enabled",
    "animation_intensity",
    "glow_strength",
    "log_rotation_size_mb",
    "log_retention_days",
    "max_log_disk_size_mb",
    "single_session_auth",
    "thermal_protection_enabled",
    "thermal_protection_threshold",
    "enable_dynamic_scheduling",
    "thinking_temperature",
    "answering_temperature",
    "quantized_kv_cache",
)


class AppState(QObject):
    state_changed = pyqtSignal(str, object)
    
    # Decoupled communication signals
    change_workspace_requested = pyqtSignal(int)
    append_to_workbench_input = pyqtSignal(str)
    replace_workbench_input = pyqtSignal(str)
    attach_image_to_workbench = pyqtSignal(str)
    set_workbench_hyperparams = pyqtSignal(dict)
    set_workbench_system_prompt = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._initialized = False

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

        # Swarm Orchestrator state variables
        self.swarm_running: bool = False
        self.swarm_last_objective: str = ""
        self.swarm_last_workspace: str = ""

        # UI Theme mode
        self.theme_mode: str = "midnight"

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
        self.log_rotation_size_mb: int = 10
        self.log_retention_days: int = 30
        self.max_log_disk_size_mb: int = 1024
        self.single_session_auth: bool = False

        # Thermal protection
        self.thermal_protection_enabled: bool = True
        self.thermal_protection_threshold: int = 95

        # Dynamic Scheduling for reasoning models
        self.enable_dynamic_scheduling: bool = True
        self.thinking_temperature: float = 0.8
        self.answering_temperature: float = 0.1

        # KV-cache quantization (8-bit) — reduces VRAM at slight accuracy cost
        self.quantized_kv_cache: bool = False

        self._initialized = True

        # Load persisted settings from disk, overriding the hardcoded defaults
        # above with any previously saved values.
        self._load_from_disk_silent()

    @property
    def cached_bridge_token(self) -> str | None:
        return load_cached_token()

    def save_to_disk(self) -> bool:
        """Persist all _PERSIST_FIELDS to data/ui_config.json via config_store.

        Returns True on success, False if the write failed.
        """
        payload = {field: getattr(self, field) for field in _PERSIST_FIELDS
                   if hasattr(self, field)}
        return config_store.save_ui_config(payload)

    def load_from_disk(self) -> None:
        """Reload all _PERSIST_FIELDS from data/ui_config.json.

        Unknown or corrupt values fall back to their hardcoded defaults via
        config_store.get_ui_config(). Non-persist attributes (rag, memory, …)
        are untouched. Emits state_changed for every field that changes.
        """
        cfg = config_store.get_ui_config()
        for field in _PERSIST_FIELDS:
            if field in cfg:
                setattr(self, field, cfg[field])

    def _load_from_disk_silent(self) -> None:
        """Internal init helper: load persisted settings without emitting signals.

        Used only during __init__ so the UI does not see spurious state_changed
        events before any widgets are connected.
        """
        cfg = config_store.get_ui_config()
        for field in _PERSIST_FIELDS:
            if field in cfg:
                # Bypass __setattr__ to avoid emitting signals during startup
                super(AppState, self).__setattr__(field, cfg[field])

    @pyqtSlot(str, object)
    def _emit_state_changed(self, name: str, value: object) -> None:
        self.state_changed.emit(name, value)

    def __setattr__(self, name, value):
        if name.startswith('_') or not getattr(self, '_initialized', False):
            super().__setattr__(name, value)
            return

        old_value = getattr(self, name, None)
        super().__setattr__(name, value)
        if old_value != value:
            try:
                QMetaObject.invokeMethod(
                    self,
                    "_emit_state_changed",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, name),
                    Q_ARG(object, value),
                )
            except Exception:
                self.state_changed.emit(name, value)
