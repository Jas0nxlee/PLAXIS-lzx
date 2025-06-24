"""
Widget for inputting Spudcan Geometry parameters.
PRD Ref: Task 6.1 (Spudcan Geometry Input Section)
"""

"""
Widget for inputting Spudcan Geometry parameters.
PRD Ref: Task 6.1 (Spudcan Geometry Input Section)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QSizePolicy # Removed QFrame, Qt
)
from PySide6.QtCore import Signal, Slot # Removed Qt
from typing import Optional

# Import the new schematic widget
from .spudcan_schematic_widget import SpudcanSchematicWidget
# from ...backend.models import SpudcanGeometry # Path for actual import later

class SpudcanGeometryWidget(QWidget):
    """
    A widget for users to input spudcan geometry details.
    Includes a dynamic schematic display.
    """
    data_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.diameter_spinbox = QDoubleSpinBox()
        self.diameter_spinbox.setSuffix(" m")
        self.diameter_spinbox.setDecimals(3)
        self.diameter_spinbox.setRange(0.1, 100.0)
        self.diameter_spinbox.setValue(6.0) # Default value
        self.diameter_spinbox.valueChanged.connect(self._update_schematic_and_emit_data_changed)
        form_layout.addRow(QLabel("Spudcan Diameter:"), self.diameter_spinbox)

        self.cone_angle_spinbox = QDoubleSpinBox()
        self.cone_angle_spinbox.setSuffix(" °")
        self.cone_angle_spinbox.setDecimals(1)
        self.cone_angle_spinbox.setRange(1.0, 89.0) # Cone angle practically > 0 and < 90
        self.cone_angle_spinbox.setValue(30.0)
        self.cone_angle_spinbox.valueChanged.connect(self._update_schematic_and_emit_data_changed)
        form_layout.addRow(QLabel("Cone Angle (half-apex):"), self.cone_angle_spinbox)

        self.main_layout.addLayout(form_layout)

        self.type_combobox = QComboBox()
        self.type_combobox.addItems(["Conical", "Flat (Not Implemented)", "Custom (Not Implemented)"])
        self.type_combobox.currentIndexChanged.connect(self.on_data_changed) # Keep simple signal for now
        form_layout.addRow(QLabel("Spudcan Type:"), self.type_combobox)

        # --- Spudcan Schematic Display (Task 6.1.3) ---
        self.schematic_widget = SpudcanSchematicWidget(self)
        self.schematic_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Let it expand

        self.main_layout.addWidget(self.schematic_widget, 1) # Add with stretch factor
        # self.main_layout.addStretch() # Remove if schematic should take available space

        # Initial schematic update
        self._update_schematic_display()
        print("SpudcanGeometryWidget initialized with schematic.")

    @Slot()
    def _update_schematic_and_emit_data_changed(self):
        """Updates the schematic and then emits the data_changed signal."""
        self._update_schematic_display()
        self.on_data_changed()

    def _update_schematic_display(self):
        """Updates the schematic widget with current dimensions."""
        diameter = self.diameter_spinbox.value()
        cone_angle = self.cone_angle_spinbox.value()
        if self.schematic_widget:
            self.schematic_widget.update_dimensions(diameter, cone_angle)
        print(f"SpudcanGeometryWidget: Schematic updated for D={diameter}, Angle={cone_angle}")

    def on_data_changed(self):
        """Emits the data_changed signal."""
        self.data_changed.emit()
        print("SpudcanGeometryWidget: Data changed.")

    def load_data(self, geometry_data) -> None: # Type hint SpudcanGeometry later
        print(f"SpudcanGeometryWidget: Loading data - {geometry_data}")
        # Block signals while setting values to avoid multiple updates
        self.diameter_spinbox.blockSignals(True)
        self.cone_angle_spinbox.blockSignals(True)
        self.type_combobox.blockSignals(True)

        if geometry_data:
            self.diameter_spinbox.setValue(getattr(geometry_data, 'diameter', 6.0))
            self.cone_angle_spinbox.setValue(getattr(geometry_data, 'height_cone_angle', 30.0))

            type_to_select = getattr(geometry_data, 'spudcan_type', "Conical")
            index = self.type_combobox.findText(type_to_select)
            if index >= 0:
               self.type_combobox.setCurrentIndex(index)
            else:
               self.type_combobox.setCurrentIndex(0) # Default to first item
            print("SpudcanGeometryWidget: Data loaded into UI fields.")
        else:
            self.diameter_spinbox.setValue(6.0)
            self.cone_angle_spinbox.setValue(30.0)
            self.type_combobox.setCurrentIndex(0)
            print("SpudcanGeometryWidget: No data provided, reset to defaults.")

        self.diameter_spinbox.blockSignals(False)
        self.cone_angle_spinbox.blockSignals(False)
        self.type_combobox.blockSignals(False)

        self._update_schematic_display() # Update schematic after loading data
        self.data_changed.emit() # Emit signal once after all updates


    def gather_data(self):
        # This should ideally return a backend.models.SpudcanGeometry instance
        data = {
            "diameter": self.diameter_spinbox.value(),
            "height_cone_angle": self.cone_angle_spinbox.value(),
            "spudcan_type": self.type_combobox.currentText()
        }
        print(f"SpudcanGeometryWidget: Gathered data - {data}")
        return data


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    # For standalone testing, create a mock of the backend model if not accessible
    class MockSpudcanGeometryData:
        def __init__(self, diameter=6.0, height_cone_angle=30.0, spudcan_type="Conical"):
            self.diameter = diameter
            self.height_cone_angle = height_cone_angle # Corresponds to cone_angle_spinbox
            self.spudcan_type = spudcan_type
        def __str__(self):
            return f"MockSpudcanData(D:{self.diameter}, Angle:{self.height_cone_angle}, T:{self.spudcan_type})"


    app = QApplication(sys.argv)
    widget = SpudcanGeometryWidget()
    widget.setWindowTitle("Spudcan Geometry Widget Test with Schematic")
    widget.resize(400, 500) # Increased height for schematic
    widget.show()

    # Test load_data
    print("\nTesting load_data:")
    test_data = MockSpudcanGeometryData(diameter=7.5, height_cone_angle=45.0, spudcan_type="Conical")
    widget.load_data(test_data)
    gathered_after_load = widget.gather_data()
    print(f"Gathered data after load: {gathered_after_load}")
    assert gathered_after_load["diameter"] == 7.5
    assert gathered_after_load["height_cone_angle"] == 45.0

    # Simulate user changing a value
    print("\nSimulating user changing diameter to 8.0 via UI:")
    widget.diameter_spinbox.setValue(8.0) # This will trigger _update_schematic_and_emit_data_changed

    sys.exit(app.exec())
