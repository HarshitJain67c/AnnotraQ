#!/usr/bin/env bash
set -euo pipefail

python3 -m unittest discover -s tests -v
python3 -m annotraq validate examples/benchmark.jsonl

report_dir=$(mktemp -d)
trap 'rm -rf "$report_dir"' EXIT
python3 -m annotraq evaluate examples/benchmark.jsonl \
  --json "$report_dir/report.json" \
  --html "$report_dir/report.html" \
  --bootstrap 100
test -s "$report_dir/report.json"
test -s "$report_dir/report.html"
