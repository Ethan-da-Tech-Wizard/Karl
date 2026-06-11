from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class SectionShell(QWidget):
    """
    A unified section wrapper that bundles a section header, description text,
    and a content widget with consistent margins and styling.
    """
    def __init__(self, title: str, content_widget: QWidget, desc_text: str = "", parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Standardized Section Header
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("section-header")
        layout.addWidget(self.title_lbl)
        
        # Optional Description Sub-Header
        if desc_text:
            self.desc_lbl = QLabel(desc_text)
            self.desc_lbl.setObjectName("lbl-muted")
            self.desc_lbl.setWordWrap(True)
            self.desc_lbl.setStyleSheet("font-size: 8.5pt; margin-bottom: 4px;")
            layout.addWidget(self.desc_lbl)
            
        layout.addWidget(content_widget, 1)
