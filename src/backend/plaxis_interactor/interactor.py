"""
Main orchestrator for interacting with PLAXIS.
This module coordinates calls to helper modules for command generation,
process execution, and results parsing.
PRD Ref: Tasks 3.7 (PLAXIS Process Execution & Monitoring), 3.9 (Error Mapping)
"""
import os
import re
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
import subprocess
import time

# Custom exceptions
from ..exceptions import (
    PlaxisAutomationError, PlaxisConnectionError, PlaxisConfigurationError,
    PlaxisCalculationError, PlaxisOutputError, PlaxisCliError
)

logger = logging.getLogger(__name__)

# Try to import plxscripting, but allow failure for environments without it
try:
    from plxscripting.easy import new_server
    from plxscripting.plx_scripting_exceptions import PlxScriptingError
except ImportError:
    logger.warning("plxscripting library not found. PlaxisInteractor will not be able to connect to PLAXIS API.")
    class PlxScriptingError(Exception): # type: ignore
        """Placeholder for PlxScriptingError if plxscripting library is not available."""
        pass
    def new_server(host: str, port: int, password: str) -> Tuple[Any, Any]: # type: ignore
        """Placeholder for new_server if plxscripting library is not available."""
        # Ensure this placeholder actually raises an error that can be caught
        raise PlaxisConnectionError("plxscripting library not available, cannot create new_server.")


from ..models import ProjectSettings, AnalysisResults
from . import geometry_builder
from . import soil_builder
from . import calculation_builder
from . import results_parser


def _map_plaxis_sdk_exception_to_custom(e: Exception, context: str = "PLAXIS operation") -> PlaxisAutomationError:
    """Maps a Python or PlxScripting exception to a custom PlaxisAutomationError."""
    logger.debug(f"Mapping SDK error: {type(e).__name__} - {e} in context: {context}", exc_info=True) # Add exc_info for original trace

    if isinstance(e, PlaxisAutomationError): # If it's already one of our custom errors
        return e

    err_str = str(e).lower() # For case-insensitive matching

    if isinstance(e, PlxScriptingError):
        # Connection issues
        if "connection refused" in err_str or "actively refused it" in err_str or \
           "server not responding" in err_str or "no response from server" in err_str or \
           "cannot connect" in err_str:
            return PlaxisConnectionError(f"PLAXIS API connection issue during {context}: {e}")
        if "password incorrect" in err_str or "authentication failed" in err_str:
            return PlaxisConnectionError(f"PLAXIS API authentication failed (password incorrect?) during {context}: {e}")

        # Configuration or model setup issues often manifest as these
        if "object not found" in err_str or "unknown identifier" in err_str or \
           "does not exist" in err_str or "property not found" in err_str or \
           "unknown command" in err_str or "command is not recognized" in err_str or \
           "incorrect mode" in err_str or "operation not allowed in current mode" in err_str or \
           "type mismatch" in err_str or "incorrect type" in err_str or \
           "index out of range" in err_str or ("is not valid" in err_str and "index" in err_str):
            return PlaxisConfigurationError(f"PLAXIS model/API configuration error during {context}: {e}")

        # Calculation specific issues
        if "calculation failed" in err_str or "convergence not reached" in err_str or \
           "did not converge" in err_str or "numerical error" in err_str or \
           "singular matrix" in err_str or "matrix is not positive definite" in err_str or \
           "soil body seems to collapse" in err_str or "mechanism formed" in err_str or \
           "error code 101" in err_str or "error code 25" in err_str or \
           "accuracy condition not met" in err_str or "load increment reduced to zero" in err_str:
            return PlaxisCalculationError(f"PLAXIS calculation error during {context}: {e}")

        # Meshing issues
        if "mesh generation failed" in err_str or "error generating mesh" in err_str or \
           "cannot generate mesh for region" in err_str:
            return PlaxisConfigurationError(f"PLAXIS meshing error during {context}: {e}") # Often config related

        # Geometry issues
        if "geometric inconsistency" in err_str or "invalid geometry" in err_str:
            return PlaxisConfigurationError(f"PLAXIS geometry error during {context}: {e}")

        # Parameter issues
        if "parameter" in err_str and ("missing" in err_str or "invalid" in err_str or "out of range" in err_str):
            param_name_match = re.search(r"parameter\s*['\"]?([^'\"\s]+)['\"]?", err_str)
            param_info = f" for parameter '{param_name_match.group(1)}'" if param_name_match else ""
            return PlaxisConfigurationError(f"Invalid PLAXIS parameter{param_info} during {context}: {e}")

        # License issues
        if "license" in err_str or "dongle" in err_str or "no valid license" in err_str:
            return PlaxisConnectionError(f"PLAXIS license issue during {context}: {e}") # Connection because it prevents use

        # File issues (often from save/load)
        if "file not found" in err_str and ".p3dscript" not in err_str : # Exclude script file not found
             return PlaxisConfigurationError(f"PLAXIS project/data file not found during {context}: {e}")
        if "cannot open file" in err_str or ("access denied" in err_str and "file" in err_str):
            return PlaxisConfigurationError(f"PLAXIS file access error during {context}: {e}")
        if "disk space" in err_str:
            return PlaxisAutomationError(f"Insufficient disk space for PLAXIS operations during {context}: {e}")

        # Default for other PlxScriptingErrors
        return PlaxisAutomationError(f"A PLAXIS scripting error occurred during {context}: {e}")

    # Mapping for standard Python exceptions that might occur during interaction
    elif isinstance(e, AttributeError): # Often means API misuse or unexpected object state
        return PlaxisConfigurationError(f"AttributeError (API misuse or unexpected PLAXIS object state) during {context}: {e}")
    elif isinstance(e, TypeError): # API called with wrong type
        return PlaxisConfigurationError(f"TypeError (API called with incorrect type) during {context}: {e}")
    elif isinstance(e, ValueError): # API called with invalid value
        return PlaxisConfigurationError(f"ValueError (API called with invalid value) during {context}: {e}")
    elif isinstance(e, FileNotFoundError) and ".p3dscript" not in err_str: # If a project file not found, not script
        return PlaxisConfigurationError(f"FileNotFoundError for a project/data file during {context}: {e}")
    elif isinstance(e, TimeoutError) or ("timeout" in err_str or "timed out" in err_str): # From subprocess or other timeouts
        return PlaxisCalculationError(f"Operation timed out during {context}: {e}") # Often calculation related

    # General fallback for truly unexpected Python errors not covered above
    return PlaxisAutomationError(f"An unexpected Python error ({type(e).__name__}) occurred during {context}: {e}")


