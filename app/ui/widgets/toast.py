from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint


class ToastOverlay(QWidget):
    """A non-intrusive floating toast overlay for success notifications."""
    
    def __init__(self, parent: QWidget, message: str, duration_ms: int = 3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        layout = QVBoxLayout(self)
        self._lbl = QLabel(message)
        self._lbl.setObjectName("toast-label")
        self._lbl.setStyleSheet("""
            QLabel#toast-label {
                background-color: #0D0D1B;
                color: #00C2FF;
                border: 1px solid #00C2FF;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 9pt;
            }
        """)
        layout.addWidget(self._lbl)
        
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(500)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        
        self._duration = duration_ms

    def show_toast(self):
        self.show()
        # Position at top center of parent
        if self.parentWidget():
            p_rect = self.parentWidget().rect()
            p_global = self.parentWidget().mapToGlobal(QPoint(0, 0))
            self.move(
                p_global.x() + (p_rect.width() - self.width()) // 2,
                p_global.y() + 40
            )
            
        self._fade_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._fade_anim.start()
        self._timer.start(self._duration)

    def _fade_out(self):
        self._fade_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self._fade_anim.finished.connect(self.close)
        self._fade_anim.start()
