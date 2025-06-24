"""
Generates PLAXIS API callables for defining loading conditions,
analysis control (meshing, phases), and output requests.
PRD Ref: Tasks 3.4 (Loading Conditions), 3.5 (Analysis Control), 3.6 (Output Request)

This module translates data models (`LoadingConditions`, `AnalysisControlParameters`)
into sequences of Python functions (callables). Each callable, when executed
with a PLAXIS input global object (g_i), performs API actions to define
loads, control meshing, set up calculation phases, and potentially configure
output requests within the PLAXIS model.
"""

import logging
from ..models import LoadingConditions, AnalysisControlParameters
from ..exceptions import PlaxisConfigurationError # Import custom exception
from typing import List, Callable, Any, Optional, Tuple # Added Tuple

logger = logging.getLogger(__name__)

# --- Loading Conditions ---

def generate_loading_condition_callables(
    loading_model: LoadingConditions,
    spudcan_ref_point: Tuple[float, float, float] = (0,0,0)
) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for defining loading conditions.
    (Args and Returns are per original spec, assumptions also largely hold)
    Raises:
        PlaxisConfigurationError: If loading_model contains invalid parameters (e.g., negative preload if not allowed by convention).
                                 Currently, this function doesn't perform extensive validation beyond type checks implied by model.
    """
    callables: List[Callable[[Any], None]] = []
    logger.info(f"Preparing loading condition callables: Preload={loading_model.vertical_preload}, "
                f"Target={loading_model.target_penetration_or_load} ({loading_model.target_type}) "
                f"at reference point {spudcan_ref_point}")

    load_application_point = spudcan_ref_point

    # Validate preload if provided (example validation)
    if loading_model.vertical_preload is not None and loading_model.vertical_preload < 0:
        # Depending on convention, negative preload might be disallowed or mean upward.
        # Assuming for this example that preload should be non-negative magnitude.
        # logger.warning(f"Vertical preload {loading_model.vertical_preload} is negative. Assuming magnitude.")
        pass # For now, allow negative, abs() is used later. Stricter validation could raise here.

    if loading_model.vertical_preload is not None and loading_model.vertical_preload != 0:
        preload_value_fz = -abs(loading_model.vertical_preload) # Convention: negative Z is downward force
        preload_name = "Spudcan_Preload"

        def define_preload_callable(g_i: Any) -> None:
            logger.info(f"  API CALL: Defining PointLoad '{preload_name}' at {load_application_point} with Fz={preload_value_fz}")
            try:
                g_i.pointload(load_application_point, Name=preload_name, Fz=preload_value_fz)
                logger.debug(f"    PointLoad '{preload_name}' defined.")
            except Exception as e: # Catch PlxScriptingError or other
                logger.error(f"    ERROR defining PointLoad '{preload_name}': {e}", exc_info=True)
                raise # Re-raise to be mapped by PlaxisInteractor
        callables.append(define_preload_callable)

    # Validate target penetration/load
    if loading_model.target_type == "penetration":
        if loading_model.target_penetration_or_load is not None and loading_model.target_penetration_or_load < 0:
            # Similar to preload, decide on convention for negative penetration.
            # logger.warning(f"Target penetration {loading_model.target_penetration_or_load} is negative. Assuming magnitude.")
            pass
    # Add validation for "load" type if needed (e.g., ensuring load value is not None)


    if loading_model.target_type == "penetration" and \
       loading_model.target_penetration_or_load is not None and \
       loading_model.target_penetration_or_load != 0:
        target_displacement_uz = -abs(loading_model.target_penetration_or_load) # Convention: negative Z is downward displacement
        displacement_name = "Spudcan_TargetPenetration"

        def define_target_displacement_callable(g_i: Any) -> None:
            logger.info(f"  API CALL: Defining PointDisplacement '{displacement_name}' at {load_application_point} with uz={target_displacement_uz}")
            try:
                # Ensure Displacement_z="Prescribed" or similar is correct for PLAXIS version
                g_i.pointdispl(load_application_point, Name=displacement_name, uz=target_displacement_uz, Displacement_z="Prescribed")
                logger.debug(f"    PointDisplacement '{displacement_name}' defined using pointdispl.")
            except Exception as e: # Catch PlxScriptingError or other
                logger.error(f"    ERROR defining PointDisplacement '{displacement_name}': {e}", exc_info=True)
                raise # Re-raise
        callables.append(define_target_displacement_callable)

    if not callables:
        logger.info("No specific loading condition objects (preload/target displacement) generated by callables.")

    return callables

# --- Analysis Control (Meshing, Phases) ---

def generate_analysis_control_callables(
    control_model: AnalysisControlParameters,
    loading_conditions_model: Optional[LoadingConditions] = None
) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for analysis control.
    Args are per original spec.
    Raises:
        PlaxisConfigurationError: If critical parameters are missing or invalid (e.g. unknown mesh coarseness).
                                 Currently, relies on default values or simple mappings. More validation can be added.
    """
    callables: List[Callable[[Any], None]] = []
    logger.info(f"Preparing analysis control callables: Mesh={control_model.meshing_global_coarseness}, "
                f"InitialStress={control_model.initial_stress_method}")

    # Example validation for mesh coarseness
    valid_coarseness = ["VeryCoarse", "Coarse", "Medium", "Fine", "VeryFine"]
    if control_model.meshing_global_coarseness and control_model.meshing_global_coarseness not in valid_coarseness:
        msg = f"Invalid meshing_global_coarseness: '{control_model.meshing_global_coarseness}'. Must be one of {valid_coarseness}."
        logger.error(msg)
        raise PlaxisConfigurationError(msg)


    # --- Meshing Callables ---
    def mesh_generation_callable(g_i: Any) -> None:
        logger.info("API CALL: Setting up and generating mesh.")
        try:
            g_i.gotomesh()
            logger.info("  Switched to mesh mode.")

            coarseness_setting = control_model.meshing_global_coarseness or "Medium"
            mesh_coarseness_map = {
                "VeryCoarse": 0.2, "Coarse": 0.1, "Medium": 0.05,
                "Fine": 0.025, "VeryFine": 0.01
            }
            # No need to raise here if not in map, as we validated above or it defaults.
            coarseness_factor = mesh_coarseness_map.get(coarseness_setting, 0.05) # Default if somehow missed validation

            g_i.mesh("Coarseness", coarseness_factor)
            logger.info(f"  Mesh generation triggered with Coarseness Factor: {coarseness_factor} (for '{coarseness_setting}').")

            if control_model.meshing_refinement_spudcan:
                spudcan_volume_name = "Spudcan_ConeVolume"
                logger.info(f"  Conceptual: Local mesh refinement for '{spudcan_volume_name}' would be applied here (e.g., g_i.refinemesh).")

            g_i.gotostages()
            logger.info("  Switched back to staged construction mode.")
        except Exception as e: # Catch PlxScriptingError or other
            logger.error(f"  ERROR during mesh generation: {e}", exc_info=True)
            raise # Re-raise
    callables.append(mesh_generation_callable)

    phase_objects_map = {}
    initial_phase_name = "InitialPhase"

    def initial_phase_setup_callable(g_i: Any) -> None:
        nonlocal phase_objects_map
        logger.info(f"API CALL: Setting up '{initial_phase_name}'.")
        try:
            retrieved_initial_phase = None
            if hasattr(g_i, 'Phases') and g_i.Phases:
                for p in g_i.Phases:
                    p_id = getattr(getattr(p, "Identification", None), "value", None)
                    p_name = getattr(getattr(p,"Name", None),"value", None)
                    if p_id == initial_phase_name or p_name == initial_phase_name or p_id == "InitialPhase" or p_name == "InitialPhase":
                        retrieved_initial_phase = p
                        break
                if not retrieved_initial_phase and g_i.Phases:
                    retrieved_initial_phase = g_i.Phases[0]

            if not retrieved_initial_phase:
                 # Raise a more specific error if the initial phase cannot be found
                 raise PlaxisConfigurationError(f"Could not retrieve InitialPhase object (expected name like '{initial_phase_name}' or at index 0). Critical for setup.")

            phase_objects_map[initial_phase_name] = retrieved_initial_phase
            logger.debug(f"  Retrieved InitialPhase: {getattr(retrieved_initial_phase,'Name',{}).get('value', 'Unnamed')}")

            calc_type = control_model.initial_stress_method or "K0Procedure"
            g_i.set(retrieved_initial_phase.DeformCalcType, calc_type)
            logger.info(f"  Set DeformCalcType for '{initial_phase_name}' to '{calc_type}'.")

            if hasattr(g_i, 'Soils'):
                for soil_vol in g_i.Soils: g_i.activate(soil_vol, retrieved_initial_phase)
            if hasattr(g_i, 'Boreholes'):
                for bh in g_i.Boreholes: g_i.activate(bh, retrieved_initial_phase)
            logger.info(f"  Activated soils and boreholes in '{initial_phase_name}'.")
        except Exception as e: # Catch PlxScriptingError or other
            logger.error(f"  ERROR during '{initial_phase_name}' setup: {e}", exc_info=True)
            raise # Re-raise
    callables.append(initial_phase_setup_callable)

    current_previous_phase_name_for_map = initial_phase_name

    if loading_conditions_model and loading_conditions_model.vertical_preload is not None and loading_conditions_model.vertical_preload != 0:
        preload_phase_name = "PreloadPhase"
        spudcan_geom_name = "Spudcan_ConeVolume"
        preload_load_name = "Spudcan_Preload"

        def preload_phase_setup_callable(g_i: Any) -> None:
            nonlocal phase_objects_map
            logger.info(f"API CALL: Setting up '{preload_phase_name}'.")
            try:
                prev_phase_obj = phase_objects_map.get(initial_phase_name)
                if not prev_phase_obj:
                    raise PlaxisConfigurationError(f"PreloadPhase setup: Previous phase '{initial_phase_name}' object not found in map.")

                current_phase_obj = g_i.phase(prev_phase_obj)
                g_i.rename(current_phase_obj, preload_phase_name)
                phase_objects_map[preload_phase_name] = current_phase_obj
                logger.info(f"  Phase '{preload_phase_name}' created after '{initial_phase_name}'.")

                g_i.set(current_phase_obj.DeformCalcType, "Plastic")
                if hasattr(g_i, 'Volumes') and spudcan_geom_name in g_i.Volumes:
                    g_i.activate(g_i.Volumes[spudcan_geom_name], current_phase_obj)
                else: logger.warning(f"  Spudcan geometry '{spudcan_geom_name}' not found for activation in {preload_phase_name}.")
                if hasattr(g_i, 'PointLoads') and preload_load_name in g_i.PointLoads:
                    g_i.activate(g_i.PointLoads[preload_load_name], current_phase_obj)
                else: logger.warning(f"  Preload object '{preload_load_name}' not found for activation in {preload_phase_name}.")
                logger.info(f"  '{preload_phase_name}' configured (Plastic analysis, spudcan & preload activated).")
            except Exception as e: # Catch PlxScriptingError or other
                logger.error(f"  ERROR during '{preload_phase_name}' setup: {e}", exc_info=True)
                raise # Re-raise
        callables.append(preload_phase_setup_callable)
        current_previous_phase_name_for_map = preload_phase_name

    penetration_phase_name = "PenetrationPhase"
    spudcan_geom_name = "Spudcan_ConeVolume"
    target_disp_name = "Spudcan_TargetPenetration"

    def penetration_phase_setup_callable(g_i: Any) -> None:
        nonlocal phase_objects_map
        logger.info(f"API CALL: Setting up '{penetration_phase_name}'.")
        try:
            prev_phase_obj = phase_objects_map.get(current_previous_phase_name_for_map)
            if not prev_phase_obj:
                 raise PlaxisConfigurationError(f"PenetrationPhase setup: Previous phase '{current_previous_phase_name_for_map}' object not found.")

            current_phase_obj = g_i.phase(prev_phase_obj)
            g_i.rename(current_phase_obj, penetration_phase_name)
            phase_objects_map[penetration_phase_name] = current_phase_obj
            logger.info(f"  Phase '{penetration_phase_name}' created after '{current_previous_phase_name_for_map}'.")

            g_i.set(current_phase_obj.DeformCalcType, "Plastic")

            if hasattr(g_i, 'Volumes') and spudcan_geom_name in g_i.Volumes:
                 g_i.activate(g_i.Volumes[spudcan_geom_name], current_phase_obj)
            else: logger.warning(f"  Spudcan geometry '{spudcan_geom_name}' not found for activation in {penetration_phase_name}.")

            if loading_conditions_model:
                if loading_conditions_model.target_type == "penetration" and \
                   target_disp_name and hasattr(g_i, 'PointDisplacements') and target_disp_name in g_i.PointDisplacements:
                    g_i.activate(g_i.PointDisplacements[target_disp_name], current_phase_obj)
                    logger.info(f"    Activated PointDisplacement '{target_disp_name}'.")
                elif loading_conditions_model.target_type == "load":
                    main_load_name = "Spudcan_Preload"
                    if hasattr(g_i, 'PointLoads') and main_load_name in g_i.PointLoads:
                        g_i.activate(g_i.PointLoads[main_load_name], current_phase_obj)
                        logger.info(f"    Activated PointLoad '{main_load_name}' for target load control.")
                    else:
                        logger.warning(f"    Load object for target type 'load' (e.g., '{main_load_name}') not found for activation.")

            if control_model.MaxStepsStored is not None:
                g_i.set(current_phase_obj.MaxStepsStored, control_model.MaxStepsStored)
                logger.info(f"    Set MaxStepsStored to {control_model.MaxStepsStored}.")

            if hasattr(current_phase_obj, 'Deform'):
                deform_obj = current_phase_obj.Deform
                if control_model.MaxSteps is not None:
                    g_i.set(deform_obj.MaxSteps, control_model.MaxSteps)
                    logger.info(f"    Set Deform.MaxSteps to {control_model.MaxSteps}.")
                if control_model.ToleratedError is not None:
                    g_i.set(deform_obj.ToleratedError, control_model.ToleratedError)
                    logger.info(f"    Set Deform.ToleratedError to {control_model.ToleratedError}.")
                if control_model.MinIterations is not None:
                    g_i.set(deform_obj.MinIterations, control_model.MinIterations)
                    logger.info(f"    Set Deform.MinIterations to {control_model.MinIterations}.")
                if control_model.MaxIterations is not None:
                    g_i.set(deform_obj.MaxIterations, control_model.MaxIterations)
                    logger.info(f"    Set Deform.MaxIterations to {control_model.MaxIterations}.")
                if control_model.OverRelaxationFactor is not None:
                    g_i.set(deform_obj.OverRelaxation, control_model.OverRelaxationFactor)
                    logger.info(f"    Set Deform.OverRelaxation to {control_model.OverRelaxationFactor}.")
                if control_model.UseArcLengthControl is not None:
                    g_i.set(deform_obj.ArcLengthControl, control_model.UseArcLengthControl)
                    logger.info(f"    Set Deform.ArcLengthControl to {control_model.UseArcLengthControl}.")
                if control_model.UseLineSearch is not None:
                    g_i.set(deform_obj.UseLineSearch, control_model.UseLineSearch)
                    logger.info(f"    Set Deform.UseLineSearch to {control_model.UseLineSearch}.")
            else:
                logger.warning(f"  Warning: Could not access Deform attribute on phase '{penetration_phase_name}' to set detailed iteration parameters.")

            if control_model.ResetDispToZero is True:
                 g_i.set(current_phase_obj.ResetDisplacementsToZero, True)
                 logger.info(f"    Set ResetDisplacementsToZero to True for '{penetration_phase_name}'.")

            deform_calc_type_value = getattr(current_phase_obj.DeformCalcType, "value", str(current_phase_obj.DeformCalcType))
            if control_model.TimeInterval is not None and deform_calc_type_value in ["Consolidation", "Dynamics", "Fully coupled flow-deformation", "Dynamics with consolidation"]:
                g_i.set(current_phase_obj.TimeInterval, control_model.TimeInterval)
                logger.info(f"    Set TimeInterval to {control_model.TimeInterval} for '{penetration_phase_name}'.")

            logger.info(f"  '{penetration_phase_name}' configured.")
        except Exception as e: # Catch PlxScriptingError or other
            logger.error(f"  ERROR during '{penetration_phase_name}' setup: {e}", exc_info=True)
            raise # Re-raise
    callables.append(penetration_phase_setup_callable)

    # --- Calculation Trigger Callable ---
    def calculate_callable(g_i: Any) -> None:
        phase_to_calculate_name = penetration_phase_name

        has_target_penetration = loading_conditions_model and loading_conditions_model.target_penetration is not None
        has_target_load = loading_conditions_model and loading_conditions_model.target_load is not None
        has_preload = loading_conditions_model and loading_conditions_model.vertical_preload is not None and loading_conditions_model.vertical_preload != 0

        if not (has_target_penetration or has_target_load):
            if has_preload:
                phase_to_calculate_name = "PreloadPhase"
                logger.debug(f"No target penetration/load specified; will calculate PreloadPhase: {phase_to_calculate_name}")
            else:
                phase_to_calculate_name = initial_phase_name
                logger.debug(f"No target penetration/load or preload specified; will calculate InitialPhase: {phase_to_calculate_name}")
        else:
            logger.debug(f"Target penetration/load specified; will calculate PenetrationPhase: {phase_to_calculate_name}")


        logger.info(f"API CALL: Triggering calculation for phase: '{phase_to_calculate_name}'.")
        try:
            phase_obj_to_calculate = phase_objects_map.get(phase_to_calculate_name)
            if not phase_obj_to_calculate:
                raise PlaxisConfigurationError(f"Cannot trigger calculation: Phase object '{phase_to_calculate_name}' not found in map. Available: {list(phase_objects_map.keys())}")

            g_i.calculate(phase_obj_to_calculate)
            logger.info(f"  Calculation command issued for phase '{phase_to_calculate_name}'.")
        except Exception as e: # Catch PlxScriptingError or other
            logger.error(f"  ERROR during calculation trigger for phase '{phase_to_calculate_name}': {e}", exc_info=True)
            raise # Re-raise
    callables.append(calculate_callable)

    logger.info(f"Generated {len(callables)} analysis control and calculation callables.")
    return callables

