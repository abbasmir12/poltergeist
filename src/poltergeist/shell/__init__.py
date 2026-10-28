"""Cross-platform haunted command execution."""

from __future__ import annotations

from pathlib import Path

from .base import Shell, ShellResult

__all__ = ["Shell", "ShellResult", "create_shell"]


def create_shell(cwd: str | Path | None = None) -> Shell:
    """Return the Shell for the current platform."""
    from ..platform import is_windows

    if is_windows():
        from .windows import WindowsShell

        return WindowsShell(cwd=cwd)
    from .posix import PosixShell

    return PosixShell(cwd=cwd)
