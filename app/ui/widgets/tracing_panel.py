from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor

class TracingPanel(QFrame):
    """
    A customizable QFrame that draws an animated neon segment tracing along
    its border when set_active(True) is called. Automatically falls back to
    a static highlight border if state.reduced_motion is active.
    """
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._active = False
        self._offset = 0
        self._accent_color = "#00C2FF"
        
        # Set up a timer for the animation (approx. 40 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        
        self.setObjectName("panel")
        self.setStyleSheet("border-radius: 4px;")

    def set_active(self, active: bool):
        self._active = active
        # Check global reduced motion setting
        is_reduced = getattr(self.state, "reduced_motion", False)
        if self._active and not is_reduced:
            if not self._timer.isActive():
                self._timer.start(25)
        else:
            self._timer.stop()
        self.update()

    def set_accent_color(self, hex_color: str):
        self._accent_color = hex_color
        self.update()

    def _on_tick(self):
        self._offset -= 2
        if self._offset <= -1000:
            self._offset = 0
        self.update()

    def paintEvent(self, event):
        # Let default styling render the background/borders
        super().paintEvent(event)
        
        # If not active, nothing more to draw
        if not self._active:
            return
            
        is_reduced = getattr(self.state, "reduced_motion", False)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create rounded rect path matching parent boundary
        path = QPainterPath()
        path.addRoundedRect(1.0, 1.0, self.width() - 2.0, self.height() - 2.0, 4.0, 4.0)
        
        # Resolve active theme colors
        color = QColor(self._accent_color)
        
        if is_reduced:
            # Draw a static continuous highlight border instead of a moving trace line
            pen = QPen(color, 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawPath(path)
        else:
            # Draw a moving neon dash tracing highlight
            pen = QPen(color, 1.5)
            # Custom dash: 60px visible dash, 180px gap
            pen.setDashPattern([60, 180])
            pen.setDashOffset(self._offset)
            painter.setPen(pen)
            painter.drawPath(path)
