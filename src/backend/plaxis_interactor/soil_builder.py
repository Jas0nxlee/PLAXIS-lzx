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
    # Sanitize material name for PLAXIS: replace spaces, ensure valid characters
    # Using a simpler sanitized name based on Identification if available, or model_name
    base_name = getattr(material_model, 'Identification', material_model.model_name or 'DefaultMaterial')
    sanitized_mat_name = "".join(c if c.isalnum() else '_' for c in base_name)
    # Ensure it's not empty and doesn't start with a number if that's a PLAXIS rule
    if not sanitized_mat_name or sanitized_mat_name[0].isdigit():
        sanitized_mat_name = "Mat_" + sanitized_mat_name

    print(f"Generating material commands for '{sanitized_mat_name}' (Model: {material_model.model_name})")

    commands.append(f"# --- Material Definition: {sanitized_mat_name} ---")
    commands.append(f"echo 'Defining material: {sanitized_mat_name}'")

    # Based on `all.md` (e.g., `soilmat` command):
    # soilmat "Identification" "Sand" "SoilModel" "Hardening Soil" "gammaUnsat" 17 ...
    # Or for API: g_i.soilmat(Identification="Sand", SoilModel="Hardening Soil", ...)

    cmd_parts = ["soilmat"] # Using CLI style as a base, easily adaptable to API calls
    cmd_parts.append(f"\"Identification\" \"{sanitized_mat_name}\"") # Use sanitized name as ID

    if material_model.model_name:
        cmd_parts.append(f"\"SoilModel\" \"{material_model.model_name}\"")
    else:
        cmd_parts.append(f"\"SoilModel\" \"MohrCoulomb\"") # Default if not specified

    # Add common parameters. Parameter names must match PLAXIS internal names.
    # These are guesses based on common geotechnical software and `all.md` SoilMat properties.
    param_map = {
        "unit_weight": "gammaSat", # Assuming gammaSat for general unit weight below WT
                                   # gammaUnsat might also be needed.
        "cohesion": "cRef",        # Reference cohesion
        "friction_angle": "phi",
        "youngs_modulus": "ERef",  # Reference Young's modulus
        "poissons_ratio": "nu"
    }
    # Need gammaUnsat as well
    if material_model.unit_weight is not None: # Assuming this is saturated unit weight
         cmd_parts.append(f"\"{param_map['unit_weight']}\" {material_model.unit_weight}")
         # Add a placeholder for gammaUnsat, assuming it's slightly less or equal
         cmd_parts.append(f"\"gammaUnsat\" {material_model.unit_weight - 1 if material_model.unit_weight > 1 else 16.0}") # Educated guess
    if material_model.cohesion is not None:
        cmd_parts.append(f"\"{param_map['cohesion']}\" {material_model.cohesion}")
    if material_model.friction_angle is not None:
        cmd_parts.append(f"\"{param_map['friction_angle']}\" {material_model.friction_angle}")
    if material_model.youngs_modulus is not None:
        cmd_parts.append(f"\"{param_map['youngs_modulus']}\" {material_model.youngs_modulus}")
    if material_model.poissons_ratio is not None:
        cmd_parts.append(f"\"{param_map['poissons_ratio']}\" {material_model.poissons_ratio}")

    # TODO: Add specific parameters based on material_model.model_name
    # e.g., for Hardening Soil: E50ref, EoedRef, EURRef, power_m (m), etc.
    # These would come from material_model.other_params or more specific fields in MaterialProperties
    # Example for Hardening Soil (parameter names from all.md SoilMat object):
    # if material_model.model_name == "Hardening Soil":
    #     if 'E50ref' in material_model.other_params: cmd_parts.append(f"\"E50ref\" {material_model.other_params['E50ref']}")
    #     ... and so on for other HS parameters ...

    commands.append(" ".join(cmd_parts))
    commands.append(f"echo 'Material {sanitized_mat_name} definition command generated.'")
    commands.append(f"# Note: Detailed parameters for specific soil models (e.g., Hardening Soil) need to be added here based on model_name.")

    return commands