class PlaxisInteractor:
    def __init__(self, plaxis_path: Optional[str] = None, project_settings: Optional[ProjectSettings] = None):
        self.plaxis_path: Optional[str] = plaxis_path
        self.project_settings: Optional[ProjectSettings] = project_settings
        self.s_i: Optional[Any] = None
        self.g_i: Optional[Any] = None
        self.s_o: Optional[Any] = None
        self.g_o: Optional[Any] = None
        self._default_input_port: int = 10000
        self._default_output_port: int = 10001
        self._default_api_password: str = "YOUR_API_PASSWORD" # Ensure this is changed or configured
        self.plaxis_process: Optional[subprocess.Popen] = None
        logger.info(f"PlaxisInteractor initialized. PLAXIS exe path: {plaxis_path or 'Not specified (API only assumed)'}")

    def _get_api_credentials(self) -> Tuple[str, int, int, str]:
        # ... (implementation remains the same, ensure logger.critical for default password)
        host: str = "localhost"
        input_port: int = self._default_input_port
        output_port: int = self._default_output_port
        password: str = self._default_api_password
        if self.project_settings:
            input_port = self.project_settings.plaxis_api_input_port
            output_port = self.project_settings.plaxis_api_output_port
            if self.project_settings.plaxis_api_password:
                password = self.project_settings.plaxis_api_password
            else:
                logger.warning("API password in project settings is empty or not set. Using interactor default.")
        if password == "YOUR_API_PASSWORD": # Critical if default password is used
            logger.critical("Using default PLAXIS API password ('YOUR_API_PASSWORD'). This is insecure. Configure a proper password.")
            # Consider raising PlaxisConfigurationError here if strict policy is needed
        return host, input_port, output_port, password

    def _connect_to_input_server(self) -> None: # Changed return type to None, raises on failure
        if self.g_i and self.s_i:
            try:
                _ = self.g_i.Project.Title.value # Simple check
                logger.info("Input server connection already active.")
                return
            except Exception as e:
                logger.warning(f"Input API connection check failed: {e}. Attempting to reconnect.", exc_info=True)
                self.s_i, self.g_i = None, None

        host, input_port, _, password = self._get_api_credentials()
        logger.info(f"Attempting to connect to PLAXIS Input API on {host}:{input_port}...")
        try:
            self.s_i, self.g_i = new_server(host, input_port, password=password)
            project_title_value = self.g_i.Project.Title.value # Verify connection
            logger.info(f"Successfully connected to PLAXIS Input API. Current project title: '{project_title_value}'.")
        except Exception as e: # Catch PlxScriptingError or any other
            self.s_i, self.g_i = None, None
            raise _map_plaxis_sdk_exception_to_custom(e, f"connecting to Input API ({host}:{input_port})")

    def _connect_to_output_server(self, project_file_to_open: Optional[str] = None) -> None: # Changed return type
        if self.g_o and self.s_o:
            try:
                _ = self.g_o.ResultTypes # Simple check
                if project_file_to_open and hasattr(self.s_o, 'open'):
                    logger.info(f"Output server already connected. Attempting to (re)open '{project_file_to_open}'.")
                    self.s_o.open(project_file_to_open) # This can also raise
                    logger.info(f"Successfully (re)opened '{project_file_to_open}' in existing output server.")
                else:
                    logger.info("Output server already connected. No new file specified or s_o cannot open files.")
                return
            except Exception as e:
                logger.warning(f"Output API connection check/re-open failed: {e}. Attempting to reconnect.", exc_info=True)
                self.s_o, self.g_o = None, None

        host, _, output_port, password = self._get_api_credentials()
        logger.info(f"Attempting to connect to PLAXIS Output API on {host}:{output_port}...")
        try:
            self.s_o, self.g_o = new_server(host, output_port, password=password)
            _ = self.g_o.ResultTypes # Verify connection
            logger.info(f"Successfully connected to PLAXIS Output API on {host}:{output_port}.")

            if project_file_to_open:
                if not os.path.exists(project_file_to_open):
                    raise PlaxisConfigurationError(f"Project file for output results does not exist: {project_file_to_open}")
                if hasattr(self.s_o, 'open'):
                    logger.info(f"Attempting to open project '{project_file_to_open}' in Output server...")
                    self.s_o.open(project_file_to_open)
                    # Check if phases exist as a proxy for successful open
                    if not self.g_o.Phases:
                        logger.warning(f"Opened '{project_file_to_open}' but no phases found or g_o not updated properly.")
                    else:
                        logger.info(f"Successfully opened '{project_file_to_open}'. Found {len(self.g_o.Phases)} phases.")
                else:
                    logger.warning(f"Output server object (type: {type(self.s_o)}) lacks 'open' method. Cannot open specific project.")
        except Exception as e: # Catch PlxScriptingError or any other
            self.s_o, self.g_o = None, None
            raise _map_plaxis_sdk_exception_to_custom(e, f"connecting/opening project in Output API ({host}:{output_port})")

    def _execute_cli_script(self, commands: List[str], script_filename: str = "temp_plaxis_script.p3dscript") -> None: # Changed return
        if not self.plaxis_path or "Plaxis3DInput.exe" not in self.plaxis_path: # Basic check
            raise PlaxisConfigurationError(f"PLAXIS executable path not configured correctly for CLI: '{self.plaxis_path}'")

        abs_script_path = os.path.abspath(script_filename)
        logger.info(f"Writing {len(commands)} commands to script '{abs_script_path}' for CLI.")

        try:
            with open(abs_script_path, 'w') as f:
                for cmd in commands: f.write(cmd + '\n')
        except IOError as e:
            raise PlaxisCliError(f"IOError writing script file '{abs_script_path}': {e}")

        cli_command_parts = [self.plaxis_path, f"--runscript={abs_script_path}"]
        logger.info(f"Executing PLAXIS CLI: {' '.join(cli_command_parts)}")

        timeout_duration = 3600 # Default
        if self.project_settings and self.project_settings.analysis_settings:
            timeout_duration = self.project_settings.analysis_settings.max_calc_time_seconds or timeout_duration
        logger.debug(f"CLI execution timeout set to: {timeout_duration} seconds.")

        try:
            if self.plaxis_path is None: # Should be caught by earlier check
                 raise PlaxisConfigurationError("PLAXIS executable path is None. Cannot execute CLI script.")

            self.plaxis_process = subprocess.Popen(
                cli_command_parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0 # type: ignore
            )
            stdout, stderr = self.plaxis_process.communicate(timeout=timeout_duration)

            if self.plaxis_process.returncode == 0:
                logger.info("PLAXIS script via CLI executed successfully.")
                if stdout: logger.debug(f"PLAXIS CLI STDOUT:\n{stdout}")
                if stderr: logger.warning(f"PLAXIS CLI STDERR (on success):\n{stderr}")
            else:
                error_output = stderr if stderr else stdout
                # Use a more specific exception for CLI failures
                raise PlaxisCliError(f"PLAXIS script via CLI failed. RC: {self.plaxis_process.returncode}. Output:\n{error_output}")

        except FileNotFoundError: # For plaxis_path not found at execution time
            raise PlaxisConfigurationError(f"PLAXIS executable not found at '{self.plaxis_path}'. Check path.")
        except subprocess.TimeoutExpired:
            logger.error(f"PLAXIS script execution timed out after {timeout_duration}s.", exc_info=True)
            if self.plaxis_process:
                self.plaxis_process.kill()
                self.plaxis_process.wait()
            raise PlaxisCalculationError(f"TimeoutExpired: PLAXIS CLI process exceeded {timeout_duration}s.") # Calculation related
        except Exception as e: # Catch other subprocess errors
            raise PlaxisCliError(f"Unexpected error during PLAXIS CLI execution: {e}")
        finally:
            if os.path.exists(abs_script_path):
                try: os.remove(abs_script_path)
                except OSError as e: logger.warning(f"Could not remove temporary script file '{abs_script_path}': {e}")

    def _execute_api_commands(self, commands: List[Callable[[Any], None]], server_global_object: Any, server_name: str) -> None: # Changed return
        if not server_global_object:
            raise PlaxisConnectionError(f"{server_name} global object (g_i/g_o) is not available.")

        logger.info(f"Executing {len(commands)} API commands on {server_name} server...")
        for i, cmd_callable in enumerate(commands):
            command_name = getattr(cmd_callable, '__name__', f"lambda_cmd_at_index_{i+1}")
            try:
                logger.debug(f"  Executing API command {i+1}/{len(commands)}: {command_name}")
                cmd_callable(server_global_object)
            except Exception as e: # Catch PlxScriptingError or any other
                # Let map_plaxis_sdk_exception_to_custom decide the type of PlaxisAutomationError
                raise _map_plaxis_sdk_exception_to_custom(e, f"executing API command '{command_name}' on {server_name}")
        logger.info(f"Successfully executed all {len(commands)} API commands on {server_name} server.")

    def setup_model_in_plaxis(self, model_setup_callables: List[Callable[[Any], None]], is_new_project: bool = True) -> None: # Changed return
        if not self.project_settings:
            raise PlaxisConfigurationError("ProjectSettings not provided to PlaxisInteractor.")

        self._connect_to_input_server() # Raises on failure
        logger.info(f"Setting up PLAXIS model via API. New project: {is_new_project}")

        if is_new_project:
            initial_api_commands: List[Callable[[Any], None]] = [lambda gi: gi.new()]
            if self.project_settings.project_name:
                 initial_api_commands.append(lambda gi: gi.settitle(self.project_settings.project_name))
            # Conceptual: Unit settings would be added here
            self._execute_api_commands(initial_api_commands, self.g_i, "Input (g_i) - Project Init")
        else: # Opening existing project
            project_file_path = self.project_settings.project_file_path
            if not project_file_path or not os.path.exists(project_file_path):
                raise PlaxisConfigurationError(f"Project file path for opening is not specified or file does not exist: '{project_file_path}'")
            if not self.s_i or not hasattr(self.s_i, 'open'):
                 raise PlaxisConnectionError("Input server object (s_i) unavailable or lacks 'open' method.")
            try:
                logger.info(f"Attempting to open existing project: '{project_file_path}' using s_i.open()")
                self.s_i.open(project_file_path) # This can raise
                logger.info(f"Project '{project_file_path}' opened successfully.")
                # Optional: Verify title if needed
            except Exception as e:
                raise _map_plaxis_sdk_exception_to_custom(e, f"opening existing project '{project_file_path}'")

        if model_setup_callables:
            logger.info(f"Executing {len(model_setup_callables)} main model setup callables...")
            self._execute_api_commands(model_setup_callables, self.g_i, "Input (g_i) - Model Definition")
        elif is_new_project: # Only log if it was a new project and no callables
            logger.info("New project initialized, but no further model setup callables were provided.")

        logger.info("PLAXIS model setup phase completed successfully via API.")

    def run_calculation(self, calculation_run_callables: List[Callable[[Any], None]]) -> None: # Changed return
        if not self.project_settings:
            raise PlaxisConfigurationError("ProjectSettings not provided. Cannot run calculation.")
        if not self.g_i: # Ensure connection if not already established
            self._connect_to_input_server()

        logger.info("Running PLAXIS calculation sequence via API...")
        self._execute_api_commands(calculation_run_callables, self.g_i, "Input (g_i) - Calculation Sequence")
        logger.info("Calculation sequence (including g_i.calculate() if present) reported success by PLAXIS.")

        project_save_path = self.project_settings.project_file_path
        if not project_save_path:
            default_filename = (self.project_settings.project_name or "UntitledPlaxisProject") + ".p3dxml"
            project_save_path = os.path.join(os.getcwd(), default_filename)
            logger.warning(f"`project_file_path` not set. Attempting to save to default: {project_save_path}")

        logger.info(f"Attempting to save project to '{project_save_path}' after calculation...")
        if self.g_i and hasattr(self.g_i, 'save') and callable(self.g_i.save):
            save_cmd_callable = lambda gi_param: gi_param.save(project_save_path) # type: ignore
            try:
                self._execute_api_commands([save_cmd_callable], self.g_i, "Input (g_i) - Save Project")
                logger.info(f"Project successfully saved to '{project_save_path}' after calculation.")
                if not self.project_settings.project_file_path: # Update settings if it was a default path
                    self.project_settings.project_file_path = project_save_path
            except PlaxisAutomationError as e: # Catch if save fails specifically
               logger.warning(f"Failed to save project to '{project_save_path}' after calculation: {e}", exc_info=True)
               # Decide if this should re-raise or just be a warning
        else:
            logger.warning("`g_i.save` method not available. Cannot save project after calculation.")
        logger.info("PLAXIS calculation and subsequent save attempt finished.")

    def extract_results(self, results_extraction_callables: List[Callable[[Any], Any]]) -> List[Any]:
        if not self.project_settings or not self.project_settings.project_file_path:
            raise PlaxisConfigurationError("ProjectSettings or project_file_path not provided for results extraction.")

        calculated_project_path = self.project_settings.project_file_path
        if not os.path.exists(calculated_project_path):
            raise PlaxisOutputError(f"Calculated project file for results not found: {calculated_project_path}")

        self._connect_to_output_server(project_file_to_open=calculated_project_path) # Raises on failure
        logger.info(f"Extracting results via API from PLAXIS Output for project: {calculated_project_path}")

        extracted_data_list: List[Any] = []
        if not self.g_o: # Should be guaranteed by _connect_to_output_server
            raise PlaxisConnectionError("PLAXIS Output global object (g_o) unavailable after connection attempt.")

        for i, cmd_callable in enumerate(results_extraction_callables):
            command_name = getattr(cmd_callable, '__name__', f"lambda_res_cmd_at_index_{i+1}")
            try:
                logger.debug(f"Executing result extraction command {i+1}/{len(results_extraction_callables)}: {command_name}")
                result_piece = cmd_callable(self.g_o)
                extracted_data_list.append(result_piece)
            except Exception as e: # Catch PlxScriptingError or any other
                logger.error(f"Result extraction command '{command_name}' failed: {e}", exc_info=True)
                # Map and potentially append a placeholder or error object
                mapped_error = _map_plaxis_sdk_exception_to_custom(e, f"extracting result '{command_name}'")
                extracted_data_list.append(mapped_error) # Store the error itself or a marker

        logger.info(f"Executed {len(results_extraction_callables)} result callables, yielding {len(extracted_data_list)} pieces.")
        return extracted_data_list

    def map_plaxis_error(self, raw_error_message: str) -> str: # This method is now mostly a fallback/logger
        """Legacy error mapper, primary mapping is now in _map_plaxis_sdk_exception_to_custom."""
        # This method can still be used for CLI error strings if needed,
        # but SDK errors should go through _map_plaxis_sdk_exception_to_custom.
        logger.warning(f"Legacy map_plaxis_error called with: {raw_error_message}. Prefer raising specific exceptions.")
        # Simplified version, as detailed mapping is in the new function.
        # This might still be useful for very generic CLI output parsing if _map_plaxis_sdk_exception_to_custom is not suitable.
        lower_error = raw_error_message.lower()
        if "connection refused" in lower_error: return "ConnectionRefused"
        if "password incorrect" in lower_error: return "InvalidPassword"
        # ... add a few very common CLI patterns if necessary ...
        return f"PlaxisGenericError: {raw_error_message[:100]}"


    def close_all_connections(self):
        logger.info("Attempting to close all PLAXIS connections and processes...")
        # For API connections, just nullify server objects. Actual server might keep running.
        if self.s_i or self.g_i:
            logger.info("Nullifying Input server objects (s_i, g_i).")
            self.s_i, self.g_i = None, None
        if self.s_o or self.g_o:
            logger.info("Nullifying Output server objects (s_o, g_o).")
            self.s_o, self.g_o = None, None

        # For CLI process
        if self.plaxis_process and self.plaxis_process.poll() is None: # Check if process is running
            logger.info("Terminating active PLAXIS CLI process...")
            try:
                self.plaxis_process.terminate() # Graceful termination
                try:
                    self.plaxis_process.wait(timeout=5) # Wait for it to terminate
                    logger.info("PLAXIS CLI process terminated gracefully.")
                except subprocess.TimeoutExpired:
                    logger.warning("PLAXIS CLI process did not terminate gracefully after 5s, attempting to kill.")
                    self.plaxis_process.kill() # Force kill
                    self.plaxis_process.wait() # Wait for kill
                    logger.info("PLAXIS CLI process killed.")
            except Exception as e: # Catch any error during termination/kill
                logger.error(f"Error during PLAXIS CLI process termination: {e}", exc_info=True)
            self.plaxis_process = None
        logger.info("PLAXIS connections and processes handled for closure by PlaxisInteractor.")

