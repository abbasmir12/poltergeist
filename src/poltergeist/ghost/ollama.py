"""Ollama provider — local HTTP on 127.0.0.1, NDJSON streaming."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from ..config import MODEL_FALLBACKS
from .provider import GhostProvider, Message, ProviderUnavailable, messages_to_dicts


class OllamaProvider(GhostProvider):
    name = "ollama"

    ALL_FALLBACK_CHAIN = MODEL_FALLBACKS

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
            "options": {"num_predict": 1024, "temperature": 0.9},
        }
        try:
            with self._client.stream("POST", "/api/chat", json=payload, timeout=120.0) as response:
                if response.status_code != 200:
                    body = response.read().decode("utf-8", errors="replace")[:500]
                    raise ProviderUnavailable(f"ollama status {response.status_code}: {body}")
                got_content = False
                for chunk in response.iter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    # Mid-stream errors arrive as {"error": "..."} lines under a 200
                    if "error" in data:
                        raise ProviderUnavailable(f"ollama error: {data['error']}")
                    msg = data.get("message") or {}
                    # gemma4 is a thinking model: reasoning goes in `thinking`,
                    # the final answer in `content`. Read both so we never lose output.
                    piece = msg.get("content", "") or ""
                    if piece:
                        got_content = True
                        yield piece
                    if data.get("done"):
                        # If we got thinking but no content, the token budget was
                        # consumed by reasoning — surface that instead of silence.
                        if not got_content:
                            thinking = msg.get("thinking", "")
                            if thinking:
                                yield f"[thinking consumed all tokens: {thinking[:120]}…]"
                        break
        except ProviderUnavailable:
            raise
        except httpx.ConnectError as exc:
            raise ProviderUnavailable(f"ollama unreachable: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"stream broken: {exc}") from exc

    def close(self) -> None:
        self._client.close()
