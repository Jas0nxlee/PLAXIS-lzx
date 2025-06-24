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
    logger.info("Starting load-penetration curve parsing.")
    curve_data: List[Dict[str, float]] = []
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available in parse_load_penetration_curve.")
        return curve_data

    try:
        target_phase = None
        if not target_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1] # Default to last phase
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            logger.info(f"Target phase not specified, using last phase: {phase_id_val}")
        elif target_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == target_phase_name or phase_id_val == target_phase_name:
                    target_phase = phase
                    logger.debug(f"Found target phase by name/ID: {target_phase_name}")
                    break

        if not target_phase:
            logger.error(f"Target phase '{target_phase_name or 'Last Phase'}' not found or no phases available.")
            return curve_data

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        logger.info(f"Parsing load-penetration curve for phase: {phase_id_val_found}")

        # Option 1: Use a predefined curve in PLAXIS
        if predefined_curve_name and curve_x_axis_result_type and curve_y_axis_result_type:
            logger.info(f"Attempting to extract predefined curve '{predefined_curve_name}'.")
            if hasattr(g_o, 'Curves') and predefined_curve_name in g_o.Curves:
                plaxis_curve_object = g_o.Curves[predefined_curve_name]
                logger.debug(f"Found predefined curve object '{predefined_curve_name}'. Using getcurveresults.")
                try:
                    x_results, y_results = g_o.getcurveresults(plaxis_curve_object, target_phase,
                                                             curve_x_axis_result_type,
                                                             curve_y_axis_result_type)
                    if isinstance(x_results, (list, tuple)) and isinstance(y_results, (list, tuple)) and len(x_results) == len(y_results):
                        for x_val, y_val in zip(x_results, y_results):
                            pen = abs(float(x_val)) if isinstance(x_val, (int, float, str)) else 0.0
                            load = abs(float(y_val)) if isinstance(y_val, (int, float, str)) else 0.0
                            curve_data.append({'penetration': pen, 'load': load})
                        logger.info(f"Extracted {len(curve_data)} points from predefined curve '{predefined_curve_name}'.")
                    else:
                        logger.warning(f"Mismatch in lengths or types from getcurveresults for '{predefined_curve_name}'. X type: {type(x_results)}, Y type: {type(y_results)}")
                except PlxScriptingError as pse_curve:
                    logger.error(f"PlxScriptingError getting predefined curve results for '{predefined_curve_name}': {pse_curve}", exc_info=True)
                except Exception as e_curve:
                    logger.error(f"Error getting predefined curve results for '{predefined_curve_name}': {e_curve}", exc_info=True)
            else:
                logger.warning(f"Predefined curve '{predefined_curve_name}' not found in g_o.Curves or axis ResultTypes not provided. Will attempt step-by-step if other params provided.")

        # Option 2: Construct curve from step-by-step results for an object
        if not curve_data and spudcan_ref_object_name and step_disp_component_result_type and step_load_component_result_type:
            logger.info(f"Attempting step-by-step curve construction for object '{spudcan_ref_object_name}'.")
            ref_object = None
            if hasattr(g_o, 'RigidBodies') and spudcan_ref_object_name in g_o.RigidBodies:
                ref_object = g_o.RigidBodies[spudcan_ref_object_name]
            elif hasattr(g_o, 'Plates') and spudcan_ref_object_name in g_o.Plates:
                 ref_object = g_o.Plates[spudcan_ref_object_name]

            if not ref_object:
                logger.error(f"Spudcan reference object '{spudcan_ref_object_name}' not found for step-by-step curve construction.")
                return curve_data

            logger.debug(f"Found reference object '{spudcan_ref_object_name}'. Using getresults.")
            try:
                displacements_all_steps = g_o.getresults(ref_object, target_phase, step_disp_component_result_type, 'step')
                loads_all_steps = g_o.getresults(ref_object, target_phase, step_load_component_result_type, 'step')

                if isinstance(displacements_all_steps, (list, tuple)) and isinstance(loads_all_steps, (list, tuple)) and \
                   len(displacements_all_steps) == len(loads_all_steps):
                    for disp_val, load_val in zip(displacements_all_steps, loads_all_steps):
                        pen = abs(float(disp_val)) if isinstance(disp_val, (int, float, str)) else 0.0
                        load = abs(float(load_val)) if isinstance(load_val, (int, float, str)) else 0.0
                        curve_data.append({'penetration': pen, 'load': load})
                    logger.info(f"Constructed curve with {len(curve_data)} points from step results for '{spudcan_ref_object_name}'.")
                else:
                    logger.warning(f"Mismatch in lengths or types of step results for '{spudcan_ref_object_name}'. "
                                   f"Disp type: {type(displacements_all_steps)}, Load type: {type(loads_all_steps)}")
            except PlxScriptingError as pse_steps:
                logger.error(f"PlxScriptingError getting step results for '{spudcan_ref_object_name}': {pse_steps}", exc_info=True)
            except Exception as e_steps:
                logger.error(f"Error getting step results for '{spudcan_ref_object_name}': {e_steps}", exc_info=True)

        # Option 3: Construct curve from step-by-step results for a node (STUB)
        elif not curve_data and spudcan_ref_node_coords and step_disp_component_result_type and step_load_component_result_type:
             logger.warning(f"STUB: Step-by-step curve construction for node coordinates {spudcan_ref_node_coords} is not yet fully implemented.")

        if not curve_data:
            logger.warning("Load-penetration curve data remains empty after all attempts.")

    except PlxScriptingError as pse:
        logger.error(f"PLAXIS API PlxScriptingError during load-penetration curve parsing: {pse}", exc_info=True)
    except AttributeError as ae:
        logger.error(f"PLAXIS API attribute error (e.g., missing Phases, Curves, ResultTypes, or sub-attributes like .value): {ae}.", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred during load-penetration curve parsing: {e}", exc_info=True)

    logger.info(f"Finished load-penetration curve parsing. {len(curve_data)} points generated.")
    return curve_data


def parse_final_penetration_depth(g_o: Any,
                                  spudcan_ref_node_coords: Optional[Tuple[float, float, float]] = None,
                                  spudcan_ref_object_name: Optional[str] = None,
                                  result_phase_name: Optional[str] = None,
                                  disp_component_result_type: Optional[Any] = None
                                  ) -> Optional[float]:
    """
    Parses the final penetration depth of the spudcan from a specific phase.
    (Args and Returns are per original spec)
    """
    logger.info("Starting final penetration depth parsing.")
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available in parse_final_penetration_depth.")
        return None

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            logger.info(f"Result phase not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase
                    logger.debug(f"Found target phase for final penetration: {result_phase_name}")
                    break

        if not target_phase:
            logger.error(f"Target phase '{result_phase_name or 'Last Phase'}' not found for final penetration.")
            return None

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        logger.info(f"Parsing final penetration depth for phase: {phase_id_val_found}")

        penetration_value: Optional[float] = None

        if spudcan_ref_object_name and disp_component_result_type:
            logger.debug(f"Attempting to get penetration for object '{spudcan_ref_object_name}'.")
            ref_object = None
            if hasattr(g_o, 'RigidBodies') and spudcan_ref_object_name in g_o.RigidBodies:
                ref_object = g_o.RigidBodies[spudcan_ref_object_name]

            if ref_object:
                all_values = g_o.getresults(ref_object, target_phase, disp_component_result_type)
                if isinstance(all_values, (list, tuple)) and all_values:
                    penetration_value = float(all_values[-1])
                elif isinstance(all_values, (int, float)):
                    penetration_value = float(all_values)
                logger.info(f"Retrieved penetration for object '{spudcan_ref_object_name}': {penetration_value}")
            else:
                logger.warning(f"Spudcan reference object '{spudcan_ref_object_name}' not found.")

        elif spudcan_ref_node_coords and disp_component_result_type:
            logger.debug(f"Attempting to get penetration for node {spudcan_ref_node_coords}.")
            raw_value = g_o.getsingleresult(target_phase, disp_component_result_type, spudcan_ref_node_coords)
            if isinstance(raw_value, (int, float)):
                penetration_value = float(raw_value)
            logger.info(f"Retrieved penetration for node {spudcan_ref_node_coords}: {penetration_value}")
        else:
            logger.error("Insufficient information (object name/type or node coords/type) to get final penetration.")
            return None

        final_pen = abs(penetration_value) if penetration_value is not None else None
        logger.info(f"Finished final penetration depth parsing. Value: {final_pen}")
        return final_pen

    except PlxScriptingError as pse:
        logger.error(f"PLAXIS API PlxScriptingError during final penetration parsing: {pse}.", exc_info=True)
    except AttributeError as ae:
        logger.error(f"PLAXIS API attribute error during final penetration parsing: {ae}.", exc_info=True)
    except Exception as e:
        logger.error(f"An error occurred during final penetration parsing: {e}", exc_info=True)
    return None


def parse_peak_vertical_resistance(load_penetration_data: List[Dict[str, float]]) -> Optional[float]:
    """
    Determines the peak vertical resistance from load-penetration data.
    (Args and Returns are per original spec)
    """
    logger.info("Parsing peak vertical resistance from curve data.")
    if not load_penetration_data:
        logger.warning("Load-penetration data is empty, cannot determine peak resistance.")
        return None

    peak_abs_load: Optional[float] = None
    try:
        for point in load_penetration_data:
            load_val = point.get('load')
            if isinstance(load_val, (int, float)):
                current_abs_load = abs(load_val)
                if peak_abs_load is None or current_abs_load > peak_abs_load:
                    peak_abs_load = current_abs_load
            else:
                logger.debug(f"Non-numeric or missing 'load' value in point: {point}")


        if peak_abs_load is not None:
            logger.info(f"Peak vertical resistance determined: {peak_abs_load}")
            return peak_abs_load
        else:
            logger.warning("No valid 'load' values found in load-penetration data to determine peak.")
            return None

    except Exception as e:
        logger.error(f"Error parsing peak resistance from data: {e}", exc_info=True)
        return None

def parse_soil_displacements(g_o: Any,
                             points_of_interest: List[Tuple[float, float, float]],
                             result_phase_name: Optional[str] = None
                             ) -> Dict[Tuple[float, float, float], Dict[str, Optional[float]]]:
    """
    Parses soil displacements (Ux, Uy, Uz, Utot) at specified points for a given phase.
    (Args and Returns are per original spec)
    """
    logger.info(f"Starting soil displacement parsing for {len(points_of_interest)} points.")
    displacements_data: Dict[Tuple[float, float, float], Dict[str, Optional[float]]] = {}
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available for soil displacement parsing.")
        return displacements_data

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            logger.info(f"Target phase for soil displacements not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase
                    logger.debug(f"Found target phase for soil displacements: {result_phase_name}")
                    break

        if not target_phase:
            logger.error(f"Target phase '{result_phase_name or 'Last Phase'}' not found for soil displacements.")
            return displacements_data

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        logger.info(f"Parsing soil displacements for phase '{phase_id_val_found}' at {len(points_of_interest)} points.")

        for point_coords in points_of_interest:
            logger.debug(f"  Getting displacements for point {point_coords}")
            point_results: Dict[str, Optional[float]] = {'Ux': None, 'Uy': None, 'Uz': None, 'Utot': None}
            try:
                # Ensure ResultTypes.Soil path is valid
                if not hasattr(g_o, 'ResultTypes') or not hasattr(g_o.ResultTypes, 'Soil'):
                    logger.error("g_o.ResultTypes.Soil path not found. Cannot get soil displacements.")
                    # Populate with errors or skip, depending on desired strictness
                    displacements_data[point_coords] = {k: "Error: ResultTypes.Soil missing" for k in point_results} # type: ignore
                    continue

                point_results['Ux'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Ux, point_coords))
                point_results['Uy'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Uy, point_coords))
                point_results['Uz'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Uz, point_coords))
                point_results['Utot'] = float(g_o.getsingleresult(target_phase, g_o.ResultTypes.Soil.Utot, point_coords))
                logger.debug(f"  Displacements at {point_coords}: Ux={point_results['Ux']:.4f}, Uy={point_results['Uy']:.4f}, Uz={point_results['Uz']:.4f}, Utot={point_results['Utot']:.4f}")
            except PlxScriptingError as pse_point:
                 logger.error(f"  PlxScriptingError for point {point_coords}: {pse_point}", exc_info=True)
            except Exception as e_point:
                logger.error(f"  Could not get soil displacement for point {point_coords}: {e_point}", exc_info=True)
            displacements_data[point_coords] = point_results

        logger.info("Finished soil displacement parsing.")

    except AttributeError as ae:
        logger.error(f"PLAXIS API attribute error during soil displacement parsing: {ae}.", exc_info=True)
    except Exception as e:
        logger.error(f"An error occurred during soil displacement parsing: {e}", exc_info=True)

    return displacements_data


