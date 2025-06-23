"""
Main orchestrator for interacting with PLAXIS.
This module will coordinate calls to helper modules for command generation,
process execution, and results parsing.
PRD Ref: Tasks 3.7, 3.9
"""

from ..models import ProjectSettings, AnalysisResults # Use .. for relative import from parent package
from . import geometry_builder
from . import soil_builder
from . import calculation_builder
from . import results_parser # Assuming this will be created

from typing import List, Dict, Any, Optional

class PlaxisInteractor:
    """
    Handles the overall process of interacting with PLAXIS, including
    model setup, calculation execution, and results extraction.
    """

    def __init__(self, plaxis_path: Optional[str] = None):
        """
        Initializes the PlaxisInteractor.

        Args:
            plaxis_path (Optional[str]): Path to the PLAXIS installation or executable.
                                         This might be needed for CLI interaction.
        """
        self.plaxis_path = plaxis_path
        self.g_i = None # Placeholder for PLAXIS global interface object (if using API)
        self.s_i = None # Placeholder for PLAXIS server object (if using API)
        self.output_port = None # Port for PLAXIS output server if different
        self.use_api = False # Flag to determine interaction method
        print(f"PlaxisInteractor initialized. PLAXIS path: {plaxis_path or 'Not specified (assuming API in environment)'}")
        # Try to connect to API by default if plaxis_path is not emphasized for CLI
        if not plaxis_path or "API" in (plaxis_path or ""): # Simple check
            self.use_api = self._connect_to_plaxis_api()
            if not self.use_api and plaxis_path:
                 print("API connection failed, will try CLI if plaxis_path is suitable for executable.")
            elif not self.use_api:
                 print("API connection failed and no PLAXIS executable path for CLI.")
        else:
            print("PLAXIS executable path provided, will prioritize CLI.")


    def _connect_to_plaxis_api(self, port: int = 10000, password: str = "plaxis") -> bool:
        """
        Attempts to connect to the PLAXIS Python API.
        This would involve importing the PLAXIS scripting library and establishing a connection.
        """
        print(f"Attempting to connect to PLAXIS API on port {port}...")
        try:
            # This is the typical way to import and connect as per PLAXIS documentation
            from plxscripting.easy import new_server
            self.s_i, self.g_i = new_server('localhost', port, password=password)
            # Perform a simple check to confirm connection
            _ = self.g_i.Project # Access a property to see if it fails
            print(f"Successfully connected to PLAXIS API (g_i type: {type(self.g_i)}).")
            # TODO: Determine output port for later results extraction if needed
            # self.output_port = self.g_i.get_output_port() # Hypothetical
            return True
        except ImportError:
            print("PLAXIS plxscripting library not found. API connection failed.")
            self.s_i, self.g_i = None, None
            return False
        except Exception as e:
            print(f"Error connecting to PLAXIS API: {e}")
            self.s_i, self.g_i = None, None
            return False

    def _execute_plaxis_commands_cli(self, commands: List[str], script_filename: str = "temp_plaxis_script.p3dscript") -> bool:
        """
        Executes a list of PLAXIS commands via the CLI by writing them to a script file.
        Actual subprocess execution and error/output capture needed.
        """
        if not self.plaxis_path or not "Plaxis3DInput.exe" in self.plaxis_path : # Basic check for executable
             print(f"Error: PLAXIS executable path not configured correctly for CLI: {self.plaxis_path}")
             return False

        print(f"Writing {len(commands)} commands to script file '{script_filename}' for CLI execution.")
        try:
            with open(script_filename, 'w') as f:
                for cmd in commands:
                    f.write(cmd + '\n') # PLAXIS commands are usually newline separated

            print(f"Executing PLAXIS CLI: {self.plaxis_path} --runscript=\"{os.path.abspath(script_filename)}\"")

            # --- Actual Subprocess Execution ---
            # import subprocess
            # import os
            # process = subprocess.Popen(
            #     [self.plaxis_path, f"--runscript={os.path.abspath(script_filename)}"],
            #     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            # )
            # stdout, stderr = process.communicate()
            # if process.returncode == 0:
            #     print("PLAXIS script executed successfully via CLI.")
            #     print("STDOUT:", stdout)
            #     return True
            # else:
            #     print("Error executing PLAXIS script via CLI.")
            #     print("Return Code:", process.returncode)
            #     print("STDOUT:", stdout)
            #     print("STDERR:", stderr) # PLAXIS often outputs errors to stdout as well
            #     # Try to map common errors from stderr or stdout
            #     if stderr: self.map_plaxis_error(stderr)
            #     elif stdout: self.map_plaxis_error(stdout) # Check stdout too
            #     return False
            print("STUB: _execute_plaxis_commands_cli - subprocess part commented out. Returning True for now.")
            return True # Placeholder
        except IOError as e:
            print(f"IOError writing/reading script file {script_filename}: {e}")
            return False
        finally:
            # if os.path.exists(script_filename):
            #     os.remove(script_filename) # Clean up script file
            pass


    def _execute_plaxis_api_commands(self, commands: List[str]) -> bool:
        """
        Executes a list of PLAXIS commands using the g_i (global input) object.
        Assumes commands are in the format expected by g_i.command() or direct method calls.
        """
        if not self.g_i:
            print("PLAXIS API (g_i) not available for executing commands.")
            return False

        print(f"Executing {len(commands)} commands via PLAXIS API (g_i)...")
        all_successful = True
        for cmd_string in commands:
            if cmd_string.strip().startswith("#") or not cmd_string.strip(): # Skip comments/empty lines
                continue
            print(f"  API CMD: {cmd_string}")
            try:
                # This is a general way to execute CLI-like commands via API.
                # More direct API calls (e.g., g_i.point(...), g_i.soilmat(...)) are preferred
                # if the command generation layer produces Pythonic API calls instead of strings.
                # For now, assume command strings are passed.
                self.g_i.command(cmd_string)
            except Exception as e:
                error_message = f"Error executing API command '{cmd_string}': {e}"
                print(error_message)
                self.map_plaxis_error(str(e)) # Try to map the error
                all_successful = False
                # Decide whether to stop on first error or try all commands
                # break # Option to stop on first error

        return all_successful


    def setup_model_in_plaxis(self, project_settings: ProjectSettings) -> bool:
        """
        Sets up the entire geotechnical model in PLAXIS based on project settings.
        This orchestrates calls to various builder modules.
        Args:
            project_settings: The ProjectSettings object containing all model data.

        Returns:
            True if model setup was successful, False otherwise.
        """
        print("Starting PLAXIS model setup...")

        if self.use_api and not self.g_i:
            print("Attempting to re-connect to PLAXIS API for model setup.")
            if not self._connect_to_plaxis_api(): # Use default port/password
                 print("Failed to connect to PLAXIS API. Model setup aborted.")
                 return False
        elif not self.use_api and not self.plaxis_path:
            print("Neither API connected nor PLAXIS CLI path available. Model setup aborted.")
            return False

        # Consolidate all command generation.
        # The builder functions should ideally return Python API calls if use_api is True,
        # or CLI command strings otherwise. For now, they return CLI-like strings.

        # Start with a clean slate in PLAXIS (optional, depends on workflow)
        # For API: self.g_i.new()
        # For CLI: a script might start with 'new'
        initial_commands = ["new"] # Start a new project in PLAXIS
        # It's also good to set project units and title early
        # Based on all.md Project object: set Project.UnitLength "m", etc.
        if project_settings.units_system == "SI": # Assuming SI for now
            initial_commands.append('set Project.UnitLength "m"')
            initial_commands.append('set Project.UnitForce "kN"')
            initial_commands.append('set Project.UnitTime "day"') # Or "s" - be consistent
        if project_settings.project_name:
             initial_commands.append(f'set Project.Title "{project_settings.project_name}"')

        all_setup_commands = initial_commands

        # 1. Materials first, as they are referenced by soil layers
        unique_materials_generated = set()
        material_definitions_commands = []
        for layer in project_settings.soil_stratigraphy:
            mat_id = (layer.material.model_name, layer.material.unit_weight, layer.material.cohesion, layer.material.friction_angle) # Simple unique ID
            if mat_id not in unique_materials_generated:
                mat_cmds = soil_builder.generate_material_commands(layer.material)
                material_definitions_commands.extend(mat_cmds)
                unique_materials_generated.add(mat_id)
        all_setup_commands.extend(material_definitions_commands)
        print(f"Generated {len(material_definitions_commands)} unique material definition commands.")

        # 2. Soil Stratigraphy (boreholes, layers, water)
        # Assuming a single borehole for now for simplicity, as per PRD context.
        # If multiple boreholes, this would need to iterate or handle complex stratigraphy.
        soil_strat_commands = soil_builder.generate_soil_stratigraphy_commands(
            project_settings.soil_stratigraphy,
            project_settings.water_table_depth
            # borehole_name and coords use defaults
        )
        all_setup_commands.extend(soil_strat_commands)
        print(f"Generated {len(soil_strat_commands)} soil stratigraphy commands.")

        # 3. Geometry (Spudcan)
        # Needs to be created in Structures mode
        all_setup_commands.append("gotostructures")
        geom_commands = geometry_builder.generate_spudcan_commands(project_settings.spudcan)
        all_setup_commands.extend(geom_commands)
        print(f"Generated {len(geom_commands)} spudcan geometry commands.")

        # 4. Loading Conditions (Define load/displacement objects)
        # These are also typically defined in Structures mode if tied to geometry
        loading_def_commands = calculation_builder.generate_loading_commands(project_settings.loading)
        all_setup_commands.extend(loading_def_commands)
        print(f"Generated {len(loading_def_commands)} loading condition definition commands.")

        # 5. Analysis Control (Meshing, Phases) - this involves mode switches
        analysis_ctrl_commands = calculation_builder.generate_analysis_control_commands(
            project_settings.analysis_control,
            project_settings.loading # Pass loading conditions for phase setup
        )
        all_setup_commands.extend(analysis_ctrl_commands)
        print(f"Generated {len(analysis_ctrl_commands)} analysis control commands (includes mesh & phases).")

        # 6. Output Requests (Pre-selection of points for curves)
        output_req_commands = calculation_builder.generate_output_request_commands()
        all_setup_commands.extend(output_req_commands)
        print(f"Generated {len(output_req_commands)} output request commands (conceptual).")

        # Execute all generated commands
        if self.use_api:
            success = self._execute_plaxis_api_commands(all_setup_commands)
        else: # Use CLI
            success = self._execute_plaxis_commands_cli(all_setup_commands)

        if success:
            print("PLAXIS model setup commands processed successfully.")
            # Optionally save the PLAXIS project after setup
            # save_cmd = f"save \"{project_settings.project_name or 'plaxis_model'}.p3d\"" # Ensure path handling
            # if self.use_api: self._execute_plaxis_api_commands([save_cmd])
            # else: self._execute_plaxis_commands_cli([save_cmd])
            return True
        else:
            print("Failed to process PLAXIS model setup commands.")
            return False

    def run_calculation(self, phase_name: Optional[str] = None) -> bool:
        """
        Executes the PLAXIS calculation for a specific phase or all marked phases.
        """
        print(f"Starting PLAXIS calculation for phase: {phase_name or 'all marked phases'}...")

        calc_command = "calculate"
        if phase_name:
            calc_command = f"calculate {phase_name}"
            # For API, it might be: self.g_i.calculate(self.g_i.Phases[phase_name])
            # Or if phase_name is already an object: self.g_i.calculate(phase_name_obj)

        if self.use_api:
            success = self._execute_plaxis_api_commands([calc_command])
        else:
            success = self._execute_plaxis_commands_cli([calc_command])

        if success:
            print("PLAXIS calculation completed successfully.")
            return True
        else:
            print("PLAXIS calculation failed.")
            return False

    def _connect_to_plaxis_output_api(self, port: Optional[int] = None, password: str = "plaxis") -> Any:
        """Placeholder for connecting to PLAXIS Output API."""
        # This would be similar to _connect_to_plaxis_api but for the output server
        # The port might be obtained from g_i after calculation or known.
        # For now, assume g_i can also access results if input and output are linked,
        # or a new g_o object would be created.
        if not port and self.output_port: # If interactor stored it
            port = self.output_port
        elif not port:
            # Try a default output port, e.g., 10001, or get from g_i if possible
            # port = self.g_i.get_output_port() # Hypothetical
            print("Output port not specified, cannot connect to Output API for results.")
            return None

        print(f"STUB: Connecting to PLAXIS Output API on port {port}...")
        # from plxscripting.easy import new_server
        # s_o, g_o = new_server('localhost', port, password)
        # return g_o
        return self.g_i # Simplistic: assume g_i can access results for now if API is used


    def extract_results(self, project_settings: ProjectSettings, phase_to_extract: str = "PenetrationPhase") -> Optional[AnalysisResults]:
        """
        Extracts relevant results from PLAXIS after calculation.
        """
        print("Extracting results from PLAXIS...")
        results = AnalysisResults()

        # Example: Get load-penetration curve data
        # This path would be determined by PLAXIS output conventions or requested output file.
        # conceptual_output_file_path = f"{project_settings.project_name}_outputs/load_penetration.txt"
        # results.load_penetration_curve_data = results_parser.parse_load_penetration_curve(conceptual_output_file_path)
        results.load_penetration_curve_data = [{"load": 0, "penetration": 0}, {"load": 1000, "penetration": 0.5}] # Stub data
        print("Load-penetration curve data parsed (stub).")

        # Example: Get final penetration depth
        # results.final_penetration_depth = results_parser.parse_final_penetration( ... ) # Needs data source
        results.final_penetration_depth = 0.5 # Stub data
        print("Final penetration depth parsed (stub).")

        # Example: Get peak resistance
        # results.peak_vertical_resistance = results_parser.parse_peak_resistance( ... ) # Needs data source
        results.peak_vertical_resistance = 1000 # Stub data
        print("Peak resistance parsed (stub).")

        if results.load_penetration_curve_data or results.final_penetration_depth is not None:
            print("Results extracted successfully (stub).")
            return results
        else:
            print("Failed to extract significant results (stub).")
            return None

    def map_plaxis_error(self, raw_error_message: str) -> str:
        """
        Maps a raw PLAXIS error message to a more user-friendly one.
        PRD Ref: Task 3.9
        """
        print(f"Mapping PLAXIS error: '{raw_error_message}'")
        lower_error = raw_error_message.lower()

        # General numerical issues
        if "convergence not reached" in lower_error or "did not converge" in lower_error:
            return "Numerical Convergence Error: The analysis did not converge. Please check model setup, soil parameters, mesh quality, or load step size. Consider enabling arc-length control if applicable."
        if "numerical stability" in lower_error or "ill-conditioned" in lower_error:
            return "Numerical Stability Issue: The model may be ill-conditioned or unstable. Review boundary conditions, material properties, and mesh."
        if "soil body seems to collapse" in lower_error or "mechanism formed" in lower_error:
            return "Model Collapse: The soil body seems to collapse, indicating a potential failure mechanism. Review loads, soil strengths, and support conditions."

        # Meshing issues
        if "mesh generation failed" in lower_error or "error generating mesh" in lower_error:
            return "Meshing Error: Mesh generation failed. Check geometry for inconsistencies, small features, or complex intersections. Try adjusting mesh coarseness."

        # Input errors
        if "parameter" in lower_error and ("missing" in lower_error or "invalid" in lower_error or "out of range" in lower_error):
            # Try to extract parameter name if possible (very basic)
            param_name_match = re.search(r"parameter\s*['\"]?([^'\"\s]+)['\"]?", lower_error)
            param_info = f" for parameter '{param_name_match.group(1)}'" if param_name_match else ""
            return f"Input Error: An input parameter{param_info} is missing, invalid, or out of range. Please check your inputs."
        if "material" in lower_error and ("not found" in lower_error or "undefined" in lower_error) :
            return "Material Error: A specified material was not found or is undefined. Ensure all materials are correctly defined and assigned."
        if "geometry" in lower_error and ("inconsistent" in lower_error or "invalid" in lower_error):
            return "Geometry Error: The model geometry is inconsistent or invalid. Please check for overlapping or problematic geometric entities."

        # Licensing issues (common pattern)
        if "license" in lower_error or "dongle" in lower_error or "no valid license" in lower_error:
            return "Licensing Error: Could not find a valid PLAXIS license. Please check your license configuration."

        # File I/O
        if "file not found" in lower_error:
            return f"File Not Found Error: A required file could not be found. Details: {raw_error_message}"
        if "cannot open file" in lower_error:
            return f"File Access Error: Cannot open a required file. Check permissions or path. Details: {raw_error_message}"

        # Default if no specific mapping
        # Truncate long generic errors for better display, but keep details for logs
        brief_error = raw_error_message[:200] + "..." if len(raw_error_message) > 200 else raw_error_message
        return f"PLAXIS Error: {brief_error} (See logs for full details)"


