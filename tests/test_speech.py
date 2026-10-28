"""Degradation tests: glitch corruption and the typewriter."""

import io
import random

from rich.console import Console

from poltergeist.ui.speech import corrupt, glitch_word, typewriter


def _str_console(color=None):
    sink = io.StringIO()
    return Console(file=sink, color_system=color, force_terminal=False), sink


def test_glitch_off_when_no_unicode():
    rng = random.Random(1)
    assert glitch_word("ghost", 2, rng, unicode=False) == "ghost"


def test_glitch_level_zero():
    rng = random.Random(1)
    assert glitch_word("ghost", 0, rng) == "ghost"


def test_glitch_adds_marks_at_high_level():
    rng = random.Random(3)
    out = glitch_word("phantomthing", 2, rng, unicode=True)
    assert out != "phantomthing"  # deterministic seed hits some letters
    assert sum("̸̧́̈̂".count(c) for c in out) >= 2


def test_url_never_glitched():
    rng = random.Random(0)
    assert glitch_word("https://example.com/ghosts", 2, rng) == "https://example.com/ghosts"


def test_corrupt_level_zero_identity():
    rng = random.Random(1)
    text = "the build failed again"
    assert corrupt(text, level=0, sanity=0, rng=rng) == text


def test_corrupt_high_sanity_rarely_changes_text():
    rng = random.Random(11)
    text = "one two three four five six seven eight"
    out = corrupt(text, level=2, sanity=100, rng=rng)
    words = out.split(" ")
    # at sanity 100 the base change chance is low; some corruption still possible
    assert len(words) == len(text.split(" "))


def test_typewriter_typed_output():
    console, sink = _str_console()
    typewriter(console, "spook", style="red", lang=0.0)
    assert sink.getvalue() == "spook\n"


def test_typewriter_empty_text():
    console, sink = _str_console()
    typewriter(console, "", style="red")
    assert sink.getvalue() == ""


def test_corrupt_ascii_terminal_never_changes_text():
    rng = random.Random(2)
    text = "alpha beta gamma"
    assert corrupt(text, level=2, sanity=0, rng=rng, unicode=False) == text
