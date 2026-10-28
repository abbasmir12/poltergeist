"""Haunted palettes + art. Themes: classic (default), ofrenda, slasher."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    glyph_prompt: str  # unicode prompt glyph
    glyph_prompt_ascii: str  # ASCII fallback glyph
    ghost: str  # ghost speech color (rich color name)
    whisper: str  # ambient/whisper color
    ok: str  # successful command framing
    fail: str  # failing command framing
    prompt_dir: str
    panel_border: str
    sanity_bar: tuple[str, str] = ("medium_purple", "grey37")
    intro_words: tuple[str, ...] = ()
    art: tuple[str, ...] = ()  # materialize lines (unicode)
    art_ascii: tuple[str, str, ...] = ()  # ASCII fallback art art


THEMES: dict[str, Theme] = {}


def _t(name: str, **kwargs) -> Theme:
    theme = Theme(name=name, **kwargs)
    THEMES[name] = theme
    return theme


_t(
    "classic",
    glyph_prompt="👻",
    glyph_prompt_ascii="[]",
    ghost="medium_purple",
    whisper="grey58",
    ok="pale_green3",
    fail="indian_red",
    prompt_dir="cornflower_blue",
    panel_border="medium_purple",
    intro_words=(
        "Lights out. The lamp exchanges its current for something older.",
        "A static hum. The cursor's blink drifts a half-second off-beat.",
    ),
    art=(
        " .--.   ",
        "/  .. \\ ",
        "|  .-. |",
        "\\  --- /",
        " '--'--'",
    ),
    art_ascii=(
        ".----.",
        "| O  |",
        "| ^  |",
        "'----'",
    ),
)

_t(
    "ofrenda",
    glyph_prompt="🕯️",
    glyph_prompt_ascii="o*",
    ghost="blanched_almond",
    whisper="wheat1",
    ok="banana",
    fail="orange_red1",
    prompt_dir="dark_orange3",
    panel_border="dark_orange",
    sanity_bar=("selago_light", "tan_dark"),
    intro_words=(
        "Marigold petals gather along the scrollbar. Candlelight distorts…",
        "A warm breeze. The dead of your shell exhale memories, gently.",
    ),
    art=(
        "  \u2232\u2232\u2232  ",
        " ( \u2022\u2080\u2022 )",
        "   \u2318   ",
    ),
    art_ascii=(
        "~~~",
        "(o)",
        " | ",
    ),
)

_t(
    "slasher",
    glyph_prompt="🩸",
    glyph_prompt_ascii="><",
    ghost="crimson",
    whisper="grey62",
    ok="spring_green3",
    fail="red",
    prompt_dir="dark_red",
    panel_border="red3",
    sanity_bar=("salmon_red", "black_noise_dk"),
    intro_words=(
        "The terminal goes still. Somewhere, a synth strings a low note.",
        "You survived last week's sprint. This did not go unnoticed.",
    ),
    art=(
        " /!!!!!\\ ",
        "[x  x  x]",
        " \\ \\_/ / ",
    ),
    art_ascii=(
        "/////",
        "[x x]",
        "____",
    ),
)


def get_theme(name: str) -> Theme:
    return THEMES.get(name.lower(), THEMES["classic"])


def names() -> list[str]:
    return list(THEMES.keys())
