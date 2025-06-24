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

# Attempt to import PySide6 for signals, but provide dummies if not found (for backend-only tests)
try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    logger.warning("PySide6.QtCore not found. Using dummy QObject and Signal for PlaxisInteractor.InteractorSignals. This is expected for backend-only tests.")
    class QObject: # type: ignore
        def __init__(self, parent=None): pass

    class Signal: # type: ignore
        def __init__(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass
        def connect(self, slot): pass
        def disconnect(self, slot): pass

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
    logger.debug(f"Mapping SDK error: {type(e).__name__} - {e} in context: {context}", exc_info=True)

    if isinstance(e, PlaxisAutomationError):
        return e

    err_str = str(e).lower()
    is_plx_scripting_error_type = type(e).__name__ == 'PlxScriptingError'

    if is_plx_scripting_error_type:
        # Using re.search for a more flexible "object not found" check.
        if re.search(r"object\s*.*not found", err_str):
            logger.debug(f"DEBUG: Matched regex 'object...not found' for err_str: {err_str}")
            return PlaxisConfigurationError(f"PLAXIS configuration: Object not found during {context}: {e}")
        elif "connection refused" in err_str or "actively refused it" in err_str or \
             "server not responding" in err_str or "no response from server" in err_str or \
             "cannot connect" in err_str:
            return PlaxisConnectionError(f"PLAXIS API connection issue during {context}: {e}")
        elif "password incorrect" in err_str or "authentication failed" in err_str:
            return PlaxisConnectionError(f"PLAXIS API authentication failed (password incorrect?) during {context}: {e}")
        elif "unknown identifier" in err_str or \
             "does not exist" in err_str or "property not found" in err_str or \
             "unknown command" in err_str or "command is not recognized" in err_str or \
             "incorrect mode" in err_str or "operation not allowed in current mode" in err_str or \
             "type mismatch" in err_str or "incorrect type" in err_str or \
             "index out of range" in err_str or ("is not valid" in err_str and "index" in err_str):
            return PlaxisConfigurationError(f"PLAXIS model/API configuration error during {context}: {e}")
        elif "calculation failed" in err_str or "convergence not reached" in err_str or \
             "did not converge" in err_str or "numerical error" in err_str or \
             "singular matrix" in err_str or "matrix is not positive definite" in err_str or \
             "soil body seems to collapse" in err_str or "mechanism formed" in err_str or \
             "error code 101" in err_str or "error code 25" in err_str or \
             "accuracy condition not met" in err_str or "load increment reduced to zero" in err_str or \
             "calculation aborted" in err_str or "calculation has been aborted" in err_str:
            return PlaxisCalculationError(f"PLAXIS calculation error/aborted during {context}: {e}")
        elif "mesh generation failed" in err_str or "error generating mesh" in err_str or \
             "cannot generate mesh for region" in err_str:
            return PlaxisConfigurationError(f"PLAXIS meshing error during {context}: {e}")
        elif "geometric inconsistency" in err_str or "invalid geometry" in err_str:
            return PlaxisConfigurationError(f"PLAXIS geometry error during {context}: {e}")
        elif ("parameter" in err_str and ("missing" in err_str or "invalid" in err_str or "out of range" in err_str)) or \
             "input value is not correct" in err_str or "value is out of range" in err_str:
            param_name_match = re.search(r"parameter\s*['\"]?([^'\"\s]+)['\"]?", err_str)
            param_info = f" for parameter '{param_name_match.group(1)}'" if param_name_match else ""
            return PlaxisConfigurationError(f"Invalid PLAXIS parameter or value{param_info} during {context}: {e}")
        elif "license" in err_str or "dongle" in err_str or "no valid license" in err_str:
            return PlaxisConnectionError(f"PLAXIS license issue during {context}: {e}")
        elif "file not found" in err_str and ".p3dscript" not in err_str:
            return PlaxisConfigurationError(f"PLAXIS project/data file not found during {context}: {e}")
        elif "cannot open file" in err_str or ("access denied" in err_str and "file" in err_str):
            return PlaxisConfigurationError(f"PLAXIS file access error during {context}: {e}")
        elif "disk space" in err_str:
            return PlaxisAutomationError(f"Insufficient disk space for PLAXIS operations during {context}: {e}")
        else: # Default for other PlxScriptingErrors
            return PlaxisAutomationError(f"A PLAXIS scripting error occurred during {context}: {e}")

    elif isinstance(e, AttributeError):
        return PlaxisConfigurationError(f"AttributeError (API misuse or unexpected PLAXIS object state) during {context}: {e}")
    elif isinstance(e, TypeError):
        return PlaxisConfigurationError(f"TypeError (API called with incorrect type) during {context}: {e}")
    elif isinstance(e, ValueError):
        return PlaxisConfigurationError(f"ValueError (API called with invalid value) during {context}: {e}")
    elif isinstance(e, FileNotFoundError) and ".p3dscript" not in err_str:
        return PlaxisConfigurationError(f"FileNotFoundError for a project/data file during {context}: {e}")
    elif isinstance(e, TimeoutError) or ("timeout" in err_str or "timed out" in err_str):
        return PlaxisCalculationError(f"Operation timed out during {context}: {e}")

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

        # Signals for progress and stage updates
        self.signals = PlaxisInteractor.InteractorSignals()

        logger.info(f"PlaxisInteractor initialized. PLAXIS exe path: {plaxis_path or 'Not specified (API only assumed)'}")

    class InteractorSignals(QObject):
        """Container for signals emitted by PlaxisInteractor."""
        analysis_stage_changed = Signal(str) # e.g., "setup", "calculating", "results", "error", "finished"
        progress_updated = Signal(int, int) # current_step, total_steps (or percentage if total is 100)

    def _get_api_credentials(self) -> Tuple[str, int, int, str]:
        host: str = "localhost"
        input_port: int = self._default_input_port
        output_port: int = self._default_output_port
        password: str = self._default_api_password
        if self.project_settings:
            input_port = getattr(self.project_settings, 'plaxis_api_input_port', input_port)
            output_port = getattr(self.project_settings, 'plaxis_api_output_port', output_port)
            if getattr(self.project_settings, 'plaxis_api_password', None):
                password = self.project_settings.plaxis_api_password # type: ignore
            else:
                logger.warning("API password in project settings is empty or not set. Using interactor default.")
        if password == "YOUR_API_PASSWORD":
            logger.critical("Using default PLAXIS API password ('YOUR_API_PASSWORD'). This is insecure. Configure a proper password.")
        return host, input_port, output_port, password

    def _connect_to_input_server(self) -> None:
        if self.g_i and self.s_i:
            try:
                _ = self.g_i.Project.Title.value
                logger.info("Input server connection already active.")
                return
            except Exception as e:
                logger.warning(f"Input API connection check failed: {e}. Attempting to reconnect.", exc_info=True)
                self.s_i, self.g_i = None, None

        host, input_port, _, password = self._get_api_credentials()
        logger.info(f"Attempting to connect to PLAXIS Input API on {host}:{input_port}...")
        try:
            self.s_i, self.g_i = new_server(host, input_port, password=password)
            project_title_value = self.g_i.Project.Title.value
            logger.info(f"Successfully connected to PLAXIS Input API. Current project title: '{project_title_value}'.")
        except Exception as e:
            self.s_i, self.g_i = None, None
            raise _map_plaxis_sdk_exception_to_custom(e, f"connecting to Input API ({host}:{input_port})")

    def _connect_to_output_server(self, project_file_to_open: Optional[str] = None) -> None:
        if self.g_o and self.s_o:
            try:
                _ = self.g_o.ResultTypes
                if project_file_to_open and hasattr(self.s_o, 'open'):
                    logger.info(f"Output server already connected. Attempting to (re)open '{project_file_to_open}'.")
                    self.s_o.open(project_file_to_open)
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
            _ = self.g_o.ResultTypes
            logger.info(f"Successfully connected to PLAXIS Output API on {host}:{output_port}.")

            if project_file_to_open:
                if not os.path.exists(project_file_to_open):
                    raise PlaxisConfigurationError(f"Project file for output results does not exist: {project_file_to_open}")
                if hasattr(self.s_o, 'open'):
                    logger.info(f"Attempting to open project '{project_file_to_open}' in Output server...")
                    self.s_o.open(project_file_to_open)
                    if not self.g_o.Phases:
                        logger.warning(f"Opened '{project_file_to_open}' but no phases found or g_o not updated properly.")
                    else:
                        logger.info(f"Successfully opened '{project_file_to_open}'. Found {len(self.g_o.Phases)} phases.")
                else:
                    logger.warning(f"Output server object (type: {type(self.s_o)}) lacks 'open' method. Cannot open specific project.")
        except Exception as e:
            self.s_o, self.g_o = None, None
            raise _map_plaxis_sdk_exception_to_custom(e, f"connecting/opening project in Output API ({host}:{output_port})")

    def _execute_cli_script(self, commands: List[str], script_filename: str = "temp_plaxis_script.p3dscript") -> None:
        if not self.plaxis_path or "Plaxis3DInput.exe" not in self.plaxis_path:
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

        timeout_duration = 3600
        if self.project_settings and hasattr(self.project_settings, 'analysis_settings') and \
           self.project_settings.analysis_settings and \
           hasattr(self.project_settings.analysis_settings, 'max_calc_time_seconds'): # type: ignore
            timeout_duration = self.project_settings.analysis_settings.max_calc_time_seconds or timeout_duration # type: ignore
        logger.debug(f"CLI execution timeout set to: {timeout_duration} seconds.")

        try:
            if self.plaxis_path is None:
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
                raise PlaxisCliError(f"PLAXIS script via CLI failed. RC: {self.plaxis_process.returncode}. Output:\n{error_output}")

        except FileNotFoundError:
            raise PlaxisConfigurationError(f"PLAXIS executable not found at '{self.plaxis_path}'. Check path.")
        except subprocess.TimeoutExpired:
            logger.error(f"PLAXIS script execution timed out after {timeout_duration}s.", exc_info=True)
            if self.plaxis_process:
                self.plaxis_process.kill()
                self.plaxis_process.wait()
            raise PlaxisCalculationError(f"TimeoutExpired: PLAXIS CLI process exceeded {timeout_duration}s.")
        except Exception as e:
            raise PlaxisCliError(f"Unexpected error during PLAXIS CLI execution: {e}")
        finally:
            if os.path.exists(abs_script_path):
                try: os.remove(abs_script_path)
                except OSError as e: logger.warning(f"Could not remove temporary script file '{abs_script_path}': {e}")

    def attempt_stop_calculation(self) -> None:
        logger.info("Attempting to stop PLAXIS calculation...")
        stopped_cli = False
        stopped_api = False

        if self.plaxis_process and self.plaxis_process.poll() is None:
            logger.info("Active CLI process found. Attempting to terminate.")
            try:
                self.plaxis_process.terminate()
                self.plaxis_process.wait(timeout=5)
                logger.info("CLI process terminated.")
                stopped_cli = True
            except subprocess.TimeoutExpired:
                logger.warning("CLI process did not terminate after 5s, attempting kill.")
                self.plaxis_process.kill()
                self.plaxis_process.wait()
                logger.info("CLI process killed.")
                stopped_cli = True
            except Exception as e:
                logger.error(f"Error terminating CLI process: {e}", exc_info=True)

        if self.g_i:
            logger.info("Attempting to send breakcalculation command via API (g_i).")
            try:
                self.g_i.breakcalculation()
                logger.info("breakcalculation command sent via API.")
                stopped_api = True
            except Exception as e:
                logger.warning(f"Failed to send breakcalculation via API: {e}", exc_info=True)

        if not stopped_cli and not stopped_api:
            logger.info("No active CLI process found and/or API break command failed or was not applicable.")

    def _execute_api_commands(self, commands: List[Callable[[Any], None]], server_global_object: Any, server_name: str) -> None:
        if not server_global_object:
            raise PlaxisConnectionError(f"{server_name} global object (g_i/g_o) is not available.")

        logger.info(f"Executing {len(commands)} API commands on {server_name} server...")
        for i, cmd_callable in enumerate(commands):
            command_name = getattr(cmd_callable, '__name__', f"lambda_cmd_at_index_{i+1}")
            try:
                logger.debug(f"  Executing API command {i+1}/{len(commands)}: {command_name}")
                cmd_callable(server_global_object)
            except Exception as e:
                raise _map_plaxis_sdk_exception_to_custom(e, f"executing API command '{command_name}' on {server_name}")
        logger.info(f"Successfully executed all {len(commands)} API commands on {server_name} server.")

    def setup_model_in_plaxis(self, model_setup_callables: List[Callable[[Any], None]], is_new_project: bool = True) -> None:
        if not self.project_settings:
            raise PlaxisConfigurationError("ProjectSettings not provided to PlaxisInteractor.")

        self.signals.analysis_stage_changed.emit("setup_start")
        self.signals.progress_updated.emit(1, 4)

        self._connect_to_input_server()
        logger.info(f"Setting up PLAXIS model via API. New project: {is_new_project}")

        if is_new_project:
            initial_api_commands: List[Callable[[Any], None]] = [lambda gi: gi.new()]
            if self.project_settings.project_name:
                 initial_api_commands.append(lambda gi: gi.settitle(self.project_settings.project_name))
            self._execute_api_commands(initial_api_commands, self.g_i, "Input (g_i) - Project Init")
        else:
            project_file_path = self.project_settings.project_file_path # type: ignore
            if not project_file_path or not os.path.exists(project_file_path):
                raise PlaxisConfigurationError(f"Project file path for opening is not specified or file does not exist: '{project_file_path}'")
            if not self.s_i or not hasattr(self.s_i, 'open'):
                 raise PlaxisConnectionError("Input server object (s_i) unavailable or lacks 'open' method.")
            try:
                logger.info(f"Attempting to open existing project: '{project_file_path}' using s_i.open()")
                self.s_i.open(project_file_path)
                logger.info(f"Project '{project_file_path}' opened successfully.")
            except Exception as e:
                raise _map_plaxis_sdk_exception_to_custom(e, f"opening existing project '{project_file_path}'")

        if model_setup_callables:
            logger.info(f"Executing {len(model_setup_callables)} main model setup callables...")
            self._execute_api_commands(model_setup_callables, self.g_i, "Input (g_i) - Model Definition")
        elif is_new_project:
            logger.info("New project initialized, but no further model setup callables were provided.")

        logger.info("PLAXIS model setup phase completed successfully via API.")
        self.signals.analysis_stage_changed.emit("setup_end")


    def run_calculation(self, calculation_run_callables: List[Callable[[Any], None]]) -> None:
        if not self.project_settings:
            raise PlaxisConfigurationError("ProjectSettings not provided. Cannot run calculation.")
        if not self.g_i:
            self._connect_to_input_server()

        self.signals.analysis_stage_changed.emit("calculation_start")
        self.signals.progress_updated.emit(2, 4)

        logger.info("Running PLAXIS calculation sequence via API...")
        self._execute_api_commands(calculation_run_callables, self.g_i, "Input (g_i) - Calculation Sequence")
        logger.info("Calculation sequence (including g_i.calculate() if present) reported success by PLAXIS.")
        self.signals.analysis_stage_changed.emit("calculation_end")


        project_save_path = self.project_settings.project_file_path # type: ignore
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
                if not self.project_settings.project_file_path:
                    self.project_settings.project_file_path = project_save_path # type: ignore
            except PlaxisAutomationError as e:
               logger.warning(f"Failed to save project to '{project_save_path}' after calculation: {e}", exc_info=True)
        else:
            logger.warning("`g_i.save` method not available. Cannot save project after calculation.")
        logger.info("PLAXIS calculation and subsequent save attempt finished.")

    def extract_results(self, results_extraction_callables: List[Callable[[Any], Any]]) -> List[Any]:
        if not self.project_settings or not self.project_settings.project_file_path: # type: ignore
            raise PlaxisConfigurationError("ProjectSettings or project_file_path not provided for results extraction.")

        self.signals.analysis_stage_changed.emit("results_start")
        self.signals.progress_updated.emit(3, 4)

        calculated_project_path = self.project_settings.project_file_path # type: ignore
        if not os.path.exists(calculated_project_path):
            raise PlaxisOutputError(f"Calculated project file for results not found: {calculated_project_path}")

        self._connect_to_output_server(project_file_to_open=calculated_project_path)
        logger.info(f"Extracting results via API from PLAXIS Output for project: {calculated_project_path}")

        extracted_data_list: List[Any] = []
        if not self.g_o:
            raise PlaxisConnectionError("PLAXIS Output global object (g_o) unavailable after connection attempt.")

        for i, cmd_callable in enumerate(results_extraction_callables):
            command_name = getattr(cmd_callable, '__name__', f"lambda_res_cmd_at_index_{i+1}")
            try:
                logger.debug(f"Executing result extraction command {i+1}/{len(results_extraction_callables)}: {command_name}")
                result_piece = cmd_callable(self.g_o)
                extracted_data_list.append(result_piece)
            except Exception as e:
                logger.error(f"Result extraction command '{command_name}' failed: {e}", exc_info=True)
                mapped_error = _map_plaxis_sdk_exception_to_custom(e, f"extracting result '{command_name}'")
                extracted_data_list.append(mapped_error)

        logger.info(f"Executed {len(results_extraction_callables)} result callables, yielding {len(extracted_data_list)} pieces.")
        self.signals.analysis_stage_changed.emit("results_end")
        self.signals.progress_updated.emit(4, 4)
        return extracted_data_list

    def map_plaxis_error(self, raw_error_message: str) -> str:
        logger.warning(f"Legacy map_plaxis_error called with: {raw_error_message}. Prefer raising specific exceptions.")
        lower_error = raw_error_message.lower()
        if "connection refused" in lower_error: return "ConnectionRefused"
        if "password incorrect" in lower_error: return "InvalidPassword"
        return f"PlaxisGenericError: {raw_error_message[:100]}"


    def close_all_connections(self):
        logger.info("Attempting to close all PLAXIS connections and processes...")
        if self.s_i or self.g_i:
            logger.info("Nullifying Input server objects (s_i, g_i).")
            self.s_i, self.g_i = None, None
        if self.s_o or self.g_o:
            logger.info("Nullifying Output server objects (s_o, g_o).")
            self.s_o, self.g_o = None, None

        if self.plaxis_process and self.plaxis_process.poll() is None:
            logger.info("Terminating active PLAXIS CLI process...")
            try:
                self.plaxis_process.terminate()
                try:
                    self.plaxis_process.wait(timeout=5)
                    logger.info("PLAXIS CLI process terminated gracefully.")
                except subprocess.TimeoutExpired:
                    logger.warning("PLAXIS CLI process did not terminate gracefully after 5s, attempting to kill.")
                    self.plaxis_process.kill()
                    self.plaxis_process.wait()
                    logger.info("PLAXIS CLI process killed.")
            except Exception as e:
                logger.error(f"Error during PLAXIS CLI process termination: {e}", exc_info=True)
            self.plaxis_process = None
        logger.info("PLAXIS connections and processes handled for closure by PlaxisInteractor.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("\n--- Conceptual Test of PlaxisInteractor (with Exception Handling) ---")

    from dataclasses import dataclass

    class MockProjectSettings(ProjectSettings):
        def __init__(self, project_name: str,
                     api_input_port: int, api_output_port: int, api_password: str,
                     proj_file_path: Optional[str] = None,
                     plaxis_exe: Optional[str] = None):
            super().__init__(project_name=project_name, plaxis_installation_path=plaxis_exe) # type: ignore
            self.plaxis_api_input_port = api_input_port # type: ignore
            self.plaxis_api_output_port = api_output_port # type: ignore
            self.plaxis_api_password = api_password # type: ignore
            self.project_file_path = os.path.abspath(proj_file_path if proj_file_path else f"{project_name}_test.p3dxml") # type: ignore

            @dataclass
            class MockAnalysisSettings:
                max_calc_time_seconds: Optional[int] = 10
            self.analysis_settings = MockAnalysisSettings() # type: ignore


    TEST_API_PASSWORD = "testpassword"
    TEST_PLAXIS_EXE_PATH = "C:/Program Files/Bentley/Geotechnical/PLAXIS 3D CONNECT Edition V22/Plaxis3DInput.exe"

    if not os.path.exists(TEST_PLAXIS_EXE_PATH):
        logger.warning(f"PLAXIS Executable path for testing does not exist: {TEST_PLAXIS_EXE_PATH}. CLI tests may fail or be skipped.")
        TEST_PLAXIS_EXE_PATH = None

    test_proj_name = "InteractorExceptionTest"
    test_file_path = os.path.join(os.getcwd(), f"{test_proj_name}.p3dxml")

    mock_settings = MockProjectSettings(
        project_name=test_proj_name,
        api_input_port=10000, api_output_port=10001,
        api_password=TEST_API_PASSWORD,
        proj_file_path=test_file_path,
        plaxis_exe=TEST_PLAXIS_EXE_PATH
    )
    interactor = PlaxisInteractor(plaxis_path=TEST_PLAXIS_EXE_PATH, project_settings=mock_settings)

    logger.info("\n--- Test 1: API Input Connection Failure (simulated by potentially wrong password/port) ---")
    original_pass = mock_settings.plaxis_api_password
    mock_settings.plaxis_api_password = "wrong_password_for_testing" # type: ignore
    try:
        interactor._connect_to_input_server()
        logger.info("Input server connection: UNEXPECTED SUCCESS (was expecting failure with bad password)")
    except PlaxisConnectionError as e:
        logger.info(f"Input server connection: EXPECTED FAILURE - Caught PlaxisConnectionError: {e}")
    except Exception as e:
        logger.error(f"Input server connection: UNEXPECTED EXCEPTION TYPE - {type(e).__name__}: {e}", exc_info=True)
    finally:
        mock_settings.plaxis_api_password = original_pass # type: ignore

    if TEST_PLAXIS_EXE_PATH:
        logger.info("\n--- Test 2: CLI Execution Failure (simulated with bad command) ---")
        bad_cli_commands = ["this_is_not_a_plaxis_command()"]
        try:
            interactor._execute_cli_script(bad_cli_commands, "bad_script_test.p3dscript")
            logger.info("CLI execution: UNEXPECTED SUCCESS (was expecting PlaxisCliError)")
        except PlaxisCliError as e:
            logger.info(f"CLI execution: EXPECTED FAILURE - Caught PlaxisCliError: {e}")
        except PlaxisConfigurationError as e:
             logger.info(f"CLI execution: EXPECTED CONFIG FAILURE - Caught PlaxisConfigurationError: {e}")
        except Exception as e:
            logger.error(f"CLI execution: UNEXPECTED EXCEPTION TYPE - {type(e).__name__}: {e}", exc_info=True)
    else:
        logger.warning("Skipping CLI execution failure test as PLAXIS executable path is not set.")

    logger.info("\n--- Test 3: Full API Workflow with Simulated Command Failure ---")

    def failing_api_command(g_i_obj: Any):
        logger.debug("Executing intentionally failing API command (e.g., referencing non-existent object).")
        g_i_obj.delete(g_i_obj.Points["NonExistentObject"])

    faulty_setup_callables = [
        lambda gi: gi.gotostructures(),
        failing_api_command
    ]

    did_setup_fail_as_expected = False
    try:
        interactor = PlaxisInteractor(plaxis_path=TEST_PLAXIS_EXE_PATH, project_settings=mock_settings)
        interactor.setup_model_in_plaxis(faulty_setup_callables, is_new_project=True)
        logger.info("Full API workflow (setup_model_in_plaxis with faulty command): UNEXPECTED SUCCESS")
    except PlaxisConfigurationError as e:
        logger.info(f"Full API workflow (setup_model_in_plaxis with faulty command): EXPECTED FAILURE - Caught PlaxisConfigurationError: {e}")
        did_setup_fail_as_expected = True
    except PlaxisAutomationError as e:
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
# The previous ``` was here, ensure it's removed.
