from pathlib import Path
import csv

from PyQt6.QtCore import QRect

from gantt_maker.exporters import (
    export_as_csv,
    export_as_pdf,
    _compute_text_columns,
    _compute_timeline_layout,
)
from gantt_maker.models import Task


def test_export_csv_handles_partial_tasks(tmp_path: Path) -> None:
    path = tmp_path / "export.csv"
    tasks = [
        Task(name="Draft"),
        Task(name="Start only", start=2),
        Task(name="Active", start=1, end=3, work_package=False),
        Task(name="Package", start=2, end=4, work_package=True),
        Task(name="Complex", segments=[(1, 1), (3, 4)]),
    ]

    export_as_csv(path, duration=4, tasks=tasks)

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == ["Task", "Start", "End", "1", "2", "3", "4"]

    assert rows[1][:3] == ["Draft", "", ""]
    assert rows[1][3:] == ["", "", "", ""]

    assert rows[2][:3] == ["Start only", "2", ""]
    assert rows[2][3:] == ["", "", "", ""]

    assert rows[3][:3] == ["Active", "1", "3"]
    assert rows[3][3:] == ["X", "X", "X", ""]

    assert rows[4][:3] == ["Package", "2", "4"]
    assert rows[4][3:] == ["", "W", "W", "W"]

    assert rows[5][:3] == ["Complex", "1", "4"]
    assert rows[5][3:] == ["X", "", "X", "X"]


def test_export_pdf_renders_long_labels(tmp_path: Path, qapp) -> None:
    path = tmp_path / "export.pdf"
    long_name = (
        "A very long task label that should wrap across several lines because the "
        "column is not wide enough to fit it on a single line."
    )
    tasks = [
        Task(name="Short", start=1, end=2),
        Task(name=long_name, start=1, end=4),
    ]

    export_as_pdf(path, duration=4, tasks=tasks)

    assert path.exists()
    assert path.stat().st_size > 0


def test_export_pdf_renders_styling(tmp_path: Path, qapp) -> None:
    """Row colors, per-cell overrides, and diamonds should all draw without error."""
    path = tmp_path / "styled.pdf"
    tasks = [
        Task(name="Row color", start=1, end=4, row_color="#43a047"),
        Task(
            name="Overrides + diamonds",
            start=2,
            end=6,
            cell_colors={3: "#e53935", 5: "#1e88e5"},
            diamond_markers={
                2: ("cell", "#fbc02d"),
                4: ("boundary-right", "#000000"),
                6: ("boundary-left", "#8e24aa"),
            },
        ),
    ]

    export_as_pdf(path, duration=8, tasks=tasks)

    assert path.exists()
    assert path.stat().st_size > 0


def test_pdf_task_width_ratio_is_honored(qapp) -> None:
    """The Task column should match the UI ratio rather than auto-sizing."""

    class _FM:
        def horizontalAdvance(self, _text: str) -> int:
            return 1000  # would auto-size to a wide column

    content = QRect(0, 0, 3000, 1000)
    tasks = [Task(name="Some task", start=1, end=4)]
    duration = 8

    columns = _compute_text_columns(_FM(), content, tasks, True, duration, task_width_ratio=4.0)
    name_width = columns[0][1]
    col_width, _ = _compute_timeline_layout(content, columns, duration)

    assert abs(name_width / col_width - 4.0) < 0.05

    # A narrower ratio yields a narrower Task column.
    narrow = _compute_text_columns(_FM(), content, tasks, True, duration, task_width_ratio=2.0)
    assert narrow[0][1] < name_width
