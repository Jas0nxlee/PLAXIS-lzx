"""
Module for parsing output files or data from PLAXIS.
Handles the transformation of raw PLAXIS output (obtained via scripting API)
into structured AnalysisResults objects.

PRD Ref: Task 3.8
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable

from ..models import AnalysisResults, ProjectSettings # For type hinting
from ..exceptions import PlaxisOutputError # For reporting issues during parsing

# Placeholder for PlxScriptingError if plxscripting is not available
try:
    from plxscripting.plx_scripting_exceptions import PlxScriptingError
except ImportError:
    class PlxScriptingError(Exception): # type: ignore
        """Placeholder for PlxScriptingError if plxscripting is not available."""
        pass

logger = logging.getLogger(__name__)

def parse_load_penetration_curve(
    g_o: Any,
    g_i: Optional[Any] = None,
    target_phase_name: Optional[str] = None,
    predefined_curve_name: Optional[str] = None,
    curve_x_axis_result_type: Optional[Any] = None,
    curve_y_axis_result_type: Optional[Any] = None,
    input_spudcan_ref: Optional[Any] = None,
    spudcan_output_object_name: Optional[str] = None,
    step_disp_component_result_type: Optional[Any] = None,
    step_load_component_result_type: Optional[Any] = None,
    # spudcan_ref_node_coords is removed as it was a STUB and not used.
) -> List[Dict[str, float]]:
    """
    Parses the load-penetration curve from PLAXIS output.

    Attempts to retrieve curve data using either a predefined curve in PLAXIS
    or by step-by-step results from a specified spudcan object. Handles potential
    errors during API calls and data conversion.

    Args:
        g_o: The PLAXIS output global object.
        g_i: Optional PLAXIS input global object (for get_equivalent).
        target_phase_name: Name of the calculation phase (defaults to the last phase).
        predefined_curve_name: Name of a predefined curve in PLAXIS Output.
        curve_x_axis_result_type: ResultType for X-axis of the predefined curve.
        curve_y_axis_result_type: ResultType for Y-axis of the predefined curve.
        input_spudcan_ref: Reference to the spudcan object in the PLAXIS Input model
                           (e.g., name or g_i object). Used with g_i.get_equivalent.
        spudcan_output_object_name: Fallback name of the reference object in PLAXIS Output
                                   if `input_spudcan_ref` or `get_equivalent` fails.
        step_disp_component_result_type: ResultType for spudcan's displacement (e.g., g_o.ResultTypes.RigidBody.Uy).
        step_load_component_result_type: ResultType for spudcan's load/reaction (e.g., g_o.ResultTypes.RigidBody.Fz).

    Returns:
        A list of dictionaries, where each dictionary is {'penetration': float, 'load': float}.
        Returns an empty list if data cannot be parsed or an error occurs.
    """
    logger.info("Starting load-penetration curve parsing.")
    curve_data: List[Dict[str, float]] = []
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available in parse_load_penetration_curve.")
        return curve_data

    try:
        target_phase = None
        if not target_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            logger.info(f"Target phase not specified for curve, using last phase: {phase_id_val}")
        elif target_phase_name and hasattr(g_o, 'Phases'):
            for phase_obj in g_o.Phases: # Renamed phase to phase_obj to avoid conflict
                phase_id_val = getattr(getattr(phase_obj, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase_obj, "Name", None), "value", None)
                if phase_name_val == target_phase_name or phase_id_val == target_phase_name:
                    target_phase = phase_obj
                    logger.debug(f"Found target phase for curve by name/ID: {target_phase_name}")
                    break
        if not target_phase:
            logger.error(f"Target phase '{target_phase_name or 'Last Phase'}' for curve not found or no phases available.")
            return curve_data

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        logger.info(f"Parsing load-penetration curve for phase: {phase_id_val_found}")

        # Option 1: Predefined curve
        if predefined_curve_name and curve_x_axis_result_type and curve_y_axis_result_type:
            logger.info(f"Attempting to extract predefined curve '{predefined_curve_name}'.")
            # ... (rest of predefined curve logic, unchanged)
            if hasattr(g_o, 'Curves') and predefined_curve_name in g_o.Curves:
                plaxis_curve_object = g_o.Curves[predefined_curve_name]
                logger.debug(f"Found predefined curve object '{predefined_curve_name}'. Using getcurveresults.")
                try:
                    x_results, y_results = g_o.getcurveresults(plaxis_curve_object, target_phase,
                                                             curve_x_axis_result_type,
                                                             curve_y_axis_result_type)
                    if isinstance(x_results, (list, tuple)) and isinstance(y_results, (list, tuple)) and len(x_results) == len(y_results):
                        for x_val, y_val in zip(x_results, y_results):
                            try:
                                pen = abs(float(x_val))
                                load = abs(float(y_val))
                                curve_data.append({'penetration': pen, 'load': load})
                            except (ValueError, TypeError) as val_err:
                                logger.warning(f"Could not convert curve point values to float: x='{x_val}', y='{y_val}'. Error: {val_err}")
                        logger.info(f"Extracted {len(curve_data)} points from predefined curve '{predefined_curve_name}'.")
                    else:
                        logger.warning(f"Mismatch in lengths or types from getcurveresults for '{predefined_curve_name}'. X type: {type(x_results)}, Y type: {type(y_results)}")
                except PlxScriptingError as pse_curve:
                    logger.error(f"PlxScriptingError getting predefined curve results for '{predefined_curve_name}': {pse_curve}", exc_info=True)
                except Exception as e_curve:
                    logger.error(f"Error getting predefined curve results for '{predefined_curve_name}': {e_curve}", exc_info=True)
            else:
                logger.warning(f"Predefined curve '{predefined_curve_name}' not found in g_o.Curves or axis ResultTypes not provided.")


        # Option 2: Step-by-step from object results
        if not curve_data and (input_spudcan_ref or spudcan_output_object_name) and \
           step_disp_component_result_type and step_load_component_result_type:
            logger.info("Attempting step-by-step curve construction from object results.")
            # ... (rest of step-by-step logic, unchanged but ensure logging clarity)
            ref_object_for_step_results = None
            effective_object_name_for_log = "N/A"

            if g_i and input_spudcan_ref and hasattr(g_i, 'get_equivalent'):
                try:
                    logger.info(f"Attempting to find output object via g_i.get_equivalent for input ref: {input_spudcan_ref}")
                    equivalent_output_obj = g_i.get_equivalent(input_spudcan_ref, g_o)
                    if isinstance(equivalent_output_obj, list) and equivalent_output_obj:
                        ref_object_for_step_results = equivalent_output_obj[0]
                    elif not isinstance(equivalent_output_obj, list) and equivalent_output_obj:
                         ref_object_for_step_results = equivalent_output_obj
                    if ref_object_for_step_results:
                        effective_object_name_for_log = getattr(ref_object_for_step_results, "Name", str(ref_object_for_step_results))
                        logger.info(f"Found output object '{effective_object_name_for_log}' using get_equivalent.")
                    else:
                        logger.warning(f"g_i.get_equivalent for '{input_spudcan_ref}' returned empty. Trying fallback name.")
                except Exception as e_equiv:
                    logger.warning(f"Error using g_i.get_equivalent for '{input_spudcan_ref}': {e_equiv}. Trying fallback name.", exc_info=True)

            if not ref_object_for_step_results and spudcan_output_object_name:
                effective_object_name_for_log = spudcan_output_object_name
                logger.info(f"Using fallback object name '{spudcan_output_object_name}' for step-by-step curve.")
                # Common collections where a spudcan might be found
                for collection_name in ['RigidBodies', 'Plates', 'PointLoads', 'PointDisplacements']: # Add more if needed
                    if hasattr(g_o, collection_name):
                        collection = getattr(g_o, collection_name)
                        if spudcan_output_object_name in collection:
                            ref_object_for_step_results = collection[spudcan_output_object_name]
                            logger.debug(f"Found '{spudcan_output_object_name}' in g_o.{collection_name}")
                            break

            if not ref_object_for_step_results:
                logger.error(f"Spudcan reference object for step-by-step curve not found (tried get_equivalent and fallback name '{spudcan_output_object_name}').")
            else:
                logger.debug(f"Using reference object '{effective_object_name_for_log}' for getresults (step-by-step curve).")
                try:
                    displacements_all_steps = g_o.getresults(ref_object_for_step_results, target_phase, step_disp_component_result_type, 'step')
                    loads_all_steps = g_o.getresults(ref_object_for_step_results, target_phase, step_load_component_result_type, 'step')

                    if isinstance(displacements_all_steps, (list, tuple)) and isinstance(loads_all_steps, (list, tuple)) and \
                       len(displacements_all_steps) == len(loads_all_steps):
                        for disp_val, load_val in zip(displacements_all_steps, loads_all_steps):
                            try:
                                pen = abs(float(disp_val))
                                load = abs(float(load_val))
                                curve_data.append({'penetration': pen, 'load': load})
                            except (ValueError, TypeError) as val_err:
                                logger.warning(f"Could not convert step result values to float: disp='{disp_val}', load='{load_val}'. Error: {val_err}")
                        logger.info(f"Constructed curve with {len(curve_data)} points from step results for '{effective_object_name_for_log}'.")
                    else:
                        logger.warning(f"Mismatch in lengths or types of step results for '{effective_object_name_for_log}'. "
                                       f"Disp type: {type(displacements_all_steps)}, Load type: {type(loads_all_steps)}")
                except PlxScriptingError as pse_steps:
                    logger.error(f"PlxScriptingError getting step results for '{effective_object_name_for_log}': {pse_steps}", exc_info=True)
                except Exception as e_steps:
                    logger.error(f"Error getting step results for '{effective_object_name_for_log}': {e_steps}", exc_info=True)

        if not curve_data:
            logger.warning("Load-penetration curve data remains empty after all parsing attempts.")

    except PlxScriptingError as pse:
        logger.error(f"PLAXIS API PlxScriptingError during load-penetration curve parsing: {pse}", exc_info=True)
    except AttributeError as ae: # Catch issues like g_o.Phases not existing
        logger.error(f"PLAXIS API attribute error (e.g., missing expected objects like Phases, Curves, ResultTypes): {ae}.", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred during load-penetration curve parsing: {e}", exc_info=True)

    logger.info(f"Finished load-penetration curve parsing. {len(curve_data)} points generated.")
    return curve_data


def parse_final_penetration_depth(
    g_o: Any,
    g_i: Optional[Any] = None,
    input_spudcan_ref: Optional[Any] = None,
    spudcan_output_object_name: Optional[str] = None,
    result_phase_name: Optional[str] = None,
    disp_component_result_type: Optional[Any] = None
) -> Optional[float]:
    """
    Parses the final penetration depth of the spudcan from a specific phase.

    Args:
        g_o: The PLAXIS output global object.
        g_i: Optional PLAXIS input global object (for get_equivalent).
        input_spudcan_ref: Reference to spudcan object in PLAXIS Input for get_equivalent.
        spudcan_output_object_name: Fallback name of spudcan object in PLAXIS Output.
        result_phase_name: Name of the phase from which to get the result (defaults to last phase).
        disp_component_result_type: ResultType for spudcan's displacement (e.g., g_o.ResultTypes.RigidBody.Uy).

    Returns:
        The absolute final penetration depth as a float, or None if not found/error.
    """
    logger.info("Starting final penetration depth parsing.")
    if not g_o:
        logger.error("PLAXIS output object (g_o) not available for final penetration depth parsing.")
        return None
    if not disp_component_result_type:
        logger.error("Displacement component result type (disp_component_result_type) not provided for final penetration.")
        return None

    try:
        target_phase = None
        if not result_phase_name and hasattr(g_o, 'Phases') and g_o.Phases:
            target_phase = g_o.Phases[-1]
            phase_id_val = getattr(getattr(target_phase, "Identification", None), "value", "N/A")
            logger.info(f"Result phase for final penetration not specified, using last phase: {phase_id_val}")
        elif result_phase_name and hasattr(g_o, 'Phases'):
            for phase_obj in g_o.Phases:
                phase_id_val = getattr(getattr(phase_obj, "Identification", None), "value", None)
                phase_name_val = getattr(getattr(phase_obj, "Name", None), "value", None)
                if phase_name_val == result_phase_name or phase_id_val == result_phase_name:
                    target_phase = phase_obj
                    logger.debug(f"Found target phase for final penetration: {result_phase_name}")
                    break
        if not target_phase:
            logger.error(f"Target phase '{result_phase_name or 'Last Phase'}' for final penetration not found.")
            return None

        phase_id_val_found = getattr(getattr(target_phase, "Identification", None), "value", "UnknownPhase")
        logger.info(f"Parsing final penetration depth for phase: {phase_id_val_found}")

        penetration_value: Optional[float] = None
        ref_object_output = None
        effective_object_name_for_log = "N/A"

        # Try to get output object via get_equivalent first
        if input_spudcan_ref and g_i and hasattr(g_i, 'get_equivalent'):
            try:
                logger.debug(f"Attempting to find output object for final penetration via g_i.get_equivalent for input ref: {input_spudcan_ref}")
                equivalent_output_obj = g_i.get_equivalent(input_spudcan_ref, g_o)
                if isinstance(equivalent_output_obj, list) and equivalent_output_obj: ref_object_output = equivalent_output_obj[0]
                elif not isinstance(equivalent_output_obj, list) and equivalent_output_obj: ref_object_output = equivalent_output_obj

                if ref_object_output:
                    effective_object_name_for_log = getattr(ref_object_output, "Name", str(ref_object_output))
                    logger.info(f"Found output object '{effective_object_name_for_log}' for final penetration using get_equivalent.")
                else: logger.warning(f"get_equivalent for '{input_spudcan_ref}' returned empty. Will try fallback name.")
            except Exception as e_equiv:
                logger.warning(f"Error using get_equivalent for '{input_spudcan_ref}': {e_equiv}. Will try fallback name.", exc_info=True)

        # Fallback to spudcan_output_object_name if get_equivalent failed or wasn't used
        if not ref_object_output and spudcan_output_object_name:
            effective_object_name_for_log = spudcan_output_object_name
            logger.debug(f"Attempting to get penetration for object '{spudcan_output_object_name}' (fallback).")
            # Check common collections where spudcan might be represented
            for collection_name in ['RigidBodies', 'Plates', 'PointDisplacements']: # PointDisplacements if it's a prescribed displacement point
                if hasattr(g_o, collection_name):
                    collection = getattr(g_o, collection_name)
                    if spudcan_output_object_name in collection:
                        ref_object_output = collection[spudcan_output_object_name]
                        logger.debug(f"Found '{spudcan_output_object_name}' in g_o.{collection_name}")
                        break

        if ref_object_output:
            all_values = g_o.getresults(ref_object_output, target_phase, disp_component_result_type) # Get final value for object
            if isinstance(all_values, (list, tuple)) and all_values: penetration_value = float(all_values[-1])
            elif isinstance(all_values, (int, float)): penetration_value = float(all_values)
            logger.info(f"Retrieved final penetration for object '{effective_object_name_for_log}': {penetration_value}")
        else:
            logger.error(f"Spudcan reference object not found (tried get_equivalent for '{input_spudcan_ref}' and fallback name '{spudcan_output_object_name}'). Cannot get final penetration.")
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
    Determines the peak absolute vertical resistance from load-penetration curve data.
    """
    logger.info("Parsing peak vertical resistance from curve data.")
    if not load_penetration_data:
        logger.warning("Load-penetration data is empty, cannot determine peak resistance.")
        return None

    peak_abs_load: Optional[float] = None
    try:
        for point in load_penetration_data:
            if not isinstance(point, dict):
                logger.warning(f"Skipping non-dict item in load_penetration_data: {point}")
                continue
            load_val = point.get('load')
            if isinstance(load_val, (int, float)):
                current_abs_load = abs(load_val)
                if peak_abs_load is None or current_abs_load > peak_abs_load:
                    peak_abs_load = current_abs_load
            else:
                logger.debug(f"Non-numeric or missing 'load' value in point: {point}")

        if peak_abs_load is not None:
            logger.info(f"Peak vertical resistance determined: {peak_abs_load}")
        else:
            logger.warning("No valid 'load' values found in load-penetration data to determine peak.")
        return peak_abs_load
    except Exception as e:
        logger.error(f"Error parsing peak resistance from data: {e}", exc_info=True)
        return None

