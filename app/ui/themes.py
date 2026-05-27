"""
Karl -- Theme System
30 hand-crafted color palettes.
Each theme is a dict of 13 named color tokens.
generate_stylesheet(theme_name) returns a complete QSS string.
"""

# ---------------------------------------------------------------------------
# Palette definitions
# ---------------------------------------------------------------------------

THEMES: dict[str, dict[str, str]] = {
    "Midnight": {
        "bg_deep":      "#0B0F19",
        "bg_base":      "#111827",
        "bg_surface":   "#1F2937",
        "bg_input":     "#1F2937",
        "border":       "#374151",
        "border_focus": "#3B82F6",
        "text_primary": "#F9FAFB",
        "text_secondary":"#9CA3AF",
        "text_muted":   "#6B7280",
        "accent":       "#3B82F6",
        "accent_hover": "#60A5FA",
        "thought_bg":   "#0B0F19",
        "thought_text": "#60A5FA",
    },
    "Carbon": {
        "bg_deep":      "#121212",
        "bg_base":      "#1A1A1A",
        "bg_surface":   "#262626",
        "bg_input":     "#262626",
        "border":       "#404040",
        "border_focus": "#A3A3A3",
        "text_primary": "#F5F5F5",
        "text_secondary":"#A3A3A3",
        "text_muted":   "#737373",
        "accent":       "#E5E5E5",
        "accent_hover": "#A3A3A3",
        "thought_bg":   "#121212",
        "thought_text": "#A3A3A3",
    },
    "Obsidian": {
        "bg_deep":      "#0E0B16",
        "bg_base":      "#161224",
        "bg_surface":   "#251D3A",
        "bg_input":     "#251D3A",
        "border":       "#3E2F5D",
        "border_focus": "#A855F7",
        "text_primary": "#F3E8FF",
        "text_secondary":"#C084FC",
        "text_muted":   "#7E22CE",
        "accent":       "#A855F7",
        "accent_hover": "#C084FC",
        "thought_bg":   "#0E0B16",
        "thought_text": "#C084FC",
    },
    "Deep Ocean": {
        "bg_deep":      "#051329",
        "bg_base":      "#0A1E3F",
        "bg_surface":   "#102A54",
        "bg_input":     "#102A54",
        "border":       "#1E40AF",
        "border_focus": "#38BDF8",
        "text_primary": "#E0F2FE",
        "text_secondary":"#7DD3FC",
        "text_muted":   "#0284C7",
        "accent":       "#38BDF8",
        "accent_hover": "#7DD3FC",
        "thought_bg":   "#051329",
        "thought_text": "#7DD3FC",
    },
    "Forest": {
        "bg_deep":      "#061F12",
        "bg_base":      "#0B2E1C",
        "bg_surface":   "#14472B",
        "bg_input":     "#14472B",
        "border":       "#15803D",
        "border_focus": "#4ADE80",
        "text_primary": "#DCFCE7",
        "text_secondary":"#86EFAC",
        "text_muted":   "#166534",
        "accent":       "#4ADE80",
        "accent_hover": "#86EFAC",
        "thought_bg":   "#061F12",
        "thought_text": "#86EFAC",
    },
    "Crimson": {
        "bg_deep":      "#24070A",
        "bg_base":      "#360B10",
        "bg_surface":   "#4D1219",
        "bg_input":     "#4D1219",
        "border":       "#991B1B",
        "border_focus": "#F87171",
        "text_primary": "#FEE2E2",
        "text_secondary":"#FCA5A5",
        "text_muted":   "#B91C1C",
        "accent":       "#F87171",
        "accent_hover": "#FCA5A5",
        "thought_bg":   "#24070A",
        "thought_text": "#FCA5A5",
    },
    "Amber": {
        "bg_deep":      "#1E1002",
        "bg_base":      "#2E1905",
        "bg_surface":   "#45270A",
        "bg_input":     "#45270A",
        "border":       "#B45309",
        "border_focus": "#FBBF24",
        "text_primary": "#FEF3C7",
        "text_secondary":"#FDE68A",
        "text_muted":   "#92400E",
        "accent":       "#FBBF24",
        "accent_hover": "#FDE68A",
        "thought_bg":   "#1E1002",
        "thought_text": "#FDE68A",
    },
    "Violet": {
        "bg_deep":      "#F3E8FF",
        "bg_base":      "#FAF5FF",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#F3E8FF",
        "border":       "#D8B4FE",
        "border_focus": "#7C3AED",
        "text_primary": "#581C87",
        "text_secondary":"#7E22CE",
        "text_muted":   "#A855F7",
        "accent":       "#7C3AED",
        "accent_hover": "#6D28D9",
        "thought_bg":   "#F3E8FF",
        "thought_text": "#6D28D9",
    },
    "Teal": {
        "bg_deep":      "#041D20",
        "bg_base":      "#072B30",
        "bg_surface":   "#0C3E45",
        "bg_input":     "#0C3E45",
        "border":       "#0D9488",
        "border_focus": "#2DD4BF",
        "text_primary": "#CCFBF1",
        "text_secondary":"#99F6E4",
        "text_muted":   "#115E59",
        "accent":       "#2DD4BF",
        "accent_hover": "#99F6E4",
        "thought_bg":   "#041D20",
        "thought_text": "#2DD4BF",
    },
    "Rose": {
        "bg_deep":      "#FFE4E6",
        "bg_base":      "#FFF1F2",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#FFE4E6",
        "border":       "#FDA4AF",
        "border_focus": "#E11D48",
        "text_primary": "#881337",
        "text_secondary":"#9F1239",
        "text_muted":   "#FB7185",
        "accent":       "#E11D48",
        "accent_hover": "#BE123C",
        "thought_bg":   "#FFE4E6",
        "thought_text": "#BE123C",
    },
    "Slate": {
        "bg_deep":      "#E2E8F0",
        "bg_base":      "#F8FAFC",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#F1F5F9",
        "border":       "#CBD5E1",
        "border_focus": "#475569",
        "text_primary": "#0F172A",
        "text_secondary":"#334155",
        "text_muted":   "#64748B",
        "accent":       "#475569",
        "accent_hover": "#334155",
        "thought_bg":   "#E2E8F0",
        "thought_text": "#334155",
    },
    "Zinc": {
        "bg_deep":      "#18181B",
        "bg_base":      "#27272A",
        "bg_surface":   "#3F3F46",
        "bg_input":     "#3F3F46",
        "border":       "#52525B",
        "border_focus": "#D4D4D8",
        "text_primary": "#F4F4F5",
        "text_secondary":"#D4D4D8",
        "text_muted":   "#A1A1AA",
        "accent":       "#E4E4E7",
        "accent_hover": "#A1A1AA",
        "thought_bg":   "#18181B",
        "thought_text": "#E4E4E7",
    },
    "Copper": {
        "bg_deep":      "#1C0E07",
        "bg_base":      "#2B170B",
        "bg_surface":   "#3D2211",
        "bg_input":     "#3D2211",
        "border":       "#C2410C",
        "border_focus": "#F97316",
        "text_primary": "#FFEDD5",
        "text_secondary":"#FED7AA",
        "text_muted":   "#9A3412",
        "accent":       "#F97316",
        "accent_hover": "#FED7AA",
        "thought_bg":   "#1C0E07",
        "thought_text": "#F97316",
    },
    "Arctic": {
        "bg_deep":      "#E0F2FE",
        "bg_base":      "#F0F9FF",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#E0F2FE",
        "border":       "#BAE6FD",
        "border_focus": "#0284C7",
        "text_primary": "#0C4A6E",
        "text_secondary":"#0369A1",
        "text_muted":   "#38BDF8",
        "accent":       "#0284C7",
        "accent_hover": "#0369A1",
        "thought_bg":   "#E0F2FE",
        "thought_text": "#0369A1",
    },
    "Ember": {
        "bg_deep":      "#200802",
        "bg_base":      "#320D04",
        "bg_surface":   "#481406",
        "bg_input":     "#481406",
        "border":       "#EA580C",
        "border_focus": "#F97316",
        "text_primary": "#FFEDD5",
        "text_secondary":"#F97316",
        "text_muted":   "#C2410C",
        "accent":       "#EA580C",
        "accent_hover": "#F97316",
        "thought_bg":   "#200802",
        "thought_text": "#F97316",
    },
    "Sage": {
        "bg_deep":      "#DCFCE7",
        "bg_base":      "#F0FDF4",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#DCFCE7",
        "border":       "#BBF7D0",
        "border_focus": "#16A34A",
        "text_primary": "#14532D",
        "text_secondary":"#166534",
        "text_muted":   "#4ADE80",
        "accent":       "#16A34A",
        "accent_hover": "#15803D",
        "thought_bg":   "#DCFCE7",
        "thought_text": "#15803D",
    },
    "Lavender": {
        "bg_deep":      "#E0E7FF",
        "bg_base":      "#EEF2FF",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#E0E7FF",
        "border":       "#C7D2FE",
        "border_focus": "#4F46E5",
        "text_primary": "#312E81",
        "text_secondary":"#3730A3",
        "text_muted":   "#6366F1",
        "accent":       "#4F46E5",
        "accent_hover": "#4338CA",
        "thought_bg":   "#E0E7FF",
        "thought_text": "#4338CA",
    },
    "Cobalt": {
        "bg_deep":      "#030D2A",
        "bg_base":      "#061642",
        "bg_surface":   "#0B2361",
        "bg_input":     "#0B2361",
        "border":       "#1E40AF",
        "border_focus": "#60A5FA",
        "text_primary": "#EFF6FF",
        "text_secondary":"#93C5FD",
        "text_muted":   "#3B82F6",
        "accent":       "#60A5FA",
        "accent_hover": "#93C5FD",
        "thought_bg":   "#030D2A",
        "thought_text": "#60A5FA",
    },
    "Onyx": {
        "bg_deep":      "#000000",
        "bg_base":      "#080808",
        "bg_surface":   "#121212",
        "bg_input":     "#1A1A1A",
        "border":       "#262626",
        "border_focus": "#FFFFFF",
        "text_primary": "#FFFFFF",
        "text_secondary":"#CCCCCC",
        "text_muted":   "#666666",
        "accent":       "#FFFFFF",
        "accent_hover": "#CCCCCC",
        "thought_bg":   "#000000",
        "thought_text": "#FFFFFF",
    },
    "Steel": {
        "bg_deep":      "#ECEFF1",
        "bg_base":      "#F4F6F7",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#ECEFF1",
        "border":       "#CFD8DC",
        "border_focus": "#546E7A",
        "text_primary": "#263238",
        "text_secondary":"#37474F",
        "text_muted":   "#78909C",
        "accent":       "#546E7A",
        "accent_hover": "#37474F",
        "thought_bg":   "#ECEFF1",
        "thought_text": "#37474F",
    },
    "Mocha": {
        "bg_deep":      "#EDE0D4",
        "bg_base":      "#F5EBE0",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#EDE0D4",
        "border":       "#D6CCC2",
        "border_focus": "#7F5539",
        "text_primary": "#463F3A",
        "text_secondary":"#7F5539",
        "text_muted":   "#9C6644",
        "accent":       "#7F5539",
        "accent_hover": "#9C6644",
        "thought_bg":   "#EDE0D4",
        "thought_text": "#9C6644",
    },
    "Jade": {
        "bg_deep":      "#021A0F",
        "bg_base":      "#042616",
        "bg_surface":   "#0B3A23",
        "bg_input":     "#0B3A23",
        "border":       "#10B981",
        "border_focus": "#34D399",
        "text_primary": "#D1FAE5",
        "text_secondary":"#A7F3D0",
        "text_muted":   "#065F46",
        "accent":       "#34D399",
        "accent_hover": "#A7F3D0",
        "thought_bg":   "#021A0F",
        "thought_text": "#34D399",
    },
    "Graphite": {
        "bg_deep":      "#181C1F",
        "bg_base":      "#22272B",
        "bg_surface":   "#2F353B",
        "bg_input":     "#2F353B",
        "border":       "#454F59",
        "border_focus": "#9CA3AF",
        "text_primary": "#E5E7EB",
        "text_secondary":"#9CA3AF",
        "text_muted":   "#6B7280",
        "accent":       "#9CA3AF",
        "accent_hover": "#E5E7EB",
        "thought_bg":   "#181C1F",
        "thought_text": "#E5E7EB",
    },
    "Dusk": {
        "bg_deep":      "#130F26",
        "bg_base":      "#1C1635",
        "bg_surface":   "#2B224E",
        "bg_input":     "#2B224E",
        "border":       "#4F3F84",
        "border_focus": "#818CF8",
        "text_primary": "#E0E7FF",
        "text_secondary":"#A5B4FC",
        "text_muted":   "#4338CA",
        "accent":       "#818CF8",
        "accent_hover": "#A5B4FC",
        "thought_bg":   "#130F26",
        "thought_text": "#818CF8",
    },
    "Marine": {
        "bg_deep":      "#E0F7FA",
        "bg_base":      "#E0F2F1",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#E0F7FA",
        "border":       "#B2DFDB",
        "border_focus": "#00695C",
        "text_primary": "#004D40",
        "text_secondary":"#00695C",
        "text_muted":   "#26A69A",
        "accent":       "#00695C",
        "accent_hover": "#00897B",
        "thought_bg":   "#E0F7FA",
        "thought_text": "#00695C",
    },
    "Saffron": {
        "bg_deep":      "#FFF3E0",
        "bg_base":      "#FFF8E1",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#FFF3E0",
        "border":       "#FFE082",
        "border_focus": "#E65100",
        "text_primary": "#5D4037",
        "text_secondary":"#E65100",
        "text_muted":   "#FFB74D",
        "accent":       "#E65100",
        "accent_hover": "#F57C00",
        "thought_bg":   "#FFF3E0",
        "thought_text": "#E65100",
    },
    "Matrix": {
        "bg_deep":      "#000000",
        "bg_base":      "#000A02",
        "bg_surface":   "#001504",
        "bg_input":     "#001A06",
        "border":       "#004D0F",
        "border_focus": "#00FF41",
        "text_primary": "#00FF41",
        "text_secondary":"#00D432",
        "text_muted":   "#004D0F",
        "accent":       "#00FF41",
        "accent_hover": "#00D432",
        "thought_bg":   "#000000",
        "thought_text": "#00FF41",
    },
    "Sand": {
        "bg_deep":      "#F5EBE0",
        "bg_base":      "#FDF8F5",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#F5EBE0",
        "border":       "#E3D5CA",
        "border_focus": "#D4A373",
        "text_primary": "#3E2723",
        "text_secondary":"#D4A373",
        "text_muted":   "#A98467",
        "accent":       "#D4A373",
        "accent_hover": "#A98467",
        "thought_bg":   "#F5EBE0",
        "thought_text": "#A98467",
    },
    "Ash": {
        "bg_deep":      "#F1F3F5",
        "bg_base":      "#F8F9FA",
        "bg_surface":   "#FFFFFF",
        "bg_input":     "#F1F3F5",
        "border":       "#E9ECEF",
        "border_focus": "#495057",
        "text_primary": "#212529",
        "text_secondary":"#495057",
        "text_muted":   "#ADB5BD",
        "accent":       "#495057",
        "accent_hover": "#343A40",
        "thought_bg":   "#F1F3F5",
        "thought_text": "#343A40",
    },
    "Neon": {
        "bg_deep":      "#0C0314",
        "bg_base":      "#180629",
        "bg_surface":   "#2A0B47",
        "bg_input":     "#2A0B47",
        "border":       "#BD08FF",
        "border_focus": "#00F5FF",
        "text_primary": "#00F5FF",
        "text_secondary":"#FF007F",
        "text_muted":   "#BD08FF",
        "accent":       "#FF007F",
        "accent_hover": "#00F5FF",
        "thought_bg":   "#0C0314",
        "thought_text": "#00F5FF",
    },
}


