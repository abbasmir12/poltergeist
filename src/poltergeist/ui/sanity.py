"""Sanity meter — failures and idle time erode it; success restores it."""

from __future__ import annotations

MAX = 100
MIN = 0

# where the spookiness ramps
BRACKETS = (
    (75, "steady"),  # > 75
    (50, "uneasy"),  # > 50
    (25, "haunted"),  # > 25
    (8, "crumbling"),  # > 8
    (-1, "meltdown"),  # <= 8… then 0
)


class Sanity:
    """Plain state machine;Pretty rendering lives repl-side (phase 5 scene)."""

    def __init__(self, value: int = MAX, *, drain_per_minute: float = 2.0) -> None:
        self.value = min(MAX, max(MIN, int(value)))
        self.drain_per_minute = drain_per_minute
        self._recent_failures: list[int] = []

    @property
    def level(self) -> str:
        for cutoff, name in BRACKETS:
            if self.value > cutoff:
                return name
        return "meltdown"

    @property
    def at_meltdown(self) -> bool:
        return self.value <= 0

    def on_command(self, *, exit_code: int, duration_ms: int = 0) -> str:
        """Update on a command; returns the new level label."""
        import time as _t

        if exit_code == 0:
            self.value = min(MAX, self.value + 3)
            self._recent_failures.clear()
        else:
            self.value = max(MIN, self.value - 7)
            now = int(_t.time())
            self._recent_failures.append(now)
            self._recent_failures = [t for t in self._recent_failures if now - t < 300]
        return self.level

    def repeated_failures(self, window: int = 300) -> int:
        import time as _t

        now = int(_t.time())
        self._recent_failures = [t for t in self._recent_failures if now - t < window]
        return len(self._recent_failures)

    def drain(self, idle_seconds: float) -> None:
        """Long idle nights gnaw at the meter, gently."""
        self.value = max(MIN, int(self.value - self.drain_per_minute * idle_seconds / 60.0))

    def restore(self, amount: int) -> int:
        self.value = min(MAX, self.value + amount)
        return self.value

    def bar(self) -> str:
        """ASCII-safe mini bar: [████░░ 62%] (phase 2 adds color/glyphs)."""
        width = 10
        filled = round(self.value / MAX * width)
        return f"[{'█' * filled}{'░' * (width - filled)} {self.value:>3}%]"
