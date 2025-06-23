"""
Generates PLAXIS commands or API calls for defining soil stratigraphy and material properties.
PRD Ref: Task 3.3
"""

from ..models import SoilLayer, MaterialProperties # Relative import
from typing import List, Optional

def generate_material_commands(material_model: MaterialProperties) -> List[str]:
    """
    Generates PLAXIS commands for defining a single soil material.
    Placeholder commands.

    Args:
        material_model: The MaterialProperties data model.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    mat_name = f"{material_model.model_name or 'DefaultMaterial'}_{material_model.cohesion or 0}_{material_model.friction_angle or 0}"
    mat_name = "".join(c if c.isalnum() or c in ['_'] else '' for c in mat_name) # Sanitize name

    print(f"STUB: Generating material commands for '{mat_name}' (Model: {material_model.model_name})")

    commands.append(f"# --- Material Definition: {mat_name} ---")
    commands.append(f"echo 'Defining material: {mat_name}'")

    # Example: _defMaterial "Sand_MC" "Mohr-Coulomb" MAT_ISOTROPIC ...
    # Actual command syntax will vary greatly.
    command_params = [
        f"material_name='{mat_name}'",
        f"soil_model='{material_model.model_name or 'MohrCoulomb'}'" # Default if not specified
    ]
    if material_model.unit_weight is not None:
        command_params.append(f"unit_weight={material_model.unit_weight}")
    if material_model.cohesion is not None:
        command_params.append(f"cohesion={material_model.cohesion}")
    if material_model.friction_angle is not None:
        command_params.append(f"friction_angle={material_model.friction_angle}")
    if material_model.youngs_modulus is not None:
        command_params.append(f"youngs_modulus={material_model.youngs_modulus}")
    if material_model.poissons_ratio is not None:
        command_params.append(f"poissons_ratio={material_model.poissons_ratio}")

    # Add other parameters based on soil_model type if they were in a dict
    # if material_model.other_params:
    #     for key, value in material_model.other_params.items():
    #         command_params.append(f"{key}={value}")

    commands.append(f"PLAXIS_API_CALL create_soil_material {' '.join(command_params)}")
    commands.append(f"echo 'Material {mat_name} definition complete (stub).'")

    if not commands:
        commands.append(f"# STUB: No material commands generated for {mat_name}.")
    return commands

def generate_soil_stratigraphy_commands(
    soil_layers: List[SoilLayer],
    water_table_depth: Optional[float]
) -> List[str]:
    """
    Generates PLAXIS commands for defining soil stratigraphy (boreholes, soil layers).
    Placeholder commands.

    Args:
        soil_layers: A list of SoilLayer data models.
        water_table_depth: Depth of the water table from the surface (e.g., z=0).

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"STUB: Generating soil stratigraphy commands for {len(soil_layers)} layers.")

    commands.append(f"# --- Soil Stratigraphy Definition ---")
    commands.append(f"echo 'Defining soil stratigraphy...'")

    # Example: Create a borehole at (0,0)
    # commands.append("CREATE_BOREHOLE bh1 x=0 y=0")
    commands.append("PLAXIS_API_CALL create_borehole name='BH1' x=0 y=0")

    current_depth_or_elevation = 0.0 # Assuming ground surface is at z=0 and layers go downwards

    for i, layer in enumerate(soil_layers):
        layer_name = layer.name or f"Layer{i+1}"
        # Material name needs to be consistent with how it was defined in generate_material_commands
        material_obj = layer.material
        mat_name = f"{material_obj.model_name or 'DefaultMaterial'}_{material_obj.cohesion or 0}_{material_obj.friction_angle or 0}"
        mat_name = "".join(c if c.isalnum() or c in ['_'] else '' for c in mat_name)


        if layer.thickness is None:
            print(f"Warning: Layer '{layer_name}' has no thickness. Skipping.")
            continue

        # Example: Add soil layer to borehole
        # commands.append(f"ADD_SOIL_LAYER borehole=bh1 top_elev={current_depth_or_elevation} thickness={layer.thickness} material='{mat_name}' name='{layer_name}'")

        # Assuming top_of_layer is defined from z=0 downwards.
        # If using elevations, this logic would change.
        bottom_of_layer = current_depth_or_elevation - layer.thickness

        commands.append(
            f"PLAXIS_API_CALL add_soil_to_borehole borehole_name='BH1' "
            f"top_elevation={current_depth_or_elevation} " # Or however PLAXIS defines this
            f"bottom_elevation={bottom_of_layer} " # Or thickness={layer.thickness}
            f"material_name='{mat_name}' layer_name='{layer_name}'"
        )
        current_depth_or_elevation = bottom_of_layer # Update for next layer's top

    if water_table_depth is not None:
        # Example: Define phreatic level
        # commands.append(f"SET_PHREATIC_LEVEL borehole=bh1 level={-water_table_depth}") # If z=0 is surface
        commands.append(f"PLAXIS_API_CALL set_water_level borehole_name='BH1' depth_from_surface={water_table_depth}")

    commands.append(f"echo 'Soil stratigraphy definition complete (stub).'")

    if not commands:
        commands.append("# STUB: No soil stratigraphy commands generated.")
    return commands

if __name__ == '__main__':
    print("--- Testing Soil Material Command Generation ---")
    sample_material_mc = MaterialProperties(
        model_name="MohrCoulomb",
        unit_weight=18.0,
        cohesion=10.0,
        friction_angle=25.0,
        youngs_modulus=15000,
        poissons_ratio=0.3
    )
    mc_cmds = generate_material_commands(sample_material_mc)
    print(f"Generated {len(mc_cmds)} commands for Mohr-Coulomb material:")
    for cmd in mc_cmds:
        print(cmd)

    sample_material_hs = MaterialProperties(
        model_name="HardeningSoil",
        unit_weight=20.0,
        # ... other HS specific params could be in other_params dict
    )
    hs_cmds = generate_material_commands(sample_material_hs)
    print(f"\nGenerated {len(hs_cmds)} commands for Hardening Soil material:")
    for cmd in hs_cmds:
        print(cmd)

    print("\n--- Testing Soil Stratigraphy Command Generation ---")
    layer1 = SoilLayer(name="Clay", thickness=5.0, material=sample_material_mc)
    layer2 = SoilLayer(name="Sand", thickness=10.0, material=sample_material_hs)
    strat_cmds = generate_soil_stratigraphy_commands([layer1, layer2], water_table_depth=2.0)
    print(f"Generated {len(strat_cmds)} commands for stratigraphy:")
    for cmd in strat_cmds:
        print(cmd)

    print("\nTest with no water table:")
    strat_cmds_no_wt = generate_soil_stratigraphy_commands([layer1], water_table_depth=None)
    print(f"Generated {len(strat_cmds_no_wt)} commands for stratigraphy without water table:")
    for cmd in strat_cmds_no_wt:
        print(cmd)

    print("--- End of Soil Builder Tests ---")