# --- `parse_soil_displacements` and `parse_structural_forces` remain unchanged for now ---
# (They are not part of the "standard results" currently compiled)
def parse_soil_displacements(g_o: Any,
                             points_of_interest: List[Tuple[float, float, float]],
                             result_phase_name: Optional[str] = None
                             ) -> Dict[Tuple[float, float, float], Dict[str, Optional[float]]]:
    logger.info(f"Starting soil displacement parsing for {len(points_of_interest)} points.")
    displacements_data: Dict[Tuple[float, float, float], Dict[str, Optional[float]]] = {}
    # ... (implementation as before)
    return displacements_data

def parse_structural_forces(g_o: Any,
                            structure_name: str,
                            structure_type: str,
                            result_phase_name: Optional[str] = None,
                            desired_results: Optional[List[str]] = None
                            ) -> Optional[Dict[str, Any]]:
    logger.info(f"Starting structural forces parsing for {structure_type} '{structure_name}'.")
    # ... (implementation as before)
    return None


# --- Main Compilation Function ---
def compile_analysis_results(
    raw_results_list: List[Any],
    project_settings: Optional[ProjectSettings] = None # Type hinted ProjectSettings
) -> AnalysisResults:
    """
    Compiles a list of raw results from PLAXIS into a structured AnalysisResults object.

    The order and type of items in `raw_results_list` are expected to match the
    callables generated by `get_standard_results_commands`.

    Args:
        raw_results_list: List of results data pieces. Expected order:
                          0: Load-penetration curve data (List[Dict[str, float]])
                          1: Final penetration depth (float)
        project_settings: Optional project settings for context (currently unused here).

    Returns:
        An AnalysisResults object populated with the compiled data.
    """
    # Local import to avoid potential circular dependencies if models.py imports this module.
    # However, it's better if AnalysisResults is directly imported if no circularity.
    # from ..models import AnalysisResults # Already imported at top level

    compiled = AnalysisResults()
    logger.info(f"Compiling {len(raw_results_list)} raw analysis result pieces into AnalysisResults object.")

    # 1. Load-penetration curve data
    if len(raw_results_list) > 0:
        curve_data_raw = raw_results_list[0]
        if isinstance(curve_data_raw, list):
            # Further check if all items are dicts with expected keys (optional, can be strict)
            if all(isinstance(item, dict) and 'penetration' in item and 'load' in item for item in curve_data_raw):
                compiled.load_penetration_curve_data = curve_data_raw
                logger.debug(f"  Assigned load_penetration_curve_data with {len(compiled.load_penetration_curve_data)} points.")
                # Calculate peak resistance from this curve data
                compiled.peak_vertical_resistance = parse_peak_vertical_resistance(compiled.load_penetration_curve_data)
                logger.debug(f"  Calculated peak_vertical_resistance: {compiled.peak_vertical_resistance}")
            else:
                logger.warning("  Raw result for curve data (index 0) is a list, but items are not all valid dicts with 'penetration' and 'load'.")
        elif isinstance(curve_data_raw, Exception): # If the parser callable returned an error
            logger.error(f"  Error extracting load-penetration curve data: {curve_data_raw}")
        else:
            logger.warning(f"  Unexpected type for load_penetration_curve_data (index 0): {type(curve_data_raw)}. Expected list.")
    else:
        logger.warning("  Raw results list is empty. Cannot extract load-penetration curve data.")

    # 2. Final penetration depth
    if len(raw_results_list) > 1:
        final_pen_raw = raw_results_list[1]
        if isinstance(final_pen_raw, (float, int)):
            compiled.final_penetration_depth = float(final_pen_raw)
            logger.debug(f"  Assigned final_penetration_depth: {compiled.final_penetration_depth}")
        elif final_pen_raw is None:
            logger.info("  Final penetration depth from raw results (index 1) is None.")
        elif isinstance(final_pen_raw, Exception):
            logger.error(f"  Error extracting final penetration depth: {final_pen_raw}")
        else:
            logger.warning(f"  Unexpected type for final_penetration_depth (index 1): {type(final_pen_raw)}. Expected float, int, or None.")
    elif len(raw_results_list) == 1 : # Only curve data was present
        logger.warning("  Not enough data in raw_results_list to get final_penetration_depth (index 1 missing).")
    # If raw_results_list is empty, already logged above.


    logger.info(f"Finished compiling results. Final AnalysisResults object: {compiled}")
    return compiled


