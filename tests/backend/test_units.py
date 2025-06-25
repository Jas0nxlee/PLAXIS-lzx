"""
Unit tests for the backend.units module.
"""
import pytest
from unittest.mock import patch, MagicMock

# Modules to test
from backend import units
from backend.units import UnitSystem
# ValidationError is in backend.validation, not backend.units

# --- Mocks for SettingsDialog dependency ---
# Create a mock that can be imported by units.py when SettingsDialog is accessed
MOCK_SETTINGS_DIALOG_PATH = "backend.units.SettingsDialog"

@pytest.fixture
def mock_settings_si(monkeypatch):
    """Mocks SettingsDialog.get_units_system to return 'SI'."""
    mock_dialog = MagicMock()
    mock_dialog.get_units_system.return_value = "SI"
    monkeypatch.setattr(MOCK_SETTINGS_DIALOG_PATH, mock_dialog, raising=False) # raising=False for dynamic import
    return mock_dialog

@pytest.fixture
def mock_settings_imperial(monkeypatch):
    """Mocks SettingsDialog.get_units_system to return 'Imperial'."""
    mock_dialog = MagicMock()
    mock_dialog.get_units_system.return_value = "Imperial" # Assuming "Imperial" is a valid key
    # Ensure "Imperial" is a defined UnitSystem value for these tests to pass if get_configured_unit_system uses it
    if "Imperial" not in [e.value for e in UnitSystem]:
        # Temporarily add it for the test if it's not in the enum, or adjust test expectations
        # This is a bit of a hack; ideally, the enum would support all testable values.
        # For now, we assume "SI" is the primary and only one that won't cause issues.
        pass
    monkeypatch.setattr(MOCK_SETTINGS_DIALOG_PATH, mock_dialog, raising=False)
    return mock_dialog

@pytest.fixture
def mock_settings_invalid(monkeypatch):
    """Mocks SettingsDialog.get_units_system to return an invalid system string."""
    mock_dialog = MagicMock()
    mock_dialog.get_units_system.return_value = "Klingon"
    monkeypatch.setattr(MOCK_SETTINGS_DIALOG_PATH, mock_dialog, raising=False)
    return mock_dialog

# --- Tests for get_configured_unit_system ---

def test_get_configured_unit_system_si(mock_settings_si):
    """Test that get_configured_unit_system returns SI when mocked."""
    assert units.get_configured_unit_system() == UnitSystem.SI

def test_get_configured_unit_system_default_on_invalid(mock_settings_invalid):
    """Test that get_configured_unit_system defaults to SI if settings return an invalid system."""
    # The units.py logic already defaults to SI if SettingsDialog.get_units_system() is bad
    # or if the value from it is not in the UnitSystem enum.
    assert units.get_configured_unit_system() == UnitSystem.SI

def test_get_configured_unit_system_default_on_import_error(monkeypatch):
    """Test defaulting to SI if SettingsDialog cannot be imported."""
    # This simulates units.py failing to import SettingsDialog
    monkeypatch.setitem(sys.modules, "frontend.settings_dialog", None) # type: ignore
    # Or, more directly, mock the import within units.py to raise ImportError
    with patch('importlib.import_module', side_effect=ImportError) as mock_import_module:
        # Ensure units module is reloaded if it was already imported by other tests,
        # so its import attempt for SettingsDialog happens under our patch.
        import importlib
        reloaded_units_module = importlib.reload(units)
        result = reloaded_units_module.get_configured_unit_system()
        assert result == reloaded_units_module.UnitSystem.SI # Compare with enum from reloaded module
        # Check that the dynamic import was indeed attempted for 'frontend.settings_dialog'
        # This requires checking the calls to the mock.
        # Note: import_module might be called for other things by pytest or dependencies.
        # We are interested if it was called for 'frontend.settings_dialog'.
        # A simple way to check if the ImportError path was taken is often enough.
        # For more specific check on import_module call:
        # call_args_list = [call_args[0][0] for call_args in mock_import_module.call_args_list]
        # assert "frontend.settings_dialog" in call_args_list
        # However, the primary check is the fallback to SI.
        # The reload ensures the 'from ... import ...' line is executed again.


# --- Tests for get_unit_label ---

def test_get_unit_label_si_known_quantity(mock_settings_si):
    """Test getting a known unit label for SI system."""
    assert units.get_unit_label("length") == "m"
    assert units.get_unit_label("pressure") == "kPa"
    assert units.get_unit_label("force") == "kN"
    assert units.get_unit_label("unit_weight") == "kN/m^3"

def test_get_unit_label_si_unknown_quantity(mock_settings_si):
    """Test getting an unknown unit label for SI system (should be empty string)."""
    assert units.get_unit_label("volume") == "" # Assuming 'volume' is not in BASE_UNITS

def test_get_unit_label_explicit_system_known(mock_settings_si): # Mock settings don't matter here
    """Test getting label with explicitly provided SI system string."""
    assert units.get_unit_label("length", system_str="SI") == "m"

def test_get_unit_label_explicit_system_unknown_quantity(mock_settings_si):
    assert units.get_unit_label("banana_quality", system_str="SI") == ""

def test_get_unit_label_explicit_invalid_system(mock_settings_si):
    """Test getting label with an invalid system string (should default to SI or handle gracefully)."""
    # Current implementation of get_unit_label defaults to SI if system_str is invalid.
    assert units.get_unit_label("length", system_str="MetricAncient") == "m"

# --- Tests for conversion stubs (they currently just return original value) ---
# These tests are more about ensuring the functions exist and run without error.

def test_convert_pressure_units_stub_same_unit():
    assert units.convert_pressure_units(100.0, "kPa", "kPa") == 100.0

def test_convert_pressure_units_stub_different_unit():
    # Currently returns original value and prints a warning
    assert units.convert_pressure_units(100.0, "kPa", "psi") == 100.0

def test_convert_length_units_stub_same_unit():
    assert units.convert_length_units(10.0, "m", "m") == 10.0

def test_convert_length_units_stub_different_unit():
    assert units.convert_length_units(10.0, "m", "ft") == 10.0

# --- Test ensure_consistent_input_units (conceptual) ---
def test_ensure_consistent_input_units_stub(mock_settings_si):
    # This function is highly conceptual and depends on how UI and PLAXIS units are handled.
    # For now, it mostly returns the original value under SI.
    assert units.ensure_consistent_input_units(5.0, "m") == 5.0
    assert units.ensure_consistent_input_units(100.0, "kPa") == 100.0


# Example to add if unit system enum or BASE_UNITS expands:
# def test_get_unit_label_imperial_known_quantity(mock_settings_imperial):
#     # This test would only pass if "Imperial" is a fully defined system in units.py
#     # and mock_settings_imperial correctly sets it.
#     # For now, "Imperial" is not in UnitSystem enum in units.py
#     # and BASE_UNITS only has SI.
#     # So this test would fail or need units.py to be updated.
#     # Example assertion if Imperial was defined:
#     # assert units.get_unit_label("length", system_str="Imperial") == "ft"
#     pass

# Helper for reloading units module if necessary (e.g., after heavy patching)
# Not strictly needed if tests are well-isolated or patching is local.
# def reload_units_module():
#     import importlib
#     importlib.reload(units)
import sys # for monkeypatching sys.modules if needed for import error test
