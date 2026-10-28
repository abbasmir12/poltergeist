"""Command-result dataclass and the cross-platform Shell interface."""

from __future__ import annotations

import abc
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


def _join_lines(chunks) -> str:
    return "".join(chunks)


OutputLine = tuple[str, Literal["stdout", "stderr"]]
OutputCallback = Callable[[str, Literal["stdout", "stderr"]], None]

INTERRUPTED_EXIT = 130
TIMEOUT_EXIT = 124
INTERNAL_ERROR_EXIT = 125


@dataclass
class ShellResult:
    """Everything Poltergeist needs to know about a command that ran."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    cwd: str = ""
    timed_out: bool = False
    interrupted: bool = False
    # Lines the user actually saw streaming, in order ("live transcript").
    transcript: list[OutputLine] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.interrupted


class Shell(abc.ABC):
    """A source of command execution in the user's *native* shell.

    Concrete shells (posix/windows) own subprocess invocation and streaming.
    State that must persist between commands (working directory, environment
    overrides) lives *here*, in Python, because spawned shells do not share
    state. Cross-platform builtin handling (`cd`, `export`, `set`) is
    intercepted before a subprocess is ever spawned — see `_intercept.py`.
    """

    def __init__(self, cwd: str | Path | None = None) -> None:
        self._cwd = Path(cwd or Path.home()).resolve()
        self._env: dict[str, str] = {}
        self._unset: set[str] = set()
        self._prev_cwd: Path | None = None
        self._kill_timer: threading.Timer | None = None
        self._timed_out_flag = False

    def _mark_timeout(self, proc) -> None:
        self._timed_out_flag = True
        try:
            proc.kill()
        except OSError:
            pass

    def _timed_out(self) -> bool:
        return self._timed_out_flag

    # -- state ------------------------------------------------------------
    @property
    def cwd(self) -> str:
        return str(self._cwd)

    @property
    def shell_name(self) -> str:
        return self._shell_name()

    @abc.abstractmethod
    def _shell_name(self) -> str: ...

    def set_cwd(self, path: str | Path) -> None:
        self._cwd = Path(path).expanduser().resolve()

    @property
    def env_overrides(self) -> dict[str, str]:
        return dict(self._env)

    def set_env(self, key: str, value: str) -> None:
        key = key.strip()
        if key:
            self._env[key] = value
            self._unset.discard(key)

    def unset_env(self, key: str) -> None:
        key = key.strip()
        self._unset.add(key)
        self._env.pop(key, None)

    def _child_env(self) -> dict[str, str]:
        env = dict(os.environ)
        for key in self._unset:
            env.pop(key, None)
        env.update(self._env)
        return env

    def _child_cwd(self) -> str:
        return str(self._cwd)

    # -- execution --------------------------------------------------------
    def run(
        self,
        command: str,
        *,
        on_output: OutputCallback | None = None,
        timeout: float | None = None,
    ) -> ShellResult:
        """Run `command`, streaming output live via `on_output(line, stream)`."""
        started = time.monotonic()
        intercepted = self._maybe_intercept(command)
        if intercepted is not None:
            result = intercepted
            transcript: list[OutputLine] = result.transcript
            if on_output is not None:
                for line, stream in transcript:
                    on_output(line, stream)
            result.duration_ms = int((time.monotonic() - started) * 1000)
            return result

        proc = self._spawn(command)
        stderr_chunks: list[str] = []
        stdout_chunks: list[str] = []
        transcript = []

        def emit(line: str, stream: Literal["stdout", "stderr"]) -> None:
            transcript.append((line, stream))
            if on_output is not None:
                on_output(line, stream)

        if timeout:
            self._timed_out_flag = False
            self._kill_timer = threading.Timer(timeout, self._mark_timeout, args=(proc,))
            self._kill_timer.daemon = True
            self._kill_timer.start()

        timed_out = False
        interrupted = False
        try:
            stderr_thread = self._drain_stderr(proc, emit)
            self._stream_stdout(proc, emit)
            stderr_thread.join()
            timed_out = self._timed_out()
        except KeyboardInterrupt:
            interrupted = True
            self._interrupt(proc)
        finally:
            if self._kill_timer:
                self._kill_timer.cancel()
                self._kill_timer = None
            try:
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001 — never crash the REPL for a hung proc
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:  # noqa: BLE001
                    pass

        result = ShellResult(
            command=command,
            exit_code=self._exit_code(proc, interrupted=interrupted, timed_out=timed_out),
            stdout=_join_lines(stdout_chunks),
            stderr=_join_lines(stderr_chunks),
            duration_ms=int((time.monotonic() - started) * 1000),
            cwd=self._child_cwd(),
            timed_out=timed_out,
            interrupted=interrupted,
            transcript=transcript,
        )
        # stdout/stderr content is filled by concrete _stream_* methods via
        # `emit`; keep chunk lists simple by re-deriving from transcript.
        result.stdout = _join_lines(line for line, stream in transcript if stream == "stdout")
        result.stderr = _join_lines(line for line, stream in transcript if stream == "stderr")
        return result

    def _exit_code(self, proc, *, interrupted: bool, timed_out: bool) -> int:
        if interrupted:
            return INTERRUPTED_EXIT
        if timed_out:
            return TIMEOUT_EXIT
        try:
            code = proc.returncode
        except Exception:  # noqa: BLE001
            return INTERNAL_ERROR_EXIT
        if code is None:
            return INTERNAL_ERROR_EXIT
        return code

    @abc.abstractmethod
    def _interrupt(self, proc) -> None:
        """Terminate the process tree on Ctrl+C."""

    @abc.abstractmethod
    def _spawn(self, command: str):
        """Popen the native shell with `command` and piped stdio."""

    @abc.abstractmethod
    def _stream_stdout(self, proc, emit: OutputCallback) -> None:
        """Read proc stdout live until EOF (blocking call)."""

    @abc.abstractmethod
    def _drain_stderr(self, proc, emit: OutputCallback) -> threading.Thread:
        """Start a thread draining proc.stderr; return the thread."""

    # -- builtins ---------------------------------------------------------
    @abc.abstractmethod
    def _maybe_intercept(self, command: str) -> ShellResult | None:
        """If `command` is a pure `cd`/env builtin, handle it and return a
        synthetic ShellResult; otherwise return None to spawn a subprocess.
        """
