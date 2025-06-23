"""
Main Window for the PLAXIS 3D Spudcan Automation Tool.
PRD Ref: Category 4 (Frontend Development: UI Shell & Framework)
"""

import sys
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QToolBar, QStatusBar, QStackedWidget
)
from PySide6.QtGui import QAction, QIcon # QIcon will be conceptual for now
from PySide6.QtCore import Qt, QSize

# Backend imports
from backend.models import ProjectSettings, SpudcanGeometry # Added SpudcanGeometry
from backend.project_io import save_project, load_project

# Frontend imports
from .widgets.spudcan_geometry_widget import SpudcanGeometryWidget

# Qt Imports
from PySide6.QtWidgets import QFileDialog, QLabel, QVBoxLayout, QWidget # Added some for clarity

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
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        # Central Widget and Layout (Task 4.2, 4.4)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # Placeholder for different views/sections (Task 4.4)
        self.view_stack = QStackedWidget()
        self.main_layout.addWidget(self.view_stack)

        # Add a couple of placeholder pages to the stack
        # self.page_input will now host more complex widgets
        self.page_input = QWidget()
        self.page_input_layout = QVBoxLayout(self.page_input) # Main layout for all input sections
        # self.page_input_layout.addWidget(QLabel("Input Parameters Section (Placeholder)")) # Remove old label

        # Instantiate and add SpudcanGeometryWidget to the input page
        self.spudcan_geometry_widget = SpudcanGeometryWidget()
        self.spudcan_geometry_widget.data_changed.connect(lambda: self.mark_project_modified(True))
        self.page_input_layout.addWidget(self.spudcan_geometry_widget)
        # TODO: Add other input section widgets here later (e.g., Soil, Loading)
        self.page_input_layout.addStretch() # Pushes widgets to the top

        self.view_stack.addWidget(self.page_input)

        self.page_results = QWidget()
        self.page_results_layout = QVBoxLayout(self.page_results)
        self.page_results_layout.addWidget(QLabel("Results Display Section (Placeholder)"))
        self.view_stack.addWidget(self.page_results)

        self.view_stack.setCurrentWidget(self.page_input) # Default to input page

        self._create_actions() # Helper for creating QAction objects
        self._create_menu_bar() # Task 4.3
        self._create_tool_bar() # Task 4.3 (Optional part)
        self._create_status_bar()

        # Conceptual Styling (Task 4.6) - very basic example
        # self.setStyleSheet("QMainWindow { background-color: #f0f0f0; }")
        print("MainWindow initialized.")

    def _create_actions(self):
        """Create QAction objects for menus and toolbars."""
        # File Actions
        self.action_new_project = QAction("&New Project", self)
        self.action_new_project.setStatusTip("Create a new project")
        self.action_new_project.triggered.connect(self.on_new_project)
        # self.action_new_project.setIcon(QIcon(":/icons/new.png")) # Conceptual icon path

        self.action_open_project = QAction("&Open Project...", self)
        self.action_open_project.setShortcut("Ctrl+O")
        self.action_open_project.setStatusTip("Open an existing project")
        self.action_open_project.triggered.connect(self.on_open_project)

        self.action_save_project = QAction("&Save Project", self)
        self.action_save_project.setShortcut("Ctrl+S")
        self.action_save_project.setStatusTip("Save the current project")
        self.action_save_project.triggered.connect(self.on_save_project)
        self.action_save_project.setEnabled(False)

        self.action_save_project_as = QAction("Save Project &As...", self)
        # self.action_save_project_as.setShortcut("Ctrl+Shift+S") # Common shortcut
        self.action_save_project_as.setStatusTip("Save the current project under a new name")
        self.action_save_project_as.triggered.connect(self.on_save_project_as)
        self.action_save_project_as.setEnabled(False) # Enable when there's a project

        self.action_settings = QAction("&Settings...", self)
        self.action_settings.setStatusTip("Application settings")
        self.action_settings.triggered.connect(self.on_settings)

        self.action_exit = QAction("E&xit", self)
        self.action_exit.setStatusTip("Exit the application")
        self.action_exit.triggered.connect(self.close) # QMainWindow.close()

        # Edit Actions (Placeholders)
        self.action_undo = QAction("&Undo", self)
        self.action_undo.setEnabled(False)
        self.action_redo = QAction("&Redo", self)
        self.action_redo.setEnabled(False)

        # View Actions (Placeholders for navigation)
        self.action_view_input = QAction("Input Section", self)
        self.action_view_input.setCheckable(True)
        self.action_view_input.setChecked(True)
        self.action_view_input.triggered.connect(lambda: self.view_stack.setCurrentWidget(self.page_input))

        self.action_view_results = QAction("Results Section", self)
        self.action_view_results.setCheckable(True)
        self.action_view_results.triggered.connect(lambda: self.view_stack.setCurrentWidget(self.page_results))

        # Help Actions
        self.action_about = QAction("&About", self)
        self.action_about.triggered.connect(self.on_about)


    def _create_menu_bar(self):
        """Create the main menu bar."""
        menu_bar = self.menuBar() # QMainWindow has one by default

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_new_project)
        file_menu.addAction(self.action_open_project)
        file_menu.addAction(self.action_save_project)
        file_menu.addAction(self.action_save_project_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_settings)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        # Edit Menu (Placeholder)
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)

        # View Menu (Placeholder for navigation)
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.action_view_input)
        view_menu.addAction(self.action_view_results)
        # In a more complex app, a QActionGroup would be good for mutually exclusive view actions.

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.action_about)

        print("Menu bar created.")

    def _create_tool_bar(self):
        """Create a main toolbar."""
        # For now, this is a very basic toolbar. Icons are conceptual.
        # In a real app, you'd use QIcon.fromTheme or load from resource files.

        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24)) # Example icon size
        self.addToolBar(toolbar) # Add it to the QMainWindow

        toolbar.addAction(self.action_new_project)
        toolbar.addAction(self.action_open_project)
        toolbar.addAction(self.action_save_project)
        toolbar.addSeparator()
        # Add other common actions if needed

        print("Toolbar created (placeholder).")

    def _create_status_bar(self):
        """Create a status bar."""
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready", 3000) # Initial message, disappears after 3s
        print("Status bar created.")

    # --- Placeholder Slot Methods for Actions ---
    def on_new_project(self):
        self.statusBar.showMessage("Action: New Project triggered", 2000)
        print("Action: New Project")

        # Optional: Check if current project is modified and prompt to save
        if self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes",
                                       "The current project has unsaved changes. Do you want to save them before creating a new project?",
                                       QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ret == QMessageBox.Save:
                if not self.on_save_project(): # if save is cancelled, abort new project
                    return
            elif ret == QMessageBox.Cancel:
                return

        self.current_project_data = ProjectSettings()
        self.current_project_path = None
        self.project_modified = False # A new, unmodified project

        # TODO: Clear/reset all UI input fields to reflect the new project state
        print("UI Cleared/Reset for New Project (Conceptual)")

        self.update_window_title()
        self.action_save_project.setEnabled(False) # Disabled until modified
        self.action_save_project_as.setEnabled(True) # Can always "Save As" a new project
        self.statusBar.showMessage("New project created.", 3000)


    def on_open_project(self):
        self.statusBar.showMessage("Action: Open Project triggered", 2000)
        print("Action: Open Project")

        # Optional: Check if current project is modified and prompt to save
        if self.project_modified:
            ret = QMessageBox.question(self, "Unsaved Changes",
                                       "The current project has unsaved changes. Do you want to save them before opening a new project?",
                                       QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if ret == QMessageBox.Save:
                if not self.on_save_project(): # if save is cancelled, abort open
                    return
            elif ret == QMessageBox.Cancel:
                return

        file_dialog = QFileDialog(self, "Open Project", "", "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        file_dialog.setAcceptMode(QFileDialog.AcceptOpen) # This is default for getOpenFileName but explicit

        if file_dialog.exec():
            filepath = file_dialog.selectedFiles()[0]
            if filepath:
                loaded_data = load_project(filepath)
                if loaded_data:
                    self.current_project_data = loaded_data
                    self.current_project_path = filepath
                    self.project_modified = False

                    # TODO: Update all UI input fields from self.current_project_data
                    self._update_ui_from_project_model() # Placeholder for actual UI update

                    self.update_window_title()
                    self.action_save_project.setEnabled(False) # Just loaded, not modified yet
                    self.action_save_project_as.setEnabled(True) # Can always "Save As"
                    self.statusBar.showMessage(f"Project '{filepath}' loaded successfully.", 3000)
                else:
                    QMessageBox.critical(self, "Load Error",
                                         f"Failed to load project from {filepath}.\n"
                                         "The file may be corrupted or not a valid project file.")
        else:
            self.statusBar.showMessage("Open project cancelled.", 2000)


    def on_save_project(self) -> bool: # Return bool to indicate success/failure/cancel
        self.statusBar.showMessage("Action: Save Project triggered", 2000)
        print("Action: Save Project")
        if not self.current_project_data:
            QMessageBox.warning(self, "No Project", "There is no project data to save.")
            return False

        if not self.current_project_path: # If no path, effectively "Save As"
            return self.on_save_project_as()
        else:
            # TODO: Gather data from UI into self.current_project_data
            # For now, assume self.current_project_data is kept up-to-date by UI elements
            print("Conceptual: Ensuring self.current_project_data is up-to-date from UI.")
            self._gather_data_from_ui_to_project_model() # Placeholder for actual data gathering

            success = save_project(self.current_project_data, self.current_project_path)
            if success:
                self.project_modified = False
                self.action_save_project.setEnabled(False)
                self.statusBar.showMessage(f"Project saved to {self.current_project_path}", 3000)
                self.update_window_title()
                return True
            else:
                QMessageBox.critical(self, "Save Error",
                                     f"Failed to save project to {self.current_project_path}.\n"
                                     "Check file permissions or see logs for more details.")
                return False

    def on_save_project_as(self) -> bool:
        self.statusBar.showMessage("Action: Save Project As triggered", 2000)
        print("Action: Save Project As")
        if not self.current_project_data:
            QMessageBox.warning(self, "No Project", "There is no project data to save.")
            return False

        # TODO: Gather data from UI into self.current_project_data (if not already up-to-date)
        print("Conceptual: Ensuring self.current_project_data is up-to-date from UI for Save As.")
        self._gather_data_from_ui_to_project_model() # Placeholder

        # Use QFileDialog to get save path
        # Default directory could be user's documents or last used path
        default_filename = self.current_project_data.project_name or "UntitledProject"
        if self.current_project_path:
            default_filename = self.current_project_path.split('/')[-1].split('\\')[-1]

        file_dialog = QFileDialog(self, "Save Project As", "", "PLAXIS Auto Project (*.plaxauto);;All Files (*)")
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("plaxauto")
        file_dialog.selectFile(default_filename) # Suggest a filename

        if file_dialog.exec():
            new_path = file_dialog.selectedFiles()[0]
            if new_path:
                self.current_project_path = new_path
                # Update project_name in data if it's still "Untitled Project" or to match filename
                if self.current_project_data.project_name == "Untitled Project" or not self.current_project_data.project_name:
                    base_name = new_path.split('/')[-1].split('\\')[-1]
                    self.current_project_data.project_name = base_name.split('.')[0] if '.' in base_name else base_name

                success = save_project(self.current_project_data, self.current_project_path)
                if success:
                    self.project_modified = False
                    self.action_save_project.setEnabled(False) # Save is now up-to-date
                    self.statusBar.showMessage(f"Project saved to {self.current_project_path}", 3000)
                    self.update_window_title()
                    return True
                else:
                    QMessageBox.critical(self, "Save Error",
                                         f"Failed to save project to {self.current_project_path}.\n"
                                         "Check file permissions or see logs for more details.")
                    # self.current_project_path = None # Optionally reset path if save failed, or keep it for retry
                    return False
        return False # User cancelled Save As dialog


    def update_window_title(self):
        base_title = "PLAXIS 3D Spudcan Automation Tool"
        project_name_display = "Untitled Project"

        if self.current_project_path:
            project_name_display = self.current_project_path.split('/')[-1].split('\\')[-1]
        elif self.current_project_data and self.current_project_data.project_name:
             project_name_display = self.current_project_data.project_name

        modified_indicator = "*" if self.project_modified else ""

        self.setWindowTitle(f"{project_name_display}{modified_indicator} - {base_title}")


    # Placeholder for marking project as modified, should be called by UI input changes
    def _gather_data_from_ui_to_project_model(self):
        """
        Conceptual: This method will be responsible for collecting all data
        from the UI input fields and updating self.current_project_data.
        This needs to be called before saving.
        """
        if not self.current_project_data:
            self.current_project_data = ProjectSettings() # Should not happen if new/open logic is correct

        print("Gathering data from UI fields into self.current_project_data model.")

        # Gather from SpudcanGeometryWidget
        if hasattr(self, 'spudcan_geometry_widget'):
            spudcan_data_dict = self.spudcan_geometry_widget.gather_data()
            # Convert dict to SpudcanGeometry model instance
            # Assuming keys in spudcan_data_dict match SpudcanGeometry fields
            self.current_project_data.spudcan = SpudcanGeometry(
                diameter=spudcan_data_dict.get('diameter'),
                height_cone_angle=spudcan_data_dict.get('height_cone_angle'),
                # spudcan_type=spudcan_data_dict.get('spudcan_type') # Add if type is part of model
            )
            print(f"Updated project_data.spudcan: {self.current_project_data.spudcan}")

        # Example: Gather project name (if there was a dedicated field)
        # if hasattr(self, 'project_name_input_field'):
        #    self.current_project_data.project_name = self.project_name_input_field.text()

        # ... and so on for all relevant UI fields / other input widgets.

        # Update project name from path if it's still default and path exists
        if (self.current_project_data.project_name == "Untitled Project" or \
            not self.current_project_data.project_name) and self.current_project_path:
             base_name = self.current_project_path.split('/')[-1].split('\\')[-1]
             self.current_project_data.project_name = base_name.split('.')[0] if '.' in base_name else base_name

    def _update_ui_from_project_model(self):
        """
        Conceptual: This method will be responsible for populating all UI
        input fields with data from self.current_project_data.
        This needs to be called after loading a project or creating a new one (for defaults).
        """
        if not self.current_project_data:
            return # Should not happen

        print("Populating UI fields from self.current_project_data model (Conceptual implementation).")
        # Example:
        # self.project_name_input.setText(self.current_project_data.project_name or "")
        if hasattr(self, 'spudcan_geometry_widget') and self.current_project_data.spudcan:
            self.spudcan_geometry_widget.load_data(self.current_project_data.spudcan)
        # ... and so on for all relevant UI fields / other input widgets.


    def mark_project_modified(self, modified_status: bool = True):
        if not self.current_project_data: # Cannot mark modified if no project is loaded/newed
            return

        # Only update if the status actually changes
        # Also, ensure that there's actually a project to modify the status for.
        # The save button should only be enabled if there's data AND it's modified.
        if self.project_modified != modified_status:
            self.project_modified = modified_status
            can_save = self.project_modified and bool(self.current_project_data)
            self.action_save_project.setEnabled(can_save)
            self.update_window_title()


    def on_settings(self):
    def mark_project_modified(self, modified_status: bool = True):
        if self.project_modified != modified_status:
            self.project_modified = modified_status
            self.action_save_project.setEnabled(self.project_modified and bool(self.current_project_data))
            self.update_window_title()


    def on_settings(self):
        self.statusBar.showMessage("Action: Settings triggered", 2000)
        print("Action: Settings")
        # Logic to open a settings dialog will go here

    def on_about(self):
        self.statusBar.showMessage("Action: About triggered", 2000)
        print("Action: About")
        # Logic to show an About dialog
        QMessageBox.about(
            self,
            "About PLAXIS Spudcan Automation Tool",
            "<p><b>PLAXIS 3D Spudcan Penetration Automation Tool</b></p>"
            "<p>Version 0.1 (Conceptual)</p>"
            "<p>This tool is designed to automate spudcan analysis using PLAXIS.</p>"
            "<p>(Further details about licensing, authors, etc.)</p>"
        )

# Need to import QMessageBox for on_about
from PySide6.QtWidgets import QMessageBox
from typing import Optional # For Python 3.8 compatibility with QWidget type hint

if __name__ == '__main__':
    # This block is for testing MainWindow directly.
    # In the actual application, main.py will run this.
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
