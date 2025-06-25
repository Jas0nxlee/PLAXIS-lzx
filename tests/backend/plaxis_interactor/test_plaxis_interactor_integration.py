"""
Integration-style tests for PlaxisInteractor, focusing on the orchestration
of command builders, execution, and result parsing, using mocked PLAXIS API.
"""
import pytest
from unittest.mock import MagicMock, patch, call
import os

from backend.plaxis_interactor.interactor import PlaxisInteractor
from backend.models import (
    ProjectSettings, SpudcanGeometry, SoilLayer, MaterialProperties,
    LoadingConditions, AnalysisControlParameters, AnalysisResults
)
from backend.exceptions import (
    PlaxisConnectionError, PlaxisConfigurationError, PlaxisCalculationError,
    PlaxisAutomationError, PlaxisCliError # Added missing imports
)

# --- Mock PLAXIS API Objects ---

class MockPlaxisGlobal:
    """Base class for mock g_i and g_o."""
    def __init__(self):
        self.command_log = []
        self.Project = MagicMock()
        self.Project.Title.value = "MockProjectTitle" # Default title
        self.Phases = [] # For g_o
        self.ResultTypes = MagicMock() # For g_o
        self.SoilMaterials = MagicMock() # For g_i
        self.Points = MagicMock() # For g_i
        self.Lines = MagicMock() # For g_i
        self.Surfaces = MagicMock() # For g_i
        self.Volumes = MagicMock() # For g_i
        self.RigidBodies = MagicMock() # For g_i and g_o
        # Add other commonly accessed top-level objects as MagicMocks

    def __call__(self, command_string: str):
        """Simulate calling g_i('command')"""
        self.command_log.append(command_string)
        # Simulate some common commands or return a new MagicMock
        if command_string.startswith("create "): # e.g. create SoilMaterial
            parts = command_string.split(" ")
            if len(parts) > 1:
                obj_type = parts[1]
                # Return a mock object that can be configured
                mock_obj = MagicMock(name=f"MockCreated_{obj_type}")
                if hasattr(self, obj_type + "s"): # e.g., self.SoilMaterials
                    getattr(self, obj_type + "s")._add_mock_object(mock_obj) # If collection is smart
                return mock_obj
        return MagicMock() # Default for other commands

    def _log_command(self, func_name, *args, **kwargs):
        self.command_log.append(f"{func_name}(args={args}, kwargs={kwargs})")

    def new(self): self._log_command("new"); self.Project.Title.value = "NewMockProject"
    def save(self, filepath: str): self._log_command("save", filepath)
    def open(self, filepath: str): self._log_command("open", filepath)
    def settitle(self, title: str): self.Project.Title.value = title; self._log_command("settitle", title)
    def gotostructures(self): self._log_command("gotostructures") # Example of a mode change
    def gotomesh(self): self._log_command("gotomesh")
    def gotoflow(self): self._log_command("gotoflow")
    def gotostages(self): self._log_command("gotostages")
    def calculate(self, phase_or_all=None): self._log_command("calculate", phase_or_all)
    def breakcalculation(self): self._log_command("breakcalculation")

    # Mock for get_equivalent if this is g_i
    def get_equivalent(self, input_object_ref, output_server_global):
        self._log_command("get_equivalent", input_object_ref, output_server_global)
        # Simulate finding an equivalent object in the output server mock
        # This needs to be smarter based on what input_object_ref is
        if isinstance(input_object_ref, str) and hasattr(output_server_global, "RigidBodies"):
            mock_rb_output = MagicMock(name=f"Equivalent_{input_object_ref}_RB")
            # output_server_global.RigidBodies[input_object_ref] = mock_rb_output # This might be too simple
            return mock_rb_output
        return MagicMock(name="MockEquivalentObject")


class MockGI(MockPlaxisGlobal):
    def __init__(self):
        super().__init__()
        # Specific g_i attributes
        self.Soils = MagicMock() # For creating soil materials
        self.Soil = self.Soils # Alias often used
        self.Phases = [] # g_i also has phases for definition

        # Mocking collections to allow item access like g_i.Points["P1"]
        # and also method calls like g_i.Points.create(...)
        # This requires the MagicMock to also behave like a dict.
        # A more robust mock might use a custom class inheriting from MagicMock.
        for collection_name in ["Points", "Lines", "Surfaces", "Volumes", "RigidBodies", "Plates", "SoilMaterials"]:
            mock_collection = MagicMock()
            # Allow dict-like access and method calls
            # setattr(self, collection_name, type(collection_name + "Collection", (MagicMock, dict), {})())
            setattr(self, collection_name, mock_collection)


