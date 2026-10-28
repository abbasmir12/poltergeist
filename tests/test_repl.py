"""HauntedRepl unit tests (no Ollama, no TTY required)."""

import io

from rich.console import Console

from poltergeist.config import Config
from poltergeist.ghost.provider import GhostProvider
from poltergeist.repl import HauntedRepl
from poltergeist.shell.posix import PosixShell


class FakeProvider(GhostProvider):
    name = "fake"

    def is_available(self) -> bool:
        return False

    def resolve_model(self) -> str | None:
        return None

    def chat_stream(self, messages):  # pragma: no cover - not reached offline
        yield ""


def make_repl(**kwargs) -> HauntedRepl:
    console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
    return HauntedRepl(
        Config(),
        PosixShell(),
        console=console,
        provider=FakeProvider(),
        **kwargs,
    )


def test_prompt_has_no_rich_markup():
    """Regression: prompt_toolkit printed raw '[italic dim ...]' tags on
    Windows because it does not parse rich markup — it needs ANSI codes."""
    repl = make_repl()
    text = str(repl._prompt_text())
    assert "[italic" not in text
    assert "›" in text
    assert "~" in text  # home is abbreviated


def test_prompt_ansi_formatted_text():
    repl = make_repl()
    prompt = repl._prompt_text()
    # .value parses the ANSI into (style, text) fragments; the raw string must
    # carry real SGR codes and never rich markup.
    raw = prompt.value
    assert "\x1b[" in raw
    assert "[italic" not in raw and "cornflower_blue" not in raw


def test_sgr_codes():
    sgr = HauntedRepl._sgr("cornflower_blue", dim=True, italic=True)
    assert sgr.startswith("\x1b[")
    assert "38;2;" in sgr and "2;" in sgr and "3;" in sgr
    assert HauntedRepl._sgr("not-a-color-xyz", dim=True) == "\x1b[2m"
    assert HauntedRepl._sgr(None) == ""


def test_plain_prompt_has_no_ansi():
    repl = make_repl()
    plain = repl._make_plain_prompt()
    assert "\x1b" not in plain
    assert "›" in plain
