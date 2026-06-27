from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF
from app.ui.themes import get_theme_colors

class BaseSymbol(QWidget):
    """Base class for theme-aware custom painted icons."""
    def __init__(self, state, color_role="accent", size=16, parent=None):
        super().__init__(parent)
        self.state = state
        self.color_role = color_role
        self._size = size
        self.setFixedSize(QSize(size, size))

    def set_color_role(self, role: str):
        self.color_role = role
        self.update()

    def get_color(self) -> QColor:
        colors = get_theme_colors(self.state)
        hex_color = colors.get(self.color_role, colors.get("accent", "#00C2FF"))
        return QColor(hex_color)


class HamburgerIcon(BaseSymbol):
    """Draws a clean, futuristic 3-line menu bar icon."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(self.get_color(), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        pad = w * 0.15
        
        # 3 horizontal lines
        painter.drawLine(int(pad), int(h * 0.3), int(w - pad), int(h * 0.3))
        painter.drawLine(int(pad), int(h * 0.5), int(w - pad), int(h * 0.5))
        painter.drawLine(int(pad), int(h * 0.7), int(w - pad), int(h * 0.7))


class BrainIcon(BaseSymbol):
    """Draws an abstract neural network node schema representing cognitive reasoning."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self.get_color()
        pen = QPen(color, 1.2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        
        w = self.width()
        h = self.height()
        
        # Define 4 nodes
        n1 = (w * 0.3, h * 0.5)
        n2 = (w * 0.7, h * 0.3)
        n3 = (w * 0.7, h * 0.7)
        n4 = (w * 0.5, h * 0.5)
        
        # Draw connections
        painter.drawLine(int(n1[0]), int(n1[1]), int(n4[0]), int(n4[1]))
        painter.drawLine(int(n4[0]), int(n4[1]), int(n2[0]), int(n2[1]))
        painter.drawLine(int(n4[0]), int(n4[1]), int(n3[0]), int(n3[1]))
        
        # Draw node circles
        r = w * 0.1
        painter.drawEllipse(int(n1[0] - r), int(n1[1] - r), int(r * 2), int(r * 2))
        painter.drawEllipse(int(n2[0] - r), int(n2[1] - r), int(r * 2), int(r * 2))
        painter.drawEllipse(int(n3[0] - r), int(n3[1] - r), int(r * 2), int(r * 2))
        
        # Inner active node
        r_inner = w * 0.08
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(int(n4[0] - r_inner), int(n4[1] - r_inner), int(r_inner * 2), int(r_inner * 2))


class ThumbsUpIcon(BaseSymbol):
    """Draws a clean vector thumbs-up glyph."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self.get_color()
        pen = QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        
        # Define path for thumbs-up
        # Simplified geometric outline
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(w * 0.2, h * 0.8)
        path.lineTo(w * 0.2, h * 0.4)
        path.lineTo(w * 0.4, h * 0.4)
        path.lineTo(w * 0.45, h * 0.15)
        path.lineTo(w * 0.55, h * 0.15)
        path.lineTo(w * 0.5, h * 0.4)
        path.lineTo(w * 0.85, h * 0.45)
        path.lineTo(w * 0.8, h * 0.75)
        path.lineTo(w * 0.4, h * 0.8)
        path.closeSubpath()
        
        painter.drawPath(path)
        # Cuff line
        painter.drawLine(int(w * 0.2), int(h * 0.4), int(w * 0.2), int(h * 0.8))


class ThumbsDownIcon(BaseSymbol):
    """Draws a clean vector thumbs-down glyph."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self.get_color()
        pen = QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(w * 0.2, h * 0.2)
        path.lineTo(w * 0.2, h * 0.6)
        path.lineTo(w * 0.4, h * 0.6)
        path.lineTo(w * 0.45, h * 0.85)
        path.lineTo(w * 0.55, h * 0.85)
        path.lineTo(w * 0.5, h * 0.6)
        path.lineTo(w * 0.85, h * 0.55)
        path.lineTo(w * 0.8, h * 0.25)
        path.lineTo(w * 0.4, h * 0.2)
        path.closeSubpath()
        
        painter.drawPath(path)
        painter.drawLine(int(w * 0.2), int(h * 0.6), int(w * 0.2), int(h * 0.2))


class DocIcon(BaseSymbol):
    """Draws a document outline sheet with a clean folded top corner."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(self.get_color(), 1.2)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        
        # Outline coordinates with folded corner
        # Fold starts at (0.7w, 0.15h) and goes to (0.85w, 0.3h)
        p1 = (w * 0.15, h * 0.1)
        p2 = (w * 0.65, h * 0.1)
        p3 = (w * 0.85, h * 0.3)
        p4 = (w * 0.85, h * 0.9)
        p5 = (w * 0.15, h * 0.9)
        
        painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
        painter.drawLine(int(p2[0]), int(p2[1]), int(p3[0]), int(p3[1]))
        painter.drawLine(int(p3[0]), int(p3[1]), int(p4[0]), int(p4[1]))
        painter.drawLine(int(p4[0]), int(p4[1]), int(p5[0]), int(p5[1]))
        painter.drawLine(int(p5[0]), int(p5[1]), int(p1[0]), int(p1[1]))
        
        # Draw folding line
        fold_corner = (w * 0.65, h * 0.3)
        painter.drawLine(int(p2[0]), int(p2[1]), int(fold_corner[0]), int(fold_corner[1]))
        painter.drawLine(int(p3[0]), int(p3[1]), int(fold_corner[0]), int(fold_corner[1]))


class CheckIcon(BaseSymbol):
    """Draws a vector checkmark path."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(self.get_color(), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        
        # Draw checkmark path
        painter.drawLine(int(w * 0.25), int(h * 0.55), int(w * 0.45), int(h * 0.75))
        painter.drawLine(int(w * 0.45), int(h * 0.75), int(w * 0.8), int(h * 0.3))


class CrossIcon(BaseSymbol):
    """Draws a vector cancel cross."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(self.get_color(), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        
        # Draw cross lines
        painter.drawLine(int(w * 0.25), int(h * 0.25), int(w * 0.75), int(h * 0.75))
        painter.drawLine(int(w * 0.75), int(h * 0.25), int(w * 0.25), int(h * 0.75))


class GearIcon(BaseSymbol):
    """Draws a clean, futuristic gear/settings icon."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self.get_color()
        pen = QPen(color, 1.5, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        r_outer = w * 0.25
        r_inner = w * 0.12
        
        # Draw central circle
        painter.drawEllipse(int(cx - r_outer), int(cy - r_outer), int(r_outer * 2), int(r_outer * 2))
        painter.drawEllipse(int(cx - r_inner), int(cy - r_inner), int(r_inner * 2), int(r_inner * 2))
        
        # Draw 8 teeth
        import math
        for i in range(8):
            angle = i * math.pi / 4.0
            x1 = cx + r_outer * math.cos(angle)
            y1 = cy + r_outer * math.sin(angle)
            x2 = cx + (r_outer + w * 0.08) * math.cos(angle)
            y2 = cy + (r_outer + h * 0.08) * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))


class IconBtn(QPushButton):
    """A QPushButton that hosts a theme-aware custom symbolic icon."""

    def __init__(self, icon_widget_class, state, color_role="accent", tooltip="", size=28, parent=None):
        """Create a fixed-size icon button from a BaseSymbol subclass."""
        super().__init__(parent)
        self.setObjectName("btn-ghost")
        self.setFixedSize(size, size)
        self.setToolTip(tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_widget = icon_widget_class(state, color_role=color_role, size=int(size * 0.58))
        self.icon_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon_widget)
        
    def update_style(self):
        """Repaint the hosted icon after a theme/state change."""
        self.icon_widget.update()
