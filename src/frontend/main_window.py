"""
Main Window for the PLAXIS 3D Spudcan Automation Tool.
Handles the main UI layout, project management, analysis execution flow,
and display of results and logs.

PRD Ref: Category 4 (Frontend Development: UI Shell & Framework)
         Task 7.1.1 (QThread for UI Responsiveness)
         Task 9.4 (Input Validation Feedback)
         Task 9.5 (UI for Log Access)
"""

import sys
import logging
import os
import traceback # For detailed error logging in worker thread
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QToolBar, QStatusBar, QStackedWidget, QFileDialog,
    QMessageBox, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QHBoxLayout, QTextEdit, QProgressBar, QFrame, QTableWidget, QHeaderView, QTableWidgetItem
)
from PySide6.QtGui import QAction, QIcon, QFont, QDesktopServices
from PySide6.QtCore import Qt, QSize, Slot, QUrl, QObject, Signal, QRunnable, QThreadPool, QThread

from ..backend.models import (
    ProjectSettings, SpudcanGeometry, SoilLayer, MaterialProperties,
    LoadingConditions, AnalysisControlParameters, AnalysisResults
)
from ..backend.project_io import save_project, load_project
from ..backend.logger_config import LOG_FILENAME

from .widgets.spudcan_geometry_widget import SpudcanGeometryWidget
from .widgets.soil_stratigraphy_widget import SoilStratigraphyWidget
from .widgets.loading_conditions_widget import LoadingConditionsWidget
from .widgets.analysis_control_widget import AnalysisControlWidget
from .widgets.mpl_widget import MplWidget
from .qt_logging_handler import QtLoggingHandler
from .settings_dialog import SettingsDialog
from ..backend.plaxis_interactor.interactor import PlaxisInteractor
from ..backend.plaxis_interactor import geometry_builder, soil_builder, calculation_builder, results_parser
from ..backend.exceptions import (
    PlaxisAutomationError, PlaxisConnectionError, PlaxisConfigurationError,
    PlaxisCalculationError, PlaxisOutputError, PlaxisCliError, ProjectValidationError
)

from typing import Optional, Dict, Any, List, Callable # Added Any, List, Callable

logger = logging.getLogger(__name__)

# --- Analysis Worker Thread ---
class AnalysisWorkerSignals(QObject):
    """
    Defines signals emitted by the AnalysisWorker.
    - analysis_stage_changed(str): Emits current stage of analysis.
    - progress_updated(int, int): Emits current progress (value, max).
    - analysis_finished(AnalysisResults): Emits the compiled results upon successful completion.
    - analysis_error(str, str): Emits error title and detailed message on failure.
    - finished: Emitted when the worker's run method completes (success or failure).
    """
    analysis_stage_changed = Signal(str)
    progress_updated = Signal(int, int)
    analysis_finished = Signal(AnalysisResults) # Pass the results object
    analysis_error = Signal(str, str) # title, message
    finished = Signal() # To signal the QThread to quit

