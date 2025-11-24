"""Data models shared across the Gantt application."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


Interval = Tuple[int, int]


@dataclass
class Task:
    """Serializable representation of a single task."""

    name: str
    start: Optional[int] = None
    end: Optional[int] = None
    work_package: bool = False
    segments: List[Interval] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.ensure_segments()

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

    def has_schedule(self) -> bool:
        """Return True when the task has at least one interval."""
        return bool(self.segments)

    def is_complex(self) -> bool:
        return len(self.segments) > 1

    def is_empty(self) -> bool:
        """Return True when the task carries no semantic data."""
        return not self.name and self.start is None and self.end is None and not self.segments

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
