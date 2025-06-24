import pytest
import logging
from typing import Any, List, Callable, Dict

# Setup basic logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Models and builder to test
from src.backend.models import MaterialProperties, SoilLayer
from src.backend.plaxis_interactor.soil_builder import generate_material_callables, generate_soil_stratigraphy_callables
from src.backend.exceptions import PlaxisConfigurationError

# Mock g_i object for testing callables
class MockG_i_ForSoilBuilder:
    def __init__(self):
        self.log = []
        self.materials_created = [] # Store the material objects created
        self._object_counter = 0

    def _create_mock_material_object(self, name_hint="Material"):
        self._object_counter += 1
        # Create a more structured mock object that can store properties
        mock_obj = type(f"Mock{name_hint}", (), {
            "Identification": name_hint + "_" + str(self._object_counter),
            "SoilModel": None # Default SoilModel
            # Add other common attributes PLAXIS might have
        })()
        # Store all set properties in a dictionary on the object
        mock_obj._properties_set = {}
        return mock_obj

    def soilmat(self):
        new_mat = self._create_mock_material_object()
        self.materials_created.append(new_mat)
        self.log.append(f"CALL: g_i.soilmat() -> {new_mat.Identification}")
        logger.debug(f"  MockG_i.soilmat() called, created {new_mat.Identification}")
        return new_mat

    def setproperties(self, target_obj: Any, *args):
        prop_dict = {args[i]: args[i+1] for i in range(0, len(args), 2)}
        obj_id = getattr(target_obj, 'Identification', str(target_obj))
        self.log.append(f"CALL: g_i.setproperties(obj='{obj_id}', props={prop_dict})")
        logger.debug(f"  MockG_i.setproperties on '{obj_id}' with {prop_dict}")

        # Store properties on the mock object directly or in its _properties_set dict
        target_obj._properties_set.update(prop_dict)
        for key, value in prop_dict.items():
            setattr(target_obj, key, value) # Also set as direct attributes for easier access in tests


# --- Tests for generate_material_callables ---

def test_generate_material_callables_mohr_coulomb_valid():
    """Test with valid Mohr-Coulomb parameters."""
    mat_props = MaterialProperties(
        Identification="TestMC", model_name="MohrCoulomb",
        gammaSat=18.0, gammaUnsat=17.0, eInit=0.8,
        Eref=15000.0, nu=0.25, cRef=5.0, phi=30.0, psi=2.0
    )
    callables = generate_material_callables(mat_props)
    assert len(callables) == 1

    mock_g_i = MockG_i_ForSoilBuilder()
    callables[0](mock_g_i)

    assert len(mock_g_i.materials_created) == 1
    created_mat_obj = mock_g_i.materials_created[0]

    # Check properties set on the mock object
    assert created_mat_obj._properties_set.get("Identification") == "TestMC"
    assert created_mat_obj._properties_set.get("SoilModel") == "MohrCoulomb"
    assert created_mat_obj._properties_set.get("gammaSat") == 18.0
    assert created_mat_obj._properties_set.get("ERef") == 15000.0 # Note: Eref maps to ERef
    assert created_mat_obj._properties_set.get("nu") == 0.25
    assert created_mat_obj._properties_set.get("cRef") == 5.0
    assert created_mat_obj._properties_set.get("phi") == 30.0
    assert created_mat_obj._properties_set.get("psi") == 2.0

def test_generate_material_callables_hardening_soil_valid():
    """Test with valid HardeningSoil parameters."""
    mat_props = MaterialProperties(
        Identification="TestHS", model_name="HardeningSoil",
        gammaSat=20.0, eInit=0.6, Eref=None, # Eref might be None if E50ref is used
        E50ref=30000.0, Eoedref=28000.0, Eurref=90000.0, m=0.5,
        cRef=2.0, phi=35.0, psi=5.0, nu=0.2, pRef=100.0, K0NC=0.5, Rf=0.9
    )
    callables = generate_material_callables(mat_props)
    mock_g_i = MockG_i_ForSoilBuilder()
    callables[0](mock_g_i)

    assert len(mock_g_i.materials_created) == 1
    created_mat_obj = mock_g_i.materials_created[0]
    props_set = created_mat_obj._properties_set

    assert props_set.get("Identification") == "TestHS"
    assert props_set.get("SoilModel") == "HardeningSoil"
    assert props_set.get("gammaSat") == 20.0
    assert props_set.get("E50Ref") == 30000.0 # Check mapping
    assert props_set.get("EoedRef") == 28000.0
    assert props_set.get("EurRef") == 90000.0
    assert props_set.get("m") == 0.5
    assert props_set.get("cRef") == 2.0
    assert props_set.get("phi") == 35.0
    assert props_set.get("psi") == 5.0
    assert props_set.get("nu") == 0.2 # Used for nu_ur in HS
    assert props_set.get("pRef") == 100.0
    assert props_set.get("K0NC") == 0.5
    assert props_set.get("Rf") == 0.9
    assert "ERef" not in props_set # Eref was None

