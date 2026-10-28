"""Terminal capability detection — every spook degrades gracefully.

Rules: no animations when not a TTY or in CI; no color when NO_COLOR; ASCII
only when Unicode is unavailable. Windows Terminal/PowerShell 5+ handle
ANSI/Truecolor via rich; we never hand-roll VT sequences beyond safe resets.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    tty: bool
    unicode: bool
    color_depth: int  # 0 = none, 8 = 256, 24 = truecolor
    term: str

    @property
    def animate(self) -> bool:
        return self.tty and self.color_depth > 0 and not os.environ.get("POLTERGEIST_NO_ANIM")

    @property
    def color(self) -> bool:
        return self.color_depth > 0

    @property
    def width(self) -> int:
        try:
            return int(os.get_terminal_size().columns)
        except (OSError, ValueError):
            return 80


def _has_unicode() -> bool:
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in enc:
        return True
    # Windows Terminal renders UTF-8 through rich regardless of cp encoding.
    return sys.platform == "win32"


def detect(console) -> Capabilities:
    """Probe a rich Console plus the environment."""
    tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
    if console.no_color or os.environ.get("NO_COLOR"):
        depth = 0
    else:
        depth = {"truecolor": 24, "256": 8, "16": 4}.get(str(console.color_system or ""), 0)
    if not tty:
        depth = 0
    return Capabilities(
        tty=tty,
        unicode=_has_unicode(),
        color_depth=depth,
        term=os.environ.get("TERM", ""),
    )
