"""
Unit tests for the project_io module.
"""
import unittest
import json
import os
from tempfile import NamedTemporaryFile

# Corrected imports based on models.py structure
from src.backend.models import (
    ProjectSettings, SpudcanGeometry, SoilLayer, MaterialProperties,
    LoadingConditions, AnalysisControlParameters # Changed AnalysisSettings to AnalysisControlParameters
)
from src.backend.project_io import save_project, load_project # Corrected function names

class TestProjectIO(unittest.TestCase):
    """
    Test suite for project save and load functionality.
    """

    def setUp(self):
        """Create a temporary file for saving/loading project settings."""
        self.temp_file = NamedTemporaryFile(mode="w+", delete=False, suffix=".json")
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

        # Define default nested models for ProjectSettings
        self.default_spudcan_geometry = SpudcanGeometry(diameter=5.0, height_cone_angle=30.0)

        # Example SoilLayer and MaterialProperties for default soil_stratigraphy
        self.default_material = MaterialProperties(model_name="MohrCoulomb", Identification="DefaultMat", Eref=10000.0)
        self.default_soil_layer = SoilLayer(name="Layer1", thickness=5.0, material=self.default_material)
        self.default_soil_stratigraphy = [self.default_soil_layer]
        self.default_water_table_depth = -2.0

        self.default_loading_conditions = LoadingConditions(vertical_preload=100.0)
        # AnalysisControlParameters does not take execution_mode directly.
        # execution_mode is typically part of higher-level settings or logic.
        self.default_analysis_control = AnalysisControlParameters(meshing_global_coarseness="Medium")


    def tearDown(self):
        """Clean up the temporary file."""
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

    def test_save_and_load_project_settings_with_new_fields(self):
        """Test saving and loading ProjectSettings with job_number and analyst_name."""
        settings_to_save = ProjectSettings(
            project_name="TestProject1",
            job_number="JN123",
            analyst_name="Test Analyst",
            spudcan=self.default_spudcan_geometry, # Corrected field name
            soil_stratigraphy=self.default_soil_stratigraphy, # Corrected field name
            water_table_depth=self.default_water_table_depth,
            loading=self.default_loading_conditions, # Corrected field name
            analysis_control=self.default_analysis_control, # Corrected field name
        )

        save_project(settings_to_save, self.temp_file_path) # Corrected function name

        loaded_settings = load_project(self.temp_file_path) # Corrected function name

        self.assertIsNotNone(loaded_settings)
        if loaded_settings:
            self.assertEqual(loaded_settings.project_name, "TestProject1")
            self.assertEqual(loaded_settings.job_number, "JN123")
            self.assertEqual(loaded_settings.analyst_name, "Test Analyst")
            self.assertEqual(loaded_settings.spudcan.diameter, self.default_spudcan_geometry.diameter)
            self.assertEqual(len(loaded_settings.soil_stratigraphy), 1)
            if loaded_settings.soil_stratigraphy: # Check if list is not empty
                 self.assertEqual(loaded_settings.soil_stratigraphy[0].material.Identification, "DefaultMat")


    def test_load_project_settings_missing_new_fields(self):
        """Test loading ProjectSettings from a file where new fields are missing."""
        # Create a JSON file content that mimics an older version
        # Note: Pydantic models will use default values for missing fields if they have defaults.
        # If job_number and analyst_name are Optional[str] = None (default), they will be None.
        old_project_data = {
            "project_name": "OldProject",
            "spudcan": {"diameter": 6.0, "height_cone_angle": 25.0},
            "soil_stratigraphy": [
                {"name": "OldLayer", "thickness": 3.0, "material": {"model_name": "MohrCoulomb", "Identification": "OldMat", "Eref": 5000.0}}
            ],
            "water_table_depth": -1.5,
            "loading": {"vertical_preload": 50.0},
            # analysis_control in old data might not have execution_mode, or it might be part of a different structure
            # For this test, let's assume a simple analysis_control dict
            "analysis_control": {"meshing_global_coarseness": "Coarse"},
            # job_number and analyst_name are missing
        }
        with open(self.temp_file_path, "w") as f:
            json.dump(old_project_data, f)

        loaded_settings = load_project(self.temp_file_path) # Corrected function name

        self.assertIsNotNone(loaded_settings)
        if loaded_settings:
            self.assertEqual(loaded_settings.project_name, "OldProject")
            self.assertIsNone(loaded_settings.job_number) # Default for Optional[str] = None
            self.assertIsNone(loaded_settings.analyst_name) # Default for Optional[str] = None
            self.assertEqual(loaded_settings.spudcan.diameter, 6.0)
            self.assertEqual(loaded_settings.soil_stratigraphy[0].material.Identification, "OldMat")


    def test_load_project_settings_file_not_found(self):
        """Test loading from a non-existent file returns None."""
        # load_project is designed to return None if file not found, not raise FileNotFoundError.
        self.assertIsNone(load_project("non_existent_file.json"))

    def test_load_project_malformed_json(self):
        """Test loading a file with malformed JSON content returns None."""
        with open(self.temp_file_path, "w") as f:
            f.write("{'project_name': 'MalformedJSON', ...") # Intentionally malformed JSON

        loaded_settings = load_project(self.temp_file_path)
        self.assertIsNone(loaded_settings, "load_project should return None for malformed JSON.")

    def test_save_project_settings_creates_file(self):
        """Test that save_project_settings creates a file."""
        # Use a new temp file path that doesn't exist yet for this test
        temp_file_path_new = self.temp_file_path + "_new.json"
        if os.path.exists(temp_file_path_new):
            os.remove(temp_file_path_new) # Ensure it doesn't exist

        settings_to_save = ProjectSettings(
            project_name="TestSaveNew",
            job_number="JN000",
            analyst_name="Saver",
            spudcan=self.default_spudcan_geometry,
            soil_stratigraphy=self.default_soil_stratigraphy,
            water_table_depth=self.default_water_table_depth, # Added missing water_table_depth
            loading=self.default_loading_conditions,
            analysis_control=self.default_analysis_control,
        )
        save_project(settings_to_save, temp_file_path_new)
        self.assertTrue(os.path.exists(temp_file_path_new))

        # Clean up this specific file
        if os.path.exists(temp_file_path_new):
            os.remove(temp_file_path_new)

    def test_comprehensive_round_trip(self):
        """Test saving and loading a ProjectSettings object with more fields populated."""
        mat1 = MaterialProperties(
            model_name="HardeningSoil",
            Identification="HS_Sand_Dense",
            gammaUnsat=18.0, gammaSat=20.0, eInit=0.5,
            E50ref=60000, Eoedref=70000, Eurref=180000, m=0.5,
            cRef=1.0, phi=38.0, psi=8.0, pRef=100.0, K0NC=0.35, Rf=0.9,
            other_params={"G0ref": 250000, "gamma07": 0.00012}
        )
        mat2 = MaterialProperties(
            model_name="MohrCoulomb",
            Identification="MC_Clay_Soft",
            gammaUnsat=16.0, gammaSat=17.5, eInit=1.2,
            Eref=5000, nu=0.33, cRef=12.0, phi=2.0, psi=0.0
        )
        layer1 = SoilLayer(name="DenseSand", thickness=10.0, material=mat1)
        layer2 = SoilLayer(name="SoftClay", thickness=15.0, material=mat2)

        settings_to_save = ProjectSettings(
            project_name="ComprehensiveTest",
            job_number="COMP-001",
            analyst_name="Dr. Roundtrip",
            spudcan=SpudcanGeometry(diameter=7.5, height_cone_angle=40.0),
            soil_stratigraphy=[layer1, layer2],
            water_table_depth=-3.0,
            loading=LoadingConditions(
                vertical_preload=1500.0,
                target_type="penetration",
                target_penetration_or_load=5.0
            ),
            analysis_control=AnalysisControlParameters(
                meshing_global_coarseness="Fine",
                meshing_refinement_spudcan=True,
                initial_stress_method="GravityLoading",
                MaxIterations=200,
                ToleratedError=0.005,
                ResetDispToZero=True,
                MaxStepsStored=500,
                MaxSteps=2000, # Mapped from MaxSteps in model
                MinIterations=5
            ),
            plaxis_installation_path="C:/PLAXIS/Path",
            units_system="SI"
        )

        self.assertTrue(save_project(settings_to_save, self.temp_file_path))
        loaded_settings = load_project(self.temp_file_path)

        self.assertIsNotNone(loaded_settings)
        if not loaded_settings: self.fail("Loaded settings should not be None")

        # Compare all fields, including nested ones
        self.assertEqual(settings_to_save.project_name, loaded_settings.project_name)
        self.assertEqual(settings_to_save.job_number, loaded_settings.job_number)
        self.assertEqual(settings_to_save.analyst_name, loaded_settings.analyst_name)
        self.assertEqual(settings_to_save.plaxis_installation_path, loaded_settings.plaxis_installation_path)
        self.assertEqual(settings_to_save.units_system, loaded_settings.units_system)

        # Spudcan
        self.assertEqual(settings_to_save.spudcan.diameter, loaded_settings.spudcan.diameter)
        self.assertEqual(settings_to_save.spudcan.height_cone_angle, loaded_settings.spudcan.height_cone_angle)

        # Loading
        self.assertEqual(settings_to_save.loading.vertical_preload, loaded_settings.loading.vertical_preload)
        self.assertEqual(settings_to_save.loading.target_type, loaded_settings.loading.target_type)
        self.assertEqual(settings_to_save.loading.target_penetration_or_load, loaded_settings.loading.target_penetration_or_load)

        # Analysis Control
        self.assertEqual(settings_to_save.analysis_control.meshing_global_coarseness, loaded_settings.analysis_control.meshing_global_coarseness)
        self.assertEqual(settings_to_save.analysis_control.MaxIterations, loaded_settings.analysis_control.MaxIterations)
        self.assertEqual(settings_to_save.analysis_control.ToleratedError, loaded_settings.analysis_control.ToleratedError)

        # Soil Stratigraphy (more detailed check)
        self.assertEqual(len(loaded_settings.soil_stratigraphy), 2)
        self.assertEqual(settings_to_save.water_table_depth, loaded_settings.water_table_depth)

        # Compare first layer and material
        saved_layer1_mat = settings_to_save.soil_stratigraphy[0].material
        loaded_layer1_mat = loaded_settings.soil_stratigraphy[0].material
        self.assertEqual(saved_layer1_mat.Identification, loaded_layer1_mat.Identification)
        self.assertEqual(saved_layer1_mat.E50ref, loaded_layer1_mat.E50ref)
        self.assertEqual(saved_layer1_mat.other_params.get("G0ref"), loaded_layer1_mat.other_params.get("G0ref"))

        # Compare second layer and material
        saved_layer2_mat = settings_to_save.soil_stratigraphy[1].material
        loaded_layer2_mat = loaded_settings.soil_stratigraphy[1].material
        self.assertEqual(saved_layer2_mat.Identification, loaded_layer2_mat.Identification)
        self.assertEqual(saved_layer2_mat.cRef, loaded_layer2_mat.cRef)


if __name__ == '__main__':
    unittest.main()
