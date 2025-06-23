"""
Module for parsing output files or data from PLAXIS.
PRD Ref: Task 3.8
"""

from typing import List, Dict, Any, Optional, Tuple

# Placeholder for PlxScriptingError if plxscripting is not available
# This helps in environments where plxscripting might not be installed (e.g. CI linting)
try:
    from plxscripting.plx_scripting_exceptions import PlxScriptingError
except ImportError:
    class PlxScriptingError(Exception): # type: ignore
        pass


def parse_load_penetration_curve(g_o: Any,
                                 spudcan_ref_node_coords: Optional[Tuple[float, float, float]] = None,
                                 spudcan_ref_object_name: Optional[str] = None,
                                 target_phase_name: Optional[str] = None, # If None, try last phase
                                 # Parameters for curve definition if not using predefined PLAXIS curve:
                                 disp_component_result_type: Optional[Any] = None, # e.g., g_o.ResultTypes.RigidBody.Uy
                                 load_component_result_type: Optional[Any] = None, # e.g., g_o.ResultTypes.RigidBody.Fz
                                 predefined_curve_name: Optional[str] = None
                                 ) -> List[Dict[str, float]]:
    """
    Parses the load-penetration curve from PLAXIS output.
    This function tries to use a predefined PLAXIS curve if `predefined_curve_name` is given.
    Otherwise, it attempts to construct the curve by fetching step-by-step results for
    the specified displacement and load components related to the spudcan object/node
    within the target phase.

    Args:
        g_o: The PLAXIS output global object.
        spudcan_ref_node_coords: Coordinates (x,y,z) of a reference node on the spudcan.
                                 Used if `spudcan_ref_object_name` is not primary.
        spudcan_ref_object_name: Name of a reference object (e.g., a plate or rigid body) representing the spudcan.
        target_phase_name: The name of the calculation phase to extract results from. If None, uses the last phase.
        disp_component_result_type: The PLAXIS ResultType for spudcan displacement (e.g., g_o.ResultTypes.RigidBody.Uy).
        load_component_result_type: The PLAXIS ResultType for spudcan load/reaction (e.g., g_o.ResultTypes.RigidBody.Fz).
        predefined_curve_name: Name of a curve object predefined in PLAXIS (via addcurvepoint).

    Returns:
        A list of dictionaries, e.g., [{'penetration': p1, 'load': l1}, ...]
        Returns empty list if data cannot be parsed.
    """
    curve_data: List[Dict[str, float]] = []
    if not g_o:
        print("Error: PLAXIS output object (g_o) not available in parse_load_penetration_curve.")
        return curve_data

    try:
        target_phase = None
        if not target_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1] # Default to last phase
            print(f"Target phase not specified, using last phase: {target_phase.Identification if target_phase else 'N/A'}")
        elif target_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                if phase.Name == target_phase_name or phase.Identification == target_phase_name:
                    target_phase = phase
                    break

        if not target_phase:
            print(f"Error: Target phase '{target_phase_name or 'Last Phase'}' not found or no phases available.")
            return curve_data
        print(f"Parsing load-penetration curve for phase: {target_phase.Identification}")

        # Option 1: Use a predefined curve in PLAXIS
        if predefined_curve_name:
            if hasattr(g_o, 'Curves') and predefined_curve_name in g_o.Curves:
                plaxis_curve_object = g_o.Curves[predefined_curve_name]
                # The result types for X and Y axis of the curve must be known or inferred.
                # Common setup: X-axis is displacement (e.g., of a point, or MStage), Y-axis is force.
                # Example: ResultTypes.SumMstage for displacement, ResultTypes.SumFstage_Z for force
                # These need to match how the curve was defined in PLAXIS.
                # For spudcan, X might be Uy of a point, Y might be Fz of a load or reaction.
                # This part requires knowledge of the curve definition.
                # Let's assume curve X-axis is penetration, Y-axis is load for simplicity.
                # Actual ResultTypes would be passed or configured.
                # x_results, y_results = g_o.getcurveresults(plaxis_curve_object, target_phase,
                #                                          g_o.ResultTypes.YOUR_CURVE_X_AXIS_TYPE,
                #                                          g_o.ResultTypes.YOUR_CURVE_Y_AXIS_TYPE)
                # For now, this part is highly conceptual as axis types are unknown.
                print(f"STUB: Predefined curve '{predefined_curve_name}' found. Extraction needs specific X/Y ResultTypes for getcurveresults.")
                # curve_data.append({'penetration': 0.0, 'load': 0.0}) # Dummy if extracted
                # curve_data.append({'penetration': 0.5, 'load': 1000.0})
                # return curve_data # If successfully extracted from predefined curve
            else:
                print(f"Warning: Predefined curve '{predefined_curve_name}' not found. Will attempt step-by-step if other params provided.")

        # Option 2: Construct curve from step-by-step results (if predefined curve not used or failed)
        if not curve_data and spudcan_ref_object_name and disp_component_result_type and load_component_result_type:
            ref_object = None
            # Find the reference object (e.g. RigidBody, Plate) by name
            # This needs to be robust, checking available object collections in g_o
            # Example for RigidBody:
            if hasattr(g_o, 'RigidBodies') and spudcan_ref_object_name in g_o.RigidBodies:
                ref_object = g_o.RigidBodies[spudcan_ref_object_name]
            # Add checks for Plates, PointLoads (if load is directly from it), etc.
            # elif hasattr(g_o, 'Plates') and spudcan_ref_object_name in g_o.Plates:
            #    ref_object = g_o.Plates[spudcan_ref_object_name] # Note: Plate results are often nodal

            if not ref_object:
                print(f"Error: Spudcan reference object '{spudcan_ref_object_name}' not found for step-by-step curve construction.")
                return curve_data

            # Get number of steps in the phase. This API might vary.
            # num_steps = target_phase.NumberOfSteps.value (hypothetical, check PLAXIS docs)
            # Or, getresults might return arrays containing all steps.

            # Try to get arrays of results for all steps for the object and phase
            try:
                displacements_all_steps = g_o.getresults(ref_object, target_phase, disp_component_result_type, 'step')
                loads_all_steps = g_o.getresults(ref_object, target_phase, load_component_result_type, 'step')

                if isinstance(displacements_all_steps, (list, tuple)) and isinstance(loads_all_steps, (list, tuple)) and \
                   len(displacements_all_steps) == len(loads_all_steps):
                    for disp_val, load_val in zip(displacements_all_steps, loads_all_steps):
                        # Ensure values are numeric; PLAXIS API might return objects or strings sometimes
                        pen = abs(float(disp_val)) if isinstance(disp_val, (int, float, str)) else 0.0
                        load = abs(float(load_val)) if isinstance(load_val, (int, float, str)) else 0.0
                        curve_data.append({'penetration': pen, 'load': load})
                    print(f"Constructed curve with {len(curve_data)} points from step results for '{spudcan_ref_object_name}'.")
                else:
                    print(f"Warning: Mismatch in lengths or types of step results for '{spudcan_ref_object_name}'. "
                          f"Disp type: {type(displacements_all_steps)}, Load type: {type(loads_all_steps)}")
            except PlxScriptingError as pse:
                print(f"PlxScriptingError getting step results for '{spudcan_ref_object_name}': {pse}")
            except Exception as e_steps:
                print(f"Error getting step results for '{spudcan_ref_object_name}': {e_steps}")

        elif not curve_data and spudcan_ref_node_coords and disp_component_result_type and load_component_result_type:
             print(f"STUB: Step-by-step curve construction for node coordinates {spudcan_ref_node_coords} is not yet fully implemented.")
             # This would involve g_o.getsingleresult for each component for each step, if steps are iterable.

        if not curve_data: # Fallback if no data yet
            print("Warning: Load-penetration curve data remains empty after all attempts.")
            # Provide a dummy curve for testing if in a dev/test mode
            # curve_data.extend([{'penetration': 0.01*i, 'load': 100.0*i + 50* (i%2)} for i in range(1, 6)])


    except PlxScriptingError as pse:
        print(f"PLAXIS API PlxScriptingError during load-penetration curve parsing: {pse}")
    except AttributeError as ae:
        print(f"PLAXIS API attribute error (e.g., missing Phases, Curves, ResultTypes): {ae}.")
    except Exception as e:
        print(f"An unexpected error occurred during load-penetration curve parsing: {e}")

    return curve_data


