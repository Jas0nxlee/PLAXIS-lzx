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


    main_window = MainWindow()
    main_window.show()

    print("Application started. Showing MainWindow.")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
