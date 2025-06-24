"""
Module for parsing output files or data from PLAXIS.
PRD Ref: Task 3.8
"""
import logging # Added logging
from typing import List, Dict, Any, Optional, Tuple, Callable # Added Callable

# Placeholder for PlxScriptingError if plxscripting is not available
# This helps in environments where plxscripting might not be installed (e.g. CI linting)
try:
    from plxscripting.plx_scripting_exceptions import PlxScriptingError
except ImportError:
    class PlxScriptingError(Exception): # type: ignore
        pass

logger = logging.getLogger(__name__) # Added logger instance

def parse_load_penetration_curve(g_o: Any,
                                 g_i: Optional[Any] = None, # Optional Input global object
                                 target_phase_name: Optional[str] = None, # If None, try last phase
                                 # For predefined curves:
                                 predefined_curve_name: Optional[str] = None,
                                 curve_x_axis_result_type: Optional[Any] = None,
                                 curve_y_axis_result_type: Optional[Any] = None,
                                 # For step-by-step construction:
                                 spudcan_ref_node_coords: Optional[Tuple[float, float, float]] = None,
                                 # Input object reference (name or actual plx object) for get_equivalent
                                 input_spudcan_ref: Optional[Any] = None,
                                 # Fallback if input_spudcan_ref not provided or get_equivalent fails
                                 spudcan_output_object_name: Optional[str] = None,
                                 step_disp_component_result_type: Optional[Any] = None,
                                 step_load_component_result_type: Optional[Any] = None
                                 ) -> List[Dict[str, float]]:
    """
    Parses the load-penetration curve from PLAXIS output.
    Priority:
    1. Predefined curve using `g_o.getcurveresults`.
    2. Step-by-step from object:
        a. Try finding output object using `g_i.get_equivalent(input_spudcan_ref, g_o)`.
        b. Fallback to `spudcan_output_object_name` if (a) fails or `g_i`/`input_spudcan_ref` not provided.
    3. Step-by-step from node coordinates (STUB).

    Args:
        g_o: The PLAXIS output global object.
        g_i: Optional PLAXIS input global object (for get_equivalent).
        target_phase_name: Name of the calculation phase (default: last phase).
        predefined_curve_name: Name of a predefined curve in PLAXIS Output.
        curve_x_axis_result_type: ResultType for X-axis of predefined curve.
        curve_y_axis_result_type: ResultType for Y-axis of predefined curve.
        spudcan_ref_node_coords: Coordinates (x,y,z) of a reference node.
        input_spudcan_ref: Reference to the spudcan object in the PLAXIS Input model
                           (e.g., name or g_i object like g_i.RigidBodies['Spudcan_RB']).
                           Used with g_i.get_equivalent(input_spudcan_ref, g_o).
        spudcan_output_object_name: Fallback name of the reference object in PLAXIS Output
                                   (e.g., "Spudcan_RB_1" or "RigidBody_1").
        step_disp_component_result_type: ResultType for spudcan's displacement.
        step_load_component_result_type: ResultType for spudcan's load/reaction.
    Returns:
        List of dictionaries, e.g., [{'penetration': p1, 'load': l1}, ...].
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
        ref_object_for_step_results = None
        effective_object_name_for_log = "N/A"

        if not curve_data and (input_spudcan_ref or spudcan_output_object_name) and \
           step_disp_component_result_type and step_load_component_result_type:

            if g_i and input_spudcan_ref and hasattr(g_i, 'get_equivalent'):
                try:
                    logger.info(f"Attempting to find output object via g_i.get_equivalent for input ref: {input_spudcan_ref}")
                    # Note: get_equivalent might return a list if the input object maps to multiple output objects.
                    # Assuming for a spudcan it's usually one primary object.
                    equivalent_output_obj = g_i.get_equivalent(input_spudcan_ref, g_o)
                    if isinstance(equivalent_output_obj, list) and equivalent_output_obj:
                        ref_object_for_step_results = equivalent_output_obj[0] # Take the first one
                        effective_object_name_for_log = getattr(ref_object_for_step_results, "Name", str(ref_object_for_step_results))
                        logger.info(f"Found output object '{effective_object_name_for_log}' using get_equivalent.")
                    elif not isinstance(equivalent_output_obj, list) and equivalent_output_obj:
                         ref_object_for_step_results = equivalent_output_obj
                         effective_object_name_for_log = getattr(ref_object_for_step_results, "Name", str(ref_object_for_step_results))
                         logger.info(f"Found output object '{effective_object_name_for_log}' using get_equivalent.")
                    else:
                        logger.warning(f"g_i.get_equivalent for '{input_spudcan_ref}' returned empty or unexpected result. Will try fallback name.")
                except Exception as e_equiv:
                    logger.warning(f"Error using g_i.get_equivalent for '{input_spudcan_ref}': {e_equiv}. Will try fallback name.", exc_info=True)

            if not ref_object_for_step_results and spudcan_output_object_name:
                effective_object_name_for_log = spudcan_output_object_name
                logger.info(f"Attempting step-by-step curve construction using fallback object name '{spudcan_output_object_name}'.")
                if hasattr(g_o, 'RigidBodies') and spudcan_output_object_name in g_o.RigidBodies:
                    ref_object_for_step_results = g_o.RigidBodies[spudcan_output_object_name]
                elif hasattr(g_o, 'Plates') and spudcan_output_object_name in g_o.Plates:
                    ref_object_for_step_results = g_o.Plates[spudcan_output_object_name]
                # Add other potential collections if necessary (e.g., g_o.Volumes)

            if not ref_object_for_step_results:
                logger.error(f"Spudcan reference object (tried get_equivalent and fallback name '{spudcan_output_object_name}') not found for step-by-step curve construction.")
            else:
                logger.debug(f"Using reference object '{effective_object_name_for_log}' for getresults.")
                try:
                    displacements_all_steps = g_o.getresults(ref_object_for_step_results, target_phase, step_disp_component_result_type, 'step')
                    loads_all_steps = g_o.getresults(ref_object_for_step_results, target_phase, step_load_component_result_type, 'step')

                    if isinstance(displacements_all_steps, (list, tuple)) and isinstance(loads_all_steps, (list, tuple)) and \
                       len(displacements_all_steps) == len(loads_all_steps):
                        for disp_val, load_val in zip(displacements_all_steps, loads_all_steps):
                            pen = abs(float(disp_val)) if isinstance(disp_val, (int, float, str)) else 0.0
                            load = abs(float(load_val)) if isinstance(load_val, (int, float, str)) else 0.0
                            curve_data.append({'penetration': pen, 'load': load})
                        logger.info(f"Constructed curve with {len(curve_data)} points from step results for '{effective_object_name_for_log}'.")
                    else:
                        logger.warning(f"Mismatch in lengths or types of step results for '{effective_object_name_for_log}'. "
                                       f"Disp type: {type(displacements_all_steps)}, Load type: {type(loads_all_steps)}")
                except PlxScriptingError as pse_steps:
                    logger.error(f"PlxScriptingError getting step results for '{effective_object_name_for_log}': {pse_steps}", exc_info=True)
                except Exception as e_steps:
                    logger.error(f"Error getting step results for '{effective_object_name_for_log}': {e_steps}", exc_info=True)

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
                                  g_i: Optional[Any] = None,
                                  input_spudcan_ref: Optional[Any] = None,
                                  spudcan_output_object_name: Optional[str] = None, # Fallback
                                  spudcan_ref_node_coords: Optional[Tuple[float, float, float]] = None,
                                  result_phase_name: Optional[str] = None,
                                  disp_component_result_type: Optional[Any] = None
                                  ) -> Optional[float]:
    """
    Parses the final penetration depth of the spudcan from a specific phase.
    Uses g_i.get_equivalent if possible, otherwise fallback to name or node coords.
    """
    logger.info("Starting final penetration depth parsing.")
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available in parse_final_penetration_depth.")
        return None

    try:
        target_phase = None
        # ... (target phase selection logic remains the same) ...
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
        ref_object_output = None
        effective_object_name_for_log = "N/A"

        if input_spudcan_ref and g_i and hasattr(g_i, 'get_equivalent'):
            try:
                logger.debug(f"Attempting to find output object for final penetration via g_i.get_equivalent for input ref: {input_spudcan_ref}")
                equivalent_output_obj = g_i.get_equivalent(input_spudcan_ref, g_o)
                if isinstance(equivalent_output_obj, list) and equivalent_output_obj:
                    ref_object_output = equivalent_output_obj[0]
                elif not isinstance(equivalent_output_obj, list) and equivalent_output_obj:
                    ref_object_output = equivalent_output_obj
                if ref_object_output:
                    effective_object_name_for_log = getattr(ref_object_output, "Name", str(ref_object_output))
                    logger.info(f"Found output object '{effective_object_name_for_log}' for final penetration using get_equivalent.")
                else:
                    logger.warning(f"get_equivalent for final penetration with '{input_spudcan_ref}' returned empty. Will try fallback name.")
            except Exception as e_equiv:
                logger.warning(f"Error using get_equivalent for final penetration with '{input_spudcan_ref}': {e_equiv}. Will try fallback name.", exc_info=True)

        if not ref_object_output and spudcan_output_object_name:
            effective_object_name_for_log = spudcan_output_object_name
            logger.debug(f"Attempting to get penetration for object '{spudcan_output_object_name}' (fallback).")
            # Assuming RigidBodies is the primary collection to check for spudcans
            if hasattr(g_o, 'RigidBodies') and spudcan_output_object_name in g_o.RigidBodies:
                ref_object_output = g_o.RigidBodies[spudcan_output_object_name]
            # Add other collections if spudcan could be other types, e.g., Plates
            # elif hasattr(g_o, 'Plates') and spudcan_output_object_name in g_o.Plates:
            #    ref_object_output = g_o.Plates[spudcan_output_object_name]

        if ref_object_output and disp_component_result_type:
            all_values = g_o.getresults(ref_object_output, target_phase, disp_component_result_type)
            if isinstance(all_values, (list, tuple)) and all_values:
                penetration_value = float(all_values[-1])
            elif isinstance(all_values, (int, float)):
                penetration_value = float(all_values)
            logger.info(f"Retrieved penetration for object '{effective_object_name_for_log}': {penetration_value}")
        elif spudcan_ref_node_coords and disp_component_result_type: # Fallback to node coords if object method fails or not specified
            logger.debug(f"Attempting to get penetration for node {spudcan_ref_node_coords}.")
            raw_value = g_o.getsingleresult(target_phase, disp_component_result_type, spudcan_ref_node_coords)
            if isinstance(raw_value, (int, float)):
                penetration_value = float(raw_value)
            logger.info(f"Retrieved penetration for node {spudcan_ref_node_coords}: {penetration_value}")
        else:
            if not disp_component_result_type:
                 logger.error("Displacement component result type not provided.")
            else:
                 logger.error("Insufficient information (input_spudcan_ref, spudcan_output_object_name, or node coords) to get final penetration.")
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


# --- Main Compilation Function ---
def compile_analysis_results(
    raw_results_list: List[Any], # List of results from the callables
    project_settings: Optional[Any] = None # Access to ProjectSettings if needed for context
) -> 'AnalysisResults': # Forward reference AnalysisResults if not imported from models
    """
    Compiles the list of raw results (output of result extraction callables)
    into a structured AnalysisResults object.

    The structure of raw_results_list is assumed to correspond to the order
    of callables generated by get_standard_results_commands.
    """
    from ..models import AnalysisResults # Local import to avoid circularity if this file grows

    compiled = AnalysisResults()
    logger.info("Compiling raw analysis results into AnalysisResults object.")

    # Assuming a specific order based on get_standard_results_commands:
    # 1. Load-penetration curve data
    # 2. Final penetration depth
    # 3. Peak vertical resistance (calculated from curve data)
    # (Add more as get_standard_results_commands evolves)

    if len(raw_results_list) > 0 and isinstance(raw_results_list[0], list):
        compiled.load_penetration_curve_data = raw_results_list[0]
        logger.debug(f"  Assigned load_penetration_curve_data with {len(compiled.load_penetration_curve_data)} points.")
        # Calculate peak resistance from this curve data
        compiled.peak_vertical_resistance = parse_peak_vertical_resistance(compiled.load_penetration_curve_data)
        logger.debug(f"  Calculated peak_vertical_resistance: {compiled.peak_vertical_resistance}")
    else:
        logger.warning("  Could not assign load_penetration_curve_data from raw results (index 0).")

    if len(raw_results_list) > 1 and isinstance(raw_results_list[1], (float, int)):
        compiled.final_penetration_depth = float(raw_results_list[1])
        logger.debug(f"  Assigned final_penetration_depth: {compiled.final_penetration_depth}")
    elif len(raw_results_list) > 1 and raw_results_list[1] is None:
        logger.warning("  Final penetration depth from raw results (index 1) is None.")
    elif len(raw_results_list) <=1:
        logger.warning("  Not enough data in raw_results_list to get final_penetration_depth (index 1).")

    # Example for future:
    # if len(raw_results_list) > 2 and isinstance(raw_results_list[2], dict):
    #     compiled.soil_displacements_at_points = raw_results_list[2] # Assuming this structure

    logger.info(f"Finished compiling results. Final object: {compiled}")
    return compiled


def get_standard_results_commands(project_settings: Any) -> List[Callable[[Any, Optional[Any]], Any]]:
    """
    Returns a list of callables, each designed to extract a specific piece of
    result information from the PLAXIS output (g_o), potentially using g_i for context.
    The order of callables here MUST match the expected order in compile_analysis_results.
    """
    from ..models import ProjectSettings as ConcreteProjectSettings # For type hinting
    ps: ConcreteProjectSettings = project_settings

    callables: List[Callable[[Any], Any]] = []
    logger.info("Generating standard results extraction commands.")

    # --- Default values for ResultTypes ---
    # These should ideally be accessible globally or via a config if they are standard.
    # For now, defined locally. These are examples and might need adjustment based on PLAXIS version/setup.
    # It's safer if these ResultType objects are obtained directly from a connected g_o instance
    # before these callables are created, but that makes the callable generation stateful.
    # Passing string representations and resolving them inside the callable is another option.

    # For predefined curve (assumes a curve named "SpudcanPath" exists)
    # Example ResultTypes for predefined curve, these need to be correct for user's PLAXIS setup or passed in.
    # curve_x_type_placeholder = "g_o.ResultTypes.SumMstage" # Placeholder, replace with actual object if possible
    # curve_y_type_placeholder = "g_o.ResultTypes.SumFstage_Z"

    # For step-by-step RigidBody results (assuming spudcan is a RigidBody)
    # These are more robust if the actual ResultType objects are used.
    # For now, we pass None and the parser will try to use defaults or handle it.
    # A better approach: The PlaxisInteractor could fetch these ResultType objects once connected
    # and pass them to the parser functions or to this command generator.

    # Placeholder values for spudcan object name and node coordinates
    # These should be derived from how the geometry was created.
    # For now, using common defaults.
    spudcan_object_name_from_geom = "Spudcan" # This should match the name used in geometry_builder
    # spudcan_tip_node_coords = (0,0, -ps.spudcan.height_cone_angle) # Example, if height_cone_angle is height

    # 1. Load-Penetration Curve
    #    Prioritize predefined curve if its name is known and configured.
    #    Fallback to step-by-step from RigidBody if spudcan_object_name_from_geom is known.
    #    The `parse_load_penetration_curve` handles this logic.
    #    We need to pass the *actual* ResultType objects for reliability.
    #    This is a challenge as g_o is not available when defining these callables.
    #    Workaround: pass string identifiers or make parser more intelligent.
    #    For now, we rely on the parser's internal defaults or ability to find ResultTypes if None is passed.

    # It's better if the specific ResultType instances are fetched from g_o when available
    # and then used to create these lambdas. For now, the parser tries to handle None.

    # Simplified: Assume the parser has access to g_o.ResultTypes or common defaults.
    # The ProjectSettings should ideally carry information about the PLAXIS model elements
    # (e.g. name of the spudcan rigid body, name of predefined curve if used).

    # --- Define a helper to get input spudcan reference (conceptual) ---
    # This would ideally fetch the actual g_i object reference if available and configured.
    # For now, we'll assume it might come from project_settings or be a known name.
    # Example: input_spudcan_object_ref = ps.spudcan.plaxis_input_object_reference # If such a field existed
    # Or, if geometry_builder always names it "Spudcan_ConeVolume" and it becomes a RigidBody named "Spudcan"
    input_spudcan_ref_for_get_equivalent = "Spudcan" # Placeholder for the name/ref in Input
    # Fallback name in Output if get_equivalent is not used or fails
    output_spudcan_name_fallback = "Spudcan" # This might need to be more specific, e.g. "RigidBody_1" if auto-named

    def get_lp_curve(g_o: Any, g_i: Optional[Any]) -> List[Dict[str, float]]:
        # Try to get common ResultTypes dynamically if available
        step_disp_type = getattr(getattr(g_o.ResultTypes, "RigidBody", None), "Uy", None) # Common for vertical
        step_load_type = getattr(getattr(g_o.ResultTypes, "RigidBody", None), "Fz", None)

        # TODO: predefined_curve_name, curve_x_type, curve_y_type could be from ps.analysis_control
        # predefined_curve_name = getattr(ps.analysis_control, "output_curve_name", None)

        return parse_load_penetration_curve(
            g_o=g_o,
            g_i=g_i,
            target_phase_name=None, # Default to last phase
            predefined_curve_name=None, # Placeholder
            curve_x_axis_result_type=None, # Placeholder
            curve_y_axis_result_type=None, # Placeholder
            input_spudcan_ref=input_spudcan_ref_for_get_equivalent,
            spudcan_output_object_name=output_spudcan_name_fallback,
            step_disp_component_result_type=step_disp_type,
            step_load_component_result_type=step_load_type
        )
    callables.append(get_lp_curve)

    # 2. Final Penetration Depth
    def get_final_pen(g_o: Any, g_i: Optional[Any]) -> Optional[float]:
        disp_comp_type = getattr(getattr(g_o.ResultTypes, "RigidBody", None), "Uy", None)
        return parse_final_penetration_depth(
            g_o=g_o,
            g_i=g_i,
            input_spudcan_ref=input_spudcan_ref_for_get_equivalent,
            spudcan_output_object_name=output_spudcan_name_fallback,
            result_phase_name=None, # Default to last phase
            disp_component_result_type=disp_comp_type
        )
    callables.append(get_final_pen)

    # Peak resistance is calculated by compile_analysis_results from curve data, so no callable here for it.

    # Add more callables for other standard results if needed, e.g.:
    # callables.append(lambda g_o_param: parse_soil_displacements(g_o_param, ...))
    # callables.append(lambda g_o_param: parse_structural_forces(g_o_param, ...))

    logger.info(f"Generated {len(callables)} standard results extraction commands.")
    return callables
