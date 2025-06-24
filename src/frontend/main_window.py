"""
Main Window for the PLAXIS 3D Spudcan Automation Tool.
PRD Ref: Category 4 (Frontend Development: UI Shell & Framework)
Task 9.4 (Input Validation Feedback)
"""

import sys
import logging
import os
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QToolBar, QStatusBar, QStackedWidget, QFileDialog,
    QMessageBox, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QHBoxLayout, QTextEdit, QProgressBar, QFrame, QTableWidget, QHeaderView, QTableWidgetItem
)
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtCore import Qt, QSize, Slot

from backend.models import (
    ProjectSettings, SpudcanGeometry, SoilLayer, MaterialProperties,
    LoadingConditions, AnalysisControlParameters, AnalysisResults
)
from backend.project_io import save_project, load_project
from .widgets.spudcan_geometry_widget import SpudcanGeometryWidget
from .widgets.soil_stratigraphy_widget import SoilStratigraphyWidget
from .widgets.loading_conditions_widget import LoadingConditionsWidget
from .widgets.analysis_control_widget import AnalysisControlWidget
from .widgets.mpl_widget import MplWidget
from .qt_logging_handler import QtLoggingHandler
from .settings_dialog import SettingsDialog
from backend.plaxis_interactor.interactor import PlaxisInteractor
from backend.plaxis_interactor import geometry_builder, soil_builder, calculation_builder, results_parser
from backend.exceptions import ( # Ensure all are imported
    PlaxisAutomationError, PlaxisConnectionError, PlaxisConfigurationError,
    PlaxisCalculationError, PlaxisOutputError, PlaxisCliError, ProjectValidationError
)

