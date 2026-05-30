"""
Karl design system — one dark theme, tunable accent.
Everything else in the UI derives from this palette.
"""

ACCENT_DEFAULT = "#00C2FF"

PALETTE = {
    "bg_deep":     "#07070D",
    "bg_base":     "#0D0D16",
    "bg_surface":  "#14141F",
    "bg_raised":   "#1C1C2A",
    "bg_input":    "#111119",
    "border":      "#252535",
    "border_hi":   "#383850",
    "accent":      ACCENT_DEFAULT,
    "accent_dark": "#008CB8",
    "text_hi":     "#E4E4F0",
    "text_mid":    "#9090A8",
    "text_lo":     "#505068",
    "think_bg":    "#0A0A14",
    "think_text":  "#505080",
    "green":       "#2DD4A0",
    "red":         "#F05050",
    "yellow":      "#F0B030",
    "sidebar_bg":  "#08080F",
    "sidebar_sel": "#161625",
}

MONO = (
    "'JetBrains Mono', 'Fira Code', 'Cascadia Code', "
    "'Consolas', 'Courier New', monospace"
)

_SHEET = """\
/* ── Reset ───────────────────────────────────────────────── */
* {{ outline: none; }}

QMainWindow, QDialog {{
    background: {bg_deep};
}}

QWidget {{
    background: transparent;
    color: {text_hi};
    font-family: {mono};
    font-size: 10pt;
    border: none;
}}

/* ── Sidebar ──────────────────────────────────────────────── */
#sidebar {{
    background: {sidebar_bg};
    border-right: 1px solid {border};
}}

#sidebar-logo {{
    color: {accent};
    font-size: 15pt;
    font-weight: bold;
    background: transparent;
    padding: 0;
}}

#sidebar-btn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {text_lo};
    padding: 6px 2px;
    font-size: 8pt;
    text-align: center;
    width: 52px;
}}

#sidebar-btn:hover {{
    background: {bg_raised};
    color: {text_mid};
}}

#sidebar-btn[active="true"] {{
    background: {sidebar_sel};
    color: {accent};
    border-left: 2px solid {accent};
    border-radius: 0 6px 6px 0;
}}

/* ── Workspace Shell ──────────────────────────────────────── */
#workspace-root {{
    background: {bg_base};
}}

#panel {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 4px;
}}

#panel-header {{
    background: {bg_raised};
    border-bottom: 1px solid {border};
    border-radius: 4px 4px 0 0;
    padding: 5px 12px;
    color: {text_lo};
    font-size: 8pt;
    letter-spacing: 2px;
}}

/* ── Text Displays ────────────────────────────────────────── */
QTextBrowser {{
    background: transparent;
    border: none;
    color: {text_hi};
    font-family: {mono};
    font-size: 10pt;
    selection-background-color: {accent_dark};
    padding: 6px;
}}

#reasoning-view {{
    background: {think_bg};
    color: {think_text};
    font-size: 9pt;
    border-right: 1px solid {border};
}}

/* ── Inputs ───────────────────────────────────────────────── */
QTextEdit {{
    background: {bg_input};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    font-family: {mono};
    font-size: 10pt;
    padding: 8px 10px;
    selection-background-color: {accent_dark};
}}

QTextEdit:focus {{
    border-color: {accent};
}}

QLineEdit {{
    background: {bg_input};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    font-family: {mono};
    font-size: 10pt;
    padding: 6px 10px;
    selection-background-color: {accent_dark};
}}

QLineEdit:focus {{
    border-color: {accent};
}}

QLineEdit:read-only {{
    color: {text_mid};
    background: {bg_surface};
}}

/* ── Buttons ──────────────────────────────────────────────── */
QPushButton {{
    background: {bg_raised};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_mid};
    padding: 6px 14px;
    font-family: {mono};
    font-size: 10pt;
}}

QPushButton:hover {{
    background: {border};
    color: {text_hi};
    border-color: {border_hi};
}}

QPushButton:pressed {{
    background: {bg_surface};
}}

QPushButton:disabled {{
    color: {text_lo};
    border-color: {border};
    background: {bg_surface};
}}

QPushButton#btn-primary {{
    background: {accent};
    border: none;
    color: #050510;
    font-weight: bold;
    padding: 6px 20px;
}}

QPushButton#btn-primary:hover {{
    background: {accent_dark};
    color: #050510;
}}

QPushButton#btn-primary:disabled {{
    background: {border};
    color: {text_lo};
}}

QPushButton#btn-danger {{
    background: transparent;
    border: 1px solid {red};
    color: {red};
}}

QPushButton#btn-danger:hover {{
    background: {red};
    color: #ffffff;
}}

QPushButton#btn-ghost {{
    background: transparent;
    border: none;
    color: {text_lo};
    padding: 4px 8px;
    font-size: 9pt;
}}

QPushButton#btn-ghost:hover {{
    color: {text_mid};
    background: transparent;
}}

QPushButton#btn-icon {{
    background: transparent;
    border: none;
    color: {text_lo};
    padding: 2px;
    font-size: 11pt;
}}

QPushButton#btn-icon:hover {{
    color: {text_mid};
}}

/* ── ComboBox ─────────────────────────────────────────────── */
QComboBox {{
    background: {bg_input};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    padding: 5px 10px;
    font-family: {mono};
    font-size: 10pt;
}}

QComboBox:hover {{
    border-color: {border_hi};
}}

QComboBox:focus {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
    padding-right: 4px;
}}

QComboBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text_lo};
}}

QComboBox QAbstractItemView {{
    background: {bg_raised};
    border: 1px solid {border_hi};
    color: {text_hi};
    selection-background-color: {accent_dark};
    outline: none;
    padding: 2px;
}}

/* ── Sliders ──────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 2px;
    background: {border};
    border-radius: 1px;
}}

QSlider::handle:horizontal {{
    background: {accent};
    border: none;
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}

QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 1px;
}}

/* ── SpinBox ──────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background: {bg_input};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    padding: 4px 8px;
    font-family: {mono};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {accent};
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {bg_raised};
    border: none;
    width: 18px;
}}

/* ── ListWidget ───────────────────────────────────────────── */
QListWidget {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    font-family: {mono};
    outline: none;
}}

QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {border};
}}

QListWidget::item:hover {{
    background: {bg_raised};
}}

QListWidget::item:selected {{
    background: {sidebar_sel};
    color: {accent};
}}

/* ── TreeWidget ───────────────────────────────────────────── */
QTreeWidget {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    font-family: {mono};
    outline: none;
}}

QTreeWidget::item {{
    padding: 4px 6px;
}}

QTreeWidget::item:hover {{
    background: {bg_raised};
}}

QTreeWidget::item:selected {{
    background: {sidebar_sel};
    color: {accent};
}}

QTreeWidget::branch {{
    background: transparent;
}}

QHeaderView::section {{
    background: {bg_raised};
    color: {text_lo};
    border: none;
    border-bottom: 1px solid {border};
    padding: 4px 8px;
    font-size: 8pt;
    letter-spacing: 1px;
    font-family: {mono};
}}

/* ── TableWidget ──────────────────────────────────────────── */
QTableWidget {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 4px;
    color: {text_hi};
    gridline-color: {border};
    font-family: {mono};
    outline: none;
}}

QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background: {sidebar_sel};
    color: {accent};
}}

/* ── Scroll Bars ──────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {border_hi};
    border-radius: 2px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: {text_lo};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {border_hi};
    border-radius: 2px;
    min-width: 20px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle            {{ background: {border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}

/* ── Status Bar ───────────────────────────────────────────── */
#status-bar {{
    background: {sidebar_bg};
    border-top: 1px solid {border};
}}

/* ── Labels ───────────────────────────────────────────────── */
QLabel {{
    color: {text_hi};
    background: transparent;
    font-family: {mono};
}}

QLabel#lbl-muted  {{ color: {text_lo}; font-size: 9pt; }}
QLabel#lbl-mid    {{ color: {text_mid}; }}
QLabel#lbl-accent {{ color: {accent}; }}
QLabel#lbl-green  {{ color: {green}; }}
QLabel#lbl-red    {{ color: {red}; }}

QLabel#section-header {{
    color: {text_lo};
    font-size: 8pt;
    letter-spacing: 2px;
    padding: 8px 0 4px 0;
}}

/* ── Separators ───────────────────────────────────────────── */
QFrame[frameShape="4"] {{ color: {border}; max-height: 1px; background: {border}; }}
QFrame[frameShape="5"] {{ color: {border}; max-width: 1px;  background: {border}; }}

/* ── Tabs ─────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 4px;
    background: {bg_surface};
}}

QTabBar::tab {{
    background: {bg_raised};
    border: 1px solid {border};
    border-bottom: none;
    color: {text_lo};
    padding: 6px 16px;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-family: {mono};
    font-size: 9pt;
}}

QTabBar::tab:selected {{
    background: {bg_surface};
    color: {text_hi};
    border-color: {border_hi};
}}

QTabBar::tab:hover:!selected {{
    color: {text_mid};
}}

/* ── Progress ─────────────────────────────────────────────── */
QProgressBar {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 3px;
    text-align: center;
    color: {text_mid};
    font-size: 8pt;
    font-family: {mono};
    max-height: 10px;
}}

QProgressBar::chunk {{
    background: {accent};
    border-radius: 3px;
}}

/* ── CheckBox ─────────────────────────────────────────────── */
QCheckBox {{
    color: {text_hi};
    spacing: 8px;
    font-family: {mono};
}}

QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    border: 1px solid {border_hi};
    border-radius: 3px;
    background: {bg_input};
}}

QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {border};
    border-radius: 4px;
    margin-top: 14px;
    padding-top: 8px;
    color: {text_lo};
    font-size: 8pt;
    letter-spacing: 1px;
    font-family: {mono};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    background: {bg_base};
}}

/* ── ToolTip ──────────────────────────────────────────────── */
QToolTip {{
    background: {bg_raised};
    border: 1px solid {border_hi};
    color: {text_hi};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 9pt;
    font-family: {mono};
}}
"""


def stylesheet(accent: str = ACCENT_DEFAULT) -> str:
    p = dict(PALETTE)
    p["accent"] = accent
    p["mono"] = MONO
    return _SHEET.format(**p)
