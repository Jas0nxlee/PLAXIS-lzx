"""
Main entry point for the PLAXIS 3D Spudcan Automation Tool application.
PRD Ref: Category 4 (Frontend Development: UI Shell & Framework) - Task 4.1
"""

import sys
from PySide6.QtWidgets import QApplication
from frontend.main_window import MainWindow # Relative import from sibling package

def main():
    """
    Initializes and runs the Qt application.
    """
    app = QApplication(sys.argv)

    # Set application details (optional but good practice)
    app.setApplicationName("PlaxisSpudcanAutomator")
    app.setOrganizationName("MyCompanyOrProject") # Replace as needed
    app.setApplicationVersion("0.1.0")

    # For high DPI scaling (Qt 5.6+)
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # Basic application stylesheet
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f8f8f8; /* Light gray background */
        }
        QWidget {
            font-family: "Segoe UI", Arial, sans-serif; /* Common sans-serif font */
            font-size: 10pt;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 0.5em;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px 0 3px;
            left: 10px; /* Indent title from the border */
        }
        QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
            padding: 4px;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
            background-color: white;
        }
        QPushButton {
            background-color: #e0e0e0; /* Default button color */
            color: #333333;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px 10px;
            min-width: 60px; /* Minimum width for buttons */
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        QMessageBox {
            font-size: 10pt;
        }
        QMenuBar {
            background-color: #e8e8e8;
        }
        QMenuBar::item {
            background: transparent;
            padding: 4px 8px;
        }
        QMenuBar::item:selected {
            background: #d8d8d8;
        }
        QMenu {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
        }
        QMenu::item:selected {
            background-color: #d8d8d8;
        }
        QToolBar {
            background-color: #efefef;
            border: none;
            padding: 2px;
        }
        QStatusBar {
            background-color: #e8e8e8;
        }
    """)

    main_window = MainWindow()
    main_window.show()

    print("Application started. Showing MainWindow.")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