class MockGO(MockPlaxisGlobal):
    def __init__(self):
        super().__init__()
        # Specific g_o attributes
        self.ResultTypes = MagicMock()
        self.ResultTypes.Soil = MagicMock()
        self.ResultTypes.RigidBody = MagicMock()
        self.ResultTypes.Plate = MagicMock()
        # ... add more result type categories

        # Define some common result type attributes (as MagicMocks themselves)
        self.ResultTypes.Soil.Ux = MagicMock(name="ResultTypes.Soil.Ux")
        self.ResultTypes.Soil.Uy = MagicMock(name="ResultTypes.Soil.Uy")
        self.ResultTypes.RigidBody.Uy = MagicMock(name="ResultTypes.RigidBody.Uy")
        self.ResultTypes.RigidBody.Fz = MagicMock(name="ResultTypes.RigidBody.Fz")

        self.Phases = [] # List of mock phase objects
        self.Curves = MagicMock()

    def getresults(self, obj_ref, phase_ref, result_type, step_or_node_or_gauss=None):
        self._log_command("getresults", obj_ref, phase_ref, result_type, step_or_node_or_gauss)
        # Return plausible data based on result_type or obj_ref if needed for tests
        if result_type == self.ResultTypes.RigidBody.Uy:
            return [-0.1, -0.2, -0.3] # Example displacement steps
        if result_type == self.ResultTypes.RigidBody.Fz:
            return [100.0, 200.0, 300.0] # Example load steps
        return MagicMock(name="MockResultsValue") # Default

    def getcurveresults(self, curve_object, phase_ref, x_result_type, y_result_type):
        self._log_command("getcurveresults", curve_object, phase_ref, x_result_type, y_result_type)
        # Return data for X and Y axes
        return ([0.1, 0.2, 0.3], [10, 20, 30]) # (x_values, y_values)


@pytest.fixture
def mock_plaxis_servers():
    """Fixture to provide mocked (s_i, g_i) and (s_o, g_o)"""
    s_i = MagicMock(name="s_i_server")
    g_i = MockGI()
    s_i.gotomesh.side_effect = lambda: g_i.gotomesh() # Link server calls to global obj methods
    s_i.gotostructures.side_effect = lambda: g_i.gotostructures()
    # ... and so on for other server methods if they directly call g_i methods.
    # Or, make s_i.g_i = g_i if PlaxisInteractor uses that pattern.
    # The interactor uses `s_i, g_i = new_server(...)` so we mock what `new_server` returns.

    s_o = MagicMock(name="s_o_server")
    g_o = MockGO()

    # Mock the `new_server` function from plxscripting.easy
    # This patch targets where `new_server` is looked up when PlaxisInteractor calls it.
    with patch('backend.plaxis_interactor.interactor.new_server') as mock_new_server:
        # Configure mock_new_server to return different mocks based on port, for example
        def new_server_side_effect(host, port, password):
            if port == 10000: # Assuming default input port
                return s_i, g_i
            elif port == 10001: # Assuming default output port
                return s_o, g_o
            raise ValueError(f"Unexpected port for new_server mock: {port}")
        mock_new_server.side_effect = new_server_side_effect
        yield s_i, g_i, s_o, g_o, mock_new_server


@pytest.fixture
def basic_project_settings():
    """Provides a basic ProjectSettings instance for tests."""
    # Keep this minimal, specific tests can add more details
    return ProjectSettings(
        project_name="TestIntegrationProject",
        spudcan=SpudcanGeometry(diameter=5.0, height_cone_angle=30.0),
        soil_stratigraphy=[
            SoilLayer(name="TopSand", thickness=10.0,
                      material=MaterialProperties(model_name="MohrCoulomb", Identification="Sand", Eref=30000, phi=30))
        ],
        water_table_depth=-2.0,
        loading=LoadingConditions(vertical_preload=100.0, target_type="penetration", target_penetration_or_load=2.0),
            analysis_control=AnalysisControlParameters(meshing_global_coarseness="Medium", MaxStepsStored=50)
            # plaxis_api_password is not a direct field of ProjectSettings dataclass.
            # It's accessed via getattr in PlaxisInteractor.
            # If tests need to simulate these, they should be set on the instance:
            # settings.plaxis_api_password = "test_password"
            # settings.plaxis_api_input_port = 12345
            # settings.plaxis_api_output_port = 12346
    )

# --- Test Cases ---

