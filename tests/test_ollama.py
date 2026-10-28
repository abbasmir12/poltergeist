"""Ollama provider contract tests — fully offline via MockTransport."""

import json

import httpx
import pytest

from poltergeist.ghost import OllamaProvider
from poltergeist.ghost.provider import Message, ProviderUnavailable


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def make_provider(handler, model="gemma3:1b") -> OllamaProvider:
    return OllamaProvider(model=model, transport=_transport(handler))


def test_ping_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/version"
        return httpx.Response(200, json={"version": "0.3.0"})

    assert make_provider(handler).is_available() is True


def test_ping_unreachable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no séance today")

    assert make_provider(handler).is_available() is False


def test_resolve_preferred_model():
    tags = ["bogus:1", "gemma3:1b", "llama3:8b"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": t} for t in tags]})

    assert make_provider(handler).resolve_model() == "gemma3:1b"


def test_resolve_falls_back_in_chain():
    tags = ["llama3:8b", "gemma3:270m"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": t} for t in tags]})

    assert make_provider(handler).resolve_model() == "gemma3:270m"


def test_resolve_any_installed_as_last_resort():
    tags = ["mistral:7b"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": t} for t in tags]})

    assert make_provider(handler).resolve_model() == "mistral:7b"


def test_resolve_none_when_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    assert make_provider(handler).resolve_model() is None


def test_stream_collects_ndjson():
    chunks = [
        {"message": {"content": "The "}, "done": False},
        {"message": {"content": "cursor "}, "done": False},
        {"message": {"content": "blinks."}, "done": True},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma3:1b"}]})
        body = json.loads(request.content.decode("utf-8"))
        assert body["stream"] is True
        assert body["model"] == "gemma3:1b"
        return httpx.Response(200, content="\n".join(json.dumps(c) for c in chunks))

    provider = make_provider(handler)
    text = "".join(provider.chat_stream([Message("user", "hello?")]))
    assert text == "The cursor blinks."


def test_stream_raises_when_offline():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dead modem")

    provider = make_provider(handler)
    with pytest.raises(ProviderUnavailable):
        list(provider.chat_stream([Message("user", "hi")]))


def test_stream_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    provider = make_provider(handler)
    with pytest.raises(ProviderUnavailable):
        list(provider.chat_stream([Message("user", "hi")]))
