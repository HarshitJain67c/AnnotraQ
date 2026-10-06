from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from annotraq.core import DatasetError


def load_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise DatasetError(f"cannot read {source}: {error}") from error

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise DatasetError(f"{source}:{line_number}: invalid JSON: {error.msg}") from error
        if not isinstance(record, dict):
            raise DatasetError(f"{source}:{line_number}: each line must contain a JSON object")
        records.append(record)
    return records


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