def get_standard_results_commands(project_settings: ProjectSettings) -> List[Callable[[Any, Optional[Any]], Any]]:
    """
    Returns an ordered list of callables for extracting standard analysis results.

    Each callable takes `g_o` (PLAXIS output global object) and an optional `g_i`
    (PLAXIS input global object) as arguments. The order of callables in the returned
    list is critical and must match the expectations of `compile_analysis_results`.

    Args:
        project_settings: The current project settings, which might contain information
                          to guide result extraction (e.g., object names).

    Returns:
        A list of callables for result extraction.
    """
    # from ..models import ProjectSettings as ConcreteProjectSettings # Already imported at top level
    ps: ProjectSettings = project_settings # Use type hint for clarity

    callables: List[Callable[[Any, Optional[Any]], Any]] = [] # Ensure type hint for list elements
    logger.info("Generating standard results extraction commands.")

    # --- Determine Spudcan Object References ---
    # These names/references should ideally be determined or stored during geometry creation.
    # Using placeholders or common defaults for now.
    input_spudcan_ref_for_get_equivalent = getattr(ps.spudcan, 'plaxis_input_name', "Spudcan") # Example: if SpudcanGeometry model had this
    output_spudcan_name_fallback = getattr(ps.spudcan, 'plaxis_output_name', "Spudcan")     # Example

    # 1. Load-Penetration Curve
    def get_lp_curve(g_o_param: Any, g_i_param: Optional[Any]) -> List[Dict[str, float]]:
        logger.debug("Callable: get_lp_curve executing.")
        # Dynamically try to get common ResultType objects from g_o if available
        step_disp_type = None
        step_load_type = None
        if hasattr(g_o_param, 'ResultTypes') and hasattr(g_o_param.ResultTypes, 'RigidBody'):
            step_disp_type = getattr(g_o_param.ResultTypes.RigidBody, "Uy", None)
            step_load_type = getattr(g_o_param.ResultTypes.RigidBody, "Fz", None)
            if not step_disp_type: logger.warning("Could not find g_o.ResultTypes.RigidBody.Uy for LP curve.")
            if not step_load_type: logger.warning("Could not find g_o.ResultTypes.RigidBody.Fz for LP curve.")
        else:
            logger.warning("g_o.ResultTypes.RigidBody not found. Cannot determine step result types for LP curve dynamically.")

        # TODO: Consider if predefined_curve_name, curve_x_type, curve_y_type should come from project_settings
        # predefined_curve_name = getattr(ps.analysis_control, "output_curve_name", None)

        return parse_load_penetration_curve(
            g_o=g_o_param,
            g_i=g_i_param,
            target_phase_name=None,
            predefined_curve_name=None,
            curve_x_axis_result_type=None,
            curve_y_axis_result_type=None,
            input_spudcan_ref=input_spudcan_ref_for_get_equivalent,
            spudcan_output_object_name=output_spudcan_name_fallback,
            step_disp_component_result_type=step_disp_type,
            step_load_component_result_type=step_load_type
        )
    callables.append(get_lp_curve)

    # 2. Final Penetration Depth
    def get_final_pen(g_o_param: Any, g_i_param: Optional[Any]) -> Optional[float]:
        logger.debug("Callable: get_final_pen executing.")
        disp_comp_type = None
        if hasattr(g_o_param, 'ResultTypes') and hasattr(g_o_param.ResultTypes, 'RigidBody'):
            disp_comp_type = getattr(g_o_param.ResultTypes.RigidBody, "Uy", None)
            if not disp_comp_type: logger.warning("Could not find g_o.ResultTypes.RigidBody.Uy for final penetration.")
        else:
            logger.warning("g_o.ResultTypes.RigidBody not found. Cannot determine displacement result type for final penetration.")

        return parse_final_penetration_depth(
            g_o=g_o_param,
            g_i=g_i_param,
            input_spudcan_ref=input_spudcan_ref_for_get_equivalent,
            spudcan_output_object_name=output_spudcan_name_fallback,
            result_phase_name=None,
            disp_component_result_type=disp_comp_type
        )
    callables.append(get_final_pen)

    logger.info(f"Generated {len(callables)} standard results extraction commands.")
    return callables


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Testing results_parser (stub mode with logging) ---")

    logger.info("\nTesting parse_peak_vertical_resistance...")
    # ... (rest of __main__ block unchanged) ...
    test_curve_data = [
        {'penetration': 0.0, 'load': 0.0}, {'penetration': 0.1, 'load': 100.0},
        {'penetration': 0.2, 'load': 250.0}, {'penetration': 0.3, 'load': 200.0},
        {'penetration': 0.25, 'load': -300.0}, # Negative load, abs should be taken
        {'penetration': 0.4, 'load': None}, # Missing load
        {'penetration': 0.5} # Missing load key
    ]
    peak = parse_peak_vertical_resistance(test_curve_data)
    logger.info(f"Peak resistance from test_curve_data: {peak} (Expected: 300.0)")
    assert peak == 300.0

    peak_empty = parse_peak_vertical_resistance([])
    logger.info(f"Peak resistance from empty curve: {peak_empty} (Expected: None)")
    assert peak_empty is None

    peak_invalid_format = parse_peak_vertical_resistance([{'p':1, 'l':100}]) # type: ignore
    logger.info(f"Peak resistance from invalid format curve: {peak_invalid_format} (Expected: None)")
    assert peak_invalid_format is None

    peak_non_numeric = parse_peak_vertical_resistance([{'penetration': 0.1, 'load': 'error'}]) # type: ignore
    logger.info(f"Peak resistance from non-numeric load: {peak_non_numeric} (Expected: None)")
    assert peak_non_numeric is None

    logger.info("\nTesting compile_analysis_results...")
    # Simulate raw_results_list
    mock_raw_results_good = [
        [{'penetration': 0.1, 'load': 100.0}, {'penetration': 0.2, 'load': 150.0}], # Curve data
        0.2  # Final penetration
    ]
    compiled_good = compile_analysis_results(mock_raw_results_good)
    logger.info(f"Compiled (good): {compiled_good}")
    assert compiled_good.final_penetration_depth == 0.2
    assert compiled_good.peak_vertical_resistance == 150.0
    assert len(compiled_good.load_penetration_curve_data) == 2 # type: ignore

    mock_raw_results_bad_type = [
        "not a list", # Bad curve data
        "not a float"  # Bad penetration
    ]
    compiled_bad_type = compile_analysis_results(mock_raw_results_bad_type)
    logger.info(f"Compiled (bad types): {compiled_bad_type}")
    assert compiled_bad_type.load_penetration_curve_data is None
    assert compiled_bad_type.peak_vertical_resistance is None
    assert compiled_bad_type.final_penetration_depth is None

    mock_raw_results_errors = [
        PlaxisOutputError("Curve extraction failed"),
        PlaxisOutputError("Penetration extraction failed")
    ]
    compiled_errors = compile_analysis_results(mock_raw_results_errors)
    logger.info(f"Compiled (errors): {compiled_errors}")
    assert compiled_errors.load_penetration_curve_data is None
    assert compiled_errors.peak_vertical_resistance is None
    assert compiled_errors.final_penetration_depth is None


    logger.info("\n--- End of results_parser tests ---")
