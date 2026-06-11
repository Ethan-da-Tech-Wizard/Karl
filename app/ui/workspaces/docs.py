import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QTextBrowser, QLabel, QFrame, QLineEdit
from PyQt6.QtCore import Qt

from app.ui.themes import MONO
from app.ui.workspaces.docs_data import DEFAULT_LIBRARY

def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l

def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f

class DocsWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._init_library()
        self._build_ui()

    def _init_library(self):
        self._library_dir = "data/codex_library"
        os.makedirs(self._library_dir, exist_ok=True)
        
        version_filepath = os.path.join(self._library_dir, ".version")
        current_version = "4.0"
        
        # Determine if we need to seed or upgrade
        needs_upgrade = True
        if os.path.exists(version_filepath):
            try:
                with open(version_filepath, "r", encoding="utf-8") as vf:
                    installed_version = vf.read().strip()
                if installed_version == current_version:
                    needs_upgrade = False
            except Exception:
                pass
                
        # If files don't exist, we definitely seed/upgrade
        existing_files = [f for f in os.listdir(self._library_dir) if f.endswith((".html", ".md"))]
        if not existing_files:
            needs_upgrade = True
            
        if needs_upgrade:
            # Seed or overwrite default files in DEFAULT_LIBRARY
            for topic, content in DEFAULT_LIBRARY.items():
                safe_name = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip()
                filepath = os.path.join(self._library_dir, f"{safe_name}.html")
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception as e:
                    print(f"[Codex] Error seeding topic {topic}: {e}")
                    
            # Write new version file
            try:
                with open(version_filepath, "w", encoding="utf-8") as vf:
                    vf.write(current_version)
            except Exception as e:
                print(f"[Codex] Error writing version: {e}")
            
        # Re-scan to build cache
        self._cache = {}
        for f in sorted(os.listdir(self._library_dir)):
            if f.endswith((".html", ".md")):
                filepath = os.path.join(self._library_dir, f)
                topic_name = os.path.splitext(f)[0]
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()
                    self._cache[topic_name] = {
                        "filepath": filepath,
                        "content": content
                    }
                except Exception as e:
                    print(f"[Codex] Error reading {f}: {e}")

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left list panel: guide chapters
        left_panel = QWidget()
        left_panel.setObjectName("panel")
        left_panel.setFixedWidth(200)
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(12, 12, 12, 12)
        lp_layout.setSpacing(8)

        lp_layout.addWidget(_section("CODEX"))

        # Live Search Input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search Codex...")
        self._search_input.setToolTip("Search for keywords in Codex titles or guides")
        self._search_input.textChanged.connect(self._filter_topics)
        lp_layout.addWidget(self._search_input)

        self._topics_list = QListWidget()
        self._topics_list.setToolTip("Select a topic to view its in-app documentation")
        self._topics_list.currentTextChanged.connect(self._on_topic_selected)
        
        # Populate topics list from scanned cache keys
        for k in self._cache.keys():
            self._topics_list.addItem(k)

        lp_layout.addWidget(self._topics_list, 1)
        root.addWidget(left_panel)

        # Right browser panel: content reader
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(8)

        self._browser = QTextBrowser()
        self._browser.setToolTip("Read-only documentation viewer")
        rp_layout.addWidget(self._browser, 1)
        root.addWidget(right_panel, 1)

        # Select first topic by default
        if self._cache:
            self._topics_list.setCurrentRow(0)

    def _filter_topics(self, text: str):
        query = text.lower().strip()
        first_visible = None
        current_visible = False
        current_item = self._topics_list.currentItem()
        
        for idx in range(self._topics_list.count()):
            item = self._topics_list.item(idx)
            topic_name = item.text()
            item_data = self._cache.get(topic_name, {})
            content = item_data.get("content", "").lower()
            match = (query in topic_name.lower()) or (query in content)
            item.setHidden(not match)
            if match:
                if first_visible is None:
                    first_visible = item
                if current_item and current_item.text() == topic_name:
                    current_visible = True
                    
        if not current_visible and first_visible:
            self._topics_list.setCurrentItem(first_visible)
        elif not first_visible:
            self._browser.setHtml(
                f"<div style='font-family:{MONO}; font-size:10pt; color:#9090A8; line-height:1.5; padding:8px;'>"
                f"No results found for query: <i>{text}</i>"
                f"</div>"
            )

    def _on_topic_selected(self, text: str):
        if not text:
            self._browser.clear()
            return
            
        item_data = self._cache.get(text)
        if not item_data:
            self._browser.setHtml(
                f"<div style='font-family:{MONO}; font-size:10pt; color:#9090A8; line-height:1.5; padding:8px;'>"
                f"No guide found for: <i>{text}</i>"
                f"</div>"
            )
            return
            
        # Dynamically load from disk to support user modifications on-demand!
        filepath = item_data["filepath"]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc_content = f.read()
        except Exception as e:
            doc_content = f"Error reading guide from disk: {e}"
            
        # Wrapped with styled div for fonts
        styled_html = (
            f"<div style='font-family:{MONO}; font-size:10pt; color:#E4E4F0; line-height:1.5; padding:8px;'>"
            f"{doc_content}"
            f"</div>"
        )
        self._browser.setHtml(styled_html)
