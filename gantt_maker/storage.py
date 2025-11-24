"""CSV persistence helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Optional
import csv

from .models import Task


_DURATION_PREFIX = "#duration"
_TASK_HEADER = ["name", "start", "end", "work_package", "intervals"]
_LEGACY_TASK_HEADER = ["name", "start", "end", "work_package"]


def save_project(path: Path | str, duration: int, tasks: Iterable[Task]) -> None:
    """Persist the project to CSV."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([_DURATION_PREFIX, duration])
        writer.writerow(_TASK_HEADER)
        for task in tasks:
            writer.writerow([
                task.name,
                _serialize_optional_int(task.start),
                _serialize_optional_int(task.end),
                int(task.work_package),
                _serialize_segments(task.segments),
            ])


def load_project(path: Path | str) -> Tuple[int, List[Task]]:
    """Load a project from CSV."""
    csv_path = Path(path)
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        duration_line = next(reader, None)
        if not duration_line or duration_line[0] != _DURATION_PREFIX:
            raise ValueError("Invalid gantt CSV: missing duration line")
        duration = int(duration_line[1])

        header = next(reader, None)
        has_intervals = True
        if header == _LEGACY_TASK_HEADER:
            has_intervals = False
        elif header != _TASK_HEADER:
            raise ValueError("Invalid gantt CSV: missing task header")

        tasks: List[Task] = []
        for row in reader:
            if len(row) < 4:
                continue
            name, start_raw, end_raw, work_package = row[:4]
            segments_raw = row[4] if has_intervals and len(row) > 4 else ""
            start = _parse_optional_int(start_raw)
            end = _parse_optional_int(end_raw)
            if not name and start is None and end is None:
                continue
            segments = _deserialize_segments(segments_raw)
            task = Task(
                name=name,
                start=start,
                end=end,
                work_package=bool(int(work_package)),
                segments=segments,
            )
            tasks.append(task)

        return duration, tasks


def _serialize_optional_int(value: Optional[int]) -> str:
    return "" if value is None else str(value)


def _parse_optional_int(value: str) -> Optional[int]:
    text = value.strip() if value is not None else ""
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _serialize_segments(segments: Iterable[tuple[int, int]]) -> str:
    parts = [f"{start}-{end}" for start, end in segments]
    return ";".join(parts)


def _deserialize_segments(value: str) -> List[tuple[int, int]]:
    text = value.strip()
    if not text:
        return []
    intervals: List[tuple[int, int]] = []
    for chunk in text.split(";"):
        if "-" not in chunk:
            continue
        start_str, end_str = chunk.split("-", 1)
        try:
            start = int(start_str)
            end = int(end_str)
        except ValueError:
            continue
        if start > end:
            start, end = end, start
        intervals.append((start, end))
    return Task._normalize_segments(intervals)