def test_plaxis_interactor_initialization(basic_project_settings):
    """Test basic initialization of PlaxisInteractor."""
    interactor = PlaxisInteractor(plaxis_path="/fake/plaxis/path", project_settings=basic_project_settings)
    assert interactor.plaxis_path == "/fake/plaxis/path"
    assert interactor.project_settings == basic_project_settings
    assert interactor.s_i is None # Servers not connected yet
    assert interactor.g_i is None

def test_connect_to_input_server_success(mock_plaxis_servers, basic_project_settings):
    """Test successful connection to the input server."""
    s_i_mock, g_i_mock, _, _, _ = mock_plaxis_servers
    interactor = PlaxisInteractor(project_settings=basic_project_settings)

    interactor._connect_to_input_server() # Should use the mocked new_server

    assert interactor.s_i == s_i_mock
    assert interactor.g_i == g_i_mock
    # Check if a basic command like getting title was implicitly called by new_server or connection check
    # This depends on the mock_new_server behavior. If new_server itself tries g_i.Project.Title.value
    # then g_i_mock.Project.Title.value would have been accessed.
    # For now, just check assignment.

def test_connect_to_input_server_failure(mock_plaxis_servers, basic_project_settings):
    """Test failed connection to the input server."""
    _, _, _, _, mock_new_server_func = mock_plaxis_servers

    # Make new_server raise a connection error for input port
    # Get the default input port from an interactor instance, or use the known default
    temp_interactor_for_defaults = PlaxisInteractor()
    default_input_port_for_test = temp_interactor_for_defaults._default_input_port

    def new_server_failure_effect(host, port, password):
        # Use the default port the interactor would try if not set in project_settings
        if port == default_input_port_for_test:
            raise PlaxisConnectionError("Mock Connection Refused")
        return MagicMock(), MagicMock() # For other ports if any
    mock_new_server_func.side_effect = new_server_failure_effect

    interactor = PlaxisInteractor(project_settings=basic_project_settings)
    with pytest.raises(PlaxisConnectionError, match="Mock Connection Refused"):
        interactor._connect_to_input_server()
    assert interactor.s_i is None
    assert interactor.g_i is None


def test_setup_model_flow(mock_plaxis_servers, basic_project_settings):
    """Test the setup_model_in_plaxis method call flow."""
    s_i_mock, g_i_mock, _, _, _ = mock_plaxis_servers
    interactor = PlaxisInteractor(project_settings=basic_project_settings)

    # Define some mock command callables (simplified)
    # These would normally come from geometry_builder, soil_builder etc.
    mock_geom_command = MagicMock(name="geom_command_callable")
    mock_soil_command = MagicMock(name="soil_command_callable")
    model_setup_callables = [mock_geom_command, mock_soil_command]

    interactor.setup_model_in_plaxis(model_setup_callables, is_new_project=True)

    # Assertions:
    # 1. Connection was made (interactor.s_i and g_i are set)
    assert interactor.s_i is not None and interactor.g_i is not None
    # 2. Initial 'new' command was sent for a new project
    assert "new" in [c.split('(')[0] for c in g_i_mock.command_log] # Check if 'new' was called
    # 3. Title was set
    assert f"settitle(args=('{basic_project_settings.project_name}',), kwargs={{}})" in g_i_mock.command_log
    # 4. Each model setup callable was called with g_i
    mock_geom_command.assert_called_once_with(g_i_mock)
    mock_soil_command.assert_called_once_with(g_i_mock)

    # Check signals emitted (example)
    # This requires interactor.signals to be a real QObject with real Signals if not mocked out.
    # For now, we can mock the signals object if it's complex to test Qt signals here.
    # If interactor.signals.analysis_stage_changed is a MagicMock:
    # interactor.signals.analysis_stage_changed.emit.assert_any_call("setup_start")
    # interactor.signals.analysis_stage_changed.emit.assert_any_call("setup_end")


# TODO: Add tests for run_calculation flow
#   - Mocks for calculation_builder.get_full_calculation_workflow_commands
#   - Assert g_i.calculate (or specific phase calculations) are called.
#   - Assert project saving.

# TODO: Add tests for extract_results flow
#   - Mocks for results_parser.get_standard_results_commands
#   - Mocks for g_o.getresults / g_o.getcurveresults
#   - Assert the structure of returned data from interactor.extract_results

# TODO: Test error handling within these flows (e.g., if a command callable raises PlxScriptingError)

