"""Provider interface for the ghost's brain — local backends only.

A provider must work with zero network beyond the local machine and must
degrade gracefully; Poltergeist never depends on a cloud API.
"""

from __future__ import annotations

import abc
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


class GhostProvider(abc.ABC):
    """A local model backend speaking short theatrical lines."""

    name: str = "abstract"

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Cheap connectivity/health probe."""

    @abc.abstractmethod
    def resolve_model(self) -> str | None:
        """The concrete model id to use, or None if nothing is installed."""

    @abc.abstractmethod
    def chat_stream(self, messages: list[Message]) -> Iterator[str]:
        """Stream a completion as text chunks; must not raise when offline —
        it may raise ProviderUnavailable, which the caller converts into
        canned fallback lines."""

    def chat(self, messages: list[Message]) -> str:
        return "".join(self.chat_stream(messages))


class ProviderUnavailable(RuntimeError):
    pass


def context_prefix(os_name: str, cwd: str, shell: str) -> str:
    """Standard environment blurb appended to chat messages (redacted upstream)."""
    return f"[context: os={os_name} shell={shell} cwd={cwd}]"


def messages_to_dicts(messages: list[Message]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in messages]
