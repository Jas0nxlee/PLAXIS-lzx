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

def generate_loading_condition_callables(loading_model: LoadingConditions) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for defining loading conditions.
    Loads are typically defined as objects first (e.g., PointLoad, PrescribedDisplacement)
    and then activated in specific calculation phases.

    Args:
        loading_model: The LoadingConditions data model instance.

    Returns:
        A list of callable functions for PLAXIS API interaction.

    Assumptions:
    - Load objects (like PointLoad, PrescribedDisplacement) are created at specific points or on geometry.
      This builder assumes a reference point (e.g., (0,0,0) for simplicity) or a named entity
      (e.g., "SpudcanRefPoint") would be used in a real scenario, passed from `ProjectSettings`.
    - Vertical loads/displacements are along the Z-axis. Downwards is negative Z.
    - PLAXIS API provides methods like `g_i.pointload(...)` and `g_i.pointdisplacement(...)`.
    - Names for load objects (e.g., "SpudcanPreload", "SpudcanPenetrationDispl") are assigned for
      later reference during phase activation.
    - Load steps or displacement increments, if specified in `loading_model`, are primarily
      used during phase definition (e.g., setting number of steps, load multipliers) rather
      than direct load object creation.
    """
    callables: List[Callable[[Any], None]] = []
    print(f"Preparing loading condition callables: Preload={loading_model.vertical_preload}, "
          f"Target={loading_model.target_penetration_or_load} ({loading_model.target_type})")

    # Define a reference point for applying loads/displacements.
    # In a real model, this would be a specific node on the spudcan or a reference geometry point.
    # For this builder, using (0,0,0) as a placeholder. This should be configurable.
    load_application_point = (0,0,0)
    # TODO: Make load_application_point configurable, possibly derived from spudcan geometry or a named point.

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
            print(f"  PLAXIS API CALL: Defining PointDisplacement '{displacement_name}' at {load_application_point} with uz={target_displacement_uz}")
            try:
                # Example: g_i.pointdisplacement(coordinates, Name="name", uz=value, Displacement_z="Prescribed")
                # The PLAXIS API for prescribed displacement needs to be verified.
                # It might be `g_i.prescribeddisplacement` or similar.
                # `all.md` suggests `pointdispl <point_obj> "uz" <value> "Displacement_z" "Prescribed"`
                # This implies creating a point object first, then applying pointdispl.
                # For simplicity, if g_i.pointdisplacement exists and takes coords directly:
                g_i.pointdisplacement(load_application_point, Name=displacement_name, uz=target_displacement_uz, Displacement_z="Prescribed")
                # If it requires a point object:
                # ref_point_obj = g_i.point(load_application_point[0], load_application_point[1], load_application_point[2])
                # g_i.pointdisplacement(ref_point_obj, Name=displacement_name, uz=target_displacement_uz, Displacement_z="Prescribed")
                print(f"    PointDisplacement '{displacement_name}' defined.")
            except Exception as e:
                print(f"    ERROR defining PointDisplacement '{displacement_name}': {e}")
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

            # Set global mesh coarseness. The exact API path might be g_i.Mesh.CoarsenessFactor,
            # g_i.MeshOptions.Coarseness, or similar. Using g_i.command for robustness if path is uncertain.
            # Example: g_i.set(g_i.Mesh.ElementDistribution, coarseness_setting) if it takes string.
            # Or: g_i.command(f"set Mesh.CoarsenessFactor {coarseness_factor}")
            # For now, conceptual set:
            if hasattr(g_i, 'Mesh') and hasattr(g_i.Mesh, 'CoarsenessFactor'):
                 g_i.set(g_i.Mesh.CoarsenessFactor, coarseness_factor)
                 print(f"    Set Mesh.CoarsenessFactor to {coarseness_factor} (for '{coarseness_setting}').")
            else:
                 g_i.command(f"coarsenessfactor {coarseness_factor}") # Fallback to generic command
                 print(f"    Attempted to set coarseness factor to {coarseness_factor} via command.")

            # TODO: Add local mesh refinement for spudcan if control_model.meshing_refinement_spudcan is True.
            # This would involve finding the spudcan volume (e.g., "Spudcan_ConeVolume") and applying
            # a refinement factor, e.g., g_i.refinemesh(g_i.Volumes["Spudcan_ConeVolume"], factor=0.5)

            g_i.mesh() # Generate the mesh
            print("    Mesh generation triggered.")

            g_i.gotostages() # Switch back to staged construction mode
            print("    Switched back to staged construction mode.")
        except Exception as e:
            print(f"    ERROR during mesh generation: {e}")
            raise
    callables.append(mesh_generation_callable)

    # --- Phase Definition Callables ---
    # These need to be appended in sequence.

    # Initial Phase
    initial_phase_name = "InitialPhase" # Standard PLAXIS name for the first phase
    def initial_phase_setup_callable(g_i: Any) -> None:
        print(f"  PLAXIS API CALL: Setting up '{initial_phase_name}'.")
        try:
            # The InitialPhase (Phase_1 in CLI) usually exists by default. We configure it.
            # Accessing it might be g_i.Phases[0] or g_i.InitialPhase or g_i.Phases["InitialPhase"]
            # For robustness, assume it's the first phase if accessible by index.
            initial_phase_obj = g_i.Phases[0] if hasattr(g_i, 'Phases') and g_i.Phases else None
            if not initial_phase_obj: # If it cannot be accessed by index, try by common name
                if hasattr(g_i.Phases, initial_phase_name): initial_phase_obj = g_i.Phases[initial_phase_name]

            if not initial_phase_obj:
                print(f"    ERROR: Could not retrieve InitialPhase object from g_i.Phases.")
                # As a fallback, try to create it if it's truly missing (unusual for PLAXIS default)
                # initial_phase_obj = g_i.phase(None, Name=initial_phase_name)
                # For now, assume it exists and raise if not found.
                raise PlxScriptingError(f"Could not find or access the default '{initial_phase_name}'.")

            # Set calculation type for initial stresses (e.g., K0Procedure)
            calc_type = control_model.initial_stress_method or "K0Procedure" # Default
            # Path to DeformCalcType: initial_phase_obj.DeformCalcType or initial_phase_obj.CalculationType
            # `all.md` suggests Phase.DeformCalcType
            g_i.set(initial_phase_obj.DeformCalcType, calc_type)
            print(f"    Set DeformCalcType for '{initial_phase_name}' to '{calc_type}'.")

            # Activate all soil volumes and boreholes for initial state
            # g_i.activateallsoils(initial_phase_obj) - if such a helper exists
            # Or, iterate g_i.Soils and g_i.Boreholes:
            if hasattr(g_i, 'Soils'):
                for soil_vol in g_i.Soils: g_i.activate(soil_vol, initial_phase_obj)
            if hasattr(g_i, 'Boreholes'):
                for bh in g_i.Boreholes: g_i.activate(bh, initial_phase_obj)
            # Water conditions are often tied to borehole heads or a global water level,
            # which should be active in this phase.
            print(f"    Activated soils and boreholes in '{initial_phase_name}'.")
        except Exception as e:
            print(f"    ERROR during '{initial_phase_name}' setup: {e}")
            raise
    callables.append(initial_phase_setup_callable)

    previous_phase_name_for_plaxis_api = initial_phase_name # Used by g_i.phase(prev_phase_obj)

    # Preloading Phase (optional)
    if loading_conditions_model and loading_conditions_model.vertical_preload is not None and loading_conditions_model.vertical_preload != 0:
        preload_phase_name = "PreloadPhase"
        spudcan_geom_name = "Spudcan_ConeVolume" # Assumed name from geometry_builder
        preload_load_name = "Spudcan_Preload"    # Assumed name from loading_condition_callables

        def preload_phase_setup_callable(g_i: Any) -> None:
            print(f"  PLAXIS API CALL: Setting up '{preload_phase_name}'.")
            try:
                prev_phase_obj = g_i.Phases[previous_phase_name_for_plaxis_api] # Get previous phase object
                current_phase_obj = g_i.phase(prev_phase_obj, Name=preload_phase_name)
                print(f"    Phase '{preload_phase_name}' created after '{previous_phase_name_for_plaxis_api}'.")

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
        previous_phase_name_for_plaxis_api = preload_phase_name


    # Penetration Phase (main analysis)
    penetration_phase_name = "PenetrationPhase"
    spudcan_geom_name = "Spudcan_ConeVolume" # Consistent name
    target_disp_name = "Spudcan_TargetPenetration" # From loading_condition_callables

    def penetration_phase_setup_callable(g_i: Any) -> None:
        print(f"  PLAXIS API CALL: Setting up '{penetration_phase_name}'.")
        try:
            prev_phase_obj = g_i.Phases[previous_phase_name_for_plaxis_api]
            current_phase_obj = g_i.phase(prev_phase_obj, Name=penetration_phase_name)
            print(f"    Phase '{penetration_phase_name}' created after '{previous_phase_name_for_plaxis_api}'.")

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

            # Set iteration control parameters (MaxStepsStored, ToleratedError)
            # Path example: current_phase_obj.Deform.MaxStepsStored
            # These attributes might be directly on the phase object or nested.
            # `all.md` suggests Phase.Deform.MaxStepsStored and Phase.Deform.ToleratedError
            if hasattr(current_phase_obj, 'Deform'):
                if hasattr(control_model, 'max_iterations') and control_model.max_iterations is not None:
                    g_i.set(current_phase_obj.Deform.MaxStepsStored, control_model.max_iterations)
                    print(f"    Set Deform.MaxStepsStored to {control_model.max_iterations}.")
                if hasattr(control_model, 'tolerated_error') and control_model.tolerated_error is not None:
                    g_i.set(current_phase_obj.Deform.ToleratedError, control_model.tolerated_error)
                    print(f"    Set Deform.ToleratedError to {control_model.tolerated_error}.")
            else:
                print(f"    Warning: Could not access Deform attribute on phase '{penetration_phase_name}' to set iteration parameters.")

            print(f"    '{penetration_phase_name}' configured.")
        except Exception as e:
            print(f"    ERROR during '{penetration_phase_name}' setup: {e}")
            raise
    callables.append(penetration_phase_setup_callable)

    return callables

# --- Output Request Configuration ---

def generate_output_request_callables() -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for requesting specific outputs,
    primarily focusing on pre-selecting points for curves if applicable in Input.

    Returns:
        A list of callable functions for PLAXIS API interaction.

    Assumptions:
    - `g_i.addcurvepoint("Node", coordinates)` or similar API is available in the Input environment
      to pre-select nodes for curve generation later in Output. PLAXIS behavior for `addcurvepoint`
      in Input vs. Output needs verification. `all.md` lists it under Output commands.
    - If `addcurvepoint` is purely an Output command, these callables might be conceptual placeholders
      or would need to be executed on `g_o` after calculation.
    - For this implementation, we assume it can be called on `g_i` to mark points.
    - A reference point (e.g., (0,0,0) representing spudcan tip or reference) is used for curve selection.
      This should ideally be a named point or coordinates derived from spudcan geometry.
    """
    callables: List[Callable[[Any], None]] = []
    print("Preparing output request callables (e.g., for curve point selection).")

    # Define a reference point for curve data, e.g., spudcan tip or center.
    # TODO: Make this configurable or derive from spudcan geometry.
    spudcan_curve_ref_point_coords = (0,0,0)
    # Name for the curve point in PLAXIS for later identification.
    curve_point_name = "SpudcanRefPoint_ForCurve"

    def select_curve_points_callable(g_i: Any) -> None:
        print(f"  PLAXIS API CALL: Selecting node at/near {spudcan_curve_ref_point_coords} for curve generation.")
        try:
            # The `addcurvepoint` command (from all.md, Output section) syntax:
            # `addcurvepoint <S_type> [plx_obj] <(x y z)> [(dirx diry dirz)]` where S_type is "Node" or "Stresspoint".
            # If this command is available and effective on `g_i` (Input server):
            # cp = g_i.addcurvepoint("Node", spudcan_curve_ref_point_coords) # Returns curve point object
            # g_i.rename(cp, curve_point_name) # Rename for easier access later

            # Using g_i.command as a placeholder if direct API is uncertain or for illustration:
            g_i.command(f'addcurvepoint "Node" ({spudcan_curve_ref_point_coords[0]} {spudcan_curve_ref_point_coords[1]} {spudcan_curve_ref_point_coords[2]})')
            # Renaming the last created curve point (assuming CurvePoints[-1] is valid syntax for g_i.command context)
            # This is highly dependent on PLAXIS supporting such access.
            # g_i.command(f'set CurvePoints[-1].Name "{curve_point_name}"') # Conceptual

            print(f"    Requested curve point selection at {spudcan_curve_ref_point_coords} (named conceptually '{curve_point_name}'). "
                  "Actual availability/naming of this point for `getcurveresults` depends on PLAXIS API specifics.")
        except Exception as e:
            print(f"    ERROR during curve point selection: {e}")
            # This might not be a fatal error for the overall process if curve generation is optional.
            # For now, let it pass and log.
            pass # Or raise if pre-selection is critical

    callables.append(select_curve_points_callable)

    # Note: Most detailed result extraction (final penetration, peak resistance, full curve data)
    # is typically performed using the PLAXIS Output environment (g_o) after the calculation is complete.
    # This function primarily handles pre-calculation setup if PLAXIS allows/requires it.

    if not callables:
        print("No specific output request callables generated (beyond default PLAXIS outputs).")
    return callables


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
