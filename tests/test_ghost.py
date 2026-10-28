"""Ghost facade + fallback behavior (offline-safe by construction)."""

from poltergeist.ghost import Ghost
from poltergeist.ghost.fallbacks import pick
from poltergeist.ghost.ollama import OllamaProvider
from poltergeist.ghost.provider import GhostProvider


class FakeProvider(GhostProvider):
    name = "fake"

    def __init__(self, available=True, text="Hello, warm blood.") -> None:
        self.available = available
        self.text = text
        self.calls = 0

    def is_available(self) -> bool:
        return self.available

    def resolve_model(self) -> str | None:
        return "fake:test" if self.available else None

    def chat_stream(self, messages):
        self.calls += 1
        assert any(m.role == "system" for m in messages), "persona must be present"
        yield self.text


def test_ghost_awake_reacts_with_model():
    provider = FakeProvider()
    ghost = Ghost(provider)
    out = "".join(ghost.react("ls", exit_code=0, stdout="", stderr=""))
    assert "Hello, warm blood." in out
    assert provider.calls == 1


def test_ghost_falls_back_when_unavailable():
    provider = FakeProvider(available=False)
    ghost = Ghost(provider)
    out = "".join(ghost.react("ls", exit_code=1, stdout="", stderr="boom"))
    assert out  # canned fallback, not empty
    assert provider.calls == 0


def test_theme_propagates():
    ghost = Ghost(FakeProvider(), theme="ofrenda")
    assert ghost._persona(None).count("Día de los Muertos") >= 1
    ghost.theme = "slasher"
    assert "horror host" in ghost._persona(None)


def test_sanity_angst_in_persona():
    ghost = Ghost(FakeProvider())
    assert "25/100" in ghost._persona(25)


def test_whisper_never_empty_across_events_and_themes():
    for event in ("greet", "idle", "night", "cycle_detect", "exorcise", "sanity_zero"):
        for theme in ("classic", "ofrenda", "slasher"):
            assert pick(event, theme, seed=1)


def test_chat_offline_line_mentions_model_fix():
    line = pick("chat_offline", "classic", seed=0)
    assert "gemma4:e4b" in line or "ollama" in line.lower()


def test_react_fail_vs_success_events():
    provider = FakeProvider()
    ghost = Ghost(provider)
    _ = list(ghost.react("bad", exit_code=1, stdout="", stderr="x", seed=2))
    _ = list(ghost.react("good", exit_code=0, stdout="y", stderr="", seed=2))
    assert provider.calls == 2


def test_react_canned_code_placeholder_fills():
    provider = FakeProvider(available=False)
    ghost = Ghost(provider)
    out = "".join(ghost.react("bad", exit_code=3, stdout="", stderr="x", seed=0))
    assert "{code}" not in out


def test_phase1_stability():
    # empty history chat and empty input paths must not explode
    ghost = Ghost(FakeProvider())
    assert "".join(ghost.chat("", recent=[], sanity=0))


def test_broken_provider_midstream_falls_back():
    class ExplodingProvider(FakeProvider):
        def chat_stream(self, messages):
            raise RuntimeError("midstream curse")

    ghost = Ghost(ExplodingProvider())
    out = "".join(ghost.react("ls", exit_code=0, stdout="", stderr=""))
    assert out


def test_ollama_provider_chain_integration():
    # integration: Ghost on OllamaProvider against an empty model list => offline
    provider = OllamaProvider(transport=httpx_mock_transport_empty(), model="gemma3:1b")
    assert OllamaProvider is not None
    ghost = Ghost(provider)
    assert not ghost.awake


def httpx_mock_transport_empty():
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    return httpx.MockTransport(handler)
