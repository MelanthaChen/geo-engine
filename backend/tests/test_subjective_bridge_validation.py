import math
import tempfile
import unittest
from pathlib import Path

from app.evaluation.subjective_bridge_validation import (
    AnswerSample,
    CANDIDATE_MODEL,
    DIMENSIONS,
    LEGACY_MODEL,
    ScoreObservation,
    agreement_metrics,
    confusion_matrix,
    expected_score,
    generate_outputs,
    kendall_tau_b,
    spearman,
)


class SubjectiveBridgeStatisticsTests(unittest.TestCase):
    def test_expected_score_matches_official_weighting(self):
        score = expected_score({" 1": math.log(0.2), " 3": math.log(0.3), " 5": math.log(0.5)})
        self.assertAlmostEqual(score, 3.6)

    def test_rank_correlations_handle_ties(self):
        left = [1, 2, 2, 4]
        self.assertAlmostEqual(spearman(left, left), 1.0)
        self.assertAlmostEqual(kendall_tau_b(left, left), 1.0)

    def test_agreement_and_confusion_matrix(self):
        metrics = agreement_metrics([1, 2, 3], [1, 2, 4])
        self.assertEqual(metrics["n"], 3)
        self.assertAlmostEqual(metrics["mae"], 1 / 3)
        matrix = confusion_matrix([1.1, 2.2, 4.8], [1.2, 3.1, 4.9])
        self.assertEqual(sum(sum(row) for row in matrix), 3)

    def test_report_and_all_plot_artifacts_are_generated(self):
        samples = []
        observations = []
        strategies = ["original", "citation", "statistics", "quotation"]
        for index in range(20):
            sample = AnswerSample(index + 1, index + 101, f"q{index}", f"a{index}", 1, strategies[index % 4], index % 5, 0.1 + index / 100)
            samples.append(sample)
            for dimension_index, dimension in enumerate(DIMENSIONS):
                legacy = 1.2 + ((index + dimension_index) % 4)
                candidate = legacy + (0.04 if index % 2 else -0.04)
                for model, score in ((LEGACY_MODEL, legacy), (CANDIDATE_MODEL, candidate)):
                    observations.append(ScoreObservation(sample.result_id, model, model, dimension, score, 100, 1, 10))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            summary = generate_outputs(output, samples, observations)
            self.assertEqual(summary["decision"], "SUPPORTED")
            self.assertTrue((output / "BridgeValidationReport.md").exists())
            self.assertTrue((output / "bland_altman_all_dimensions.svg").exists())
            for dimension in DIMENSIONS:
                self.assertTrue((output / f"scatter_{dimension}.svg").exists())
                self.assertTrue((output / f"confusion_{dimension}.svg").exists())


if __name__ == "__main__":
    unittest.main()