def parse_final_penetration_depth(g_o: Any,
                                  spudcan_ref_node_coords: Optional[Tuple[float, float, float]] = None,
                                  spudcan_ref_object_name: Optional[str] = None,
                                  result_phase_name: Optional[str] = None, # If None, try last phase
                                  disp_component_result_type: Optional[Any] = None # e.g., g_o.ResultTypes.RigidBody.Uy
                                  ) -> Optional[float]:
    """
    Parses the final penetration depth of the spudcan from a specific phase.
    Args:
        g_o: The PLAXIS output global object.
        spudcan_ref_node_coords: Coordinates (x,y,z) of a reference node.
        spudcan_ref_object_name: Name of a reference object (e.g., RigidBody).
        result_phase_name: Name of the phase. If None, uses the last phase.
        disp_component_result_type: The specific PLAXIS ResultType for displacement.
    Returns:
        The final penetration depth (float, absolute value), or None if not found.
    """
    if not g_o:
        print("Error: PLAXIS output object (g_o) not available in parse_final_penetration_depth.")
        return None

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
            print(f"Result phase not specified, using last phase: {target_phase.Identification if target_phase else 'N/A'}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                if phase.Name == result_phase_name or phase.Identification == result_phase_name:
                    target_phase = phase
                    break

        if not target_phase:
            print(f"Error: Target phase '{result_phase_name or 'Last Phase'}' not found for final penetration.")
            return None
        print(f"Parsing final penetration depth for phase: {target_phase.Identification}")

        penetration_value: Optional[float] = None

        if spudcan_ref_object_name and disp_component_result_type:
            ref_object = None
            if hasattr(g_o, 'RigidBodies') and spudcan_ref_object_name in g_o.RigidBodies:
                ref_object = g_o.RigidBodies[spudcan_ref_object_name]
            # Add other object types like Plate if relevant

            if ref_object:
                # For objects, getresults might return a list (e.g., for each step or node).
                # We need the value at the end of the phase.
                # If 'step' specifier gives all steps, take the last one.
                # If no 'step' specifier, it might give the final value directly.
                all_values = g_o.getresults(ref_object, target_phase, disp_component_result_type) # No step specifier
                if isinstance(all_values, (list, tuple)) and all_values:
                    penetration_value = float(all_values[-1]) # Assume last value is final
                elif isinstance(all_values, (int, float)):
                    penetration_value = float(all_values)
                print(f"Retrieved penetration for object '{spudcan_ref_object_name}': {penetration_value}")
            else:
                print(f"Warning: Spudcan reference object '{spudcan_ref_object_name}' not found.")

        elif spudcan_ref_node_coords and disp_component_result_type:
            # For nodes, getsingleresult is usually appropriate for the final state of the phase.
            raw_value = g_o.getsingleresult(target_phase, disp_component_result_type, spudcan_ref_node_coords)
            if isinstance(raw_value, (int, float)):
                penetration_value = float(raw_value)
            print(f"Retrieved penetration for node {spudcan_ref_node_coords}: {penetration_value}")

        else:
            print("Error: Insufficient information (object name/type or node coords/type) to get final penetration.")
            return None

        return abs(penetration_value) if penetration_value is not None else None

    except PlxScriptingError as pse:
        print(f"PLAXIS API PlxScriptingError during final penetration parsing: {pse}.")
    except AttributeError as ae:
        print(f"PLAXIS API attribute error during final penetration parsing: {ae}.")
    except Exception as e:
        print(f"An error occurred during final penetration parsing: {e}")

    return None


def parse_peak_vertical_resistance(load_penetration_data: List[Dict[str, float]]) -> Optional[float]:
    """
    Determines the peak vertical resistance from load-penetration data.
    Args:
        load_penetration_data: A list of dictionaries [{'penetration': p, 'load': l}, ...].
    Returns:
        The peak vertical load (float, absolute value), or None if data is empty/invalid.
    """
    if not load_penetration_data:
        print("Warning: Load-penetration data is empty, cannot determine peak resistance.")
        return None

    peak_abs_load: Optional[float] = None
    try:
        for point in load_penetration_data:
            load_val = point.get('load')
            if isinstance(load_val, (int, float)):
                current_abs_load = abs(load_val)
                if peak_abs_load is None or current_abs_load > peak_abs_load:
                    peak_abs_load = current_abs_load

        if peak_abs_load is not None:
            print(f"Peak vertical resistance determined: {peak_abs_load}")
            return peak_abs_load
        else:
            print("No valid 'load' values found in load-penetration data to determine peak.")
            return None

    except Exception as e:
        print(f"Error parsing peak resistance from data: {e}")
        return None

def parse_soil_displacements(g_o: Any,
                             points_of_interest: List[Tuple[float, float, float]],
                             result_phase_name: Optional[str] = None # If None, try last phase
                             ) -> Dict[Tuple[float, float, float], Dict[str, Optional[float]]]:
    """
    Parses soil displacements (Ux, Uy, Uz, Utot) at specified points for a given phase.
    Args:
        g_o: The PLAXIS output global object.
        points_of_interest: List of (x,y,z) coordinates.
        result_phase_name: Name of the phase. If None, uses the last phase.
    Returns:
        A dictionary mapping coordinates to displacement dicts {'Ux': val, 'Uy': val, ...}.
        Values can be None if a specific result fails.
    """
    displacements_data: Dict[Tuple[float, float, float], Dict[str, Optional[float]]] = {}
    if not g_o: return displacements_data

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                if phase.Name == result_phase_name or phase.Identification == result_phase_name:
                    target_phase = phase
                    break

        if not target_phase:
            print(f"Error: Target phase '{result_phase_name or 'Last Phase'}' not found for soil displacements.")
            return displacements_data
        print(f"Parsing soil displacements for phase '{target_phase.Identification}' at {len(points_of_interest)} points...")

        for point_coords in points_of_interest:
            point_results: Dict[str, Optional[float]] = {'Ux': None, 'Uy': None, 'Uz': None, 'Utot': None}
            try:
                point_results['Ux'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Ux, point_coords))
                point_results['Uy'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Uy, point_coords))
                point_results['Uz'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Uz, point_coords))
                point_results['Utot'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Utot, point_coords))
                print(f"  Displacements at {point_coords}: Ux={point_results['Ux']:.4f}, Uy={point_results['Uy']:.4f}, Uz={point_results['Uz']:.4f}, Utot={point_results['Utot']:.4f}")
            except PlxScriptingError as pse_point:
                 print(f"  PlxScriptingError for point {point_coords}: {pse_point}")
            except Exception as e_point:
                print(f"  Could not get soil displacement for point {point_coords}: {e_point}")
            displacements_data[point_coords] = point_results

    except AttributeError as ae: # e.g. g_o.Phases or g_o.ResultTypes.Soil is missing
        print(f"PLAXIS API attribute error during soil displacement parsing: {ae}.")
    except Exception as e:
        print(f"An error occurred during soil displacement parsing: {e}")

    return displacements_data


