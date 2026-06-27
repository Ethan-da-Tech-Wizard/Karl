"""Model combo box — reusable model and adapter selector widget."""

from __future__ import annotations

import logging
import os
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import Qt

from app.engine import config_store

logger = logging.getLogger("karl.widgets.model_combo")


class ModelComboBox(QComboBox):
    """Reusable dropdown to select local models and their compatible LoRA adapters."""

    def __init__(self, state, parent=None, short_labels: bool = True):
        super().__init__(parent)
        self.state = state
        self.short_labels = short_labels
        self.refresh_models()

    def update_theme(self):
        """Update the component dynamically when the theme changes."""
        # Read theme colors and refresh to re-evaluate ACTIVE labels
        self.refresh_models()

    def refresh_models(self):
        """Re-scan models and adapters, rebuild items, and restore selection."""
        self.blockSignals(True)
        current_data = self.currentData()
        self.clear()

        # Scan adapters
        adapters_dir = "data/adapters"
        adapters = []
        if os.path.exists(adapters_dir):
            try:
                for d in sorted(os.listdir(adapters_dir)):
                    d_path = os.path.join(adapters_dir, d)
                    if os.path.isdir(d_path):
                        files_in_dir = os.listdir(d_path)
                        if any(f.endswith(".gguf") or f.endswith(".bin") for f in files_in_dir):
                            adapters.append(d)
            except Exception as e:
                logger.warning("Error scanning adapters in ModelComboBox: %s", e)

        # Scan models
        models_dir = "data/models"
        files = []
        if os.path.exists(models_dir):
            try:
                files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
            except Exception as e:
                logger.warning("Error scanning models in ModelComboBox: %s", e)

        # Get registry
        registry = {}
        try:
            for item in config_store.get_model_registry():
                registry[item.get("filename", "")] = item
        except Exception as e:
            logger.warning("Error reading model registry in ModelComboBox: %s", e)

        entries = []
        for filename in sorted(files):
            meta = registry.get(filename, {})
            size = self._model_file_size_label(filename)
            detail = self._model_registry_detail(filename, meta, size)

            entries.append({
                "short_label": filename,
                "label": detail,
                "tooltip": self._model_tooltip(filename, meta, size, None),
                "data": {"model": filename, "adapter": None, "meta": meta},
            })
            for adapter in adapters:
                if config_store.is_adapter_compatible(filename, adapter):
                    entries.append({
                        "short_label": f"{filename} ({adapter})",
                        "label": f"{detail} · adapter {adapter}",
                        "tooltip": self._model_tooltip(filename, meta, size, adapter),
                        "data": {"model": filename, "adapter": adapter, "meta": meta},
                    })

        # Add items
        for entry in entries:
            label = entry["short_label"] if self.short_labels else entry["label"]
            self.addItem(label, entry["data"])
            idx = self.count() - 1
            self.setItemData(idx, entry["tooltip"], Qt.ItemDataRole.ToolTipRole)

        # Restore selection
        target_model = None
        target_adapter = None
        if current_data and isinstance(current_data, dict):
            target_model = current_data.get("model")
            target_adapter = current_data.get("adapter")
        elif self.state:
            target_model = self.state.model_name
            target_adapter = self.state.adapter_name

        self.select_model(target_model, target_adapter)
        self.blockSignals(False)

    def select_model(self, model_filename: str | None, adapter_name: str | None) -> bool:
        """Find and select the matching model and adapter combination."""
        if not model_filename:
            if self.count() > 0:
                self.setCurrentIndex(0)
            return False

        found = False
        for idx in range(self.count()):
            d = self.itemData(idx)
            if isinstance(d, dict) and d.get("model") == model_filename and d.get("adapter") == adapter_name:
                self.setCurrentIndex(idx)
                found = True
                break

        if not found:
            # Fallback to model match only without adapter
            for idx in range(self.count()):
                d = self.itemData(idx)
                if isinstance(d, dict) and d.get("model") == model_filename and d.get("adapter") is None:
                    self.setCurrentIndex(idx)
                    found = True
                    break

        if not found and self.count() > 0:
            self.setCurrentIndex(0)

        return found

    def _model_file_size_label(self, filename: str) -> str:
        path = os.path.join("data", "models", filename)
        try:
            return f"{os.path.getsize(path) / (1024 ** 3):.2f} GB"
        except Exception:
            return "unknown size"

    def _model_registry_detail(self, filename: str, meta: dict, size: str) -> str:
        tier = meta.get("tier")
        n_ctx = meta.get("n_ctx")
        ram = meta.get("min_ram_gb")
        bits = [filename, size]
        if tier:
            bits.append(f"Tier {tier}")
        if n_ctx:
            bits.append(f"ctx {int(n_ctx):,}")
        if ram:
            bits.append(f"RAM {ram} GB")
        if self.state and filename == self.state.model_name:
            bits.append("ACTIVE")
        return " · ".join(bits)

    def _model_tooltip(self, filename: str, meta: dict, size: str, adapter: str | None) -> str:
        lines = [
            f"File: {filename}",
            f"Size: {size}",
            f"Adapter: {adapter or 'none'}",
        ]
        if meta:
            lines.extend([
                f"Registry name: {meta.get('name', filename)}",
                f"Tier: {meta.get('tier', 'unknown')}",
                f"Context: {meta.get('n_ctx', 'unknown')}",
                f"Recommended RAM: {meta.get('min_ram_gb', 'unknown')} GB",
            ])
        return "\n".join(lines)
