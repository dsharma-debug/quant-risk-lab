"""Checks of experiment statistics and reproducible trial scheduling."""

import math
import unittest

from mc_repeated_experiment import run_experiment, summarize_trials


class RepeatedExperimentTests(unittest.TestCase):
    def test_hand_calculated_summary(self):
        trials = [dict(price=1, standard_error=0.5, ci_low=0.02, ci_high=1.98),
                  dict(price=3, standard_error=1.0, ci_low=1.04, ci_high=4.96)]
        summary = summarize_trials(trials, reference=2)
        self.assertEqual(summary["mean_price"], 2)
        self.assertEqual(summary["estimated_bias"], 0)
        self.assertEqual(summary["rmse"], 1)
        self.assertAlmostEqual(summary["empirical_sd"], math.sqrt(2))
        self.assertEqual(summary["mean_standard_error"], 0.75)
        self.assertEqual(summary["coverage_count"], 1)
        self.assertEqual(summary["coverage_rate"], 0.5)

    def test_interval_endpoints_are_included(self):
        rows = [dict(price=2, standard_error=0, ci_low=2, ci_high=2)] * 2
        result = summarize_trials(rows, reference=2)
        self.assertEqual(result["coverage_rate"], 1)
        self.assertEqual(result["rmse"], 0)
        self.assertEqual(result["empirical_sd"], 0)

    def test_reject_too_few_trials(self):
        for rows in ([], [dict(price=2)]):
            with self.assertRaises(ValueError):
                summarize_trials(rows, reference=2)

    def test_small_experiment_structure_and_seeds(self):
        trials, summaries = run_experiment((5, 10), repetitions=3, seed_start=20)
        self.assertEqual(len(trials), 12)
        self.assertEqual(len(summaries), 4)
        for kind in ("call", "put"):
            for samples in (5, 10):
                group = [row for row in trials if row["option_type"] == kind
                         and row["samples"] == samples]
                self.assertEqual([row["seed"] for row in group], [20, 21, 22])
                self.assertTrue(all(row["covered"] in (0, 1) for row in group))
        self.assertEqual((trials, summaries),
                         run_experiment((5, 10), repetitions=3, seed_start=20))

    def test_invalid_experiment_configuration(self):
        invalid = [dict(repetitions=1), dict(repetitions=True),
                   dict(sample_counts=()), dict(sample_counts=(1,)),
                   dict(sample_counts=(10, 10)), dict(sample_counts=(True,)),
                   dict(sample_counts=(2.5,)), dict(seed_start="20")]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    run_experiment(**kwargs)


if __name__ == "__main__":
    unittest.main()
