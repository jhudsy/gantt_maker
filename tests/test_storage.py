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
    assert text[1] == "name,start,end,work_package,row_color,intervals,cell_colors,diamond_markers"
    assert text[2] == "Notes,,,0,,,,"
    assert text[3] == "Rough start,2,,0,,,,"


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


def test_save_and_load_with_cell_colors(tmp_path: Path) -> None:
    path = tmp_path / "colors.csv"
    tasks = [
        Task(name="Colored", start=1, end=3, cell_colors={1: "#ff0000", 3: "#00ff00"}),
    ]

    save_project(path, duration=6, tasks=tasks)
    duration, loaded = load_project(path)

    assert duration == 6
    assert loaded == tasks


def test_save_and_load_with_row_color(tmp_path: Path) -> None:
    path = tmp_path / "row_color.csv"
    tasks = [Task(name="Colored", start=1, end=3, row_color="#112233")]

    save_project(path, duration=6, tasks=tasks)
    duration, loaded = load_project(path)

    assert duration == 6
    assert loaded == tasks


def test_load_pre_color_csv_with_intervals(tmp_path: Path) -> None:
    path = tmp_path / "pre_color.csv"
    path.write_text(
        "\n".join(
            [
                "#duration,6",
                "name,start,end,work_package,intervals",
                "Phased,1,5,0,1-2;4-5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    duration, tasks = load_project(path)

    assert duration == 6
    assert tasks == [Task(name="Phased", start=1, end=5, work_package=False, segments=[(1, 2), (4, 5)])]


def test_save_and_load_with_diamonds(tmp_path: Path) -> None:
    path = tmp_path / "diamonds.csv"
    tasks = [
        Task(
            name="Milestones",
            start=1,
            end=4,
            diamond_markers={2: ("cell", "#ff0000"), 4: ("boundary", "#00ff00")},
        ),
    ]

    save_project(path, duration=8, tasks=tasks)
    duration, loaded = load_project(path)

    assert duration == 8
    assert loaded == tasks


def test_load_pre_diamond_header(tmp_path: Path) -> None:
    path = tmp_path / "pre_diamond.csv"
    path.write_text(
        "\n".join(
            [
                "#duration,6",
                "name,start,end,work_package,intervals,cell_colors",
                "Phased,1,5,0,1-2;4-5,1:#ff0000;3:#00ff00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    duration, tasks = load_project(path)

    assert duration == 6
    assert tasks == [
        Task(
            name="Phased",
            start=1,
            end=5,
            work_package=False,
            segments=[(1, 2), (4, 5)],
            cell_colors={1: "#ff0000", 3: "#00ff00"},
        )
    ]
