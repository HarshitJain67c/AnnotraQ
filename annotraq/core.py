from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import math
import random
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SUPPORTED_TASKS = {"classification", "multilabel", "span", "free_text"}
DEFAULT_WEIGHTS = {
    "accuracy": 0.60,
    "completeness": 0.20,
    "consistency": 0.10,
    "format_validity": 0.10,
}
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


class DatasetError(ValueError):
    """Raised when an input dataset cannot be benchmarked."""


def _normalize_text(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(value.casefold()))


def _tokens(value: str) -> List[str]:
    return TOKEN_PATTERN.findall(value.casefold())


def _counter_prf(reference: Sequence[str], annotation: Sequence[str]) -> Tuple[float, float, float]:
    reference_counts = Counter(reference)
    annotation_counts = Counter(annotation)
    overlap = sum((reference_counts & annotation_counts).values())
    precision = overlap / len(annotation) if annotation else float(not reference)
    recall = overlap / len(reference) if reference else float(not annotation)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _set_prf(reference: Iterable[Any], annotation: Iterable[Any]) -> Tuple[float, float, float]:
    reference_set = set(reference)
    annotation_set = set(annotation)
    overlap = len(reference_set & annotation_set)
    precision = overlap / len(annotation_set) if annotation_set else float(not reference_set)
    recall = overlap / len(reference_set) if reference_set else float(not annotation_set)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _validate_weights(weights: Mapping[str, float] | None) -> Dict[str, float]:
    result = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(result) != set(DEFAULT_WEIGHTS):
        raise DatasetError("weights must define accuracy, completeness, consistency, and format_validity")
    if any(not isinstance(value, (int, float)) or value < 0 for value in result.values()):
        raise DatasetError("weights must be non-negative numbers")
    total = sum(result.values())
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise DatasetError(f"weights must add up to 1.0, got {total:g}")
    return {key: float(value) for key, value in result.items()}


def _span_values(value: Any, source: str) -> Tuple[List[Tuple[int, int, str]], List[str]]:
    if not isinstance(value, list):
        return [], ["span annotations must be a list"]
    spans: List[Tuple[int, int, str]] = []
    errors: List[str] = []
    for index, span in enumerate(value):
        if not isinstance(span, dict):
            errors.append(f"span {index} must be an object")
            continue
        start = span.get("start")
        end = span.get("end")
        label = span.get("label")
        if not isinstance(start, int) or isinstance(start, bool):
            errors.append(f"span {index} start must be an integer")
            continue
        if not isinstance(end, int) or isinstance(end, bool):
            errors.append(f"span {index} end must be an integer")
            continue
        if not isinstance(label, str) or not label.strip():
            errors.append(f"span {index} label must be a non-empty string")
            continue
        if start < 0 or end <= start or end > len(source):
            errors.append(f"span {index} bounds [{start}, {end}) are outside the input")
            continue
        if "text" in span and span["text"] != source[start:end]:
            errors.append(f"span {index} text does not match input[{start}:{end}]")
            continue
        spans.append((start, end, label.casefold().strip()))
    return spans, errors


def _normalized_annotation(item: Mapping[str, Any]) -> Any:
    task = item["task"]
    annotation = item["annotation"]
    if task in {"classification", "free_text"}:
        return _normalize_text(annotation) if isinstance(annotation, str) else repr(annotation)
    if task == "multilabel":
        if not isinstance(annotation, list):
            return repr(annotation)
        return tuple(sorted(str(value).casefold().strip() for value in annotation))
    spans, errors = _span_values(annotation, item["input"])
    return tuple(sorted(spans)) if not errors else repr(annotation)


def _score_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    task = item["task"]
    reference = item["reference"]
    annotation = item["annotation"]
    details: Dict[str, Any] = {}
    errors: List[str] = []

    if task == "classification":
        if not isinstance(reference, str) or not isinstance(annotation, str):
            errors.append("classification reference and annotation must be strings")
            accuracy = completeness = 0.0
        else:
            reference_value = _normalize_text(reference)
            annotation_value = _normalize_text(annotation)
            accuracy = float(reference_value == annotation_value)
            completeness = float(bool(annotation_value))
            details["exact_match"] = bool(accuracy)

    elif task == "multilabel":
        if not isinstance(reference, list) or not isinstance(annotation, list):
            errors.append("multilabel reference and annotation must be lists")
            accuracy = completeness = 0.0
        elif not all(isinstance(label, str) and label.strip() for label in reference + annotation):
            errors.append("multilabel values must be non-empty strings")
            accuracy = completeness = 0.0
        else:
            reference_values = [label.casefold().strip() for label in reference]
            annotation_values = [label.casefold().strip() for label in annotation]
            precision, recall, accuracy = _set_prf(reference_values, annotation_values)
            completeness = recall
            details.update(precision=round(precision, 4), recall=round(recall, 4), f1=round(accuracy, 4))

    elif task == "span":
        reference_values, reference_errors = _span_values(reference, item["input"])
        annotation_values, annotation_errors = _span_values(annotation, item["input"])
        errors.extend(f"reference: {error}" for error in reference_errors)
        errors.extend(f"annotation: {error}" for error in annotation_errors)
        if reference_errors or annotation_errors:
            accuracy = completeness = 0.0
        else:
            precision, recall, accuracy = _set_prf(reference_values, annotation_values)
            completeness = recall
            details.update(precision=round(precision, 4), recall=round(recall, 4), f1=round(accuracy, 4))

    else:
        if not isinstance(reference, str) or not isinstance(annotation, str):
            errors.append("free_text reference and annotation must be strings")
            accuracy = completeness = 0.0
        else:
            precision, recall, accuracy = _counter_prf(_tokens(reference), _tokens(annotation))
            completeness = recall
            details.update(
                exact_match=_normalize_text(reference) == _normalize_text(annotation),
                token_precision=round(precision, 4),
                token_recall=round(recall, 4),
                token_f1=round(accuracy, 4),
            )

    return {
        "id": item["id"],
        "task": task,
        "group_id": item.get("group_id"),
        "scores": {
            "accuracy": accuracy,
            "completeness": completeness,
            "consistency": 1.0,
            "format_validity": float(not errors),
        },
        "errors": errors,
        "details": details,
    }


