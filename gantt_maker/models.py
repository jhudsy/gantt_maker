"""Data models shared across the Gantt application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    """Serializable representation of a single task."""

    name: str
    start: Optional[int] = None
    end: Optional[int] = None
    work_package: bool = False

    def clamp_to_duration(self, duration: int) -> None:
        """Ensure the task stays within the provided duration bounds."""
        if self.start is not None:
            self.start = max(1, min(self.start, duration))
        if self.end is not None:
            self.end = max(1, min(self.end, duration))
        if self.start is not None and self.end is not None and self.start > self.end:
            self.start, self.end = self.end, self.start

    def has_schedule(self) -> bool:
        """Return True when both start and end values are defined."""
        return self.start is not None and self.end is not None

    def is_empty(self) -> bool:
        """Return True when the task carries no semantic data."""
        return not self.name and self.start is None and self.end is None
