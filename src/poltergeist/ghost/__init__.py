"""The Ghost: provider + persona + fallbacks fused into one theatrical being."""

from __future__ import annotations

from collections.abc import Iterator

from .fallbacks import pick
from .ollama import OllamaProvider
from .persona import chat_prefix, commentary_prompt, persona_for
from .provider import GhostProvider, Message

__all__ = ["Ghost", "OllamaProvider", "GhostProvider", "Message"]


class Ghost:
    """Facade used by the REPL. Never raises on provider failure."""

    def __init__(self, provider: GhostProvider, theme: str = "classic") -> None:
        self.provider = provider
        self.theme = theme
        self.model: str | None = None
        self.try_wake()

    # -- lifecycle ------------------------------------------------------------
    def try_wake(self) -> bool:
        """Attempt to bind a local model; cache its name."""
        self.model = self.provider.resolve_model() if self.provider.is_available() else None
        return self.model is not None

    @property
    def awake(self) -> bool:
        return self.model is not None

    # -- speech -----------------------------------------------------------------
    def _persona(self, sanity: int | None) -> str:
        return persona_for(self.theme, sanity=sanity)

    def _stream_or_fallback(
        self,
        messages: list[Message],
        fallback_event: str,
        sanity: int | None,
        seed: object = None,
        format_kwargs: dict | None = None,
    ) -> Iterator[str]:
        if not self.awake:
            yield pick(fallback_event, self.theme, seed=seed, format_kwargs=format_kwargs)
            return
        try:
            got_any = False
            for piece in self.provider.chat_stream(
                [Message("system", self._persona(sanity)), *messages]
            ):
                got_any = True
                yield piece
            if not got_any:
                yield pick(fallback_event, self.theme, seed=seed, format_kwargs=format_kwargs)
        except Exception as exc:  # noqa: BLE001 — ProviderUnavailable and midstream faults
            self.model = None
            yield f"(The séance broke mid-ritual: {exc})"

    def react(
        self,
        command: str,
        *,
        exit_code: int,
        stdout: str,
        stderr: str,
        sanity: int | None = None,
        seed: object = None,
    ) -> Iterator[str]:
        event = "comment_success" if exit_code == 0 else "comment_fail"
        prompt = commentary_prompt(command, exit_code, stderr, stdout)
        yield from self._stream_or_fallback(
            [Message("user", prompt)],
            event,
            sanity,
            seed,
            format_kwargs={"code": exit_code, "n": abs(exit_code)},
        )

    def chat(
        self, text: str, *, recent: list[tuple[str, int]], sanity: int | None = None
    ) -> Iterator[str]:
        context = chat_prefix(recent)
        yield from self._stream_or_fallback(
            [Message("user", context + text)], "chat_offline", sanity
        )

    def whisper(self, event: str, sanity: int | None = None, seed: object = None) -> str:
        """Unprompted lines (idle, night-hour). Offline-safe."""
        return pick(event, self.theme, seed=seed)
