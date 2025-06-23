"""
Input validation utilities for the PLAXIS 3D Spudcan Automation Tool.
PRD Ref: 4.3.2 (Input Validation)
"""

from typing import Any, Optional, Union, Type

class ValidationError(ValueError):
    """Custom exception for validation errors."""
    pass

def validate_numerical_range(
    value: Any,
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
    param_name: str = "Parameter",
    can_be_none: bool = False,
    value_type: Type = float # Expected type (float or int)
) -> Optional[Union[int, float]]:
    """
    Validates if a value is a number and falls within an optional specified range.

    Args:
        value: The value to validate.
        min_val: The minimum allowed value (inclusive).
        max_val: The maximum allowed value (inclusive).
        param_name: The name of the parameter being validated (for error messages).
        can_be_none: If True, None is considered a valid value.
        value_type: The expected numerical type (float or int).

    Returns:
        The validated value if it's valid.

    Raises:
        ValidationError: If the value is not valid.
    """
    if value is None:
        if can_be_none:
            return None
        else:
            raise ValidationError(f"{param_name} cannot be None.")

    if not isinstance(value, (int, float)):
        raise ValidationError(f"{param_name} must be a number. Got type: {type(value).__name__}.")

    try:
        # Attempt to cast to the desired type (e.g. if an int is given for a float)
        # This is useful if the source is e.g. a string from UI that was converted
        numeric_value = value_type(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{param_name} must be a valid {value_type.__name__}. Got value: {value}.")


    if min_val is not None and numeric_value < min_val:
        raise ValidationError(f"{param_name} ({numeric_value}) must be greater than or equal to {min_val}.")

    if max_val is not None and numeric_value > max_val:
        raise ValidationError(f"{param_name} ({numeric_value}) must be less than or equal to {max_val}.")

    return numeric_value

def validate_not_empty(
    value: Any,
    param_name: str = "Parameter",
    can_be_none: bool = False # If string, None is different from empty string ""
) -> Any:
    """
    Validates if a value (typically a string or collection) is not empty.

    Args:
        value: The value to validate.
        param_name: The name of the parameter being validated.
        can_be_none: If True, None is accepted. If False, None is treated as empty.

    Returns:
        The value if it's not empty.

    Raises:
        ValidationError: If the value is empty.
    """
    if value is None:
        if can_be_none:
            return None
        else: # If None is not allowed, it's effectively "empty" in terms of required input
            raise ValidationError(f"{param_name} cannot be empty (was None).")

    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{param_name} cannot be an empty or whitespace-only string.")

    # Could add checks for collections like list, dict if needed:
    # if isinstance(value, (list, dict, tuple, set)) and not value:
    #     raise ValidationError(f"{param_name} collection cannot be empty.")

    return value

def validate_selection(
    value: Any,
    allowed_values: list,
    param_name: str = "Parameter",
    can_be_none: bool = False
) -> Any:
    """
    Validates if a value is one of the allowed selections.

    Args:
        value: The value to validate.
        allowed_values: A list of permissible values.
        param_name: The name of the parameter being validated.
        can_be_none: If True, None is considered a valid value.

    Returns:
        The value if it's valid.

    Raises:
        ValidationError: If the value is not in the allowed selections.
    """
    if value is None:
        if can_be_none:
            return None
        else:
            raise ValidationError(f"{param_name} must be selected (cannot be None).")

    if value not in allowed_values:
        raise ValidationError(f"{param_name} has an invalid selection: '{value}'. Allowed values are: {allowed_values}.")

    return value


if __name__ == '__main__':
    print("--- Testing Validation Utilities ---")

    # Test validate_numerical_range
    print("\nTesting validate_numerical_range:")
    try:
        validate_numerical_range(5, 0, 10, "TestNum")
        print("PASS: 5 in [0, 10]")
    except ValidationError as e:
        print(f"FAIL: {e}")

    try:
        validate_numerical_range(15, 0, 10, "TestNum")
        print("FAIL: Should have raised error for 15 not in [0, 10]")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for 15 not in [0, 10]: {e}")

    try:
        validate_numerical_range("abc", 0, 10, "TestNum")
        print("FAIL: Should have raised error for non-numeric 'abc'")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for non-numeric 'abc': {e}")

    try:
        validate_numerical_range(None, 0, 10, "TestNum", can_be_none=True)
        print("PASS: None allowed for TestNum when can_be_none=True")
    except ValidationError as e:
        print(f"FAIL: {e}")

    try:
        validate_numerical_range(None, 0, 10, "TestNum", can_be_none=False)
        print("FAIL: Should have raised error for None when can_be_none=False")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for None: {e}")

    try:
        validate_numerical_range(5.5, value_type=int) # Check type enforcement
        print("FAIL: Should have raised error for float when int expected by value_type (depends on strictness)")
    except ValidationError as e:
        # This might pass if float(5.5) is acceptable and then compared.
        # The current implementation casts to value_type first. int(5.5) is 5.
        # Let's test strict type before casting.
        # The current implementation of validate_numerical_range attempts to cast.
        # If strict type checking *before* casting is needed, the function would need adjustment.
        # For now, int(5.5) becomes 5, which is valid in a default [0,10] range.
        # A better test for type strictness would be `isinstance(value, value_type)`
        # before attempting conversion, if that's the desired behavior.
        # The current one is more about "can it be interpreted as this type and is it in range".
        print(f"INFO: Behavior of float for int type: {e} (value becomes int(5.5)=5)")
        # To make it fail, the range should exclude 5, e.g. min_val=6
        try:
            validate_numerical_range(5.5, min_val=6, value_type=int, param_name="IntTypeStrict")
            print("FAIL: Strict int type test.")
        except ValidationError as e_strict:
            print(f"PASS: Stricter int type test failed as expected: {e_strict}")


    # Test validate_not_empty
    print("\nTesting validate_not_empty:")
    try:
        validate_not_empty("hello", "TestStr")
        print("PASS: 'hello' is not empty")
    except ValidationError as e:
        print(f"FAIL: {e}")

    try:
        validate_not_empty("", "TestStr")
        print("FAIL: Should have raised error for empty string ''")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for empty string '': {e}")

    try:
        validate_not_empty("   ", "TestStr")
        print("FAIL: Should have raised error for whitespace string '   '")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for whitespace string '   ': {e}")

    try:
        validate_not_empty(None, "TestStr", can_be_none=True)
        print("PASS: None allowed for TestStr when can_be_none=True")
    except ValidationError as e:
        print(f"FAIL: {e}")

    try:
        validate_not_empty(None, "TestStr", can_be_none=False)
        print("FAIL: Should have raised error for None for TestStr when can_be_none=False")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for None for TestStr: {e}")

    # Test validate_selection
    print("\nTesting validate_selection:")
    options = ["OptionA", "OptionB", "OptionC"]
    try:
        validate_selection("OptionA", options, "TestSelect")
        print("PASS: 'OptionA' is in options")
    except ValidationError as e:
        print(f"FAIL: {e}")

    try:
        validate_selection("OptionD", options, "TestSelect")
        print("FAIL: Should have raised error for 'OptionD' not in options")
    except ValidationError as e:
        print(f"PASS: Correctly raised error for 'OptionD' not in options: {e}")

    try:
        validate_selection(None, options, "TestSelect", can_be_none=True)
        print("PASS: None allowed for TestSelect when can_be_none=True")
    except ValidationError as e:
        print(f"FAIL: {e}")

    print("\n--- End of Validation Utilities Tests ---")
