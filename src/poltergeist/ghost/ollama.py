"""Ollama provider — local HTTP on 127.0.0.1, NDJSON streaming."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from .provider import GhostProvider, Message, ProviderUnavailable, messages_to_dicts


class OllamaProvider(GhostProvider):
    name = "ollama"

    ALL_FALLBACK_CHAIN = ("gemma3:1b", "gemma3:270m")

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.requested_model = model
        self._client = httpx.Client(base_url=self.base_url, transport=transport)
        self._resolved: str | None = None

    # -- health -------------------------------------------------------------
    def is_available(self) -> bool:
        try:
            resp = self._client.get("/api/version", timeout=2.0)
            return resp.status_code == 200
        except Exception:  # noqa: BLE001 — network faults mean "not available"
            return False

    def installed_models(self) -> list[str]:
        try:
            resp = self._client.get("/api/tags", timeout=2.0)
            resp.raise_for_status()
            return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:  # noqa: BLE001
            return []

    def resolve_model(self) -> str | None:
        if self._resolved:
            return self._resolved
        tags = self.installed_models()
        tagset = set(tags)
        for candidate in filter(None, (self.requested_model, *self.ALL_FALLBACK_CHAIN)):
            if candidate in tagset:
                self._resolved = candidate
                return candidate
        if tags:
            self._resolved = sorted(tags)[0]
            return self._resolved
        self._resolved = None
        return None

    # -- generation -----------------------------------------------------------
    def chat_stream(self, messages: list[Message]) -> Iterator[str]:
        model = self.resolve_model()
        if not model:
            raise ProviderUnavailable("no ollama model installed")
        payload = {
            "model": model,
            "messages": messages_to_dicts(messages),
            "stream": True,
            "options": {"num_predict": 160, "temperature": 0.9},
        }
        try:
            req = self._client.build_request("POST", "/api/chat", json=payload, timeout=60.0)
            response = self._client.send(req, stream=True)
        except Exception as exc:  # noqa: BLE001 — httpx transport errors
            raise ProviderUnavailable(f"ollama unreachable: {exc}") from exc
        if response.status_code != 200:
            response.close()
            raise ProviderUnavailable(f"ollama status {response.status_code}")
        try:
            for chunk in response.iter_lines():
                if not chunk:
                    continue
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                piece = (data.get("message") or {}).get("content", "")
                if piece:
                    yield piece
                if data.get("done"):
                    break
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"stream broken: {exc}") from exc
        finally:
            response.close()

    def close(self) -> None:
        self._client.close()