def _apply_consistency(items: Sequence[Mapping[str, Any]], results: List[Dict[str, Any]]) -> None:
    groups: Dict[str, List[int]] = defaultdict(list)
    for index, item in enumerate(items):
        group_id = item.get("group_id")
        if group_id is not None:
            groups[str(group_id)].append(index)

    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        values = [_normalized_annotation(items[index]) for index in indexes]
        counts = Counter(values)
        agreement = max(counts.values()) / len(values)
        for index in indexes:
            results[index]["scores"]["consistency"] = agreement
            results[index]["details"]["group_agreement"] = round(agreement, 4)


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def _confidence_interval(scores: Sequence[float], rounds: int, seed: int) -> List[float]:
    if not scores:
        return [0.0, 0.0]
    if rounds <= 0:
        return [round(sum(scores) / len(scores), 2)] * 2
    generator = random.Random(seed)
    means = []
    for _ in range(rounds):
        sample = [generator.choice(scores) for _ in scores]
        means.append(sum(sample) / len(sample))
    means.sort()
    return [round(_percentile(means, 0.025), 2), round(_percentile(means, 0.975), 2)]


def validate_items(items: Sequence[Mapping[str, Any]]) -> None:
    if not items:
        raise DatasetError("dataset is empty")
    seen = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            raise DatasetError(f"item {index} must be an object")
        missing = {"id", "task", "input", "reference", "annotation"} - set(item)
        if missing:
            raise DatasetError(f"item {index} is missing: {', '.join(sorted(missing))}")
        if not isinstance(item["id"], str) or not item["id"].strip():
            raise DatasetError(f"item {index} id must be a non-empty string")
        if item["id"] in seen:
            raise DatasetError(f"duplicate id: {item['id']}")
        seen.add(item["id"])
        if item["task"] not in SUPPORTED_TASKS:
            raise DatasetError(f"item {item['id']} has unsupported task: {item['task']}")
        if not isinstance(item["input"], str):
            raise DatasetError(f"item {item['id']} input must be a string")
        if "group_id" in item and not isinstance(item["group_id"], (str, int)):
            raise DatasetError(f"item {item['id']} group_id must be a string or integer")


def evaluate(
    items: Sequence[Mapping[str, Any]],
    weights: Mapping[str, float] | None = None,
    bootstrap_rounds: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Evaluate annotation records and return a JSON-serializable report."""
    validate_items(items)
    active_weights = _validate_weights(weights)
    results = [_score_item(item) for item in items]
    _apply_consistency(items, results)

    for result in results:
        overall = 100 * sum(
            result["scores"][dimension] * active_weights[dimension]
            for dimension in active_weights
        )
        result["overall_score"] = round(overall, 2)
        result["grade"] = _grade(overall)
        result["scores"] = {
            dimension: round(value * 100, 2)
            for dimension, value in result["scores"].items()
        }

    overall_scores = [result["overall_score"] for result in results]
    overall = sum(overall_scores) / len(overall_scores)
    dimensions = {
        dimension: round(sum(result["scores"][dimension] for result in results) / len(results), 2)
        for dimension in active_weights
    }
    slices: Dict[str, Dict[str, Any]] = {}
    for task in sorted(SUPPORTED_TASKS):
        task_results = [result for result in results if result["task"] == task]
        if task_results:
            task_score = sum(result["overall_score"] for result in task_results) / len(task_results)
            slices[task] = {
                "count": len(task_results),
                "overall_score": round(task_score, 2),
                "grade": _grade(task_score),
            }

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "item_count": len(results),
            "overall_score": round(overall, 2),
            "grade": _grade(overall),
            "confidence_interval_95": _confidence_interval(overall_scores, bootstrap_rounds, seed),
            "dimensions": dimensions,
        },
        "weights": active_weights,
        "slices": slices,
        "items": results,
    }
