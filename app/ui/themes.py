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
        "bg_deep":      "#07070A",
        "bg_base":      "#0D0D0F",
        "bg_surface":   "#141416",
        "bg_input":     "#1A1A1D",
        "border":       "#252528",
        "border_focus": "#3B82F6",
        "text_primary": "#DDDDE0",
        "text_secondary":"#71717A",
        "text_muted":   "#3F3F46",
        "accent":       "#3B82F6",
        "accent_hover": "#2563EB",
        "thought_bg":   "#080C18",
        "thought_text": "#2D4A8A",
    },
    "Carbon": {
        "bg_deep":      "#0A0A0A",
        "bg_base":      "#111111",
        "bg_surface":   "#181818",
        "bg_input":     "#1E1E1E",
        "border":       "#2A2A2A",
        "border_focus": "#60A5FA",
        "text_primary": "#E8E8E8",
        "text_secondary":"#737373",
        "text_muted":   "#404040",
        "accent":       "#60A5FA",
        "accent_hover": "#3B82F6",
        "thought_bg":   "#0A0A0E",
        "thought_text": "#304070",
    },
    "Obsidian": {
        "bg_deep":      "#08060E",
        "bg_base":      "#0E0B16",
        "bg_surface":   "#16121F",
        "bg_input":     "#1D1828",
        "border":       "#2A2040",
        "border_focus": "#8B5CF6",
        "text_primary": "#DDD8F0",
        "text_secondary":"#6B6080",
        "text_muted":   "#3A3050",
        "accent":       "#8B5CF6",
        "accent_hover": "#7C3AED",
        "thought_bg":   "#0A0714",
        "thought_text": "#3D2A6A",
    },
    "Deep Ocean": {
        "bg_deep":      "#050A14",
        "bg_base":      "#0A1220",
        "bg_surface":   "#0F1A2E",
        "bg_input":     "#142038",
        "border":       "#1E2F4A",
        "border_focus": "#38BDF8",
        "text_primary": "#C8E0F8",
        "text_secondary":"#4A7090",
        "text_muted":   "#1E3A50",
        "accent":       "#38BDF8",
        "accent_hover": "#0EA5E9",
        "thought_bg":   "#060C18",
        "thought_text": "#1A3A5A",
    },
    "Forest": {
        "bg_deep":      "#060A06",
        "bg_base":      "#0A100A",
        "bg_surface":   "#101810",
        "bg_input":     "#162016",
        "border":       "#1E2E1E",
        "border_focus": "#4ADE80",
        "text_primary": "#D0E8D0",
        "text_secondary":"#4A7050",
        "text_muted":   "#1E3020",
        "accent":       "#4ADE80",
        "accent_hover": "#22C55E",
        "thought_bg":   "#060C06",
        "thought_text": "#1A3A1A",
    },
    "Crimson": {
        "bg_deep":      "#0E0607",
        "bg_base":      "#140A0B",
        "bg_surface":   "#1C1010",
        "bg_input":     "#221414",
        "border":       "#301818",
        "border_focus": "#F87171",
        "text_primary": "#F0D8D8",
        "text_secondary":"#8A5050",
        "text_muted":   "#502020",
        "accent":       "#F87171",
        "accent_hover": "#EF4444",
        "thought_bg":   "#0E0606",
        "thought_text": "#4A1515",
    },
    "Amber": {
        "bg_deep":      "#0C0902",
        "bg_base":      "#120E04",
        "bg_surface":   "#1C1608",
        "bg_input":     "#241E0C",
        "border":       "#302810",
        "border_focus": "#FBBF24",
        "text_primary": "#F0E8D0",
        "text_secondary":"#806830",
        "text_muted":   "#403010",
        "accent":       "#FBBF24",
        "accent_hover": "#F59E0B",
        "thought_bg":   "#0C0A02",
        "thought_text": "#4A3808",
    },
    "Violet": {
        "bg_deep":      "#09080F",
        "bg_base":      "#100E18",
        "bg_surface":   "#181524",
        "bg_input":     "#201C30",
        "border":       "#2C2840",
        "border_focus": "#A78BFA",
        "text_primary": "#E0DCF8",
        "text_secondary":"#6860A0",
        "text_muted":   "#382860",
        "accent":       "#A78BFA",
        "accent_hover": "#8B5CF6",
        "thought_bg":   "#08060E",
        "thought_text": "#3A286A",
    },
    "Teal": {
        "bg_deep":      "#060C0C",
        "bg_base":      "#0A1414",
        "bg_surface":   "#0F1E1E",
        "bg_input":     "#142828",
        "border":       "#1A3232",
        "border_focus": "#2DD4BF",
        "text_primary": "#C8E8E8",
        "text_secondary":"#3A7878",
        "text_muted":   "#184040",
        "accent":       "#2DD4BF",
        "accent_hover": "#14B8A6",
        "thought_bg":   "#060C0C",
        "thought_text": "#0E3838",
    },
    "Rose": {
        "bg_deep":      "#0E0608",
        "bg_base":      "#160A0D",
        "bg_surface":   "#1E1015",
        "bg_input":     "#26141C",
        "border":       "#321820",
        "border_focus": "#FB7185",
        "text_primary": "#F0D0D8",
        "text_secondary":"#8A4060",
        "text_muted":   "#501828",
        "accent":       "#FB7185",
        "accent_hover": "#F43F5E",
        "thought_bg":   "#0C0608",
        "thought_text": "#4A1828",
    },
    "Slate": {
        "bg_deep":      "#080B0F",
        "bg_base":      "#0F1318",
        "bg_surface":   "#161C22",
        "bg_input":     "#1C232C",
        "border":       "#252E38",
        "border_focus": "#94A3B8",
        "text_primary": "#D8E0EA",
        "text_secondary":"#5A6878",
        "text_muted":   "#2A3440",
        "accent":       "#94A3B8",
        "accent_hover": "#64748B",
        "thought_bg":   "#070A0E",
        "thought_text": "#243040",
    },
    "Zinc": {
        "bg_deep":      "#090909",
        "bg_base":      "#101010",
        "bg_surface":   "#181818",
        "bg_input":     "#202020",
        "border":       "#2C2C2C",
        "border_focus": "#A1A1AA",
        "text_primary": "#E4E4E7",
        "text_secondary":"#71717A",
        "text_muted":   "#3F3F46",
        "accent":       "#A1A1AA",
        "accent_hover": "#71717A",
        "thought_bg":   "#080808",
        "thought_text": "#303030",
    },
    "Copper": {
        "bg_deep":      "#0C0806",
        "bg_base":      "#140E0A",
        "bg_surface":   "#1E160E",
        "bg_input":     "#281E14",
        "border":       "#342618",
        "border_focus": "#F97316",
        "text_primary": "#F0E0D0",
        "text_secondary":"#806040",
        "text_muted":   "#402818",
        "accent":       "#F97316",
        "accent_hover": "#EA580C",
        "thought_bg":   "#0C0806",
        "thought_text": "#4A2808",
    },
    "Arctic": {
        "bg_deep":      "#06080C",
        "bg_base":      "#0C1018",
        "bg_surface":   "#121820",
        "bg_input":     "#182028",
        "border":       "#202A34",
        "border_focus": "#BAE6FD",
        "text_primary": "#D8EEF8",
        "text_secondary":"#4A7890",
        "text_muted":   "#1A3850",
        "accent":       "#BAE6FD",
        "accent_hover": "#7DD3FC",
        "thought_bg":   "#060810",
        "thought_text": "#0E3050",
    },
    "Ember": {
        "bg_deep":      "#0E0804",
        "bg_base":      "#160E06",
        "bg_surface":   "#201408",
        "bg_input":     "#2A1C0C",
        "border":       "#362410",
        "border_focus": "#FB923C",
        "text_primary": "#F8E8D8",
        "text_secondary":"#806040",
        "text_muted":   "#402010",
        "accent":       "#FB923C",
        "accent_hover": "#F97316",
        "thought_bg":   "#0E0802",
        "thought_text": "#4A2008",
    },
    "Sage": {
        "bg_deep":      "#080C08",
        "bg_base":      "#0E1410",
        "bg_surface":   "#141E16",
        "bg_input":     "#1A281C",
        "border":       "#223022",
        "border_focus": "#86EFAC",
        "text_primary": "#D4ECD8",
        "text_secondary":"#4A7050",
        "text_muted":   "#1E3020",
        "accent":       "#86EFAC",
        "accent_hover": "#4ADE80",
        "thought_bg":   "#080C08",
        "thought_text": "#163020",
    },
    "Lavender": {
        "bg_deep":      "#0A080E",
        "bg_base":      "#120E18",
        "bg_surface":   "#1A1622",
        "bg_input":     "#221E2C",
        "border":       "#2C2838",
        "border_focus": "#C4B5FD",
        "text_primary": "#E8E0F8",
        "text_secondary":"#706888",
        "text_muted":   "#3C3450",
        "accent":       "#C4B5FD",
        "accent_hover": "#A78BFA",
        "thought_bg":   "#08060C",
        "thought_text": "#382860",
    },
    "Cobalt": {
        "bg_deep":      "#050810",
        "bg_base":      "#080D1A",
        "bg_surface":   "#0D1424",
        "bg_input":     "#121C30",
        "border":       "#18243C",
        "border_focus": "#60A5FA",
        "text_primary": "#C8D8F8",
        "text_secondary":"#3A5A90",
        "text_muted":   "#183060",
        "accent":       "#60A5FA",
        "accent_hover": "#3B82F6",
        "thought_bg":   "#050810",
        "thought_text": "#102050",
    },
    "Onyx": {
        "bg_deep":      "#000000",
        "bg_base":      "#080808",
        "bg_surface":   "#101010",
        "bg_input":     "#181818",
        "border":       "#222222",
        "border_focus": "#FFFFFF",
        "text_primary": "#F0F0F0",
        "text_secondary":"#606060",
        "text_muted":   "#303030",
        "accent":       "#FFFFFF",
        "accent_hover": "#D0D0D0",
        "thought_bg":   "#050505",
        "thought_text": "#303030",
    },
    "Steel": {
        "bg_deep":      "#080B0E",
        "bg_base":      "#0F1318",
        "bg_surface":   "#171C22",
        "bg_input":     "#1E242C",
        "border":       "#272E36",
        "border_focus": "#7DD3FC",
        "text_primary": "#D4DCE8",
        "text_secondary":"#52647A",
        "text_muted":   "#263040",
        "accent":       "#7DD3FC",
        "accent_hover": "#38BDF8",
        "thought_bg":   "#060A0E",
        "thought_text": "#162840",
    },
    "Mocha": {
        "bg_deep":      "#0C0906",
        "bg_base":      "#141009",
        "bg_surface":   "#1E170E",
        "bg_input":     "#271E14",
        "border":       "#33271A",
        "border_focus": "#D4A96A",
        "text_primary": "#EDE0CC",
        "text_secondary":"#806840",
        "text_muted":   "#402C10",
        "accent":       "#D4A96A",
        "accent_hover": "#B8903A",
        "thought_bg":   "#0A0806",
        "thought_text": "#3C2810",
    },
    "Jade": {
        "bg_deep":      "#050D0A",
        "bg_base":      "#09130E",
        "bg_surface":   "#0F1E16",
        "bg_input":     "#14281E",
        "border":       "#1A3224",
        "border_focus": "#34D399",
        "text_primary": "#C8F0E0",
        "text_secondary":"#2A7050",
        "text_muted":   "#0E3828",
        "accent":       "#34D399",
        "accent_hover": "#10B981",
        "thought_bg":   "#050D08",
        "thought_text": "#0C3820",
    },
    "Graphite": {
        "bg_deep":      "#0C0C0C",
        "bg_base":      "#141414",
        "bg_surface":   "#1C1C1C",
        "bg_input":     "#242424",
        "border":       "#2E2E2E",
        "border_focus": "#8B8B8F",
        "text_primary": "#E0E0E0",
        "text_secondary":"#787878",
        "text_muted":   "#444444",
        "accent":       "#8B8B8F",
        "accent_hover": "#60606A",
        "thought_bg":   "#0A0A0A",
        "thought_text": "#383838",
    },
    "Dusk": {
        "bg_deep":      "#08060E",
        "bg_base":      "#100D18",
        "bg_surface":   "#181420",
        "bg_input":     "#201A2C",
        "border":       "#2A2238",
        "border_focus": "#818CF8",
        "text_primary": "#D8D4F0",
        "text_secondary":"#5850A0",
        "text_muted":   "#2C2860",
        "accent":       "#818CF8",
        "accent_hover": "#6366F1",
        "thought_bg":   "#07060E",
        "thought_text": "#282068",
    },
    "Marine": {
        "bg_deep":      "#040810",
        "bg_base":      "#080F1C",
        "bg_surface":   "#0D1828",
        "bg_input":     "#122034",
        "border":       "#182840",
        "border_focus": "#38BDF8",
        "text_primary": "#C0D8F8",
        "text_secondary":"#2A5880",
        "text_muted":   "#0C3060",
        "accent":       "#38BDF8",
        "accent_hover": "#0EA5E9",
        "thought_bg":   "#04080E",
        "thought_text": "#0C2848",
    },
    "Saffron": {
        "bg_deep":      "#0C0A04",
        "bg_base":      "#141006",
        "bg_surface":   "#1E180A",
        "bg_input":     "#28200E",
        "border":       "#342C12",
        "border_focus": "#FDE68A",
        "text_primary": "#FEF8E8",
        "text_secondary":"#8A7030",
        "text_muted":   "#443808",
        "accent":       "#FDE68A",
        "accent_hover": "#FCD34D",
        "thought_bg":   "#0A0802",
        "thought_text": "#4A3808",
    },
    "Matrix": {
        "bg_deep":      "#000500",
        "bg_base":      "#000A02",
        "bg_surface":   "#001204",
        "bg_input":     "#001A06",
        "border":       "#00280A",
        "border_focus": "#00FF41",
        "text_primary": "#00D432",
        "text_secondary":"#006018",
        "text_muted":   "#002A08",
        "accent":       "#00FF41",
        "accent_hover": "#00CC34",
        "thought_bg":   "#000400",
        "thought_text": "#003010",
    },
    "Sand": {
        "bg_deep":      "#0E0C08",
        "bg_base":      "#161208",
        "bg_surface":   "#201C0E",
        "bg_input":     "#2A2414",
        "border":       "#362E1A",
        "border_focus": "#E2C97E",
        "text_primary": "#EEE8D8",
        "text_secondary":"#8A7850",
        "text_muted":   "#483C1A",
        "accent":       "#E2C97E",
        "accent_hover": "#D4A96A",
        "thought_bg":   "#0C0A06",
        "thought_text": "#3A3010",
    },
    "Ash": {
        "bg_deep":      "#0A0B0D",
        "bg_base":      "#111418",
        "bg_surface":   "#191D22",
        "bg_input":     "#21262D",
        "border":       "#2A3038",
        "border_focus": "#B0B8C4",
        "text_primary": "#CDD5E0",
        "text_secondary":"#5A6470",
        "text_muted":   "#2A3040",
        "accent":       "#B0B8C4",
        "accent_hover": "#8890A0",
        "thought_bg":   "#09090C",
        "thought_text": "#20283A",
    },
    "Neon": {
        "bg_deep":      "#080009",
        "bg_base":      "#0E000F",
        "bg_surface":   "#160018",
        "bg_input":     "#1E0020",
        "border":       "#2A0030",
        "border_focus": "#E879F9",
        "text_primary": "#F0C8F8",
        "text_secondary":"#903090",
        "text_muted":   "#500050",
        "accent":       "#E879F9",
        "accent_hover": "#D946EF",
        "thought_bg":   "#070008",
        "thought_text": "#400040",
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
    border-radius: 4px;
    padding: 9px 12px;
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
    border-radius: 4px;
    padding: 12px 16px;
    color: {text_primary};
    font-size: 11pt;
}}

