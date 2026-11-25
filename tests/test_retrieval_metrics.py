import unittest
from pathlib import Path
from tests.evaluate_retrieval import (
    KNOWLEDGE_PATH,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


class TestRetrievalMetrics(unittest.TestCase):

    def setUp(self):
        self.relevant_ids = {
            ("functions", 2),
            ("routes", 2),
        }

    def test_precision_at_k(self):
        retrieved_ids = [
            ("functions", 2),
            ("routes", 0),
            ("routes", 2),
            ("files", "app.py", 0),
            ("forms", 1),
        ]

        self.assertEqual(
            precision_at_k(retrieved_ids, self.relevant_ids, 5),
            0.4,
        )

    def test_precision_when_fewer_than_k_results_are_returned(self):
        retrieved_ids = [
            ("functions", 2),
            ("routes", 0),
        ]

        self.assertEqual(
            precision_at_k(retrieved_ids, self.relevant_ids, 5),
            0.5,
        )

    def test_precision_when_no_results_are_returned(self):
        self.assertEqual(
            precision_at_k([], self.relevant_ids, 5),
            0.0,
        )

    def test_recall_at_k(self):
        retrieved_ids = [
            ("functions", 2),
            ("routes", 0),
            ("routes", 2),
        ]

        self.assertEqual(
            recall_at_k(retrieved_ids, self.relevant_ids, 3),
            1.0,
        )

    def test_reciprocal_rank(self):
        retrieved_ids = [
            ("routes", 0),
            ("functions", 2),
            ("routes", 2),
        ]

        self.assertAlmostEqual(
            reciprocal_rank(retrieved_ids, self.relevant_ids),
            0.5,
        )

    def test_reciprocal_rank_when_no_relevant_result_exists(self):
        retrieved_ids = [
            ("routes", 0),
            ("files", "app.py", 0),
        ]

        self.assertEqual(
            reciprocal_rank(retrieved_ids, self.relevant_ids),
            0.0,
        )

    def test_evaluation_uses_canonical_knowledge_fixture(self):


        expected_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "application_knowledge.json"
        )

        self.assertEqual(KNOWLEDGE_PATH, expected_path)
        self.assertTrue(KNOWLEDGE_PATH.is_file())

    def test_recall_at_k_rejects_empty_relevant_documents(self):
        with self.assertRaises(ValueError):
            recall_at_k(
                [("routes", 0)],
                set(),
                5,
            )

    def test_precision_at_k_rejects_non_positive_k(self):
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    precision_at_k(
                        [("routes", 0)],
                        self.relevant_ids,
                        k,
                    )

    def test_recall_at_k_rejects_non_positive_k(self):
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    recall_at_k(
                        [("routes", 0)],
                        self.relevant_ids,
                        k,
                    )

    def test_reciprocal_rank_with_empty_relevant_documents(self):
        self.assertEqual(
            reciprocal_rank(
                [("routes", 0)],
                set(),
            ),
            0.0,
        )

    def test_precision_at_k_does_not_reward_duplicate_results(self):
        retrieved_ids = [
            ("functions", 2),
            ("functions", 2),
            ("routes", 2),
        ]

        self.assertAlmostEqual(
            precision_at_k(
                retrieved_ids,
                self.relevant_ids,
                3,
            ),
            1.0,
        )
if __name__ == "__main__":
    unittest.main()
