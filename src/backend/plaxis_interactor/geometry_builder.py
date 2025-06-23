"""
Generates PLAXIS API callables for creating spudcan geometry.
PRD Ref: Task 3.2 (Spudcan Geometry Command Generation)

This module translates high-level spudcan parameters from `SpudcanGeometry`
into a sequence of Python functions (callables). Each callable, when executed
with a PLAXIS input global object (g_i), will perform specific API actions
to create or modify geometry in the PLAXIS model.
"""

import math # For trigonometric calculations (e.g., tan for cone height)
from typing import List, Callable, Any # For type hinting
from ..models import SpudcanGeometry # Relative import from parent package

# --- Main Function to Generate Spudcan Geometry Callables ---

def generate_spudcan_geometry_callables(spudcan_model: SpudcanGeometry) -> List[Callable[[Any], None]]:
    """
    Generates a list of Python callables to create the spudcan geometry in PLAXIS
    using its Python API.

    The spudcan is currently modeled as a simple cone pointing downwards.
    The base of the cone is at z=0, centered at (0,0,0). The apex points in the -z direction.

    Args:
        spudcan_model: The SpudcanGeometry data model containing parameters like
                       diameter and cone angle.

    Returns:
        A list of callable functions. Each function takes the PLAXIS input global
        object (g_i) as an argument and executes one or more API commands.
        Returns an empty list if essential parameters are missing or invalid.

    Assumptions:
    - The PLAXIS global input object (g_i) provided to the callables will have
      methods like `g_i.cone()`, `g_i.rename()`, etc., as per the PLAXIS scripting reference.
    - The spudcan is modeled as a single conical volume. More complex geometries (e.g., with
      a cylindrical section, or modeled as shell plates) would require different callables.
    - The coordinate system assumes z is vertical, with -z being downwards.
    - The spudcan apex is intended to be the point of initial soil contact.
    - Material properties and structural behavior (e.g., rigid body, deformable plate)
      are handled separately, likely after this geometry creation step or by assigning
      properties to the created volume/surfaces.
    - The `spudcan_model.height_cone_angle` is the half-apex angle (angle between the cone's
      axis and its slant surface).
    """
    callables: List[Callable[[Any], None]] = []

    # --- Input Validation ---
    if spudcan_model.diameter is None or spudcan_model.diameter <= 0:
        print("Error in generate_spudcan_geometry_callables: Spudcan diameter must be defined and positive.")
        return callables # Return empty list, no geometry can be created

    if spudcan_model.height_cone_angle is None or \
       not (0 < spudcan_model.height_cone_angle < 90):
        print("Error in generate_spudcan_geometry_callables: Spudcan cone angle must be defined and between 0 and 90 degrees (exclusive).")
        return callables

    # --- Parameter Calculation ---
    radius = spudcan_model.diameter / 2.0
    cone_angle_deg = spudcan_model.height_cone_angle

    # Calculate cone height (H) based on radius (R) and half-apex angle (alpha):
    # tan(alpha) = R / H  =>  H = R / tan(alpha)
    cone_angle_rad = math.radians(cone_angle_deg)
    height = radius / math.tan(cone_angle_rad)

    # Define a descriptive name for the spudcan volume in PLAXIS
    spudcan_volume_name = "Spudcan_ConeVolume"

    # --- Callable for Creating the Cone ---
    def create_cone_callable(g_i: Any) -> None:
        """
        Callable to create the spudcan cone volume.
        PLAXIS `cone` command/API details:
        - `g_i.cone(Radius, Height, TopRadius, BaseCenterCoordinates, AxisVector)` (conceptual, actual API might vary)
        - Radius: Radius of the cone's base.
        - Height: Absolute height of the cone.
        - TopRadius: For a perfect cone, this is 0. For a frustum, it's non-zero.
        - BaseCenterCoordinates: Tuple (x,y,z) for the center of the cone's base.
        - AxisVector: Tuple (dx,dy,dz) for the direction vector of the cone's axis,
                      pointing from the base towards the apex.

        This implementation assumes:
        - Base of the cone is at (0,0,0).
        - Cone points downwards, so axis is (0,0,-1).
        - The created volume is a "soil volume" by default if `g_i.cone` behaves like the CLI `cone` command.
          If it needs to be a structural element or rigid body, further operations or different
          creation methods (e.g., creating surfaces and assigning plate properties, or using `g_i.rigidbodyA`)
          would be required.
        """
        print(f"  PLAXIS API CALL (conceptual): Creating cone for spudcan.")
        print(f"    Radius: {radius}, Height: {height:.3f}, TopRadius: 0")
        print(f"    BaseCenter: (0,0,0), AxisVector: (0,0,-1)")

        # Actual PLAXIS API call for creating a cone.
        # The exact method and parameters might differ slightly based on the PLAXIS version
        # and whether it's a direct geometry creation or a soil volume creation.
        # Example: g_i.cone(radius, height, 0, (0,0,0), (0,0,-1))
        # If g_i.cone directly returns the created object:
        # cone_object = g_i.cone(radius, height, TopRadius=0, BaseCenter=(0,0,0), Axis=(0,0,-1))
        # If it doesn't, one might need to access it via g_i.Volumes[-1] or similar.

        # The PLAXIS documentation for `cone` command (Python API examples) shows:
        # g_i.cone(Radius, Height, BaseCenter_tuple, Axis_tuple)
        # BaseCenter is the center of the cone base. AxisVector points from base towards apex.
        # For a downward pointing cone with base at (0,0,0), BaseCenter is (0,0,0) and Axis is (0,0,-1).
        # The command returns a list of created objects; the first is usually the volume.
        try:
            # Parameters for our spudcan cone:
            # Radius: radius
            # Height: height (calculated positive value)
            # TopRadius: 0 (implied for g_i.cone, not specified as a separate param in API like CLI)
            # BaseCenter: (0,0,0)
            # AxisVector: (0,0,-1) (PLAXIS typically takes Z positive upwards, so -1 for downwards)

            # Explicitly creating a non-truncated cone.
            # The documentation examples for `g_i.cone(R, H, BaseCenter, Axis)` seem most appropriate.
            # Example from docs: volume_g = g_i.cone(2, 5, (1, 2, 3), (5, 7, 12))[0]
            # Here, (1,2,3) is BaseCenter, (5,7,12) is AxisVector.
            # For our case: BaseCenter=(0,0,0), AxisVector=(0,0,-1)
            # Note: PLAXIS might default to Z-axis if AxisVector is omitted for simple cases,
            # but being explicit is better.

            cone_objects = g_i.cone(radius, height, (0,0,0), (0,0,-1))

            if not cone_objects:
                raise Exception("g_i.cone command did not return any objects.")

            # Assuming the first object returned is the cone volume
            cone_volume = cone_objects[0]
            print(f"    Cone volume created successfully via g_i.cone(). Object: {cone_volume}")

            # Rename the created cone volume
            g_i.rename(cone_volume, spudcan_volume_name)
            print(f"    Renamed cone volume to '{spudcan_volume_name}'.")

            print(f"  Spudcan cone volume '{spudcan_volume_name}' defined: Diameter={spudcan_model.diameter}, "
                  f"Calculated Height={height:.3f} (from angle {cone_angle_deg} deg).")
        except Exception as e:
            # This catch is general. Specific PlxScriptingError should be caught by _execute_api_commands.
            print(f"    ERROR during spudcan cone creation/renaming using direct API: {e}")
            # Re-raise or handle appropriately if necessary. For a callable, raising allows
            # _execute_api_commands in PlaxisInteractor to catch and map it.
            raise

    callables.append(create_cone_callable)

    # --- Future Enhancements / Other Geometry Parts ---
    # If the spudcan includes a cylindrical section above the cone:
    # 1. Calculate cylinder height (from spudcan_model, if provided).
    # 2. Define a callable for g_i.cylinder(radius, height, base_center_coords, axis_vector).
    #    The base_center for the cylinder would be on top of the cone's base (e.g., (0,0,0) if cone base is at z=0).
    #
    # If the spudcan is to be modeled as a rigid body or with plate elements:
    # - Rigid Body: After creating the volume, a callable for `g_i.createrigidbody(VolumeObject, ...)`
    # - Plates: Instead of `g_i.cone` for volume, create surfaces (e.g., `g_i.createsurface` from points
    #   defining the cone) and then assign plate properties `g_i.createplate(SurfaceObject, Material, Thickness)`.
    #   This is significantly more complex geometrically.
    #
    # Material Assignment:
    # - The created volume (`Spudcan_ConeVolume`) is initially a "soil volume" if created by `g_i.cone` (like CLI).
    # - It needs to be assigned appropriate material properties (e.g., steel if it's a structure, or made
    #   part of a rigid body). This is typically done in a separate step after geometry creation.
    #   e.g., `g_i.setmaterial(g_i.Volumes['Spudcan_ConeVolume'], material_object_for_spudcan)`
    #   This module focuses only on the geometry creation part.

    if not callables:
        print(f"Warning: No geometry callables generated for spudcan D={spudcan_model.diameter}, Angle={spudcan_model.height_cone_angle}.")

    return callables


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    print("--- Testing Spudcan Geometry Callable Generation ---")

    # Mock PLAXIS g_i object for testing the callables' structure (not actual PLAXIS interaction)
    class MockG_i:
        def __init__(self):
            self.Volumes = [] # Simulate a list of volumes
            self.last_command = None
            self.log = []

        def command(self, cmd_str: str):
            self.log.append(f"COMMAND: {cmd_str}")
            # Simulate object creation for rename
            if "cone" in cmd_str:
                self.Volumes.append(f"Volume_{len(self.Volumes)+1}")
            self.last_command = cmd_str
            print(f"  MockG_i.command executed: {cmd_str}")

        def rename(self, obj_ref: Any, new_name: str):
            self.log.append(f"RENAME: {obj_ref} to {new_name}")
            print(f"  MockG_i.rename executed: {obj_ref} to {new_name}")

        # Add other methods like cone, cylinder if directly callable in real API
        # def cone(self, radius, height, top_radius, base_center, axis_vector):
        #     cmd_str = f"cone {radius} {height} {top_radius} {base_center} {axis_vector}"
        #     self.log.append(f"DIRECT_API_CALL: {cmd_str}")
        #     print(f"  MockG_i.cone executed: {cmd_str}")
        #     new_vol = f"ConeVolume_{len(self.Volumes)+1}"
        #     self.Volumes.append(new_vol)
        #     return new_vol # Assume it returns the created object or its name/reference

    # Test case 1: Valid spudcan
    sample_spudcan_valid = SpudcanGeometry(diameter=6.0, height_cone_angle=30.0)
    print(f"\nTesting with valid spudcan: D={sample_spudcan_valid.diameter}, Angle={sample_spudcan_valid.height_cone_angle}")
    generated_callables_valid = generate_spudcan_geometry_callables(sample_spudcan_valid)
    print(f"Generated {len(generated_callables_valid)} callables.")

    mock_g_i_instance_valid = MockG_i()
    for i, callable_func in enumerate(generated_callables_valid):
        print(f"Executing callable {i+1}/{len(generated_callables_valid)} ({getattr(callable_func, '__name__', 'lambda')})...")
        try:
            callable_func(mock_g_i_instance_valid)
        except Exception as e:
            print(f"  Error executing callable: {e}")
    print("Log of mock g_i commands for valid spudcan:")
    for entry in mock_g_i_instance_valid.log:
        print(f"  - {entry}")

    # Test case 2: Invalid cone angle
    sample_spudcan_invalid_angle = SpudcanGeometry(diameter=6.0, height_cone_angle=90.0)
    print(f"\nTesting with invalid cone angle: D={sample_spudcan_invalid_angle.diameter}, Angle={sample_spudcan_invalid_angle.height_cone_angle}")
    generated_callables_invalid = generate_spudcan_geometry_callables(sample_spudcan_invalid_angle)
    print(f"Generated {len(generated_callables_invalid)} callables (expected 0).")
    assert len(generated_callables_invalid) == 0

    # Test case 3: Missing diameter
    sample_spudcan_no_diameter = SpudcanGeometry(height_cone_angle=30.0) # Diameter defaults to None
    print(f"\nTesting with missing diameter: Angle={sample_spudcan_no_diameter.height_cone_angle}")
    generated_callables_no_dia = generate_spudcan_geometry_callables(sample_spudcan_no_diameter)
    print(f"Generated {len(generated_callables_no_dia)} callables (expected 0).")
    assert len(generated_callables_no_dia) == 0

    print("\n--- End of Geometry Builder Callable Generation Tests ---")
