"""
Handles saving and loading of project data for the PLAXIS 3D Spudcan Automation Tool.
PRD Ref: 4.1.1.2, 4.1.1.3 (Project Save/Load)
Serialization format: JSON is planned (PRD 7.4.1)
"""

from .models import ProjectSettings # Assuming models.py is in the same package
import json
from dataclasses import asdict, is_dataclass
from typing import Type, TypeVar

T = TypeVar('T')

class EnhancedJSONEncoder(json.JSONEncoder):
    """
    A custom JSON encoder that can handle dataclasses.
    """
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)

def dataclass_from_dict(klass: Type[T], d: dict) -> T:
    """
    Recursively converts a dictionary to a dataclass instance.
    This is a simplified version; more robust handling might be needed for complex nested types
    or specific field transformations.
    """
    # This is a basic implementation. For production, a more robust library like `dacite`
    # or `pydantic` (if models were pydantic models) would be better.
    # For now, we assume fields match and types are simple or handled by recursive calls.

    # Note: This basic version doesn't deeply reconstruct nested dataclasses automatically
    # without more complex logic to inspect field types.
    # For now, we will rely on the structure being relatively flat or handle nesting manually
    # in the load_project function for specific known nested dataclasses.
    try:
        # A more robust solution would inspect field types and recursively call
        # dataclass_from_dict for nested dataclasses.
        # For this stub, we'll assume simple types or handle nesting explicitly in load_project.
        return klass(**d)
    except TypeError as e:
        print(f"Error converting dict to {klass.__name__}: {e}. Dict: {d}")
        # Potentially raise a custom exception or return None/partial object
        raise ValueError(f"Could not instantiate {klass.__name__} from dictionary: {e}")


def save_project(project_data: ProjectSettings, filepath: str) -> bool:
    """
    Saves the project settings data to a JSON file.

    Args:
        project_data: The ProjectSettings object to save.
        filepath: The path to the file where the project will be saved.

    Returns:
        True if saving was successful, False otherwise.
    """
    print(f"Attempting to save project to: {filepath}")
    try:
        with open(filepath, 'w') as f:
            json.dump(project_data, f, cls=EnhancedJSONEncoder, indent=4)
        print(f"Project data successfully saved to {filepath}")
        return True
    except IOError as e:
        print(f"Error saving project to {filepath}: {e}")
        # In a real app, this would propagate to UI via logging/error handling
        return False
    except TypeError as e:
        print(f"Error serializing project data: {e}")
        return False

def load_project(filepath: str) -> Optional[ProjectSettings]:
    """
    Loads project settings data from a JSON file.

    Args:
        filepath: The path to the file from which the project will be loaded.

    Returns:
        A ProjectSettings object if loading was successful, None otherwise.
    """
    print(f"Attempting to load project from: {filepath}")
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Manual reconstruction for nested dataclasses - this needs to match ProjectSettings structure
        # This is where a library like dacite would be very helpful.
        spudcan_data = data.pop('spudcan', {})
        stratigraphy_data = data.pop('soil_stratigraphy', [])
        loading_data = data.pop('loading', {})
        analysis_control_data = data.pop('analysis_control', {})

        project_settings = dataclass_from_dict(ProjectSettings, data)

        project_settings.spudcan = dataclass_from_dict(models.SpudcanGeometry, spudcan_data)
        project_settings.loading = dataclass_from_dict(models.LoadingConditions, loading_data)
        project_settings.analysis_control = dataclass_from_dict(models.AnalysisControlParameters, analysis_control_data)

        project_settings.soil_stratigraphy = []
        for layer_data in stratigraphy_data:
            material_data = layer_data.pop('material', {})
            layer = dataclass_from_dict(models.SoilLayer, layer_data)
            layer.material = dataclass_from_dict(models.MaterialProperties, material_data)
            project_settings.soil_stratigraphy.append(layer)

        print(f"Project data successfully loaded from {filepath}")
        return project_settings
    except FileNotFoundError:
        print(f"Error: Project file not found at {filepath}")
        return None
    except IOError as e:
        print(f"Error loading project from {filepath}: {e}")
        return None
    except (json.JSONDecodeError, ValueError, TypeError) as e: # Added ValueError & TypeError for dataclass_from_dict
        print(f"Error parsing project file {filepath}: {e}")
        return None

