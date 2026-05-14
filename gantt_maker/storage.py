"""CSV persistence helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Optional
import csv

from .models import Task


_DURATION_PREFIX = "#duration"
_TASK_HEADER = ["name", "start", "end", "work_package", "intervals", "cell_colors", "diamond_markers"]
_PRE_DIAMOND_TASK_HEADER = ["name", "start", "end", "work_package", "intervals", "cell_colors"]
_PRE_COLOR_TASK_HEADER = ["name", "start", "end", "work_package", "intervals"]
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
                _serialize_cell_colors(task.cell_colors),
                _serialize_diamond_markers(task.diamond_markers),
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
        has_intervals = False
        has_colors = False
        has_diamonds = False
        if header == _TASK_HEADER:
            has_intervals = True
            has_colors = True
            has_diamonds = True
        elif header == _PRE_DIAMOND_TASK_HEADER:
            has_intervals = True
            has_colors = True
        elif header == _PRE_COLOR_TASK_HEADER:
            has_intervals = True
        elif header == _LEGACY_TASK_HEADER:
            has_intervals = False
        else:
            raise ValueError("Invalid gantt CSV: missing task header")

        tasks: List[Task] = []
        for row in reader:
            if len(row) < 4:
                continue
            name, start_raw, end_raw, work_package = row[:4]
            segments_raw = row[4] if has_intervals and len(row) > 4 else ""
            colors_raw = row[5] if has_colors and len(row) > 5 else ""
            diamonds_raw = row[6] if has_diamonds and len(row) > 6 else ""
            start = _parse_optional_int(start_raw)
            end = _parse_optional_int(end_raw)
            if not name and start is None and end is None:
                continue
            segments = _deserialize_segments(segments_raw)
            cell_colors = _deserialize_cell_colors(colors_raw)
            diamond_markers = _deserialize_diamond_markers(diamonds_raw)
            task = Task(
                name=name,
                start=start,
                end=end,
                work_package=bool(int(work_package)),
                segments=segments,
                cell_colors=cell_colors,
                diamond_markers=diamond_markers,
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


def _serialize_cell_colors(cell_colors: dict[int, str]) -> str:
    parts: List[str] = []
    for period in sorted(cell_colors):
        color = str(cell_colors[period]).strip()
        if not color:
            continue
        parts.append(f"{period}:{color}")
    return ";".join(parts)


def _deserialize_cell_colors(value: str) -> dict[int, str]:
    text = value.strip()
    if not text:
        return {}
    colors: dict[int, str] = {}
    for chunk in text.split(";"):
        if ":" not in chunk:
            continue
        period_raw, color_raw = chunk.split(":", 1)
        try:
            period = int(period_raw)
        except ValueError:
            continue
        color = color_raw.strip()
        if period <= 0 or not color:
            continue
        colors[period] = color
    return colors


def _serialize_diamond_markers(diamond_markers: dict[int, tuple[str, str]]) -> str:
    parts: List[str] = []
    for period in sorted(diamond_markers):
        marker = diamond_markers[period]
        if not isinstance(marker, tuple) or len(marker) != 2:
            continue
        placement = str(marker[0]).strip().lower()
        color = str(marker[1]).strip()
        if placement not in {"cell", "boundary"} or not color:
            continue
        parts.append(f"{period}|{placement}|{color}")
    return ";".join(parts)


def _deserialize_diamond_markers(value: str) -> dict[int, tuple[str, str]]:
    text = value.strip()
    if not text:
        return {}
    markers: dict[int, tuple[str, str]] = {}
    for chunk in text.split(";"):
        parts = chunk.split("|", 2)
        if len(parts) != 3:
            continue
        period_raw, placement_raw, color_raw = parts
        try:
            period = int(period_raw)
        except ValueError:
            continue
        placement = placement_raw.strip().lower()
        color = color_raw.strip()
        if period <= 0 or placement not in {"cell", "boundary"} or not color:
            continue
        markers[period] = (placement, color)
    return markers
