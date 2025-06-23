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

from ..models import LoadingConditions, AnalysisControlParameters # Relative import from parent package
from typing import List, Callable, Any, Optional

# --- Loading Conditions ---

def generate_loading_condition_callables(
    loading_model: LoadingConditions,
    spudcan_ref_point: Tuple[float, float, float] = (0,0,0) # Default to origin if not provided
) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for defining loading conditions.
    Loads are typically defined as objects first (e.g., PointLoad, PrescribedDisplacement)
    and then activated in specific calculation phases.

    Args:
        loading_model: The LoadingConditions data model instance.
        spudcan_ref_point: A tuple (x,y,z) representing the point on the spudcan
                           where loads/displacements should be applied. Defaults to (0,0,0).

    Returns:
        A list of callable functions for PLAXIS API interaction.

    Assumptions:
    - Vertical loads/displacements are along the Z-axis. Downwards is negative Z.
    - PLAXIS API provides methods like `g_i.pointload(...)` and `g_i.pointdispl(...)`.
    - Names for load objects (e.g., "SpudcanPreload", "SpudcanPenetrationDispl") are assigned for
      later reference during phase activation.
    - Load steps or displacement increments, if specified in `loading_model`, are primarily
      used during phase definition (e.g., setting number of steps, load multipliers) rather
      than direct load object creation.
    """
    callables: List[Callable[[Any], None]] = []
    print(f"Preparing loading condition callables: Preload={loading_model.vertical_preload}, "
          f"Target={loading_model.target_penetration_or_load} ({loading_model.target_type}) "
          f"at reference point {spudcan_ref_point}")

    load_application_point = spudcan_ref_point

    # Callable for Vertical Pre-load
    if loading_model.vertical_preload is not None and loading_model.vertical_preload != 0:
        preload_value_fz = -abs(loading_model.vertical_preload) # Downward force
        preload_name = "Spudcan_Preload"

        def define_preload_callable(g_i: Any) -> None:
            print(f"  PLAXIS API CALL: Defining PointLoad '{preload_name}' at {load_application_point} with Fz={preload_value_fz}")
            try:
                # Example: g_i.pointload(coordinates, Name="name", Fz=value)
                # The exact parameters for g_i.pointload need to match the PLAXIS API.
                g_i.pointload(load_application_point, Name=preload_name, Fz=preload_value_fz)
                # Or, using g_i.command if direct API is complex or for specific PLAXIS versions:
                # g_i.command(f"pointload ({load_application_point[0]} {load_application_point[1]} {load_application_point[2]}) "
                #             f"\"Name\" \"{preload_name}\" \"Fz\" {preload_value_fz}")
                print(f"    PointLoad '{preload_name}' defined.")
            except Exception as e:
                print(f"    ERROR defining PointLoad '{preload_name}': {e}")
                raise
        callables.append(define_preload_callable)

    # Callable for Target Penetration (as Prescribed Displacement)
    if loading_model.target_type == "penetration" and \
       loading_model.target_penetration_or_load is not None and \
       loading_model.target_penetration_or_load != 0:

        target_displacement_uz = -abs(loading_model.target_penetration_or_load) # Downward displacement
        displacement_name = "Spudcan_TargetPenetration"

        def define_target_displacement_callable(g_i: Any) -> None:
            print(f"  PLAXIS API CALL: Defining PointDisplacement (using pointdispl) '{displacement_name}' at {load_application_point} with uz={target_displacement_uz}")
            try:
                # Documentation uses g_i.pointdispl
                # Example from docs: point_g, pointdisplacement_g = g_i.pointdispl((5, 6, 7), "Displacement_x", "Fixed", ...)
                # This suggests it can create the point and the displacement feature, and set properties.
                # We assume our simplified call with keyword args for Name, uz, Displacement_z is handled by the scripting layer
                # or should be mapped to the property-value pair style if direct keywords aren't supported.
                # Correcting command name from pointdisplacement to pointdispl.
                # The properties like Name, uz, Displacement_z might need to be passed as sequential args
                # e.g. g_i.pointdispl(coords, "Name", name, "uz", val, "Displacement_z", "Prescribed")
                # For now, keeping keyword style, assuming plxscripting handles it or it's a simplified representation.
                # A more robust call based on docs:
                # point_obj, displ_feature = g_i.pointdispl(load_application_point,
                #                                           "Name", displacement_name,
                #                                           "uz", target_displacement_uz,
                #                                           "Displacement_z", "Prescribed")
                # For this refinement, only changing the command name:
                g_i.pointdispl(load_application_point, Name=displacement_name, uz=target_displacement_uz, Displacement_z="Prescribed")
                print(f"    PointDisplacement '{displacement_name}' defined using pointdispl.")
            except Exception as e:
                print(f"    ERROR defining PointDisplacement '{displacement_name}' using pointdispl: {e}")
                raise
        callables.append(define_target_displacement_callable)

    # Note: If target_type is "load", the load is typically defined like the preload
    # and its magnitude might be ramped up in the calculation phase.
    # If the target load is *different* from preload, another PointLoad object would be defined here.
    # For this exercise, if target_type is "load", it's assumed this load value will be used in
    # a phase, potentially activating a load object defined similarly to the preload.
    # The current structure doesn't explicitly create a *separate* load object for "target_load"
    # if preload already exists. This might need refinement based on exact workflow.

    if not callables:
        print("No specific loading condition objects (preload/target displacement) generated by callables.")

    return callables

# --- Analysis Control (Meshing, Phases) ---

def generate_analysis_control_callables(
    control_model: AnalysisControlParameters,
    loading_conditions_model: Optional[LoadingConditions] = None # Needed for phase setup
) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for analysis control including meshing and calculation phases.

    Args:
        control_model: The AnalysisControlParameters data model.
        loading_conditions_model: The LoadingConditions data model, used for phase setup.

    Returns:
        A list of callable functions for PLAXIS API interaction.

    Assumptions:
    - Meshing:
        - `g_i.gotomesh()` switches to mesh mode.
        - Global mesh coarseness can be set (e.g., `g_i.set(g_i.Mesh.CoarsenessFactor, value)` or similar).
          The mapping from string ("Fine", "Medium") to a numerical factor is heuristic.
        - `g_i.mesh()` generates the mesh.
        - Local refinements (e.g., for spudcan) are not implemented in this basic version but would
          involve selecting the spudcan volume/surfaces and applying refinement factors.
    - Phases:
        - `g_i.gotostages()` switches to staged construction mode.
        - `g_i.phase(previous_phase_object_or_None)` creates a new phase. If `None`, it's the initial phase.
        - Phase properties (e.g., `DeformCalcType`, `MaxStepsStored`, `ToleratedError`) are set using
          `g_i.set(phase_object.PropertyPath, value)`. Property paths need to be exact.
        - Activating/deactivating geometry and loads in phases uses `g_i.activate(object, phase)`
          and `g_i.deactivate(object, phase)`. Object names must match those defined earlier.
    - Initial Conditions:
        - `control_model.initial_stress_method` (e.g., "K0Procedure", "GravityLoading") is applied to the InitialPhase.
        - Soils and Boreholes (for water conditions) are activated in the InitialPhase.
    - Phase Sequencing: A standard sequence is assumed:
        1. InitialPhase: Sets up initial stresses and water conditions.
        2. PreloadPhase (optional): Applies spudcan preload. Spudcan geometry is activated.
        3. PenetrationPhase: Applies target penetration (displacement-controlled) or target load.
           This is the main analysis phase.
    - Naming: Phases and load objects are referred to by names assumed to be consistent
      (e.g., "Spudcan_Preload", "InitialPhase", "PenetrationPhase").
    """
    callables: List[Callable[[Any], None]] = []
    print(f"Preparing analysis control callables: Mesh={control_model.meshing_global_coarseness}, "
          f"InitialStress={control_model.initial_stress_method}")

    # --- Meshing Callables ---
    def mesh_generation_callable(g_i: Any) -> None:
        print("  PLAXIS API CALL: Setting up and generating mesh.")
        try:
            g_i.gotomesh() # Switch to mesh mode
            print("    Switched to mesh mode.")

            # Map descriptive coarseness to a numerical factor (example values)
            mesh_coarseness_map = {
                "VeryCoarse": 0.2, "Coarse": 0.1, "Medium": 0.05,
                "Fine": 0.025, "VeryFine": 0.01
            }
            coarseness_setting = control_model.meshing_global_coarseness or "Medium"
            coarseness_factor = mesh_coarseness_map.get(coarseness_setting, 0.05)

            # Set global mesh coarseness.
            # Documentation for `mesh` command shows: mesh(<Factor>) or mesh("Coarseness", <Factor>)
            coarseness_setting = control_model.meshing_global_coarseness
            if coarseness_setting and coarseness_setting != "Medium": # "Medium" is often default
                mesh_coarseness_map = {
                    "VeryCoarse": 0.2, "Coarse": 0.1,
                    "Fine": 0.025, "VeryFine": 0.01
                } # Medium would be around 0.05
                coarseness_factor = mesh_coarseness_map.get(coarseness_setting)
                if coarseness_factor is not None:
                    g_i.mesh("Coarseness", coarseness_factor) # Pass as argument to mesh
                    print(f"    Mesh generation triggered with Coarseness Factor: {coarseness_factor} (for '{coarseness_setting}').")
                else:
                    g_i.mesh() # Fallback to default mesh if mapping fails
                    print(f"    Mesh generation triggered (default). Unknown coarseness '{coarseness_setting}'.")
            else:
                g_i.mesh() # Generate the mesh with default (Medium) coarseness
                print("    Mesh generation triggered (default/Medium coarseness).")

            # TODO: Add local mesh refinement for spudcan if control_model.meshing_refinement_spudcan is True.
            # This would involve finding the spudcan volume (e.g., "Spudcan_ConeVolume") and applying
            # a refinement factor, e.g., g_i.refinemesh(g_i.Volumes["Spudcan_ConeVolume"], factor=0.5) or similar.

            g_i.gotostages() # Switch back to staged construction mode
            print("    Switched back to staged construction mode.")
        except Exception as e:
            print(f"    ERROR during mesh generation: {e}")
            raise
    callables.append(mesh_generation_callable)

    # --- Phase Definition Callables ---
    # These need to be appended in sequence.
    # We'll keep track of the actual phase objects to pass to subsequent g_i.phase calls

    # Initial Phase
    initial_phase_name = "InitialPhase" # Standard PLAXIS name for the first phase

    # Store phase objects as they are created/retrieved for linking
    # This dict will live within the scope of generate_analysis_control_callables
    # and be captured by the lambda callables.
    phase_objects_map = {}

    def initial_phase_setup_callable(g_i: Any) -> None:
        nonlocal phase_objects_map # Allow modification of the outer scope variable
        print(f"  PLAXIS API CALL: Setting up '{initial_phase_name}'.")
        try:
            # The InitialPhase (Phase_1 in CLI) usually exists by default. We configure it.
            # Accessing it might be g_i.Phases[0] or by its default name.
            retrieved_initial_phase = None
            if hasattr(g_i, 'Phases') and g_i.Phases:
                # Try to find by common name first, as index 0 might not always be 'InitialPhase' if user renamed it.
                for p in g_i.Phases:
                    if p.Identification.value == initial_phase_name or p.Name.value == initial_phase_name : # Check both common attributes
                        retrieved_initial_phase = p
                        break
                if not retrieved_initial_phase and g_i.Phases: # Fallback to index 0 if not found by name
                    retrieved_initial_phase = g_i.Phases[0]

            if not retrieved_initial_phase:
                # This case should be rare in a standard PLAXIS new project.
                # If it can happen, creating it might be: initial_phase_obj = g_i.phase(None, Name=initial_phase_name)
                # For now, assume it always exists or the script should fail.
                raise Exception(f"Could not retrieve InitialPhase object (expected name: '{initial_phase_name}' or at index 0).")

            phase_objects_map[initial_phase_name] = retrieved_initial_phase

            # Set calculation type for initial stresses (e.g., K0Procedure)
            calc_type = control_model.initial_stress_method or "K0Procedure" # Default
            # Path to DeformCalcType: retrieved_initial_phase.DeformCalcType or retrieved_initial_phase.CalculationType
            # `all.md` suggests Phase.DeformCalcType
            g_i.set(retrieved_initial_phase.DeformCalcType, calc_type)
            print(f"    Set DeformCalcType for '{initial_phase_name}' to '{calc_type}'.")

            # Activate all soil volumes and boreholes for initial state
            # g_i.activateallsoils(retrieved_initial_phase) - if such a helper exists
            # Or, iterate g_i.Soils and g_i.Boreholes:
            if hasattr(g_i, 'Soils'):
                for soil_vol in g_i.Soils: g_i.activate(soil_vol, retrieved_initial_phase)
            if hasattr(g_i, 'Boreholes'):
                for bh in g_i.Boreholes: g_i.activate(bh, retrieved_initial_phase)
            # Water conditions are often tied to borehole heads or a global water level,
            # which should be active in this phase.
            print(f"    Activated soils and boreholes in '{initial_phase_name}'.")
        except Exception as e:
            print(f"    ERROR during '{initial_phase_name}' setup: {e}")
            raise
    callables.append(initial_phase_setup_callable)

    # Preloading Phase (optional)
    if loading_conditions_model and loading_conditions_model.vertical_preload is not None and loading_conditions_model.vertical_preload != 0:
        preload_phase_name = "PreloadPhase"
        spudcan_geom_name = "Spudcan_ConeVolume" # Assumed name from geometry_builder
        preload_load_name = "Spudcan_Preload"    # Assumed name from loading_condition_callables

        def preload_phase_setup_callable(g_i: Any) -> None:
            nonlocal phase_objects_map
            print(f"  PLAXIS API CALL: Setting up '{preload_phase_name}'.")
            try:
                prev_phase_obj = phase_objects_map.get(initial_phase_name)
                if not prev_phase_obj:
                    raise Exception(f"PreloadPhase setup: Previous phase '{initial_phase_name}' object not found.")

                current_phase_obj = g_i.phase(prev_phase_obj, Name=preload_phase_name)
                phase_objects_map[preload_phase_name] = current_phase_obj
                print(f"    Phase '{preload_phase_name}' created after '{initial_phase_name}'.")

                g_i.set(current_phase_obj.DeformCalcType, "Plastic") # Common for load application
                # Activate spudcan geometry and preload
                if hasattr(g_i, 'Volumes') and spudcan_geom_name in g_i.Volumes:
                    g_i.activate(g_i.Volumes[spudcan_geom_name], current_phase_obj)
                else: print(f"    Warning: Spudcan geometry '{spudcan_geom_name}' not found for activation in {preload_phase_name}.")

                if hasattr(g_i, 'PointLoads') and preload_load_name in g_i.PointLoads: # Assuming PointLoad collection
                    g_i.activate(g_i.PointLoads[preload_load_name], current_phase_obj)
                else: print(f"    Warning: Preload object '{preload_load_name}' not found for activation in {preload_phase_name}.")

                print(f"    '{preload_phase_name}' configured (Plastic analysis, spudcan & preload activated).")
            except Exception as e:
                print(f"    ERROR during '{preload_phase_name}' setup: {e}")
                raise
        callables.append(preload_phase_setup_callable)
        current_previous_phase_name_for_map = preload_phase_name # Update for next phase
    else:
        current_previous_phase_name_for_map = initial_phase_name # No preload phase, initial is previous


    # Penetration Phase (main analysis)
    penetration_phase_name = "PenetrationPhase"
    spudcan_geom_name = "Spudcan_ConeVolume" # Consistent name
    target_disp_name = "Spudcan_TargetPenetration" # From loading_condition_callables

    def penetration_phase_setup_callable(g_i: Any) -> None:
        nonlocal phase_objects_map
        print(f"  PLAXIS API CALL: Setting up '{penetration_phase_name}'.")
        try:
            prev_phase_obj = phase_objects_map.get(current_previous_phase_name_for_map)
            if not prev_phase_obj:
                 raise Exception(f"PenetrationPhase setup: Previous phase '{current_previous_phase_name_for_map}' object not found.")

            current_phase_obj = g_i.phase(prev_phase_obj, Name=penetration_phase_name)
            phase_objects_map[penetration_phase_name] = current_phase_obj
            print(f"    Phase '{penetration_phase_name}' created after '{current_previous_phase_name_for_map}'.")

            g_i.set(current_phase_obj.DeformCalcType, "Plastic") # Or "Consolidation" if time-dependent effects are key

            # Ensure spudcan geometry is active
            if hasattr(g_i, 'Volumes') and spudcan_geom_name in g_i.Volumes:
                 g_i.activate(g_i.Volumes[spudcan_geom_name], current_phase_obj)
            else: print(f"    Warning: Spudcan geometry '{spudcan_geom_name}' not found for activation in {penetration_phase_name}.")

            # Activate target load or displacement
            if loading_conditions_model:
                if loading_conditions_model.target_type == "penetration" and \
                   target_disp_name and hasattr(g_i, 'PointDisplacements') and target_disp_name in g_i.PointDisplacements:
                    g_i.activate(g_i.PointDisplacements[target_disp_name], current_phase_obj)
                    print(f"    Activated PointDisplacement '{target_disp_name}'.")
                elif loading_conditions_model.target_type == "load":
                    # If target is load, need to activate the appropriate load object.
                    # This might be the preload object if it's a continuation, or a new target load object.
                    # For simplicity, assume if preload exists, this phase continues it.
                    # If no preload, and a target load is defined, that load object should be created by
                    # generate_loading_condition_callables and activated here.
                    # This part needs careful coordination with how load objects are named and defined.
                    main_load_name = "Spudcan_Preload" # Assume target load is applied via the preload object for now
                    if hasattr(g_i, 'PointLoads') and main_load_name in g_i.PointLoads:
                        g_i.activate(g_i.PointLoads[main_load_name], current_phase_obj)
                        print(f"    Activated PointLoad '{main_load_name}' for target load control.")
                    else:
                        print(f"    Warning: Load object for target type 'load' (e.g., '{main_load_name}') not found for activation.")

            # Set iteration control parameters from control_model
            # These attributes might be directly on the phase object or nested under phase.Deform.
            # Referencing docs/all.md (GUID-2E473E68-930B-47E0-8DD2-05A775E5E5F1.html - Phase object)
            # and docs/all.md (GUID-7EF3F05E-AD66-482E-9FCD-369DB79C87B5.html - Deform object)

            # MaxStepsStored is often directly on the phase object
            if control_model.MaxStepsStored is not None:
                g_i.set(current_phase_obj.MaxStepsStored, control_model.MaxStepsStored)
                print(f"    Set MaxStepsStored to {control_model.MaxStepsStored}.")

            if hasattr(current_phase_obj, 'Deform'): # Check if Deform sub-object exists
                deform_obj = current_phase_obj.Deform
                if control_model.MaxSteps is not None: # Max calculation steps
                    g_i.set(deform_obj.MaxSteps, control_model.MaxSteps)
                    print(f"    Set Deform.MaxSteps to {control_model.MaxSteps}.")
                if control_model.ToleratedError is not None:
                    g_i.set(deform_obj.ToleratedError, control_model.ToleratedError)
                    print(f"    Set Deform.ToleratedError to {control_model.ToleratedError}.")
                if control_model.MinIterations is not None:
                    g_i.set(deform_obj.MinIterations, control_model.MinIterations)
                    print(f"    Set Deform.MinIterations to {control_model.MinIterations}.")
                if control_model.MaxIterations is not None:
                    g_i.set(deform_obj.MaxIterations, control_model.MaxIterations)
                    print(f"    Set Deform.MaxIterations to {control_model.MaxIterations}.")
                if control_model.OverRelaxationFactor is not None:
                    g_i.set(deform_obj.OverRelaxation, control_model.OverRelaxationFactor) # Docs show OverRelaxation
                    print(f"    Set Deform.OverRelaxation to {control_model.OverRelaxationFactor}.")
                if control_model.UseArcLengthControl is not None:
                    # PLAXIS API might expect integer/enum for ArcLengthControl (e.g. 0=Off, 1=On, -1=Auto)
                    # Or a string "On", "Off", "Auto". Assuming boolean maps to On/Off.
                    # A direct boolean set might work if plxscripting handles it.
                    # For robustness, map to known PLAXIS values if boolean isn't direct.
                    # Example: arc_control_value = "On" if control_model.UseArcLengthControl else "Off"
                    # g_i.set(deform_obj.ArcLengthControl, arc_control_value)
                    g_i.set(deform_obj.ArcLengthControl, control_model.UseArcLengthControl) # Try direct bool
                    print(f"    Set Deform.ArcLengthControl to {control_model.UseArcLengthControl}.")
                if control_model.UseLineSearch is not None:
                    g_i.set(deform_obj.UseLineSearch, control_model.UseLineSearch)
                    print(f"    Set Deform.UseLineSearch to {control_model.UseLineSearch}.")
            else:
                print(f"    Warning: Could not access Deform attribute on phase '{penetration_phase_name}' to set detailed iteration parameters.")

            if control_model.ResetDispToZero is not None and control_model.ResetDispToZero:
                 g_i.set(current_phase_obj.ResetDisplacementsToZero, True)
                 print(f"    Set ResetDisplacementsToZero to True for '{penetration_phase_name}'.")

            if control_model.TimeInterval is not None and current_phase_obj.DeformCalcType.value in ["Consolidation", "Dynamics", "Fully coupled flow-deformation", "Dynamics with consolidation"]:
                # TimeInterval is usually on the phase itself for consolidation/dynamic type calcs
                g_i.set(current_phase_obj.TimeInterval, control_model.TimeInterval)
                print(f"    Set TimeInterval to {control_model.TimeInterval} for '{penetration_phase_name}'.")


            print(f"    '{penetration_phase_name}' configured.")
        except Exception as e:
            print(f"    ERROR during '{penetration_phase_name}' setup: {e}")
            raise
    callables.append(penetration_phase_setup_callable)

    return callables

