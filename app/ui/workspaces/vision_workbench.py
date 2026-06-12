from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.engine.image_analysis_thread import ImageAnalysisThread
from app.vision.vision_model_loader import VisionModelLoader, installed_vision_models


class VisionWorkbench(QWidget):
    def __init__(self, state, workbench_ref=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.workbench_ref = workbench_ref
        self.setObjectName("workspace-root")
        self._records = []
        self._selected_id = ""
        self._active_threads = set()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title_row = QWidget()
        tl = QHBoxLayout(title_row)
        tl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Vision Workbench")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        tl.addWidget(title)
        tl.addStretch()

        self._refresh_btn = QPushButton("refresh")
        self._refresh_btn.setObjectName("btn-ghost")
        self._refresh_btn.clicked.connect(self.refresh)
        tl.addWidget(self._refresh_btn)

        self._import_btn = QPushButton("import image")
        self._import_btn.setObjectName("btn-primary")
        self._import_btn.clicked.connect(self._import_image)
        tl.addWidget(self._import_btn)

        self._rerun_analysis_btn = QPushButton("run analysis")
        self._rerun_analysis_btn.setObjectName("btn-ghost")
        self._rerun_analysis_btn.clicked.connect(self._run_analysis)
        tl.addWidget(self._rerun_analysis_btn)
        root.addWidget(title_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)
        self._library = QListWidget()
        self._library.currentItemChanged.connect(self._on_selected)
        ll.addWidget(self._library, 1)
        splitter.addWidget(left)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)
        self._preview = QLabel("No image selected.")
        self._preview.setObjectName("panel")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(360, 300)
        self._preview.setScaledContents(False)
        cl.addWidget(self._preview, 1)
        action_row = QWidget()
        al = QHBoxLayout(action_row)
        al.setContentsMargins(0, 0, 0, 0)
        self._open_btn = QPushButton("open file")
        self._open_btn.clicked.connect(self._open_file)
        self._send_btn = QPushButton("send to workbench")
        self._send_btn.setObjectName("btn-primary")
        self._send_btn.clicked.connect(self._send_to_workbench)
        al.addWidget(self._open_btn)
        al.addWidget(self._send_btn)
        cl.addWidget(action_row)
        splitter.addWidget(center)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self._meta = QLabel("Select an image to inspect metadata.")
        self._meta.setObjectName("lbl-muted")
        self._meta.setWordWrap(True)
        rl.addWidget(self._meta)

        analysis_panel = QWidget()
        analysis_panel.setObjectName("panel")
        apl = QVBoxLayout(analysis_panel)
        apl.setContentsMargins(10, 10, 10, 10)
        apl.setSpacing(8)

        self._vision_status = QLabel("")
        self._vision_status.setObjectName("lbl-muted")
        self._vision_status.setWordWrap(True)
        apl.addWidget(self._vision_status)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("OCR + Vision", "ocr_vision")
        self._mode_combo.addItem("OCR Only", "ocr_only")
        self._mode_combo.addItem("Vision Only", "vision_only")
        apl.addWidget(self._mode_combo)

        self._analysis_prompt = QTextEdit()
        self._analysis_prompt.setMaximumHeight(72)
        self._analysis_prompt.setPlaceholderText(
            "Optional image question for local vision model. Leave blank for Karl's screenshot/debugging prompt."
        )
        apl.addWidget(self._analysis_prompt)

        analysis_row = QWidget()
        arl = QHBoxLayout(analysis_row)
        arl.setContentsMargins(0, 0, 0, 0)
        self._analysis_btn = QPushButton("analyze selected image")
        self._analysis_btn.setObjectName("btn-primary")
        self._analysis_btn.clicked.connect(self._run_analysis)
        arl.addWidget(self._analysis_btn)
        apl.addWidget(analysis_row)

        self._registry_label = QLabel("")
        self._registry_label.setObjectName("lbl-muted")
        self._registry_label.setWordWrap(True)
        apl.addWidget(self._registry_label)
        rl.addWidget(analysis_panel)

        self._kind_combo = QComboBox()
        for kind in ("unknown", "code_screenshot", "error", "document", "diagram", "ui_mockup", "photo"):
            self._kind_combo.addItem(kind.replace("_", " ").title(), kind)
        rl.addWidget(self._kind_combo)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("tags: code, error, vscode")
        rl.addWidget(self._tags)

        meta_row = QWidget()
        ml = QHBoxLayout(meta_row)
        ml.setContentsMargins(0, 0, 0, 0)
        self._save_meta_btn = QPushButton("save metadata")
        self._save_meta_btn.clicked.connect(self._save_metadata)
        ml.addWidget(self._save_meta_btn)
        rl.addWidget(meta_row)

        self._ocr = QTextEdit()
        self._ocr.setReadOnly(False)
        self._ocr.setPlaceholderText("OCR text will appear here after analysis. Edit and save corrections here.")
        rl.addWidget(self._ocr, 1)

        ocr_row = QWidget()
        ol = QHBoxLayout(ocr_row)
        ol.setContentsMargins(0, 0, 0, 0)
        self._save_ocr_btn = QPushButton("save OCR correction")
        self._save_ocr_btn.setObjectName("btn-primary")
        self._save_ocr_btn.clicked.connect(self._save_ocr_correction)
        ol.addWidget(self._save_ocr_btn)
        rl.addWidget(ocr_row)

        self._caption = QTextEdit()
        self._caption.setPlaceholderText("Future visual summary/caption correction area.")
        rl.addWidget(self._caption, 1)

        caption_row = QWidget()
        crl = QHBoxLayout(caption_row)
        crl.setContentsMargins(0, 0, 0, 0)
        self._save_caption_btn = QPushButton("save caption correction")
        self._save_caption_btn.clicked.connect(self._save_caption_correction)
        crl.addWidget(self._save_caption_btn)
        rl.addWidget(caption_row)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)
        root.addWidget(splitter, 1)
        self._update_vision_status()

    def refresh(self):
        self._records = self.state.image_store.list_recent(limit=500)
        current = self._selected_id
        self._library.blockSignals(True)
        self._library.clear()
        selected_item = None
        for record in self._records:
            label = f"{record.created_at[:19]}  {record.width}x{record.height}  {record.kind}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, record.id)
            item.setToolTip(record.original_path)
            self._library.addItem(item)
            if record.id == current:
                selected_item = item
        self._library.blockSignals(False)
        if selected_item:
            self._library.setCurrentItem(selected_item)
        elif self._library.count():
            self._library.setCurrentRow(0)
        else:
            self._clear_details()

    def _on_selected(self, current, _previous):
        if not current:
            self._clear_details()
            return
        image_id = current.data(Qt.ItemDataRole.UserRole)
        self._selected_id = image_id
        self._render_record(self.state.image_store.get(image_id))

    def _render_record(self, record):
        pix = QPixmap(record.original_path)
        if not pix.isNull():
            scaled = pix.scaled(
                self._preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview.setPixmap(scaled)
        else:
            self._preview.setText("Could not load image preview.")

        self._meta.setText(
            "\n".join([
                f"ID: {record.id}",
                f"Source: {record.source}",
                f"Kind: {record.kind}",
                f"Size: {record.width}x{record.height}",
                f"OCR: {record.ocr.engine} · confidence {record.ocr.confidence:.2f}",
                f"Vision: {record.vision.engine} · {record.vision.model or 'no model'}",
                f"Detected code: {record.vision.detected_code}",
                f"Detected error: {record.vision.detected_error}",
                f"Path: {record.original_path}",
            ])
        )
        idx = self._kind_combo.findData(record.kind)
        self._kind_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._tags.setText(", ".join(record.tags))
        self._ocr.setPlainText(record.ocr.text or "(OCR pending or unavailable.)")
        self._caption.setPlainText(record.vision.caption or "")
        self._update_vision_status()

    def _clear_details(self):
        self._selected_id = ""
        self._preview.setText("No image selected.")
        self._preview.setPixmap(QPixmap())
        self._meta.setText("No images saved yet. Paste one into Workbench or import a file.")
        self._kind_combo.setCurrentIndex(0)
        self._tags.clear()
        self._ocr.clear()
        self._caption.clear()
        self._update_vision_status()

    def _selected_record(self):
        if not self._selected_id:
            return None
        return self.state.image_store.get(self._selected_id)

    def _import_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import image into Karl Vision",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;All files (*)",
        )
        if not path:
            return
        try:
            record = self.state.image_store.import_file(path, source="file")
        except Exception as exc:
            QMessageBox.critical(self, "Image Import Failed", str(exc))
            return
        self._selected_id = record.id
        self.refresh()
        self._run_analysis()

    def _open_file(self):
        record = self._selected_record()
        if record:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(record.original_path).resolve())))

    def _send_to_workbench(self):
        record = self._selected_record()
        if not record or not self.workbench_ref:
            return
        self.workbench_ref.attach_existing_image(record.id)
        QMessageBox.information(self, "Image Sent", "Image attached to the Workbench composer.")

    def _run_analysis(self):
        record = self._selected_record()
        if not record:
            return
        mode = self._mode_combo.currentData() or "ocr_vision"
        prompt = self._analysis_prompt.toPlainText().strip() or None
        self._meta.setText(self._meta.text() + f"\nAnalysis: running ({mode})")
        thread = ImageAnalysisThread(self.state.image_store, record.id, mode=mode, prompt=prompt)
        thread.progress.connect(self._on_analysis_progress)
        thread.ocr_done.connect(self._on_ocr_done)
        thread.vision_done.connect(self._on_vision_done)
        thread.done.connect(self._on_analysis_done)
        thread.error.connect(self._on_analysis_error)
        self._active_threads.add(thread)
        thread.finished.connect(lambda: self._active_threads.discard(thread))
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_analysis_progress(self, msg: str):
        if self._selected_id:
            self._meta.setText(self._meta.text() + f"\nAnalysis: {msg}")

    def _on_ocr_done(self, image_id: str, ocr):
        if image_id == self._selected_id:
            self._ocr.setPlainText(ocr.text or "(OCR unavailable or no text detected.)")

    def _on_vision_done(self, image_id: str, vision):
        if image_id == self._selected_id:
            self._caption.setPlainText(vision.caption or "")
            self._update_vision_status()

    def _on_analysis_done(self, image_id: str, _record):
        if image_id == self._selected_id:
            self._render_record(self.state.image_store.get(image_id))
        self.refresh()

    def _on_analysis_error(self, msg: str):
        QMessageBox.warning(self, "Image Analysis Failed", msg)
        self._update_vision_status()

    def _save_metadata(self):
        record = self._selected_record()
        if not record:
            return
        tags = [t.strip() for t in self._tags.text().split(",") if t.strip()]
        updated = self.state.image_store.update_metadata(
            record.id,
            kind=self._kind_combo.currentData() or "unknown",
            tags=tags,
        )
        self._render_record(updated)
        self.refresh()

    def _save_ocr_correction(self):
        record = self._selected_record()
        if not record:
            return
        updated = self.state.image_store.save_ocr_correction(record.id, self._ocr.toPlainText().strip())
        self._render_record(updated)
        self.refresh()

    def _save_caption_correction(self):
        record = self._selected_record()
        if not record:
            return
        updated = self.state.image_store.save_caption_correction(record.id, self._caption.toPlainText().strip())
        self._render_record(updated)
        self.refresh()

    def _update_vision_status(self):
        status = VisionModelLoader.status()
        backend = "ready" if status["backend_available"] else "blocked"
        active = status.get("active_name") or "none"
        loaded = "loaded" if status["loaded"] else "not loaded"
        lines = [f"Vision runtime: {backend} · {loaded} · active: {active}"]
        if status.get("backend_error"):
            lines.append(status["backend_error"])
        if status.get("last_error"):
            lines.append(status["last_error"])
        self._vision_status.setText("\n".join(lines))

        rows = installed_vision_models()
        installed = [
            row["name"]
            for row in rows
            if row.get("model_installed") and row.get("projector_installed")
        ]
        missing_count = len(rows) - len(installed)
        if installed:
            registry = "Installed vision models: " + ", ".join(installed)
        else:
            registry = "No complete local vision model/projector pair installed."
        if missing_count:
            registry += f"\nRegistry entries waiting for local files: {missing_count}"
        self._registry_label.setText(registry)
