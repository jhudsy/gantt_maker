from PyQt6.QtWidgets import QApplication

from gantt_maker.app import TaskTableWidget
from gantt_maker.models import Task


def _snapshot(tasks):
    return [Task(name=t.name, start=t.start, end=t.end, work_package=t.work_package) for t in tasks]


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
