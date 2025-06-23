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

class MainWindow(QMainWindow):
    """
    Main application window.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("PLAXIS 3D Spudcan Automation Tool")
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        # Central Widget and Layout (Task 4.2, 4.4)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # Placeholder for different views/sections (Task 4.4)
        self.view_stack = QStackedWidget()
        self.main_layout.addWidget(self.view_stack)

        # Add a couple of placeholder pages to the stack
        self.page_input = QWidget()
        self.page_input_layout = QVBoxLayout(self.page_input)
        self.page_input_layout.addWidget(QLabel("Input Parameters Section (Placeholder)"))
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
        self.action_open_project.setStatusTip("Open an existing project")
        self.action_open_project.triggered.connect(self.on_open_project)

        self.action_save_project = QAction("&Save Project", self)
        self.action_save_project.setStatusTip("Save the current project")
        self.action_save_project.triggered.connect(self.on_save_project)
        self.action_save_project.setEnabled(False) # Typically disabled until project is modified

        self.action_save_project_as = QAction("Save Project &As...", self)
        self.action_save_project_as.setStatusTip("Save the current project under a new name")
        self.action_save_project_as.triggered.connect(self.on_save_project_as)

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
        # Logic for new project (e.g., clear inputs, reset models) will go here
        self.action_save_project.setEnabled(True) # Example: enable save after new

    def on_open_project(self):
        self.statusBar.showMessage("Action: Open Project triggered", 2000)
        print("Action: Open Project")
        # Logic for opening a project file will go here

    def on_save_project(self):
        self.statusBar.showMessage("Action: Save Project triggered", 2000)
        print("Action: Save Project")
        # Logic for saving the current project will go here

    def on_save_project_as(self):
        self.statusBar.showMessage("Action: Save Project As triggered", 2000)
        print("Action: Save Project As")
        # Logic for save as will go here

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
