"""
Core data models for the PLAXIS 3D Spudcan Automation Tool.

These classes represent the main entities and their parameters, primarily used for
storing project data, communicating with the PLAXIS application, and displaying results.
The definitions are based on requirements outlined in the Project Requirements Document (PRD),
particularly Section 4.1.2 (Input Parameter Sections) and related sections.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

SoilMaterialName = str # Type alias for soil model names, e.g., "MohrCoulomb", "HardeningSoil"

@dataclass
class SpudcanGeometry:
    """
    Represents the spudcan's geometric properties.
    PRD Ref: 4.1.2.1
    """
    diameter: Optional[float] = None # Spudcan diameter, typically in meters.
    height_cone_angle: Optional[float] = None # For conical spudcans, this is the cone angle (half-apex) in degrees.
                                            # For other types, interpretation might vary (e.g., could be total height).
    # Example: spudcan_type: Optional[str] = "Conical" # Could be "Conical", "Flat", etc.

@dataclass
class MaterialProperties:
    """
    Represents the properties of a soil material.
    Parameters will vary based on the selected soil model (e.g., Mohr-Coulomb, Hardening Soil).
    Units should be consistent with the project's unit system (default: SI - m, kN, kPa, deg).
    PRD Ref: 4.1.2.2
    """
    model_name: Optional[SoilMaterialName] = None # PLAXIS soil model name (e.g., "MohrCoulomb", "HardeningSoil").
    Identification: Optional[str] = None      # User-defined name for the material.

    # General parameters (common across many models)
    gammaUnsat: Optional[float] = None  # Unsaturated unit weight (e.g., kN/m^3).
    gammaSat: Optional[float] = None    # Saturated unit weight (e.g., kN/m^3).
    eInit: Optional[float] = None       # Initial void ratio.

    # Common Elastic Properties (units depend on model, typically stress units for E)
    Eref: Optional[float] = None        # Reference Young's modulus (e.g., kPa or MPa). For MC, often E'.
    nu: Optional[float] = None          # Poisson's ratio (dimensionless). For MC, often nu'.

    # Common Strength Properties (Mohr-Coulomb based)
    cRef: Optional[float] = None        # Effective Cohesion (e.g., kPa).
    phi: Optional[float] = None         # Effective Friction angle (degrees).
    psi: Optional[float] = None         # Dilatancy angle (degrees). Typically 0 for undrained, phi-30 for dense sands.

    # Parameters specific to Hardening Soil model
    E50ref: Optional[float] = None      # Secant stiffness in standard drained triaxial test (e.g., kPa).
    Eoedref: Optional[float] = None     # Tangent stiffness for primary oedometer loading (e.g., kPa).
    Eurref: Optional[float] = None      # Unloading/reloading stiffness (e.g., kPa). Usually EurRef = 3 * E50Ref.
    m: Optional[float] = None           # Power for stress-level dependency of stiffness (dimensionless).
    pRef: Optional[float] = None        # Reference stress for stiffnesses (e.g., kPa).
    K0NC: Optional[float] = None        # K0-value for normal consolidation (advanced tab, dimensionless).
    Rf: Optional[float] = None          # Failure ratio qf/qa (advanced tab, dimensionless).
    # Note: For HardeningSoil, 'nu' field is often used for nu_ur (Poisson's ratio for unloading-reloading).

    # Parameters specific to Soft Soil model
    lambda_star: Optional[float] = None # Modified compression index (λ*) (dimensionless).
    kappa_star: Optional[float] = None  # Modified swelling index (κ*) (dimensionless).
    # Note: SoftSoil also uses nu (as nu_ur), cRef, phi, psi from common properties.
    # Advanced SoftSoil parameters like M, K0NC for creep are not explicitly listed here but can go in other_params.

    other_params: Dict[str, Any] = field(default_factory=dict) # For additional or model-specific parameters.

@dataclass
class SoilLayer:
    """
    Represents a single soil layer in the stratigraphy.
    PRD Ref: 4.1.2.2
    """
    name: str = "DefaultLayer"              # User-defined name or ID for the layer.
    thickness: Optional[float] = None       # Thickness of the soil layer (e.g., meters).
    material: MaterialProperties = field(default_factory=MaterialProperties) # Material properties for this layer.

@dataclass
class LoadingConditions:
    """
    Represents the loading conditions for the spudcan penetration analysis.
    PRD Ref: 4.1.2.3
    """
    vertical_preload: Optional[float] = None  # Magnitude of vertical pre-load (e.g., kN).
    target_penetration_or_load: Optional[float] = None # Value for the target control (e.g., m for penetration, kN for load).
    target_type: Optional[str] = None         # Type of target control: "penetration" or "load".

@dataclass
class AnalysisControlParameters:
    """
    Represents parameters controlling the PLAXIS analysis execution, including meshing and calculation phases.
    PRD Ref: 4.1.2.4
    """
    meshing_global_coarseness: Optional[str] = "Medium" # Global mesh coarseness setting in PLAXIS.
    meshing_refinement_spudcan: Optional[bool] = False  # Whether to apply local mesh refinement to the spudcan area.

    initial_stress_method: Optional[str] = "K0Procedure" # Method for initial stress calculation (e.g., "K0Procedure", "GravityLoading").

    # Iteration/Deformation control parameters (defaults often from PLAXIS).
    MaxSteps: Optional[int] = None          # Max number of calculation steps for a phase (e.g., Deform.MaxSteps).
    MaxStepsStored: Optional[int] = None    # Max number of steps with full results stored (e.g., Phase.MaxStepsStored).
    ToleratedError: Optional[float] = None  # Tolerated error for iterative procedure (e.g., Deform.ToleratedError).
    MinIterations: Optional[int] = None     # Desired minimum iterations per step (e.g., Deform.MinIterations).
    MaxIterations: Optional[int] = None     # Desired maximum iterations per step (e.g., Deform.MaxIterations).
    OverRelaxationFactor: Optional[float] = None # Over-relaxation factor (e.g., Deform.OverRelaxation).
    UseArcLengthControl: Optional[bool] = None   # Whether to use arc-length control (e.g., Deform.ArcLengthControl).
    UseLineSearch: Optional[bool] = None         # Whether to use line search (e.g., Deform.UseLineSearch).
    ResetDispToZero: Optional[bool] = False      # Reset displacements to zero before a calculation phase.
    TimeInterval: Optional[float] = None         # Time interval for consolidation/dynamic phases (e.g., seconds or days).

@dataclass
class ProjectSettings:
    """
    Main container for all project-related settings, input data, and configurations.
    Aggregates all other specific data models.
    PRD Ref: 4.1.1.4 (Project Information), and various input sections.
    """
    project_name: Optional[str] = "Untitled Project" # User-defined project name.
    job_number: Optional[str] = None                 # Optional job number for identification.
    analyst_name: Optional[str] = None               # Optional name of the analyst.

    spudcan: SpudcanGeometry = field(default_factory=SpudcanGeometry)
    soil_stratigraphy: List[SoilLayer] = field(default_factory=list)
    water_table_depth: Optional[float] = None # Depth of the water table from ground surface (e.g., meters, positive downwards). PRD 4.1.2.2.3

    loading: LoadingConditions = field(default_factory=LoadingConditions)
    analysis_control: AnalysisControlParameters = field(default_factory=AnalysisControlParameters)

    # Application-specific configuration
    plaxis_installation_path: Optional[str] = None # Path to PLAXIS executable. PRD 4.1.7.1
    units_system: Optional[str] = "SI"             # Selected unit system (e.g., "SI"). PRD 4.1.7.3

    # Placeholder for API connection details if they were to be stored per project
    # plaxis_api_input_port: Optional[int] = None
    # plaxis_api_output_port: Optional[int] = None
    # plaxis_api_password: Optional[str] = None

    analysis_results: Optional['AnalysisResults'] = None # To store results associated with these settings


@dataclass
class AnalysisResults:
    """
    Stores key results obtained from the PLAXIS analysis.
    PRD Ref: 4.1.6 (Results Display Section)
    """
    final_penetration_depth: Optional[float] = None # Final penetration depth achieved (e.g., meters).
    peak_vertical_resistance: Optional[float] = None# Peak vertical load/resistance encountered (e.g., kN).

    # List of dictionaries, where each dictionary represents a data point on the curve.
    # Example: [{'penetration': 0.1, 'load': 100.5}, {'penetration': 0.2, 'load': 250.7}, ...]
    # 'penetration' values are typically absolute depths (e.g., meters).
    # 'load' values are typically absolute vertical forces (e.g., kN).
    load_penetration_curve_data: Optional[List[Dict[str, float]]] = None

    # Placeholder for other potential results:
    # soil_pressures_at_points: Optional[Dict[str, float]] = None # e.g. {'point_name': pressure_value}
    # contour_plot_image_path: Optional[str] = None # Path to a saved contour plot image

if __name__ == '__main__':
    # Example usage (for testing the models and demonstrating structure)
    settings = ProjectSettings(
        project_name="Test Spudcan Project",
        job_number="TSP-001",
        analyst_name="J. Doe"
    )
    settings.spudcan = SpudcanGeometry(diameter=6.0, height_cone_angle=30.0)

    clay_material = MaterialProperties(
        model_name="MohrCoulomb",
        Identification="SoftClay",
        gammaUnsat=17.0, gammaSat=18.0, eInit=1.0,
        Eref=3000.0, nu=0.35,
        cRef=15.0, phi=0.0, psi=0.0
    )
    sand_material = MaterialProperties(
        model_name="HardeningSoil",
        Identification="DenseSand",
        gammaUnsat=19.0, gammaSat=21.0, eInit=0.6,
        E50ref=50000.0, Eoedref=50000.0, Eurref=150000.0, m=0.5,
        cRef=1.0, phi=35.0, psi=5.0, pRef=100.0
    )
    settings.soil_stratigraphy = [
        SoilLayer(name="Top Clay", thickness=5.0, material=clay_material),
        SoilLayer(name="Dense Sand", thickness=10.0, material=sand_material)
    ]
    settings.water_table_depth = -2.0 # 2m above ground surface, or set to positive for below ground.

    settings.loading = LoadingConditions(
        vertical_preload=1000.0,
        target_type="penetration",
        target_penetration_or_load=3.0
    )
    settings.analysis_control = AnalysisControlParameters(
        meshing_global_coarseness="Medium",
        MaxStepsStored=100
    )

    print("--- Example ProjectSettings ---")
    print(settings)

    results = AnalysisResults(
        final_penetration_depth=2.85,
        peak_vertical_resistance=5500.0,
        load_penetration_curve_data=[
            {'penetration': 0.0, 'load': 0.0},
            {'penetration': 1.0, 'load': 2000.0},
            {'penetration': 2.0, 'load': 4500.0},
            {'penetration': 2.85, 'load': 5500.0},
        ]
    )
    print("\n--- Example AnalysisResults ---")
    print(results)
