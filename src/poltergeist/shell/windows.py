"""Command execution on Windows (PowerShell preferred, cmd.exe fallback)."""

from __future__ import annotations

import codecs
import shutil
import signal
import subprocess
import threading
from pathlib import Path

from . import _intercept
from .base import (
    OutputCallback,
    Shell,
    ShellResult,
)
from .posix import LineSplitter

CHUNK = 4096


def posix_line_splitter() -> LineSplitter:
    return LineSplitter()


def _powershell_exe() -> str | None:
    for exe in ("pwsh", "powershell"):
        path = shutil.which(exe)
        if path:
            return path
    return None


class WindowsShell(Shell):
    """Haunts PowerShell (or cmd.exe) via `powershell -NoProfile -Command`."""

    def __init__(self, cwd: str | Path | None = None, *, powershell: str | None = None) -> None:
        super().__init__(cwd)
        self._ps = powershell or _powershell_exe()
        self._posix = False

    def _shell_name(self) -> str:
        return (
            ("pwsh" if self._ps and "pwsh" in self._ps.lower() else "powershell")
            if self._ps
            else "cmd"
        )

    def _spawn(self, command: str):
        if self._ps:
            argv = [self._ps, "-NoProfile", "-NonInteractive", "-Command", command]
        else:
            argv = ["cmd.exe", "/d", "/c", command]
        creationflags = 0
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):  # windows-only constant
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(  # noqa: S603,S607 — user-authored command by design
            argv,
            cwd=self._child_cwd(),
            env=self._child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            bufsize=0,
            creationflags=creationflags,
        )

    def _interrupt(self, proc) -> None:
        # CTRL_BREAK reaches child processes in the new group better than CTRL_C
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        except Exception:  # noqa: BLE001
            proc.kill()

    def _stream_stdout(self, proc, emit: OutputCallback) -> None:
        assert proc.stdout is not None
        self._stream(proc.stdout, emit, "stdout")

    def _drain_stderr(self, proc, emit: OutputCallback) -> threading.Thread:
        def worker() -> None:
            assert proc.stderr is not None
            self._stream(proc.stderr, emit, "stderr")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    @staticmethod
    def _stream(pipe, emit: OutputCallback, stream: str) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        splitter = posix_line_splitter()
        while True:
            try:
                chunk = pipe.read1(CHUNK)
            except OSError:
                break
            if not chunk:
                break
            for line in splitter.feed(decoder.decode(chunk)):
                emit(line, stream)
        tail = splitter.eof()
        if tail:
            emit(tail, stream)

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
        except (RuntimeError, OSError):
            target = None
        if target is not None and not target.is_dir():
            display = target if op.target != "home" else Path.home()
            return ShellResult(
                command=f"cd {op.target}",
                exit_code=1,
                stdout="",
                stderr=f"cd : Cannot find path '{display}' because it does not exist.",
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
