"""
Generates PLAXIS commands or API calls for creating spudcan geometry.
PRD Ref: Task 3.2
"""

from ..models import SpudcanGeometry # Relative import from parent package
from typing import List

def generate_spudcan_commands(spudcan_model: SpudcanGeometry) -> List[str]:
    """
    Generates a list of PLAXIS commands to create the spudcan geometry.
    These are placeholder commands. Actual commands will depend on PLAXIS API/scripting syntax.

    Args:
        spudcan_model: The SpudcanGeometry data model.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"Generating spudcan geometry commands for diameter {spudcan_model.diameter}, cone_angle {spudcan_model.height_cone_angle}")

    if spudcan_model.diameter is None or spudcan_model.height_cone_angle is None:
        print("Warning: Spudcan diameter or cone angle is not defined. Cannot generate full geometry commands.")
        # Depending on strictness, could return empty or raise error.
        # For now, allow partial if some info exists, but a real spudcan needs all key dims.
        if spudcan_model.diameter is None:
             commands.append("# ERROR: Spudcan diameter not provided.")
        if spudcan_model.height_cone_angle is None: # Assuming this is cone angle
             commands.append("# ERROR: Spudcan cone angle not provided.")
        return commands

    commands.append(f"# --- Spudcan Geometry Definition ---")
    commands.append(f"echo 'Defining spudcan geometry...'")

    # Assuming the spudcan is a cone for simplicity, created at origin (0,0,0) with its base on XY plane, pointing downwards (-Z)
    # The actual spudcan geometry might be more complex (e.g., flat bottom, specific height vs. just angle)
    # and might require a combination of commands (e.g., circle + cone, or a dedicated footing command if available).
    # The PRD (4.1.2.1) mentions diameter and height/cone angle. Let's assume 'height_cone_angle' is the cone's angle with vertical.
    # A typical cone command might take base radius, height, and orientation.
    # If PLAXIS has a `cone` command like `cone <BaseRadius> <Height> [TopCircleBase] [Coords]` (from all.md example for general cone)
    # we need to calculate height from diameter and angle, or assume a different interpretation.

    # Let's assume spudcan_model.height_cone_angle is the *half* apex angle of the cone (angle from axis to side).
    # And that the spudcan tip points downwards.
    # If the spudcan has a flat circular top of a certain small diameter, or if it's a perfect cone.
    # For a perfect cone of a given diameter (base) and cone angle (alpha from axis to side),
    # Height = (Diameter/2) / tan(alpha)
    # We'll use a generic command structure based on `all.md` for now.
    # The command `cone <BaseRadius> <Height> [TopCircleBase] [Coords]` seems relevant.
    # Let's assume a perfect cone (TopCircleBase = 0).
    # And the spudcan is placed with its base at z=0, tip pointing in -z.
    # Coords would be the center of the base. Let's assume (0,0,0) for now.
    # The `cone` command in `all.md` seems to build upwards by default. We may need to adjust or use `move` / `rotate`.

    # Placeholder for using PLAXIS Python API (g_i object)
    # if g_i_object_is_available:
    #   try:
    #     # Example of potential API calls (highly speculative based on common patterns)
    #     # This assumes g_i is the global PLAXIS input object
    #     # spudcan_obj = g_i.footing() # Hypothetical high-level footing tool
    #     # spudcan_obj.set("type", "conical")
    #     # spudcan_obj.set("diameter", spudcan_model.diameter)
    #     # spudcan_obj.set("cone_angle", spudcan_model.height_cone_angle) # Or height
    #     # spudcan_obj.set("position", (0,0,0)) # Base center
    #     # commands.append(f"# API: Created spudcan {spudcan_obj.name}")
    #
    #     # Alternative: building from primitives if no direct spudcan tool
    #     # radius = spudcan_model.diameter / 2.0
    #     # cone_angle_rad = math.radians(spudcan_model.height_cone_angle) # Assuming height_cone_angle is half apex angle
    #     # height = radius / math.tan(cone_angle_rad) if math.tan(cone_angle_rad) > 1e-6 else some_large_number
    #     #
    #     # # Create cone (assuming base at z=0, tip at z=-height)
    #     # # The PLAXIS 'cone' command from all.md seems to point upwards.
    #     # # cone <BaseRadius> <Height> [TopRadius] [(x y z_base_center)] [(dirx diry dirz_axis)]
    #     # commands.append(f"cone {radius} {height} 0 (0 0 0) (0 0 -1)") # Tip downwards
    #     # commands.append(f"rename Volumes[-1] SpudcanVolume")
    #     # This is a simplified interpretation. Real spudcans might have flat tops or specific aspect ratios.
    #     # The "基于PLAXIS3D的海洋桩靴入泥深度设计流程.pdf" would provide the exact geometry.
    #     # For now, using a generic placeholder.
    #     commands.append(f"_g.echo(\"--- Spudcan Geometry --- Expecting PLAXIS API calls here ---\")") # For Python API style
    #     commands.append(f"s_i.spudcan(diameter={spudcan_model.diameter}, cone_angle={spudcan_model.height_cone_angle}, name='Spudcan') # Hypothetical API")
    #
    #   except Exception as e:
    #     commands.append(f"# ERROR in API call for spudcan: {e}")
    # else: # Fallback to CLI style commands based on all.md

    radius = spudcan_model.diameter / 2.0
    # Assuming height_cone_angle is the angle from the vertical axis to the cone surface (degrees)
    # If it's the full apex angle, then divide by 2.
    # Height H = R / tan(angle_from_vertical_to_surface)
    # For now, we don't have height directly, only diameter and angle.
    # The reference PDF "基于PLAXIS3D的海洋桩靴入泥深度设计流程.pdf" would specify how these relate.
    # Let's assume for CLI we use a placeholder for a spudcan creation command or a sequence.
    # The `cone` command: cone <BaseRadius> <Height> [TopCircleBase] [Coords]
    # To use this, we need Height. If the spudcan is purely conical to a point, height = radius / tan(cone_angle_rad).
    # This is a complex part without direct PLAXIS experience or clearer command examples for this specific shape.

    commands.append(f"# Placeholder for spudcan geometry creation. Details depend on exact PLAXIS commands/API.")
    commands.append(f"# Assumed spudcan is a conical shape created at origin.")
    commands.append(f"# Diameter: {spudcan_model.diameter}, Cone Angle: {spudcan_model.height_cone_angle}")
    commands.append(f"echo 'PLAXIS_COMMAND_PLACEHOLDER: Create spudcan geometry (e.g., using 'cone' or custom footing tool)'")
    commands.append(f"echo '  parameters: diameter={spudcan_model.diameter}, cone_angle={spudcan_model.height_cone_angle}'")

    commands.append(f"echo 'Spudcan geometry definition commands generated (stubs needing PLAXIS specifics).'")

    return commands

if __name__ == '__main__':
    print("--- Testing Spudcan Geometry Command Generation ---")
    sample_spudcan = SpudcanGeometry(diameter=6.0, height_cone_angle=30.0)
    cmds = generate_spudcan_commands(sample_spudcan)
    print(f"Generated {len(cmds)} commands:")
    for cmd in cmds:
        print(cmd)

    print("\nTest with undefined diameter:")
    sample_spudcan_no_dia = SpudcanGeometry(height_cone_angle=30.0)
    cmds_no_dia = generate_spudcan_commands(sample_spudcan_no_dia)
    print(f"Generated {len(cmds_no_dia)} commands for spudcan with no diameter:")
    for cmd in cmds_no_dia:
        print(cmd)
    print("--- End of Geometry Builder Tests ---")
