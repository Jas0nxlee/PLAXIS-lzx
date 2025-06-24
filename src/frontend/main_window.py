"""
Main Window for the PLAXIS 3D Spudcan Automation Tool.
PRD Ref: Category 4 (Frontend Development: UI Shell & Framework)
"""

import sys
import logging
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QToolBar, QStatusBar, QStackedWidget, QFileDialog,
    QMessageBox, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QHBoxLayout, QTextEdit, QProgressBar, QFrame # Added QProgressBar, QFrame
)
from PySide6.QtGui import QAction, QIcon, QFont # Added QFont for monospaced log
from PySide6.QtCore import Qt, QSize, Slot # Added Slot

# Backend imports
from backend.models import (
    ProjectSettings, SpudcanGeometry, SoilLayer, MaterialProperties,
    LoadingConditions, AnalysisControlParameters, AnalysisResults
)
from backend.project_io import save_project, load_project

# Frontend imports
from .widgets.spudcan_geometry_widget import SpudcanGeometryWidget
from .widgets.soil_stratigraphy_widget import SoilStratigraphyWidget
from .widgets.loading_conditions_widget import LoadingConditionsWidget
from .widgets.analysis_control_widget import AnalysisControlWidget
from .qt_logging_handler import QtLoggingHandler # Import the new handler
from .settings_dialog import SettingsDialog # Import SettingsDialog

# Backend interactor and builders
from backend.plaxis_interactor.interactor import PlaxisInteractor
from backend.plaxis_interactor import geometry_builder, soil_builder, calculation_builder, results_parser
from backend.exceptions import PlaxisAutomationError


