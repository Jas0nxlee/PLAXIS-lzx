"""
Custom widget to display a 2D schematic of a spudcan.
"""
import math
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QPainter, QPen, QBrush, QPolygonF, QColor, QFont, QFontMetrics
from PySide6.QtCore import Qt, QPointF, Signal, Slot

class SpudcanSchematicWidget(QWidget):
    """
    A widget that draws a 2D schematic of a spudcan cone.
    It updates based on diameter and cone angle (to calculate height).
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._diameter: float = 0.0
        self._height: float = 0.0 # Calculated height
        self._cone_angle_deg: float = 0.0 # Store for display if needed

        self.setMinimumHeight(150)
        self.setMinimumWidth(200)
        # self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred) # Already in parent

    def update_dimensions(self, diameter: float, cone_angle_deg: float):
        """
        Updates the dimensions used for drawing the schematic.
        Triggers a repaint.

        Args:
            diameter: The diameter of the spudcan base.
            cone_angle_deg: The half-apex angle of the cone in degrees.
        """
        self._diameter = diameter
        self._cone_angle_deg = cone_angle_deg

        if self._diameter > 0 and 0 < self._cone_angle_deg < 90:
            radius = self._diameter / 2.0
            cone_angle_rad = math.radians(self._cone_angle_deg)
            self._height = radius / math.tan(cone_angle_rad)
        else:
            self._height = 0 # Invalid input, draw nothing or a placeholder

        self.update() # Trigger repaint

    def paintEvent(self, event):
        """
        Handles the paint event to draw the spudcan schematic.
        """
        super().paintEvent(event) # Important for QWidget subclasses

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        padding = 20  # Padding around the drawing

        # Clear background (optional, depends on stylesheet)
        # painter.fillRect(self.rect(), self.palette().color(self.backgroundRole()))

        if self._diameter <= 0 or self._height <= 0:
            # Draw placeholder text if dimensions are invalid
            painter.setPen(QColor(Qt.GlobalColor.gray))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Invalid Spudcan Dimensions")
            return

        # --- Drawing Parameters ---
        # Scale the spudcan to fit within the widget, maintaining aspect ratio
        drawable_width = width - 2 * padding
        drawable_height = height - 2 * padding

        if drawable_width <= 0 or drawable_height <= 0:
            return # Not enough space to draw

        # Determine scale factor
        # We want the drawing to fit, so scale by the limiting dimension
        scale_w = drawable_width / self._diameter
        scale_h = drawable_height / self._height
        scale = min(scale_w, scale_h) # Use the smaller scale to ensure fit

        if scale <= 0: return # Avoid division by zero or negative scale

        scaled_diameter = self._diameter * scale
        scaled_height = self._height * scale

        # Center the drawing
        offset_x = (width - scaled_diameter) / 2
        # Spudcan base (widest part) will be at the top of the drawing area
        # Tip will point downwards
        base_y = padding
        tip_y = base_y + scaled_height

        # --- Draw Cone (Triangle) ---
        # Points for the triangle (base left, base right, tip)
        p1 = QPointF(offset_x, base_y)  # Base left
        p2 = QPointF(offset_x + scaled_diameter, base_y)  # Base right
        p3 = QPointF(offset_x + scaled_diameter / 2, tip_y)  # Tip

        cone_polygon = QPolygonF([p1, p2, p3])

        painter.setPen(QPen(QColor(Qt.GlobalColor.black), 2))
        painter.setBrush(QBrush(QColor(Qt.GlobalColor.lightGray)))
        painter.drawPolygon(cone_polygon)

        # --- Draw Dimensions and Labels ---
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor(Qt.GlobalColor.darkGray))
        fm = QFontMetrics(font)

        # Diameter line and label
        dim_line_y_offset = -10 # Above the base
        dim_line_y = base_y + dim_line_y_offset
        if dim_line_y < padding / 2 : dim_line_y = base_y + 5 # ensure it's visible

        painter.drawLine(QPointF(p1.x(), dim_line_y), QPointF(p2.x(), dim_line_y))
        painter.drawLine(QPointF(p1.x(), dim_line_y - 3), QPointF(p1.x(), dim_line_y + 3)) # Tick left
        painter.drawLine(QPointF(p2.x(), dim_line_y - 3), QPointF(p2.x(), dim_line_y + 3)) # Tick right

        diameter_text = f"D: {self._diameter:.2f} m"
        text_width_d = fm.horizontalAdvance(diameter_text)
        painter.drawText(QPointF(offset_x + (scaled_diameter - text_width_d) / 2, dim_line_y - 3), diameter_text)

        # Height line and label
        dim_line_x_offset = -10 # To the left of the cone
        dim_line_x = offset_x + dim_line_x_offset
        if dim_line_x < padding / 2: dim_line_x = offset_x + scaled_diameter + 5 # Or to the right if no space left

        painter.drawLine(QPointF(dim_line_x, base_y), QPointF(dim_line_x, tip_y))
        painter.drawLine(QPointF(dim_line_x - 3, base_y), QPointF(dim_line_x + 3, base_y)) # Tick top
        painter.drawLine(QPointF(dim_line_x - 3, tip_y), QPointF(dim_line_x + 3, tip_y)) # Tick bottom

        height_text = f"H: {self._height:.2f} m"
        text_width_h = fm.horizontalAdvance(height_text)
        # For vertical text, it's a bit more complex to center along the line.
        # Simple placement:
        painter.drawText(QPointF(dim_line_x - text_width_h - 3, base_y + (scaled_height / 2) + (fm.ascent()/2) ), height_text)

        # Angle (optional, can get cluttered)
        # angle_text = f"Angle: {self._cone_angle_deg:.1f}°"
        # painter.drawText(QPointF(padding, height - padding / 2), angle_text)

        painter.end()

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QDoubleSpinBox, QFormLayout

    app = QApplication(sys.argv)
    main_window = QWidget()
    layout = QVBoxLayout(main_window)

    schematic_widget = SpudcanSchematicWidget()

    # Controls to test the schematic
    dia_input = QDoubleSpinBox()
    dia_input.setRange(0.1, 50)
    dia_input.setValue(6)
    dia_input.setSuffix(" m")

    angle_input = QDoubleSpinBox()
    angle_input.setRange(1, 89)
    angle_input.setValue(30)
    angle_input.setSuffix(" °")

    form = QFormLayout()
    form.addRow("Diameter:", dia_input)
    form.addRow("Cone Angle:", angle_input)

    layout.addLayout(form)
    layout.addWidget(schematic_widget)
    main_window.setWindowTitle("Spudcan Schematic Test")

    def update_schematic():
        schematic_widget.update_dimensions(dia_input.value(), angle_input.value())

    dia_input.valueChanged.connect(update_schematic)
    angle_input.valueChanged.connect(update_schematic)

    # Initial update
    update_schematic()

    main_window.resize(300, 400)
    main_window.show()
    sys.exit(app.exec())
