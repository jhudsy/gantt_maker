"""Data models shared across the Gantt application."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


Interval = Tuple[int, int]


@dataclass
class Task:
    """Serializable representation of a single task."""

    name: str
    start: Optional[int] = None
    end: Optional[int] = None
    work_package: bool = False
    row_color: Optional[str] = None
    segments: List[Interval] = field(default_factory=list)
    cell_colors: Dict[int, str] = field(default_factory=dict)
    diamond_markers: Dict[int, Tuple[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.ensure_segments()
        self.normalize_row_color()
        self.normalize_cell_colors()
        self.normalize_diamond_markers()

    def clamp_to_duration(self, duration: int) -> None:
        """Ensure the task stays within the provided duration bounds."""
        if self.segments:
            normalized = self._normalize_segments(self.segments)
            clamped: List[Interval] = []
            for start, end in normalized:
                start = max(1, min(start, duration))
                end = max(1, min(end, duration))
                if start > end:
                    continue
                clamped.append((start, end))
            self.segments = self._normalize_segments(clamped)
        elif self.start is not None and self.end is not None:
            start = max(1, min(self.start, duration))
            end = max(1, min(self.end, duration))
            if start > end:
                start, end = end, start
            self.segments = [(start, end)]
        if self.segments:
            self.start = self.segments[0][0]
            self.end = self.segments[-1][1]
        else:
            if self.start is not None:
                self.start = max(1, min(self.start, duration))
            if self.end is not None:
                self.end = max(1, min(self.end, duration))
        if self.cell_colors:
            self.cell_colors = {
                period: color
                for period, color in self.cell_colors.items()
                if 1 <= period <= duration and color
            }
        if self.row_color:
            self.row_color = self.row_color.strip() or None
        if self.diamond_markers:
            self.diamond_markers = {
                period: marker
                for period, marker in self.diamond_markers.items()
                if 1 <= period <= duration and marker
            }

    def has_schedule(self) -> bool:
        """Return True when the task has at least one interval."""
        return bool(self.segments)

    def is_complex(self) -> bool:
        return len(self.segments) > 1

    def is_empty(self) -> bool:
        """Return True when the task carries no semantic data."""
        return (
            not self.name
            and self.start is None
            and self.end is None
            and not self.segments
            and not self.row_color
            and not self.cell_colors
            and not self.diamond_markers
        )

    def ensure_segments(self) -> List[Interval]:
        if self.segments:
            self.segments = self._normalize_segments(self.segments)
        elif self.start is not None and self.end is not None:
            self.segments = [(self.start, self.end)]
        else:
            self.segments = []
        if self.segments:
            self.start = self.segments[0][0]
            self.end = self.segments[-1][1]
        return list(self.segments)

    def normalize_cell_colors(self) -> Dict[int, str]:
        normalized: Dict[int, str] = {}
        for period, color in self.cell_colors.items():
            try:
                key = int(period)
            except (TypeError, ValueError):
                continue
            value = str(color).strip()
            if key <= 0 or not value:
                continue
            normalized[key] = value
        self.cell_colors = normalized
        return dict(self.cell_colors)

    def normalize_row_color(self) -> Optional[str]:
        if self.row_color is None:
            return None
        text = str(self.row_color).strip()
        self.row_color = text or None
        return self.row_color

    def normalize_diamond_markers(self) -> Dict[int, Tuple[str, str]]:
        normalized: Dict[int, Tuple[str, str]] = {}
        for period, marker in self.diamond_markers.items():
            try:
                key = int(period)
            except (TypeError, ValueError):
                continue
            if key <= 0:
                continue
            if not isinstance(marker, (tuple, list)) or len(marker) != 2:
                continue
            placement = str(marker[0]).strip().lower()
            color = str(marker[1]).strip()
            if placement not in {"cell", "boundary"} or not color:
                continue
            normalized[key] = (placement, color)
        self.diamond_markers = normalized
        return dict(self.diamond_markers)

    @staticmethod
    def _normalize_segments(segments: Sequence[Interval]) -> List[Interval]:
        cleaned: List[Interval] = []
        for start, end in segments:
            if start is None or end is None:
                continue
            if start > end:
                start, end = end, start
            cleaned.append((start, end))
        cleaned.sort()
        merged: List[Interval] = []
        for start, end in cleaned:
            if not merged:
                merged.append((start, end))
                continue
            prev_start, prev_end = merged[-1]
            if start <= prev_end + 1:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))
        return merged
