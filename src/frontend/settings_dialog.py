"""
Settings Dialog for the PLAXIS Spudcan Automation Tool.
Allows configuration of application-level settings, e.g., PLAXIS path.
PRD Ref: 4.1.7 (Configuration & Settings Section)
"""
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QFileDialog, QDialogButtonBox, QLabel, QGroupBox
)
from PySide6.QtCore import Qt, QSettings, Slot, QStandardPaths

logger = logging.getLogger(__name__)

# Define settings keys
PLAXIS_PATH_SETTING = "plaxis/installation_path"
# Add other settings keys here as needed, e.g.:
# DEFAULT_PROJECT_SETTINGS_KEY = "defaults/project_settings"
# UNITS_SYSTEM_KEY = "general/units_system"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(500)

        self.settings = QSettings(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation) + "/settings.ini",
            QSettings.Format.IniFormat
        )

        main_layout = QVBoxLayout(self)

        # --- PLAXIS Configuration Group ---
        plaxis_group = QGroupBox("PLAXIS Configuration")
        plaxis_form_layout = QFormLayout(plaxis_group)

        self.plaxis_path_edit = QLineEdit()
        self.plaxis_path_edit.setPlaceholderText("Path to Plaxis3DInput.exe")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_plaxis_path)

        path_layout = QVBoxLayout() # Use QVBoxLayout for QLineEdit and description
        path_layout.addWidget(self.plaxis_path_edit)
        path_desc_label = QLabel("Specify the full path to your Plaxis3DInput.exe (or equivalent for your version).")
        path_desc_label.setStyleSheet("font-size: 8pt; color: gray;")
        path_layout.addWidget(path_desc_label)

        plaxis_form_layout.addRow(QLabel("PLAXIS Executable Path:"), path_layout)
        plaxis_form_layout.addRow("", browse_button) # Button on its own line or next to edit

        main_layout.addWidget(plaxis_group)

        # --- Placeholder for other settings sections (Defaults, Units) ---
        # Example: Defaults Group (Task 8.2 - Deferred for now)
        # defaults_group = QGroupBox("Default Project Settings")
        # ... layout for defaults ...
        # main_layout.addWidget(defaults_group)

        # Example: Units Group (Task 8.3 - Deferred for now)
        # units_group = QGroupBox("Units System")
        # ... layout for units ...
        # main_layout.addWidget(units_group)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_settings)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.load_settings()
        logger.info("SettingsDialog initialized.")

    @Slot()
    def browse_plaxis_path(self):
        # Determine the executable name based on OS, though primarily targeting Windows
        exe_filter = "PLAXIS Executable (Plaxis3DInput.exe Plaxis2DInput.exe *.exe)" if os.name == 'nt' else "All files (*)"

        # Start directory could be last used path or a common PLAXIS install location
        start_dir = os.path.dirname(self.plaxis_path_edit.text()) if self.plaxis_path_edit.text() else "C:\\Program Files"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PLAXIS Executable",
            start_dir,
            exe_filter
        )
        if file_path:
            self.plaxis_path_edit.setText(file_path)
            logger.debug(f"PLAXIS path selected via browser: {file_path}")

    def load_settings(self):
        """Loads settings from QSettings into the UI."""
        plaxis_path = self.settings.value(PLAXIS_PATH_SETTING, "")
        self.plaxis_path_edit.setText(plaxis_path) # type: ignore
        logger.info(f"Loaded PLAXIS path from settings: '{plaxis_path}'")
        # Load other settings here

    def save_settings(self):
        """Saves UI settings to QSettings."""
        self.settings.setValue(PLAXIS_PATH_SETTING, self.plaxis_path_edit.text())
        logger.info(f"Saved PLAXIS path to settings: '{self.plaxis_path_edit.text()}'")
        # Save other settings here
        self.settings.sync() # Ensure changes are written to disk

    @Slot()
    def accept_settings(self):
        """Saves settings and accepts the dialog."""
        self.save_settings()
        self.accept()

    # Static method to retrieve settings from elsewhere in the app
    @staticmethod
    def get_plaxis_path() -> Optional[str]:
        settings = QSettings(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation) + "/settings.ini",
            QSettings.Format.IniFormat
        )
        path = settings.value(PLAXIS_PATH_SETTING, None) # type: ignore
        return path if path else None


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    import os # For os.name in browse_plaxis_path

    app = QApplication(sys.argv)
    # For QSettings to work without full app name/org:
    QApplication.setOrganizationName("MySoft")
    QApplication.setApplicationName("PlaxisAutomator")

    dialog = SettingsDialog()
    if dialog.exec():
        print("Settings Accepted.")
        print(f"PLAXIS Path: {SettingsDialog.get_plaxis_path()}")
    else:
        print("Settings Cancelled.")
    sys.exit()