def parse_structural_forces(g_o: Any,
                            structure_name: str,
                            structure_type: str, # e.g., "Plate", "Beam", "RigidBody"
                            result_phase_name: Optional[str] = None, # If None, try last phase
                            desired_results: Optional[List[str]] = None # e.g. ["M2D", "Q2D"] for Plate
                            ) -> Optional[Dict[str, Any]]:
    """
    Parses forces/moments for a specified structural element.
    Args:
        g_o: The PLAXIS output global object.
        structure_name: Name of the structural element.
        structure_type: Type of structure (helps select correct ResultTypes collection and attributes).
        result_phase_name: Name of the phase. If None, uses the last phase.
        desired_results: A list of specific result component names (e.g., "M2D", "Fx") to fetch.
                         If None, fetches a default set based on structure_type.
    Returns:
        A dictionary of results {result_name: value_or_list_of_values}, or None on failure.
    """
    if not g_o: return None

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                if phase.Name == result_phase_name or phase.Identification == result_phase_name:
                    target_phase = phase
                    break
        if not target_phase:
            print(f"Error: Target phase '{result_phase_name or 'Last Phase'}' not found for structural forces.")
            return None
        print(f"Parsing forces for {structure_type} '{structure_name}' in phase '{target_phase.Identification}'...")

        structural_element = None
        # Map structure_type to PLAXIS object collection and ResultTypes path
        # This is a simplified mapping; PLAXIS API can be more nuanced.
        type_map = {
            "Plate": (getattr(g_o, 'Plates', None), getattr(g_o.ResultTypes, 'Plate', None)),
            "RigidBody": (getattr(g_o, 'RigidBodies', None), getattr(g_o.ResultTypes, 'RigidBody', None)),
            "Beam": (getattr(g_o, 'Beams', None), getattr(g_o.ResultTypes, 'Beam', None)),
            # Add NodeToNodeAnchor, FixedEndAnchor, EmbeddedBeamRow, etc.
        }

        collection, result_type_enum_path = type_map.get(structure_type, (None, None))

        if not collection or not hasattr(collection, structure_name):
            print(f"Error: Structure collection for '{structure_type}' not found or element '{structure_name}' not in collection.")
            return None
        structural_element = collection[structure_name]

        if not result_type_enum_path:
            print(f"Error: ResultTypes path for '{structure_type}' not defined in parser.")
            return None

        # Define default results if not specified by caller
        if desired_results is None:
            if structure_type == "Plate": desired_results = ["M2D", "Q2D", "N1", "N2"]
            elif structure_type == "RigidBody": desired_results = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
            elif structure_type == "Beam": desired_results = ["M", "Q", "N"] # Example
            else: desired_results = []

        parsed_forces: Dict[str, Any] = {}
        for res_name in desired_results:
            try:
                if not hasattr(result_type_enum_path, res_name):
                    print(f"  Warning: Result component '{res_name}' not found in ResultTypes for '{structure_type}'. Skipping.")
                    parsed_forces[res_name] = "Error: ResultType not found"
                    continue

                plaxis_res_type = getattr(result_type_enum_path, res_name)
                # getresults specifier ('node', 'body', 'element', etc.) depends on result and object type.
                # For Plates/Beams, 'node' or 'gauss' are common. For RigidBody, often no specifier or 'body'.
                specifier = 'node' if structure_type in ["Plate", "Beam"] else None # Default or 'body' for RigidBody

                value = g_o.getresults(structural_element, target_phase, plaxis_res_type, specifier)
                parsed_forces[res_name] = value
                # print(f"  {res_name}: {str(value)[:100] + '...' if len(str(value)) > 100 else value}") # Print truncated if long list
            except PlxScriptingError as pse_res:
                print(f"  PlxScriptingError getting result '{res_name}' for {structure_name}: {pse_res}")
                parsed_forces[res_name] = f"Error: {pse_res}"
            except Exception as e_res:
                print(f"  Could not get result '{res_name}' for {structure_name}: {e_res}")
                parsed_forces[res_name] = f"Error: {e_res}"

        return parsed_forces

    except AttributeError as ae:
        print(f"PLAXIS API attribute error during structural force parsing: {ae}.")
    except Exception as e:
        print(f"An error occurred during structural force parsing: {e}")
    return None


