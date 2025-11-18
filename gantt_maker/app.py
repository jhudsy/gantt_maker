"""Main PyQt application entry point."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QItemSelectionModel
from PyQt6.QtGui import QAction, QColor, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QHeaderView,
)

from .exporters import export_as_csv, export_as_pdf
from .models import Task
from .storage import load_project, save_project


TASK_HEADERS = ["Task", "Start", "End"]
_DEFAULT_DURATION = 20
_UNDO_STACK_LIMIT = 20
_DRAG_HANDLE_TOLERANCE = 6


@dataclass(slots=True)
class DragState:
    row: int
    edge: str  # "start" or "end"


class SummaryRowWidget(QTableWidget):
    """Displays task density across the duration."""

    def __init__(self, duration: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(1, 0, parent)
        self.timeline_start_col = len(TASK_HEADERS)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setMaximumHeight(48)
        self.set_duration(duration)

    def set_duration(self, duration: int) -> None:
        self.setColumnCount(self.timeline_start_col + duration)
        self._init_cells()

    def _init_cells(self) -> None:
        self.blockSignals(True)
        for col in range(self.columnCount()):
            item = self.item(0, col)
            if item is None:
                item = QTableWidgetItem()
                self.setItem(0, col, item)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if col < self.timeline_start_col:
                item.setText("Summary" if col == 0 else "")
            else:
                item.setText("0")
        self.blockSignals(False)

    def update_counts(self, counts: List[int]) -> None:
        for offset, value in enumerate(counts):
            col = self.timeline_start_col + offset
            if col >= self.columnCount():
                break
            item = self.item(0, col)
            if item is None:
                item = QTableWidgetItem()
                self.setItem(0, col, item)
            item.setText(str(value))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


class TaskTableWidget(QTableWidget):
    """Task grid with embedded timeline visualization.

    The widget keeps a trailing blank row as a buffer for new entries and
    emits `tasks_updated` any time the underlying Task list changes.
    """

    tasks_updated = pyqtSignal(list)
    undo_available = pyqtSignal(bool)
    column_widths_updated = pyqtSignal()

    def __init__(self, duration: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(0, 0, parent)
        self.duration = duration
        self.timeline_start_col = len(TASK_HEADERS)
        self.blank_row_index = 0
        self._drag_state: Optional[DragState] = None
        self._block_cell = False
        self._undo_stack: List[List[Task]] = []
        self._suppress_selection_sync = False
        self._setup_table()
        self.set_duration(duration)
        self._append_blank_row()
        self._emit_undo_available()

    def _setup_table(self) -> None:
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.cellChanged.connect(self._handle_cell_changed)
        self.verticalHeader().setVisible(False)
        self.setMouseTracking(True)
        self.itemSelectionChanged.connect(self._limit_selection_to_text_columns)

    def _make_cell(self, *, selectable: bool = False) -> QTableWidgetItem:
        """Create a cell with the proper flags for timeline vs text columns."""
        item = QTableWidgetItem("")
        if selectable:
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        return item

    def set_duration(self, duration: int) -> None:
        self.duration = max(1, duration)
        column_labels = TASK_HEADERS + [str(i + 1) for i in range(self.duration)]
        self.setColumnCount(len(column_labels))
        self.setHorizontalHeaderLabels(column_labels)
        self._configure_column_widths()
        self._recolor_all_rows()
        self.tasks_updated.emit(self.get_tasks())

    def _configure_column_widths(self) -> None:
        header = self.horizontalHeader()
        fm = self.fontMetrics()
        name_width = max(fm.horizontalAdvance("M" * 30), 240)
        numeric_width = max(fm.horizontalAdvance("00") + 12, 32)
        viz_width = max(fm.horizontalAdvance("00") + 8, 26)

        target_widths = {
            0: name_width,
            1: numeric_width,
            2: numeric_width,
        }

        for col in range(self.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            width = target_widths.get(col, viz_width if col >= self.timeline_start_col else numeric_width)
            self.setColumnWidth(col, width)
        self.column_widths_updated.emit()

    # --- Row lifecycle helpers -------------------------------------------------

    def _append_blank_row(self) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self.blank_row_index = row
        for col in range(self.columnCount()):
            item = self._make_cell(selectable=col >= self.timeline_start_col)
            self.setItem(row, col, item)

    def _ensure_blank_row(self) -> None:
        """Keep a blank row at the bottom so users can type new tasks inline."""
        if not self._row_has_data(self.blank_row_index):
            return
        self._append_blank_row()

    def _row_has_data(self, row: int) -> bool:
        if row < 0 or row >= self.rowCount():
            return False
        for col in range(self.timeline_start_col):
            item = self.item(row, col)
            if item and item.text().strip():
                return True
        return False

    def _show_context_menu(self, position: QPoint) -> None:
        """Provide quick row actions (insert/toggle/delete/undo)."""
        index = self.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        if row == self.blank_row_index:
            return
        menu = QMenu(self)
        insert_action = menu.addAction("Insert row")
        toggle_action = menu.addAction("Toggle work package")
        delete_action = menu.addAction("Delete row")
        menu.addSeparator()
        undo_action = menu.addAction("Undo delete")
        undo_action.setEnabled(bool(self._undo_stack))
        action = menu.exec(self.viewport().mapToGlobal(position))
        if action == insert_action:
            self._insert_row_after(row)
        elif action == toggle_action:
            self._toggle_work_package(row)
        elif action == delete_action:
            self._delete_row(row)
        elif action == undo_action:
            self.undo_last_change()

    def _insert_row_after(self, row: int) -> None:
        insert_at = min(self.blank_row_index, row + 1)
        self.insertRow(insert_at)
        for col in range(self.columnCount()):
            item = self._make_cell(selectable=col >= self.timeline_start_col)
            self.setItem(insert_at, col, item)
        if insert_at <= self.blank_row_index:
            self.blank_row_index += 1
        self.selectRow(insert_at)

    def _toggle_work_package(self, row: int) -> None:
        item = self.item(row, 0)
        if item is None:
            item = QTableWidgetItem("")
            self.setItem(row, 0, item)
        flag = bool(item.data(Qt.ItemDataRole.UserRole))
        item.setData(Qt.ItemDataRole.UserRole, not flag)
        self._recolor_row(row)
        self.tasks_updated.emit(self.get_tasks())

    def _delete_row(self, row: int) -> None:
        if row == self.blank_row_index:
            return
        self._push_undo_state()
        self.removeRow(row)
        if self.rowCount() == 0 or self._row_has_data(self.rowCount() - 1):
            self._append_blank_row()
        else:
            self.blank_row_index = self.rowCount() - 1
        self._recolor_all_rows()
        self.tasks_updated.emit(self.get_tasks())

    def _handle_cell_changed(self, row: int, column: int) -> None:
        if self._block_cell:
            return
        if row == self.blank_row_index and not self._row_has_data(row):
            return
        if column >= self.timeline_start_col:
            return
        if column in (1, 2):
            self._normalize_dates(row)
        draw_bars = self._row_has_complete_dates(row)
        self._recolor_row(row, draw_bars=draw_bars)
        self._ensure_blank_row()
        self.tasks_updated.emit(self.get_tasks())

    def _normalize_dates(self, row: int) -> None:
        """Clamp start/end inputs to the project duration and keep start <= end."""
        has_start = self._cell_has_value(row, 1)
        has_end = self._cell_has_value(row, 2)
        if not has_start and not has_end:
            return
        if has_start:
            start = self._clamp_value(self._read_int(row, 1))
            self._write_int(row, 1, start)
        if has_end:
            end = self._clamp_value(self._read_int(row, 2))
            self._write_int(row, 2, end)
        if not (has_start and has_end):
            return
        start = self._read_int(row, 1)
        end = self._read_int(row, 2)
        if start > end:
            start, end = end, start
        self._write_int(row, 1, start)
        self._write_int(row, 2, end)

    def _clamp_value(self, value: int) -> int:
        if value <= 0:
            value = 1
        return max(1, min(value, self.duration))

    def _cell_has_value(self, row: int, col: int) -> bool:
        item = self.item(row, col)
        return bool(item and item.text().strip())

    def _read_int(self, row: int, col: int) -> int:
        item = self.item(row, col)
        if not item:
            return 0
        try:
            return int(item.text())
        except ValueError:
            return 0

    def _write_int(self, row: int, col: int, value: int) -> None:
        item = self.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            self.setItem(row, col, item)
        text_value = str(value)
        if item.text() == text_value:
            return
        self._block_cell = True
        item.setText(text_value)
        self._block_cell = False

    def _recolor_all_rows(self) -> None:
        for row in range(self.rowCount()):
            self._recolor_row(row)

    def _recolor_row(self, row: int, *, draw_bars: bool = True) -> None:
        """Refresh the miniature bar visualization for a single row."""
        for col in range(self.timeline_start_col, self.columnCount()):
            item = self.item(row, col)
            if item is None:
                item = self._make_cell(selectable=True)
                self.setItem(row, col, item)
            item.setBackground(QColor("white"))
        if row == self.blank_row_index or not draw_bars:
            return
        start = self._read_int(row, 1)
        end = self._read_int(row, 2)
        if not start or not end:
            return
        color = QColor("#1976d2")
        if self._is_work_package(row):
            color = QColor("#8d6e63")
        for period in range(start, end + 1):
            col = self.timeline_start_col + period - 1
            if 0 <= col < self.columnCount():
                item = self.item(row, col)
                if item is None:
                    item = self._make_cell(selectable=True)
                    self.setItem(row, col, item)
                item.setBackground(color)

    def _row_has_complete_dates(self, row: int) -> bool:
        return self._cell_has_value(row, 1) and self._cell_has_value(row, 2)

    def _is_work_package(self, row: int) -> bool:
        item = self.item(row, 0)
        return bool(item and item.data(Qt.ItemDataRole.UserRole))

    def get_tasks(self) -> List[Task]:
        tasks: List[Task] = []
        for row in range(self.rowCount()):
            if row == self.blank_row_index:
                continue
            name_item = self.item(row, 0)
            start = self._read_int(row, 1)
            end = self._read_int(row, 2)
            if not name_item or not name_item.text().strip():
                continue
            if not start or not end:
                continue
            task = Task(
                name=name_item.text().strip(),
                start=start,
                end=end,
                work_package=self._is_work_package(row),
            )
            tasks.append(task)
        return tasks

    def set_tasks(self, tasks: List[Task]) -> None:
        self._block_cell = True
        self.setRowCount(0)
        for task in tasks:
            task.clamp_to_duration(self.duration)
            row = self.rowCount()
            self.insertRow(row)
            for col in range(self.columnCount()):
                item = self._make_cell(selectable=col >= self.timeline_start_col)
                self.setItem(row, col, item)
            self.item(row, 0).setText(task.name)
            self.item(row, 1).setText(str(task.start))
            self.item(row, 2).setText(str(task.end))
            self.item(row, 0).setData(Qt.ItemDataRole.UserRole, task.work_package)
        self._append_blank_row()
        self._block_cell = False
        self._recolor_all_rows()
        self.tasks_updated.emit(self.get_tasks())

    def reset_undo_stack(self) -> None:
        """Drop all undo history (used after opening a new project)."""
        self._undo_stack.clear()
        self._emit_undo_available()

    def undo_last_change(self) -> bool:
        if not self._undo_stack:
            return False
        snapshot = self._undo_stack.pop()
        self.set_tasks(snapshot)
        self._emit_undo_available()
        return True

    def _snapshot_tasks(self) -> List[Task]:
        """Capture a deep copy of the current tasks for undo purposes."""
        return [
            Task(name=task.name, start=task.start, end=task.end, work_package=task.work_package)
            for task in self.get_tasks()
        ]

    def _push_undo_state(self) -> None:
        """Persist the latest snapshot and trim the fixed-size undo buffer."""
        snapshot = self._snapshot_tasks()
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > _UNDO_STACK_LIMIT:
            self._undo_stack.pop(0)
        self._emit_undo_available()

    def _emit_undo_available(self) -> None:
        """Notify any listeners (menu items) that undo availability changed."""
        self.undo_available.emit(bool(self._undo_stack))

    # Drag handling -----------------------------------------------------
    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            row = self.rowAt(int(event.position().y()))
            col = self.columnAt(int(event.position().x()))
            if row != self.blank_row_index and col >= self.timeline_start_col:
                period = col - self.timeline_start_col + 1
                start = self._read_int(row, 1)
                end = self._read_int(row, 2)
                if start and end:
                    # Detect drags even if users grab near, but not exactly on, the edge.
                    pointer_x = int(event.position().x())
                    start_edge = self._period_left_edge(start)
                    end_edge = self._period_right_edge(end)
                    if abs(pointer_x - start_edge) <= _DRAG_HANDLE_TOLERANCE:
                        self._drag_state = DragState(row=row, edge="start")
                    elif abs(pointer_x - end_edge) <= _DRAG_HANDLE_TOLERANCE:
                        self._drag_state = DragState(row=row, edge="end")
                    elif period == start:
                        self._drag_state = DragState(row=row, edge="start")
                    elif period == end:
                        self._drag_state = DragState(row=row, edge="end")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._drag_state:
            col = self.columnAt(int(event.position().x()))
            if col >= self.timeline_start_col:
                period = col - self.timeline_start_col + 1
                period = max(1, min(period, self.duration))
                if self._drag_state.edge == "start":
                    end = self._read_int(self._drag_state.row, 2)
                    if period <= end:
                        self._write_int(self._drag_state.row, 1, period)
                else:
                    start = self._read_int(self._drag_state.row, 1)
                    if period >= start:
                        self._write_int(self._drag_state.row, 2, period)
                self._recolor_row(self._drag_state.row)
                self.tasks_updated.emit(self.get_tasks())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_state = None
        super().mouseReleaseEvent(event)

    def _period_left_edge(self, period: int) -> int:
        """Translate a period index into pixel coordinates for drag math."""
        col = self.timeline_start_col + period - 1
        if col < 0 or col >= self.columnCount():
            return 0
        position = self.columnViewportPosition(col)
        return max(0, position)

    def _period_right_edge(self, period: int) -> int:
        """Same as `_period_left_edge`, but returns the right-hand boundary."""
        col = self.timeline_start_col + period - 1
        if col < 0 or col >= self.columnCount():
            return 0
        position = self.columnViewportPosition(col)
        width = self.columnWidth(col)
        return max(0, position + width)

    def _limit_selection_to_text_columns(self) -> None:
        """Prevent the timeline portion from highlighting so bars stay visible."""
        if self._suppress_selection_sync:
            return
        selection_model = self.selectionModel()
        if selection_model is None:
            return
        indexes = selection_model.selectedIndexes()
        if not indexes:
            return
        self._suppress_selection_sync = True
        for index in indexes:
            if index.column() >= self.timeline_start_col:
                selection_model.select(index, QItemSelectionModel.SelectionFlag.Deselect)
        self._suppress_selection_sync = False


class MainWindow(QMainWindow):
    """Primary window with menus and central widgets."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gantt Maker")
        self.current_path: Optional[Path] = None
        self.table = TaskTableWidget(_DEFAULT_DURATION)
        self.summary = SummaryRowWidget(_DEFAULT_DURATION)
        self.undo_action: QAction | None = None
        # Wire up the table so the summary row and menu items stay in sync.
        self.table.tasks_updated.connect(self._update_summary)
        self.table.undo_available.connect(self._handle_undo_available)
        self.table.column_widths_updated.connect(self._mirror_all_column_widths)
        self._update_summary(self.table.get_tasks())
        self._build_layout()
        self._build_menu()
        self._resize_initial()

    def _build_layout(self) -> None:
        """Stack the editable table and the summary density row."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.table)
        layout.addWidget(self.summary)
        self.setCentralWidget(container)

    def _build_menu(self) -> None:
        """Create File/Edit menus along with shortcuts."""
        menu = self.menuBar()
        file_menu = menu.addMenu("File")

        new_action = QAction("New", self)
        new_action.triggered.connect(self.action_new)
        file_menu.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.action_open)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.action_save)
        file_menu.addAction(save_action)

        export_action = QAction("Export", self)
        export_action.triggered.connect(self.action_export)
        file_menu.addAction(export_action)

        change_duration_action = QAction("Change Duration...", self)
        change_duration_action.triggered.connect(self.action_change_duration)
        file_menu.addAction(change_duration_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = menu.addMenu("Edit")
        undo_action = QAction("Undo delete", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setEnabled(False)
        undo_action.triggered.connect(self._handle_undo_request)
        edit_menu.addAction(undo_action)
        self.undo_action = undo_action

    def _resize_initial(self) -> None:
        """Start with a generous window size so the timeline fits on screen."""
        width = self.table.horizontalHeader().length() + self.table.verticalHeader().width() + 100
        height = max(600, self.table.viewport().sizeHint().height() + 200)
        self.resize(int(max(width, 1000)), int(height))

    def _update_summary(self, tasks: List[Task]) -> None:
        """Recalculate how many tasks overlap each period and mirror widths."""
        counts = [0] * self.table.duration
        for task in tasks:
            start = max(1, min(task.start, self.table.duration))
            end = max(1, min(task.end, self.table.duration))
            for idx in range(start - 1, end):
                counts[idx] += 1
        self.summary.set_duration(self.table.duration)
        self._mirror_all_column_widths()
        self.summary.update_counts(counts)

    # Menu actions ------------------------------------------------------
    def action_new(self) -> None:
        """Reset the table to a clean slate with a new duration."""
        duration, ok = QInputDialog.getInt(
            self,
            "Project duration",
            "Number of periods",
            value=self.table.duration,
            min=1,
            max=365,
        )
        if not ok:
            return
        self.table.setRowCount(0)
        self.table.set_duration(duration)
        self.table.set_tasks([])
        self.table.reset_undo_stack()
        self.current_path = None
        self.statusBar().showMessage("Started new project", 3000)

    def action_open(self) -> None:
        """Load a saved CSV project file into the table."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open project",
            filter="CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            duration, tasks = load_project(path)
        except Exception as exc:  # pragma: no cover - interactive guard
            QMessageBox.critical(self, "Open failed", str(exc))
            return
        self.table.set_duration(duration)
        self.table.set_tasks(tasks)
        self.table.reset_undo_stack()
        self.current_path = Path(path)
        self.statusBar().showMessage(f"Loaded project from {path}", 3000)

    def action_save(self) -> None:
        """Persist the minimal CSV format used for reopening projects."""
        if not self.current_path:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save project",
                filter="CSV Files (*.csv)",
                initialFilter="CSV Files (*.csv)",
            )
            if not path:
                return
            self.current_path = Path(path)
        tasks = self.table.get_tasks()
        save_project(self.current_path, self.table.duration, tasks)
        self.statusBar().showMessage(f"Saved to {self.current_path}", 3000)

    def action_export(self) -> None:
        """Export the richer CSV/PDF formats used for sharing."""
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export project",
            filter="CSV Files (*.csv);;PDF Files (*.pdf)",
        )
        if not path:
            return
        tasks = self.table.get_tasks()
        if path.lower().endswith(".pdf") or "PDF" in selected_filter:
            include_dates = (
                QMessageBox.question(
                    self,
                    "PDF Columns",
                    "Include Start/End columns in the PDF export?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                == QMessageBox.StandardButton.Yes
            )
            export_as_pdf(path, self.table.duration, tasks, include_dates=include_dates)
            self.statusBar().showMessage(f"Exported PDF to {path}", 3000)
        else:
            export_as_csv(path, self.table.duration, tasks)
            self.statusBar().showMessage(f"Exported CSV to {path}", 3000)

    def action_change_duration(self) -> None:
        """Prompt for a new duration and clamp existing tasks."""
        duration, ok = QInputDialog.getInt(
            self,
            "Change duration",
            "Number of periods",
            value=self.table.duration,
            min=1,
            max=365,
        )
        if not ok or duration == self.table.duration:
            return
        tasks = self.table.get_tasks()
        self.table.set_duration(duration)
        self.table.set_tasks(tasks)
        self.table.reset_undo_stack()
        self.statusBar().showMessage(f"Duration set to {duration}", 3000)

    def _handle_undo_available(self, available: bool) -> None:
        """Enable/disable the Edit → Undo delete action based on history."""
        if self.undo_action is not None:
            self.undo_action.setEnabled(available)

    def _handle_undo_request(self) -> None:
        """Trigger a restore of the most recent deletion."""
        if self.table.undo_last_change():
            self.statusBar().showMessage("Restored last deleted row", 3000)

    def _mirror_all_column_widths(self) -> None:
        """Keep the summary row perfectly aligned with the main table."""
        if self.summary.columnCount() != self.table.columnCount():
            self.summary.set_duration(self.table.duration)
        columns = min(self.summary.columnCount(), self.table.columnCount())
        for col in range(columns):
            self.summary.setColumnWidth(col, self.table.columnWidth(col))

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - requires UI
        """Ask for confirmation before closing the application."""
        if QMessageBox.question(self, "Quit", "Close Gantt Maker?") == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def run() -> None:
    """Entry point used by `python -m gantt_maker`."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
