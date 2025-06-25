"""
Widget for inputting Loading Conditions parameters.

This widget allows the user to define the vertical pre-load on the spudcan,
the type of analysis control (penetration or load controlled), and the
target value for that control. It includes input validation for numerical fields.

PRD Ref: Task 6.3 (Loading Conditions Input Section)
         Task 9.4 (Input Validation Feedback)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QGroupBox
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Optional, Any, Dict

from ...backend.validation import validate_numerical_range, ValidationError
from ...backend.models import LoadingConditions

logger = logging.getLogger(__name__)

VALID_STYLE = ""
INVALID_STYLE = "border: 1px solid red; background-color: #fff0f0;"

class LoadingConditionsWidget(QWidget):
    """
    A widget for users to input loading conditions for the analysis.

    Signals:
        data_changed: Emitted when any input field's value changes.
        validation_status_changed (bool): Emitted when the overall validation status
                                          of the widget changes. True if all inputs valid.
    """
    data_changed = Signal()
    validation_status_changed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initializes the LoadingConditionsWidget.
        Sets up UI elements for preload, target type, and target value.
        Connects signals for input changes and validation.
        """
        super().__init__(parent)
        self._is_valid = True # Internal state for overall widget validity

        self.main_layout = QVBoxLayout(self)
        group_box = QGroupBox("Loading Conditions")
        self.main_layout.addWidget(group_box)

        form_layout = QFormLayout(group_box)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- Vertical Pre-load Input ---
        self.preload_spinbox = QDoubleSpinBox()
        self.preload_spinbox.setSuffix(" kN")
        self.preload_spinbox.setDecimals(2)
        self.preload_spinbox.setRange(0, 1e9) # Allow zero preload
        self.preload_spinbox.setValue(0.0)
        self.preload_spinbox.valueChanged.connect(self._on_preload_changed)
        self.preload_spinbox.editingFinished.connect(self._on_preload_editing_finished)
        form_layout.addRow(QLabel("Vertical Pre-load (Fz):"), self.preload_spinbox)

        # --- Target Type Selection ---
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["Penetration Control", "Load Control"])
        self.target_type_combo.currentTextChanged.connect(self.on_target_type_changed)
        form_layout.addRow(QLabel("Target Control Type:"), self.target_type_combo)

        # --- Target Penetration/Load Input ---
        self.target_value_spinbox = QDoubleSpinBox()
        self.target_value_spinbox.setDecimals(3)
        # Range is set dynamically by on_target_type_changed when control type changes
        self.target_value_spinbox.setValue(1.0)
        self.target_value_spinbox.valueChanged.connect(self._on_target_value_changed)
        self.target_value_spinbox.editingFinished.connect(self._on_target_value_editing_finished)
        self.target_value_label = QLabel("Target Penetration (uz):")
        form_layout.addRow(self.target_value_label, self.target_value_spinbox)

        self.on_target_type_changed(self.target_type_combo.currentText()) # Set initial suffix & validation range
        self._validate_all_inputs() # Perform initial validation
        logger.info("LoadingConditionsWidget initialized.")

    @Slot()
    def _on_preload_changed(self):
        """Handles changes to the preload spinbox value."""
        self._validate_preload()
        self.data_changed.emit()

    @Slot()
    def _on_preload_editing_finished(self):
        """Ensures final validation for preload when editing is finished."""
        self._validate_preload()

    @Slot()
    def _on_target_value_changed(self):
        """Handles changes to the target value spinbox."""
        self._validate_target_value()
        self.data_changed.emit()

    @Slot()
    def _on_target_value_editing_finished(self):
        """Ensures final validation for target value when editing is finished."""
        self._validate_target_value()

    @Slot(str)
    def on_target_type_changed(self, text: str):
        """
        Updates the label, suffix, and validation range for the target value
        spinbox based on the selected control type.
        """
        if text == "Penetration Control":
            self.target_value_label.setText("Target Penetration (uz):")
            self.target_value_spinbox.setSuffix(" m")
            self.target_value_spinbox.setRange(0.001, 200.0) # Max reasonable penetration
            self.target_value_spinbox.setDecimals(3)
        elif text == "Load Control":
            self.target_value_label.setText("Target Load (Fz):")
            self.target_value_spinbox.setSuffix(" kN")
            self.target_value_spinbox.setRange(0.1, 1e9) # Max reasonable load
            self.target_value_spinbox.setDecimals(2)
        self._validate_target_value() # Re-validate as range/suffix changes
        self.data_changed.emit() # Emit data changed as meaning/units of target_value changes

    def _validate_preload(self) -> bool:
        """Validates the vertical preload input field."""
        is_field_valid = True
        try:
            # Allow 0 for preload
            validate_numerical_range(self.preload_spinbox.value(), 0, 1e9, "Vertical Pre-load")
            self.preload_spinbox.setStyleSheet(VALID_STYLE)
            self.preload_spinbox.setToolTip("")
        except ValidationError as e:
            self.preload_spinbox.setStyleSheet(INVALID_STYLE)
            self.preload_spinbox.setToolTip(str(e))
            is_field_valid = False
        self._check_overall_validation_status()
        return is_field_valid

    def _validate_target_value(self) -> bool:
        """Validates the target penetration or load input field."""
        is_field_valid = True
        current_text = self.target_type_combo.currentText()
        param_name = "Target Penetration" if current_text == "Penetration Control" else "Target Load"
        # Min value must be greater than zero for these target controls
        min_val = 0.001 if current_text == "Penetration Control" else 0.1
        max_val = 200.0 if current_text == "Penetration Control" else 1e9
        try:
            validate_numerical_range(self.target_value_spinbox.value(), min_val, max_val, param_name)
            self.target_value_spinbox.setStyleSheet(VALID_STYLE)
            self.target_value_spinbox.setToolTip("")
        except ValidationError as e:
            self.target_value_spinbox.setStyleSheet(INVALID_STYLE)
            self.target_value_spinbox.setToolTip(str(e))
            is_field_valid = False
        self._check_overall_validation_status()
        return is_field_valid

    def _validate_all_inputs(self) -> bool:
        """
        Runs all individual validation checks and updates the overall validation status.
        Returns:
            bool: True if all inputs are currently valid, False otherwise.
        """
        self._validate_preload()
        self._validate_target_value()
        return self._is_valid

    def _check_overall_validation_status(self):
        """
        Checks if all fields are currently valid and emits `validation_status_changed` if the overall status changes.
        """
        is_preload_valid = self.preload_spinbox.styleSheet() != INVALID_STYLE
        is_target_valid = self.target_value_spinbox.styleSheet() != INVALID_STYLE
        current_overall_status = is_preload_valid and is_target_valid

        if self._is_valid != current_overall_status:
            self._is_valid = current_overall_status
            self.validation_status_changed.emit(self._is_valid)
            logger.debug(f"LoadingConditionsWidget overall validation status changed to: {self._is_valid}")

    def load_data(self, loading_data: Optional[LoadingConditions]) -> None:
        """
        Populates the UI fields from a LoadingConditions data object.
        Args:
            loading_data: The LoadingConditions object containing data to load.
                           If None, fields are reset to default values.
        """
        logger.debug(f"LoadingConditionsWidget: Loading data - {loading_data}")
        self.preload_spinbox.blockSignals(True)
        self.target_type_combo.blockSignals(True)
        self.target_value_spinbox.blockSignals(True)

        if loading_data:
            self.preload_spinbox.setValue(loading_data.vertical_preload if loading_data.vertical_preload is not None else 0.0)

            target_type_str = loading_data.target_type or "penetration"
            self.target_type_combo.setCurrentText("Load Control" if target_type_str == "load" else "Penetration Control")

            # Manually trigger on_target_type_changed to set suffix and range BEFORE setting value
            self.on_target_type_changed(self.target_type_combo.currentText())

            self.target_value_spinbox.setValue(loading_data.target_penetration_or_load if loading_data.target_penetration_or_load is not None else 1.0)
        else:
            self.preload_spinbox.setValue(0.0)
            self.target_type_combo.setCurrentIndex(0) # Default to "Penetration Control"
            self.on_target_type_changed(self.target_type_combo.currentText()) # Set initial state for target_value_spinbox
            self.target_value_spinbox.setValue(1.0)

        self.preload_spinbox.blockSignals(False)
        self.target_type_combo.blockSignals(False)
        self.target_value_spinbox.blockSignals(False)

        self._validate_all_inputs() # Validate after loading all data
        self.data_changed.emit() # Emit once after all updates

    def gather_data(self) -> Dict[str, Any]:
        """
        Collects data from UI fields into a dictionary.
        Returns None for fields that are currently invalid.

        Returns:
            Dict[str, Any]: A dictionary containing the current loading conditions data.
        """
        target_type_str = "load" if self.target_type_combo.currentText() == "Load Control" else "penetration"
        return {
            "vertical_preload": self.preload_spinbox.value() if self.preload_spinbox.styleSheet() != INVALID_STYLE else None,
            "target_type": target_type_str,
            "target_penetration_or_load": self.target_value_spinbox.value() if self.target_value_spinbox.styleSheet() != INVALID_STYLE else None,
        }

    def gather_data_to_model(self) -> Optional[LoadingConditions]:
        """
        Gathers data from UI fields and returns a LoadingConditions model instance.
        If inputs are currently invalid, this may return a model with None for those fields.

        Returns:
            Optional[LoadingConditions]: A LoadingConditions object.
        """
        self._validate_all_inputs() # Ensure current validation state is accurate

        # If not strictly valid, one might choose to return None or raise an error.
        # Here, we return a model with None for invalid fields, relying on gather_data's behavior.
        if not self._is_valid:
            logger.warning("Attempting to gather LoadingConditions model data when inputs are invalid.")

        raw_data = self.gather_data() # This will have None for invalid fields
        return LoadingConditions(
            vertical_preload=raw_data["vertical_preload"],
            target_type=raw_data["target_type"],
            target_penetration_or_load=raw_data["target_penetration_or_load"]
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
    widget = LoadingConditionsWidget()
    widget.setWindowTitle("Loading Conditions Widget Test")
    widget.resize(400, 200)
    widget.show()
    sys.exit(app.exec())