if __name__ == '__main__':
    # Example Usage for testing save/load (requires models.py)
    import os
    from . import models # Ensure models.py can be imported

    # Create a sample ProjectSettings object
    sample_project = models.ProjectSettings(
        project_name="Test SaveLoad Project",
        job_number="TSL-001",
        analyst_name="Jules Verne",
        plaxis_installation_path="C:/PLAXIS3D",
        units_system="SI"
    )
    sample_project.spudcan = models.SpudcanGeometry(diameter=7.5, height_cone_angle=30.0)
    sample_project.soil_stratigraphy.append(
        models.SoilLayer(
            name="Soft Clay",
            thickness=10.0,
            material=models.MaterialProperties(
                model_name="MohrCoulomb",
                unit_weight=17.5,
                cohesion=15.0,
                friction_angle=2.0
            )
        )
    )
    sample_project.soil_stratigraphy.append(
        models.SoilLayer(
            name="Stiff Sand",
            thickness=20.0,
            material=models.MaterialProperties(
                model_name="HardeningSoil", # Example
                unit_weight=19.5,
                youngs_modulus=50000.0 # Example parameter
            )
        )
    )
    sample_project.loading = models.LoadingConditions(
        vertical_preload=1500.0,
        target_penetration_or_load=5.0,
        target_type="penetration"
    )
    sample_project.analysis_control = models.AnalysisControlParameters(
        meshing_global_coarseness="Fine"
    )
    sample_project.water_table_depth = 2.0

    test_filepath = "test_project.json"

    # Test save
    print("\n--- Testing Save ---")
    if save_project(sample_project, test_filepath):
        print(f"'{test_filepath}' saved successfully.")

        # Test load
        print("\n--- Testing Load ---")
        loaded_project = load_project(test_filepath)
        if loaded_project:
            print(f"'{test_filepath}' loaded successfully.")
            # Basic check (can be more thorough)
            if loaded_project.project_name == sample_project.project_name and \
               len(loaded_project.soil_stratigraphy) == len(sample_project.soil_stratigraphy) and \
               loaded_project.soil_stratigraphy[0].material.cohesion == sample_project.soil_stratigraphy[0].material.cohesion:
                print("Basic content verification PASSED.")
            else:
                print("Basic content verification FAILED.")
                print("Original:", sample_project)
                print("Loaded:", loaded_project)
        else:
            print(f"Failed to load '{test_filepath}'.")
    else:
        print(f"Failed to save '{test_filepath}'.")

    # Clean up test file
    if os.path.exists(test_filepath):
        # os.remove(test_filepath)
        print(f"\nNote: Test file '{test_filepath}' was not removed for inspection.")

    # Test loading a non-existent file
    print("\n--- Testing Load Non-Existent File ---")
    non_existent_project = load_project("non_existent_project.json")
    if non_existent_project is None:
        print("Loading non-existent file handled correctly (returned None).")
    else:
        print("Loading non-existent file FAILED to handle correctly.")

    # Test loading a malformed JSON file (manual step: create a malformed_project.json)
    # malformed_filepath = "malformed_project.json"
    # with open(malformed_filepath, "w") as f:
    #    f.write("{'project_name': 'Malformed',,}") # Example of malformed JSON
    # print("\n--- Testing Load Malformed File ---")
    # malformed_project = load_project(malformed_filepath)
    # if malformed_project is None:
    #    print("Loading malformed file handled correctly (returned None).")
    # else:
    #    print("Loading malformed file FAILED to handle correctly.")
    # if os.path.exists(malformed_filepath):
    #    os.remove(malformed_filepath)

    # A note on the from_dict helper for dataclasses:
    # The provided `dataclass_from_dict` is very basic.
    # For robust production code, especially with complex nested structures,
    # unions, or optional fields with defaults that differ from None,
    # a dedicated library like `dacite` (for pure dataclasses) or using `Pydantic`
    # for model definitions would be highly recommended.
    # Pydantic models, for example, have built-in `.parse_obj()` and `.json()` methods.
    print("\n--- End of project_io.py tests ---")

# Need to import models for the type hint in the functions
from . import models # This line might cause issues if run directly without package context
from typing import Optional # Ensure Optional is imported for return type hints
