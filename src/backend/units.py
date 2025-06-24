"""
Unit system management utilities for the PLAXIS 3D Spudcan Automation Tool.
PRD Ref: 4.1.7.3 (Units System selection)
PRD Ref: 2.4 (Backend Unit System Management Logic in tasks.md)

For the initial version, we might enforce a single unit system (e.g., SI)
to simplify development. This module will lay the groundwork for potential
future expansion to support multiple unit systems and conversions.
"""

from enum import Enum
from typing import Union, Dict

class UnitSystem(Enum):
    """
    Defines supported unit systems.
    """
    SI = "SI"  # International System of Units (meters, kilonewtons, seconds, etc.)
    # IMPERIAL_FT_KIP = "Imperial_ft_kip" # Feet, kips, seconds
    # IMPERIAL_IN_LB = "Imperial_in_lb" # Inches, pounds, seconds

# Define standard units for the primary system (e.g., SI)
# These would be used for internal consistency and potentially for display or conversion.
# This is a conceptual representation; actual conversion factors would be more complex.
BASE_UNITS = {
    UnitSystem.SI: {
        "length": "m",
        "force": "kN",
        "pressure": "kPa", # kN/m^2
        "density": "kg/m^3", # Note: PLAXIS often uses unit weight kN/m^3
        "unit_weight": "kN/m^3",
        "time": "s",
        "angle": "degrees" # Or radians, be consistent
    }
    # Add other systems if/when supported
}

# The global state for unit system is removed.
# The application should fetch the current unit system from settings when needed.
# from frontend.settings_dialog import SettingsDialog # Avoid direct frontend import in backend logic

# It's better if the part of the code needing the unit system setting
# calls SettingsDialog.get_units_system() directly, or it's passed down.

def get_configured_unit_system() -> UnitSystem:
    """
    Returns the unit system configured in the application settings.
    This function acts as a placeholder for where the actual settings lookup would occur.
    For direct use in backend logic, the setting should ideally be passed
    from the frontend or a shared configuration component.
    """
    # This is a conceptual link. In a real scenario, avoid direct UI import here.
    # The SettingsDialog.get_units_system() would be called by a higher-level
    # controller or the main application instance and the value passed down.
    # For now, we'll simulate this by trying to import and call if possible,
    # but it's not ideal for true backend/frontend separation.
    try:
        # Attempt to dynamically import for loose coupling, not recommended for production
        from frontend.settings_dialog import SettingsDialog # type: ignore
        system_str = SettingsDialog.get_units_system()
        return UnitSystem(system_str)
    except (ImportError, ValueError) as e:
        # print(f"Warning: Could not retrieve unit system from SettingsDialog ({e}). Defaulting to SI.")
        return UnitSystem.SI


def get_unit_label(quantity: str, system_str: Optional[str] = None) -> str:
    """
    Returns the appropriate unit label for a given physical quantity and unit system.

    Args:
        quantity: The physical quantity (e.g., "length", "pressure").
        system_str: The string identifier of the unit system (e.g., "SI").
                    If None, uses the globally configured unit system.

    Returns:
        The unit label string (e.g., "m", "kPa"). Returns empty string if not found.
    """
    target_system_enum: UnitSystem
    if system_str is None:
        target_system_enum = get_configured_unit_system()
    else:
        try:
            target_system_enum = UnitSystem(system_str)
        except ValueError:
            # print(f"Warning: Invalid system_str '{system_str}' in get_unit_label. Defaulting to SI.")
            target_system_enum = UnitSystem.SI

    return BASE_UNITS.get(target_system_enum, {}).get(quantity, "")


# Placeholder for conversion functions.
# Actual implementation of these would require detailed conversion factors.
# For now, they acknowledge the need if multiple systems are supported.

def convert_pressure_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Converts a pressure value from one unit to another.
    This is a STUB function. A real implementation needs conversion factors.
    Example units: "Pa", "kPa", "psi", "ksf"
    """
    if from_unit == to_unit:
        return value

    # TODO: Implement actual conversion logic
    # Example:
    # if from_unit == "kPa" and to_unit == "psi":
    #     return value * 0.145038
    # elif from_unit == "psi" and to_unit == "kPa":
    #     return value / 0.145038

    print(f"Warning: Unit conversion for pressure from '{from_unit}' to '{to_unit}' is not yet implemented. Returning original value.")
    # raise NotImplementedError(f"Conversion from '{from_unit}' to '{to_unit}' not implemented.")
    return value

def convert_length_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Converts a length value from one unit to another.
    This is a STUB function.
    Example units: "m", "cm", "mm", "ft", "in"
    """
    if from_unit == to_unit:
        return value
    print(f"Warning: Unit conversion for length from '{from_unit}' to '{to_unit}' is not yet implemented. Returning original value.")
    return value

