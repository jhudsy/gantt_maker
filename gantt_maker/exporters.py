"""Export helpers for CSV and PDF."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Optional

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPen, QPdfWriter

from .models import Task

CSV_HEADERS = ["Task", "Start", "End"]
CSV_ACTIVE_MARKER = "X"
CSV_WORK_MARKER = "W"

PDF_TASK_MIN_WIDTH = 160
PDF_TASK_MAX_WIDTH_RATIO = 0.45  # fraction of available width
PDF_TASK_PADDING = 48
PDF_START_END_WIDTH = 100
PDF_TIMELINE_MIN_COL_WIDTH = 12
PDF_PAGE_MARGIN_RATIO = 0.04
PDF_HEADER_HEIGHT = 40
PDF_ROW_HEIGHT_MIN = 24
PDF_ROW_HEIGHT_MAX = 48
PDF_FONT_SIZE = 10
PDF_ROW_TEXT_BOTTOM_PADDING = 4
PDF_HEADER_TEXT_BOTTOM_PADDING = 2
PDF_TASK_COLOR = QColor("#1976d2")
PDF_WORK_COLOR = QColor("#8d6e63")
PDF_DIAMOND_SYMBOL = "◆"


def export_as_csv(path: Path | str, duration: int, tasks: Iterable[Task]) -> None:
    """Export a rich CSV with visualization columns."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    header = CSV_HEADERS + [str(period) for period in range(1, duration + 1)]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for task in tasks:
            row = [task.name, _format_optional_int(task.start), _format_optional_int(task.end)]
            markers = []
            for period in range(1, duration + 1):
                if _task_active_during(task, period):
                    markers.append(CSV_WORK_MARKER if task.work_package else CSV_ACTIVE_MARKER)
                else:
                    markers.append("")
            writer.writerow(row + markers)


