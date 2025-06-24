import pytest
import logging
from typing import Any, List, Dict, Optional, Tuple

# Setup basic logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Models and parser to test
from src.backend.models import AnalysisResults, ProjectSettings, SpudcanGeometry, LoadingConditions, AnalysisControlParameters
from src.backend.plaxis_interactor.results_parser import (
    parse_load_penetration_curve,
    parse_final_penetration_depth,
    parse_peak_vertical_resistance,
    compile_analysis_results,
    get_standard_results_commands
)
# from src.backend.exceptions import PlaxisOutputError # If we want to test for specific errors

# Mock g_o object for testing parser functions
class MockG_o_ForResults:
    def __init__(self):
        self.log = []
        self.ResultTypes = self._create_mock_result_types()
        self.Phases = [] # List of mock phase objects
        self.RigidBodies = {} # Dict of mock rigid body objects
        self.Curves = {} # Dict of mock curve objects
        self._current_phase_results = {} # Stores results for the "current" phase being queried

    def _create_mock_result_types(self):
        # Create nested mock objects to simulate g_o.ResultTypes.Soil.Ux etc.
        class MockResultType:
            def __init__(self, name): self.name = name
            def __repr__(self): return f"MockResultType({self.name})"

        SoilResults = type("Soil", (), {
            "Ux": MockResultType("Soil.Ux"), "Uy": MockResultType("Soil.Uy"),
            "Uz": MockResultType("Soil.Uz"), "Utot": MockResultType("Soil.Utot")
        })
        RigidBodyResults = type("RigidBody", (), {
            "Uy": MockResultType("RigidBody.Uy"), # Vertical displacement
            "Fz": MockResultType("RigidBody.Fz")  # Vertical force
        })
        # Example for predefined curves (these are just placeholders for type checking)
        SumMstage = MockResultType("SumMstage")
        SumFstage_Z = MockResultType("SumFstage_Z")

        return type("ResultTypes", (), {
            "Soil": SoilResults(),
            "RigidBody": RigidBodyResults(),
            "SumMstage": SumMstage, # Example, actual name might vary
            "SumFstage_Z": SumFstage_Z # Example
        })()

    def _add_mock_phase(self, name="Phase_1", identification="Phase_1_ID"):
        mock_phase = type("MockPhase", (), {
            "Name": type("NameProp", (), {"value": name})(),
            "Identification": type("IdProp", (), {"value": identification})()
        })()
        self.Phases.append(mock_phase)
        return mock_phase

    def _add_mock_rigid_body(self, name="Spudcan"):
        mock_rb = type("MockRigidBody", (), {"Name": name})()
        self.RigidBodies[name] = mock_rb
        return mock_rb

    def _add_mock_curve(self, name="SpudcanPath"):
        mock_curve = type("MockCurve", (), {"Name": name})()
        self.Curves[name] = mock_curve
        return mock_curve

    def getresults(self, obj_ref, phase_ref, result_type, step_or_node=None):
        obj_name = getattr(obj_ref, "Name", str(obj_ref))
        phase_name = getattr(phase_ref.Name, "value", str(phase_ref))
        rt_name = getattr(result_type, "name", str(result_type))
        self.log.append(f"CALL: g_o.getresults(obj='{obj_name}', phase='{phase_name}', type='{rt_name}', step/node='{step_or_node}')")

        # Return predefined data for specific scenarios
        if obj_name == "Spudcan" and self.Phases and phase_name == self.Phases[-1].Name.value: # Assuming last phase
            if rt_name == "RigidBody.Uy":
                return [-0.1, -0.2, -0.3, -0.4, -0.5] # Penetration steps
            if rt_name == "RigidBody.Fz":
                return [-100.0, -200.0, -300.0, -280.0, -250.0] # Load steps
        return [] # Default empty

    def getsingleresult(self, phase_ref, result_type, coords_or_object):
        phase_name = getattr(phase_ref.Name, "value", str(phase_ref))
        rt_name = getattr(result_type, "name", str(result_type))
        self.log.append(f"CALL: g_o.getsingleresult(phase='{phase_name}', type='{rt_name}', target='{coords_or_object}')")
        if isinstance(coords_or_object, str) and coords_or_object == "Spudcan" and rt_name == "RigidBody.Uy":
             # Get the last value from the step results for the final value
            step_results = self.getresults(self.RigidBodies["Spudcan"], phase_ref, result_type, 'step')
            return step_results[-1] if step_results else None
        return 0.0 # Default

    def getcurveresults(self, curve_obj, phase_obj, x_type, y_type):
        curve_name = getattr(curve_obj, "Name", str(curve_obj))
        phase_name = getattr(phase_obj.Name, "value", str(phase_obj))
        x_type_name = getattr(x_type, "name", str(x_type))
        y_type_name = getattr(y_type, "name", str(y_type))
        self.log.append(f"CALL: g_o.getcurveresults(curve='{curve_name}', phase='{phase_name}', x_type='{x_type_name}', y_type='{y_type_name}')")
        if curve_name == "PredefinedSpudcanCurve" and self.Phases and phase_name == self.Phases[-1].Name.value:
             # Ensure X is penetration (negative displacement), Y is load (negative force)
            return ([-0.1, -0.2, -0.3, -0.4, -0.55], [-110.0, -220.0, -330.0, -290.0, -260.0])
        return ([], [])