def parse_structural_forces(g_o: Any,
                            structure_name: str,
                            structure_type: str,
                            result_phase_name: Optional[str] = None,
                            desired_results: Optional[List[str]] = None
                            ) -> Optional[Dict[str, Any]]:
    """
    Parses forces/moments for a specified structural element.
    (Args and Returns are per original spec)
    """
    logger.info(f"Starting structural forces parsing for {structure_type} '{structure_name}'.")
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available for structural forces parsing.")
        return None

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            logger.info(f"Target phase for structural forces not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase in g_o.Phases:
                phase_id_val = getattr(getattr(phase, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase
                    logger.debug(f"Found target phase for structural forces: {result_phase_name}")
                    break
        if not target_phase:
            logger.error(f"Target phase '{result_phase_name or 'Last Phase'}' not found for structural forces.")
            return None

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        logger.info(f"Parsing forces for {structure_type} '{structure_name}' in phase '{phase_id_val_found}'.")

        structural_element = None
        type_map = {
            "Plate": (getattr(g_o, 'Plates', None), getattr(g_o.ResultTypes, 'Plate', None)),
            "RigidBody": (getattr(g_o, 'RigidBodies', None), getattr(g_o.ResultTypes, 'RigidBody', None)),
            "Beam": (getattr(g_o, 'Beams', None), getattr(g_o.ResultTypes, 'Beam', None)),
        }

        collection, result_type_enum_path = type_map.get(structure_type, (None, None))

        if not collection or not hasattr(collection, structure_name): # Check if collection itself is None first
            if not collection: logger.error(f"Structure collection for '{structure_type}' not found in g_o (e.g., g_o.Plates).")
            else: logger.error(f"Element '{structure_name}' not found in collection for '{structure_type}'.")
            return None
        structural_element = collection[structure_name]
        logger.debug(f"Found structural element '{structure_name}'.")


        if not result_type_enum_path: # Check if ResultTypes path is valid
            logger.error(f"ResultTypes path for '{structure_type}' not defined in parser or not found in g_o.ResultTypes.")
            return None

        if desired_results is None:
            if structure_type == "Plate": desired_results = ["M2D", "Q2D", "N1", "N2"]
            elif structure_type == "RigidBody": desired_results = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
            elif structure_type == "Beam": desired_results = ["N", "Q12", "Q13", "M1", "M2", "M3"]
            else: desired_results = []
            logger.debug(f"Using default desired_results for {structure_type}: {desired_results}")


        parsed_forces: Dict[str, Any] = {}
        for res_name in desired_results:
            logger.debug(f"  Attempting to get result '{res_name}'.")
            try:
                if not hasattr(result_type_enum_path, res_name):
                    logger.warning(f"  Result component '{res_name}' not found in ResultTypes for '{structure_type}'. Skipping.")
                    parsed_forces[res_name] = "Error: ResultType not found"
                    continue

                plaxis_res_type = getattr(result_type_enum_path, res_name)
                specifier = 'node' if structure_type in ["Plate", "Beam"] else None

                value = g_o.getresults(structural_element, target_phase, plaxis_res_type, specifier)
                parsed_forces[res_name] = value
                logger.debug(f"  Successfully retrieved '{res_name}'.")
            except PlxScriptingError as pse_res:
                logger.error(f"  PlxScriptingError getting result '{res_name}' for {structure_name}: {pse_res}", exc_info=True)
                parsed_forces[res_name] = f"Error: {pse_res}"
            except Exception as e_res:
                logger.error(f"  Could not get result '{res_name}' for {structure_name}: {e_res}", exc_info=True)
                parsed_forces[res_name] = f"Error: {e_res}"

        logger.info(f"Finished structural forces parsing for {structure_type} '{structure_name}'.")
        return parsed_forces

    except AttributeError as ae:
        logger.error(f"PLAXIS API attribute error during structural force parsing: {ae}.", exc_info=True)
    except Exception as e:
        logger.error(f"An error occurred during structural force parsing: {e}", exc_info=True)
    return None


if __name__ == '__main__':
    # Setup basic logging for console output during direct script run
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Testing results_parser (stub mode with logging) ---")

    logger.info("\nTesting parse_peak_vertical_resistance...")
    test_curve_data = [
        {'penetration': 0.0, 'load': 0.0}, {'penetration': 0.1, 'load': 100.0},
        {'penetration': 0.2, 'load': 250.0}, {'penetration': 0.3, 'load': 200.0},
        {'penetration': 0.25, 'load': -300.0},
    ]
    peak = parse_peak_vertical_resistance(test_curve_data)
    logger.info(f"Peak resistance from test_curve_data: {peak} (Expected: 300.0)")

    peak_empty = parse_peak_vertical_resistance([])
    logger.info(f"Peak resistance from empty curve: {peak_empty} (Expected: None)")

    peak_invalid_format = parse_peak_vertical_resistance([{'p':1, 'l':100}])
    logger.info(f"Peak resistance from invalid format curve: {peak_invalid_format} (Expected: None)")

    peak_non_numeric = parse_peak_vertical_resistance([{'penetration': 0.1, 'load': 'error'}])
    logger.info(f"Peak resistance from non-numeric load: {peak_non_numeric} (Expected: None)")

    logger.info("\nConceptual calls for other parsers (require mock g_o for non-stub tests):")
    logger.info("  parse_load_penetration_curve(g_o_mock, ...)")
    logger.info("  parse_final_penetration_depth(g_o_mock, ...)")
    logger.info("  parse_soil_displacements(g_o_mock, ...)")
    logger.info("  parse_structural_forces(g_o_mock, ...)")

    logger.info("\n--- End of results_parser tests (stub mode with logging) ---")