# Example for testing a more complex scenario like error during command execution
def test_setup_model_with_command_failure(mock_plaxis_servers, basic_project_settings):
    s_i_mock, g_i_mock, _, _, _ = mock_plaxis_servers
    interactor = PlaxisInteractor(project_settings=basic_project_settings)

    failing_command_callable = MagicMock(name="failing_command")
    # Simulate a PlxScriptingError (or any error that _map_plaxis_sdk_exception_to_custom would handle)
    # Note: PlxScriptingError might not be available if plxscripting is not installed.
    # Using a generic Exception and checking if it's wrapped is also an option.
    try:
        from plxscripting.plx_scripting_exceptions import PlxScriptingError
        error_to_raise = PlxScriptingError("Simulated PLAXIS API error during command")
    except ImportError:
        error_to_raise = RuntimeError("Simulated PLAXIS API error during command (plxscripting not found)")

    failing_command_callable.side_effect = error_to_raise

    model_setup_callables = [failing_command_callable]

    with pytest.raises(PlaxisAutomationError) as excinfo: # Expect our wrapped error
        interactor.setup_model_in_plaxis(model_setup_callables, is_new_project=True)

    assert "Simulated PLAXIS API error" in str(excinfo.value)
    failing_command_callable.assert_called_once_with(g_i_mock)


# Test CLI execution path (if plaxis_path is provided)
# This requires mocking subprocess.Popen
@patch('backend.plaxis_interactor.interactor.os.path.exists')
@patch('backend.plaxis_interactor.interactor.open', new_callable=MagicMock)
@patch('backend.plaxis_interactor.interactor.subprocess.Popen')
def test_execute_cli_script_success(mock_subproc_popen, mock_open_func, mock_os_path_exists, basic_project_settings):
    # Configure the mock Popen object
    mock_os_path_exists.return_value = True # Ensure the mock path is seen as existing
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = ('stdout output', '') # No stderr for clean success
    mock_proc.returncode = 0
    mock_subproc_popen.return_value = mock_proc

    # Configure mock for open (file writing part)
    mock_file_handle = MagicMock()
    mock_open_func.return_value.__enter__.return_value = mock_file_handle

    interactor = PlaxisInteractor(plaxis_path="C:/Plaxis3D/Plaxis3DInput.exe", project_settings=basic_project_settings)

    test_commands = ["command1", "command2"]
    script_filename = "test_cli_script.p3dscript" # This name is used to form abspath
    abs_script_path = os.path.abspath(script_filename)

    interactor._execute_cli_script(test_commands, script_filename)

    # Assert open was called correctly
    mock_open_func.assert_called_once_with(abs_script_path, 'w')

    # Assert commands were written to the mock file handle
    expected_writes = [call("command1\n"), call("command2\n")]
    mock_file_handle.write.assert_has_calls(expected_writes, any_order=False)

    # Assert Popen was called correctly
    expected_cli_call = ["C:/Plaxis3D/Plaxis3DInput.exe", f"--runscript={abs_script_path}"]
    mock_subproc_popen.assert_called_once_with(
        expected_cli_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    mock_proc.communicate.assert_called_once()


# Test CLI execution path failure
@patch('backend.plaxis_interactor.interactor.os.path.exists')
@patch('backend.plaxis_interactor.interactor.open', new_callable=MagicMock)
@patch('backend.plaxis_interactor.interactor.subprocess.Popen')
def test_execute_cli_script_failure(mock_subproc_popen, mock_open_func, mock_os_path_exists, basic_project_settings):
    mock_os_path_exists.return_value = True # Ensure the mock path is seen as existing for this test too
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = ('stdout output', 'CLI ERROR XYZ')
    mock_proc.returncode = 1 # Simulate failure
    mock_subproc_popen.return_value = mock_proc

    interactor = PlaxisInteractor(plaxis_path="C:/Plaxis3D/Plaxis3DInput.exe", project_settings=basic_project_settings)
    test_commands = ["badcommand"]

    with pytest.raises(PlaxisCliError, match="CLI ERROR XYZ"):
        interactor._execute_cli_script(test_commands)

    # Ensure script file is cleaned up if created (it might be, depending on where Popen fails)
        # script_filename = "temp_plaxis_script.p3dscript" # Default name used by interactor
        # abs_script_path = os.path.abspath(script_filename)
        # No need to remove if open is mocked, as it won't be created on disk by the interactor.
        # The interactor's own finally block will attempt os.remove, which is fine.
        pass # No cleanup needed here for the script file due to mocking 'open'

# Need to import subprocess for the Popen mock assertions
import subprocess

# TODO: Test attempt_stop_calculation for both CLI and API scenarios.
# TODO: Test close_all_connections.
# TODO: Test _get_api_credentials with and without project_settings overrides.

# This makes it easier to run this test file directly if needed, though pytest is preferred.
if __name__ == "__main__":
    pytest.main([__file__])
