"""
Custom widget to display a 2D schematic of soil stratigraphy.
"""
import logging
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF

logger = logging.getLogger(__name__)

# Define a simple structure for layer data passed to this widget
# to decouple it from the main backend models directly for rendering.
class LayerDisplayData:
    def __init__(self, name: str, thickness: float, material_display_name: str, original_material_id: Optional[str] = None):
        self.name = name
        self.thickness = thickness
        self.material_display_name = material_display_name # Name or ID to display
        self.original_material_id = original_material_id # Actual ID for color mapping

class SoilStratigraphySchematicWidget(QWidget):
    """
    A widget that draws a 2D schematic of soil layers and water table.
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layers_data: List[LayerDisplayData] = []
        self._water_table_depth: Optional[float] = None # Depth below surface (positive down)
        self._total_thickness: float = 0.0

        self.setMinimumHeight(200)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Simple color cycle for layers if no specific mapping is done
        self._layer_colors = [
            QColor(210, 180, 140),  # Tan
            QColor(188, 143, 143),  # RosyBrown
            QColor(245, 222, 179),  # Wheat
            QColor(211, 211, 211),  # LightGray
            QColor(176, 196, 222),  # LightSteelBlue
            QColor(240, 230, 140),  # Khaki
        ]
        self._material_color_map: Dict[str, QColor] = {}


    def update_data(self, layers_data: List[Dict[str, Any]], water_table_depth: Optional[float]):
        """
        Updates the layer and water table data for the schematic.
        Triggers a repaint.

        Args:
            layers_data: A list of dictionaries, each with "name", "thickness",
                         "material_display_name", and optionally "original_material_id".
            water_table_depth: Depth of the water table below the surface (positive downwards).
                               If None, no water table is drawn.
        """
        self._layers_data = []
        self._total_thickness = 0

        current_color_idx = 0
        unique_material_ids = set()

        for ld_dict in layers_data:
            thickness = ld_dict.get("thickness", 0.0)
            if thickness > 0:
                layer = LayerDisplayData(
                    name=ld_dict.get("name", "Unnamed Layer"),
                    thickness=thickness,
                    material_display_name=ld_dict.get("material_display_name", "N/A"),
                    original_material_id=ld_dict.get("original_material_id")
                )
                self._layers_data.append(layer)
                self._total_thickness += thickness
                if layer.original_material_id:
                    unique_material_ids.add(layer.original_material_id)

        # Assign colors to materials if not already assigned
        for mat_id in unique_material_ids:
            if mat_id not in self._material_color_map:
                self._material_color_map[mat_id] = self._layer_colors[current_color_idx % len(self._layer_colors)]
                current_color_idx +=1

        self._water_table_depth = water_table_depth
        logger.debug(f"Schematic data updated: {len(self._layers_data)} layers, WT depth: {self._water_table_depth}, Total thickness: {self._total_thickness}")
        self.update()


    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        padding_top_bottom = 20
        padding_left_right = 25 # Increased for text
        text_area_width = 80 # Reserved width for text labels on the side

        drawable_width = width - 2 * padding_left_right - text_area_width
        drawable_height = height - 2 * padding_top_bottom

        if drawable_width <= 20 or drawable_height <= 0 or not self._layers_data or self._total_thickness <= 0:
            painter.setPen(QColor(Qt.GlobalColor.gray))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Soil Data or Not Enough Space")
            return

        # Scale factor for layer thickness
        scale_y = drawable_height / self._total_thickness

        current_y = float(padding_top_bottom)
        layer_rect_x = float(padding_left_right)
        layer_rect_width = float(drawable_width)

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        fm = QFontMetrics(font)

        for i, layer in enumerate(self._layers_data):
            scaled_thickness = layer.thickness * scale_y

            # Layer rectangle
            layer_rect = QRectF(layer_rect_x, current_y, layer_rect_width, scaled_thickness)

            # Determine color
            color = self._layer_colors[i % len(self._layer_colors)] # Default cycle
            if layer.original_material_id and layer.original_material_id in self._material_color_map:
                color = self._material_color_map[layer.original_material_id]

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(layer_rect)

            # Layer text (name, material, thickness) - try to fit inside or beside
            text_padding = 3
            text_x = layer_rect_x + layer_rect_width + text_padding * 2

            name_text = f"{layer.name}"
            mat_text = f"({layer.material_display_name})"
            thick_text = f"T: {layer.thickness:.2f} m"

            text_y_start = current_y + fm.ascent() + text_padding

            if text_y_start + 2 * (fm.height()) < current_y + scaled_thickness : # Check if text fits
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(QPointF(text_x, text_y_start), name_text)
                painter.drawText(QPointF(text_x, text_y_start + fm.height()), mat_text)
                painter.drawText(QPointF(text_x, text_y_start + 2 * fm.height()), thick_text)
            else: # If too small, just draw material name centered in rect
                painter.setPen(Qt.GlobalColor.black)
                center_text_rect = QRectF(layer_rect_x, current_y, layer_rect_width, scaled_thickness)
                painter.drawText(center_text_rect, Qt.AlignmentFlag.AlignCenter, layer.material_display_name[:10])


            current_y += scaled_thickness

        # Draw Water Table line
        if self._water_table_depth is not None and self._water_table_depth >= 0:
            water_table_y_abs = self._water_table_depth * scale_y
            water_table_draw_y = padding_top_bottom + water_table_y_abs

            if water_table_draw_y <= height - padding_top_bottom : # Ensure it's within drawable area
                pen = QPen(QColor(Qt.GlobalColor.blue), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                # Draw line slightly wider than layers for visibility
                line_x_start = layer_rect_x - 5
                line_x_end = layer_rect_x + layer_rect_width + 5
                painter.drawLine(QPointF(line_x_start, water_table_draw_y), QPointF(line_x_end, water_table_draw_y))

                # Draw water table symbol (triangle)
                triangle_size = 6
                triangle = QPolygonF()
                triangle.append(QPointF(line_x_start - triangle_size/2, water_table_draw_y))
                triangle.append(QPointF(line_x_start + triangle_size/2, water_table_draw_y))
                triangle.append(QPointF(line_x_start, water_table_draw_y - triangle_size)) # Pointing up

                painter.setBrush(QBrush(Qt.GlobalColor.blue))
                painter.setPen(QPen(Qt.GlobalColor.blue, 1))
                painter.drawPolygon(triangle)

                # Water table depth text
                wt_text = f"WT @ {self._water_table_depth:.2f} m"
                painter.setPen(QColor(Qt.GlobalColor.blue))
                painter.drawText(QPointF(line_x_end + text_padding, water_table_draw_y + fm.descent()), wt_text)


        painter.end()

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QPushButton

    app = QApplication(sys.argv)
    main_window = QWidget()
    layout = QVBoxLayout(main_window)

    schematic = SoilStratigraphySchematicWidget()

    # Sample data
    sample_layers_1 = [
        {"name": "Top Clay", "thickness": 3.0, "material_display_name": "Soft Clay", "original_material_id": "ClayMat01"},
        {"name": "Sand Layer", "thickness": 5.0, "material_display_name": "Medium Sand", "original_material_id": "SandMat02"},
        {"name": "Stiff Clay", "thickness": 2.5, "material_display_name": "Stiff Clay", "original_material_id": "ClayMat03"},
    ]
    sample_wt_1 = 2.0

    sample_layers_2 = [
        {"name": "Peat", "thickness": 1.0, "material_display_name": "Peat", "original_material_id": "Peat01"},
        {"name": "Silty Sand", "thickness": 4.0, "material_display_name": "Silty Sand", "original_material_id": "SiltySand01"},
        {"name": "Gravel", "thickness": 3.0, "material_display_name": "Gravel", "original_material_id": "Gravel01"},
        {"name": "Bedrock", "thickness": 2.0, "material_display_name": "Rock", "original_material_id": "Rock01"},
    ]
    sample_wt_2 = 0.5


    schematic.update_data(sample_layers_1, sample_wt_1) # Initial data

    def toggle_data():
        if schematic._water_table_depth == sample_wt_1:
            schematic.update_data(sample_layers_2, sample_wt_2)
        else:
            schematic.update_data(sample_layers_1, sample_wt_1)

    button = QPushButton("Toggle Data")
    button.clicked.connect(toggle_data)

    layout.addWidget(schematic)
    layout.addWidget(button)

    main_window.setWindowTitle("Soil Stratigraphy Schematic Test")
    main_window.resize(350, 500)
    main_window.show()
    sys.exit(app.exec())
