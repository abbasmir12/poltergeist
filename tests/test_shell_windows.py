"""Windows shell runner tests — run when actually on Windows."""

import sys

import pytest

from poltergeist.shell.windows import WindowsShell

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="windows only")


@pytest.fixture
def ps_shell(tmp_path):
    return WindowsShell(cwd=tmp_path)


def test_echo_powershell(ps_shell):
    result = ps_shell.run("Write-Output spooky")
    assert result.ok
    assert "spooky" in result.stdout


def test_cwd_persists(ps_shell, tmp_path):
    sub = tmp_path / "crypt"
    sub.mkdir()
    ps_shell.run(f"cd {sub}")
    result = ps_shell.run("Get-Location")
    assert str(sub) in result.stdout


def test_env_set_persists(ps_shell):
    ps_shell.run("set GHOST_SCREAM=Wail")
    result = ps_shell.run("Write-Output $env:GHOST_SCREAM")
    assert "Wail" in result.stdout