from typing import Optional, Dict

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.current_project_data: Optional[ProjectSettings] = None
        self.current_project_path: Optional[str] = None
        self.project_modified: bool = False
        self.active_plaxis_interactor: Optional[PlaxisInteractor] = None

        # For input validation (Task 9.4)
        self.widget_validation_states: Dict[str, bool] = {
            "spudcan_geometry": True, # Assume valid initially until first check
            "soil_stratigraphy": True, # Placeholder, to be implemented
            "loading_conditions": True, # Placeholder
            "analysis_control": True,   # Placeholder
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
        # TODO: Connect validation_status_changed for soil_stratigraphy_widget
        # self.soil_stratigraphy_widget.validation_status_changed.connect(
        #     lambda status: self._handle_widget_validation_status_changed("soil_stratigraphy", status)
        # )
        self.page_input_layout.addWidget(self.soil_stratigraphy_widget)

        self.loading_conditions_widget = LoadingConditionsWidget()
        self.loading_conditions_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        # TODO: Connect validation_status_changed for loading_conditions_widget
        # self.loading_conditions_widget.validation_status_changed.connect(
        #     lambda status: self._handle_widget_validation_status_changed("loading_conditions", status)
        # )
        self.page_input_layout.addWidget(self.loading_conditions_widget)

        self.analysis_control_widget = AnalysisControlWidget()
        self.analysis_control_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        # TODO: Connect validation_status_changed for analysis_control_widget
        # self.analysis_control_widget.validation_status_changed.connect(
        #    lambda status: self._handle_widget_validation_status_changed("analysis_control", status)
        # )
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
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        execution_main_layout.addWidget(self.progress_bar)

        execution_buttons_layout = QHBoxLayout()
        self.run_analysis_button = QPushButton("Run Analysis")
        self.run_analysis_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }")
        self.run_analysis_button.clicked.connect(self.on_run_analysis_clicked)
        execution_buttons_layout.addWidget(self.run_analysis_button)

        self.pause_analysis_button = QPushButton("Pause Analysis")
        self.pause_analysis_button.setVisible(False)
        execution_buttons_layout.addWidget(self.pause_analysis_button)

        self.resume_analysis_button = QPushButton("Resume Analysis")
        self.resume_analysis_button.setVisible(False)
        execution_buttons_layout.addWidget(self.resume_analysis_button)

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
        self.results_table_widget.setColumnCount(2)
        self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])
        self.results_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table_widget.setAlternatingRowColors(True)
        results_table_layout.addWidget(self.results_table_widget)
        self.page_results_layout.addWidget(results_table_group, 1)

        export_buttons_layout = QHBoxLayout()
        self.export_plot_button = QPushButton("Export Plot as Image")
        self.export_plot_button.clicked.connect(self.on_export_plot)
        self.export_table_button = QPushButton("Export Table Data as CSV")
        self.export_table_button.clicked.connect(self.on_export_table_data)
        export_buttons_layout.addStretch()
        export_buttons_layout.addWidget(self.export_plot_button)
        export_buttons_layout.addWidget(self.export_table_button)
        self.page_results_layout.addLayout(export_buttons_layout)

        self.view_stack.addWidget(self.page_results)
        self.view_stack.setCurrentWidget(self.page_input)

        log_group_box = QGroupBox("Application Log")
        log_layout = QVBoxLayout(log_group_box)
        self.log_display_textedit = QTextEdit()
        self.log_display_textedit.setReadOnly(True)
        self.log_display_textedit.setFont(QFont("Courier New", 9))
        log_layout.addWidget(self.log_display_textedit)
        self.main_layout.addWidget(log_group_box, 0)

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        self._setup_ui_logging()

        self._update_run_analysis_button_state() # Initial state check

        self.on_new_project(prompt_save=False) # This will also call _update_run_analysis_button_state
        logger.info("MainWindow initialized and UI logger configured.")

    @Slot(str, bool)
    def _handle_widget_validation_status_changed(self, widget_name: str, is_valid: bool):
        logger.debug(f"Validation status changed for {widget_name}: {is_valid}")
        if widget_name in self.widget_validation_states:
            self.widget_validation_states[widget_name] = is_valid
            self._update_run_analysis_button_state()
        else:
            logger.warning(f"Received validation status for unknown widget: {widget_name}")

    def _update_run_analysis_button_state(self):
        """Enables or disables the 'Run Analysis' button based on overall validation status."""
        project_exists = bool(self.current_project_data)
        all_widgets_valid = all(self.widget_validation_states.values())

        can_run = project_exists and all_widgets_valid
        self.run_analysis_button.setEnabled(can_run)

        if not can_run:
            if not project_exists:
                self.run_analysis_button.setToolTip("Create or load a project to run analysis.")
            elif not all_widgets_valid:
                invalid_widgets = [name.replace("_", " ").title() for name, valid in self.widget_validation_states.items() if not valid]
                self.run_analysis_button.setToolTip(f"Cannot run analysis: Invalid inputs in {', '.join(invalid_widgets)} section(s).")
            else:
                 self.run_analysis_button.setToolTip("Run Analysis button is currently disabled.") # Generic fallback
        else:
            self.run_analysis_button.setToolTip("Run PLAXIS analysis with current settings.")
        logger.debug(f"Run analysis button enabled: {can_run} (Project: {project_exists}, All Widgets Valid: {all_widgets_valid})")


    @Slot(str)
    def _append_log_message(self, message: str):
        self.log_display_textedit.append(message)

    def _setup_ui_logging(self):
        self.qt_log_handler = QtLoggingHandler(self)
        log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self.qt_log_handler.setFormatter(log_formatter)
        self.qt_log_handler.connect(self._append_log_message)
        logging.getLogger().addHandler(self.qt_log_handler)
        self.qt_log_handler.setLevel(logging.INFO)
        logger.info("UI logging handler configured.")

    def _create_actions(self):
        self.action_new_project = QAction("&New Project", self)
        self.action_new_project.triggered.connect(lambda: self.on_new_project(prompt_save=True))
        self.action_open_project = QAction("&Open Project...", self)
        self.action_open_project.setShortcut("Ctrl+O")
        self.action_open_project.triggered.connect(self.on_open_project)
        self.action_save_project = QAction("&Save Project", self)
        self.action_save_project.setShortcut("Ctrl+S")
        self.action_save_project.triggered.connect(self.on_save_project)
        self.action_save_project_as = QAction("Save Project &As...", self)
        self.action_save_project_as.triggered.connect(self.on_save_project_as)
        self.action_settings = QAction("&Settings...", self)
        self.action_settings.triggered.connect(self.on_settings)
        self.action_exit = QAction("E&xit", self)
        self.action_exit.triggered.connect(self.close)
        self.action_view_input = QAction("Input Section", self)
        self.action_view_input.setCheckable(True)
        self.action_view_input.setChecked(True)
        self.action_view_input.triggered.connect(lambda: self.view_stack.setCurrentWidget(self.page_input))
        self.action_view_results = QAction("Results Section", self)
        self.action_view_results.setCheckable(True)
        self.action_view_results.triggered.connect(lambda: self.view_stack.setCurrentWidget(self.page_results))
        self.action_about = QAction("&About", self)
        self.action_about.triggered.connect(self.on_about)
        self.mark_project_modified(False) # Initial state for actions

    @Slot()
    def on_export_plot(self):
        logger.info("Export plot action triggered.")
        if not hasattr(self, 'load_penetration_plot_widget') or not self.load_penetration_plot_widget.figure:
            QMessageBox.warning(self, "Export Error", "No plot available to export.")
            return

        suggested_filename = "load_penetration_curve.png"
        if self.current_project_data and self.current_project_data.project_name and self.current_project_data.project_name != "Untitled Project":
            clean_proj_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in self.current_project_data.project_name)
            suggested_filename = f"{clean_proj_name}_load_penetration.png"

        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Plot As Image", suggested_filename,
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG Files (*.svg);;PDF Files (*.pdf);;All Files (*)"
        )

        if filePath:
            try:
                self.load_penetration_plot_widget.figure.savefig(filePath, dpi=300)
                logger.info(f"Plot saved to {filePath}")
                QMessageBox.information(self, "Export Successful", f"Plot saved to:\n{filePath}")
            except Exception as e:
                logger.error(f"Error saving plot to {filePath}: {e}", exc_info=True)
                QMessageBox.critical(self, "Export Error", f"Could not save plot:\n{e}")
        else:
            logger.info("Plot export cancelled by user.")

    @Slot()
    def on_export_table_data(self):
        logger.info("Export table data action triggered.")
        if not hasattr(self, 'results_table_widget') or self.results_table_widget.rowCount() == 0:
            QMessageBox.warning(self, "Export Error", "No table data available to export.")
            return

        suggested_filename = "results_data.csv"
        if self.current_project_data and self.current_project_data.project_name and self.current_project_data.project_name != "Untitled Project":
            clean_proj_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in self.current_project_data.project_name)
            suggested_filename = f"{clean_proj_name}_table_data.csv"

        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Table Data As CSV", suggested_filename, "CSV Files (*.csv);;All Files (*)"
        )

        if filePath:
            try:
                with open(filePath, 'w', newline='') as f:
                    header_labels = [self.results_table_widget.horizontalHeaderItem(i).text()
                                     for i in range(self.results_table_widget.columnCount())]
                    f.write(",".join(header_labels) + "\n")

                    for row in range(self.results_table_widget.rowCount()):
                        row_data = [self.results_table_widget.item(row, col).text() if self.results_table_widget.item(row, col) else ""
                                    for col in range(self.results_table_widget.columnCount())]
                        f.write(",".join(row_data) + "\n")

                logger.info(f"Table data saved to {filePath}")
                QMessageBox.information(self, "Export Successful", f"Table data saved to:\n{filePath}")
            except Exception as e:
                logger.error(f"Error saving table data to {filePath}: {e}", exc_info=True)
                QMessageBox.critical(self, "Export Error", f"Could not save table data:\n{e}")
        else:
            logger.info("Table data export cancelled by user.")

    def _update_results_display(self):
        if self.current_project_data and self.current_project_data.analysis_results:
            results = self.current_project_data.analysis_results
            pen_depth = results.final_penetration_depth
            peak_res = results.peak_vertical_resistance

            self.result_final_penetration_label.setText(f"{pen_depth:.3f} m" if pen_depth is not None else "N/A")
            self.result_peak_resistance_label.setText(f"{peak_res:.2f} kN" if peak_res is not None else "N/A")

            penetration_values, load_values = [], []
            if results.load_penetration_curve_data:
                try:
                    valid_data = [item for item in results.load_penetration_curve_data if isinstance(item, dict)]
                    if len(valid_data) != len(results.load_penetration_curve_data):
                        logger.warning("Some items in load_penetration_curve_data are not dictionaries.")

                    temp_pen_values = [item.get('penetration') for item in valid_data]
                    temp_load_values = [item.get('load') for item in valid_data]

                    pen_load_pairs = [(p, l) for p, l in zip(temp_pen_values, temp_load_values) if p is not None and l is not None]

                    if pen_load_pairs:
                        penetration_values = [p for p, l in pen_load_pairs]
                        load_values = [l for p, l in pen_load_pairs]

                    if not (all(isinstance(p, (int, float)) for p in penetration_values) and \
                            all(isinstance(l, (int, float)) for l in load_values) and \
                            len(penetration_values) == len(load_values)):
                        if penetration_values or load_values:
                            logger.warning("Load-penetration data malformed after filtering Nones. Clearing.")
                        penetration_values, load_values = [], []
                except Exception as e:
                    logger.error(f"Error processing load_penetration_curve_data: {e}", exc_info=True)
                    penetration_values, load_values = [], []

            if penetration_values and load_values:
                self.load_penetration_plot_widget.plot_data(
                    penetration_values, load_values, "Load vs. Penetration",
                    f"Penetration ({SettingsDialog.get_units_system()})", f"Vertical Load ({SettingsDialog.get_units_system()})"
                )
                logger.info("Load-penetration curve plotted.")
            else:
                self.load_penetration_plot_widget.clear_plot()
                self.load_penetration_plot_widget.plot_data([],[], "Load vs. Penetration (No Data)", "Penetration", "Vertical Load")

            self.results_table_widget.setRowCount(0)
            if penetration_values and load_values:
                self.results_table_widget.setRowCount(len(penetration_values))
                pen_unit, load_unit = SettingsDialog.get_units_system(), SettingsDialog.get_units_system()
                self.results_table_widget.setHorizontalHeaderLabels([f"Penetration ({pen_unit})", f"Load ({load_unit})"])
                for row, (pen, load_val) in enumerate(zip(penetration_values, load_values)):
                    self.results_table_widget.setItem(row, 0, QTableWidgetItem(f"{pen:.4f}"))
                    self.results_table_widget.setItem(row, 1, QTableWidgetItem(f"{load_val:.2f}"))
                logger.info(f"Results table populated with {len(penetration_values)} rows.")
            else:
                self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])

            self.view_stack.setCurrentWidget(self.page_results)
            self.action_view_results.setChecked(True)
            self.action_view_input.setChecked(False)
            logger.info("Results display updated.")
        else:
            self.result_final_penetration_label.setText("N/A")
            self.result_peak_resistance_label.setText("N/A")
            if hasattr(self, 'load_penetration_plot_widget'):
                self.load_penetration_plot_widget.clear_plot()
                self.load_penetration_plot_widget.plot_data([],[], "Load vs. Penetration (No Data)", "Penetration", "Vertical Load")
            if hasattr(self, 'results_table_widget'):
                self.results_table_widget.setRowCount(0)
                self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])
            logger.info("No analysis results. Plot and table cleared.")

    @Slot(str)
    def _update_workflow_stage(self, stage_key: str):
        default_style = "QLabel { background-color: lightgray; color: black; padding: 3px; border: 1px solid darkgray; }"
        active_style = "QLabel { background-color: #4CAF50; color: white; font-weight: bold; padding: 3px; border: 1px solid darkgreen; }"
        for label in self.stage_labels.values(): label.setStyleSheet(default_style)
        if stage_key in ["setup_start", "setup_end"]: self.stage_labels["setup"].setStyleSheet(active_style)
        elif stage_key in ["calculation_start", "calculation_end"]:
            self.stage_labels["mesh"].setStyleSheet(active_style)
            self.stage_labels["calculate"].setStyleSheet(active_style)
        elif stage_key in ["results_start", "results_end"]: self.stage_labels["results"].setStyleSheet(active_style)
        elif stage_key == "finished_ok":
            for label in self.stage_labels.values(): label.setStyleSheet(active_style)
        logger.debug(f"Workflow stage updated to: {stage_key}")

    @Slot(int, int)
    def _update_progress_bar(self, current_value: int, max_value: int):
        if self.progress_bar.maximum() != max_value: self.progress_bar.setMaximum(max_value)
        self.progress_bar.setValue(current_value)
        logger.debug(f"Progress bar: {current_value}/{max_value}")

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

    def on_new_project(self, prompt_save=True):
        if prompt_save and self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes", "Save current project?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.on_save_project(): return
            elif ret == QMessageBox.StandardButton.Cancel: return
        self.current_project_data = ProjectSettings(); self.current_project_path = None
        self._update_ui_from_project_model(); self.mark_project_modified(False); self.update_window_title()
        # Reset all widget validation states to true on new project, then re-check
        for key in self.widget_validation_states: self.widget_validation_states[key] = True # Assume valid
        self.widget_validation_states["spudcan_geometry"] = self.spudcan_geometry_widget.is_valid() # Re-check
        # TODO: Re-check other widgets once they have is_valid()
        self._update_run_analysis_button_state()
        self.statusBar.showMessage("New project created.", 3000)

    def on_open_project(self):
        if self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes", "Save current project?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.on_save_project(): return
            elif ret == QMessageBox.StandardButton.Cancel: return
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        if filepath:
            loaded_data = load_project(filepath)
            if loaded_data:
                self.current_project_data = loaded_data; self.current_project_path = filepath
                self._update_ui_from_project_model(); self.mark_project_modified(False); self.update_window_title()
                # After loading, widgets get new data, so their validation status should be re-checked
                self.widget_validation_states["spudcan_geometry"] = self.spudcan_geometry_widget.is_valid()
                # TODO: Re-check other widgets
                self._update_run_analysis_button_state()
                self.statusBar.showMessage(f"Project '{filepath}' loaded.", 3000)
            else: QMessageBox.critical(self, "Load Error", f"Failed to load project from {filepath}.")
        else: self.statusBar.showMessage("Open project cancelled.", 2000)

    def on_save_project(self) -> bool:
        if not self.current_project_data: QMessageBox.warning(self, "No Project", "No data to save."); return False
        if not self.current_project_path: return self.on_save_project_as()
        self._gather_data_from_ui_to_project_model()
        if save_project(self.current_project_data, self.current_project_path):
            self.mark_project_modified(False); self.statusBar.showMessage(f"Project saved to {self.current_project_path}", 3000); return True
        QMessageBox.critical(self, "Save Error", f"Failed to save to {self.current_project_path}."); return False

    def on_save_project_as(self) -> bool:
        if not self.current_project_data: QMessageBox.warning(self, "No Project", "No data to save."); return False
        self._gather_data_from_ui_to_project_model()
        suggested_name = (self.current_project_data.project_name if self.current_project_data.project_name != "Untitled Project" else None) or \
                         (os.path.basename(self.current_project_path).split('.')[0] if self.current_project_path else "UntitledProject")

        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project As", suggested_name, "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        if filepath:
            self.current_project_path = filepath
            base_name = os.path.basename(filepath)
            self.current_project_data.project_name = os.path.splitext(base_name)[0]
            if save_project(self.current_project_data, self.current_project_path):
                self.mark_project_modified(False); self.update_window_title(); self.statusBar.showMessage(f"Project saved to {self.current_project_path}", 3000); return True
            QMessageBox.critical(self, "Save Error", f"Failed to save to {self.current_project_path}."); return False
        return False

    def update_window_title(self):
        base = "PLAXIS 3D Spudcan Automation Tool"
        name = "Untitled Project"
        if self.current_project_data and self.current_project_data.project_name and self.current_project_data.project_name != "Untitled Project":
            name = self.current_project_data.project_name
        elif self.current_project_path:
            name = os.path.basename(self.current_project_path).split('.')[0]

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
            logger.warning("No project data to update UI from. Resetting UI.")
            self.spudcan_geometry_widget.load_data(SpudcanGeometry())
            self.soil_stratigraphy_widget.load_data(ProjectSettings())
            self.loading_conditions_widget.load_data(LoadingConditions())
            self.analysis_control_widget.load_data(AnalysisControlParameters())
            self.job_number_input.setText("")
            self.analyst_name_input.setText("")
            self.project_name_display_label.setText("N/A")
            if hasattr(self, 'load_penetration_plot_widget'): self.load_penetration_plot_widget.clear_plot()
            if hasattr(self, 'results_table_widget'): self.results_table_widget.setRowCount(0)
            # Reset validation states as well
            for key in self.widget_validation_states: self.widget_validation_states[key] = True # Assume valid on reset
            self.widget_validation_states["spudcan_geometry"] = self.spudcan_geometry_widget.is_valid() # Re-check default state
            # TODO: Re-check other widgets once they have is_valid() for their default states
            self._update_run_analysis_button_state()
            return

        logger.info("Populating UI from model.")
        self.spudcan_geometry_widget.load_data(self.current_project_data.spudcan)
        self.soil_stratigraphy_widget.load_data(self.current_project_data)
        self.loading_conditions_widget.load_data(self.current_project_data.loading)
        self.analysis_control_widget.load_data(self.current_project_data.analysis_control)
        self.job_number_input.setText(self.current_project_data.job_number or "")
        self.analyst_name_input.setText(self.current_project_data.analyst_name or "")
        if self.current_project_data.analysis_results:
            self._update_results_display()
        else:
            self.result_final_penetration_label.setText("N/A")
            self.result_peak_resistance_label.setText("N/A")
            if hasattr(self, 'load_penetration_plot_widget'):
                self.load_penetration_plot_widget.clear_plot()
                self.load_penetration_plot_widget.plot_data([],[], "Load vs. Penetration (No Data)", "Penetration", "Vertical Load")
            if hasattr(self, 'results_table_widget'):
                self.results_table_widget.setRowCount(0)
                self.results_table_widget.setHorizontalHeaderLabels(["Penetration", "Load"])

        # After loading data into widgets, their validation status should be re-checked
        self.widget_validation_states["spudcan_geometry"] = self.spudcan_geometry_widget.is_valid()
        # TODO: self.widget_validation_states["soil_stratigraphy"] = self.soil_stratigraphy_widget.is_valid()
        # TODO: self.widget_validation_states["loading_conditions"] = self.loading_conditions_widget.is_valid()
        # TODO: self.widget_validation_states["analysis_control"] = self.analysis_control_widget.is_valid()
        self._update_run_analysis_button_state()


    def mark_project_modified(self, modified_status: bool = True):
        if not self.current_project_data: self.project_modified = False
        else: self.project_modified = modified_status

        self.action_save_project.setEnabled(self.project_modified and bool(self.current_project_data))
        self.action_save_project_as.setEnabled(bool(self.current_project_data))

        self._update_run_analysis_button_state()
        self.update_window_title()

    def on_run_analysis_clicked(self):
        logger.info("Run Analysis button clicked.")
        if not self._validate_all_input_widgets(): # Explicitly validate all before run
             QMessageBox.warning(self, "Invalid Input",
                                "Please correct the invalid inputs (marked in red) before running the analysis.")
             return

        if not self.current_project_data:
            QMessageBox.warning(self, "No Project Data", "Please load or create a project before running analysis.")
            return
        self._gather_data_from_ui_to_project_model()

        if not self.current_project_data.spudcan.diameter or \
           not self.current_project_data.spudcan.height_cone_angle or \
           not self.current_project_data.soil_stratigraphy:
            QMessageBox.warning(self, "Incomplete Data", "Spudcan geometry (diameter, angle) and soil stratigraphy must be defined and valid.")
            return

        self.statusBar.showMessage("Starting analysis...", 0)
        self.run_analysis_button.setEnabled(False) # Disable during run
        self.stop_analysis_button.setEnabled(True)
        try:
            plaxis_exe_path = SettingsDialog.get_plaxis_path() or \
                              (self.current_project_data.plaxis_installation_path if self.current_project_data else None) or \
                              os.getenv("PLAXIS_EXE_PATH")
            if not plaxis_exe_path:
                QMessageBox.warning(self, "PLAXIS Path Error",
                                    "PLAXIS installation path not configured.\n"
                                    "Please set it via File > Settings.")
                self.statusBar.showMessage("Analysis aborted: PLAXIS path not configured.", 5000)
                self._update_run_analysis_button_state() # Re-evaluate based on current (still invalid) path state
                self.stop_analysis_button.setEnabled(False)
                return

            self.active_plaxis_interactor = PlaxisInteractor(plaxis_exe_path, self.current_project_data)
            self.active_plaxis_interactor.signals.analysis_stage_changed.connect(self._update_workflow_stage)
            self.active_plaxis_interactor.signals.progress_updated.connect(self._update_progress_bar)

            setup_calls = geometry_builder.get_spudcan_geometry_commands(self.current_project_data.spudcan) + \
                          soil_builder.get_soil_material_commands(self.current_project_data.soil_stratigraphy) + \
                          soil_builder.get_soil_stratigraphy_commands(self.current_project_data.soil_stratigraphy, self.current_project_data.water_table_depth)
            calc_calls = calculation_builder.get_full_calculation_workflow_commands(self.current_project_data)
            result_calls = results_parser.get_standard_results_commands(self.current_project_data)

            QApplication.processEvents(); self.active_plaxis_interactor.setup_model_in_plaxis(setup_calls, True)
            QApplication.processEvents(); self.active_plaxis_interactor.run_calculation(calc_calls)
            QApplication.processEvents(); raw_results = self.active_plaxis_interactor.extract_results(result_calls)

            if self.current_project_data:
                self.current_project_data.analysis_results = results_parser.compile_analysis_results(raw_results, self.current_project_data)
                self._update_results_display()

            QMessageBox.information(self, "Analysis Complete", "PLAXIS analysis workflow finished successfully.")
            self.statusBar.showMessage("Analysis complete.", 5000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("finished_ok")

        except PlaxisConnectionError as e:
            logger.error(f"PLAXIS Connection Error: {e}", exc_info=True)
            QMessageBox.critical(self, "PLAXIS Connection Error",
                                 f"Could not connect to PLAXIS services:\n{e}\n\n"
                                 "Please ensure PLAXIS is running, the API service is enabled, "
                                 "and the connection details (port, password) in settings are correct.")
            self.statusBar.showMessage(f"Analysis failed: Connection Error. Check PLAXIS API settings.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except PlaxisConfigurationError as e:
            logger.error(f"PLAXIS Configuration Error: {e}", exc_info=True)
            QMessageBox.warning(self, "PLAXIS Configuration Error",
                                f"There's an issue with the model or analysis configuration for PLAXIS:\n{e}\n\n"
                                "Please check your input parameters, soil definitions, and analysis settings.")
            self.statusBar.showMessage(f"Analysis failed: Configuration Error. Check inputs.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except PlaxisCalculationError as e:
            logger.error(f"PLAXIS Calculation Error: {e}", exc_info=True)
            QMessageBox.critical(self, "PLAXIS Calculation Error",
                                 f"PLAXIS reported an error during calculation:\n{e}\n\n"
                                 "This might be due to numerical issues, model instability, or other calculation problems. "
                                 "Review the PLAXIS output or log for more details if possible.")
            self.statusBar.showMessage(f"Analysis failed: Calculation Error.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except PlaxisOutputError as e:
            logger.error(f"PLAXIS Output Error: {e}", exc_info=True)
            QMessageBox.warning(self, "PLAXIS Output Error",
                                f"Could not retrieve or parse results from PLAXIS:\n{e}")
            self.statusBar.showMessage(f"Analysis failed: Error processing results.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except PlaxisCliError as e:
            logger.error(f"PLAXIS CLI Error: {e}", exc_info=True)
            QMessageBox.critical(self, "PLAXIS Scripting Error",
                                 f"An error occurred while trying to run a PLAXIS script (CLI):\n{e}\n\n"
                                 "Ensure the PLAXIS installation path is correct and scripting is enabled.")
            self.statusBar.showMessage(f"Analysis failed: CLI Scripting Error.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except ProjectValidationError as ve:
            logger.error(f"Project Validation Error: {ve}", exc_info=True)
            QMessageBox.warning(self, "Input Validation Error",
                                f"There is an issue with the provided input data:\n{ve}\n\n"
                                "Please review your inputs.")
            self.statusBar.showMessage(f"Analysis failed: Input Validation Error.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except PlaxisAutomationError as pae:
            logger.error(f"PLAXIS Automation Error: {pae}", exc_info=True)
            QMessageBox.critical(self, "PLAXIS Automation Error",
                                 f"An automation error occurred:\n{pae}")
            self.statusBar.showMessage(f"Analysis failed: {pae}", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
            QMessageBox.critical(self, "Unexpected Application Error",
                                 f"An unexpected error occurred in the application:\n{e}\n\n"
                                 "Please check the logs for more details.")
            self.statusBar.showMessage(f"Analysis failed with unexpected error.", 7000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("error")
        finally:
            self._update_run_analysis_button_state() # Re-evaluate run button state after attempt
            self.stop_analysis_button.setEnabled(False)
            if self.active_plaxis_interactor:
                self.active_plaxis_interactor.close_all_connections()
                self.active_plaxis_interactor = None

    def _validate_all_input_widgets(self) -> bool:
        """Forces validation on all relevant input widgets and updates overall status."""
        # Assuming each widget has an is_valid() method that performs its internal validation
        # and returns its status.
        self.widget_validation_states["spudcan_geometry"] = self.spudcan_geometry_widget.is_valid()
        # self.widget_validation_states["soil_stratigraphy"] = self.soil_stratigraphy_widget.is_valid()
        # self.widget_validation_states["loading_conditions"] = self.loading_conditions_widget.is_valid()
        # self.widget_validation_states["analysis_control"] = self.analysis_control_widget.is_valid()

        self._update_run_analysis_button_state() # Update button based on fresh validation
        return all(self.widget_validation_states.values())


    @Slot()
    def on_stop_analysis_clicked(self):
        if self.active_plaxis_interactor:
            self.statusBar.showMessage("Attempting to stop analysis...", 0); QApplication.processEvents()
            try: self.active_plaxis_interactor.attempt_stop_calculation(); QMessageBox.information(self, "Stop Analysis", "Stop request sent.")
            except Exception as e: logger.error(f"Stop error: {e}"); QMessageBox.warning(self, "Stop Error", str(e))
        else: QMessageBox.information(self, "Stop Analysis", "No active analysis.")
        self.stop_analysis_button.setEnabled(False)
        self._update_run_analysis_button_state()

    def on_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec(): logger.info("Settings accepted."); self.statusBar.showMessage("Settings updated.", 3000)
        else: logger.info("Settings cancelled."); self.statusBar.showMessage("Settings dialog cancelled.", 2000)

    def on_about(self):
        QMessageBox.about(self, "About PLAXIS Spudcan Automation Tool",
                          "<p><b>PLAXIS 3D Spudcan Penetration Automation Tool</b></p>"
                          "<p>Version 0.2 (Jules Enhanced)</p>"
                          "<p>This tool automates spudcan penetration analysis using PLAXIS.</p>")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
