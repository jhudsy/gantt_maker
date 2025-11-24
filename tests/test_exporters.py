from pathlib import Path
import csv

from gantt_maker.exporters import export_as_csv
from gantt_maker.models import Task


def test_export_csv_handles_partial_tasks(tmp_path: Path) -> None:
    path = tmp_path / "export.csv"
    tasks = [
        Task(name="Draft"),
        Task(name="Start only", start=2),
        Task(name="Active", start=1, end=3, work_package=False),
        Task(name="Package", start=2, end=4, work_package=True),
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
