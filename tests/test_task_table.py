from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from gantt_maker.app import TaskTableWidget, MainWindow
from gantt_maker.models import Task


def _snapshot(tasks):
    return [
        Task(
            name=t.name,
            start=t.start,
            end=t.end,
            work_package=t.work_package,
            segments=list(t.segments),
            cell_colors=dict(t.cell_colors),
            diamond_markers=dict(t.diamond_markers),
        )
        for t in tasks
    ]


def _summary_counts(window: MainWindow) -> list[int]:
    counts: list[int] = []
    start_col = window.summary.timeline_start_col
    for offset in range(window.table.duration):
        item = window.summary.item(0, start_col + offset)
        assert item is not None
        counts.append(int(item.text()))
    return counts


def test_change_duration_preserves_partial_rows(qapp: QApplication) -> None:
    table = TaskTableWidget(5)
    table.set_tasks(
        [
            Task(name="Idea"),
            Task(name="Needs end", start=2),
            Task(name="Scoped", start=2, end=4, work_package=True),
        ]
    )

    baseline = _snapshot(table.get_tasks())

    tasks_before = table.get_tasks()
    table.set_duration(12)
    table.set_tasks(tasks_before)

    assert table.duration == 12
    assert table.get_tasks() == baseline


def test_split_task_creates_complex_segments(qapp: QApplication) -> None:
    table = TaskTableWidget(10)
    table.set_tasks([Task(name="Phase", start=1, end=6)])

    table._split_task_at_period(0, 3)

    segments = table._get_row_segments(0)
    assert segments == [(1, 2), (4, 6)]
    start_item = table.item(0, 1)
    end_item = table.item(0, 2)
    assert start_item is not None
    assert end_item is not None
    assert start_item.text() == "1"
    assert end_item.text() == "6"
    assert not (start_item.flags() & Qt.ItemFlag.ItemIsEditable)
    assert not (end_item.flags() & Qt.ItemFlag.ItemIsEditable)

    tasks = table.get_tasks()
    assert tasks[0].segments == segments


def test_complex_intervals_merge_back_to_simple(qapp: QApplication) -> None:
    table = TaskTableWidget(10)
    table.set_tasks([Task(name="Phase", start=1, end=6)])
    table._set_row_segments(0, [(1, 2), (4, 6)])

    assert table._is_complex_row(0)

    table._set_row_segments(0, [(1, 6)])

    segments = table._get_row_segments(0)
    assert segments == [(1, 6)]
    start_item = table.item(0, 1)
    assert start_item is not None
    assert start_item.flags() & Qt.ItemFlag.ItemIsEditable


def test_summary_ignores_work_packages(qapp: QApplication) -> None:
    window = MainWindow()
    try:
        window.table.set_duration(6)
        window.table.set_tasks(
            [
                Task(name="Feature", segments=[(1, 4)]),
                Task(name="WP", segments=[(1, 6)], work_package=True),
            ]
        )

        window._update_summary(window.table.get_tasks())

        counts = _summary_counts(window)
        assert counts[:4] == [1, 1, 1, 1]
        assert counts[4:] == [0, 0]
    finally:
        window.close()


def test_summary_scroll_tracks_table(qapp: QApplication) -> None:
    window = MainWindow()
    try:
        window.table.set_duration(40)
        window.resize(400, 300)
        table_bar = window.table.horizontalScrollBar()
        summary_bar = window.summary.horizontalScrollBar()
        assert table_bar is not None
        assert summary_bar is not None

        table_bar.setValue(table_bar.maximum() // 2)
        qapp.processEvents()
        assert summary_bar.value() == table_bar.value()

        summary_bar.setValue(summary_bar.maximum())
        qapp.processEvents()
        assert table_bar.value() == summary_bar.value()
    finally:
        window.close()


def test_cell_and_row_color_overrides_roundtrip(qapp: QApplication) -> None:
    table = TaskTableWidget(6)
    table.set_tasks([Task(name="Color", start=2, end=4)])

    table._set_cell_color(0, 2, "#ff0000")
    table._set_row_color(0, "#00ff00")
    table._set_cell_color(0, 5, "#0000ff")

    tasks = table.get_tasks()
    assert tasks[0].cell_colors[2] == "#00ff00"
    assert tasks[0].cell_colors[4] == "#00ff00"
    assert tasks[0].cell_colors[5] == "#0000ff"

    table.set_tasks(tasks)
    reloaded = table.get_tasks()
    assert reloaded[0].cell_colors == tasks[0].cell_colors


def test_diamond_marker_roundtrip_and_rendering(qapp: QApplication) -> None:
    table = TaskTableWidget(6)
    table.set_tasks([Task(name="Milestone", start=2, end=5)])

    table._set_diamond_marker(0, 3, "cell", "#ff0000")
    table._set_diamond_marker(0, 4, "boundary", "#00ff00")

    tasks = table.get_tasks()
    assert tasks[0].diamond_markers[3] == ("cell", "#ff0000")
    assert tasks[0].diamond_markers[4] == ("boundary", "#00ff00")

    cell_item = table.item(0, table.timeline_start_col + 2)
    boundary_item = table.item(0, table.timeline_start_col + 3)
    assert cell_item is not None
    assert boundary_item is not None
    assert cell_item.text() == "◆"
    assert boundary_item.text() == "◆"
    assert boundary_item.textAlignment() & Qt.AlignmentFlag.AlignRight

    table._remove_diamond_marker(0, 3)
    tasks_after_remove = table.get_tasks()
    assert 3 not in tasks_after_remove[0].diamond_markers

    table.set_tasks(tasks)
    reloaded = table.get_tasks()
    assert reloaded[0].diamond_markers == tasks[0].diamond_markers
