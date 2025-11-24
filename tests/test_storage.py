from pathlib import Path

from gantt_maker.models import Task
from gantt_maker.storage import load_project, save_project


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    tasks = [
        Task(name="Task A", start=1, end=3, work_package=False),
        Task(name="Task B", start=2, end=5, work_package=True),
    ]

    save_project(path, duration=6, tasks=tasks)
    duration, loaded = load_project(path)

    assert duration == 6
    assert loaded == tasks


def test_save_and_load_with_partial_tasks(tmp_path: Path) -> None:
    path = tmp_path / "partial.csv"
    tasks = [
        Task(name="Draft", start=None, end=None, work_package=False),
        Task(name="Dates TBD", start=2, end=None, work_package=False),
        Task(name="Range", start=3, end=4, work_package=True),
    ]

    save_project(path, duration=10, tasks=tasks)
    duration, loaded = load_project(path)

    assert duration == 10
    assert loaded == tasks


def test_save_project_writes_blank_cells_for_missing_dates(tmp_path: Path) -> None:
    path = tmp_path / "draft.csv"
    tasks = [
        Task(name="Notes"),
        Task(name="Rough start", start=2),
    ]

    save_project(path, duration=4, tasks=tasks)

    text = path.read_text().splitlines()
    assert text[0] == "#duration,4"
    assert text[1] == "name,start,end,work_package"
    assert text[2] == "Notes,,,0"
    assert text[3] == "Rough start,2,,0"
