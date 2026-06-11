"""
Karl design system — customizable theme engine.
Palettes are compiled dynamically into QSS.
"""

ACCENT_DEFAULT = "#00C2FF"

THEMES = {
    "Karl Obsidian": {
        "bg_deep":     "#020205",
        "bg_base":     "#07070F",
        "bg_surface":  "#0D0D1B",
        "bg_raised":   "#14142D",
        "bg_input":    "#05050D",
        "border":      "#1F1F3D",
        "border_hi":   "#35356E",
        "accent":      "#00E5FF",
        "accent_dark": "#0099AA",
        "text_hi":     "#F0F5FF",
        "text_mid":    "#A0AEC0",
        "text_lo":     "#6A7B95",
        "think_bg":    "#04040A",
        "think_text":  "#7F95B5",
        "green":       "#00FFAA",
        "red":         "#FF3366",
        "yellow":      "#FFCC00",
        "sidebar_bg":  "#030308",
        "sidebar_sel": "#111129",
    },
    "USMC Tactical": {
        "bg_deep":     "#0E100D",
        "bg_base":     "#141812",
        "bg_surface":  "#1C2119",
        "bg_raised":   "#252C21",
        "bg_input":    "#11140F",
        "border":      "#323C2D",
        "border_hi":   "#4A5842",
        "accent":      "#D4AF37", # Desert Gold
        "accent_dark": "#9E7D1A",
        "text_hi":     "#E4E8E2",
        "text_mid":    "#9BA896",
        "text_lo":     "#5F6C5B",
        "think_bg":    "#0B0D0A",
        "think_text":  "#5F6C5B",
        "green":       "#76D437",
        "red":         "#D43737",
        "yellow":      "#D4A037",
        "sidebar_bg":  "#0A0C09",
        "sidebar_sel": "#1D2319",
    },
    "macOS Sonoma": {
        "bg_deep":     "#161616",
        "bg_base":     "#1E1E1E",
        "bg_surface":  "#262626",
        "bg_raised":   "#303030",
        "bg_input":    "#1C1C1C",
        "border":      "#3A3A3A",
        "border_hi":   "#505050",
        "accent":      "#007AFF", # Apple Blue
        "accent_dark": "#005EC2",
        "text_hi":     "#F5F5F7",
        "text_mid":    "#8E8E93",
        "text_lo":     "#5A5A5F",
        "think_bg":    "#1C1C1E",
        "think_text":  "#8E8E93",
        "green":       "#34C759",
        "red":         "#FF3B30",
        "yellow":      "#FFCC00",
        "sidebar_bg":  "#121212",
        "sidebar_sel": "#2C2C2E",
    },
    "Cyberpunk Neon": {
        "bg_deep":     "#0A0512",
        "bg_base":     "#110A24",
        "bg_surface":  "#1A1135",
        "bg_raised":   "#231747",
        "bg_input":    "#0D071B",
        "border":      "#321C63",
        "border_hi":   "#4D2D8F",
        "accent":      "#FF007F", # Neon Pink
        "accent_dark": "#C2005F",
        "text_hi":     "#00FFFF", # Cyan
        "text_mid":    "#BD93F9",
        "text_lo":     "#6272A4",
        "think_bg":    "#0D071C",
        "think_text":  "#8BE9FD",
        "green":       "#50FA7B",
        "red":         "#FF5555",
        "yellow":      "#FFB86C",
        "sidebar_bg":  "#08040F",
        "sidebar_sel": "#21153E",
    },
    "Nordic Frost": {
        "bg_deep":     "#1B222A",
        "bg_base":     "#242E38",
        "bg_surface":  "#2E3A47",
        "bg_raised":   "#394756",
        "bg_input":    "#1F2730",
        "border":      "#3E4E5E",
        "border_hi":   "#546A80",
        "accent":      "#88C0D0", # Frost Blue
        "accent_dark": "#5E81AC",
        "text_hi":     "#ECEFF4",
        "text_mid":    "#D8DEE9",
        "text_lo":     "#4C566A",
        "think_bg":    "#1F2731",
        "think_text":  "#4C566A",
        "green":       "#A3BE8C",
        "red":         "#BF616A",
        "yellow":      "#EBCB8B",
        "sidebar_bg":  "#181E25",
        "sidebar_sel": "#344251",
    },
    "Solarized Dark": {
        "bg_deep":     "#001B21",
        "bg_base":     "#002B36",
        "bg_surface":  "#073642",
        "bg_raised":   "#586E75",
        "bg_input":    "#00212B",
        "border":      "#0A4656",
        "border_hi":   "#0E5E72",
        "accent":      "#CB4B16", # Orange
        "accent_dark": "#9B3005",
        "text_hi":     "#93A1A1",
        "text_mid":    "#839496",
        "text_lo":     "#586E75",
        "think_bg":    "#00212C",
        "think_text":  "#586E75",
        "green":       "#859900",
        "red":         "#DC322F",
        "yellow":      "#B58900",
        "sidebar_bg":  "#00171D",
        "sidebar_sel": "#0A3B47",
    },
    "Monokai Pro": {
        "bg_deep":     "#191919",
        "bg_base":     "#222222",
        "bg_surface":  "#2D2D2D",
        "bg_raised":   "#3A3A3A",
        "bg_input":    "#1D1D1D",
        "border":      "#404040",
        "border_hi":   "#555555",
        "accent":      "#FFD866", # Yellow
        "accent_dark": "#C4A23B",
        "text_hi":     "#FCFCFA",
        "text_mid":    "#C1C0C0",
        "text_lo":     "#727072",
        "think_bg":    "#1E1E1E",
        "think_text":  "#727072",
        "green":       "#A9DC76",
        "red":         "#FF6188",
        "yellow":      "#FFD866",
        "sidebar_bg":  "#141414",
        "sidebar_sel": "#333333",
    },
    "Dracula": {
        "bg_deep":     "#1E1F29",
        "bg_base":     "#282A36",
        "bg_surface":  "#343746",
        "bg_raised":   "#414558",
        "bg_input":    "#21222C",
        "border":      "#44475A",
        "border_hi":   "#6272A4",
        "accent":      "#BD93F9", # Orchid
        "accent_dark": "#8E62C9",
        "text_hi":     "#F8F8F2",
        "text_mid":    "#8BE9FD",
        "text_lo":     "#6272A4",
        "think_bg":    "#22232D",
        "think_text":  "#6272A4",
        "green":       "#50FA7B",
        "red":         "#FF5555",
        "yellow":      "#FFB86C",
        "sidebar_bg":  "#191A21",
        "sidebar_sel": "#383A49",
    },
    "Forest Ranger": {
        "bg_deep":     "#0A140F",
        "bg_base":     "#101E17",
        "bg_surface":  "#182C22",
        "bg_raised":   "#223C2F",
        "bg_input":    "#0D1913",
        "border":      "#2B4C3B",
        "border_hi":   "#3C6B53",
        "accent":      "#E5A93C", # Autumn Gold
        "accent_dark": "#B38024",
        "text_hi":     "#E4EEE9",
        "text_mid":    "#A4BFB1",
        "text_lo":     "#58826D",
        "think_bg":    "#0C1712",
        "think_text":  "#58826D",
        "green":       "#3CD178",
        "red":         "#D13C3C",
        "yellow":      "#D19E3C",
        "sidebar_bg":  "#08100C",
        "sidebar_sel": "#1D3529",
    },
    "Steel & Rust": {
        "bg_deep":     "#151719",
        "bg_base":     "#1F2226",
        "bg_surface":  "#2A2E33",
        "bg_raised":   "#363B42",
        "bg_input":    "#1A1D20",
        "border":      "#3E444B",
        "border_hi":   "#555D67",
        "accent":      "#D05C2A", # Rust Orange
        "accent_dark": "#9E3F18",
        "text_hi":     "#E6E8EA",
        "text_mid":    "#A4ADB6",
        "text_lo":     "#64707C",
        "think_bg":    "#1B1E21",
        "think_text":  "#64707C",
        "green":       "#41C366",
        "red":         "#C34141",
        "yellow":      "#C39441",
        "sidebar_bg":  "#111315",
        "sidebar_sel": "#2E3339",
    },
    "Deep Space": {
        "bg_deep":     "#000000",
        "bg_base":     "#050508",
        "bg_surface":  "#0C0C12",
        "bg_raised":   "#151520",
        "bg_input":    "#040406",
        "border":      "#1B1B2A",
        "border_hi":   "#2C2C42",
        "accent":      "#8A2BE2", # Purple
        "accent_dark": "#6318AF",
        "text_hi":     "#F0F0F5",
        "text_mid":    "#9E9EAE",
        "text_lo":     "#545468",
        "think_bg":    "#030305",
        "think_text":  "#545468",
        "green":       "#00E676",
        "red":         "#FF1744",
        "yellow":      "#FFEA00",
        "sidebar_bg":  "#000000",
        "sidebar_sel": "#12121E",
    },
    "Sunset Glow": {
        "bg_deep":     "#120508",
        "bg_base":     "#1D0B10",
        "bg_surface":  "#2A121A",
        "bg_raised":   "#381B24",
        "bg_input":    "#17080C",
        "border":      "#471E2D",
        "border_hi":   "#632C40",
        "accent":      "#FF5722", # Sunset Orange
        "accent_dark": "#C43A0F",
        "text_hi":     "#F9F0F2",
        "text_mid":    "#D4AAB6",
        "text_lo":     "#8F5F6D",
        "think_bg":    "#17080D",
        "think_text":  "#8F5F6D",
        "green":       "#4CAF50",
        "red":         "#F44336",
        "yellow":      "#FFC107",
        "sidebar_bg":  "#0F0306",
        "sidebar_sel": "#31141E",
    },
    "Retro Terminal": {
        "bg_deep":     "#000000",
        "bg_base":     "#020B04",
        "bg_surface":  "#051408",
        "bg_raised":   "#09210E",
        "bg_input":    "#010803",
        "border":      "#0F3818",
        "border_hi":   "#185926",
        "accent":      "#33FF33", # Phosphor Green
        "accent_dark": "#16B816",
        "text_hi":     "#85FF85",
        "text_mid":    "#24B824",
        "text_lo":     "#0E4D1D",
        "think_bg":    "#000000",
        "think_text":  "#0E4D1D",
        "green":       "#33FF33",
        "red":         "#FF3333",
        "yellow":      "#FFFF33",
        "sidebar_bg":  "#000000",
        "sidebar_sel": "#08210C",
    },
    "Ghost Shell": {
        "bg_deep":     "#12161A",
        "bg_base":     "#1A1E24",
        "bg_surface":  "#232930",
        "bg_raised":   "#2C343D",
        "bg_input":    "#151A1F",
        "border":      "#39434F",
        "border_hi":   "#4B596A",
        "accent":      "#00E5FF", # Cyber Cyan
        "accent_dark": "#0099AA",
        "text_hi":     "#F0F4F8",
        "text_mid":    "#A2B2C3",
        "text_lo":     "#5A6E82",
        "think_bg":    "#161A20",
        "think_text":  "#5A6E82",
        "green":       "#00E676",
        "red":         "#FF1744",
        "yellow":      "#FFEA00",
        "sidebar_bg":  "#0E1216",
        "sidebar_sel": "#272E37",
    },
    "Midnight Purple": {
        "bg_deep":     "#09050F",
        "bg_base":     "#140D21",
        "bg_surface":  "#1E1530",
        "bg_raised":   "#2B1F43",
        "bg_input":    "#0F091A",
        "border":      "#322352",
        "border_hi":   "#4A3579",
        "accent":      "#DA70D6", # Orchid
        "accent_dark": "#A74AA3",
        "text_hi":     "#E6DDF2",
        "text_mid":    "#AF9ECA",
        "text_lo":     "#68558A",
        "think_bg":    "#100A1B",
        "think_text":  "#68558A",
        "green":       "#32CD32",
        "red":         "#DC143C",
        "yellow":      "#FFD700",
        "sidebar_bg":  "#08040C",
        "sidebar_sel": "#24193A",
    },
    "Titanium": {
        "bg_deep":     "#1A1A1E",
        "bg_base":     "#222228",
        "bg_surface":  "#2C2C34",
        "bg_raised":   "#373740",
        "bg_input":    "#1D1D23",
        "border":      "#40404C",
        "border_hi":   "#565666",
        "accent":      "#E5E5E5", # Silver-White
        "accent_dark": "#A6A6A6",
        "text_hi":     "#FAFAFA",
        "text_mid":    "#B0B0B8",
        "text_lo":     "#6C6C78",
        "think_bg":    "#1F1F24",
        "think_text":  "#6C6C78",
        "green":       "#26A69A",
        "red":         "#EF5350",
        "yellow":      "#FFCA28",
        "sidebar_bg":  "#151518",
        "sidebar_sel": "#31313A",
    },
    "Desert Storm": {
        "bg_deep":     "#1A1712",
        "bg_base":     "#24201A",
        "bg_surface":  "#302A22",
        "bg_raised":   "#3C352B",
        "bg_input":    "#1F1C16",
        "border":      "#4C4336",
        "border_hi":   "#655A48",
        "accent":      "#C8B195", # Sand
        "accent_dark": "#9A846A",
        "text_hi":     "#ECE8E2",
        "text_mid":    "#BBAE9D",
        "text_lo":     "#796E5E",
        "think_bg":    "#1F1C17",
        "think_text":  "#796E5E",
        "green":       "#7BA05B",
        "red":         "#A05B5B",
        "yellow":      "#A08B5B",
        "sidebar_bg":  "#15120E",
        "sidebar_sel": "#362F27",
    },
    "Stealth Bomber": {
        "bg_deep":     "#030303",
        "bg_base":     "#0A0A0A",
        "bg_surface":  "#121212",
        "bg_raised":   "#1B1B1B",
        "bg_input":    "#070707",
        "border":      "#242424",
        "border_hi":   "#363636",
        "accent":      "#E53935", # Stealth Red
        "accent_dark": "#B71C1C",
        "text_hi":     "#F5F5F5",
        "text_mid":    "#A0A0A0",
        "text_lo":     "#555555",
        "think_bg":    "#060606",
        "think_text":  "#555555",
        "green":       "#4CAF50",
        "red":         "#E53935",
        "yellow":      "#FFB300",
        "sidebar_bg":  "#000000",
        "sidebar_sel": "#1F1F1F",
    },
    "Ocean Trench": {
        "bg_deep":     "#030D16",
        "bg_base":     "#071424",
        "bg_surface":  "#0D2034",
        "bg_raised":   "#152E47",
        "bg_input":    "#04101D",
        "border":      "#173D5E",
        "border_hi":   "#225887",
        "accent":      "#00F5D4", # Luminescent Aqua
        "accent_dark": "#00BBA2",
        "text_hi":     "#ECEFF4",
        "text_mid":    "#8EAFCE",
        "text_lo":     "#3F6C95",
        "think_bg":    "#04101E",
        "think_text":  "#3F6C95",
        "green":       "#00E676",
        "red":         "#FF1744",
        "yellow":      "#FFEA00",
        "sidebar_bg":  "#020A10",
        "sidebar_sel": "#12263C",
    },
    "Carbon Fiber": {
        "bg_deep":     "#121212",
        "bg_base":     "#191919",
        "bg_surface":  "#212121",
        "bg_raised":   "#2C2C2C",
        "bg_input":    "#161616",
        "border":      "#383838",
        "border_hi":   "#4C4C4C",
        "accent":      "#FFEA00", # Safety Yellow
        "accent_dark": "#C4B200",
        "text_hi":     "#F5F5F5",
        "text_mid":    "#B0B0B0",
        "text_lo":     "#5C5C5C",
        "think_bg":    "#151515",
        "think_text":  "#5C5C5C",
        "green":       "#00E676",
        "red":         "#FF1744",
        "yellow":      "#FFEA00",
        "sidebar_bg":  "#0C0C0C",
        "sidebar_sel": "#262626",
    }
}