QPushButton {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 8px 18px;
    color: {text_primary};
    font-weight: 600;
    font-size: 10.5pt;
    min-height: 32px;
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
    font-weight: 700;
}}
QPushButton#btn_generate:hover {{
    background-color: {accent_hover};
    border-color: {accent};
}}
QPushButton#btn_generate:disabled {{
    background-color: {thought_bg};
    border-color: {border};
    color: {text_muted};
}}

QPushButton#btn_stop {{
    background-color: {bg_deep};
    border-color: #7F1D1D;
    color: #FCA5A5;
}}
QPushButton#btn_stop:hover {{
    background-color: #7F1D1D;
    color: #FFFFFF;
}}
QPushButton#btn_stop:disabled {{
    background-color: {bg_deep};
    border-color: {bg_surface};
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

QCheckBox {{
    color: {text_secondary};
    spacing: 8px;
    font-size: 10.5pt;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
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
    border-radius: 4px;
    padding: 7px 10px;
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
    border-radius: 4px;
    padding: 7px 12px;
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
    selection-background-color: {accent};
    color: {text_primary};
    padding: 4px;
    font-size: 11pt;
}}

QListWidget {{
    background-color: {bg_deep};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 4px;
    color: {text_primary};
    font-size: 10.5pt;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 3px;
}}
QListWidget::item:hover {{
    background-color: {bg_surface};
    color: {text_primary};
}}
QListWidget::item:selected {{
    background-color: {accent};
    color: {bg_deep};
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
    border-radius: 4px;
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
"""
