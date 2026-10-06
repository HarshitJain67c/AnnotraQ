from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from annotraq.cli import main
from annotraq.core import evaluate
from annotraq.io import load_jsonl
from annotraq.reporting import render_html


class CliAndReportingTest(unittest.TestCase):
    def test_cli_writes_json_and_html_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "input.jsonl"
            json_report = root / "report.json"
            html_report = root / "report.html"
            dataset.write_text(
                json.dumps({"id": "example", "task": "classification", "input": "Text", "reference": "yes", "annotation": "yes"}) + "\n",
                encoding="utf-8",
            )
            status = main(["evaluate", str(dataset), "--json", str(json_report), "--html", str(html_report), "--bootstrap", "10"])
            self.assertEqual(0, status)
            self.assertEqual(100.0, json.loads(json_report.read_text())["summary"]["overall_score"])
            self.assertIn("AnnotraQ", html_report.read_text())

    def test_loader_identifies_line_with_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "bad.jsonl"
            dataset.write_text('{"id": "good"}\nnot json\n', encoding="utf-8")
            with self.assertRaisesRegex(Exception, ":2: invalid JSON"):
                load_jsonl(dataset)

    def test_report_escapes_user_controlled_identifiers(self) -> None:
        item = {"id": "<script>alert(1)</script>", "task": "classification", "input": "", "reference": "a", "annotation": "a"}
        html = render_html(evaluate([item]))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
