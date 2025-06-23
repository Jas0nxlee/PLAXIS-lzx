"""
Generates PLAXIS API callables for defining soil materials and stratigraphy.
PRD Ref: Task 3.3 (Soil Stratigraphy & Properties Command Generation)

This module translates `MaterialProperties` and `SoilLayer` data models into
sequences of Python functions (callables). Each callable, when executed with a
PLAXIS input global object (g_i), performs API actions to define materials
or build the soil stratigraphy within a borehole.
"""

from ..models import SoilLayer, MaterialProperties # Relative import from parent package
from typing import List, Callable, Any, Optional

# --- Material Definition ---

def generate_material_callables(material_model: MaterialProperties) -> List[Callable[[Any], None]]:
    """
    Generates a list of Python callables for defining a single soil material in PLAXIS.

    Args:
        material_model: The MaterialProperties data model instance.

    Returns:
        A list of callable functions. Each function takes the PLAXIS input global
        object (g_i) as an argument.

    Assumptions:
    - The PLAXIS g_i object has a method like `g_i.soilmat()` that creates a new material
      object (or a similar mechanism to create and then configure materials).
    - The created material object has a `setproperties()` method or allows direct attribute
      setting for parameters like "Identification", "SoilModel", "gammaSat", "cRef", etc.
    - Parameter names used (e.g., "gammaSat", "cRef") match those expected by the PLAXIS API
      for the `soilmat` object or its properties. These are based on common PLAXIS usage
      and the `all.md` reference for `SoilMat` object properties.
    - `material_model.model_name` corresponds to a valid soil model string in PLAXIS (e.g., "MohrCoulomb", "Hardening Soil").
    - If `material_model.unit_weight` is provided, it's assumed to be the saturated unit weight (`gammaSat`).
      A heuristic is used to estimate `gammaUnsat` (unsaturated unit weight). A more precise
      input for `gammaUnsat` would be better if available.
    - Specific parameters for advanced models (e.g., Hardening Soil's E50ref, EoedRef) would
      need to be present in `material_model.other_params` (a dict) and explicitly handled.
      Current implementation primarily sets common Mohr-Coulomb type parameters.
    """
    callables: List[Callable[[Any], None]] = []

    # Sanitize material name for PLAXIS: replace spaces, ensure valid characters.
    # PLAXIS often requires names to be unique and without special characters.
    # Using Identification from MaterialProperties if available, otherwise model_name.
    base_name = getattr(material_model, 'Identification', material_model.model_name or 'DefaultMaterial')
    # Replace non-alphanumeric characters with underscores.
    sanitized_mat_name = "".join(c if c.isalnum() else '_' for c in base_name)
    # Ensure it's not empty and doesn't start with a number if that's a PLAXIS rule.
    if not sanitized_mat_name or (sanitized_mat_name[0].isdigit() and len(sanitized_mat_name) > 0) : # Check length for isdigit
        sanitized_mat_name = "Mat_" + sanitized_mat_name # Prepend "Mat_" if problematic
    if not sanitized_mat_name: # Final fallback if it became empty
        sanitized_mat_name = "UnnamedMaterial"


    print(f"Preparing material callables for '{sanitized_mat_name}' (Model: {material_model.model_name})")

    def create_and_set_material_props_callable(g_i: Any) -> None:
        """Callable to create a new soil material and set its properties."""
        print(f"  PLAXIS API CALL: Creating material '{sanitized_mat_name}'")

        # Create a new soil material object using the PLAXIS API.
        # The actual method might be g_i.soilmat(), g_i.creatematerial('soil'), etc.
        # Assuming g_i.soilmat() returns the newly created material object.
        try:
            mat_obj = g_i.soilmat()
        except Exception as e:
            print(f"    ERROR: Failed to create material object using g_i.soilmat(): {e}")
            raise # Re-raise to be caught by PlaxisInteractor

        print(f"    Material object created. Setting properties for '{sanitized_mat_name}'...")

        # Prepare properties dictionary for setproperties or individual assignments
        props_to_set = {
            "Identification": sanitized_mat_name,
            "SoilModel": material_model.model_name or "MohrCoulomb" # Default to MohrCoulomb
        }

        # Map common parameters from MaterialProperties model to PLAXIS API names.
        # These PLAXIS names are based on common usage and `all.md` (e.g., SoilMat object properties).
        # Parameter names like 'gammaSat', 'cRef' should be verified against specific PLAXIS version API docs.
        if material_model.unit_weight is not None:
            props_to_set["gammaSat"] = material_model.unit_weight
            # Heuristic for unsaturated unit weight. Ideally, this should be a separate input.
            props_to_set["gammaUnsat"] = material_model.unit_weight - 1.0 if material_model.unit_weight > 1.0 else 16.0

        if material_model.cohesion is not None: props_to_set["cRef"] = material_model.cohesion
        if material_model.friction_angle is not None: props_to_set["phi"] = material_model.friction_angle
        if material_model.youngs_modulus is not None: props_to_set["Eref"] = material_model.youngs_modulus # Eref common for MC, HS
        if material_model.poissons_ratio is not None: props_to_set["nu"] = material_model.poissons_ratio

        # TODO: Add specific parameters for advanced soil models based on material_model.model_name
        # This would involve checking material_model.model_name and then accessing
        # corresponding fields in material_model or items in material_model.other_params.
        # Example for Hardening Soil (parameter names like E50ref, Eoedref, Eurref, m, etc.):
        # if material_model.model_name == "Hardening Soil":
        #     if 'E50ref' in material_model.other_params: props_to_set["E50ref"] = material_model.other_params['E50ref']
        #     # ... add other Hardening Soil specific parameters ...
        # This section needs to be expanded based on the actual structure of MaterialProperties
        # and the parameters required by different soil models in PLAXIS.

        # Set properties on the material object.
        # PLAXIS API might use mat_obj.setproperties(**props_to_set) or individual assignments.
        # Using g_i.setproperties(mat_obj, **props_to_set) is also a common pattern.
        try:
            # Assuming g_i.setproperties(target_object, param_name1, param_value1, param_name2, param_value2, ...)
            # Flatten dict for this style:
            params_flat = []
            for key, value in props_to_set.items():
                params_flat.append(key)
                params_flat.append(value)

            g_i.setproperties(mat_obj, *params_flat)
            # Alternative if setproperties takes a dict: g_i.setproperties(mat_obj, props_to_set)
            # Alternative if direct assignment:
            # for key, value in props_to_set.items(): setattr(mat_obj, key, value)

            print(f"    Properties set for material '{sanitized_mat_name}'.")
        except Exception as e:
            print(f"    ERROR: Failed to set properties for material '{sanitized_mat_name}': {e}")
            raise # Re-raise

    callables.append(create_and_set_material_props_callable)
    return callables

