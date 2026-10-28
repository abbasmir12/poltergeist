"""The haunted REPL — user command execution, ghost commentary, exorcism.

Phase 1 scope: solid loop, live-streaming command execution, sanity meter,
theme switching, help, `ghost,` chat, offline fallbacks, safe terminal
teardown. Ghost command proposals and autonomy UI land in phase 4; the ghost
*never* spawns commands on its own in this phase.
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import random
import sys
from time import sleep

import rich.box
import rich.panel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from .config import Config, save_config
from .ghost import Ghost, OllamaProvider
from .safety import AuditLog, classify
from .safety.redact import redact_output
from .shell import Shell
from .ui import Sanity

NIGHT_HOURS = range(0, 5)  # whisper window: 00:00–04:59 local


def _night_now() -> bool:
    return _dt.datetime.now().hour in NIGHT_HOURS


class HauntedRepl:
    def __init__(
        self,
        config: Config,
        shell: Shell,
        *,
        console: Console | None = None,
        provider: OllamaProvider | None = None,
        seed: object = None,
    ) -> None:
        self.config = config
        self.shell = shell
        self.console = console or Console(highlight=False)
        self.provider = provider or OllamaProvider(base_url=config.ollama_url, model=config.model)
        self.ghost = Ghost(self.provider, theme=config.theme)
        self.sanity = Sanity()
        self.audit = AuditLog(Config.audit_path())
        self.history: list[tuple[str, int]] = []
        self.session = PromptSession(history=InMemoryHistory())
        self.recent_failures = 0
        self._rng = random.Random(seed)
        self.stdin_is_tty = sys.stdin.isatty()

    # -- speech ------------------------------------------------------------
    def say(self, text: str, *, style: str = "italic pale_turquoise4") -> None:
        self.console.print(f"🜸 {text}", style=style)

    def say_stream(self, chunks) -> None:
        self.console.print("🜸 ", style="italic pale_turquoise4", end="")
        self.console.print(chunks, style="italic pale_turquoise4", end="")
        self.console.print()

    # -- prompt / loop -------------------------------------------------------
    def run(self) -> int:
        if not self.ghost.try_wake():
            self.console.print(
                rich.panel.Panel(
                    "[italic]No local model answered the summoning — the ghost speaks in its "
                    "canned voice for now. Install Ollama, then `ollama pull gemma3:1b`, and run "
                    "`haunt doctor` to diagnose. Nothing leaves this machine either way.[/italic]",
                    border_style="dark_orange3",
                    box=rich.box.ROUNDED,
                )
            )
        self.say(self.ghost.whisper("greet", seed=self._rng.random()))
        try:
            while True:
                try:
                    text = self._read_input().strip()
                except (UnicodeDecodeError, OSError):
                    continue
                if not text:
                    continue
                try:
                    if text in {"exorcise", "quit", "exit"}:
                        return self._exorcise()
                    if text == "help":
                        self._help()
                        continue
                    if text == "sanity":
                        self._print_sanity()
                        continue
                    if text.startswith("theme "):
                        self._set_theme(text.split(None, 1)[1])
                        continue
                    if text.startswith(("ghost,", "?", "ghost?")):
                        self._chat(text)
                        continue
                    self._execute(text)
                except KeyboardInterrupt:
                    self.say(
                        "Interrupted — even ghosts respect Ctrl+C. (Use `exorcise` to leave.)",
                        style="dim",
                    )
                    continue
        except EOFError:
            return self._exorcise()
        finally:
            _restore_terminal()

    def _read_input(self) -> str:
        """prompt_toolkit when it is real terminal; plain input() otherwise."""
        if self.stdin_is_tty:
            return self.session.prompt(self._prompt_text())
        return input(self._make_plain_prompt())

    def _make_plain_prompt(self) -> str:
        return f"{self._cwd_display()} › "

    def _prompt_text(self) -> str:
        cwd = self._cwd_display()
        glyph = "👻" if self.config.flicker else "*"
        return f" {glyph}  [italic dim]{cwd}[/italic dim] › "

    def _cwd_display(self) -> str:
        cwd = self.shell.cwd
        home = str(pathlib.Path.home())
        return ("~" + cwd[len(home) :]) if cwd.startswith(home) else cwd

    # -- command execution ---------------------------------------------------
    def _execute(self, text: str) -> None:
        verdict = classify(text)

        def stream(line: str, channel: str) -> None:
            style = "bright_black" if channel == "stderr" else ""
            self.console.print(line, end="", style=style)

        if self.stdin_is_tty:
            self.console.print(self._render_command_header(text), end="")

        result = self.shell.run(text, on_output=stream)
        self.history.append((text, result.exit_code))
        self.sanity.on_command(exit_code=result.exit_code)

        if verdict.blocked:
            self.say(
                "No. That spell unbinds things that should not be unbound. "
                "It does not run — not even for spectacle.",
                style="red3",
            )
        elif result.exit_code != 0:
            self.recent_failures += 1
            if self.recent_failures >= 3:
                self.recent_failures = 0
                self.say(self.ghost.whisper("cycle_detect"))
                self._record(verdict, result)
                return
        else:
            self.recent_failures = 0

        comment = None
        wants_comment = result.exit_code != 0 or self._rng.random() < self.config.commentary_rate
        if wants_comment:
            comment = "".join(
                self.ghost.react(
                    text,
                    exit_code=result.exit_code,
                    stdout=redact_output(result.stdout),
                    stderr=redact_output(result.stderr),
                    sanity=self.sanity.value,
                    seed=self._rng.random(),
                )
            ).strip()
            if comment:
                self.say(comment)
        self._record(verdict, result, comment)
        if _night_now() and self._rng.random() < 0.08:
            self.say(self.ghost.whisper("night"), style="dim italic")

    @staticmethod
    def _render_command_header(text: str) -> str:
        return f"[dim purple]⟨ {text} ⟩[/dim purple]\n"

    def _record(self, verdict, result, comment: str | None = None) -> None:
        self.audit.record(
            command=result.command,
            verdict=verdict.verdict,
            approved_by="user",
            exit_code=result.exit_code,
            output=(result.stdout + result.stderr)[-1200:],
            shell=self.shell.shell_name,
            cwd=self.shell.cwd,
            ghost_comment=comment or "",
        )

    # -- ghost chat ------------------------------------------------------------
    def _chat(self, text: str) -> None:
        message = text
        for prefix in ("ghost,", "ghost?", "?"):
            if message.startswith(prefix):
                message = message[len(prefix) :].strip()
        message = redact_output(message)
        if not message:
            self.say("Speak, even if only to test whether this silence is real.")
            return
        try:
            self.say_stream(
                "*"
                + "".join(
                    self.ghost.chat(
                        message, recent=list(self.history[-8:]), sanity=self.sanity.value
                    )
                )
            )
        except Exception:  # noqa: BLE001 — chat must never crash the loop
            self.say(self.ghost.whisper("chat_offline"), style="dim")

    # -- misc commands ---------------------------------------------------------
    def _print_sanity(self) -> None:
        self.console.print(f"[bold]sanity[/bold]  {self.sanity.bar()}  — {self.sanity.level}")

    def _set_theme(self, name: str) -> None:
        if name.lower() not in ("classic", "ofrenda", "slasher"):
            self.say("Themes: classic · ofrenda · slasher. Reality offers only these.", style="dim")
            return
        self.config.theme = name.lower()
        self.ghost.theme = name.lower()
        save_config(self.config)
        self.say(f"The room rearranges itself into a {name.lower()} vision.")

    def _exorcise(self) -> int:
        self.say(self.ghost.whisper("exorcise"))
        sleep(0.25)
        return 0

    def _help(self) -> None:
        self.console.print(
            rich.panel.Panel(
                "[bold]haunted commands[/bold]\n"
                "  ghost, <chat> · ?<chat>      consult the poltergeist\n"
                "  sanity                       show the sanity meter\n"
                "  theme classic|ofrenda|slasher  possession styles\n"
                "  exorcise                     release your terminal (exit)\n"
                "  anything else runs in your real shell, streamed live,\n"
                "  and the ghost may comment — thoughtfully, on failures; sometimes\n"
                "  on success. Command proposals arrive in a later haunting (phase 4).",
                border_style="dark_orange3",
                box=rich.box.ROUNDED,
            )
        )


def _restore_terminal() -> None:
    """Best-effort ANSI cleanup so nothing leaves the TTY possessed."""
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\x1b[?25h\x1b[0m")  # cursor visible, default SGR
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 — restoration itself must never fail loudly
        pass
