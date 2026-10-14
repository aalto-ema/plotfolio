import unittest

import numpy as np

from plotfolio.fitting import fit_curve
from plotfolio.uncertainty import prediction_band


class UncertaintyTests(unittest.TestCase):
    def test_prediction_bands_are_wider_and_weighted_noise_is_explicit(self):
        x = np.linspace(0, 4, 20)
        y = 2 * x + 1 + 0.1 * np.sin(7 * x)
        fit = fit_curve(x, y)
        interval = prediction_band(fit)
        self.assertTrue(np.all(np.array(interval["prediction_lower"]) <= fit["lower"]))
        self.assertTrue(np.all(np.array(interval["prediction_upper"]) >= fit["upper"]))
        weighted = fit_curve(x, y, sigma=np.full(20, 0.1), absolute_sigma=True)
        with self.assertRaisesRegex(ValueError, "explicit"):
            prediction_band(weighted)
        self.assertEqual(prediction_band(weighted, 0.2)["prediction_sd"], 0.2)