# ... (Rest of the file, including __main__ block, remains the same for now) ...
# The __main__ block would need updates to catch PlaxisConfigurationError for tests that previously expected ValueError or similar.
# For brevity, those __main__ changes are omitted here but would be part of the actual implementation.
# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    # Setup basic logging for __main__
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("--- Testing Calculation Builder Callable Generation (with Exception Handling) ---")

    # Mock g_i for testing callable structure
    class MockG_i_Calc:
        # ... (MockG_i_Calc definition as in SEARCH block) ...
        def __init__(self):
            self.log = []
            self.Mesh = type("MockMesh", (), {"CoarsenessFactor": 0.05})()
            self.Phases = []
            self.Volumes = {"Spudcan_ConeVolume": "spudcan_geom_obj_placeholder"}
            self.PointLoads = {}
            self.PointDisplacements = {}
            self.CurvePoints = []

        def command(self, cmd_str: str): self.log.append(f"COMMAND: {cmd_str}"); logger.debug(f"  MockG_i.command: {cmd_str}")
        def gotomesh(self): self.log.append("CALL: gotomesh()"); logger.debug("  MockG_i.gotomesh()")
        def mesh(self, coarseness_type=None, factor=None): # Added args to match call
             self.log.append(f"CALL: mesh(Coarseness={coarseness_type}, Factor={factor})"); logger.debug(f"  MockG_i.mesh(Coarseness={coarseness_type}, Factor={factor})")
        def gotostages(self): self.log.append("CALL: gotostages()"); logger.debug("  MockG_i.gotostages()")

        def set(self, target_attr_path, value):
            # This mock is still very simplified.
            log_msg = f"CALL: g_i.set({str(target_attr_path)}, {value})"
            self.log.append(log_msg)
            logger.debug(f"  MockG_i.set({str(target_attr_path)}, {value})")
            # Simulate setting on mock objects if possible
            if hasattr(target_attr_path, 'value'): # If it's a property object
                target_attr_path.value = value
            # Or if target_attr_path is the object and value is a dict of props (not used here)
            # Or if it's obj, "PropName", value (not used here)

        def phase(self, prev_phase_obj_or_none=None, Name=None): # Added default for prev_phase
            new_phase_name = Name or f"Phase_{len(self.Phases)+1}"
            mock_phase = type("MockPhase", (), {
                "Name": type("MockName",(),{"value":new_phase_name})(), # Simulate .value access
                "Identification": type("MockId",(),{"value":new_phase_name})(),
                "DeformCalcType": type("MockProp",(),{"value":None})(),
                "MaxStepsStored": type("MockProp",(),{"value":None})(),
                "ResetDisplacementsToZero": type("MockProp",(),{"value":False})(),
                "TimeInterval": type("MockProp",(),{"value":None})(),
                "Deform": type("MockDeform", (), { # Nested mock for Deform attributes
                    "MaxSteps": type("MockProp",(),{"value":None})(),
                    "ToleratedError": type("MockProp",(),{"value":None})(),
                    "MinIterations": type("MockProp",(),{"value":None})(),
                    "MaxIterations": type("MockProp",(),{"value":None})(),
                    "OverRelaxation": type("MockProp",(),{"value":None})(),
                    "ArcLengthControl": type("MockProp",(),{"value":None})(),
                    "UseLineSearch": type("MockProp",(),{"value":None})(),
                    })()
            })()
            self.Phases.append(mock_phase)
            prev_phase_id = getattr(getattr(prev_phase_obj_or_none, "Identification", None), "value", "None")
            self.log.append(f"CALL: g_i.phase(prev='{prev_phase_id}', Name='{Name}') -> {new_phase_name}")
            logger.debug(f"  MockG_i.phase created: {new_phase_name}")
            return mock_phase

        def activate(self, obj_to_activate, phase_obj):
            obj_name = obj_to_activate.Name.value if hasattr(obj_to_activate, 'Name') and hasattr(obj_to_activate.Name, 'value') else str(obj_to_activate)
            phase_name = phase_obj.Name.value if hasattr(phase_obj, 'Name') and hasattr(phase_obj.Name, 'value') else str(phase_obj)
            self.log.append(f"CALL: g_i.activate(obj='{obj_name}', phase='{phase_name}')")
            logger.debug(f"  MockG_i.activate('{obj_name}' in phase '{phase_name}')")

        def pointload(self, coords, Name, Fz):
            self.PointLoads[Name] = {"coords": coords, "Fz": Fz}
            self.log.append(f"CALL: g_i.pointload({coords}, Name='{Name}', Fz={Fz})")
            logger.debug(f"  MockG_i.pointload created: {Name}")

        def pointdispl(self, coords, Name, uz, Displacement_z): # Changed from pointdisplacement
            self.PointDisplacements[Name] = {"coords": coords, "uz": uz, "Displacement_z": Displacement_z}
            self.log.append(f"CALL: g_i.pointdispl({coords}, Name='{Name}', uz={uz}, Disp_z='{Displacement_z}')")
            logger.debug(f"  MockG_i.pointdispl created: {Name}")

        def calculate(self, phase_to_calculate):
            phase_name = phase_to_calculate.Name.value
            self.log.append(f"CALL: g_i.calculate(phase='{phase_name}')")
            logger.debug(f"  MockG_i.calculate on phase: {phase_name}")
            if phase_name == "PhaseToFailCalculation": # For testing error propagation
                raise Exception("Simulated PlxScriptingError during g_i.calculate")


        def rename(self, obj_ref, new_name):
             old_name = obj_ref.Name.value
             obj_ref.Name.value = new_name
             obj_ref.Identification.value = new_name # Assuming ID also changes
             self.log.append(f"CALL: g_i.rename(obj with old name '{old_name}', new_name='{new_name}')")
             logger.debug(f"  MockG_i.rename obj to '{new_name}'")


    # Test Loading Condition Callables
    logger.info("\n--- Testing Loading Condition Callable Generation ---")
    sample_loading_cond = LoadingConditions(
        vertical_preload=1000.0,
        target_penetration_or_load=0.5,
        target_type="penetration"
    )
    loading_callables = generate_loading_condition_callables(sample_loading_cond)
    logger.info(f"Generated {len(loading_callables)} loading callables.")
    mock_g_i_loading = MockG_i_Calc()
    for func in loading_callables: func(mock_g_i_loading)
    assert "Spudcan_Preload" in mock_g_i_loading.PointLoads
    assert "Spudcan_TargetPenetration" in mock_g_i_loading.PointDisplacements

    # Test Analysis Control Callables - Valid
    logger.info("\n--- Testing Analysis Control Callable Generation (Valid) ---")
    sample_control_params_valid = AnalysisControlParameters(
        meshing_global_coarseness="Fine",
        initial_stress_method="K0Procedure",
        max_iterations=150,
        tolerated_error=0.005
    )
    try:
        analysis_callables_valid = generate_analysis_control_callables(sample_control_params_valid, sample_loading_cond)
        logger.info(f"Generated {len(analysis_callables_valid)} analysis control callables.")
        mock_g_i_analysis_valid = MockG_i_Calc()
        # Initialize a mock InitialPhase as it's assumed to exist by initial_phase_setup_callable
        mock_g_i_analysis_valid.Phases.append(mock_g_i_analysis_valid.phase(Name="InitialPhase")) # Use mock phase creation

        for func in analysis_callables_valid: func(mock_g_i_analysis_valid)
        assert len(mock_g_i_analysis_valid.Phases) >= 3 # Initial + Preload + Penetration
        assert mock_g_i_analysis_valid.Phases[1].Name.value == "PreloadPhase"
        assert mock_g_i_analysis_valid.Phases[2].Name.value == "PenetrationPhase"
        logger.info("Valid analysis control callables executed with mock.")
    except Exception as e:
        logger.error(f"Error during valid analysis control test: {type(e).__name__} - {e}", exc_info=True)


    # Test Analysis Control Callables - Invalid Mesh Coarseness
    logger.info("\n--- Testing Analysis Control with Invalid Mesh Coarseness ---")
    sample_control_invalid_mesh = AnalysisControlParameters(meshing_global_coarseness="SuperFine")
    try:
        generate_analysis_control_callables(sample_control_invalid_mesh, sample_loading_cond)
        logger.error("UNEXPECTED: generate_analysis_control_callables did not raise for invalid mesh coarseness.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for invalid mesh: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED error type for invalid mesh: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)

    # Test error propagation from calculate_callable
    logger.info("\n--- Testing Error Propagation from calculate_callable ---")
    mock_g_i_calc_fail = MockG_i_Calc()
    # Setup phases so calculate_callable can find "PhaseToFailCalculation"
    initial_phase_calc_fail = mock_g_i_calc_fail.phase(Name="InitialPhase")
    # Modify the last phase to be the one that fails calculation for the test
    preload_phase_calc_fail = mock_g_i_calc_fail.phase(prev_phase_obj_or_none=initial_phase_calc_fail, Name="PreloadPhase")
    penetration_phase_to_fail = mock_g_i_calc_fail.phase(prev_phase_obj_or_none=preload_phase_calc_fail, Name="PhaseToFailCalculation") # This is the one to calculate

    # Create a map similar to what's in generate_analysis_control_callables
    phase_map_for_fail_test = {
        "InitialPhase": initial_phase_calc_fail,
        "PreloadPhase": preload_phase_calc_fail,
        "PhaseToFailCalculation": penetration_phase_to_fail
    }

    # Get only the calculate_callable (it's the last one)
    # Need to generate all callables to get the `calculate_callable` with its closure state.
    # We'll use a valid control model for setup, but the mock g_i's `calculate` will fail.
    analysis_callables_for_calc_fail = generate_analysis_control_callables(sample_control_params_valid, sample_loading_cond)

    # Simulate the state of phase_objects_map *before* calculate_callable is invoked
    # This is a bit of a hack for testing the standalone callable. In reality, the main function sets this up.
    # We'll find the actual calculate_callable and try to invoke it.

    # Find the calculate_callable (usually the last one)
    actual_calculate_callable = None
    for c in reversed(analysis_callables_for_calc_fail):
        if "calculate_callable" in getattr(c, "__name__", ""):
            actual_calculate_callable = c
            break

    if actual_calculate_callable:
        try:
            # To properly test calculate_callable, its closure needs `phase_objects_map`
            # This is difficult to inject from outside. The test for `PlaxisInteractor` executing these
            # callables is a more robust way to test this error propagation.
            # For now, this specific test of calculate_callable in isolation for exception is limited.
            # We'll rely on the `mock_g_i_calc_fail.calculate` to raise.
            # We need to execute the phase setup callables first to populate the map in the closure.

            # Execute setup callables on mock_g_i_calc_fail to populate its internal phase_objects_map
            # This assumes the closure of calculate_callable uses the *same* phase_objects_map instance
            # as the phase setup callables when generated by generate_analysis_control_callables.

            # Re-generate with the specific mock instance to ensure closure capture
            # This is not ideal but necessary for this type of unit test of a closure.

            # The best way is to test this via the PlaxisInteractor's execution of these callables.
            # However, for a direct test of the callable:
            # We would need to modify generate_analysis_control_callables to accept phase_objects_map
            # or make calculate_callable not rely on closure but take phase_objects_map as arg.

            logger.warning("Direct test of calculate_callable's error propagation is limited here. "
                           "Relies on mock g_i.calculate raising, and assumes phase map is populated by prior calls "
                           "if this were part of a sequence. Better tested via Interactor.")

            # To simulate the map being populated for the *specific* `calculate_callable` obtained:
            # This requires a bit of introspection or refactoring.
            # For now, let's assume the mock `g_i.calculate` is set to fail for "PhaseToFailCalculation"
            # and that the `phase_objects_map` within the `calculate_callable`'s closure
            # will contain this phase if the preceding setup callables were run.

            # The test setup for mock_g_i_calc_fail already created "PhaseToFailCalculation".
            # If generate_analysis_control_callables is called with this mock, it will use this phase.

            # Let's try to run the sequence on mock_g_i_calc_fail
            mock_g_i_calc_fail.Phases = [] # Reset phases for this specific mock
            mock_g_i_calc_fail.Phases.append(mock_g_i_calc_fail.phase(Name="InitialPhase")) # Initial phase for the mock

            # This will generate callables where calculate_callable's closure has the map from this run
            callables_run_on_failing_mock = generate_analysis_control_callables(sample_control_params_valid, sample_loading_cond)

            failed_as_expected = False
            for func_idx, func_call in enumerate(callables_run_on_failing_mock):
                try:
                    func_call(mock_g_i_calc_fail)
                except Exception as e_calc:
                    if "Simulated PlxScriptingError during g_i.calculate" in str(e_calc) and "calculate_callable" in getattr(func_call, "__name__", ""):
                        logger.info(f"SUCCESS: Caught expected error from calculate_callable: {e_calc}")
                        failed_as_expected = True
                        break
                    else: # Some other callable failed, or unexpected error
                        logger.error(f"Error in callable {func_idx} ('{getattr(func_call,'__name__','')}') before reaching intended failure: {e_calc}", exc_info=True)
                        failed_as_expected = True # Mark as failed to prevent "UNEXPECTED SUCCESS" log
                        break
            if not failed_as_expected:
                 logger.error("UNEXPECTED SUCCESS: calculate_callable did not propagate error as expected.")

        except Exception as e:
            logger.error(f"Error during calculate_callable error propagation test setup: {e}", exc_info=True)
    else:
        logger.warning("Could not find calculate_callable for error propagation test.")


    # Note: Output Request Callables are removed, so no test for them.

    logger.info("\n--- End of Calculation Builder Callable Generation Tests (with Exception Handling) ---")
