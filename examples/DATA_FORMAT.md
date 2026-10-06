# Dataset format

AnnotraQ reads UTF-8 JSON Lines: one object per annotation.

Every record requires:

- `id`: unique string
- `task`: `classification`, `multilabel`, `span`, or `free_text`
- `input`: source text presented to the annotator
- `reference`: adjudicated gold annotation
- `annotation`: annotation being evaluated
- `group_id` (optional): links repeated examples for consistency scoring

## Classification

```json
{"id":"c-1","task":"classification","input":"Great service","reference":"positive","annotation":"positive"}
```

## Multilabel

```json
{"id":"m-1","task":"multilabel","input":"Charged twice","reference":["billing","urgent"],"annotation":["billing"]}
```

## Spans

Offsets are zero-based, use an exclusive `end`, and must refer to the original `input`.
The optional `text` value is checked against the selected source substring.

```json
{"id":"s-1","task":"span","input":"Ada works here","reference":[{"start":0,"end":3,"label":"PERSON","text":"Ada"}],"annotation":[{"start":0,"end":3,"label":"PERSON","text":"Ada"}]}
```

## Free text

Free-text accuracy uses case-insensitive token F1. It measures lexical agreement,
not factual equivalence or semantic correctness.

```json
{"id":"f-1","task":"free_text","input":"Summarize...","reference":"A short reference.","annotation":"A short response."}
```
