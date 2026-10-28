"""Theme data + capability detection + degradation rules."""

import io
import os
import sys

from rich.console import Console

from poltergeist.ui.capabilities import Capabilities, detect
from poltergeist.ui.theme import THEMES, get_theme, names


def test_all_themes_complete():
    assert set(names()) == {"classic", "ofrenda", "slasher"}
    for name in names():
        theme = THEMES[name]
        assert theme.glyph_prompt and theme.glyph_prompt_ascii
        assert theme.art and theme.art_ascii  # both unicode + ascii fallbacks
        assert theme.ghost and theme.fail and theme.panel_border
        assert len(theme.sanity_bar) == 2
        assert theme.intro_words


def test_all_theme_colors_parse_in_rich():
    """Regression: a bad color name crashed a live séance once."""
    from rich.style import Style

    for name in names():
        theme = THEMES[name]
        fields = (
            theme.ghost,
            theme.whisper,
            theme.ok,
            theme.fail,
            theme.prompt_dir,
            theme.panel_border,
            *theme.sanity_bar,
        )
        for color in fields:
            Style.parse(f"italic {color}")  # raises if unknown


def test_get_theme_falls_back():
    assert get_theme("nope").name == "classic"
    assert get_theme("OFRENDA").name == "ofrenda"


def _console(**kw):
    return Console(file=io.StringIO(), **kw)


def test_no_color_disables_color():
    console = _console(no_color=True)
    caps = detect(console)
    assert caps.color_depth == 0
    assert caps.animate is False


def test_non_tty_never_animates():
    console = _console(no_color=False)
    console.file = io.StringIO()
    caps = detect(console)
    assert caps.animate is False


def test_ansi_env_no_color(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "environ", {**os.environ, "NO_COLOR": "1"})
    console = Console(file=io.StringIO(), force_terminal=True, color_system="truecolor")
    caps = detect(console)
    assert caps.color_depth == 0


def test_unicode_capability(monkeypatch):
    class Fake:
        encoding = "utf-8"

    monkeypatch.setattr(sys, "stdout", Fake(), raising=False)
    from poltergeist.ui import capabilities as cap

    assert cap._has_unicode() is True
    Fake.encoding = "cp1252"
    if sys.platform != "win32":
        assert cap._has_unicode() is False


def test_caps_defaults():
    caps = Capabilities(tty=False, unicode=False, color_depth=0, term="")
    assert caps.animate is False and caps.width == 80
