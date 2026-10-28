"""Command execution in the user's POSIX shell (bash/zsh/sh/fish)."""

from __future__ import annotations

import codecs
import os
import signal
import subprocess
import threading
from pathlib import Path

from . import _intercept
from .base import (
    INTERNAL_ERROR_EXIT,
    OutputCallback,
    Shell,
    ShellResult,
)


class LineSplitter:
    """Chunk -> complete lines logic (keeps a partial buffer until newline)."""

    def __init__(self) -> None:
        self.buffer = ""

    def feed(self, text: str) -> list[str]:
        self.buffer += text
        if "\n" not in self.buffer:
            return []
        complete = self.buffer.split("\n")
        self.buffer = complete.pop()
        return [line + "\n" for line in complete]

    def eof(self) -> str:
        pending, self.buffer = self.buffer, ""
        return pending


CHUNK = 4096

_SAFE_SHELLS = ("bash", "zsh", "sh", "fish", "dash", "ksh", "ash")


def _detect_shell() -> str:
    env_shell = os.environ.get("SHELL", "")
    if env_shell and Path(env_shell).name in _SAFE_SHELLS:
        return env_shell
    # .best effort, keep POSIX-portable without hardcoding Linux-only paths
    for candidate in (
        "/bin/bash",
        "/bin/sh",
        "/usr/bin/bash",
        "/usr/bin/sh",
        "/usr/local/bin/bash",
    ):
        if os.path.exists(candidate):
            return candidate
    return "sh"


class PosixShell(Shell):
    """Haunts bash/zsh/fish/etc. via `$SHELL -c` (or a safe fallback)."""

    def __init__(self, cwd: str | Path | None = None, *, shell_path: str | None = None) -> None:
        super().__init__(cwd)
        self._shell_path = shell_path or _detect_shell()
        self._posix = True

    def _shell_name(self) -> str:
        return Path(self._shell_path).name

    # -- builtins ---------------------------------------------------------
    def _maybe_intercept(self, command: str) -> ShellResult | None:
        cwd = self._cwd
        cd_op = _intercept.parse_cd(command, posix=self._posix)
        if cd_op is not None:
            return self._apply_cd(cd_op, cwd)
        env_op = _intercept.parse_env(command, posix=self._posix)
        if env_op is not None:
            return self._apply_env(env_op, command)
        return None

    def _apply_cd(self, op: _intercept.BuiltinOp, cwd: Path) -> ShellResult:
        try:
            target = _intercept.resolve_cd_target(op, cwd, self._prev_cwd)
        except (RuntimeError, OSError):  # unresolvable target
            target = None
        if target is not None and not target.is_dir():
            return ShellResult(
                command=f"cd {op.target}",
                exit_code=1,
                stdout="",
                stderr=f"cd: no such directory: {op.target}",
                duration_ms=0,
                cwd=str(cwd),
            )
        self._prev_cwd = cwd
        self._cwd = target or cwd
        return ShellResult(
            command=f"cd {op.target}",
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=0,
            cwd=str(self._cwd),
        )

    def _apply_env(self, op: _intercept.BuiltinOp, command: str) -> ShellResult:
        if op.env_kind == "set":
            self.set_env(op.key, op.value)
        else:
            self.unset_env(op.key)
        return ShellResult(
            command=command, exit_code=0, stdout="", stderr="", duration_ms=0, cwd=str(self._cwd)
        )

    # -- execution --------------------------------------------------------
    def _spawn(self, command: str):
        return subprocess.Popen(  # noqa: S603 — command is user-authored by design
            [self._shell_path, "-c", command],
            cwd=self._child_cwd(),
            env=self._child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            bufsize=-1,  # buffered, but BufferedReader.read1 keeps live streaming
            start_new_session=True,  # signal-only process group (Ctrl+C kills tree)
        )

    def _interrupt(self, proc) -> None:
        # start_new_session → kill the whole process group.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()

    def _stream_stdout(self, proc, emit: OutputCallback) -> None:
        assert proc.stdout is not None
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        splitter = LineSplitter()
        while True:
            try:
                chunk = proc.stdout.read1(CHUNK)
            except OSError:
                break
            if not chunk:
                break
            for line in splitter.feed(decoder.decode(chunk)):
                emit(line, "stdout")
        tail = splitter.eof()
        if tail:
            emit(tail, "stdout")

    def _drain_stderr(self, proc, emit: OutputCallback) -> threading.Thread:
        def worker() -> None:
            assert proc.stderr is not None
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            splitter = LineSplitter()
            while True:
                try:
                    chunk = proc.stderr.read1(CHUNK)
                except OSError:
                    return
                if not chunk:
                    return
                for line in splitter.feed(decoder.decode(chunk)):
                    emit(line, "stderr")
            tail = splitter.eof()
            if tail:
                emit(tail, "stderr")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread


__all__ = ["PosixShell", "INTERNAL_ERROR_EXIT"]
