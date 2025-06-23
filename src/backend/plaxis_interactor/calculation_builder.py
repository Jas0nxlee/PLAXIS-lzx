"""
Generates PLAXIS commands or API calls for defining loading conditions,
analysis control (meshing, phases), and output requests.
PRD Ref: Tasks 3.4, 3.5, 3.6
"""

from ..models import LoadingConditions, AnalysisControlParameters # Relative import
from typing import List

def generate_loading_commands(loading_model: LoadingConditions) -> List[str]:
    """
    Generates PLAXIS commands for defining loading conditions.
    Placeholder commands.

    Args:
        loading_model: The LoadingConditions data model.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"Generating loading commands: Preload={loading_model.vertical_preload}, Target={loading_model.target_penetration_or_load} ({loading_model.target_type})")

    commands.append(f"# --- Loading Conditions Definition ---")
    commands.append(f"echo 'Defining loading conditions (Note: loads are typically applied/activated in specific phases)...'")

    # PRD 4.1.2.3.1: Vertical pre-load applied to the spudcan.
    # This load needs to be associated with a geometric entity representing the spudcan.
    # Let's assume a surface named 'Spudcan_Base_Surface' exists, or a point 'Spudcan_Ref_Point'.
    # The `surfload` or `pointload` commands from `all.md` are relevant.
    # Example: surfload <surface_obj> "sigz" <value> (for uniform vertical load)
    # Example: pointload <point_obj> "Fz" <value>
    # These definitions create load objects. Activation happens per phase.

    if loading_model.vertical_preload is not None:
        # For a spudcan, preload is likely a distributed load or a force at a reference point.
        # Assuming it's a force applied downwards (negative Z) at a conceptual 'Spudcan_Ref_Point'.
        # The point itself would be defined in geometry_builder. For now, assume it's named.
        # We define the load here; it will be activated in a calculation phase.
        commands.append(f"# Define Preload (e.g., as a point load at spudcan reference point)")
        commands.append(f"pointload (0 0 0) \"Name\" \"SpudcanPreload\" \"Fz\" {-abs(loading_model.vertical_preload)}")
        # For API: g_i.pointload((0,0,0), Name="SpudcanPreload", Fz=-abs(loading_model.vertical_preload))
        commands.append(f"echo 'Defined SpudcanPreload object with Fz={-abs(loading_model.vertical_preload)} (stub for association with actual spudcan geometry).'")

    # PRD 4.1.2.3.2: Target penetration depth or target load for the analysis.
    # This is not a command itself but a control parameter for a calculation phase,
    # often related to prescribed displacements or load control steps.
    # It will be used when defining calculation phases in generate_analysis_control_commands.
    if loading_model.target_penetration_or_load is not None and loading_model.target_type:
        commands.append(f"# INFO: Target for analysis: {loading_model.target_type} = {loading_model.target_penetration_or_load}")
        commands.append(f"# This target will be used in calculation phase setup.")
        # Example: If target is penetration, a prescribed displacement might be defined.
        # pointdispl <point_obj> "uz" <value> "Displacement_z" "Prescribed"
        if loading_model.target_type == "penetration":
            commands.append(f"# Define Prescribed Displacement for penetration target (e.g., at Spudcan_Ref_Point)")
            # Assuming penetration is downwards (-Z)
            commands.append(f"pointdispl (0 0 0) \"Name\" \"SpudcanPenetrationDispl\" \"uz\" {-abs(loading_model.target_penetration_or_load)} \"Displacement_z\" \"Prescribed\"")
            commands.append(f"echo 'Defined SpudcanPenetrationDispl object for target penetration.'")


    # PRD 4.1.2.3.3: Definition of load steps or displacement increments.
    # This is also typically part of phase control (e.g., MaxStepsStored, or specific loading type parameters).
    # It's not a direct geometry/load definition command but influences how a phase runs.
    # For now, just an echo, actual use in phase definition.
    # if loading_model.load_steps_or_displacement_increments:
    #    commands.append(f"# INFO: Load/Displacement increments defined: {loading_model.load_steps_or_displacement_increments}")
    #    commands.append(f"# This will be used in calculation phase setup (e.g. number of steps, loading type).")

    commands.append(f"echo 'Loading conditions definition commands generated (actual application in phases).'")
    return commands

def generate_analysis_control_commands(control_model: AnalysisControlParameters, loading_conditions_model: Optional[LoadingConditions] = None) -> List[str]:
    """
    Generates PLAXIS commands for analysis control (meshing, phases, initial conditions).
    Placeholder commands.

    Args:
        control_model: The AnalysisControlParameters data model.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"Generating analysis control commands: Mesh={control_model.meshing_global_coarseness}, InitStressMethod={control_model.initial_stress_method}")

    commands.append(f"# --- Analysis Control Definition (Meshing & Phases) ---")
    commands.append(f"echo 'Defining analysis control parameters...'")

    # 1. Meshing (PRD 4.1.2.4.1)
    # From all.md: mesh <coarseness_factor> or mesh "Coarseness" <value> ...
    # The `mesh` command itself triggers mesh generation. Mesh parameters are often properties of a global MeshOptions object or project settings.
    # For now, we'll assume these are set on a global object before calling `mesh`.
    # Example: set g_i.Mesh.CoarsenessFactor <value>
    #          mesh
    mesh_coarseness_map = {
        "VeryCoarse": 0.2, "Coarse": 0.1, "Medium": 0.05,
        "Fine": 0.025, "VeryFine": 0.01 # Example mapping to numerical factors
    }
    coarseness_factor = mesh_coarseness_map.get(control_model.meshing_global_coarseness or "Medium", 0.05)
    commands.append(f"# Set global mesh parameters (conceptual - actual object path may vary)")
    commands.append(f"set MeshOptions.Coarseness {coarseness_factor} # Or ElementRelativeSize")
    # if control_model.meshing_refinement_spudcan: # This would involve local refinement commands
    #    commands.append(f"refine SpudcanVolume <factor_value>") # Placeholder
    commands.append(f"echo 'Meshing parameters set (conceptual: CoarsenessFactor={coarseness_factor}).'")
    commands.append(f"gotomesh") # Switch to mesh mode
    commands.append(f"mesh")    # Generate mesh
    commands.append(f"echo 'Mesh generation command issued.'")
    commands.append(f"gotostages") # Switch back to staged construction

    # 2. Calculation Phases (PRD 4.1.2.4.3)
    # This is where the workflow from "基于PLAXIS3D的海洋桩靴入泥深度设计流程.pdf" is critical.
    # We'll define a typical sequence: InitialPhase, PreloadPhase (if any), PenetrationPhase.

    # Initial Phase (PRD 4.1.2.4.2 for K0 procedure)
    # From all.md: phase <existing_phase_obj> -> creates new phase after existing
    # InitialPhase is usually Phase[0] or g_i.InitialPhase
    # Properties set via: set <Phase_obj>.DeformCalcType "K0 procedure"
    commands.append(f"# --- Initial Phase Definition ---")
    commands.append(f"echo 'Defining InitialPhase...'")
    commands.append(f"set InitialPhase.DeformCalcType \"{control_model.initial_stress_method or 'K0 procedure'}\"")
    # Activate initial soil geometry, set water conditions
    commands.append(f"activate Soils InitialPhase") # Activate all soil volumes
    commands.append(f"activate Boreholes InitialPhase") # And boreholes for water
    # Water conditions are typically set via borehole head or global water level in this phase.
    # This is handled by set <borehole_obj>.Head in soil_builder or setglobalwaterlevel.
    commands.append(f"echo 'InitialPhase settings configured.'")

    # Preloading Phase (if applicable)
    if loading_conditions_model and loading_conditions_model.vertical_preload is not None:
        commands.append(f"# --- Preloading Phase Definition ---")
        commands.append(f"phase InitialPhase \"Name\" \"PreloadPhase\"") # Create phase after InitialPhase
        preload_phase_name = "PreloadPhase" # Or get from Phases[-1].Name
        commands.append(f"echo 'Defining {preload_phase_name}...'")
        commands.append(f"set {preload_phase_name}.DeformCalcType \"Plastic\"") # Common for loading
        commands.append(f"activate SpudcanVolume {preload_phase_name}") # Activate spudcan geometry
        commands.append(f"activate SpudcanPreload {preload_phase_name}") # Activate the predefined preload
        commands.append(f"echo '{preload_phase_name} configured.'")
        last_defined_phase = preload_phase_name
    else:
        last_defined_phase = "InitialPhase"

    # Penetration Phase
    commands.append(f"# --- Penetration Phase Definition ---")
    commands.append(f"phase {last_defined_phase} \"Name\" \"PenetrationPhase\"")
    penetration_phase_name = "PenetrationPhase" # Or get from Phases[-1].Name
    commands.append(f"echo 'Defining {penetration_phase_name}...'")
    commands.append(f"set {penetration_phase_name}.DeformCalcType \"Plastic\"") # Or Consolidation if time-dependent

    # Activate spudcan if not already active (e.g. if no preload phase)
    commands.append(f"activate SpudcanVolume {penetration_phase_name}")

    if loading_conditions_model and \
       loading_conditions_model.target_type == "penetration" and \
       loading_conditions_model.target_penetration_or_load is not None:
        # Activate the prescribed displacement defined in loading_commands
        commands.append(f"activate SpudcanPenetrationDispl {penetration_phase_name}")
        commands.append(f"echo 'Activated SpudcanPenetrationDispl for penetration target.'")
    elif loading_conditions_model and \
         loading_conditions_model.target_type == "load" and \
         loading_conditions_model.target_penetration_or_load is not None:
        # Define and activate a load for this phase (if different from preload)
        # For simplicity, assume if there was preload, this is an additional load or the main load.
        # If no preload, this is the main load.
        if loading_conditions_model.vertical_preload is None: # If no preload was defined, use this as main load
             commands.append(f"pointload (0 0 0) \"Name\" \"SpudcanMainLoad\" \"Fz\" {-abs(loading_conditions_model.target_penetration_or_load)}")
             commands.append(f"activate SpudcanMainLoad {penetration_phase_name}")
        else: # This implies an additional target load or just a target for a load already defined.
             commands.append(f"# INFO: Target load {loading_conditions_model.target_penetration_or_load} to be achieved in this phase.")
             # Logic to increment existing load or apply new load to reach target would be here.
             # For now, assume preload was the only load defined and this phase runs it.

    # Iteration control parameters (PRD 4.1.2.4.4)
    # Example: set <Phase_obj>.Deform.MaxSteps <value> (from all.md, Phase.Deform.MaxSteps)
    # if control_model.max_iterations: # This is MaxIterations in PRD, PLAXIS might call it MaxSteps for the phase
    #    commands.append(f"set {penetration_phase_name}.Deform.MaxStepsStored {control_model.max_iterations}") # Or MaxSteps
    # if control_model.tolerated_error: # Example: set Phase_1.Deform.ToleratedError 0.01
    #    commands.append(f"set {penetration_phase_name}.Deform.ToleratedError {control_model.tolerated_error}")
    # if control_model.max_iterations: # Example: set Phase_1.Deform.MaxStepsStored 100 (or MaxIterations if it's a direct param)
    #    commands.append(f"set {penetration_phase_name}.Deform.MaxStepsStored {control_model.max_iterations}")


    commands.append(f"echo '{penetration_phase_name} configured.'")
    commands.append(f"echo 'Analysis control and phase definitions generated.'")
    return commands