if __name__ == '__main__':
    print("\n--- Testing PlaxisInteractor ---")
    # Create dummy project settings for testing
    test_settings = ProjectSettings(
        project_name="InteractorTest",
        plaxis_installation_path="C:/Program Files/Bentley/PLAXIS 3D CONNECT Edition V22/Plaxis3DInput.exe" # Example
    )
    test_settings.spudcan = models.SpudcanGeometry(diameter=5)
    # Add more dummy data to test_settings if needed for more thorough stub testing.

    interactor = PlaxisInteractor(plaxis_path=test_settings.plaxis_installation_path)

    print("\n--- Testing Model Setup ---")
    setup_ok = interactor.setup_model_in_plaxis(test_settings)
    print(f"Model setup status: {'OK' if setup_ok else 'Failed'}")

    if setup_ok:
        print("\n--- Testing Run Calculation ---")
        calc_ok = interactor.run_calculation()
        print(f"Calculation status: {'OK' if calc_ok else 'Failed'}")

        if calc_ok:
            print("\n--- Testing Extract Results ---")
            results_data = interactor.extract_results(test_settings)
            if results_data:
                print("Results obtained:")
                print(f"  Final Penetration: {results_data.final_penetration_depth}")
                print(f"  Peak Resistance: {results_data.peak_vertical_resistance}")
                print(f"  Load-Pen Curve Points: {len(results_data.load_penetration_curve_data or [])}")
            else:
                print("No results data obtained.")

    print("\n--- Testing Error Mapping ---")
    raw_error = "Error code 10: convergence not reached in phase 2"
    friendly_error = interactor.map_plaxis_error(raw_error)
    print(f"Raw: '{raw_error}' -> Friendly: '{friendly_error}'")

    raw_error_unknown = "Error 999: Unknown PLAXIS issue"
    friendly_error_unknown = interactor.map_plaxis_error(raw_error_unknown)
    print(f"Raw: '{raw_error_unknown}' -> Friendly: '{friendly_error_unknown}'")

    print("\n--- End of PlaxisInteractor Tests ---")
