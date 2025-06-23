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
    print(f"STUB: Generating loading commands: Preload={loading_model.vertical_preload}, Target={loading_model.target_penetration_or_load} ({loading_model.target_type})")

    commands.append(f"# --- Loading Conditions Definition ---")
    commands.append(f"echo 'Defining loading conditions...'")

    if loading_model.vertical_preload is not None:
        # Example: Apply a point load or surface load representing preload
        # commands.append(f"APPLY_SURFACE_LOAD surface_name='SpudcanBase' load_value={loading_model.vertical_preload} direction='Z'")
        commands.append(f"PLAXIS_API_CALL apply_preload type='surface' value={loading_model.vertical_preload}")

    if loading_model.target_penetration_or_load is not None and loading_model.target_type:
        # This would typically be part of a calculation phase definition
        # e.g., a prescribed displacement or a load-controlled step
        # commands.append(f"DEFINE_TARGET type='{loading_model.target_type}' value={loading_model.target_penetration_or_load}")
        commands.append(
            f"PLAXIS_API_CALL define_analysis_target "
            f"type='{loading_model.target_type}' "
            f"value={loading_model.target_penetration_or_load}"
        )

    # Add commands for load steps or displacement increments if defined in loading_model

    commands.append(f"echo 'Loading conditions definition complete (stub).'")

    if not commands:
         commands.append("# STUB: No loading commands generated.")
    return commands

def generate_analysis_control_commands(control_model: AnalysisControlParameters) -> List[str]:
    """
    Generates PLAXIS commands for analysis control (meshing, phases, initial conditions).
    Placeholder commands.

    Args:
        control_model: The AnalysisControlParameters data model.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"STUB: Generating analysis control commands: Mesh={control_model.meshing_global_coarseness}, InitStress={control_model.initial_stress_method}")

    commands.append(f"# --- Analysis Control Definition ---")
    commands.append(f"echo 'Defining analysis control parameters...'")

    # 1. Initial Conditions (K0 procedure)
    # commands.append(f"SET_INITIAL_CONDITIONS method='{control_model.initial_stress_method or 'K0Procedure'}'")
    commands.append(f"PLAXIS_API_CALL set_initial_conditions method='{control_model.initial_stress_method or 'K0Procedure'}'")

    # 2. Meshing
    # commands.append(f"GENERATE_MESH coarseness='{control_model.meshing_global_coarseness or 'Medium'}'")
    # if control_model.meshing_refinement_spudcan:
    #    commands.append(f"REFINE_MESH_AROUND_SPUDCAN factor='{control_model.meshing_refinement_spudcan}'")
    commands.append(f"PLAXIS_API_CALL generate_mesh coarseness='{control_model.meshing_global_coarseness or 'Medium'}'")

    # 3. Calculation Phases (Simplified - actual phase setup is complex)
    # This section would be much more detailed in a real implementation, defining each phase,
    # its calculation type, reset displacements, active loads/BCs, etc.
    # The PRD (4.1.2.4.3) mentions "Selection of calculation phases as per the PDF".
    # This implies the sequence of phases is somewhat predefined by the workflow.

    # Example: Initial Phase (after initial conditions and meshing)
    # commands.append("DEFINE_PHASE name='InitialPhase' type='KoStress' ...")
    commands.append("PLAXIS_API_CALL define_phase phase_id='InitialPhase' type='InitialStresses' description='Initial geostatic stress state'")

    # Example: Spudcan Installation/Penetration Phase
    # This phase would activate the spudcan structure and apply loads or prescribed displacements.
    # commands.append("DEFINE_PHASE name='PenetrationPhase' type='Plastic' ...")
    # commands.append("ACTIVATE_SPUDCAN_LOADS_IN_PHASE phase_name='PenetrationPhase'")
    commands.append("PLAXIS_API_CALL define_phase phase_id='PenetrationPhase' type='Consolidation_or_Plastic' description='Spudcan penetration analysis'")
    # Additional commands here to activate spudcan elements, apply loads for this phase, etc.

    # Tolerated error / max iterations - often set globally or per phase
    # if control_model.tolerated_error:
    #    commands.append(f"SET_CALCULATION_PARAMETER tolerated_error={control_model.tolerated_error}")

    commands.append(f"echo 'Analysis control definition complete (stub).'")

    if not commands:
        commands.append("# STUB: No analysis control commands generated.")
    return commands

def generate_output_request_commands() -> List[str]:
    """
    Generates PLAXIS commands for requesting specific outputs.
    Placeholder commands.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"STUB: Generating output request commands.")

    commands.append(f"# --- Output Request Definition ---")
    commands.append(f"echo 'Defining output requests...'")

    # Example: Request load-displacement curve for a specific point on the spudcan
    # commands.append("SELECT_POINT spudcan_center_top x=0 y=0 z=spudcan_top_z")
    # commands.append("CREATE_CURVE point=spudcan_center_top x_axis=Uz y_axis=Fz")
    # commands.append("EXPORT_CURVE curve_name='LoadPenCurve' filename='load_penetration_data.txt'")
    commands.append("PLAXIS_API_CALL select_result_point point_name='SpudcanRefPoint' coordinates='0,0,Z_ref'")
    commands.append("PLAXIS_API_CALL request_curve point='SpudcanRefPoint' x_param='Uz' y_param='SumFz' output_file='load_pen_curve.txt'")

    # Request other specific results as needed by PRD 4.1.6 (Results Display)
    # e.g., final penetration depth, peak resistance, soil pressures, deformation contours (if exportable)
    commands.append("PLAXIS_API_CALL request_final_values parameters='Uz_SpudcanRefPoint, Max_SumFz_SpudcanRefPoint'")

    commands.append(f"echo 'Output request definition complete (stub).'")

    if not commands:
        commands.append("# STUB: No output request commands generated.")
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
