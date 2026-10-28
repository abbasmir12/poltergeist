"""Integration tests for the POSIX shell runner (Linux/macOS)."""

import os
import signal
import sys
import threading
import time

import pytest

from poltergeist.shell.posix import PosixShell

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="posix shell semantics")


def test_run_echo_streams_and_captures():
    shell = PosixShell()
    lines: list[tuple[str, str]] = []
    result = shell.run("echo spooky", on_output=lambda line, ch: lines.append((line, ch)))
    assert result.ok
    assert result.stdout.strip() == "spooky"
    assert any("spooky" in line for line, _ in lines)


def test_run_stderr_capture():
    shell = PosixShell()
    result = shell.run("echo wail 1>&2")
    assert result.exit_code == 0
    assert "wail" in result.stderr


def test_exit_code_propagates():
    shell = PosixShell()
    result = shell.run("false")
    assert result.exit_code == 1 and not result.ok


def test_cwd_persists_via_cd():
    shell = PosixShell()
    shell.run("cd /tmp")
    result = shell.run("pwd")
    assert result.stdout.strip() == "/tmp"
    assert shell.cwd == "/tmp"


def test_cd_missing_dir_errors_and_keeps_cwd(tmp_path):
    shell = PosixShell()
    before = shell.cwd
    result = shell.run("cd /nonexistent-ghouls-4-arvos")
    assert result.exit_code != 0
    assert "no such directory" in result.stderr
    assert shell.cwd == before


def test_cd_prev_swaps():
    shell = PosixShell()
    origin = shell.cwd
    shell.run("cd /tmp")
    shell.run("cd -")
    assert shell.cwd == origin


def test_env_export_persists():
    shell = PosixShell()
    shell.run("export GHOST_SCREAM=Wail")
    shell.run("GHOST_SCREAM2=Second")  # bare assignment
    assert shell.run("echo $GHOST_SCREAM").stdout.strip() == "Wail"
    result = shell.run("echo $GHOST_SCREAM2")
    assert result.stdout.strip() == "Second"


def test_env_prefix_assignment_does_not_break_command():
    shell = PosixShell()
    shell.run("FIRST=one")
    result = shell.run("GHOST_SCREAM=Three true")  # one-shot env → handled by real shell
    assert result.ok
    assert shell.run("echo $GHOST_SCREAM").stdout.strip() == ""  # did not persist


def test_env_unset():
    shell = PosixShell()
    shell.run("export GHOST_SCREAM=1")
    shell.run("unset GHOST_SCREAM")
    result = shell.run("echo ${GHOST_SCREAM:+set}")
    assert result.stdout.strip() == ""


def test_streaming_is_live():
    shell = PosixShell()
    stamps: list[float] = []
    result = shell.run(
        "for i in 1 2 3; do echo tick-$i; sleep 0.25; done",
        on_output=lambda line, ch: stamps.append(time.monotonic()),
    )
    assert result.ok
    assert "tick-3" in result.stdout
    assert len(stamps) >= 3
    assert stamps[-1] - stamps[0] >= 0.35  # 3 spaced outputs prove live streaming


def test_timeout_kills_process():
    shell = PosixShell()
    result = shell.run("sleep 8", timeout=0.5)
    assert result.timed_out
    assert result.exit_code == 124
    assert result.duration_ms < 3000


def test_interrupt_lands_as_ctrl_c():
    shell = PosixShell()
    timer = threading.Timer(0.4, lambda: os.kill(os.getpid(), signal.SIGINT))
    timer.start()
    result = shell.run("sleep 5")
    timer.join()
    assert result.interrupted
    assert result.exit_code == 130


def test_shell_name():
    shell = PosixShell(shell_path="/bin/bash")
    assert shell.shell_name == "bash"


def test_scoped_transcript_ordering():
    shell = PosixShell()
    seen: list[str] = []
    result = shell.run(
        "echo a; echo err 1>&2; echo b",
        on_output=lambda line, ch: seen.append(f"{ch}:{line.strip()}"),
    )
    assert result.ok
    assert "stdout:a" in seen and "stderr:err" in seen and "stdout:b" in seen