# --- Tests for individual parsers ---

def test_parse_load_penetration_curve_step_by_step():
    mock_g_o = MockG_o_ForResults()
    mock_g_o._add_mock_phase("CalcPhase")
    mock_g_o._add_mock_rigid_body("Spudcan")

    curve = parse_load_penetration_curve(
        mock_g_o,
        spudcan_ref_object_name="Spudcan",
        step_disp_component_result_type=mock_g_o.ResultTypes.RigidBody.Uy,
        step_load_component_result_type=mock_g_o.ResultTypes.RigidBody.Fz
    )
    assert len(curve) == 5
    assert curve[2] == {'penetration': 0.3, 'load': 300.0} # abs values

def test_parse_load_penetration_curve_predefined():
    mock_g_o = MockG_o_ForResults()
    mock_g_o._add_mock_phase("CalcPhase")
    mock_g_o._add_mock_curve("PredefinedSpudcanCurve")

    curve = parse_load_penetration_curve(
        mock_g_o,
        predefined_curve_name="PredefinedSpudcanCurve",
        curve_x_axis_result_type=mock_g_o.ResultTypes.RigidBody.Uy, # Using these as placeholders
        curve_y_axis_result_type=mock_g_o.ResultTypes.RigidBody.Fz
    )
    assert len(curve) == 5
    assert curve[2] == {'penetration': 0.3, 'load': 330.0}

def test_parse_final_penetration_depth_object():
    mock_g_o = MockG_o_ForResults()
    mock_g_o._add_mock_phase("CalcPhaseFinal")
    mock_g_o._add_mock_rigid_body("Spudcan")

    # Mock getresults for this specific case
    def mock_getresults_final_pen(obj_ref, phase_ref, result_type, step_or_node=None):
        if getattr(obj_ref,"Name","") == "Spudcan" and result_type.name == "RigidBody.Uy":
            return [-0.1, -0.5, -0.9] # Final value -0.9
        return []
    mock_g_o.getresults = mock_getresults_final_pen

    depth = parse_final_penetration_depth(
        mock_g_o,
        spudcan_ref_object_name="Spudcan",
        disp_component_result_type=mock_g_o.ResultTypes.RigidBody.Uy
    )
    assert depth == pytest.approx(0.9)

def test_parse_peak_vertical_resistance():
    curve_data = [
        {'penetration': 0.1, 'load': 100},
        {'penetration': 0.2, 'load': 250}, # Peak
        {'penetration': 0.3, 'load': 200},
        {'penetration': 0.4, 'load': -300}, # Higher absolute, but check if logic uses abs()
    ]
    peak = parse_peak_vertical_resistance(curve_data)
    assert peak == 300 # parse_peak_vertical_resistance uses abs(load)

# --- Tests for compile_analysis_results and get_standard_results_commands ---

def test_compile_analysis_results():
    raw_results = [
        [{'penetration': 0.1, 'load': 100}, {'penetration': 0.2, 'load': 200}], # Curve
        0.2  # Final penetration
    ]
    compiled = compile_analysis_results(raw_results)
    assert len(compiled.load_penetration_curve_data) == 2
    assert compiled.final_penetration_depth == 0.2
    assert compiled.peak_vertical_resistance == 200

def test_get_standard_results_commands_and_compile():
    mock_g_o = MockG_o_ForResults()
    mock_g_o._add_mock_phase("StandardPhase")
    mock_g_o._add_mock_rigid_body("Spudcan") # Name used in get_standard_results_commands

    # Mock project settings (simplified)
    class MockSpudcanModel:
        diameter = 6.0
        height_cone_angle = 30.0

    class MockProjectSettings:
        spudcan = MockSpudcanModel()
        # Add other fields if get_standard_results_commands uses them

    mock_ps = MockProjectSettings()

    result_callables = get_standard_results_commands(mock_ps)
    assert len(result_callables) == 2 # Curve and Final Penetration

    raw_data = []
    for func in result_callables:
        raw_data.append(func(mock_g_o))

    assert len(raw_data) == 2
    # raw_data[0] is curve, raw_data[1] is final penetration
    assert len(raw_data[0]) == 5 # From mock_g_o.getresults for curve
    assert raw_data[1] == pytest.approx(0.5) # From mock_g_o.getresults, last value is -0.5

    compiled = compile_analysis_results(raw_data, mock_ps)
    assert len(compiled.load_penetration_curve_data) == 5
    assert compiled.load_penetration_curve_data[2]['penetration'] == 0.3
    assert compiled.load_penetration_curve_data[2]['load'] == 300.0
    assert compiled.final_penetration_depth == pytest.approx(0.5)
    assert compiled.peak_vertical_resistance == 300.0