PALETTE = THEMES["Karl Obsidian"]

MONO = (
    "'JetBrains Mono', 'Fira Code', 'Cascadia Code', "
    "'Consolas', 'Courier New', monospace"
)

def darken_hex_color(hex_str: str, factor: float = 0.7) -> str:
    """Darken a hex color string by a given factor."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return "#008CB8"
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02X}{g:02X}{b:02X}"
    except ValueError:
        return "#008CB8"

def _tint_hex_color(hex_str: str, r_mod: int, g_mod: int, b_mod: int) -> str:
    """Tint a hex color by adding offsets to its RGB channels."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return "#" + hex_str
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        r = max(0, min(255, r + r_mod))
        g = max(0, min(255, g + g_mod))
        b = max(0, min(255, b + b_mod))
        return f"#{r:02X}{g:02X}{b:02X}"
    except ValueError:
        return "#" + hex_str

def get_theme_colors(theme_name: str, custom_accent: str | None = None, bg_tone: str | None = None) -> dict:
    """Get the palette colors dictionary for the given theme, custom accent and background tone overlay."""
    p = dict(THEMES.get(theme_name, THEMES["Karl Obsidian"]))
    if custom_accent:
        p["accent"] = custom_accent
        p["accent_dark"] = darken_hex_color(custom_accent, 0.7)
    
    if bg_tone == "Pitch Black":
        for k in ["bg_deep", "bg_base", "bg_surface", "bg_raised", "bg_input", "sidebar_bg", "think_bg"]:
            p[k] = "#000000"
    elif bg_tone == "Warm Sepia":
        for k in ["bg_deep", "bg_base", "bg_surface", "bg_raised", "bg_input", "sidebar_bg", "think_bg"]:
            p[k] = _tint_hex_color(p[k], r_mod=10, g_mod=4, b_mod=-10)
    elif bg_tone == "Cool Slate":
        for k in ["bg_deep", "bg_base", "bg_surface", "bg_raised", "bg_input", "sidebar_bg", "think_bg"]:
            p[k] = _tint_hex_color(p[k], r_mod=-8, g_mod=2, b_mod=12)
            
    return p