if __name__ == '__main__':
    # Basic logging setup for __main__ testing
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("\n--- Conceptual Test of PlaxisInteractor (with Exception Handling) ---")

    from dataclasses import dataclass # For MockAnalysisSettings

    class MockProjectSettings(ProjectSettings):
        def __init__(self, project_name: str,
                     api_input_port: int, api_output_port: int, api_password: str,
                     proj_file_path: Optional[str] = None,
                     plaxis_exe: Optional[str] = None):
            super().__init__(project_name=project_name, plaxis_installation_path=plaxis_exe) # type: ignore
            self.plaxis_api_input_port = api_input_port
            self.plaxis_api_output_port = api_output_port
            self.plaxis_api_password = api_password
            self.project_file_path = os.path.abspath(proj_file_path if proj_file_path else f"{project_name}_test.p3dxml")

            @dataclass
            class MockAnalysisSettings: # Simple mock for analysis settings
                max_calc_time_seconds: Optional[int] = 10 # Short timeout for testing
            self.analysis_settings = MockAnalysisSettings()


    TEST_API_PASSWORD = "testpassword" # Change if your PLAXIS API has a different password
    TEST_PLAXIS_EXE_PATH = "C:/Program Files/Bentley/Geotechnical/PLAXIS 3D CONNECT Edition V22/Plaxis3DInput.exe" # Adjust if necessary

    # Ensure TEST_PLAXIS_EXE_PATH is valid on your system if running CLI tests, otherwise set to None
    if not os.path.exists(TEST_PLAXIS_EXE_PATH):
        logger.warning(f"PLAXIS Executable path for testing does not exist: {TEST_PLAXIS_EXE_PATH}. CLI tests may fail or be skipped.")
        TEST_PLAXIS_EXE_PATH = None # Prevents FileNotFoundError if path is wrong

    test_proj_name = "InteractorExceptionTest"
    test_file_path = os.path.join(os.getcwd(), f"{test_proj_name}.p3dxml")

    mock_settings = MockProjectSettings(
        project_name=test_proj_name,
        api_input_port=10000, api_output_port=10001, # Standard ports
        api_password=TEST_API_PASSWORD,
        proj_file_path=test_file_path,
        plaxis_exe=TEST_PLAXIS_EXE_PATH
    )
    interactor = PlaxisInteractor(plaxis_path=TEST_PLAXIS_EXE_PATH, project_settings=mock_settings)

    # --- Test API Connection Failure (example: wrong port or password) ---
    logger.info("\n--- Test 1: API Input Connection Failure (simulated by potentially wrong password/port) ---")
    # To truly test this, you might need to ensure PLAXIS API is NOT running or use a bad password
    # For this conceptual test, we'll assume it might fail and catch the specific exception.
    original_pass = mock_settings.plaxis_api_password
    mock_settings.plaxis_api_password = "wrong_password_for_testing"
    try:
        interactor._connect_to_input_server()
        logger.info("Input server connection: UNEXPECTED SUCCESS (was expecting failure with bad password)")
    except PlaxisConnectionError as e:
        logger.info(f"Input server connection: EXPECTED FAILURE - Caught PlaxisConnectionError: {e}")
    except Exception as e:
        logger.error(f"Input server connection: UNEXPECTED EXCEPTION TYPE - {type(e).__name__}: {e}", exc_info=True)
    finally:
        mock_settings.plaxis_api_password = original_pass # Reset password

    # --- Test CLI Execution Failure (example: bad script content or PLAXIS error) ---
    if TEST_PLAXIS_EXE_PATH: # Only run if PLAXIS path is set
        logger.info("\n--- Test 2: CLI Execution Failure (simulated with bad command) ---")
        bad_cli_commands = ["this_is_not_a_plaxis_command()"]
        try:
            interactor._execute_cli_script(bad_cli_commands, "bad_script_test.p3dscript")
            logger.info("CLI execution: UNEXPECTED SUCCESS (was expecting PlaxisCliError)")
        except PlaxisCliError as e:
            logger.info(f"CLI execution: EXPECTED FAILURE - Caught PlaxisCliError: {e}")
        except PlaxisConfigurationError as e: # If path was bad
             logger.info(f"CLI execution: EXPECTED CONFIG FAILURE - Caught PlaxisConfigurationError: {e}")
        except Exception as e:
            logger.error(f"CLI execution: UNEXPECTED EXCEPTION TYPE - {type(e).__name__}: {e}", exc_info=True)
    else:
        logger.warning("Skipping CLI execution failure test as PLAXIS executable path is not set.")

    # --- Test Full Workflow with Potential Error (e.g., during command execution) ---
    # This requires a running PLAXIS instance. We simulate an error during API command execution.
    logger.info("\n--- Test 3: Full API Workflow with Simulated Command Failure ---")

    def failing_api_command(g_i_obj: Any):
        logger.debug("Executing intentionally failing API command (e.g., referencing non-existent object).")
        # This command is likely to fail if no object "NonExistentObject" exists.
        g_i_obj.delete(g_i_obj.Points["NonExistentObject"])

    faulty_setup_callables = [
        lambda gi: gi.gotostructures(), # A valid command
        failing_api_command             # An intentionally failing command
    ]

    # Assuming PLAXIS API is actually running for this test to make sense
    # If not, the _connect_to_input_server will fail first.
    did_setup_fail_as_expected = False
    try:
        # Reset interactor to clear any previous state
        interactor = PlaxisInteractor(plaxis_path=TEST_PLAXIS_EXE_PATH, project_settings=mock_settings)
        interactor.setup_model_in_plaxis(faulty_setup_callables, is_new_project=True)
        logger.info("Full API workflow (setup_model_in_plaxis with faulty command): UNEXPECTED SUCCESS")
    except PlaxisConfigurationError as e: # Could be this if the error is config-like (e.g. object not found)
        logger.info(f"Full API workflow (setup_model_in_plaxis with faulty command): EXPECTED FAILURE - Caught PlaxisConfigurationError: {e}")
        did_setup_fail_as_expected = True
    except PlaxisAutomationError as e: # Generic catch for other automation errors
        logger.info(f"Full API workflow (setup_model_in_plaxis with faulty command): EXPECTED FAILURE - Caught PlaxisAutomationError: {e}")
        did_setup_fail_as_expected = True
    except Exception as e:
        logger.error(f"Full API workflow (setup_model_in_plaxis with faulty command): UNEXPECTED EXCEPTION TYPE - {type(e).__name__}: {e}", exc_info=True)

    if not did_setup_fail_as_expected:
        logger.warning("The setup_model_in_plaxis test with a faulty command did not fail as expected. "
                       "This might happen if PLAXIS API is not running or if the 'failing_api_command' "
                       "did not actually cause a PlxScriptingError (e.g., if it was caught internally by plxscripting).")


    if 'interactor' in locals() and isinstance(interactor, PlaxisInteractor):
        interactor.close_all_connections()
    logger.info("\n--- Conceptual Test of PlaxisInteractor (with Exception Handling) Finished ---")
