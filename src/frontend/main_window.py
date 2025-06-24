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
    QHBoxLayout # Added QHBoxLayout for execution buttons
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSize, Slot # Added Slot

# Backend imports
from backend.models import ProjectSettings, SpudcanGeometry, SoilLayer, MaterialProperties, LoadingConditions, AnalysisControlParameters
from backend.project_io import save_project, load_project

# Frontend imports
from .widgets.spudcan_geometry_widget import SpudcanGeometryWidget
from .widgets.soil_stratigraphy_widget import SoilStratigraphyWidget
from .widgets.loading_conditions_widget import LoadingConditionsWidget
from .widgets.analysis_control_widget import AnalysisControlWidget

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
        execution_buttons_layout = QHBoxLayout() # Use QHBoxLayout for side-by-side buttons

        self.run_analysis_button = QPushButton("Run Analysis")
        self.run_analysis_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }")
        self.run_analysis_button.clicked.connect(self.on_run_analysis_clicked)
        execution_buttons_layout.addWidget(self.run_analysis_button)

        self.pause_analysis_button = QPushButton("Pause Analysis")
        self.pause_analysis_button.setStyleSheet("QPushButton { background-color: #ff9800; color: white; padding: 6px; border-radius: 3px; }")
        self.pause_analysis_button.clicked.connect(self.on_pause_analysis_clicked)
        self.pause_analysis_button.setEnabled(False)
        execution_buttons_layout.addWidget(self.pause_analysis_button)

        self.resume_analysis_button = QPushButton("Resume Analysis")
        self.resume_analysis_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 6px; border-radius: 3px; }")
        self.resume_analysis_button.clicked.connect(self.on_resume_analysis_clicked)
        self.resume_analysis_button.setEnabled(False)
        execution_buttons_layout.addWidget(self.resume_analysis_button)

        self.stop_analysis_button = QPushButton("Stop Analysis")
        self.stop_analysis_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 6px; border-radius: 3px; font-weight: bold; }") # Red
        self.stop_analysis_button.clicked.connect(self.on_stop_analysis_clicked)
        self.stop_analysis_button.setEnabled(False) # Disabled initially
        execution_buttons_layout.addWidget(self.stop_analysis_button)

        execution_group_box.setLayout(execution_buttons_layout)
        self.page_input_layout.addWidget(execution_group_box)

        self.page_input_layout.addStretch()
        self.view_stack.addWidget(self.page_input)

        self.page_results = QWidget()
        self.page_results_layout = QVBoxLayout(self.page_results)
        self.page_results_layout.addWidget(QLabel("Results Display Section (Placeholder)"))
        self.view_stack.addWidget(self.page_results)

        self.view_stack.setCurrentWidget(self.page_input)

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()

        self.on_new_project(prompt_save=False)
        logger.info("MainWindow initialized.")

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
        self.statusBar.showMessage("Starting analysis (simulated)...", 0)

        QMessageBox.information(self, "Analysis Simulation", "Analysis execution started (simulated).\n"
                                "Backend call to PLAXIS would happen here.")
        self.statusBar.showMessage("Analysis simulation finished.", 5000)

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
        self.statusBar.showMessage("Action: Settings triggered", 2000)
        print("Action: Settings")

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