if __name__ == '__main__':
    # This block is for STUB testing, does not connect to PLAXIS
    print("--- Testing results_parser (stub mode) ---")

    # Test parse_peak_vertical_resistance
    print("\nTesting parse_peak_vertical_resistance...")
    test_curve_data = [
        {'penetration': 0.0, 'load': 0.0}, {'penetration': 0.1, 'load': 100.0},
        {'penetration': 0.2, 'load': 250.0}, {'penetration': 0.3, 'load': 200.0},
        {'penetration': 0.25, 'load': -300.0}, # Test absolute value
    ]
    peak = parse_peak_vertical_resistance(test_curve_data)
    print(f"Peak resistance from test_curve_data: {peak} (Expected: 300.0)")

    peak_empty = parse_peak_vertical_resistance([])
    print(f"Peak resistance from empty curve: {peak_empty} (Expected: None)")

    peak_invalid_format = parse_peak_vertical_resistance([{'p':1, 'l':100}]) # Wrong keys
    print(f"Peak resistance from invalid format curve: {peak_invalid_format} (Expected: None)")

    peak_non_numeric = parse_peak_vertical_resistance([{'penetration': 0.1, 'load': 'error'}])
    print(f"Peak resistance from non-numeric load: {peak_non_numeric} (Expected: None)")


    # The other functions require a mock g_o object to test properly without a live PLAXIS connection.
    # Creating a comprehensive mock g_o is complex.
    print("\nConceptual calls for other parsers (require mock g_o for non-stub tests):")
    print("  parse_load_penetration_curve(g_o_mock, ...)")
    print("  parse_final_penetration_depth(g_o_mock, ...)")
    print("  parse_soil_displacements(g_o_mock, ...)")
    print("  parse_structural_forces(g_o_mock, ...)")

    print("\n--- End of results_parser tests (stub mode) ---")
