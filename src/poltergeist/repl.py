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

import rich.box
import rich.panel
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI as PTANSI
from prompt_toolkit.history import InMemoryHistory
from rich.color import Color
from rich.console import Console

from .config import Config, save_config
from .ghost import Ghost, OllamaProvider
from .safety import AuditLog, classify
from .safety.redact import redact_output
from .shell import Shell
from .ui import Sanity
from .ui.capabilities import detect as detect_caps
from .ui.sequences import intro as play_intro
from .ui.sequences import outro as play_outro
from .ui.speech import corrupt, typewriter
from .ui.terminal import exorcise_terminal, possess
from .ui.theme import get_theme

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
        self.session = None  # created lazily in _read_input (prompt_toolkit needs a real console)
        self.recent_failures = 0
        self._rng = random.Random(seed)
        self.stdin_is_tty = sys.stdin.isatty()
        self.caps = detect_caps(self.console)
        self.theme = get_theme(config.theme)
        self.palette = None
        self._ctrl_handler = None

    # -- speech ------------------------------------------------------------
    def say(self, text: str, *, style: str | None = None, idle: bool = False) -> None:
        """Ghost speech: typewriter + corruption (all effects degrade safely)."""
        style = style or f"italic {self.theme.ghost}"
        glitch_level = 2 if self.sanity.value < 30 else (1 if self.sanity.value < 60 else 0)
        spoken = corrupt(
            text,
            level=glitch_level,
            sanity=self.sanity.value,
            rng=self._rng,
            unicode=self.caps.unicode,
        )
        if self.caps.tty and sys.stdout.isatty():
            try:
                typewriter(self.console, f"🜸 {spoken}", style=style)
                return
            except KeyboardInterrupt:
                return
        self.console.print(f"🜸 {spoken}", style=style)

    def say_stream(self, chunks) -> None:
        self.console.print("🜸 ", style="italic pale_turquoise4", end="")
        self.console.print(chunks, style="italic pale_turquoise4", end="")
        self.console.print()

    # -- prompt / loop -------------------------------------------------------
    def run(self) -> int:
        # Possess the whole terminal (bg/fg/cursor/title) with a random
        # haunted palette — different every session.
        if self.caps.tty:
            self.palette = possess(rng=self._rng)
        # Ensure the terminal is restored on ANY exit path: Ctrl+C, Ctrl+D,
        # SIGTERM, window close, or an unhandled exception. Without this the
        # haunted background color would linger after `haunt` is killed.
        import atexit
        import signal

        def _restore_now(*_args) -> None:
            try:
                exorcise_terminal()
            except Exception:  # noqa: BLE001
                pass

        atexit.register(_restore_now)
        if hasattr(signal, "SIGTERM"):
            try:
                signal.signal(signal.SIGTERM, lambda *_: (_restore_now(), sys.exit(0)))
            except (OSError, ValueError):
                pass  # not in main thread or not allowed
        if hasattr(signal, "SIGINT") and not self.stdin_is_tty:
            try:
                signal.signal(signal.SIGINT, lambda *_: (_restore_now(), sys.exit(130)))
            except (OSError, ValueError):
                pass
        # Windows console control handler (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT,
        # CTRL_SHUTDOWN_EVENT) — fires when the window is closed.
        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)

                def _console_ctrl(ctrl_type: int) -> bool:
                    # 0=CTRL_C, 1=CTRL_BREAK, 2=CTRL_CLOSE, 5=CTRL_LOGOFF, 6=CTRL_SHUTDOWN
                    if ctrl_type in (0, 1, 2, 5, 6):
                        _restore_now()
                        return True
                    return False

                self._ctrl_handler = HandlerRoutine(_console_ctrl)
                kernel32.SetConsoleCtrlHandler(self._ctrl_handler, True)
            except Exception:  # noqa: BLE001
                self._ctrl_handler = None
        if self.config.intro and self.caps.tty:
            play_intro(self.console, self.theme, caps=self.caps, seed=self._rng.random())
        if not self.ghost.try_wake():
            self.console.print(
                rich.panel.Panel(
                    "[italic]No local model answered the summoning — the ghost speaks in its "
                    "canned voice for now. Install Ollama, then `ollama pull "
                    f"{self.config.model}`, "
                    "and run "
                    "`haunt doctor` to diagnose. Nothing leaves this machine either way.[/italic]",
                    border_style=self.theme.panel_border,
                    box=rich.box.ROUNDED,
                )
            )
        else:
            self.console.print(
                f"[dim italic {self.theme.whisper}]🜸 bound to local model "
                f"[bold]{self.ghost.model}[/bold] — everything stays on this machine[/dim italic "
                f"{self.theme.whisper}]"
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
            if self.session is None:
                self.session = PromptSession(history=InMemoryHistory())
            return self.session.prompt(self._prompt_text())
        return input(self._make_plain_prompt())

    def _make_plain_prompt(self) -> str:
        """Non-tty fallback prompt: no ANSI, ASCII-safe glyph."""
        glyph = self.theme.glyph_prompt_ascii
        return f"{glyph} {self._cwd_display()} › "

    @staticmethod
    def _sgr(color: str | None, *, dim: bool = False, italic: bool = False) -> str:
        """SGR sequence for a rich color name (truecolor ANSI), or '' if none."""
        codes: list[str] = []
        if italic:
            codes.append("3")
        if dim:
            codes.append("2")
        if color:
            try:
                rgb = Color.parse(color).get_truecolor()
                codes += ["38", "2", str(rgb.red), str(rgb.green), str(rgb.blue)]
            except Exception:  # noqa: BLE001 — an unknown color never breaks the prompt
                pass
        return f"\x1b[{';'.join(codes)}m" if codes else ""

    def _prompt_text(self) -> PTANSI:
        """prompt_toolkit prompt as ANSI formatted text.

        NOTE: prompt_toolkit does NOT parse rich markup — feeding it rich
        strings printed raw `[italic dim …]` tags on a live Windows séance.
        It must receive ANSI escape codes instead.
        """
        cwd = self._cwd_display()
        glyph = (
            self.theme.glyph_prompt
            if self.caps.unicode and self.config.flicker
            else self.theme.glyph_prompt_ascii
        )
        dir_sgr = self._sgr(self.theme.prompt_dir, dim=True, italic=True)
        sep_sgr = self._sgr(self.theme.whisper, dim=True)
        return PTANSI(f" {glyph} {dir_sgr}{cwd}\x1b[0m{sep_sgr} › \x1b[0m")

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
        level_before = self.sanity.level
        self.sanity.on_command(exit_code=result.exit_code)
        if self.stdin_is_tty and result.exit_code != 0:
            fail = self.theme.fail
            self.console.print(
                f"[{fail}]☠ exit {result.exit_code}[/]"
                f"[dim {fail}] — {self.sanity.bar()} ({self.sanity.level})[/dim {fail}]"
            )
        elif self.stdin_is_tty and result.exit_code == 0 and level_before != self.sanity.level:
            pass  # meter drifts silently upward; the ghost may comment below

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
        color = self.theme.sanity_bar[0] if self.sanity.value > 40 else self.theme.fail
        whisper = self.theme.whisper
        self.console.print(
            f"[bold]sanity[/bold]  [{color}]{self.sanity.bar()}[/{color}] — {self.sanity.level}"
            f"  [dim {whisper}]failures curdle it; clean exits heal it[/dim {whisper}]"
        )

    def _set_theme(self, name: str) -> None:
        if name.lower() not in ("classic", "ofrenda", "slasher"):
            self.say("Themes: classic · ofrenda · slasher. Reality offers only these.", style="dim")
            return
        self.config.theme = name.lower()
        self.theme = get_theme(name.lower())
        self.ghost.theme = name.lower()
        save_config(self.config)
        self.say(f"The room rearranges itself into a {name.lower()} vision.")

    def _exorcise(self) -> int:
        self.say(self.ghost.whisper("exorcise"))
        play_outro(self.console, self.theme, caps=self.caps, seed=self._rng.random())
        exorcise_terminal()
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
        exorcise_terminal()
    except Exception:  # noqa: BLE001
        pass
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\x1b[?25h\x1b[0m")
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 — restoration itself must never fail loudly
        pass
