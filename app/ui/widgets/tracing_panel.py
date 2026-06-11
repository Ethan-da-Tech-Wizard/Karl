from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor
from app.ui.themes import get_theme_colors

class TracingPanel(QFrame):
    """
    A customizable QFrame that draws an animated neon segment tracing along
    its border when set_active(True) is called. Adapts to theme-specific
    motion styles (normal, slow, pulse, static) and user speed configurations.
    """
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._active = False
        self._offset = 0
        self._pulse_val = 0.6
        self._pulse_direction = 1
        self._accent_color = None
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        
        self.setObjectName("panel")
        self.setStyleSheet("border-radius: 4px;")

    def set_active(self, active: bool):
        self._active = active
        self._update_timer_state()
        self.update()

    def set_accent_color(self, hex_color: str):
        self._accent_color = hex_color
        self.update()

    def _update_timer_state(self):
        is_reduced = getattr(self.state, "reduced_motion", False) if self.state else False
        colors = get_theme_colors(self.state) if self.state else {}
        motion_style = colors.get("motion_style", "normal")
        
        if self._active and not is_reduced and motion_style != "static":
            if not self._timer.isActive():
                self._timer.start(25)
        else:
            self._timer.stop()

    def _on_tick(self):
        intensity = getattr(self.state, "animation_intensity", 1.0) if self.state else 1.0
        colors = get_theme_colors(self.state) if self.state else {}
        motion_style = colors.get("motion_style", "normal")
        
        if motion_style == "pulse":
            step = 0.03 * intensity
            self._pulse_val += step * self._pulse_direction
            if self._pulse_val >= 1.0:
                self._pulse_val = 1.0
                self._pulse_direction = -1
            elif self._pulse_val <= 0.2:
                self._pulse_val = 0.2
                self._pulse_direction = 1
        else:
            step = 2.0 * intensity
            if motion_style == "slow":
                step = 0.8 * intensity
            self._offset -= int(step)
            if self._offset <= -1000:
                self._offset = 0
        self.update()

    def update_style(self):
        self._update_timer_state()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._active:
            return
            
        is_reduced = getattr(self.state, "reduced_motion", False) if self.state else False
        colors = get_theme_colors(self.state) if self.state else {}
        motion_style = colors.get("motion_style", "normal")
        accent = self._accent_color or colors.get("accent", "#00C2FF")
        color = QColor(accent)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(1.0, 1.0, self.width() - 2.0, self.height() - 2.0, 4.0, 4.0)
        
        if is_reduced or motion_style == "static":
            pen = QPen(color, 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawPath(path)
        elif motion_style == "pulse":
            pulse_color = QColor(color)
            pulse_color.setAlphaF(self._pulse_val)
            pen = QPen(pulse_color, 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawPath(path)
        else:
            pen = QPen(color, 1.5)
            pen.setDashPattern([60, 180])
            pen.setDashOffset(self._offset)
            painter.setPen(pen)
            painter.drawPath(path)
