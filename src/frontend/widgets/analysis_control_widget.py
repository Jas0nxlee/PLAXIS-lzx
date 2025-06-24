"""
Widget for inputting Analysis Control parameters.
PRD Ref: Task 6.4 (Analysis Control Parameters Input Section)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QComboBox, QGroupBox, QCheckBox, QSpinBox
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Optional, Any

# from ...backend.models import AnalysisControlParameters # For actual data interaction

logger = logging.getLogger(__name__)

class AnalysisControlWidget(QWidget):
    """
    A widget for users to input analysis control parameters for PLAXIS.
    """
    data_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)

        group_box = QGroupBox("Analysis Control Parameters")
        self.main_layout.addWidget(group_box)

        form_layout = QFormLayout(group_box)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- Meshing Parameters (Task 6.4.1) ---
        self.mesh_coarseness_combo = QComboBox()
        self.mesh_coarseness_combo.addItems(["VeryCoarse", "Coarse", "Medium", "Fine", "VeryFine"])
        self.mesh_coarseness_combo.setCurrentText("Medium")
        self.mesh_coarseness_combo.currentTextChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Global Mesh Coarseness:"), self.mesh_coarseness_combo)

        self.refine_spudcan_checkbox = QCheckBox("Refine Spudcan Area")
        self.refine_spudcan_checkbox.setChecked(False)
        self.refine_spudcan_checkbox.stateChanged.connect(self.on_data_changed)
        form_layout.addRow(self.refine_spudcan_checkbox)

        # --- Initial Stress Calculation (Task 6.4.2) ---
        self.initial_stress_combo = QComboBox()
        self.initial_stress_combo.addItems(["K0Procedure", "GravityLoading", "FieldStress (Not Implemented)"])
        self.initial_stress_combo.setCurrentText("K0Procedure")
        self.initial_stress_combo.currentTextChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Initial Stress Method:"), self.initial_stress_combo)

        # --- Calculation Phase Configuration (Task 6.4.3 - Simplified) ---
        # For now, this is very simplified. Full phase control is complex.
        # Example: A checkbox for a common optional phase.
        # self.include_preload_phase_checkbox = QCheckBox("Include Preloading Phase")
        # self.include_preload_phase_checkbox.setChecked(True) # Default might depend on typical workflow
        # self.include_preload_phase_checkbox.stateChanged.connect(self.on_data_changed)
        # form_layout.addRow(self.include_preload_phase_checkbox)
        # Actual phase sequence is primarily backend-defined for now.

        # --- Advanced Analysis Settings (Task 6.4.4 - Subset) ---
        self.max_iterations_spinbox = QSpinBox()
        self.max_iterations_spinbox.setRange(10, 1000)
        self.max_iterations_spinbox.setValue(100) # PLAXIS default is often 60 or 100
        self.max_iterations_spinbox.setToolTip("Maximum number of iterations for calculation steps.")
        self.max_iterations_spinbox.valueChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Max Iterations:"), self.max_iterations_spinbox)

        self.tolerated_error_spinbox = QDoubleSpinBox()
        self.tolerated_error_spinbox.setDecimals(4)
        self.tolerated_error_spinbox.setRange(1e-5, 1e-1)
        self.tolerated_error_spinbox.setSingleStep(0.001)
        self.tolerated_error_spinbox.setValue(0.01) # PLAXIS default
        self.tolerated_error_spinbox.setToolTip("Tolerated error for iterative procedure.")
        self.tolerated_error_spinbox.valueChanged.connect(self.on_data_changed)
        form_layout.addRow(QLabel("Tolerated Error:"), self.tolerated_error_spinbox)

        self.reset_displacements_checkbox = QCheckBox("Reset Displacements to Zero (for main phase)")
        self.reset_displacements_checkbox.setChecked(False)
        self.reset_displacements_checkbox.setToolTip("If checked, displacements are reset to zero before the main penetration phase.")
        self.reset_displacements_checkbox.stateChanged.connect(self.on_data_changed)
        form_layout.addRow(self.reset_displacements_checkbox)

        # TODO: Add more advanced parameters as needed: MaxSteps, MaxStepsStored, MinIterations etc.

        logger.info("AnalysisControlWidget initialized.")

    @Slot()
    def on_data_changed(self):
        """Emits the data_changed signal."""
        self.data_changed.emit()
        logger.debug("AnalysisControlWidget: Data changed signal emitted.")

    def load_data(self, analysis_control_data: Optional[Any]) -> None: # Any for backend.models.AnalysisControlParameters
        """Populates UI from an AnalysisControlParameters data object."""
        logger.debug(f"AnalysisControlWidget: Loading data - {analysis_control_data}")

        # Block signals to prevent premature emission of data_changed
        self.mesh_coarseness_combo.blockSignals(True)
        self.refine_spudcan_checkbox.blockSignals(True)
        self.initial_stress_combo.blockSignals(True)
        self.max_iterations_spinbox.blockSignals(True)
        self.tolerated_error_spinbox.blockSignals(True)
        self.reset_displacements_checkbox.blockSignals(True)

        if analysis_control_data:
            self.mesh_coarseness_combo.setCurrentText(getattr(analysis_control_data, 'meshing_global_coarseness', "Medium"))
            self.refine_spudcan_checkbox.setChecked(getattr(analysis_control_data, 'meshing_refinement_spudcan', False))
            self.initial_stress_combo.setCurrentText(getattr(analysis_control_data, 'initial_stress_method', "K0Procedure"))
            self.max_iterations_spinbox.setValue(getattr(analysis_control_data, 'MaxIterations', 100))
            self.tolerated_error_spinbox.setValue(getattr(analysis_control_data, 'ToleratedError', 0.01))
            self.reset_displacements_checkbox.setChecked(getattr(analysis_control_data, 'ResetDispToZero', False))
        else: # Reset to defaults
            self.mesh_coarseness_combo.setCurrentText("Medium")
            self.refine_spudcan_checkbox.setChecked(False)
            self.initial_stress_combo.setCurrentText("K0Procedure")
            self.max_iterations_spinbox.setValue(100)
            self.tolerated_error_spinbox.setValue(0.01)
            self.reset_displacements_checkbox.setChecked(False)

        self.mesh_coarseness_combo.blockSignals(False)
        self.refine_spudcan_checkbox.blockSignals(False)
        self.initial_stress_combo.blockSignals(False)
        self.max_iterations_spinbox.blockSignals(False)
        self.tolerated_error_spinbox.blockSignals(False)
        self.reset_displacements_checkbox.blockSignals(False)
        self.data_changed.emit() # Emit once after all updates

    def gather_data(self) -> Dict[str, Any]: # Placeholder, should return AnalysisControlParameters
        """Collects data from UI fields."""
        data = {
            "meshing_global_coarseness": self.mesh_coarseness_combo.currentText(),
            "meshing_refinement_spudcan": self.refine_spudcan_checkbox.isChecked(),
            "initial_stress_method": self.initial_stress_combo.currentText(),
            "MaxIterations": self.max_iterations_spinbox.value(),
            "ToleratedError": self.tolerated_error_spinbox.value(),
            "ResetDispToZero": self.reset_displacements_checkbox.isChecked(),
            # Add other parameters as they are implemented in the UI
        }
        logger.debug(f"AnalysisControlWidget: Gathered data - {data}")
        return data

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    # Mock for backend.models.AnalysisControlParameters
    class MockAnalysisControlParameters:
        def __init__(self, meshing_global_coarseness="Medium", meshing_refinement_spudcan=False,
                     initial_stress_method="K0Procedure", MaxIterations=100, ToleratedError=0.01,
                     ResetDispToZero=False):
            self.meshing_global_coarseness = meshing_global_coarseness
            self.meshing_refinement_spudcan = meshing_refinement_spudcan
            self.initial_stress_method = initial_stress_method
            self.MaxIterations = MaxIterations
            self.ToleratedError = ToleratedError
            self.ResetDispToZero = ResetDispToZero


    app = QApplication(sys.argv)
    widget = AnalysisControlWidget()

    # Test loading data
    test_data = MockAnalysisControlParameters(
        meshing_global_coarseness="Fine",
        meshing_refinement_spudcan=True,
        initial_stress_method="GravityLoading",
        MaxIterations=150,
        ToleratedError=0.005,
        ResetDispToZero=True
    )
    widget.load_data(test_data)
    logger.info(f"Data after load_data: {widget.gather_data()}")

    # Test changing data via UI (conceptual)
    widget.mesh_coarseness_combo.setCurrentText("Coarse")
    widget.refine_spudcan_checkbox.setChecked(False)
    logger.info(f"Data after UI changes: {widget.gather_data()}")

    widget.setWindowTitle("Analysis Control Widget Test")
    widget.resize(500, 300)
    widget.show()
    sys.exit(app.exec())
