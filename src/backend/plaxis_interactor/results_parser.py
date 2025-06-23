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
                                 target_phase_name: Optional[str] = None, # If None, try last phase
                                 # For predefined curves:
                                 predefined_curve_name: Optional[str] = None,
                                 # ResultTypes for X and Y axes of the predefined PLAXIS curve
                                 # These might be different from components used for step-by-step construction.
                                 # e.g. g_o.ResultTypes.SumMstage for displacement, g_o.ResultTypes.SumFstage_Z for force
                                 curve_x_axis_result_type: Optional[Any] = None,
                                 curve_y_axis_result_type: Optional[Any] = None,
                                 # For step-by-step construction if predefined_curve_name is not used/found:
                                 spudcan_ref_node_coords: Optional[Tuple[float, float, float]] = None,
                                 spudcan_ref_object_name: Optional[str] = None,
                                 # ResultTypes for individual displacement and load components of the spudcan object/node
                                 step_disp_component_result_type: Optional[Any] = None, # e.g., g_o.ResultTypes.RigidBody.Uy
                                 step_load_component_result_type: Optional[Any] = None  # e.g., g_o.ResultTypes.RigidBody.Fz
                                 ) -> List[Dict[str, float]]:
    """
    Parses the load-penetration curve from PLAXIS output.

    Priority:
    1. If `predefined_curve_name` and its axis ResultTypes (`curve_x_axis_result_type`, `curve_y_axis_result_type`)
       are provided, attempts to use `g_o.getcurveresults`.
    2. If that fails or is not applicable, and if `spudcan_ref_object_name` and its component ResultTypes
       (`step_disp_component_result_type`, `step_load_component_result_type`) are provided,
       attempts to construct the curve step-by-step using `g_o.getresults`.
    3. If that also fails or is not applicable, and if `spudcan_ref_node_coords` and its component ResultTypes
       are provided, this part is currently a STUB and would need implementation for step-by-step node results.

    Args:
        g_o: The PLAXIS output global object.
        target_phase_name: The name of the calculation phase. If None, uses the last phase.

        predefined_curve_name: Name of a curve object predefined in PLAXIS (e.g., via `addcurvepoint` in Output).
        curve_x_axis_result_type: PLAXIS ResultType for the X-axis of the `predefined_curve_name`.
                                  This is CRITICAL for `getcurveresults` to function correctly.
        curve_y_axis_result_type: PLAXIS ResultType for the Y-axis of the `predefined_curve_name`.
                                  This is CRITICAL for `getcurveresults` to function correctly.

        spudcan_ref_node_coords: Coordinates (x,y,z) of a reference node on the spudcan for step-by-step.
        spudcan_ref_object_name: Name of a reference object (e.g., RigidBody, Plate) for step-by-step results.
        step_disp_component_result_type: PLAXIS ResultType for the spudcan's displacement component for step-by-step.
        step_load_component_result_type: PLAXIS ResultType for the spudcan's load/reaction component for step-by-step.

    Returns:
        A list of dictionaries, e.g., [{'penetration': p1, 'load': l1}, ...].
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
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            print(f"Target phase not specified, using last phase: {phase_id_val}")
        elif target_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == target_phase_name or phase_id_val == target_phase_name:
                    target_phase = phase
                    break

        if not target_phase:
            print(f"Error: Target phase '{target_phase_name or 'Last Phase'}' not found or no phases available.")
            return curve_data

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        print(f"Parsing load-penetration curve for phase: {phase_id_val_found}")

        # Option 1: Use a predefined curve in PLAXIS
        if predefined_curve_name and curve_x_axis_result_type and curve_y_axis_result_type:
            if hasattr(g_o, 'Curves') and predefined_curve_name in g_o.Curves:
                plaxis_curve_object = g_o.Curves[predefined_curve_name]
                print(f"Attempting to extract predefined curve '{predefined_curve_name}' using getcurveresults.")
                try:
                    x_results, y_results = g_o.getcurveresults(plaxis_curve_object, target_phase,
                                                             curve_x_axis_result_type,
                                                             curve_y_axis_result_type)
                    if isinstance(x_results, (list, tuple)) and isinstance(y_results, (list, tuple)) and len(x_results) == len(y_results):
                        for x_val, y_val in zip(x_results, y_results):
                            pen = abs(float(x_val)) if isinstance(x_val, (int, float, str)) else 0.0
                            load = abs(float(y_val)) if isinstance(y_val, (int, float, str)) else 0.0
                            curve_data.append({'penetration': pen, 'load': load})
                        print(f"Extracted {len(curve_data)} points from predefined curve '{predefined_curve_name}'.")
                    else:
                        print(f"Warning: Mismatch in lengths or types from getcurveresults for '{predefined_curve_name}'. X type: {type(x_results)}, Y type: {type(y_results)}")
                except PlxScriptingError as pse_curve:
                    print(f"PlxScriptingError getting predefined curve results for '{predefined_curve_name}': {pse_curve}")
                except Exception as e_curve: # Catch any other error during getcurveresults
                    print(f"Error getting predefined curve results for '{predefined_curve_name}': {e_curve}")
            else:
                print(f"Warning: Predefined curve '{predefined_curve_name}' not found in g_o.Curves or axis ResultTypes not provided. Will attempt step-by-step if other params provided.")

        # Option 2: Construct curve from step-by-step results for an object (if predefined curve not used or failed)
        if not curve_data and spudcan_ref_object_name and step_disp_component_result_type and step_load_component_result_type:
            ref_object = None
            # Find the reference object (e.g. RigidBody, Plate) by name
            if hasattr(g_o, 'RigidBodies') and spudcan_ref_object_name in g_o.RigidBodies:
                ref_object = g_o.RigidBodies[spudcan_ref_object_name]
            elif hasattr(g_o, 'Plates') and spudcan_ref_object_name in g_o.Plates: # Example for another type
                 ref_object = g_o.Plates[spudcan_ref_object_name]
            # Add more checks for other relevant object types if necessary

            if not ref_object:
                print(f"Error: Spudcan reference object '{spudcan_ref_object_name}' not found for step-by-step curve construction.")
                return curve_data

            print(f"Attempting step-by-step curve construction for object '{spudcan_ref_object_name}'.")
            try:
                displacements_all_steps = g_o.getresults(ref_object, target_phase, step_disp_component_result_type, 'step')
                loads_all_steps = g_o.getresults(ref_object, target_phase, step_load_component_result_type, 'step')

                if isinstance(displacements_all_steps, (list, tuple)) and isinstance(loads_all_steps, (list, tuple)) and \
                   len(displacements_all_steps) == len(loads_all_steps):
                    for disp_val, load_val in zip(displacements_all_steps, loads_all_steps):
                        pen = abs(float(disp_val)) if isinstance(disp_val, (int, float, str)) else 0.0
                        load = abs(float(load_val)) if isinstance(load_val, (int, float, str)) else 0.0
                        curve_data.append({'penetration': pen, 'load': load})
                    print(f"Constructed curve with {len(curve_data)} points from step results for '{spudcan_ref_object_name}'.")
                else:
                    print(f"Warning: Mismatch in lengths or types of step results for '{spudcan_ref_object_name}'. "
                          f"Disp type: {type(displacements_all_steps)}, Load type: {type(loads_all_steps)}")
            except PlxScriptingError as pse_steps:
                print(f"PlxScriptingError getting step results for '{spudcan_ref_object_name}': {pse_steps}")
            except Exception as e_steps:
                print(f"Error getting step results for '{spudcan_ref_object_name}': {e_steps}")

        # Option 3: Construct curve from step-by-step results for a node (STUB)
        elif not curve_data and spudcan_ref_node_coords and step_disp_component_result_type and step_load_component_result_type:
             print(f"STUB: Step-by-step curve construction for node coordinates {spudcan_ref_node_coords} is not yet fully implemented.")
             # This would involve iterating through steps (if possible via API) and calling getsingleresult for each.
             # Example:
             # num_steps = target_phase.NumberOfSteps.value # This needs to be a valid API call
             # for step_index in range(num_steps):
             #     current_step_obj = target_phase.Steps[step_index] # This needs to be valid
             #     disp_val = g_o.getsingleresult(current_step_obj, step_disp_component_result_type, spudcan_ref_node_coords)
             #     load_val = g_o.getsingleresult(current_step_obj, step_load_component_result_type, spudcan_ref_node_coords)
             #     # ... append to curve_data ...


        if not curve_data: # Fallback if no data yet
            print("Warning: Load-penetration curve data remains empty after all attempts.")
            # Provide a dummy curve for testing if in a dev/test mode
            # curve_data.extend([{'penetration': 0.01*i, 'load': 100.0*i + 50* (i%2)} for i in range(1, 6)])

    except PlxScriptingError as pse:
        print(f"PLAXIS API PlxScriptingError during load-penetration curve parsing: {pse}")
    except AttributeError as ae: # Catches errors like g_o.Phases not existing or phase.Identification.value on None
        print(f"PLAXIS API attribute error (e.g., missing Phases, Curves, ResultTypes, or sub-attributes like .value): {ae}.")
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
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            print(f"Result phase not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase
                    break

        if not target_phase:
            print(f"Error: Target phase '{result_phase_name or 'Last Phase'}' not found for final penetration.")
            return None

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        print(f"Parsing final penetration depth for phase: {phase_id_val_found}")


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
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            print(f"Target phase for soil displacements not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase
                    break

        if not target_phase:
            print(f"Error: Target phase '{result_phase_name or 'Last Phase'}' not found for soil displacements.")
            return displacements_data

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        print(f"Parsing soil displacements for phase '{phase_id_val_found}' at {len(points_of_interest)} points...")


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
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            print(f"Target phase for structural forces not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase
                    break
        if not target_phase:
            print(f"Error: Target phase '{result_phase_name or 'Last Phase'}' not found for structural forces.")
            return None

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        print(f"Parsing forces for {structure_type} '{structure_name}' in phase '{phase_id_val_found}'...")


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
            if structure_type == "Plate": desired_results = ["M2D", "Q2D", "N1", "N2"] # Example from all.md: M11, M22, N11, N22, Q12, Q13, Q23
            elif structure_type == "RigidBody": desired_results = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
            elif structure_type == "Beam": desired_results = ["N", "Q12", "Q13", "M1", "M2", "M3"] # Example from all.md: N, Q12, Q13, M1, M2, M3
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
