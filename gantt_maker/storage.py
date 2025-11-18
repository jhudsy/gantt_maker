"""CSV persistence helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple
import csv

from .models import Task


_DURATION_PREFIX = "#duration"
_TASK_HEADER = ["name", "start", "end", "work_package"]


def save_project(path: Path | str, duration: int, tasks: Iterable[Task]) -> None:
    """Persist the project to CSV."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([_DURATION_PREFIX, duration])
        writer.writerow(_TASK_HEADER)
        for task in tasks:
            writer.writerow([task.name, task.start, task.end, int(task.work_package)])


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
        if header != _TASK_HEADER:
            raise ValueError("Invalid gantt CSV: missing task header")

        tasks: List[Task] = []
        for row in reader:
            if len(row) < 4:
                continue
            name, start, end, work_package = row[:4]
            if not name and not start and not end:
                continue
            task = Task(name=name, start=int(start), end=int(end), work_package=bool(int(work_package)))
            tasks.append(task)

        return duration, tasks