class AnalysisWorker(QObject): # Changed from QRunnable to QObject for QThread.moveToThread()
    """
    Worker object to perform PLAXIS analysis in a separate thread.
    """
    def __init__(self, plaxis_exe_path: str, project_settings: ProjectSettings):
        super().__init__()
        self.signals = AnalysisWorkerSignals()
        self.plaxis_exe_path = plaxis_exe_path
        self.project_settings = project_settings
        self.interactor: Optional[PlaxisInteractor] = None
        self._is_cancelled = False

    @Slot()
    def run_analysis(self):
        """
        Executes the full PLAXIS analysis workflow.
        This method is intended to be run in a separate thread.
        """
        try:
            logger.info("AnalysisWorker: Starting analysis run.")
            self.interactor = PlaxisInteractor(self.plaxis_exe_path, self.project_settings)

            # Connect interactor signals to worker signals to relay them to MainWindow
            self.interactor.signals.analysis_stage_changed.connect(self.signals.analysis_stage_changed)
            self.interactor.signals.progress_updated.connect(self.signals.progress_updated)

            if self._is_cancelled: return

            # 1. Define Model Setup Callables
            self.signals.analysis_stage_changed.emit("setup_start")
            model_setup_callables = geometry_builder.get_spudcan_geometry_commands(self.project_settings.spudcan) + \
                                  soil_builder.get_soil_material_commands(self.project_settings.soil_stratigraphy) + \
                                  soil_builder.get_soil_stratigraphy_commands(self.project_settings.soil_stratigraphy, self.project_settings.water_table_depth)
            self.interactor.setup_model_in_plaxis(model_setup_callables, is_new_project=True)
            self.signals.analysis_stage_changed.emit("setup_end")
            if self._is_cancelled: return

            # 2. Define Calculation Run Callables
            self.signals.analysis_stage_changed.emit("calculation_start") # Broadly covers mesh, calc
            calculation_run_callables = calculation_builder.get_full_calculation_workflow_commands(self.project_settings)
            self.interactor.run_calculation(calculation_run_callables)
            self.signals.analysis_stage_changed.emit("calculation_end")
            if self._is_cancelled: return

            # 3. Define Results Extraction Callables
            self.signals.analysis_stage_changed.emit("results_start")
            results_extraction_callables = results_parser.get_standard_results_commands(self.project_settings)
            raw_results_data = self.interactor.extract_results(results_extraction_callables)

            # 4. Process raw_results_data into AnalysisResults object
            compiled_results = results_parser.compile_analysis_results(raw_results_data, self.project_settings)
            self.signals.analysis_stage_changed.emit("results_end")
            if self._is_cancelled: return

            self.signals.analysis_finished.emit(compiled_results)
            logger.info("AnalysisWorker: Analysis completed successfully.")

        except PlaxisConnectionError as e:
            logger.error(f"AnalysisWorker: PLAXIS Connection Error: {e}", exc_info=True)
            self.signals.analysis_error.emit("PLAXIS Connection Error",
                                             f"Could not connect to PLAXIS services:\n{e}\n\n"
                                             "Ensure PLAXIS is running, API service enabled, and connection details are correct.")
        except PlaxisConfigurationError as e:
            logger.error(f"AnalysisWorker: PLAXIS Configuration Error: {e}", exc_info=True)
            self.signals.analysis_error.emit("PLAXIS Configuration Error",
                                             f"Model or analysis configuration issue for PLAXIS:\n{e}\n\n"
                                             "Check input parameters, soil definitions, and analysis settings.")
        except PlaxisCalculationError as e:
            logger.error(f"AnalysisWorker: PLAXIS Calculation Error: {e}", exc_info=True)
            self.signals.analysis_error.emit("PLAXIS Calculation Error",
                                             f"PLAXIS reported an error during calculation:\n{e}\n\n"
                                             "This may be due to numerical issues or model instability. Check PLAXIS output.")
        except PlaxisOutputError as e:
            logger.error(f"AnalysisWorker: PLAXIS Output Error: {e}", exc_info=True)
            self.signals.analysis_error.emit("PLAXIS Output Error",
                                             f"Could not retrieve or parse results from PLAXIS:\n{e}")
        except PlaxisCliError as e: # Should not happen if using API primarily
            logger.error(f"AnalysisWorker: PLAXIS CLI Error: {e}", exc_info=True)
            self.signals.analysis_error.emit("PLAXIS Scripting Error",
                                             f"Error running PLAXIS script (CLI):\n{e}")
        except ProjectValidationError as ve: # If validation is done before this worker
            logger.error(f"AnalysisWorker: Project Validation Error: {ve}", exc_info=True)
            self.signals.analysis_error.emit("Input Validation Error",
                                             f"Issue with provided input data:\n{ve}\n\nPlease review inputs.")
        except PlaxisAutomationError as pae: # Catch-all for other specific automation errors
            logger.error(f"AnalysisWorker: PLAXIS Automation Error: {pae}", exc_info=True)
            self.signals.analysis_error.emit("PLAXIS Automation Error", f"An automation error occurred:\n{pae}")
        except Exception as e:
            detailed_error = traceback.format_exc()
            logger.error(f"AnalysisWorker: Unexpected error during analysis: {e}\n{detailed_error}", exc_info=True)
            self.signals.analysis_error.emit("Unexpected Application Error",
                                             f"An unexpected error occurred:\n{e}\n\nCheck logs for details.")
        finally:
            if self.interactor:
                self.interactor.close_all_connections()
            self.signals.finished.emit()
            logger.info("AnalysisWorker: Run method finished.")

    def request_stop(self):
        """Requests the analysis to stop."""
        logger.info("AnalysisWorker: Stop requested.")
        self._is_cancelled = True
        if self.interactor:
            self.interactor.attempt_stop_calculation()