def generate_stylesheet(theme_name: str) -> str:
    """Returns a complete QSS string for the given theme."""
    t = THEMES.get(theme_name, THEMES["Midnight"])
    bg_deep      = t["bg_deep"]
    bg_base      = t["bg_base"]
    bg_surface   = t["bg_surface"]
    bg_input     = t["bg_input"]
    border       = t["border"]
    border_focus = t["border_focus"]
    text_primary = t["text_primary"]
    text_secondary = t["text_secondary"]
    text_muted   = t["text_muted"]
    accent       = t["accent"]
    accent_hover = t["accent_hover"]
    thought_bg   = t["thought_bg"]
    thought_text = t["thought_text"]

    return f"""
/* Karl -- Dynamic Theme: {theme_name} */

QMainWindow, QWidget {{
    background-color: {bg_base};
    color: {text_primary};
    font-family: 'Segoe UI', Inter, Arial, sans-serif;
    font-size: 11pt;
}}

QSplitter::handle {{
    background-color: {border};
}}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}
QSplitter::handle:hover {{ background-color: {border_focus}; }}

QLabel {{
    color: {text_secondary};
    background: transparent;
}}

QLineEdit, QTextEdit {{
    background-color: {bg_input};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 14px;
    color: {text_primary};
    font-size: 11pt;
    selection-background-color: {accent};
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid {border_focus};
    background-color: {bg_surface};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {bg_deep};
    color: {text_muted};
    border-color: {bg_surface};
}}

QTextBrowser {{
    background-color: {bg_deep};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 24px 28px;
    color: {text_primary};
    font-size: 11.5pt;
}}

QTextBrowser#thought_display {{
    background-color: {thought_bg};
    color: {thought_text};
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
    font-size: 10pt;
    border: 1px solid {border};
    border-radius: 12px;
    padding: 18px 22px;
}}

QPushButton {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 20px;
    color: {text_primary};
    font-weight: 600;
    font-size: 10.5pt;
    min-height: 36px;
    min-width: 80px;
}}
QPushButton:hover {{
    background-color: {bg_input};
    border-color: {text_muted};
    color: {text_primary};
}}
QPushButton:pressed {{
    background-color: {bg_deep};
    border-color: {border_focus};
}}
QPushButton:disabled {{
    background-color: {bg_deep};
    border-color: {bg_surface};
    color: {text_muted};
}}

QPushButton#btn_generate {{
    background-color: {accent};
    border-color: {accent_hover};
    color: {bg_deep};
    font-weight: 900;
    font-size: 15pt;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 18px;
    padding: 0;
}}
QPushButton#btn_generate:hover {{
    background-color: {accent_hover};
    border-color: {accent};
}}
QPushButton#btn_generate:disabled {{
    background-color: {border};
    border-color: {border};
    color: {text_muted};
}}

QPushButton#btn_stop {{
    background-color: transparent;
    border: 1px solid #7F1D1D;
    border-radius: 18px;
    color: #FCA5A5;
    font-weight: bold;
    font-size: 11pt;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0;
}}
QPushButton#btn_stop:hover {{
    background-color: #7F1D1D;
    color: #FFFFFF;
}}
QPushButton#btn_stop:disabled {{
    background-color: transparent;
    border-color: {border};
    color: {text_muted};
}}

QPushButton#btn_agentic {{
    background-color: {bg_deep};
    border-color: {border};
    color: {accent};
    font-weight: 700;
}}
QPushButton#btn_agentic:hover {{
    background-color: {bg_surface};
    border-color: {accent};
    color: {text_primary};
}}

QPushButton#btn_force_thought {{
    background-color: {bg_deep};
    border-color: {border};
    color: {text_secondary};
}}
QPushButton#btn_force_thought:hover {{
    background-color: {bg_surface};
    border-color: {text_secondary};
    color: {text_primary};
}}

QPushButton#btn_accept {{
    background-color: {bg_deep};
    border-color: #14532D;
    color: #86EFAC;
}}
QPushButton#btn_accept:hover {{
    background-color: #14532D;
    color: #FFFFFF;
}}

QPushButton#btn_correct {{
    background-color: {bg_deep};
    border-color: #78350F;
    color: #FCD34D;
}}
QPushButton#btn_correct:hover {{
    background-color: #78350F;
    color: #FFFFFF;
}}

QPushButton#btn_nav {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    padding: 10px 24px;
    color: {text_muted};
    font-size: 10.5pt;
    font-weight: 600;
    min-height: 40px;
    letter-spacing: 0.04em;
}}
QPushButton#btn_nav:hover {{
    color: {text_secondary};
    background-color: transparent;
}}
QPushButton#btn_nav[active="true"] {{
    color: {text_primary};
    border-bottom: 2px solid {accent};
}}

QPushButton#btn_think_toggle {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 6px;
    color: {text_secondary};
    font-size: 8pt;
    min-height: 22px;
    min-width: 52px;
    padding: 2px 8px;
}}
QPushButton#btn_think_toggle:hover {{
    color: {text_primary};
    border-color: {border_focus};
}}

QCheckBox {{
    color: {text_secondary};
    spacing: 8px;
    font-size: 10.5pt;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {text_muted};
    background-color: {bg_input};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {border_focus};
}}
QCheckBox::indicator:hover {{
    border-color: {text_secondary};
}}
QCheckBox:hover {{
    color: {text_primary};
}}

QDoubleSpinBox, QSpinBox {{
    background-color: {bg_input};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 12px;
    color: {text_primary};
    font-size: 11pt;
    min-width: 80px;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {border_focus};
}}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    background-color: {bg_surface};
    border: none;
    width: 20px;
}}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background-color: {bg_input};
}}

QComboBox {{
    background-color: {bg_input};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 14px;
    color: {text_primary};
    font-size: 11pt;
    min-width: 130px;
}}
QComboBox:hover {{
    border-color: {text_muted};
}}
QComboBox:focus {{
    border-color: {border_focus};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox QAbstractItemView {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 8px;
    selection-background-color: {accent};
    color: {text_primary};
    padding: 4px;
    font-size: 11pt;
}}

QListWidget {{
    background-color: {bg_deep};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 6px;
    color: {text_primary};
    font-size: 10.5pt;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 4px;
}}
QListWidget::item:hover {{
    background-color: {bg_surface};
    color: {text_primary};
}}
QListWidget::item:selected {{
    background-color: {bg_surface};
    color: {accent};
    font-weight: bold;
}}

QScrollBar:vertical {{
    background-color: {bg_deep};
    width: 7px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {border};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {text_muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background-color: {bg_deep};
    height: 7px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {border};
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {text_muted};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{
    background-color: {bg_deep};
    color: {text_primary};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 9.5pt;
}}

QStatusBar {{
    background-color: {bg_deep};
    color: {text_muted};
    border-top: 1px solid {border};
    font-size: 9pt;
    padding: 2px 10px;
}}

QMessageBox, QDialog {{
    background-color: {bg_surface};
}}
QDialogButtonBox QPushButton {{
    min-width: 90px;
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    border: none;
    border-top: 1px solid {border};
    max-height: 1px;
    color: {border};
}}

QScrollArea {{
    background-color: {bg_base};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {bg_base};
}}

/* Dynamic Theme-Aware Containers */
QWidget#navbar {{
    background-color: {bg_deep};
    border-bottom: 1px solid {border};
}}

QWidget#sidebar {{
    background-color: {bg_deep};
    border-right: 1px solid {border};
}}

QWidget#reasoning_panel {{
    background-color: {thought_bg};
    border-bottom: 1px solid {border};
}}

QWidget#config_page {{
    background-color: {bg_base};
}}

QFrame#config_card {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
}}

/* Clean developer-oriented console label classes */
QLabel#lbl_section {{
    color: {text_secondary};
}}
QLabel#lbl_hint {{
    color: {text_muted};
}}
QLabel#config_header {{
    color: {accent};
}}
QLabel#control_label {{
    color: {text_primary};
}}
QLabel#status_label {{
    color: {text_secondary};
}}
QLabel#upgrade_label {{
    color: {accent};
}}

/* Pill-shaped chat input bar & container styles */
QWidget#input_container {{
    background-color: {bg_input};
    border: 1px solid {border};
    border-radius: 27px; /* Pill-shaped container for 54px height */
}}
QWidget#input_container:focus-within {{
    border: 1px solid {border_focus};
    background-color: {bg_surface};
}}
QLineEdit#user_input {{
    background: transparent;
    border: none;
    color: {text_primary};
}}
QLineEdit#user_input:focus {{
    background: transparent;
    border: none;
}}
"""

