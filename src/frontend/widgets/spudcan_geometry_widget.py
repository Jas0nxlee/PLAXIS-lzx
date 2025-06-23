"""
Widget for inputting Spudcan Geometry parameters.
PRD Ref: Task 6.1 (Spudcan Geometry Input Section)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QFrame,QSizePolicy
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Optional

# Assuming backend.models.SpudcanGeometry will be passed for data interaction
# We'll import it when type hinting in methods, or define a local placeholder if needed for design.
# from ...backend.models import SpudcanGeometry # Path for actual import later

class SpudcanGeometryWidget(QWidget):
    """
    A widget for users to input spudcan geometry details.
    """
    # Signal emitted when any data in this widget changes
    data_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0) # Use parent's margins

        # Form layout for dimensional inputs
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow) # Fields expand

        # --- Spudcan Dimensional Inputs (Task 6.1.1) ---
        self.diameter_spinbox = QDoubleSpinBox()
        self.diameter_spinbox.setSuffix(" m") # Example unit
        self.diameter_spinbox.setDecimals(3)
        self.diameter_spinbox.setRange(0.1, 100.0) # Example range
        self.diameter_spinbox.setValue(5.0) # Example default
        self.diameter_spinbox.valueChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Spudcan Diameter:"), self.diameter_spinbox)

        self.cone_angle_spinbox = QDoubleSpinBox()
        self.cone_angle_spinbox.setSuffix(" °") # Degrees
        self.cone_angle_spinbox.setDecimals(1)
        self.cone_angle_spinbox.setRange(0.0, 180.0) # Example range for angle
        self.cone_angle_spinbox.setValue(30.0) # Example default
        self.cone_angle_spinbox.valueChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Cone Angle:"), self.cone_angle_spinbox)

        # TODO: Add other dimensional inputs as identified from PRD or detailed design

        self.main_layout.addLayout(form_layout)

        # --- Spudcan Type Selection (Task 6.1.2) ---
        self.type_combobox = QComboBox()
        self.type_combobox.addItems(["Conical", "Flat", "Custom (Placeholder)"]) # Example types
        self.type_combobox.currentIndexChanged.connect(self.on_data_changed)
        # Add to form_layout or a new layout as preferred
        form_layout.addRow(QLabel("Spudcan Type:"), self.type_combobox)


        # --- Spudcan Schematic Display Placeholder (Task 6.1.3) ---
        self.schematic_placeholder = QFrame()
        self.schematic_placeholder.setFrameShape(QFrame.Shape.StyledPanel)
        self.schematic_placeholder.setFrameShadow(QFrame.Shadow.Sunken)
        schematic_layout = QVBoxLayout(self.schematic_placeholder)
        schematic_label = QLabel("Spudcan Schematic Placeholder")
        schematic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        schematic_layout.addWidget(schematic_label)
        self.schematic_placeholder.setMinimumHeight(150) # Ensure it's visible
        self.schematic_placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.main_layout.addWidget(self.schematic_placeholder)
        self.main_layout.addStretch() # Pushes elements up if space allows

        print("SpudcanGeometryWidget initialized.")

    def on_data_changed(self):
        """Emits the data_changed signal."""
        self.data_changed.emit()
        print("SpudcanGeometryWidget: Data changed.")

    def load_data(self, geometry_data) -> None: # Type hint SpudcanGeometry later
        """
        Populates the UI fields from a SpudcanGeometry data object.
        """
        print(f"SpudcanGeometryWidget: Loading data - {geometry_data}")
        if geometry_data:
            self.diameter_spinbox.setValue(geometry_data.diameter or 0.0)
            self.cone_angle_spinbox.setValue(geometry_data.height_cone_angle or 0.0) # Assuming height_cone_angle is cone angle

            # For QComboBox, find the index of the text.
            # This needs robust handling if geometry_data.spudcan_type might not be in items.
            # type_to_select = getattr(geometry_data, 'spudcan_type', "Conical") # Example default
            # index = self.type_combobox.findText(type_to_select)
            # if index >= 0:
            #    self.type_combobox.setCurrentIndex(index)
            # else:
            #    self.type_combobox.setCurrentIndex(0) # Default to first item if not found
            print("SpudcanGeometryWidget: Data loaded into UI fields (conceptual for type).")
        else:
            # Reset to defaults if no data provided
            self.diameter_spinbox.setValue(5.0)
            self.cone_angle_spinbox.setValue(30.0)
            self.type_combobox.setCurrentIndex(0)
            print("SpudcanGeometryWidget: No data provided, reset to defaults.")


    def gather_data(self): # Returns SpudcanGeometry later
        """
        Collects data from UI fields and returns a SpudcanGeometry data object.
        This method will create a new SpudcanGeometry object from backend.models.
        For now, it returns a dictionary as a placeholder until models are fully integrated.
        """
        # from ...backend.models import SpudcanGeometry # Import when ready
        # data = SpudcanGeometry() # Create instance from backend model
        # data.diameter = self.diameter_spinbox.value()
        # data.height_cone_angle = self.cone_angle_spinbox.value() # Store as cone angle
        # data.spudcan_type = self.type_combobox.currentText()

        # Placeholder until backend.models.SpudcanGeometry is used:
        data = {
            "diameter": self.diameter_spinbox.value(),
            "height_cone_angle": self.cone_angle_spinbox.value(), # Representing cone angle
            "spudcan_type": self.type_combobox.currentText()
        }
        print(f"SpudcanGeometryWidget: Gathered data - {data}")
        return data


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    # from ...backend.models import SpudcanGeometry as BackendSpudcanGeometry # For testing load/gather

    app = QApplication(sys.argv)

    # Dummy data for testing load_data (if BackendSpudcanGeometry was available)
    # class MockSpudcanGeometry: # Mocking the backend model for standalone test
    #     def __init__(self, diameter=None, height_cone_angle=None, spudcan_type=None):
    #         self.diameter = diameter
    #         self.height_cone_angle = height_cone_angle
    #         self.spudcan_type = spudcan_type
    #     def __str__(self):
    #         return f"MockSpudcan(D:{self.diameter}, A:{self.height_cone_angle}, T:{self.spudcan_type})"

    # test_data_real = BackendSpudcanGeometry(diameter=7.5, height_cone_angle=45.0)
    # test_data_mock = MockSpudcanGeometry(diameter=7.5, height_cone_angle=45.0, spudcan_type="Conical")


    widget = SpudcanGeometryWidget()

    # Test load_data (conceptual, as SpudcanGeometry from backend is not directly used here yet)
    # print("\nTesting load_data:")
    # widget.load_data(test_data_mock) # Pass the mock object

    # Test gather_data
    print("\nTesting gather_data:")
    gathered = widget.gather_data()
    print(f"Gathered data from UI: {gathered}")
    assert gathered["diameter"] == 5.0 # Initial default value

    # Simulate user changing a value
    print("\nSimulating user changing diameter to 8.0:")
    widget.diameter_spinbox.setValue(8.0)
    gathered_after_change = widget.gather_data()
    print(f"Gathered data after change: {gathered_after_change}")
    assert gathered_after_change["diameter"] == 8.0

    widget.setWindowTitle("Spudcan Geometry Widget Test")
    widget.resize(400, 300)
    widget.show()

    sys.exit(app.exec())
