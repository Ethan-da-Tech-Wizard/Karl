"""Floating, semi-transparent keyboard shortcuts reference overlay."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt, QEvent


_SHORTCUTS = [
    # (key display, description)
    ("Ctrl + Enter",  "Send message"),
    ("Esc",           "Cancel generation"),
    ("Ctrl + R",      "Reload active model"),
    ("Ctrl + S",      "Save current session"),
    ("Ctrl + N",      "New session"),
    ("Ctrl + V",      "Paste image from clipboard"),
    ("Ctrl + Shift+H","Toggle all HUD panels"),
    ("?",             "Toggle this shortcuts panel"),
]


def _kbd(text: str, accent: str, border: str, bg_raised: str, text_hi: str) -> QLabel:
    """Render a key name as a styled kbd badge."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        background-color: {bg_raised};
        border: 1px solid {border};
        border-radius: 3px;
        color: {accent};
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 8pt;
        font-weight: bold;
        padding: 2px 7px;
    """)
    return lbl


class ShortcutsOverlay(QWidget):
    """Semi-transparent floating panel listing Workbench keyboard shortcuts.

    Parent must be the widget over which the overlay should be positioned.
    Call show_overlay() / hide() to toggle. The overlay repositions itself
    whenever its parent is resized.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("shortcuts-overlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.hide()

        self._build(parent)
        self._reposition()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self, parent: QWidget):
        from app.ui.themes import get_theme_colors
        try:
            colors = get_theme_colors(getattr(parent, "state", None))
        except Exception:
            colors = {}

        bg_raised = colors.get("bg_raised", "#1C1C2A")
        border    = colors.get("border",    "#252535")
        border_hi = colors.get("border_hi", "#383850")
        accent    = colors.get("accent",    "#00C2FF")
        text_hi   = colors.get("text_hi",   "#E4E4F0")
        text_lo   = colors.get("text_lo",   "#505068")

        self.setStyleSheet(f"""
            ShortcutsOverlay {{
                background-color: rgba(13, 13, 22, 220);
                border: 1px solid {border_hi};
                border-radius: 8px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        # ── header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet(
            f"color: {accent}; font-size: 10pt; font-weight: bold; "
            f"letter-spacing: 1px; font-family: 'JetBrains Mono', monospace; "
            f"background: transparent;"
        )
        header_row.addWidget(title)
        header_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {border};
                border-radius: 11px;
                color: {text_lo};
                font-size: 9pt;
            }}
            QPushButton:hover {{
                color: {text_hi};
                border-color: {accent};
            }}
        """)
        close_btn.clicked.connect(self.hide)
        header_row.addWidget(close_btn)
        outer.addLayout(header_row)

        # ── divider ───────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {border}; background: {border};")
        divider.setFixedHeight(1)
        outer.addWidget(divider)

        # ── shortcut rows ─────────────────────────────────────────────────────
        for key_text, description in _SHORTCUTS:
            row = QHBoxLayout()
            row.setSpacing(12)
            row.setContentsMargins(0, 0, 0, 0)

            kbd_parts = key_text.split(" + ")
            for i, part in enumerate(kbd_parts):
                row.addWidget(_kbd(part.strip(), accent, border, bg_raised, text_hi))
                if i < len(kbd_parts) - 1:
                    plus = QLabel("+")
                    plus.setStyleSheet(
                        f"color: {text_lo}; font-size: 8pt; background: transparent;"
                    )
                    row.addWidget(plus)

            row.addStretch()

            desc_lbl = QLabel(description)
            desc_lbl.setStyleSheet(
                f"color: {text_hi}; font-size: 8.5pt; background: transparent;"
            )
            row.addWidget(desc_lbl)

            outer.addLayout(row)

    # ── positioning ───────────────────────────────────────────────────────────

    def _reposition(self):
        parent = self.parent()
        if parent is None:
            return
        w = 340
        h = self.sizeHint().height() or 320
        pw = parent.width()
        # Anchor: top-right corner with some margin
        x = max(0, pw - w - 12)
        y = 48
        self.setGeometry(x, y, w, max(h, 300))

    def show_overlay(self):
        self._reposition()
        self.raise_()
        self.show()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_overlay()

    # ── respond to parent resize ──────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._reposition()
        return super().eventFilter(obj, event)
