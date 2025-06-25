"""
Widget for inputting Spudcan Geometry parameters.

This widget provides UI elements for defining the spudcan's dimensions,
such as diameter and cone angle. It also includes a schematic display
that updates dynamically based on the input values. Input validation is
performed on the fields to ensure data integrity.

PRD Ref: Task 6.1 (Spudcan Geometry Input Section)
         Task 9.4 (Input Validation Feedback)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QSizePolicy
)
from PySide6.QtCore import Signal, Slot
from typing import Optional, Dict, Any

from .spudcan_schematic_widget import SpudcanSchematicWidget
from ...backend.validation import validate_numerical_range, ValidationError
from ...backend.models import SpudcanGeometry

logger = logging.getLogger(__name__)

VALID_STYLE = ""
INVALID_STYLE = "border: 1px solid red; background-color: #fff0f0;"

class SpudcanGeometryWidget(QWidget):
    """
    A widget for users to input spudcan geometry details.

    Signals:
        data_changed: Emitted when any input field's value changes.
        validation_status_changed (bool): Emitted when the overall validation status
                                          of the widget changes. True if all inputs valid.
    """
    data_changed = Signal()
    validation_status_changed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initializes the SpudcanGeometryWidget.
        Sets up UI elements for diameter, cone angle, type, and the schematic display.
        Connects signals for input changes and validation.
        """
        super().__init__(parent)
        self._is_valid = True # Internal state for overall widget validity

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- Diameter Input ---
        self.diameter_spinbox = QDoubleSpinBox()
        self.diameter_spinbox.setSuffix(" m")
        self.diameter_spinbox.setDecimals(3)
        self.diameter_spinbox.setRange(0.001, 200.0)
        self.diameter_spinbox.setValue(6.0)
        self.diameter_spinbox.valueChanged.connect(self._on_diameter_changed)
        self.diameter_spinbox.editingFinished.connect(self._on_diameter_editing_finished)
        form_layout.addRow(QLabel("Spudcan Diameter:"), self.diameter_spinbox)

        # --- Cone Angle Input ---
        self.cone_angle_spinbox = QDoubleSpinBox()
        self.cone_angle_spinbox.setSuffix(" °")
        self.cone_angle_spinbox.setDecimals(1)
        self.cone_angle_spinbox.setRange(1.0, 89.0)
        self.cone_angle_spinbox.setValue(30.0)
        self.cone_angle_spinbox.valueChanged.connect(self._on_cone_angle_changed)
        self.cone_angle_spinbox.editingFinished.connect(self._on_cone_angle_editing_finished)
        form_layout.addRow(QLabel("Cone Angle (half-apex):"), self.cone_angle_spinbox)

        # --- Spudcan Type Selection ---
        self.type_combobox = QComboBox()
        self.type_combobox.addItems(["Conical", "Flat (Not Implemented)", "Custom (Not Implemented)"])
        self.type_combobox.currentIndexChanged.connect(self.data_changed.emit) # Simpler signal for now
        form_layout.addRow(QLabel("Spudcan Type:"), self.type_combobox)

        self.main_layout.addLayout(form_layout)

        # --- Spudcan Schematic Display ---
        self.schematic_widget = SpudcanSchematicWidget(self)
        self.schematic_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.schematic_widget, 1) # Give stretch factor

        self._validate_all_inputs()
        self._update_schematic_display()
        logger.info("SpudcanGeometryWidget initialized.")

    @Slot()
    def _on_diameter_changed(self):
        """Handles changes to the diameter spinbox value."""
        self._validate_diameter()
        self._update_schematic_display()
        self.data_changed.emit()

    @Slot()
    def _on_diameter_editing_finished(self):
        """Ensures final validation when diameter editing is finished."""
        self._validate_diameter()
        self._update_schematic_display()

    @Slot()
    def _on_cone_angle_changed(self):
        """Handles changes to the cone angle spinbox value."""
        self._validate_cone_angle()
        self._update_schematic_display()
        self.data_changed.emit()

    @Slot()
    def _on_cone_angle_editing_finished(self):
        """Ensures final validation when cone angle editing is finished."""
        self._validate_cone_angle()
        self._update_schematic_display()

    def _validate_diameter(self) -> bool:
        """Validates the spudcan diameter input field."""
        is_field_valid = True
        try:
            value = self.diameter_spinbox.value()
            validate_numerical_range(value, 0.001, 200.0, "Spudcan Diameter")
            self.diameter_spinbox.setStyleSheet(VALID_STYLE)
            self.diameter_spinbox.setToolTip("")
        except ValidationError as e:
            self.diameter_spinbox.setStyleSheet(INVALID_STYLE)
            self.diameter_spinbox.setToolTip(str(e))
            is_field_valid = False

        self._check_overall_validation_status()
        return is_field_valid

    def _validate_cone_angle(self) -> bool:
        """Validates the cone angle input field."""
        is_field_valid = True
        try:
            value = self.cone_angle_spinbox.value()
            validate_numerical_range(value, 1.0, 89.0, "Cone Angle")
            self.cone_angle_spinbox.setStyleSheet(VALID_STYLE)
            self.cone_angle_spinbox.setToolTip("")
        except ValidationError as e:
            self.cone_angle_spinbox.setStyleSheet(INVALID_STYLE)
            self.cone_angle_spinbox.setToolTip(str(e))
            is_field_valid = False

        self._check_overall_validation_status()
        return is_field_valid

    def _validate_all_inputs(self) -> bool:
        """
        Runs all individual validation checks and updates the overall validation status.
        Returns:
            bool: True if all inputs are currently valid, False otherwise.
        """
        # Call individual validation methods which will also update styles and tooltips
        dia_valid = self._validate_diameter()
        angle_valid = self._validate_cone_angle()
        # Note: _check_overall_validation_status is called by each _validate_... method
        # so self._is_valid will be up-to-date by the end of these calls.
        return self._is_valid

    def _check_overall_validation_status(self):
        """
        Checks if all fields are currently valid and emits `validation_status_changed` if the overall status changes.
        """
        is_dia_valid = self.diameter_spinbox.styleSheet() != INVALID_STYLE
        is_angle_valid = self.cone_angle_spinbox.styleSheet() != INVALID_STYLE

        current_overall_status = is_dia_valid and is_angle_valid

        if self._is_valid != current_overall_status:
            self._is_valid = current_overall_status
            self.validation_status_changed.emit(self._is_valid)
            logger.debug(f"SpudcanGeometryWidget overall validation status changed to: {self._is_valid}")

    def _update_schematic_display(self):
        """Updates the schematic widget with current dimensions, using 0 for invalid inputs."""
        diameter = self.diameter_spinbox.value() if self.diameter_spinbox.styleSheet() != INVALID_STYLE else 0
        cone_angle = self.cone_angle_spinbox.value() if self.cone_angle_spinbox.styleSheet() != INVALID_STYLE else 0
        if self.schematic_widget:
            self.schematic_widget.update_dimensions(diameter, cone_angle)

    def load_data(self, geometry_data: Optional[SpudcanGeometry]) -> None:
        """
        Populates the UI fields from a SpudcanGeometry data object.
        Args:
            geometry_data: The SpudcanGeometry object containing data to load.
                           If None, fields are reset to default values.
        """
        logger.debug(f"SpudcanGeometryWidget loading data: {geometry_data}")

        self.diameter_spinbox.blockSignals(True)
        self.cone_angle_spinbox.blockSignals(True)
        self.type_combobox.blockSignals(True)

        if geometry_data:
            self.diameter_spinbox.setValue(geometry_data.diameter if geometry_data.diameter is not None else 6.0)
            self.cone_angle_spinbox.setValue(geometry_data.height_cone_angle if geometry_data.height_cone_angle is not None else 30.0)
            # spudcan_type is not currently part of SpudcanGeometry model
            # type_to_select = getattr(geometry_data, 'spudcan_type', "Conical")
            # index = self.type_combobox.findText(type_to_select) ...
        else:
            self.diameter_spinbox.setValue(6.0)
            self.cone_angle_spinbox.setValue(30.0)
            self.type_combobox.setCurrentIndex(0)

        self.diameter_spinbox.blockSignals(False)
        self.cone_angle_spinbox.blockSignals(False)
        self.type_combobox.blockSignals(False)

        self._validate_all_inputs()
        self._update_schematic_display()
        self.data_changed.emit()

    def gather_data(self) -> Dict[str, Any]:
        """
        Collects data from UI fields into a dictionary.
        Returns None for fields that are currently invalid.
        Returns:
            Dict[str, Any]: A dictionary containing the current spudcan geometry data.
        """
        return {
            "diameter": self.diameter_spinbox.value() if self.diameter_spinbox.styleSheet() != INVALID_STYLE else None,
            "height_cone_angle": self.cone_angle_spinbox.value() if self.cone_angle_spinbox.styleSheet() != INVALID_STYLE else None,
            "spudcan_type": self.type_combobox.currentText()
        }

    def gather_data_to_model(self) -> Optional[SpudcanGeometry]:
        """
        Gathers data from UI fields and returns a SpudcanGeometry model instance.
        If inputs are currently invalid, this may return a model with None for those fields,
        or could return None entirely if strict validation on gather is required.
        Returns:
            Optional[SpudcanGeometry]: A SpudcanGeometry object, or None if critical data is invalid.
        """
        self._validate_all_inputs() # Ensure validation status is current

        if not self._is_valid:
            logger.warning("Attempting to gather SpudcanGeometry model data when inputs are invalid.")
            # Return a model with invalid fields as None, as per gather_data behavior
            raw_data = self.gather_data()
            return SpudcanGeometry(
                diameter=raw_data["diameter"], # Will be None if invalid
                height_cone_angle=raw_data["height_cone_angle"] # Will be None if invalid
            )

        return SpudcanGeometry(
            diameter=self.diameter_spinbox.value(),
            height_cone_angle=self.cone_angle_spinbox.value()
            # spudcan_type could be added to model if needed
        )

    def is_valid(self) -> bool:
        """
        Returns the current overall validation status of the widget by re-evaluating all fields.
        Returns:
            bool: True if all inputs are valid, False otherwise.
        """
        return self._validate_all_inputs()

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    app = QApplication(sys.argv)
    widget = SpudcanGeometryWidget()
    widget.setWindowTitle("Spudcan Geometry Widget Test")
    widget.resize(400, 500)

    def on_status_change(is_valid_status):
        print(f"VALIDATION STATUS CHANGED: {is_valid_status}")
    widget.validation_status_changed.connect(on_status_change)

    widget.show()
    sys.exit(app.exec())