def get_theme_stylesheet(theme_name: str, custom_accent: str | None = None, bg_tone: str | None = None) -> str:
    """Compile the QSS stylesheet for the given theme and options."""
    p = get_theme_colors(theme_name, custom_accent, bg_tone)
    p["mono"] = MONO
    return _SHEET.format(**p)

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

QPushButton#btn-success {{
    background: transparent;
    border: 1px solid {green};
    color: {green};
    border-radius: 4px;
}}

QPushButton#btn-success:hover {{
    background: {green};
    color: #050510;
    font-weight: bold;
}}

QPushButton#btn-warning {{
    background: transparent;
    border: 1px solid {yellow};
    color: {yellow};
    border-radius: 4px;
}}

QPushButton#btn-warning:hover {{
    background: {yellow};
    color: #050510;
    font-weight: bold;
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

QPushButton#btn-ghost:disabled {{
    color: {text_lo};
    background: transparent;
    border: none;
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
    border-radius: 6px;
    color: {text_hi};
    font-family: {mono};
    outline: none;
    padding: 4px;
}}

QListWidget::item {{
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}}

QListWidget::item:hover {{
    background: {bg_raised};
    color: {text_hi};
}}

QListWidget::item:selected {{
    background: {sidebar_sel};
    color: {accent};
    font-weight: bold;
}}

