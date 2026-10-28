"""Terminal possession — change the whole window's look, not just the text.

Windows Terminal, iTerm2, kitty, xterm and friends all honor OSC escape
sequences for background/foreground/cursor color and the window title. We
randomize a haunted palette per session so every `haunt` feels different,
and always restore the original state on exorcise or crash.

Sequences used (all widely supported, degrade silently on terminals that
ignore them):

    OSC 0  ; title        BEL   window title
    OSC 10 ; color        BEL   foreground
    OSC 11 ; color        BEL   background
    OSC 12 ; color        BEL   cursor
    OSC 110              BEL   restore default foreground
    OSC 111              BEL   restore default background
    OSC 112              BEL   restore default cursor

Nothing here is required for the core loop — every call is guarded so a
terminal that ignores OSC just keeps its default colors.
"""

from __future__ import annotations

import random
import sys

# A handful of haunted palettes. Each is (bg, fg, cursor, accent).
# Backgrounds are deep and dark; accents are Halloween-ish (orange, green,
# purple, blood-red). Foregrounds stay readable (off-white / pale).
PALETTES: list[dict[str, str]] = [
    {"name": "crypt", "bg": "#0a0612", "fg": "#d8d0e8", "cursor": "#b45309", "accent": "#7c3aed"},
    {"name": "pumpkin", "bg": "#0f0804", "fg": "#f5e6d3", "cursor": "#ea580c", "accent": "#c2410c"},
    {
        "name": "ectoplasm",
        "bg": "#040f08",
        "fg": "#d3f5e6",
        "cursor": "#22c55e",
        "accent": "#16a34a",
    },
    {
        "name": "bloodmoon",
        "bg": "#0f0404",
        "fg": "#f5d3d3",
        "cursor": "#dc2626",
        "accent": "#991b1b",
    },
    {
        "name": "midnight",
        "bg": "#04060f",
        "fg": "#d3ddf5",
        "cursor": "#3b82f6",
        "accent": "#1e40af",
    },
    {"name": "fog", "bg": "#0a0a0a", "fg": "#e5e5e5", "cursor": "#a3a3a3", "accent": "#525252"},
    {"name": "witch", "bg": "#0c0414", "fg": "#e8d3f5", "cursor": "#a855f7", "accent": "#7e22ce"},
    {
        "name": "graveyard",
        "bg": "#060a06",
        "fg": "#d3e8d3",
        "cursor": "#84cc16",
        "accent": "#4d7c0f",
    },
]

TITLES: list[str] = [
    "🜸 Poltergeist — possessed terminal",
    "👻 The ghost is in the machine",
    "🕯️ Séance in progress",
    "🩸 Final survivor detected",
    "🜸 Your terminal belongs to the ghost now",
    " Dominion of the poltergeist",
]


def _osc(seq: str) -> str:
    """Wrap an OSC sequence in ST (string terminator). BEL works everywhere."""
    return f"\x1b]{seq}\x07"


def _write_raw(text: str) -> None:
    try:
        if sys.stdout.isatty():
            sys.stdout.write(text)
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 — theming is cosmetic, never crash
        pass


def pick_palette(rng: random.Random | None = None) -> dict[str, str]:
    """Choose a haunted palette; rng=None uses the global RNG (varies per session)."""
    rng = rng or random
    return rng.choice(PALETTES)


def possess(
    palette: dict[str, str] | None = None,
    *,
    rng: random.Random | None = None,
    title: str | None = None,
) -> dict[str, str]:
    """Apply a haunted palette + title to the terminal. Returns the palette used."""
    if palette is None:
        palette = pick_palette(rng)
    title = title or (rng or random).choice(TITLES)
    _write_raw(_osc(f"0;{title}"))
    _write_raw(_osc(f"10;{palette['fg']}"))
    _write_raw(_osc(f"11;{palette['bg']}"))
    _write_raw(_osc(f"12;{palette['cursor']}"))
    # Also set the tab color in Windows Terminal (OSC 9;4 with state 3 = indeterminate
    # progress-ish, but state 1 = error-ish red is too aggressive; use state 0 = clear first
    # then state 2 = paused/amber for a "haunted" tab tint).
    _write_raw(_osc("9;2"))
    return palette


def exorcise_terminal() -> None:
    """Restore default terminal colors and title."""
    _write_raw(_osc("0;Terminal"))  # restore title
    _write_raw(_osc("110"))  # restore default foreground
    _write_raw(_osc("111"))  # restore default background
    _write_raw(_osc("112"))  # restore default cursor
    _write_raw(_osc("9;0"))  # clear tab color
    _write_raw("\x1b[?25h\x1b[0m")  # cursor visible, SGR reset


def is_capable() -> bool:
    """Best-effort: can we theme the terminal at all?"""
    if not sys.stdout.isatty():
        return False
    term = (sys.platform == "win32") or bool(__import__("os").environ.get("TERM"))
    return term
