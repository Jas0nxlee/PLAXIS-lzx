"""
Generates PLAXIS API callables for defining soil materials and stratigraphy.
PRD Ref: Task 3.3 (Soil Stratigraphy & Properties Command Generation)

This module translates `MaterialProperties` and `SoilLayer` data models into
sequences of Python functions (callables). Each callable, when executed with a
PLAXIS input global object (g_i), performs API actions to define materials
or build the soil stratigraphy within a borehole.
"""

import logging
from ..models import SoilLayer, MaterialProperties
from ..exceptions import PlaxisConfigurationError # Import custom exception
from typing import List, Callable, Any, Optional

logger = logging.getLogger(__name__)

# --- Material Definition ---

def generate_material_callables(material_model: MaterialProperties) -> List[Callable[[Any], None]]:
    """
    Generates a list of Python callables for defining a single soil material in PLAXIS.
    Args are per original spec.
    Raises:
        PlaxisConfigurationError: If material_model.Identification or model_name is missing.
    """
    callables: List[Callable[[Any], None]] = []

    if material_model.Identification:
        sanitized_mat_name = material_model.Identification
    elif material_model.model_name : # Use model_name if ID is missing but model_name exists
        base_name = material_model.model_name
        sanitized_mat_name = "".join(c if c.isalnum() else '_' for c in base_name)
        if not sanitized_mat_name or (sanitized_mat_name[0].isdigit() and len(sanitized_mat_name) > 0):
            sanitized_mat_name = "Mat_" + sanitized_mat_name
        if not sanitized_mat_name: # Should not happen if base_name was not empty
             sanitized_mat_name = "UnnamedMaterialFromSoilBuilder" # Fallback
    else: # Both Identification and model_name are missing
        msg = "MaterialProperties must have either 'Identification' or 'model_name' specified."
        logger.error(msg)
        raise PlaxisConfigurationError(msg)


    logger.info(f"Preparing material callables for '{sanitized_mat_name}' (PLAXIS Model: {material_model.model_name or 'DefaultMohrCoulomb'})")

    def create_and_set_material_props_callable(g_i: Any) -> None:
        logger.info(f"API CALL: Creating material '{sanitized_mat_name}' with model '{material_model.model_name or 'DefaultMohrCoulomb'}'.")
        try:
            mat_obj = g_i.soilmat()
            logger.debug(f"  Material object created via g_i.soilmat() for '{sanitized_mat_name}'.")
        except Exception as e:
            logger.error(f"  ERROR: Failed to create material object for '{sanitized_mat_name}' using g_i.soilmat(): {e}", exc_info=True)
            raise # Re-raise to be mapped by PlaxisInteractor

        logger.debug(f"  Setting properties for material '{sanitized_mat_name}'...")
        props_to_set: Dict[str, Any] = {}
        props_to_set["Identification"] = sanitized_mat_name

        if material_model.model_name:
            plaxis_model_name = material_model.model_name.replace(" ", "")
            props_to_set["SoilModel"] = plaxis_model_name
        else:
            props_to_set["SoilModel"] = "MohrCoulomb"

        if material_model.gammaUnsat is not None: props_to_set["gammaUnsat"] = material_model.gammaUnsat
        if material_model.gammaSat is not None: props_to_set["gammaSat"] = material_model.gammaSat

        if material_model.eInit is not None: props_to_set["eInit"] = material_model.eInit

        if material_model.Eref is not None: props_to_set["ERef"] = material_model.Eref
        if material_model.nu is not None: props_to_set["nu"] = material_model.nu
        if material_model.cRef is not None: props_to_set["cRef"] = material_model.cRef
        if material_model.phi is not None: props_to_set["phi"] = material_model.phi
        if material_model.psi is not None: props_to_set["psi"] = material_model.psi

        if material_model.other_params:
            for key, value in material_model.other_params.items():
                if value is not None:
                    props_to_set[key] = value
            logger.debug(f"  Including {len(material_model.other_params)} parameters from other_params for '{sanitized_mat_name}'.")

        params_flat = []
        for key, value in props_to_set.items():
            params_flat.append(key)
            params_flat.append(value)

        try:
            g_i.setproperties(mat_obj, *params_flat)
            logger.info(f"  Properties set for material '{sanitized_mat_name}'. Applied: {props_to_set}")
        except Exception as e: # Catch PlxScriptingError or other Python errors
            logger.error(f"  ERROR: Failed to set properties for material '{sanitized_mat_name}': {e}", exc_info=True)
            logger.error(f"  Attempted to set: {props_to_set}")
            raise # Re-raise to be mapped by PlaxisInteractor

    callables.append(create_and_set_material_props_callable)
    return callables

