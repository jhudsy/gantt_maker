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
    assert text[1] == "name,start,end,work_package,intervals"
    assert text[2] == "Notes,,,0,"
    assert text[3] == "Rough start,2,,0,"


def test_save_and_load_complex_task(tmp_path: Path) -> None:
    path = tmp_path / "complex.csv"
    tasks = [
        Task(name="Phased", segments=[(3, 5), (8, 9), (12, 14)]),
    ]

    save_project(path, duration=16, tasks=tasks)
    duration, loaded = load_project(path)

    assert duration == 16
    assert loaded == tasks


def test_load_legacy_csv_without_intervals(tmp_path: Path) -> None:
    path = tmp_path / "legacy.csv"
    path.write_text(
        "\n".join(
            [
                "#duration,5",
                "name,start,end,work_package",
                "Legacy,1,3,0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    duration, tasks = load_project(path)

    assert duration == 5
    assert tasks == [Task(name="Legacy", start=1, end=3, work_package=False)]
