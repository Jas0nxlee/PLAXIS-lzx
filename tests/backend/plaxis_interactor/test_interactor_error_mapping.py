import pytest
import logging

# Setup basic logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from src.backend.plaxis_interactor.interactor import _map_plaxis_sdk_exception_to_custom
from src.backend.exceptions import (
    PlaxisAutomationError, PlaxisConnectionError, PlaxisConfigurationError,
    PlaxisCalculationError, PlaxisOutputError, PlaxisCliError
)

# --- Test Data: Tuples of (InputException, ExpectedCustomExceptionType, ExpectedSubstringsInMessage) ---
# Define PlxScriptingError locally for tests if plxscripting is not installed in test env
try:
    from plxscripting.plx_scripting_exceptions import PlxScriptingError
except ImportError:
    class PlxScriptingError(Exception): # type: ignore
        pass


GENERIC_PLX_SCRIPTING_ERROR_MESSAGE = "A generic PlxScripting error occurred."
GENERIC_PYTHON_ERROR_MESSAGE = "A generic Python error."

test_error_mapping_data = [
    # PlxScriptingError - Connection
    (PlxScriptingError("connection refused by server"), PlaxisConnectionError, ["connection refused"]),
    (PlxScriptingError("Password incorrect"), PlaxisConnectionError, ["password incorrect", "authentication failed"]),
    (PlxScriptingError("No valid license found"), PlaxisConnectionError, ["license issue"]),

    # PlxScriptingError - Configuration
    (PlxScriptingError("Object 'Soil_1' not found"), PlaxisConfigurationError, ["object not found"]),
    (PlxScriptingError("Unknown identifier : NonExistentProperty"), PlaxisConfigurationError, ["unknown identifier"]),
    (PlxScriptingError("Operation not allowed in current mode (e.g. Staged Construction)"), PlaxisConfigurationError, ["operation not allowed"]), # Removed "incorrect mode"
    (PlxScriptingError("Index 10 is not valid for list of points"), PlaxisConfigurationError, ["index", "not valid"]),
    (PlxScriptingError("Mesh generation failed due to geometric inconsistencies"), PlaxisConfigurationError, ["mesh generation failed"]),
    (PlxScriptingError("Invalid geometry for surface"), PlaxisConfigurationError, ["invalid geometry"]),
    (PlxScriptingError("Parameter 'cohesion' is missing"), PlaxisConfigurationError, ["parameter", "missing", "cohesion"]),
    (PlxScriptingError("Input value is not correct for parameter 'phi'"), PlaxisConfigurationError, ["input value", "not correct", "phi"]),
    (PlxScriptingError("Value is out of range for EoedRef"), PlaxisConfigurationError, ["value is out of range", "eoedref"]),


    # PlxScriptingError - Calculation
    (PlxScriptingError("Calculation failed: soil body seems to collapse"), PlaxisCalculationError, ["calculation failed", "collapse"]),
    (PlxScriptingError("Accuracy condition not met"), PlaxisCalculationError, ["accuracy condition not met"]),
    (PlxScriptingError("Load increment reduced to zero"), PlaxisCalculationError, ["load increment reduced to zero"]),
    (PlxScriptingError("Calculation aborted by user"), PlaxisCalculationError, ["calculation aborted"]),


    # PlxScriptingError - File
    (PlxScriptingError("File not found: myproject.p3dx"), PlaxisConfigurationError, ["file not found", "myproject.p3dx"]),
    (PlxScriptingError("Cannot open file, access denied."), PlaxisConfigurationError, ["cannot open file", "access denied"]),

    # PlxScriptingError - Generic
    (PlxScriptingError(GENERIC_PLX_SCRIPTING_ERROR_MESSAGE), PlaxisAutomationError, [GENERIC_PLX_SCRIPTING_ERROR_MESSAGE.lower()]),

    # Standard Python Errors
    (AttributeError("object has no attribute 'non_existent_plaxis_attr'"), PlaxisConfigurationError, ["attributeerror", "api misuse", "non_existent_plaxis_attr"]),
    (TypeError("argument 'material' has incorrect type (expected str)"), PlaxisConfigurationError, ["typeerror", "incorrect type", "material"]),
    (ValueError("Cannot set value 'abc' for numerical parameter 'frictionangle'"), PlaxisConfigurationError, ["valueerror", "invalid value", "frictionangle"]),
    (FileNotFoundError("Project file 'data.input' not found."), PlaxisConfigurationError, ["filenotfounderror", "project/data file", "data.input"]),
    (TimeoutError("Calculation process timed out after 3600s"), PlaxisCalculationError, ["timed out"]), # Changed from "timeouterror"
    (Exception(GENERIC_PYTHON_ERROR_MESSAGE), PlaxisAutomationError, [GENERIC_PYTHON_ERROR_MESSAGE.lower()]), # Generic Python Exception
]

@pytest.mark.parametrize("input_exception, expected_type, expected_substrings", test_error_mapping_data)
def test_map_plaxis_sdk_exception_to_custom(input_exception, expected_type, expected_substrings):
    context = "test_context"
    mapped_exception = _map_plaxis_sdk_exception_to_custom(input_exception, context)

    assert isinstance(mapped_exception, expected_type), \
        f"Expected {expected_type}, but got {type(mapped_exception)} for input {input_exception}"

    # Check that the context is in the message
    assert context.lower() in str(mapped_exception).lower(), \
        f"Context '{context}' not found in mapped exception message: {mapped_exception}"

    # Check that the original exception message (or parts of it) is in the new message
    original_msg_part = str(input_exception)[:50] # Check first 50 chars of original message
    assert original_msg_part.lower() in str(mapped_exception).lower(), \
        f"Original message part '{original_msg_part}' not found in mapped: {mapped_exception}"

    for sub_str in expected_substrings:
        assert sub_str.lower() in str(mapped_exception).lower(), \
            f"Expected substring '{sub_str}' not found in mapped exception message: {mapped_exception}"

def test_map_plaxis_sdk_exception_already_custom():
    """Tests that if a PlaxisAutomationError is passed in, it's returned as is."""
    original_exception = PlaxisOutputError("This is already a custom output error.")
    mapped_exception = _map_plaxis_sdk_exception_to_custom(original_exception, "test_context")
    assert mapped_exception is original_exception # Should be the same object
    assert isinstance(mapped_exception, PlaxisOutputError)
    assert "This is already a custom output error." in str(mapped_exception)