def export_as_pdf(
    path: Path | str,
    duration: int,
    tasks: Iterable[Task],
    *,
    include_dates: bool = True,
    task_width_ratio: Optional[float] = None,
) -> None:
    """Render a formatted view of the Gantt table to PDF.

    ``task_width_ratio`` (Task column width / one period column width, as seen
    in the UI) lets the export reproduce the on-screen Task column width. When
    omitted, the column is auto-sized to the longest label.
    """
    pdf_path = Path(path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(pdf_path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    writer.setResolution(300)

    task_list = list(tasks)
    painter = QPainter(writer)
    _draw_pdf_table(painter, writer, duration, task_list, include_dates, task_width_ratio)
    painter.end()


def _compute_text_columns(
    font_metrics,
    content_rect,
    tasks: List[Task],
    include_dates: bool,
    duration: int,
    task_width_ratio: Optional[float] = None,
) -> List[tuple[str, int]]:
    """Figure out how wide the Task/Start/End columns should be for PDF."""
    other_width = 2 * PDF_START_END_WIDTH if include_dates else 0
    if task_width_ratio and task_width_ratio > 0:
        # Honor the UI Task-column width: solve name_width / col_width == ratio,
        # where col_width = (content - name_width - other) / duration.
        duration = max(1, duration)
        usable = max(1, content_rect.width() - other_width)
        name_width = int(task_width_ratio * usable / (duration + task_width_ratio))
        name_width = max(PDF_TIMELINE_MIN_COL_WIDTH, min(name_width, usable - PDF_TIMELINE_MIN_COL_WIDTH * duration))
        name_width = max(PDF_TIMELINE_MIN_COL_WIDTH, name_width)
    else:
        longest_task = max((font_metrics.horizontalAdvance(task.name) for task in tasks), default=0)
        proportional_cap = int(content_rect.width() * PDF_TASK_MAX_WIDTH_RATIO)
        desired_width = longest_task + PDF_TASK_PADDING
        name_width = max(PDF_TASK_MIN_WIDTH, min(desired_width, proportional_cap))
    columns = [("Task", name_width)]
    if include_dates:
        columns.extend([("Start", PDF_START_END_WIDTH), ("End", PDF_START_END_WIDTH)])
    return columns


def _compute_timeline_layout(content_rect, text_columns, duration: int):
    """Decide where the timeline columns begin and how wide each period is."""
    text_total_width = sum(width for _, width in text_columns)
    remaining = max(1, content_rect.width() - text_total_width)
    duration = max(1, duration)
    avg_col_width = remaining / duration
    if avg_col_width < PDF_TIMELINE_MIN_COL_WIDTH:
        col_width = PDF_TIMELINE_MIN_COL_WIDTH
        timeline_total_width = col_width * duration
        timeline_start_x = max(content_rect.left() + text_total_width, content_rect.right() - timeline_total_width)
    else:
        col_width = avg_col_width
        timeline_total_width = remaining
        timeline_start_x = content_rect.left() + text_total_width
    return col_width, timeline_start_x


def _compute_row_height(content_rect, duration: int, tasks: List[Task]):
    """Compute a bounded row height so all tasks fit on the page."""
    header_height = PDF_HEADER_HEIGHT
    rows = max(1, len(tasks))
    available_height = max(PDF_ROW_HEIGHT_MIN, content_rect.height() - header_height)
    row_height = max(PDF_ROW_HEIGHT_MIN, min(PDF_ROW_HEIGHT_MAX, int(available_height / rows)))
    return row_height


def _compute_per_row_heights(
    painter: QPainter,
    tasks: List[Task],
    name_width: float,
    base_row_height: int,
) -> List[int]:
    """Return a per-row height that grows to fit wrapped task names."""
    heights: List[int] = []
    padding = 6
    available = max(1, int(name_width) - 2 * padding)
    flags = (
        int(Qt.AlignmentFlag.AlignLeft)
        | int(Qt.AlignmentFlag.AlignTop)
        | int(Qt.TextFlag.TextWordWrap)
    )
    measuring_rect = QRectF(0.0, 0.0, float(available), 100000.0)
    for task in tasks:
        text = task.name or ""
        if not text:
            heights.append(base_row_height)
            continue
        bounding = painter.boundingRect(measuring_rect, flags, text)
        natural = int(bounding.height()) + 2 * PDF_ROW_TEXT_BOTTOM_PADDING
        heights.append(max(base_row_height, natural))
    return heights


def _draw_pdf_table(
    painter: QPainter,
    writer: QPdfWriter,
    duration: int,
    tasks: List[Task],
    include_dates: bool,
    task_width_ratio: Optional[float] = None,
) -> None:
    page_rect = writer.pageLayout().paintRectPixels(writer.resolution())
    margin = int(page_rect.width() * PDF_PAGE_MARGIN_RATIO)
    content_rect = page_rect.adjusted(margin, margin, -margin, -margin)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    font = QFont(painter.font())
    font.setPointSize(PDF_FONT_SIZE)
    painter.setFont(font)
    pen = QPen(QColor("#333333"))
    pen.setWidth(1)
    painter.setPen(pen)
    font_metrics = painter.fontMetrics()

    text_columns = _compute_text_columns(
        font_metrics, content_rect, tasks, include_dates, duration, task_width_ratio
    )
    col_width, timeline_start_x = _compute_timeline_layout(content_rect, text_columns, duration)
    base_row_height = _compute_row_height(content_rect, duration, tasks)
    name_width = text_columns[0][1]
    row_heights = _compute_per_row_heights(painter, tasks, name_width, base_row_height)
    header_height = PDF_HEADER_HEIGHT

    header_y = content_rect.top()
    column_positions: List[float] = []
    cursor_x = content_rect.left()
    for _, width in text_columns:
        column_positions.append(cursor_x)
        cursor_x += width

    # Draw text column headers
    for (title, width), x in zip(text_columns, column_positions):
        rect = QRectF(x, header_y, width, header_height)
        painter.fillRect(rect, QColor("#eceff1"))
        painter.drawRect(rect)
        header_text_rect = rect.adjusted(0, 0, 0, -PDF_HEADER_TEXT_BOTTOM_PADDING)
        painter.drawText(header_text_rect, Qt.AlignmentFlag.AlignCenter, title)

    # Timeline headers
    for period in range(duration):
        rect = QRectF(timeline_start_x + period * col_width, header_y, col_width, header_height)
        painter.fillRect(rect, QColor("#e8eaf6"))
        painter.drawRect(rect)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(period + 1))

    # Draw task rows
    current_y = header_y + header_height
    for task, row_height in zip(tasks, row_heights):
        values = [task.name]
        if include_dates:
            values.extend([
                _format_optional_int(task.start),
                _format_optional_int(task.end),
            ])
        for ( _title, width), x, value in zip(text_columns, column_positions, values):
            rect = QRectF(x, current_y, width, row_height)
            painter.drawRect(rect)
            is_name_column = x == column_positions[0]
            padding = 6 if is_name_column else 0
            text_rect = rect.adjusted(padding, 0, -padding, -PDF_ROW_TEXT_BOTTOM_PADDING)
            if is_name_column:
                alignment = (
                    int(Qt.AlignmentFlag.AlignLeft)
                    | int(Qt.AlignmentFlag.AlignVCenter)
                    | int(Qt.TextFlag.TextWordWrap)
                )
            else:
                alignment = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
            painter.drawText(text_rect, alignment, value)

        default_fill = PDF_WORK_COLOR if task.work_package else PDF_TASK_COLOR
        active_fill = QColor(task.row_color) if task.row_color else default_fill
        if not active_fill.isValid():
            active_fill = default_fill
        for period in range(duration):
            rect = QRectF(timeline_start_x + period * col_width, current_y, col_width, row_height)
            painter.drawRect(rect)
            timeline_period = period + 1
            # Background: active periods use the row/default bar color; an explicit
            # per-cell override wins over both (mirrors the on-screen grid).
            fill = active_fill if _task_active_during(task, timeline_period) else None
            override = task.cell_colors.get(timeline_period)
            if override:
                override_color = QColor(override)
                if override_color.isValid():
                    fill = override_color
            if fill is not None:
                painter.fillRect(rect.adjusted(1, 1, -1, -1), fill)
            marker = task.diamond_markers.get(timeline_period)
            if marker:
                _draw_diamond(painter, rect, marker)
        current_y += row_height

    if not tasks:
        rect = QRectF(content_rect.left(), current_y, content_rect.width(), base_row_height)
        painter.drawRect(rect)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No tasks defined")


def _draw_diamond(painter: QPainter, rect: QRectF, marker) -> None:
    """Render a diamond glyph inside a timeline cell, matching the UI placement."""
    if not isinstance(marker, (tuple, list)) or len(marker) != 2:
        return
    placement, color = marker
    marker_color = QColor(color)
    if not marker_color.isValid():
        marker_color = QColor("black")
    if placement == "boundary-left":
        alignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
    elif placement == "boundary-right":
        alignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
    else:
        alignment = Qt.AlignmentFlag.AlignCenter
    painter.save()
    painter.setPen(QPen(marker_color))
    painter.drawText(rect, alignment, PDF_DIAMOND_SYMBOL)
    painter.restore()


def _format_optional_int(value: Optional[int]) -> str:
    return "" if value is None else str(value)


def _task_active_during(task: Task, period: int) -> bool:
    for start, end in task.segments:
        if start <= period <= end:
            return True
    return False