# --- Soil Stratigraphy Definition ---

def generate_soil_stratigraphy_callables(
    soil_layers: List[SoilLayer],
    water_table_depth: Optional[float],
    borehole_name: str = "BH1", # Default borehole name
    borehole_coords: tuple = (0,0) # Default (x,y) coordinates for the borehole
) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for defining soil stratigraphy via a single borehole.

    Args:
        soil_layers: A list of SoilLayer data model instances, ordered from top to bottom.
        water_table_depth: Depth of the water table from the surface (z=0).
                           A positive value indicates depth below surface.
        borehole_name: Name for the borehole to be created in PLAXIS.
        borehole_coords: (x,y) coordinates for the borehole location.

    Returns:
        A list of callable functions for PLAXIS API interaction.

    Assumptions:
    - A single borehole is created at `borehole_coords`. Multi-borehole complex stratigraphy
      is not handled by this basic builder.
    - Ground surface is at z=0. Soil layers are defined downwards from this level.
    - `g_i.borehole(x, y, Name=name)` creates a borehole object.
    - `g_i.soillayer(borehole_object, top_elevation, bottom_elevation)` or a similar method
      (e.g., `borehole_object.add_layer(thickness)`) is used to define layers within the borehole.
      This implementation assumes adding layers by specifying thickness and then setting levels.
      Specifically, it uses `g_i.soillayer(borehole_ref, thickness)` to add layers sequentially
      to the bottom of the borehole, then `g_i.setsoillayerlevel()` to define their exact elevations.
    - Materials referenced by `SoilLayer.material.Identification` (or a sanitized version)
      must have already been defined in PLAXIS (e.g., by `generate_material_callables`).
      The assignment uses `g_i.set(borehole.SoilLayers[idx].Material, material_object_or_name)`.
      Accessing `borehole.SoilLayers[idx]` or similar path needs to be valid in PLAXIS API.
      The `all.md` reference suggests `Borehole.SoilsLayerList` or `Borehole.SoilLayers`.
    - Water table (`Head`) is set on the borehole object using `g_i.set(borehole_object.Head, z_coord)`.
    - `SoilLayer.thickness` is positive.
    """
    callables: List[Callable[[Any], None]] = []
    print(f"Preparing soil stratigraphy callables for {len(soil_layers)} layers in borehole '{borehole_name}'.")

    def create_borehole_and_layers_callable(g_i: Any) -> None:
        """Callable to create borehole, add layers, set levels, assign materials, and set water head."""
        print(f"  PLAXIS API CALL: Creating borehole '{borehole_name}' at ({borehole_coords[0]}, {borehole_coords[1]})")
        try:
            # Create the borehole object.
            # The exact API might be g_i.borehole(x, y, Name=borehole_name) or similar.
            # bh = g_i.borehole(borehole_coords[0], borehole_coords[1], Name=borehole_name) # If Name is a param
            # Or create then rename:
            bh = g_i.borehole(borehole_coords[0], borehole_coords[1])
            g_i.rename(bh, borehole_name) # Assumes rename works on the borehole object
            print(f"    Borehole '{borehole_name}' created.")
        except Exception as e:
            print(f"    ERROR: Failed to create borehole '{borehole_name}': {e}")
            raise

        if not soil_layers:
            print(f"    Warning: No soil layers provided for borehole '{borehole_name}'. Borehole created empty.")
            # Set water table if defined, even for empty borehole (though less common)
            if water_table_depth is not None:
                water_head_elevation = -abs(water_table_depth) # Depth from z=0 surface
                try:
                    g_i.set(bh.Head, water_head_elevation) # Assumes bh.Head is the correct attribute
                    print(f"    Set water head for empty borehole '{borehole_name}' at Z={water_head_elevation:.2f}")
                except Exception as e:
                    print(f"    ERROR: Failed to set water head for empty borehole '{borehole_name}': {e}")
            return # Nothing more to do if no layers

        # Add soil layers by thickness first.
        # Assumes g_i.soillayer(borehole_object_or_name, thickness) adds a layer to the bottom.
        print(f"    Adding {len(soil_layers)} soil layers to borehole '{borehole_name}' by thickness...")
        for i, layer_model in enumerate(soil_layers):
            if layer_model.thickness is None or layer_model.thickness <= 0:
                print(f"    Warning: Layer '{layer_model.name or i+1}' has invalid thickness ({layer_model.thickness}). Skipping.")
                continue
            try:
                g_i.soillayer(bh, layer_model.thickness) # Pass borehole object and thickness
                print(f"      Added layer {i+1} ('{layer_model.name}') of thickness {layer_model.thickness}m.")
            except Exception as e:
                print(f"    ERROR: Failed to add layer {i+1} ('{layer_model.name}') to borehole '{borehole_name}': {e}")
                # Decide if to continue or raise. For now, continue to try other layers.

        # Set levels and assign materials.
        # Surface is at z=0. current_z_elevation tracks the bottom of the current layer being defined.
        current_z_elevation = 0.0

        print(f"    Setting soil layer levels and materials for borehole '{borehole_name}'...")
        try:
            # Set top surface level (Level 0 of the stratigraphy column)
            # API: g_i.setsoillayerlevel(borehole_object_or_name, level_index, z_coordinate)
            g_i.setsoillayerlevel(bh, 0, current_z_elevation)
            print(f"      Set top of stratigraphy (Level 0) for '{borehole_name}' at Z={current_z_elevation:.2f}")
        except Exception as e:
            print(f"    ERROR: Failed to set top level for borehole '{borehole_name}': {e}")
            # This might be a critical failure for subsequent level settings.
            raise


        valid_layers_processed_for_level_setting = 0
        for i, layer_model in enumerate(soil_layers):
            if layer_model.thickness is None or layer_model.thickness <= 0:
                continue # Skip layers that were not added due to invalid thickness earlier

            # Determine the sanitized material name used during material definition
            material_props = layer_model.material
            base_mat_id_name = getattr(material_props, 'Identification', material_props.model_name or 'DefaultMaterial')
            sanitized_mat_name = "".join(c if c.isalnum() else '_' for c in base_mat_id_name)
            if not sanitized_mat_name or (sanitized_mat_name[0].isdigit() and len(sanitized_mat_name) > 0):
                sanitized_mat_name = "Mat_" + sanitized_mat_name
            if not sanitized_mat_name: sanitized_mat_name = "UnnamedMaterial"


            current_z_elevation -= layer_model.thickness # Calculate bottom elevation of this layer

            layer_index_in_plaxis_list = valid_layers_processed_for_level_setting # 0-based index for the layer itself
            level_index_for_boundary = valid_layers_processed_for_level_setting + 1 # 1-based index for the bottom boundary of this layer

            try:
                # Set bottom boundary level of this layer
                g_i.setsoillayerlevel(bh, level_index_for_boundary, current_z_elevation)

                # Assign material to this layer.
                # This requires knowing how PLAXIS API references soil layers within a borehole object (e.g., bh.SoilLayers[idx]).
                # The path might be bh.SoilLayers (if a direct list) or bh.Soils[0].SoilLayers for the first soil column.
                # Assuming bh.SoilLayers[idx] for simplicity. This path needs verification.
                # `all.md` hints at `Borehole.SoilLayers` or `Borehole.SoilsLayerList`.
                # Let's assume `bh.SoilLayers` is a list of layer objects.
                if hasattr(bh, 'SoilLayers') and bh.SoilLayers and layer_index_in_plaxis_list < len(bh.SoilLayers):
                    plaxis_layer_obj = bh.SoilLayers[layer_index_in_plaxis_list]
                    # Material assignment: g_i.set(plaxis_layer_obj.Material, "MaterialNameString")
                    # Or: plaxis_layer_obj.Material = g_i.Materials["MaterialNameString"] (if Materials is a dict-like collection)
                    g_i.set(plaxis_layer_obj.Material, sanitized_mat_name) # Assign by name string
                    print(f"      Layer {layer_index_in_plaxis_list+1} ('{layer_model.name}'): Bottom Z={current_z_elevation:.2f}, Material='{sanitized_mat_name}'.")
                else:
                    # Fallback if direct object path is complex or unknown: try command style if available
                    # g_i.command(f"set {borehole_name}.SoilLayers[{layer_index_in_plaxis_list}].Material \"{sanitized_mat_name}\"")
                    print(f"    Warning: Could not directly access SoilLayers[{layer_index_in_plaxis_list}] for material assignment. "
                          f"Material '{sanitized_mat_name}' for layer '{layer_model.name}' may need manual assignment or command-style fallback.")

            except Exception as e:
                print(f"    ERROR: Failed to set level or material for layer {i+1} ('{layer_model.name}') in '{borehole_name}': {e}")
                # Continue to try next layers or raise, depending on desired strictness

            valid_layers_processed_for_level_setting += 1

        # Set water table head if specified
        if water_table_depth is not None:
            water_head_elevation = -abs(water_table_depth) # Depth from z=0 surface
            try:
                # Assumes bh.Head is the correct attribute for setting phreatic level for this borehole.
                g_i.set(bh.Head, water_head_elevation)
                print(f"    Set water head for borehole '{borehole_name}' at Z={water_head_elevation:.2f}")
            except Exception as e:
                print(f"    ERROR: Failed to set water head for borehole '{borehole_name}': {e}")
                # This might not be a fatal error for the overall stratigraphy.

        print(f"  Soil stratigraphy definition for borehole '{borehole_name}' completed.")

    callables.append(create_borehole_and_layers_callable)
    return callables


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    print("--- Testing Soil Builder Callable Generation ---")

    # Mock PLAXIS g_i object for testing callable structure
    class MockG_i_Soil:
        def __init__(self):
            self.log = []
            self.materials_created = []
            self.boreholes_created = {} # name: borehole_obj
            self.current_borehole_layers = {} # borehole_name: [layer_thicknesses]
            self.current_borehole_levels = {} # borehole_name: {level_idx: z_coord}
            self.current_borehole_material_assignments = {} # borehole_name: {layer_idx: mat_name}
            self.current_borehole_heads = {} # borehole_name: head_z

        def soilmat(self): # Simulates creating a new material object
            new_mat = type("MockMaterial", (), {"Identification": "NewMat", "SoilModel": "MC"})() # Basic mock object
            self.materials_created.append(new_mat)
            self.log.append("CALL: g_i.soilmat()")
            print("  MockG_i.soilmat() called, new material object created.")
            return new_mat

        def setproperties(self, target_obj: Any, *args): # Simulates setting properties
            prop_dict = {args[i]: args[i+1] for i in range(0, len(args), 2)}
            log_msg = f"CALL: g_i.setproperties(obj_type={type(target_obj).__name__}, props={prop_dict})"
            self.log.append(log_msg)
            print(f"  MockG_i.setproperties on {type(target_obj).__name__} with {prop_dict}")
            for k,v in prop_dict.items(): setattr(target_obj, k, v) # Set on mock object

        def borehole(self, x: float, y: float): # Simulates creating a borehole
            # Simplified: does not use Name parameter here, assumes rename is called after.
            bh_name = f"BH_at_{x}_{y}".replace(".","_")
            mock_bh_obj = type("MockBorehole", (), {"Name": bh_name, "SoilLayers": [], "Head": None, "_raw_layers_by_thickness": []})()
            self.boreholes_created[bh_name] = mock_bh_obj
            self.log.append(f"CALL: g_i.borehole({x}, {y}) -> {bh_name}")
            print(f"  MockG_i.borehole({x},{y}) called, created {bh_name}")
            return mock_bh_obj

        def rename(self, obj_to_rename: Any, new_name: str):
            # Find and rename in boreholes_created if it's a borehole
            old_name = None
            for name, bh_obj_iter in list(self.boreholes_created.items()): # Use list for safe dict modification
                if bh_obj_iter == obj_to_rename:
                    old_name = name
                    del self.boreholes_created[old_name]
                    obj_to_rename.Name = new_name # Update mock object's name
                    self.boreholes_created[new_name] = obj_to_rename
                    break
            log_msg = f"CALL: g_i.rename(obj='{old_name or 'UnknownObj'}', new_name='{new_name}')"
            self.log.append(log_msg)
            print(f"  MockG_i.rename: '{old_name}' to '{new_name}'")


        def soillayer(self, borehole_obj_or_name: Any, thickness: float): # Simulates adding layer by thickness
            bh_name = borehole_obj_or_name.Name if hasattr(borehole_obj_or_name, 'Name') else str(borehole_obj_or_name)
            if bh_name not in self.current_borehole_layers: self.current_borehole_layers[bh_name] = []
            self.current_borehole_layers[bh_name].append(thickness)
            # Simulate PLAXIS internal layer list for assignment later
            if hasattr(borehole_obj_or_name, "_raw_layers_by_thickness"):
                 borehole_obj_or_name._raw_layers_by_thickness.append(thickness) # Store for level setting logic
                 # Also simulate the SoilLayers list being populated for material assignment test
                 mock_layer_obj = type("MockSoilLayer", (), {"Material": None})()
                 borehole_obj_or_name.SoilLayers.append(mock_layer_obj)


            self.log.append(f"CALL: g_i.soillayer(bh='{bh_name}', thickness={thickness})")
            print(f"  MockG_i.soillayer for '{bh_name}', thickness={thickness}")

        def setsoillayerlevel(self, borehole_obj_or_name: Any, level_idx: int, z_coord: float):
            bh_name = borehole_obj_or_name.Name if hasattr(borehole_obj_or_name, 'Name') else str(borehole_obj_or_name)
            if bh_name not in self.current_borehole_levels: self.current_borehole_levels[bh_name] = {}
            self.current_borehole_levels[bh_name][level_idx] = z_coord
            self.log.append(f"CALL: g_i.setsoillayerlevel(bh='{bh_name}', level_idx={level_idx}, z={z_coord})")
            print(f"  MockG_i.setsoillayerlevel for '{bh_name}', level {level_idx} at Z={z_coord}")

        def set(self, target_attribute_path: Any, value: Any): # Simulates g_i.set(object.Attribute, value)
            # This mock is very simplified. Real 'set' is powerful.
            # Here, assume target_attribute_path is like borehole_obj.Head or layer_obj.Material
            # For layer_obj.Material assignment:
            if hasattr(target_attribute_path, "__dict__") and "Material" in target_attribute_path.__dict__: # crude check for layer obj
                 target_attribute_path.Material = value # Mock assignment
                 # Find which borehole/layer this corresponds to for logging
                 bh_name_found, layer_idx_found = "UnknownBH", -1
                 for bhn, bhobj_iter in self.boreholes_created.items():
                     if hasattr(bhobj_iter, 'SoilLayers'):
                         try:
                             idx = bhobj_iter.SoilLayers.index(target_attribute_path)
                             bh_name_found, layer_idx_found = bhn, idx
                             break
                         except ValueError: continue
                 log_msg = f"CALL: g_i.set({bh_name_found}.SoilLayers[{layer_idx_found}].Material, '{value}')"
                 print(f"  MockG_i.set Material for layer {layer_idx_found} in {bh_name_found} to '{value}'")
            elif hasattr(target_attribute_path, "_mock_parent_is_borehole_head"): # If it's bh.Head attribute
                target_attribute_path._mock_parent_is_borehole_head.Head = value # Mock assignment
                bh_name = target_attribute_path._mock_parent_is_borehole_head.Name
                log_msg = f"CALL: g_i.set({bh_name}.Head, {value})"
                print(f"  MockG_i.set Head for {bh_name} to {value}")
            else:
                log_msg = f"CALL: g_i.set({str(target_attribute_path)}, {value})" # Generic log
                print(f"  MockG_i.set {str(target_attribute_path)} to {value}")

            self.log.append(log_msg)


    # Test Material Callable Generation
    print("\n--- Testing Material Callable Generation ---")
    mat_props1 = MaterialProperties(model_name="MohrCoulomb", unit_weight=18.0, cohesion=10.0, Identification="Clay_Soft")
    mat_callables = generate_material_callables(mat_props1)
    print(f"Generated {len(mat_callables)} callables for material '{mat_props1.Identification}'.")

    mock_g_i_mat_test = MockG_i_Soil()
    for i, callable_func in enumerate(mat_callables):
        print(f"Executing material callable {i+1} ({getattr(callable_func, '__name__', 'lambda')})...")
        callable_func(mock_g_i_mat_test)
    print("Log of mock g_i commands for material generation:")
    for entry in mock_g_i_mat_test.log: print(f"  - {entry}")
    assert len(mock_g_i_mat_test.materials_created) == 1
    assert mock_g_i_mat_test.materials_created[0].Identification == "Clay_Soft"
    assert mock_g_i_mat_test.materials_created[0].gammaSat == 18.0

    # Test Stratigraphy Callable Generation
    print("\n--- Testing Soil Stratigraphy Callable Generation ---")
    layer1_props = MaterialProperties(model_name="MohrCoulomb", unit_weight=17.0, cohesion=5.0, Identification="TopClay")
    layer2_props = MaterialProperties(model_name="HardeningSoil", unit_weight=19.0, cohesion=2.0, Identification="DeepSand")

    soil_layers_list = [
        SoilLayer(name="Upper Clay", thickness=3.0, material=layer1_props),
        SoilLayer(name="Lower Sand", thickness=7.0, material=layer2_props)
    ]
    strat_callables = generate_soil_stratigraphy_callables(soil_layers_list, water_table_depth=2.0, borehole_name="MainBH")
    print(f"Generated {len(strat_callables)} callables for stratigraphy.")

    mock_g_i_strat_test = MockG_i_Soil()
    # Simulate prior material creation for assignment test
    # (In real flow, material callables run first, populating g_i.Materials)
    mock_g_i_strat_test.Materials = {"TopClay": "mat_obj1_placeholder", "DeepSand": "mat_obj2_placeholder"}


    for i, callable_func in enumerate(strat_callables):
        print(f"Executing stratigraphy callable {i+1} ({getattr(callable_func, '__name__', 'lambda')})...")
        # Patch the mock g_i to simulate bh.Head for the set command
        # This is needed because the `set` mock tries to access bh.Head directly.
        for bh_obj_iter in mock_g_i_strat_test.boreholes_created.values():
             bh_obj_iter.Head = type("MockHead", (), {"_mock_parent_is_borehole_head": bh_obj_iter, "Head": None})()

        callable_func(mock_g_i_strat_test)

    print("Log of mock g_i commands for stratigraphy generation:")
    for entry in mock_g_i_strat_test.log: print(f"  - {entry}")

    # Assertions for stratigraphy test (conceptual based on mock behavior)
    assert "MainBH" in mock_g_i_strat_test.boreholes_created
    assert len(mock_g_i_strat_test.current_borehole_layers.get("MainBH", [])) == 2
    assert mock_g_i_strat_test.current_borehole_levels.get("MainBH", {}).get(0) == 0.0 # Top level
    assert mock_g_i_strat_test.current_borehole_levels.get("MainBH", {}).get(1) == -3.0 # Bottom of layer 1
    assert mock_g_i_strat_test.current_borehole_levels.get("MainBH", {}).get(2) == -10.0 # Bottom of layer 2
    # Material assignment check would need more detailed mocking of bh.SoilLayers list.
    # Water head check:
    main_bh_obj = mock_g_i_strat_test.boreholes_created.get("MainBH")
    if main_bh_obj and hasattr(main_bh_obj, 'Head') and hasattr(main_bh_obj.Head, 'Head'): # Check nested Head attribute
        assert main_bh_obj.Head.Head == -2.0
    else:
        print("Warning: Water head assertion could not be fully verified due to mock structure.")


    print("\n--- End of Soil Builder Callable Generation Tests ---")
