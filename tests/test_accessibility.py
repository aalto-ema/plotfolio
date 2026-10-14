import unittest

import numpy as np

from plotfolio.accessibility import simulate


class AccessibilityTests(unittest.TestCase):
    def test_grayscale_equal_channels_and_white_preserved(self):
        colors = np.array([[1, 0, 0], [1, 1, 1], [0, 0, 0]])
        gray = simulate(colors, "Grayscale")
        np.testing.assert_allclose(gray[:, 0], gray[:, 1])
        for mode in ["Original", "Protan", "Deutan", "Tritan"]:
            output = simulate(colors, mode)
            self.assertTrue(np.all(output >= 0))
            self.assertTrue(np.all(output <= 1))
            np.testing.assert_allclose(output[1], [1, 1, 1], atol=2e-6)