def test_generate_material_callables_soft_soil_valid():
    """Test with valid SoftSoil parameters."""
    mat_props = MaterialProperties(
        Identification="TestSS", model_name="SoftSoil",
        gammaUnsat=15.0, gammaSat=17.0, eInit=1.2,
        lambda_star=0.1, kappa_star=0.02, nu=0.15, # nu here is nu_ur
        cRef=1.0, phi=22.0, psi=0.0
    )
    callables = generate_material_callables(mat_props)
    mock_g_i = MockG_i_ForSoilBuilder()
    callables[0](mock_g_i)

    assert len(mock_g_i.materials_created) == 1
    created_mat_obj = mock_g_i.materials_created[0]
    props_set = created_mat_obj._properties_set

    assert props_set.get("Identification") == "TestSS"
    assert props_set.get("SoilModel") == "SoftSoil"
    assert props_set.get("gammaSat") == 17.0
    assert props_set.get("lambda*") == 0.1 # Check mapping
    assert props_set.get("kappa*") == 0.02 # Check mapping
    assert props_set.get("nu") == 0.15
    assert props_set.get("cRef") == 1.0
    assert props_set.get("phi") == 22.0

def test_generate_material_callables_other_params():
    """Test that other_params are included."""
    mat_props = MaterialProperties(
        Identification="TestOther", model_name="MohrCoulomb",
        gammaSat=19.0, cRef=8.0,
        other_params={"K0": 0.55, "OCR": 1.2, "SomeCustomParam": "Value"}
    )
    callables = generate_material_callables(mat_props)
    mock_g_i = MockG_i_ForSoilBuilder()
    callables[0](mock_g_i)

    assert len(mock_g_i.materials_created) == 1
    props_set = mock_g_i.materials_created[0]._properties_set
    assert props_set.get("K0") == 0.55
    assert props_set.get("OCR") == 1.2
    assert props_set.get("SomeCustomParam") == "Value"

def test_generate_material_callables_missing_identification_and_model():
    """Test error when both Identification and model_name are missing."""
    mat_props = MaterialProperties(gammaSat=18.0) # No ID, no model_name
    with pytest.raises(PlaxisConfigurationError, match="MaterialProperties must have either 'Identification' or 'model_name' specified."):
        generate_material_callables(mat_props)

def test_generate_material_callables_missing_model_uses_id_for_name():
    """Test uses Identification for sanitized_mat_name if model_name is None."""
    mat_props = MaterialProperties(Identification="MyMaterialOnlyID", model_name=None, gammaSat=18.0)
    callables = generate_material_callables(mat_props)
    mock_g_i = MockG_i_ForSoilBuilder()
    callables[0](mock_g_i)
    assert mock_g_i.materials_created[0]._properties_set.get("Identification") == "MyMaterialOnlyID"
    assert mock_g_i.materials_created[0]._properties_set.get("SoilModel") == "MohrCoulomb" # Default

def test_generate_material_callables_missing_id_uses_model_for_name():
    """Test uses model_name for sanitized_mat_name if Identification is None."""
    mat_props = MaterialProperties(Identification=None, model_name="HardeningSoil", gammaSat=18.0)
    callables = generate_material_callables(mat_props)
    mock_g_i = MockG_i_ForSoilBuilder()
    callables[0](mock_g_i)
    # Name sanitization will occur
    assert mock_g_i.materials_created[0]._properties_set.get("Identification") == "HardeningSoil"
    assert mock_g_i.materials_created[0]._properties_set.get("SoilModel") == "HardeningSoil"

# --- Tests for generate_soil_stratigraphy_callables (Basic tests, can be expanded) ---