def generate_soil_stratigraphy_commands(
    soil_layers: List[SoilLayer],
    water_table_depth: Optional[float],
    borehole_name: str = "BH1",
    borehole_coords: tuple = (0,0) # (x,y)
) -> List[str]:
    """
    Generates PLAXIS commands for defining soil stratigraphy via a borehole.
    Commands based on `all.md` (e.g., `borehole`, `soillayer`, `setsoillayerlevel`).

    Args:
        soil_layers: A list of SoilLayer data models.
        water_table_depth: Depth of the water table from the surface (e.g., z=0 is surface).
        borehole_name: Name for the borehole.
        borehole_coords: (x,y) coordinates for the borehole.

    Returns:
        A list of string commands for PLAXIS.
    """
    commands = []
    print(f"Generating soil stratigraphy commands for {len(soil_layers)} layers in borehole '{borehole_name}'.")

    commands.append(f"# --- Soil Stratigraphy Definition for {borehole_name} ---")
    commands.append(f"echo 'Defining soil stratigraphy for {borehole_name}...'")

    # Create a borehole (from all.md: borehole <x y>)
    commands.append(f"borehole {borehole_coords[0]} {borehole_coords[1]} \"Name\" \"{borehole_name}\"")

    # For API style, it might be:
    # commands.append(f"bh = g_i.borehole(x={borehole_coords[0]}, y={borehole_coords[1]}, name='{borehole_name}')")

    current_z_elevation = 0.0 # Assuming ground surface is at z=0 and layers go downwards

    for i, layer_model in enumerate(soil_layers):
        # Material name must match how it was defined in generate_material_commands (sanitized name)
        material_obj = layer_model.material
        base_name = getattr(material_obj, 'Identification', material_obj.model_name or 'DefaultMaterial')
        sanitized_mat_name = "".join(c if c.isalnum() else '_' for c in base_name)
        if not sanitized_mat_name or sanitized_mat_name[0].isdigit():
            sanitized_mat_name = "Mat_" + sanitized_mat_name

        if layer_model.thickness is None:
            print(f"Warning: Layer '{layer_model.name or i}' has no thickness. Skipping.")
            commands.append(f"# SKIPPING LAYER: {layer_model.name or i} - No thickness defined.")
            continue

        # Add soil layer to borehole (from all.md: soillayer <h> | <bh_obj> <h>)
        # This command seems to add a layer of thickness <h> at the current bottom of the borehole.
        # Then assign material to it.
        # The object name for the created soil layer is often Soillayers[-1] or similar.
        # We need to refer to the borehole when setting levels and materials.

        # Command: soillayer <bh_obj> <h> (adds layer of thickness h to borehole)
        # This command creates a soillayer object, e.g., SoilLayer_1
        # Then: set <bh_obj>.SoilLayers[idx].Material <mat_obj>
        # And: setsoillayerlevel <bh_obj> <idx_boundary> <level_z>

        # Step 1: Add a generic layer of given thickness to the borehole
        # The 'soillayer <bh_obj> <h>' command from all.md adds a layer of thickness 'h'
        # at the current bottom of the specified borehole.
        # This seems simpler than creating a global soillayer and then assigning.
        commands.append(f"soillayer {borehole_name} {layer_model.thickness}")
        # The newly added layer is typically g_i.SoilLayers[-1] or can be referenced via borehole.
        # e.g., {borehole_name}.SoilLayers[-1].Material = {sanitized_mat_name}
        # For CLI, this might be: set {borehole_name}.SoilsLayerList[-1].Material {sanitized_mat_name}
        # Or setmaterial Soillayer_<idx> <material_name> after identifying the Soillayer object.

        # The `setsoillayerlevel` command from all.md seems more appropriate for defining layer boundaries.
        # setsoillayerlevel <bh_obj> <level_index> <z_coordinate>
        # Level 0 is top surface, Level 1 is bottom of first layer, etc.

        # Set top of this layer (which is bottom of previous, or surface for first layer)
        commands.append(f"setsoillayerlevel {borehole_name} {i} {current_z_elevation}")

        # Calculate bottom elevation of this layer
        current_z_elevation -= layer_model.thickness

        # Set bottom of this layer
        commands.append(f"setsoillayerlevel {borehole_name} {i+1} {current_z_elevation}")

        # Assign material to this layer
        # This assumes we can identify the layer object created by its index in the borehole
        # The exact syntax for referencing a specific layer within a borehole for material assignment
        # needs to be precise for PLAXIS.
        # Conceptual:
        commands.append(f"set {borehole_name}.SoilLayers[{i}].Material {sanitized_mat_name}")
        # Alternative, if layers are globally indexed and then assigned:
        # commands.append(f"setmaterial SoilLayer_{i+1}_{borehole_name_suffix} {sanitized_mat_name}")
        # For now, use the direct property access style shown in some `set` examples in all.md
        commands.append(f"echo 'Defined layer {i+1} in {borehole_name}: Top Z={current_z_elevation + layer_model.thickness}, Bottom Z={current_z_elevation}, Material={sanitized_mat_name}'")


    if water_table_depth is not None:
        # From all.md: set <bh_obj>.Head <z_coord_of_water_head>
        # Assuming water_table_depth is depth from surface (z=0), so head is at z = -water_table_depth
        water_head_elevation = -abs(water_table_depth) # Ensure it's negative or zero
        commands.append(f"set {borehole_name}.Head {water_head_elevation}")
        commands.append(f"echo 'Set water head for {borehole_name} at Z={water_head_elevation}'")

    commands.append(f"echo 'Soil stratigraphy for {borehole_name} definition complete.'")

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
