"""
Core data models for the PLAXIS 3D Spudcan Automation Tool.
These classes represent the main entities and their parameters as defined
in the PRD (Section 4.1.2 and others).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any # Any for soil params initially

# Forward declaration for type hinting if needed, or define simple types
SoilMaterialName = str # e.g., "MohrCoulomb", "HardeningSoil"

@dataclass
class SpudcanGeometry:
    """
    Represents the spudcan's geometric properties.
    PRD Ref: 4.1.2.1
    """
    diameter: Optional[float] = None
    height_cone_angle: Optional[float] = None # Could be height or angle depending on definition
    # Add other relevant geometric parameters as identified
    # e.g., spudcan_type: Optional[str] = None

@dataclass
class MaterialProperties:
    """
    Represents the properties of a soil material.
    Parameters will vary based on the selected soil model.
    PRD Ref: 4.1.2.2
    """
    model_name: Optional[SoilMaterialName] = None
    unit_weight: Optional[float] = None
    # Common parameters (can be expanded or made more specific)
    cohesion: Optional[float] = None
    friction_angle: Optional[float] = None
    youngs_modulus: Optional[float] = None
    poissons_ratio: Optional[float] = None
    # For more complex models, parameters might be stored in a dictionary
    # e.g. other_params: Dict[str, Any] = field(default_factory=dict)
    # Specific parameters for Hardening Soil, etc., would go here or in other_params
    # For now, keeping it simple, will be expanded based on actual PLAXIS needs.

@dataclass
class SoilLayer:
    """
    Represents a single soil layer in the stratigraphy.
    PRD Ref: 4.1.2.2
    """
    name: str = "DefaultLayer" # Layer name or ID
    thickness: Optional[float] = None
    # elevation_top: Optional[float] = None # Alternative to thickness for defining stratigraphy
    material: MaterialProperties = field(default_factory=MaterialProperties)
    # Add other layer-specific properties if any

@dataclass
class LoadingConditions:
    """
    Represents the loading conditions for the analysis.
    PRD Ref: 4.1.2.3
    """
    vertical_preload: Optional[float] = None
    target_penetration_or_load: Optional[float] = None # Value
    target_type: Optional[str] = None # "penetration" or "load"
    # load_steps_or_displacement_increments: Optional[Any] = None # Define structure later

@dataclass
class AnalysisControlParameters:
    """
    Represents parameters controlling the PLAXIS analysis execution.
    PRD Ref: 4.1.2.4
    """
    meshing_global_coarseness: Optional[str] = "Medium" # Example default
    # meshing_refinement_spudcan: Optional[str] = "Medium"
    initial_stress_method: Optional[str] = "K0Procedure" # Example default
    # calculation_phases_config: Optional[Any] = None # Define structure later
    # tolerated_error: Optional[float] = None # Use PLAXIS default initially
    # max_iterations: Optional[int] = None # Use PLAXIS default initially

@dataclass
class ProjectSettings:
    """
    Main container for all project-related settings and data.
    PRD Ref: 4.1.1.4 (Project Information), and aggregates other models.
    """
    project_name: Optional[str] = "Untitled Project"
    job_number: Optional[str] = None
    analyst_name: Optional[str] = None

    spudcan: SpudcanGeometry = field(default_factory=SpudcanGeometry)
    soil_stratigraphy: List[SoilLayer] = field(default_factory=list)
    water_table_depth: Optional[float] = None # PRD 4.1.2.2.3

    loading: LoadingConditions = field(default_factory=LoadingConditions)
    analysis_control: AnalysisControlParameters = field(default_factory=AnalysisControlParameters)

    # Configuration related to the tool itself
    plaxis_installation_path: Optional[str] = None # PRD 4.1.7.1
    units_system: Optional[str] = "SI" # PRD 4.1.7.3, example default

@dataclass
class AnalysisResults:
    """
    Placeholder for storing results from the PLAXIS analysis.
    PRD Ref: 4.1.6
    """
    final_penetration_depth: Optional[float] = None
    peak_vertical_resistance: Optional[float] = None
    load_penetration_curve_data: Optional[List[Dict[str, float]]] = None # e.g., [{'load': x, 'penetration': y}, ...]
    # Other results like soil pressures, contour plot image paths, etc.

if __name__ == '__main__':
    # Example usage (for testing the models)
    settings = ProjectSettings(project_name="Test Spudcan Project")
    settings.spudcan.diameter = 6.0
    settings.soil_stratigraphy.append(
        SoilLayer(
            name="Top Clay",
            thickness=5.0,
            material=MaterialProperties(
                model_name="MohrCoulomb",
                unit_weight=18.0,
                cohesion=20.0,
                friction_angle=0.0
            )
        )
    )
    settings.soil_stratigraphy.append(
        SoilLayer(
            name="Dense Sand",
            thickness=10.0,
            material=MaterialProperties(
                model_name="MohrCoulomb",
                unit_weight=20.0,
                cohesion=1.0,
                friction_angle=35.0
            )
        )
    )
    settings.loading.vertical_preload = 1000.0
    print(settings)

    results = AnalysisResults(final_penetration_depth=3.5, peak_vertical_resistance=5000.0)
    print(results)
