"""
Generates PLAXIS API callables for creating spudcan geometry.
PRD Ref: Task 3.2 (Spudcan Geometry Command Generation)

This module translates high-level spudcan parameters from `SpudcanGeometry`
into a sequence of Python functions (callables). Each callable, when executed
with a PLAXIS input global object (g_i), will perform specific API actions
to create or modify geometry in the PLAXIS model.
"""

import math
import logging
from typing import List, Callable, Any
from ..models import SpudcanGeometry
from ..exceptions import PlaxisConfigurationError # Import custom exception

logger = logging.getLogger(__name__)

# --- Main Function to Generate Spudcan Geometry Callables ---

def generate_spudcan_geometry_callables(spudcan_model: SpudcanGeometry) -> List[Callable[[Any], None]]:
    """
    Generates a list of Python callables to create the spudcan geometry in PLAXIS.
    (Args and Returns are per original spec, assumptions also largely hold)
    Raises:
        PlaxisConfigurationError: If essential parameters are missing or invalid.
    """
    callables: List[Callable[[Any], None]] = []
    logger.info(f"Generating spudcan geometry callables for diameter: {spudcan_model.diameter}, angle/height: {spudcan_model.height_cone_angle}")

    # --- Input Validation ---
    if spudcan_model.diameter is None or spudcan_model.diameter <= 0:
        msg = "Spudcan diameter must be defined and positive."
        logger.error(msg)
        raise PlaxisConfigurationError(msg)

    if spudcan_model.height_cone_angle is None or \
       not (0 < spudcan_model.height_cone_angle < 90):
        msg = "Spudcan cone angle must be defined and between 0 and 90 degrees (exclusive)."
        logger.error(msg)
        raise PlaxisConfigurationError(msg)

    # --- Parameter Calculation ---
    radius = spudcan_model.diameter / 2.0
    cone_angle_deg = spudcan_model.height_cone_angle
    cone_angle_rad = math.radians(cone_angle_deg)
    height = radius / math.tan(cone_angle_rad)
    spudcan_volume_name = "Spudcan_ConeVolume"

    # --- Callable for Creating the Cone ---
    def create_cone_callable(g_i: Any) -> None:
        logger.info(f"API CALL: Creating cone for spudcan '{spudcan_volume_name}'.")
        logger.debug(f"  Parameters: Radius={radius}, Height={height:.3f}, BaseCenter=(0,0,0), Axis=(0,0,-1)")
        try:
            cone_objects = g_i.cone(radius, height, (0,0,0), (0,0,-1))
            if not cone_objects: # Should ideally not happen if g_i.cone is successful
                # This might indicate an issue with the PLAXIS environment or a very unusual API return
                raise PlaxisConfigurationError("g_i.cone command did not return any objects, though no direct PlxScriptingError was raised.")

            cone_volume = cone_objects[0]
            logger.info(f"  Cone volume created successfully: {cone_volume}")

            g_i.rename(cone_volume, spudcan_volume_name)
            logger.info(f"  Renamed cone volume to '{spudcan_volume_name}'.")
        except Exception as e: # Catch PlxScriptingError or other Python errors
            logger.error(f"ERROR during spudcan cone creation/renaming for '{spudcan_volume_name}': {e}", exc_info=True)
            # Re-raise the original exception. The PlaxisInteractor will map it.
            raise

    callables.append(create_cone_callable)

    # No need to check `if not callables:` here, as an exception would have been raised if parameters were bad.
    logger.info(f"Generated {len(callables)} geometry callable(s) for spudcan.")
    return callables


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("--- Testing Spudcan Geometry Callable Generation (with Exception Handling) ---")

    class MockG_i:
        # ... (MockG_i remains the same as in the SEARCH block) ...
        def __init__(self):
            self.Volumes = []
            self.log = []
            self._object_counter = 0

        def _create_mock_object(self, type_name="Object"):
            self._object_counter +=1
            return f"Mock{type_name}_{self._object_counter}"

        def cone(self, radius, height, base_center, axis_vector):
            cmd_str = f"cone R={radius} H={height} Base={base_center} Axis={axis_vector}"
            self.log.append(f"DIRECT_API_CALL: {cmd_str}")
            logger.debug(f"  MockG_i.cone executed: {cmd_str}")

            # Simulate failure for a specific test case
            if radius == -100.0: # Arbitrary condition to simulate failure
                 raise Exception("Simulated PlxScriptingError: Invalid radius for cone from mock.")

            new_vol = self._create_mock_object("ConeVolume")
            self.Volumes.append(new_vol)
            return [new_vol]

        def rename(self, obj_ref: Any, new_name: str):
            self.log.append(f"RENAME: {obj_ref} to {new_name}")
            logger.debug(f"  MockG_i.rename executed: {obj_ref} to {new_name}")
            if isinstance(obj_ref, str) and obj_ref in self.Volumes:
                pass

    # Test case 1: Valid spudcan
    sample_spudcan_valid = SpudcanGeometry(diameter=6.0, height_cone_angle=30.0)
    logger.info(f"\nTesting with valid spudcan: D={sample_spudcan_valid.diameter}, Angle={sample_spudcan_valid.height_cone_angle}")
    try:
        generated_callables_valid = generate_spudcan_geometry_callables(sample_spudcan_valid)
        logger.info(f"Generated {len(generated_callables_valid)} callables.")

        mock_g_i_instance_valid = MockG_i()
        for i, callable_func in enumerate(generated_callables_valid):
            logger.info(f"Executing callable {i+1}/{len(generated_callables_valid)} ({getattr(callable_func, '__name__', 'lambda')})...")
            try:
                callable_func(mock_g_i_instance_valid)
            except Exception as e_exec: # Catch errors from mock execution
                logger.error(f"  Error executing callable with mock: {e_exec}", exc_info=True)
        logger.info("Log of mock g_i commands for valid spudcan:")
        for entry in mock_g_i_instance_valid.log: logger.info(f"  - {entry}")
    except PlaxisConfigurationError as pce:
        logger.error(f"UNEXPECTED PlaxisConfigurationError for valid model: {pce}", exc_info=True)


    # Test case 2: Invalid cone angle
    sample_spudcan_invalid_angle = SpudcanGeometry(diameter=6.0, height_cone_angle=90.0)
    logger.info(f"\nTesting with invalid cone angle: D={sample_spudcan_invalid_angle.diameter}, Angle={sample_spudcan_invalid_angle.height_cone_angle}")
    try:
        generate_spudcan_geometry_callables(sample_spudcan_invalid_angle)
        logger.error("UNEXPECTED: generate_spudcan_geometry_callables did not raise for invalid angle.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for invalid angle: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED exception type for invalid angle: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)


    # Test case 3: Missing diameter (diameter=None)
    sample_spudcan_no_diameter = SpudcanGeometry(height_cone_angle=30.0)
    logger.info(f"\nTesting with missing diameter (None): Angle={sample_spudcan_no_diameter.height_cone_angle}")
    try:
        generate_spudcan_geometry_callables(sample_spudcan_no_diameter)
        logger.error("UNEXPECTED: generate_spudcan_geometry_callables did not raise for missing diameter.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for missing diameter: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED exception type for missing diameter: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)

    # Test case 4: Zero diameter
    sample_spudcan_zero_diameter = SpudcanGeometry(diameter=0.0, height_cone_angle=30.0)
    logger.info(f"\nTesting with zero diameter: D={sample_spudcan_zero_diameter.diameter}, Angle={sample_spudcan_zero_diameter.height_cone_angle}")
    try:
        generate_spudcan_geometry_callables(sample_spudcan_zero_diameter)
        logger.error("UNEXPECTED: generate_spudcan_geometry_callables did not raise for zero diameter.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for zero diameter: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED exception type for zero diameter: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)


    # Test case 5: Simulating an error during the execution of a callable (e.g., PlxScriptingError from g_i.cone)
    logger.info(f"\nTesting simulation of PlxScriptingError during callable execution:")
    # Create a model that would pass initial validation but cause mock g_i to fail
    error_sim_model = SpudcanGeometry(diameter=-100.0, height_cone_angle=30.0) # Use a normally invalid diameter to trigger mock failure
    try:
        # This first call should raise PlaxisConfigurationError due to diameter validation
        error_sim_callables = generate_spudcan_geometry_callables(error_sim_model)
        logger.error("UNEXPECTED: generate_spudcan_geometry_callables did not raise for error_sim_model initially.")
    except PlaxisConfigurationError as pce_setup:
        logger.info(f"SUCCESS: Correctly caught PlaxisConfigurationError during setup for error_sim_model: {pce_setup}")

    # To test error during callable execution, we need valid setup callables first
    valid_model_for_exec_test = SpudcanGeometry(diameter=5.0, height_cone_angle=45.0)
    callables_for_exec_test = generate_spudcan_geometry_callables(valid_model_for_exec_test)

    mock_g_i_for_exec_fail = MockG_i()
    # Modify the model or mock_g_i so cone call fails
    # Here, we'll rely on the MockG_i's internal logic to fail if radius is -100.0 (which it won't be here)
    # So, let's simulate the callable itself raising an error if g_i.cone fails
    # The current mock_g_i.cone has: if radius == -100.0: raise Exception(...)
    # The current `create_cone_callable` re-raises.

    # This test is slightly artificial as the mock needs to be set up to fail.
    # The key is that `create_cone_callable` should propagate the exception from `g_i.cone`.
    # Let's assume `g_i.cone` itself raises PlxScriptingError for some reason.
    # The `create_cone_callable` catches `Exception as e` and re-raises `e`.
    # The `PlaxisInteractor` would then catch this `e` and map it using `_map_plaxis_sdk_exception_to_custom`.
    logger.info("Note: Testing error propagation from callable execution relies on PlaxisInteractor's mapping.")
    logger.info("If a PlxScriptingError occurs inside a callable, it should be caught and mapped by the calling Interactor method.")


    logger.info("\n--- End of Geometry Builder Callable Generation Tests (with Exception Handling) ---")
