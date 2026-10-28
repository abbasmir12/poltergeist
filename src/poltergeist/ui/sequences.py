"""Transformation + exorcism sequences. Skippable, never crashy, always
restoring the terminal. Under ~4 seconds; any key skips (or --no-intro).
"""

from __future__ import annotations

import random
import sys
import time

from rich.console import Console

from .theme import Theme

TOTAL_BUDGET = 4.0  # seconds


def any_key_poll(timeout: float, wait: float = 0.05) -> bool:
    """True when a key arrives within `timeout` seconds (cross-platform)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _key_ready():
            return True
        time.sleep(wait)
    return False


def _key_ready() -> bool:
    if sys.platform == "win32":
        import msvcrt

        return bool(msvcrt.kbhit())
    import select

    fd = sys.stdin.fileno()
    try:
        ready, _, _ = select.select([fd], [], [], 0)
    except (OSError, ValueError):
        return False
    return bool(ready)


class Sequencer:
    """Step clock so a sequence never exceeds its time budget."""

    def __init__(
        self, console: Console, budget: float = TOTAL_BUDGET, *, seed: object = None
    ) -> None:
        self.console = console
        self.budget = budget
        self.start = time.monotonic()
        self.rng = random.Random(seed)

    @property
    def time_left(self) -> float:
        return self.budget - (time.monotonic() - self.start)

    def nap(self, seconds: float) -> None:
        time.sleep(max(0.0, min(seconds, max(self.time_left, 0.0))))

    def skipped(self) -> bool:
        return self.time_left <= 0


def intro(console: Console, theme: Theme, *, caps, seed: object = None, on_step=None) -> bool:
    """Cinematic transformation. Returns True if completed (not skipped)."""
    if not caps.animate:
        console.print(
            f"[{theme.whisper}]🜸 you run haunt; the darkness runs a checksum[/{theme.whisper}]"
        )
        return True
    seq = Sequencer(console, seed=seed)
    # 1. lights flicker off — a few fast/dim blankings
    for _ in ("reverse", "grey27", "grey19", "grey15"):
        console.print("[on black]" + " " * min(caps.width, 80), end="\r", highlight=False)
        seq.nap(0.12)
        if seq.skipped() or any_key_poll(0.01):
            break
    # 2. static glitch lines
    glitch_rows = ("░▒▓̸▒░alive░▒▓", " ▂▃▅ ghost ░ ▓ ", "~⌁~ syscall ~⌁~")
    for row in glitch_rows:
        console.print(row, style=theme.whisper, markup=False, highlight=False)
        seq.nap(0.15)
        if any_key_poll(0.01):
            break
    # 3. ghost art materializes line by line (markup off: art contains brackets)
    art = theme.art if caps.unicode else theme.art_ascii
    console.print()
    for line in art:
        console.print(f"  {line}", style=theme.ghost, markup=False, highlight=False)
        seq.nap(0.18)
        if any_key_poll(0.01):
            break
    # 4. first words
    words = list(theme.intro_words) or ["The dwelling is claimed."]
    for line in words:
        console.print()
        console.print(f"[italic {theme.ghost}]🜸 {line}[/italic {theme.ghost}]")
        seq.nap(0.35)
        if any_key_poll(0.01):
            break
    console.print("[dim](press any key to skip the séance in future runs: --no-intro)[/dim]")
    time.sleep(0.4 if not seq.skipped() else 0.05)
    return True


def outro(console: Console, theme: Theme, *, caps, seed: object = None) -> None:
    """Dramatic goodbye + full terminal restoration."""
    if not caps.animate:
        console.print(
            f"[{theme.ghost}]🜸 the haunting concludes. your terminal returns.[/{theme.ghost}]"
        )
        _restore()
        return
    try:
        lines = [
            f"[{theme.ghost}]exorcism rites applied…[/{theme.ghost}]",
            f"[{theme.whisper}]chains lower. glyphs stop crawling. the fan forgets."
            f"[/{theme.whisper}]",
            f"[bold {theme.ghost}]👻 the ghost withdraws — mostly.[/bold {theme.ghost}]",
        ]
        for text in lines:
            console.print(text)
            time.sleep(0.25)
        time.sleep(0.2)
    except KeyboardInterrupt:  # banner interrupted mid-scene: keep restoring
        pass
    finally:
        _restore()


def _restore() -> None:
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\x1b[?25h\x1b[0m\x1b[2J")  # cursor visible, SGR reset, clear
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 — restoration must never fail loudly
        pass