# Add more conversion functions as needed (e.g., force, unit_weight)

def ensure_consistent_input_units(value: float, expected_unit_for_plaxis: str, user_provided_unit: Optional[str] = None) -> float:
    """
    Ensures a value provided by the user is converted to the unit expected by PLAXIS.
    This is conceptual. The application will likely enforce a single unit system for inputs
    that directly map to PLAXIS, simplifying this.
    If the UI allows input in different units, this function would be crucial.
    """
    configured_system = get_configured_unit_system()
    # For now, assume user_provided_unit matches configured_system's unit for that quantity type
    # and expected_unit_for_plaxis is also from that same system, or PLAXIS uses SI directly.

    # If the application strictly uses SI for PLAXIS interaction:
    if configured_system == UnitSystem.SI and expected_unit_for_plaxis.lower() in ["m", "kn", "kpa"]: # etc.
        # Assume value is already in SI if configured_system is SI
        # This logic needs to be more robust based on actual UI input flexibility
        return value

    # More complex logic would be:
    # 1. Determine the type of quantity (e.g., length, pressure)
    # 2. Get the base unit for that quantity in the current_project_unit_system
    # 3. If user_provided_unit is different from base unit, convert value to base unit.
    # 4. Then convert from base unit to expected_unit_for_plaxis.

    print(f"Warning: Unit consistency check for '{expected_unit_for_plaxis}' is conceptual. Returning original value.")
    return value


if __name__ == '__main__':
    # Note: The direct import of SettingsDialog in get_configured_unit_system
    # makes standalone testing of this script tricky without a QApplication instance
    # and proper QSettings setup. For true unit tests, this dependency would be mocked.
    print("--- Testing Unit System Utilities (Conceptual - Relies on SettingsDialog) ---")

    # To properly test get_configured_unit_system, you'd typically mock SettingsDialog.get_units_system
    # For this __main__ block, we'll assume it might work if run in an environment where Qt can init.
    try:
        from PySide6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() # Get existing instance if any
        if not app: # Create a new one if not
            # For QSettings to work without full app name/org in test:
            QApplication.setOrganizationName("MySoftTest")
            QApplication.setApplicationName("PlaxisAutomatorTest")
            app = QApplication(sys.argv)

        print(f"Configured unit system (from settings): {get_configured_unit_system().value}")
    except Exception as e:
        print(f"Could not initialize QApplication for test settings: {e}")
        print(f"Configured unit system (defaulting due to error): {get_configured_unit_system().value}")


    print(f"Length unit in SI: {get_unit_label('length', 'SI')}")
    print(f"Pressure unit using configured system: {get_unit_label('pressure')}")

    # Test conversion stubs
    pressure_kpa = 100.0
    pressure_psi = convert_pressure_units(pressure_kpa, from_unit="kPa", to_unit="psi")
    print(f"{pressure_kpa} kPa is approx. {pressure_psi} psi (stubbed)")

    length_m = 10.0
    length_ft = convert_length_units(length_m, from_unit="m", to_unit="ft")
    print(f"{length_m} m is approx. {length_ft} ft (stubbed)")

    # Test ensuring consistent units (conceptual)
    user_input_pressure = 1.0 # e.g., user typed this, assuming it's in project's current system units
    plaxis_expected_pressure_unit = "kPa" # PLAXIS needs kPa

    # Assume user input is already in the project's current unit system.
    # This function's role would be more significant if UI allowed mixed unit inputs.
    value_for_plaxis = ensure_consistent_input_units(user_input_pressure, plaxis_expected_pressure_unit)
    print(f"Value {user_input_pressure} (assumed {get_unit_label('pressure')}) prepared for PLAXIS as {value_for_plaxis} (expected {plaxis_expected_pressure_unit})")

    print("\n--- End of Unit System Utilities Tests ---")
