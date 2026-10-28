"""Cross-platform builtin interception (pure parsing, no I/O)."""

import pytest

from poltergeist.shell import _intercept as ic


def test_cd_plain_posix():
    op = ic.parse_cd("cd /tmp", posix=True)
    assert op is not None and op.kind == "cd" and op.target == "/tmp"


def test_cd_home_posix():
    op = ic.parse_cd("cd", posix=True)
    assert op is not None and op.target == "home"


def test_cd_quoted():
    op = ic.parse_cd('cd "/a b/kern"', posix=True)
    assert op is not None and op.target == "/a b/kern"


def test_cd_compound_not_intercepted():
    assert ic.parse_cd("cd /tmp && echo hi", posix=True) is None
    assert ic.parse_cd("echo hi | cd /tmp", posix=True) is None


def test_cd_not_cd():
    assert ic.parse_cd("pod /tmp", posix=True) is None


def test_cd_prev():
    op = ic.parse_cd("cd -", posix=True)
    assert op is not None and op.target == "prev"


def test_cd_windows_flags():
    op = ic.parse_cd("cd /d C:\\Users", posix=False)
    assert op is not None and op.target == "C:\\Users"
    op2 = ic.parse_cd("Set-Location -Path C:\\x", posix=False)
    assert op2 is not None and op2.target == "C:\\x"


def test_resolve_cd_relative():
    op = ic.BuiltinOp(kind="cd", target="sub")
    out = ic.resolve_cd_target(op, ic.Path.home() / "tmp", None)
    expected = (ic.Path.home() / "tmp" / "sub").resolve()
    assert ic.Path(out) == expected


def test_resolve_cd_tilde():
    op = ic.BuiltinOp(kind="cd", target="~/repro")
    out = ic.resolve_cd_target(op, ic.Path("/tmp"), None)
    assert str(out).endswith("repro")


@pytest.mark.parametrize(
    "cmd,posix,expect",
    [
        ("export POLTERGEIST_TEST=1", True, ("set", "POLTERGEIST_TEST", "1")),
        ("POLTERGEIST_TEST=2 tar -xf", True, None),
        ("unset POLTERGEIST_TEST", True, ("unset", "POLTERGEIST_TEST", "")),
        ("set POLTERGEIST_TEST=3", False, ("set", "POLTERGEIST_TEST", "3")),
        ("set POLTERGEIST_TEST=", False, ("unset", "POLTERGEIST_TEST", "")),
        ("$env:POLTERGEIST_TEST = 'ghost'", False, ("set", "POLTERGEIST_TEST", "ghost")),
    ],
)
def test_parse_env(cmd, posix, expect):
    op = ic.parse_env(cmd, posix=posix)
    if expect is None:
        assert op is None
    else:
        assert op is not None and (op.env_kind, op.key, op.value) == expect


def test_env_export_then_command_not_intercepted():
    assert ic.parse_env("export A=1 && ls", posix=True) is None


def test_env_multiple_exports_not_intercepted():
    # `export A=1 B=2` is more than one assignment — let the shell do it
    op = ic.parse_env("export A=1 B=2", posix=True)
    assert op is None or op.key == "A"  # conservative: only strict match (None) allowed
    assert op is None
