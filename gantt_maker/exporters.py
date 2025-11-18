"""Export helpers for CSV and PDF."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

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


def export_as_csv(path: Path | str, duration: int, tasks: Iterable[Task]) -> None:
    """Export a rich CSV with visualization columns."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    header = CSV_HEADERS + [str(period) for period in range(1, duration + 1)]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for task in tasks:
            row = [task.name, task.start, task.end]
            markers = []
            for period in range(1, duration + 1):
                if task.start <= period <= task.end:
                    markers.append(CSV_WORK_MARKER if task.work_package else CSV_ACTIVE_MARKER)
                else:
                    markers.append("")
            writer.writerow(row + markers)


def export_as_pdf(path: Path | str, duration: int, tasks: Iterable[Task], *, include_dates: bool = True) -> None:
    """Render a formatted view of the Gantt table to PDF."""
    pdf_path = Path(path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(pdf_path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    writer.setResolution(300)

    task_list = list(tasks)
    painter = QPainter(writer)
    _draw_pdf_table(painter, writer, duration, task_list, include_dates)
    painter.end()


def _compute_text_columns(font_metrics, content_rect, tasks: List[Task], include_dates: bool) -> List[tuple[str, int]]:
    """Figure out how wide the Task/Start/End columns should be for PDF."""
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


def _draw_pdf_table(
    painter: QPainter,
    writer: QPdfWriter,
    duration: int,
    tasks: List[Task],
    include_dates: bool,
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

    text_columns = _compute_text_columns(font_metrics, content_rect, tasks, include_dates)
    col_width, timeline_start_x = _compute_timeline_layout(content_rect, text_columns, duration)
    row_height = _compute_row_height(content_rect, duration, tasks)
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
    for task in tasks:
        values = [task.name]
        if include_dates:
            values.extend([str(task.start), str(task.end)])
        for ( _title, width), x, value in zip(text_columns, column_positions, values):
            rect = QRectF(x, current_y, width, row_height)
            painter.drawRect(rect)
            alignment = Qt.AlignmentFlag.AlignVCenter | (
                Qt.AlignmentFlag.AlignLeft if x == column_positions[0] else Qt.AlignmentFlag.AlignCenter
            )
            padding = 6 if x == column_positions[0] else 0
            text_rect = rect.adjusted(padding, 0, -padding, -PDF_ROW_TEXT_BOTTOM_PADDING)
            painter.drawText(text_rect, alignment, value)

        fill_color = PDF_WORK_COLOR if task.work_package else PDF_TASK_COLOR
        for period in range(duration):
            rect = QRectF(timeline_start_x + period * col_width, current_y, col_width, row_height)
            painter.drawRect(rect)
            timeline_period = period + 1
            if task.start <= timeline_period <= task.end:
                painter.fillRect(rect.adjusted(1, 1, -1, -1), fill_color)
        current_y += row_height

    if not tasks:
        rect = QRectF(content_rect.left(), current_y, content_rect.width(), row_height)
        painter.drawRect(rect)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No tasks defined")
