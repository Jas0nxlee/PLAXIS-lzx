"""
Unit tests for the PLAXIS geometry_builder module.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.backend.models import SpudcanGeometry
from src.backend.plaxis_interactor.geometry_builder import generate_spudcan_geometry_callables
from src.backend.exceptions import PlaxisConfigurationError

class TestGeometryBuilder(unittest.TestCase):
    """
    Test suite for functions in geometry_builder.py.
    """

    def test_generate_spudcan_geometry_callables_valid_cone(self):
        """
        Test generation of callables for a valid spudcan cone.
        """
        spudcan_model = SpudcanGeometry(diameter=6.0, height_cone_angle=30.0) # Using height_cone_angle as per model

        callables = generate_spudcan_geometry_callables(spudcan_model)
        self.assertEqual(len(callables), 1, "Should generate one callable for a simple cone.")

        mock_g_i = MagicMock()
        # Expected calculations based on input:
        # radius = 3.0
        # cone_angle_rad = math.radians(30.0)
        # height = 3.0 / math.tan(cone_angle_rad) approx 5.196

        # Execute the callable
        callables[0](mock_g_i)

        # Assert that g_i.cone was called
        mock_g_i.cone.assert_called_once()
        args, kwargs = mock_g_i.cone.call_args

        # Check parameters passed to g_i.cone
        # args[0] is radius, args[1] is height
        self.assertAlmostEqual(args[0], 3.0, places=5)
        self.assertAlmostEqual(args[1], 5.196152, places=5) # R / tan(30deg)
        self.assertEqual(args[2], (0,0,0)) # BaseCenterCoordinates
        self.assertEqual(args[3], (0,0,-1)) # AxisVector (pointing downwards)

        # Assert that g_i.rename was called
        # The cone_objects from g_i.cone() is expected to be a list, [0] is the volume
        # This depends on the mock_g_i.cone() returning a list with a mock object.
        # If cone_objects[0] is passed directly to rename, then:
        mock_g_i.rename.assert_called_once_with(mock_g_i.cone.return_value[0], "Spudcan_ConeVolume")


    def test_generate_spudcan_geometry_invalid_diameter(self):
        """
        Test that PlaxisConfigurationError is raised for invalid diameter.
        """
        spudcan_model_zero_dia = SpudcanGeometry(diameter=0.0, height_cone_angle=30.0)
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan diameter must be defined and positive."):
            generate_spudcan_geometry_callables(spudcan_model_zero_dia)

        spudcan_model_neg_dia = SpudcanGeometry(diameter=-5.0, height_cone_angle=30.0)
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan diameter must be defined and positive."):
            generate_spudcan_geometry_callables(spudcan_model_neg_dia)

        spudcan_model_none_dia = SpudcanGeometry(diameter=None, height_cone_angle=30.0) # type: ignore
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan diameter must be defined and positive."):
            generate_spudcan_geometry_callables(spudcan_model_none_dia)


    def test_generate_spudcan_geometry_invalid_angle(self):
        """
        Test that PlaxisConfigurationError is raised for invalid cone angle.
        """
        spudcan_model_zero_angle = SpudcanGeometry(diameter=6.0, height_cone_angle=0.0)
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan cone angle must be defined and between 0 and 90 degrees"):
            generate_spudcan_geometry_callables(spudcan_model_zero_angle)

        spudcan_model_90_angle = SpudcanGeometry(diameter=6.0, height_cone_angle=90.0)
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan cone angle must be defined and between 0 and 90 degrees"):
            generate_spudcan_geometry_callables(spudcan_model_90_angle)

        spudcan_model_neg_angle = SpudcanGeometry(diameter=6.0, height_cone_angle=-10.0)
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan cone angle must be defined and between 0 and 90 degrees"):
            generate_spudcan_geometry_callables(spudcan_model_neg_angle)

        spudcan_model_none_angle = SpudcanGeometry(diameter=6.0, height_cone_angle=None) # type: ignore
        with self.assertRaisesRegex(PlaxisConfigurationError, "Spudcan cone angle must be defined and between 0 and 90 degrees"):
            generate_spudcan_geometry_callables(spudcan_model_none_angle)

    def test_create_cone_callable_plaxis_api_error(self):
        """
        Test that an error during g_i.cone or g_i.rename call within the callable propagates up.
        """
        spudcan_model = SpudcanGeometry(diameter=6.0, height_cone_angle=30.0)
        callables = generate_spudcan_geometry_callables(spudcan_model)

        mock_g_i_fails_cone = MagicMock()
        mock_g_i_fails_cone.cone.side_effect = Exception("PLAXIS API error on cone")

        with self.assertRaisesRegex(Exception, "PLAXIS API error on cone"):
            callables[0](mock_g_i_fails_cone)

        mock_g_i_fails_rename = MagicMock()
        # Let cone succeed but rename fail
        mock_g_i_fails_rename.cone.return_value = [MagicMock(name="MockConeVolume")] # Simulate successful cone creation
        mock_g_i_fails_rename.rename.side_effect = Exception("PLAXIS API error on rename")

        with self.assertRaisesRegex(Exception, "PLAXIS API error on rename"):
            callables[0](mock_g_i_fails_rename)

    def test_generate_spudcan_geometry_no_callables_on_init_fail(self):
        """
        Test that if initial validation fails, an empty list or exception is raised
        (current implementation raises PlaxisConfigurationError directly).
        This test re-confirms the behavior checked in invalid_diameter/angle tests.
        """
        spudcan_model_invalid = SpudcanGeometry(diameter=0.0, height_cone_angle=30.0)
        with self.assertRaises(PlaxisConfigurationError):
            generate_spudcan_geometry_callables(spudcan_model_invalid)

if __name__ == '__main__':
    unittest.main()