# --- Soil Stratigraphy Definition ---

def generate_soil_stratigraphy_callables(
    soil_layers: List[SoilLayer],
    water_table_depth: Optional[float],
    borehole_name: str = "BH1",
    borehole_coords: tuple = (0,0)
) -> List[Callable[[Any], None]]:
    """
    Generates PLAXIS API callables for defining soil stratigraphy.
    Args are per original spec.
    Raises:
        PlaxisConfigurationError: If a layer's material properties are invalid or thickness is missing/invalid.
    """
    callables: List[Callable[[Any], None]] = []
    logger.info(f"Preparing soil stratigraphy callables for {len(soil_layers)} layers in borehole '{borehole_name}' at {borehole_coords}.")

    # Pre-validate layers before creating callables
    for i, layer_model in enumerate(soil_layers):
        if layer_model.thickness is None or layer_model.thickness <= 0:
            msg = f"Layer '{layer_model.name or i+1}' has invalid thickness ({layer_model.thickness})."
            logger.error(msg)
            raise PlaxisConfigurationError(msg)
        if not (layer_model.material.Identification or layer_model.material.model_name):
             msg = f"Material for layer '{layer_model.name or i+1}' is missing 'Identification' or 'model_name'."
             logger.error(msg)
             raise PlaxisConfigurationError(msg)


    def create_borehole_and_layers_callable(g_i: Any) -> None:
        logger.info(f"API CALL: Creating borehole '{borehole_name}' at ({borehole_coords[0]}, {borehole_coords[1]})")
        try:
            bh = g_i.borehole(borehole_coords[0], borehole_coords[1])
            g_i.rename(bh, borehole_name)
            logger.info(f"  Borehole '{borehole_name}' created.")
        except Exception as e:
            logger.error(f"  ERROR: Failed to create borehole '{borehole_name}': {e}", exc_info=True)
            raise # Re-raise to be mapped by PlaxisInteractor

        if not soil_layers: # Should not happen if validation above is strict, but good check
            logger.warning(f"  No soil layers provided for borehole '{borehole_name}'. Borehole created empty.")
            # Set water head even for empty borehole if specified
            if water_table_depth is not None and hasattr(bh, 'Head'):
                water_head_elevation = -abs(water_table_depth)
                try:
                    g_i.set(bh.Head, water_head_elevation)
                    logger.info(f"  Set water head for empty borehole '{borehole_name}' at Z={water_head_elevation:.2f}")
                except Exception as e_wh:
                    logger.error(f"  ERROR: Failed to set water head for empty borehole '{borehole_name}': {e_wh}", exc_info=True)
            return

        logger.info(f"  Adding {len(soil_layers)} soil layers to borehole '{borehole_name}' by thickness...")
        for i, layer_model in enumerate(soil_layers):
            # Thickness already validated
            try:
                g_i.soillayer(bh, layer_model.thickness) # type: ignore
                logger.debug(f"    Added layer {i+1} ('{layer_model.name}') of thickness {layer_model.thickness}m.")
            except Exception as e: # Catch PlxScriptingError or other Python errors
                logger.error(f"  ERROR: Failed to add layer {i+1} ('{layer_model.name}') to borehole '{borehole_name}': {e}", exc_info=True)
                # Depending on severity, might want to raise here or try to continue

        current_z_elevation = 0.0
        logger.info(f"  Setting soil layer levels and materials for borehole '{borehole_name}'...")
        try:
            g_i.setsoillayerlevel(bh, 0, current_z_elevation)
            logger.debug(f"    Set top of stratigraphy (Level 0) for '{borehole_name}' at Z={current_z_elevation:.2f}")
        except Exception as e:
            logger.error(f"  ERROR: Failed to set top level for borehole '{borehole_name}': {e}", exc_info=True)
            raise # Re-raise, this is critical

        valid_layers_processed_for_level_setting = 0
        for i, layer_model in enumerate(soil_layers):
            # Thickness already validated, material name/ID also validated
            material_props = layer_model.material
            sanitized_mat_name = material_props.Identification or \
                                 ("".join(c if c.isalnum() else '_' for c in (material_props.model_name or 'DefaultMat'))) # Fallback logic for name
            if not sanitized_mat_name or (sanitized_mat_name[0].isdigit() and len(sanitized_mat_name) > 0):
                sanitized_mat_name = "Mat_" + sanitized_mat_name
            if not sanitized_mat_name : sanitized_mat_name = "UnnamedMaterialForLayer"


            current_z_elevation -= layer_model.thickness # type: ignore
            layer_index_in_plaxis_list = valid_layers_processed_for_level_setting
            level_index_for_boundary = valid_layers_processed_for_level_setting + 1

            try:
                g_i.setsoillayerlevel(bh, level_index_for_boundary, current_z_elevation)
                if hasattr(bh, 'SoilLayers') and bh.SoilLayers and layer_index_in_plaxis_list < len(bh.SoilLayers):
                    plaxis_layer_obj = bh.SoilLayers[layer_index_in_plaxis_list]
                    g_i.set(plaxis_layer_obj.Material, sanitized_mat_name)
                    logger.debug(f"    Layer {layer_index_in_plaxis_list+1} ('{layer_model.name}'): Bottom Z={current_z_elevation:.2f}, Material='{sanitized_mat_name}'.")
                else:
                    logger.warning(f"  Could not access SoilLayers[{layer_index_in_plaxis_list}] for material assignment for layer '{layer_model.name}'.")
            except Exception as e: # Catch PlxScriptingError or other
                logger.error(f"  ERROR: Failed to set level or material for layer {i+1} ('{layer_model.name}') in '{borehole_name}': {e}", exc_info=True)
                # Optionally raise here or collect errors
            valid_layers_processed_for_level_setting += 1

        if water_table_depth is not None and hasattr(bh, 'Head'):
            water_head_elevation = -abs(water_table_depth)
            try:
                g_i.set(bh.Head, water_head_elevation)
                logger.info(f"  Set water head for borehole '{borehole_name}' at Z={water_head_elevation:.2f}")
            except Exception as e: # Catch PlxScriptingError or other
                logger.error(f"  ERROR: Failed to set water head for borehole '{borehole_name}': {e}", exc_info=True)
                # Optionally raise
        elif water_table_depth is not None:
             logger.warning(f"  Borehole object for '{borehole_name}' does not have 'Head' attribute. Cannot set water level.")
        logger.info(f"  Soil stratigraphy definition for borehole '{borehole_name}' completed.")

    callables.append(create_borehole_and_layers_callable)
    return callables


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    # Setup basic logging for the __main__ block
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("--- Testing Soil Builder Callable Generation (with Exception Handling) ---")

    # Mock PLAXIS g_i object for testing callable structure
    class MockG_i_Soil:
        # ... (MockG_i_Soil remains largely the same as in SEARCH block, ensure it can handle exceptions if needed for tests) ...
        def __init__(self):
            self.log = []
            self.materials_created = []
            self.boreholes_created = {}
            self._object_counter = 0

        def _create_mock_object(self, type_name="Object"):
            self._object_counter +=1
            mock_obj = type(f"Mock{type_name}", (), {"Name": type(f"Mock{type_name}Name", (), {"value": f"{type_name}_{self._object_counter}"})()})()
            setattr(mock_obj, "Identification", type("MockId", (), {"value": f"{type_name}Id_{self._object_counter}"})())
            # Add attributes that might be set by `setproperties` or `set`
            attrs_to_init = ["SoilModel", "gammaUnsat", "gammaSat", "ERef", "nu", "cRef", "phi", "psi", "eInit"]
            for attr_name in attrs_to_init: setattr(mock_obj, attr_name, None)
            return mock_obj

        def soilmat(self):
            new_mat = self._create_mock_object("Material")
            self.materials_created.append(new_mat)
            self.log.append("CALL: g_i.soilmat()")
            logger.debug("  MockG_i.soilmat() called, new material object created.")
            return new_mat

        def setproperties(self, target_obj: Any, *args):
            prop_dict = {args[i]: args[i+1] for i in range(0, len(args), 2)}
            log_msg = f"CALL: g_i.setproperties(obj={getattr(target_obj, 'Name', {}).get('value', str(target_obj))}, props={prop_dict})"
            self.log.append(log_msg)
            logger.debug(f"  MockG_i.setproperties on {getattr(target_obj, 'Name', {}).get('value', str(target_obj))} with {prop_dict}")
            for k,v in prop_dict.items(): setattr(target_obj, k, v)

        def borehole(self, x: float, y: float):
            bh_name_val = f"BH_at_{x}_{y}".replace(".","_")
            mock_bh_obj = self._create_mock_object("Borehole")
            mock_bh_obj.Name.value = bh_name_val
            mock_bh_obj.SoilLayers = []
            mock_bh_obj.Head = None
            self.boreholes_created[bh_name_val] = mock_bh_obj
            self.log.append(f"CALL: g_i.borehole({x}, {y}) -> {bh_name_val}")
            logger.debug(f"  MockG_i.borehole({x},{y}) called, created {bh_name_val}")
            return mock_bh_obj

        def rename(self, obj_to_rename: Any, new_name: str):
            old_name = getattr(obj_to_rename, 'Name', {}).get('value', 'UnknownObj')
            if hasattr(obj_to_rename, 'Name') and hasattr(obj_to_rename.Name, 'value'):
                 obj_to_rename.Name.value = new_name
            if old_name in self.boreholes_created and self.boreholes_created[old_name] == obj_to_rename:
                del self.boreholes_created[old_name]
                self.boreholes_created[new_name] = obj_to_rename
            log_msg = f"CALL: g_i.rename(obj='{old_name}', new_name='{new_name}')"
            self.log.append(log_msg)
            logger.debug(f"  MockG_i.rename: '{old_name}' to '{new_name}'")

        def soillayer(self, borehole_obj: Any, thickness: float):
            bh_name = borehole_obj.Name.value
            mock_layer_obj = self._create_mock_object("SoilLayer")
            mock_layer_obj.Material = None
            borehole_obj.SoilLayers.append(mock_layer_obj)
            self.log.append(f"CALL: g_i.soillayer(bh='{bh_name}', thickness={thickness})")
            logger.debug(f"  MockG_i.soillayer for '{bh_name}', thickness={thickness}")

        def setsoillayerlevel(self, borehole_obj: Any, level_idx: int, z_coord: float):
            bh_name = borehole_obj.Name.value
            self.log.append(f"CALL: g_i.setsoillayerlevel(bh='{bh_name}', level_idx={level_idx}, z={z_coord})")
            logger.debug(f"  MockG_i.setsoillayerlevel for '{bh_name}', level {level_idx} at Z={z_coord}")

        def set(self, target_attribute_holder: Any, value: Any): # More robust mock for set
            # This mock assumes target_attribute_holder is the direct PlaxisObjectAttribute proxy
            # In a real scenario, this proxy would be an object itself, and setting its .value would work.
            # For the mock, we'll try to find which object and attribute this proxy belongs to.
            # This is still a simplification.

            # Identify if it's bh.Head
            for bh_name, bh_obj_iter in self.boreholes_created.items():
                if hasattr(bh_obj_iter, 'Head') and target_attribute_holder is bh_obj_iter.Head : # Compare by identity if Head is an object
                    bh_obj_iter.Head = value # Directly set the mock's Head value
                    log_msg = f"CALL: g_i.set({bh_name}.Head, {value})"
                    logger.debug(f"  MockG_i.set Head for {bh_name} to {value}")
                    self.log.append(log_msg)
                    return

            # Identify if it's layer.Material
            for bh_name, bh_obj_iter in self.boreholes_created.items():
                if hasattr(bh_obj_iter, 'SoilLayers'):
                    for layer_obj_iter in bh_obj_iter.SoilLayers:
                         if hasattr(layer_obj_iter, 'Material') and target_attribute_holder is layer_obj_iter.Material:
                            layer_obj_iter.Material = value # Set the mock layer's Material value
                            layer_name = getattr(layer_obj_iter, 'Name', {}).get('value', 'UnnamedLayer')
                            log_msg = f"CALL: g_i.set({layer_name}.Material, '{value}')"
                            logger.debug(f"  MockG_i.set Material for {layer_name} to '{value}'")
                            self.log.append(log_msg)
                            return

            # Fallback for other generic set calls (e.g., material properties directly on mat_obj)
            # This part is tricky because `target_attribute_holder` in PLAXIS is the property object itself.
            # Our mock `mat_obj` doesn't have sub-property objects like `mat_obj.ERef` that can be passed to `set`.
            # The `setproperties` mock is more aligned with how material properties are set.
            # If `set` is used for individual material props, the mock needs adjustment.
            log_msg = f"CALL: g_i.set (generic) on {str(target_attribute_holder)} to {value}"
            self.log.append(log_msg)
            logger.debug(f"  MockG_i.set (generic) on {str(target_attribute_holder)} to {value} - needs specific mock handling if this is for material properties.")


    # Test Material Callable Generation - Valid
    logger.info("\n--- Testing Material Callable Generation (Valid) ---")
    mat_props_valid = MaterialProperties(model_name="MohrCoulomb", gammaSat=18.0, cRef=10.0, Identification="ValidClay")
    try:
        mat_callables_valid = generate_material_callables(mat_props_valid)
        mock_g_i_mat_valid = MockG_i_Soil()
        for func in mat_callables_valid: func(mock_g_i_mat_valid)
        logger.info(f"Material callables for '{mat_props_valid.Identification}' executed (mock).")
        # Add assertions here if mock_g_i_mat_valid stores set properties
    except Exception as e:
        logger.error(f"UNEXPECTED error for valid material: {type(e).__name__} - {e}", exc_info=True)

    # Test Material Callable Generation - Missing ID and Name
    logger.info("\n--- Testing Material Callable Generation (Missing ID and Name) ---")
    mat_props_no_id_name = MaterialProperties(model_name=None, gammaSat=17.0) # No ID, no model_name
    try:
        generate_material_callables(mat_props_no_id_name)
        logger.error("UNEXPECTED: generate_material_callables did not raise for missing ID and model_name.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for missing ID/name: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED error type for missing ID/name: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)


    # Test Stratigraphy Callable Generation - Valid
    logger.info("\n--- Testing Soil Stratigraphy Callable Generation (Valid) ---")
    # Use materials defined above for consistency in this test block
    layer1_valid_strat = SoilLayer(name="Upper Silt", thickness=2.0, material=mat_props_valid) # References ValidClay
    # Need another material for a second layer
    mat_props_sand = MaterialProperties(model_name="MohrCoulomb", gammaSat=20.0, Eref=40000, Identification="MediumSand")
    layer2_valid_strat = SoilLayer(name="Lower Sand", thickness=5.0, material=mat_props_sand)

    # Valid profile for stratigraphy test
    soil_profile_strat_valid = SoilProfile(
        materials=[mat_props_valid, mat_props_sand], # Ensure all referenced materials are here
        layers=[layer1_valid_strat, layer2_valid_strat],
        water_table_depth=1.0
    )
    try:
        strat_callables_valid = generate_soil_stratigraphy_callables(
            soil_layers=soil_profile_strat_valid.layers,
            water_table_depth=soil_profile_strat_valid.water_table_elevation # Corrected attribute name
        )
        mock_g_i_strat_valid = MockG_i_Soil()
        # Manually add materials to mock_g_i_strat_valid as if generate_material_callables ran
        mock_g_i_strat_valid.Materials["ValidClay"] = mock_g_i_strat_valid._create_mock_object("Material")
        mock_g_i_strat_valid.Materials["MediumSand"] = mock_g_i_strat_valid._create_mock_object("Material")

        for func in strat_callables_valid: func(mock_g_i_strat_valid)
        logger.info("Stratigraphy callables for valid profile executed (mock).")
        # Add assertions for borehole and layer setup if mock stores this state
        assert "BH1" in mock_g_i_strat_valid.boreholes_created # Default name
        # Further assertions would check layer material assignments and water head on the mock_bh_obj

    except Exception as e:
         logger.error(f"UNEXPECTED error for valid stratigraphy: {type(e).__name__} - {e}", exc_info=True)


    # Test Stratigraphy - Invalid Layer Thickness
    logger.info("\n--- Testing Stratigraphy with Invalid Layer Thickness ---")
    layer_bad_thickness = SoilLayer(name="BadLayer", thickness=0.0, material=mat_props_valid)
    soil_profile_bad_thick = SoilProfile(materials=[mat_props_valid], layers=[layer_bad_thickness])
    try:
        generate_soil_stratigraphy_callables(soil_profile_bad_thick.layers, None)
        logger.error("UNEXPECTED: generate_soil_stratigraphy_callables did not raise for invalid thickness.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for invalid thickness: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED error type for invalid thickness: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)

    # Test Stratigraphy - Layer material missing Identification and model_name
    logger.info("\n--- Testing Stratigraphy with Layer Material Missing ID/Name ---")
    mat_for_layer_no_id_name = MaterialProperties(gammaSat=16.0) # No ID, no model_name
    layer_mat_no_id_name = SoilLayer(name="LayerWithBadMat", thickness=2.0, material=mat_for_layer_no_id_name)
    soil_profile_layer_mat_no_id = SoilProfile(materials=[mat_for_layer_no_id_name], layers=[layer_mat_no_id_name])
    try:
        generate_soil_stratigraphy_callables(soil_profile_layer_mat_no_id.layers, None)
        logger.error("UNEXPECTED: generate_soil_stratigraphy_callables did not raise for layer material missing ID/name.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for layer material missing ID/name: {pce}")
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED error type for layer material missing ID/name: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)


    # Test generate_soil_callables (combined) - Layer referencing material not in profile's materials list
    logger.info("\n--- Testing Combined Callables: Layer Referencing Material Not in SoilProfile.materials ---")
    # This requires generate_stratigraphy_callables to be called by generate_soil_callables
    # and for the validation to occur there.
    mat_defined_in_profile = MaterialProperties(Identification="DefinedSand", model_name="MohrCoulomb")
    # This material object is for the layer, but its definition won't be in soil_profile_combined_bad.materials
    mat_for_layer_not_in_profile = MaterialProperties(Identification="GhostClay", model_name="SoftSoil")
    layer_ref_ghost_mat = SoilLayer(name="GhostLayer", thickness=3.0, material=mat_for_layer_not_in_profile)

    soil_profile_combined_bad = SoilProfile(
        materials=[mat_defined_in_profile], # Only "DefinedSand" is in the list of materials for the profile
        layers=[layer_ref_ghost_mat],       # This layer uses "GhostClay"
        water_table_elevation=-1.0
    )
    try:
        generate_soil_callables(soil_profile_combined_bad)
        logger.error("UNEXPECTED: generate_soil_callables did not raise for layer referencing material not in profile list.")
    except PlaxisConfigurationError as pce:
        logger.info(f"SUCCESS: Caught expected PlaxisConfigurationError for layer referencing material not in profile: {pce}")
        assert "GhostClay" in str(pce) or "not defined" in str(pce).lower()
    except Exception as e_unexp:
        logger.error(f"UNEXPECTED error type for combined callables bad ref: {type(e_unexp).__name__} - {e_unexp}", exc_info=True)


    logger.info("\n--- End of Soil Builder Callable Generation Tests (with Exception Handling) ---")
