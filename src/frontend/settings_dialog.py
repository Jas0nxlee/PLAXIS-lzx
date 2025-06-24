"""
Settings Dialog for the PLAXIS Spudcan Automation Tool.
Allows configuration of application-level settings, e.g., PLAXIS path.
PRD Ref: 4.1.7 (Configuration & Settings Section)
"""
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QFileDialog, QDialogButtonBox, QLabel, QGroupBox, QComboBox
)
from PySide6.QtCore import Qt, QSettings, Slot, QStandardPaths
from typing import Optional # Added for type hinting
import os # Added for os.name in browse_plaxis_path

logger = logging.getLogger(__name__)

# Define settings keys
PLAXIS_PATH_SETTING = "plaxis/installation_path"
UNITS_SYSTEM_KEY = "general/units_system"
# Add other settings keys here as needed, e.g.:
# DEFAULT_PROJECT_SETTINGS_KEY = "defaults/project_settings"


# Define available unit systems
UNIT_SYSTEMS = {
    "SI (m, kN, kPa, deg)": "SI",
    "Imperial (ft, kip, ksf, deg)": "Imperial" # Example, if ever supported
}

class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None): # type: ignore
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

        # --- Units System Group (Task 8.3) ---
        units_group = QGroupBox("Units System Configuration")
        units_form_layout = QFormLayout(units_group)

        self.units_system_combo = QComboBox()
        for display_name in UNIT_SYSTEMS.keys():
            self.units_system_combo.addItem(display_name, UNIT_SYSTEMS[display_name])

        units_desc_label = QLabel("Select the primary unit system for the application.\nCurrently, only SI is fully supported for backend calculations.")
        units_desc_label.setStyleSheet("font-size: 8pt; color: gray;")
        units_form_layout.addRow(QLabel("Unit System:"), self.units_system_combo)
        units_form_layout.addRow(units_desc_label)
        main_layout.addWidget(units_group)

        # --- Default Project Settings Group (Task 8.2 - Currently Deferred) ---
        # defaults_group = QGroupBox("Default Project Settings")
        # defaults_layout = QVBoxLayout(defaults_group)
        # save_defaults_button = QPushButton("Save Current Inputs as Default")
        # # save_defaults_button.clicked.connect(self.on_save_defaults)
        # load_defaults_button = QPushButton("Load Defaults on New Project (Not Implemented)") # Or a checkbox
        # clear_defaults_button = QPushButton("Clear Saved Defaults")
        # # clear_defaults_button.clicked.connect(self.on_clear_defaults)
        # defaults_layout.addWidget(save_defaults_button)
        # defaults_layout.addWidget(load_defaults_button)
        # defaults_layout.addWidget(clear_defaults_button)
        # defaults_desc = QLabel("Configure whether new projects should start with these saved defaults.\n(This feature is planned but not yet fully implemented).")
        # defaults_desc.setStyleSheet("font-size: 8pt; color: gray;")
        # defaults_layout.addWidget(defaults_desc)
        # main_layout.addWidget(defaults_group)


        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Apply)
        self.button_box.accepted.connect(self.accept_settings)
        self.button_box.rejected.connect(self.reject)
        apply_button = self.button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button: # Should exist
            apply_button.clicked.connect(self.save_settings) # Apply button just saves
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

        # Load Units System
        saved_unit_system_value = self.settings.value(UNITS_SYSTEM_KEY, "SI") # Default to SI
        idx = self.units_system_combo.findData(saved_unit_system_value)
        if idx != -1:
            self.units_system_combo.setCurrentIndex(idx)
        else: # Fallback if stored value is somehow invalid
            self.units_system_combo.setCurrentIndex(0)
        logger.info(f"Loaded Units System from settings: '{saved_unit_system_value}' (ComboBox index: {idx})")


    def save_settings(self):
        """Saves UI settings to QSettings."""
        # Save PLAXIS Path
        self.settings.setValue(PLAXIS_PATH_SETTING, self.plaxis_path_edit.text())
        logger.info(f"Saved PLAXIS path to settings: '{self.plaxis_path_edit.text()}'")

        # Save Units System
        selected_unit_system_data = self.units_system_combo.currentData()
        self.settings.setValue(UNITS_SYSTEM_KEY, selected_unit_system_data)
        logger.info(f"Saved Units System to settings: '{selected_unit_system_data}'")

        self.settings.sync() # Ensure changes are written to disk
        logger.info("All settings synced to disk.")


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

    @staticmethod
    def get_units_system() -> str:
        """Retrieves the configured unit system (e.g., 'SI', 'Imperial'). Defaults to 'SI'."""
        settings = QSettings(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation) + "/settings.ini",
            QSettings.Format.IniFormat
        )
        # Default to "SI" if not set or if the stored value is not one of the known values
        stored_value = settings.value(UNITS_SYSTEM_KEY, "SI")
        if stored_value not in UNIT_SYSTEMS.values():
            logger.warning(f"Invalid unit system '{stored_value}' found in settings. Defaulting to 'SI'.")
            return "SI"
        return str(stored_value)


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QWidget # Added QWidget

    app = QApplication(sys.argv)
    # For QSettings to work without full app name/org:
    QApplication.setOrganizationName("MySoft")
    QApplication.setApplicationName("PlaxisAutomator")

    dialog = SettingsDialog()
    if dialog.exec():
        print("Settings Accepted.")
        print(f"PLAXIS Path: {SettingsDialog.get_plaxis_path()}")
        print(f"Units System: {SettingsDialog.get_units_system()}")
    else:
        print("Settings Cancelled.")
    sys.exit()
