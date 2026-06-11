from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor

class GlowPanel(QFrame):
    """
    A QFrame that displays a soft neon glow around its edges using
    QGraphicsDropShadowEffect. The glow is bypassed if reduced_motion is active.
    """
    def __init__(self, state, parent=None, glow_color="#00C2FF", blur_radius=12):
        super().__init__(parent)
        self.state = state
        self._glow_color = glow_color
        self._blur_radius = blur_radius
        self._effect = None
        
        self.setObjectName("panel")
        self.setStyleSheet("border-radius: 4px;")
        self._apply_glow()

    def set_glow_color(self, hex_color: str):
        self._glow_color = hex_color
        self._apply_glow()

    def _apply_glow(self):
        is_reduced = getattr(self.state, "reduced_motion", False) if self.state else False
        if is_reduced:
            self.setGraphicsEffect(None)
            self._effect = None
        else:
            self._effect = QGraphicsDropShadowEffect(self)
            self._effect.setColor(QColor(self._glow_color))
            self._effect.setBlurRadius(self._blur_radius)
            self._effect.setXOffset(0)
            self._effect.setYOffset(0)
            self.setGraphicsEffect(self._effect)
            
    def update_style(self):
        # Refresh the glow effect if settings change
        self._apply_glow()
