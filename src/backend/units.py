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

# Store the currently active unit system for the project.
# This would ideally be part of the ProjectSettings model from models.py
# For now, a global placeholder.
# In a real app, this should be managed more robustly, perhaps via a config object or context.
_current_project_unit_system: UnitSystem = UnitSystem.SI

def get_current_unit_system() -> UnitSystem:
    """Returns the currently active unit system for the project."""
    # In a real app, this would fetch from project settings.
    return _current_project_unit_system

def set_current_unit_system(system: UnitSystem):
    """Sets the active unit system for the project."""
    # In a real app, this would update project settings and might trigger UI updates.
    global _current_project_unit_system
    if not isinstance(system, UnitSystem):
        raise ValueError("Invalid unit system specified.")
    _current_project_unit_system = system
    print(f"Project unit system set to: {system.value}")


def get_unit_label(quantity: str, system: Optional[UnitSystem] = None) -> str:
    """
    Returns the appropriate unit label for a given physical quantity and unit system.

    Args:
        quantity: The physical quantity (e.g., "length", "pressure").
        system: The unit system. If None, uses the current project unit system.

    Returns:
        The unit label string (e.g., "m", "kPa"). Returns empty string if not found.
    """
    if system is None:
        system = get_current_unit_system()

    return BASE_UNITS.get(system, {}).get(quantity, "")


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
    current_system = get_current_unit_system()
    # For now, assume user_provided_unit matches current_system's unit for that quantity type
    # and expected_unit_for_plaxis is also from that same system, or PLAXIS uses SI directly.

    # If the application strictly uses SI for PLAXIS interaction:
    if current_system == UnitSystem.SI and expected_unit_for_plaxis.lower() in ["m", "kn", "kpa"]: # etc.
        # Assume value is already in SI if current_system is SI
        # This logic needs to be more robust based on actual UI input flexibility
        return value

    # More complex logic would be:
    # 1. Determine the type of quantity (e.g. length, pressure)
    # 2. Get the base unit for that quantity in the current_project_unit_system
    # 3. If user_provided_unit is different from base unit, convert value to base unit.
    # 4. Then convert from base unit to expected_unit_for_plaxis.

    print(f"Warning: Unit consistency check for '{expected_unit_for_plaxis}' is conceptual. Returning original value.")
    return value


if __name__ == '__main__':
    print("--- Testing Unit System Utilities ---")

    print(f"Default project unit system: {get_current_unit_system()}")

    print(f"Length unit in SI: {get_unit_label('length', UnitSystem.SI)}")
    print(f"Pressure unit in SI: {get_unit_label('pressure')}") # Uses current default

    # Example of setting a different system (if it were defined)
    # set_current_unit_system(UnitSystem.IMPERIAL_FT_KIP) # Assuming this enum existed
    # print(f"Length unit in Imperial: {get_unit_label('length', UnitSystem.IMPERIAL_FT_KIP)}")

    # Reset to SI for other tests
    set_current_unit_system(UnitSystem.SI)

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
