"""Terminal possession tests (no real TTY required)."""

import io

from rich.console import Console

from poltergeist.ui.terminal import (
    PALETTES,
    TITLES,
    exorcise_terminal,
    is_capable,
    pick_palette,
    possess,
)


def test_pick_palette_returns_known_palette():
    p = pick_palette()
    assert p in PALETTES
    assert set(p.keys()) >= {"name", "bg", "fg", "cursor", "accent"}


def test_pick_palette_deterministic_with_rng():
    import random

    rng = random.Random(42)
    p1 = pick_palette(rng)
    rng2 = random.Random(42)
    p2 = pick_palette(rng2)
    assert p1 == p2


def test_palettes_have_valid_hex():
    for p in PALETTES:
        for key in ("bg", "fg", "cursor", "accent"):
            assert p[key].startswith("#") and len(p[key]) == 7


def test_possess_writes_osc_to_tty(monkeypatch):
    # Force isatty True
    sink = io.StringIO()
    console = Console(file=sink, force_terminal=True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout", sink, raising=False)
    # monkeypatch sys.stdout.write/flush
    buf = []

    class FakeStdout:
        def isatty(self):
            return True

        def write(self, s):
            buf.append(s)
            return len(s)

        def flush(self):
            pass

    monkeypatch.setattr("sys.stdout", FakeStdout())
    p = possess(rng=__import__("random").Random(1))
    assert p in PALETTES
    joined = "".join(buf)
    assert "\x1b]11;" in joined  # background set
    assert "\x1b]10;" in joined  # foreground set
    assert "\x1b]12;" in joined  # cursor set
    assert "\x1b]0;" in joined  # title set


def test_exorcise_restores():
    buf = []

    class FakeStdout:
        def isatty(self):
            return True

        def write(self, s):
            buf.append(s)
            return len(s)

        def flush(self):
            pass

    import unittest.mock as m

    m.patch("sys.stdout", FakeStdout()).start()
    exorcise_terminal()
    joined = "".join(buf)
    assert "\x1b]110" in joined
    assert "\x1b]111" in joined
    assert "\x1b]112" in joined
    assert "\x1b]9;0" in joined


def test_possess_noop_when_not_tty(monkeypatch):
    class FakeStdout:
        def isatty(self):
            return False

        def write(self, s):
            raise AssertionError("should not write when not a tty")

        def flush(self):
            pass

    monkeypatch.setattr("sys.stdout", FakeStdout())
    # Should not raise
    possess()


def test_is_capable_non_tty(monkeypatch):
    class FakeStdout:
        def isatty(self):
            return False

    monkeypatch.setattr("sys.stdout", FakeStdout())
    assert is_capable() is False