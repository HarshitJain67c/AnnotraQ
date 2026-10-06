from __future__ import annotations

import unittest

from annotraq.core import DatasetError, evaluate, validate_items


class EvaluationTest(unittest.TestCase):
    def test_perfect_classification_scores_one_hundred(self) -> None:
        report = evaluate([
            {"id": "one", "task": "classification", "input": "Text", "reference": "Positive", "annotation": "positive"}
        ], bootstrap_rounds=20)
        self.assertEqual(100.0, report["summary"]["overall_score"])
        self.assertEqual("A", report["summary"]["grade"])
        self.assertEqual([100.0, 100.0], report["summary"]["confidence_interval_95"])

    def test_multilabel_uses_f1_and_recall(self) -> None:
        report = evaluate([
            {"id": "labels", "task": "multilabel", "input": "Text", "reference": ["billing", "urgent"], "annotation": ["billing"]}
        ], bootstrap_rounds=0)
        item = report["items"][0]
        self.assertEqual(66.67, item["scores"]["accuracy"])
        self.assertEqual(50.0, item["scores"]["completeness"])
        self.assertEqual(70.0, item["overall_score"])

    def test_group_consistency_penalizes_disagreement(self) -> None:
        items = [
            {"id": "repeat-a", "group_id": "repeat", "task": "classification", "input": "Same", "reference": "yes", "annotation": "yes"},
            {"id": "repeat-b", "group_id": "repeat", "task": "classification", "input": "Same", "reference": "yes", "annotation": "no"},
        ]
        report = evaluate(items, bootstrap_rounds=0)
        self.assertEqual(50.0, report["items"][0]["scores"]["consistency"])
        self.assertEqual(95.0, report["items"][0]["overall_score"])
        self.assertEqual(35.0, report["items"][1]["overall_score"])

    def test_valid_spans_match_exact_boundaries_and_labels(self) -> None:
        item = {
            "id": "span",
            "task": "span",
            "input": "Ada works at Acme",
            "reference": [{"start": 0, "end": 3, "label": "PERSON", "text": "Ada"}],
            "annotation": [{"start": 0, "end": 3, "label": "person", "text": "Ada"}],
        }
        self.assertEqual(100.0, evaluate([item])["summary"]["overall_score"])

    def test_bad_span_is_reported_instead_of_crashing(self) -> None:
        item = {
            "id": "bad-span",
            "task": "span",
            "input": "Ada",
            "reference": [{"start": 0, "end": 3, "label": "PERSON"}],
            "annotation": [{"start": 0, "end": 7, "label": "PERSON"}],
        }
        result = evaluate([item])["items"][0]
        self.assertEqual(0.0, result["scores"]["format_validity"])
        self.assertEqual(10.0, result["overall_score"])
        self.assertIn("outside the input", result["errors"][0])

    def test_free_text_is_case_and_punctuation_insensitive(self) -> None:
        item = {"id": "text", "task": "free_text", "input": "Prompt", "reference": "A short answer.", "annotation": "a SHORT answer"}
        self.assertEqual(100.0, evaluate([item])["summary"]["overall_score"])

    def test_validation_rejects_duplicate_ids_and_unknown_tasks(self) -> None:
        duplicate = {"id": "same", "task": "classification", "input": "", "reference": "a", "annotation": "a"}
        with self.assertRaisesRegex(DatasetError, "duplicate id"):
            validate_items([duplicate, duplicate])
        with self.assertRaisesRegex(DatasetError, "unsupported task"):
            validate_items([{**duplicate, "id": "other", "task": "ranking"}])

    def test_custom_weights_must_sum_to_one(self) -> None:
        item = {"id": "one", "task": "classification", "input": "", "reference": "a", "annotation": "a"}
        with self.assertRaisesRegex(DatasetError, "add up to 1.0"):
            evaluate([item], weights={"accuracy": 1, "completeness": 1, "consistency": 1, "format_validity": 1})


if __name__ == "__main__":
    unittest.main()