class MainWindow(QMainWindow):
    # ... (rest of MainWindow __init__ and other methods up to on_run_analysis_clicked) ...
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.current_project_data: Optional[ProjectSettings] = None
        self.current_project_path: Optional[str] = None
        self.project_modified: bool = False

        # For QThread implementation
        self.analysis_thread: Optional[QThread] = None
        self.analysis_worker: Optional[AnalysisWorker] = None

        self.widget_validation_states: Dict[str, bool] = {
            "spudcan_geometry": True,
            "loading_conditions": True,
            "analysis_control": True,
            "soil_stratigraphy": True,
        }

        self.setWindowTitle("Untitled Project - PLAXIS 3D Spudcan Automation Tool")
        self.setGeometry(100, 100, 1200, 800)

        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        project_info_group = QGroupBox("Project Information")
        project_info_layout = QFormLayout(project_info_group)
        self.project_name_display_label = QLabel("N/A")
        project_info_layout.addRow(QLabel("Current Project:"), self.project_name_display_label)
        self.job_number_input = QLineEdit()
        self.job_number_input.textChanged.connect(lambda: self.mark_project_modified(True))
        project_info_layout.addRow(QLabel("Job Number:"), self.job_number_input)
        self.analyst_name_input = QLineEdit()
        self.analyst_name_input.textChanged.connect(lambda: self.mark_project_modified(True))
        project_info_layout.addRow(QLabel("Analyst Name:"), self.analyst_name_input)
        self.main_layout.addWidget(project_info_group)

        self.view_stack = QStackedWidget()
        self.main_layout.addWidget(self.view_stack, 1)

        self.page_input = QWidget()
        self.page_input_layout = QVBoxLayout(self.page_input)

        self.spudcan_geometry_widget = SpudcanGeometryWidget()
        self.spudcan_geometry_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.spudcan_geometry_widget.validation_status_changed.connect(
            lambda status: self._handle_widget_validation_status_changed("spudcan_geometry", status)
        )
        self.page_input_layout.addWidget(self.spudcan_geometry_widget)

        self.soil_stratigraphy_widget = SoilStratigraphyWidget()
        self.soil_stratigraphy_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.page_input_layout.addWidget(self.soil_stratigraphy_widget)

        self.loading_conditions_widget = LoadingConditionsWidget()
        self.loading_conditions_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.loading_conditions_widget.validation_status_changed.connect(
            lambda status: self._handle_widget_validation_status_changed("loading_conditions", status)
        )
        self.page_input_layout.addWidget(self.loading_conditions_widget)

        self.analysis_control_widget = AnalysisControlWidget()
        self.analysis_control_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.analysis_control_widget.validation_status_changed.connect(
           lambda status: self._handle_widget_validation_status_changed("analysis_control", status)
        )
        self.page_input_layout.addWidget(self.analysis_control_widget)

        execution_group_box = QGroupBox("Execution Controls")
        execution_main_layout = QVBoxLayout(execution_group_box)
        self.workflow_indicator_layout = QHBoxLayout()
        self.stage_labels = {
            "setup": QLabel("Setup"), "mesh": QLabel("Mesh"),
            "calculate": QLabel("Calculate"), "results": QLabel("Results")
        }
        for label in self.stage_labels.values():
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFrameShape(QFrame.Shape.StyledPanel) # type: ignore
            self.workflow_indicator_layout.addWidget(label)
        execution_main_layout.addLayout(self.workflow_indicator_layout)
        self._update_workflow_stage("idle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(True)
        execution_main_layout.addWidget(self.progress_bar)
        execution_buttons_layout = QHBoxLayout()
        self.run_analysis_button = QPushButton("Run Analysis")
        self.run_analysis_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }")
        self.run_analysis_button.clicked.connect(self.on_run_analysis_clicked)
        execution_buttons_layout.addWidget(self.run_analysis_button)
        self.stop_analysis_button = QPushButton("Stop Analysis")
        self.stop_analysis_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }")
        self.stop_analysis_button.clicked.connect(self.on_stop_analysis_clicked)
        self.stop_analysis_button.setEnabled(False)
        execution_buttons_layout.addWidget(self.stop_analysis_button)
        execution_main_layout.addLayout(execution_buttons_layout)
        self.page_input_layout.addWidget(execution_group_box)
        self.page_input_layout.addStretch()
        self.view_stack.addWidget(self.page_input)

        self.page_results = QWidget()
        self.page_results_layout = QVBoxLayout(self.page_results)
        results_summary_group = QGroupBox("Key Results Summary")
        results_summary_form_layout = QFormLayout(results_summary_group)
        self.result_final_penetration_label = QLabel("N/A")
        self.result_peak_resistance_label = QLabel("N/A")
        results_summary_form_layout.addRow(QLabel("Final Penetration Depth:"), self.result_final_penetration_label)
        results_summary_form_layout.addRow(QLabel("Peak Vertical Resistance:"), self.result_peak_resistance_label)
        self.page_results_layout.addWidget(results_summary_group)
        results_plot_group = QGroupBox("Load-Penetration Curve")
        results_plot_layout = QVBoxLayout(results_plot_group)
        self.load_penetration_plot_widget = MplWidget()
        results_plot_layout.addWidget(self.load_penetration_plot_widget)
        self.page_results_layout.addWidget(results_plot_group, 1)
        results_table_group = QGroupBox("Detailed Results Data")
        results_table_layout = QVBoxLayout(results_table_group)
        self.results_table_widget = QTableWidget()
        self.results_table_widget.setColumnCount(2); self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])
        self.results_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); self.results_table_widget.setAlternatingRowColors(True)
        results_table_layout.addWidget(self.results_table_widget)
        self.page_results_layout.addWidget(results_table_group, 1)
        export_buttons_layout = QHBoxLayout()
        self.export_plot_button = QPushButton("Export Plot as Image"); self.export_plot_button.clicked.connect(self.on_export_plot)
        self.export_table_button = QPushButton("Export Table Data as CSV"); self.export_table_button.clicked.connect(self.on_export_table_data)
        export_buttons_layout.addStretch(); export_buttons_layout.addWidget(self.export_plot_button); export_buttons_layout.addWidget(self.export_table_button)
        self.page_results_layout.addLayout(export_buttons_layout)
        self.view_stack.addWidget(self.page_results)
        self.view_stack.setCurrentWidget(self.page_input)

        log_group_box = QGroupBox("Application Log")
        log_main_layout = QVBoxLayout(log_group_box)
        self.log_display_textedit = QTextEdit()
        self.log_display_textedit.setReadOnly(True)
        self.log_display_textedit.setFont(QFont("Courier New", 9))
        log_main_layout.addWidget(self.log_display_textedit)
        log_actions_layout = QHBoxLayout()
        self.open_log_dir_button = QPushButton("Open Log File Location")
        self.open_log_dir_button.clicked.connect(self.on_open_log_directory)
        log_actions_layout.addStretch(); log_actions_layout.addWidget(self.open_log_dir_button)
        log_main_layout.addLayout(log_actions_layout)
        self.main_layout.addWidget(log_group_box, 0)

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        self._setup_ui_logging()
        self._update_run_analysis_button_state()
        self.on_new_project(prompt_save=False)
        logger.info("MainWindow initialized.")

    @Slot(str, bool)
    def _handle_widget_validation_status_changed(self, widget_name: str, is_valid: bool):
        logger.debug(f"Validation status from {widget_name}: {is_valid}")
        if widget_name in self.widget_validation_states:
            self.widget_validation_states[widget_name] = is_valid
            self._update_run_analysis_button_state()
        else:
            logger.warning(f"Status for unknown widget: {widget_name}")

    def _update_run_analysis_button_state(self):
        project_exists = bool(self.current_project_data)
        all_valid = all(self.widget_validation_states.values())
        can_run = project_exists and all_valid
        self.run_analysis_button.setEnabled(can_run)
        # ... (tooltip logic as before) ...
        tooltip = ""
        if not can_run:
            if not project_exists: tooltip = "Create or load a project."
            elif not all_valid:
                invalid_widgets = [name.replace("_", " ").title() for name, v_status in self.widget_validation_states.items() if not v_status]
                tooltip = f"Invalid inputs in: {', '.join(invalid_widgets)}." if invalid_widgets else "Inputs require validation."
            else: tooltip = "Run Analysis disabled."
        else: tooltip = "Run PLAXIS analysis."
        self.run_analysis_button.setToolTip(tooltip)

    @Slot(str)
    def _append_log_message(self, message: str): self.log_display_textedit.append(message)
    def _setup_ui_logging(self):
        self.qt_log_handler = QtLoggingHandler() # No parent needed if signal name is explicit
        log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self.qt_log_handler.setFormatter(log_formatter)
        self.qt_log_handler.connect(self._append_log_message) # Use the provided connect method
        logging.getLogger().addHandler(self.qt_log_handler)
        self.qt_log_handler.setLevel(logging.INFO)

    def _create_actions(self):
        self.action_new_project = QAction(QIcon.fromTheme("document-new"), "&New Project", self)
        self.action_new_project.triggered.connect(lambda: self.on_new_project(prompt_save=True))
        self.action_open_project = QAction(QIcon.fromTheme("document-open"), "&Open Project...", self)
        self.action_open_project.setShortcut("Ctrl+O"); self.action_open_project.triggered.connect(self.on_open_project)
        self.action_save_project = QAction(QIcon.fromTheme("document-save"), "&Save Project", self)
        self.action_save_project.setShortcut("Ctrl+S"); self.action_save_project.triggered.connect(self.on_save_project)
        self.action_save_project_as = QAction(QIcon.fromTheme("document-save-as"), "Save Project &As...", self)
        self.action_save_project_as.triggered.connect(self.on_save_project_as)
        self.action_settings = QAction(QIcon.fromTheme("preferences-system"), "&Settings...", self)
        self.action_settings.triggered.connect(self.on_settings)
        self.action_exit = QAction(QIcon.fromTheme("application-exit"), "E&xit", self)
        self.action_exit.triggered.connect(self.close)
        self.action_view_input = QAction("Input Section", self); self.action_view_input.setCheckable(True); self.action_view_input.setChecked(True)
        self.action_view_input.triggered.connect(lambda: self.view_stack.setCurrentWidget(self.page_input))
        self.action_view_results = QAction("Results Section", self); self.action_view_results.setCheckable(True)
        self.action_view_results.triggered.connect(lambda: self.view_stack.setCurrentWidget(self.page_results))
        self.action_about = QAction(QIcon.fromTheme("help-about"), "&About", self)
        self.action_about.triggered.connect(self.on_about)
        self.mark_project_modified(False)

    @Slot()
    def on_open_log_directory(self):
        log_file_abs_path = os.path.abspath(LOG_FILENAME)
        log_dir = os.path.dirname(log_file_abs_path)
        if not os.path.isdir(log_dir): # Check if dir exists, not just the file
            log_dir = os.getcwd()
            QMessageBox.information(self, "Open Log Directory", f"Log directory for '{LOG_FILENAME}' might not exist yet or is not standard. Opening current directory: {log_dir}")
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(log_dir)):
            QMessageBox.warning(self, "Open Log Directory", f"Could not open log directory:\n{log_dir}")

    @Slot()
    def on_export_plot(self):
        # ... (implementation as before) ...
        logger.info("Export plot action triggered.")
        if not hasattr(self, 'load_penetration_plot_widget') or not self.load_penetration_plot_widget.figure:
            QMessageBox.warning(self, "Export Error", "No plot available to export.")
            return
        suggested_filename = "load_penetration_curve.png"
        if self.current_project_data and self.current_project_data.project_name and self.current_project_data.project_name != "Untitled Project":
            clean_proj_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in self.current_project_data.project_name)
            suggested_filename = f"{clean_proj_name}_load_penetration.png"
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Plot As Image", suggested_filename, "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG Files (*.svg);;PDF Files (*.pdf);;All Files (*)")
        if filePath:
            try:
                self.load_penetration_plot_widget.figure.tight_layout()
                self.load_penetration_plot_widget.figure.savefig(filePath, dpi=300)
                QMessageBox.information(self, "Export Successful", f"Plot saved to:\n{filePath}")
            except Exception as e: QMessageBox.critical(self, "Export Error", f"Could not save plot:\n{e}")

    @Slot()
    def on_export_table_data(self):
        # ... (implementation as before) ...
        logger.info("Export table data action triggered.")
        if not hasattr(self, 'results_table_widget') or self.results_table_widget.rowCount() == 0:
            QMessageBox.warning(self, "Export Error", "No table data available to export.")
            return
        suggested_filename = "results_data.csv"
        if self.current_project_data and self.current_project_data.project_name and self.current_project_data.project_name != "Untitled Project":
            clean_proj_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in self.current_project_data.project_name)
            suggested_filename = f"{clean_proj_name}_table_data.csv"
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Table Data As CSV", suggested_filename, "CSV Files (*.csv);;All Files (*)")
        if filePath:
            try:
                with open(filePath, 'w', newline='') as f:
                    headers = [self.results_table_widget.horizontalHeaderItem(i).text() for i in range(self.results_table_widget.columnCount())]
                    f.write(",".join(headers) + "\n")
                    for row in range(self.results_table_widget.rowCount()):
                        rowData = [self.results_table_widget.item(row, col).text() if self.results_table_widget.item(row, col) else "" for col in range(self.results_table_widget.columnCount())]
                        f.write(",".join(rowData) + "\n")
                QMessageBox.information(self, "Export Successful", f"Table data saved to:\n{filePath}")
            except Exception as e: QMessageBox.critical(self, "Export Error", f"Could not save table data:\n{e}")

    def _update_results_display(self):
        # ... (implementation mostly as before, ensure variables are defined before use) ...
        penetration_values, load_values = [], [] # Initialize here
        if self.current_project_data and self.current_project_data.analysis_results:
            results = self.current_project_data.analysis_results
            pen_depth = results.final_penetration_depth
            peak_res = results.peak_vertical_resistance
            self.result_final_penetration_label.setText(f"{pen_depth:.3f} m" if pen_depth is not None else "N/A")
            self.result_peak_resistance_label.setText(f"{peak_res:.2f} kN" if peak_res is not None else "N/A")
            if results.load_penetration_curve_data:
                try: # Simplified data extraction
                    valid_data = [item for item in results.load_penetration_curve_data if isinstance(item, dict)]
                    pen_load_pairs = [(item.get('penetration'), item.get('load')) for item in valid_data if item.get('penetration') is not None and item.get('load') is not None and isinstance(item.get('penetration'), (int,float)) and isinstance(item.get('load'),(int,float))]
                    if pen_load_pairs: penetration_values, load_values = zip(*pen_load_pairs)
                except Exception as e: logger.error(f"Error processing curve data: {e}", exc_info=True)
            # Plotting and table update logic as before...
            if penetration_values and load_values:
                self.load_penetration_plot_widget.plot_data(list(penetration_values), list(load_values), "Load vs. Penetration", f"Penetration ({SettingsDialog.get_units_system()})", f"Vertical Load ({SettingsDialog.get_units_system()})")
            else: self.load_penetration_plot_widget.plot_data([],[], "Load vs. Penetration (No Data)", "Penetration", "Vertical Load")
            self.results_table_widget.setRowCount(0)
            if penetration_values and load_values:
                self.results_table_widget.setRowCount(len(penetration_values))
                pen_unit, load_unit = SettingsDialog.get_units_system(), SettingsDialog.get_units_system()
                self.results_table_widget.setHorizontalHeaderLabels([f"Penetration ({pen_unit})", f"Load ({load_unit})"])
                for row, (pen, load_val) in enumerate(zip(penetration_values, load_values)):
                    self.results_table_widget.setItem(row, 0, QTableWidgetItem(f"{pen:.4f}")); self.results_table_widget.setItem(row, 1, QTableWidgetItem(f"{load_val:.2f}"))
            else: self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])
            self.view_stack.setCurrentWidget(self.page_results); self.action_view_results.setChecked(True); self.action_view_input.setChecked(False)
        else: # Clear results display
            self.result_final_penetration_label.setText("N/A"); self.result_peak_resistance_label.setText("N/A")
            if hasattr(self, 'load_penetration_plot_widget'): self.load_penetration_plot_widget.plot_data([],[], "Load vs. Penetration (No Data)", "Penetration", "Vertical Load")
            if hasattr(self, 'results_table_widget'): self.results_table_widget.setRowCount(0); self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])
        logger.info("Results display updated/cleared.")


    @Slot(str)
    def _update_workflow_stage(self, stage_key: str):
        default_style = "QLabel { background-color: lightgray; color: black; padding: 3px; border: 1px solid darkgray; }"
        active_style = "QLabel { background-color: #4CAF50; color: white; font-weight: bold; padding: 3px; border: 1px solid darkgreen; }"
        error_style = "QLabel { background-color: #f44336; color: white; font-weight: bold; padding: 3px; border: 1px solid darkred; }"
        for label in self.stage_labels.values(): label.setStyleSheet(default_style)
        if stage_key == "error":
             for label in self.stage_labels.values(): label.setStyleSheet(error_style)
        elif stage_key in ["setup_start", "setup_end"]: self.stage_labels["setup"].setStyleSheet(active_style)
        elif stage_key == "calculation_start": self.stage_labels["mesh"].setStyleSheet(active_style); self.stage_labels["calculate"].setStyleSheet(active_style)
        elif stage_key == "calculation_end": self.stage_labels["mesh"].setStyleSheet(active_style); self.stage_labels["calculate"].setStyleSheet(active_style)
        elif stage_key in ["results_start", "results_end", "finished_ok"]:
            self.stage_labels["results"].setStyleSheet(active_style)
            if stage_key == "finished_ok":
                 for label in self.stage_labels.values(): label.setStyleSheet(active_style)
        logger.debug(f"Workflow stage: {stage_key}")

    @Slot(int, int)
    def _update_progress_bar(self, current_value: int, max_value: int):
        if self.progress_bar.maximum() != max_value: self.progress_bar.setMaximum(max_value)
        self.progress_bar.setValue(current_value)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File"); view_menu = menu_bar.addMenu("&View"); help_menu = menu_bar.addMenu("&Help")
        file_menu.addActions([self.action_new_project, self.action_open_project, self.action_save_project, self.action_save_project_as])
        file_menu.addSeparator(); file_menu.addAction(self.action_settings); file_menu.addSeparator(); file_menu.addAction(self.action_exit)
        view_menu.addActions([self.action_view_input, self.action_view_results])
        help_menu.addAction(self.action_about)

    def _create_tool_bar(self):
        toolbar = QToolBar("Main Toolbar"); toolbar.setIconSize(QSize(24, 24)); self.addToolBar(toolbar)
        toolbar.addActions([self.action_new_project, self.action_open_project, self.action_save_project])

    def _create_status_bar(self):
        self.statusBar = QStatusBar(self); self.setStatusBar(self.statusBar); self.statusBar.showMessage("Ready", 3000)

    @Slot()
    def on_new_project(self, prompt_save=True):
        if prompt_save and self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes", "Save current project?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.on_save_project(): return
            elif ret == QMessageBox.StandardButton.Cancel: return
        self.current_project_data = ProjectSettings(); self.current_project_path = None
        self._update_ui_from_project_model(); self.mark_project_modified(False); self.update_window_title()
        for key in self.widget_validation_states: self.widget_validation_states[key] = True
        self._validate_all_input_widgets_quietly() # Ensure initial valid state for run button
        self.statusBar.showMessage("New project created.", 3000)

    @Slot()
    def on_open_project(self):
        if self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes", "Save current project?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.on_save_project(): return
            elif ret == QMessageBox.StandardButton.Cancel: return
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        if filepath:
            try:
                loaded_data = load_project(filepath)
                if loaded_data:
                    self.current_project_data = loaded_data; self.current_project_path = filepath
                    self._update_ui_from_project_model(); self.mark_project_modified(False); self.update_window_title()
                    self._validate_all_input_widgets_quietly()
                    self.statusBar.showMessage(f"Project '{filepath}' loaded.", 3000)
                else: QMessageBox.critical(self, "Load Error", f"Failed to load project from {filepath}.\nFile might be corrupted.")
            except Exception as e: QMessageBox.critical(self, "Load Error", f"An unexpected error occurred while loading project:\n{e}")
        else: self.statusBar.showMessage("Open project cancelled.", 2000)

    @Slot()
    def on_save_project(self) -> bool:
        if not self._validate_all_input_widgets():
            QMessageBox.warning(self, "Invalid Input", "Cannot save. Please correct invalid inputs."); return False
        if not self.current_project_data: QMessageBox.warning(self, "No Project", "No data to save."); return False
        if not self.current_project_path: return self.on_save_project_as()
        self._gather_data_from_ui_to_project_model()
        if save_project(self.current_project_data, self.current_project_path):
            self.mark_project_modified(False); self.statusBar.showMessage(f"Project saved: {self.current_project_path}", 3000); return True
        QMessageBox.critical(self, "Save Error", f"Failed to save to {self.current_project_path}."); return False

    @Slot()
    def on_save_project_as(self) -> bool:
        if not self._validate_all_input_widgets():
            QMessageBox.warning(self, "Invalid Input", "Cannot save. Please correct invalid inputs."); return False
        if not self.current_project_data: QMessageBox.warning(self, "No Project", "No data to save."); return False
        self._gather_data_from_ui_to_project_model()
        suggested_name = (self.current_project_data.project_name if self.current_project_data.project_name != "Untitled Project" else None) or \
                         (os.path.basename(self.current_project_path).split('.')[0] if self.current_project_path else "UntitledProject")
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project As", suggested_name + ".plaxauto", "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        if filepath:
            self.current_project_path = filepath
            self.current_project_data.project_name = os.path.splitext(os.path.basename(filepath))[0]
            if save_project(self.current_project_data, self.current_project_path):
                self.mark_project_modified(False); self.update_window_title(); self.statusBar.showMessage(f"Project saved: {self.current_project_path}", 3000); return True
            QMessageBox.critical(self, "Save Error", f"Failed to save to {self.current_project_path}."); return False
        return False

    def update_window_title(self):
        base = "PLAXIS 3D Spudcan Automation Tool"
        name = "Untitled Project"
        if self.current_project_data and self.current_project_data.project_name and self.current_project_data.project_name != "Untitled Project":
            name = self.current_project_data.project_name
        elif self.current_project_path: name = os.path.splitext(os.path.basename(self.current_project_path))[0]
        mod = "*" if self.project_modified else ""
        self.setWindowTitle(f"{name}{mod} - {base}"); self.project_name_display_label.setText(name)

    def _gather_data_from_ui_to_project_model(self):
        if not self.current_project_data: self.current_project_data = ProjectSettings()
        logger.info("Gathering data from UI to model.")
        spudcan_model = self.spudcan_geometry_widget.gather_data_to_model()
        if spudcan_model: self.current_project_data.spudcan = spudcan_model
        soil_data = self.soil_stratigraphy_widget.gather_data()
        self.current_project_data.soil_stratigraphy = soil_data.get("layers", [])
        self.current_project_data.water_table_depth = soil_data.get("water_table_depth")
        loading_model = self.loading_conditions_widget.gather_data_to_model()
        if loading_model: self.current_project_data.loading = loading_model
        analysis_model = self.analysis_control_widget.gather_data_to_model()
        if analysis_model: self.current_project_data.analysis_control = analysis_model
        self.current_project_data.job_number = self.job_number_input.text() or None
        self.current_project_data.analyst_name = self.analyst_name_input.text() or None

    def _update_ui_from_project_model(self):
        if not self.current_project_data:
            logger.warning("No project data for UI update. Resetting UI.")
            self.spudcan_geometry_widget.load_data(None) # Widgets handle None by resetting to defaults
            self.soil_stratigraphy_widget.load_data(None)
            self.loading_conditions_widget.load_data(None)
            self.analysis_control_widget.load_data(None)
            self.job_number_input.setText(""); self.analyst_name_input.setText("")
            self._clear_results_ui()
            return
        logger.info("Populating UI from model.")
        self.spudcan_geometry_widget.load_data(self.current_project_data.spudcan)
        self.soil_stratigraphy_widget.load_data(self.current_project_data)
        self.loading_conditions_widget.load_data(self.current_project_data.loading)
        self.analysis_control_widget.load_data(self.current_project_data.analysis_control)
        self.job_number_input.setText(self.current_project_data.job_number or "")
        self.analyst_name_input.setText(self.current_project_data.analyst_name or "")
        if self.current_project_data.analysis_results: self._update_results_display()
        else: self._clear_results_ui()
        self._validate_all_input_widgets_quietly()


    def _clear_results_ui(self):
        """Clears all result display areas."""
        self.result_final_penetration_label.setText("N/A")
        self.result_peak_resistance_label.setText("N/A")
        if hasattr(self, 'load_penetration_plot_widget'):
            self.load_penetration_plot_widget.clear_plot()
            self.load_penetration_plot_widget.plot_data([],[], "Load vs. Penetration (No Data)", "Penetration", "Vertical Load")
        if hasattr(self, 'results_table_widget'):
            self.results_table_widget.setRowCount(0)
            self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])
        logger.info("Results UI cleared.")


    def mark_project_modified(self, modified_status: bool = True):
        if not self.current_project_data and modified_status: self.project_modified = False
        else: self.project_modified = modified_status
        self.action_save_project.setEnabled(self.project_modified and bool(self.current_project_data))
        self.action_save_project_as.setEnabled(bool(self.current_project_data))
        self._update_run_analysis_button_state()
        self.update_window_title()

    @Slot()
    def on_run_analysis_clicked(self):
        logger.info("Run Analysis button clicked.")
        if not self._validate_all_input_widgets():
             QMessageBox.warning(self, "Invalid Input", "Please correct invalid inputs (marked red) before running analysis.")
             return
        if not self.current_project_data: return # Should be caught by button state

        self._gather_data_from_ui_to_project_model()

        # Final critical data check after gathering
        if not self.current_project_data.spudcan or \
           not self.current_project_data.spudcan.diameter or \
           not self.current_project_data.spudcan.height_cone_angle or \
           not self.current_project_data.soil_stratigraphy:
            QMessageBox.warning(self, "Incomplete Core Data", "Spudcan geometry and at least one soil layer must be defined and valid.")
            return

        plaxis_exe_path = SettingsDialog.get_plaxis_path() or \
                          (self.current_project_data.plaxis_installation_path if self.current_project_data else None) or \
                          os.getenv("PLAXIS_EXE_PATH")
        if not plaxis_exe_path:
            QMessageBox.warning(self, "PLAXIS Path Error", "PLAXIS installation path not configured.\nPlease set it via File > Settings."); return

        self.statusBar.showMessage("Starting analysis...", 0)
        self.run_analysis_button.setEnabled(False)
        self.stop_analysis_button.setEnabled(True)

        # --- Threaded Analysis ---
        if self.analysis_thread and self.analysis_thread.isRunning():
            QMessageBox.information(self, "Analysis Busy", "An analysis is already in progress.")
            return

        self.analysis_thread = QThread()
        self.analysis_worker = AnalysisWorker(plaxis_exe_path, self.current_project_data)
        self.analysis_worker.moveToThread(self.analysis_thread)

        # Connect worker signals to MainWindow slots
        self.analysis_worker.signals.analysis_stage_changed.connect(self._update_workflow_stage)
        self.analysis_worker.signals.progress_updated.connect(self._update_progress_bar)
        self.analysis_worker.signals.analysis_finished.connect(self._on_analysis_worker_finished)
        self.analysis_worker.signals.analysis_error.connect(self._on_analysis_worker_error)

        self.analysis_thread.started.connect(self.analysis_worker.run_analysis)
        self.analysis_worker.signals.finished.connect(self.analysis_thread.quit)
        self.analysis_worker.signals.finished.connect(self.analysis_worker.deleteLater)
        self.analysis_thread.finished.connect(self.analysis_thread.deleteLater)
        self.analysis_thread.finished.connect(self._on_thread_finished_cleanup) # Additional cleanup

        self.analysis_thread.start()

    @Slot(AnalysisResults)
    def _on_analysis_worker_finished(self, results: AnalysisResults):
        """Handles successful completion of analysis from worker thread."""
        logger.info("MainWindow: Received analysis_finished signal from worker.")
        if self.current_project_data:
            self.current_project_data.analysis_results = results
            self._update_results_display()
        QMessageBox.information(self, "Analysis Complete", "PLAXIS analysis workflow finished successfully.")
        self.statusBar.showMessage("Analysis complete.", 5000)
        self._update_workflow_stage("finished_ok") # Ensure final stage is green

    @Slot(str, str)
    def _on_analysis_worker_error(self, title: str, message: str):
        """Handles errors reported by the worker thread."""
        logger.error(f"MainWindow: Received analysis_error signal: {title} - {message}")
        QMessageBox.critical(self, title, message)
        self.statusBar.showMessage(f"Analysis failed: {title}", 7000)
        self._update_workflow_stage("error") # Mark workflow as error

    @Slot()
    def _on_thread_finished_cleanup(self):
        """General cleanup after the analysis thread finishes (success or error)."""
        logger.info("MainWindow: Analysis thread finished. Cleaning up.")
        self._update_run_analysis_button_state() # Re-evaluate run button
        self.stop_analysis_button.setEnabled(False)
        self.analysis_thread = None # Clear references
        self.analysis_worker = None

    def _validate_all_input_widgets(self, quiet: bool = False) -> bool:
        """
        Forces validation on all relevant input widgets and updates overall status.
        Args:
            quiet: If True, suppresses debug logging during this validation call.
        Returns: True if all are valid.
        """
        if not quiet: logger.debug("MainWindow: Validating all input widgets.")

        # Call is_valid() which should internally trigger validation and update styles
        self.widget_validation_states["spudcan_geometry"] = self.spudcan_geometry_widget.is_valid()
        self.widget_validation_states["loading_conditions"] = self.loading_conditions_widget.is_valid()
        self.widget_validation_states["analysis_control"] = self.analysis_control_widget.is_valid()
        # TODO: Add other widgets once they implement is_valid()
        # self.widget_validation_states["soil_stratigraphy"] = self.soil_stratigraphy_widget.is_valid()

        self._update_run_analysis_button_state()
        return all(self.widget_validation_states.values())

    def _validate_all_input_widgets_quietly(self):
        """Convenience method to call _validate_all_input_widgets without logging its own call."""
        self._validate_all_input_widgets(quiet=True)


    @Slot()
    def on_stop_analysis_clicked(self):
        """Handles the 'Stop Analysis' button click. Requests the worker to stop."""
        logger.info("Stop Analysis button clicked.")
        if self.analysis_worker and self.analysis_thread and self.analysis_thread.isRunning():
            self.statusBar.showMessage("Attempting to stop analysis...", 0)
            self.analysis_worker.request_stop()
            # Worker's finally block and signals will handle UI updates and thread cleanup.
            # Stop button will be re-enabled by _on_thread_finished_cleanup via _update_run_analysis_button_state
        else:
            QMessageBox.information(self, "Stop Analysis", "No analysis is currently running or worker not available.")
            self.stop_analysis_button.setEnabled(False) # Should already be if no analysis running
            self._update_run_analysis_button_state()


    @Slot()
    def on_settings(self):
        """Opens the application settings dialog."""
        logger.info("Settings action triggered.")
        dialog = SettingsDialog(self)
        if dialog.exec():
            logger.info("Settings dialog accepted.")
            self.statusBar.showMessage("Settings updated.", 3000)
            # Potentially re-check PLAXIS path if it affects run button state, though run button primarily checks on run click
            self._update_run_analysis_button_state()
        else:
            logger.info("Settings dialog cancelled.")
            self.statusBar.showMessage("Settings dialog cancelled.", 2000)

    @Slot()
    def on_about(self):
        """Displays the 'About' dialog."""
        self.statusBar.showMessage("Action: About triggered", 2000)
        QMessageBox.about(self, "About PLAXIS Spudcan Automation Tool",
                          "<p><b>PLAXIS 3D Spudcan Penetration Automation Tool</b></p>"
                          "<p>Version 0.4 (Jules Threaded)</p>"
                          "<p>This tool automates spudcan penetration analysis using PLAXIS.</p>"
                          "<p>Developed by AI Software Engineer, Jules.</p>")

    def closeEvent(self, event):
        """Handle window close event to ensure threads are stopped."""
        logger.info("Close event triggered. Checking for active analysis thread.")
        if self.analysis_thread and self.analysis_thread.isRunning():
            logger.info("Analysis thread is running. Requesting stop and attempting to wait.")
            if self.analysis_worker:
                self.analysis_worker.request_stop()

            # Give the thread a moment to finish after stop request
            # This is a simple wait; a more robust solution might involve a timeout
            # or ensuring the event loop processes events for the thread to finish.
            # For GUI apps, QApplication.processEvents() might be needed if the thread
            # doesn't terminate quickly.
            if not self.analysis_thread.wait(2000): # Wait up to 2 seconds
                 logger.warning("Analysis thread did not finish cleanly after 2 seconds on close. Forcing termination if possible.")
                 # self.analysis_thread.terminate() # Use with caution
            else:
                 logger.info("Analysis thread finished after stop request during close.")

        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    logging.basicConfig(
        level=logging.DEBUG, # DEBUG for more verbose output during development
        format="%(asctime)s - %(name)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