# Mock g_i parts needed for stratigraphy
class MockG_i_ForStratigraphy(MockG_i_ForSoilBuilder): # Inherits material parts
    def __init__(self):
        super().__init__()
        self.boreholes_created = {} # Store by name
        self._current_borehole_obj = None

    def borehole(self, x: float, y: float):
        bh_name = f"BH_at_{x}_{y}".replace(".", "_") # Default name if not renamed
        mock_bh = type(f"MockBorehole_{bh_name}", (), {
            "Name": type("BHName", (), {"value": bh_name})(),
            "Identification": type("BHId", (), {"value": bh_name})(),
            "SoilLayers": [],
            "Head": None # Placeholder for water head property
        })()
        self._current_borehole_obj = mock_bh
        self.boreholes_created[bh_name] = mock_bh
        self.log.append(f"CALL: g_i.borehole({x}, {y}) -> {bh_name}")
        return mock_bh

    def rename(self, obj_to_rename: Any, new_name: str):
        old_name = obj_to_rename.Name.value
        obj_to_rename.Name.value = new_name
        obj_to_rename.Identification.value = new_name
        if old_name in self.boreholes_created and self.boreholes_created[old_name] == obj_to_rename:
            del self.boreholes_created[old_name]
            self.boreholes_created[new_name] = obj_to_rename
        self.log.append(f"CALL: g_i.rename(obj='{old_name}', new_name='{new_name}')")

    def soillayer(self, borehole_obj: Any, thickness: float):
        # Create a mock layer object and add to the borehole's SoilLayers list
        # Simulate that layer.Material is a special object that g_i.set can target
        class MaterialProxy: pass
        mock_layer = type("MockSoilLayer", (), {
            "Material": MaterialProxy(), # Give it a distinct object to be the target_attribute_holder
            "_actual_material_name": None # Store the set name here
        })()
        borehole_obj.SoilLayers.append(mock_layer)
        self.log.append(f"CALL: g_i.soillayer(bh='{borehole_obj.Name.value}', thickness={thickness})")

    def setsoillayerlevel(self, borehole_obj: Any, level_idx: int, z_coord: float):
        self.log.append(f"CALL: g_i.setsoillayerlevel(bh='{borehole_obj.Name.value}', idx={level_idx}, z={z_coord})")

    def set(self, target_attribute_holder: Any, value: Any):
        # Find which object and attribute this target_attribute_holder represents
        for bh_name, bh_obj in self.boreholes_created.items():
            if hasattr(bh_obj, 'Head') and target_attribute_holder is bh_obj.Head: # Check if it's the Head attribute itself
                bh_obj.Head = value # Assume Head can be directly set
                self.log.append(f"CALL: g_i.set({bh_name}.Head, {value})")
                logger.debug(f"  MockG_i.set Head for {bh_name} to {value}")
                return
            if hasattr(bh_obj, 'SoilLayers'):
                for idx, layer_obj in enumerate(bh_obj.SoilLayers):
                    if hasattr(layer_obj, 'Material') and target_attribute_holder is layer_obj.Material:
                        layer_obj._actual_material_name = str(value) # Store the string name
                        self.log.append(f"CALL: g_i.set(SoilLayers[{idx}].Material, '{str(value)}')")
                        logger.debug(f"  MockG_i.set Material for {bh_name}.SoilLayers[{idx}] to '{str(value)}'")
                        return

        # Fallback for other generic set calls
        self.log.append(f"CALL: g_i.set({str(target_attribute_holder)}, {value}) (Generic mock set for unhandled target)")
        logger.debug(f"  MockG_i.set (generic) on {str(target_attribute_holder)} to {value} - needs specific mock handling if this is for material properties.")


def test_generate_soil_stratigraphy_valid():
    """Test valid stratigraphy generation."""
    mat1 = MaterialProperties(Identification="Clay", model_name="MohrCoulomb")
    mat2 = MaterialProperties(Identification="Sand", model_name="HardeningSoil")
    layers = [
        SoilLayer(name="TopClay", thickness=2.0, material=mat1),
        SoilLayer(name="MidSand", thickness=3.0, material=mat2)
    ]
    callables = generate_soil_stratigraphy_callables(layers, water_table_depth=-1.0)
    assert len(callables) == 1

    mock_g_i = MockG_i_ForStratigraphy()
    # Simulate materials already existing for assignment
    # This part is tricky as the actual material objects aren't passed to setsoillayerlevel
    # It relies on names. The mock doesn't have a full material database.
    callables[0](mock_g_i)

    assert "BH1" in mock_g_i.boreholes_created
    bh_obj = mock_g_i.boreholes_created["BH1"]
    assert len(bh_obj.SoilLayers) == 2

    log_str = "\n".join(mock_g_i.log)
    # Check if set material was logged with correct indexing
    assert f"CALL: g_i.set(SoilLayers[0].Material, 'Clay')" in log_str
    assert f"CALL: g_i.set(SoilLayers[1].Material, 'Sand')" in log_str
    assert f"CALL: g_i.set(BH1.Head, -1.0)" in log_str


def test_generate_stratigraphy_invalid_thickness():
    mat = MaterialProperties(Identification="ValidMat")
    layers = [SoilLayer(name="BadLayer", thickness=0.0, material=mat)]
    with pytest.raises(PlaxisConfigurationError, match="invalid thickness"):
        generate_soil_stratigraphy_callables(layers, -1.0)

def test_generate_stratigraphy_material_missing_id_and_name():
    mat_bad = MaterialProperties() # No ID, no model_name
    layers = [SoilLayer(name="LayerWithBadMat", thickness=1.0, material=mat_bad)]
    with pytest.raises(PlaxisConfigurationError, match="missing 'Identification' or 'model_name'"):
        generate_soil_stratigraphy_callables(layers, -1.0)
