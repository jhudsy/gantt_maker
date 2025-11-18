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