/* ── CheckBox ─────────────────────────────────────────────── */
QCheckBox {{
    color: {text_mid};
    spacing: 6px;
    font-family: {mono};
    font-size: 9pt;
}}

QCheckBox:hover {{
    color: {text_hi};
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {border};
    border-radius: 3px;
    background: {bg_input};
}}

QCheckBox::indicator:hover {{
    border-color: {border_hi};
}}

QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}

QCheckBox::indicator:disabled {{
    background: {bg_surface};
    border-color: {border};
}}


/* ── TreeWidget ───────────────────────────────────────────── */
QTreeWidget {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 6px;
    color: {text_hi};
    font-family: {mono};
    outline: none;
    padding: 4px;
}}

QTreeWidget::item {{
    padding: 6px 10px;
    border-radius: 4px;
    margin: 1px 2px;
}}

QTreeWidget::item:hover {{
    background: {bg_raised};
    color: {text_hi};
}}

QTreeWidget::item:selected {{
    background: {sidebar_sel};
    color: {accent};
    font-weight: bold;
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
QLabel#model-pill {{
    font-size: 8pt;
    font-weight: bold;
    color: {accent};
    background: {bg_deep};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 2px 6px;
}}


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
    border-bottom: 2px solid {accent};
}}

QTabBar::tab:hover:!selected {{
    color: {text_mid};
}}

/* ── Progress ─────────────────────────────────────────────── */
QProgressBar {{
    background: {bg_input};
    border: 1px solid {border};
    border-radius: 6px;
    text-align: center;
    color: {text_hi};
    font-size: 8pt;
    font-family: {mono};
    height: 16px;
}}

QProgressBar::chunk {{
    background: {accent};
    border-radius: 5px;
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

/* ── Docks & Splitters ────────────────────────────────────── */
QDockWidget {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 4px;
}}

QDockWidget::title {{
    background: {bg_raised};
    border-bottom: 1px solid {border};
    padding: 6px 12px;
    color: {text_hi};
    font-size: 8pt;
    font-weight: bold;
    letter-spacing: 2px;
    text-align: left;
}}

QDockWidget::close-button, QDockWidget::float-button {{
    border: none;
    background: transparent;
    padding: 2px;
    border-radius: 3px;
}}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background: {border};
}}

QMainWindow::separator {{
    background: {border};
    width: 2px;
    height: 2px;
}}

QMainWindow::separator:hover {{
    background: {accent};
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
    return get_theme_stylesheet("Karl Obsidian", accent)