from typing import Optional

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Main application window.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.current_project_data: Optional[ProjectSettings] = None
        self.current_project_path: Optional[str] = None
        self.project_modified: bool = False
        self.active_plaxis_interactor: Optional[PlaxisInteractor] = None # For managing active analysis

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
        self.page_input_layout.addWidget(self.spudcan_geometry_widget)

        self.soil_stratigraphy_widget = SoilStratigraphyWidget()
        self.soil_stratigraphy_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.page_input_layout.addWidget(self.soil_stratigraphy_widget)

        self.loading_conditions_widget = LoadingConditionsWidget()
        self.loading_conditions_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.page_input_layout.addWidget(self.loading_conditions_widget)

        self.analysis_control_widget = AnalysisControlWidget()
        self.analysis_control_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.page_input_layout.addWidget(self.analysis_control_widget)

        execution_group_box = QGroupBox("Execution Controls")
        execution_main_layout = QVBoxLayout(execution_group_box) # Main layout for this group

        # Workflow Indicator (Task 7.2.1)
        self.workflow_indicator_layout = QHBoxLayout()
        self.stage_labels = {
            "setup": QLabel("Setup"),
            "mesh": QLabel("Mesh"), # Mesh is part of calculation_builder now
            "calculate": QLabel("Calculate"),
            "results": QLabel("Results")
        }
        for stage_name, label in self.stage_labels.items():
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFrameShape(QFrame.Shape.StyledPanel) # type: ignore
            self.workflow_indicator_layout.addWidget(label)
        execution_main_layout.addLayout(self.workflow_indicator_layout)
        self._update_workflow_stage("idle") # Initial state

        # Progress Bar (Task 7.3.1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        execution_main_layout.addWidget(self.progress_bar)

        # Execution Buttons
        execution_buttons_layout = QHBoxLayout()
        self.run_analysis_button = QPushButton("Run Analysis")
        self.run_analysis_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }")
        self.run_analysis_button.clicked.connect(self.on_run_analysis_clicked)
        execution_buttons_layout.addWidget(self.run_analysis_button)

        self.pause_analysis_button = QPushButton("Pause Analysis")
        self.pause_analysis_button.setStyleSheet("QPushButton { background-color: #ff9800; color: white; padding: 6px; border-radius: 3px; }")
        self.pause_analysis_button.clicked.connect(self.on_pause_analysis_clicked)
        self.pause_analysis_button.setEnabled(False)
        self.pause_analysis_button.setVisible(False) # Hidden as it's not feasible
        execution_buttons_layout.addWidget(self.pause_analysis_button)

        self.resume_analysis_button = QPushButton("Resume Analysis")
        self.resume_analysis_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 6px; border-radius: 3px; }")
        self.resume_analysis_button.clicked.connect(self.on_resume_analysis_clicked)
        self.resume_analysis_button.setEnabled(False)
        self.resume_analysis_button.setVisible(False) # Hidden as it's not feasible
        execution_buttons_layout.addWidget(self.resume_analysis_button)

        self.stop_analysis_button = QPushButton("Stop Analysis")
        self.stop_analysis_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }") # Red
        self.stop_analysis_button.clicked.connect(self.on_stop_analysis_clicked)
        self.stop_analysis_button.setEnabled(False) # Disabled initially
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
        # Add more labels as key results are defined

        results_summary_form_layout.addRow(QLabel("Final Penetration Depth:"), self.result_final_penetration_label)
        results_summary_form_layout.addRow(QLabel("Peak Vertical Resistance:"), self.result_peak_resistance_label)

        self.page_results_layout.addWidget(results_summary_group)
        self.page_results_layout.addStretch() # Push summary to the top

        self.view_stack.addWidget(self.page_results)

        self.view_stack.setCurrentWidget(self.page_input)

        # --- Log Display Area ---
        log_group_box = QGroupBox("Application Log")
        log_layout = QVBoxLayout(log_group_box)
        self.log_display_textedit = QTextEdit()
        self.log_display_textedit.setReadOnly(True)
        self.log_display_textedit.setFont(QFont("Courier New", 9)) # Monospaced font for logs
        log_layout.addWidget(self.log_display_textedit)
        # Add log display to the main layout, perhaps make it collapsible or in a tab later
        # For now, adding it below the view_stack with a smaller stretch factor
        self.main_layout.addWidget(log_group_box, 0) # Stretch factor 0 for log

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        self._setup_ui_logging() # Setup logging to QTextEdit

        self.on_new_project(prompt_save=False)
        logger.info("MainWindow initialized and UI logger configured.")

    @Slot(str)
    def _append_log_message(self, message: str):
        """Appends a formatted log message to the QTextEdit."""
        self.log_display_textedit.append(message)
        # Optional: Auto-scroll to the bottom
        # self.log_display_textedit.verticalScrollBar().setValue(self.log_display_textedit.verticalScrollBar().maximum())

    def _setup_ui_logging(self):
        """Sets up the QtLoggingHandler to route log messages to the UI."""
        self.qt_log_handler = QtLoggingHandler(self) # Pass self as parent

        # Configure formatter for the Qt handler (can be same or different from console/file)
        log_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        ) # Simpler format for UI
        self.qt_log_handler.setFormatter(log_formatter)
        self.qt_log_handler.connect(self._append_log_message)

        # Add this handler to the root logger
        logging.getLogger().addHandler(self.qt_log_handler)
        # Optionally set a specific level for this handler if different from root
        self.qt_log_handler.setLevel(logging.INFO) # Show INFO and above in UI log

        logger.info("UI logging handler configured and attached to root logger.")


    def _create_actions(self):
        self.action_new_project = QAction("&New Project", self)
        self.action_new_project.triggered.connect(lambda: self.on_new_project(prompt_save=True)) # Ensure prompt
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
        self.mark_project_modified(False)

    def _update_results_display(self):
        """Updates the result labels from self.current_project_data.analysis_results."""
        if self.current_project_data and self.current_project_data.analysis_results:
            results = self.current_project_data.analysis_results
            pen_depth = results.final_penetration_depth
            peak_res = results.peak_vertical_resistance

            self.result_final_penetration_label.setText(f"{pen_depth:.3f} m" if pen_depth is not None else "N/A")
            self.result_peak_resistance_label.setText(f"{peak_res:.2f} kN" if peak_res is not None else "N/A")

            # Switch to results page
            self.view_stack.setCurrentWidget(self.page_results)
            self.action_view_results.setChecked(True)
            self.action_view_input.setChecked(False)
            logger.info("Results display updated.")
        else:
            self.result_final_penetration_label.setText("N/A")
            self.result_peak_resistance_label.setText("N/A")
            logger.info("No analysis results to display or results are empty.")

    @Slot(str)
    def _update_workflow_stage(self, stage_key: str):
        """Updates the visual workflow indicator."""
        # Reset all to default style
        default_style = "QLabel { background-color: lightgray; color: black; padding: 3px; border: 1px solid darkgray; }"
        active_style = "QLabel { background-color: #4CAF50; color: white; font-weight: bold; padding: 3px; border: 1px solid darkgreen; }"

        for label in self.stage_labels.values():
            label.setStyleSheet(default_style)

        if stage_key == "setup_start" or stage_key == "setup_end":
            self.stage_labels["setup"].setStyleSheet(active_style)
        elif stage_key == "calculation_start" or stage_key == "calculation_end":
             # Assuming mesh is part of calculation_start internally now
            self.stage_labels["mesh"].setStyleSheet(active_style) # Show mesh as active during calc
            self.stage_labels["calculate"].setStyleSheet(active_style)
        elif stage_key == "results_start" or stage_key == "results_end":
            self.stage_labels["results"].setStyleSheet(active_style)
        elif stage_key == "finished_ok":
            for label in self.stage_labels.values(): # All green if successfully finished
                 label.setStyleSheet(active_style)
        elif stage_key == "error" or stage_key == "idle":
             pass # Default style already applied, or could apply a specific error style

        logger.debug(f"Workflow stage updated to: {stage_key}")

    @Slot(int, int)
    def _update_progress_bar(self, current_value: int, max_value: int):
        """Updates the overall progress bar."""
        if self.progress_bar.maximum() != max_value:
            self.progress_bar.setMaximum(max_value)
        self.progress_bar.setValue(current_value)
        logger.debug(f"Progress bar updated: {current_value}/{max_value}")


    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_new_project)
        file_menu.addAction(self.action_open_project)
        file_menu.addAction(self.action_save_project)
        file_menu.addAction(self.action_save_project_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_settings)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.action_view_input)
        view_menu.addAction(self.action_view_results)
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.action_about)

    def _create_tool_bar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        toolbar.addAction(self.action_new_project)
        toolbar.addAction(self.action_open_project)
        toolbar.addAction(self.action_save_project)

    def _create_status_bar(self):
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready", 3000)

    def on_new_project(self, prompt_save=True):
        logger.info("Action: New Project")
        if prompt_save and self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes",
                                       "Current project has unsaved changes. Save before creating a new one?",
                                       QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.on_save_project(): return
            elif ret == QMessageBox.StandardButton.Cancel:
                return

        self.current_project_data = ProjectSettings()
        self.current_project_path = None
        self._update_ui_from_project_model()
        self.mark_project_modified(False)
        self.update_window_title()
        self.statusBar.showMessage("New project created.", 3000)

    def on_open_project(self):
        logger.info("Action: Open Project")
        if self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes", "Save current project before opening another?",
                                       QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.on_save_project(): return
            elif ret == QMessageBox.StandardButton.Cancel:
                return

        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        if filepath:
            loaded_data = load_project(filepath)
            if loaded_data:
                self.current_project_data = loaded_data
                self.current_project_path = filepath
                self._update_ui_from_project_model()
                self.mark_project_modified(False)
                self.update_window_title()
                self.statusBar.showMessage(f"Project '{filepath}' loaded.", 3000)
            else:
                QMessageBox.critical(self, "Load Error", f"Failed to load project from {filepath}.")
        else:
            self.statusBar.showMessage("Open project cancelled.", 2000)

    def on_save_project(self) -> bool:
        logger.info("Action: Save Project")
        if not self.current_project_data:
            QMessageBox.warning(self, "No Project", "No data to save.")
            return False
        if not self.current_project_path:
            return self.on_save_project_as()
        else:
            self._gather_data_from_ui_to_project_model()
            if save_project(self.current_project_data, self.current_project_path):
                self.mark_project_modified(False)
                self.statusBar.showMessage(f"Project saved to {self.current_project_path}", 3000)
                return True
            else:
                QMessageBox.critical(self, "Save Error", f"Failed to save to {self.current_project_path}.")
                return False

    def on_save_project_as(self) -> bool:
        logger.info("Action: Save Project As")
        if not self.current_project_data:
            QMessageBox.warning(self, "No Project", "No data to save.")
            return False
        self._gather_data_from_ui_to_project_model()

        suggested_name = self.current_project_data.project_name or "UntitledProject"
        if self.current_project_path:
            suggested_name = self.current_project_path.split('/')[-1].split('\\')[-1]

        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project As", suggested_name, "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        if filepath:
            self.current_project_path = filepath
            if not self.current_project_data.project_name or self.current_project_data.project_name == "Untitled Project":
                base_name = filepath.split('/')[-1].split('\\')[-1]
                self.current_project_data.project_name = base_name.split('.')[0] if '.' in base_name else base_name

            if save_project(self.current_project_data, self.current_project_path):
                self.mark_project_modified(False)
                self.update_window_title()
                self.statusBar.showMessage(f"Project saved to {self.current_project_path}", 3000)
                return True
            else:
                QMessageBox.critical(self, "Save Error", f"Failed to save to {self.current_project_path}.")
                return False
        return False

    def update_window_title(self):
        base_title = "PLAXIS 3D Spudcan Automation Tool"
        project_name_display = "Untitled Project"
        if self.current_project_path:
            project_name_display = self.current_project_path.split('/')[-1].split('\\')[-1]
        elif self.current_project_data and self.current_project_data.project_name not in [None, "Untitled Project"]:
             project_name_display = self.current_project_data.project_name
        modified_indicator = "*" if self.project_modified else ""
        self.setWindowTitle(f"{project_name_display}{modified_indicator} - {base_title}")
        self.project_name_display_label.setText(project_name_display) # Update dedicated label too

    def _gather_data_from_ui_to_project_model(self):
        if not self.current_project_data:
            self.current_project_data = ProjectSettings()
            logger.warning("Gathering data but current_project_data was None. Initialized new.")
        logger.info("Gathering data from UI fields into self.current_project_data model.")

        spudcan_ui_data = self.spudcan_geometry_widget.gather_data()
        self.current_project_data.spudcan.diameter = spudcan_ui_data.get('diameter')
        self.current_project_data.spudcan.height_cone_angle = spudcan_ui_data.get('height_cone_angle')

        soil_widget_data = self.soil_stratigraphy_widget.gather_data()
        self.current_project_data.soil_stratigraphy = soil_widget_data.get("layers", [])
        self.current_project_data.water_table_depth = soil_widget_data.get("water_table_depth")

        loading_ui_data = self.loading_conditions_widget.gather_data()
        self.current_project_data.loading.vertical_preload = loading_ui_data.get('vertical_preload')
        self.current_project_data.loading.target_type = loading_ui_data.get('target_type')
        self.current_project_data.loading.target_penetration_or_load = loading_ui_data.get('target_penetration_or_load')

        if hasattr(self, 'analysis_control_widget'):
            gathered_analysis_data = self.analysis_control_widget.gather_data()
            if not self.current_project_data.analysis_control:
                self.current_project_data.analysis_control = AnalysisControlParameters()
            ac = self.current_project_data.analysis_control
            ac.meshing_global_coarseness = gathered_analysis_data.get("meshing_global_coarseness")
            ac.meshing_refinement_spudcan = gathered_analysis_data.get("meshing_refinement_spudcan")
            ac.initial_stress_method = gathered_analysis_data.get("initial_stress_method")
            ac.MaxIterations = gathered_analysis_data.get("MaxIterations")
            ac.ToleratedError = gathered_analysis_data.get("ToleratedError")
            ac.ResetDispToZero = gathered_analysis_data.get("ResetDispToZero")

        self.current_project_data.job_number = self.job_number_input.text() or None
        self.current_project_data.analyst_name = self.analyst_name_input.text() or None

        if (not self.current_project_data.project_name or \
            self.current_project_data.project_name == "Untitled Project") and \
            self.current_project_path:
             base_name = self.current_project_path.split('/')[-1].split('\\')[-1]
             self.current_project_data.project_name = base_name.split('.')[0] if '.' in base_name else base_name
        logger.debug(f"Gathered project settings updated: {self.current_project_data.project_name}")

    def _update_ui_from_project_model(self):
        if not self.current_project_data:
            logger.warning("_update_ui_from_project_model called with no current_project_data. Resetting UI.")
            self.spudcan_geometry_widget.load_data(None)
            self.soil_stratigraphy_widget.load_data(None)
            self.loading_conditions_widget.load_data(None)
            if hasattr(self, 'analysis_control_widget'):
                self.analysis_control_widget.load_data(None)
            self.job_number_input.setText("")
            self.analyst_name_input.setText("")
            self.project_name_display_label.setText("N/A")
            return
        logger.info("Populating UI fields from self.current_project_data model.")

        self.spudcan_geometry_widget.load_data(self.current_project_data.spudcan)
        self.soil_stratigraphy_widget.load_data(self.current_project_data)
        self.loading_conditions_widget.load_data(self.current_project_data.loading)
        if hasattr(self, 'analysis_control_widget'):
           self.analysis_control_widget.load_data(self.current_project_data.analysis_control)

        self.job_number_input.setText(self.current_project_data.job_number or "")
        self.analyst_name_input.setText(self.current_project_data.analyst_name or "")
        self.project_name_display_label.setText(self.current_project_data.project_name or "Untitled Project")

    def mark_project_modified(self, modified_status: bool = True):
        if not self.current_project_data:
            self.action_save_project.setEnabled(False)
            self.action_save_project_as.setEnabled(False)
            if hasattr(self, 'run_analysis_button'): self.run_analysis_button.setEnabled(False)
            if self.project_modified != False:
                self.project_modified = False
                self.update_window_title()
            return

        if self.project_modified != modified_status:
            self.project_modified = modified_status

        can_save = self.project_modified and bool(self.current_project_data)
        self.action_save_project.setEnabled(can_save)
        self.update_window_title()

        can_save_as_or_run = bool(self.current_project_data)
        self.action_save_project_as.setEnabled(can_save_as_or_run)
        if hasattr(self, 'run_analysis_button'): self.run_analysis_button.setEnabled(can_save_as_or_run)

    def on_run_analysis_clicked(self):
        logger.info("Run Analysis button clicked.")
        if not self.current_project_data:
            QMessageBox.warning(self, "No Project Data", "Please load or create a project before running analysis.")
            return

        self._gather_data_from_ui_to_project_model()

        if not self.current_project_data.spudcan.diameter or \
           not self.current_project_data.soil_stratigraphy:
            QMessageBox.warning(self, "Incomplete Data", "Spudcan geometry and soil stratigraphy must be defined.")
            return

        logger.info(f"Attempting to run analysis with data: {self.current_project_data}")
        self.statusBar.showMessage("Starting analysis...", 0)
        self.run_analysis_button.setEnabled(False)
        self.stop_analysis_button.setEnabled(True)

        # TODO: Consider running this in a QThread to keep UI responsive
        try:
            # Get PLAXIS path: Prioritize QSettings, then project data, then environment variable
            plaxis_exe_path = SettingsDialog.get_plaxis_path()

            if not plaxis_exe_path and self.current_project_data:
                plaxis_exe_path = self.current_project_data.plaxis_installation_path
                if plaxis_exe_path:
                    logger.info(f"Using PLAXIS path from current project settings: {plaxis_exe_path}")

            if not plaxis_exe_path:
                plaxis_exe_path = os.getenv("PLAXIS_EXE_PATH")
                if plaxis_exe_path:
                    logger.info(f"Using PLAXIS path from environment variable (PLAXIS_EXE_PATH): {plaxis_exe_path}")

            if not plaxis_exe_path:
                QMessageBox.warning(self, "Configuration Error",
                                    "PLAXIS installation path not configured.\n"
                                    "Please set it via File > Settings, or ensure it's in the project file, "
                                    "or set the PLAXIS_EXE_PATH environment variable.")
                self.statusBar.showMessage("Analysis aborted: PLAXIS path not configured.", 5000)
                self.run_analysis_button.setEnabled(True)
                return

            # If a path was found and it wasn't from QSettings, and current_project_data exists, update it.
            if self.current_project_data and self.current_project_data.plaxis_installation_path != plaxis_exe_path :
                 if SettingsDialog.get_plaxis_path() is None : # only update project data if not from global settings
                      logger.info(f"Updating project's PLAXIS path to: {plaxis_exe_path}")
                      self.current_project_data.plaxis_installation_path = plaxis_exe_path
                      self.mark_project_modified(True) # Project data changed
            # Create and store the interactor instance
            self.active_plaxis_interactor = PlaxisInteractor(
                plaxis_path=plaxis_exe_path, # Must be set
                project_settings=self.current_project_data
            )
            # Connect signals from interactor to MainWindow slots
            self.active_plaxis_interactor.signals.analysis_stage_changed.connect(self._update_workflow_stage)
            self.active_plaxis_interactor.signals.progress_updated.connect(self._update_progress_bar)


            # 1. Define Model Setup Callables
            model_setup_callables = []
            model_setup_callables.extend(geometry_builder.get_spudcan_geometry_commands(self.current_project_data.spudcan))
            model_setup_callables.extend(soil_builder.get_soil_material_commands(self.current_project_data.soil_stratigraphy))
            model_setup_callables.extend(soil_builder.get_soil_stratigraphy_commands(self.current_project_data.soil_stratigraphy, self.current_project_data.water_table_depth))
            # Add more setup commands as needed (e.g., structures, initial conditions not part of phases)

            # 2. Define Calculation Run Callables
            # These include creating phases, assigning loads, meshing, and running calculations
            calculation_run_callables = calculation_builder.get_full_calculation_workflow_commands(
                project_settings=self.current_project_data
            ) # This function needs to be smart

            # 3. Define Results Extraction Callables
            results_extraction_callables = results_parser.get_standard_results_commands(self.current_project_data)


            # Execute workflow
            self.statusBar.showMessage("Setting up PLAXIS model...", 0)
            QApplication.processEvents() # Keep UI responsive
            if self.active_plaxis_interactor:
                self.active_plaxis_interactor.setup_model_in_plaxis(model_setup_callables, is_new_project=True) # Assuming new project for now

            self.statusBar.showMessage("Running PLAXIS calculation...", 0)
            QApplication.processEvents()
            if self.active_plaxis_interactor:
                self.active_plaxis_interactor.run_calculation(calculation_run_callables)

            self.statusBar.showMessage("Extracting results...", 0)
            QApplication.processEvents()
            raw_results_data = []
            if self.active_plaxis_interactor:
                # raw_results_data will be a list of whatever each result callable returns
                raw_results_data = self.active_plaxis_interactor.extract_results(results_extraction_callables)

            # Process raw_results_data into AnalysisResults object
            if self.current_project_data: # Ensure current_project_data is still valid
                # The results_parser.compile_analysis_results needs to be implemented
                # For now, creating a placeholder AnalysisResults or handling raw data directly
                # This part needs a robust results_parser.compile_analysis_results function.
                # Let's assume results_parser.compile_analysis_results populates an AnalysisResults object
                # and attaches it to self.current_project_data.analysis_results

                # Placeholder: Manually create AnalysisResults for demonstration
                # In reality, this would come from parsing raw_results_data
                compiled_results = results_parser.compile_analysis_results(raw_results_data, self.current_project_data)
                self.current_project_data.analysis_results = compiled_results
                logger.info(f"Compiled analysis results: {compiled_results}")
                self._update_results_display() # Update UI with results
            else:
                logger.error("current_project_data became None during analysis run unexpectedly.")
                QMessageBox.critical(self, "Internal Error", "Project data lost during analysis.")


            QMessageBox.information(self, "Analysis Complete", "PLAXIS analysis workflow finished successfully.")
            self.statusBar.showMessage("Analysis complete.", 5000)
            if self.active_plaxis_interactor: self.active_plaxis_interactor.signals.analysis_stage_changed.emit("finished_ok")


        except PlaxisAutomationError as pae:
            logger.error(f"PLAXIS Automation Error: {pae}", exc_info=True)
            QMessageBox.critical(self, "PLAXIS Error", f"An error occurred during PLAXIS automation:\n{pae}")
            self.statusBar.showMessage(f"Analysis failed: {pae}", 5000)
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred:\n{e}")
            self.statusBar.showMessage(f"Analysis failed with unexpected error: {e}", 5000)
        finally:
            self.run_analysis_button.setEnabled(True)
            self.stop_analysis_button.setEnabled(False)
            if self.active_plaxis_interactor:
                self.active_plaxis_interactor.close_all_connections() # Ensure connections are closed
                self.active_plaxis_interactor = None # Clear active interactor
            logger.info("Run analysis routine finished.")

    @Slot()
    def on_stop_analysis_clicked(self):
        logger.info("Stop Analysis button clicked.")
        if self.active_plaxis_interactor:
            self.statusBar.showMessage("Attempting to stop analysis...", 0)
            QApplication.processEvents()
            try:
                self.active_plaxis_interactor.attempt_stop_calculation()
                self.statusBar.showMessage("Stop request sent. Calculation may take time to halt.", 5000)
                QMessageBox.information(self, "Stop Analysis", "Stop request sent. Monitor PLAXIS or messages for confirmation.")
            except Exception as e: # Should be PlaxisAutomationError if interactor handles it
                logger.error(f"Error during stop attempt: {e}", exc_info=True)
                QMessageBox.warning(self, "Stop Error", f"Could not stop analysis: {e}")
                self.statusBar.showMessage("Stop attempt failed.", 3000)
        else:
            self.statusBar.showMessage("No active analysis to stop.", 3000)
            QMessageBox.information(self, "Stop Analysis", "No analysis is currently running.")

        self.stop_analysis_button.setEnabled(False)
        self.run_analysis_button.setEnabled(True) # Always re-enable run button after stop attempt

    @Slot()
    def on_pause_analysis_clicked(self):
        logger.info("Pause Analysis button clicked (Not Implemented).")
        QMessageBox.information(self, "Pause Analysis", "Pause/Resume feature is not yet implemented.")
        # self.pause_analysis_button.setEnabled(False)
        # self.resume_analysis_button.setEnabled(True)

    @Slot()
    def on_resume_analysis_clicked(self):
        logger.info("Resume Analysis button clicked (Not Implemented).")
        QMessageBox.information(self, "Resume Analysis", "Pause/Resume feature is not yet implemented.")
        # self.pause_analysis_button.setEnabled(True)
        # self.resume_analysis_button.setEnabled(False)

    def on_settings(self):
        logger.info("Settings action triggered.")
        dialog = SettingsDialog(self)
        if dialog.exec(): # exec() is blocking and returns QDialog.Accepted or QDialog.Rejected
            logger.info("Settings dialog accepted.")
            # Settings are saved by the dialog itself on accept.
            # MainWindow can react to changes if needed, e.g., by re-checking PLAXIS path.
            self.statusBar.showMessage("Settings updated.", 3000)
        else:
            logger.info("Settings dialog cancelled.")
            self.statusBar.showMessage("Settings dialog cancelled.", 2000)


    def on_about(self):
        self.statusBar.showMessage("Action: About triggered", 2000)
        print("Action: About")
        QMessageBox.about(
            self,
            "About PLAXIS Spudcan Automation Tool",
            "<p><b>PLAXIS 3D Spudcan Penetration Automation Tool</b></p>"
            "<p>Version 0.1 (Conceptual)</p>"
            "<p>This tool is designed to automate spudcan analysis using PLAXIS.</p>"
            "<p>(Further details about licensing, authors, etc.)</p>"
        )

from PySide6.QtWidgets import QMessageBox
from typing import Optional

if __name__ == '__main__':
    app = QApplication(sys.argv)
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