def generate_output_request_commands() -> List[str]:
    """
    Generates PLAXIS commands for requesting specific outputs.
    Placeholder commands.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"Generating output request commands.")

    commands.append(f"# --- Output Request Definition ---")
    commands.append(f"echo 'Defining output requests (Note: these are typically configured before calculation or in Output module after)...'")

    # Output requests are often set up *before* calculation or are part of the post-processing in the Output module.
    # The PRD (4.1.6) specifies what results are needed: Load-Penetration Curve, final penetration, peak resistance.
    # The `all.md` document has an "Output commands reference" section.
    # Commands like `addcurvepoint` (to preselect nodes for curves) and then `getcurveresults` or `getsingleresult` are used in Output.
    # If using the PLAXIS Python API with the Output environment (g_o), these are calls made after calculation.
    # If certain outputs can be "requested" from the Input environment to be generated by the kernel, the syntax would differ.

    # For now, these commands will be more like notes on what to select/extract in the Output environment,
    # or conceptual pre-calculation requests if such exist.

    # 1. Load-Penetration Curve:
    #    - Requires selecting a reference point on the spudcan (e.g., center top or a specific node).
    #    - Plotting Vertical Displacement (Uz) vs. Sum Vertical Forces (SumFz) for that point.
    #    - `all.md` mentions `addcurvepoint "Node" (x y z)` for preselecting nodes in Input/Output.
    #    - And `getcurveresults <Node> <Phase> ResultTypes.Soil.Uz` (example).
    #    - `getcurveresults <Node> <Phase> ResultTypes.PointLoad.Fz` (if load is a PointLoad).
    #    - Or for a rigid body: `ResultTypes.RigidBody.Fz` and `ResultTypes.RigidBody.Uz`.

    commands.append(f"# For Load-Penetration Curve (typically configured in Output or via preselected points):")
    commands.append(f"# Ensure a reference point on the spudcan is defined/selected, e.g., 'SpudcanRefPoint'.")
    commands.append(f"addcurvepoint \"Node\" (0 0 0) \"Name\" \"SpudcanRefPointForCurve\" # Example: select node at origin, assuming it's spudcan ref")
    commands.append(f"# In Output, after calculation, a curve would be generated using this point for displacement (e.g., Uz) vs. applied load/reaction.")
    commands.append(f"echo 'Defined SpudcanRefPointForCurve for load-penetration curve generation in Output.'")

    # 2. Final Penetration Depth & Peak Resistance:
    #    - These are typically specific values from the end of the analysis or from the curve data.
    #    - `getsingleresult` or processing `getcurveresults` data would yield these in Output.
    commands.append(f"# Final penetration depth and peak resistance are typically post-processed from results:")
    commands.append(f"# e.g., from the last point of the load-penetration curve or specific result queries in Output.")
    commands.append(f"# Example (conceptual for Output API):")
    commands.append(f"# final_pen = g_o.getsingleresult(g_o.Phases['PenetrationPhase'], g_o.ResultTypes.Soil.Uz, SpudcanRefPointForCurve)")
    commands.append(f"# peak_res = max(load_values_from_curve_data)")

    # If PLAXIS Input allows explicit requests for certain summary outputs to be written to files:
    # (This is speculative as `all.md` mainly shows Output commands for results)
    # commands.append(f"EXPORT_RESULT Point='SpudcanRefPoint' Parameter='Uz' Phase='PenetrationPhase' Step='Last' File='final_penetration.txt'")
    # commands.append(f"EXPORT_CURVE Name='LoadPenCurve' File='load_pen_data.txt'")

    commands.append(f"echo 'Output request definitions are primarily for post-processing in PLAXIS Output.'")
    commands.append(f"echo 'Key points for curves should be pre-selected (e.g., using addcurvepoint).'")

    return commands

if __name__ == '__main__':
    print("--- Testing Loading Command Generation ---")
    sample_loading = LoadingConditions(
        vertical_preload=1000.0,
        target_penetration_or_load=5.0,
        target_type="penetration"
    )
    load_cmds = generate_loading_commands(sample_loading)
    print(f"Generated {len(load_cmds)} loading commands:")
    for cmd in load_cmds:
        print(cmd)

    print("\n--- Testing Analysis Control Command Generation ---")
    sample_control = AnalysisControlParameters(
        meshing_global_coarseness="Fine",
        initial_stress_method="K0Procedure"
    )
    ctrl_cmds = generate_analysis_control_commands(sample_control)
    print(f"Generated {len(ctrl_cmds)} analysis control commands:")
    for cmd in ctrl_cmds:
        print(cmd)

    print("\n--- Testing Output Request Command Generation ---")
    output_cmds = generate_output_request_commands()
    print(f"Generated {len(output_cmds)} output request commands:")
    for cmd in output_cmds:
        print(cmd)

    print("--- End of Calculation Builder Tests ---")
