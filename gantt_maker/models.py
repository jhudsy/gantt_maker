"""Data models shared across the Gantt application."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    """Serializable representation of a single task."""

    name: str
    start: int
    end: int
    work_package: bool = False

    def clamp_to_duration(self, duration: int) -> None:
        """Ensure the task stays within the provided duration bounds."""
        self.start = max(1, min(self.start, duration))
        self.end = max(1, min(self.end, duration))
        if self.start > self.end:
            self.start, self.end = self.end, self.start

    def is_empty(self) -> bool:
        """Return True when the task carries no semantic data."""
        return not self.name and self.start == 0 and self.end == 0