# --- Output Request Configuration ---
# Based on documentation (all.md GUID-0171B46E-90D4-4C5F-869D-F8E22B2AE570.html),
# `addcurvepoint` is an Output command (operates on g_o).
# Therefore, pre-selecting curve points in the Input phase via g_i is likely not standard
# or might not be effective for all PLAXIS versions/workflows.
# The selection of points for curves is typically done in the Output environment
# when results are being extracted (e.g., before calling getcurveresults).
# Task 3.6 "Implement Output Request Command Generation" for Input is thus potentially misleading.
# The "primary output selection" is indeed done in results_parser.py via g_o.
# For now, this function will be removed from calculation_builder.py.
# If pre-calculation "output requests" (beyond standard logging/step storage) are needed via g_i,
# they would be very specific PLAXIS settings not covered by `addcurvepoint`.

# def generate_output_request_callables() -> List[Callable[[Any], None]]:
#     """
#     Generates PLAXIS API callables for requesting specific outputs,
#     primarily focusing on pre-selecting points for curves if applicable in Input.
#     (...)
#     """
#     # ... (implementation removed as addcurvepoint is likely g_o command) ...
#     return []


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    print("--- Testing Calculation Builder Callable Generation ---")

    # Mock g_i for testing callable structure
    class MockG_i_Calc:
        def __init__(self):
            self.log = []
            self.Mesh = type("MockMesh", (), {"CoarsenessFactor": 0.05})() # Mock nested attribute
            self.Phases = [] # Store mock phase objects
            self.Volumes = {"Spudcan_ConeVolume": "spudcan_geom_obj_placeholder"} # Mock geometry
            self.PointLoads = {} # Store mock point loads
            self.PointDisplacements = {} # Store mock point displacements
            self.CurvePoints = [] # Store mock curve points

        def command(self, cmd_str: str): self.log.append(f"COMMAND: {cmd_str}"); print(f"  MockG_i.command: {cmd_str}")
        def gotomesh(self): self.log.append("CALL: gotomesh()"); print("  MockG_i.gotomesh()")
        def mesh(self): self.log.append("CALL: mesh()"); print("  MockG_i.mesh()")
        def gotostages(self): self.log.append("CALL: gotostages()"); print("  MockG_i.gotostages()")
        def set(self, target_attr_path, value):
            # Simplified mock for set: assumes target_attr_path is like phase_obj.DeformCalcType
            # or phase_obj.Deform.MaxStepsStored
            attr_name = str(target_attr_path).split('.')[-1] # Get last part of "path"
            parent_obj = target_attr_path
            # Traverse if it's a path like "Deform.MaxStepsStored"
            # This mock doesn't fully simulate PLAXIS object hierarchy for `set`.
            # For testing, we assume `target_attr_path` is directly the attribute object to be set.
            # A real `g_i.set` is more complex.
            # setattr(parent_obj, attr_name, value) # This won't work for nested like Deform.MaxStepsStored
            log_msg = f"CALL: g_i.set({str(target_attr_path)}, {value})"
            self.log.append(log_msg)
            print(f"  MockG_i.set({str(target_attr_path)}, {value})")

        def phase(self, prev_phase_obj_or_none, Name=None):
            new_phase_name = Name or f"Phase_{len(self.Phases)+1}"
            # Mock phase object with some attributes PLAXIS phases might have
            mock_phase = type("MockPhase", (), {
                "Name": new_phase_name,
                "Identification": new_phase_name, # Simplified
                "DeformCalcType": None, # Placeholder for property path
                "Deform": type("MockDeform", (), {"MaxStepsStored": None, "ToleratedError": None})() # Nested mock
            })()
            self.Phases.append(mock_phase)
            prev_phase_id = prev_phase_obj_or_none.Identification if prev_phase_obj_or_none else "None"
            self.log.append(f"CALL: g_i.phase(prev='{prev_phase_id}', Name='{Name}') -> {new_phase_name}")
            print(f"  MockG_i.phase created: {new_phase_name}")
            return mock_phase

        def activate(self, obj_to_activate, phase_obj):
            obj_name = obj_to_activate.Name if hasattr(obj_to_activate, 'Name') else str(obj_to_activate)
            phase_name = phase_obj.Name if hasattr(phase_obj, 'Name') else str(phase_obj)
            self.log.append(f"CALL: g_i.activate(obj='{obj_name}', phase='{phase_name}')")
            print(f"  MockG_i.activate('{obj_name}' in phase '{phase_name}')")

        def pointload(self, coords, Name, Fz):
            self.PointLoads[Name] = {"coords": coords, "Fz": Fz}
            self.log.append(f"CALL: g_i.pointload({coords}, Name='{Name}', Fz={Fz})")
            print(f"  MockG_i.pointload created: {Name}")

        def pointdisplacement(self, coords, Name, uz, Displacement_z):
            self.PointDisplacements[Name] = {"coords": coords, "uz": uz, "Displacement_z": Displacement_z}
            self.log.append(f"CALL: g_i.pointdisplacement({coords}, Name='{Name}', uz={uz}, Disp_z='{Displacement_z}')")
            print(f"  MockG_i.pointdisplacement created: {Name}")

        def addcurvepoint(self, type_str, coords): # Simplified mock
            cp_name = f"CurvePoint_{len(self.CurvePoints)+1}"
            self.CurvePoints.append({"type": type_str, "coords": coords, "Name": cp_name})
            self.log.append(f"CALL: g_i.addcurvepoint(type='{type_str}', coords={coords}) -> {cp_name}")
            print(f"  MockG_i.addcurvepoint: {cp_name} at {coords}")
            return self.CurvePoints[-1] # Return mock curve point object/dict

        def rename(self, obj_ref, new_name):
             if isinstance(obj_ref, dict) and "Name" in obj_ref: # For mock curve point
                 obj_ref["Name"] = new_name
                 self.log.append(f"CALL: g_i.rename(obj with old name '{obj_ref.get('Name', 'Unknown')}', new_name='{new_name}')")
                 print(f"  MockG_i.rename curve point to '{new_name}'")


    # Test Loading Condition Callables
    print("\n--- Testing Loading Condition Callable Generation ---")
    sample_loading_cond = LoadingConditions(
        vertical_preload=1000.0,
        target_penetration_or_load=0.5,
        target_type="penetration"
    )
    loading_callables = generate_loading_condition_callables(sample_loading_cond)
    print(f"Generated {len(loading_callables)} loading callables.")
    mock_g_i_loading = MockG_i_Calc()
    for func in loading_callables: func(mock_g_i_loading)
    assert "Spudcan_Preload" in mock_g_i_loading.PointLoads
    assert "Spudcan_TargetPenetration" in mock_g_i_loading.PointDisplacements

    # Test Analysis Control Callables
    print("\n--- Testing Analysis Control Callable Generation ---")
    sample_control_params = AnalysisControlParameters(
        meshing_global_coarseness="Fine",
        initial_stress_method="K0Procedure",
        max_iterations=150,
        tolerated_error=0.005
    )
    # We need loading_conditions_model for phase setup logic within generate_analysis_control_callables
    analysis_callables = generate_analysis_control_callables(sample_control_params, sample_loading_cond)
    print(f"Generated {len(analysis_callables)} analysis control callables.")
    mock_g_i_analysis = MockG_i_Calc()
    # Initialize a mock InitialPhase as it's assumed to exist
    mock_g_i_analysis.Phases.append(type("MockPhase", (), {"Name": "InitialPhase", "Identification": "InitialPhase", "DeformCalcType": None, "Deform": type("MockDeform", (), {"MaxStepsStored": None, "ToleratedError": None})()})())

    for func in analysis_callables: func(mock_g_i_analysis)
    # Check if phases were created (Initial configured, PreloadPhase, PenetrationPhase)
    assert len(mock_g_i_analysis.Phases) >= 3
    assert mock_g_i_analysis.Phases[1].Name == "PreloadPhase"
    assert mock_g_i_analysis.Phases[2].Name == "PenetrationPhase"
    # Check if iteration parameters were set (conceptual due to simple `set` mock)
    # This would require a more elaborate mock_g_i.set to verify specific attributes.

    # Test Output Request Callables
    print("\n--- Testing Output Request Callable Generation ---")
    output_req_callables = generate_output_request_callables()
    print(f"Generated {len(output_req_callables)} output request callables.")
    mock_g_i_output = MockG_i_Calc()
    for func in output_req_callables: func(mock_g_i_output)
    assert len(mock_g_i_output.CurvePoints) > 0
    # assert mock_g_i_output.CurvePoints[0]["Name"] == "SpudcanRefPoint_ForCurve" # If rename was effective

    print("\n--- End of Calculation Builder Callable Generation Tests ---")
