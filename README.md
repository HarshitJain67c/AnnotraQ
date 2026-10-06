# AnnotraQ

AnnotraQ is a transparent benchmark for measuring the quality of AI-generated
data annotations against adjudicated reference data. It produces a 0–100 score,
dimension-level diagnostics, task slices, item-level errors, and a self-contained
HTML audit report.

The runtime uses only the Python standard library. Scoring is deterministic;
the bootstrap confidence interval is reproducible with a configurable seed.

## What it measures

| Dimension | Default weight | Meaning |
| --- | ---: | --- |
| Accuracy | 60% | Exact match or task-appropriate F1 against the reference |
| Completeness | 20% | Reference coverage (recall) or presence of a required answer |
| Consistency | 10% | Agreement across records sharing a `group_id` |
| Format validity | 10% | Correct types, span bounds, labels, and source alignment |

The total score is the weighted mean of these four dimensions. Letter grades use
90/80/70/60 cutoffs. AnnotraQ also reports a non-parametric 95% bootstrap
confidence interval over item scores.

Supported task types:

- single-label classification
- multilabel classification
- exact labeled spans
- free text using token-level precision, recall, and F1

## Quick start

Python 3.9 or newer is required.

```bash
python3 -m annotraq validate examples/benchmark.jsonl
python3 -m annotraq evaluate examples/benchmark.jsonl \
  --json annotraq-report.json \
  --html annotraq-report.html
```

The evaluation prints the overall score and creates both a machine-readable JSON
report and a responsive HTML report that can be opened directly in a browser.

To install the `annotraq` command locally:

```bash
python3 -m pip install -e .
annotraq evaluate examples/benchmark.jsonl
```

## Input

AnnotraQ accepts UTF-8 JSONL with one record per annotation:

```json
{"id":"sentiment-1","task":"classification","input":"Great service","reference":"positive","annotation":"positive"}
```

Use the optional `group_id` on repeated or equivalent records to measure output
consistency. Span annotations use zero-based, end-exclusive offsets.

See [examples/DATA_FORMAT.md](examples/DATA_FORMAT.md) for all task formats and
[examples/benchmark.jsonl](examples/benchmark.jsonl) for a mixed-quality sample.

## Customize scoring

All four weights must be provided and must add up to `1.0`:

```bash
annotraq evaluate data.jsonl \
  --weights accuracy=.7,completeness=.15,consistency=.1,format_validity=.05
```

For reproducible uncertainty estimates, the default seed is `42`. Change the
number of resamples or seed with `--bootstrap` and `--seed`.

## Use as a library

```python
from annotraq import evaluate

report = evaluate([
    {
        "id": "example-1",
        "task": "classification",
        "input": "The product arrived early.",
        "reference": "positive",
        "annotation": "positive",
    }
])

print(report["summary"]["overall_score"])
```

## Responsible interpretation

AnnotraQ measures agreement with the supplied reference—not truth in isolation.
A high score is meaningful only when references are accurate, guidelines are
clear, and the benchmark represents production data. Free-text scoring is lexical
and should not be presented as a semantic or factuality judgment. Use item-level
diagnostics and human adjudication for consequential decisions.

## Verify

```bash
./verify.sh
```

The verification suite tests scoring, validation, consistency groups, malformed
annotations, report escaping, and command-line output.

## License

[MIT](LICENSE)
