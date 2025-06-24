"""
Widget for inputting Loading Conditions parameters.
PRD Ref: Task 6.3 (Loading Conditions Input Section)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Optional, Any

# from ...backend.models import LoadingConditions # For actual data interaction

logger = logging.getLogger(__name__)

class LoadingConditionsWidget(QWidget):
    """
    A widget for users to input loading conditions for the analysis.
    """
    data_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)

        group_box = QGroupBox("Loading Conditions")
        self.main_layout.addWidget(group_box)

        form_layout = QFormLayout(group_box)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- Vertical Pre-load Input (Task 6.3.1) ---
        self.preload_spinbox = QDoubleSpinBox()
        self.preload_spinbox.setSuffix(" kN") # Example unit
        self.preload_spinbox.setDecimals(2)
        self.preload_spinbox.setRange(0, 1e9) # Allow zero preload
        self.preload_spinbox.setValue(0.0)
        self.preload_spinbox.valueChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Vertical Pre-load (Fz):"), self.preload_spinbox)

        # --- Target Type Selection (Task 6.3.2) ---
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["Penetration Control", "Load Control"])
        self.target_type_combo.currentTextChanged.connect(self.on_target_type_changed)
        form_layout.addRow(QLabel("Target Control Type:"), self.target_type_combo)

        # --- Target Penetration/Load Input (Task 6.3.2) ---
        self.target_value_spinbox = QDoubleSpinBox()
        self.target_value_spinbox.setDecimals(3)
        self.target_value_spinbox.setRange(0, 1000) # General range, unit changes
        self.target_value_spinbox.setValue(1.0)
        self.target_value_spinbox.valueChanged.connect(self.on_data_changed)
        self.target_value_label = QLabel("Target Penetration (uz):") # Initial label
        form_layout.addRow(self.target_value_label, self.target_value_spinbox)
        self.on_target_type_changed(self.target_type_combo.currentText()) # Set initial suffix

        # --- Load Steps/Displacement Increments Input (Task 6.3.3) ---
        # This is simplified for now. PLAXIS handles this through calculation control parameters (MaxStepsStored etc.)
        # or specific load function definitions which are more complex.
        # For a basic UI, we might just note that this is controlled elsewhere or add a simple "Number of Steps" if desired.
        # self.num_steps_lineedit = QLineEdit() # Placeholder, could be QSpinBox
        # self.num_steps_lineedit.setPlaceholderText("e.g., 100 or (PLAXIS Default)")
        # self.num_steps_lineedit.textChanged.connect(self.on_data_changed)
        # form_layout.addRow(QLabel("Number of Steps (Optional):"), self.num_steps_lineedit)
        # This field will be moved to AnalysisControlWidget as MaxStepsStored.

        logger.info("LoadingConditionsWidget initialized.")

    @Slot(str)
    def on_target_type_changed(self, text: str):
        """Updates the label and suffix for the target value based on type."""
        if text == "Penetration Control":
            self.target_value_label.setText("Target Penetration (uz):")
            self.target_value_spinbox.setSuffix(" m")
        elif text == "Load Control":
            self.target_value_label.setText("Target Load (Fz):")
            self.target_value_spinbox.setSuffix(" kN")
        self.on_data_changed() # Emit data changed as the meaning of target_value changes

    @Slot()
    def on_data_changed(self):
        """Emits the data_changed signal."""
        self.data_changed.emit()
        logger.debug("LoadingConditionsWidget: Data changed signal emitted.")

    def load_data(self, loading_data: Optional[Any]) -> None: # Any for backend.models.LoadingConditions
        """Populates UI from a LoadingConditions data object."""
        logger.debug(f"LoadingConditionsWidget: Loading data - {loading_data}")

        self.preload_spinbox.blockSignals(True)
        self.target_type_combo.blockSignals(True)
        self.target_value_spinbox.blockSignals(True)
        # self.num_steps_lineedit.blockSignals(True) # Removed

        if loading_data:
            self.preload_spinbox.setValue(getattr(loading_data, 'vertical_preload', 0.0))

            target_type_str = getattr(loading_data, 'target_type', "penetration")
            if target_type_str == "penetration":
                self.target_type_combo.setCurrentText("Penetration Control")
            elif target_type_str == "load":
                self.target_type_combo.setCurrentText("Load Control")
            else:
                self.target_type_combo.setCurrentIndex(0) # Default to penetration

            self.on_target_type_changed(self.target_type_combo.currentText()) # Update label/suffix
            self.target_value_spinbox.setValue(getattr(loading_data, 'target_penetration_or_load', 1.0))

            # num_steps is not directly in LoadingConditions model, might be in AnalysisControlParameters
            # For now, this is a placeholder UI element.
            # self.num_steps_lineedit.setText(str(getattr(loading_data, 'number_of_steps', '')))
            # self.num_steps_lineedit.setText("") # Reset placeholder # Removed

        else: # Reset to defaults
            self.preload_spinbox.setValue(0.0)
            self.target_type_combo.setCurrentIndex(0)
            self.on_target_type_changed(self.target_type_combo.currentText())
            self.target_value_spinbox.setValue(1.0)
            # self.num_steps_lineedit.setText("") # Removed

        self.preload_spinbox.blockSignals(False)
        self.target_type_combo.blockSignals(False)
        self.target_value_spinbox.blockSignals(False)
        # self.num_steps_lineedit.blockSignals(False) # Removed
        self.data_changed.emit() # Emit once after all updates

    def gather_data(self) -> Dict[str, Any]: # Placeholder, should return LoadingConditions
        """Collects data from UI fields."""
        target_type_str = "penetration"
        if self.target_type_combo.currentText() == "Load Control":
            target_type_str = "load"

        # num_steps is more complex, might not directly map to LoadingConditions.
        # For now, not including it in the core gathered data for the model.
        # num_steps_val = self.num_steps_lineedit.text()
        # try:
        #     num_steps_int = int(num_steps_val) if num_steps_val else None
        # except ValueError:
        #     num_steps_int = None # Or handle error

        data = {
            "vertical_preload": self.preload_spinbox.value(),
            "target_type": target_type_str,
            "target_penetration_or_load": self.target_value_spinbox.value(),
            # "number_of_steps": num_steps_int # If we decide to include it
        }
        logger.debug(f"LoadingConditionsWidget: Gathered data - {data}")
        return data

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    # Mock backend LoadingConditions for testing
    class MockLoadingConditions:
        def __init__(self, vertical_preload=0.0, target_type="penetration", target_penetration_or_load=1.0):
            self.vertical_preload = vertical_preload
            self.target_type = target_type
            self.target_penetration_or_load = target_penetration_or_load

    app = QApplication(sys.argv)
    widget = LoadingConditionsWidget()

    # Test loading data
    test_data = MockLoadingConditions(vertical_preload=500.0, target_type="load", target_penetration_or_load=1000.0)
    widget.load_data(test_data)
    logger.info(f"Data after load_data: {widget.gather_data()}")

    # Test changing data via UI (conceptual)
    widget.preload_spinbox.setValue(750.0)
    widget.target_type_combo.setCurrentText("Penetration Control")
    widget.target_value_spinbox.setValue(2.5)
    logger.info(f"Data after UI changes: {widget.gather_data()}")

    widget.setWindowTitle("Loading Conditions Widget Test")
    widget.resize(400, 200)
    widget.show()
    sys.exit(app.exec())
