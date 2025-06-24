"""
Widget for inputting Analysis Control parameters.

This widget allows the user to configure various parameters that control
the PLAXIS analysis, such as meshing settings, initial stress calculation
method, and iteration/convergence criteria for calculation phases.
Input validation is performed on numerical fields.

PRD Ref: Task 6.4 (Analysis Control Parameters Input Section)
         Task 9.4 (Input Validation Feedback)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QGroupBox, QCheckBox, QSpinBox
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Optional, Any, Dict

from backend.validation import validate_numerical_range, ValidationError
from backend.models import AnalysisControlParameters

logger = logging.getLogger(__name__)

VALID_STYLE = ""
INVALID_STYLE = "border: 1px solid red; background-color: #fff0f0;"

class AnalysisControlWidget(QWidget):
    """
    A widget for users to input analysis control parameters for PLAXIS.

    Signals:
        data_changed: Emitted when any input field's value changes.
        validation_status_changed (bool): Emitted when the overall validation status
                                          of the widget changes. True if all inputs valid.
    """
    data_changed = Signal()
    validation_status_changed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initializes the AnalysisControlWidget.
        Sets up UI elements for various analysis parameters and connects validation signals.
        """
        super().__init__(parent)
        self._is_valid = True # Internal state for overall widget validity

        self.main_layout = QVBoxLayout(self)
        group_box = QGroupBox("Analysis Control Parameters")
        self.main_layout.addWidget(group_box)

        form_layout = QFormLayout(group_box)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- Meshing Parameters ---
        self.mesh_coarseness_combo = QComboBox()
        self.mesh_coarseness_combo.addItems(["VeryCoarse", "Coarse", "Medium", "Fine", "VeryFine"])
        self.mesh_coarseness_combo.setCurrentText("Medium")
        self.mesh_coarseness_combo.currentTextChanged.connect(self.on_data_changed) # No specific validation needed
        form_layout.addRow(QLabel("Global Mesh Coarseness:"), self.mesh_coarseness_combo)

        self.refine_spudcan_checkbox = QCheckBox("Refine Spudcan Area")
        self.refine_spudcan_checkbox.setChecked(False)
        self.refine_spudcan_checkbox.stateChanged.connect(self.on_data_changed) # Boolean, always valid
        form_layout.addRow(self.refine_spudcan_checkbox)

        # --- Initial Stress Calculation ---
        self.initial_stress_combo = QComboBox()
        self.initial_stress_combo.addItems(["K0Procedure", "GravityLoading", "FieldStress (Not Implemented)"])
        self.initial_stress_combo.setCurrentText("K0Procedure")
        self.initial_stress_combo.currentTextChanged.connect(self.on_data_changed) # No specific validation needed
        form_layout.addRow(QLabel("Initial Stress Method:"), self.initial_stress_combo)

        # --- Iteration/Convergence Parameters ---
        self.max_iterations_spinbox = QSpinBox()
        self.max_iterations_spinbox.setRange(10, 10000)
        self.max_iterations_spinbox.setValue(100)
        self.max_iterations_spinbox.setToolTip("Maximum number of iterations for calculation steps (e.g., Phase.Deform.MaxIterations).")
        self.max_iterations_spinbox.valueChanged.connect(self._on_max_iterations_changed)
        self.max_iterations_spinbox.editingFinished.connect(self._on_max_iterations_editing_finished)
        form_layout.addRow(QLabel("Max Iterations (per step):"), self.max_iterations_spinbox)

        self.tolerated_error_spinbox = QDoubleSpinBox()
        self.tolerated_error_spinbox.setDecimals(4)
        self.tolerated_error_spinbox.setRange(1e-5, 0.5)
        self.tolerated_error_spinbox.setSingleStep(0.001)
        self.tolerated_error_spinbox.setValue(0.01)
        self.tolerated_error_spinbox.setToolTip("Tolerated error for iterative procedure (e.g., Phase.Deform.ToleratedError).")
        self.tolerated_error_spinbox.valueChanged.connect(self._on_tolerated_error_changed)
        self.tolerated_error_spinbox.editingFinished.connect(self._on_tolerated_error_editing_finished)
        form_layout.addRow(QLabel("Tolerated Error:"), self.tolerated_error_spinbox)

        self.reset_displacements_checkbox = QCheckBox("Reset Displacements to Zero (for main phase)")
        self.reset_displacements_checkbox.setChecked(False)
        self.reset_displacements_checkbox.setToolTip("If checked, displacements are reset to zero before the main penetration phase.")
        self.reset_displacements_checkbox.stateChanged.connect(self.on_data_changed) # Boolean, always valid
        form_layout.addRow(self.reset_displacements_checkbox)

        self.max_steps_stored_spinbox = QSpinBox()
        self.max_steps_stored_spinbox.setRange(1, 10000)
        self.max_steps_stored_spinbox.setValue(250)
        self.max_steps_stored_spinbox.setToolTip("Maximum number of calculation steps to store for results/curves (e.g., Phase.MaxStepsStored).")
        self.max_steps_stored_spinbox.valueChanged.connect(self._on_max_steps_stored_changed)
        self.max_steps_stored_spinbox.editingFinished.connect(self._on_max_steps_stored_editing_finished)
        form_layout.addRow(QLabel("Number of Stored Output Steps:"), self.max_steps_stored_spinbox)

        self.max_calc_steps_spinbox = QSpinBox()
        self.max_calc_steps_spinbox.setRange(10, 100000)
        self.max_calc_steps_spinbox.setValue(1000)
        self.max_calc_steps_spinbox.setToolTip("Maximum calculation steps per phase (e.g., Phase.Deform.MaxSteps).")
        self.max_calc_steps_spinbox.valueChanged.connect(self._on_max_calc_steps_changed)
        self.max_calc_steps_spinbox.editingFinished.connect(self._on_max_calc_steps_editing_finished)
        form_layout.addRow(QLabel("Max Calculation Steps (per phase):"), self.max_calc_steps_spinbox)

        self.min_iterations_spinbox = QSpinBox()
        self.min_iterations_spinbox.setRange(1, 100) # Min iterations should not exceed Max Iterations, validated dynamically
        self.min_iterations_spinbox.setValue(10)
        self.min_iterations_spinbox.setToolTip("Desired minimum iterations per calculation step (e.g., Phase.Deform.MinIterations).")
        self.min_iterations_spinbox.valueChanged.connect(self._on_min_iterations_changed)
        self.min_iterations_spinbox.editingFinished.connect(self._on_min_iterations_editing_finished)
        form_layout.addRow(QLabel("Min Iterations (per step):"), self.min_iterations_spinbox)

        self._validate_all_inputs() # Perform initial validation
        logger.info("AnalysisControlWidget initialized.")

    # --- Slots for valueChanged signals of spinboxes ---
    @Slot()
    def _on_max_iterations_changed(self):
        self._validate_max_iterations()
        self._validate_min_iterations() # Min iterations depends on max
        self.data_changed.emit()
    @Slot()
    def _on_tolerated_error_changed(self): self._validate_tolerated_error(); self.data_changed.emit()
    @Slot()
    def _on_max_steps_stored_changed(self): self._validate_max_steps_stored(); self.data_changed.emit()
    @Slot()
    def _on_max_calc_steps_changed(self): self._validate_max_calc_steps(); self.data_changed.emit()
    @Slot()
    def _on_min_iterations_changed(self): self._validate_min_iterations(); self.data_changed.emit()

    # --- Slots for editingFinished signals (for final validation on focus lost) ---
    @Slot()
    def _on_max_iterations_editing_finished(self):
        self._validate_max_iterations()
        self._validate_min_iterations() # Re-check min if max changed
    @Slot()
    def _on_tolerated_error_editing_finished(self): self._validate_tolerated_error()
    @Slot()
    def _on_max_steps_stored_editing_finished(self): self._validate_max_steps_stored()
    @Slot()
    def _on_max_calc_steps_editing_finished(self): self._validate_max_calc_steps()
    @Slot()
    def _on_min_iterations_editing_finished(self): self._validate_min_iterations()

    @Slot()
    def on_data_changed(self):
        """Slot for QComboBox and QCheckBox changes. These are inherently valid."""
        # No specific validation for these simple selection/boolean widgets needed here,
        # but call _check_overall_validation_status to ensure overall status is updated.
        self._check_overall_validation_status()
        self.data_changed.emit()
        logger.debug("AnalysisControlWidget: Data changed signal emitted (combo/checkbox).")

    # --- Individual validation methods ---
    def _validate_max_iterations(self) -> bool:
        """Validates the Max Iterations spinbox."""
        return self._validate_spinbox(self.max_iterations_spinbox, 10, 10000, "Max Iterations")

    def _validate_tolerated_error(self) -> bool:
        """Validates the Tolerated Error spinbox."""
        return self._validate_spinbox(self.tolerated_error_spinbox, 1e-5, 0.5, "Tolerated Error", is_double=True)

    def _validate_max_steps_stored(self) -> bool:
        """Validates the Max Steps Stored spinbox."""
        return self._validate_spinbox(self.max_steps_stored_spinbox, 1, 10000, "Max Steps Stored")

    def _validate_max_calc_steps(self) -> bool:
        """Validates the Max Calculation Steps spinbox."""
        return self._validate_spinbox(self.max_calc_steps_spinbox, 10, 100000, "Max Calculation Steps")

    def _validate_min_iterations(self) -> bool:
        """Validates the Min Iterations spinbox, ensuring it's <= Max Iterations."""
        # Max iterations value is used as the upper bound for min iterations.
        max_iter_val = self.max_iterations_spinbox.value()
        is_field_valid = self._validate_spinbox(self.min_iterations_spinbox, 1, max_iter_val, "Min Iterations")

        # Additional check if the primary validation passed but value > max_iterations
        if is_field_valid and self.min_iterations_spinbox.value() > max_iter_val:
             self.min_iterations_spinbox.setStyleSheet(INVALID_STYLE)
             self.min_iterations_spinbox.setToolTip(f"Min Iterations ({self.min_iterations_spinbox.value()}) cannot exceed Max Iterations ({max_iter_val}).")
             is_field_valid = False
             self._check_overall_validation_status() # Update overall status as this specific check might change it
        return is_field_valid

    def _validate_spinbox(self, spinbox: QWidget, min_val: Any, max_val: Any, name: str, is_double: bool = False) -> bool:
        """Helper to validate a QSpinBox or QDoubleSpinBox."""
        is_field_valid = True
        try:
            value = spinbox.value() # type: ignore
            validate_numerical_range(value, min_val, max_val, name, value_type=float if is_double else int)
            spinbox.setStyleSheet(VALID_STYLE)
            spinbox.setToolTip("")
        except ValidationError as e:
            spinbox.setStyleSheet(INVALID_STYLE)
            spinbox.setToolTip(str(e))
            is_field_valid = False
        # This call will update the overall widget validity and emit signal if it changed
        self._check_overall_validation_status()
        return is_field_valid

    def _validate_all_inputs(self) -> bool:
        """
        Runs all individual validation checks and updates the overall validation status.
        Returns:
            bool: True if all inputs are currently valid, False otherwise.
        """
        # Order matters if one validation depends on another (e.g., min_iterations depends on max_iterations)
        self._validate_max_iterations()
        self._validate_tolerated_error()
        self._validate_max_steps_stored()
        self._validate_max_calc_steps()
        self._validate_min_iterations() # Depends on max_iterations, so called after
        # The self._is_valid state is updated by the last _check_overall_validation_status call in the chain
        return self._is_valid

    def _check_overall_validation_status(self):
        """
        Checks if all fields are currently valid and emits `validation_status_changed` if the overall status changes.
        """
        widgets_to_check = [
            self.max_iterations_spinbox, self.tolerated_error_spinbox,
            self.max_steps_stored_spinbox, self.max_calc_steps_spinbox,
            self.min_iterations_spinbox
        ]
        # A field is valid if its stylesheet is not the INVALID_STYLE
        current_overall_status = all(w.styleSheet() != INVALID_STYLE for w in widgets_to_check)

        if self._is_valid != current_overall_status:
            self._is_valid = current_overall_status
            self.validation_status_changed.emit(self._is_valid)
            logger.debug(f"AnalysisControlWidget overall validation status changed to: {self._is_valid}")

    def load_data(self, ac_data: Optional[AnalysisControlParameters]) -> None:
        """
        Populates the UI fields from an AnalysisControlParameters data object.
        Args:
            ac_data: The AnalysisControlParameters object. Resets to defaults if None.
        """
        logger.debug(f"AnalysisControlWidget: Loading data - {ac_data}")

        for child in self.findChildren((QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox)):
            child.blockSignals(True)

        if ac_data:
            self.mesh_coarseness_combo.setCurrentText(ac_data.meshing_global_coarseness or "Medium")
            self.refine_spudcan_checkbox.setChecked(ac_data.meshing_refinement_spudcan or False)
            self.initial_stress_combo.setCurrentText(ac_data.initial_stress_method or "K0Procedure")
            self.max_iterations_spinbox.setValue(ac_data.MaxIterations if ac_data.MaxIterations is not None else 100)
            self.tolerated_error_spinbox.setValue(ac_data.ToleratedError if ac_data.ToleratedError is not None else 0.01)
            self.reset_displacements_checkbox.setChecked(ac_data.ResetDispToZero or False)
            self.max_steps_stored_spinbox.setValue(ac_data.MaxStepsStored if ac_data.MaxStepsStored is not None else 250)
            self.max_calc_steps_spinbox.setValue(ac_data.MaxSteps if ac_data.MaxSteps is not None else 1000)
            self.min_iterations_spinbox.setValue(ac_data.MinIterations if ac_data.MinIterations is not None else 10)
        else: # Reset to defaults
            self.mesh_coarseness_combo.setCurrentText("Medium")
            self.refine_spudcan_checkbox.setChecked(False)
            self.initial_stress_combo.setCurrentText("K0Procedure")
            self.max_iterations_spinbox.setValue(100)
            self.tolerated_error_spinbox.setValue(0.01)
            self.reset_displacements_checkbox.setChecked(False)
            self.max_steps_stored_spinbox.setValue(250)
            self.max_calc_steps_spinbox.setValue(1000)
            self.min_iterations_spinbox.setValue(10)

        for child in self.findChildren((QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox)):
            child.blockSignals(False)

        self._validate_all_inputs() # Validate after loading all data
        self.data_changed.emit() # Emit that data has changed

    def gather_data(self) -> Dict[str, Any]:
        """
        Collects data from UI fields into a dictionary.
        Returns None for fields that are currently invalid.

        Returns:
            Dict[str, Any]: Dictionary of analysis control parameters.
        """
        data = {
            "meshing_global_coarseness": self.mesh_coarseness_combo.currentText(),
            "meshing_refinement_spudcan": self.refine_spudcan_checkbox.isChecked(),
            "initial_stress_method": self.initial_stress_combo.currentText(),
            "MaxIterations": self.max_iterations_spinbox.value() if self.max_iterations_spinbox.styleSheet()!=INVALID_STYLE else None,
            "ToleratedError": self.tolerated_error_spinbox.value() if self.tolerated_error_spinbox.styleSheet()!=INVALID_STYLE else None,
            "ResetDispToZero": self.reset_displacements_checkbox.isChecked(),
            "MaxStepsStored": self.max_steps_stored_spinbox.value() if self.max_steps_stored_spinbox.styleSheet()!=INVALID_STYLE else None,
            "MaxSteps": self.max_calc_steps_spinbox.value() if self.max_calc_steps_spinbox.styleSheet()!=INVALID_STYLE else None,
            "MinIterations": self.min_iterations_spinbox.value() if self.min_iterations_spinbox.styleSheet()!=INVALID_STYLE else None,
        }
        logger.debug(f"AnalysisControlWidget: Gathered data - {data}")
        return data

    def gather_data_to_model(self) -> Optional[AnalysisControlParameters]:
        """
        Gathers data from UI fields and returns an AnalysisControlParameters model instance.
        If inputs are currently invalid, this may return a model with None for those fields.

        Returns:
            Optional[AnalysisControlParameters]: An AnalysisControlParameters object.
        """
        self._validate_all_inputs() # Ensure current validation status is accurate

        if not self._is_valid:
            logger.warning("Attempting to gather AnalysisControlParameters model data when inputs are invalid.")

        # Even if not valid, gather what's there; None will be set for invalid numeric fields by gather_data()
        raw_data = self.gather_data()
        return AnalysisControlParameters(
            meshing_global_coarseness=raw_data["meshing_global_coarseness"],
            meshing_refinement_spudcan=raw_data["meshing_refinement_spudcan"],
            initial_stress_method=raw_data["initial_stress_method"],
            MaxIterations=raw_data["MaxIterations"],
            ToleratedError=raw_data["ToleratedError"],
            ResetDispToZero=raw_data["ResetDispToZero"],
            MaxStepsStored=raw_data["MaxStepsStored"],
            MaxSteps=raw_data["MaxSteps"],
            MinIterations=raw_data["MinIterations"]
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
    widget = AnalysisControlWidget()
    widget.setWindowTitle("Analysis Control Widget Test")
    widget.resize(500, 400)
    widget.show()
    sys.exit(app.exec())
